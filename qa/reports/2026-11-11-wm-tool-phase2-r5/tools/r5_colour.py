#!/usr/bin/env python3
"""
qa-agent 2026-11-11 (R5): the colour fixes in code, checked for honesty (faithful to the card, not only inside the numeric targets).

Two readings for every product (median over a clean mask, Lab D65, OpenCV):
  abs   the pixels as they are in the graded scene (what render-agent's targets were written in);
  rel   'as the eye reads it in the room': the linear-RGB pixel divided channel by channel by the room's white (von Kries), then Lab
        against D65, so the room's white reads (100, 0, 0). The room's white = the lit back-wall plaster (base.png, x 1100-1400,
        y 200-600, no product there). The supplier photo gets the same treatment against its own white (its brightest neutral area),
        so both sides are 'colour relative to white'. A cream fabric must keep a cream offset from the white in both; a fabric that
        is only as far from the room's white as the white itself reads grey / white.
  For the planter, in a shaded corner, also 'rel_local': against the shaded plaster beside it (the same light falls on both).

Also: the floor lamp's wisp (QA R4's measure, r5), the magazine holder's rods (L* / C* on the two rod bands of fix-r5.json) and the
vases (lit half). Supplier photos: the scratchpad only, never in the repo.
Writes data/colour.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r5")
SC = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
m5 = json.load(open(os.path.join(P2, "layers/manifest-r5.json")))
m4 = json.load(open(os.path.join(P2, "layers/manifest-r4.json")))
b5 = {l_["id"]: l_ for l_ in m5["layers"]}
b4 = {l_["id"]: l_ for l_ in m4["layers"]}
vf = {v["id"]: v["file"] for vs in m5["variants"].values() for v in vs}


def rgb(p):
    return np.asarray(Image.open(p).convert("RGB"))


def lin(c8):
    c = c8.astype(np.float64) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def enc(l_):
    l_ = np.clip(l_, 0, 1)
    return np.where(l_ <= 0.0031308, 12.92 * l_, 1.055 * l_ ** (1 / 2.4) - 0.055)


def lab_f(c01):
    return cv2.cvtColor(c01.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float64)


def summ(lab):
    L, a, b = np.median(lab, 0)
    C = np.hypot(lab[:, 1], lab[:, 2])
    return dict(L=round(float(L), 2), a=round(float(a), 2), b=round(float(b), 2), C=round(float(np.hypot(a, b)), 2),
                h=round(float(np.degrees(np.arctan2(b, a)) % 360), 1), C_px_p95=round(float(np.percentile(C, 95)), 2), px=int(len(lab)))


def abs_lab(px8):
    return summ(lab_f(px8.astype(np.float64) / 255))


def rel_lab(px8, white_lin):
    """von Kries in linear RGB against the white, scaled so the white's luminance stays its own (L of the white -> 100)"""
    r = lin(px8) / white_lin[None, :]
    return summ(lab_f(enc(np.clip(r, 0, 1))))


SCENE = {"r5": rgb(os.path.join(P2, "graded/default-scene-r5-set-B-graded-v3c.png")),
         "r4": rgb(os.path.join(P2, "graded/default-scene-r4-set-B-graded-v3c.png"))}
BASE = rgb(os.path.join(P2, "layers/base.png"))
wall = BASE[200:600, 1100:1400].reshape(-1, 3)
W_ROOM = np.median(lin(wall), 0)
res = dict(room_white=dict(patch="base.png x 1100-1400, y 200-600", abs=abs_lab(wall), lin_rgb=[round(float(v), 4) for v in W_ROOM]))


def photo(path, box, keep=None, white_box=None):
    im = rgb(path)
    c = im[box[1]:box[3], box[0]:box[2]].reshape(-1, 3)
    L = lab_f(c.astype(np.float64) / 255)[:, 0]
    if keep:
        c = c[(L > keep[0]) & (L < keep[1])]
    if white_box:
        w = im[white_box[1]:white_box[3], white_box[0]:white_box[2]].reshape(-1, 3)
    else:
        allp = im.reshape(-1, 3)
        Lall = lab_f(allp.astype(np.float64) / 255)[:, 0]
        w = allp[Lall >= np.percentile(Lall, 98)]
    wl = np.median(lin(w), 0)
    return dict(file=os.path.relpath(path, SC), abs=abs_lab(c), rel=rel_lab(c, wl), white_abs=abs_lab(w))


def mask_of(f, erode=5, rows=None, cols=None):
    a = np.asarray(Image.open(os.path.join(P2, "layers", f)))[..., 3]
    m = cv2.erode((a == 255).astype(np.uint8), np.ones((erode, erode), np.uint8)) > 0
    if rows:
        r = np.zeros_like(m)
        r[rows[0]:rows[1]] = True
        m &= r
    if cols:
        c = np.zeros_like(m)
        c[:, cols[0]:cols[1]] = True
        m &= c
    return m


# ---------------------------------------------------------------- curtains
cm = mask_of(b5["curtains"]["file"], rows=(100, 1400))
res["curtains"] = dict(
    r4=dict(abs=abs_lab(SCENE["r4"][cm]), rel=rel_lab(SCENE["r4"][cm], W_ROOM)),
    r5=dict(abs=abs_lab(SCENE["r5"][cm]), rel=rel_lab(SCENE["r5"][cm], W_ROOM)),
    photo=photo(os.path.join(SC, "ph2/refs-dl/curtains/img1.jpg"), (100, 100, 900, 650)))
# the plaster beside the curtain, measured clean: the back wall right of the glazing is far; the window lining (the reveal) next to the
# stack: QA's ring 15-40 px from the eroded alpha, only pixels that no product covers and that are light (L > 80: plaster, not glass)
allprod = np.zeros(cm.shape, bool)
for l_ in m5["layers"]:
    if "product" in l_:
        allprod |= np.asarray(Image.open(os.path.join(P2, "layers", l_["file"])))[..., 3] > 0
d = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
ring = (d >= 15) & (d <= 40)
ring_any = SCENE["r5"][ring]
ring_clean = ring & ~allprod
Lr = lab_f(SCENE["r5"][ring_clean].astype(np.float64) / 255)[:, 0]
res["curtains"]["ring_15_40_as_measured_by_targets"] = abs_lab(ring_any)
res["curtains"]["ring_15_40_without_any_product_px"] = abs_lab(SCENE["r5"][ring_clean][Lr > 80]) if (Lr > 80).any() else None
res["curtains"]["ring_px_under_the_curtain_alpha_share"] = round(float((ring & allprod).sum() / max(1, ring.sum())), 3)
vm = mask_of(vf["curtains-v2"], rows=(100, 1400))
V2 = rgb(os.path.join(P2, "graded/variant-r5-curtains-v2-set-B-graded-v3c.png"))
res["curtains-v2"] = dict(abs=abs_lab(V2[vm]), rel=rel_lab(V2[vm], W_ROOM),
                          photo=photo(os.path.join(SC, "r5/refs-dl/curtains2/img4.jpg"), (170, 40, 790, 520), keep=(40, 96)))
print("curtains", json.dumps(res["curtains"]))
print("curtains-v2", json.dumps(res["curtains-v2"]))

# ---------------------------------------------------------------- vases (lit half = the left half of the body, rows of the body)
for name, f, scene, ph, phbox, keep in (
        ("vase r5", b5["vase"]["file"], SCENE["r5"], "ph2/refs-dl/vase/sku.jpeg", (300, 250, 480, 600), None),
        ("vase r4", b4["vase"]["file"], SCENE["r4"], None, None, None),
        ("vase-v2", vf["vase-v2"], rgb(os.path.join(P2, "graded/variant-r5-vase-v2-set-B-graded-v3c.png")), "r5/refs-dl/vase2/sku.jpeg", (380, 380, 650, 820), (3, 60))):
    a = np.asarray(Image.open(os.path.join(P2, "layers", f)))[..., 3]
    full = cv2.erode((a == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    ys, xs = np.nonzero(full)
    body = full.copy()
    body[: ys.max() - 120] = False                 # the body below the neck (the branches are above)
    body[ys.max() - 6:] = False
    xs_b = np.nonzero(body.any(0))[0]
    mid = (xs_b.min() + xs_b.max()) / 2
    lit = body.copy()
    lit[:, int(mid):] = False
    rec = dict(lit_half_abs=abs_lab(scene[lit]), lit_half_rel=rel_lab(scene[lit], W_ROOM), whole_abs=abs_lab(scene[body]))
    if ph:
        rec["photo"] = photo(os.path.join(SC, ph), phbox, keep=keep)
    res[name] = rec
    print(name, json.dumps(rec))

# ---------------------------------------------------------------- planter (the visible pot left of the basket, below the rim)
for t, man, scene in (("r5", b5, SCENE["r5"]), ("r4", b4, SCENE["r4"])):
    a = np.asarray(Image.open(os.path.join(P2, "layers", man["planter"]["file"])))[..., 3]
    bk = np.asarray(Image.open(os.path.join(P2, "layers", man["basket"]["file"])))[..., 3] > 0
    pot = cv2.erode((a == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    pot[:1060] = False
    pot &= ~cv2.dilate(bk.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    upper = pot.copy()
    upper[1120:] = False
    lower = pot.copy()
    lower[:1135] = False
    # the shaded plaster beside it: left of the pot, rows 1060-1150 (above the floor line), 12-45 px out, no product
    dd = cv2.distanceTransform((~(a > 0)).astype(np.uint8), cv2.DIST_L2, 5)
    side = (dd >= 12) & (dd <= 45) & ~allprod
    side[:1000] = False
    side[1150:] = False
    side[:, 960:] = False
    w_loc = np.median(lin(scene[side]), 0) if side.any() else W_ROOM
    rec = dict(pot_abs=abs_lab(scene[pot]), pot_rel_room=rel_lab(scene[pot], W_ROOM), pot_rel_local=rel_lab(scene[pot], w_loc),
               ribbed_upper_abs=abs_lab(scene[upper]) if upper.any() else None, smooth_lower_abs=abs_lab(scene[lower]) if lower.any() else None,
               plaster_beside_abs=abs_lab(scene[side]) if side.any() else None, plaster_beside_rel_room=rel_lab(scene[side], W_ROOM) if side.any() else None,
               pot_minus_plaster_L=round(abs_lab(scene[pot])["L"] - abs_lab(scene[side])["L"], 2) if side.any() else None)
    res["planter " + t] = rec
    print("planter", t, json.dumps(rec))
res["planter photo"] = photo(os.path.join(SC, "ph2/refs-dl/planter/sku.jpg"), (120, 130, 640, 640), keep=(35, 93))
res["planter card hex"] = abs_lab(np.array([[0xBD, 0xB6, 0xA8]], np.uint8))
print("planter photo", res["planter photo"], res["planter card hex"])

# ---------------------------------------------------------------- the rods (fix-r5.json's bands)
fx = json.load(open(os.path.join(P2, "work-r5/fix-r5.json")))["magazine-holder"]["rods"]
H, W = SCENE["r5"].shape[:2]
yy, xx = np.mgrid[0:H, 0:W]
mh = np.asarray(Image.open(os.path.join(P2, "layers", b5["magazine-holder"]["file"])))[..., 3] == 255
rods = {}
for nm, r in fx.items():
    k, b = r["line_y_eq_ax_plus_b"]
    band = (np.abs(yy - (k * xx + b)) <= r["half_width_px"] - 1.5) & (xx >= r["x_span"][0]) & (xx <= r["x_span"][1]) & mh
    rods[nm] = dict(px=int(band.sum()), r5=abs_lab(SCENE["r5"][band]), r4=abs_lab(SCENE["r4"][band]))
res["magazine-holder rods"] = rods
print("rods", json.dumps(rods))

# ---------------------------------------------------------------- the floor lamp's wisp (QA R4 measure) on r5, and what is left
L5 = np.asarray(Image.open(os.path.join(P2, "layers", b5["floor-lamp"]["file"])))
a = L5[..., 3]
S5lab = lab_f(SCENE["r5"].astype(np.float64) / 255).reshape(H, W, 3)
Blab = lab_f(BASE.astype(np.float64) / 255).reshape(H, W, 3)
dL = S5lab[..., 0] - Blab[..., 0]
box = np.zeros(a.shape, bool)
box[700:800, 2380:2470] = True
w5 = box & (a > 0) & (dL > 2)
brass = w5 & ((S5lab[..., 2] > 20) | (S5lab[..., 0] < 60))
# connected to the stem / collar / chain: the alpha-255 core dilated by 2 px
core = cv2.dilate(((a == 255) & box).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
ys, xs = np.nonzero(w5)
res["floor-lamp wisp r5"] = dict(px=int(w5.sum()), brass_or_dark_px=int(brass.sum()), not_brass_px=int((w5 & ~brass).sum()),
                                 not_brass_and_detached_px=int((w5 & ~brass & ~core).sum()),
                                 dL_p50_p95_max=[round(float(np.percentile(dL[w5], q)), 2) for q in (50, 95, 100)] if w5.any() else None,
                                 b_star_p50=round(float(np.median(S5lab[..., 2][w5])), 2) if w5.any() else None,
                                 alpha_p50=int(np.median(a[w5])) if w5.any() else None,
                                 box_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if w5.any() else None)
print("wisp", res["floor-lamp wisp r5"])
json.dump(res, open(os.path.join(OUT, "data/colour.json"), "w"), indent=1)
