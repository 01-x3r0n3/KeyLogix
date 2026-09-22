from __future__ import annotations

from keylogix.constants import SCHEMA_OBSERVABILITY
from keylogix.observability import ObservabilityLog


def test_observability_log():
    obs = ObservabilityLog("exp1", "sess1")
    rec = obs.record("pipeline_step", {"status": "ok"}, notes="test note")
    assert rec["kind"] == "pipeline_step"
    assert rec["experiment_id"] == "exp1"
    assert rec["session_id"] == "sess1"
    assert rec["observed"] == {"status": "ok"}
    assert rec["notes"] == "test note"

    d = obs.to_dict()
    assert d["schema"] == SCHEMA_OBSERVABILITY
    assert len(d["records"]) == 1
