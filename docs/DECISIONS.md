# KeyLogix — Design Decisions

This document records implementation-level decisions for items that
`docs/SPECIFICATION.md` marked TBD. These decisions are binding for the
current implementation (v0.1.0) unless the specification is updated.

Decisions are conservative: they exist so the system can be implemented,
tested, and reproduced. They are not a license to expand scope.

---

## D1. Source-tree architecture

```text
KeyLogix/
  src/keylogix/          Python research pipeline (canonical high-level implementation)
  native/                C ABI, NASM research routines, Win32 observer
  tests/                 pytest suite (analysis-host executable)
  experiments/           experiment definitions (JSON)
  scripts/               build and reproducibility helpers
  docs/                  specification, architecture, decisions, status
  output/                generated artifacts (gitignored)
```

Rationale: the specification names Python for orchestration/analysis and
NASM/Win32 for low-level research. The pipeline must be testable on the
analysis host without a Windows kernel. Native code is isolated behind a
documented ABI and a file-based observation contract (JSONL).

---

## D2. Module boundaries

| Component | Location | Responsibility |
|-----------|----------|----------------|
| Observation | `keylogix.observation` | Produce raw observations or an explicit failure status |
| Normalization | `keylogix.normalize` | Raw → normalized event; no fabrication |
| Context | `keylogix.context` | Validate/associate application/window/session context |
| Classification | `keylogix.classify` | Deterministic key taxonomy; heuristic sequence labels |
| Behavioral analysis | `keylogix.analysis` | Measured sequence metrics + labeled conclusions |
| Observability | `keylogix.observability` | Record artifacts/telemetry about the run itself |
| Evidence | `keylogix.evidence` | Provenance-preserving research records |
| Experiment | `keylogix.experiment` | Controlled run lifecycle and schema |
| Report | `keylogix.report` | Markdown rendering of what was actually measured |
| Pipeline | `keylogix.pipeline` | Orchestration only; no domain logic of its own |
| Persistence | `keylogix.persist` | JSON/JSONL filesystem store under `output/` |
| Native ABI | `native/include/keylogix_abi.h` | C ABI for research routines |
| Win32 observer | `native/win32/observer.c` | Laboratory WH_KEYBOARD_LL capture → JSONL |

---

## D3. Language and runtime

* Python 3.8+ for the pipeline (Windows 7 laboratory constraint).
* C11 for the ABI reference implementation and Win32 observer.
* NASM, `BITS 32`, cdecl, for Windows 7 x86 research routines.
* No runtime Python dependencies. `pytest` is a development dependency.
* The Python pipeline does not require native libraries to operate.

---

## D4. Event identity

* `event_id` is a UUID version 4 string (canonical 8-4-4-4-12 hex form).
* Uniqueness is required within a research dataset. The identity factory
  records issued IDs for the process and rejects collisions.
* Normalized events **reuse** the originating raw observation's `event_id`.
  The keyboard event is the identity; later records point at it.
* Derived records (classification, evidence, analysis) have a distinct
  `record_id` (also UUID4) and cite `event_id` / parent IDs in provenance.
* Tests inject a deterministic ID factory. Production uses `uuid.uuid4`.

---

## D5. Timestamp and clock

* Canonical wall-clock field: `timestamp` as UTC ISO-8601 with microsecond
  precision and `Z` suffix, e.g. `2026-09-18T12:34:56.123456Z`.
* Additional implementation field `monotonic_ns` (int) is used for interval
  math. It is **not** semantic identity.
* Clock sources (recorded on every raw observation):
  * `synthetic_clock` — scripted, deterministic
  * `python_datetime_utc+perf_counter_ns` — analysis host default
  * `win32_filetime_utc+kbdll_tickms` — Win32 observer
* Win32 `KBDLLHOOKSTRUCT.time` is stored as `tick_ms` (milliseconds since
  boot). It is not treated as wall-clock time.
* Precision: microseconds for Python UTC; Windows FILETIME is 100 ns
  intervals converted to UTC microseconds.

---

## D6. Event type

Only:

```text
KEY_DOWN
KEY_UP
```

Win32 `WM_SYSKEYDOWN` / `WM_SYSKEYUP` normalize to `KEY_DOWN` / `KEY_UP`.
The original Win32 message is preserved on the raw observation as
`event_type_raw`. No other normalized event types are defined in v0.1.0.

---

## D7. Key code

* Normalized `key_code` is the Win32 virtual-key code as an integer
  (`0`–`255` inclusive).
* Raw observations may also carry `scan_code`, `flags`, and `extra_info`
  from `KBDLLHOOKSTRUCT` when the source provides them.
* A missing `key_code` cannot be normalized: the event is
  `INVALID_INPUT`, not a fabricated key.
* Values outside `0`–`255` are `INVALID_INPUT`.

---

## D8. Key label

* `key_label` is a deterministic VK→label table (see `keylogix.vk`).
* Labels name the **key**, not the produced character. `VK_A` is `"A"`
  regardless of Shift. Character/layout translation is **not implemented**.
* If the VK is not in the table, `key_label` is unavailable (not guessed).
  A derived fallback `VK_0xNN` is **not** written into `key_label`.
* Keyboard layout, dead keys, and `ToUnicode` are documented limitations.

---

## D9. Modifier state encoding

Structured fields plus a bitfield:

| Bit | Meaning |
|-----|---------|
| 0 | Shift |
| 1 | Ctrl |
| 2 | Alt |
| 3 | Win |

```text
encoding = shift*1 + ctrl*2 + alt*4 + win*8
```

`ModifierState.known` distinguishes “all modifiers false” from “modifier
state was not obtained”.

Origin values:

* `observed_snapshot` — source provided the snapshot
* `derived_tracking` — normalizer tracked modifier key-down/up
* `unknown` — not known; `known=False`; encoding 0 is not a claim

Modifier tracking rule: a modifier VK key-down sets the corresponding bit
for that event and subsequent events; a modifier VK key-up clears it
after being recorded as still down on the key-up event of that modifier
itself? **Decision:** the snapshot on an event is the state **after**
applying that event. Shift key-down has `shift=True`. Shift key-up has
`shift=False`.

Left/right modifiers collapse into the same bit (LShift and RShift both
set Shift). Distinct left/right identity remains in `key_code`/`key_label`.

---

## D10. Source vocabulary

```text
synthetic
win32_llhook
unknown
```

`replay` is an ingestion path, not an originating source. Replayed events
retain their original `source`. Provenance records `ingested_via=replay`.

---

## D11. Optional context fields

`application` and `window_title` use `OptionalField`:

```text
presence: observed | unavailable | not_applicable | derived
value: string or null
obtained_via: string or null
```

Rules:

* `unavailable` / `not_applicable` ⇒ `value` must be `null`
* `observed` / `derived` ⇒ `value` is a string (empty string allowed)
* Empty window title from the API is `observed` + `""`, not unavailable
* Missing context is never treated as malicious or as a fabricated name
* Observed context is never overwritten by derived context
* Conflicts are retained and recorded; nothing is silently dropped

---

## D12. Normalization rules

1. Assign/preserve `event_id` from the raw observation.
2. Normalize timestamp (UTC ISO-8601) from the raw timestamp; do not
   invent a timestamp if the raw record has none → `INVALID_INPUT`.
3. Map `event_type_raw` / LLKHF_UP to `KEY_DOWN` / `KEY_UP`.
4. Copy `key_code` if valid; otherwise fail that event.
5. Look up `key_label` (deterministic) or mark unavailable.
6. Apply modifier snapshot if provided; else derived tracking; else unknown.
7. Copy context fields with presence preserved.
8. Copy `session_id` and `source`.
9. Attach provenance `information_kind=normalized_observation`.

Normalization never fills application/window from guesses.

Stream-level result: all valid → `SUCCESS_WITH_DATA` (or `SUCCESS_NO_DATA`
if empty). Mix of valid and invalid → `PARTIAL` with both sets retained.

---

## D13. Native ABI / calling convention

See `docs/NATIVE_ABI.md`.

* i386 cdecl for NASM (Windows 7 x86 laboratory).
* C reference implementation of the same functions for analysis-host tests.
* Error codes: `0` success; negative for failure (`-1` null, `-2` invalid,
  `-3` buffer too small, `-4` overflow, `-5` bad magic).
* `key_classify` returns a non-negative category id; out-of-range VK →
  category `UNKNOWN` (0), not an error.

Python does not depend on these routines. They are isolated research
components with a C test harness.

---

## D14. Serialization and persistence

* Events and evidence: JSON Lines (UTF-8, one JSON object per line).
* Experiment manifests, analysis, observability, reports metadata: JSON.
* Reports: Markdown.
* Schema field: `schema` on every persisted object.
* Directory: `output/experiments/<experiment_id>/<run_id>/`.
* Writes are atomic where practical (temp file + rename).
* Persistence failure is `PROVIDER_FAILURE`, not success with empty data.
* No database. No network transport.

---

## D15. Session lifecycle

* A session has `session_id` (UUID4), `started_at`, `ended_at`, status.
* Observation sources are bound to one session.
* Shutdown: source `stop()` must be idempotent. Win32 observer unhooks
  and exits the message loop. In-flight events are flushed; incomplete
  last records are not treated as valid events.
* Restart: a new session_id is issued. Previous files are not appended
  unless an explicit replay/ingest path is used.

---

## D16. Observation buffering

* Python sources yield events in order; no shared mutable buffer across
  components.
* Win32 observer writes JSONL incrementally (line-buffered).
* Native `evt_buffer_init` initializes a header only; it is a research
  routine, not the observer's I/O path.
* The observer always calls `CallNextHookEx` (does not swallow input).

---

## D17. Hook lifecycle (Win32)

1. Parse CLI (`--output`, `--session`, `--duration-ms` optional).
2. Print a laboratory banner to stderr (intentional visibility).
3. Install `WH_KEYBOARD_LL` via `SetWindowsHookExW`.
4. Failure → non-zero exit, JSON error object on stderr,
   status semantically `PROVIDER_FAILURE`.
5. Run a message loop on the installing thread.
6. Shutdown on Ctrl+C, `WM_QUIT`, or duration elapsed: unhook, flush,
   exit 0 if any event was written else still 0 with a session summary
   recording count=0 (`SUCCESS_NO_DATA` at the Python ingest layer).

Callback ownership: the hook procedure is in the observer process, same
thread as the message loop. No injection into other processes.

---

## D18. Classification taxonomy

Deterministic per-key categories (from VK):

```text
unknown
ordinary
modifier
navigation
control
function
lock
numpad
oem
```

Heuristic sequence labels (never presented as certainty):

```text
empty
text_oriented
special_key_sequence
modifier_chord
mixed
```

Heuristic rule (documented, not a detector):

* `empty` — no key-down events
* `text_oriented` — ≥70% of key-downs are `ordinary` or `oem`
* `modifier_chord` — ≥1 modifier key-down and ≥1 non-modifier key-down
  with overlapping modifier state
* `special_key_sequence` — ≥70% of key-downs are navigation/control/function
* `mixed` — otherwise

Confidence: deterministic category `1.0`; heuristic labels `< 1.0`
(`0.7` for the thresholded rules above).

---

## D19. Behavioral analysis

Measured:

* counts (events, downs, ups)
* unmatched downs/ups (pairing by `key_code`, FIFO per code)
* duration from first to last `monotonic_ns`
* inter-arrival mean/median/p95
* events per second
* max consecutive repeat of the same `key_code` (key-downs)
* burst count
* context-change count
* modifier-event fraction
* ordinary-event fraction

Burst definition (research default, not malice):

* ≥5 key-down events with consecutive inter-arrival `< 50 ms`

Repeat-run definition:

* same `key_code` key-down ≥3 times with consecutive inter-arrival `< 100 ms`

Conclusions are objects with `kind` in
`measured | derived | inferred | hypothetical` and never claim intent.

---

## D20. Evidence schema

Each evidence record includes:

```text
schema
record_id
timestamp
source
information_kind
experiment_id
session_id
event_id          (nullable if not event-scoped)
parent_ids
observed          (object or null)
derived           (object or null)
classification    (object or null)
confidence        (number or null)
notes
```

An evidence record is not written for an observation that did not occur.

---

## D21. Experiment schema

See `docs/ARCHITECTURE.md` §Experiments. Required fields:

```text
experiment_id, objective, environment, implementation_version,
configuration, input, procedure, expected_observation,
actual_observation, telemetry, security_product_state,
result, limitations, status
```

`security_product_state.present` is explicit. If the product was not
measured, result text must not claim non-detection.

---

## D22. Failure semantics

Canonical statuses (specification names):

```text
SUCCESS_WITH_DATA
SUCCESS_NO_DATA
INVALID_INPUT
UNREACHABLE
TIMEOUT
PROVIDER_FAILURE
PARTIAL
INCONCLUSIVE
SKIPPED
INTERRUPTED
OUT_OF_SCOPE
UNAVAILABLE_CONTEXT
```

`UNAVAILABLE_CONTEXT` is retained from `CONTEXT.md` as a distinct state
from `UNREACHABLE`. It means context collection ran but the context was
not obtainable. `OUT_OF_SCOPE` covers `not_applicable`.

Win32 observer on non-Windows when explicitly requested: `SKIPPED`
(provider cannot operate on this OS). Missing observer binary on Windows:
`UNREACHABLE`. `SetWindowsHookEx` failure: `PROVIDER_FAILURE`.

---

## D23. Test architecture

* `pytest` on the analysis host.
* Python unit, boundary, integrity, failure, state, integration,
  adversarial tests — no Windows required.
* Native C harness linked to the C reference, executed on the analysis host.
* NASM assembled to `win32` objects; Win32 observer cross-compiled with
  `i686-w64-mingw32-gcc` when available (compile verification, not execution).
* Performance measurements recorded as analysis-host baselines, not
  Windows-lab claims.

---

## D24. Performance

No acceptance threshold is defined by research need. v0.1.0 records
baselines for synthetic throughput on the analysis host. No optimization
beyond ordinary algorithmic clarity.

---

## D25. Visibility research boundary

The Win32 observer is intentionally visible: stderr banner, ordinary
process, no unhooking of other hooks, no hiding, no persistence, no
injection, no network. Visibility characteristics may be *measured* in
the laboratory. They must not be *reduced by concealment features*.

---

## D26. Remaining TBD (not required to implement v0.1.0)

* Keyboard-layout-aware character translation (`ToUnicodeEx`)
* Execution of WH_KEYBOARD_LL on a Windows 7 SP1 VM (environment not
  present on the analysis host)
* Endpoint-security product identity/version for a specific lab VM
* Comparative multi-product detection experiments
* Additional input sources (mouse, raw input API)
