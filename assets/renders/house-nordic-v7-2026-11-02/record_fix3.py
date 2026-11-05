#!/usr/bin/env python3
"""Manifest entries for the fix3 round (fix_v10.py, recompose_cb0_v3.py, m0p_fix3.py; render-agent 2026-11-05, 0 tokens). New ids only."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
man_path = os.path.join(REPO, "assets", "manifest.json")
man = json.load(open(man_path))
have = {a["id"] for a in man["assets"]}
added = []
NOTE = "self-checked by the render-agent; awaiting qa-agent; not for site"


def add(aid, path, room, frame, kind, status, **kw):
    if aid in have or not os.path.exists(os.path.join(REPO, path)):
        return
    man["assets"].append(dict(id=aid, path=path, room=room, style="nordic", kind=kind, frame=frame, status=status, created="2026-11-05", **kw))
    have.add(aid)
    added.append(aid)


for fid, od, room, frame in (("b1-v7-r3", "assets/renders/bath/nordic/v7/", "bath", "B1"), ("pose-w0-in-v7-r2", "assets/renders/poses/nordic/v7/", "work", "W0-in"),
                             ("pose-k-girl-0-v7-r2", "assets/renders/poses/nordic/v7/", "girl", "K-girl-0")):
    lk = json.load(open(os.path.join(REPO, od, fid + "-lock-fix3.json")))["after"]
    gr = json.load(open(os.path.join(REPO, od, fid + "-fix3.json"))).get("grade_v5", {})
    st = (f"fix3 (QA 2026-11-04-m0-fix2-cb0-g1 §8; fix_v10.py, 0 tokens); lock v3 band {lk['worst_band_px_after_register']} tile {lk['worst_tile_px_after_register']} "
          f"(limit {lk['residual_limit_px']}), named edges worst {lk['named_edges_worst_px']}: {'PASS' if lk['pass'] else 'FAIL'}; grading v5 "
          + ("meets Bible 1.8.4" if gr.get("meets_bible") else "fails " + ", ".join(gr.get("fails", []))) + "; " + NOTE)
    pre = ("v8-pose-" if fid.startswith("pose-") else "v8-") + fid
    base = dict(recipe="B v8 + fix_v8 / fix_v9 / fix_v10 (0 tokens)", model="gpt-image-2-5", fix_record=od + fid + "-fix3.json", lock_record=od + fid + "-lock-fix3.json")
    add(pre + "-fix3", od + fid + "-fix3.png", room, frame, "v8-fix3 (ungraded)", st, **base)
    add(pre + "-lock-fix3", od + fid + "-lock-fix3.jpg", room, frame, "v8-fix3 lock v3 overlay", st, **base)
    for key, mid in (("graded", "-graded-fix3-v5"), ("frame", "-frame-fix3-v5"), ("os6", "-graded-os6-fix3-v5")):
        add(pre + "-fix3-" + key + "-v5", od + fid + mid + ".png", room, frame, f"v8-fix3 {key} v5", st, **base)

od = "assets/renders/poses/nordic/v7/"
rec = json.load(open(os.path.join(REPO, od, "pose-cb-0-v7-b1r3f3.json")))
ov = json.load(open(os.path.join(REPO, od, "pose-cb-0-v7-b1r3f3-overlap.json")))["result"]
g = rec["grade_v5"]
st = (f"CB-0 recomposed from B1 r3 fix3 (recompose_cb0_v3.py, 0 tokens): T-CBath overlap {ov['worst_band_px_reliable']} px, dL {ov['dL_mean']} "
      f"({'PASS' if ov['passes'] else 'FAIL'}); grading v5 at B1's point projected: L {g['L']} [{g['range'][0]}-{g['range'][1]}], C* {g['C_star']}: "
      + ("meets Bible 1.8.4" if g["meets_bible_1_8_4"] else "fails") + "; " + NOTE)
base = dict(recipe="reprojection of B1 r3 fix3 + the v7 CB-0 outside B1's coverage (gain field)", model="code", record=od + "pose-cb-0-v7-b1r3f3.json")
add("v7-pose-cb-0-b1r3f3", od + "pose-cb-0-v7-b1r3f3.png", "bath", "CB-0", "CB-0 recomposite (ungraded)", st, **base)
for key, mid in (("graded", "-graded-b1r3f3-v5"), ("frame", "-frame-b1r3f3-v5"), ("os6", "-graded-os6-b1r3f3-v5")):
    add("v7-pose-cb-0-b1r3f3-" + key + "-v5", od + "pose-cb-0-v7" + mid + ".png", "bath", "CB-0", f"CB-0 recomposite, {key} v5", st, **base)
add("v7-pose-cb-0-b1r3f3-overlap", od + "pose-cb-0-v7-b1r3f3-overlap.jpg", "bath", "CB-0", "overlap sheet B1 r3 fix3 -> CB-0", st, **base)
add("v7-pose-cb-0-b1r3f3-lock", od + "pose-cb-0-v7-b1r3f3-lock-v2.jpg", "bath", "CB-0", "lock_v2 overlay", st, **base)

od = "assets/renders/poses/nordic/v8/"
jid = "pose-m0p-v8b"
n3 = json.load(open(os.path.join(REPO, od, jid + "-fix3.json")))
nb = json.load(open(os.path.join(REPO, od, jid + "-fix3-base.json")))
lk = nb["lock_v2"]
st = (f"M0p fix3 (m0p_fix3.py, 0 tokens): vertical affine +1.34 % on the raw, composite redone, bowl duplicate removed, triptych; lock_v2 of the composite "
      f"without the art: shift {lk['shift_px']} scale {lk['scale_pct']} %, band {lk['band_after']} tile {lk['tile_after']}: {'PASS' if lk['verdict']['pass'] else 'FAIL'}; grading v5 "
      + ("meets Bible 1.8.4" if n3["checks"]["grade_v5"]["meets_bible"] else "fails") + "; wall-decor pending a paid pass; " + NOTE)
base = dict(recipe="B v8 + fix_m0_12.py + art_m0_12.py (0 tokens)", model="gpt-image-2-5", fix_record=od + jid + "-fix3.json")
for aid, path, kind in ((f"v8-{jid}-va", od + jid + "-va.png", "M0p raw + vertical affine"),
                        (f"v8-{jid}-fix3-base", od + jid + "-fix3-base.png", "M0p composite (no art)"),
                        (f"v8-{jid}-fix3-base-lock", od + jid + "-fix3-base-lock-v2.jpg", "lock_v2 overlay (no art)"),
                        (f"v8-{jid}-fix3", od + jid + "-fix3.png", "M0p composite + triptych (ungraded)"),
                        (f"v8-{jid}-fix3-lock", od + jid + "-fix3-lock-v2.jpg", "lock_v2 overlay"),
                        (f"v8-{jid}-fix3-graded-v5", od + jid + "-graded-fix3-v5.png", "graded v5"),
                        (f"v8-{jid}-fix3-frame-v5", od + jid + "-frame-fix3-v5.png", "graded v5 16:9 frame"),
                        (f"v8-{jid}-fix3-os6-v5", od + jid + "-graded-os6-fix3-v5.png", "graded v5, frame width + 3% height")):
    add(aid, path, "living-room", "M0p", kind, st, **base)
json.dump(man, open(man_path, "w"), indent=1, ensure_ascii=False)
print("added", len(added), "manifest assets:", len(man["assets"]))
