from __future__ import annotations

import pytest
from keylogix.constants import (
    CAT_CONTROL,
    CAT_FUNCTION,
    CAT_LOCK,
    CAT_MODIFIER,
    CAT_NAVIGATION,
    CAT_NUMPAD,
    CAT_OEM,
    CAT_ORDINARY,
    CAT_UNKNOWN,
)
from keylogix.vk import (
    classify_vk,
    is_modifier_vk,
    known_vk_codes,
    label_for_vk,
    modifier_bit_for_vk,
)


def test_classify_vk_ordinary():
    assert classify_vk(0x41) == CAT_ORDINARY  # 'A'
    assert classify_vk(0x5A) == CAT_ORDINARY  # 'Z'
    assert classify_vk(0x30) == CAT_ORDINARY  # '0'
    assert classify_vk(0x39) == CAT_ORDINARY  # '9'
    assert classify_vk(0x20) == CAT_ORDINARY  # Space


def test_classify_vk_modifier():
    assert classify_vk(0x10) == CAT_MODIFIER  # Shift
    assert classify_vk(0x11) == CAT_MODIFIER  # Ctrl
    assert classify_vk(0x12) == CAT_MODIFIER  # Alt
    assert classify_vk(0x5B) == CAT_MODIFIER  # LWin
    assert classify_vk(0x5C) == CAT_MODIFIER  # RWin
    assert classify_vk(0xA0) == CAT_MODIFIER  # LShift
    assert classify_vk(0xA5) == CAT_MODIFIER  # RAlt


def test_classify_vk_navigation():
    assert classify_vk(0x21) == CAT_NAVIGATION  # PageUp
    assert classify_vk(0x22) == CAT_NAVIGATION  # PageDown
    assert classify_vk(0x25) == CAT_NAVIGATION  # Left
    assert classify_vk(0x28) == CAT_NAVIGATION  # Down


def test_classify_vk_control():
    assert classify_vk(0x08) == CAT_CONTROL  # Backspace
    assert classify_vk(0x09) == CAT_CONTROL  # Tab
    assert classify_vk(0x0D) == CAT_CONTROL  # Return
    assert classify_vk(0x1B) == CAT_CONTROL  # Escape
    assert classify_vk(0x5D) == CAT_CONTROL  # Apps


def test_classify_vk_function():
    assert classify_vk(0x70) == CAT_FUNCTION  # F1
    assert classify_vk(0x7B) == CAT_FUNCTION  # F12
    assert classify_vk(0x87) == CAT_FUNCTION  # F24


def test_classify_vk_locks_numpad_oem():
    assert classify_vk(0x14) == CAT_LOCK    # CapsLock
    assert classify_vk(0x90) == CAT_LOCK    # NumLock
    assert classify_vk(0x60) == CAT_NUMPAD  # NumPad0
    assert classify_vk(0x69) == CAT_NUMPAD  # NumPad9
    assert classify_vk(0xBA) == CAT_OEM     # Oem1
    assert classify_vk(0xE2) == CAT_OEM     # Oem102


def test_classify_vk_unknown_and_invalid():
    assert classify_vk(0x00) == CAT_UNKNOWN
    assert classify_vk(0xFF) == CAT_UNKNOWN
    assert classify_vk(-1) == CAT_UNKNOWN
    assert classify_vk(256) == CAT_UNKNOWN
    assert classify_vk("not_int") == CAT_UNKNOWN  # type: ignore


def test_label_for_vk():
    assert label_for_vk(0x41) == "A"
    assert label_for_vk(0x30) == "0"
    assert label_for_vk(0x20) == "Space"
    assert label_for_vk(0x10) == "Shift"
    assert label_for_vk(0x0D) == "Return"
    assert label_for_vk(0x70) == "F1"
    assert label_for_vk(0x00) is None
    assert label_for_vk(999) is None
    assert label_for_vk(-5) is None


def test_modifier_helpers():
    assert is_modifier_vk(0x10) is True
    assert is_modifier_vk(0xA0) is True
    assert is_modifier_vk(0x41) is False

    assert modifier_bit_for_vk(0x10) == 1
    assert modifier_bit_for_vk(0xA0) == 1
    assert modifier_bit_for_vk(0x11) == 2
    assert modifier_bit_for_vk(0x12) == 4
    assert modifier_bit_for_vk(0x5B) == 8
    assert modifier_bit_for_vk(0x41) == 0


def test_known_vk_codes():
    codes = known_vk_codes()
    assert isinstance(codes, tuple)
    assert len(codes) > 50
    assert all(0 <= c <= 255 for c in codes)
    assert sorted(codes) == list(codes)
