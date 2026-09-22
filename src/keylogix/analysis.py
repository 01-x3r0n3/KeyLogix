"""Behavioral analysis of normalized event sequences.

Measurements are separate from conclusions. Nothing here asserts intent.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Set, Tuple

from keylogix.classify import Classifier
from keylogix.constants import (
    BURST_MAX_INTERARRIVAL_NS,
    BURST_MIN_EVENTS,
    CAT_MODIFIER,
    CAT_ORDINARY,
    EVENT_KEY_DOWN,
    EVENT_KEY_UP,
    REPEAT_MAX_INTERARRIVAL_NS,
    REPEAT_MIN_COUNT,
)
from keylogix.identity import IdentityFactory
from keylogix.model import BehavioralSummary, Conclusion, NormalizedEvent
from keylogix.status import Result
from keylogix.vk import classify_vk


def _percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        raise ValueError("empty")
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return float(sorted_vals[f])
    return float(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f))


def _pair_unmatched(events: Sequence[NormalizedEvent]) -> Tuple[int, int]:
    pending: Dict[int, int] = defaultdict(int)
    unmatched_ups = 0
    for event in events:
        if event.event_type == EVENT_KEY_DOWN:
            pending[event.key_code] += 1
        elif event.event_type == EVENT_KEY_UP:
            if pending[event.key_code] > 0:
                pending[event.key_code] -= 1
            else:
                unmatched_ups += 1
    unmatched_downs = sum(pending.values())
    return unmatched_downs, unmatched_ups


def _context_key(event: NormalizedEvent) -> Tuple[str, str]:
    app = event.application.value if event.application.value is not None else ""
    win = event.window_title.value if event.window_title.value is not None else ""
    pres = event.application.presence + "/" + event.window_title.presence
    return pres + ":" + app, win


def _bursts_and_repeats(downs: Sequence[NormalizedEvent]) -> Tuple[int, int]:
    burst_count = 0
    max_repeat = 1 if downs else 0
    if len(downs) < 2:
        return burst_count, max_repeat
    run = 1
    burst_run = 1
    for prev, cur in zip(downs, downs[1:]):
        interval = cur.monotonic_ns - prev.monotonic_ns
        if interval < 0:
            interval = 0
        if cur.key_code == prev.key_code and interval < REPEAT_MAX_INTERARRIVAL_NS:
            run += 1
            if run > max_repeat:
                max_repeat = run
        else:
            run = 1
        if interval < BURST_MAX_INTERARRIVAL_NS:
            burst_run += 1
        else:
            if burst_run >= BURST_MIN_EVENTS:
                burst_count += 1
            burst_run = 1
    if burst_run >= BURST_MIN_EVENTS:
        burst_count += 1
    return burst_count, max_repeat


class Analyzer:
    def __init__(self, ids: Optional[IdentityFactory] = None) -> None:
        self.ids = ids or IdentityFactory()
        self._classifier = Classifier(ids=self.ids)

    def analyze(
        self,
        events: Sequence[NormalizedEvent],
        condition_event_ids: Optional[Set[str]] = None,
    ) -> Result:
        if not isinstance(events, (list, tuple)):
            return Result.invalid("events must be a list")
        if not events:
            return Result.no_data("no events to analyze")

        session_id = events[0].session_id
        downs = [e for e in events if e.event_type == EVENT_KEY_DOWN]
        ups = [e for e in events if e.event_type == EVENT_KEY_UP]
        unmatched_downs, unmatched_ups = _pair_unmatched(events)
        mono = [e.monotonic_ns for e in events]
        duration = max(mono) - min(mono) if len(mono) >= 2 else 0
        intervals = [
            float(b.monotonic_ns - a.monotonic_ns)
            for a, b in zip(events, events[1:])
            if b.monotonic_ns >= a.monotonic_ns
        ]
        mean_i = statistics.mean(intervals) if intervals else None
        median_i = statistics.median(intervals) if intervals else None
        p95_i = _percentile(sorted(intervals), 0.95) if intervals else None
        eps = None
        if duration > 0:
            eps = (len(events) / (duration / 1_000_000_000.0))

        burst_count, max_repeat = _bursts_and_repeats(downs)

        ctx_changes = 0
        prev_ctx = None
        for event in events:
            ctx = _context_key(event)
            if prev_ctx is not None and ctx != prev_ctx:
                # Ignore presence-only changes that still have unavailable/unavailable
                ctx_changes += 1
            prev_ctx = ctx

        mod_frac = (
            sum(1 for e in events if classify_vk(e.key_code) == CAT_MODIFIER) / float(len(events))
        )
        ord_frac = (
            sum(1 for e in events if classify_vk(e.key_code) == CAT_ORDINARY) / float(len(events))
        )

        seq = self._classifier.classify_sequence(events)
        seq_label = "empty"
        seq_conf = 0.7
        if seq.ok and seq.value is not None:
            seq_label = seq.value.category
            seq_conf = seq.value.confidence

        conclusions: List[Conclusion] = [
            Conclusion(
                statement="event_count={0}".format(len(events)),
                kind="measured",
                confidence=1.0,
                based_on=tuple(e.event_id for e in events[:8]),
            ),
            Conclusion(
                statement="unmatched_downs={0} unmatched_ups={1}".format(
                    unmatched_downs, unmatched_ups
                ),
                kind="measured",
                confidence=1.0,
            ),
            Conclusion(
                statement="burst_count={0} using research default 5 events / 50ms".format(
                    burst_count
                ),
                kind="derived",
                based_on=(),
            ),
            Conclusion(
                statement="sequence_label={0} is heuristic and is not a determination of intent".format(
                    seq_label
                ),
                kind="inferred",
                confidence=seq_conf,
            ),
        ]
        if condition_event_ids is not None:
            cond = [e for e in events if e.event_id in condition_event_ids]
            other = [e for e in events if e.event_id not in condition_event_ids]
            conclusions.append(
                Conclusion(
                    statement="condition_events={0} other_events={1}".format(
                        len(cond), len(other)
                    ),
                    kind="measured",
                    confidence=1.0,
                )
            )

        summary = BehavioralSummary(
            record_id=self.ids.new_id(),
            session_id=session_id,
            event_count=len(events),
            key_down_count=len(downs),
            key_up_count=len(ups),
            unmatched_downs=unmatched_downs,
            unmatched_ups=unmatched_ups,
            duration_ns=duration,
            events_per_second=eps,
            mean_interarrival_ns=mean_i,
            median_interarrival_ns=median_i,
            p95_interarrival_ns=p95_i,
            max_repeat_run=max_repeat,
            burst_count=burst_count,
            context_change_count=ctx_changes,
            modifier_key_event_fraction=mod_frac,
            ordinary_key_event_fraction=ord_frac,
            sequence_label=seq_label,
            sequence_label_confidence=seq_conf,
            conclusions=tuple(conclusions),
            event_ids=tuple(e.event_id for e in events),
        )
        return Result.success(summary)
