#!/usr/bin/env python3
"""
fix_lfix.py: the owner's three defects in the M0 living room, fixed in code, 0 tokens (render-agent, 2026-11-25).
Brief: briefs/wm-living-fix-cushion-basket-2026-11-25.md (+ the coordinator's third defect, the throw, same day).
NEW FILES ONLY (tag "lfix"): every fb12s1 / fb12s0 / R9 file is read, never written. Works on the 8-bit v3c layers as FB12 did.

  1 the cushion   the cushion sets' shadow files (from phase 1, carried unchanged since) hold a flat dark field (0.35 multiply, 40 x 150 px)
                  on the sofa's back cushion right of the left cushion: the model's relighting read as shadow. In that zone the shadow is
                  capped by a contact shadow that fades from the cushion's edge (1 - 0.30 exp(-d / 7 px)); the seat contact below is kept.
  2 the basket    the R3a cut kept the render's own background inside its alpha (the loop interiors of the handles, a light rim on the
                  sides) and its shadow file darkened the wall and the pot around it (a box, with the render's skirting as a ghost line):
                  the R3a render's pot and wall are not the plate's (the planter was re-rendered in R5 / R7). Re-matted: the handles by
                  the rope's chroma, the body's edge un-mixed against the render's own background (F / B projection, fix_r4.rematte's
                  method); the shadow = the frozen recipe's contact shadow restricted to where a contact shadow can fall here (the floor
                  and the rug: no wall, no pot), carried to the new edge. Placement unchanged: no floor point clears the pot, the sofa's
                  arm and the rug corner by F3 (placement() writes the grid).
  3 the throw     each set's throw was cut along the OLD table's top (phase 1 never rendered it behind that table): with Olia lower and
                  smaller, its straight cut edge and the sofa under it show. The throw's lower 4 x d px are stretched down per column so
                  its cut edge falls behind Olia's top (d = the gap + 6 px); its own folds and knit carry on. Sets A and C: the grey
                  stripe on the throw (R8) is filled from the knit 7 px above and below.

  python3.12 -I -B fix_lfix.py all     (cushions, basket, placement, build, frames, sheet, records)
"""
import hashlib
import importlib.util
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
LAY = os.path.join(P2, "layers")
OUT = os.environ.get("LFIX_OUT", P2)
WORK = os.path.join(OUT, "work-lfix")
TAG = "lfix"
MAN1 = os.path.join(LAY, "manifest-fb12s1.json")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


S0 = _load("fb12_s0", os.path.join(P2, "fb12_s0.py"))     # read-only: camera, H_FLOOR, compose8, FRAME_BOX
W, H = S0.W, S0.H
man1 = json.load(open(MAN1))
BY = {l_["id"]: l_ for l_ in man1["layers"]}
REC = {}


def arr(p, mode=None):
    im = Image.open(p)
    return np.asarray(im.convert(mode) if mode else im)


def L(rel):
    q = os.path.join(OUT, "layers", rel)
    return q if os.path.exists(q) else os.path.join(LAY, rel)


def save(p, a):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    Image.fromarray(a).save(p, optimize=False, compress_level=6)
    return p


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def rel(p):
    return os.path.relpath(p, REPO)


def lab(rgb8):
    return cv2.cvtColor(rgb8.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)


def nblur(x, w, s):
    w = w.astype(np.float32)
    den = cv2.GaussianBlur(w, (0, 0), s)
    if x.ndim == 3:
        num = np.stack([cv2.GaussianBlur((x[..., i] * w).astype(np.float32), (0, 0), s) for i in range(x.shape[2])], -1)
        return num / np.maximum(den, 1e-6)[..., None], den
    return cv2.GaussianBlur((x * w).astype(np.float32), (0, 0), s) / np.maximum(den, 1e-6), den


def dil(m, r):
    return cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0


def ero(m, r):
    return cv2.erode(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0


def nearest_fill(val, known, todo):
    """each todo pixel takes the value of its nearest known pixel"""
    _, lbl = cv2.distanceTransformWithLabels((~known).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ky, kx = np.nonzero(known)
    lut = np.zeros((lbl.max() + 1,) + val.shape[2:], val.dtype)
    lut[lbl[ky, kx]] = val[ky, kx]
    out = val.copy()
    out[todo] = lut[lbl[todo]]
    return out


def sets():
    return man1["slot_cushions"]["sets"]


# ================================================================================================= 1 + 3: the cushion sets
def cushion_shadow(st, Lc, Sh):
    """the flat dark field right of the left cushion -> a contact shadow fading from the cushion's edge"""
    a = Lc[..., 3].astype(np.float32) / 255
    n, lab_, stt, _ = cv2.connectedComponentsWithStats((a > 0.5).astype(np.uint8))
    left = [i for i in range(1, n) if stt[i, 4] > 5000 and stt[i, 0] < 1500]
    cu = lab_ == min(left, key=lambda i: stt[i, 0])                     # the left cushion
    ys, xs = np.nonzero(cu)
    yy, xx = np.mgrid[0:H, 0:W]
    xr = np.full(H, -1)
    for y in range(ys.min(), ys.max() + 1):
        r_ = xs[ys == y]
        if len(r_):
            xr[y] = r_.max()
    y_bot = int(ys.max())
    zone = (yy >= ys.min()) & (yy <= y_bot + 2) & (xx > xr[yy]) & (xr[yy] >= 0) & (xx <= xr[yy] + 75) & ~cu
    d = cv2.distanceTransform((~cu).astype(np.uint8), cv2.DIST_L2, 5)
    model = 1 - 0.30 * np.exp(-d / 7.0)
    s = Sh.astype(np.float32) / 255
    capped = np.maximum(s, model[..., None])
    # feather: full inside the zone, fading over 6 px at its edges; the seat contact (below the cushion's bottom) keeps its own values
    w = cv2.GaussianBlur(zone.astype(np.float32), (0, 0), 3.0) * dil(zone, 6)
    w = np.where(zone, 1.0, w)
    w = w * np.clip((y_bot + 4 - yy) / 6.0, 0, 1)
    out = s * (1 - w[..., None]) + capped * w[..., None]
    out8 = np.clip(np.floor(out * 255 + 0.5), 0, 255).astype(np.uint8)
    out8 = np.where((a >= 0.999)[..., None], Sh, out8)                  # under the cushion itself: unchanged bytes
    ch = (out8 != Sh).any(2)
    return out8, dict(zone_px=int(zone.sum()), changed_px=int(ch.sum()), bbox=[int(xx[ch].min()), int(yy[ch].min()), int(xx[ch].max()), int(yy[ch].max())],
                      dark_before_mean=round(float(1 - s[..., :].mean(2)[zone].mean()), 3), dark_after_mean=round(float(1 - out8.mean(2)[zone].mean() / 255), 3),
                      model="max(old, 1 - 0.30 exp(-d / 7 px)), d = distance from the left cushion's alpha; feathered 6 px; below its bottom unchanged")


def throw_extend(st, Lc):
    """stretch the throw down behind Olia where its cut edge follows the old table's top"""
    a = Lc[..., 3].astype(np.float32) / 255
    T = arr(L(BY["coffee-table"]["file"]))[..., 3] > 127
    OT = dil(np.load(os.path.join(P2, "work-fb12s0", "fb12s0-masks.npz"))["table"] > 0, 6)
    MARGIN = 6
    xs_ = np.arange(1850, 2200)
    yb = np.full(W, -1)
    d = np.zeros(W, np.float32)
    for x in xs_:
        col = a[:, x] > 0.5
        for y in range(1330, 1100, -1):
            if col[y] and not col[y + 1:y + 4].any() and OT[y + 2, x]:
                t = np.nonzero(T[y + 1:y + 140, x])[0]
                if len(t):
                    yb[x], d[x] = y, t[0] + 1 + MARGIN
                break
    cut = d > 0
    if not cut.any():
        return Lc, dict(columns=0)
    # smooth d along x (never under the need), and give the taper columns their own bottom
    dm = cv2.dilate(d[None, :], np.ones((1, 9), np.uint8))[0]
    ds = cv2.GaussianBlur(dm[None, :], (0, 0), 3.0)[0]
    ds = np.maximum(ds, d)
    for x in xs_:
        if ds[x] > 0.5 and yb[x] < 0:
            col = np.nonzero(a[1100:1340, x] > 0.5)[0]
            if len(col):
                yb[x] = 1100 + col.max()
            else:
                ds[x] = 0
    yb_s = yb.astype(np.float32)
    ok = (yb >= 0) & (ds > 0.5)
    mx = np.tile(np.arange(W, dtype=np.float32), (H, 1))
    my = np.tile(np.arange(H, dtype=np.float32)[:, None], (1, W))
    for x in np.nonzero(ok)[0]:
        R = max(90.0, 4.0 * ds[x])
        y0 = yb_s[x] - R
        y1 = yb_s[x] + ds[x]
        rows = np.arange(int(np.floor(y0)), int(np.ceil(y1)) + 1)
        rows = rows[(rows >= 0) & (rows < H)]
        my[rows, x] = y0 + (rows - y0) * R / (R + ds[x])
    pm = Lc.astype(np.float32)
    pm[..., :3] *= pm[..., 3:4] / 255
    wp = cv2.remap(pm, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    aw = wp[..., 3:4]
    rgb = np.where(aw > 0.5, wp[..., :3] * 255 / np.maximum(aw, 1e-3), Lc[..., :3].astype(np.float32))
    out = np.concatenate([rgb, aw], 2)
    zone = np.zeros((H, W), bool)
    for x in np.nonzero(ok)[0]:
        zone[max(0, int(yb_s[x] - max(90.0, 4.0 * ds[x])) - 1):min(H, int(yb_s[x] + ds[x]) + 2), x] = True
    out8 = np.where(zone[..., None], np.clip(np.floor(out + 0.5), 0, 255), Lc).astype(np.uint8)
    gap_b = gap_px(Lc[..., 3], T, OT)
    gap_a = gap_px(out8[..., 3], T, OT)
    return out8, dict(columns=int(ok.sum()), x=[int(np.nonzero(ok)[0].min()), int(np.nonzero(ok)[0].max())], d_px_max=round(float(ds.max()), 1),
                      d_px_median=round(float(np.median(ds[ok])), 1), stretch_max=round(float((max(90, 4 * ds.max()) + ds.max()) / max(90, 4 * ds.max())), 3),
                      margin_px=MARGIN, gap_px_before=gap_b, gap_px_after=gap_a,
                      how="per column: the throw's lower R = max(90, 4 d) px stretched over R + d (premultiplied RGBA, bilinear), so its cut edge "
                          "lies d px lower, MARGIN px behind Olia's top; d smoothed along x (dilate 9, Gaussian 3, never under the need)")


def gap_px(alpha8, T, OT):
    """visible px between the throw's cut edge and Olia: inside the old table's outline, under some throw, above Olia, not covered"""
    a = alpha8 > 127
    cnt = 0
    for x in range(1850, 2200):
        col = a[:, x]
        ys = np.nonzero(col[1100:1340])[0]
        if not len(ys):
            continue
        yb = 1100 + ys.max()
        t = np.nonzero(T[yb + 1:yb + 140, x])[0]
        if len(t) and OT[yb + 2, x]:
            cnt += int(t[0])
    return cnt


def stripe_fix(st, Lc):
    """sets A and C: the grey horizontal stripe on the throw (R8), filled from the knit 7 px above and below"""
    box = dict(A=(2150, 1252, 2260, 1282), C=(2174, 1252, 2203, 1282)).get(st)
    if box is None:
        return Lc, dict(px=0)
    x0, y0, x1, y1 = box
    rgb = Lc[..., :3].astype(np.float32)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    sub = lum[y0:y1, x0:x1]
    ref = 0.5 * (lum[y0 - 7:y1 - 7, x0:x1] + lum[y0 + 7:y1 + 7, x0:x1])
    ratio = sub / np.maximum(ref, 1)
    # the stripe: rows whose median ratio dips, and in them the px below 0.95 of their knit reference
    rmed = np.median(ratio, 1)
    rows = rmed < 0.9
    m = np.zeros((H, W), bool)
    if rows.any():
        cdip = np.median(ratio[rows], 0)
        xs = np.nonzero(cdip < 0.95)[0]
        ry = np.nonzero(rows)[0]
        m[y0 + ry.min() - 1:y0 + ry.max() + 2, max(x0, x0 + xs.min() - 3):min(x1, x0 + xs.max() + 4)] = True
    m = m & (Lc[..., 3] > 127)
    m[:y0] = m[y1:] = False
    m[:, :x0] = m[:, x1:] = False
    fill = 0.5 * (np.roll(rgb, 7, 0) + np.roll(rgb, -7, 0))
    out = Lc.copy()
    out[..., :3] = np.where(m[..., None], np.clip(np.floor(fill + 0.5), 0, 255), rgb).astype(np.uint8)
    return out, dict(px=int(m.sum()), rows=[int(y0 + i) for i in np.nonzero(rows)[0]], box=list(box))


def cushions():
    os.makedirs(WORK, exist_ok=True)
    rec = {}
    for st in "BAC":
        v = sets()[st]
        Lc, Sh = arr(L(v["layer"])), arr(L(v["shadow"]), "RGB")
        Sh2, r1 = cushion_shadow(st, Lc, Sh)
        Lc2, r3 = throw_extend(st, Lc)
        Lc2, r4 = stripe_fix(st, Lc2)
        save(os.path.join(OUT, "layers", "cushions", f"set-{st}-{TAG}.png"), Lc2)
        save(os.path.join(OUT, "layers", "cushions", f"set-{st}-shadow-{TAG}.png"), Sh2)
        rec[st] = dict(from_layer=v["layer"], from_shadow=v["shadow"], cushion_shadow=r1, throw=r3, stripe=r4)
        print(st, json.dumps(rec[st])[:600])
    json.dump(rec, open(os.path.join(WORK, f"cushions-{TAG}.json"), "w"), indent=1)
    return rec


# ================================================================================================= 2: the basket
def floor_mask():
    """the floor (and the rug lying on it) as the M0 camera sees it: the floor plane in front of the back wall (Y > 0.004) and right
    of the window wall (X > -2.296), not behind the planter's pot"""
    X_, Y_ = S0.img_to_plane(S0.H_FLOOR)
    m = (Y_ > 0.004) & (X_ > -2.296)
    yy = np.arange(H)[:, None]
    m &= yy > 900                                                       # the floor plane's horizon side only
    return m


def basket():
    sys.path[:0] = [P2, os.path.join(P2, "step0")]
    import stack                                                        # noqa: E402  (read-only: the one v3c grade)
    G = stack.Grade()
    regt = np.load(os.path.join(P2, "work-r3", "r3a-regt.npy")).astype(np.float32)
    g8 = G(regt)                                                        # the R3a render in the layers' graded space (core = layer +-1)
    del regt
    Lb, Sb = arr(L(BY["basket"]["file"])), arr(L(BY["basket-shadow"]["file"]), "RGB")
    a0 = Lb[..., 3].astype(np.float32) / 255
    M = a0 > 0.5
    yy, xx = np.mgrid[0:H, 0:W]
    I = g8.astype(np.float32) / 255
    Lab = lab(g8)
    C = np.hypot(Lab[..., 1], Lab[..., 2])
    # (a) the handles (rows above the rim, 1066): the rope is chroma >= ~19, the render's wall / pot / soil inside the loops is not
    RIM = 1066
    Hz = dil(M, 2) & (yy <= RIM)
    lo = np.where(Lab[..., 0] < 35, 15.0, 11.0)
    hi = np.where(Lab[..., 0] < 35, 21.0, 19.0)
    s = np.clip((C - lo) / (hi - lo), 0, 1)
    s = s * s * (3 - 2 * s)
    s = cv2.GaussianBlur(s.astype(np.float32), (0, 0), 0.6)
    a_h = np.where(Hz, np.minimum(a0, s), a0)
    # (b) the body's edge (below the rim): un-mixed against the render's own background (fix_r4.rematte's F / B projection)
    core = ero(M, 3)
    outer = dil(M, 7) & ~dil(M, 2)
    F, wF = nblur(I, core, 2.0)
    F5, _ = nblur(I, core, 5.0)
    F = np.where((wF > 0.02)[..., None], F, F5)
    B, wB = nblur(I, outer, 2.0)
    B5, _ = nblur(I, outer, 5.0)
    B = np.where((wB > 0.02)[..., None], B, B5)
    band = dil(M, 3) & ~core & (yy > RIM)
    D = F - B
    den = (D * D).sum(2)
    aest = np.clip(((I - B) * D).sum(2) / np.maximum(den, 1e-6), 0, 1)
    trust = band & (np.sqrt(den) > 0.06)
    a_b = np.where(trust, np.minimum(a0, aest), a0)
    a_b = np.where(core & (yy > RIM), 1.0, a_b)
    a1 = np.where(yy <= RIM, a_h, a_b).astype(np.float32)
    a1 = np.where(dil(M, 3), a1, 0.0)
    # the outline smoothed (4x, sigma 1 px) and anti-aliased, as the render's neighbours; the handles keep their thin rope
    hard = (a1 > 0.5).astype(np.float32)
    up = cv2.resize(hard, (W * 4, H * 4), interpolation=cv2.INTER_NEAREST)
    up = (cv2.GaussianBlur(up, (0, 0), 3.0) > 0.5).astype(np.float32)
    a_s = cv2.GaussianBlur(cv2.resize(up, (W, H), interpolation=cv2.INTER_AREA), (0, 0), 0.6)
    a_new = np.where(yy <= RIM, np.minimum(a_s, np.maximum(a1, 0)), np.where(core, 1.0, np.minimum(a_s, a0)))
    a_new = np.clip(a_new, 0, 1).astype(np.float32)
    # colour: un-mixed where soft, toward the rope's own colour; no render background left in the layer
    Fu = (I - (1 - aest[..., None]) * B) / np.maximum(aest, 0.5)[..., None]
    kk = np.clip((aest - 0.5) / 0.4, 0, 1)[..., None]
    col = np.clip(kk * Fu + (1 - kk) * F, 0, 1)
    rgb = np.where((band & (a_new < 0.95))[..., None], col, I)
    rgb = np.where(((yy <= RIM) & (a_new < 0.95))[..., None], F, rgb)
    rgb = np.where((a_new < 0.02)[..., None], F, rgb)                   # bleed: the rope's colour, never the render's wall
    Lb2 = np.dstack([np.clip(np.floor(rgb * 255 + 0.5), 0, 255), np.floor(a_new * 255 + 0.5)]).astype(np.uint8)
    Lb2[..., :3] = np.where((Lb2[..., 3] == 255)[..., None] & (Lb[..., 3] == 255)[..., None], Lb[..., :3], Lb2[..., :3])
    # the shadow: the frozen recipe's contact shadow where one can fall (floor and rug), carried in to the new edge
    potm = arr(L(BY["planter"]["file"]))[..., 3] > 25
    fl = floor_mask() & ~potm
    s0 = Sb.astype(np.float32) / 255
    old_in = Lb[..., 3] > 127
    new_in = Lb2[..., 3] > 127
    keep = fl & ~old_in
    exposed = fl & old_in & ~new_in                                     # floor px the old cut covered: the contact shadow carried in
    s1 = nearest_fill(s0, keep & (dil(old_in, 4)), exposed & dil(old_in, 0))
    wfl = cv2.GaussianBlur(fl.astype(np.float32), (0, 0), 1.5)
    s2 = 1 - (1 - s1) * np.where(fl, 1.0, wfl * (dil(fl, 3) & ~potm))[..., None]       # a 3 px anti-aliased edge at the skirting, none on the pot
    s2 = np.where(new_in[..., None] & (Lb2[..., 3:4] == 255), 1.0, s2)
    Sb2 = np.clip(np.floor(s2 * 255 + 0.5), 0, 255).astype(np.uint8)
    pf = os.path.join(OUT, "layers", "basket", f"basket-cj-jute-rope-cylinder-{TAG}.png")
    ps = os.path.join(OUT, "layers", "basket", f"basket-cj-jute-rope-cylinder-{TAG}-shadow.png")
    save(pf, Lb2)
    save(ps, Sb2)
    rec = dict(source=rel(os.path.join(P2, "work-r3", "r3a-regt.npy")) + " graded by stack.Grade (the core = the layer +-1)",
               rim_row=RIM, handles=dict(rule="alpha = min(old, smoothstep(C*, 11..19; 15..21 where L* < 35)), sigma 0.6", px_removed=int(((a0 > 0.5) & (a_new <= 0.5) & (yy <= RIM)).sum())),
               body=dict(rule="F / B projection in the band (dilate 3 minus erode 3), where |F - B| > 0.06; alpha never raised", px_removed=int(((a0 > 0.5) & (a_new <= 0.5) & (yy > RIM)).sum())),
               alpha_px_before=int((a0 > 0).sum()), alpha_px_after=int((Lb2[..., 3] > 0).sum()),
               shadow=dict(rule="the frozen recipe's shadow (layers/" + BY["basket-shadow"]["file"] + ") kept on the floor and the rug only; removed on the wall, the skirting and the pot; "
                                "floor px the old cut covered take the nearest outside value (no light line)",
                           px_before=int((Sb < 255).any(2).sum()), px_after=int((Sb2 < 255).any(2).sum()),
                           wall_pot_px_removed=int(((Sb < 255).any(2) & ~fl).sum()), carried_in_px=int(exposed.sum())),
               files=dict(layer=rel(pf), shadow=rel(ps)))
    os.makedirs(WORK, exist_ok=True)
    json.dump(rec, open(os.path.join(WORK, f"basket-{TAG}.json"), "w"), indent=1)
    print("basket", json.dumps(rec)[:800])
    return rec


def placement():
    """the brief's 'beside the pot with a gap': every floor point for the 35 x 39 basket (+9 handles), off the rug, 3 cm clear of the pot
    and the walls, scored on the image: the pot's right contour 1101 px, the sofa's left arm 1284 px, the rug's back-left corner (1125,
    1222); F3 needs >= 0.02 of the frame width (51 px) to each, or a decisive overlap"""
    import math
    FW = S0.FRAME_BOX[2] - S0.FRAME_BOX[0]

    def box(cx, cy, r=0.175, h=0.39, n=72):
        P = np.array([S0.project(cx + r * math.cos(t), cy + r * math.sin(t), z) for z in (0, h) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)])
        return P[:, 0].min(), P[:, 0].max(), P[:, 1].max()
    pot = box(-1.95, 0.42, 0.21, 0.355)
    best = []
    for X in np.arange(-2.12, -1.28, 0.02):
        for Y in np.arange(0.20, 1.00, 0.02):
            if math.hypot(X + 1.95, Y - 0.42) - 0.385 < 0.03 or X - 0.175 < -2.27 or (Y + 0.175 > 1.0 and X - 0.175 < -1.90) or Y - 0.175 < 0.03:
                continue
            if not (X + 0.175 <= -1.45 or Y + 0.175 <= 0.72):
                continue
            x0, x1, yb = box(X, Y)
            ov = max(0.0, min(x1, pot[1]) - max(x0, pot[0])) / (pot[1] - pot[0])
            g_pot = (x0 - pot[1]) / FW
            g_arm = (1284 - x1) / FW
            g_rug = (1222 - yb) / FW if x1 > 1100 else 1.0
            clear = (g_pot >= 0.02 or ov >= 0.35) and g_arm >= 0.02 and g_rug >= 0.02
            best.append(dict(X=round(float(X), 2), Y=round(float(Y), 2), pot_overlap=round(float(ov), 3), gap_pot=round(float(g_pot), 4), gap_arm=round(float(g_arm), 4), gap_rug=round(float(g_rug), 4), clear=bool(clear)))
    no_overlap = [b for b in best if b["pot_overlap"] == 0 and b["gap_pot"] >= 0.02 and b["gap_arm"] >= 0.02 and b["gap_rug"] >= 0.02]
    partial = [b for b in best if 0 < b["pot_overlap"] < 0.6 and b["clear"]]
    rec = dict(points=len(best), beside_with_gap_points=len(no_overlap), partial_overlap_points=len(partial),
               best_beside=sorted(best, key=lambda b: -min(b["gap_pot"], b["gap_arm"], b["gap_rug"]))[:3],
               now=dict(plan=(-1.62, 0.78), render=(-1.60, 0.762), pot_overlap=round(float((pot[1] - 1004) / (pot[1] - pot[0])), 3)),
               verdict="no floor point stands beside the pot with F3 gaps: the room between the pot (1101 px) and the sofa's arm (1284) is 183 px for "
                       "a 124 px basket, and the rug's corner (1125, 1222) closes it from the front; a smaller overlap is a tangent (< 0.02) to the pot, "
                       "the arm or the rug. The placement stays (designer 1.9.2 / 1.9.4: the decisive overlap)")
    json.dump(rec, open(os.path.join(WORK, f"placement-{TAG}.json"), "w"), indent=1)
    print("placement", json.dumps({k: v for k, v in rec.items() if k != "best_beside"}), rec["best_beside"][:1])
    return rec


# ================================================================================================= build
def files_new():
    f = {("cushions", st): f"cushions/set-{st}-{TAG}.png" for st in "BAC"}
    f.update({("cushions-shadow", st): f"cushions/set-{st}-shadow-{TAG}.png" for st in "BAC"})
    f["basket"] = f"basket/basket-cj-jute-rope-cylinder-{TAG}.png"
    f["basket-shadow"] = f"basket/basket-cj-jute-rope-cylinder-{TAG}-shadow.png"
    return f


def stack(st, new):
    f = files_new()
    out = []
    for l_ in man1["layers"]:
        k = l_["id"]
        if k == "base" or k.endswith("-shadow"):
            continue
        if k == "cushions":
            v = sets()[st]
            out.append((k, L(f[("cushions", st)]) if new else L(v["layer"]), L(f[("cushions-shadow", st)]) if new else L(v["shadow"])))
            continue
        sh = BY[k + "-shadow"]
        if new and k == "basket":
            out.append((k, L(f["basket"]), L(f["basket-shadow"])))
        else:
            out.append((k, L(l_["file"]), L(sh["file"])))
    return out


def build():
    base8 = arr(L(BY["base"]["file"]), "RGB")
    rec, R = {}, {}
    for st in "BAC":
        s_old = S0.compose8(base8, stack(st, False), {})
        s_new = S0.compose8(base8, stack(st, True), {})
        Rg = (s_old != s_new).any(2)
        t1 = arr(os.path.normpath(os.path.join(LAY, man1["truths"]["default"][st])), "RGB")
        truth = np.where(Rg[..., None], s_new, t1)
        fp = save(os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png"), truth)
        R[st] = Rg
        ys, xs = np.nonzero(Rg)
        rec[st] = dict(file=rel(fp), region_px=int(Rg.sum()), outside_region_vs_fb12s1_truth_px=int(((truth != t1).any(2) & ~Rg).sum()))
    np.savez_compressed(os.path.join(WORK, f"regions-{TAG}.npz"), **{f"default_{k}": v for k, v in R.items()})
    json.dump(rec, open(os.path.join(WORK, f"defaults-{TAG}.json"), "w"), indent=1)
    print("build", rec)
    return rec


def frames():
    for st in "BAC":
        im = Image.open(os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png")).convert("RGB")
        im.resize((1920, 1080), Image.LANCZOS, box=S0.FRAME_BOX).save(os.path.join(OUT, f"default-frame-{TAG}-set-{st}.png"))


def sheet():
    """before (fb12s1) and after (lfix) at x2 of the 1920 frame (= 1.497 x the canvas), each defect and each set"""
    k = 1920 / (S0.FRAME_BOX[2] - S0.FRAME_BOX[0]) * 2
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    boxes = [("cushion", (1500, 880, 1760, 1100)), ("throw", (1900, 1130, 2200, 1300)), ("basket", (930, 990, 1190, 1280))]
    tiles = []
    for name, (x0, y0, x1, y1) in boxes:
        for st in "BAC":
            b = Image.open(os.path.join(LAY, man1["truths"]["default"][st])).convert("RGB").crop((x0, y0, x1, y1))
            a = Image.open(os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png")).convert("RGB").crop((x0, y0, x1, y1))
            sz = (int((x1 - x0) * k), int((y1 - y0) * k))
            tiles.append((f"{name} {st}", b.resize(sz, Image.LANCZOS), a.resize(sz, Image.LANCZOS)))
    rows = []
    for t, b, a in tiles:
        w, h = b.size
        im = Image.new("RGB", (2 * w + 30, h + 40), "white")
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, im.width, 34), fill="black")
        d.text((10, 5), f"x2 {t}: before | after", fill="white", font=font)
        im.paste(b, (0, 40))
        im.paste(a, (w + 30, 40))
        rows.append(im)
    # three columns of rows (one per defect), stacked
    cols = [rows[i * 3:(i + 1) * 3] for i in range(3)]
    cw = [max(r.width for r in c) for c in cols]
    ch = [sum(r.height + 12 for r in c) for c in cols]
    out = Image.new("RGB", (sum(cw) + 24 * 2, max(ch)), "white")
    x = 0
    for c, w_ in zip(cols, cw):
        y = 0
        for r in c:
            out.paste(r, (x, y))
            y += r.height + 12
        x += w_ + 24
    p = os.path.join(OUT, "qa-sheet-living-fix.jpg")
    out.save(p, quality=90)
    print("sheet", out.size, p)


def records(scan_before=None, scan_after=None):
    f = files_new()
    m = json.loads(json.dumps(man1))
    m["id"] = "wm-living-room-m0-tool-layers-phase2-lfix"
    m["version"] = "lfix (the owner's three defects, 2026-11-25: the dark field behind the left cushion, the basket's box and cut, the throw's cut edge; supersedes manifest-fb12s1.json for the tool; fb12s1 kept for rollback)"
    m["date"] = "2026-11-25"
    m["brief"] = "briefs/wm-living-fix-cushion-basket-2026-11-25.md (+ the throw, the coordinator, same day)"
    m["approval"] += "; lfix: code only, 0 tokens (studio rules: 0-token code fixes are decided at once)"
    m["status"] = ("lfix: fb12s1 with three code fixes (0 tokens): the cushion sets' shadow right of the left cushion (a flat 0.35 field from phase 1) "
                   "now a contact shadow; the basket re-matted (the handles' loops and the light rim were the R3a render's wall) and its shadow on the "
                   "floor and rug only (the box on the wall and the pot is gone); each set's throw continues behind Olia (its cut edge followed the old "
                   "table) and the grey stripe on throws A and C is gone. Not QA'd; for qa-agent. HD_PUBLIC=0 only.")
    for st in "BAC":
        s_ = m["slot_cushions"]["sets"][st]
        s_["previous_layer"], s_["previous_shadow"] = s_["layer"], s_["shadow"]
        s_["layer"], s_["shadow"] = f[("cushions", st)], f[("cushions-shadow", st)]
        s_["lfix"] = "the shadow right of the left cushion capped by a contact shadow; the throw stretched behind Olia" + ("; the grey stripe filled" if st in "AC" else "")
    for l_ in m["layers"]:
        if l_["id"] == "basket":
            l_["previous_file"], l_["file"] = l_["file"], f["basket"]
            l_["lfix"] = "re-matted from the R3a render (graded): the handles' loop interiors and the light rim were the render's background"
        if l_["id"] == "basket-shadow":
            l_["previous_file"], l_["file"] = l_["file"], f["basket-shadow"]
            l_["lfix"] = "the frozen recipe's contact shadow on the floor and the rug only; the wall / skirting / pot part removed"
    m["truths"] = dict(default={st: f"../graded/default-scene-{TAG}-set-{st}-graded-v3c.png" for st in "BAC"},
                       variants_fb12s1=man1["truths"].get("variants_fb12s1"),
                       note="lfix: each default = the 8-bit stack of this manifest where it differs from fb12s1's stack, fb12s1's truth bytes elsewhere "
                            "(RND2 0 outside); the variants' truths are fb12s1's / R9's (their regions do not touch the cushions or the basket)")
    m["lfix"] = dict(record="../work-lfix/", script="../fix_lfix.py", verify="verify_layers_lfix.py -> verify-layers-lfix.json",
                     scan="scan_edge_bleed.py -> scan-edge-bleed-fb12s1.json (before), scan-edge-bleed-lfix.json (after)",
                     sheet="../qa-sheet-living-fix.jpg", frames=[f"../default-frame-{TAG}-set-{st}.png" for st in "BAC"], tokens=0)
    m.setdefault("history", [])
    if isinstance(m["history"], list):
        m["history"].append("lfix 2026-11-25: manifest-fb12s1.json -> manifest-lfix.json (the owner's three defects, code, 0 tokens)")
    json.dump(m, open(os.path.join(OUT, "layers", f"manifest-{TAG}.json"), "w"), indent=1, ensure_ascii=False)
    print("manifest written")


def asset_entries():
    """the new files' entries in assets/manifest.json 'assets' (re-read right before writing; same ids replaced, the rest appended)"""
    def e(id_, path, kind, status):
        fp = os.path.join(REPO, path)
        return dict(id=id_, path=path, kind=kind, room="living-room", style="warm-modern", created="2026-11-25", model="code (0 tokens)", tokens=0,
                    status=status, sha256=sha(fp), bytes=os.path.getsize(fp))
    stl = "warm-modern tool, lfix (the owner's three defects): not QA'd (qa-agent next); HD_PUBLIC=0 only"
    f = files_new()
    lp = lambda r_: rel(os.path.join(OUT, "layers", r_))  # noqa: E731
    E = []
    for st in "BAC":
        E.append(e(f"wm-tool-{TAG}-cushions-{st}", lp(f[("cushions", st)]), f"layer: cushion set {st} (z 55), the throw continued behind Olia" + (", the grey stripe filled" if st in "AC" else ""), stl))
        E.append(e(f"wm-tool-{TAG}-cushions-shadow-{st}", lp(f[("cushions-shadow", st)]), f"shadow: cushion set {st} (z 54), the dark field right of the left cushion -> a contact shadow", stl))
    E.append(e(f"wm-tool-{TAG}-basket", lp(f["basket"]), "layer: basket (z 60), re-matted: the handles' loops open, no render background in its edge", stl))
    E.append(e(f"wm-tool-{TAG}-basket-shadow", lp(f["basket-shadow"]), "shadow: basket (z 59), the recipe's contact shadow on the floor and the rug only", stl))
    for st in "BAC":
        E.append(e(f"wm-tool-{TAG}-default-{st}", rel(os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png")), f"truth: the default scene, set {st}", "QA material, not for the site"))
        E.append(e(f"wm-tool-{TAG}-frame-{st}", rel(os.path.join(OUT, f"default-frame-{TAG}-set-{st}.png")), f"frame 1920 x 1080: the default scene, set {st}", "preview, not for the site before QA"))
    for id_, path, kind in [
            (f"wm-tool-{TAG}-manifest", lp(f"manifest-{TAG}.json"), "layers manifest (supersedes manifest-fb12s1 for the tool)"),
            (f"wm-tool-{TAG}-verify", lp(f"verify-layers-{TAG}.json"), "verification record"),
            (f"wm-tool-{TAG}-qa-sheet", rel(os.path.join(OUT, "qa-sheet-living-fix.jpg")), "QA sheet: the cushion, the throw and the basket at x2, before / after, sets B, A, C"),
            (f"wm-tool-{TAG}-scan-before", lp("scan-edge-bleed-fb12s1.json"), "scan: carried background and false shadows, fb12s1 (before)"),
            (f"wm-tool-{TAG}-scan-after", lp(f"scan-edge-bleed-{TAG}.json"), "scan: carried background and false shadows, lfix (after)"),
            (f"wm-tool-{TAG}-records", rel(os.path.join(WORK, f"cushions-{TAG}.json")), "build record: the cushion sets (shadow zone, throw stretch, stripe)"),
            (f"wm-tool-{TAG}-basket-record", rel(os.path.join(WORK, f"basket-{TAG}.json")), "build record: the basket's matte and shadow"),
            (f"wm-tool-{TAG}-placement", rel(os.path.join(WORK, f"placement-{TAG}.json")), "the basket's placement grid (F3 against the pot, the sofa's arm and the rug)"),
            (f"wm-tool-{TAG}-build-script", rel(os.path.join(OUT, "fix_lfix.py")), "tool: the lfix build"),
            (f"wm-tool-{TAG}-verify-script", lp(f"verify_layers_{TAG}.py"), "tool: the lfix checks"),
            ("wm-tool-scan-edge-bleed-script", lp("scan_edge_bleed.py"), "tool: the carried-background / false-shadow scan, for every room's manifest (QA)")]:
        if os.path.exists(os.path.join(REPO, path)):
            E.append(e(id_, path, kind, "record / source, not for the site"))
    json.dump(dict(note="merged into assets/manifest.json 'assets' (render-agent 2026-11-25, lfix)", assets=E),
              open(os.path.join(OUT, "layers", f"asset-manifest-entries-{TAG}.json"), "w"), indent=1, ensure_ascii=False)
    p = os.path.join(REPO, "assets/manifest.json")
    m = json.load(open(p))
    ids = {x["id"] for x in E}
    m["assets"] = [x for x in m["assets"] if x["id"] not in ids] + E
    with open(p, "w") as fh:
        fh.write(json.dumps(m, indent=1, ensure_ascii=False))
    print("assets", len(E), "->", len(m["assets"]))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("cushions", "all"):
        cushions()
    if cmd in ("basket", "all"):
        basket()
    if cmd in ("placement", "all"):
        placement()
    if cmd in ("build", "all"):
        build()
        frames()
    if cmd in ("sheet", "all"):
        sheet()
    if cmd in ("records", "all"):
        records()
    if cmd == "assets":                                                  # after verify_layers_lfix.py and the two scans
        asset_entries()
