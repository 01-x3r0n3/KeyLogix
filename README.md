# KeyLogix

**Controlled laboratory for Windows low-level input-capture and endpoint-security research.**

KeyLogix is a security-research and adversary-emulation laboratory framework for studying low-level keyboard input observation, event representation, normalization, contextual analysis, observability, and endpoint-security telemetry in a controlled research environment.

---

## 1. Laboratory Safety Boundaries

KeyLogix is strictly a research and laboratory tool. It is **not** designed or intended for real-world surveillance or malicious use.

**Out of Scope / Prohibited Capabilities:**
- Real-user credential theft or monitoring
- Remote targeting or Command-and-Control (C2)
- Data exfiltration
- Covert persistence or process hiding
- Anti-forensics or defense evasion
- Unauthorized process injection or propagation

All sensitive test data used in experiments must be synthetic.

---

## 2. Architecture & Pipeline

```text
Input Observation (Synthetic / Replay / Win32 LLHook)
       ↓
Normalization (Raw → NormalizedEvent)
       ↓
Context Collection (Application & Window Title Association)
       ↓
Event Classification (Deterministic VK Categories & Heuristic Sequence Labels)
       ↓
Behavioral Analysis (Frequencies, Intervals, Bursts, Repeats, Down/Up Pairing)
       ↓
Observability (Experiment Run Logs & Lifecycle Records)
       ↓
Evidence Store (Provenance-Preserving Records)
       ↓
Experiment Runner (Controlled Conditions, Expected vs Actual Observations)
       ↓
Report Generation (Structured JSON & Human-Readable Markdown)
```

---

## 3. Project Structure

```text
KeyLogix/
├── src/keylogix/              # Core Python research pipeline
│   ├── model.py               # Immutable research data models
│   ├── normalize.py           # Normalization stage
│   ├── context.py             # Context association & conflict tracking
│   ├── classify.py            # Deterministic & heuristic classification
│   ├── analysis.py            # Behavioral analysis & metrics
│   ├── experiment.py          # Experiment schema & execution runner
│   ├── native_bridge.py       # C reference library ctypes bridge
│   ├── pipeline.py            # Pipeline orchestrator
│   ├── persist.py             # Atomic JSON / JSONL storage
│   ├── observation/           # Observation sources (synthetic, replay, win32)
│   └── cli.py                 # Command-line interface
├── native/                    # Low-level C and NASM components
│   ├── include/keylogix_abi.h # Shared C ABI definition
│   ├── c/keylogix_ref.c       # Host C reference implementation
│   ├── asm/i386/              # NASM x86 32-bit cdecl research routines
│   ├── win32/observer.c       # WH_KEYBOARD_LL laboratory capture tool
│   └── harness/test_native.c  # Native C test harness (68 tests)
├── experiments/               # Bundled experiment definitions & sample data
├── tests/                     # Comprehensive pytest test suite (76 tests)
├── scripts/                   # Reproducibility verification scripts
└── docs/                      # Technical specification, architecture, decisions
```

---

## 4. Building and Verification

### Prerequisites
- Python 3.8+ (tested on Python 3.13)
- `gcc` (for C reference library and test harness)
- `nasm` (for x86 assembly routines)
- `i686-w64-mingw32-gcc` (optional, for cross-compiling Win32 observer)
- `pytest` (development dependency)

### Quick Start & Verification

Run the full automated verification suite:

```bash
./scripts/verify_reproducibility.sh
```

Or run individual components:

```bash
# Build native components and execute C test harness
make -C native all

# Run Python test suite
PYTHONPATH=src pytest -q

# Run an experiment definition
PYTHONPATH=src python3 -m keylogix run-experiment experiments/definitions/EXP-001-synthetic-pipeline.json

# Run synthetic pipeline manually
PYTHONPATH=src python3 -m keylogix run-synthetic --keys 0x41,0x42,0x43

# Verify environment and native library bridge
PYTHONPATH=src python3 -m keylogix verify
```

---

## 5. Status and Verified Capabilities

| Component | Status | Verification Details |
|---|---|---|
| Core Python Pipeline | Implemented & Verified | 76 automated pytest tests pass across all stages. |
| Native C Reference | Implemented & Verified | 68 automated C tests in test harness pass. |
| NASM x86 Routines | Implemented & Compile-Checked | Assembles to win32 objects (`.obj`) with NASM. |
| Win32 Observer | Implemented & Cross-Compiled | Cross-compiled with MinGW (`observer.exe`). |
| Bundled Experiments | Implemented & Verified | EXP-001 through EXP-005 execute and verify artifacts. |

---

## 6. Limitations & Scope

- **Analysis Host**: Development and testing were conducted on an x86_64 Linux analysis host.
- **Win32 Hook Execution**: `WH_KEYBOARD_LL` requires a Windows target environment (e.g. Windows 7 SP1 VM); on non-Windows hosts, the Win32 source reports `SKIPPED`.
- **Layout Translation**: Virtual key codes are mapped to deterministic key labels without keyboard layout (`ToUnicodeEx`) translation.
- **Security Telemetry**: No endpoint security software was evaluated in this host environment; experiment records explicitly state that telemetry is not measured rather than claiming non-detection.
