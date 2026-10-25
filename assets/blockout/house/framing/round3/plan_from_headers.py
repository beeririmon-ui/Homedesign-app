#!/usr/bin/env python3
"""
Draft plan.json for framing_r3.py from the `#` headers of the designer's prompt files (assets/prompts/recipe-v5.nordic/<frame>.txt):
one `#   <slot>   <card or STAND-IN ...>` line per rendered product = one placeholder; "Explicitly empty" = no placeholder.
Reconciled by hand against docs/rooms-render-plan-2026-10-25.md when it exists (that document wins).
  python3 plan_from_headers.py > plan.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
PROMPTS = os.path.join(REPO, "assets", "prompts", "recipe-v5.nordic")
FILES = {"D1": "d1.txt", "D2": "d2.txt", "H0": "h0-B.txt", "C0": "c0.txt", "MB0": "mb0.txt", "K-boy": "k-boy.txt", "K-girl": "k-girl.txt",
         "B1": "b1.txt", "B2": "b2.txt", "W0": "w0.txt"}
ROOM = {"D1": "kitchen-dining", "D2": "kitchen-dining", "H0": "hall", "C0": "corridor", "MB0": "master", "K-boy": "boy", "K-girl": "girl",
        "B1": "bath", "B2": "bath", "W0": "work"}
SLOT_RE = re.compile(r"^#\s{2,}([a-z][a-z0-9-]+)(?:\s+\([^)]*\))?\s+(\S.*)$")
SKIP = {"fixed", "living", "hall", "transit"}
plan = {"version": "draft from the prompt headers (render-agent, 2026-10-25); reconciled with docs/rooms-render-plan-2026-10-25.md",
        "source": "assets/prompts/recipe-v5.nordic/<frame>.txt # headers", "hall_cube_lamp": None, "frames": {}}
for fid, fn in FILES.items():
    p = os.path.join(PROMPTS, fn)
    f = dict(placeholders=[], lamps=None, also_visible=[], notes="", empty=[], prompt_file=fn)
    if not os.path.exists(p):
        f["notes"] = "prompt file not written yet"
        plan["frames"][fid] = f
        continue
    for line in open(p, encoding="utf-8"):
        if not line.startswith("#"):
            break
        m = SLOT_RE.match(line.rstrip("\n"))
        if m:
            slot, rest = m.group(1), m.group(2)
            if slot.split("-")[0] in SKIP or slot in ("fixed-furniture",):
                continue
            if re.match(r"^\d", rest) or rest.startswith("http"):
                continue
            f["placeholders"].append(slot)
            continue
        if "Explicitly empty" in line:
            body = line.split(":", 1)[1] if ":" in line else ""
            f["empty"] = [s.strip().split(" ")[0] for s in re.split(r",", body) if s.strip()]
    plan["frames"][fid] = f
if "H0" in plan["frames"]:
    plan["frames"]["H0"]["also_visible"] = ["living/pendant", "living/wall-decor", "living/accent-sconces"]
    plan["frames"]["H0"]["notes"] = "verdict 3.3: living vista = M0 clay + pumpkin 40 / sun 30 / travertine pair"
if "C0" in plan["frames"]:
    plan["frames"]["C0"]["also_visible"] = ["living/pendant", "living/wall-decor", "living/accent-sconces"]
json.dump(plan, sys.stdout, indent=1, ensure_ascii=False)
