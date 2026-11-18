#!/usr/bin/env python3
"""
tone.py: the WM-G1 display toe on HC and inside HDx2's console mask (master-designer 12.7.1 and 12.7.3), render-agent 2026-11-18. 0 tokens.
The curve QA approved on the bath plate (assets/renders/bath/warm-modern/stage1-2026-11-17/tools/grade_plate.py, QA round 2, BP-M1):
  - L*: f(L) = L + A (1 - L/30)^2 below the knee 30, identity above. f'(L) = 1 - (2A/30)(1 - L/30): never above 1, continuous at the knee,
    and positive at black for A < 15 (monotonic, so every percentile maps through f exactly)
  - chroma lifts with the lightness: a*, b* += (f(L) - L) * (5.1, 6.4) / 14.4, base.png's walnut in shadow, fading to 0 at the knee
  - pointwise only: no blur, no neighbourhood; the same pixel gives the same result in every asset
  hc    A = 9.0 on the whole canvas: the black point lands in L* 11-14 under every convention in use (the frame's p0.1 6.14 -> 11.83,
        its p0.5 9.45 -> 13.67, the canvas p0.1 4.93 -> 11.30). The raw is kept as hc-raw.png.
  hdx2  inside hdx2-mask.png only (the console and its shadow on the plaster; the plaster is above the knee, so only the walnut moves):
        A set so that the console's crushed drum (p2 5.76) reaches the frame's p0.1 outside the mask + 8 L* (4.62 + 8 = 12.62).
        The pre-tone still is kept as sources/hdx2-pre-tone.png.
  python3 tone.py hc   <hc-raw.png> <hc.png> <hc-grade.json>
  python3 tone.py hdx2 <hdx2-pre.png> <hdx2.png> <hdx2-console-grade.json>
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402

KNEE = 30.0
CHROMA = (5.1 / 14.4, 6.4 / 14.4)


def lab(rgb):
    return K.lab_from_lin(K.to_lin(rgb))


def apply(rgb, A, mask=None):
    """rgb in 0-1. Returns the toned image and the pixels that moved."""
    lb = lab(rgb)
    L = lb[..., 0]
    m = L < KNEE
    if mask is not None:
        m &= mask
    Lm = L[m]
    lift = A * (1 - Lm / KNEE) ** 2
    new = lb[m].copy()
    new[:, 0] = Lm + lift
    new[:, 1] += lift * CHROMA[0]
    new[:, 2] += lift * CHROMA[1]
    out = rgb.copy()
    out[m] = K.to_srgb(K.lin_from_lab(new))
    return out, m


def f(L, A):
    return np.where(L < KNEE, L + A * (1 - L / KNEE) ** 2, L)


def frame_box(name):
    cv = K.canvas(name)
    x0, y0, x1, y1 = (int(round(v)) for v in cv.box)
    m = np.zeros((cv.h, cv.w), bool)
    m[y0:y1, x0:x1] = True
    return m


def pct(L, m, q):
    return round(float(np.percentile(L[m], q)), 2)


def hc(raw, outp, gp, A=9.0):
    a8 = K.rgb8(raw)
    rgb = a8 / 255.0
    L0 = lab(rgb)[..., 0]
    fr = frame_box("HC")
    allm = np.ones_like(fr)
    out, moved = apply(rgb, A)
    o8 = np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)
    K.save(outp, o8)
    L1 = lab(K.rgb8(outp) / 255.0)[..., 0]
    above = L0 >= KNEE
    rep = dict(curve=dict(A=A, knee=KNEE, chroma_per_lift=[round(c, 4) for c in CHROMA], slope_at_black=round(1 - 2 * A / KNEE, 3)),
               scope="the whole canvas", px_moved=int(moved.sum()),
               before=dict(frame_p01=pct(L0, fr, 0.1), frame_p05=pct(L0, fr, 0.5), frame_p1=pct(L0, fr, 1), canvas_p01=pct(L0, allm, 0.1)),
               after=dict(frame_p01=pct(L1, fr, 0.1), frame_p05=pct(L1, fr, 0.5), frame_p1=pct(L1, fr, 1), canvas_p01=pct(L1, allm, 0.1)),
               above_knee_max_diff_levels=int(np.abs(o8.astype(int) - a8.astype(int))[above].max()), target="black point L* 11-14 (12.7.1)")
    K.dump(gp, rep)
    print(rep)


def hdx2(pre, outp, gp):
    a8 = K.rgb8(pre)
    rgb = a8 / 255.0
    L0 = lab(rgb)[..., 0]
    mask = K.rgb8(os.path.join(K.OUT, "hdx2-mask.png"))[..., 0] > 127
    fr = frame_box("HDx")
    cls = K.clay_id("HDx")
    obj = cls == K.CONSOLE_ID
    P, ok = K.world("HDx")
    drum = obj & (P[..., 2] < 0.745)
    bp = pct(L0, fr & ~mask, 0.1)
    p2 = float(np.percentile(L0[drum], 2))
    target = bp + 8.0
    A = (target - p2) / (1 - p2 / KNEE) ** 2
    A = float(min(max(A, 0.0), 14.5))
    out, moved = apply(rgb, A, mask)
    o8 = np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)
    o8[~mask] = a8[~mask]
    K.save(outp, o8)
    L1 = lab(K.rgb8(outp) / 255.0)[..., 0]
    n = None
    try:
        from prep_ht2 import normals
        n = normals("HDx")
    except Exception:
        pass
    Z = P[..., 2]
    parts = dict(drum=drum, console=obj)
    if n is not None:
        parts.update({"top front edge": obj & (n[..., 1] > 0.7) & (Z >= 0.745), "top surface": obj & (n[..., 2] > 0.7),
                      "end face": obj & (n[..., 0] < -0.7) & (Z >= 0.745)})
    rep = dict(curve=dict(A=round(A, 3), knee=KNEE, chroma_per_lift=[round(c, 4) for c in CHROMA], slope_at_black=round(1 - 2 * A / KNEE, 3)),
               scope="hdx2-mask.png only (the console and its 12 px ring; nothing outside it moves)", px_moved=int(moved.sum()),
               frame_black_point_outside_mask=dict(p01=bp, p05=pct(L0, fr & ~mask, 0.5)),
               target=f"drum p2 >= frame p0.1 outside the mask + 8 = {round(target, 2)} (the coordinator); 12.7.3: console p2 >= that p0.1, drum median >= it + 8",
               outside_mask_max_diff_levels=int(np.abs(o8.astype(int) - a8.astype(int))[~mask].max()),
               parts={k: dict(before_median=round(float(np.median(L0[m])), 2), after_median=round(float(np.median(L1[m])), 2),
                              before_p2=round(float(np.percentile(L0[m], 2)), 2), after_p2=round(float(np.percentile(L1[m], 2)), 2)) for k, m in parts.items()})
    K.dump(gp, rep)
    print(rep)


if __name__ == "__main__":
    {"hc": hc, "hdx2": hdx2}[sys.argv[1]](*sys.argv[2:5])
