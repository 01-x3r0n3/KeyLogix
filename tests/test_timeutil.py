from __future__ import annotations

from datetime import datetime, timezone
import pytest
from keylogix.timeutil import Clock, SyntheticClock, SystemClock, format_utc, parse_utc


def test_format_and_parse_utc():
    now = datetime(2026, 9, 18, 15, 30, 45, 123456, tzinfo=timezone.utc)
    formatted = format_utc(now)
    assert formatted == "2026-09-18T15:30:45.123456Z"

    parsed = parse_utc(formatted)
    assert parsed is not None
    assert parsed == now

    # Test parse invalid
    assert parse_utc("") is None
    assert parse_utc("not-a-timestamp") is None


def test_system_clock():
    clk = SystemClock()
    assert clk.source_name() == "python_datetime_utc+perf_counter_ns"
    t_iso = clk.utc_iso()
    assert t_iso.endswith("Z")
    m1 = clk.monotonic_ns()
    m2 = clk.monotonic_ns()
    assert m2 >= m1


def test_synthetic_clock():
    start_dt = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    clk = SyntheticClock(start=start_dt, start_mono_ns=1000, step_ns=5000000)
    assert clk.source_name() == "synthetic_clock"
    assert clk.utc_iso() == "2026-01-01T00:00:00.000000Z"
    assert clk.monotonic_ns() == 1000

    clk.advance()
    assert clk.monotonic_ns() == 5001000
    assert clk.utc_iso() == "2026-01-01T00:00:00.005000Z"

    with pytest.raises(ValueError, match="cannot move backwards"):
        clk.advance(-100)
