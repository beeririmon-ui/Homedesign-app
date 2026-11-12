#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R6/R7): the curtains.
  R6  the default flip (180502 = R5's curtains-v2 bytes) and 554205 recoloured relative to 180502 (QA's same mask, set-B truths).
  R7  the sold length (designer, owner-answers-applied-2026-11-12.md section 6.3), on all three layers:
      - the plan's lines with QA's OWN projection (qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py, camera M0 1.2,
        canvas_uv of shell_lock.py): the hem (Z 0.12 / 0.22 on X -2.15, Y 2.95 -> 2.85), the stone contact (Z 0.45 on X -2.15,
        Y 2.85 -> 2.65), the bench end face's top edge (Y 2.85, Z 0.45, X -2.30 -> -1.98) for the snap-to-base condition;
      - per column the layer's lowest alpha-0.5 crossing (sub-pixel) against the line: deviation in canvas px, in 2160-frame px and in cm;
      - the alpha ramp at the hem (px with 0 < a < 255 per column); alpha 0 below the lines;
      - the composite below the lines = base x the curtain's shadow (nothing else of the curtain);
      - the shadow: the floor contact line gone, the shade under the hem (max darkening, fade), the stone contact line (multiply);
      - the hem band (18 px above the hem) against the 20 px above it, L* on the set-B truth; the break over the bench;
      - the layer above the cut unchanged against r6 (RGB and alpha), and the room-side inner edge (rows 200-1200) per variant;
      - the base's own edge where the bench end face's top edge projects (designer item 2: within 8 px at 3840 -> follow the base).
  Colour: 554205 and curtain 3 against 180502 in QA's same mask (alpha 255 eroded 5x5, rows 100-1400 of both layers, the free part
  only), absolute and relative to the room's white (von Kries against the lit back-wall plaster of base.png), and the curtain-3 SKU
  photo (Linen) against 180502's photo, relative to their own whites, from the scratchpad (never in the repo).
Writes data/curtains.json.
"""
import hashlib
import importlib.util
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-tool-phase2-r6-r7")
SC = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
spec = importlib.util.spec_from_file_location("r1", os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py"))
r1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r1)
CAM = r1.CAM["M0"]
K = 2720 / 4072          # 3840-frame px -> canvas px
PX_2160 = 1530 / 2290 * 2290 / 2160 * 0 + K   # canvas px per 2160-frame px is K (both axes)


def px(X, Y, Z):
    u, v, d = r1.project(CAM, X, Y, Z)
    return np.array([(116 + u * 3840) * K, (65 + v * 2160) * K])


def u8(p):
    return np.asarray(Image.open(p))


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def lab8(c8):
    return cv2.cvtColor(c8.reshape(-1, 1, 3).astype(np.float32) / 255, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float64)


def lin(c8):
    c = c8.astype(np.float64) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def enc(l_):
    l_ = np.clip(l_, 0, 1)
    return np.where(l_ <= 0.0031308, 12.92 * l_, 1.055 * l_ ** (1 / 2.4) - 0.055)


def summ(lab):
    L, a, b = np.median(lab, 0)
    C = np.hypot(lab[:, 1], lab[:, 2])
    return dict(L=round(float(L), 2), C=round(float(np.hypot(a, b)), 2), h=round(float(np.degrees(np.arctan2(b, a)) % 360), 1),
                C_p95=round(float(np.percentile(C, 95)), 2), L_p99=round(float(np.percentile(lab[:, 0], 99)), 2), px=int(len(lab)))


def rel(px8, white):
    r = lin(px8) / white[None, :]
    return summ(lab8((enc(np.clip(r, 0, 1)) * 255)))


def hp_std(L, mask):
    lo = cv2.GaussianBlur(L.astype(np.float32), (0, 0), 3)
    return round(float(np.std((L - lo)[mask])), 3)


m6 = json.load(open(os.path.join(P2, "layers/manifest-r6.json")))
m7 = json.load(open(os.path.join(P2, "layers/manifest-r7.json")))
m5 = json.load(open(os.path.join(P2, "layers/manifest-r5.json")))
b6 = {l_["id"]: l_ for l_ in m6["layers"]}
b7 = {l_["id"]: l_ for l_ in m7["layers"]}
b5 = {l_["id"]: l_ for l_ in m5["layers"]}
V = {v["id"]: v for vs in m7["variants"].values() for v in vs}
V6 = {v["id"]: v for vs in m6["variants"].values() for v in vs}
V5 = {v["id"]: v for vs in m5["variants"].values() for v in vs}
LD = os.path.join(P2, "layers")
res = {}

# ---------------------------------------------------------------- R6: the flip
res["r6_flip"] = dict(
    r6_default_file=b6["curtains"]["file"], r6_default_card=b6["curtains"]["product"]["card_id"],
    r6_default_same_bytes_as_r5_curtains_v2=sha(os.path.join(LD, b6["curtains"]["file"])) == sha(os.path.join(LD, V5["curtains-v2"]["file"])),
    r6_default_shadow_same_bytes_as_r5_v2=sha(os.path.join(LD, b6["curtains-shadow"]["file"])) == sha(os.path.join(LD, V5["curtains-v2"]["shadow"])),
    r6_v2_card=V6["curtains-v2"]["product"]["card_id"], r7_default_card=b7["curtains"]["product"]["card_id"],
    r7_v2_card=V["curtains-v2"]["product"]["card_id"], r7_v3_card=V["curtains-v3"]["product"]["card_id"],
    r7_v3_option=V["curtains-v3"]["product"].get("option"), r7_v3_sku=V["curtains-v3"]["product"].get("sku"),
    r6_default_flag=b6["curtains"]["product"].get("default"), r7_default_flag=b7["curtains"]["product"].get("default"))
print(res["r6_flip"])

# ---------------------------------------------------------------- colour (same mask)
base = u8(os.path.join(LD, "base.png"))[..., :3]
WHITE = np.median(lin(base[200:600, 1100:1400].reshape(-1, 3)), 0)
fa = u8(os.path.join(P1, "fixed-furniture.png"))[..., 3]


def lay(tag, key):
    if tag == "r6":
        f = b6["curtains"]["file"] if key == "default" else V6[key]["file"]
    elif tag == "r5":
        f = b5["curtains"]["file"] if key == "default" else V5[key]["file"]
    else:
        f = b7["curtains"]["file"] if key == "default" else V[key]["file"]
    return u8(os.path.join(LD, f))


def truth(tag, key):
    return u8(os.path.join(P2, f"graded/default-scene-{tag}-set-B-graded-v3c.png" if key == "default" else f"graded/variant-{tag}-{key}-set-B-graded-v3c.png"))[..., :3]


def mask_of(A):
    m = cv2.erode((A == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    m[:100] = False
    m[1400:] = False
    return m


col = {}
for tag, keys in (("r6", ("default", "curtains-v2")), ("r7", ("default", "curtains-v2", "curtains-v3"))):
    Ls = {k: lay(tag, k) for k in keys}
    same = np.ones(fa.shape, bool)
    for k in keys:
        same &= mask_of(Ls[k][..., 3])
    same[1150:] = False      # above the cut zone (R7) and above the armchair, so R6 and R7 read the same cloth
    col[tag] = {}
    for k in keys:
        T = truth(tag, k)
        Lab = lab8(T[same])
        Lmap = cv2.cvtColor(T.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
        col[tag][k] = dict(abs=summ(Lab), rel_room_white=rel(T[same], WHITE), highpass_L_std=hp_std(Lmap, same), mask_px=int(same.sum()),
                           card=(b7 if tag == "r7" else b6)["curtains"]["product"]["card_id"] if k == "default" else (V if tag == "r7" else V6)[k]["product"]["card_id"])
    print(tag, {k: (v["abs"]["L"], v["abs"]["C"], v["abs"]["h"]) for k, v in col[tag].items()})
res["colour_same_mask"] = col


# the photos, relative to their own white (scratchpad; supplier images only as a reference)
def photo(path, box, wbox):
    im = np.asarray(Image.open(path).convert("RGB"))
    H, W = im.shape[:2]
    x0, y0, x1, y1 = [int(round(t)) for t in (box[0] * W, box[1] * H, box[2] * W, box[3] * H)]
    a = im[y0:y1, x0:x1].reshape(-1, 3)
    wx0, wy0, wx1, wy1 = [int(round(t)) for t in (wbox[0] * W, wbox[1] * H, wbox[2] * W, wbox[3] * H)]
    w = im[wy0:wy1, wx0:wx1].reshape(-1, 3)
    wl = np.median(lin(w), 0)
    return dict(abs=summ(lab8(a)), white_abs=summ(lab8(w)), rel_own_white=rel(a, wl))


ph = {}
try:
    # Linen SKU image (card option 'linen' image = refs-dl/curt3/img1.jpg): the backlit cloth on the left; its white: the window pane at the
    # right edge behind the sheer is not clean, so the brightest 2 % of the whole image stands in for the white (reported)
    p3 = os.path.join(SC, "r7/refs-dl/curt3/img1.jpg")
    im3 = np.asarray(Image.open(p3).convert("RGB"))
    Lm = cv2.cvtColor(im3.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
    thr = np.percentile(Lm, 98)
    wl3 = np.median(lin(im3[Lm >= thr]), 0)
    H3, W3 = im3.shape[:2]
    a3 = im3[0:int(0.5 * H3), 0:int(0.58 * W3)].reshape(-1, 3)
    ph["linen_curt3_img1"] = dict(crop="x 0-0.58, y 0-0.50 (the cloth)", abs=summ(lab8(a3)), white="brightest 2 %", white_abs=summ(lab8(im3[Lm >= thr])),
                                  rel_own_white=rel(a3, wl3))
    p1 = os.path.join(SC, "r5/refs-dl/curtains2/sku.jpg")
    im1 = np.asarray(Image.open(p1).convert("RGB"))
    Lm1 = cv2.cvtColor(im1.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
    thr1 = np.percentile(Lm1, 98)
    wl1 = np.median(lin(im1[Lm1 >= thr1]), 0)
    H1, W1 = im1.shape[:2]
    a1 = im1[int(0.1 * H1):int(0.8 * H1), int(0.2 * W1):int(0.95 * W1)]
    a1 = a1[(cv2.cvtColor(a1.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0] > 60)].reshape(-1, 3)
    ph["s_fold_180502_sku"] = dict(crop="x 0.2-0.95, y 0.1-0.8, L > 60", abs=summ(lab8(a1)), white="brightest 2 %", white_abs=summ(lab8(im1[Lm1 >= thr1])),
                                   rel_own_white=rel(a1, wl1))
except Exception as e:      # noqa: BLE001
    ph["error"] = repr(e)
res["photos"] = ph
print("photos", json.dumps(ph)[:800])

# ---------------------------------------------------------------- R7 geometry
hem = {0.12: [px(-2.15, 2.95, 0.12), px(-2.15, 2.85, 0.12)], 0.22: [px(-2.15, 2.95, 0.22), px(-2.15, 2.85, 0.22)]}
con = [px(-2.15, 2.85, 0.45), px(-2.15, 2.65, 0.45)]
endtop = [px(-2.30, 2.85, 0.45), px(-1.98, 2.85, 0.45)]
cm_px = float(np.linalg.norm(px(-2.15, 2.85, 0.12) - px(-2.15, 2.85, 0.22))) / 10.0
res["lines_canvas_px"] = dict(hem_270=[list(map(lambda t: round(float(t), 1), p)) for p in hem[0.12]],
                              hem_260=[list(map(lambda t: round(float(t), 1), p)) for p in hem[0.22]],
                              contact=[list(map(lambda t: round(float(t), 1), p)) for p in con],
                              bench_end_face_top=[list(map(lambda t: round(float(t), 1), p)) for p in endtop], canvas_px_per_cm_at_hem=round(cm_px, 2),
                              frame_left_canvas_px=77.49)


def yline(P, x):
    (x0, y0), (x1, y1) = P
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


# the base's own edge along the bench end face's top edge (x 80-190): the strongest vertical L* step within +-10 px of the line
Lb = cv2.cvtColor(base.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
Lbs = cv2.GaussianBlur(Lb, (0, 0), 0.8)
offs = []
for x in range(80, 128):
    y0 = yline(endtop, x)
    ys = np.arange(int(y0) - 10, int(y0) + 11)
    g = np.abs(np.diff(Lbs[ys, x]))
    i = int(np.argmax(g))
    offs.append(float(ys[i] + 0.5 - y0))
offs = np.array(offs)
res["snap_to_base"] = dict(what="the base's L* step along the bench end face's top edge, x 80-127 (left of the curtain cut's corner)",
                           median_px=round(float(np.median(offs)), 2), p90_abs_px=round(float(np.percentile(np.abs(offs), 90)), 2),
                           in_3840_px_p90=round(float(np.percentile(np.abs(offs), 90)) / K, 2), rule="<= 8 px at 3840: follow the base")
print("snap", res["snap_to_base"])


def hem_cross(A, x, ylo, yhi):
    """the lowest alpha 0.5 crossing in column x between rows ylo..yhi (sub-pixel), going down"""
    a = A[ylo:yhi, x].astype(np.float32) / 255
    idx = np.nonzero(a >= 0.5)[0]
    if not len(idx):
        return None
    i = int(idx.max())
    if i + 1 < len(a):
        a0, a1 = a[i], a[i + 1]
        t = (a0 - 0.5) / max(a0 - a1, 1e-6)
        return ylo + i + float(np.clip(t, 0, 1)) + 0.5 - 0.5
    return float(ylo + i)


geo = {}
for key, hz in (("default", 0.12), ("curtains-v2", 0.12), ("curtains-v3", 0.22)):
    L7 = lay("r7", key)
    A = L7[..., 3]
    free = A.astype(np.float32)
    rec = {}
    dev = []
    ramps = []
    for x in range(78, 128):
        yp = yline(hem[hz], x)
        yc = hem_cross(A, x, int(yp) - 40, int(yp) + 40)
        if yc is None:
            continue
        dev.append(yc - yp)
        col_ = A[int(yp) - 10:int(yp) + 12, x]
        ramps.append(int(((col_ > 0) & (col_ < 255)).sum()))
    dev = np.array(dev)
    rec["hem_in_frame_x78_127"] = dict(n=len(dev), median_px=round(float(np.median(dev)), 2), min_px=round(float(dev.min()), 2), max_px=round(float(dev.max()), 2),
                                       max_abs_cm=round(float(np.abs(dev).max()) / cm_px, 2), median_cm=round(float(np.median(dev)) / cm_px, 2),
                                       max_abs_px_2160=round(float(np.abs(dev).max()) / K, 2), rule="+-1 cm (+-9 px at 2160)")
    rec["hem_ramp_px_per_column"] = dict(median=float(np.median(ramps)), max=int(max(ramps)))
    # overscan part (x 40-77): reported
    devo = []
    for x in range(40, 78):
        yp = yline(hem[hz], x)
        yc = hem_cross(A, x, int(yp) - 40, int(yp) + 40)
        if yc is not None:
            devo.append(yc - yp)
    rec["hem_overscan_x40_77"] = dict(n=len(devo), median_px=round(float(np.median(devo)), 2) if devo else None,
                                      max_abs_px=round(float(np.abs(devo).max()), 2) if devo else None)
    # the contact segment: where the armchair does not cover (fixed furniture alpha 0 at the line)
    dc = []
    for x in range(131, 245):
        yp = yline(con, x)
        if fa[int(yp) - 6:int(yp) + 6, x].max() > 0:
            continue
        yc = hem_cross(A, x, int(yp) - 30, int(yp) + 30)
        if yc is not None:
            dc.append(yc - yp)
    rec["contact_visible_columns"] = dict(n=len(dc), median_px=round(float(np.median(dc)), 2) if dc else None,
                                          max_abs_px=round(float(np.abs(dc).max()), 2) if dc else None)
    # alpha 0 below the lines
    H, W = A.shape
    yy, xx = np.mgrid[0:H, 0:W]
    below = np.zeros(A.shape, bool)
    xs_ = np.arange(W)
    yh = np.where(xs_ <= 129, yline(hem[hz], xs_), np.inf)
    ycn = np.where((xs_ > 136) & (xs_ < 420), yline(con, xs_), np.inf)
    below |= (yy > yh[None, :] + 3) & (xx <= 129)
    below |= (yy > ycn[None, :] + 3) & (xx > 136) & (xx < 420)
    rec["alpha_above_0_below_the_lines_px"] = int(((A > 0) & below).sum())
    # the composite below the lines = base x the shadow (set-B truth)
    T = truth("r7", key).astype(np.int16)
    S = u8(os.path.join(LD, b7["curtains-shadow"]["file"] if key == "default" else V[key]["shadow"]))
    S = S if S.ndim == 2 else S[..., 0]
    exp = np.floor(base.astype(np.float32) * S[..., None].astype(np.float32) / 255 + 0.5).astype(np.int16)
    zone = below & (fa == 0)
    d = np.abs(T - exp).max(2)
    rec["below_lines_truth_vs_base_x_shadow"] = dict(px=int(zone.sum()), max=int(d[zone].max()), px_gt2=int((d[zone] > 2).sum()))
    # shadow under the hem: darkening and fade (x 78-127)
    sh = S.astype(np.float32) / 255
    prof = []
    for x in range(80, 126):
        yp = yline(hem[hz], x)
        prof.append(1 - sh[int(round(yp)):int(round(yp)) + 40, x])
    prof = np.median(np.array(prof), 0)
    rec["shade_under_hem"] = dict(max_darkening=round(float(prof.max()), 4), rows_until_below_1pct=int(np.argmax(prof < 0.01)) if (prof < 0.01).any() else None,
                                  rule="<= 6 %, gone by ~17 px (25 at 3840)")
    # the floor contact line (r6) gone: x 0-310, rows 1440-1530, outside the furniture
    S6 = u8(os.path.join(LD, b6["curtains-shadow"]["file"] if key in ("default",) else V6.get(key, {}).get("shadow", b6["curtains-shadow"]["file"])))
    S6 = S6 if S6.ndim == 2 else S6[..., 0]
    fl = np.zeros(A.shape, bool)
    fl[1440:, :310] = True
    rec["floor_contact"] = dict(r6_min=int(S6[fl].min()), r7_min=int(S[fl].min()), r7_px_lt_255=int((S[fl] < 255).sum()))
    # the stone contact line: min along the visible contact columns
    cmins = []
    for x in range(131, 245):
        yp = yline(con, x)
        if fa[int(yp) - 6:int(yp) + 8, x].max() > 0:
            continue
        cmins.append(float(S[int(yp):int(yp) + 6, x].min()) / 255)
    rec["stone_contact_multiply"] = dict(n=len(cmins), median_min=round(float(np.median(cmins)), 3) if cmins else None, rule="0.90-0.95")
    # the hem band and the break, L* on the truth
    Lt = cv2.cvtColor(T.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
    band, above = [], []
    for x in range(80, 126):
        yp = yline(hem[hz], x)
        b0 = int(round(yp)) - 3
        band.append(np.median(Lt[b0 - 15:b0, x]))
        above.append(np.median(Lt[b0 - 35:b0 - 15, x]))
    rec["hem_band_dL"] = dict(value=round(float(np.median(np.array(band) - np.array(above))), 2), rule="-2 +-1 against the 20 px above (30 at 3840)")
    brk, abv = [], []
    for x in range(200, 245):
        yp = yline(con, x)
        if fa[int(yp) - 20:int(yp) + 2, x].max() > 0:
            continue
        b0 = int(round(yp)) - 1
        brk.append(np.median(Lt[b0 - 5:b0, x]))
        abv.append(np.median(Lt[b0 - 15:b0 - 5, x]))
    rec["break_dL"] = dict(n=len(brk), value=round(float(np.median(np.array(brk) - np.array(abv))), 2) if brk else None, rule="-3 to -5")
    # above the cut: unchanged against r6 (default and v2); v3 is new
    if key in ("default", "curtains-v2"):
        L6 = lay("r6", key)
        diff = (np.abs(L7.astype(np.int16) - L6.astype(np.int16)).max(2) > 0)
        yc_top = int(min(yline(con, 245), yline(con, 129))) - 40
        rec["changed_vs_r6_above_row"] = dict(row=yc_top, px=int(diff[:yc_top].sum()),
                                              where=None if not diff[:yc_top].any() else [int(v) for v in (np.nonzero(diff[:yc_top])[1].min(), np.nonzero(diff[:yc_top])[0].min(), np.nonzero(diff[:yc_top])[1].max(), np.nonzero(diff[:yc_top])[0].max())],
                                              max_change=int(np.abs(L7.astype(np.int16) - L6.astype(np.int16))[:yc_top].max()))
    geo[key] = rec
    print(key, json.dumps(rec)[:1500])


# the room-side inner edge per row (rows 200-1200 at the canvas): the rightmost alpha >= 128 column of the stack, per option
def inner_edge(A, rows):
    out = []
    for y in rows:
        xs = np.nonzero(A[y, :420] >= 128)[0]
        out.append(float(xs.max()) if len(xs) else np.nan)
    return np.array(out)


rows = np.arange(200, 1151)
e_def = inner_edge(lay("r7", "default")[..., 3], rows)
e_r1 = inner_edge(lay("r6", "curtains-v2")[..., 3], rows)     # 554205 R1 / R6: the reference stack of R1
ie = {}
for key in ("default", "curtains-v2", "curtains-v3"):
    e = inner_edge(lay("r7", key)[..., 3], rows)
    d = (e - e_r1) / 2565.02
    ok = ~np.isnan(d)
    ie[key] = dict(rows_out_of_0_003_u=int((np.abs(d[ok]) > 0.003).sum()), rows=int(ok.sum()), max_abs_u=round(float(np.abs(d[ok]).max()), 4),
                   median_u=round(float(np.median(d[ok])), 4))
res["inner_edge_vs_R1_554205"] = ie
res["geometry_r7"] = geo
print("inner", ie)
json.dump(res, open(os.path.join(OUT, "data/curtains.json"), "w"), indent=1, default=float)
