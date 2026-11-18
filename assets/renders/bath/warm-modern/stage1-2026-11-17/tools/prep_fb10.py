#!/usr/bin/env python3
"""
prep_fb10.py: the model inputs of the FB10 passes on B2 (proposal 12.6, HOUSE2B), render-agent 2026-11-18. 0 tokens.
  the base: the QA-passed defaults recomposed from the layer files, then the WM-G1 curve inverted (the model works in the plate's
            own exposure; the curve is applied once, on the cut layers): pass A on the defaults, pass T3 on the defaults without
            the hand towel and its shadow (the ring only)
  pass A:   placeholders at the 12.6 positions (the camera's analytic projection, CB, as QA's b2_ring.py): the waffle stack and
            the rope basket on the vanity's open shelf, the travertine tray under the soap dispenser and the cup (not over them)
  pass T3:  a placeholder of the khaki waffle tea towel (45 x 65): the caramel's silhouette, its hanging part 10 cm longer (hem Z 0.21, in the frame and clear of the skirting)
Writes inputs/fb10-a-input.png, inputs/fb10-t3-input.png and the placeholder masks inputs/fb10-*-mask.png.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import compose_defaults as C  # noqa: E402
import grade_plate as G  # noqa: E402

FX0, FY0, FW, FH = 77.4882, 43.4301, 2565.0236, 1443.1398
YAW = math.radians(-57)
FWD = np.array([-math.sin(YAW), -math.cos(YAW)])
RIGHT = np.array([-FWD[1], FWD[0]])
BOXES = dict(towels=(5.84, 6.07, 11.86, 12.21, 0.15, 0.23), basket=(5.86, 6.11, 12.37, 12.75, 0.15, 0.38),
             tray=(5.98, 6.15, 12.50, 12.74, 0.88, 0.90))


def px(x, y, z):
    r = np.array([x - 3.80, y - 13.20])
    d, s = r @ FWD, r @ RIGHT
    return FX0 + (0.52 + s / d * (24 / 36)) * FW, FY0 + (0.46 - (z - 1.15) / d * (24 / 20.25)) * FH


def inv_curve(rgb, c):
    lab = G.to_lab(rgb)
    Lp = lab[..., 0]
    m = Lp < c["knee"]
    k, A = c["knee"], c["A"]
    disc = np.clip(k * k - 4 * A * (k - Lp[m]), 0, None)
    t = (k - np.sqrt(disc)) / (2 * A)
    L = k * (1 - t)
    lift = Lp[m] - L
    new = lab[m].copy()
    new[:, 0] = L
    new[:, 1] -= lift * c["chroma_per_lift"][0]
    new[:, 2] -= lift * c["chroma_per_lift"][1]
    out = rgb.copy()
    out[m] = G.from_lab(new)
    return out


def faces(b):
    """the three faces the camera sees: top (z1), front (x0, toward the camera) and the +Y side; shading 1.0 / 0.8 / 0.62"""
    x0, x1, y0, y1, z0, z1 = b
    return [([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], 1.0),
            ([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], 0.8),
            ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], 0.62)]


DEPTH = np.asarray(Image.open(C.CLAY + "B2-plate-depth.png")).astype(np.float64) / 5000     # planar metres (the clay README)


def pdepth(x, y):
    return float(np.array([x - 3.80, y - 13.20]) @ FWD)


def face_depth(kind, val, H, W):
    """planar depth (m) of the plane x = val, y = val or z = val along each pixel's ray (the analytic CB camera)"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    u, v = (xx - FX0) / FW, (yy - FY0) / FH
    k = (u - 0.52) * 36 / 24                              # s / d
    m = -(v - 0.46) * 20.25 / 24                          # (z - 1.15) / d
    with np.errstate(divide="ignore", invalid="ignore"):
        if kind == "x":
            d = (val - 3.80) / (FWD[0] + k * RIGHT[0])
        elif kind == "y":
            d = (val - 13.20) / (FWD[1] + k * RIGHT[1])
        else:
            d = (val - 1.15) / m
    return np.where(np.isfinite(d) & (d > 0), d, np.inf)


def paint(img, b, colour_fn, keep_off=None):
    """a box's three visible faces, each pixel only where the face is in front of the plate's own surface (the clay's planar
    depth): the drawer and the frame hide what is behind them"""
    H, W = img.shape[:2]
    mask = np.zeros((H, W), bool)
    x0, x1, y0, y1, z0, z1 = b
    for (quad, sh), (kind, val) in zip(faces(b), (("z", z1), ("x", x0), ("y", y1))):
        pts = [px(*p) for p in quad]
        im = Image.new("L", (W, H), 0)
        ImageDraw.Draw(im).polygon(pts, fill=255)
        f = np.asarray(im) > 0
        f &= face_depth(kind, val, H, W) < DEPTH - 0.005
        if keep_off is not None:
            f &= ~keep_off
        if not f.any():
            continue
        img[f] = np.clip(colour_fn(np.nonzero(f), b) * sh, 0, 1)
        mask |= f
    return mask


def main():
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    curve = json.load(open(os.path.join(ST, "plate-grade.json")))["curve"]
    plate = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    L8 = np.asarray(Image.open(os.path.join(ST, man["light"]["file"])).convert("RGB"))
    def stack(skip=()):
        out = plate.astype(np.float64) / 255
        for l in sorted(man["layers"], key=lambda l: l["z"]):
            if l["slot"] in skip:
                continue
            out = C.compose_one(out, np.asarray(Image.open(os.path.join(ST, l["layer"]))), np.asarray(Image.open(os.path.join(ST, l["shadow"]))))
        return C.light_one(out, L8)
    dflt = stack()
    assert np.array_equal(C.q(dflt), np.asarray(Image.open(os.path.join(ST, "b2-defaults.png")).convert("RGB")))
    base_a = inv_curve(dflt, curve)
    H, W = base_a.shape[:2]
    lay = {l["slot"]: l for l in man["layers"]}
    onvan = np.zeros((H, W), bool)
    for k in ("soap-dispenser", "toothbrush-cup", "vanity-vase"):
        onvan |= np.asarray(Image.open(os.path.join(ST, lay[k]["layer"])))[..., 3] > 0
    srgb_ = lambda c: np.array(c) / 255.0  # noqa: E731
    taupe = lambda idx, b: srgb_((128, 112, 102))  # noqa: E731
    def basket(idx, b):
        ys = idx[0]
        z_band = px(b[0], b[2], 0.29)[1]                 # the jute band: the top 40 % (Z 0.29-0.38)
        col = np.where((ys < z_band)[:, None], srgb_((150, 118, 84))[None], srgb_((196, 190, 178))[None])
        return col
    trav = lambda idx, b: srgb_((206, 192, 172))  # noqa: E731
    # the plate's drawer is drawn about 25 px lower than the clay's: its bottom edge, column by column (the strongest drop from
    # the lit walnut face to the dark shelf, within 45 px under the clay's edge), hides the top of what stands on the shelf
    ids = np.asarray(Image.open(C.CLAY + "B2-plate-id.png"))
    Y = C.blur(C.luma(base_a), 1.0)
    above = np.zeros((H, W), bool)
    xs_, edge = [], []
    for x in range(1340, 2180):
        c = np.nonzero(ids[1000:1450, x] == 21)[0]
        if not len(c):
            continue
        e0 = 1000 + c.max()
        prof = Y[e0 - 5:e0 + 60, x]
        cand = [i for i in range(len(prof) - 14) if prof[i] - prof[i + 4] > 0.06 and prof[i + 4:i + 14].mean() < 0.22]
        if not cand:
            continue
        xs_.append(x)
        edge.append(e0 - 5 + max(cand) + 2)               # the last drop into the dark shelf (under the rail), not the groove
    edge = np.array(edge, float)
    edge = np.array([np.median(edge[max(0, i - 15):i + 16]) for i in range(len(edge))])
    for x, e in zip(xs_, edge):
        above[:int(round(e)) + 2, x] = True
    a = base_a.copy()
    masks = {}
    masks["towels"] = paint(a, BOXES["towels"], taupe, keep_off=above)
    masks["basket"] = paint(a, BOXES["basket"], basket, keep_off=above)
    masks["tray"] = paint(a, BOXES["tray"], trav, keep_off=onvan)
    Image.fromarray(C.q(a)).save(os.path.join(ST, "inputs", "fb10-a-input.png"))
    Image.fromarray((masks["towels"] | masks["basket"] | masks["tray"]).astype(np.uint8) * 255).save(os.path.join(ST, "inputs", "fb10-a-mask.png"))
    # T3: the defaults without the hand towel, and the khaki placeholder
    t = inv_curve(stack(skip=("hand-towel",)), curve)
    al = np.asarray(Image.open(os.path.join(ST, lay["hand-towel"]["layer"])))[..., 3] > 0
    ys, xs = np.nonzero(al)
    top, bot = ys.min(), ys.max()
    hang0 = top + 30                                     # below the fold over the bar the towel is stretched 10 cm longer
    extra = 63                                           # 10 cm longer: the caramel's hem Z 0.31 -> 0.21 (analytic, CB): 1408 -> 1471
    new = np.zeros_like(al)
    new[:hang0] = al[:hang0]
    rows = np.arange(hang0, min(H, bot + extra + 1))
    src_rows = hang0 + (rows - hang0) * (bot - hang0) / (bot + extra - hang0)
    new[rows] = al[np.clip(np.rint(src_rows).astype(int), 0, H - 1)]
    t[new] = srgb_((112, 96, 72)) * (0.85 + 0.15 * np.linspace(1, 0.6, H)[:, None])[np.nonzero(new)[0]]
    Image.fromarray(C.q(t)).save(os.path.join(ST, "inputs", "fb10-t3-input.png"))
    Image.fromarray(new.astype(np.uint8) * 255).save(os.path.join(ST, "inputs", "fb10-t3-mask.png"))
    print({k: [int(v) for v in (np.nonzero(m)[1].min(), np.nonzero(m)[0].min(), np.nonzero(m)[1].max(), np.nonzero(m)[0].max())] for k, m in masks.items()},
          "t3 rows", int(top), int(min(H - 1, bot + extra)))


if __name__ == "__main__":
    main()
