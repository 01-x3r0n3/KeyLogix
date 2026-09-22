from __future__ import annotations

from keylogix.constants import (
    EVENT_KEY_DOWN,
    KIND_NORMALIZED,
    PRESENCE_DERIVED,
    PRESENCE_OBSERVED,
    PRESENCE_UNAVAILABLE,
    SOURCE_SYNTHETIC,
)
from keylogix.context import ContextAssociator, ContextTimelineEntry
from keylogix.model import (
    ModifierState,
    NormalizedEvent,
    OptionalField,
    Provenance,
)
from keylogix.status import Status


def make_event(
    event_id: str,
    monotonic_ns: int,
    app: OptionalField = OptionalField.unavailable(),
    win: OptionalField = OptionalField.unavailable(),
) -> NormalizedEvent:
    return NormalizedEvent(
        event_id=event_id,
        timestamp="2026-09-18T12:00:00.000000Z",
        event_type=EVENT_KEY_DOWN,
        key_code=65,
        key_label=OptionalField.derived("A", "vk_table"),
        modifier_state=ModifierState.unknown(),
        application=app,
        window_title=win,
        session_id="s1",
        source=SOURCE_SYNTHETIC,
        monotonic_ns=monotonic_ns,
        clock_source="synthetic",
        sequence=0,
        provenance=Provenance(KIND_NORMALIZED, "normalize", parent_ids=(event_id,)),
    )


def test_context_associator_timeline_fill():
    timeline = [
        ContextTimelineEntry(1000, "app1.exe", "Win 1"),
        ContextTimelineEntry(2000, "app2.exe", "Win 2"),
    ]
    associator = ContextAssociator(timeline)

    e1 = make_event("e1", 1500)
    res1 = associator.associate_one(e1)
    assert res1.ok is True
    assoc1 = res1.value
    assert assoc1.event.application.presence == PRESENCE_DERIVED
    assert assoc1.event.application.value == "app1.exe"
    assert assoc1.event.window_title.value == "Win 1"

    e2 = make_event("e2", 2500)
    res2 = associator.associate_one(e2)
    assert res2.ok is True
    assoc2 = res2.value
    assert assoc2.event.application.value == "app2.exe"
    assert assoc2.event.window_title.value == "Win 2"


def test_context_associator_conflict():
    timeline = [ContextTimelineEntry(1000, "app1.exe", "Win 1")]
    associator = ContextAssociator(timeline)

    # Observed application is different from timeline
    e = make_event("e1", 1500, app=OptionalField.observed("other.exe", "observed"))
    res = associator.associate_one(e)
    assert res.status == Status.PARTIAL
    assoc = res.value
    assert len(assoc.conflicts) == 1
    assert assoc.conflicts[0].observed == "other.exe"
    assert assoc.conflicts[0].derived == "app1.exe"
    # Preserves observed value!
    assert assoc.event.application.value == "other.exe"


def test_context_associator_unavailable():
    associator = ContextAssociator([])
    e = make_event("e1", 1000)
    res = associator.associate_one(e)
    assert res.status == Status.UNAVAILABLE_CONTEXT
