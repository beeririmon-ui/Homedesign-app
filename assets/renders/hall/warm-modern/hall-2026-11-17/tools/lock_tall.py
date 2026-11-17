#!/usr/bin/env python3
"""
lock_tall.py: lines, seed paste and seams for the stills on the tall 3:2 canvas (HDx, HD) and for HT. render-agent 2026-11-17.
0 tokens.

Lines come from the clay's id pass of the still. A "curve" line (a stone joint seen at an angle) is followed column by column:
its centre row per column comes from the id pass, the across-line profile (vertical) is taken at that row, and segments of
columns are registered against the model input (whose geometry is the clay's).
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from PIL import Image

import hallkit as K


def joint_curves(cls, ids_joint, ids_face, x0, x1, y0, y1, min_len=120, max_run=8, max_dy=3):
    """Joints (id in ids_joint) that run across the face: tracked column by column from the id pass. In each column the
    runs of the joint id no longer than max_run px are centres; a centre continues a track when it lies within max_dy px
    of the track's last centre in the previous column. Long runs (vertical joints) are skipped. Returns [(x, yc)] arrays."""
    tracks, live = [], []
    for x in range(x0, x1):
        col = np.isin(cls[y0:y1, x], ids_joint).astype(np.int8)
        d = np.diff(np.concatenate([[0], col, [0]]))
        s_, e_ = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        cents = [y0 + (a + b - 1) / 2.0 for a, b in zip(s_, e_) if b - a <= max_run]
        new_live = []
        used = set()
        for t in live:
            ly = t[-1][1]
            best = None
            for j, c in enumerate(cents):
                if j not in used and abs(c - ly) <= max_dy and (best is None or abs(c - ly) < abs(cents[best] - ly)):
                    best = j
            if best is not None:
                t.append((x, cents[best]))
                used.add(best)
                new_live.append(t)
            else:
                tracks.append(t)
        for j, c in enumerate(cents):
            if j not in used:
                new_live.append([(x, c)])
        live = new_live
    tracks += live
    return [np.array(t) for t in tracks if len(t) >= min_len]


def measure_curve(L, R, pts, seg=40, half=8, maxs=4):
    """pts: (x, yc) per column. Profiles (vertical, +-half) at round(yc) per column, averaged over segments of columns
    after aligning each column at its own centre. Returns the median offset (image - ref, px) and stats."""
    offs, cs = [], []
    for s in range(0, len(pts) - seg + 1, seg):
        pa, pb = [], []
        for x, yc in pts[s:s + seg]:
            x = int(x)
            yi = int(round(yc))
            if yi - half < 0 or yi + half + 1 > L.shape[0]:
                continue
            pa.append(R[yi - half:yi + half + 1, x])
            pb.append(L[yi - half:yi + half + 1, x])
        if len(pa) < seg // 2:
            continue
        o, c = K._shift(np.mean(pa, 0), np.mean(pb, 0), maxs)
        if c > 0.5:
            offs.append(o)
            cs.append(c)
    a = np.array(offs) if offs else np.array([np.nan])
    return dict(kind="joint (followed per column)", n=len(offs), median_offset_px=round(float(np.nanmedian(a)), 2),
                p90_abs_px=round(float(np.nanpercentile(np.abs(a), 90)), 2) if offs else None,
                mean_corr=round(float(np.mean(cs)), 3) if cs else None,
                clay_row_mid=round(float(pts[len(pts) // 2][1]), 1), cols=[int(pts[0][0]), int(pts[-1][0])])


def vstep_col(cls, row, a, b, lo=0, hi=None):
    r = cls[row]
    hi = len(r) - 1 if hi is None else hi
    for x in range(lo, hi):
        if r[x] in a and r[x + 1] in b:
            return x + 1
    return None


def paste_seed(model, seed, keep, cls, living_ids, hard_near_ids_px=6, feather_sigma=3.0, hard_ids=(), hard_pad=30):
    """model, seed: float RGB (0-1) on the same canvas; keep: bool mask of the seed to keep.
    Hard edge where the seed meets surfaces that are not `living_ids` (a real edge of the architecture); feathered where
    it meets the model's own continuation of the same surfaces."""
    other = ~np.isin(cls, living_ids)
    near_other = cv2.dilate(other.astype(np.uint8), np.ones((2 * hard_near_ids_px + 1,) * 2, np.uint8)) > 0
    inner = cv2.erode(keep.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
    soft = cv2.GaussianBlur(inner, (0, 0), feather_sigma)
    soft = np.where(keep, np.maximum(soft, 0), 0)
    alpha = np.where(near_other, keep.astype(np.float32), soft)
    alpha = np.where(keep & ~near_other & (cv2.erode(keep.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0), 1.0, alpha)
    if hard_ids:
        # around objects (the products): a hard paste, so that the model's own legs and edges never ghost through
        near_obj = cv2.dilate(np.isin(cls, hard_ids).astype(np.uint8), np.ones((2 * hard_pad + 1,) * 2, np.uint8)) > 0
        alpha = np.where(near_obj, keep.astype(np.float32), alpha)
    return model * (1 - alpha[..., None]) + seed * alpha[..., None], alpha


def seam_tone(img_lin_Y, keep, cls, ids, band=6, gap=3):
    """Tone across the boundary of `keep` per surface id: median Y in a band just inside vs just outside (with a gap),
    as a ratio. Only where the boundary lies inside one surface (not at an architectural edge)."""
    k = keep.astype(np.uint8)
    ins = (cv2.erode(k, np.ones((2 * gap + 1,) * 2, np.uint8)) > 0) & ~(cv2.erode(k, np.ones((2 * (gap + band) + 1,) * 2, np.uint8)) > 0)
    outs = (cv2.dilate(k, np.ones((2 * (gap + band) + 1,) * 2, np.uint8)) > 0) & ~(cv2.dilate(k, np.ones((2 * gap + 1,) * 2, np.uint8)) > 0)
    res = {}
    for i in ids:
        a, b = ins & (cls == i), outs & (cls == i)
        if a.sum() > 300 and b.sum() > 300:
            r = float(np.median(img_lin_Y[a]) / np.median(img_lin_Y[b]))
            res[int(i)] = dict(inside_seed_over_outside=round(r, 4), pct=round(100 * (r - 1), 2), px=[int(a.sum()), int(b.sum())])
    return res
