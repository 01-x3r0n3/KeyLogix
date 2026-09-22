from __future__ import annotations

import pytest
from keylogix.constants import KIND_RAW, SCHEMA_EVIDENCE
from keylogix.evidence import EvidenceRecord, EvidenceStore


def test_evidence_store():
    store = EvidenceStore("exp1", "sess1")
    rec = store.add(
        source="synthetic",
        information_kind=KIND_RAW,
        event_id="e1",
        parent_ids=["p1"],
        observed={"key_code": 65},
        notes="sample evidence",
    )
    assert rec.schema == SCHEMA_EVIDENCE
    assert rec.experiment_id == "exp1"
    assert rec.session_id == "sess1"
    assert rec.event_id == "e1"
    assert rec.parent_ids == ("p1",)
    assert rec.observed == {"key_code": 65}

    records = store.records()
    assert len(records) == 1

    dicts = store.to_dicts()
    assert len(dicts) == 1
    assert dicts[0]["record_id"] == rec.record_id

    # Adding empty data must raise ValueError
    with pytest.raises(ValueError, match="evidence must contain observed, derived, or classification data"):
        store.add(source="test", information_kind=KIND_RAW)
