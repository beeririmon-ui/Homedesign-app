#!/usr/bin/env python3
"""
ledge_planter_b1.py: the ledge planter (card 228781, SKU ...577 'large brown round', 13.2 x 11.8 cm, matte taupe-sand stoneware) added
to B1 as one crop edit (render-agent, 2026-11-25; briefs/wm-bath-b1-ledge-planter-2026-11-25.md). 0 tokens beyond the one send.
The kitchen's / kids' method (dining kd_crop.py, kids_crop.py): a placeholder in the current canvas, a crop round it upscaled to 2048,
the edit locked back onto the crop and cut into a layer (straight alpha) and a contact shadow one z below; colour by R5 against the SKU
photo's reading, size against the clay's projection (b1proj), the WM-G1 black point; the composites restacked from the files (RND2).

  prep              : the analytic placeholder (a truncated ellipsoid of revolution, 13.2 wide, 11.8 high, foot and mouth 8 cm,
                      at (4.27, 10.06) on the ledge top Z 1.00) in b1-defaults.png; inputs/planter-crop.png (the upload) + prep json
  assemble <raw>    : the edit back to the crop's size, locked (ECC affine, masked away from the planter) -> scratchpad
  cut               : layer, shadow, refit, colour, black point -> layers/ledge-planter/, shadows/ledge-planter/
  compose           : b1-defaults(.png, -frame), b1-variant-mat-beige(.png, -frame) restacked; layers/manifest.json updated
  sheet             : qa-sheet-planter.jpg (x2 of the shelf region: before, after, the alpha, the measures)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
B2T = "/home/user/homedesign-app/assets/renders/bath/warm-modern/stage1-2026-11-17/tools"
sys.path.insert(0, B2T)
sys.path.insert(0, HERE)
import compose_defaults as C  # noqa: E402
import grade_plate as G  # noqa: E402
import b1proj as P  # noqa: E402

SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/planter/"
CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-bath-b1-2026-11-19/"
SLOT = "ledge-planter"
PID = "ledge-planter-aliexpress-retro-ceramic-flower-vase-228781-large-brown-round"
CARD = "data/products/bath/ledge-planter/ledge-planter-aliexpress-retro-ceramic-flower-vase-228781.json"
SKU = "12000061187780577"
Z = 46                                   # the slot's z (data/slots/bath.json), as the candle, the diffuser and the jar
CENTRE = (4.27, 10.06)
LEDGE_Z = 1.00                           # the ledge top in the clay (ids 29 from row 789 at the slot's column; the candle and diffuser stand there)
POT_W, POT_H, MOUTH = 13.2, 11.8, 8.0    # cm, the SKU (...577); the mouth from the SKU photo ('Diameter: 8 cm')
SKU_LAB = (59.0, 4.4, 12.7)              # ae-round-photo-check.json item 24, '...577 large-brown-round' (L* 59, C* 13.5, h 71)
BOX = (780, 590, 1180, 890)              # the crop (x0, y0, x1, y1): 400 x 300, 4:3, the candle and diffuser in it for context
UP = 2048 / 400.0
REF_BOX = (690, 820, 1040, 1180)         # rows, cols: the plaster right of the window reveal, behind and right of the pot
PREP = os.path.join(ST, "inputs", "planter-prep.json")


def ellipsoid():
    """the SKU's ball pot as a truncated ellipsoid of revolution: r(z) = a sqrt(1 - ((z - h/2) / b)^2), a = W/2, cut at the foot and
    the mouth where r = MOUTH/2"""
    a = POT_W / 2
    k = np.sqrt(1 - (MOUTH / 2 / a) ** 2)
    b = POT_H / 2 / k
    return a, b


def radius(zc):
    a, b = ellipsoid()
    return a * np.sqrt(np.clip(1 - ((zc - POT_H / 2) / b) ** 2, 0, 1))


def surface_points(nz=120, nt=360):
    zs = np.linspace(0, POT_H, nz)
    th = np.linspace(0, 2 * np.pi, nt, endpoint=False)
    Z_, T_ = np.meshgrid(zs, th, indexing="ij")
    R = radius(Z_)
    X = CENTRE[0] + R * np.cos(T_) / 100
    Y = CENTRE[1] + R * np.sin(T_) / 100
    ZZ = LEDGE_Z + Z_ / 100
    return X.ravel(), Y.ravel(), ZZ.ravel()


def project(X, Y, ZZ):
    out = [P.px(x, y, z) for x, y, z in zip(X, Y, ZZ)]
    return np.array(out, float)


def silhouette(H, W, ss=4):
    """the clay-scale silhouette (anti-aliased, 0-1) and its measures (px): width at the belly, height foot-to-mouth"""
    pts = project(*surface_points())
    hull = cv2.convexHull((pts * ss).astype(np.float32)).reshape(-1, 2)
    x0, y0 = int(np.floor(pts[:, 0].min())) - 4, int(np.floor(pts[:, 1].min())) - 4
    x1, y1 = int(np.ceil(pts[:, 0].max())) + 4, int(np.ceil(pts[:, 1].max())) + 4
    big = np.zeros(((y1 - y0) * ss, (x1 - x0) * ss), np.uint8)
    cv2.fillPoly(big, [np.round(hull - [x0 * ss, y0 * ss]).astype(np.int32)], 255)
    small = cv2.resize(big.astype(np.float32) / 255, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    a = np.zeros((H, W))
    a[y0:y1, x0:x1] = small
    meas = dict(width_px=round(float(pts[:, 0].max() - pts[:, 0].min()), 2), height_px=round(float(pts[:, 1].max() - pts[:, 1].min()), 2),
                x=[round(float(pts[:, 0].min()), 1), round(float(pts[:, 0].max()), 1)],
                y=[round(float(pts[:, 1].min()), 1), round(float(pts[:, 1].max()), 1)],
                foot_centre=[round(float(v), 2) for v in P.px(CENTRE[0], CENTRE[1], LEDGE_Z)],
                px_per_cm_w=round(float((pts[:, 0].max() - pts[:, 0].min()) / POT_W), 4),
                px_per_cm_h=round(float((pts[:, 1].max() - pts[:, 1].min()) / POT_H), 4))
    return a, meas


def plaster_ref(img, ids, allfg):
    """the light on the plaster behind and right of the pot: mid-tone median (linear) of ids 1-4 in REF_BOX, off every product"""
    y0, y1, x0, x1 = REF_BOX
    box = np.zeros(ids.shape, bool)
    box[y0:y1, x0:x1] = True
    lab = G.to_lab(img)
    sel = box & np.isin(ids, (1, 2, 3, 4)) & ~C.dil(allfg, 8) & (np.hypot(lab[..., 1], lab[..., 2]) < 9)
    L = lab[..., 0][sel]
    lo, hi = np.percentile(L, [20, 80])
    return np.median(C.lin(img[sel][(L >= lo) & (L <= hi)]), 0), int(sel.sum())


def all_fg(man, H, W):
    m = np.zeros((H, W), bool)
    for l in man["layers"]:
        if l["slot"] == SLOT:
            continue
        m |= np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3] > 0
    return m


def prep():
    base8 = np.asarray(Image.open(os.path.join(ST, "b1-defaults.png")).convert("RGB"))
    base = base8.astype(np.float64) / 255
    H, W = base.shape[:2]
    ids = np.asarray(Image.open(CLAY + "B1-id.png"))
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    a, meas = silhouette(H, W)
    # the placeholder's colour: the SKU's reading in the light of the plaster beside it (R5 inverted), shaded as a matte ball lit from
    # above-front (the scene's soft light: the sconce above right, the window behind); no texture, the model draws the mottle
    ref, nref = plaster_ref(base, ids, all_fg(man, H, W))
    sku_lin = C.lin(G.from_lab(np.array([SKU_LAB]))[0])
    mid = sku_lin / C.hex_lin(C.WHITE["plaster"]) * ref
    ys, xs = np.nonzero(a > 0)
    fx, fy = meas["foot_centre"]
    s = meas["px_per_cm_w"]
    u = (xs - fx) / s
    zc = (fy - ys) / meas["px_per_cm_h"]
    aa, bb = ellipsoid()
    r = radius(np.clip(zc, 0, POT_H))
    d = np.sqrt(np.clip(r ** 2 - u ** 2, 0, None))
    n = np.stack([u / aa ** 2, d / aa ** 2, (zc - POT_H / 2) / bb ** 2], -1)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    lv = np.array([0.35, 0.65, 0.68])
    lv /= np.linalg.norm(lv)
    sh = 0.62 + 0.55 * np.clip(n @ lv, 0, 1)
    sh = sh / np.median(sh)
    col = C.srgb(np.clip(sh[:, None] * mid[None, :], 0, 1))
    ph = base.copy()
    ph[ys, xs] = col
    av = a[..., None]
    inp = ph * av + base * (1 - av)
    x0, y0, x1, y1 = BOX
    crop = Image.fromarray(C.q(inp)).crop((x0, y0, x1, y1)).resize((2048, int(round((y1 - y0) * UP))), Image.LANCZOS)
    os.makedirs(os.path.join(ST, "inputs"), exist_ok=True)
    cp = os.path.join(ST, "inputs", "planter-crop.png")
    crop.save(cp)
    import hashlib
    rec = dict(pass_="ledge-planter-r1", base="b1-defaults.png as of 2026-11-19 (QA round 1), graded",
               placeholder=dict(shape="truncated ellipsoid of revolution (the SKU's ball pot): W 13.2, H 11.8, foot and mouth 8 cm",
                                at=dict(plan=list(CENTRE), ledge_z=LEDGE_Z), clay_scale=meas, px=int((a > 0).sum()),
                                colour="the SKU reading (L* 59, a* 4.4, b* 12.7) in the light of the plaster beside it, matte ball shading, no texture",
                                plaster_ref_lin=[round(float(v), 4) for v in ref], plaster_ref_px=nref),
               crop_box=list(BOX), upscale=UP, aspect="4:3", crop="inputs/planter-crop.png",
               crop_sha256=hashlib.sha256(open(cp, "rb").read()).hexdigest())
    json.dump(rec, open(PREP, "w"), indent=1, ensure_ascii=False)
    np.save(SCR + "placeholder_alpha.npy", a.astype(np.float32))
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prep":
        prep()
    else:
        globals()[cmd](*sys.argv[2:])
