"""Event classification.

Per-key categories are deterministic transforms of the virtual-key code.
Sequence labels are heuristic and never reported as certainty.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from keylogix.constants import (
    CAT_CONTROL,
    CAT_FUNCTION,
    CAT_MODIFIER,
    CAT_NAVIGATION,
    CAT_ORDINARY,
    CAT_OEM,
    EVENT_KEY_DOWN,
    HEURISTIC_CONFIDENCE,
    KIND_DERIVED,
    KIND_HEURISTIC,
    METHOD_DETERMINISTIC,
    METHOD_HEURISTIC,
    SEQ_CHORD,
    SEQ_EMPTY,
    SEQ_MIXED,
    SEQ_SPECIAL,
    SEQ_TEXT_ORIENTED,
    SPECIAL_SEQUENCE_FRACTION,
    TEXT_ORIENTED_FRACTION,
)
from keylogix.identity import IdentityFactory
from keylogix.model import ClassificationRecord, NormalizedEvent
from keylogix.status import Result, Status
from keylogix.vk import classify_vk


class Classifier:
    def __init__(self, ids: Optional[IdentityFactory] = None) -> None:
        self.ids = ids or IdentityFactory()

    def classify_event(self, event: NormalizedEvent) -> Result:
        if not isinstance(event, NormalizedEvent):
            return Result.invalid("expected NormalizedEvent")
        category = classify_vk(event.key_code)
        record = ClassificationRecord(
            record_id=self.ids.new_id(),
            event_id=event.event_id,
            category=category,
            method=METHOD_DETERMINISTIC,
            confidence=1.0,
            information_kind=KIND_DERIVED,
            details={"key_code": event.key_code, "event_type": event.event_type},
        )
        return Result.success(record)

    def classify_many(self, events: Sequence[NormalizedEvent]) -> Result:
        if not isinstance(events, (list, tuple)):
            return Result.invalid("events must be a list")
        if not events:
            return Result.no_data("no events to classify")
        records: List[ClassificationRecord] = []
        for event in events:
            item = self.classify_event(event)
            if not item.ok:
                return Result(
                    Status.PARTIAL,
                    records,
                    "classification stopped: {0}".format(item.message),
                    {"error": item.to_dict()},
                )
            records.append(item.value)
        return Result.success(records)

    def classify_sequence(self, events: Sequence[NormalizedEvent]) -> Result:
        if not isinstance(events, (list, tuple)):
            return Result.invalid("events must be a list")
        downs = [e for e in events if e.event_type == EVENT_KEY_DOWN]
        if not downs:
            record = ClassificationRecord(
                record_id=self.ids.new_id(),
                event_id=events[0].event_id if events else "none",
                category=SEQ_EMPTY,
                method=METHOD_HEURISTIC,
                confidence=HEURISTIC_CONFIDENCE,
                information_kind=KIND_HEURISTIC,
                details={"key_down_count": 0, "event_count": len(events)},
            )
            if not events:
                return Result.no_data("no events to classify")
            return Result.success(record)

        cats = [classify_vk(e.key_code) for e in downs]
        n = float(len(cats))
        ordinary_like = sum(1 for c in cats if c in (CAT_ORDINARY, CAT_OEM)) / n
        special_like = (
            sum(1 for c in cats if c in (CAT_NAVIGATION, CAT_CONTROL, CAT_FUNCTION)) / n
        )
        modifier_downs = sum(1 for c in cats if c == CAT_MODIFIER)
        non_mod = len(cats) - modifier_downs
        chord = modifier_downs >= 1 and non_mod >= 1

        if ordinary_like >= TEXT_ORIENTED_FRACTION:
            label = SEQ_TEXT_ORIENTED
        elif special_like >= SPECIAL_SEQUENCE_FRACTION:
            label = SEQ_SPECIAL
        elif chord and ordinary_like < TEXT_ORIENTED_FRACTION:
            label = SEQ_CHORD
        else:
            label = SEQ_MIXED

        record = ClassificationRecord(
            record_id=self.ids.new_id(),
            event_id=downs[0].event_id,
            category=label,
            method=METHOD_HEURISTIC,
            confidence=HEURISTIC_CONFIDENCE,
            information_kind=KIND_HEURISTIC,
            details={
                "key_down_count": len(downs),
                "ordinary_like_fraction": ordinary_like,
                "special_like_fraction": special_like,
                "modifier_downs": modifier_downs,
                "chord_condition": chord,
            },
        )
        return Result.success(record)
