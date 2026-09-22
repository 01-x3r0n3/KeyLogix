"""Win32 virtual-key tables.

Labels name keys, not produced characters. Layout translation is out of
scope for v0.1.0. Category rules match docs/DECISIONS.md D18 and the
native ABI.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

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

# (label, category) — only keys we claim to know.
_VK: Dict[int, Tuple[str, str]] = {}


def _put(code: int, label: str, category: str) -> None:
    _VK[code] = (label, category)


def _init() -> None:
    if _VK:
        return
    for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        _put(0x41 + i, ch, CAT_ORDINARY)
    for i in range(10):
        _put(0x30 + i, str(i), CAT_ORDINARY)
    _put(0x20, "Space", CAT_ORDINARY)

    _put(0x10, "Shift", CAT_MODIFIER)
    _put(0x11, "Ctrl", CAT_MODIFIER)
    _put(0x12, "Alt", CAT_MODIFIER)
    _put(0x5B, "LWin", CAT_MODIFIER)
    _put(0x5C, "RWin", CAT_MODIFIER)
    _put(0xA0, "LShift", CAT_MODIFIER)
    _put(0xA1, "RShift", CAT_MODIFIER)
    _put(0xA2, "LCtrl", CAT_MODIFIER)
    _put(0xA3, "RCtrl", CAT_MODIFIER)
    _put(0xA4, "LAlt", CAT_MODIFIER)
    _put(0xA5, "RAlt", CAT_MODIFIER)

    _put(0x14, "CapsLock", CAT_LOCK)
    _put(0x90, "NumLock", CAT_LOCK)
    _put(0x91, "ScrollLock", CAT_LOCK)

    _put(0x21, "PageUp", CAT_NAVIGATION)
    _put(0x22, "PageDown", CAT_NAVIGATION)
    _put(0x23, "End", CAT_NAVIGATION)
    _put(0x24, "Home", CAT_NAVIGATION)
    _put(0x25, "Left", CAT_NAVIGATION)
    _put(0x26, "Up", CAT_NAVIGATION)
    _put(0x27, "Right", CAT_NAVIGATION)
    _put(0x28, "Down", CAT_NAVIGATION)

    _put(0x08, "Backspace", CAT_CONTROL)
    _put(0x09, "Tab", CAT_CONTROL)
    _put(0x0D, "Return", CAT_CONTROL)
    _put(0x1B, "Escape", CAT_CONTROL)
    _put(0x13, "Pause", CAT_CONTROL)
    _put(0x2C, "PrintScreen", CAT_CONTROL)
    _put(0x2D, "Insert", CAT_CONTROL)
    _put(0x2E, "Delete", CAT_CONTROL)

    for i in range(24):
        _put(0x70 + i, "F{0}".format(i + 1), CAT_FUNCTION)

    names = [
        "NumPad0",
        "NumPad1",
        "NumPad2",
        "NumPad3",
        "NumPad4",
        "NumPad5",
        "NumPad6",
        "NumPad7",
        "NumPad8",
        "NumPad9",
        "NumPadMultiply",
        "NumPadAdd",
        "NumPadSeparator",
        "NumPadSubtract",
        "NumPadDecimal",
        "NumPadDivide",
    ]
    for i, name in enumerate(names):
        _put(0x60 + i, name, CAT_NUMPAD)

    oem = {
        0xBA: "Oem1",
        0xBB: "OemPlus",
        0xBC: "OemComma",
        0xBD: "OemMinus",
        0xBE: "OemPeriod",
        0xBF: "Oem2",
        0xC0: "Oem3",
        0xDB: "Oem4",
        0xDC: "Oem5",
        0xDD: "Oem6",
        0xDE: "Oem7",
        0xDF: "Oem8",
        0xE2: "Oem102",
    }
    for code, label in oem.items():
        _put(code, label, CAT_OEM)

    _put(0x5D, "Apps", CAT_CONTROL)
    _put(0x03, "Cancel", CAT_CONTROL)
    _put(0x0C, "Clear", CAT_CONTROL)


_init()

_MODIFIER_VKS = frozenset(
    {0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5}
)
_NAV_VKS = frozenset({0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28})
_CTRL_VKS = frozenset({0x08, 0x09, 0x0D, 0x1B, 0x2C, 0x2D, 0x2E, 0x13})
_LOCK_VKS = frozenset({0x14, 0x90, 0x91})
_OEM_VKS = frozenset(
    {0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF, 0xC0, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF, 0xE2}
)


def classify_vk(vk_code: int) -> str:
    """Deterministic category. Unknown is a category, not an exception."""
    if not isinstance(vk_code, int) or vk_code < 0 or vk_code > 255:
        return CAT_UNKNOWN
    if vk_code in _MODIFIER_VKS:
        return CAT_MODIFIER
    if vk_code in _LOCK_VKS:
        return CAT_LOCK
    if vk_code in _NAV_VKS:
        return CAT_NAVIGATION
    if vk_code in _CTRL_VKS:
        return CAT_CONTROL
    if 0x70 <= vk_code <= 0x87:
        return CAT_FUNCTION
    if 0x60 <= vk_code <= 0x6F:
        return CAT_NUMPAD
    if vk_code == 0x20 or (0x30 <= vk_code <= 0x39) or (0x41 <= vk_code <= 0x5A):
        return CAT_ORDINARY
    if vk_code in _OEM_VKS:
        return CAT_OEM
    # Remaining labelled keys (Apps, Cancel, Clear) fall through to table.
    if vk_code in _VK:
        return _VK[vk_code][1]
    return CAT_UNKNOWN


def label_for_vk(vk_code: int) -> Optional[str]:
    if not isinstance(vk_code, int) or vk_code < 0 or vk_code > 255:
        return None
    entry = _VK.get(vk_code)
    if entry is None:
        return None
    return entry[0]


def is_modifier_vk(vk_code: int) -> bool:
    return vk_code in _MODIFIER_VKS


def modifier_bit_for_vk(vk_code: int) -> int:
    if vk_code in (0x10, 0xA0, 0xA1):
        return 1
    if vk_code in (0x11, 0xA2, 0xA3):
        return 2
    if vk_code in (0x12, 0xA4, 0xA5):
        return 4
    if vk_code in (0x5B, 0x5C):
        return 8
    return 0


def known_vk_codes() -> Tuple[int, ...]:
    return tuple(sorted(_VK.keys()))
