from __future__ import annotations

import string
import pytest
from keylogix.constants import CATEGORY_IDS, CAT_UNKNOWN
from keylogix.native_bridge import NativeBridge
from keylogix.vk import classify_vk, is_modifier_vk, modifier_bit_for_vk


def test_differential_key_classify_all_256_vk_codes():
    bridge = NativeBridge()
    if not bridge.available:
        pytest.skip("Native library not available on host")

    for vk in range(256):
        py_cat_str = classify_vk(vk)
        expected_cat_id = CATEGORY_IDS.get(py_cat_str, 0)

        c_res = bridge.key_classify(vk)
        assert c_res.ok is True, f"key_classify failed for VK 0x{vk:02X}"
        assert c_res.value == expected_cat_id, (
            f"Classification mismatch for VK 0x{vk:02X}: Python gave '{py_cat_str}' (ID {expected_cat_id}), "
            f"C gave ID {c_res.value}"
        )


def test_differential_modifier_state():
    bridge = NativeBridge()
    if not bridge.available:
        pytest.skip("Native library not available on host")

    # Test all combinations of 4-bit prior state and modifier VKs
    modifier_vks = [0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5]
    for prior in range(16):
        for vk in modifier_vks:
            bit = modifier_bit_for_vk(vk)
            # Key Down (is_key_up = False)
            expected_down = prior | bit
            res_down = bridge.modifier_state(prior, vk, is_key_up=False)
            assert res_down.value == expected_down, (
                f"Modifier down mismatch for prior {prior}, VK 0x{vk:02X}: expected {expected_down}, got {res_down.value}"
            )

            # Key Up (is_key_up = True)
            expected_up = prior & ~bit
            res_up = bridge.modifier_state(prior, vk, is_key_up=True)
            assert res_up.value == expected_up, (
                f"Modifier up mismatch for prior {prior}, VK 0x{vk:02X}: expected {expected_up}, got {res_up.value}"
            )


def test_differential_str_to_upper():
    bridge = NativeBridge()
    if not bridge.available:
        pytest.skip("Native library not available on host")

    test_strings = [
        "",
        "abc",
        "ABC",
        "Hello World 123 !@#",
        "The Quick Brown Fox Jumps Over The Lazy Dog",
        "mixed 123 CASE with symbols -- ++ __",
    ]
    for text in test_strings:
        py_upper = text.upper()
        # Count lowercase letters in input
        expected_converted = sum(1 for c in text if 'a' <= c <= 'z')
        c_res = bridge.str_to_upper(text)
        assert c_res.ok is True
        assert c_res.value["text"] == py_upper
        assert c_res.value["converted_count"] == expected_converted


def test_differential_pattern_scan():
    bridge = NativeBridge()
    if not bridge.available:
        pytest.skip("Native library not available on host")

    haystack = b"KeyLogix-Research-Pipeline-Laboratory-Data-2026"
    test_cases = [
        (b"KeyLogix", 0),
        (b"Research", 9),
        (b"2026", len(haystack) - 4),
        (b"NotFoundPattern", -1),
    ]
    for needle, expected_idx in test_cases:
        res = bridge.pattern_scan(haystack, needle)
        if expected_idx == -1:
            assert res.status.value == "SUCCESS_NO_DATA"
        else:
            assert res.ok is True
            assert res.value == expected_idx
