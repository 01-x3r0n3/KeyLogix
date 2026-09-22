from __future__ import annotations

from pathlib import Path
from keylogix.observation.synthetic import SyntheticSource, script_from_keys
from keylogix.pipeline import Pipeline, PipelineConfig
from keylogix.status import Status


def test_pipeline_end_to_end(tmp_path: Path):
    script = script_from_keys([65, 66], hold=True, application="notepad.exe")
    source = SyntheticSource(script=script)

    pipe = Pipeline()
    out_dir = tmp_path / "run1"
    config = PipelineConfig(
        experiment_id="TEST-EXP-01",
        output_dir=out_dir,
        associate_context=True,
        persist=True,
    )

    res = pipe.run(source, config)
    assert res.ok is True
    assert res.status == Status.SUCCESS_WITH_DATA

    out = res.value
    assert len(out.raw) == 4
    assert len(out.normalized) == 4
    assert len(out.classified) == 4
    assert out.analysis is not None
    assert out.analysis["event_count"] == 4

    # Verify persisted files
    assert (out_dir / "raw.jsonl").is_file()
    assert (out_dir / "normalized.jsonl").is_file()
    assert (out_dir / "classified.jsonl").is_file()
    assert (out_dir / "analysis.json").is_file()
    assert (out_dir / "evidence.jsonl").is_file()
    assert (out_dir / "observability.json").is_file()


def test_pipeline_empty_source(tmp_path: Path):
    source = SyntheticSource(script=[])
    pipe = Pipeline()
    out_dir = tmp_path / "empty_run"
    config = PipelineConfig(
        experiment_id="TEST-EMPTY",
        output_dir=out_dir,
        persist=True,
    )
    res = pipe.run(source, config)
    assert res.status == Status.SUCCESS_NO_DATA
