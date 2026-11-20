#!/usr/bin/env python3
"""
kd_fixes2.py: the product-specific code fixes of the second cut (render-agent, resumed session, 2026-11-20; 0 tokens). Only what
shows at x1-x2 or does not match the product (EFF1):
  - runner_footprint / runner_matte: the edit draped the runner over both table ends (the prompt said not to; the card is 40 x 140 on a
    160 table). The runner is the clay's footprint (X 3.90-5.30, 40 wide: the card's size, its hems straight, 10 cm in from each end),
    its staircase smoothed; its colour is the edit's runner where the edit has runner, filled from the runner itself elsewhere (under
    the hems the edit draped, under and round the candles and the vase);
  - pendant: the shade at the card's size (V1 / V2 the clay's 50 x 19 box, V3 45 cm at the hem, the edit's own proportion), its bottom
    on Z 1.50, centred under the canopy; V1's suspension is the SKU drawing's: a 30 cm rod above the shade (the edit's rod pixels),
    then the thin black suspension line to the top of the frame;
  - olive_to_z120: the olive sprigs scaled about the vase mouth so their top is at Z 1.20 at most (7.5).
"""
import cv2
import numpy as np

import kd_common as K

C = K.C
H, W = K.H, K.W
MOUTH = (918.9, 721.1)                  # the amphora's mouth in D1 (4.60, 1.65, 1.01)
Z120_Y = 600.5                          # Z 1.20 over the vase in D1
CARD = {"V1": dict(box=(750, 280, 1079, 413), uniform=False, rod_cm=30, line=True),
        "V2": dict(box=(750, 276, 1079, 413), uniform=False, rod_cm=0, line=False),
        "V3": dict(width_px=299, bottom_y=430, uniform=True, rod_cm=0, line=False)}


def runner_footprint(ids, pl_ids, m):
    fp = (ids == 52) & C.dil(pl_ids == 20, 1)
    fp = C.blur(fp.astype(np.float64), 3.0) > 0.5          # the clay's staircase smoothed
    info = dict(rule="the clay's footprint, X 3.90-5.30 x 40 (the card), straight hems, never draped", px=int(fp.sum()),
                edit_px_outside=int((m & ~fp).sum()), edit_px_inside=int((m & fp).sum()))
    return fp, info


def aa_alpha(m, sigma=3.0, width=1.2):
    """an anti-aliased alpha along a smoothed contour of m (no staircase at shallow slopes)"""
    b = C.blur(m.astype(np.float64), sigma)
    k = 1.0 / (0.3989 / sigma) / width
    return np.clip((b - 0.5) * k + 0.5, 0, 1)


def runner_matte(e, m_edit, fp, Bk, children):
    """the edit's runner (its own long edges, matted on the table) inside the footprint widened by 5 px; its ends cut straight on the
    footprint's ends (never draped); under the children it is filled from its own pixels; its contact shading is kept (a variant
    swap of a child is a later pass)"""
    ch = np.zeros((H, W), bool)
    for c in children:
        ch |= c
    lim = C.dil(fp, 5)
    under = fp & C.dil(ch, 2)
    m = (m_edit & lim) | under
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(2)).astype(bool) & lim
    good = m_edit & lim & ~C.dil(ch, 2) & C.ero(m, 1)
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min() - 20, ys.max() + 21, xs.min() - 20, xs.max() + 21
    col = e.copy()
    for c in range(3):                                       # 16-bit (OpenCV's float path returns garbage here)
        chn = np.clip(np.rint(np.where(good, e[..., c], 0) * 65535), 0, 65535).astype(np.uint16)[y0:y1, x0:x1]
        mk = (~good)[y0:y1, x0:x1].astype(np.uint8)
        col[y0:y1, x0:x1, c] = cv2.inpaint(chn, mk, 5, cv2.INPAINT_TELEA).astype(np.float64) / 65535
    col = np.where(good[..., None], e, col)
    # the long edges: known-background alpha on the table; the ends: the widened footprint's anti-aliased line
    F = col
    dFB = F - Bk
    den = (dFB ** 2).sum(-1)
    a = np.clip(((e - Bk) * dFB).sum(-1) / np.maximum(den, 1e-6), 0, 1)
    sure = C.ero(m, 2)
    band = C.dil(m, 2) & ~sure
    a = np.where(sure | under, 1.0, np.where(band, a, 0.0))
    a = np.minimum(a, aa_alpha(lim, sigma=2.0))
    a = np.where(a < 0.04, 0.0, a)
    colu = (e - (1 - a[..., None]) * Bk) / np.maximum(a[..., None], 1e-3)
    col = np.where((band & (a > 0.3))[..., None], np.clip(colu, 0, 1), col)
    return a, np.clip(col, 0, 1)


def runner_colour(a, col, h_target=55.0, c_target=35.0, dL=-4.0):
    """10.2: the runner at the photo's caramel, relative to the room (R5): the photo reads L*59 C*49 h52; in this light the walnut
    reads 0.88 of its chroma, so the target is h 52-56 and C* about 40-43; L* stays the edit's (relative to the walnut it is right).
    A uniform hue rotation and chroma gain on the layer, measured on its opaque pixels"""
    lab = C.to_lab(col)
    m = a > 0.99
    L0, A0, B0 = np.median(lab[m], 0)
    h0, c0 = np.degrees(np.arctan2(B0, A0)), np.hypot(A0, B0)
    dh = np.radians(h_target - h0)
    k = min(1.5, c_target / max(c0, 1e-3))
    A1 = (lab[..., 1] * np.cos(dh) - lab[..., 2] * np.sin(dh)) * k
    B1 = (lab[..., 1] * np.sin(dh) + lab[..., 2] * np.cos(dh)) * k
    out = np.clip(C.from_lab(np.stack([lab[..., 0] + dL, A1, B1], -1)), 0, 1)
    lab2 = C.to_lab(out)
    L2, A2, B2 = np.median(lab2[m], 0)
    return out, dict(before=dict(L=round(float(L0), 1), C=round(float(c0), 1), h=round(float(h0), 1)),
                     after=dict(L=round(float(L2), 1), C=round(float(np.hypot(A2, B2)), 1), h=round(float(np.degrees(np.arctan2(B2, A2))), 1)),
                     rule="photo L*59 C*49 h52 (new-rooms-photo-check); target h 55, C* 35, L* -4 (a deeper caramel: at C* 40 and the edit's L* it read orange at x1)")


# the size check against the card (the clay is built at the card's size): per group, the reference product and the dimension measured;
# a group off by more than 10 % is scaled uniformly about its bottom centre (its contact with the support stays), and moved along the
# support onto the clay's centre when the edit drew it more than 12 px off (B1 / MB1)
SIZE = {
    "E-left": [dict(ids=(71, 72), ref=71, dim="w")],
    "F-niche": [dict(ids=(74,), ref=74, dim="h"), dict(ids=(76,), ref=76, dim="h")],
    "Dc-right": [dict(ids=(61,), ref=61, dim="h"), dict(ids=(62,), ref=62, dim="h"), dict(ids=(63,), ref=63, dim="w"),
                 dict(ids=(65,), ref=65, dim="w"), dict(ids=(66,), ref=66, dim="h")],
    "Ec-sconce-board": [dict(ids=(73,), ref=73, dim="h")],          # the sconce came back on its clay at its size
}
FILL = {50: (51,), 53: (54,), 55: (56,), 58: (59,), 63: (64,), 67: (68,), 74: (75,)}


def _bbox(m):
    ys, xs = np.nonzero(m)
    return xs.min(), ys.min(), xs.max(), ys.max()


def size_fix(p, e, layers, ids, base, tol=0.10):
    """all groups are measured and warped from the edit as it came; then every moved group's old place (with its old shadow, 45 px)
    goes back to the plate, never over another product; then each group's shading ring and the group itself are laid in"""
    info = {}
    e0 = e.copy()
    rat = np.clip(C.blur(C.luma(C.lin(e0)), 1.0) / np.maximum(C.blur(C.luma(C.lin(base)), 1.0), 1e-4), 0.2, 1.0)
    todo = []
    allm = {k: m.copy() for k, m in layers.items()}
    for g in SIZE.get(p, []):
        if not all(k in layers and layers[k].any() for k in g["ids"]):
            continue
        clay = np.isin(ids, [g["ref"]] + list(FILL.get(g["ref"], ())))
        x0, y0, x1, y1 = _bbox(layers[g["ref"]])
        c0, d0, c1, d1 = _bbox(clay)
        s = (c1 - c0 + 1) / (x1 - x0 + 1) if g["dim"] == "w" else (d1 - d0 + 1) / (y1 - y0 + 1)
        U = np.zeros((H, W), bool)
        for k in g["ids"]:
            U |= layers[k]
        ux0, uy0, ux1, uy1 = _bbox(U)
        rec = dict(ref=g["ref"], dim=g["dim"], edit_px=int((x1 - x0 + 1) if g["dim"] == "w" else (y1 - y0 + 1)),
                   clay_px=int((c1 - c0 + 1) if g["dim"] == "w" else (d1 - d0 + 1)), scale=round(float(s), 3))
        sx, sy = (ux0 + ux1) / 2, uy1
        cx_off = (x0 + x1) / 2 - sx
        tx = (c0 + c1) / 2 - cx_off * s
        if abs(tx - sx) <= 12:
            tx = sx
        ty = sy
        moved = abs(tx - sx) > 3
        if abs(s - 1) <= tol and not moved:
            rec["applied"] = False
            info[",".join(map(str, g["ids"]))] = rec
            continue
        if abs(s - 1) <= tol:
            s = 1.0
        A = np.array([[s, 0, tx - s * sx], [0, s, ty - s * sy]], np.float32)
        ew = cv2.warpAffine(e0.astype(np.float32), A, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
        rat_w = cv2.warpAffine(rat.astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR, borderValue=1.0).astype(np.float64)
        new = {k: cv2.warpAffine(layers[k].astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR) > 0.5 for k in g["ids"]}
        Un = np.zeros((H, W), bool)
        for k in g["ids"]:
            Un |= new[k]
        todo.append((g, U, Un, new, ew, rat_w))
        rec.update(applied=True, scale=round(float(s), 3), moved_px=[round(float(tx - sx), 1), round(float(ty - sy), 1)],
                   rule="scaled uniformly about the group's bottom centre (its contact stays), moved along the support onto its clay when off by more than 12 px")
        info[",".join(map(str, g["ids"]))] = rec
    if not todo:
        return e, layers, info
    moved_ids = {k for t in todo for k in t[0]["ids"]}
    keep = np.zeros((H, W), bool)                               # the products that stay where the edit drew them
    for k, m in allm.items():
        if k not in moved_ids:
            keep |= C.dil(m, 2)
    for g, U, Un, new, ew, rat_w in todo:
        e = np.where((C.dil(U, 45) & ~keep)[..., None], base, e)
    for g, U, Un, new, ew, rat_w in todo:
        ring = C.dil(Un, 25) & ~Un & ~keep
        shaded = C.srgb(np.clip(C.lin(base) * rat_w[..., None], 0, 1))
        e = np.where(ring[..., None], np.minimum(e, shaded), e)
    for g, U, Un, new, ew, rat_w in todo:
        e = np.where(Un[..., None], np.clip(ew, 0, 1), e)
        for k in g["ids"]:
            layers[k] = new[k]
    return e, layers, info


def canister_geom(lab_e, m):
    """the canisters as clean cylinders seen from the front: per body, its column span (the median row extent of its lower part),
    the bamboo lid band above it (rows still lighter than 55), a rounded bottom; the edit's own pixels inside"""
    out = np.zeros((H, W), bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    info = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 100:
            continue
        b = lb == i
        ys = np.nonzero(b.any(1))[0]
        y0, y1 = ys.min(), ys.max()
        lows = [np.nonzero(b[y])[0] for y in range(y0 + int(0.3 * (y1 - y0)), y1 - 2)]
        x0 = int(np.median([r.min() for r in lows if r.size]))
        x1 = int(np.median([r.max() for r in lows if r.size]))
        top = y0
        for y in range(y0 - 1, max(0, y0 - 14), -1):
            if lab_e[y, x0 + 2:x1 - 1, 0].mean() > 55:
                top = y
            else:
                break
        rect = np.zeros((H, W), np.uint8)
        cv2.rectangle(rect, (x0, top), (x1, y1), 1, -1)
        r = 4
        for cx in (x0 + r, x1 - r):                             # the rounded bottom corners
            rect[y1 - r + 1:y1 + 1, (cx - r if cx < (x0 + x1) / 2 else cx):(cx + 1 if cx < (x0 + x1) / 2 else cx + r + 1)] = 0
            cv2.circle(rect, (cx, y1 - r), r, 1, -1)
        out |= rect.astype(bool)
        info.append(dict(x=[x0, x1], y=[int(top), int(y1)]))
    return out, info


# colour against the SKU photo's reading (R5, relative to the room): (target h, target C*, dL, why)
COLOUR = {73: (56.0, 32.0, 0.0, "photo L*39 C*25 h54 (new-rooms-photo-check); the edit read C*43 h62, orange: C* x0.75 to 32, h 56"),
          76: (None, None, 0.0, "the edit's canisters read cool (b* -1.5, h -153) in a warm niche; warm white: a* +0.8, b* +4 (no pure white)")}


def product_colour(k, a, col):
    if k not in COLOUR:
        return col, None
    h_t, c_t, dL, why = COLOUR[k]
    lab = C.to_lab(col)
    m = a > 0.99
    L0, A0, B0 = np.median(lab[m], 0)
    if k == 76:
        lab[..., 1] += 0.8
        lab[..., 2] += 4.0
    else:
        h0, c0 = np.degrees(np.arctan2(B0, A0)), np.hypot(A0, B0)
        dh = np.radians(h_t - h0)
        kk = c_t / max(c0, 1e-3)
        A1 = (lab[..., 1] * np.cos(dh) - lab[..., 2] * np.sin(dh)) * kk
        B1 = (lab[..., 1] * np.sin(dh) + lab[..., 2] * np.cos(dh)) * kk
        lab[..., 1], lab[..., 2] = A1, B1
    lab[..., 0] += dL
    out = np.clip(C.from_lab(lab), 0, 1)
    l2 = C.to_lab(out)[m]
    L2, A2, B2 = np.median(l2, 0)
    return out, dict(before=[round(float(L0), 1), round(float(np.hypot(A0, B0)), 1), round(float(np.degrees(np.arctan2(B0, A0))), 1)],
                     after=[round(float(L2), 1), round(float(np.hypot(A2, B2)), 1), round(float(np.degrees(np.arctan2(B2, A2))), 1)], why=why)


def diff_matte(e, B, region, a_est=None):
    """the exact difference matte on a known background B: the least alpha that keeps the colour in range, or the estimate if higher;
    over B the layer gives the edit back"""
    up = np.where(e > B, (e - B) / np.maximum(1 - B, 1e-3), (B - e) / np.maximum(B, 1e-3)).max(-1)
    a = up if a_est is None else np.maximum(a_est, up)
    a = np.clip(a, 0, 1) * region
    a = np.where(a < 0.05, 0.0, a)
    col = B + (e - B) / np.maximum(a[..., None], 1e-3)
    return a, np.clip(col, 0, 1)


def _hull(m):
    pts = cv2.findNonZero(m.astype(np.uint8))
    out = np.zeros((H, W), np.uint8)
    if pts is not None:
        cv2.fillConvexPoly(out, cv2.convexHull(pts), 1)
    return out.astype(bool)


def _rows(m, min_w=40):
    w = m.sum(1)
    r = np.nonzero(w >= min_w)[0]
    return r.min(), r.max()


def pendant(e, m, ids, card, diff_base):
    spec = CARD[card]
    ey0, ey1 = _rows(m)
    if spec["uniform"]:                                       # V3: the ceramic ball and the collar go with the shade; the cord is
        w_ = m.sum(1)                                         # the rows no wider than 12 px above them
        y = ey0
        while y > 0 and w_[y - 1] > 12:
            y -= 1
        ey0 = y
    sh = m.copy()
    sh[:ey0] = False
    sh = _hull(sh) & C.dil(sh, 1)
    exs = np.nonzero(sh.any(0))[0]
    ex0, ex1 = exs.min(), exs.max()
    ecx = (ex0 + ex1) / 2
    if spec["uniform"]:
        s = sy = spec["width_px"] / (ex1 - ex0 + 1)
        tcx, tcy = 914.5, spec["bottom_y"]
    else:
        cx0, cy0, cx1, cy1 = spec["box"]
        s = (cx1 - cx0 + 1) / (ex1 - ex0 + 1)
        sy = (cy1 - cy0 + 1) / (ey1 - ey0 + 1)
        tcx, tcy = (cx0 + cx1) / 2, cy1
    A = np.array([[s, 0, tcx - s * ecx], [0, sy, tcy - sy * ey1]], np.float32)
    rgb_s = cv2.warpAffine(e.astype(np.float32), A, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
    sh_s = cv2.warpAffine(sh.astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR) > 0.5
    new_top = _rows(sh_s)[0]
    old = C.dil(m, 6)                                       # the edit's own shade and rod: the background there (for the matte only)
    out = np.where(sh_s[..., None], np.clip(rgb_s, 0, 1), np.where(old[..., None], diff_base, e))
    mask = sh_s.copy()
    # the suspension: the edit's rod (its columns over the 40 rows above its shade), then the line
    rod = m.copy()
    rod[ey0 - 2:] = False
    if spec["uniform"]:
        rod &= (m.sum(1) <= 12)[:, None]
    rows = np.nonzero(rod.any(1))[0]
    info = dict(card=card, scale_x=round(float(s), 4), scale_y=round(float(sy), 4), edit_shade_px=[int(ex0), int(ey0), int(ex1), int(ey1)],
                new_shade_top_row=int(new_top), centre_x=round(float(tcx), 1))
    if rows.size:
        prof_rows = rows[-40:]
        lefts = [np.nonzero(rod[y])[0].min() for y in prof_rows]
        rights = [np.nonzero(rod[y])[0].max() for y in prof_rows]
        rx0, rx1 = int(np.median(lefts)), int(np.median(rights))
        wid = rx1 - rx0 + 1
        prof = np.median(np.stack([e[y, rx0 - 1:rx1 + 2] for y in prof_rows]), 0)        # the rod's colour across its width
        dx = int(round(tcx - (rx0 + rx1) / 2))
        rod_px = int(round(spec["rod_cm"] * 6.6)) if spec["rod_cm"] else new_top + 2
        y_rod_top = max(0, new_top - rod_px)
        for y in range(y_rod_top, new_top + 2):
            out[y, rx0 - 1 + dx:rx1 + 2 + dx] = prof
            mask[y, rx0 + dx:rx1 + 1 + dx] = True
        info.update(rod_px=[int(y_rod_top), int(new_top)], rod_width_px=int(wid))
        if spec["line"] and y_rod_top > 0:
            cx = tcx
            dark = prof[wid // 2 + 1]
            for y in range(0, y_rod_top):
                x0 = int(np.floor(cx - 1))
                out[y, x0:x0 + 2] = dark
                mask[y, x0:x0 + 2] = True
            info["line"] = dict(rows=[0, int(y_rod_top)], width_px=2, rule="the SKU drawing: rod 30 cm, then a thin suspension line")
    return out, mask, info


def olive_to_z120(a, col, fz):
    ys = np.nonzero((a > 0.15).any(1) & fz.any(1))[0]
    if not ys.size:
        return a, col, None
    top = int(ys.min())
    if top >= Z120_Y:
        return a, col, dict(top_px=top, scale=1.0)
    s = (MOUTH[1] - Z120_Y) / (MOUTH[1] - top)
    A = np.array([[s, 0, MOUTH[0] - s * MOUTH[0]], [0, s, MOUTH[1] - s * MOUTH[1]]], np.float32)
    a2 = cv2.warpAffine(a.astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR).astype(np.float64)
    c2 = np.stack([cv2.warpAffine((col[..., c] * a).astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR) for c in range(3)], -1).astype(np.float64)
    c2 = c2 / np.maximum(a2[..., None], 1e-4)
    a2 = np.where(a2 < 0.04, 0, a2)
    return a2, np.clip(c2, 0, 1), dict(top_px_before=top, scale=round(float(s), 3), top_px_after=int(round(MOUTH[1] - s * (MOUTH[1] - top))),
                                       rule="7.5: no sprig above Z 1.20; the sprigs scaled about the vase mouth (a filler, not a product)")
