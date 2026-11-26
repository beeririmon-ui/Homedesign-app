#!/usr/bin/env python3
"""prints.py: the three prints set into the hero's blank canvases in code (0 tokens; proposal 3.2 item 8, as MB0 / MB1). The model drew
three blank sand canvases (#D8C8AE) in slim walnut frames. Per frame: the canvas is found in the hero itself (the sand pixels inside
the projected frame; its four corners from the mask), the flat print of the SKU (TL2356-1 / -2 / -3: the card's sku images, cropped
to the print) is laid on that quad by a homography and multiplied by the canvas's own light in the hero (its linear colour over the
sand's, 1.5 px blur): the sun's gradient, the glazing bars' bands, the leaf shadow and the wall lights' wash pass over the print.
Only canvas pixels change. Works on the raw (ungraded) hero; the one grade comes after."""
import os

import cv2
import numpy as np

import hwlib as L
import guide_hw_geom as GG

CANVAS_ALBEDO = np.float32([216, 200, 174]) / 255.0


def _fit_line(pts):
    vx, vy, x0, y0 = cv2.fitLine(np.float32(pts), cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
    return np.float64([x0, y0]), np.float64([vx, vy])


def _meet(l1, l2):
    (p, d), (q, e) = l1, l2
    A = np.array([[d[0], -e[0]], [d[1], -e[1]]])
    t = np.linalg.solve(A, q - p)
    return p + t[0] * d


def find_canvas(lab, outer, inner):
    """the canvas inside one frame, found in the hero itself: the light region around the projected canvas's core that the darker walnut
    moulding closes (a flood over 'not darker than the canvas by 16 L*', inside the projected frame grown 14 px). Its four edges are
    lines fitted to the region's boundary near each projected edge; the corners are where they meet. A leak (the moulding open) or a
    poor fit falls back to the projected quad."""
    H, W = lab.shape[:2]
    inner = np.float32(inner)
    mi = GG.quad_mask(inner, (H, W)) > 0.5
    core = cv2.erode(mi.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    grow = cv2.dilate((GG.quad_mask(outer, (H, W)) > 0.5).astype(np.uint8), np.ones((29, 29), np.uint8)).astype(bool)
    Lloc = cv2.GaussianBlur(np.where(core, lab[..., 0], 0).astype(np.float32), (0, 0), 30) / np.maximum(
        cv2.GaussianBlur(core.astype(np.float32), (0, 0), 30), 1e-3)
    Lloc = np.where(cv2.GaussianBlur(core.astype(np.float32), (0, 0), 30) > 0.02, Lloc, float(np.median(lab[..., 0][core])))
    light = grow & (lab[..., 0] > Lloc - 16.0)
    light = cv2.morphologyEx(light.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lb = cv2.connectedComponents(light, connectivity=4)
    ids = np.unique(lb[core])
    ids = ids[ids > 0]
    m = np.isin(lb, ids)
    info = dict(found_px=int(m.sum()), projected_px=int(mi.sum()))
    if m.sum() > 1.2 * mi.sum() or m.sum() < 0.75 * mi.sum():
        info["fallback"] = "the projected canvas (the found region leaks or is too small)"
        return mi, inner, info
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    bd = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    ys, xs = np.where(bd)
    pts = np.stack([xs, ys], 1).astype(np.float64)
    lines = []
    for i in range(4):
        p0, p1 = inner[i].astype(np.float64), inner[(i + 1) % 4].astype(np.float64)
        d = (p1 - p0) / np.linalg.norm(p1 - p0)
        nrm = np.array([-d[1], d[0]])
        rel = pts - p0
        along, off = rel @ d, rel @ nrm
        ln = np.linalg.norm(p1 - p0)
        sel = (np.abs(off) < 14) & (along > 0.12 * ln) & (along < 0.88 * ln)
        if sel.sum() < 0.4 * ln:
            lines.append((p0, d))
            info.setdefault("edges_from_projection", []).append(i)
        else:
            lines.append(_fit_line(pts[sel]))
    quad = np.float32([_meet(lines[3], lines[0]), _meet(lines[0], lines[1]), _meet(lines[1], lines[2]), _meet(lines[2], lines[3])])
    if np.abs(quad - inner).max() > 16:
        info["fallback"] = f"the projected canvas (a corner {np.abs(quad - inner).max():.1f} px from the projection)"
        return mi, inner, info
    mq = GG.quad_mask(quad, (H, W)) > 0.5
    return mq, quad, info


def set_prints(hero_raw, files, log=None):
    """-> hero with the prints, the canvas masks (list), the quads (list)"""
    H, W = hero_raw.shape[:2]
    lab = L.to_lab(hero_raw)
    out = hero_raw.copy()
    masks, quads = [], []
    lin_h = L.srgb2lin(hero_raw)
    for n, ((outer, inner), f) in enumerate(zip(GG.art_quads(), files), 1):
        m, quad, info = find_canvas(lab, outer, inner)
        rec = dict(file=os.path.basename(f), canvas=info)
        pr = L.rd(f)
        ph, pw = pr.shape[:2]
        # the print fills the canvas quad (cover fit: the canvas is 50 x 70 less the moulding; the print's own ratio is kept by cropping)
        wq = 0.5 * (np.linalg.norm(quad[1] - quad[0]) + np.linalg.norm(quad[2] - quad[3]))
        hq = 0.5 * (np.linalg.norm(quad[3] - quad[0]) + np.linalg.norm(quad[2] - quad[1]))
        ar_q, ar_p = wq / hq, pw / ph
        if ar_p > ar_q:
            cw = ph * ar_q
            x0, y0, x1, y1 = (pw - cw) / 2, 0, (pw + cw) / 2, ph
        else:
            chh = pw / ar_q
            x0, y0, x1, y1 = 0, (ph - chh) / 2, pw, (ph + chh) / 2
        src = np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
        # 1.5 px outside the found corners, so the print runs under the moulding's edge
        c = quad.mean(0)
        dst = c + (quad - c) * (1 + 3.0 / max(wq, hq))
        Hm = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(pr, Hm, (W, H), flags=cv2.INTER_AREA if wq < pw else cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        light = lin_h / L.srgb2lin(CANVAS_ALBEDO)
        mf = m.astype(np.float32)
        # the canvas's light, inside the canvas only (normalised blur), 1.5 px
        num = cv2.GaussianBlur(light * mf[..., None], (0, 0), 1.5)
        den = cv2.GaussianBlur(mf, (0, 0), 1.5)
        light = num / np.maximum(den[..., None], 1e-3)
        pr_lit = np.clip(L.lin2srgb(L.srgb2lin(np.clip(warped, 0, 1)) * light), 0, 1)
        a = cv2.GaussianBlur(cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 0.8)[..., None]
        out = out * (1 - a) + pr_lit * a
        rec.update(canvas_px=int(m.sum()), quad=[[round(float(v), 1) for v in q] for q in quad], canvas_Lab=[round(float(v), 1) for v in np.median(lab[m], axis=0)],
                   projected_inner=[[round(float(v), 1) for v in q] for q in inner], cover_crop_px=[round(x0), round(y0), round(x1), round(y1)], print_px=[pw, ph])
        if log is not None:
            log[f"print-{n}"] = rec
        masks.append(m)
        quads.append(quad)
    return out.astype(np.float32), masks, quads
