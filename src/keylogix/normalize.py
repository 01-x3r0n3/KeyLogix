"""Raw observation → normalized event.

Does not query the OS. Does not invent context, timestamps, or key codes.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from keylogix.constants import (
    EVENT_KEY_DOWN,
    EVENT_KEY_UP,
    KIND_NORMALIZED,
    LLKHF_UP,
    RAW_WM_KEYDOWN,
    RAW_WM_KEYUP,
    RAW_WM_SYSKEYDOWN,
    RAW_WM_SYSKEYUP,
)
from keylogix.model import (
    ModelError,
    ModifierState,
    NormalizedEvent,
    OptionalField,
    Provenance,
    RawObservation,
)
from keylogix.status import Result, Status
from keylogix.timeutil import parse_utc
from keylogix.vk import label_for_vk, modifier_bit_for_vk


_DOWN_RAW = {EVENT_KEY_DOWN, RAW_WM_KEYDOWN, RAW_WM_SYSKEYDOWN, "keydown", "down"}
_UP_RAW = {EVENT_KEY_UP, RAW_WM_KEYUP, RAW_WM_SYSKEYUP, "keyup", "up"}


def _map_event_type(raw: RawObservation) -> Optional[str]:
    if raw.event_type in (EVENT_KEY_DOWN, EVENT_KEY_UP):
        return raw.event_type
    token = (raw.event_type_raw or "").strip()
    if token in _DOWN_RAW:
        return EVENT_KEY_DOWN
    if token in _UP_RAW:
        return EVENT_KEY_UP
    if raw.flags is not None:
        return EVENT_KEY_UP if (raw.flags & LLKHF_UP) else EVENT_KEY_DOWN
    return None


class Normalizer:
    def __init__(self) -> None:
        self._modifiers = 0
        self._tracking = False

    def reset(self) -> None:
        self._modifiers = 0
        self._tracking = False

    def normalize_one(self, raw: RawObservation) -> Result:
        if not isinstance(raw, RawObservation):
            return Result.invalid("expected RawObservation")
        if parse_utc(raw.timestamp) is None:
            return Result.invalid(
                "invalid timestamp", details={"event_id": raw.event_id}
            )
        event_type = _map_event_type(raw)
        if event_type is None:
            return Result.invalid(
                "cannot determine event_type", details={"event_id": raw.event_id}
            )
        if raw.key_code is None:
            return Result.invalid(
                "missing key_code", details={"event_id": raw.event_id}
            )
        if raw.key_code < 0 or raw.key_code > 255:
            return Result.invalid(
                "key_code out of range", details={"event_id": raw.event_id, "key_code": raw.key_code}
            )
        if raw.monotonic_ns < 0:
            return Result.invalid("negative monotonic_ns")

        if raw.modifier_state.known:
            modifier_state = raw.modifier_state
            self._modifiers = modifier_state.encoding
            self._tracking = True
        else:
            bit = modifier_bit_for_vk(raw.key_code)
            if bit:
                if event_type == EVENT_KEY_DOWN:
                    self._modifiers |= bit
                else:
                    self._modifiers &= ~bit
                self._tracking = True
            if self._tracking:
                modifier_state = ModifierState.from_encoding(
                    self._modifiers, "derived_tracking"
                )
            else:
                modifier_state = ModifierState.unknown()

        label = label_for_vk(raw.key_code)
        if raw.key_label.presence in ("observed", "derived") and raw.key_label.value:
            # Preserve provided label only if it matches the table; otherwise
            # keep the provided derived/observed label as-is but do not invent.
            key_label = raw.key_label
            if label is not None and raw.key_label.value != label:
                # Conflict: keep observed/derived original, note in provenance.
                key_label = raw.key_label
        elif label is not None:
            key_label = OptionalField.derived(label, "vk_table")
        else:
            key_label = OptionalField.unavailable("vk_table")

        try:
            event = NormalizedEvent(
                event_id=raw.event_id,
                timestamp=raw.timestamp,
                event_type=event_type,
                key_code=raw.key_code,
                key_label=key_label,
                modifier_state=modifier_state,
                application=raw.application,
                window_title=raw.window_title,
                session_id=raw.session_id,
                source=raw.source,
                monotonic_ns=raw.monotonic_ns,
                clock_source=raw.clock_source,
                sequence=raw.sequence,
                provenance=Provenance(
                    information_kind=KIND_NORMALIZED,
                    transform="normalize",
                    parent_ids=(raw.event_id,),
                ),
            )
        except ModelError as exc:
            return Result.invalid(str(exc), details={"event_id": raw.event_id})
        return Result.success(event)

    def normalize_many(self, raws: Sequence[RawObservation]) -> Result:
        if raws is None:
            return Result.invalid("raw event sequence is null")
        if not isinstance(raws, (list, tuple)):
            return Result.invalid("raw event sequence must be a list")
        if len(raws) == 0:
            return Result.no_data("no raw observations")
        ok: List[NormalizedEvent] = []
        errors: List[dict] = []
        for raw in raws:
            item = self.normalize_one(raw)
            if item.ok and item.has_data:
                ok.append(item.value)
            else:
                errors.append(item.to_dict())
        if ok and not errors:
            return Result.success(ok)
        if ok and errors:
            return Result(
                Status.PARTIAL,
                ok,
                "normalized {0} of {1}".format(len(ok), len(raws)),
                {"errors": errors},
            )
        return Result.failure(
            Status.INVALID_INPUT,
            "no observations could be normalized",
            details={"errors": errors},
        )
