#!/usr/bin/env python3
"""split.py: the M0-N layers, split from ONE photograph as in M0-W (render-agent, 2026-11-27). 0 tokens.
  python3 split.py <hero_final.png> <plate.png> <masks.npz> <outdir>
The base is the plate P (registered to the hero H on the room outside the products, ECC affine). Every product is cut from H with its
mask (segment masks, cleaned; masks.npz: name -> bool HxW). What the products and the lamps do to the room is H over P:
  r = low-pass(H) / low-pass(P) outside every product (per channel; 3 px beside a product, 14 px elsewhere: the model re-drew the
      room's fine texture, so only the light is compared)
  d = min(r, 1) -> each product's MULTIPLY layer, shared between the products by distance (zone radius RADIUS)
  g = H over P where brighter, as SCREEN: s = (H - P) / (1 - P) -> each lamp's SCREEN layer, shared by the clay's lamp maps
Composition (the manifest's formula): P; per layer in z order: shadow multiply, then the layer (straight alpha); lights screen x
(1 - every alpha). Outside every zone nothing is taken and nothing is given: the plate, pixel for pixel."""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

CLAY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clay")
ORDER = [("curtains", 10), ("framed-art", 12), ("wall-decor", 12), ("accent-sconces", 12), ("vase", 16), ("rug", 20), ("floor-lamp", 30),
         ("planter", 32), ("sofa-cover", 50), ("cushions", 55), ("coffee-table", 57), ("basket", 60), ("magazine-holder", 60),
         ("table-runner", 62), ("tray", 64), ("bowl", 65), ("candle-holders", 65), ("pouf", 70), ("pendant", 80)]
RADIUS = {"curtains": 30, "framed-art": 30, "wall-decor": 26, "accent-sconces": 26, "vase": 50, "rug": 40, "floor-lamp": 70, "planter": 90,
          "sofa-cover": 70, "cushions": 70, "coffee-table": 120, "basket": 70, "magazine-holder": 80, "table-runner": 40, "tray": 30, "bowl": 40,
          "candle-holders": 40, "pouf": 80, "pendant": 24}
LAMP_REACH = {"accent-sconces": 160, "floor-lamp": 220, "pendant": 200}
LAMPS = {"accent-sconces": "light-accent-sconces.png", "floor-lamp": "light-floor-lamp.png", "pendant": "light-pendant.png"}
dil = lambda m, r: cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)


def nblur(img, w, sigma):
    f = 4 if sigma >= 10 else 1
    hs, ws = img.shape[0] // f, img.shape[1] // f
    im = img * (w[..., None] if img.ndim == 3 else w)
    if f > 1:
        im, wi = cv2.resize(im, (ws, hs), interpolation=cv2.INTER_AREA), cv2.resize(w, (ws, hs), interpolation=cv2.INTER_AREA)
    else:
        wi = w
    num, den = cv2.GaussianBlur(im, (0, 0), sigma / f), cv2.GaussianBlur(wi, (0, 0), sigma / f)
    if f > 1:
        num = cv2.resize(num, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
        den = cv2.resize(den, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
    return num / np.maximum(den[..., None] if img.ndim == 3 else den, 1e-4)


def register(P, H, valid):
    s = 0.25
    g = lambda a: cv2.resize(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), None, fx=s, fy=s, interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    a, b = g(P), g(H)
    msk = cv2.resize(valid.astype(np.uint8), (a.shape[1], a.shape[0]), interpolation=cv2.INTER_NEAREST)
    warp = np.eye(2, 3, dtype=np.float32)
    cc, warp = cv2.findTransformECC(b, a, warp, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), msk, 5)
    warp[:, 2] /= s
    Pw = cv2.warpAffine(P, warp, (P.shape[1], P.shape[0]), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    return Pw, warp, cc


def main(hero_p, plate_p, masks_p, out):
    H8 = np.asarray(Image.open(hero_p).convert("RGB"))
    P8 = np.asarray(Image.open(plate_p).convert("RGB"))
    h, w = H8.shape[:2]
    M = dict(np.load(masks_p))
    anyp = np.zeros((h, w), bool)
    for k, _ in ORDER:
        anyp |= M[k]
    P8w, A, cc = register(P8, H8, ~dil(anyp, 60))
    H, P = H8.astype(np.float32) / 255, P8w.astype(np.float32) / 255
    room = ~dil(anyp, 2)
    # 1. the plate in the hero's light at a large scale (40 px, every room pixel): the zones' edges meet the base without a step.
    #    The lamps' broad wash is part of this relit base; their light layers keep the local pools and cones (below)
    wbig = room.astype(np.float32)
    Rbig = np.clip(nblur(H, wbig, 40.0) / np.maximum(nblur(P, wbig, 40.0), 1e-3), 0.70, 1.40)
    P = P * Rbig
    P8w = np.clip(np.rint(P * 255), 0, 255).astype(np.uint8)
    # 2. what the products take (multiply) and the lamps give (screen), on the room's pixels only (a product's own pixels come from H
    #    with whatever falls on them baked in)
    wroom = room.astype(np.float32)
    near = dil(anyp, 40)
    den_s = cv2.GaussianBlur(wroom, (0, 0), 3.0)
    lpH_s, lpP_s = nblur(H, wroom, 3.0), nblur(P, wroom, 3.0)
    lpH_l, lpP_l = nblur(H, wroom, 14.0), nblur(P, wroom, 14.0)
    r = np.where(near[..., None], lpH_s / np.maximum(lpP_s, 1e-3), lpH_l / np.maximum(lpP_l, 1e-3))
    r = np.where((den_s < 0.05)[..., None], 1.0, np.clip(r, 0, 4))
    dmul = np.clip(r, 0.15, 1)
    Hl = np.where(near[..., None], lpH_s, lpH_l)
    scr = np.clip((Hl - P) / np.maximum(1 - P, 1e-3), 0, 1) * room[..., None]
    # zones: distance to each product
    dist = {k: cv2.distanceTransform((~M[k]).astype(np.uint8), cv2.DIST_L2, 5) for k, _ in ORDER}
    zone = {}
    for k, _ in ORDER:
        z = (dist[k] <= RADIUS[k]) & ~M[k]
        zone[k] = z
    # the nearest product (in units of its radius) owns each shadow pixel
    stack = np.stack([np.where(zone[k], dist[k] / RADIUS[k], 9.0) for k, _ in ORDER])
    owner = np.argmin(stack, 0)
    owned = stack.min(0) < 9.0
    fade = lambda k: np.clip(1.0 - (dist[k] / RADIUS[k] - 0.75) / 0.25, 0, 1)        # the last quarter of a zone fades to neutral
    os.makedirs(out, exist_ok=True)
    rec = dict(registration=dict(ecc=round(float(cc), 4), matrix=[[round(float(x), 5) for x in rr] for rr in A]), layers={}, lights={})
    alpha_all = np.zeros((h, w), np.float32)
    for i, (k, z) in enumerate(ORDER):
        # the product + a 3 px fringe of the hero's own room around it (its contact and its edge come with it), feathered
        a = cv2.GaussianBlur(dil(M[k], 3).astype(np.float32), (0, 0), 1.2)
        a = np.where(dil(M[k], 1), 1.0, a)
        rgba = np.dstack([H8, np.rint(np.clip(a, 0, 1) * 255).astype(np.uint8)])
        rgba[a <= 0.002] = 0
        os.makedirs(os.path.join(out, "layers", k), exist_ok=True)
        Image.fromarray(rgba).save(os.path.join(out, "layers", k, "layer.png"), optimize=True)
        sh = np.ones((h, w, 3), np.float32)
        own = owned & (owner == i) & room
        f = fade(k)[..., None]
        sh[own] = (1 - f[own]) + f[own] * dmul[own]
        sh = np.where(scr.sum(-1, keepdims=True) > 0, np.maximum(sh, 1.0), sh)     # a lit pixel is the lamps', not a shadow
        os.makedirs(os.path.join(out, "shadows", k), exist_ok=True)
        Image.fromarray(np.rint(np.clip(sh, 0, 1) * 255).astype(np.uint8)).save(os.path.join(out, "shadows", k, "shadow.png"), optimize=True)
        rec["layers"][k] = dict(z=z, alpha_px=int((a > 0.5).sum()), shadow_px=int((sh < 0.995).any(-1).sum()))
        alpha_all = 1 - (1 - alpha_all) * (1 - a)
    fks = {}
    for k in LAMPS:                                    # each lamp: its local light within LAMP_REACH px of its shade, faded
        fk = np.clip(1.0 - dist[k] / LAMP_REACH[k], 0, 1)
        fks[k] = fk * fk * (3 - 2 * fk)
    fsum = np.maximum(sum(fks.values()), 1.0)          # where two reaches overlap, the light is shared, not doubled
    for k in LAMPS:
        L = np.clip(scr * (fks[k] / fsum)[..., None], 0, 1)
        os.makedirs(os.path.join(out, "light"), exist_ok=True)
        Image.fromarray(np.rint(L * 255).astype(np.uint8)).save(os.path.join(out, "light", f"{k}.png"), optimize=True)
        rec["lights"][k] = dict(px=int((L > 1 / 255).any(-1).sum()), reach_px=LAMP_REACH[k])
    Image.fromarray(P8w).save(os.path.join(out, "plate-registered.png"))
    json.dump(rec, open(os.path.join(out, "split.json"), "w"), indent=1)
    print(json.dumps(rec["registration"]), flush=True)


def compose(out, base_p, order=ORDER, swap=None):
    """the manifest's formula, from the files (swap: {slot: (layer_png, shadow_png)})"""
    B = np.asarray(Image.open(base_p).convert("RGB")).astype(np.float32) / 255
    h, w = B.shape[:2]
    acc = B.copy()
    alpha_all = np.zeros((h, w), np.float32)
    for k, _ in order:
        lp, sp = (swap or {}).get(k, (os.path.join(out, "layers", k, "layer.png"), os.path.join(out, "shadows", k, "shadow.png")))
        if lp is None:
            continue
        S = np.asarray(Image.open(sp).convert("RGB")).astype(np.float32) / 255
        Lr = np.asarray(Image.open(lp).convert("RGBA")).astype(np.float32) / 255
        acc = acc * S
        a = Lr[..., 3:4]
        acc = acc * (1 - a) + Lr[..., :3] * a
        alpha_all = 1 - (1 - alpha_all) * (1 - a[..., 0])
    for k in LAMPS:
        Lg = np.asarray(Image.open(os.path.join(out, "light", f"{k}.png")).convert("RGB")).astype(np.float32) / 255 * (1 - alpha_all)[..., None]
        acc = 1 - (1 - acc) * (1 - Lg)
    return acc


if __name__ == "__main__":
    main(*sys.argv[1:5])
