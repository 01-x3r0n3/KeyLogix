# KeyLogix — Laboratory Environment

## Analysis host (verified in v0.1.0 development)

The current development/analysis host is a Linux x86_64 machine used to:

* implement and unit-test the Python pipeline
* execute synthetic and replay experiments
* compile the C reference library and native test harness
* assemble NASM to Win32 objects
* cross-compile the Win32 observer with `i686-w64-mingw32-gcc`

This host **cannot** execute `WH_KEYBOARD_LL`. Win32 observation is
implemented in source and compile-checked; it is **not** runtime-verified
here.

## Target laboratory (specified, not executed in v0.1.0 on this host)

Per `CONTEXT.md`:

* Windows 7 SP1 virtual machine
* x86
* isolated from production networks and real user data
* synthetic credentials/data only
* NASM and a C toolchain (MinGW or MSVC) for native builds
* Python 3.8+ for the pipeline if analysis is run on the VM

### Suggested VM procedure (not executed here)

1. Snapshot the VM before experiments.
2. Record OS build, architecture, and any security-product identity,
   version, signature date, and relevant configuration.
3. Copy `native/win32/observer.c` (or a cross-compiled `observer.exe`)
   into the VM.
4. Build if needed (see `native/Makefile` target `observer-win32`).
5. Run from a console so the laboratory banner is visible:

   ```text
   observer.exe --session <uuid> --output raw.jsonl --duration-ms 15000
   ```

6. Type **synthetic** test input only.
7. Stop the observer (duration elapsed or Ctrl+C).
8. Copy `raw.jsonl` to the analysis host and ingest with replay.

Do not point the observer at real credentials, production systems, or
networks outside the laboratory.

### Endpoint-security experiments

If a security product is present, record its state **before** claiming
any detection result. If the product is absent, disabled, or its
telemetry cannot be read, the experiment status for detection questions
is `INCONCLUSIVE` or `SKIPPED`, never “no detection”.

## Synthetic data policy

Bundled experiments use strings such as `synthetic-user` and
`lab-password-not-real`. These are fabricated. Do not replace them with
real secrets.
