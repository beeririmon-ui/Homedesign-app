#!/usr/bin/env python3
"""Manifest entries for the grading-v3 files of the 22 v7 stills and the 4 fixes (regrade_v8.py; render-agent, 2026-11-03, 0 tokens).
Idempotent: existing ids are kept.  python3 record_regrade_v3.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
S = json.load(open(os.path.join(HERE, "regrade-v3-summary.json")))
man_path = os.path.join(REPO, "assets", "manifest.json")
man = json.load(open(man_path))
have = {a["id"] for a in man["assets"]}
n = 0
for r in S["rows"]:
    pose = r["id"].startswith("pose-")
    pref = ("v7-pose-" if pose else "v7-") + r["id"] + ("-fix" if r["fix"] else "")
    status = ("grading v3 (Bible targets, V7Q4 / BIB1; test page only) of the v7 still" + (" after the zero-token fix" if r["fix"] else "") +
              f"; reference wall L {r['measured_L']} (target {r['target_L']}, {r['range'][0]}-{r['range'][1]}); " + ("meets every Bible check" if r["meets_bible"] else "see regrade-v3-summary.json") +
              "; self-checked by the render-agent, awaiting qa-agent / master-designer / user; not for site")
    for key, kind in (("graded", "graded-v3"), ("frame", "graded-v3 16:9 frame (centre crop of the overscan canvas)"), ("os6", "graded-v3, frame width + 3% height top and bottom (motion-agent)")):
        p = r["outputs"].get(key)
        if not p:
            continue
        aid = pref + "-" + key + "-v3"
        if aid in have or not os.path.exists(os.path.join(REPO, p)):
            continue
        room = p.split("/")[2]
        man["assets"].append({"id": aid, "path": p, "room": room, "style": "nordic", "kind": ("v7-pose-" if pose else "v7-frame-") + kind, "frame": r["frame"], "recipe": "B v7 + grading v3",
                              "model": "gpt-image-2-5", "status": status, "measurements": r["measurements"], "grading": "assets/renders/house-nordic-v7-2026-11-02/regrade-v3-summary.json", "created": "2026-11-03"})
        have.add(aid)
        n += 1
json.dump(man, open(man_path, "w"), indent=1, ensure_ascii=False)
print("added", n, "manifest assets:", len(man["assets"]))
