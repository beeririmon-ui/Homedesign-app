#!/usr/bin/env python3
"""
lock_r12.py: the shell lock and the grade numbers of the r12 default scenes (after the reserve passes), render-agent 2026-11-11, 0 tokens.
The lock is QA's own measure (qa/reports/2026-11-07-pilot-phase1-g1/tools/shell_lock.py: nearest-peak against clay r4, raw, on the named
lines), as in lock-and-grade-check.json of steps 1-3, on graded/default-scene-r12-set-B-graded-v3c.png; the same verdict rule (every named
line p90 <= 9.6 px with >= 20 paired samples). Grade numbers: the L* black point (p0.5) and the clipped share (any channel >= 254, as steps 1-3) for sets B / A / C.
Writes lock-and-grade-check-r12.json.   python3 lock_r12.py
"""
import importlib.util
import json
import os

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 5))
spec = importlib.util.spec_from_file_location("sl", os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1/tools/shell_lock.py"))
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)
PREV = json.load(open(os.path.join(HERE, "lock-and-grade-check.json")))


def lstar(p):
    a = np.asarray(Image.open(p).convert("RGB"))
    return cv2.cvtColor(a.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0], a


def main():
    gc = sl.gray(Image.open(sl.CLAY).convert("RGB").resize((1920, 1080), Image.LANCZOS))
    out = {}
    pB = os.path.join(HERE, "graded/default-scene-r12-set-B-graded-v3c.png")
    gr = sl.gray(Image.open(pB).convert("RGB").resize((1920, 1080), Image.LANCZOS))
    lines = {ln: sl.nearest_peak_line(gc, gr, A, B) for ln, (A, B) in sl.LINES.items()}
    ok = all(v["p90_abs_px"] <= 9.6 and v["paired"] >= 20 for v in lines.values())
    prev = PREV["default_scene_set_B (phase 2)"]["lock_F3"]["lines"]
    same = {}
    for ln, v in lines.items():
        pk = next((k for k in prev if k.split(" (")[0] == ln.split(" (")[0]), None)
        same[ln] = None if pk is None else (prev[pk]["p90_abs_px"], v["p90_abs_px"])
    out["default_scene_r12_set_B"] = dict(lock_F3=dict(verdict=dict(pass_=bool(ok), rule="every named line p90 <= 9.6 px with >= 20 paired samples"),
                                                       lines=lines, p90_steps1_3_vs_r12=same))
    for s in "BAC":
        L, a = lstar(os.path.join(HERE, f"graded/default-scene-r12-set-{s}-graded-v3c.png"))
        rec = dict(black_point_p005=round(float(np.percentile(L, 0.5)), 2), clipped_254_pct=round(100 * float((a >= 254).any(2).mean()), 3),
                   black_point_steps1_3=PREV.get(f"default_scene_set_{s}", PREV.get("default_scene_set_B (phase 2)", {})).get("black_point_p005"))
        out.setdefault(f"default_scene_r12_set_{s}", {}).update(rec)
    json.dump(out, open(os.path.join(HERE, "lock-and-grade-check-r12.json"), "w"), indent=1)
    print(json.dumps(dict(pass_=ok, worst_p90=max(v["p90_abs_px"] for v in lines.values()),
                          min_paired=min(v["paired"] for v in lines.values()), p90_steps1_3_vs_r12=same,
                          grade={s: out[f"default_scene_r12_set_{s}"] for s in "BAC"}), indent=1))


if __name__ == "__main__":
    main()
