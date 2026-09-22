"""Pluggable clocks. Timestamp source is always recorded."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional


def format_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    # Always microseconds + Z.
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_utc(value: str) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class Clock:
    def utc_iso(self) -> str:
        raise NotImplementedError

    def monotonic_ns(self) -> int:
        raise NotImplementedError

    def source_name(self) -> str:
        raise NotImplementedError


class SystemClock(Clock):
    def utc_iso(self) -> str:
        return format_utc(datetime.now(timezone.utc))

    def monotonic_ns(self) -> int:
        import time

        return time.perf_counter_ns()

    def source_name(self) -> str:
        return "python_datetime_utc+perf_counter_ns"


class SyntheticClock(Clock):
    """Deterministic clock. Starts at a fixed UTC instant."""

    def __init__(
        self,
        start: Optional[datetime] = None,
        start_mono_ns: int = 0,
        step_ns: int = 10_000_000,
    ) -> None:
        self._t = start or datetime(2026, 1, 1, tzinfo=timezone.utc)
        self._mono = start_mono_ns
        self._step = step_ns

    def utc_iso(self) -> str:
        return format_utc(self._t)

    def monotonic_ns(self) -> int:
        return self._mono

    def source_name(self) -> str:
        return "synthetic_clock"

    def advance(self, ns: Optional[int] = None) -> None:
        delta = self._step if ns is None else ns
        if delta < 0:
            raise ValueError("clock cannot move backwards")
        self._mono += delta
        self._t = self._t + timedelta(microseconds=delta // 1000)
