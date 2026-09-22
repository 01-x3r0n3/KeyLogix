"""Pipeline orchestration. Domain logic lives in the stage modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from keylogix.analysis import Analyzer
from keylogix.classify import Classifier
from keylogix.constants import (
    IMPLEMENTATION_VERSION,
    KIND_BEHAVIORAL,
    KIND_DERIVED,
    KIND_HEURISTIC,
    KIND_NORMALIZED,
    KIND_RAW,
)
from keylogix.context import ContextAssociator, ContextTimelineEntry
from keylogix.evidence import EvidenceStore
from keylogix.identity import IdentityFactory
from keylogix.model import NormalizedEvent, RawObservation
from keylogix.normalize import Normalizer
from keylogix.observability import ObservabilityLog
from keylogix.observation.base import ObservationSource, Session
from keylogix.persist import write_json, write_jsonl
from keylogix.status import Result, Status
from keylogix.timeutil import Clock, SystemClock


@dataclass
class PipelineConfig:
    experiment_id: str
    output_dir: Path
    associate_context: bool = True
    timeline: Sequence[ContextTimelineEntry] = field(default_factory=tuple)
    condition_event_ids: Optional[Set[str]] = None
    persist: bool = True


@dataclass
class PipelineOutput:
    status: Status
    session: Optional[Session]
    raw: List[RawObservation]
    normalized: List[NormalizedEvent]
    classified: List[dict]
    sequence_classification: Optional[dict]
    analysis: Optional[dict]
    evidence_count: int
    observability: dict
    failures: List[dict]
    output_dir: Optional[str]


class Pipeline:
    def __init__(
        self,
        ids: Optional[IdentityFactory] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self.ids = ids or IdentityFactory()
        self.clock = clock or SystemClock()
        self.normalizer = Normalizer()
        self.classifier = Classifier(ids=self.ids)
        self.analyzer = Analyzer(ids=self.ids)

    def run(self, source: ObservationSource, config: PipelineConfig) -> Result:
        obs = ObservabilityLog(config.experiment_id, "pending", ids=self.ids, clock=self.clock)
        obs.record(
            "pipeline_start",
            {"implementation_version": IMPLEMENTATION_VERSION, "source": source.name},
        )
        started = source.start()
        if not started.ok:
            obs.record("source_start", started.to_dict(), notes="source did not start")
            out = self._empty_output(started.status, obs, config, failures=[started.to_dict()])
            return Result(started.status, out, started.message)

        session: Session = started.value
        obs.session_id = session.session_id
        evidence = EvidenceStore(
            config.experiment_id, session.session_id, ids=self.ids, clock=self.clock
        )
        obs.record("source_start", {"session_id": session.session_id, "status": started.status.value})

        raws: List[RawObservation] = []
        failures: List[dict] = []
        interrupted = False
        for item in source.events():
            if item.status == Status.INTERRUPTED:
                interrupted = True
                failures.append(item.to_dict())
                break
            if item.status == Status.SUCCESS_NO_DATA:
                continue
            if not item.ok:
                failures.append(item.to_dict())
                continue
            if not isinstance(item.value, RawObservation):
                failures.append(
                    Result.invalid("source yielded non-raw value").to_dict()
                )
                continue
            raws.append(item.value)
            evidence.add(
                source=item.value.source,
                information_kind=KIND_RAW,
                event_id=item.value.event_id,
                observed=item.value.to_dict(),
            )

        stop = source.stop()
        if not stop.ok:
            failures.append(stop.to_dict())
        obs.record("source_stop", {"event_count": len(raws), "stop": stop.to_dict()})

        if interrupted and not raws:
            out = self._finish(
                Status.INTERRUPTED,
                session,
                raws,
                [],
                [],
                None,
                None,
                evidence,
                obs,
                failures,
                config,
            )
            return Result(Status.INTERRUPTED, out, "interrupted before any observation")

        if not raws and failures and all(
            f.get("status") in (Status.SKIPPED.value, Status.OUT_OF_SCOPE.value) for f in failures
        ):
            out = self._finish(
                Status(failures[0]["status"]),
                session,
                raws,
                [],
                [],
                None,
                None,
                evidence,
                obs,
                failures,
                config,
            )
            return Result(out.status, out, failures[0].get("message") or out.status.value)

        if not raws and failures:
            # Observation mechanism failed rather than observing emptiness.
            status = Status.PROVIDER_FAILURE
            first = failures[0].get("status")
            try:
                status = Status(first)
            except ValueError:
                status = Status.PROVIDER_FAILURE
            if status in (Status.SUCCESS_WITH_DATA, Status.SUCCESS_NO_DATA):
                status = Status.PROVIDER_FAILURE
            out = self._finish(status, session, raws, [], [], None, None, evidence, obs, failures, config)
            return Result(status, out, "observation produced no valid events")

        if not raws:
            out = self._finish(
                Status.SUCCESS_NO_DATA,
                session,
                raws,
                [],
                [],
                None,
                None,
                evidence,
                obs,
                failures,
                config,
            )
            return Result(Status.SUCCESS_NO_DATA, out, "no events observed")

        self.normalizer.reset()
        norm_result = self.normalizer.normalize_many(raws)
        normalized: List[NormalizedEvent] = []
        if norm_result.value:
            normalized = list(norm_result.value)
        if not norm_result.ok and norm_result.status != Status.PARTIAL:
            failures.append(norm_result.to_dict())
        elif norm_result.status == Status.PARTIAL:
            failures.append(norm_result.to_dict())
        for event in normalized:
            evidence.add(
                source=event.source,
                information_kind=KIND_NORMALIZED,
                event_id=event.event_id,
                parent_ids=(event.event_id,),
                derived=event.to_dict(),
            )

        if config.associate_context and normalized:
            associator = ContextAssociator(config.timeline)
            ctx = associator.associate_many(normalized)
            if ctx.value:
                normalized = list(ctx.value)
            if ctx.status in (Status.PARTIAL, Status.UNAVAILABLE_CONTEXT):
                obs.record("context", ctx.to_dict())
            elif not ctx.ok and ctx.status != Status.SUCCESS_NO_DATA:
                failures.append(ctx.to_dict())

        classified_dicts: List[dict] = []
        seq_dict = None
        if normalized:
            cls = self.classifier.classify_many(normalized)
            if cls.ok and cls.value:
                for rec in cls.value:
                    classified_dicts.append(rec.to_dict())
                    evidence.add(
                        source=normalized[0].source,
                        information_kind=KIND_DERIVED,
                        event_id=rec.event_id,
                        parent_ids=(rec.event_id,),
                        classification=rec.to_dict(),
                        confidence=rec.confidence,
                    )
            elif not cls.ok:
                failures.append(cls.to_dict())
            seq = self.classifier.classify_sequence(normalized)
            if seq.ok and seq.value is not None:
                seq_dict = seq.value.to_dict()
                evidence.add(
                    source=normalized[0].source,
                    information_kind=KIND_HEURISTIC,
                    event_id=seq.value.event_id,
                    parent_ids=tuple(e.event_id for e in normalized),
                    classification=seq_dict,
                    confidence=seq.value.confidence,
                    notes="heuristic sequence label; not a determination of intent",
                )

        analysis_dict = None
        if normalized:
            analyzed = self.analyzer.analyze(normalized, config.condition_event_ids)
            if analyzed.ok and analyzed.value is not None:
                analysis_dict = analyzed.value.to_dict()
                evidence.add(
                    source=normalized[0].source,
                    information_kind=KIND_BEHAVIORAL,
                    parent_ids=tuple(e.event_id for e in normalized),
                    derived=analysis_dict,
                    notes="behavioral measurements; not a determination of intent",
                )
            elif not analyzed.ok:
                failures.append(analyzed.to_dict())

        status = Status.SUCCESS_WITH_DATA
        if interrupted:
            status = Status.INTERRUPTED
        elif failures and normalized:
            status = Status.PARTIAL
        elif failures and not normalized:
            status = Status.INVALID_INPUT

        out = self._finish(
            status,
            session,
            raws,
            normalized,
            classified_dicts,
            seq_dict,
            analysis_dict,
            evidence,
            obs,
            failures,
            config,
        )
        return Result(status, out, "pipeline {0}".format(status.value))

    def _empty_output(
        self,
        status: Status,
        obs: ObservabilityLog,
        config: PipelineConfig,
        failures: List[dict],
    ) -> PipelineOutput:
        return PipelineOutput(
            status=status,
            session=None,
            raw=[],
            normalized=[],
            classified=[],
            sequence_classification=None,
            analysis=None,
            evidence_count=0,
            observability=obs.to_dict(),
            failures=failures,
            output_dir=None,
        )

    def _finish(
        self,
        status: Status,
        session: Session,
        raws: List[RawObservation],
        normalized: List[NormalizedEvent],
        classified: List[dict],
        seq_dict: Optional[dict],
        analysis_dict: Optional[dict],
        evidence: EvidenceStore,
        obs: ObservabilityLog,
        failures: List[dict],
        config: PipelineConfig,
    ) -> PipelineOutput:
        out_dir = None
        obs.record(
            "pipeline_finish",
            {
                "status": status.value,
                "raw": len(raws),
                "normalized": len(normalized),
                "classified": len(classified),
                "failures": len(failures),
            },
        )
        if config.persist:
            dest = Path(config.output_dir)
            writes = [
                write_jsonl(dest / "raw.jsonl", [r.to_dict() for r in raws]),
                write_jsonl(dest / "normalized.jsonl", [n.to_dict() for n in normalized]),
                write_jsonl(dest / "classified.jsonl", classified),
                write_jsonl(dest / "evidence.jsonl", evidence.to_dicts()),
                write_json(dest / "observability.json", obs.to_dict()),
            ]
            if analysis_dict is not None:
                writes.append(write_json(dest / "analysis.json", analysis_dict))
            if seq_dict is not None:
                writes.append(write_json(dest / "sequence_classification.json", seq_dict))
            persist_fail = [w.to_dict() for w in writes if not w.ok]
            if persist_fail:
                failures.extend(persist_fail)
                status = Status.PROVIDER_FAILURE
            else:
                out_dir = str(dest)
        return PipelineOutput(
            status=status,
            session=session,
            raw=raws,
            normalized=normalized,
            classified=classified,
            sequence_classification=seq_dict,
            analysis=analysis_dict,
            evidence_count=len(evidence.records()),
            observability=obs.to_dict(),
            failures=failures,
            output_dir=out_dir,
        )
