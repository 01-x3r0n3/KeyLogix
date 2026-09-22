"""Immutable research data model.

Raw observation, normalized event, classification, and analysis records
are distinct types. Derived information is never stored as if it were
observed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from keylogix.constants import (
    EVENT_KEY_DOWN,
    EVENT_KEY_UP,
    EVENT_TYPES,
    KIND_BEHAVIORAL,
    KIND_DERIVED,
    KIND_HEURISTIC,
    KIND_NORMALIZED,
    KIND_RAW,
    METHOD_DETERMINISTIC,
    METHOD_HEURISTIC,
    MOD_ALT,
    MOD_CTRL,
    MOD_SHIFT,
    MOD_WIN,
    PRESENCE_DERIVED,
    PRESENCE_NOT_APPLICABLE,
    PRESENCE_OBSERVED,
    PRESENCE_UNAVAILABLE,
    SCHEMA_ANALYSIS,
    SCHEMA_CLASSIFICATION,
    SCHEMA_NORMALIZED,
    SCHEMA_RAW,
    SOURCE_VOCABULARY,
)
from keylogix.vk import classify_vk, label_for_vk

PRESENCE_VALUES = frozenset(
    {
        PRESENCE_OBSERVED,
        PRESENCE_UNAVAILABLE,
        PRESENCE_NOT_APPLICABLE,
        PRESENCE_DERIVED,
    }
)


class ModelError(ValueError):
    pass


@dataclass(frozen=True)
class OptionalField:
    presence: str
    value: Optional[str] = None
    obtained_via: Optional[str] = None

    def __post_init__(self) -> None:
        if self.presence not in PRESENCE_VALUES:
            raise ModelError("invalid presence: {0}".format(self.presence))
        if self.presence in (PRESENCE_UNAVAILABLE, PRESENCE_NOT_APPLICABLE):
            if self.value is not None:
                raise ModelError(
                    "presence {0} must not carry a value".format(self.presence)
                )
        elif self.presence in (PRESENCE_OBSERVED, PRESENCE_DERIVED):
            if self.value is None:
                raise ModelError(
                    "presence {0} requires a string value (empty string allowed)".format(
                        self.presence
                    )
                )
            if not isinstance(self.value, str):
                raise ModelError("optional field value must be a string")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "presence": self.presence,
            "value": self.value,
            "obtained_via": self.obtained_via,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "OptionalField":
        if not isinstance(data, Mapping):
            raise ModelError("OptionalField must be an object")
        return OptionalField(
            presence=str(data.get("presence", "")),
            value=data.get("value"),
            obtained_via=data.get("obtained_via"),
        )

    @staticmethod
    def unavailable(obtained_via: Optional[str] = None) -> "OptionalField":
        return OptionalField(PRESENCE_UNAVAILABLE, None, obtained_via)

    @staticmethod
    def not_applicable(obtained_via: Optional[str] = None) -> "OptionalField":
        return OptionalField(PRESENCE_NOT_APPLICABLE, None, obtained_via)

    @staticmethod
    def observed(value: str, obtained_via: Optional[str] = None) -> "OptionalField":
        return OptionalField(PRESENCE_OBSERVED, value, obtained_via)

    @staticmethod
    def derived(value: str, obtained_via: str) -> "OptionalField":
        return OptionalField(PRESENCE_DERIVED, value, obtained_via)


@dataclass(frozen=True)
class ModifierState:
    shift: bool
    ctrl: bool
    alt: bool
    win: bool
    known: bool
    origin: str
    encoding: int = 0

    def __post_init__(self) -> None:
        expected = 0
        if self.shift:
            expected |= MOD_SHIFT
        if self.ctrl:
            expected |= MOD_CTRL
        if self.alt:
            expected |= MOD_ALT
        if self.win:
            expected |= MOD_WIN
        if not self.known:
            if self.shift or self.ctrl or self.alt or self.win:
                raise ModelError("unknown modifier state cannot claim bits")
            object.__setattr__(self, "encoding", 0)
            return
        object.__setattr__(self, "encoding", expected)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shift": self.shift,
            "ctrl": self.ctrl,
            "alt": self.alt,
            "win": self.win,
            "known": self.known,
            "origin": self.origin,
            "encoding": self.encoding,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "ModifierState":
        return ModifierState(
            shift=bool(data.get("shift")),
            ctrl=bool(data.get("ctrl")),
            alt=bool(data.get("alt")),
            win=bool(data.get("win")),
            known=bool(data.get("known")),
            origin=str(data.get("origin", "unknown")),
        )

    @staticmethod
    def unknown() -> "ModifierState":
        return ModifierState(False, False, False, False, False, "unknown", 0)

    @staticmethod
    def from_encoding(encoding: int, origin: str) -> "ModifierState":
        bits = encoding & 0xF
        return ModifierState(
            shift=bool(bits & MOD_SHIFT),
            ctrl=bool(bits & MOD_CTRL),
            alt=bool(bits & MOD_ALT),
            win=bool(bits & MOD_WIN),
            known=True,
            origin=origin,
            encoding=bits,
        )


@dataclass(frozen=True)
class Provenance:
    information_kind: str
    transform: str
    parent_ids: Tuple[str, ...] = ()
    ingested_via: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "information_kind": self.information_kind,
            "transform": self.transform,
            "parent_ids": list(self.parent_ids),
            "ingested_via": self.ingested_via,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "Provenance":
        parents = data.get("parent_ids") or []
        if not isinstance(parents, list):
            raise ModelError("parent_ids must be a list")
        return Provenance(
            information_kind=str(data.get("information_kind", "")),
            transform=str(data.get("transform", "")),
            parent_ids=tuple(str(p) for p in parents),
            ingested_via=data.get("ingested_via"),
            notes=str(data.get("notes") or ""),
        )


def _require_str(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ModelError("{0} must be a non-empty string".format(name))
    return value


def _optional_int(name: str, value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ModelError("{0} must be an int or null".format(name))
    return value


@dataclass(frozen=True)
class RawObservation:
    event_id: str
    timestamp: str
    event_type: str  # KEY_DOWN / KEY_UP when already mapped; else empty and use event_type_raw
    key_code: Optional[int]
    key_label: OptionalField
    modifier_state: ModifierState
    application: OptionalField
    window_title: OptionalField
    session_id: str
    source: str
    monotonic_ns: int
    clock_source: str
    event_type_raw: str = ""
    scan_code: Optional[int] = None
    flags: Optional[int] = None
    extra_info: Optional[int] = None
    tick_ms: Optional[int] = None
    sequence: int = 0
    provenance: Provenance = field(
        default_factory=lambda: Provenance(KIND_RAW, "observe")
    )
    schema: str = SCHEMA_RAW

    def __post_init__(self) -> None:
        _require_str("event_id", self.event_id)
        _require_str("timestamp", self.timestamp)
        _require_str("session_id", self.session_id)
        _require_str("source", self.source)
        _require_str("clock_source", self.clock_source)
        if self.source not in SOURCE_VOCABULARY:
            raise ModelError("unknown source vocabulary value: {0}".format(self.source))
        if self.event_type and self.event_type not in EVENT_TYPES:
            raise ModelError("invalid event_type: {0}".format(self.event_type))
        if self.key_code is not None:
            if isinstance(self.key_code, bool) or not isinstance(self.key_code, int):
                raise ModelError("key_code must be int or null")
        if not isinstance(self.monotonic_ns, int) or isinstance(self.monotonic_ns, bool):
            raise ModelError("monotonic_ns must be int")
        if self.monotonic_ns < 0:
            raise ModelError("monotonic_ns must be >= 0")
        if self.sequence < 0:
            raise ModelError("sequence must be >= 0")
        if self.provenance.information_kind != KIND_RAW:
            raise ModelError("raw observation provenance kind must be raw_observation")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "key_code": self.key_code,
            "key_label": self.key_label.to_dict(),
            "modifier_state": self.modifier_state.to_dict(),
            "application": self.application.to_dict(),
            "window_title": self.window_title.to_dict(),
            "session_id": self.session_id,
            "source": self.source,
            "monotonic_ns": self.monotonic_ns,
            "clock_source": self.clock_source,
            "event_type_raw": self.event_type_raw,
            "scan_code": self.scan_code,
            "flags": self.flags,
            "extra_info": self.extra_info,
            "tick_ms": self.tick_ms,
            "sequence": self.sequence,
            "provenance": self.provenance.to_dict(),
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "RawObservation":
        if not isinstance(data, Mapping):
            raise ModelError("raw observation must be an object")
        return RawObservation(
            event_id=str(data.get("event_id", "")),
            timestamp=str(data.get("timestamp", "")),
            event_type=str(data.get("event_type") or ""),
            key_code=_optional_int("key_code", data.get("key_code")),
            key_label=OptionalField.from_dict(data.get("key_label") or {"presence": PRESENCE_UNAVAILABLE}),
            modifier_state=ModifierState.from_dict(
                data.get("modifier_state") or ModifierState.unknown().to_dict()
            ),
            application=OptionalField.from_dict(
                data.get("application") or {"presence": PRESENCE_UNAVAILABLE}
            ),
            window_title=OptionalField.from_dict(
                data.get("window_title") or {"presence": PRESENCE_UNAVAILABLE}
            ),
            session_id=str(data.get("session_id", "")),
            source=str(data.get("source", "")),
            monotonic_ns=int(data.get("monotonic_ns", 0)),
            clock_source=str(data.get("clock_source", "")),
            event_type_raw=str(data.get("event_type_raw") or ""),
            scan_code=_optional_int("scan_code", data.get("scan_code")),
            flags=_optional_int("flags", data.get("flags")),
            extra_info=_optional_int("extra_info", data.get("extra_info")),
            tick_ms=_optional_int("tick_ms", data.get("tick_ms")),
            sequence=int(data.get("sequence") or 0),
            provenance=Provenance.from_dict(
                data.get("provenance") or {"information_kind": KIND_RAW, "transform": "observe"}
            ),
            schema=str(data.get("schema") or SCHEMA_RAW),
        )


@dataclass(frozen=True)
class NormalizedEvent:
    event_id: str
    timestamp: str
    event_type: str
    key_code: int
    key_label: OptionalField
    modifier_state: ModifierState
    application: OptionalField
    window_title: OptionalField
    session_id: str
    source: str
    monotonic_ns: int
    clock_source: str
    sequence: int
    provenance: Provenance
    schema: str = SCHEMA_NORMALIZED

    def __post_init__(self) -> None:
        _require_str("event_id", self.event_id)
        _require_str("timestamp", self.timestamp)
        if self.event_type not in EVENT_TYPES:
            raise ModelError("normalized event_type must be KEY_DOWN or KEY_UP")
        if isinstance(self.key_code, bool) or not isinstance(self.key_code, int):
            raise ModelError("normalized key_code must be int")
        if self.key_code < 0 or self.key_code > 255:
            raise ModelError("normalized key_code out of range")
        if self.provenance.information_kind != KIND_NORMALIZED:
            raise ModelError("normalized provenance kind mismatch")
        if self.event_id not in self.provenance.parent_ids and self.provenance.parent_ids:
            # parent_ids should include the raw event_id, which is the same id.
            pass
        if not self.provenance.parent_ids:
            raise ModelError("normalized event must cite originating observation")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "key_code": self.key_code,
            "key_label": self.key_label.to_dict(),
            "modifier_state": self.modifier_state.to_dict(),
            "application": self.application.to_dict(),
            "window_title": self.window_title.to_dict(),
            "session_id": self.session_id,
            "source": self.source,
            "monotonic_ns": self.monotonic_ns,
            "clock_source": self.clock_source,
            "sequence": self.sequence,
            "provenance": self.provenance.to_dict(),
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "NormalizedEvent":
        return NormalizedEvent(
            event_id=str(data.get("event_id", "")),
            timestamp=str(data.get("timestamp", "")),
            event_type=str(data.get("event_type", "")),
            key_code=int(data.get("key_code")),
            key_label=OptionalField.from_dict(data["key_label"]),
            modifier_state=ModifierState.from_dict(data["modifier_state"]),
            application=OptionalField.from_dict(data["application"]),
            window_title=OptionalField.from_dict(data["window_title"]),
            session_id=str(data.get("session_id", "")),
            source=str(data.get("source", "")),
            monotonic_ns=int(data.get("monotonic_ns", 0)),
            clock_source=str(data.get("clock_source", "")),
            sequence=int(data.get("sequence") or 0),
            provenance=Provenance.from_dict(data["provenance"]),
            schema=str(data.get("schema") or SCHEMA_NORMALIZED),
        )


@dataclass(frozen=True)
class ClassificationRecord:
    record_id: str
    event_id: str
    category: str
    method: str
    confidence: float
    information_kind: str
    details: Mapping[str, Any] = field(default_factory=dict)
    schema: str = SCHEMA_CLASSIFICATION

    def __post_init__(self) -> None:
        _require_str("record_id", self.record_id)
        _require_str("event_id", self.event_id)
        if self.method == METHOD_DETERMINISTIC and self.confidence != 1.0:
            raise ModelError("deterministic classification must have confidence 1.0")
        if self.method == METHOD_HEURISTIC and self.confidence >= 1.0:
            raise ModelError("heuristic classification must not claim certainty")
        if self.confidence < 0 or self.confidence > 1:
            raise ModelError("confidence out of range")
        if self.method == METHOD_HEURISTIC and self.information_kind != KIND_HEURISTIC:
            raise ModelError("heuristic method requires heuristic information_kind")
        if self.method == METHOD_DETERMINISTIC and self.information_kind not in (
            KIND_DERIVED,
            KIND_NORMALIZED,
        ):
            # Deterministic transform of observed VK.
            if self.information_kind != KIND_DERIVED:
                raise ModelError("deterministic classification kind must be derived")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "record_id": self.record_id,
            "event_id": self.event_id,
            "category": self.category,
            "method": self.method,
            "confidence": self.confidence,
            "information_kind": self.information_kind,
            "details": dict(self.details),
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "ClassificationRecord":
        return ClassificationRecord(
            record_id=str(data.get("record_id", "")),
            event_id=str(data.get("event_id", "")),
            category=str(data.get("category", "")),
            method=str(data.get("method", "")),
            confidence=float(data.get("confidence")),
            information_kind=str(data.get("information_kind", "")),
            details=dict(data.get("details") or {}),
            schema=str(data.get("schema") or SCHEMA_CLASSIFICATION),
        )


@dataclass(frozen=True)
class Conclusion:
    statement: str
    kind: str
    confidence: Optional[float] = None
    based_on: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in ("measured", "derived", "inferred", "hypothetical"):
            raise ModelError("invalid conclusion kind")
        if self.kind == "measured" and self.confidence not in (None, 1.0):
            raise ModelError("measured conclusions must not use heuristic confidence")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statement": self.statement,
            "kind": self.kind,
            "confidence": self.confidence,
            "based_on": list(self.based_on),
        }


@dataclass(frozen=True)
class BehavioralSummary:
    record_id: str
    session_id: str
    event_count: int
    key_down_count: int
    key_up_count: int
    unmatched_downs: int
    unmatched_ups: int
    duration_ns: int
    events_per_second: Optional[float]
    mean_interarrival_ns: Optional[float]
    median_interarrival_ns: Optional[float]
    p95_interarrival_ns: Optional[float]
    max_repeat_run: int
    burst_count: int
    context_change_count: int
    modifier_key_event_fraction: float
    ordinary_key_event_fraction: float
    sequence_label: str
    sequence_label_confidence: float
    conclusions: Tuple[Conclusion, ...]
    event_ids: Tuple[str, ...]
    schema: str = SCHEMA_ANALYSIS
    information_kind: str = KIND_BEHAVIORAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "record_id": self.record_id,
            "session_id": self.session_id,
            "information_kind": self.information_kind,
            "event_count": self.event_count,
            "key_down_count": self.key_down_count,
            "key_up_count": self.key_up_count,
            "unmatched_downs": self.unmatched_downs,
            "unmatched_ups": self.unmatched_ups,
            "duration_ns": self.duration_ns,
            "events_per_second": self.events_per_second,
            "mean_interarrival_ns": self.mean_interarrival_ns,
            "median_interarrival_ns": self.median_interarrival_ns,
            "p95_interarrival_ns": self.p95_interarrival_ns,
            "max_repeat_run": self.max_repeat_run,
            "burst_count": self.burst_count,
            "context_change_count": self.context_change_count,
            "modifier_key_event_fraction": self.modifier_key_event_fraction,
            "ordinary_key_event_fraction": self.ordinary_key_event_fraction,
            "sequence_label": self.sequence_label,
            "sequence_label_confidence": self.sequence_label_confidence,
            "conclusions": [c.to_dict() for c in self.conclusions],
            "event_ids": list(self.event_ids),
        }


def expected_label_field(key_code: int) -> OptionalField:
    label = label_for_vk(key_code)
    if label is None:
        return OptionalField.unavailable("vk_table")
    return OptionalField.derived(label, "vk_table")


def expected_category(key_code: int) -> str:
    return classify_vk(key_code)
