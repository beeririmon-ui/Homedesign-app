#!/usr/bin/env python3
"""
post_b2.py: the designer's two code fixes on B2 (chapter 0א, "הכרעות על ברירות המחדל של B2", 2026-11-18). 0 tokens.
Runs on the files that compose_defaults.py wrote (the defaults run, then --recolour), once: it refuses a second run.
  1. the ring (rejection 2, the A3 SKU: ring 16, base 5): the drawn ring is a centreline ellipse (OpenCV fitEllipse on the visible
     rod, the wall base left out) and a rod; its hidden lower arc is completed (the rod's own colour by angle and radial position),
     its alpha redrawn from the ellipse (anti-aliased), and the whole ring, base and shadow, scaled uniformly about the wall base,
     which stays, to the clay's outer width. The towel, both variants, with its shadow, rises by the rise of the bar's top
     (integer rows, no resampling): not scaled, not moved sideways. The ring layer is complete under the towel (z 50 under 52),
     so the fold's overlap is rebuilt by the towel's own mask.
  2. the two washes (the designer's check on the light layer): the peak of the added light (linear luminance, p99.5 over each
     lamp's beams) of the left lamp against the right; outside 0.8-1.25, the left lamp's added light is scaled (linear) to the
     right's peak and written back as screen.
Then both composites are recomposed from the files (the engine's formula), RND2 is checked, and layers/manifest.json,
b2-defaults-compose.json and b2-defaults-checks.json get the record.

  python3 post_b2.py
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import compose_defaults as C  # noqa: E402

CLAY_ID = C.CLAY + "B2-id.png"
RING_CLAY_ID = 49
MOUNT_R = 32


def load_rgba(p):
    return np.asarray(Image.open(os.path.join(ST, p))).astype(np.float64) / 255


def save_rgba(a, p):
    q = np.clip(np.rint(a * 255), 0, 255).astype(np.uint8)
    q[..., :3][q[..., 3] == 0] = 0
    Image.fromarray(q, "RGBA").save(os.path.join(ST, p))


def fit_ring(alpha, towel):
    a = alpha > 0.5
    ys, xs = np.nonzero(a)
    top = ys.min()
    m = a.copy()
    m[top + 52:] = False
    cxm = np.median(xs[ys < top + 20])
    m[:, :int(cxm - 35)] = False
    m[:, int(cxm + 35):] = False
    my, mx = np.nonzero(m)
    mc = np.array([mx.mean(), my.mean()])
    H, W = a.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    rod = a & (np.hypot(xx - mc[0], yy - mc[1]) > MOUNT_R) & ~towel
    ry, rx = np.nonzero(rod)
    (cx, cy), (w, h), ang = cv2.fitEllipse(np.stack([rx, ry], 1).astype(np.float32))
    e = dict(cx=cx, cy=cy, A=w / 2, B=h / 2, th=np.radians(ang))
    d, t_ang = ell_coords(e, rx.astype(float), ry.astype(float))
    lo, hi = np.percentile(d, [2, 98])
    e.update(c0=(lo + hi) / 2, t=(hi - lo) / 2, mount=mc)
    return e


def ell_coords(e, x, y):
    dx, dy = x - e["cx"], y - e["cy"]
    qx = dx * np.cos(e["th"]) + dy * np.sin(e["th"])
    qy = -dx * np.sin(e["th"]) + dy * np.cos(e["th"])
    rn = np.sqrt((qx / e["A"]) ** 2 + (qy / e["B"]) ** 2)
    rad = np.hypot(qx, qy) / np.maximum(rn, 1e-6)
    return (rn - 1) * rad, np.degrees(np.arctan2(qy / e["B"], qx / e["A"])) % 360


def extent(e, H, W):
    """outer box of the rod (the ellipse grown by the rod's outer offset)"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    d, _ = ell_coords(e, xx, yy)
    m = np.abs(d - e["c0"]) <= e["t"]
    ys, xs = np.nonzero(m)
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], m


def complete_ring(R, towel, e):
    """the ring with its hidden arc: the rod's alpha from the ellipse, the wall base from the cut; colours of the hidden or
    missing rod pixels by (angle bin 6 deg, radial bin 0.25 of the half thickness) from the visible rod's interior"""
    H, W = R.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    d, ang = ell_coords(e, xx, yy)
    rho = (d - e["c0"]) / e["t"]
    rod_a = np.clip(e["t"] + 0.5 - np.abs(d - e["c0"]), 0, 1)
    mdist = np.hypot(xx - e["mount"][0], yy - e["mount"][1])
    mount_a = np.where(mdist <= MOUNT_R + 4, R[..., 3], 0)
    mount_a = cv2.GaussianBlur(mount_a.astype(np.float32), (0, 0), 0.6).astype(np.float64) * (mdist <= MOUNT_R + 6)
    alpha = np.maximum(rod_a, mount_a)
    vis = (R[..., 3] > 0.95) & ~C.dil(towel, 2) & (np.abs(rho) < 0.9) & (mdist > MOUNT_R)
    ab = (ang[vis] // 6).astype(int)
    rb = np.clip(((rho[vis] + 1) / 0.25).astype(int), 0, 7)
    table = np.full((60, 8, 3), np.nan)
    for i in range(60):
        for j in range(8):
            s = (ab == i) & (rb == j)
            if s.sum() >= 3:
                table[i, j] = np.median(R[..., :3][vis][s], 0)
    for j in range(8):                                    # empty angle bins take the nearest filled one (circularly)
        filled = [i for i in range(60) if not np.isnan(table[i, j, 0])]
        if not filled:
            continue
        for i in range(60):
            if np.isnan(table[i, j, 0]):
                k = min(filled, key=lambda f: min(abs(f - i), 60 - abs(f - i)))
                table[i, j] = table[k, j]
    need = (alpha > 0) & ~((R[..., 3] > 0.95) & ~C.dil(towel, 1)) & (mdist > MOUNT_R - 2)
    rgb = R[..., :3].copy()
    ai = (ang[need] // 6).astype(int) % 60
    rj = np.clip(((np.clip(rho[need], -0.99, 0.99) + 1) / 0.25).astype(int), 0, 7)
    rgb[need] = table[ai, rj]
    rgb = np.nan_to_num(rgb)
    base_zone = (alpha > 0) & (mdist <= MOUNT_R - 2) & (R[..., 3] < 0.95)   # round the wall base: its own colour carried in
    wgt = cv2.GaussianBlur(R[..., 3].astype(np.float32), (0, 0), 2).astype(np.float64)
    for c in range(3):
        v = cv2.GaussianBlur((R[..., c] * R[..., 3]).astype(np.float32), (0, 0), 2).astype(np.float64) / np.maximum(wgt, 1e-6)
        rgb[..., c][base_zone] = v[base_zone]
    return np.dstack([rgb, alpha])


def warp_rgba(rgba, M, H, W):
    pm = np.dstack([rgba[..., :3] * rgba[..., 3:4], rgba[..., 3]]).astype(np.float32)
    w = cv2.warpAffine(pm, M, (W, H), flags=cv2.INTER_AREA).astype(np.float64)
    a = np.clip(w[..., 3], 0, 1)
    rgb = np.where(a[..., None] > 1e-4, w[..., :3] / np.maximum(a[..., None], 1e-4), 0)
    a = np.where(a < 1 / 510, 0, a)
    return np.dstack([np.clip(rgb, 0, 1), a])


def shift_up(arr, dy, fill):
    out = np.full_like(arr, fill)
    out[:-dy] = arr[dy:]
    return out


def stack_files(man, plate, swap=None):
    out = plate.astype(np.float64) / 255
    for l in sorted(man["layers"], key=lambda l: l["z"]):
        rgba, s8 = (swap or {}).get(l["slot"], (np.asarray(Image.open(os.path.join(ST, l["layer"]))),
                                                np.asarray(Image.open(os.path.join(ST, l["shadow"])))))
        out = C.compose_one(out, rgba, s8)
    return out


def lamp_peaks(below, L8, boxes):
    lin = C.lin
    F = C.light_one(below, L8)
    add = (lin(F) - lin(below)) @ np.array([0.2126, 0.7152, 0.0722])
    res = {}
    for i, (x0, y0, x1, y1) in boxes.items():
        up = add[max(0, y0 - 380):y0, max(0, x0 - 250):x1 + 250]
        dn = add[y1:y1 + 340, max(0, x0 - 250):x1 + 250]
        w = np.concatenate([up.ravel(), dn.ravel()])
        res[i] = dict(p995=float(np.percentile(w[w > 0], 99.5)), max=float(w.max()), sum=float(w.sum()))
    return res, add


def main():
    man_p = os.path.join(ST, "layers", "manifest.json")
    man = json.load(open(man_p))
    if man.get("post_b2"):
        sys.exit("post_b2 already applied: re-run compose_defaults.py (the defaults, then --recolour) first")
    comp_p = os.path.join(ST, "b2-defaults-compose.json")
    comp = json.load(open(comp_p))
    plate = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    H, W = plate.shape[:2]
    lay = {l["slot"]: l for l in man["layers"]}
    rec = {}
    # ---- 1. the ring ----
    ring_l, towel_l = lay["towel-ring"], lay["hand-towel"]
    R = load_rgba(ring_l["layer"])
    Rs = np.asarray(Image.open(os.path.join(ST, ring_l["shadow"]))).astype(np.float64) / 255
    towel = np.asarray(Image.open(os.path.join(ST, towel_l["layer"])))[..., 3] > 0
    e = fit_ring(R[..., 3], towel)
    ids = np.asarray(Image.open(CLAY_ID))
    cy_, cx_ = np.nonzero(ids == RING_CLAY_ID)
    clay_w = int(cx_.max() - cx_.min() + 1)
    box0, _ = extent(e, H, W)
    s = clay_w / (box0[2] - box0[0] + 1)
    mx, my = e["mount"]
    M = np.float32([[s, 0, mx - s * mx], [0, s, my - s * my]])
    full = complete_ring(R, towel, e)
    ring_new = warp_rgba(full, M, H, W)
    # the ring's shadow is carried on under the drawn ring's footprint (normalised blur from the plaster round it), so the new,
    # smooth rod leaves no unshadowed sliver where the old cut was ragged
    dark = 1 - Rs
    hole = C.dil(R[..., 3] > 0, 3)
    wv = C.blur((~hole).astype(np.float64), 3)
    fillv = C.blur(dark * ~hole, 3) / np.maximum(wv, 1e-6)
    dark = np.where(hole & (wv > 0.05), fillv, dark)
    sh_new = 1 - cv2.warpAffine(dark.astype(np.float32), M, (W, H), flags=cv2.INTER_AREA).astype(np.float64)
    sh_new = np.where(sh_new > 0.996, 1.0, sh_new)
    e2 = dict(e, cx=mx + s * (e["cx"] - mx), cy=my + s * (e["cy"] - my), A=e["A"] * s, B=e["B"] * s, c0=e["c0"] * s, t=e["t"] * s)
    box1, _ = extent(e2, H, W)
    # the bar: the lowest point of the rod's top surface (centreline + c0 - t) under the wall base
    xs = np.arange(box0[0], box0[2] + 1)
    def bar_top(ee):
        yy = np.arange(int(ee["cy"]), int(ee["cy"] + ee["A"] + ee["B"]) + 40)
        X, Y = np.meshgrid(np.arange(int(ee["cx"]) - 3, int(ee["cx"]) + 4), yy)
        d, _ = ell_coords(ee, X.astype(float), Y.astype(float))
        inside = np.abs(d - ee["c0"]) <= ee["t"]
        return float(Y[inside].min()), float(Y[inside].max())
    t0, b0 = bar_top(e)
    t1, b1 = bar_top(e2)
    dy = int(round(t0 - t1))
    # ---- the towel (both variants) and its shadow ----
    tw_files = [towel_l["layer"]] + [v["layer"] for v in man.get("variants", []) if v["slot"] == "hand-towel"]
    tws_files = [towel_l["shadow"]] + [v["shadow"] for v in man.get("variants", []) if v["slot"] == "hand-towel"]
    for p in tw_files:
        a = np.asarray(Image.open(os.path.join(ST, p)))
        Image.fromarray(shift_up(a, dy, 0), "RGBA").save(os.path.join(ST, p))
    for p in tws_files:
        a = np.asarray(Image.open(os.path.join(ST, p)))
        Image.fromarray(shift_up(a, dy, 255)).save(os.path.join(ST, p))
    save_rgba(ring_new, ring_l["layer"])
    Image.fromarray(np.clip(np.rint(sh_new * 255), 0, 255).astype(np.uint8)).save(os.path.join(ST, ring_l["shadow"]))
    towel_new = np.asarray(Image.open(os.path.join(ST, towel_l["layer"])))[..., 3] > 0
    ring_a = ring_new[..., 3] > 0
    # the checks: the rod in the open (not under the towel) must be continuous down to the towel: the rod's visible part,
    # per side, reaches the towel's mask; no plate pixel enclosed between the bar and the fold
    rod2 = (np.abs(ell_coords(e2, *np.mgrid[0:H, 0:W][::-1].astype(np.float64))[0] - e2["c0"]) <= e2["t"])
    vis_rod = rod2 & ~towel_new
    n, lab = cv2.connectedComponents(vis_rod.astype(np.uint8), connectivity=8)
    touch = [int((C.dil(lab == i, 1) & towel_new).any()) for i in range(1, n)]
    enclosed = 0
    ring_or_towel = (ring_a | towel_new).astype(np.uint8)
    inv = 1 - ring_or_towel
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    yb = int(b1) + 2
    win = lab2[int(t1) - 60:yb, box1[0]:box1[2]]
    for i in set(np.unique(win)) - {0}:
        if st2[i, cv2.CC_STAT_AREA] < 2000:               # a pocket of plate between the rod and the fold
            enclosed += int(st2[i, cv2.CC_STAT_AREA])
    clay_h_note = "the clay ring's visible part (its lower arc is under the clay towel)"
    rec["ring"] = dict(rule="0א 4: the A3 SKU (ring 16, base 5); diameter within +-5 % of the clay; the base stays",
                       fit=dict(centre=[round(e["cx"], 1), round(e["cy"], 1)], axes=[round(2 * e["A"], 1), round(2 * e["B"], 1)],
                                angle_deg=round(float(np.degrees(e["th"])), 1), rod_half_thickness=round(e["t"], 2), wall_base=[round(mx, 1), round(my, 1)]),
                       scale=round(float(s), 4), outer_box_before=box0, outer_box_after=box1, clay_box=[int(cx_.min()), int(cy_.min()), int(cx_.max()), int(cy_.max())],
                       width_ratio_to_clay=round((box1[2] - box1[0] + 1) / clay_w, 3),
                       height_before_after_px=[box0[3] - box0[1] + 1, box1[3] - box1[1] + 1], clay_height_note=clay_h_note,
                       bar_top_before_after=[round(t0, 1), round(t1, 1)], towel_rise_px=dy,
                       towel_top_at_bar_before_after=[int(np.nonzero(towel[:, int(e["cx"])])[0].min()), int(np.nonzero(towel_new[:, int(e2["cx"])])[0].min())],
                       visible_rod_pieces_touching_the_towel=touch, plate_pockets_between_rod_and_fold_px=enclosed,
                       towel_variants_shifted=tw_files)
    # ---- 2. the washes ----
    L8 = np.asarray(Image.open(os.path.join(ST, man["light"]["file"])).convert("RGB"))
    below = stack_files(man, plate)
    boxes = {int(k): v["new_box"] for k, v in comp["sconce_fix"].items()}
    pk, add = lamp_peaks(below, L8, boxes)
    ratio = pk[42]["p995"] / pk[43]["p995"]
    wash = dict(rule="0א 5: the left lamp's peak 0.8-1.25 of the right's (added light, linear luminance, p99.5 over the beams)",
                before=dict(left=round(pk[42]["p995"], 4), right=round(pk[43]["p995"], 4), ratio=round(ratio, 3)))
    if not 0.8 <= ratio <= 1.25:
        # the left plaster is lit more by the window, so the left lamp has less headroom before white: its added light cannot
        # reach the right's peak without blowing its whole V. Both gains move: the left up (at most 2x, linear), then the right
        # down until the left is 0.9 of it
        lin_b, lin_f = C.lin(below), C.lin(C.light_one(below, L8))
        Y3 = np.array([0.2126, 0.7152, 0.0722])

        def beam_win(i):
            x0, y0, x1, y1 = boxes[i]
            w = np.zeros((H, W), bool)
            w[max(0, y0 - 380):y0, max(0, x0 - 250):x1 + 250] = True
            w[y1:y1 + 340, max(0, x0 - 250):x1 + 250] = True
            return w & (L8.max(2) > 0)

        def with_gain(i, g, f_in):
            w = beam_win(i)
            x0, y0, x1, y1 = boxes[i]
            full = np.zeros((H, W), bool)
            full[max(0, y0 - 380):y1 + 340, max(0, x0 - 250):x1 + 250] = True
            full &= L8.max(2) > 0
            f = f_in.copy()
            f[full] = np.clip(lin_b[full] + g * (lin_f[full] - lin_b[full]), 0, 1)
            a2 = (f - lin_b) @ Y3
            v = a2[w]
            return f, float(np.percentile(v[v > 0], 99.5))

        def solve(i, target, lo, hi, f_in):
            for _ in range(30):
                g = (lo + hi) / 2
                _, p = with_gain(i, g, f_in)
                lo, hi = (g, hi) if p < target else (lo, g)
            return g

        gL = solve(42, pk[43]["p995"], 1.0, 2.0, lin_f)
        fL, pL = with_gain(42, gL, lin_f)
        gR = 1.0
        fR, pR = fL, pk[43]["p995"]
        if pL / pR < 0.9:
            gR = solve(43, pL / 0.9, 0.2, 1.0, fL)
            fR, pR = with_gain(43, gR, fL)
        Fn = C.srgb(fR)
        changed = np.abs(fR - lin_f).max(2) > 1e-9
        Ln = 1 - (1 - Fn) / np.maximum(1 - below, 1e-3)
        Ln = np.clip(np.where(changed[..., None], Ln, L8 / 255), 0, 1)
        L8 = np.clip(np.rint(Ln * 255), 0, 255).astype(np.uint8)
        Image.fromarray(L8).save(os.path.join(ST, man["light"]["file"]))
        pk2, _ = lamp_peaks(below, L8, boxes)
        wash.update(gain_linear_left=round(float(gL), 3), gain_linear_right=round(float(gR), 3),
                    after=dict(left=round(pk2[42]["p995"], 4), right=round(pk2[43]["p995"], 4), ratio=round(pk2[42]["p995"] / pk2[43]["p995"], 3)),
                    note="the left plaster takes more window light (less headroom to white), so the left gain alone could not reach 0.8")
    # M6 (QA 2026-11-18): the left lamp's wash went magenta at its edges (G = 0 in most of its light). Its colour is rebuilt from
    # the right lamp's (the same SKU), intensity by intensity: the added light keeps its luminance and takes the right wash's
    # R:G:B at the same luminance; where a channel would pass white the whole colour is scaled down (no burnt core)
    Y3 = np.array([0.2126, 0.7152, 0.0722])
    lin_b = C.lin(below)
    add = C.lin(C.light_one(below, L8)) - lin_b
    Ya = add @ Y3
    def lamp_win(i):
        x0, y0, x1, y1 = boxes[i]
        w = np.zeros((H, W), bool)
        w[max(0, y0 - 380):y1 + 340, max(0, x0 - 250):x1 + 250] = True
        return w & (L8.max(2) > 0)
    wl, wr = lamp_win(42), lamp_win(43)
    edges = np.geomspace(0.002, 1.0, 25)
    ref = wr & (Ya > 0.002)
    ratios = []
    for lo_, hi_ in zip(edges[:-1], edges[1:]):
        m = ref & (Ya >= lo_) & (Ya < hi_)
        ratios.append(np.median(add[m] / Ya[m][:, None], 0) if m.sum() >= 30 else None)
    filled = [i for i, r in enumerate(ratios) if r is not None]
    ratios = [ratios[i] if ratios[i] is not None else ratios[min(filled, key=lambda f: abs(f - i))] for i in range(len(ratios))]
    ratios = np.array(ratios)
    tgt = wl & (Ya > 0)
    bi = np.clip(np.searchsorted(edges, Ya[tgt]) - 1, 0, len(ratios) - 1)
    new_add = Ya[tgt][:, None] * ratios[bi]
    head = (1 - lin_b[tgt]) / np.maximum(new_add, 1e-6)
    new_add *= np.minimum(1.0, head.min(1))[:, None] * 0.999
    f = lin_b.copy()
    f[tgt] = lin_b[tgt] + new_add
    Fn = C.srgb(np.clip(f, 0, 1))
    Ln = 1 - (1 - Fn) / np.maximum(1 - below, 1e-3)
    Lw = L8.astype(np.float64) / 255
    Lw[tgt] = np.clip(Ln[tgt], 0, 1)
    L8 = np.clip(np.rint(Lw * 255), 0, 255).astype(np.uint8)
    # the headroom scaling took a little off the left's core: the right is trimmed (linear, no clipping) back to the 0.90 balance
    pk3, add3 = lamp_peaks(below, L8, boxes)
    trim = 1.0
    if pk3[42]["p995"] / pk3[43]["p995"] < 0.9:
        trim = pk3[42]["p995"] / 0.9 / pk3[43]["p995"]
        lin_f2 = C.lin(C.light_one(below, L8))
        f2 = lin_f2.copy()
        f2[wr] = lin_b[wr] + trim * (lin_f2[wr] - lin_b[wr])
        Ln2 = 1 - (1 - C.srgb(np.clip(f2, 0, 1))) / np.maximum(1 - below, 1e-3)
        Lw = L8.astype(np.float64) / 255
        Lw[wr] = np.clip(Ln2[wr], 0, 1)
        L8 = np.clip(np.rint(Lw * 255), 0, 255).astype(np.uint8)
    wash["right_trim_after_colour"] = round(float(trim), 4)
    Image.fromarray(L8).save(os.path.join(ST, man["light"]["file"]))
    pk3, add3 = lamp_peaks(below, L8, boxes)
    Ff = C.light_one(below, L8)
    labf = C.G.to_lab(Ff)
    def edge_hue(w):
        m = w & (add3 >= 0.02) & (add3 <= 0.06)
        return round(float(np.degrees(np.arctan2(np.median(labf[..., 2][m]), np.median(labf[..., 1][m]))) % 360), 1)
    def g0(w):
        return round(float(((L8[..., 1] == 0) & w).sum() / max(w.sum(), 1)), 3)
    burnt = lambda w: int(((C.q(Ff) == 255).all(2) & w & ~(C.q(below) == 255).all(2)).sum())  # noqa: E731
    wash["colour"] = dict(rule="M6: the left wash's colour from the right's by intensity (3000 K as drawn on the right); luminance kept",
                          edge_hue_deg=dict(left=edge_hue(wl), right=edge_hue(wr)), share_G0=dict(left=g0(wl), right=g0(wr)),
                          burnt_white_px=dict(left=burnt(wl), right=burnt(wr)),
                          peaks_after=dict(left=round(pk3[42]["p995"], 4), right=round(pk3[43]["p995"], 4), ratio=round(pk3[42]["p995"] / pk3[43]["p995"], 3)))
    rec["washes"] = wash
    # ---- recompose both composites from the files ----
    L8 = np.asarray(Image.open(os.path.join(ST, man["light"]["file"])).convert("RGB"))
    out = {}
    region = np.zeros((H, W), bool)
    for l in man["layers"]:
        region |= (np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3] > 0) | (np.asarray(Image.open(os.path.join(ST, l["shadow"]))) < 255)
    region |= L8.max(2) > 0
    o8 = C.q(C.light_one(stack_files(man, plate), L8))
    Image.fromarray(o8).save(os.path.join(ST, "b2-defaults.png"))
    C.frame_png(o8, os.path.join(ST, "b2-defaults-frame.png"))
    out["defaults"] = int((np.abs(o8.astype(int) - plate.astype(int)).max(2)[~region] > 0).sum())
    for v in man.get("variants", []):
        swap = {v["slot"]: (np.asarray(Image.open(os.path.join(ST, v["layer"]))), np.asarray(Image.open(os.path.join(ST, v["shadow"]))))}
        ov = C.q(C.light_one(stack_files(man, plate, swap), L8))
        name = v["composite"].rsplit(".", 1)[0]
        Image.fromarray(ov).save(os.path.join(ST, name + ".png"))
        C.frame_png(ov, os.path.join(ST, name + "-frame.png"))
        rv = region | (swap[v["slot"]][0][..., 3] > 0) | (swap[v["slot"]][1] < 255)
        out[name] = int((np.abs(ov.astype(int) - plate.astype(int)).max(2)[~rv] > 0).sum())
        diff = np.abs(ov.astype(int) - o8.astype(int)).max(2) > 0
        v["differing_px_vs_defaults"] = int(diff.sum())
        v["differing_px_vs_defaults_outside_alpha"] = int((diff & (swap[v["slot"]][0][..., 3] == 0)).sum())
        v["outside_differing_px_vs_plate"] = out[name]
    rec["rnd2_outside_differing_px"] = out
    # ---- records ----
    for l in man["layers"]:
        a = np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3]
        s8 = np.asarray(Image.open(os.path.join(ST, l["shadow"])))
        r = (a > 0) | (s8 < 255)
        ys_, xs_ = np.nonzero(r)
        l.update(alpha_px=int((a > 0).sum()), shadow_px=int((s8 < 255).sum()), bbox_px=[int(xs_.min()), int(ys_.min()), int(xs_.max()) + 1, int(ys_.max()) + 1])
    lay["towel-ring"]["refit"] = {"49": dict(scale=rec["ring"]["scale"], outer_box_before=box0, outer_box_after=box1, about="the wall base")}
    lay["hand-towel"]["moved_up_px"] = dy
    man["light"]["px"] = int((L8.max(2) > 0).sum())
    man["rnd2"] = dict(region_px=int(region.sum()), outside_differing_px=out["defaults"], rule=man["rnd2"]["rule"])
    man["post_b2"] = dict(date="2026-11-18", tool="tools/post_b2.py", source="docs/proposals/wm-bath-render-2026-11-17.md 0א (B2 rulings 4 and 5)",
                          ring=rec["ring"], washes=rec["washes"])
    json.dump(man, open(man_p, "w"), indent=1, ensure_ascii=False)
    comp["post_b2"] = rec
    json.dump(comp, open(comp_p, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(rec, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
