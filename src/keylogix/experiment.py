"""Experiment schema and runner.

Manages controlled laboratory experiments, artifact generation, and reporting.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Union

from keylogix.constants import IMPLEMENTATION_VERSION, SCHEMA_EXPERIMENT, SOURCE_SYNTHETIC
from keylogix.environment import collect_environment
from keylogix.identity import IdentityFactory
from keylogix.observation.base import ObservationSource
from keylogix.observation.replay import ReplaySource
from keylogix.observation.synthetic import SyntheticSource
from keylogix.observation.win32 import Win32HookSource
from keylogix.persist import ensure_dir, read_json, write_json, atomic_write_text
from keylogix.pipeline import Pipeline, PipelineConfig, PipelineOutput
from keylogix.report import render_report
from keylogix.status import Result, Status
from keylogix.timeutil import Clock, SystemClock


@dataclass
class ExperimentDefinition:
    experiment_id: str
    objective: str
    procedure: List[str]
    expected_observation: Dict[str, Any]
    input_data: Dict[str, Any]
    configuration: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)
    schema: str = SCHEMA_EXPERIMENT

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> ExperimentDefinition:
        if not isinstance(data, Mapping):
            raise ValueError("ExperimentDefinition must be an object")
        exp_id = str(data.get("experiment_id") or "")
        if not exp_id:
            raise ValueError("experiment_id is required")
        objective = str(data.get("objective") or "")
        procedure = list(data.get("procedure") or [])
        expected = dict(data.get("expected_observation") or {})
        input_data = dict(data.get("input") or data.get("input_data") or {})
        config = dict(data.get("configuration") or {})
        limitations = list(data.get("limitations") or [])
        return ExperimentDefinition(
            experiment_id=exp_id,
            objective=objective,
            procedure=procedure,
            expected_observation=expected,
            input_data=input_data,
            configuration=config,
            limitations=limitations,
            schema=str(data.get("schema") or SCHEMA_EXPERIMENT),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "experiment_id": self.experiment_id,
            "objective": self.objective,
            "procedure": list(self.procedure),
            "expected_observation": dict(self.expected_observation),
            "input": dict(self.input_data),
            "configuration": dict(self.configuration),
            "limitations": list(self.limitations),
        }


def create_source_from_spec(
    input_spec: Mapping[str, Any],
    ids: Optional[IdentityFactory] = None,
    clock: Optional[Clock] = None,
) -> Result:
    source_type = input_spec.get("type") or input_spec.get("source") or SOURCE_SYNTHETIC
    if source_type == "synthetic":
        script = input_spec.get("script") or []
        default_app = input_spec.get("default_application")
        default_win = input_spec.get("default_window")
        interrupt_after = input_spec.get("interrupt_after")
        source = SyntheticSource(
            script=script,
            ids=ids,
            clock=clock,
            default_application=default_app,
            default_window=default_win,
            interrupt_after=interrupt_after,
        )
        return Result.success(source)
    elif source_type == "replay":
        path = input_spec.get("path") or input_spec.get("file")
        if not path:
            return Result.invalid("replay source requires path/file")
        expected_session = input_spec.get("expected_session_id")
        source = ReplaySource(
            path=path,
            ids=ids,
            clock=clock,
            expected_session_id=expected_session,
        )
        return Result.success(source)
    elif source_type == "win32_llhook":
        out_path = input_spec.get("output_path") or "output/raw_hook.jsonl"
        observer_path = input_spec.get("observer_path")
        duration_ms = input_spec.get("duration_ms")
        extra_args = input_spec.get("extra_args")
        source = Win32HookSource(
            output_path=out_path,
            observer_path=observer_path,
            duration_ms=duration_ms,
            extra_args=extra_args,
            ids=ids,
            clock=clock,
        )
        return Result.success(source)
    return Result.invalid(f"unrecognized source type: {source_type}")


class ExperimentRunner:
    def __init__(
        self,
        base_output_dir: Union[str, Path] = "output/experiments",
        ids: Optional[IdentityFactory] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self.base_output_dir = Path(base_output_dir)
        self.ids = ids or IdentityFactory()
        self.clock = clock or SystemClock()
        self.pipeline = Pipeline(ids=self.ids, clock=self.clock)

    def load_definition(self, path_or_dict: Union[str, Path, Mapping[str, Any]]) -> Result:
        if isinstance(path_or_dict, Mapping):
            try:
                defn = ExperimentDefinition.from_dict(path_or_dict)
                return Result.success(defn)
            except Exception as exc:
                return Result.invalid(f"invalid experiment definition: {exc}")
        path = Path(path_or_dict)
        read_res = read_json(path)
        if not read_res.ok:
            return read_res
        try:
            defn = ExperimentDefinition.from_dict(read_res.value)
            return Result.success(defn)
        except Exception as exc:
            return Result.invalid(f"invalid experiment definition in {path}: {exc}")

    def run_experiment(
        self,
        definition: Union[ExperimentDefinition, Path, str, Mapping[str, Any]],
        run_id: Optional[str] = None,
        custom_output_dir: Optional[Union[str, Path]] = None,
    ) -> Result:
        if not isinstance(definition, ExperimentDefinition):
            loaded = self.load_definition(definition)
            if not loaded.ok:
                return loaded
            exp_defn: ExperimentDefinition = loaded.value
        else:
            exp_defn = definition

        active_run_id = run_id or self.ids.new_id()
        if custom_output_dir:
            run_output_dir = Path(custom_output_dir)
        else:
            run_output_dir = self.base_output_dir / exp_defn.experiment_id / active_run_id

        ensure_res = ensure_dir(run_output_dir)
        if not ensure_res.ok:
            return ensure_res

        # Collect environment
        env_data = collect_environment()
        write_json(run_output_dir / "environment.json", env_data)

        # Create observation source
        src_res = create_source_from_spec(exp_defn.input_data, ids=self.ids, clock=self.clock)
        if not src_res.ok:
            return src_res
        source: ObservationSource = src_res.value

        # Configure pipeline
        pipe_cfg = PipelineConfig(
            experiment_id=exp_defn.experiment_id,
            output_dir=run_output_dir,
            associate_context=exp_defn.configuration.get("associate_context", True),
            persist=True,
        )

        pipe_res = self.pipeline.run(source, pipe_cfg)
        output: PipelineOutput = pipe_res.value

        actual_obs = {
            "status": output.status.value,
            "raw_count": len(output.raw),
            "normalized_count": len(output.normalized),
            "classified_count": len(output.classified),
            "evidence_count": output.evidence_count,
            "failures": output.failures,
        }
        if output.analysis:
            actual_obs["analysis"] = output.analysis
        if output.sequence_classification:
            actual_obs["sequence_classification"] = output.sequence_classification

        # Evaluate result vs expected
        matches_expected = True
        mismatches = []
        for k, expected_val in exp_defn.expected_observation.items():
            if k == "status":
                if output.status.value != expected_val:
                    matches_expected = False
                    mismatches.append(f"status: expected {expected_val}, got {output.status.value}")
            elif k == "raw_count":
                if len(output.raw) != expected_val:
                    matches_expected = False
                    mismatches.append(f"raw_count: expected {expected_val}, got {len(output.raw)}")
            elif k == "normalized_count":
                if len(output.normalized) != expected_val:
                    matches_expected = False
                    mismatches.append(f"normalized_count: expected {expected_val}, got {len(output.normalized)}")
            elif k == "sequence_label":
                actual_label = output.sequence_classification.get("category") if output.sequence_classification else None
                if actual_label != expected_val:
                    matches_expected = False
                    mismatches.append(f"sequence_label: expected {expected_val}, got {actual_label}")
            elif k == "context_changes":
                actual_ctx = output.analysis.get("context_change_count") if output.analysis else 0
                if actual_ctx != expected_val:
                    matches_expected = False
                    mismatches.append(f"context_changes: expected {expected_val}, got {actual_ctx}")
            elif k == "burst_count":
                actual_burst = output.analysis.get("burst_count") if output.analysis else 0
                if actual_burst < expected_val:
                    matches_expected = False
                    mismatches.append(f"burst_count: expected >={expected_val}, got {actual_burst}")
            elif k == "max_repeat_run":
                actual_rep = output.analysis.get("max_repeat_run") if output.analysis else 0
                if actual_rep < expected_val:
                    matches_expected = False
                    mismatches.append(f"max_repeat_run: expected >={expected_val}, got {actual_rep}")
            elif k == "failure_count":
                if len(output.failures) != expected_val:
                    matches_expected = False
                    mismatches.append(f"failure_count: expected {expected_val}, got {len(output.failures)}")

        result_text = f"Executed with status {output.status.value}. Raw events: {len(output.raw)}, Normalized: {len(output.normalized)}."
        if mismatches:
            result_text += f" Mismatches: {'; '.join(mismatches)}."
        else:
            result_text += " All expected observations matched."

        exp_record = {
            "schema": SCHEMA_EXPERIMENT,
            "experiment_id": exp_defn.experiment_id,
            "run_id": active_run_id,
            "status": output.status.value,
            "objective": exp_defn.objective,
            "environment": env_data,
            "implementation_version": IMPLEMENTATION_VERSION,
            "configuration": exp_defn.configuration,
            "input": exp_defn.input_data,
            "procedure": exp_defn.procedure,
            "expected_observation": exp_defn.expected_observation,
            "actual_observation": actual_obs,
            "matches_expected": matches_expected,
            "mismatches": mismatches,
            "telemetry": output.observability,
            "security_product_state": env_data.get("security_product", {}),
            "result": result_text,
            "limitations": exp_defn.limitations,
            "analysis": output.analysis or {},
        }

        # Persist experiment record and report
        write_json(run_output_dir / "experiment.json", exp_record)
        report_md = render_report(exp_record)
        atomic_write_text(run_output_dir / "report.md", report_md)

        return Result(
            output.status,
            {
                "experiment_id": exp_defn.experiment_id,
                "run_id": active_run_id,
                "output_dir": str(run_output_dir),
                "pipeline_output": output,
                "experiment_record": exp_record,
            },
            f"experiment {exp_defn.experiment_id} run {active_run_id} finished: {output.status.value}",
        )
