#!/usr/bin/env python3
"""
m0_shell_fix.py: M0 1.2 on the seedream-5-pro shell (briefs/render-m0-model-test-2026-11-05.md, step 2; render-agent, 2026-11-05, 0 tokens).
The seedream render passed the shell lock (QA's named shell lines raw <= 5.5 px) and its furniture already sits on the round-5b clay
(lock_v2 box edges <= 3 px, sofa / table / armchair width ratios 0.995-1.002), so the code composite of the gpt furniture is not laid on it
(it would bring another render's light onto a shell that is already right); what code does:
  1. one global affine (the inverse of lock_v2's ECC register against the clay: the render is ~0.5 % short vertically; G1.4 scale);
  2. the wall round (wall-decor-cj-corn-husk-round-38, RND3 test default) came out right in look but ~2x too large (233 px across for the
     118 px of a 38 cm plate at (-1.20, 0.02, 1.20)): scaled about its centre onto the projected 38 cm circle, the wall behind it filled
     (membrane + the wall's texture), its soft shadow carried as a ratio map;
  3. the triptych (RND3 a) warped onto the wall above the sofa (art_m0_12.py, the same placement as on m0-v8b-r2-fix2).
New files: assets/renders/living-room/nordic/v9/m0-1-2-shell-seedream-fix-base.png / .json (1 + 2), -fix.png / .json (+ 3), lock_v2, shell
lock, grading v5.
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fix_v7 as F  # noqa: E402
import fix_m0_12 as M  # noqa: E402
import shell_lock_m0 as SL  # noqa: E402
import m0_model_test as T  # noqa: E402

REPO = M.REPO
DATE = "2026-11-05"
SRC_ID = "m0-shell-seedream"
JID = "m0-1-2-shell-seedream"
OD_REL, OD = T.OD_REL, T.OD
ROUND_XZ, ROUND_D = (-1.20, 1.20), 0.38
WALL_TEX = (1900, 380, 2050, 520)          # canvas px of a plain back-wall patch (right of the pendant, above the right cube's fan)


def register(PL, jid):
    PL.VF.RETAKES[jid] = PL.JOBS["m0-v8b"]
    J = T.jr()
    if not any(j["id"] == jid for j in J["jobs"]):
        J["jobs"].append(dict(id=jid, out_dir=OD_REL, model="code (on m0-shell-seedream)", tokens=0, status="composite"))
        T.save_jr(J)
    PL.VF.RETAKES_JOBS = T.JR


def round_fix(a):
    import art_m0_12 as A
    import fix_v8 as F8
    H, W = a.shape[:2]
    Hh, L, S = M.hls(a)
    rope = ((Hh >= 15) & (Hh <= 50) & (S >= 22) & (L < 85)).astype(np.uint8) * F.rect_mask(H, W, 1150 / W, 1520 / W, 600 / H, 1000 / H).astype(np.uint8)
    rope = cv2.morphologyEx(rope, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(rope)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    comp = (lab == k).astype(np.uint8)
    cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    (ecx, ecy), (ew, eh), ang = cv2.fitEllipse(max(cnts, key=len).astype(np.float32))          # the outer contour
    matte = np.zeros((H, W), np.uint8)
    cv2.ellipse(matte, ((ecx, ecy), (ew + 3, eh + 3), ang), 1, -1)
    matte = matte.astype(np.float32)
    # the target: the 38 cm circle at (-1.20, 0.02, 1.20) projected with the 1.2.3 camera
    Hn = A.C_canvas(W, H) @ A.H_wall(A.CAMS["m0-v8b-r2"])
    th = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    circ = A.apply_h(Hn, np.stack([ROUND_XZ[0] + ROUND_D / 2 * np.cos(th), ROUND_XZ[1] + ROUND_D / 2 * np.sin(th)], 1))
    (tcx, tcy), (tw, thh), tang = cv2.fitEllipse(circ.astype(np.float32))
    s = float(np.sqrt((tw * thh) / (ew * eh)))
    # the wall behind: membrane through the wall around (the round and its shadow, 30 px), + the wall's texture
    hole = M.dil(matte, 30)
    wall = (L > 70).astype(np.float32) * F.rect_mask(H, W, 0.38, 0.70, 0.25, 0.70)
    clean = M.laplace_fill(a, hole, np.maximum(wall, hole), pad=60)
    clean = M.add_texture_m(a, clean, hole, WALL_TEX, strength=1.0, blur=2)
    ring = np.clip(hole - M.dil(matte, 1), 0, 1)
    ratio = np.where((ring > 0.5)[..., None], np.clip(a / np.maximum(clean, 1.0), 0.6, 1.02), 1.0).astype(np.float32)
    ratio = cv2.GaussianBlur(ratio, (0, 0), 2.0)
    Mx = np.float32([[s, 0, tcx - s * ecx], [0, s, tcy - s * ecy]])
    r_n = cv2.warpAffine(ratio, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(1, 1, 1))
    out = clean * r_n
    l_rgb = cv2.warpAffine(a, Mx, (W, H), flags=cv2.INTER_AREA)
    l_al = cv2.warpAffine(F.feather(matte, 0.8), Mx, (W, H), flags=cv2.INTER_LINEAR)
    out = F.composite(out, l_rgb, np.clip(l_al, 0, 1))
    rec = dict(rendered=dict(centre_px=[round(ecx, 1), round(ecy, 1)], axes_px=[round(ew, 1), round(eh, 1)]),
               target=dict(centre_px=[round(tcx, 1), round(tcy, 1)], axes_px=[round(tw, 1), round(thh, 1)], wall_point=[ROUND_XZ[0], 0.02, ROUND_XZ[1]], diameter_cm=38),
               scale=round(s, 4), size_before_over_card=round(float(np.sqrt(ew * eh / (tw * thh))), 3),
               how=("rope pixels (hue 15-50, S >= 22, L < 85) -> the largest component -> an ellipse fit to its outer contour (the matte, +3 px); scaled about its centre onto the "
                    "projected 38 cm circle; the wall behind (the round + 30 px) by a membrane through the wall around + the wall's texture; the soft shadow "
                    "(ratio original / clean wall in that ring) carried by the same scale"))
    return out, rec


def build():
    PL = M._pipeline()
    import fix_v8 as F8
    register(PL, SRC_ID)
    a = F.load(os.path.join(OD, SRC_ID + ".png"))
    PL.VF.RETAKES[SRC_ID] = PL.JOBS["m0-v8b"]
    F8.VF = PL.VF
    warped, aff = F8.global_affine_to_clay(SRC_ID, a)
    out, rrec = round_fix(warped)
    p = os.path.join(OD, JID + "-fix-base.png")
    F.save(out, p)
    note = dict(asset_id=JID + "-fix-base", date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/m0_shell_fix.py",
                source=OD_REL + SRC_ID + ".png", clay="assets/blockout/house/framing/round5b/M0.png",
                global_affine=dict(aff, why="G1.4: lock_v2's register of the raw read -0.51 % vertical (limit 0.5 %)"),
                wall_round=rrec, furniture=("kept as rendered: on the clay (lock_v2 box edges <= 3 px; width ratios sofa 1.001, table 0.995, armchair 1.002), "
                                            "so the gpt composite (fix_m0_12.py) is not laid on it"),
                output=OD_REL + JID + "-fix-base.png")
    json.dump(note, open(p.replace(".png", ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(affine_after=aff["register_after"], round=rrec), indent=0)[:1500])
    return note


def art():
    import art_m0_12 as A
    PL = M._pipeline()
    register(PL, JID)
    M.OUT[JID] = OD_REL
    A.CAMS[JID] = A.CAMS["m0-v8b-r2"]
    A.BASE_SUF, A.ART_SUF, A.DATE = "-fix-base", "-fix", DATE
    return A.run(JID, do_lock=True)


def checks():
    rep = SL.measure(os.path.join(OD, JID + "-fix.png"), JID + "-fix")
    json.dump(rep, open(os.path.join(OD, JID + "-fix-shell.json"), "w"), indent=1, ensure_ascii=False)
    T.overlay(os.path.join(OD, JID + "-fix.png"), rep, os.path.join(OD, JID + "-fix-shell.jpg"))
    n = json.load(open(os.path.join(OD, JID + "-fix.json")))
    n["shell_lock"] = dict(raw_max_px=rep["raw_max_px"], per_line=rep["per_line"], vanishing_point=rep["back_wall_vanishing_point"],
                           verdict=rep["verdict"], record=OD_REL + JID + "-fix-shell.json")
    json.dump(n, open(os.path.join(OD, JID + "-fix.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(shell=n["shell_lock"], lock=n["checks"]["lock_v2"], grade=n["checks"]["grade_v5"]), indent=0)[:3000])


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    if w in ("build", "all"):
        build()
    if w in ("art", "all"):
        art()
    if w in ("checks", "all"):
        checks()
