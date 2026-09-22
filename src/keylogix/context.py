"""Context association.

Context is an observation with its own reliability. Missing context is
not evidence of abnormal behavior. Observed context is never overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from keylogix.constants import PRESENCE_DERIVED, PRESENCE_OBSERVED
from keylogix.model import NormalizedEvent, OptionalField, Provenance
from keylogix.status import Result, Status


@dataclass(frozen=True)
class ContextConflict:
    event_id: str
    field: str
    observed: str
    derived: str


@dataclass(frozen=True)
class ContextTimelineEntry:
    monotonic_ns: int
    application: Optional[str]
    window_title: Optional[str]


@dataclass(frozen=True)
class ContextAssociation:
    event: NormalizedEvent
    conflicts: Tuple[ContextConflict, ...]
    context_status: str


class ContextAssociator:
    def __init__(self, timeline: Optional[Sequence[ContextTimelineEntry]] = None) -> None:
        self._timeline = list(timeline or [])

    def _lookup(self, monotonic_ns: int) -> Optional[ContextTimelineEntry]:
        chosen = None
        for entry in self._timeline:
            if entry.monotonic_ns <= monotonic_ns:
                chosen = entry
            else:
                break
        return chosen

    def associate_one(self, event: NormalizedEvent) -> Result:
        if not isinstance(event, NormalizedEvent):
            return Result.invalid("expected NormalizedEvent")
        conflicts: List[ContextConflict] = []
        application = event.application
        window_title = event.window_title
        entry = self._lookup(event.monotonic_ns)
        if entry is not None:
            if entry.application is not None:
                if event.application.presence == PRESENCE_OBSERVED:
                    if event.application.value != entry.application:
                        conflicts.append(
                            ContextConflict(
                                event.event_id,
                                "application",
                                event.application.value or "",
                                entry.application,
                            )
                        )
                elif event.application.presence != PRESENCE_DERIVED:
                    application = OptionalField.derived(entry.application, "context_timeline")
            if entry.window_title is not None:
                if event.window_title.presence == PRESENCE_OBSERVED:
                    if event.window_title.value != entry.window_title:
                        conflicts.append(
                            ContextConflict(
                                event.event_id,
                                "window_title",
                                event.window_title.value or "",
                                entry.window_title,
                            )
                        )
                elif event.window_title.presence != PRESENCE_DERIVED:
                    window_title = OptionalField.derived(entry.window_title, "context_timeline")

        notes = event.provenance.notes
        if conflicts:
            notes = (notes + " context_conflict").strip()
        new_event = NormalizedEvent(
            event_id=event.event_id,
            timestamp=event.timestamp,
            event_type=event.event_type,
            key_code=event.key_code,
            key_label=event.key_label,
            modifier_state=event.modifier_state,
            application=application,
            window_title=window_title,
            session_id=event.session_id,
            source=event.source,
            monotonic_ns=event.monotonic_ns,
            clock_source=event.clock_source,
            sequence=event.sequence,
            provenance=Provenance(
                information_kind=event.provenance.information_kind,
                transform=event.provenance.transform,
                parent_ids=event.provenance.parent_ids,
                ingested_via=event.provenance.ingested_via,
                notes=notes,
            ),
            schema=event.schema,
        )
        ctx_status = "ok"
        if (
            new_event.application.presence == "unavailable"
            and new_event.window_title.presence == "unavailable"
        ):
            ctx_status = Status.UNAVAILABLE_CONTEXT.value
        associated = ContextAssociation(new_event, tuple(conflicts), ctx_status)
        if ctx_status == Status.UNAVAILABLE_CONTEXT.value and not self._timeline:
            return Result(
                Status.UNAVAILABLE_CONTEXT,
                associated,
                "context fields unavailable",
            )
        if conflicts:
            return Result(
                Status.PARTIAL,
                associated,
                "context conflict retained",
                {"conflicts": [c.__dict__ for c in conflicts]},
            )
        return Result.success(associated)

    def associate_many(self, events: Sequence[NormalizedEvent]) -> Result:
        if not isinstance(events, (list, tuple)):
            return Result.invalid("events must be a list")
        if not events:
            return Result.no_data("no events for context association")
        out: List[NormalizedEvent] = []
        conflicts: List[dict] = []
        unavailable = 0
        for event in events:
            item = self.associate_one(event)
            if item.value is None:
                return item
            assoc: ContextAssociation = item.value
            out.append(assoc.event)
            if assoc.conflicts:
                conflicts.extend(c.__dict__ for c in assoc.conflicts)
            if assoc.context_status == Status.UNAVAILABLE_CONTEXT.value:
                unavailable += 1
        details = {"conflicts": conflicts, "unavailable_count": unavailable}
        if conflicts:
            return Result(Status.PARTIAL, out, "context conflicts retained", details)
        return Result.success(out, details=details)
