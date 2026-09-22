from __future__ import annotations

from pathlib import Path
import pytest
from keylogix.cli import build_parser, main


def test_cli_help(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])


def test_cli_version(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--version"])


def test_cli_verify():
    rc = main(["verify"])
    assert rc == 0


def test_cli_run_synthetic(tmp_path: Path):
    out_dir = tmp_path / "cli_syn_out"
    rc = main([
        "run-synthetic",
        "--keys", "0x41,0x42",
        "--experiment-id", "CLI-SYN-TEST",
        "--output-dir", str(out_dir),
    ])
    assert rc == 0
    assert (out_dir / "raw.jsonl").is_file()
    assert (out_dir / "normalized.jsonl").is_file()


def test_cli_inspect_raw_and_normalized(tmp_path: Path):
    out_dir = tmp_path / "cli_inspect"
    main([
        "run-synthetic",
        "--keys", "65",
        "--output-dir", str(out_dir),
    ])
    rc_raw = main(["inspect-raw", str(out_dir / "raw.jsonl")])
    assert rc_raw == 0

    rc_norm = main(["inspect-normalized", str(out_dir / "normalized.jsonl")])
    assert rc_norm == 0


def test_cli_run_experiment(tmp_path: Path):
    exp_file = Path("experiments/definitions/EXP-001-synthetic-pipeline.json")
    if exp_file.is_file():
        rc = main(["run-experiment", str(exp_file), "--output-dir", str(tmp_path / "exp_out")])
        assert rc == 0
