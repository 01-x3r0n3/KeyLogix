# KeyLogix — Reproducibility

## What has been verified on the analysis host

The script `scripts/verify_reproducibility.sh`:

1. uses the repository Python package (`PYTHONPATH=src`)
2. runs `pytest -q`
3. runs bundled synthetic experiments via `python -m keylogix`
4. checks that experiment artifact files exist

If that script exits 0, another engineer on a similar Unix analysis host
can repeat those steps.

## What has not been verified here

* Running `observer.exe` on Windows 7 SP1
* Endpoint-security product telemetry
* NASM routine *execution* (assembly is compile-checked)

## How to build

Python:

```text
python3 -m pytest -q
python3 -m keylogix --help
```

Native (from `native/`):

```text
make test-ref          # C reference harness (runs on analysis host)
make asm-win32         # NASM → win32 objects
make observer-win32    # cross-compile observer.exe (not executed here)
```

## How to run an experiment

```text
python3 -m keylogix run-experiment experiments/definitions/EXP-001-synthetic-pipeline.json
```

Artifacts: `output/experiments/<id>/<run_id>/`.

## What to record for a laboratory run

* source revision (`git rev-parse HEAD` or `uncommitted`)
* dirty tree or not
* implementation version (`keylogix.__version__`)
* OS / arch
* Python version
* whether the Win32 observer was used
* security-product state, or explicit absence
* experiment id and run id
* input script identity
* output directory

`environment.json` written by the runner captures the analysis-host
portion of this automatically.
