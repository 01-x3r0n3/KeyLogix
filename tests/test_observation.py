from __future__ import annotations

from pathlib import Path
import pytest
from keylogix.constants import EVENT_KEY_DOWN, EVENT_KEY_UP
from keylogix.observation.base import ObservationSource
from keylogix.observation.replay import ReplaySource
from keylogix.observation.synthetic import SyntheticSource, script_from_keys
from keylogix.observation.win32 import Win32HookSource
from keylogix.status import Status


def test_base_observation_source_lifecycle():
    src = ObservationSource()
    res = src.start("sess-1")
    assert res.ok is True
    assert src.session is not None
    assert src.session.session_id == "sess-1"

    # Start again while active fails
    assert src.start().status == Status.INVALID_INPUT

    # Stop source
    stop_res = src.stop()
    assert stop_res.ok is True
    assert src.stopped is True


def test_synthetic_source_script():
    script = [
        {"action": "context", "application": "notepad.exe", "window_title": "Notes"},
        {"action": "key", "key_code": 65, "event_type": "KEY_DOWN"},
        {"action": "key", "key_code": 65, "event_type": "KEY_UP"},
    ]
    src = SyntheticSource(script=script)
    src.start()
    events = list(src.events())
    assert len(events) == 2
    assert all(e.ok for e in events)
    e1 = events[0].value
    assert e1.key_code == 65
    assert e1.event_type == EVENT_KEY_DOWN
    assert e1.application.value == "notepad.exe"
    src.stop()


def test_synthetic_source_interrupt():
    script = [
        {"action": "key", "key_code": 65, "event_type": "KEY_DOWN"},
        {"action": "key", "key_code": 65, "event_type": "KEY_UP"},
        {"action": "key", "key_code": 66, "event_type": "KEY_DOWN"},
    ]
    src = SyntheticSource(script=script, interrupt_after=1)
    src.start()
    events = list(src.events())
    assert len(events) == 2
    assert events[0].ok is True
    assert events[1].status == Status.INTERRUPTED


def test_script_from_keys():
    script = script_from_keys([65, 66], hold=True, application="app.exe")
    assert script[0]["action"] == "context"
    assert script[0]["application"] == "app.exe"
    assert script[1]["key_code"] == 65
    assert script[1]["event_type"] == EVENT_KEY_DOWN
    assert script[2]["key_code"] == 65
    assert script[2]["event_type"] == EVENT_KEY_UP
    assert len(script) == 5


def test_replay_source(tmp_path: Path):
    sample_file = tmp_path / "test_raw.jsonl"
    sample_file.write_text(
        '{"clock_source": "synthetic", "event_id": "e1", "event_type": "KEY_DOWN", "key_code": 65, "monotonic_ns": 1000, "session_id": "s1", "source": "synthetic", "timestamp": "2026-09-18T12:00:00.000000Z"}\n',
        encoding="utf-8",
    )
    src = ReplaySource(sample_file, expected_session_id="s1")
    src.start()
    events = list(src.events())
    assert len(events) == 1
    assert events[0].ok is True
    assert events[0].value.event_id == "e1"
    src.stop()


def test_win32_hook_source_availability():
    src = Win32HookSource("dummy_out.jsonl")
    avail = src.availability()
    # On Linux analysis host, availability returns SKIPPED
    assert avail.status == Status.SKIPPED
