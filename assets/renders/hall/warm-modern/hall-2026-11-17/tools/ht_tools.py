#!/usr/bin/env python3
"""ht_tools.py: compose and check the HT still. render-agent 2026-11-17, 0 tokens.
  compose <render_on_canvas.png> <seed_kept.png> <keep_mask.png> <out.png> [ramp=40]
      the seed (seeds.py ht: HD, HDx, base.png) pasted back over the render: ramped inside the seed where the same surface continues
      outside it (plaster 120 px, stone 12 px, living room 40 px; or one RAMP for all), hard at the architecture's edges
  check <img.png> <input.png> <keep_mask.png> <out.json>"""
import json, sys
import cv2
import numpy as np
from PIL import Image
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K, lock_tall as T
from prep_d0o import to_lin, to_srgb
CV = K.canvas("HT")
GROUPS = ((11, 82, 83, 14, 72), (94, 86), tuple(range(30, 44)) + (0,))


def cls_ht():
    c = K.clay_id("HT").copy()
    c[c == 72] = 11
    return c


RAMPS = {0: 120, 1: 12, 2: 40}      # r2: plaster 120 px (a gradual hand-over, no step), stone 12 px (the seed's own joints), living room 40


def compose(rp, sp, kp, out, ramp=None):
    r = to_lin(np.asarray(Image.open(rp).convert("RGB")).astype(np.float64) / 255)
    s = to_lin(np.asarray(Image.open(sp).convert("RGB")).astype(np.float64) / 255)
    keep = np.asarray(Image.open(kp)) > 127
    cls = cls_ht()
    dt = cv2.distanceTransform(keep.astype(np.uint8), cv2.DIST_L2, 5)
    al = keep.astype(np.float64)
    ramps = {i: (ramp if ramp else RAMPS[i]) for i in range(len(GROUPS))}
    for i, grp in enumerate(GROUPS):
        g_ = np.isin(cls, grp)
        rp_ = ramps[i]
        same = g_ & (cv2.dilate((g_ & ~keep).astype(np.uint8), np.ones((2 * rp_ + 1,) * 2, np.uint8)) > 0)
        t = np.clip(dt / rp_, 0, 1)
        al = np.where(same & keep, t * t * (3 - 2 * t), al)
    K.save_rgb(out, to_srgb(r * (1 - al[..., None]) + s * al[..., None]))
    return dict(ramps_px={"plaster": ramps[0], "stone": ramps[1], "living room": ramps[2]}, seed_exact_px=int((al >= 0.999).sum()), ramped_px=int(((al > 0) & (al < 0.999)).sum()))


def check(img, inp, kp, outp):
    cls = cls_ht()
    keep = np.asarray(Image.open(kp)) > 127
    row = lambda v: int(round(CV.box[1] + v * CV.fh))
    to_u = lambda px: (px + 0.5 - CV.box[0]) / CV.fw
    r = row(0.50)
    rr = cls[r]
    seams = [(a + b - 1) / 2 for a, b in K.runs_1d(rr, (83,))]
    edge = T.vstep_col(cls, r, (11, 82, 83), (94, 86))
    corner = T.vstep_col(cls, r, (94, 86), (12,), lo=edge)
    wal = T.vstep_col(cls, r, (12, 14, 24), (23, 20), lo=corner)
    walr = T.vstep_col(cls, r, (20, 23), (24,) + tuple(range(30, 44)) + (0,), lo=wal)
    V = {"jib door seam left (u 0.158)": (int(round(seams[0])), row(0.05), row(0.85), 10, 6),
         "jib door seam right (u 0.372)": (int(round(seams[1])), row(0.05), row(0.85), 10, 6),
         "stone edge (u 0.456)": (edge, row(0.05), row(0.90), 12, 8),
         "inside corner (u 0.790)": (corner, row(0.05), row(0.90), 12, 8),
         "return / walnut (u 0.814)": (wal, row(0.05), row(0.90), 10, 6),
         "walnut / living room (u 0.850)": (walr, row(0.05), row(0.90), 10, 6)}
    meas = K.measure_lines(img, inp, V, {}, seg=40)
    L, R = K.lum(img), K.lum(inp)
    curves = T.joint_curves(cls, (86,), (94,), edge + 4, corner - 3, 0, CV.h, min_len=150)
    for i, pts in enumerate(sorted(curves, key=lambda p: p[len(p) // 2][1])):
        meas[f"stone joint {i + 1} (clay row {pts[len(pts) // 2][1]:.0f})"] = T.measure_curve(L, R, pts)
    joints = [v["median_offset_px"] for k, v in meas.items() if "joint" in k and v["median_offset_px"] == v["median_offset_px"]]
    pos = {k: dict(clay_u=round(to_u(x), 4), still_u=round(to_u(x + meas[k]["median_offset_px"]), 4)) for k, (x, *_r) in V.items()}
    Y = K.lin_Y(img)
    lv = K.levels("HT", img, cls=K.clay_id("HT"))
    fb = (slice(int(CV.box[1]), int(CV.box[3])), slice(int(CV.box[0]), int(CV.box[2])))
    Lf = K.lstar(Y[fb])
    wal_m = np.isin(cls, (20,))
    wal_L = float(np.median(K.lstar(Y[wal_m])))
    black = float(np.percentile(Lf, 0.5))
    seam = T.seam_tone(Y, keep, cls, (11, 82, 94, 30, 32, 35))
    rep = dict(lines=meas, positions_u=pos, joints_n=len(joints), joints_worst_px=max(abs(j) for j in joints) if joints else None,
               architecture_worst_px=max(abs(meas[k]["median_offset_px"]) for k in V),
               rejection_11_5_7=dict(stone_0456_0790=[pos["stone edge (u 0.456)"], pos["inside corner (u 0.790)"]],
                                     walnut_0814_0850=[pos["return / walnut (u 0.814)"], pos["walnut / living room (u 0.850)"]],
                                     walnut_L=round(wal_L, 1), frame_L_p0_5=round(black, 1),
                                     walnut_8_above_the_grade_black_point=bool(wal_L - 14.0 >= 8),
                                     black_point_note="the black point of the door doc (10.2 item 4, ch. 2) is the grade's, L* 11-14 (WM-G1), not the frame's darkest 0.5 %, which is the walnut itself here",
                                     joints_within_3px=bool(joints and max(abs(j) for j in joints) <= 3)),
               levels=lv, seam_tone_at_the_seed_edge=seam,
               px_with_a_channel_at_255=float((np.asarray(Image.open(img).convert("RGB")).max(-1) >= 255).mean()))
    json.dump(rep, open(outp, "w"), indent=1)
    return rep


if __name__ == "__main__":
    if sys.argv[1] == "compose":
        print(json.dumps(compose(*sys.argv[2:6], *(int(x) for x in sys.argv[6:7]))))  # no ramp argument = the per-surface RAMPS
    else:
        r = check(*sys.argv[2:6])
        print(json.dumps({k: v for k, v in r.items() if k != "lines"}, indent=1))
