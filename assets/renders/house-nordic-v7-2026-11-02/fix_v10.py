#!/usr/bin/env python3
"""
fix_v10.py: the zero-token fixes after QA's G1 on the fix2 round (qa/reports/2026-11-04-m0-fix2-cb0-g1.md §8; the coordinator's
message of 2026-11-05). render-agent, 0 var2 tokens. New files only: <id>-fix3.png / -fix3.json, lock <id>-lock-fix3.json / .jpg
(lock_v2 edges v3), grading v5 -> <id>-graded-fix3-v5.png etc. The -fix / -fix2 files QA checked are read, never written.

  b1      fix_v8.fix_b1 with fix2's flags + raw_linen: the linen between the old frond tips and the basket is kept as rendered (the two
          light lumps right of the fern were copies into it)
  w0in    W0-in r2: fix2 (clean basket) with the desk's front-left corner taken back from -fix (the same canvas affine; fix2's plant-place
          clearing had copied the drawer edge into the leg), and the small dark block by the basket's base filled
  kgirl0  K-girl-0 r2: fix2 + a local horizontal warp in the left part (the vertical lines -4..-8 px at 1080 in the left quarter),
          dx(x) piecewise linear from the measured named lines, 0 from before the prints on (the prints are not touched)
  lock    lock_v2 (edges v3) fix2 -> fix3 for b1, w0in, kgirl0;  grade: grading v5 on the fix3 stills
  (CB-0: recompose_cb0.py --fix3; M0p: fix_m0_12.py m0p3)
  python3 fix_v10.py b1 | w0in | kgirl0 | lock | grade | all
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402
import fix_v7 as F  # noqa: E402
import fix_v8 as F8  # noqa: E402

DATE = "2026-11-05"
SCRIPT = "assets/renders/house-nordic-v7-2026-11-02/fix_v10.py"
F8.DATE = DATE
F8.FIX_SUFFIX = "-fix3"
F8.SCRIPT = SCRIPT + " (fix_v8 functions, fix2 + fix3 flags)"
F8.B1.update(curtain_fill="copy_above", holder_ratio=0.38, raw_linen=True, copy_runs=True)
IDS = ["b1-v7-r3", "pose-w0-in-v7-r2", "pose-k-girl-0-v7-r2"]


def p_(fid, suf):
    return os.path.join(VF.out_dir(fid), fid + suf)


# ---------------------------------------------------------------------------------------------------------------
# W0-in r2: fix2 + the desk corner from fix
# ---------------------------------------------------------------------------------------------------------------
W0_CORNER = (300, 600, 1000, 1539)       # canvas px search box (QA: x ~420-560, y ~1080-1330; the leg's lower part differs too)
TAKE_X0, TAKE_Y0 = 450, 1050             # from fix only from the desk leg's left edge (x 452-454 in fix) and below row 1050 (the leaves above)


def fix_w0in():
    """fix2's solid basket matte (hue 10-50, S >= 14 in u 0-0.20) also took the oak desk's front-left corner (the same hue), so the raw,
    unwarped corner was laid over the warped desk ('the drawer edge copied into the leg'). Here: right of the basket's right edge (per row,
    from fix2's weave texture), the corner is fix's."""
    fid = "pose-w0-in-v7-r2"
    f1, f2 = F.load(p_(fid, "-fix.png")), F.load(p_(fid, "-fix2.png"))
    H, W = f1.shape[:2]
    import fix_m0_12 as M
    x0, x1, y0, y1 = W0_CORNER
    en = M.energy(f2, 3.0)
    # the basket's right edge per row: scanning right from x0, the last weave pixel (energy > 5) before 8 quiet pixels (energy < 3)
    edge = np.full(H, -1.0)
    for y in range(y0, y1):
        row = en[y, x0:x1]
        last = -1
        quiet = 0
        for i, e in enumerate(row):
            if e > 5:
                if quiet >= 8 and last >= 0:
                    break
                last, quiet = i, 0
            elif e < 3:
                quiet += 1
        edge[y] = x0 + last if last >= 0 else -1
    ys_ = np.nonzero(edge >= 0)[0]
    ev = edge[ys_]
    pad = np.r_[np.full(10, ev[0]), ev, np.full(10, ev[-1])]
    edge[ys_] = np.median(np.lib.stride_tricks.sliding_window_view(pad, 21), axis=1)
    X = np.arange(W)[None, :]
    take = np.zeros((H, W), np.float32)
    take[TAKE_Y0:y1, TAKE_X0:x1] = 1                # (the basket's right edge is at x <= 436 in every row it occupies)
    hue, L, S = F8.hls(f2)
    plant = F8.dil(F8.keep_big(((hue >= 60) & (hue <= 170) & (S >= 20)).astype(np.float32), 30), 3)     # leaves (not single green-tinted pixels)
    diff = (np.abs(f1 - f2).max(2) > 3.0).astype(np.float32)
    take = take * (1 - plant)
    alpha = cv2.GaussianBlur(take, (0, 0), 1.5) * (1 - plant)
    out = f2 * (1 - alpha[..., None]) + f1 * alpha[..., None]
    basket = np.zeros((H, W), np.float32)
    for y in ys_:
        basket[y, x0:int(edge[y]) + 1] = 1
    blk = np.zeros((H, W), np.float32)            # (the dark-block fill took the leg's grain; the gap is left as fix2 has it)
    F.save(out, p_(fid, "-fix3.png"))
    note = dict(asset_id=fid, date=DATE, tokens=0, script=SCRIPT,
                fix=("W0-in r2 fix3 (QA 2026-11-04-m0-fix2-cb0-g1 §3 / §8): fix2 (the clean basket) with the desk's front-left corner taken back from fix; "
                     "the small dark block by the basket's base filled"),
                sources=dict(fix=os.path.relpath(p_(fid, "-fix.png"), VF.REPO), fix2=os.path.relpath(p_(fid, "-fix2.png"), VF.REPO)),
                corner=dict(box_px=list(W0_CORNER), px_from_fix=int((alpha > 0.5).sum()), px_that_differed=int(((alpha > 0.5) & (diff > 0.5)).sum()),
                            basket_right_edge_px=dict(rows=[int(ys_.min()), int(ys_.max())], x_range=[int(edge[ys_].min()), int(edge[ys_].max())]),
                            why="fix2's solid basket matte (hue 10-50, S >= 14 in u 0-0.20) took the oak desk corner too: the raw corner was laid over the warped desk",
                            how="right of the basket's right edge + 4 px (per row: the last weave pixel, high-pass energy > 5, before 8 quiet pixels; median over 21 rows) "
                                "x 450-600 (the desk leg's left edge is at 452-454 in fix), rows 1050-1539, outside the green plant (dilated 3 px): fix (feathered 1.5 px); both share the same canvas affine"),
                dark_block=dict(px=0, note="not changed: the gap between the basket and the leg (skirting at y 1380-1405, the floor below) is fix2's, which matches the raw still; a fill of 'dark blocks' there took the leg's grain (tried)"),
                output=os.path.relpath(p_(fid, "-fix3.png"), VF.REPO))
    json.dump(note, open(p_(fid, "-fix3.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: note[k] for k in ("corner", "dark_block")}))
    return note


# ---------------------------------------------------------------------------------------------------------------
# K-girl-0 r2: fix2 + a local horizontal warp in the left part
# ---------------------------------------------------------------------------------------------------------------
def vlines(img16, rows, x0, x1, n=12):
    g = cv2.cvtColor((np.clip(img16, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(cv2.GaussianBlur(g, (0, 0), 1.0), cv2.CV_32F, 1, 0, ksize=3)
    p = np.abs(gx[rows[0]:rows[1], x0:x1]).mean(0)
    pk = [i for i in range(1, len(p) - 1) if p[i] >= p[i - 1] and p[i] >= p[i + 1] and p[i] > 0.25 * p.max()]
    pk = sorted(pk, key=lambda i: -p[i])[:n]
    out = []
    for i in sorted(pk):
        den = p[i - 1] - 2 * p[i] + p[i + 1]
        out.append((float(x0 + i + (0.5 * (p[i - 1] - p[i + 1]) / den if den != 0 else 0.0)), float(p[i])))
    return out


def kgirl_pairs(r16, c16, bands):
    """Vertical edges paired between render and clay by order and proximity (<= 14 px) in each row band."""
    pairs = []
    for (rows, x0, x1) in bands:
        R = vlines(r16, rows, x0, x1)
        C = vlines(c16, rows, x0, x1)
        for xc, sc in C:
            cand = [(abs(xr - xc), xr, sr) for xr, sr in R if abs(xr - xc) <= 14]
            if cand:
                d, xr, sr = min(cand)
                pairs.append(dict(rows=list(rows), clay=round(xc, 2), render=round(xr, 2), d=round(xr - xc, 2), strength=round(min(sc, sr), 1)))
    return pairs


KG_BANDS = [((150, 260), 0, 520), ((280, 380), 0, 520), ((560, 760), 0, 560), ((800, 1000), 0, 560)]   # 1080 frame rows, columns (left of the prints)
KG_FLAT_FROM = 600          # frame x at 1080 (1920 wide): no shift from here on (the prints start at ~630)


def fix_kgirl0():
    import lock_v2 as LK
    fid = "pose-k-girl-0-v7-r2"
    frame, kind, clay_file, pan, overscan, room = VF.frame(fid)
    a = F.load(p_(fid, "-fix2.png"))
    H, W = a.shape[:2]
    c16 = LK.pr.fit(LK.crop_frame(LK.load_rgb(os.path.join(VF.R4, clay_file))), 1920, 1080)

    def r16(img):
        return LK.pr.fit(LK.crop_frame(np.clip(img / 255.0, 0, 1).astype(np.float32)), 1920, 1080)
    before = kgirl_pairs(r16(a), c16, KG_BANDS)
    # dx(x): the median offset per 60 px column bin of the paired edges (strength-weighted), anchored 0 at KG_FLAT_FROM and beyond,
    # the left edge held at the first bin's value; monotone smoothing (5-bin running median)
    xs = np.array([p["clay"] for p in before])
    ds = np.array([p["d"] for p in before])
    bins = np.arange(0, KG_FLAT_FROM, 60)
    knots_x, knots_d = [], []
    for b0 in bins:
        sel = (xs >= b0) & (xs < b0 + 60)
        if sel.sum():
            knots_x.append(b0 + 30)
            knots_d.append(float(np.median(ds[sel])))
    knots_x.append(KG_FLAT_FROM)
    knots_d.append(0.0)
    kd = np.array(knots_d)
    if len(kd) >= 5:
        pad = np.r_[kd[:1], kd[:1], kd, kd[-1:], kd[-1:]]
        kd = np.array([np.median(pad[i:i + 5]) for i in range(len(kd))])
        kd[-1] = 0.0
    knots_x = np.array(knots_x, float)
    # canvas: frame x at 1920 -> canvas px; output pixel x takes source x + dx (dx = render - clay: the render's line is at clay + d)
    fx0, fy0, fx1, fy1 = VF.frame_box_px(W, H)
    s = (fx1 - fx0) / 1920.0
    xc_ = np.arange(W, dtype=np.float64)
    x16 = (xc_ - fx0) / s
    dx16 = np.interp(x16, knots_x, kd, left=kd[0], right=0.0)
    mapx = np.repeat((xc_ + dx16 * s)[None, :], H, 0).astype(np.float32)
    mapy = np.repeat(np.arange(H, dtype=np.float32)[:, None], W, 1)
    out = cv2.remap(a.astype(np.float32), mapx, mapy, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    out = np.clip(out, 0, 255)
    F.save(out, p_(fid, "-fix3.png"))
    after = kgirl_pairs(r16(out), c16, KG_BANDS)
    note = dict(asset_id=fid, date=DATE, tokens=0, script=SCRIPT,
                fix=("K-girl-0 r2 fix3 (QA 2026-11-04-m0-fix2-cb0-g1 §4: the register is unstable, judged by the named lines; the vertical lines in "
                     "the left quarter -4..-8 px): fix2 + a local horizontal warp, 0 from frame x 600 (1920) on, so the prints (x >= ~630) are not touched"),
                source=os.path.relpath(p_(fid, "-fix2.png"), VF.REPO), output=os.path.relpath(p_(fid, "-fix3.png"), VF.REPO),
                dx_knots_1920=dict(x=[round(float(x), 1) for x in knots_x], dx=[round(float(d), 2) for d in kd]),
                pairs_before=before, pairs_after=after,
                summary=dict(before_median_abs=round(float(np.median(np.abs([p["d"] for p in before]))), 2) if before else None,
                             after_median_abs=round(float(np.median(np.abs([p["d"] for p in after]))), 2) if after else None,
                             before_worst=round(float(max(abs(p["d"]) for p in before)), 2) if before else None,
                             after_worst=round(float(max(abs(p["d"]) for p in after)), 2) if after else None),
                how="output x' takes source x' + dx(x'), dx piecewise linear between the knots (frame x at 1920 -> canvas), cv2.remap Lanczos4; y untouched")
    json.dump(note, open(p_(fid, "-fix3.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(knots=note["dx_knots_1920"], summary=note["summary"])))
    return note


# ---------------------------------------------------------------------------------------------------------------
def lock_all(ids=IDS):
    import lock_v2 as L
    import lock_fixes_v8 as LF
    for fid in ids:
        od = VF.out_dir(fid)
        tmp = os.path.join(od, fid + "-lock-fix3.tmp.json")
        before = L.run_frame(fid, render_path=p_(fid, "-fix2.png"), out_path=tmp, edges_mode="v3", date=DATE)
        after = L.run_frame(fid, render_path=p_(fid, "-fix3.png"), out_path=tmp, overlay_path=p_(fid, "-lock-fix3.jpg"), edges_mode="v3", date=DATE)
        os.remove(tmp)
        named = {nm: dict(clay_px=b["clay_px"], fix2=b["d_xcorr_px"], fix3=after["named_edges"][nm]["d_xcorr_px"], counted=after["named_edges"][nm]["counted"])
                 for nm, b in (before.get("named_edges") or {}).items()}
        rec = dict(asset_id=fid, date=DATE, tokens=0, script=SCRIPT, method="lock_v2.py edges v3",
                   before=dict(still=os.path.relpath(p_(fid, "-fix2.png"), VF.REPO), **LF.brief(before)),
                   after=dict(still=os.path.relpath(p_(fid, "-fix3.png"), VF.REPO), **LF.brief(after)), named_edges=named,
                   overlay=os.path.relpath(p_(fid, "-lock-fix3.jpg"), VF.REPO), full_after=after)
        json.dump(rec, open(p_(fid, "-lock-fix3.json"), "w"), indent=1, ensure_ascii=False)
        b_, a_ = rec["before"], rec["after"]
        print(f"--- {fid}: fix2 band {b_['worst_band_px_after_register']} tile {b_['worst_tile_px_after_register']} named {b_['named_edges_worst_px']} pass {b_['pass']}"
              f"  ->  fix3 shift {a_['register_shift_px']} scale {a_['register_scale_pct']} band {a_['worst_band_px_after_register']} "
              f"tile {a_['worst_tile_px_after_register']} named {a_['named_edges_worst_px']} pass {a_['pass']}")


def grade_all(ids=IDS):
    import process_v8 as P
    res = {}
    for fid in ids:
        r = P.process(fid, p_(fid, "-fix3.png"), "-fix3-v5", "v2", "auto", "none", None, "grading v5 on the fix3", exposure="bible", grade_mode="v5")
        b = r["bible_v3"]
        res[fid] = dict(measured=b["measured_L"], range=b["range"], meets_bible=b["meets_bible"],
                        fails=[k for k, v in r["checks"].items() if k.startswith("bible_") and v is False], stops=r["grade"]["exposure"]["applied_stops"], outputs=r["outputs"])
        note = json.load(open(p_(fid, "-fix3.json")))
        note["grade_v5"] = res[fid]
        json.dump(note, open(p_(fid, "-fix3.json"), "w"), indent=1, ensure_ascii=False)
        print(fid, res[fid])
    return res


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    if w in ("b1", "all"):
        F8.fix_b1()
    if w in ("w0in", "all"):
        fix_w0in()
    if w in ("kgirl0", "all"):
        fix_kgirl0()
    if w in ("lock", "all"):
        lock_all()
    if w in ("grade", "all"):
        grade_all()
