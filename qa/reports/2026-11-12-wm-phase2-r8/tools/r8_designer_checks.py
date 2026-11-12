#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R8, the coordinator's addendum): the checks the designer handed QA in docs/proposals/wm-r7-table-decisions-2026-11-12.md
that the R6/R7 report did not close (3.2.1, 3.2.2, 3.2.3, 3.3.2, 3.4), measured on the R8 files; and the designer's WM-T3 between-the-feet
rule (docs/proposals/wm-r8-eye-2026-11-12.md 3.3) read on R8 as written.
  3.2.1  554205: median h and C* over the bottom 120 rows of the free part (x 0-129; per column the 120 rows above the hem's alpha-0.5
         crossing; alpha 255 eroded 2) against the curtain body above it (rows 300 .. hem-160) in the same columns; target |dh| <= 8, C* >= 3.
         On the set-B variant truth; also 180502 for reference, and the in-frame columns x 78-129 alone.
  3.2.2  Linen 260: the light band under the hem at x 40-75, y 1368-1384: curtain 3's alpha and shadow there, the truth vs base.png, and
         base.png's own L* profile (is the band in the base?).
  3.2.3  Linen weave vs the SKU photo (CJYD218713946TG's image, read from the session scratchpad only, -I; nothing of it is written to the
         repo): high-pass L* (sigma 3); per direction the share of gradient energy (horizontal vs vertical threads); and the regularity of
         each thread direction: the peak-to-median ratio of the 1-D power spectrum of the direction's mean profile over periods 3-40 px
         (a woven check / grid reads >> 10; random slubs read ~3-6). Numbers only.
  3.3.2  travertine B's cup, left soft edge (x 1747-1752, y 1204-1213; set B): the layer's alpha and RGB there against base.png at the same
         pixel and at the R6 place (+81, +10: the pair moved by (-81, -10)); the composite's L* against base.
  3.4a   the black bowl's right edge (x ~1998-2002, y 1269-1289, set B): per row, L* 1-3 px outside the alpha-0.5 edge minus the walnut 6-10
         px outside; > 2 = halo; the same on base.png (is the light line the table's own?).
  3.4b   the table's rounded edge under the throw (x 2045-2100, y 1185-1255): bright dots (L* >= 4 above the 5 x 5 median) in the set-B
         composite, and how many of them are in base.png at the same pixel; set B's alpha and shadow there.
  T3     the WM-T3 rule as written: "between the feet (alpha 0, between A's and B's boxes): max darkening <= 4/255", on the R8 shadow.
Writes data/designer-checks.json and overlays/designer-*.png (renders only).    ~/.venvs/motion/bin/python3.12 -I r8_designer_checks.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
LD = os.path.join(P2, "layers")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r8")
SC = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
WP = np.array([0.95047, 1.0, 1.08883])


def u8(p):
    return np.asarray(Image.open(p))


def lab(c8):
    c = np.asarray(c8, np.float64) / 255
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = lin @ M.T / WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def hC(L):
    a, b = np.median(L[:, 1]), np.median(L[:, 2])
    return dict(L=round(float(np.median(L[:, 0])), 2), C=round(float(np.hypot(a, b)), 2), h=round(float(np.degrees(np.arctan2(b, a)) % 360), 1), px=int(len(L)))


m8 = json.load(open(os.path.join(LD, "manifest-r8.json")))
b8 = {l_["id"]: l_ for l_ in m8["layers"]}
V8 = {v["id"]: v for vs in m8["variants"].values() for v in vs}
base = u8(os.path.join(LD, "base.png"))[..., :3]
res = {}

# ------------------------------------------------------------------ 3.2.1
r321 = {}
for key, lf, tf in (("554205 (v2)", V8["curtains-v2"]["file"], "graded/variant-r8-curtains-v2-set-B-graded-v3c.png"),
                    ("180502 (default, reference)", b8["curtains"]["file"], "graded/default-scene-r8-set-B-graded-v3c.png")):
    A = u8(os.path.join(LD, lf))[..., 3]
    T = u8(os.path.join(P2, tf))[..., :3]
    inner = cv2.erode((A == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    rec = {}
    for name, xs in (("x 0-129", range(0, 130)), ("in frame x 78-129", range(78, 130))):
        bot, body = np.zeros(A.shape, bool), np.zeros(A.shape, bool)
        for x in xs:
            ys = np.nonzero(A[1250:1460, x] >= 128)[0]
            if not len(ys):
                continue
            hem = 1250 + int(ys.max())
            bot[hem - 120:hem, x] = True
            body[300:hem - 160, x] = True
        bot &= inner
        body &= inner
        lb, lo = hC(lab(T[bot])), hC(lab(T[body]))
        dh = (lb["h"] - lo["h"] + 180) % 360 - 180
        rec[name] = dict(bottom_120=lb, body_above=lo, dh=round(float(dh), 1), pass_=bool(abs(dh) <= 8 and lb["C"] >= 3))
    r321[key] = rec
res["3.2.1_554205_bottom_hue"] = dict(rule="|dh| <= 8 deg against the body above and C* >= 3", result=r321)
print("3.2.1", json.dumps(r321), flush=True)

# ------------------------------------------------------------------ 3.2.2
A3 = u8(os.path.join(LD, V8["curtains-v3"]["file"]))[..., 3]
S3 = u8(os.path.join(LD, V8["curtains-v3"]["shadow"]))
S3 = S3[..., :3].min(2) if S3.ndim == 3 else S3
T3 = u8(os.path.join(P2, "graded/variant-r8-curtains-v3-set-B-graded-v3c.png"))[..., :3]
x0, x1, y0, y1 = 40, 76, 1368, 1385
Lb = lab(base)[..., 0]
Lt = lab(T3)[..., 0]
prof = {str(y): round(float(np.median(Lb[y, x0:x1])), 1) for y in range(1352, 1402, 2)}
res["3.2.2_linen_band_under_hem"] = dict(
    box=[x0, y0, x1 - 1, y1 - 1], in_camera_frame=False, camera_frame_left_x=77.49,
    v3_alpha_gt0_px=int((A3[y0:y1, x0:x1] > 0).sum()), v3_shadow_lt255_px=int((S3[y0:y1, x0:x1] < 255).sum()),
    v3_shadow_min=int(S3[y0:y1, x0:x1].min()),
    truth_minus_base_L_max_abs=round(float(np.abs(Lt[y0:y1, x0:x1] - Lb[y0:y1, x0:x1]).max()), 2),
    base_L_profile_median_x40_75=prof,
    band_in_base_row_median_test=bool(np.median(Lb[y0:y1, x0:x1]) - np.median(np.r_[Lb[1352:1364, x0:x1].ravel(), Lb[1390:1402, x0:x1].ravel()]) > 3),
    row_median_test_note="the band is a 1-px DIAGONAL line, which a per-row median smears out; the per-column test below follows it")
# per column: the brightest row in y 1360-1395 against the median of the 4 rows above and below it, in base and in the truth
pc = []
for x in range(x0, x1):
    colb = Lb[1356:1400, x]
    i = 4 + int(np.argmax(colb[4:-4]))
    prom_b = float(colb[i] - np.median(np.r_[colb[i - 4:i - 1], colb[i + 2:i + 5]]))
    colt = Lt[1356:1400, x]
    prom_t = float(colt[i] - np.median(np.r_[colt[i - 4:i - 1], colt[i + 2:i + 5]]))
    pc.append((x, 1356 + i, round(prom_b, 2), round(prom_t, 2)))
res["3.2.2_linen_band_under_hem"].update(
    line_per_column=dict(rows_x40_75=[r[1] for r in pc], base_prominence_median=round(float(np.median([r[2] for r in pc])), 2),
                         truth_prominence_median=round(float(np.median([r[3] for r in pc])), 2)),
    band_in_base=bool(np.median([r[2] for r in pc]) >= 1.5))
print("3.2.2", res["3.2.2_linen_band_under_hem"], flush=True)


# ------------------------------------------------------------------ 3.2.3
def weave(L):
    hp = L - cv2.GaussianBlur(L.astype(np.float32), (0, 0), 3)
    gx, gy = np.abs(np.diff(hp, axis=1)).mean(), np.abs(np.diff(hp, axis=0)).mean()
    out = dict(vertical_thread_share=round(float(gx / (gx + gy)), 3))

    def peak(profile):
        p = profile - profile.mean()
        P = np.abs(np.fft.rfft(p * np.hanning(len(p)))) ** 2
        f = np.fft.rfftfreq(len(p))
        sel = (f >= 1 / 40) & (f <= 1 / 3)
        return round(float(P[sel].max() / np.median(P[sel])), 1), round(float(1 / f[sel][np.argmax(P[sel])]), 1)

    out["horizontal_threads_peak_to_median"], out["horizontal_threads_period_px"] = peak(hp.mean(1))
    out["vertical_threads_peak_to_median"], out["vertical_threads_period_px"] = peak(hp.mean(0))
    out["hp_std"] = round(float(hp.std()), 2)
    return out


rw = {}
Lv3 = lab(T3)[..., 0]
for name, (a, b, c, d) in (("render, R8 Linen, x 80-250 y 300-700", (80, 300, 250, 700)), ("render, R8 Linen, x 80-250 y 700-1100", (80, 700, 250, 1100))):
    rw[name] = weave(Lv3[b:d, a:c])
p = os.path.join(SC, "r7/refs-dl/curt3/img1.jpg")
if os.path.exists(p):
    ph = np.asarray(Image.open(p).convert("RGB"))
    H_, W_ = ph.shape[:2]
    Lp = lab(ph)[..., 0]
    rw["SKU photo (CJYD218713946TG image), cloth x 0.03-0.55, y 0.02-0.50"] = weave(Lp[int(0.02 * H_):int(0.50 * H_), int(0.03 * W_):int(0.55 * W_)])
    rw["SKU photo, cloth x 0.03-0.55, y 0.72-0.98 (below the shadow band)"] = weave(Lp[int(0.72 * H_):int(0.98 * H_), int(0.03 * W_):int(0.55 * W_)])
else:
    rw["SKU photo"] = "not available offline"
res["3.2.3_linen_weave_vs_sku"] = dict(method="numbers only; the photo stays in the session scratchpad", result=rw)
print("3.2.3", json.dumps(rw), flush=True)

# ------------------------------------------------------------------ 3.3.2
L8 = u8(os.path.join(LD, b8["candle-holders"]["file"]))
TB = u8(os.path.join(P2, "graded/default-scene-r8-set-B-graded-v3c.png"))[..., :3]
bx = (1744, 1200, 1756, 1218)
A = L8[bx[1]:bx[3], bx[0]:bx[2], 3].astype(int)
soft = (A > 0) & (A < 255)
ys, xs = np.nonzero(soft)
rgb = L8[bx[1]:bx[3], bx[0]:bx[2], :3].astype(float)
dnew = [float(np.abs(rgb[y, x] - base[bx[1] + y, bx[0] + x]).max()) for y, x in zip(ys, xs)]
dold = [float(np.abs(rgb[y, x] - base[bx[1] + y + 10, bx[0] + x + 81]).max()) for y, x in zip(ys, xs)]
LT, LB = lab(TB[bx[1]:bx[3], bx[0]:bx[2]])[..., 0], Lb[bx[1]:bx[3], bx[0]:bx[2]]
outside = A == 0
res["3.3.2_travertine_B_cup_left_edge"] = dict(
    box=list(bx), soft_alpha_px=int(soft.sum()), soft_alpha_max=int(A[soft].max()) if soft.any() else 0,
    layer_rgb_vs_base_here_median=round(float(np.median(dnew)), 1) if dnew else None, layer_rgb_vs_base_at_r6_place_median=round(float(np.median(dold)), 1) if dold else None,
    composite_minus_base_L_alpha0_max=round(float((LT - LB)[outside].max()), 2), composite_minus_base_L_alpha0_min=round(float((LT - LB)[outside].min()), 2),
    composite_minus_base_L_soft_max=round(float((LT - LB)[soft].max()), 2) if soft.any() else None,
    base_L_in_box_p90=round(float(np.percentile(LB, 90)), 1), composite_L_in_box_p90=round(float(np.percentile(LT, 90)), 1))
print("3.3.2", res["3.3.2_travertine_B_cup_left_edge"], flush=True)

# ------------------------------------------------------------------ 3.4a
Ab = u8(os.path.join(LD, b8["bowl"]["file"]))[..., 3]
rows = []
for y in range(1262, 1296):
    xs_ = np.nonzero(Ab[y, 1900:2060] >= 128)[0]
    if not len(xs_):
        continue
    e = 1900 + int(xs_.max())
    if not (1990 <= e <= 2010):
        continue
    nb = TB[y, e + 1:e + 4]
    far = TB[y, e + 6:e + 11]
    dl = float(lab(nb)[..., 0].mean() - lab(far)[..., 0].mean())
    dlb = float(lab(base[y, e + 1:e + 4])[..., 0].mean() - lab(base[y, e + 6:e + 11])[..., 0].mean())
    rows.append(dict(y=y, edge_x=e, dL_composite=round(dl, 2), dL_base=round(dlb, 2), alpha_e1_e3=[int(v) for v in Ab[y, e + 1:e + 4]]))
dls = [r["dL_composite"] for r in rows if 1269 <= r["y"] <= 1289]
res["3.4a_black_bowl_right_edge"] = dict(rule="dL (1-3 px out minus 6-10 px out) > 2 = halo", rows=rows,
                                         dL_max_1269_1289=round(max(dls), 2) if dls else None, dL_median_1269_1289=round(float(np.median(dls)), 2) if dls else None,
                                         rows_over_2=sum(d > 2 for d in dls), base_dL_median=round(float(np.median([r["dL_base"] for r in rows])), 2) if rows else None)
print("3.4a", {k: v for k, v in res["3.4a_black_bowl_right_edge"].items() if k != "rows"}, flush=True)

# ------------------------------------------------------------------ 3.4b
bb = (2040, 1180, 2105, 1260)
SBl = u8(os.path.join(LD, m8["slot_cushions"]["sets"]["B"]["layer"]))
SBs = u8(os.path.join(LD, m8["slot_cushions"]["sets"]["B"]["shadow"]))
SBs = SBs[..., :3].min(2) if SBs.ndim == 3 else SBs
LTb = lab(TB[bb[1]:bb[3], bb[0]:bb[2]])[..., 0].astype(np.float32)
LBb = Lb[bb[1]:bb[3], bb[0]:bb[2]].astype(np.float32)


def dots(L):
    med = cv2.medianBlur(np.clip(L * 2.55, 0, 255).astype(np.uint8), 5).astype(np.float32) / 2.55
    return (L - med) >= 4


dT, dB = dots(LTb), dots(LBb)
aB = SBl[bb[1]:bb[3], bb[0]:bb[2], 3]
res["3.4b_table_edge_under_throw"] = dict(box=list(bb), bright_dots_composite=int(dT.sum()), of_them_also_in_base=int((dT & dB).sum()),
                                          bright_dots_base=int(dB.sum()), composite_dots_under_set_B_alpha=int((dT & (aB > 0)).sum()),
                                          composite_dots_where_set_B_alpha0=int((dT & (aB == 0)).sum()),
                                          composite_eq_base_x_shadow_where_alpha0_maxdiff=int(np.abs(TB[bb[1]:bb[3], bb[0]:bb[2]].astype(int) -
                                                                                               np.floor(base[bb[1]:bb[3], bb[0]:bb[2]].astype(float) * SBs[bb[1]:bb[3], bb[0]:bb[2], None] / 255 + 0.5).astype(int)).max(2)[aB == 0].max()))
print("3.4b", res["3.4b_table_edge_under_throw"], flush=True)

# ------------------------------------------------------------------ T3: the rule as written, on R8
s8 = u8(os.path.join(P2, "work-r8/shadows/candle-holders.png"))
s8 = (s8[..., :3].min(2) if s8.ndim == 3 else s8).astype(int)
a8 = u8(os.path.join(P2, "work-r8/layers/candle-holders.png"))[..., 3]
boxA, boxB = (1648, 1148, 1692, 1258), (1747, 1166, 1795, 1270)        # fix-r8.json holders.pieces (x0, y0, x1, y1)
zone = np.zeros(s8.shape, bool)
zone[min(boxA[1], boxB[1]):max(boxA[3], boxB[3]) + 1, boxA[2] + 1:boxB[0]] = True
zone &= a8 == 0
dz = 255 - s8[zone]
zx = np.nonzero(zone.any(0))[0]
per_col = {int(x): int(255 - s8[:, x][zone[:, x]].min()) for x in zx}
first_le4 = next((x for x in sorted(per_col) if all(per_col[c] <= 4 for c in per_col if c >= x)), None)
res["T3_rule_on_r8"] = dict(zone="alpha 0, x 1693-1746 (between the boxes), y 1148-1270", max_darkening=int(dz.max()), px_gt4=int((dz > 4).sum()),
                            per_column_max=per_col, first_column_from_which_all_le4=first_le4,
                            note="the zone as written holds A's own cast fan (the light from the left) and its fade; the gap proper (x >= 1718) reads <= 2")
print("T3", {k: v for k, v in res["T3_rule_on_r8"].items() if k != "per_column_max"}, flush=True)

# overlays (renders only)
c1 = TB[1180:1300, 1960:2120]
c2 = base[1180:1300, 1960:2120]
row = np.concatenate([c1, np.zeros((120, 4, 3), np.uint8), c2], 1)
Image.fromarray(row).resize((row.shape[1] * 4, row.shape[0] * 4), Image.NEAREST).save(os.path.join(OUT, "overlays/designer-3.4-bowl-edge-and-table-edge-r8-vs-base-x4.png"))
c1 = TB[1190:1230, 1730:1770]
c2 = base[1190:1230, 1730:1770]
row = np.concatenate([c1, np.zeros((40, 2, 3), np.uint8), c2], 1)
Image.fromarray(row).resize((row.shape[1] * 8, row.shape[0] * 8), Image.NEAREST).save(os.path.join(OUT, "overlays/designer-3.3.2-cup-B-left-edge-r8-vs-base-x8.png"))
c1 = T3[1340:1410, 20:140]
c2 = base[1340:1410, 20:140]
row = np.concatenate([c1, np.zeros((70, 3, 3), np.uint8), c2], 1)
Image.fromarray(row).resize((row.shape[1] * 6, row.shape[0] * 6), Image.NEAREST).save(os.path.join(OUT, "overlays/designer-3.2.2-linen-under-hem-r8-vs-base-x6.png"))
json.dump(res, open(os.path.join(OUT, "data/designer-checks.json"), "w"), indent=1)
