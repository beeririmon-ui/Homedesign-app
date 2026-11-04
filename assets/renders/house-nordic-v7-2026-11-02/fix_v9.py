#!/usr/bin/env python3
"""
fix_v9.py: the cleanup of the four 2026-11-04 code fixes per QA (qa/reports/2026-11-04-retakes-fixes-g1.md §§ 1, 3, 4; brief
briefs/render-m0-composite-and-cleanup-2026-11-04.md task 2). render-agent, 2026-11-04. 0 var2 tokens. New files only: every
output is <id>-fix2.png / -fix2.json (the QA'd <id>-fix stills stay), and its lock <id>-lock-fix2.json / .jpg.

  b1     fix_v8.fix_b1 with curtain_fill "copy_above" (the covered linen copied along its folds from above, not the column profile that
         left the rectangular patches) and holder_ratio 0.38 (the holder squashed about its base to the card's 14.5 of 38 cm; the handle
         continued down to it); the global affine as before
  w0in   fix_v8.fix_w0in with solid_basket (the basket's matte convex per row, the plant's place below row 880 cleared before the warp:
         no shifted stems in the weave, no shifted basket on the skirting); the global affine as before
  kgirl0 one vertical affine on the K-girl-0 r2 fix, fitted to the horizontal lines measured in the fix and its clay at 1080 (shelves,
         band, desk top, skirting), so the ~+0.9 % stretch goes to ~0
  b2     fix_v8.fix_b2 with fill_mode "membrane" (wall and limestone panel, the low band included, by a membrane through each surface's own
         intact boundary + its texture: no light rectangle, no lumps), a contact shadow along the basket's bottom, and the global affine as
         B1 r3 (the inverse of lock_v2's register); the storage basket unchanged
  lock   lock_v2 (edges v3) before (-fix) / after (-fix2) for the four

  python3 fix_v9.py b1 | w0in | kgirl0 | b2 | lock | all
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

DATE = "2026-11-04"
SCRIPT = "assets/renders/house-nordic-v7-2026-11-02/fix_v9.py"
F8.FIX_SUFFIX = "-fix2"
F8.SCRIPT = SCRIPT + " (fix_v8 functions, cleanup flags)"
F8.B1.update(curtain_fill="copy_above", holder_ratio=0.38)
F8.W0IN.update(solid_basket=True)
# the W0-in r2 fix's own canvas affine (QA: locked): the cleaned basket changes the ECC register (the shifted copies of the stems
# and basket were edges it fitted), and a fresh register left the desk +6 px; the geometry under the patch is the same, so the same affine
_w0 = os.path.join(VF.out_dir("pose-w0-in-v7-r2"), "pose-w0-in-v7-r2-fix.json")
if os.path.exists(_w0):
    F8.W0IN.update(global_affine_A=json.load(open(_w0))["global_affine"]["canvas_affine_inverse_map"],
                   global_affine_A_from="assets/renders/poses/nordic/v7/pose-w0-in-v7-r2-fix.json (canvas_affine_inverse_map)")
F8.B2.update(fill_mode="membrane", global_affine=True)
IDS = ["b1-v7-r3", "pose-w0-in-v7-r2", "pose-k-girl-0-v7-r2", "b2-v7-r3"]


def fix_kgirl0():
    """One vertical affine y_src = (1 + a) y' + c (output row y' takes source row y_src), a and c the least-squares fit of
    d = y_render - y_clay over the horizontal lines measured at 1080 on the frame (|d/dy| maxima in the columns named), carried to
    the canvas; Lanczos, border replicate."""
    import lock_v2 as LK
    fid = "pose-k-girl-0-v7-r2"
    frame, kind, clay_file, pan, overscan, room = VF.frame(fid)
    src_p = os.path.join(VF.out_dir(fid), fid + "-fix.png")
    a = F.load(src_p)
    H, W = a.shape[:2]
    cl = LK.load_rgb(os.path.join(VF.R4, clay_file))
    c16 = LK.pr.fit(LK.crop_frame(cl), 1920, 1080)

    def r16(img):
        return LK.pr.fit(LK.crop_frame(np.clip(img / 255.0, 0, 1).astype(np.float32)), 1920, 1080)

    def peak(img, x0, x1, y0, y1, sign):
        g = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        gy = cv2.Sobel(cv2.GaussianBlur(g, (0, 0), 1.2), cv2.CV_32F, 0, 1, ksize=3)
        p = gy[y0:y1, x0:x1].mean(1) * sign
        i = int(np.argmax(p))
        # sub-pixel (parabola through the peak)
        if 0 < i < len(p) - 1:
            den = p[i - 1] - 2 * p[i] + p[i + 1]
            off = 0.5 * (p[i - 1] - p[i + 1]) / den if den != 0 else 0.0
        else:
            off = 0.0
        return y0 + i + off
    # (name, columns, rows to search in the clay / render, edge sign)
    LINES = [("upper shelf front, bottom", (60, 200), (215, 245), -1), ("upper shelf, lower lip", (60, 200), (228, 246), 1),
             ("lower shelf front", (60, 200), (375, 395), -1), ("band top (desk wall)", (400, 1000), (365, 395), -1),
             ("desk top front", (450, 850), (675, 695), -1), ("skirting top (desk wall)", (700, 1200), (950, 980), 1)]

    def measure(img16):
        rows = []
        for nm, (x0, x1), (y0, y1), sg in LINES:
            yc = peak(c16, x0, x1, y0, y1, sg)
            yr = peak(img16, x0, x1, y0, y1, sg)
            rows.append(dict(line=nm, clay=round(float(yc), 2), render=round(float(yr), 2), d=round(float(yr - yc), 2)))
        return rows
    before = measure(r16(a))
    yc = np.array([r["clay"] for r in before])
    d = np.array([r["d"] for r in before])
    A_ = np.stack([yc, np.ones_like(yc)], 1)
    (sa, sc), *_ = np.linalg.lstsq(A_, d, rcond=None)              # d = sa * y + sc  (1080 rows of the frame)
    # canvas: y_1080 = (y_c - fy0) / sy
    fx0, fy0, fx1, fy1 = VF.frame_box_px(W, H)
    sy = (fy1 - fy0) / 1080.0
    ys = np.arange(H, dtype=np.float64)
    y16 = (ys - fy0) / sy
    src16 = y16 + (sa * y16 + sc)
    src = src16 * sy + fy0
    mapy = np.repeat(src[:, None], W, 1).astype(np.float32)
    mapx = np.repeat(np.arange(W, dtype=np.float32)[None, :], H, 0)
    out = cv2.remap(a.astype(np.float32), mapx, mapy, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    out = np.clip(out, 0, 255)
    F.save(out, os.path.join(VF.out_dir(fid), fid + "-fix2.png"))
    after = measure(r16(out))
    note = dict(asset_id=fid, date=DATE, script=SCRIPT, tokens=0,
                fix="K-girl-0 r2 fix + one vertical affine (QA 2026-11-04-retakes-fixes-g1: the ~+0.9 % vertical stretch, 0 tokens)",
                source=os.path.relpath(src_p, VF.REPO), output=os.path.relpath(os.path.join(VF.out_dir(fid), fid + "-fix2.png"), VF.REPO),
                fit_1080=dict(stretch_pct=round(sa * 100, 3), offset_px=round(sc, 2), how="d = y_render - y_clay = a y + c, least squares over the lines"),
                lines_1080_before=before, lines_1080_after=after,
                how="output row y' takes source row y' + a y' + c (frame rows at 1080, carried to the canvas), cv2.remap Lanczos4, border replicate; x untouched")
    json.dump(note, open(os.path.join(VF.out_dir(fid), fid + "-fix2.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(fit=note["fit_1080"], before=[(r["line"], r["d"]) for r in before], after=[(r["line"], r["d"]) for r in after]), indent=1))
    return note


def lock_all(ids=IDS):
    import lock_v2 as L
    import lock_fixes_v8 as LF
    recs = {}
    for fid in ids:
        od = VF.out_dir(fid)
        fix1, fix2 = os.path.join(od, fid + "-fix.png"), os.path.join(od, fid + "-fix2.png")
        tmp = os.path.join(od, fid + "-lock-fix2.tmp.json")
        before = L.run_frame(fid, render_path=fix1, out_path=tmp, edges_mode="v3", date=DATE)
        after = L.run_frame(fid, render_path=fix2, out_path=tmp, overlay_path=os.path.join(od, fid + "-lock-fix2.jpg"), edges_mode="v3", date=DATE)
        os.remove(tmp)
        named = {}
        for nm, b in (before.get("named_edges") or {}).items():
            a_ = after["named_edges"][nm]
            named[nm] = dict(clay_px=b["clay_px"], fix=b["d_xcorr_px"], fix2=a_["d_xcorr_px"], r_fix2=a_["r"], counted=a_["counted"],
                             **({"eye_override": a_["eye_override"]} if "eye_override" in a_ else {}))
        rec = dict(asset_id=fid, date=DATE, tokens=0, script=SCRIPT, method="lock_v2.py edges v3",
                   before=dict(still=os.path.relpath(fix1, VF.REPO), **LF.brief(before)), after=dict(still=os.path.relpath(fix2, VF.REPO), **LF.brief(after)),
                   named_edges=named, overlay=os.path.relpath(os.path.join(od, fid + "-lock-fix2.jpg"), VF.REPO), full_after=after)
        json.dump(rec, open(os.path.join(od, fid + "-lock-fix2.json"), "w"), indent=1, ensure_ascii=False)
        b_, a_ = rec["before"], rec["after"]
        print(f"--- {fid}: fix shift {b_['register_shift_px']} scale {b_['register_scale_pct']} band {b_['worst_band_px_after_register']} tile {b_['worst_tile_px_after_register']} "
              f"pass {b_['pass']}  ->  fix2 shift {a_['register_shift_px']} scale {a_['register_scale_pct']} band {a_['worst_band_px_after_register']} "
              f"tile {a_['worst_tile_px_after_register']} named {a_['named_edges_worst_px']} pass {a_['pass']}")
        recs[fid] = rec
    return recs


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("b1", "all"):
        F8.fix_b1()
    if which in ("w0in", "all"):
        F8.fix_w0in()
    if which in ("kgirl0", "all"):
        fix_kgirl0()
    if which in ("b2", "all"):
        F8.fix_b2()
    if which in ("lock", "all"):
        lock_all()
