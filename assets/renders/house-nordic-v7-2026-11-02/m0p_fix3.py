#!/usr/bin/env python3
"""
m0p_fix3.py: M0p 1.2 fix3 (QA qa/reports/2026-11-04-m0-fix2-cb0-g1.md §2 / §8; the coordinator's message of 2026-11-05). render-agent,
0 var2 tokens. New files only: pose-m0p-v8b-va.png / .json (the raw after the vertical affine), -fix3-base.png / .json (the composite),
-fix3.png / .json (+ the triptych), their lock_v2 records and grading v5. The -fix / -fix2 files QA checked are read, never written.

  1. the raw still's shell is ~1.3 % short vertically against the round-5b clay, uniformly across the frame (QA): one vertical affine,
     fitted by least squares to the shell lines measured in the raw and the clay (the cornice's two edges, the skirting's top, the floor
     line; their sub-pixel |d/dy| peaks over the wall columns left and right of the sofa), applied to the raw before anything else;
  2. the sofa / table composite (fix_m0_12.fix_m0 with the M0p config) redone on that still, the config's y values carried by the same
     affine; the table top under the bowl and the candle holders filled before the table is warped (the duplicated bowl rim);
  3. the triptych (art_m0_12) warped onto the new composite.
  python3 m0p_fix3.py [all | va | composite | art | lock]
"""
import copy
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fix_v7 as F  # noqa: E402
import fix_m0_12 as M  # noqa: E402

REPO = M.REPO
DATE = "2026-11-05"
SCRIPT = "assets/renders/house-nordic-v7-2026-11-02/m0p_fix3.py"
JID = "pose-m0p-v8b"
OD = os.path.join(REPO, M.OUT[JID])
VA = os.path.join(OD, JID + "-va.png")
# the shell lines: (name, render search rows, clay search rows, columns, sign of d/dy at the edge)
LINES = [("cornice, upper edge", (118, 136), (124, 142), "-"), ("cornice, lower edge", (134, 150), (138, 156), "-"),
         ("skirting top", (1140, 1160), (1150, 1168), "c"), ("floor line", (1186, 1206), (1205, 1225), "-")]
COLS = [(150, 350), (1700, 1880)]
# fitted on the room's junctions (the cornice's lower edge = wall / cornice, the floor line = wall / floor); the skirting's top is reported
# only: the render draws the skirting ~10 px lower than the clay's (47 vs 57 px), a content difference, not the camera's
FIT_LINES = ("cornice, lower edge", "floor line")


def peak(img, y0, y1, sign):
    g = M.gray(img)
    gy = cv2.Sobel(cv2.GaussianBlur(g, (0, 0), 1.2), cv2.CV_32F, 0, 1, ksize=3)
    vals = []
    for x0, x1 in COLS:
        p = gy[y0:y1, x0:x1].mean(1)
        p = -p if sign == "-" else (np.abs(p) if sign == "c" else p)
        i = int(np.argmax(p))
        if 0 < i < len(p) - 1:
            den = p[i - 1] - 2 * p[i] + p[i + 1]
            off = 0.5 * (p[i - 1] - p[i + 1]) / den if den != 0 else 0.0
        else:
            off = 0.0
        vals.append(float(y0 + i + off))
    return float(np.mean(vals)), [round(v, 2) for v in vals]


def va():
    a = M.still(JID)
    H, W = a.shape[:2]
    c = M.clay(JID, W, H)
    rows = []
    for nm, rr, rc, sg in LINES:
        yr, yrs = peak(a, *rr, sg)
        yc, ycs = peak(c, *rc, sg)
        rows.append(dict(line=nm, render=round(yr, 2), clay=round(yc, 2), d=round(yr - yc, 2), render_lr=yrs, clay_lr=ycs))
    use = [r for r in rows if r["line"] in FIT_LINES]
    yr = np.array([r["render"] for r in use])
    yc = np.array([r["clay"] for r in use])
    s, t = np.polyfit(yr, yc, 1)                     # y_clay = s y_render + t
    ys = np.arange(H, dtype=np.float64)
    src = (ys - t) / s                               # output row y' takes source row (y' - t) / s
    mapy = np.repeat(src[:, None], W, 1).astype(np.float32)
    mapx = np.repeat(np.arange(W, dtype=np.float32)[None, :], H, 0)
    out = np.clip(cv2.remap(a.astype(np.float32), mapx, mapy, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE), 0, 255)
    F.save(out, VA)
    after = []
    for nm, rr, rc, sg in LINES:
        y2, _ = peak(out, int(rr[0] * s + t) - 4, int(rr[1] * s + t) + 4, sg)
        yc2 = next(r["clay"] for r in rows if r["line"] == nm)
        after.append(dict(line=nm, render=round(y2, 2), clay=yc2, d=round(y2 - yc2, 2)))
    rec = dict(asset_id=JID + "-va", date=DATE, tokens=0, script=SCRIPT,
               what="the raw M0p still with one vertical affine onto the round-5b clay's shell lines (QA: ~-1.3 % vertical, uniform across the frame)",
               source=M.OUT[JID] + JID + ".png", fit=dict(scale=round(float(s), 5), scale_pct=round(float(s - 1) * 100, 3), offset_px=round(float(t), 2),
                                                          how="y_clay = s y_render + t through the cornice's lower edge and the floor line (canvas px of the 2736 x 1539 still); the other lines reported"),
               lines_before=rows, lines_after=after, output=os.path.relpath(VA, REPO),
               how="cv2.remap, output row y' <- source row (y' - t) / s, Lanczos4, border replicate; x untouched")
    json.dump(rec, open(VA.replace(".png", ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(fit=rec["fit"], before=[(r["line"], r["d"]) for r in rows], after=[(r["line"], r["d"]) for r in after])))
    return float(s), float(t)


def carried_cfg(s, t):
    """CFG_M0P with every y coordinate measured on the raw carried by y' = s y + t (x unchanged)."""
    fy = lambda y: float(s * y + t)                                   # noqa: E731
    fp = lambda p: (p[0], fy(p[1]))                                   # noqa: E731
    fr = lambda r: (r[0], r[1], int(round(fy(r[2]))), int(round(fy(r[3]))))      # (x0, x1, y0, y1)  # noqa: E731
    fb = lambda b: (b[0], int(round(fy(b[1]))), b[2], int(round(fy(b[3]))))      # (x0, y0, x1, y1)  # noqa: E731
    g = copy.deepcopy(M.M0P)
    sr = g["sofa_render"]
    for k in ("back_top", "foot_r"):
        sr[k] = fy(sr[k])
    for k in ("base_l", "base_r", "feet_l", "feet_r"):
        sr[k] = fp(sr[k])
    for k in ("sofa_rect", "throw_rect", "leg_l", "leg_r", "table_rect", "bowl_rect", "holders_rect"):
        g[k] = fr(g[k])
    g["runner_poly"] = [(int(x), int(round(fy(y)))) for x, y in g["runner_poly"]]
    for k in ("table_near_line", "skirting_line", "floor_line", "rug_line"):
        g[k] = (fp(g[k][0]), fp(g[k][1]))
    tr = copy.deepcopy(M.M0P_TABLE_R)
    tr["far"], tr["foot_l"] = fy(tr["far"]), fy(tr["foot_l"])
    tex = {k: fb(v) for k, v in M.M0P_TEX.items()}
    cfg = copy.deepcopy(M.CFG_M0P)
    cfg.update(geom=g, table_r=tr, tex=tex, clay=copy.deepcopy(M.M0P_CLAY), fringe_below_base=fr(cfg["fringe_below_base"]),
               clean_decor=True, oak_tex=fb((925, 1175, 995, 1270)))
    cfg["strips"] = tuple(tuple(st[:6]) + ((int(round(st[6] * s)),) if len(st) > 6 else ()) for st in cfg["strips"])
    return cfg


def composite(s, t):
    M.FIX_SUF = "-fix3-base"
    M.RAW_OVERRIDE[JID] = VA
    M.DATE = DATE
    M.use(carried_cfg(s, t))
    try:
        note = M.fix_m0()
    finally:
        M.use(M.CFG_M0)
    p = os.path.join(OD, JID + "-fix3-base.json")
    n = json.load(open(p))
    n.update(source=os.path.relpath(VA, REPO), output=M.OUT[JID] + JID + "-fix3-base.png", clay="assets/blockout/house/framing/round5b/poses/M0p.png",
             fix3=dict(why="QA 2026-11-04-m0-fix2-cb0-g1 §2 / §8: the vertical affine on the raw before the composite; the bowl duplicated in fix",
                       vertical_affine=os.path.relpath(VA.replace(".png", ".json"), REPO)))
    json.dump(n, open(p, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(sofa=n["sofa"]["matrix"], table=n["table"]["matrix"], decor_clean=n["table"].get("decor_clean"))))
    return n


def art():
    import art_m0_12 as A
    A.BASE_SUF, A.ART_SUF, A.DATE = "-fix3-base", "-fix3", DATE
    return A.run(JID, do_lock=True)


def lock_base():
    PL = M._pipeline()
    p = os.path.join(OD, JID + "-fix3-base.png")
    lock = PL.LK.run_frame(JID, render_path=p, out_path=os.path.join(OD, JID + "-fix3-base-lock-v2.json"),
                           overlay_path=os.path.join(OD, JID + "-fix3-base-lock-v2.jpg"), date=DATE)
    s_, v = lock["summary"], lock["verdict"]
    rec = dict(shift_px=s_["register_shift_px"], scale_pct=s_["register_scale_pct"], band_after=s_["worst_band_px_after_register"],
               tile_after=s_["worst_tile_ecc_px_after_register"], fixed_edges_worst_px=s_["fixed_edges_worst_px"], fixed_ratios=s_["fixed_ratios"],
               verdict={k: v[k] for k in ("global_pass", "residual_pass", "edges_pass", "pass")},
               bands=[(b["u"], b["dx_px"], b["dy_px"], b["response"]) for b in lock["check_registered"]["bands"]])
    n = json.load(open(os.path.join(OD, JID + "-fix3-base.json")))
    n["lock_v2"] = rec
    json.dump(n, open(os.path.join(OD, JID + "-fix3-base.json"), "w"), indent=1, ensure_ascii=False)
    print("base lock", json.dumps(rec))


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    if w in ("all", "va", "composite"):
        s_, t_ = va()
    if w in ("all", "composite"):
        composite(s_, t_)
    if w in ("all", "lock"):
        lock_base()
    if w in ("all", "art"):
        art()
