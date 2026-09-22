from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional

from keylogix.identity import IdentityFactory
from keylogix.model import RawObservation
from keylogix.status import Result
from keylogix.timeutil import Clock, SystemClock


@dataclass
class Session:
    session_id: str
    started_at: str
    clock_source: str
    ended_at: Optional[str] = None
    event_count: int = 0
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "schema": "keylogix.session.v1",
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "clock_source": self.clock_source,
            "event_count": self.event_count,
            "notes": self.notes,
        }


class ObservationSource:
    name = "base"

    def __init__(
        self,
        ids: Optional[IdentityFactory] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self.ids = ids or IdentityFactory()
        self.clock = clock or SystemClock()
        self._session: Optional[Session] = None
        self._stopped = False

    def start(self, session_id: Optional[str] = None) -> Result:
        if self._session is not None and not self._stopped:
            return Result.invalid("source already started")
        sid = session_id or self.ids.new_id()
        self._stopped = False
        self._session = Session(
            session_id=sid,
            started_at=self.clock.utc_iso(),
            clock_source=self.clock.source_name(),
        )
        return Result.success(self._session)

    def events(self) -> Iterator[Result]:
        raise NotImplementedError

    def stop(self) -> Result:
        self._stopped = True
        if self._session is None:
            return Result.invalid("source not started")
        self._session.ended_at = self.clock.utc_iso()
        return Result.success(self._session)

    @property
    def session(self) -> Optional[Session]:
        return self._session

    @property
    def stopped(self) -> bool:
        return self._stopped
