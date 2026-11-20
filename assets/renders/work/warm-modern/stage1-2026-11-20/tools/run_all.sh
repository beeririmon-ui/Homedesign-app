#!/bin/bash
# run_all.sh: rebuild W0 stage one from the raw passes, 0 tokens (render-agent, 2026-11-20): every layer, shadow and light, the prints,
# the defaults frame, the two variant frames and the checks. About 8 minutes. The listing files of the prints and the SKU boards are read
# from the scratchpad (never copied into the repo).
set -euo pipefail
cd "$(dirname "$0")/.."
PY="python3.12 -I"
$PY tools/work_compose.py pA-wall
$PY tools/work_compose.py pC-sides
$PY tools/work_compose.py pB-desk
$PY tools/work_compose.py pD-front
$PY tools/work_compose.py pD-throw
$PY tools/work_prints.py
$PY tools/work_compose.py compose
$PY tools/work_variants.py
$PY tools/work_checks.py
