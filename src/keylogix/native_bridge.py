"""Native bridge: ctypes wrapper for the C reference ABI library.

Optional layer used for cross-checking research routines against the C reference.
"""

from __future__ import annotations

import ctypes
from pathlib import Path
from typing import Optional, Tuple, Union

from keylogix.constants import (
    KLX_BUF_MAGIC,
    KLX_ERR_INVALID,
    KLX_ERR_MAGIC,
    KLX_ERR_NOSPACE,
    KLX_ERR_NULL,
    KLX_ERR_OVERFLOW,
    KLX_OK,
)
from keylogix.status import Result, Status


class EvtBufferHeader(ctypes.Structure):
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("capacity", ctypes.c_uint32),
        ("count", ctypes.c_uint32),
        ("rec_size", ctypes.c_uint32),
    ]


class EvtRawPacked(ctypes.Structure):
    _fields_ = [
        ("vk_code", ctypes.c_uint32),
        ("scan_code", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("extra", ctypes.c_uint32),
        ("tick_ms", ctypes.c_uint32),
    ]


class EvtNormPacked(ctypes.Structure):
    _fields_ = [
        ("event_type", ctypes.c_uint32),
        ("key_code", ctypes.c_uint32),
        ("modifier_bits", ctypes.c_uint32),
        ("tick_ms", ctypes.c_uint32),
        ("class_id", ctypes.c_uint32),
    ]


def find_native_library(path: Optional[Union[str, Path]] = None) -> Optional[Path]:
    if path:
        p = Path(path)
        if p.is_file():
            return p
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / "native" / "build" / "libkeylogix_ref.so",
        root / "native" / "build" / "libkeylogix_ref.dll",
        root / "native" / "libkeylogix_ref.so",
        root / "native" / "libkeylogix_ref.dll",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


class NativeBridge:
    def __init__(self, lib_path: Optional[Union[str, Path]] = None) -> None:
        self.lib_path = find_native_library(lib_path)
        self._lib: Optional[ctypes.CDLL] = None
        if self.lib_path:
            try:
                self._lib = ctypes.CDLL(str(self.lib_path))
                self._bind()
            except OSError:
                self._lib = None

    @property
    def available(self) -> bool:
        return self._lib is not None

    def _bind(self) -> None:
        if not self._lib:
            return

        # int32_t evt_buffer_init(void *dest, uint32_t capacity)
        self._lib.evt_buffer_init.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self._lib.evt_buffer_init.restype = ctypes.c_int32

        # int32_t evt_normalize(const EvtRawPacked *src, EvtNormPacked *dst)
        self._lib.evt_normalize.argtypes = [
            ctypes.POINTER(EvtRawPacked),
            ctypes.POINTER(EvtNormPacked),
        ]
        self._lib.evt_normalize.restype = ctypes.c_int32

        # int32_t key_classify(uint32_t vk_code)
        self._lib.key_classify.argtypes = [ctypes.c_uint32]
        self._lib.key_classify.restype = ctypes.c_int32

        # int32_t modifier_state(uint32_t prior_state, uint32_t vk_code, uint32_t is_key_up)
        self._lib.modifier_state.argtypes = [
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]
        self._lib.modifier_state.restype = ctypes.c_int32

        # int32_t str_to_upper(char *s, uint32_t len)
        self._lib.str_to_upper.argtypes = [ctypes.c_char_p, ctypes.c_uint32]
        self._lib.str_to_upper.restype = ctypes.c_int32

        # int32_t pattern_scan(const uint8_t *haystack, uint32_t hay_len, const uint8_t *needle, uint32_t needle_len)
        self._lib.pattern_scan.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint32,
        ]
        self._lib.pattern_scan.restype = ctypes.c_int32

    def evt_buffer_init(self, capacity: int) -> Result:
        if not self.available:
            return Result.failure(Status.UNREACHABLE, "native library unavailable")
        header = EvtBufferHeader()
        ptr = ctypes.cast(ctypes.byref(header), ctypes.c_void_p)
        rc = self._lib.evt_buffer_init(ptr, capacity)  # type: ignore[union-attr]
        if rc != KLX_OK:
            return Result.failure(Status.INVALID_INPUT, f"evt_buffer_init error code: {rc}", details={"rc": rc})
        return Result.success({
            "magic": hex(header.magic),
            "capacity": header.capacity,
            "count": header.count,
            "rec_size": header.rec_size,
        })

    def evt_normalize(
        self,
        vk_code: int,
        scan_code: int = 0,
        flags: int = 0,
        extra: int = 0,
        tick_ms: int = 0,
    ) -> Result:
        if not self.available:
            return Result.failure(Status.UNREACHABLE, "native library unavailable")
        src = EvtRawPacked(
            vk_code=vk_code,
            scan_code=scan_code,
            flags=flags,
            extra=extra,
            tick_ms=tick_ms,
        )
        dst = EvtNormPacked()
        rc = self._lib.evt_normalize(ctypes.byref(src), ctypes.byref(dst))  # type: ignore[union-attr]
        if rc != KLX_OK:
            return Result.failure(Status.INVALID_INPUT, f"evt_normalize error code: {rc}", details={"rc": rc})
        return Result.success({
            "event_type": dst.event_type,
            "key_code": dst.key_code,
            "modifier_bits": dst.modifier_bits,
            "tick_ms": dst.tick_ms,
            "class_id": dst.class_id,
        })

    def key_classify(self, vk_code: int) -> Result:
        if not self.available:
            return Result.failure(Status.UNREACHABLE, "native library unavailable")
        cat_id = self._lib.key_classify(vk_code)  # type: ignore[union-attr]
        return Result.success(cat_id)

    def modifier_state(self, prior_state: int, vk_code: int, is_key_up: bool) -> Result:
        if not self.available:
            return Result.failure(Status.UNREACHABLE, "native library unavailable")
        res = self._lib.modifier_state(prior_state, vk_code, 1 if is_key_up else 0)  # type: ignore[union-attr]
        return Result.success(res)

    def str_to_upper(self, text: str) -> Result:
        if not self.available:
            return Result.failure(Status.UNREACHABLE, "native library unavailable")
        encoded = text.encode("latin-1", errors="replace")
        buf = ctypes.create_string_buffer(encoded)
        converted = self._lib.str_to_upper(buf, len(encoded))  # type: ignore[union-attr]
        if converted < 0:
            return Result.failure(Status.INVALID_INPUT, f"str_to_upper error: {converted}")
        return Result.success({
            "text": buf.value.decode("latin-1", errors="replace"),
            "converted_count": converted,
        })

    def pattern_scan(self, haystack: bytes, needle: bytes) -> Result:
        if not self.available:
            return Result.failure(Status.UNREACHABLE, "native library unavailable")
        if len(needle) == 0:
            return Result.failure(Status.INVALID_INPUT, "needle cannot be empty")
        h_arr = (ctypes.c_uint8 * len(haystack))(*haystack) if haystack else None
        n_arr = (ctypes.c_uint8 * len(needle))(*needle)
        h_ptr = ctypes.cast(h_arr, ctypes.POINTER(ctypes.c_uint8)) if h_arr else None
        n_ptr = ctypes.cast(n_arr, ctypes.POINTER(ctypes.c_uint8))
        idx = self._lib.pattern_scan(h_ptr, len(haystack), n_ptr, len(needle))  # type: ignore[union-attr]
        if idx == -2:
            return Result.failure(Status.INVALID_INPUT, "pattern_scan: invalid arguments")
        if idx == -1:
            return Result.no_data("pattern not found")
        return Result.success(idx)
