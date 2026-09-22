from __future__ import annotations

from keylogix.constants import (
    EVENT_KEY_DOWN,
    EVENT_KEY_UP,
    KIND_RAW,
    LLKHF_UP,
    RAW_WM_KEYDOWN,
    RAW_WM_KEYUP,
    SOURCE_SYNTHETIC,
)
from keylogix.model import (
    ModifierState,
    OptionalField,
    Provenance,
    RawObservation,
)
from keylogix.normalize import Normalizer
from keylogix.status import Status


def make_raw(
    event_id: str = "r1",
    vk_code: int = 0x41,
    event_type: str = EVENT_KEY_DOWN,
    flags: int = 0,
    timestamp: str = "2026-09-18T12:00:00.000000Z",
    monotonic_ns: int = 1000,
    mod_state: ModifierState = ModifierState.unknown(),
) -> RawObservation:
    return RawObservation(
        event_id=event_id,
        timestamp=timestamp,
        event_type=event_type,
        key_code=vk_code,
        key_label=OptionalField.unavailable(),
        modifier_state=mod_state,
        application=OptionalField.unavailable(),
        window_title=OptionalField.unavailable(),
        session_id="s1",
        source=SOURCE_SYNTHETIC,
        monotonic_ns=monotonic_ns,
        clock_source="synthetic",
        flags=flags,
    )


def test_normalizer_single_valid():
    norm = Normalizer()
    raw = make_raw(vk_code=0x41)
    res = norm.normalize_one(raw)
    assert res.ok is True
    event = res.value
    assert event.event_id == "r1"
    assert event.key_code == 0x41
    assert event.key_label.value == "A"
    assert event.event_type == EVENT_KEY_DOWN


def test_normalizer_flag_and_raw_message_mapping():
    norm = Normalizer()
    raw_wm = RawObservation(
        event_id="r2",
        timestamp="2026-09-18T12:00:00.000000Z",
        event_type="",
        event_type_raw=RAW_WM_KEYUP,
        key_code=0x42,
        key_label=OptionalField.unavailable(),
        modifier_state=ModifierState.unknown(),
        application=OptionalField.unavailable(),
        window_title=OptionalField.unavailable(),
        session_id="s1",
        source=SOURCE_SYNTHETIC,
        monotonic_ns=2000,
        clock_source="synthetic",
    )
    res = norm.normalize_one(raw_wm)
    assert res.ok is True
    assert res.value.event_type == EVENT_KEY_UP

    raw_flags = RawObservation(
        event_id="r3",
        timestamp="2026-09-18T12:00:00.000000Z",
        event_type="",
        key_code=0x43,
        key_label=OptionalField.unavailable(),
        modifier_state=ModifierState.unknown(),
        application=OptionalField.unavailable(),
        window_title=OptionalField.unavailable(),
        session_id="s1",
        source=SOURCE_SYNTHETIC,
        monotonic_ns=3000,
        clock_source="synthetic",
        flags=LLKHF_UP,
    )
    res = norm.normalize_one(raw_flags)
    assert res.ok is True
    assert res.value.event_type == EVENT_KEY_UP


def test_normalizer_invalid_inputs():
    norm = Normalizer()

    # Invalid timestamp
    bad_time = make_raw(timestamp="invalid-time")
    assert norm.normalize_one(bad_time).status == Status.INVALID_INPUT

    # Missing key code
    bad_key = RawObservation(
        event_id="r4",
        timestamp="2026-09-18T12:00:00.000000Z",
        event_type=EVENT_KEY_DOWN,
        key_code=None,
        key_label=OptionalField.unavailable(),
        modifier_state=ModifierState.unknown(),
        application=OptionalField.unavailable(),
        window_title=OptionalField.unavailable(),
        session_id="s1",
        source=SOURCE_SYNTHETIC,
        monotonic_ns=1000,
        clock_source="synthetic",
    )
    assert norm.normalize_one(bad_key).status == Status.INVALID_INPUT

    # Out of range key code
    out_of_range = make_raw(vk_code=999)
    assert norm.normalize_one(out_of_range).status == Status.INVALID_INPUT


def test_normalizer_modifier_tracking():
    norm = Normalizer()
    # Shift down
    r_shift_dn = make_raw(event_id="m1", vk_code=0x10, event_type=EVENT_KEY_DOWN)
    res1 = norm.normalize_one(r_shift_dn)
    assert res1.value.modifier_state.shift is True
    assert res1.value.modifier_state.encoding == 1

    # 'A' down while shift is held
    r_a_dn = make_raw(event_id="m2", vk_code=0x41, event_type=EVENT_KEY_DOWN)
    res2 = norm.normalize_one(r_a_dn)
    assert res2.value.modifier_state.shift is True
    assert res2.value.modifier_state.encoding == 1

    # Shift up
    r_shift_up = make_raw(event_id="m3", vk_code=0x10, event_type=EVENT_KEY_UP)
    res3 = norm.normalize_one(r_shift_up)
    assert res3.value.modifier_state.shift is False
    assert res3.value.modifier_state.encoding == 0


def test_normalizer_batch():
    norm = Normalizer()
    raws = [make_raw(event_id=f"r{i}", vk_code=65 + i) for i in range(5)]
    res = norm.normalize_many(raws)
    assert res.ok is True
    assert len(res.value) == 5

    # Batch with invalid raw
    raws_mixed = [make_raw(event_id="ok", vk_code=65), make_raw(event_id="bad", vk_code=999)]
    res_mixed = norm.normalize_many(raws_mixed)
    assert res_mixed.status == Status.PARTIAL
    assert len(res_mixed.value) == 1
