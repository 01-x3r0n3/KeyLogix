"""Replay previously recorded raw observations from JSONL."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Optional, Union

from keylogix.identity import IdentityFactory
from keylogix.model import ModelError, Provenance, RawObservation
from keylogix.observation.base import ObservationSource
from keylogix.persist import iter_jsonl
from keylogix.status import Result, Status
from keylogix.timeutil import Clock, SystemClock


class ReplaySource(ObservationSource):
    name = "replay"

    def __init__(
        self,
        path: Union[str, Path],
        ids: Optional[IdentityFactory] = None,
        clock: Optional[Clock] = None,
        expected_session_id: Optional[str] = None,
    ) -> None:
        super().__init__(ids=ids or IdentityFactory(), clock=clock or SystemClock())
        self.path = Path(path)
        self.expected_session_id = expected_session_id

    def events(self) -> Iterator[Result]:
        if self._session is None:
            yield Result.invalid("source not started")
            return
        count = 0
        for item in iter_jsonl(self.path):
            if self._stopped:
                yield Result.failure(Status.INTERRUPTED, "replay stopped")
                return
            if item.status == Status.SUCCESS_NO_DATA:
                return
            if not item.ok:
                yield item
                continue
            try:
                raw = RawObservation.from_dict(item.value)
            except (ModelError, ValueError, TypeError, KeyError) as exc:
                yield Result.invalid("replay parse: {0}".format(exc))
                continue
            if self.expected_session_id and raw.session_id != self.expected_session_id:
                yield Result.invalid(
                    "session mismatch: {0} != {1}".format(
                        raw.session_id, self.expected_session_id
                    )
                )
                continue
            try:
                self.ids.register(raw.event_id)
            except ValueError as exc:
                yield Result.invalid(str(exc), details={"event_id": raw.event_id})
                continue
            prov = Provenance(
                information_kind=raw.provenance.information_kind,
                transform=raw.provenance.transform,
                parent_ids=raw.provenance.parent_ids,
                ingested_via="replay",
                notes=raw.provenance.notes,
            )
            object.__setattr__(raw, "provenance", prov)
            count += 1
            if self._session is not None:
                self._session.event_count = count
            yield Result.success(raw)
