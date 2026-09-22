"""Synthetic laboratory observation source.

Produces raw observations from a scripted sequence. No OS hook is used.
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence

from keylogix.constants import (
    EVENT_KEY_DOWN,
    EVENT_KEY_UP,
    KIND_RAW,
    PRESENCE_UNAVAILABLE,
    SOURCE_SYNTHETIC,
)
from keylogix.identity import IdentityFactory
from keylogix.model import (
    ModifierState,
    OptionalField,
    Provenance,
    RawObservation,
)
from keylogix.observation.base import ObservationSource
from keylogix.status import Result, Status
from keylogix.timeutil import Clock, SyntheticClock
from keylogix.vk import is_modifier_vk, label_for_vk, modifier_bit_for_vk


def _field_from_script(value: Any, obtained_via: str) -> OptionalField:
    if value is None:
        return OptionalField.unavailable(obtained_via)
    if not isinstance(value, str):
        raise ValueError("context value must be string or null")
    return OptionalField.observed(value, obtained_via)


class SyntheticSource(ObservationSource):
    name = SOURCE_SYNTHETIC

    def __init__(
        self,
        script: Sequence[Mapping[str, Any]],
        ids: Optional[IdentityFactory] = None,
        clock: Optional[Clock] = None,
        default_application: Optional[str] = None,
        default_window: Optional[str] = None,
        interrupt_after: Optional[int] = None,
    ) -> None:
        super().__init__(ids=ids, clock=clock or SyntheticClock())
        self._script = list(script)
        self._default_application = default_application
        self._default_window = default_window
        self._interrupt_after = interrupt_after

    def events(self) -> Iterator[Result]:
        if self._session is None:
            yield Result.invalid("source not started")
            return
        if not self._script:
            return
        modifiers = 0
        app = self._default_application
        window = self._default_window
        seq = 0
        emitted = 0
        for step_index, step in enumerate(self._script):
            if self._stopped:
                yield Result.failure(Status.INTERRUPTED, "observation stopped")
                return
            if not isinstance(step, Mapping):
                yield Result.invalid(
                    "script step {0} is not an object".format(step_index)
                )
                continue
            action = str(step.get("action") or "key")
            if action == "delay":
                ns = int(step.get("ns") or 0)
                if ns < 0:
                    yield Result.invalid("delay ns must be >= 0")
                    continue
                if hasattr(self.clock, "advance"):
                    self.clock.advance(ns)  # type: ignore[attr-defined]
                continue
            if action == "context":
                if "application" in step:
                    app = step.get("application")
                if "window_title" in step:
                    window = step.get("window_title")
                continue
            if action != "key":
                yield Result.invalid("unknown action: {0}".format(action))
                continue
            if self._interrupt_after is not None and emitted >= self._interrupt_after:
                yield Result.failure(Status.INTERRUPTED, "interrupt_after reached")
                return
            try:
                raw = self._key_step(step, seq, modifiers, app, window)
            except (ValueError, TypeError) as exc:
                yield Result.invalid(str(exc), details={"step": step_index})
                continue
            event, modifiers = raw
            seq += 1
            emitted += 1
            if self._session is not None:
                self._session.event_count = emitted
            if hasattr(self.clock, "advance"):
                self.clock.advance()  # type: ignore[attr-defined]
            yield Result.success(event)

    def _key_step(
        self,
        step: Mapping[str, Any],
        seq: int,
        modifiers: int,
        app: Optional[str],
        window: Optional[str],
    ) -> tuple:
        key_code = step.get("key_code")
        if isinstance(key_code, bool) or not isinstance(key_code, int):
            raise ValueError("key_code must be int")
        event_type = str(step.get("event_type") or "")
        if event_type not in (EVENT_KEY_DOWN, EVENT_KEY_UP):
            raise ValueError("event_type must be KEY_DOWN or KEY_UP")
        is_up = event_type == EVENT_KEY_UP
        bit = modifier_bit_for_vk(key_code)
        if bit:
            if is_up:
                modifiers &= ~bit
            else:
                modifiers |= bit
        origin = "observed_snapshot"
        if "modifier_encoding" in step:
            modifiers = int(step["modifier_encoding"]) & 0xF
            origin = "observed_snapshot"
        modifier_state = ModifierState.from_encoding(modifiers, origin)
        label = label_for_vk(key_code)
        if label is None:
            key_label = OptionalField.unavailable("vk_table")
        else:
            # Label is a deterministic interpretation, but the synthetic
            # source may include it as observed-from-script. Keep it derived
            # so it is not confused with a layout-aware character.
            key_label = OptionalField.derived(label, "vk_table")
        if "application" in step:
            application = _field_from_script(step.get("application"), "synthetic_script")
        elif app is None:
            application = OptionalField.unavailable("synthetic_script")
        else:
            application = OptionalField.observed(app, "synthetic_script")
        if "window_title" in step:
            window_title = _field_from_script(step.get("window_title"), "synthetic_script")
        elif window is None:
            window_title = OptionalField.unavailable("synthetic_script")
        else:
            window_title = OptionalField.observed(window, "synthetic_script")
        flags = int(step["flags"]) if "flags" in step else (0x80 if is_up else 0)
        event = RawObservation(
            event_id=self.ids.new_id(),
            timestamp=self.clock.utc_iso(),
            event_type=event_type,
            key_code=key_code,
            key_label=key_label,
            modifier_state=modifier_state,
            application=application,
            window_title=window_title,
            session_id=self._session.session_id if self._session else "missing",
            source=SOURCE_SYNTHETIC,
            monotonic_ns=self.clock.monotonic_ns(),
            clock_source=self.clock.source_name(),
            event_type_raw=event_type,
            scan_code=step.get("scan_code") if isinstance(step.get("scan_code"), int) else None,
            flags=flags,
            extra_info=0,
            tick_ms=int(self.clock.monotonic_ns() // 1_000_000),
            sequence=seq,
            provenance=Provenance(KIND_RAW, "synthetic_observe"),
        )
        return event, modifiers


def script_from_keys(
    keys: Sequence[int],
    hold: bool = True,
    application: Optional[str] = None,
    window_title: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Expand a list of VK codes into down/up pairs."""
    script: List[Dict[str, Any]] = []
    if application is not None or window_title is not None:
        ctx: Dict[str, Any] = {"action": "context"}
        if application is not None:
            ctx["application"] = application
        if window_title is not None:
            ctx["window_title"] = window_title
        script.append(ctx)
    for vk in keys:
        script.append({"action": "key", "key_code": vk, "event_type": EVENT_KEY_DOWN})
        if hold:
            script.append({"action": "key", "key_code": vk, "event_type": EVENT_KEY_UP})
    return script
