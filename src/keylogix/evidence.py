"""Evidence records with explicit provenance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from keylogix.constants import SCHEMA_EVIDENCE
from keylogix.identity import IdentityFactory
from keylogix.status import Result
from keylogix.timeutil import Clock, SystemClock


@dataclass(frozen=True)
class EvidenceRecord:
    record_id: str
    timestamp: str
    source: str
    information_kind: str
    experiment_id: str
    session_id: str
    event_id: Optional[str]
    parent_ids: tuple
    observed: Optional[Mapping[str, Any]]
    derived: Optional[Mapping[str, Any]]
    classification: Optional[Mapping[str, Any]]
    confidence: Optional[float]
    notes: str = ""
    schema: str = SCHEMA_EVIDENCE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "information_kind": self.information_kind,
            "experiment_id": self.experiment_id,
            "session_id": self.session_id,
            "event_id": self.event_id,
            "parent_ids": list(self.parent_ids),
            "observed": dict(self.observed) if self.observed is not None else None,
            "derived": dict(self.derived) if self.derived is not None else None,
            "classification": dict(self.classification) if self.classification is not None else None,
            "confidence": self.confidence,
            "notes": self.notes,
        }


class EvidenceStore:
    def __init__(
        self,
        experiment_id: str,
        session_id: str,
        ids: Optional[IdentityFactory] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self.experiment_id = experiment_id
        self.session_id = session_id
        self.ids = ids or IdentityFactory()
        self.clock = clock or SystemClock()
        self._records: List[EvidenceRecord] = []

    def add(
        self,
        source: str,
        information_kind: str,
        *,
        event_id: Optional[str] = None,
        parent_ids: Sequence[str] = (),
        observed: Optional[Mapping[str, Any]] = None,
        derived: Optional[Mapping[str, Any]] = None,
        classification: Optional[Mapping[str, Any]] = None,
        confidence: Optional[float] = None,
        notes: str = "",
    ) -> EvidenceRecord:
        if observed is None and derived is None and classification is None:
            raise ValueError("evidence must contain observed, derived, or classification data")
        rec = EvidenceRecord(
            record_id=self.ids.new_id(),
            timestamp=self.clock.utc_iso(),
            source=source,
            information_kind=information_kind,
            experiment_id=self.experiment_id,
            session_id=self.session_id,
            event_id=event_id,
            parent_ids=tuple(parent_ids),
            observed=dict(observed) if observed is not None else None,
            derived=dict(derived) if derived is not None else None,
            classification=dict(classification) if classification is not None else None,
            confidence=confidence,
            notes=notes,
        )
        self._records.append(rec)
        return rec

    def records(self) -> List[EvidenceRecord]:
        return list(self._records)

    def to_dicts(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._records]
