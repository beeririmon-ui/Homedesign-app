#!/usr/bin/env python3
"""
fix_basket.py: the jute basket of the warm-modern M0 living room moves to the designer's new point, in code, 0 tokens (render-agent,
2026-11-25). The decision: docs/proposals/wm-fb12-2026-11-25.md, last section "lfix, מקום הסל" (the owner: "dropped at random in front of
the olive pot"). NEW FILES ONLY (tag "basket"): every lfix / fb12s1 / fb12s0 file is read, never written; manifest-lfix.json stays for
rollback.

  where     the basket's floor centre (-1.62, 0.78) -> (-1.20, 0.30), on the parquet off the rug, 12.5 cm from the sofa's left arm side and
            from the back wall; same angle as today (the layer is not rotated); empty. The old centre is the one the layer's own axis shows:
            the body's centre column is x 1061.0 (median over its rows), the projection of the plan point (-1.62, 0.78) is 1060.84; the
            record's (-1.60, 0.762) (1070.91) is its measuring method's reading, biased by the same 1.5-2 cm the clay showed ((-1.605, 0.764)
            for a clay at the plan point). Mapping the axis puts the basket's centre itself on (-1.20, 0.30).
  layer     a similarity taken from the floor homography (fb12_s0.H_FLOOR, camera M0 1.2): the contact point is mapped by it, the scale is
            the depth ratio (= the homography's horizontal scale at the contact point); premultiplied, bicubic. Exposure: one factor in
            linear light (see exposure()). Occlusion: alpha x (1 - fa_s), fa_s = the plate's own fixed-furniture alpha (work-fb12s0, the
            sofa and the armchair) sharpened to its silhouette (see fa()), so the sofa's left arm stands in front of the basket's right side.
  shadow    the frozen recipe's contact shadow (the lfix file: extract.shadow_one, floor and rug only) moved by the floor homography itself
            (H T H^-1, T = the plan translation), its source holes (under the old basket, behind the pot) filled from the nearest floor
            value first; then re-cut for the new spot: floor and rug only (a 3 px anti-aliased edge at the skirting's foot, as lfix), none
            on the wall, the pot or the sofa (x (1 - fa_s)), none where the basket (behind the arm or not) hides the floor.
  old spot  without the basket layer the stack shows the plate, the pot (planter r7: the smooth band at its bottom is the product's own), its
            shadow and the rug. One fix there, in code (planter_shadow()): the light ring between the pot's base and its contact shadow,
            which the basket hid on the right of the base, is filled inside the old basket region.

  BASKET_OUT=<dir> writes everything under <dir> instead (development); default = this folder.
  python3.12 -I -B fix_basket.py all       (layer, shadow, build, frames, sheet, records)
  python3.12 -I -B fix_basket.py assets    (after layers/verify_layers_basket.py and the scan: the entries in assets/manifest.json)
"""
import hashlib
import importlib.util
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
LAY = os.path.join(P2, "layers")
OUT = os.environ.get("BASKET_OUT", P2)
WORK = os.path.join(OUT, "work-basket")
TAG = "basket"
MAN0 = os.path.join(LAY, "manifest-lfix.json")

OLD = (-1.62, 0.78)         # the basket's floor centre in the layer: its axis (x 1061.0) = the plan point's projection (see the docstring)
NEW = (-1.20, 0.30)         # the designer's point (wm-fb12-2026-11-25.md, "lfix, מקום הסל")
HOTSPOT_UV = (0.458, 0.75)  # the designer's dot, camera-frame uv, on the visible part
FA_PATH = os.path.join(P2, "work-fb12s0", "fixed-furniture-fb12s0.png")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


S0 = _load("fb12_s0", os.path.join(P2, "fb12_s0.py"))     # read-only: camera, H_FLOOR, compose8, FRAME_BOX, s2l / l2s
W, H = S0.W, S0.H
man0 = json.load(open(MAN0))
BY = {l_["id"]: l_ for l_ in man0["layers"]}
FX0, FY0, FX1, FY1 = S0.FRAME_BOX
FW, FH = FX1 - FX0, FY1 - FY0


def arr(p, mode=None):
    im = Image.open(p)
    return np.asarray(im.convert(mode) if mode else im)


def L(rel_):
    q = os.path.join(OUT, "layers", rel_)
    return q if os.path.exists(q) else os.path.join(LAY, rel_)


def save(p, a):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    Image.fromarray(a).save(p, optimize=False, compress_level=6)
    return p


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def rel(p):
    return os.path.relpath(p, REPO)


def dil(m, r):
    return cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0


def nearest_fill(val, known, todo):
    """each todo pixel takes the value of its nearest known pixel"""
    _, lbl = cv2.distanceTransformWithLabels((~known).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ky, kx = np.nonzero(known)
    lut = np.zeros((lbl.max() + 1,) + val.shape[2:], val.dtype)
    lut[lbl[ky, kx]] = val[ky, kx]
    out = val.copy()
    out[todo] = lut[lbl[todo]]
    return out


def lab(rgb01):
    """sRGB 0-1 -> OpenCV Lab (L* 0-100); any shape (..., 3)"""
    x = np.ascontiguousarray(rgb01, np.float32)
    return cv2.cvtColor(x.reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(x.shape)


def de2000(l1, l2):
    """CIEDE2000 between two Lab arrays (..., 3)"""
    L1, a1, b1 = [l1[..., i].astype(np.float64) for i in range(3)]
    L2, a2, b2 = [l2[..., i].astype(np.float64) for i in range(3)]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    dh = np.where(C1p * C2p == 0, 0, np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)))
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    hpm = np.where(C1p * C2p == 0, hs, np.where(np.abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    T = 1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm)) + 0.32 * np.cos(np.radians(3 * hpm + 6)) - 0.20 * np.cos(np.radians(4 * hpm - 63))
    dth = 30 * np.exp(-(((hpm - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25.0 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


# ================================================================================================= geometry
def depth(X, Y):
    a = math.radians(S0.CAM["yaw_deg_left"])
    fwd = np.array([-math.sin(a), -math.cos(a), 0.0])
    return float((np.array([X, Y, 0.0]) - np.array(S0.CAM["loc"], np.float64)) @ fwd)


def geometry():
    c0 = np.array(S0.project(OLD[0], OLD[1], 0.0))
    c1 = np.array(S0.project(NEW[0], NEW[1], 0.0))
    s = depth(*OLD) / depth(*NEW)
    A = np.array([[s, 0.0, c1[0] - s * c0[0]], [0.0, s, c1[1] - s * c0[1]]])
    T = np.array([[1.0, 0.0, NEW[0] - OLD[0]], [0.0, 1.0, NEW[1] - OLD[1]], [0.0, 0.0, 1.0]])
    Hm = S0.H_FLOOR @ T @ np.linalg.inv(S0.H_FLOOR)
    Hm = Hm / Hm[2, 2]
    # the homography's Jacobian at the old contact point (horizontal = the depth ratio; vertical ~ its square: the floor foreshortens)
    p = np.array([c0[0], c0[1], 1.0])
    q = Hm @ p
    J = (Hm[:2, :2] * q[2] - np.outer(q[:2], Hm[2, :2])) / q[2] ** 2
    return dict(c0=c0, c1=c1, s=s, A=A, Hm=Hm, T=T, J=J, depth_old=depth(*OLD), depth_new=depth(*NEW))


def fa():
    """the occluder: the plate's own fixed-furniture alpha (fb12s0), sharpened to the arm's silhouette. Against the bright wall fa' carries
    a 7 px feathered ramp (0.19-0.73, then 1) that the plate cannot show (wall and lit boucle are both ~230); on the floor rows, where the
    plate does show it, the silhouette is 1-2 px wide at fa ~0.5 (x 1283.5). smoothstep(0.35, 0.65) puts the cut there on every row:
    with the raw ramp the jute would fade over 7 px into the bright edge (a halo); with it the jute meets the arm's lit boucle rim."""
    f = arr(FA_PATH)[..., 3].astype(np.float32) / 255.0
    t = np.clip((f - 0.35) / 0.30, 0, 1)
    return (t * t * (3 - 2 * t)).astype(np.float32)


def floor_mask():
    """the floor (and the rug lying on it) as M0 sees it (fix_lfix.floor_mask): in front of the back wall, right of the window wall"""
    X_, Y_ = S0.img_to_plane(S0.H_FLOOR)
    return (Y_ > 0.004) & (X_ > -2.296) & (np.arange(H)[:, None] > 900)


# ================================================================================================= exposure
def exposure(base_lum, fam):
    """the plate's ratio between the two spots (the decision: floor and wall), and the factor used.
    floor: the parquet in front of each basket (Y + 0.19..0.45, |X - x| < 0.25); wall: the back wall behind it (Z 0.13-0.45, its image
    span), both clear of the sofa (fa), the pot and the plate's patch behind the pot (x <= 1101). Medians of linear luminance."""
    X_, Y_ = S0.img_to_plane(S0.H_FLOOR)
    Xw, Zw = S0.img_to_plane(S0.plane_H("y", 0.0))
    yy = np.arange(H)[:, None] + np.zeros((1, W))
    xx = np.arange(W)[None, :] + np.zeros((H, 1))
    fl = floor_mask()
    potd = dil(arr(L(BY["planter"]["file"]))[..., 3] > 0, 4)
    out = {}
    for nm, (cx, cy) in dict(old=OLD, new=NEW).items():
        x0, _ = S0.project(cx - 0.18, cy, 0.0)
        x1, _ = S0.project(cx + 0.18, cy, 0.0)
        wall = (~fl) & (xx >= x0) & (xx <= x1) & (Zw > 0.13) & (Zw < 0.45) & (Xw > -2.29) & (fam < 0.02) & ~potd & (xx > 1101)
        front = fl & (Y_ > cy + 0.19) & (Y_ < cy + 0.45) & (np.abs(X_ - cx) < 0.25) & (fam < 0.02) & ~potd
        out[nm] = dict(wall=float(np.median(base_lum[wall])), wall_px=int(wall.sum()), floor=float(np.median(base_lum[front])), floor_px=int(front.sum()))
    r_wall = out["new"]["wall"] / out["old"]["wall"]
    r_floor = out["new"]["floor"] / out["old"]["floor"]
    out["ratio_wall"], out["ratio_floor"] = round(r_wall, 3), round(r_floor, 3)
    out["ratio_plate"] = round(math.sqrt(r_wall * r_floor), 3)
    return out


# ================================================================================================= the layer
def layer(G, gain):
    Lb = arr(L(BY["basket"]["file"]))
    a = Lb[..., 3].astype(np.float32) / 255
    rgb = Lb[..., :3].astype(np.float32) / 255
    pm = np.dstack([rgb * a[..., None], a]).astype(np.float32)
    w = cv2.warpAffine(pm, G["A"], (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    aw = np.clip(w[..., 3], 0, 1)
    aw = np.where(aw > 0.996, 1.0, np.where(aw < 0.004, 0.0, aw)).astype(np.float32)
    ok = aw > 0.02
    col = np.clip(w[..., :3], 0, None) / np.maximum(aw, 1e-6)[..., None]
    col = np.clip(col, 0, 1)
    col = nearest_fill(col, ok, (~ok) & dil(aw > 0, 6))                 # the soft rim and the bleed: the rope's own colour
    col = np.where(((~ok) & ~dil(aw > 0, 6))[..., None], 0.0, col)
    col_g = S0.l2s(S0.s2l(col) * gain)                                  # exposure: one factor in linear light
    F = fa()
    a_vis = aw * (1.0 - F)                                              # the sofa's arm (in the plate) in front of the basket
    a8 = np.floor(a_vis * 255 + 0.5).astype(np.uint8)
    a8u = np.floor(aw * 255 + 0.5).astype(np.uint8)                     # unoccluded (for the visible share; not written as a layer)
    L8 = np.dstack([np.floor(col_g * 255 + 0.5), a8]).astype(np.uint8)
    L8u = np.dstack([np.floor(col * 255 + 0.5), a8u]).astype(np.uint8)  # moved, no exposure, unoccluded: the fidelity reference
    return L8, L8u


# ================================================================================================= the shadow
def shadow(G, L8, L8u):
    Lb0 = arr(L(BY["basket"]["file"]))
    S8 = arr(L(BY["basket-shadow"]["file"]), "RGB")
    D = 1.0 - S8.astype(np.float32) / 255
    potm = arr(L(BY["planter"]["file"]))[..., 3] > 25
    fl = floor_mask()
    old_in = Lb0[..., 3] > 0
    valid = fl & ~potm & ~old_in
    todo = dil(old_in, 30) & ~valid & (dil(fl, 2) | old_in)
    Df = nearest_fill(D, valid, todo)                                   # the source's holes: under the old cut, behind the pot
    Dn = cv2.warpPerspective(Df, G["Hm"], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    F = fa()
    wfl = cv2.GaussianBlur(fl.astype(np.float32), (0, 0), 1.5)
    wgt = np.where(fl & ~potm, 1.0, wfl * (dil(fl, 3) & ~potm))          # floor and rug; a 3 px anti-aliased edge at the skirting's foot
    wgt = wgt * (1.0 - F)                                               # none on the sofa
    Dn = np.clip(Dn, 0, 1) * wgt[..., None]
    Dn = np.where((L8u[..., 3] == 255)[..., None], 0.0, Dn)             # none where the basket (behind the arm or not) hides the floor
    S8n = np.clip(np.floor((1.0 - Dn) * 255 + 0.5), 0, 255).astype(np.uint8)
    return S8n, dict(src_holes_filled_px=int(todo.sum()), px=int((S8n < 255).any(2).sum()), darkening_max=round(float(Dn.max()), 3),
                     px_on_sofa_fa_over_0_5=int(((S8n < 255).any(2) & (F > 0.5)).sum()), max_levels_on_sofa_fa_over_0_5=int((255 - S8n.min(2))[F > 0.5].max()))


# ================================================================================================= files
def files_new():
    return dict(basket=f"basket/basket-cj-jute-rope-cylinder-{TAG}.png", shadow=f"basket/basket-cj-jute-rope-cylinder-{TAG}-shadow.png",
                planter_shadow=f"planter/planter-cj-cement-ribbed-belly-{TAG}-shadow.png")


# ================================================================================================= the old spot: the pot's contact
def old_region():
    """the old basket's region (the lfix layer's alpha > 0 or its shadow < 255): the only place outside the new region that may change"""
    return (arr(L(BY["basket"]["file"]))[..., 3] > 0) | (arr(L(BY["basket-shadow"]["file"]), "RGB") < 255).any(2)


def planter_shadow():
    """the pot's base, now seen whole: its contact shadow (the R5 file) is weakest right at the R7 cut's soft edge and darkest 3-5 px out,
    so a light ring (~5 L*, 2-3 px) runs between the base and its shadow (a double contour at x2, on the right of the base the basket hid).
    Inside the old basket region only, at the base (rows >= 1135), on the cut's soft edge and the floor up to 3 px out, the shadow takes the
    darkest value within 5 px (the ring's own), so it hugs the base; faded in over 8 px from the region's border and row 1135. The pot's pixels and its
    alpha are untouched (the smooth band at the bottom is the product's own: the card's 'smooth diagonal band', the SKU photos)."""
    a = arr(L(BY["planter"]["file"]))[..., 3].astype(np.float32) / 255
    S5 = arr(L(BY["planter-shadow"]["file"]), "RGB").astype(np.float32) / 255
    R = old_region()
    yy = np.arange(H)[:, None] + np.zeros((1, W))
    inside = a > 0.5
    d_out = cv2.distanceTransform((~inside).astype(np.uint8), cv2.DIST_L2, 5)
    zone = (yy >= 1135) & (((a > 0) & (a < 1)) | ((~inside) & (d_out <= 3.0)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    Sx = np.where(inside[..., None], 1.0, S5).astype(np.float32)
    ring = np.dstack([cv2.erode(Sx[..., i], k) for i in range(3)])
    fixd = np.minimum(S5, ring)
    dR = cv2.distanceTransform(R.astype(np.uint8), cv2.DIST_L2, 5)
    w = (np.clip(dR / 8.0, 0, 1) * np.clip((yy - 1135) / 8.0, 0, 1) * zone * R).astype(np.float32)
    out = S5 * (1 - w[..., None]) + fixd * w[..., None]
    S8 = arr(L(BY["planter-shadow"]["file"]), "RGB")
    o8 = np.where((w > 0)[..., None], np.clip(np.floor(out * 255 + 0.5), 0, 255), S8).astype(np.uint8)
    gap = lambda S: int(((S.astype(np.float32) / 255 - ring) > 0.06).any(2)[zone & (w > 0.99)].sum())  # noqa: E731
    ch = (o8 != S8).any(2)
    return o8, dict(changed_px=int(ch.sum()), changed_outside_old_region_px=int((ch & ~R).sum()),
                    light_gap_px_before=gap(S8), light_gap_px_after=gap(o8), zone_px=int(zone.sum()),
                    rule="in the old basket region, rows >= 1135, the R7 cut's soft edge and the floor <= 3 px out: min(shadow, the darkest within 5 px); "
                         "faded in over 8 px from the region's border and from row 1135")


def stack(st, new):
    f = files_new()
    out = []
    for l_ in man0["layers"]:
        k = l_["id"]
        if k == "base" or k.endswith("-shadow"):
            continue
        if k == "cushions":
            v = man0["slot_cushions"]["sets"][st]
            out.append((k, L(v["layer"]), L(v["shadow"])))
            continue
        if new and k == "basket":
            out.append((k, L(f["basket"]), L(f["shadow"])))
        elif new and k == "planter":
            out.append((k, L(l_["file"]), L(f["planter_shadow"])))
        else:
            out.append((k, L(l_["file"]), L(BY[k + "-shadow"]["file"])))
    return out


def make():
    os.makedirs(WORK, exist_ok=True)
    G = geometry()
    base8 = arr(L(BY["base"]["file"]), "RGB")
    base_lum = S0.lum(S0.s2l(base8.astype(np.float32) / 255))
    F = fa()
    ex = exposure(base_lum, F)
    # the factor: the plate's ratio, held to the fidelity bar (dE00 <= 3 against the same file) and to no clipped highlight
    _, L8u = layer(G, 1.0)
    core = (L8u[..., 3] == 255) & (F < 0.02)
    lin = S0.s2l(L8u[..., :3].astype(np.float32) / 255)
    lab0 = lab(L8u[..., :3][core].astype(np.float32) / 255)
    cap = 1.0
    for g in np.arange(1.0, 2.501, 0.005):
        lab1 = lab(S0.l2s(np.clip(lin[core] * g, 0, 1)))
        d = de2000(lab0, lab1)
        if np.percentile(d, 95) > 3.0 or np.percentile(lin[core].max(1) * g, 99.5) > 1.0:
            break
        cap = float(g)
    gain = min(ex["ratio_plate"], cap)
    ex.update(cap_dE00_p95_3=round(cap, 3), gain=round(gain, 3),
              rule="gain = min(the plate's ratio (geometric mean of floor and wall), the largest factor whose dE00 p95 against the same file "
                   "is <= 3 and whose p99.5 linear channel stays <= 1); one factor on RGB in linear light")
    L8, L8u = layer(G, gain)
    S8n, rs = shadow(G, L8, L8u)
    P8, rp = planter_shadow()
    f = files_new()
    pf = save(os.path.join(OUT, "layers", f["basket"]), L8)
    ps = save(os.path.join(OUT, "layers", f["shadow"]), S8n)
    pp = save(os.path.join(OUT, "layers", f["planter_shadow"]), P8)
    np.savez_compressed(os.path.join(WORK, f"unoccluded-{TAG}.npz"), alpha=L8u[..., 3])
    a_old = arr(L(BY["basket"]["file"]))[..., 3] > 127
    wid = a_old.sum(1)
    rows = np.nonzero(wid >= 0.6 * np.median(wid[wid > 0]))[0]
    axis_x = float(np.median([(np.nonzero(a_old[y])[0].min() + np.nonzero(a_old[y])[0].max()) / 2 for y in range(rows.min() + 8, rows.max() - 8)]))
    rec = dict(old_floor_centre=OLD, new_floor_centre=NEW,
               old_centre_evidence=dict(layer_axis_x=axis_x, plan_point_x=round(float(G["c0"][0]), 2),
                                        record_render_centre=[-1.60, 0.762], record_render_centre_x=round(float(S0.project(-1.60, 0.762, 0.0)[0]), 2),
                                        note="the record's centre carries its method's bias (the clay read the same way: (-1.605, 0.764)); the axis is the plan point"),
               contact_px=dict(old=[round(float(v), 2) for v in G["c0"]], new=[round(float(v), 2) for v in G["c1"]]),
               depth_m=dict(old=round(G["depth_old"], 4), new=round(G["depth_new"], 4)), scale=round(G["s"], 5),
               affine=[[round(float(v), 6) for v in r_] for r_ in G["A"]], floor_homography_move=S0.homog(G["Hm"]),
               homography_jacobian_at_contact=[[round(float(v), 4) for v in r_] for r_ in G["J"]],
               plan_translation_m=[round(NEW[0] - OLD[0], 3), round(NEW[1] - OLD[1], 3)],
               exposure=ex, shadow=rs, occluder=dict(file=rel(FA_PATH), rule="alpha x (1 - smoothstep(0.35, 0.65, fa)): the plate's own sofa alpha (fb12s0), sharpened to its silhouette (fa() docstring)"),
               planter_shadow=rp, files=dict(layer=rel(pf), shadow=rel(ps), planter_shadow=rel(pp)))
    json.dump(rec, open(os.path.join(WORK, f"basket-{TAG}.json"), "w"), indent=1)
    print("make", json.dumps(dict(scale=rec["scale"], contact=rec["contact_px"], exposure=ex, shadow=rs, planter_shadow=rp)))
    return rec


def build():
    base8 = arr(L(BY["base"]["file"]), "RGB")
    rec, R = {}, {}
    for st in "BAC":
        s_old = S0.compose8(base8, stack(st, False), {})
        s_new = S0.compose8(base8, stack(st, True), {})
        Rg = (s_old != s_new).any(2)
        t0 = arr(os.path.normpath(os.path.join(LAY, man0["truths"]["default"][st])), "RGB")
        truth = np.where(Rg[..., None], s_new, t0)
        fp = save(os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png"), truth)
        R[st] = Rg
        rec[st] = dict(file=rel(fp), region_px=int(Rg.sum()), outside_region_vs_lfix_truth_px=int(((truth != t0).any(2) & ~Rg).sum()))
    np.savez_compressed(os.path.join(WORK, f"regions-{TAG}.npz"), **{f"default_{k}": v for k, v in R.items()})
    json.dump(rec, open(os.path.join(WORK, f"defaults-{TAG}.json"), "w"), indent=1)
    print("build", rec)
    return rec


def frames():
    for st in "BAC":
        im = Image.open(os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png")).convert("RGB")
        im.resize((1920, 1080), Image.LANCZOS, box=S0.FRAME_BOX).save(os.path.join(OUT, f"default-frame-{TAG}-set-{st}.png"))


# ================================================================================================= the QA sheet
def sheet():
    """x1: the whole room, set B, before (lfix) | after (basket); x2 (1.497 x the canvas): the old spot and the new spot, set B, before |
    after, and the new spot after in sets A and C"""
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    k = 1920 / FW * 2

    def head(im, text):
        out = Image.new("RGB", (im.width, im.height + 40), "white")
        d = ImageDraw.Draw(out)
        d.rectangle((0, 0, out.width, 36), fill="black")
        d.text((10, 4), text, fill="white", font=font)
        out.paste(im, (0, 40))
        return out

    b1 = Image.open(os.path.join(P2, "default-frame-lfix-set-B.png")).convert("RGB")
    a1 = Image.open(os.path.join(OUT, f"default-frame-{TAG}-set-B.png")).convert("RGB")
    row1 = [head(b1, "x1 set B: before (lfix)"), head(a1, "x1 set B: after (basket)")]

    def crop2(p, box):
        im = Image.open(p).convert("RGB").crop(box)
        return im.resize((int(round(im.width * k)), int(round(im.height * k))), Image.LANCZOS)
    tb = lambda st: os.path.normpath(os.path.join(LAY, man0["truths"]["default"][st]))  # noqa: E731
    ta = lambda st: os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png")  # noqa: E731
    old_box, new_box = (920, 980, 1200, 1290), (1150, 960, 1450, 1290)
    row2 = [head(crop2(tb("B"), old_box), "x2 old spot B: before"), head(crop2(ta("B"), old_box), "x2 old spot B: after"),
            head(crop2(tb("B"), new_box), "x2 new spot B: before"), head(crop2(ta("B"), new_box), "x2 new spot B: after"),
            head(crop2(ta("A"), new_box), "x2 new spot A: after"), head(crop2(ta("C"), new_box), "x2 new spot C: after")]
    gap = 24
    w1 = sum(r.width for r in row1) + gap
    w2 = sum(r.width for r in row2) + gap * (len(row2) - 1)
    Wd = max(w1, w2)
    Hd = max(r.height for r in row1) + gap + max(r.height for r in row2)
    out = Image.new("RGB", (Wd, Hd), "white")
    x = 0
    for r in row1:
        out.paste(r, (x, 0))
        x += r.width + gap
    x, y = 0, max(r.height for r in row1) + gap
    for r in row2:
        out.paste(r, (x, y))
        x += r.width + gap
    p = os.path.join(OUT, f"qa-sheet-{TAG}.jpg")
    out.save(p, quality=88)
    print("sheet", out.size, p)


# ================================================================================================= records
def region_of(lf, sf):
    a = arr(lf)[..., 3]
    s = arr(sf, "RGB")
    m = (a > 0) | (s < 255).any(2)
    ys, xs = np.nonzero(m)
    bb = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    return dict(px=int(m.sum()), alpha_255_px=int((a == 255).sum()), bbox_px=bb,
                rect_canvas_uv=[round(bb[0] / W, 4), round(bb[2] / W, 4), round(bb[1] / H, 4), round(bb[3] / H, 4)],
                rect_camera_frame_uv=[round((bb[0] - FX0) / FW, 4), round((bb[2] - FX0) / FW, 4), round((bb[1] - FY0) / FH, 4), round((bb[3] - FY0) / FH, 4)])


def records():
    f = files_new()
    rec = json.load(open(os.path.join(WORK, f"basket-{TAG}.json")))
    m = json.loads(json.dumps(man0))
    m["id"] = "wm-living-room-m0-tool-layers-phase2-basket"
    m["version"] = ("basket (the basket moves to the designer's point, 2026-11-25: (-1.20, 0.30) by the sofa's left arm, off the rug, empty; "
                    "supersedes manifest-lfix.json for the tool; lfix kept for rollback)")
    m["date"] = "2026-11-25"
    m["brief"] = "docs/proposals/wm-fb12-2026-11-25.md, section 'lfix, מקום הסל' (the designer; the owner's note: dropped at random in front of the olive pot)"
    m["approval"] += "; basket: code only, 0 tokens (the coordinator, 2026-11-25); the slot's new point in data/slots waits for the owner's yes (the designer's note)"
    m["status"] = (f"basket: lfix with the basket moved in code (0 tokens) from {OLD} to {NEW}: the same layer, scaled by the depth "
                   "ratio about its floor contact, exposure-matched, hidden behind the sofa's left arm by the plate's own sofa alpha; its contact shadow "
                   "moved by the floor homography and re-cut (floor only). The old spot shows the pot, the floor and the rug; the pot's contact shadow hugs its base there (planter-shadow, inside the old region only). Not QA'd; for qa-agent. "
                   "HD_PUBLIC=0 only.")
    lp = lambda r_: os.path.join(OUT, "layers", r_)  # noqa: E731
    for l_ in m["layers"]:
        if l_["id"] == "basket":
            l_["previous_file"], l_["file"] = l_["file"], f["basket"]
            l_["previous_region"] = l_.get("region")
            l_["region"] = region_of(lp(f["basket"]), lp(f["shadow"]))
            a = arr(lp(f["basket"]))[..., 3]
            l_["build"] = dict(alpha_px=int((a > 0).sum()), alpha_255_px=int((a == 255).sum()), soft_px=int(((a > 0) & (a < 255)).sum()),
                               shadow_px=int((arr(lp(f["shadow"]), "RGB") < 255).any(2).sum()),
                               bleed_px=int((arr(lp(f["basket"]))[..., :3] > 0).any(2).sum()), note="basket round: recomputed for the moved file")
            l_["behind_fixed_furniture"] = True
            l_["hotspot"] = dict(frame="M0", u=HOTSPOT_UV[0], v=HOTSPOT_UV[1], plan=[NEW[0], NEW[1]], provisional=True,
                                 note="the designer's dot on the visible part; data/slots/living-room.json is the coordinator's (after the owner's yes)")
            l_["basket_move"] = dict(record="../work-basket/basket-basket.json", from_m=list(OLD), to_m=list(NEW),
                                     contact_px=rec["contact_px"], scale=rec["scale"], affine=rec["affine"],
                                     exposure_gain_linear=rec["exposure"]["gain"], plate_ratio=rec["exposure"]["ratio_plate"],
                                     occluder="work-fb12s0/fixed-furniture-fb12s0.png alpha (the plate's sofa): alpha x (1 - smoothstep(0.35, 0.65, fa))",
                                     angle="unchanged (the layer is not rotated: the view direction turns ~7 deg, a rope cylinder about its axis)",
                                     contents="empty, as the SKU photo")
        if l_["id"] == "planter-shadow":
            l_["previous_file"], l_["file"] = l_["file"], f["planter_shadow"]
            l_["basket_move"] = ("the pot's base, now seen whole: inside the old basket region only, its contact shadow hugs the base (the light "
                                 "ring between the R7 cut's soft edge and the R5 shadow's darkest line filled with that line's value); "
                                 f"{rec['planter_shadow']['changed_px']} px changed, 0 outside the old region")
        if l_["id"] == "basket-shadow":
            l_["previous_file"], l_["file"] = l_["file"], f["shadow"]
            l_["basket_move"] = (f"the lfix file (the frozen recipe's contact shadow) moved by the floor homography H T H^-1 (T = plan {rec['plan_translation_m']} m) "
                                 "after its holes were filled from the nearest floor value; re-cut: floor and rug only (3 px anti-aliased at the "
                                 "skirting's foot), none on the wall, the pot or the sofa, none under the basket's full alpha")
    m["truths"] = dict(default={st: f"../graded/default-scene-{TAG}-set-{st}-graded-v3c.png" for st in "BAC"},
                       variants_fb12s1=man0["truths"].get("variants_fb12s1"),
                       note="basket: each default = the 8-bit stack of this manifest where it differs from lfix's stack, lfix's truth bytes "
                            "elsewhere (RND2 0 outside the old and new basket regions); the variants' truths are fb12s1's / R9's (their regions "
                            "do not touch either basket region)")
    m["basket"] = dict(record="../work-basket/", script="../fix_basket.py", verify="verify_layers_basket.py -> verify-layers-basket.json",
                       scan="scan_edge_bleed.py -> scan-edge-bleed-lfix.json (before), scan-edge-bleed-basket.json (after)",
                       sheet="../qa-sheet-basket.jpg", frames=[f"../default-frame-{TAG}-set-{st}.png" for st in "BAC"], tokens=0,
                       previous_manifest="manifest-lfix.json")
    if isinstance(m.get("history"), dict):
        m["history"]["basket"] = "2026-11-25: manifest-lfix.json -> manifest-basket.json (the basket to the designer's point, code, 0 tokens)"
    json.dump(m, open(os.path.join(OUT, "layers", f"manifest-{TAG}.json"), "w"), indent=1, ensure_ascii=False)
    print("manifest written")


def asset_entries():
    """the new files' entries in assets/manifest.json 'assets' (re-read right before writing; same ids replaced, the rest appended)"""
    def e(id_, path, kind, status):
        fp = os.path.join(REPO, path)
        return dict(id=id_, path=path, kind=kind, room="living-room", style="warm-modern", created="2026-11-25", model="code (0 tokens)", tokens=0,
                    status=status, sha256=sha(fp), bytes=os.path.getsize(fp))
    stl = "warm-modern tool, basket move (the designer's point): not QA'd (qa-agent next); HD_PUBLIC=0 only"
    f = files_new()
    lp = lambda r_: rel(os.path.join(OUT, "layers", r_))  # noqa: E731
    E = [e(f"wm-tool-{TAG}-basket", lp(f["basket"]), "layer: basket (z 60) at (-1.20, 0.30), behind the sofa's left arm, exposure-matched", stl),
         e(f"wm-tool-{TAG}-basket-shadow", lp(f["shadow"]), "shadow: basket (z 59), the recipe's contact shadow moved by the floor homography, floor only", stl),
         e(f"wm-tool-{TAG}-planter-shadow", lp(f["planter_shadow"]), "shadow: planter (z 31), the base's contact shadow without the light ring, inside the old basket region only", stl)]
    for st in "BAC":
        E.append(e(f"wm-tool-{TAG}-default-{st}", rel(os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png")), f"truth: the default scene, set {st}", "QA material, not for the site"))
        E.append(e(f"wm-tool-{TAG}-frame-{st}", rel(os.path.join(OUT, f"default-frame-{TAG}-set-{st}.png")), f"frame 1920 x 1080: the default scene, set {st}", "preview, not for the site before QA"))
    for id_, path, kind in [
            (f"wm-tool-{TAG}-manifest", lp(f"manifest-{TAG}.json"), "layers manifest (supersedes manifest-lfix for the tool)"),
            (f"wm-tool-{TAG}-verify", lp(f"verify-layers-{TAG}.json"), "verification record"),
            (f"wm-tool-{TAG}-qa-sheet", rel(os.path.join(OUT, f"qa-sheet-{TAG}.jpg")), "QA sheet: x1 the room (set B) and x2 both spots, before / after"),
            (f"wm-tool-{TAG}-scan-after", lp(f"scan-edge-bleed-{TAG}.json"), "scan: carried background and false shadows, basket (after)"),
            (f"wm-tool-{TAG}-record", rel(os.path.join(WORK, f"basket-{TAG}.json")), "build record: the move, the exposure, the shadow"),
            (f"wm-tool-{TAG}-build-script", rel(os.path.join(OUT, "fix_basket.py")), "tool: the basket-move build"),
            (f"wm-tool-{TAG}-verify-script", lp(f"verify_layers_{TAG}.py"), "tool: the basket-move checks")]:
        if os.path.exists(os.path.join(REPO, path)):
            E.append(e(id_, path, kind, "record / source, not for the site"))
    json.dump(dict(note="merged into assets/manifest.json 'assets' (render-agent 2026-11-25, basket move)", assets=E),
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
    if cmd in ("make", "all"):
        make()
    if cmd in ("build", "all"):
        build()
        frames()
    if cmd in ("sheet", "all"):
        sheet()
    if cmd in ("records", "all"):
        records()
    if cmd == "assets":
        asset_entries()
