# KeyLogix — Native ABI

Status: implemented as specified here for v0.1.0.

Target for NASM: Windows 7 SP1, x86, cdecl.

Analysis-host tests execute the **C reference** (`native/c/keylogix_ref.c`)
which implements the same signatures and semantics. NASM is assembled to
`win32` objects to verify syntax and exported symbols. Execution of NASM
on Windows is a laboratory procedure, not an analysis-host claim.

---

## Calling convention

* NASM: `BITS 32`, cdecl (caller cleans the stack).
* Arguments on the stack: `[ebp+8]` is the first argument.
* Return value in `eax`.
* Callee-saved: `ebx`, `esi`, `edi`, `ebp`. `eax`, `ecx`, `edx` scratch.
* No floating point.
* Little-endian.

C reference: the same signatures, compiled for the host (`x86_64` Linux
in the current development environment) as a shared library and as a
statically linked test harness.

---

## Error codes

```text
KLX_OK                 0
KLX_ERR_NULL          -1
KLX_ERR_INVALID       -2
KLX_ERR_NOSPACE       -3
KLX_ERR_OVERFLOW      -4
KLX_ERR_MAGIC         -5
KLX_NOT_FOUND         -1   /* pattern_scan only, when inputs are valid */
```

`pattern_scan` uses `-1` for “valid input, not found” and `-2` for invalid
input so callers must check invalid first (null pointers, zero-length
needle).

---

## Structures

All packed, little-endian, no implicit padding.

```c
#define KLX_BUF_MAGIC 0x314C4B58u  /* 'XKL1' */

typedef struct {
    uint32_t magic;      /* KLX_BUF_MAGIC after init */
    uint32_t capacity;   /* caller-provided max records */
    uint32_t count;      /* set to 0 by init */
    uint32_t rec_size;   /* sizeof(EvtRawPacked) = 20 */
} EvtBufferHeader;       /* 16 bytes */

typedef struct {
    uint32_t vk_code;
    uint32_t scan_code;
    uint32_t flags;      /* LLKHF_* compatible; bit 7 = up */
    uint32_t extra;
    uint32_t tick_ms;
} EvtRawPacked;          /* 20 bytes */

typedef struct {
    uint32_t event_type;     /* 0 = KEY_DOWN, 1 = KEY_UP */
    uint32_t key_code;
    uint32_t modifier_bits;  /* 0; native normalize does not invent modifiers */
    uint32_t tick_ms;
    uint32_t class_id;       /* key_classify(vk_code) */
} EvtNormPacked;             /* 20 bytes */
```

---

## Functions

### `int32_t evt_buffer_init(void *dest, uint32_t capacity);`

Writes `EvtBufferHeader` at `dest`. Does not allocate. Does not touch
memory beyond 16 bytes.

* `dest == NULL` → `-1`
* `capacity == 0` or `capacity > 1000000` → `-2`
* else magic, capacity, count=0, rec_size=20 → `0`

### `int32_t evt_normalize(const EvtRawPacked *src, EvtNormPacked *dst);`

Stateless numeric normalize. Does not fabricate labels, context, or
modifier snapshots.

* null `src` or `dst` → `-1`
* `event_type` = 1 iff `src->flags & 0x80` (LLKHF_UP), else 0
* `key_code` = `src->vk_code` (copied even if >255; classification then
  yields UNKNOWN)
* `modifier_bits` = 0
* `tick_ms` copied
* `class_id` = `key_classify(src->vk_code)` if vk ≤ 255 else 0

### `int32_t key_classify(uint32_t vk_code);`

Returns category id:

```text
0 unknown
1 ordinary
2 modifier
3 navigation
4 control
5 function
6 lock
7 numpad
8 oem
```

Rules match `docs/DECISIONS.md` D18 and `keylogix.vk.classify_vk`.
`vk_code > 255` → `0`. Never returns negative.

### `int32_t modifier_state(uint32_t prior_state, uint32_t vk_code, uint32_t is_key_up);`

Updates a modifier bitfield.

Bits: Shift=1, Ctrl=2, Alt=4, Win=8.

Modifier VKs: `0x10,0xA0,0xA1` Shift; `0x11,0xA2,0xA3` Ctrl;
`0x12,0xA4,0xA5` Alt; `0x5B,0x5C` Win.

Non-modifier VK: returns `prior_state & 0xF`.
`is_key_up == 0`: set bit. else: clear bit.
`prior_state` is masked to 4 bits.

### `int32_t str_to_upper(char *s, uint32_t len);`

ASCII `a`–`z` → `A`–`Z` in place, up to `len` bytes or a NUL, whichever
first. Other bytes unchanged.

* `s == NULL` → `-1`
* `len == 0` → `0`
* else returns count of letters actually converted

### `int32_t pattern_scan(const uint8_t *haystack, uint32_t hay_len, const uint8_t *needle, uint32_t needle_len);`

Naive first-match search.

* null pointer with positive length → `-2`
* `needle_len == 0` → `-2` (invalid; not “match at 0”)
* not found → `-1`
* found → starting index `0 .. hay_len - needle_len`

---

## Memory ownership

Caller allocates all buffers. Routines do not `malloc` or `free`.
`str_to_upper` mutates the caller buffer. Other routines do not mutate
inputs.

---

## Thread safety

Routines are pure with respect to global state (none). Concurrent use on
distinct buffers is safe. Concurrent `str_to_upper` on the same buffer is
not.
