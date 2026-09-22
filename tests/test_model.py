from __future__ import annotations

import pytest
from keylogix.constants import (
    EVENT_KEY_DOWN,
    EVENT_KEY_UP,
    KIND_DERIVED,
    KIND_HEURISTIC,
    KIND_NORMALIZED,
    KIND_RAW,
    METHOD_DETERMINISTIC,
    METHOD_HEURISTIC,
    PRESENCE_DERIVED,
    PRESENCE_NOT_APPLICABLE,
    PRESENCE_OBSERVED,
    PRESENCE_UNAVAILABLE,
    SCHEMA_RAW,
    SOURCE_SYNTHETIC,
)
from keylogix.model import (
    BehavioralSummary,
    ClassificationRecord,
    Conclusion,
    ModelError,
    ModifierState,
    NormalizedEvent,
    OptionalField,
    Provenance,
    RawObservation,
)


def test_optional_field():
    f_obs = OptionalField.observed("notepad.exe", "test")
    assert f_obs.presence == PRESENCE_OBSERVED
    assert f_obs.value == "notepad.exe"
    assert f_obs.obtained_via == "test"

    f_unavail = OptionalField.unavailable("test")
    assert f_unavail.presence == PRESENCE_UNAVAILABLE
    assert f_unavail.value is None

    f_not_app = OptionalField.not_applicable("test")
    assert f_not_app.presence == PRESENCE_NOT_APPLICABLE
    assert f_not_app.value is None

    f_derived = OptionalField.derived("calc.exe", "test")
    assert f_derived.presence == PRESENCE_DERIVED
    assert f_derived.value == "calc.exe"

    with pytest.raises(ModelError, match="invalid presence"):
        OptionalField("invalid_presence")

    with pytest.raises(ModelError, match="must not carry a value"):
        OptionalField(PRESENCE_UNAVAILABLE, value="cannot_have_val")

    with pytest.raises(ModelError, match="requires a string value"):
        OptionalField(PRESENCE_OBSERVED, value=None)

    # Round trip dict
    d = f_obs.to_dict()
    restored = OptionalField.from_dict(d)
    assert restored == f_obs


def test_modifier_state():
    mod_none = ModifierState.unknown()
    assert mod_none.known is False
    assert mod_none.encoding == 0

    mod_shift = ModifierState.from_encoding(1, "observed_snapshot")
    assert mod_shift.shift is True
    assert mod_shift.ctrl is False
    assert mod_shift.encoding == 1
    assert mod_shift.known is True

    mod_all = ModifierState.from_encoding(15, "test")
    assert mod_all.shift and mod_all.ctrl and mod_all.alt and mod_all.win
    assert mod_all.encoding == 15

    with pytest.raises(ModelError, match="unknown modifier state cannot claim bits"):
        ModifierState(shift=True, ctrl=False, alt=False, win=False, known=False, origin="test")

    # Round trip dict
    d = mod_all.to_dict()
    assert ModifierState.from_dict(d) == mod_all


def test_provenance():
    prov = Provenance(
        information_kind=KIND_RAW,
        transform="observe",
        parent_ids=("p1", "p2"),
        ingested_via="test",
        notes="note",
    )
    d = prov.to_dict()
    assert d["information_kind"] == KIND_RAW
    assert d["parent_ids"] == ["p1", "p2"]

    restored = Provenance.from_dict(d)
    assert restored.parent_ids == ("p1", "p2")
    assert restored.transform == "observe"


def test_raw_observation_validation():
    raw = RawObservation(
        event_id="e1",
        timestamp="2026-09-18T12:00:00.000000Z",
        event_type=EVENT_KEY_DOWN,
        key_code=0x41,
        key_label=OptionalField.derived("A", "vk_table"),
        modifier_state=ModifierState.unknown(),
        application=OptionalField.unavailable(),
        window_title=OptionalField.unavailable(),
        session_id="s1",
        source=SOURCE_SYNTHETIC,
        monotonic_ns=1000,
        clock_source="synthetic",
    )
    assert raw.event_id == "e1"
    assert raw.key_code == 0x41

    d = raw.to_dict()
    restored = RawObservation.from_dict(d)
    assert restored.event_id == raw.event_id
    assert restored.key_code == 0x41

    with pytest.raises(ModelError, match="event_id must be a non-empty string"):
        RawObservation(
            event_id="",
            timestamp="2026-09-18T12:00:00.000000Z",
            event_type=EVENT_KEY_DOWN,
            key_code=0x41,
            key_label=OptionalField.unavailable(),
            modifier_state=ModifierState.unknown(),
            application=OptionalField.unavailable(),
            window_title=OptionalField.unavailable(),
            session_id="s1",
            source=SOURCE_SYNTHETIC,
            monotonic_ns=1000,
            clock_source="synthetic",
        )

    with pytest.raises(ModelError, match="unknown source vocabulary value"):
        RawObservation(
            event_id="e1",
            timestamp="2026-09-18T12:00:00.000000Z",
            event_type=EVENT_KEY_DOWN,
            key_code=0x41,
            key_label=OptionalField.unavailable(),
            modifier_state=ModifierState.unknown(),
            application=OptionalField.unavailable(),
            window_title=OptionalField.unavailable(),
            session_id="s1",
            source="illegal_source_name",
            monotonic_ns=1000,
            clock_source="synthetic",
        )


def test_normalized_event_validation():
    norm = NormalizedEvent(
        event_id="e1",
        timestamp="2026-09-18T12:00:00.000000Z",
        event_type=EVENT_KEY_DOWN,
        key_code=65,
        key_label=OptionalField.derived("A", "vk_table"),
        modifier_state=ModifierState.unknown(),
        application=OptionalField.unavailable(),
        window_title=OptionalField.unavailable(),
        session_id="s1",
        source=SOURCE_SYNTHETIC,
        monotonic_ns=1000,
        clock_source="synthetic",
        sequence=0,
        provenance=Provenance(KIND_NORMALIZED, "normalize", parent_ids=("e1",)),
    )
    assert norm.key_code == 65
    d = norm.to_dict()
    assert NormalizedEvent.from_dict(d) == norm

    with pytest.raises(ModelError, match="out of range"):
        NormalizedEvent(
            event_id="e1",
            timestamp="2026-09-18T12:00:00.000000Z",
            event_type=EVENT_KEY_DOWN,
            key_code=300,
            key_label=OptionalField.unavailable(),
            modifier_state=ModifierState.unknown(),
            application=OptionalField.unavailable(),
            window_title=OptionalField.unavailable(),
            session_id="s1",
            source=SOURCE_SYNTHETIC,
            monotonic_ns=1000,
            clock_source="synthetic",
            sequence=0,
            provenance=Provenance(KIND_NORMALIZED, "normalize", parent_ids=("e1",)),
        )


def test_classification_record():
    det = ClassificationRecord(
        record_id="c1",
        event_id="e1",
        category="ordinary",
        method=METHOD_DETERMINISTIC,
        confidence=1.0,
        information_kind=KIND_DERIVED,
    )
    assert det.confidence == 1.0
    assert ClassificationRecord.from_dict(det.to_dict()) == det

    with pytest.raises(ModelError, match="deterministic classification must have confidence 1.0"):
        ClassificationRecord(
            record_id="c1",
            event_id="e1",
            category="ordinary",
            method=METHOD_DETERMINISTIC,
            confidence=0.8,
            information_kind=KIND_DERIVED,
        )

    heur = ClassificationRecord(
        record_id="c2",
        event_id="e1",
        category="text_oriented",
        method=METHOD_HEURISTIC,
        confidence=0.7,
        information_kind=KIND_HEURISTIC,
    )
    assert heur.confidence == 0.7

    with pytest.raises(ModelError, match="heuristic classification must not claim certainty"):
        ClassificationRecord(
            record_id="c2",
            event_id="e1",
            category="text_oriented",
            method=METHOD_HEURISTIC,
            confidence=1.0,
            information_kind=KIND_HEURISTIC,
        )
