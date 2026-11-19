#!/bin/bash
# MB1, the whole chain from the four edits (0 tokens; about 6 min): the passes, the prints, the tone fixes, the frame, the checks
set -e
cd "$(dirname "$0")/.."
python3 tools/mb1_compose.py p1-bed p2-right p3-wall p4-floor
python3 tools/mb1_prints.py
python3 tools/mb1_tone_fix.py
python3 tools/mb1_compose.py compose
python3 tools/mb1_checks.py
