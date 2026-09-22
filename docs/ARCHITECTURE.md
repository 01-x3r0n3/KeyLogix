# KeyLogix — Architecture

This document describes the implemented v0.1.0 architecture. It is
subordinate to `docs/SPECIFICATION.md` and `CONTEXT.md`. Decisions that
resolved specification TBDs live in `docs/DECISIONS.md`.

---

## 1. Pipeline

```text
Input Observation
       ↓
Normalization
       ↓
Context Collection
       ↓
Event Classification
       ↓
Behavioral Analysis
       ↓
Observability
       ↓
Evidence
       ↓
Experiment
       ↓
Report
```

Each arrow is a typed contract. Downstream components consume copies of
immutable records. No stage silently replaces raw observations with
interpretations.

Information kinds, in order of derivation:

```text
raw_observation
normalized_observation
derived_interpretation
heuristic_classification
behavioral_analysis
```

---

## 2. Process topology

```text
[Win32 observer.exe]  --JSONL raw observations-->  [Python pipeline]
[Synthetic source ]  --in-process objects------->  [Python pipeline]
[Replay source    ]  --JSONL ingest------------->  [Python pipeline]
                                                      |
                                                      v
                                              output/experiments/...
```

The Win32 observer is a separate process. It does not load Python. The
Python pipeline never installs a keyboard hook itself. This keeps the
Windows API boundary small and auditable.

On the analysis host (Linux in the current development environment),
only synthetic and replay sources execute. Requesting `win32_llhook`
returns `SKIPPED`.

---

## 3. Python package (`src/keylogix`)

| Module | Role |
|--------|------|
| `status` | `Status`, `Result` |
| `constants` | schema ids, version, thresholds |
| `vk` | virtual-key labels and deterministic categories |
| `model` | immutable data types |
| `identity` | UUID factories, collision detection |
| `timeutil` | pluggable clocks |
| `observation` | observation sources |
| `normalize` | raw → normalized |
| `context` | context validation/association |
| `classify` | per-event and sequence classification |
| `analysis` | behavioral measurements |
| `observability` | run-level artifact log |
| `evidence` | evidence records |
| `persist` | JSON/JSONL atomic writes |
| `experiment` | experiment schema and runner |
| `report` | Markdown report |
| `pipeline` | orchestration |
| `native_bridge` | optional ctypes to the C reference library |
| `cli` | command-line entry |

---

## 4. Contracts

### 4.1 Result

Every public operation that can fail returns `Result`:

* `status`: canonical `Status` value
* `value`: payload when applicable
* `message`: human-readable explanation
* `details`: optional immutable mapping

`SUCCESS_WITH_DATA` and `SUCCESS_NO_DATA` are both successful completions.
Callers must not treat `SUCCESS_NO_DATA` as failure, and must not treat
`PARTIAL` / `INCONCLUSIVE` as full success.

### 4.2 Raw observation → normalizer

Input: `RawObservation`
Output: `Result[NormalizedEvent]`

The normalizer does not query the OS. It does not invent context.

### 4.3 Normalized event → classifier

Input: `NormalizedEvent`
Output: `ClassificationRecord` with `method=deterministic` for VK
category. Sequence classification is a separate call over a list of
events and is `method=heuristic`.

### 4.4 Event list → analysis

Input: sequence of `NormalizedEvent` plus optional condition event IDs
Output: `BehavioralSummary` with measured fields and `Conclusion` objects

### 4.5 Persistence

Input: objects with `to_dict()`
Output: files under `output/` or an explicit `PROVIDER_FAILURE`

---

## 5. Data ownership

* Dataclasses are frozen. Transforms produce new objects.
* Observation sources own their runtime handles (files, subprocess).
* The pipeline owns the output directory for a run.
* Native buffers are caller-allocated; `evt_buffer_init` writes a header
  only and does not allocate.

---

## 6. Native layer

See `docs/NATIVE_ABI.md`.

```text
native/include/keylogix_abi.h     shared C ABI
native/c/keylogix_ref.c           analysis-host reference (tested)
native/asm/i386/*.asm             NASM cdecl routines (Windows x86)
native/win32/observer.c           WH_KEYBOARD_LL laboratory observer
native/harness/test_native.c      ABI tests
```

The Win32 observer does **not** link the NASM routines. The observer's
job is capture. Normalization/classification of captured JSONL is Python
(and optionally the C reference) after ingest.

---

## 7. Experiments

Definitions live in `experiments/definitions/*.json`.

A run produces:

```text
output/experiments/<id>/<run_id>/
  experiment.json
  environment.json
  raw.jsonl
  normalized.jsonl
  classified.jsonl
  analysis.json
  evidence.jsonl
  observability.json
  report.md
```

---

## 8. Security boundary

The system:

* has no network client
* has no C2 or exfiltration path
* does not persist across reboots
* does not hide processes
* does not inject into other processes
* does not disable security products
* uses synthetic data in bundled experiments

The laboratory observer is a visible user-mode process that installs a
documented Win32 hook and always chains `CallNextHookEx`.

---

## 9. What v0.1.0 does not claim

* That WH_KEYBOARD_LL was executed on Windows 7 SP1 in this environment
* That any endpoint-security product did or did not generate an alert
* That behavior is undetectable, stealthy, or operationally useful
* That key labels equal typed characters under an arbitrary layout
