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
os.makedirs(SCR, exist_ok=True)


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
    base = defaults_without_planter().astype(np.float64) / 255
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


def defaults_without_planter():
    """B1's defaults as of 2026-11-19 (QA round 1): the files restacked without the planter (byte for byte the old b1-defaults.png)"""
    import copy
    cache = SCR + "defaults-without-planter.png"
    if os.path.exists(cache):
        return np.asarray(Image.open(cache).convert("RGB"))
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    old = copy.deepcopy(man)
    old["layers"] = [l for l in old["layers"] if l["slot"] != SLOT]
    o8 = stack_files(old)[0]
    Image.fromarray(o8).save(cache)
    return o8


def base_crop_up():
    """the crop of b1-defaults.png WITHOUT the placeholder, upscaled as the upload was (the reference the edit is cut against)"""
    x0, y0, x1, y1 = BOX
    im = Image.fromarray(defaults_without_planter()).crop((x0, y0, x1, y1))
    w, h = 2048, int(round((y1 - y0) * UP))
    return np.asarray(im.resize((w, h), Image.LANCZOS)).astype(np.float64) / 255


def grad(img):
    g = cv2.cvtColor(C.q(img), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    g = cv2.GaussianBlur(g, (0, 0), 2.0)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    return np.hypot(gx, gy)


def assemble(rawp):
    """the edit back to the upload's size (2048 x 1536), locked onto the upload by one ECC affine on the gradient, masked away from
    the placeholder and the plant's room above it; written to the scratchpad (re-made from the raw at any time)"""
    inp = C.load(os.path.join(ST, "inputs", "planter-crop.png"))
    h, w = inp.shape[:2]
    raw = C.load(rawp, (h, w))
    a, _ = silhouette(1530, 2720)                        # the placeholder's alpha (prep's, re-made)
    x0, y0, x1, y1 = BOX
    ac = cv2.resize(a[y0:y1, x0:x1], (w, h), interpolation=cv2.INTER_LINEAR) > 0.02
    keep = ~C.dil(ac, int(14 * UP))
    ys, xs = np.nonzero(ac)
    keep[: ys.max(), max(0, xs.min() - int(20 * UP)): xs.max() + int(20 * UP)] = False     # the plant's room above the pot
    warp = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
    cc, warp = cv2.findTransformECC(grad(inp), grad(raw), warp, cv2.MOTION_AFFINE, crit, keep.astype(np.uint8), 5)
    al = cv2.warpAffine(raw.astype(np.float32), warp, (w, h), flags=cv2.INTER_LANCZOS4 + cv2.WARP_INVERSE_MAP,
                        borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
    al = np.clip(al, 0, 1)
    np.save(SCR + "aligned.npy", al.astype(np.float32))
    base = base_crop_up()
    d = np.abs(al - base).max(2)
    rec = dict(raw=os.path.relpath(rawp, ST), raw_size=list(Image.open(rawp).size), ecc=round(float(cc), 4),
               warp=[[round(float(v), 5) for v in r] for r in warp], stable_px=int(keep.sum()),
               outside_diff_p50_p99=[round(float(np.percentile(d[keep], q)) * 255, 2) for q in (50, 99)])
    pr = json.load(open(PREP))
    pr["assemble"] = rec
    json.dump(pr, open(PREP, "w"), indent=1, ensure_ascii=False)
    Image.fromarray(C.q(np.clip(d * 4, 0, 1))).save(SCR + "diff_x4.png")
    print(json.dumps(rec))


# ---- the cut (QA-able constants read off the aligned edit at 3x, up-res crop px; scratchpad fit_overlay.png) ----
MOUTH_D = (1131.0, 680.0, 132.0, 50.0)   # the drawn mouth ellipse: centre x, y, rx, ry (front rim at y 730 on the axis)
FOOT_D = 1034.0                          # the drawn foot's contact row
EDGE_ROWS = (730, 992)                   # rows where the drawn outline is clean (above: the rim seen from above; below: the shadow)


def drawn_outline(al, base):
    """the drawn pot's outline: per row, from the axis outwards to the last changed pixel (|edit - base| > 0.10, gaps <= 6 px), on
    the clean rows; an axis-aligned ellipse hw^2 = c0 + c1 y + c2 y^2 fitted to the half-widths"""
    d = np.abs(al - base).max(2) > 0.10
    rows, L, R = [], [], []
    for y in range(EDGE_ROWS[0], EDGE_ROWS[1] + 1, 2):
        out = []
        for dirn in (-1, 1):
            x, gap, last = 1129, 0, 1129
            while 850 < x < 1449 and gap <= 6:
                x += dirn
                if d[y, x]:
                    last, gap = x, 0
                else:
                    gap += 1
            out.append(last)
        rows.append(y)
        L.append(out[0])
        R.append(out[1])
    y = np.array(rows, float)
    hw = (np.array(R) - np.array(L)) / 2.0
    c2, c1, c0 = np.polyfit(y, hw ** 2, 2)
    yc = -c1 / (2 * c2)
    rx2 = c2 * yc ** 2 + c1 * yc + c0
    xc = float(np.median((np.array(L) + np.array(R)) / 2.0))
    res = float(np.abs(np.sqrt(np.clip(c2 * y ** 2 + c1 * y + c0, 0, None)) - hw).max())
    return dict(xc=xc, yc=float(yc), rx=float(np.sqrt(rx2)), ry=float(np.sqrt(-rx2 / c2)), resid_px=round(res, 2), rows=len(rows))


def clay_up(ss=4):
    """the clay-scale silhouette in the up-res crop: AA alpha, and per column its top and bottom (sub-pixel, from a 4x raster)"""
    x0, y0, _, _ = BOX
    h, w = int(round((BOX[3] - y0) * UP)), 2048
    pts = (project(*surface_points()) - [x0, y0]) * UP
    hull = cv2.convexHull(pts.astype(np.float32)).reshape(-1, 2)
    bx0, by0 = int(np.floor(hull[:, 0].min())) - 3, int(np.floor(hull[:, 1].min())) - 3
    bx1, by1 = int(np.ceil(hull[:, 0].max())) + 3, int(np.ceil(hull[:, 1].max())) + 3
    big = np.zeros(((by1 - by0) * ss, (bx1 - bx0) * ss), np.uint8)
    cv2.fillPoly(big, [np.round((hull - [bx0, by0]) * ss).astype(np.int32)], 1, lineType=cv2.LINE_8)
    a = np.zeros((h, w))
    a[by0:by1, bx0:bx1] = cv2.resize(big.astype(np.float32), (bx1 - bx0, by1 - by0), interpolation=cv2.INTER_AREA)
    cols = np.arange(big.shape[1])
    has = big.any(0)
    top = np.where(has, big.argmax(0), 0) / ss + by0
    bot = np.where(has, big.shape[0] - big[::-1].argmax(0), 0) / ss + by0
    xs = (cols + 0.5) / ss + bx0
    xc = float((hull[:, 0].min() + hull[:, 0].max()) / 2)
    rx = float((hull[:, 0].max() - hull[:, 0].min()) / 2)
    return a, dict(xs=xs[has], top=top[has], bot=bot[has], xc=xc, rx=rx, top_c=float(hull[:, 1].min()), foot=float(hull[:, 1].max()),
                   box=(bx0, by0, bx1, by1))


def plant_alpha(al):
    """the plant's matte by its colour (the GrabCut took the dark mouth and the pot behind the stem): the leaves and stems are the
    only green in the crop (a* < -6, C* > 8 is sure); alpha = (-a* - 1) / 5 clipped, within 4 px of the sure green and connected to
    it; edge colours taken from the leaf interior (no dark-mouth or wall fringe)"""
    lab = G.to_lab(al)
    A, B = lab[..., 1], lab[..., 2]
    core = (A < -6) & (np.hypot(A, B) > 8)
    win = np.zeros(A.shape, bool)
    win[440:960, 900:1480] = True
    core &= win
    n, lab_, st, _ = cv2.connectedComponentsWithStats(core.astype(np.uint8), connectivity=8)
    core = np.isin(lab_, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= 40])
    a = np.clip((-A - 1.0) / 5.0, 0, 1) * C.dil(core, 4)
    a = np.where(core, 1.0, a)
    inner = C.ero(core, 1)
    w_ = C.blur(inner.astype(np.float64), 2.5)
    spread = np.stack([C.blur(al[..., i] * inner, 2.5) for i in range(3)], -1) / np.maximum(w_, 1e-6)[..., None]
    edge = (a > 0) & ~inner
    col = al.copy()
    col[edge] = np.where((w_[edge] > 0.02)[:, None], spread[edge], al[edge])
    return a, col, dict(method="colour matte: a* < -6 and C* > 8 sure; (-a* - 1) / 5 within 4 px of it", plant_px_up=int((a > 0.5).sum()),
                        core_px_up=int(core.sum()))


def cut():
    al = np.load(SCR + "aligned.npy").astype(np.float64)
    base = base_crop_up()
    h, w = al.shape[:2]
    rec = {}
    # 1. tone: the edit came back a little lighter in R and B; one per-channel linear gain from a ring round the pot (wall, reveal,
    #    ledge) brings it to the frame (the layer then gets its colour by R5; this sets the plant's)
    chg = np.abs(al - base).max(2) > 0.08
    obj = np.zeros((h, w), bool)
    obj[450:1070, 880:1480] = chg[450:1070, 880:1480]
    ring = C.dil(obj, int(60 * UP)) & ~C.dil(obj, int(15 * UP))
    g = np.median(C.lin(base[ring]), 0) / np.median(C.lin(al[ring]), 0)
    al = C.srgb(np.clip(C.lin(al) * g, 0, 1))
    rec["tone_gain_linear"] = [round(float(v), 4) for v in g]
    # 2. geometry: the drawn outline and mouth, the clay's silhouette
    dr = drawn_outline(al, base)
    ca, cl = clay_up()
    s = cl["rx"] / dr["rx"]
    rec["drawn"] = dict(outline=dr, mouth=list(MOUTH_D), foot=FOOT_D,
                        width_cm_at_clay_scale=round(2 * dr["rx"] / UP / json.load(open(PREP))["placeholder"]["clay_scale"]["px_per_cm_w"], 2),
                        back_rim_to_foot_cm=round((FOOT_D - (MOUTH_D[1] - MOUTH_D[3]) + 0) / UP / json.load(open(PREP))["placeholder"]["clay_scale"]["px_per_cm_h"], 2))
    rec["clay"] = dict(xc=round(cl["xc"], 2), rx=round(cl["rx"], 2), top=round(cl["top_c"], 2), foot=round(cl["foot"], 2))
    rec["scale_w"] = round(float(s), 4)
    MX, MY, MRX, MRY = MOUTH_D

    def top_d(x):
        dx = x - MX
        inm = np.abs(dx) < MRX
        arc = MY + MRY * np.sqrt(np.clip(1 - (dx / MRX) ** 2, 0, 1))
        ell = dr["yc"] - dr["ry"] * np.sqrt(np.clip(1 - ((x - dr["xc"]) / dr["rx"]) ** 2, 0, 1))
        return np.where(inm, arc, ell)

    def bot_d(x):
        ell = dr["yc"] + dr["ry"] * np.sqrt(np.clip(1 - ((x - dr["xc"]) / dr["rx"]) ** 2, 0, 1))
        return np.minimum(FOOT_D, ell)

    # 3. the body: every clay pixel takes the drawn pot's pixel at the same relative column (u, of the max half-width) and the same
    #    relative height in that column (t, between the column's bottom and top; the drawn top is the FRONT rim arc in the mouth's
    #    columns, so the mouth seen from above is left out): the drawn view (about 20 deg above) becomes the clay's (0.6 deg),
    #    the width the card's; t clipped 0.012-0.985 and u to 0.99 so no outside pixel is sampled
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    tc = np.interp(xx[0], cl["xs"], cl["top"], left=np.nan, right=np.nan)
    bc = np.interp(xx[0], cl["xs"], cl["bot"], left=np.nan, right=np.nan)
    u = np.clip((xx - cl["xc"]) / cl["rx"], -0.99, 0.99)
    t = np.clip((bc[None, :] - yy) / np.maximum(bc - tc, 1e-3)[None, :], 0.012, 0.985)
    xd = dr["xc"] + u * dr["rx"]
    yd = bot_d(xd) - t * (bot_d(xd) - top_d(xd))
    xd, yd = np.nan_to_num(xd, nan=-10.0), np.nan_to_num(yd, nan=-10.0)
    body = cv2.remap(al.astype(np.float32), xd.astype(np.float32), yd.astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
    body = np.nan_to_num(body)
    ba = np.nan_to_num(ca) * np.isfinite(tc)[None, :]
    # 4. the plant: pinned to the rim: x by the same scale about the axis, y from the drawn front-rim arc (the mouth's mid height
    #    beyond its columns) to the clay's rim line, at the same scale; only what the edit drew ABOVE that line (what hangs over the
    #    front came with the body)
    pa, pcol, prec = plant_alpha(al)
    rec["plant"] = prec
    xs_ = dr["xc"] + (xx - cl["xc"]) / s                       # inverse: output -> drawn
    A_ = np.where(np.abs(xs_ - MX) < MRX, MY + MRY * np.sqrt(np.clip(1 - ((xs_ - MX) / MRX) ** 2, 0, 1)), MY)
    ys_ = A_ + (yy - cl["top_c"]) / s
    pr = cv2.remap(np.dstack([pcol * pa[..., None], pa]).astype(np.float32), xs_.astype(np.float32), ys_.astype(np.float32),
                   cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(np.float64)
    above = ys_ < A_ - 0.5
    pr *= above[..., None]
    pal = np.clip(pr[..., 3], 0, 1)
    # 5. compose at up-res (premultiplied): plant over body; then down to the canvas (area, x 1/5.12) and straight alpha
    prem = pr[..., :3] + body * ba[..., None] * (1 - pal[..., None])
    alpha = pal + ba * (1 - pal)
    x0, y0, x1, y1 = BOX
    cw, ch = x1 - x0, y1 - y0
    prem_c = cv2.resize(prem.astype(np.float32), (cw, ch), interpolation=cv2.INTER_AREA).astype(np.float64)
    a_c = cv2.resize(alpha.astype(np.float32), (cw, ch), interpolation=cv2.INTER_AREA).astype(np.float64)
    pal_c = cv2.resize(pal.astype(np.float32), (cw, ch), interpolation=cv2.INTER_AREA).astype(np.float64)
    ba_c = cv2.resize(ba.astype(np.float32), (cw, ch), interpolation=cv2.INTER_AREA).astype(np.float64)
    a_c[a_c < 1 / 255] = 0
    rgb_c = np.where((a_c > 0)[..., None], prem_c / np.maximum(a_c, 1e-6)[..., None], 0)
    # 6. the contact shadow: the edit's darkening of the ledge round the foot (luminance ratio to the frame), filled under the drawn
    #    pot (inpaint) and scaled about the axis with the pot; one z below
    Y = lambda im: C.lin(im) @ np.array([0.2126, 0.7152, 0.0722])  # noqa: E731
    rat = np.clip(Y(al) / np.maximum(Y(base), 1e-4), 0, 1)
    band = np.zeros((h, w), bool)
    band[960:1075, 880:1480] = True
    drawn_pot = (((xx - dr["xc"]) / dr["rx"]) ** 2 + ((yy - dr["yc"]) / dr["ry"]) ** 2 <= 1.0) & (yy <= FOOT_D + 1)
    drawn_pot = C.dil(drawn_pot | (pa > 0.05), 3)
    # the edit's tone residual (a few % over the whole band) is not shadow: a floor of 0.04 off the darkening, and the band's edges
    # feathered (sigma 12 up-px), so no box edge shows
    dk = np.clip((1 - rat - 0.04) / 0.96, 0, 1) * np.clip(C.blur(band.astype(np.float64), 12.0) * 2 - 1, 0, 1)
    rat = 1 - dk
    sm = np.where(band & ~drawn_pot, rat, 1.0)
    hole = (band & drawn_pot).astype(np.uint8)
    sm8 = cv2.inpaint(C.q(sm), hole, 6, cv2.INPAINT_TELEA).astype(np.float64) / 255
    sm8[~band] = 1.0
    sm8 = C.blur(sm8, 2.0)
    sm8[sm8 > 0.985] = 1.0
    M = np.float32([[s, 0, cl["xc"] - s * dr["xc"]], [0, 1, cl["foot"] - FOOT_D]])
    shw = cv2.warpAffine(sm8.astype(np.float32), M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=1.0)
    shw = np.clip(shw.astype(np.float64), 0, 1)
    sh_c = cv2.resize(shw.astype(np.float32), (cw, ch), interpolation=cv2.INTER_AREA).astype(np.float64)
    sh_c[sh_c > 0.99] = 1.0
    np.savez_compressed(SCR + "cut.npz", rgb=rgb_c, a=a_c, sh=sh_c, pal=pal_c, ba=ba_c)
    json.dump(rec, open(SCR + "cut-record.json", "w"), indent=1)
    print(json.dumps(rec, indent=1))


AXIS_X = None                                   # the pot's axis in the canvas: from the clay (b1proj), set in finish()
BLACK_L = 11.3                                  # WM-G1: black L* 11-14; no layer pixel darker than 11


def stack_files(man, extra=None, swap=None):
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    L8 = np.asarray(Image.open(os.path.join(ST, man["light"]["file"])).convert("RGB"))
    layers, order = {}, []
    for l in man["layers"]:
        layers[l["slot"]] = (np.asarray(Image.open(os.path.join(ST, l["layer"]))), np.asarray(Image.open(os.path.join(ST, l["shadow"]))))
        order.append(l["slot"])
    if swap:
        layers.update(swap)
    sys.path.insert(0, HERE)
    import compose_b1_defaults as D
    return C.q(D.stack(plate8, layers, order, L8)), plate8, L8, layers, order


def r5_half(img, body, side, ref):
    """R5 (QA's reading): the mid-tone (L* 20-80th pct) median, linear, of the pot's body on one half, over the plaster's light, times
    #ECE5DA"""
    m = body & side
    return C.r5_lab(img, m, ref, "plaster"), int(m.sum())


def finish():
    """the layer and shadow in the full canvas; R5 on the lit half to the SKU photo's reading (one per-channel linear gain on the pot,
    its mottle and shading kept; the plant untouched); the WM-G1 black point; written to layers/ and shadows/"""
    z = np.load(SCR + "cut.npz")
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    H, W = 1530, 2720
    x0, y0, x1, y1 = BOX
    rgb = np.zeros((H, W, 3))
    a = np.zeros((H, W))
    sh = np.ones((H, W))
    pal = np.zeros((H, W))
    rgb[y0:y1, x0:x1], a[y0:y1, x0:x1], sh[y0:y1, x0:x1], pal[y0:y1, x0:x1] = z["rgb"], z["a"], z["sh"], z["pal"]
    ba = np.zeros((H, W))
    ba[y0:y1, x0:x1] = z["ba"]
    rgb = np.clip(rgb, 0, 1)
    ids = np.asarray(Image.open(CLAY + "B1-id.png"))
    others = all_fg(man, H, W)
    dflt = defaults_without_planter().astype(np.float64) / 255
    ref, nref = plaster_ref(dflt, ids, others | (a > 0) | (sh < 1))
    ax = P.px(CENTRE[0], CENTRE[1], LEDGE_Z)[0]
    xx = np.arange(W)[None, :]
    body = C.ero((ba > 0.99) & (pal < 0.02) & (a > 0.99), 2)
    lit = np.broadcast_to(xx >= ax, (H, W))
    shade = ~lit
    before, nb = r5_half(rgb, body, lit, ref)
    before_shade, _ = r5_half(rgb, body, shade, ref)
    # which half is lit: the brighter (the sconce is above right; the edit lit the right half, L* 63 against 56 at up-res)
    Lr = G.to_lab(rgb[body & lit])[:, 0].mean()
    Ls = G.to_lab(rgb[body & shade])[:, 0].mean()
    if Ls > Lr:
        lit, shade = shade, lit
        before, nb = r5_half(rgb, body, lit, ref)
    tgt = C.lin(G.from_lab(np.array([SKU_LAB]))[0])
    k = np.ones(3)
    wpot = np.clip(1 - pal, 0, 1) * (a > 0)
    lin0 = C.lin(rgb)
    for _ in range(6):
        cur = C.srgb(np.clip(lin0 * (1 + (k - 1)[None, None, :] * wpot[..., None]), 0, 1))
        got, _ = r5_half(cur, body, lit, ref)
        k = k * tgt / C.lin(G.from_lab(np.array([got]))[0])
    new = C.srgb(np.clip(lin0 * (1 + (k - 1)[None, None, :] * wpot[..., None]), 0, 1))
    clipped = int(((lin0 * k).max(-1)[(a > 0) & (wpot > 0.5)] > 1).sum())
    after, _ = r5_half(new, body, lit, ref)
    after_shade, _ = r5_half(new, body, shade, ref)
    de = lambda x, y: round(float(G.de00(np.array([x]), np.array([y]))[0]), 2)  # noqa: E731
    # black point: no pixel of the layer under L* 11 (a*, b* kept)
    lab = G.to_lab(new)
    low = (a > 0) & (lab[..., 0] < BLACK_L)
    nlow = int(low.sum())
    if nlow:
        lab[low, 0] = BLACK_L
        new[low] = np.clip(G.from_lab(lab[low]), 0, 1)
    a8 = C.q(a)
    rgba = np.dstack([np.where((a8 > 0)[..., None], C.q(new), 0), a8])
    s8 = C.q(sh)
    lp = os.path.join("layers", SLOT, PID + ".png")
    sp = os.path.join("shadows", SLOT, PID + ".png")
    os.makedirs(os.path.join(ST, "layers", SLOT), exist_ok=True)
    os.makedirs(os.path.join(ST, "shadows", SLOT), exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(os.path.join(ST, lp))
    Image.fromarray(s8).save(os.path.join(ST, sp))
    rec = json.load(open(SCR + "cut-record.json"))
    rec["colour"] = dict(method="R5 (QA's reading) on the lit half of the pot's body (eroded 2, no plant): mid-tone median over the plaster's "
                                "light right of the reveal (REF_BOX, off every product) x #ECE5DA; one per-channel linear gain on the pot (its "
                                "mottle and shading kept), weighted off the plant",
                         lit_half="right (x >= %.1f; the sconce is above right)" % ax if not (Ls > Lr) else "left (x < %.1f)" % ax,
                         sku_photo_lab=list(SKU_LAB), plaster_ref_lin=[round(float(v), 4) for v in ref], plaster_ref_px=nref, body_px_lit=nb,
                         before=[round(float(v), 2) for v in before], de00_before=de(before, SKU_LAB),
                         gain_linear=[round(float(v), 4) for v in k], clipped_px=clipped,
                         after_lit=[round(float(v), 2) for v in after], de00_after_lit=de(after, SKU_LAB),
                         after_shaded_half=[round(float(v), 2) for v in after_shade], de00_shaded_half=de(after_shade, SKU_LAB))
    rec["black_point"] = dict(rule="WM-G1 L* 11-14: no layer pixel under 11", raised_px=nlow,
                              layer_min_L=round(float(G.to_lab(C.q(new)[(a8 > 0)].astype(np.float64) / 255)[:, 0].min()), 2))
    rec["files"] = dict(layer=lp, shadow=sp, alpha_px=int((a8 > 0).sum()), shadow_px=int((s8 < 255).sum()))
    json.dump(rec, open(SCR + "cut-record.json", "w"), indent=1)
    print(json.dumps(dict(colour=rec["colour"], black=rec["black_point"], files=rec["files"]), indent=1))


def compose():
    """the planter's layer and shadow into layers/manifest.json (z 46, shadow 45, after the jar), then b1-defaults and the Beige
    restacked from the files on plate.png, with their frames. Checks: RND2 against the plate, and against the composites without
    the planter (restacked in memory, which reproduce the 2026-11-19 files byte for byte): no pixel changes outside the planter's
    alpha and shadow"""
    import copy
    rec = json.load(open(SCR + "cut-record.json"))
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    old = copy.deepcopy(man)
    old["layers"] = [l for l in old["layers"] if l["slot"] != SLOT]
    ent = dict(slot=SLOT, product=PID, card=CARD, sku=SKU, z=Z, shadow_z=Z - 1, default=True, layer=rec["files"]["layer"],
               shadow=rec["files"]["shadow"], alpha_px=rec["files"]["alpha_px"], shadow_px=rec["files"]["shadow_px"],
               added="2026-11-25 (briefs/wm-bath-b1-ledge-planter-2026-11-25.md)", filler="a small succulent rosette and trailing stems "
               "(not sold, not counted)")
    lays = [l for l in man["layers"] if l["slot"] != SLOT]
    i = [l["slot"] for l in lays].index("window-sill-vase") + 1
    lays.insert(i, ent)
    man["layers"] = lays
    beige = [v for v in man["variants"] if v["slot"] == "bath-mat"][0]
    sw = {"bath-mat": (np.asarray(Image.open(os.path.join(ST, beige["layer"]))), np.asarray(Image.open(os.path.join(ST, beige["shadow"]))))}
    out = {}
    for name, swap, fn in (("defaults", None, "b1-defaults"), ("beige", sw, "b1-variant-mat-beige")):
        o8, plate8, L8, layers, order = stack_files(man, swap=swap)
        b8 = stack_files(old, swap=swap)[0]
        a = layers[SLOT][0][..., 3] > 0
        shm = layers[SLOT][1] < 255
        region = L8.max(2) > 0
        for k in order:
            region |= (layers[k][0][..., 3] > 0) | (layers[k][1] < 255)
        rnd2 = int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum())
        changed = np.abs(o8.astype(int) - b8.astype(int)).max(2) > 0
        out[name] = dict(rnd2_outside_differing_px=rnd2, region_px=int(region.sum()), changed_px=int(changed.sum()),
                         changed_outside_planter_alpha_and_shadow=int((changed & ~(a | shm)).sum()),
                         overlap_with_other_layers_px=int(sum(int(((layers[k][0][..., 3] > 0) & (a | shm)).sum()) for k in order if k != SLOT)))
        Image.fromarray(o8).save(os.path.join(ST, fn + ".png"))
        C.frame_png(o8, os.path.join(ST, fn + "-frame.png"))
        if name == "defaults":
            man["rnd2"] = dict(region_px=int(region.sum()), outside_differing_px=rnd2, rule=man["rnd2"]["rule"])
        else:
            beige["outside_differing_px_vs_plate"] = rnd2
            beige["differing_px_vs_defaults_outside_alpha"] = int(((np.abs(o8.astype(int) - np.asarray(Image.open(os.path.join(ST, "b1-defaults.png")).convert("RGB")).astype(int)).max(2) > 0)
                                                                   & ~(layers["bath-mat"][0][..., 3] > 0)).sum())
    man["compose"]["order"] = ["base"] + [f"{l['slot']}-shadow, {l['slot']}" for l in man["layers"]] + ["light (screen)"]
    man["gaps_left_empty"] = [g for g in man["gaps_left_empty"] if g != SLOT]
    man["record"]["ledge_planter"] = dict(rec, compose=out, tool="tools/ledge_planter_b1.py (prep, assemble, cut, finish, compose, sheet)",
                                          job="jobs.json sent[ledge-planter-r1]", prompt="assets/prompts/warm-modern-bath-b1-2026-11-19/ledge-planter.json")
    man["updated"] = "2026-11-25: the ledge planter added (render-agent)"
    json.dump(man, open(os.path.join(ST, "layers", "manifest.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1))


SHEET_BOX = (700, 600, 1150, 880)       # the shelf region (x0, y0, x1, y1), shown at x2


def sheet():
    """qa-sheet-planter.jpg: the shelf region at x2 before / after; after with the planter's alpha (red, >= 128), its shadow (blue,
    < 0.97) and the clay's silhouette (green); the measures and flat swatches (computed from L*a*b*: no supplier pixels)"""
    import copy
    from PIL import ImageFont
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    old = copy.deepcopy(man)
    old["layers"] = [l for l in old["layers"] if l["slot"] != SLOT]
    before = defaults_without_planter()
    after = np.asarray(Image.open(os.path.join(ST, "b1-defaults.png")).convert("RGB"))
    lay = [l for l in man["layers"] if l["slot"] == SLOT][0]
    a = np.asarray(Image.open(os.path.join(ST, lay["layer"])))[..., 3]
    sh = np.asarray(Image.open(os.path.join(ST, lay["shadow"])))
    ck = json.load(open(os.path.join(ST, "b1-checks.json")))["ledge_planter"]
    x0, y0, x1, y1 = SHEET_BOX
    W2, H2 = (x1 - x0) * 2, (y1 - y0) * 2

    def panel(img):
        return Image.fromarray(img).crop((x0, y0, x1, y1)).resize((W2, H2), Image.LANCZOS)
    ov = after.astype(np.float64).copy()
    sm = sh < 247
    ov[sm] = ov[sm] * 0.6 + np.array([40, 90, 255]) * 0.4
    am = a >= 128
    edge = am & ~C.ero(am, 1)
    ov[edge] = [255, 30, 30]
    ca, _ = silhouette(1530, 2720)
    cm = ca >= 0.5
    ov[cm & ~C.ero(cm, 1)] = [20, 200, 60]
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
    out = Image.new("RGB", (W2 * 2 + 30, H2 * 2 + 90), (245, 243, 239))
    d = ImageDraw.Draw(out)
    tiles = [(panel(before), "before (B1 defaults, 2026-11-19), x2"), (panel(after), "after: ledge planter 228781 ...577, x2"),
             (panel(C.q(ov / 255)), "alpha >= 128 (red), shadow < 0.97 (blue), clay silhouette (green)")]
    for i, (im, t) in enumerate(tiles):
        x, y = (i % 2) * (W2 + 30), (i // 2) * (H2 + 45)
        d.text((x + 6, y + 8), t, fill=(30, 30, 30), font=f)
        out.paste(im, (x, y + 40))
    x, y = W2 + 30, H2 + 45
    sz, col = ck["size"], ck["colour"]
    lines = [f"Shelf region canvas x {x0}-{x1}, y {y0}-{y1} (2720 x 1530), shown x2",
             f"Size vs clay scale: W {sz['width_cm']} cm ({sz['width_ratio']:.3f}), H {sz['height_cm']} cm ({sz['height_ratio']:.3f});",
             f"   SKU 13.2 x 11.8, rule +-5 %. As drawn: W {sz['as_drawn']['width_cm_at_clay_scale']} cm, back rim-foot {sz['as_drawn']['back_rim_to_foot_cm']} cm",
             f"Colour R5, lit half (right): {col['after_lit']}  dE00 {col['de00_after_lit']} (before gain {col['de00_before']})",
             f"   SKU photo ...577: {col['sku_photo_lab']}; shaded half {col['after_shaded_half']} dE00 {col['de00_shaded_half']}",
             f"Black point: layer min L* {ck['black_point']['layer_min_L']} (WM-G1 11-14)",
             f"RND2 outside every mask: {ck['rnd2']['defaults']['rnd2_outside_differing_px']} (defaults), {ck['rnd2']['beige']['rnd2_outside_differing_px']} (Beige)",
             f"Changed outside the planter alpha+shadow: {ck['rnd2']['defaults']['changed_outside_planter_alpha_and_shadow']}",
             f"Plant (filler, not sold): rises {ck['plant_rises_above_rim_cm']} cm above the rim",
             "Swatches (flat, from L*a*b*): SKU reading | R5 after | rendered lit-half median"]
    for j, t in enumerate(lines):
        d.text((x + 6, y + 10 + j * 30), t, fill=(30, 30, 30), font=fs)
    pg = after.astype(np.float64) / 255
    lab_lit = G.to_lab(pg[(a == 255) & (np.arange(2720)[None, :] >= P.px(CENTRE[0], CENTRE[1], LEDGE_Z)[0])
                          & ~C.dil(G.to_lab(pg)[..., 1] < -4, 1)])
    sw = [G.from_lab(np.array([SKU_LAB]))[0], G.from_lab(np.array([col["after_lit"]]))[0], G.from_lab(np.median(lab_lit, 0)[None])[0]]
    for j, c in enumerate(sw):
        d.rectangle([x + 10 + j * 150, y + 320, x + 140 + j * 150, y + 420], fill=tuple(int(v) for v in C.q(np.clip(c, 0, 1))))
    out.save(os.path.join(ST, "qa-sheet-planter.jpg"), quality=90)
    print(out.size)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prep":
        prep()
    else:
        globals()[cmd](*sys.argv[2:])
