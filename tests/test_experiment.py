from __future__ import annotations

from pathlib import Path
from keylogix.experiment import ExperimentDefinition, ExperimentRunner, create_source_from_spec
from keylogix.status import Status


def test_experiment_definition_from_dict():
    data = {
        "experiment_id": "EXP-TEST",
        "objective": "Test objective",
        "procedure": ["Step 1", "Step 2"],
        "expected_observation": {"status": "SUCCESS_WITH_DATA"},
        "input": {"type": "synthetic", "script": []},
    }
    defn = ExperimentDefinition.from_dict(data)
    assert defn.experiment_id == "EXP-TEST"
    assert len(defn.procedure) == 2
    d = defn.to_dict()
    assert d["experiment_id"] == "EXP-TEST"


def test_create_source_from_spec():
    syn_spec = {"type": "synthetic", "script": []}
    res = create_source_from_spec(syn_spec)
    assert res.ok is True

    rep_spec = {"type": "replay", "path": "some/path.jsonl"}
    res2 = create_source_from_spec(rep_spec)
    assert res2.ok is True

    bad_spec = {"type": "unknown_source_type"}
    res3 = create_source_from_spec(bad_spec)
    assert res3.status == Status.INVALID_INPUT


def test_experiment_runner(tmp_path: Path):
    runner = ExperimentRunner(base_output_dir=tmp_path / "experiments")
    defn = ExperimentDefinition(
        experiment_id="EXP-RUN-TEST",
        objective="Verify runner execution",
        procedure=["Run simple synthetic script"],
        expected_observation={"status": "SUCCESS_WITH_DATA"},
        input_data={
            "type": "synthetic",
            "script": [
                {"action": "key", "key_code": 65, "event_type": "KEY_DOWN"},
                {"action": "key", "key_code": 65, "event_type": "KEY_UP"},
            ],
        },
    )
    res = runner.run_experiment(defn)
    assert res.ok is True
    val = res.value
    out_dir = Path(val["output_dir"])
    assert (out_dir / "experiment.json").is_file()
    assert (out_dir / "environment.json").is_file()
    assert (out_dir / "report.md").is_file()
    assert (out_dir / "raw.jsonl").is_file()
    assert (out_dir / "normalized.jsonl").is_file()
