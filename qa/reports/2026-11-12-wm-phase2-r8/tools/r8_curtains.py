#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R8): the curtains. QA's own code (colour maths in numpy, D65; the projection of
qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py, camera M0 1.2, as in r67_curtains.py).
  A. True length (owner WM-C3 / SUP-C1, slots 1.9.4 drop_1_9_4, plan 1.3.6): the hem lines Z 0.12 (270) and 0.22 (260) on X -2.15,
     Y 2.95 -> 2.85; per column x 78-127 the R8 layer's lowest alpha-0.5 crossing against the line (cm); alpha 0 below the lines; the
     ungraded alpha R7 == R8; the graded alpha R7 vs R8.
  B. The bench (designer section 6.3; R8's -3.95..-3.99 and 0.925): method 1 = QA's R6/R7 formulas (r67_curtains.py, unchanged);
     method 2 (new, independent of the formula R8 copied): per visible column x 200-244 the median L* over the 4 rows just above the
     contact (y_c-5..y_c-2) minus the median over rows y_c-20..y_c-12 (the cloth above the break), and the stone contact as seen: the
     composite over base.png in linear light (Y ratio), median of the per-column minimum over the 6 rows below the contact line;
     the hem band (-2 +-1); the dark run of the halo model at x 206-216, y 1188-1194 against the contact line.
  C. Curtain 3 colour: QA's same mask (alpha 255 eroded 5x5 in all three curtain layers, rows 100-1149) on the set-B truths; L*, C*, h
     (median Lab), R7 and R8 and 180502; a "lit fabric" median (same mask, L* above the mask's own p25, the fold shadows out) and the
     in-frame part only; the cards (#D9CDB8 Linen, #EDE7DB 180502) and the card ratio; the designer's lock (L* 71.5-74.5, h 81-87,
     C* 10.5-12.5).
  D. Curtain 3 specks: (literal) h 150-230 and C* > 6, alpha > 0; (wide, R8's) h 100-230, C* > 6, a* - median7x7(a*) <= -8, alpha > 0;
     on the graded layer (straight RGB), the ungraded source and the set-B truth inside alpha > 0; R7 and R8. The speck step's invariants
     on the ungraded R7 -> R8 pair: a*b* changed only on the specks (R8's mask and QA's wide mask); Y (= L*) on the specks moved by the
     same global factor as the cloth around them (i.e. the speck step kept L*).
Writes data/curtains.json.    ~/.venvs/motion/bin/python3.12 -I r8_curtains.py
"""
import importlib.util
import json
import os

import cv2
import numpy as np
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r8")
LD = os.path.join(P2, "layers")
spec = importlib.util.spec_from_file_location("r1", os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py"))
r1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r1)
CAM = r1.CAM["M0"]
K = 2720 / 4072


def px(X, Y, Z):
    u, v, d = r1.project(CAM, X, Y, Z)
    return np.array([(116 + u * 3840) * K, (65 + v * 2160) * K])


def u8(p):
    return np.asarray(Image.open(p))


def lin(c8):
    c = np.asarray(c8, np.float64) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
WP = np.array([0.95047, 1.0, 1.08883])


def lab(c8):
    xyz = lin(c8) @ M.T / WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def Yof(c8):
    return lin(c8) @ M[1]


def hexlab(h):
    return lab(np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)]], np.uint8))[0]


def summ(L):
    a, b = np.median(L[:, 1]), np.median(L[:, 2])
    return dict(L=round(float(np.median(L[:, 0])), 2), C=round(float(np.hypot(a, b)), 2), h=round(float(np.degrees(np.arctan2(b, a)) % 360), 2),
                C_of_medians_note="C and h from the median a*, b* (as fix-r8 and r67_curtains)", px=int(len(L)))


m7 = json.load(open(os.path.join(LD, "manifest-r7.json")))
m8 = json.load(open(os.path.join(LD, "manifest-r8.json")))
b7 = {l_["id"]: l_ for l_ in m7["layers"]}
b8 = {l_["id"]: l_ for l_ in m8["layers"]}
V7 = {v["id"]: v for vs in m7["variants"].values() for v in vs}
V8 = {v["id"]: v for vs in m8["variants"].values() for v in vs}
KEYS = ("default", "curtains-v2", "curtains-v3")
WK = {"default": "curtains", "curtains-v2": "curtains-v2", "curtains-v3": "curtains-v3"}


def layer(tag, key):
    b, V = (b7, V7) if tag == "r7" else (b8, V8)
    return u8(os.path.join(LD, b["curtains"]["file"] if key == "default" else V[key]["file"]))


def shadow(tag, key):
    b, V = (b7, V7) if tag == "r7" else (b8, V8)
    s = u8(os.path.join(LD, b["curtains-shadow"]["file"] if key == "default" else V[key]["shadow"]))
    return s[..., :3].min(2) if s.ndim == 3 else s


def truth(tag, key):
    return u8(os.path.join(P2, f"graded/default-scene-{tag}-set-B-graded-v3c.png" if key == "default" else f"graded/variant-{tag}-{key}-set-B-graded-v3c.png"))[..., :3]


base = u8(os.path.join(LD, "base.png"))[..., :3]
fa = u8(os.path.join(P1, "fixed-furniture.png"))[..., 3]
res = {}

# ------------------------------------------------------------------ A. the true length
hem = {0.12: [px(-2.15, 2.95, 0.12), px(-2.15, 2.85, 0.12)], 0.22: [px(-2.15, 2.95, 0.22), px(-2.15, 2.85, 0.22)]}
con = [px(-2.15, 2.85, 0.45), px(-2.15, 2.65, 0.45)]
cm_px = float(np.linalg.norm(px(-2.15, 2.85, 0.12) - px(-2.15, 2.85, 0.22))) / 10.0


def yline(P, x):
    (x0, y0), (x1, y1) = P
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


def hem_cross(A, x, ylo, yhi):
    a = A[ylo:yhi, x].astype(np.float64) / 255
    idx = np.nonzero(a >= 0.5)[0]
    if not len(idx):
        return None
    i = int(idx.max())
    if i + 1 < len(a):
        t = (a[i] - 0.5) / max(a[i] - a[i + 1], 1e-6)
        return ylo + i + float(np.clip(t, 0, 1))
    return float(ylo + i)


res["lines_canvas_px"] = dict(hem_270=[[round(float(t), 1) for t in p] for p in hem[0.12]], hem_260=[[round(float(t), 1) for t in p] for p in hem[0.22]],
                              contact=[[round(float(t), 1) for t in p] for p in con], px_per_cm_at_hem=round(cm_px, 2))
geo = {}
H, W = base.shape[:2]
yy, xx = np.mgrid[0:H, 0:W]
for key, hz, sold in (("default", 0.12, 270), ("curtains-v2", 0.12, 270), ("curtains-v3", 0.22, 260)):
    L8 = layer("r8", key)
    A = L8[..., 3]
    dev = []
    for x in range(78, 128):
        yp = yline(hem[hz], x)
        yc = hem_cross(A, x, int(yp) - 40, int(yp) + 40)
        if yc is not None:
            dev.append(yc - yp)
    dev = np.array(dev)
    xs_ = np.arange(W)
    below = ((yy > np.where(xs_ <= 129, yline(hem[hz], xs_), np.inf)[None, :] + 3) & (xx <= 129)) | \
            ((yy > np.where((xs_ > 136) & (xs_ < 420), yline(con, xs_), np.inf)[None, :] + 3) & (xx > 136) & (xx < 420))
    ua7 = u8(os.path.join(P2, f"work-r7/layers/{WK[key]}.png"))[..., 3]
    ua8 = u8(os.path.join(P2, f"work-r8/layers/{WK[key]}.png"))[..., 3]
    A7 = layer("r7", key)[..., 3].astype(int)
    T = truth("r8", key).astype(np.int32)
    S = shadow("r8", key).astype(np.float64)
    exp_ = np.floor(base.astype(np.float64) * S[..., None] / 255 + 0.5).astype(np.int32)
    zone = below & (fa == 0)
    geo[key] = dict(sold_length_cm=sold, hem_z_m=hz, n=len(dev), median_cm=round(float(np.median(dev)) / cm_px, 2), max_abs_cm=round(float(np.abs(dev).max()) / cm_px, 2),
                    hem_height_above_floor_cm=round(100 * hz - float(np.median(dev)) / cm_px, 2), rule="+-1 cm",
                    alpha_gt0_below_lines_px=int(((A > 0) & below).sum()),
                    below_lines_truth_vs_base_x_shadow_max=int(np.abs(T - exp_).max(2)[zone].max()),
                    ungraded_alpha_r7_eq_r8=bool((ua7 == ua8).all()),
                    graded_alpha_changed_px=int((A7 != A.astype(int)).sum()), graded_alpha_max_change=int(np.abs(A7 - A.astype(int)).max()),
                    graded_alpha_changed_r7_values_max=int(A7[A7 != A.astype(int)].max()) if (A7 != A.astype(int)).any() else None)
    print("A", key, geo[key], flush=True)
res["true_length"] = geo


# ------------------------------------------------------------------ B. the bench
def Lmap(rgb8):
    return lab(rgb8)[..., 0]


bench = {}
for key in KEYS:
    rec = {}
    for tag in ("r7", "r8"):
        T = truth(tag, key)
        Lt = Lmap(T)
        S = shadow(tag, key).astype(np.float64) / 255
        # method 1: QA R6/R7 (r67_curtains.py), unchanged
        brk, abv, cols = [], [], []
        for x in range(200, 245):
            yp = yline(con, x)
            if fa[int(yp) - 20:int(yp) + 2, x].max() > 0:
                continue
            b0 = int(round(yp)) - 1
            brk.append(np.median(Lt[b0 - 5:b0, x]))
            abv.append(np.median(Lt[b0 - 15:b0 - 5, x]))
            cols.append(x)
        cmins = []
        for x in range(131, 245):
            yp = yline(con, x)
            if fa[int(yp) - 6:int(yp) + 8, x].max() > 0:
                continue
            cmins.append(float(S[int(yp):int(yp) + 6, x].min()))
        # method 2: the 4 rows just above the contact vs the cloth 12-20 rows up; the stone contact as seen (composite / base, linear Y)
        m2b, m2c = [], []
        Yt, Yb = Yof(T), Yof(base)
        for x in cols:
            yc = yline(con, x)
            yi = int(np.floor(yc))
            m2b.append(np.median(Lt[yi - 5:yi - 1, x]) - np.median(Lt[yi - 20:yi - 11, x]))
        for x in range(131, 245):
            yc = yline(con, x)
            if fa[int(yc) - 6:int(yc) + 8, x].max() > 0:
                continue
            yi = int(np.ceil(yc))
            r = Yt[yi:yi + 6, x] / np.maximum(Yb[yi:yi + 6, x], 1e-6)
            m2c.append(float(r.min()))
        # the hem band
        hz = 0.22 if key == "curtains-v3" else 0.12
        band, above = [], []
        for x in range(80, 126):
            yp = yline(hem[hz], x)
            b0 = int(round(yp)) - 3
            band.append(np.median(Lt[b0 - 15:b0, x]))
            above.append(np.median(Lt[b0 - 35:b0 - 15, x]))
        rec[tag] = dict(m1_break_dL=round(float(np.median(np.array(brk) - np.array(abv))), 2), m1_columns=len(brk),
                        m1_contact_multiply=round(float(np.median(cmins)), 4), m1_contact_columns=len(cmins),
                        m2_break_dL=round(float(np.median(m2b)), 2), m2_break_p10_p90=[round(float(np.percentile(m2b, q)), 2) for q in (10, 90)],
                        m2_contact_seen_Y_ratio=round(float(np.median(m2c)), 4), m2_contact_columns=len(m2c),
                        hem_band_dL=round(float(np.median(np.array(band) - np.array(above))), 2))
    bench[key] = rec
    print("B", key, rec, flush=True)
# the halo model's dark run (x 206-216, y 1188-1194) against the contact line
bench["dark_run_vs_contact_line"] = dict(contact_y_at_x206=round(float(yline(con, 206)), 1), contact_y_at_x216=round(float(yline(con, 216)), 1),
                                         run_rows=[1188, 1194],
                                         crosses=bool(1188 <= yline(con, 216) <= 1194 or 1188 <= yline(con, 206) <= 1194))
# the break's top edge: the step's sharpness (L* gradient across its top) against the cloth's own row-to-row texture
edge = {}
for key in KEYS:
    T = truth("r8", key)
    Lt = Lmap(T)
    g_top, g_cloth = [], []
    for x in range(200, 245):
        yp = yline(con, x)
        if fa[int(yp) - 20:int(yp) + 2, x].max() > 0:
            continue
        yi = int(np.floor(yp))
        prof = Lt[yi - 22:yi, x]
        d = np.diff(prof)
        g_top.append(float(np.abs(d[-11:-4]).max()))
        g_cloth.append(float(np.abs(d[:8]).max()))
    edge[key] = dict(top_edge_max_row_step_median=round(float(np.median(g_top)), 2), cloth_max_row_step_median=round(float(np.median(g_cloth)), 2))
bench["break_top_edge_vs_cloth_texture"] = edge
res["bench"] = bench


# ------------------------------------------------------------------ C. curtain 3 colour
def mask_of(A):
    m = cv2.erode((A == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    m[:100] = False
    m[1150:] = False
    return m


col = {}
for tag in ("r7", "r8"):
    same = np.ones((H, W), bool)
    for key in KEYS:
        same &= mask_of(layer(tag, key)[..., 3])
    col[tag] = {}
    for key in KEYS:
        T = truth(tag, key)
        Lb = lab(T[same])
        rec = dict(same_mask=summ(Lb))
        thr = np.percentile(Lb[:, 0], 25)
        rec["lit_fabric_L_above_p25"] = summ(Lb[Lb[:, 0] >= thr])
        fr = same.copy()
        fr[:, :78] = False
        rec["same_mask_in_frame_x_ge_78"] = summ(lab(T[fr]))
        rec["Y_median"] = round(float(np.median(Yof(T[same]))), 4)
        col[tag][key] = rec
    print("C", tag, {k: v["same_mask"] for k, v in col[tag].items()}, flush=True)
card = {k: hexlab(h) for k, h in (("linen", "#D9CDB8"), ("180502", "#EDE7DB"), ("light_beige", "#E6DDCE"))}
Ycard = {k: float(Yof(np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)]], np.uint8))[0]) for k, h in (("linen", "#D9CDB8"), ("180502", "#EDE7DB"), ("light_beige", "#E6DDCE"))}
ratio_card = Ycard["linen"] / Ycard["180502"]
Y180 = col["r8"]["default"]["Y_median"]
expL = float(lab(np.array([[255, 255, 255]], np.uint8))[0][0])  # 100
Lexp = 116 * np.cbrt(Y180 * ratio_card) - 16
v3 = col["r8"]["curtains-v3"]["same_mask"]
LOCK = dict(L=(71.5, 74.5), h=(81.0, 87.0), C=(10.5, 12.5))
res["curtain3_colour"] = dict(
    measured=col, cards={k: dict(L=round(float(v[0]), 2), C=round(float(np.hypot(v[1], v[2])), 2), h=round(float(np.degrees(np.arctan2(v[2], v[1])) % 360), 1))
                         for k, v in card.items()},
    card_ratio_Y_linen_over_180502=round(ratio_card, 4), expected_L_by_card_ratio=round(float(Lexp), 2),
    in_room_ratio_Y_v3_over_180502=round(col["r8"]["curtains-v3"]["Y_median"] / Y180, 4),
    designer_lock=LOCK,
    lock_check={k: dict(value=v3[k], range=LOCK[k], pass_=bool(LOCK[k][0] <= v3[k] <= LOCK[k][1])) for k in ("L", "h", "C")},
    r8_reported=dict(L=72.99, C=12.5, h=83.5))
print("C lock", res["curtain3_colour"]["lock_check"], "expected", res["curtain3_colour"]["expected_L_by_card_ratio"], flush=True)


# ------------------------------------------------------------------ D. specks
def med7(a, box):
    x0, y0, x1, y1 = box
    pad = np.pad(a[y0:y1, x0:x1], 3, mode="edge")
    return np.median(sliding_window_view(pad, (7, 7)), axis=(-2, -1))


def specks(rgb8, alpha, box):
    x0, y0, x1, y1 = box
    Lb = lab(rgb8[y0:y1, x0:x1])
    A_, B_ = Lb[..., 1], Lb[..., 2]
    C = np.hypot(A_, B_)
    h = np.degrees(np.arctan2(B_, A_)) % 360
    on = alpha[y0:y1, x0:x1] > 0
    lit = on & (h >= 150) & (h <= 230) & (C > 6)
    # the wide rule's median: a* rounded to integers as R8 does (uint8 a*+128), the 7 x 7 median by QA's own numpy
    ar = np.clip(np.round(A_ + 128), 0, 255)
    full = np.zeros(alpha.shape)
    full[y0:y1, x0:x1] = ar
    md = med7(full, box) - 128
    wide = on & (h >= 100) & (h <= 230) & (C > 6) & (A_ - md <= -8)
    return lit, wide, Lb


BOX = (0, 0, 300, 1460)
sp = {}
for tag in ("r7", "r8"):
    Lg = layer(tag, "curtains-v3")
    U = u8(os.path.join(P2, f"work-{tag}/layers/curtains-v3.png"))
    T = truth(tag, "curtains-v3")
    for name, rgb, al in (("graded_layer", Lg[..., :3], Lg[..., 3]), ("ungraded_source", U[..., :3], U[..., 3]), ("set_B_truth_in_alpha", T, Lg[..., 3])):
        lit, wide, _ = specks(rgb, al, BOX)
        sp[f"{tag} {name}"] = dict(literal=int(lit.sum()), wide=int(wide.sum()), literal_not_in_wide=int((lit & ~wide).sum()))
    # opaque only (alpha 255): the specks a viewer could see at full strength
    lit, wide, _ = specks(Lg[..., :3], (Lg[..., 3] == 255).astype(np.uint8), BOX)
    sp[f"{tag} graded_layer_alpha255"] = dict(literal=int(lit.sum()), wide=int(wide.sum()))
print("D", sp, flush=True)
# the speck step's invariants (ungraded R7 -> R8)
U7 = u8(os.path.join(P2, "work-r7/layers/curtains-v3.png"))
U8 = u8(os.path.join(P2, "work-r8/layers/curtains-v3.png"))
x0, y0, x1, y1 = BOX
on = (U7[y0:y1, x0:x1, 3] > 0)
l7 = lab(U7[y0:y1, x0:x1, :3])
l8 = lab(U8[y0:y1, x0:x1, :3])
dab = np.hypot(l8[..., 1] - l7[..., 1], l8[..., 2] - l7[..., 2])
_, wide7, _ = specks(U7[..., :3], U7[..., 3], BOX)
rmask = np.load(os.path.join(P2, "work-r8/curtain3-speck-mask.npy"), allow_pickle=False)
rmask = rmask[y0:y1, x0:x1] if rmask.shape == (H, W) else None
Y7 = Yof(U7[y0:y1, x0:x1, :3])
Y8 = Yof(U8[y0:y1, x0:x1, :3])
ratio = Y8 / np.maximum(Y7, 1e-6)
spk = rmask if rmask is not None else wide7
body = on & (U7[y0:y1, x0:x1, 3] == 255) & ~cv2.dilate(spk.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
body[1150:] = False                     # the fringe and the break are below
spk_body = spk & on
spk_body[1150:] = False
# a*b* change outside the specks: the 8-bit rounding of an L*-only scale moves a*b* a little; report the distribution and the big ones
outside = on & ~cv2.dilate(spk.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
res["curtain3_specks"] = dict(
    counts=sp, r8_mask_px=int(rmask.sum()) if rmask is not None else None, qa_wide_r7_ungraded_px=int(wide7.sum()),
    qa_wide_vs_r8_mask=dict(both=int((wide7 & spk).sum()), qa_only=int((wide7 & ~spk).sum()), r8_only=int((spk & ~wide7).sum())) if rmask is not None else None,
    speck_step=dict(
        dab_on_specks_median=round(float(np.median(dab[spk & on])), 2), dab_on_specks_max=round(float(dab[spk & on].max()), 2),
        dab_outside_specks_p99=round(float(np.percentile(dab[outside], 99)), 2), dab_outside_specks_p999=round(float(np.percentile(dab[outside], 99.9)), 2),
        dab_outside_specks_px_gt3=int((dab[outside] > 3).sum()), dab_outside_specks_px_gt5=int((dab[outside] > 5).sum()),
        dab_outside_gt3_rows=sorted(set((np.nonzero(outside & (dab > 3))[0] + y0).tolist()))[:12],
        Y_factor_cloth_median=round(float(np.median(ratio[body])), 4), Y_factor_cloth_p5_p95=[round(float(np.percentile(ratio[body], q)), 4) for q in (5, 95)],
        Y_factor_on_specks_median=round(float(np.median(ratio[spk_body])), 4), Y_factor_on_specks_p5_p95=[round(float(np.percentile(ratio[spk_body], q)), 4) for q in (5, 95)],
        dL_on_specks_vs_global_factor_max=round(float(np.abs(116 * np.cbrt(Y7[spk_body] * np.median(ratio[body])) - 16 - l8[..., 0][spk_body]).max()), 2),
        dL_on_cloth_vs_global_factor_p99=round(float(np.percentile(np.abs(116 * np.cbrt(Y7[body] * np.median(ratio[body])) - 16 - l8[..., 0][body]), 99)), 2)))
print("D step", res["curtain3_specks"], flush=True)
json.dump(res, open(os.path.join(OUT, "data/curtains.json"), "w"), indent=1, default=float)
