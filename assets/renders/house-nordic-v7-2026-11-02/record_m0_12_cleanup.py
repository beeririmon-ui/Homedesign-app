#!/usr/bin/env python3
"""
Manifest entries for briefs/render-m0-composite-and-cleanup-2026-11-04.md (render-agent, 2026-11-04, 0 tokens): the M0 1.2 composites
(fix_m0_12.py), the four cleaned fixes (fix_v9.py, -fix2), CB-0 recomposed from B1 r3 fix2 (recompose_cb0.py) and the grading v5
(regrade_v5.py). Adds new entries only; an id already in the manifest is left as it is.
  python3 record_m0_12_cleanup.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
man_path = os.path.join(REPO, "assets", "manifest.json")
man = json.load(open(man_path))
have = {a["id"] for a in man["assets"]}
S5 = json.load(open(os.path.join(HERE, "regrade-v5-summary.json")))
rows5 = {(r["id"], r["fix"]): r for r in S5["rows"]}
added = []
NOTE = "self-checked by the render-agent; awaiting qa-agent / master-designer / user; not for site"


def add(aid, path, room, frame, kind, status, **kw):
    if aid in have or not os.path.exists(os.path.join(REPO, path)):
        return
    man["assets"].append(dict(id=aid, path=path, room=room, style="nordic", kind=kind, frame=frame, status=status, created="2026-11-04", **kw))
    have.add(aid)
    added.append(aid)


def v5_txt(r):
    if not r:
        return "grading v5: not run"
    return (f"grading v5 (Bible 1.8.4): reference {r['scale']} {r['measured']} [{r['range'][0]}-{r['range'][1]}]; "
            + ("meets Bible 1.8.4" if r["meets_bible_1_8_4"] else "fails " + ", ".join(r["fails"])))


# --- the M0 1.2 composites
M12 = {"m0-v8b-r2": ("assets/renders/living-room/nordic/v8/", "living-room", "M0"), "pose-m0p-v8b": ("assets/renders/poses/nordic/v8/", "living-room", "M0p"),
       "pose-m0x-v8b": ("assets/renders/poses/nordic/v8/", "living-room", "M0x")}
for jid, (od, room, frame) in M12.items():
    note = json.load(open(os.path.join(REPO, od, jid + "-fix.json")))
    lk = note.get("checks", {}).get("v4", {}).get("lock_v2", {})
    v = lk.get("verdict", {})
    lock_txt = (f"lock_v2 (edges v3, round-5b clay): shift {lk.get('shift_px')} scale {lk.get('scale_pct')} %, band {lk.get('band_after')} tile {lk.get('tile_after')}, "
                f"box edges worst {lk.get('fixed_edges_worst_px')} ratios {lk.get('fixed_ratios')}: "
                + ("PASS" if v.get("pass") else f"FAIL (g {int(bool(v.get('global_pass')))} r {int(bool(v.get('residual_pass')))} e {int(bool(v.get('edges_pass')))})"))
    st = "M0 1.2 composite in code (fix_m0_12.py, 0 tokens); " + lock_txt + "; " + v5_txt(rows5.get((jid, "fix"))) + "; " + NOTE
    base = dict(recipe="B v8 (paid M0 1.2 render) + fix_m0_12.py (0 tokens)", model="gpt-image-2-5", fix_record=od + jid + "-fix.json",
                clay="assets/blockout/house/framing/round5b/" + ("M0.png" if frame == "M0" else "poses/" + frame + ".png"))
    add("v8-" + jid + "-fix", od + jid + "-fix.png", room, frame, "M0 1.2 composite (ungraded)", st, **base)
    add("v8-" + jid + "-fix-lock", od + jid + "-fix-lock-v2.jpg", room, frame, "lock_v2 overlay of the composite (red = round-5b clay edges)", st, **base)
    for suf in ("v4", "v5"):
        for key, kind in (("graded", "graded"), ("frame", "graded 16:9 frame"), ("os6", "graded, frame width + 3% height (motion-agent)")):
            p = od + jid + {"graded": "-graded-fix-", "frame": "-frame-fix-", "os6": "-graded-os6-fix-"}[key] + suf + ".png"
            add("v8-" + jid + "-fix-" + key + "-" + suf, p, room, frame, f"M0 1.2 composite, {kind} {suf}", st, **base)

# --- the four cleaned fixes
for fid, od, room, frame in (("b1-v7-r3", "assets/renders/bath/nordic/v7/", "bath", "B1"), ("b2-v7-r3", "assets/renders/bath/nordic/v7/", "bath", "B2"),
                             ("pose-k-girl-0-v7-r2", "assets/renders/poses/nordic/v7/", "girl", "K-girl-0"), ("pose-w0-in-v7-r2", "assets/renders/poses/nordic/v7/", "work", "W0-in")):
    lk = json.load(open(os.path.join(REPO, od, fid + "-lock-fix2.json")))["after"]
    lock_txt = (f"lock v3: shift {lk['register_shift_px']} scale {lk['register_scale_pct']} %, band {lk['worst_band_px_after_register']} tile {lk['worst_tile_px_after_register']} "
                f"(limit {lk['residual_limit_px']}), named edges worst {lk['named_edges_worst_px']}: "
                + ("PASS" if lk["pass"] else f"FAIL (g {int(lk['global_pass'])} r {int(lk['residual_pass'])} e {int(lk['edges_pass'])})"))
    st = "cleanup of the 2026-11-04 code fix (QA 2026-11-04-retakes-fixes-g1; fix_v9.py, 0 tokens); " + lock_txt + "; " + v5_txt(rows5.get((fid, "fix2"))) + "; " + NOTE
    pre = ("v8-pose-" if fid.startswith("pose-") else "v8-") + fid
    base = dict(recipe="B v8 (retake) + fix_v8.py / fix_v9.py (0 tokens)", model="gpt-image-2-5", fix_record=od + fid + "-fix2.json", lock_record=od + fid + "-lock-fix2.json")
    add(pre + "-fix2", od + fid + "-fix2.png", room, frame, "v8-fix2 (ungraded, cleanup)", st, **base)
    add(pre + "-lock-fix2", od + fid + "-lock-fix2.jpg", room, frame, "v8-fix2 lock v3 overlay", st, **base)
    for key, mid in (("graded", "-graded-fix2-v5"), ("frame", "-frame-fix2-v5"), ("os6", "-graded-os6-fix2-v5")):
        add(pre + "-fix2-" + key + "-v5", od + fid + mid + ".png", room, frame, f"v8-fix2 {key} v5", st, **base)

# --- CB-0 recomposed
od = "assets/renders/poses/nordic/v7/"
ov = os.path.join(REPO, od, "pose-cb-0-v7-b1r3-overlap.json")
if os.path.exists(ov):
    o = json.load(open(ov))["results"]["new"]
    st = (f"CB-0 recomposed from B1 r3 fix2 (recompose_cb0.py, 0 tokens): overlap with B1 (T-CBath, QA G1.14) worst reliable band {o['worst_band_px_reliable']} px, "
          f"dL {o['dL_mean']}: {'PASS' if o['passes'] else 'FAIL'} (2 px / dL 1); " + NOTE)
    base = dict(recipe="reprojection of B1 r3 fix2 (pan_reproject.warp) + the v7 CB-0 left of B1's coverage", model="code", record=od + "pose-cb-0-v7-b1r3.json")
    add("v7-pose-cb-0-b1r3", od + "pose-cb-0-v7-b1r3.png", "bath", "CB-0", "CB-0 recomposite (ungraded)", st, **base)
    for key, mid in (("graded", "-graded-b1r3-v5"), ("frame", "-frame-b1r3-v5"), ("os6", "-graded-os6-b1r3-v5")):
        add("v7-pose-cb-0-b1r3-" + key + "-v5", od + "pose-cb-0-v7" + mid + ".png", "bath", "CB-0", f"CB-0 recomposite, {key} v5", st, **base)
    add("v7-pose-cb-0-b1r3-overlap", od + "pose-cb-0-v7-b1r3-overlap.jpg", "bath", "CB-0", "overlap sheet B1 r3 fix2 -> CB-0 recomposite", st, **base)

# --- grading v5 of the v7 stills and the 11-03 fixes
for r in S5["rows"]:
    if r["fix"] == "fix2" or r["id"] in M12:
        continue
    pose = r["id"].startswith("pose-")
    pref = ("v7-pose-" if pose else "v7-") + r["id"] + ("-" + r["fix"] if r["fix"] else "")
    st = v5_txt(r) + "; " + NOTE
    for key in ("graded", "frame", "os6"):
        p = r["outputs"].get(key)
        if p:
            add(pref + "-" + key + "-v5", p, p.split("/")[2], r["frame"], ("v7-pose-" if pose else "v7-frame-") + key + "-v5", st,
                recipe="B v7 + grading v5", model="gpt-image-2-5", grading="assets/renders/house-nordic-v7-2026-11-02/regrade-v5-summary.json")

json.dump(man, open(man_path, "w"), indent=1, ensure_ascii=False)
print("added", len(added), "manifest assets:", len(man["assets"]))
