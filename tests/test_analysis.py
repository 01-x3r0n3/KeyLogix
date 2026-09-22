from __future__ import annotations

from keylogix.analysis import Analyzer
from keylogix.constants import (
    EVENT_KEY_DOWN,
    EVENT_KEY_UP,
    KIND_NORMALIZED,
    SOURCE_SYNTHETIC,
)
from keylogix.model import (
    ModifierState,
    NormalizedEvent,
    OptionalField,
    Provenance,
)
from keylogix.status import Status


def make_norm_with_time(
    event_id: str,
    vk_code: int,
    event_type: str,
    monotonic_ns: int,
    app: str = "app.exe",
) -> NormalizedEvent:
    return NormalizedEvent(
        event_id=event_id,
        timestamp="2026-09-18T12:00:00.000000Z",
        event_type=event_type,
        key_code=vk_code,
        key_label=OptionalField.derived("A", "vk_table"),
        modifier_state=ModifierState.unknown(),
        application=OptionalField.observed(app, "test"),
        window_title=OptionalField.observed("win", "test"),
        session_id="s1",
        source=SOURCE_SYNTHETIC,
        monotonic_ns=monotonic_ns,
        clock_source="synthetic",
        sequence=0,
        provenance=Provenance(KIND_NORMALIZED, "normalize", parent_ids=(event_id,)),
    )


def test_analyzer_basic_metrics():
    analyzer = Analyzer()
    events = [
        make_norm_with_time("e1", 65, EVENT_KEY_DOWN, 100000000),
        make_norm_with_time("e2", 65, EVENT_KEY_UP, 150000000),
        make_norm_with_time("e3", 66, EVENT_KEY_DOWN, 200000000),
        make_norm_with_time("e4", 66, EVENT_KEY_UP, 250000000),
    ]
    res = analyzer.analyze(events)
    assert res.ok is True
    summary = res.value
    assert summary.event_count == 4
    assert summary.key_down_count == 2
    assert summary.key_up_count == 2
    assert summary.unmatched_downs == 0
    assert summary.unmatched_ups == 0
    assert summary.duration_ns == 150000000
    assert summary.events_per_second is not None
    assert summary.events_per_second > 0


def test_analyzer_burst_and_repeat():
    analyzer = Analyzer()
    # 6 rapid key downs with interval 10ms (< 50ms)
    events = []
    t = 100000000
    for i in range(6):
        events.append(make_norm_with_time(f"e{i}", 65, EVENT_KEY_DOWN, t))
        t += 10000000  # 10ms
    res = analyzer.analyze(events)
    assert res.ok is True
    summary = res.value
    assert summary.burst_count >= 1
    assert summary.max_repeat_run == 6


def test_analyzer_context_transitions():
    analyzer = Analyzer()
    events = [
        make_norm_with_time("e1", 65, EVENT_KEY_DOWN, 1000, app="app1.exe"),
        make_norm_with_time("e2", 65, EVENT_KEY_UP, 2000, app="app1.exe"),
        make_norm_with_time("e3", 66, EVENT_KEY_DOWN, 3000, app="app2.exe"),
        make_norm_with_time("e4", 66, EVENT_KEY_UP, 4000, app="app2.exe"),
    ]
    res = analyzer.analyze(events)
    assert res.ok is True
    summary = res.value
    assert summary.context_change_count == 1


def test_analyzer_empty():
    analyzer = Analyzer()
    res = analyzer.analyze([])
    assert res.status == Status.SUCCESS_NO_DATA
