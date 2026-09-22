from __future__ import annotations

import time
from pathlib import Path
from keylogix.observation.synthetic import SyntheticSource, script_from_keys
from keylogix.pipeline import Pipeline, PipelineConfig
from keylogix.status import Status


def test_pipeline_throughput_large_synthetic(tmp_path: Path):
    # Generate 5,000 keys (10,000 events total: down + up)
    keys = ([65, 66, 67, 68, 69, 70, 71, 72, 73, 74] * 500)
    script = script_from_keys(keys, hold=True, application="benchmark.exe")

    source = SyntheticSource(script=script)
    pipe = Pipeline()
    out_dir = tmp_path / "bench_run"
    config = PipelineConfig(
        experiment_id="BENCHMARK-10K",
        output_dir=out_dir,
        associate_context=True,
        persist=True,
    )

    t0 = time.perf_counter()
    res = pipe.run(source, config)
    t1 = time.perf_counter()

    elapsed = t1 - t0
    assert res.ok is True
    assert len(res.value.raw) == 10000
    assert len(res.value.normalized) == 10000
    assert len(res.value.classified) == 10000
    assert res.value.analysis is not None
    assert res.value.analysis["event_count"] == 10000

    # Ensure files exist and have reasonable size
    assert (out_dir / "raw.jsonl").stat().st_size > 0
    assert (out_dir / "normalized.jsonl").stat().st_size > 0
    assert (out_dir / "classified.jsonl").stat().st_size > 0

    events_per_sec = 10000.0 / elapsed
    print(f"\n[BENCHMARK] Processed 10,000 events in {elapsed:.3f}s ({events_per_sec:.0f} events/sec)")
