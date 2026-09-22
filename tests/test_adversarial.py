from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest
from keylogix.analysis import Analyzer
from keylogix.context import ContextAssociator, ContextTimelineEntry
from keylogix.identity import IdentityFactory
from keylogix.model import (
    ModelError,
    ModifierState,
    NormalizedEvent,
    OptionalField,
    Provenance,
    RawObservation,
)
from keylogix.normalize import Normalizer
from keylogix.observation.synthetic import SyntheticSource
from keylogix.pipeline import Pipeline, PipelineConfig
from keylogix.status import Result, Status


def test_frozen_immutability():
    field = OptionalField.observed("val", "test")
    with pytest.raises(FrozenInstanceError):
        field.value = "new_val"  # type: ignore

    mod = ModifierState.unknown()
    with pytest.raises(FrozenInstanceError):
        mod.shift = True  # type: ignore


def test_extreme_and_unicode_inputs():
    # Long unicode window title
    unicode_title = "研究ウィンドウ 🚀 — KeyLogix — \u2603 \U0001F600" * 20
    field = OptionalField.observed(unicode_title, "synthetic")
    assert field.value == unicode_title

    raw = RawObservation(
        event_id="unicode-evt-1",
        timestamp="2026-09-18T12:00:00.123456Z",
        event_type="KEY_DOWN",
        key_code=65,
        key_label=OptionalField.derived("A", "vk_table"),
        modifier_state=ModifierState.unknown(),
        application=OptionalField.observed("テスト.exe", "test"),
        window_title=field,
        session_id="session-unicode",
        source="synthetic",
        monotonic_ns=999999999999999,
        clock_source="synthetic",
    )
    norm = Normalizer().normalize_one(raw)
    assert norm.ok is True
    assert norm.value.window_title.value == unicode_title


def test_adversarial_malformed_script_pipeline(tmp_path: Path):
    # Script containing malformed entries
    malformed_script = [
        "not_a_dict",
        {"action": "unknown_action"},
        {"action": "key", "key_code": "not_int", "event_type": "KEY_DOWN"},
        {"action": "key", "key_code": 65, "event_type": "INVALID_TYPE"},
        {"action": "delay", "ns": -500},
        {"action": "key", "key_code": 65, "event_type": "KEY_DOWN"},
        {"action": "key", "key_code": 65, "event_type": "KEY_UP"},
    ]
    source = SyntheticSource(script=malformed_script)
    pipe = Pipeline()
    config = PipelineConfig(
        experiment_id="EXP-ADVERSARIAL",
        output_dir=tmp_path / "adv_out",
        persist=True,
    )
    res = pipe.run(source, config)
    assert res.status == Status.PARTIAL
    # Valid key down and up are still processed and persisted!
    assert len(res.value.normalized) == 2
    assert len(res.value.failures) > 0


def test_repeated_pipeline_runs_state_isolation(tmp_path: Path):
    ids = IdentityFactory()
    source1 = SyntheticSource(
        script=[
            {"action": "key", "key_code": 65, "event_type": "KEY_DOWN"},
            {"action": "key", "key_code": 65, "event_type": "KEY_UP"},
        ],
        ids=ids,
    )
    source2 = SyntheticSource(
        script=[
            {"action": "key", "key_code": 66, "event_type": "KEY_DOWN"},
            {"action": "key", "key_code": 66, "event_type": "KEY_UP"},
        ],
        ids=ids,
    )
    pipe = Pipeline(ids=ids)

    res1 = pipe.run(source1, PipelineConfig("EXP-ISO-1", tmp_path / "run1", persist=True))
    assert res1.ok is True

    res2 = pipe.run(source2, PipelineConfig("EXP-ISO-2", tmp_path / "run2", persist=True))
    assert res2.ok is True

    # Ensure no ID collisions between runs
    ids_1 = {e.event_id for e in res1.value.normalized}
    ids_2 = {e.event_id for e in res2.value.normalized}
    assert len(ids_1.intersection(ids_2)) == 0
