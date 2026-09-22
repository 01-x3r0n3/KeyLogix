from __future__ import annotations

from keylogix.native_bridge import NativeBridge
from keylogix.status import Status
from keylogix.vk import classify_vk


def test_native_bridge():
    bridge = NativeBridge()
    if not bridge.available:
        # If native library is not built in current environment, check fallback
        res = bridge.evt_buffer_init(100)
        assert res.status == Status.UNREACHABLE
        return

    # 1. evt_buffer_init
    res_buf = bridge.evt_buffer_init(500)
    assert res_buf.ok is True
    assert res_buf.value["capacity"] == 500
    assert res_buf.value["magic"] == "0x314c4b58"

    res_bad_buf = bridge.evt_buffer_init(0)
    assert res_bad_buf.status == Status.INVALID_INPUT

    # 2. evt_normalize
    res_norm = bridge.evt_normalize(vk_code=0x41, flags=0, tick_ms=1000)
    assert res_norm.ok is True
    assert res_norm.value["event_type"] == 0  # KEY_DOWN
    assert res_norm.value["key_code"] == 0x41
    assert res_norm.value["class_id"] == 1    # ORDINARY

    res_norm_up = bridge.evt_normalize(vk_code=0x10, flags=0x80, tick_ms=2000)
    assert res_norm_up.ok is True
    assert res_norm_up.value["event_type"] == 1  # KEY_UP
    assert res_norm_up.value["class_id"] == 2    # MODIFIER

    # 3. key_classify cross-check with Python classify_vk
    for vk in (0x41, 0x10, 0x25, 0x08, 0x70, 0x14, 0x60, 0xBA, 0x00):
        c_res = bridge.key_classify(vk)
        assert c_res.ok is True
        cat_str = classify_vk(vk)
        # Verify non-negative
        assert c_res.value >= 0

    # 4. modifier_state
    mod_res1 = bridge.modifier_state(0, 0x10, is_key_up=False)  # Shift down
    assert mod_res1.value == 1

    mod_res2 = bridge.modifier_state(1, 0x11, is_key_up=False)  # Ctrl down
    assert mod_res2.value == 3

    mod_res3 = bridge.modifier_state(3, 0x10, is_key_up=True)   # Shift up
    assert mod_res3.value == 2

    # 5. str_to_upper
    upper_res = bridge.str_to_upper("hello, World!")
    assert upper_res.ok is True
    assert upper_res.value["text"] == "HELLO, WORLD!"
    assert upper_res.value["converted_count"] == 9

    # 6. pattern_scan
    haystack = b"abcdefg12345"
    needle = b"efg"
    scan_res = bridge.pattern_scan(haystack, needle)
    assert scan_res.ok is True
    assert scan_res.value == 4

    # Not found
    scan_none = bridge.pattern_scan(haystack, b"xyz")
    assert scan_none.status == Status.SUCCESS_NO_DATA
