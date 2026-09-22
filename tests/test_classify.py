from __future__ import annotations

from keylogix.classify import Classifier
from keylogix.constants import (
    CAT_ORDINARY,
    EVENT_KEY_DOWN,
    EVENT_KEY_UP,
    KIND_NORMALIZED,
    SEQ_CHORD,
    SEQ_EMPTY,
    SEQ_SPECIAL,
    SEQ_TEXT_ORIENTED,
    SOURCE_SYNTHETIC,
)
from keylogix.model import (
    ModifierState,
    NormalizedEvent,
    OptionalField,
    Provenance,
)


def make_norm(event_id: str, vk_code: int, event_type: str = EVENT_KEY_DOWN) -> NormalizedEvent:
    return NormalizedEvent(
        event_id=event_id,
        timestamp="2026-09-18T12:00:00.000000Z",
        event_type=event_type,
        key_code=vk_code,
        key_label=OptionalField.derived("X", "vk_table"),
        modifier_state=ModifierState.unknown(),
        application=OptionalField.unavailable(),
        window_title=OptionalField.unavailable(),
        session_id="s1",
        source=SOURCE_SYNTHETIC,
        monotonic_ns=1000,
        clock_source="synthetic",
        sequence=0,
        provenance=Provenance(KIND_NORMALIZED, "normalize", parent_ids=(event_id,)),
    )


def test_classifier_single_event():
    clf = Classifier()
    ev = make_norm("e1", 0x41)
    res = clf.classify_event(ev)
    assert res.ok is True
    assert res.value.category == CAT_ORDINARY
    assert res.value.confidence == 1.0


def test_classifier_sequence_text_oriented():
    clf = Classifier()
    events = [make_norm(f"e{i}", 65 + i) for i in range(10)]
    res = clf.classify_sequence(events)
    assert res.ok is True
    assert res.value.category == SEQ_TEXT_ORIENTED
    assert res.value.confidence == 0.7


def test_classifier_sequence_special():
    clf = Classifier()
    # F1..F10 keys
    events = [make_norm(f"e{i}", 0x70 + i) for i in range(10)]
    res = clf.classify_sequence(events)
    assert res.ok is True
    assert res.value.category == SEQ_SPECIAL


def test_classifier_sequence_chord():
    clf = Classifier()
    # Shift down (0x10) + 'A' down (0x41)
    events = [make_norm("e1", 0x10), make_norm("e2", 0x41)]
    res = clf.classify_sequence(events)
    assert res.ok is True
    assert res.value.category == SEQ_CHORD


def test_classifier_sequence_empty():
    clf = Classifier()
    res = clf.classify_sequence([])
    assert res.status.value == "SUCCESS_NO_DATA"
