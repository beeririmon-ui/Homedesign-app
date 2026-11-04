#!/usr/bin/env python3
"""
Box overlays and manifest entries for the 2026-11-04 work (briefs/render-retakes-code-fixes-2026-11-04.md; render-agent, 0 tokens):
the four code fixes (fix_v8.py: `<id>-fix.png`), their lock v3 overlays (lock_fixes_v8.py: `<id>-lock-fix.jpg` after,
`<id>-lock-v3.jpg` before), their grading-v4 files and product-box overlays (`<id>-boxes-fix-v4.png`), and the grading-v4 files
of the 22 v7 stills and the 4 fixes of 2026-11-03 (regrade_v4.py). Idempotent: existing ids are kept.
  python3 record_v8_fixes.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402
import fetch_retakes as FR  # noqa: E402

REPO = VF.REPO
S = json.load(open(os.path.join(HERE, "regrade-v4-summary.json")))
man_path = os.path.join(REPO, "assets", "manifest.json")
man = json.load(open(man_path))
have = {a["id"] for a in man["assets"]}
NEW = ["b1-v7-r3", "b2-v7-r3", "pose-k-girl-0-v7-r2", "pose-w0-in-v7-r2"]
added = []


def add(aid, path, room, frame, kind, status, **kw):
    if aid in have or not os.path.exists(os.path.join(REPO, path)):
        return
    e = dict(id=aid, path=path, room=room, style="nordic", kind=kind, frame=frame, status=status, created="2026-11-04", **kw)
    man["assets"].append(e)
    have.add(aid)
    added.append(aid)


rows = {(r["id"], r["fix"]): r for r in S["rows"]}
for fid in NEW:
    frame, kind, clay_file, pan, overscan, room = VF.frame(fid)
    od = VF.out_dir(fid)
    rel = lambda p: os.path.relpath(p, REPO)  # noqa: E731
    r = rows[(fid, True)]
    g = os.path.join(REPO, r["outputs"]["graded"])
    bx = os.path.join(od, fid + "-boxes-fix-v4.png")
    if not os.path.exists(bx):
        FR.boxes_overlay(g, bx, frame, fid, overscan)
    lock = json.load(open(os.path.join(od, fid + "-lock-fix.json")))
    a = lock["after"]
    lock_txt = (f"lock v3 after the fix: named edges worst {a['named_edges_worst_px']} px ({a['named_edges_counted']} counted), box edges worst {a['box_edges_worst_px']}, "
                f"residual band {a['worst_band_px_after_register']} / tile {a['worst_tile_px_after_register']} (limit {a['residual_limit_px']}), register scale {a['register_scale_pct']} %: "
                f"{'PASS' if a['pass'] else 'FAIL (g %d r %d e %d)' % (a['global_pass'], a['residual_pass'], a['edges_pass'])}")
    base = dict(recipe="B v8 (retake) + fix_v8.py (0 tokens)", model="gpt-image-2-5", fix_record=rel(os.path.join(od, fid + "-fix.json")),
                lock_record=rel(os.path.join(od, fid + "-lock-fix.json")), clay=rel(os.path.join(VF.R4, clay_file)))
    st = ("code fix of the v8 retake (QA 2026-11-03 §11.1), self-checked by the render-agent; " + lock_txt +
          f"; grading v4: {'meets Bible 1.8.2' if r['meets_bible_1_8_2'] else 'fails ' + ', '.join(r['fails'])}; awaiting qa-agent G1 / master-designer / user; not for site")
    pre = ("v8-pose-" if kind == "pose" else "v8-") + fid
    add(pre + "-fix", rel(os.path.join(od, fid + "-fix.png")), room, frame, "v8-fix (ungraded)", st, **base)
    add(pre + "-fix-graded-v4", r["outputs"]["graded"], room, frame, "v8-fix-graded-v4", st, measurements=r["measurements"], **base)
    if r["outputs"].get("frame"):
        add(pre + "-fix-frame-v4", r["outputs"]["frame"], room, frame, "v8-fix-graded-v4 16:9 frame (centre crop of the overscan canvas)", st, measurements=r["measurements"], **base)
    if r["outputs"].get("os6"):
        add(pre + "-fix-os6-v4", r["outputs"]["os6"], room, frame, "v8-fix-graded-v4, frame width + 3% height top and bottom (motion-agent)", st, measurements=r["measurements"], **base)
    add(pre + "-fix-boxes-v4", rel(bx), room, frame, "v8-fix product-boxes overlay (graded v4; red = clay box, yellow = +-15 %)", st, **base)
    add(pre + "-lock-fix", rel(os.path.join(od, fid + "-lock-fix.jpg")), room, frame, "v8-fix lock v3 overlay (after; red = clay edges and named lines, green = measured)", st, **base)
    add(pre + "-lock-v3", rel(os.path.join(od, fid + "-lock-v3.jpg")), room, frame, "v8 retake lock v3 overlay (before the fix; for comparison)",
        "the raw retake measured with lock v3 (2026-11-04) for the before / after comparison; not for site", **base)

for r in S["rows"]:
    if r["id"] in NEW:
        continue
    pose = r["id"].startswith("pose-")
    pref = ("v7-pose-" if pose else "v7-") + r["id"] + ("-fix" if r["fix"] else "")
    status = ("grading v4 (Bible 1.8.2 light rules + QA §11.2: wall hue, absolute C*, window wall; test page only) of the v7 still" + (" after the zero-token fix" if r["fix"] else "") +
              f"; reference wall L {r['L_reference']} H {r['H']} C* {r['C_star']}; " + ("meets Bible 1.8.2" if r["meets_bible_1_8_2"] else "fails " + ", ".join(r["fails"])) +
              "; self-checked by the render-agent, awaiting qa-agent / master-designer / user; not for site")
    for key, kind in (("graded", "graded-v4"), ("frame", "graded-v4 16:9 frame (centre crop of the overscan canvas)"), ("os6", "graded-v4, frame width + 3% height top and bottom (motion-agent)")):
        p = r["outputs"].get(key)
        if not p:
            continue
        room = p.split("/")[2]
        add(pref + "-" + key + "-v4", p, room, r["frame"], ("v7-pose-" if pose else "v7-frame-") + kind, status, recipe="B v7 + grading v4", model="gpt-image-2-5",
            measurements=r["measurements"], grading="assets/renders/house-nordic-v7-2026-11-02/regrade-v4-summary.json")

json.dump(man, open(man_path, "w"), indent=1, ensure_ascii=False)
print("added", len(added), "manifest assets:", len(man["assets"]))
