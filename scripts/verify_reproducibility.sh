#!/usr/bin/env bash
set -euo pipefail

echo "================================================================"
echo " KeyLogix — Verification and Reproducibility Suite"
echo "================================================================"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

export PYTHONPATH="src"

echo ""
echo "[1/4] Building and testing native C reference & NASM objects..."
make -C native all

echo ""
echo "[2/4] Running Python pytest test suite..."
pytest -q

echo ""
echo "[3/4] Running KeyLogix CLI verification..."
python3 -m keylogix verify

echo ""
echo "[4/4] Executing bundled experiment definitions..."
EXP_FILES=(
    "experiments/definitions/EXP-001-synthetic-pipeline.json"
    "experiments/definitions/EXP-002-context-timeline.json"
    "experiments/definitions/EXP-003-special-keys-burst.json"
    "experiments/definitions/EXP-004-replay-ingest.json"
    "experiments/definitions/EXP-005-noise-handling.json"
)

for exp in "${EXP_FILES[@]}"; do
    echo "  -> Running ${exp}..."
    python3 -m keylogix run-experiment "${exp}"
done

echo ""
echo "[+] Checking generated experiment artifacts..."
for exp_id in EXP-001-synthetic-pipeline EXP-002-context-timeline EXP-003-special-keys-burst EXP-004-replay-ingest EXP-005-noise-handling; do
    LATEST_RUN=$(ls -td output/experiments/"${exp_id}"/*/ 2>/dev/null | head -n1 || true)
    if [ -z "${LATEST_RUN}" ]; then
        echo "[-] ERROR: Missing run directory for ${exp_id}"
        exit 1
    fi
    for artifact in experiment.json environment.json raw.jsonl normalized.jsonl classified.jsonl evidence.jsonl observability.json report.md; do
        if [ ! -f "${LATEST_RUN}/${artifact}" ]; then
            echo "[-] ERROR: Missing artifact ${artifact} in ${LATEST_RUN}"
            exit 1
        fi
    done
    echo "  [OK] ${exp_id} verified at ${LATEST_RUN}"
done

echo ""
echo "================================================================"
echo " [SUCCESS] All KeyLogix reproducibility checks passed."
echo "================================================================"
