"""Run-level observability: artifacts about the experiment itself."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from keylogix.constants import SCHEMA_OBSERVABILITY
from keylogix.identity import IdentityFactory
from keylogix.timeutil import Clock, SystemClock


class ObservabilityLog:
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
        self._records: List[Dict[str, Any]] = []

    def record(self, kind: str, observed: Dict[str, Any], notes: str = "") -> Dict[str, Any]:
        item = {
            "record_id": self.ids.new_id(),
            "timestamp": self.clock.utc_iso(),
            "kind": kind,
            "experiment_id": self.experiment_id,
            "session_id": self.session_id,
            "observed": observed,
            "notes": notes,
        }
        self._records.append(item)
        return item

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA_OBSERVABILITY,
            "experiment_id": self.experiment_id,
            "session_id": self.session_id,
            "records": list(self._records),
        }
