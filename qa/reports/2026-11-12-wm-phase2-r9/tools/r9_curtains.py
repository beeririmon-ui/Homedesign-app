#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R9): curtain 3 (curtains-cj-japanese-linen-half-shade, Linen), QA R8 F1 and F2, and the colour lock by the
designer's recorded method (data/selections/living-room.warm-modern.json, curtains pick 3, colour_2026_11_12: lock, measurement,
precision). QA's own code; the Lab formulas are those of qa/reports/2026-11-12-wm-phase2-r8/tools/r8_curtains.py (numpy CIELAB D65),
OpenCV float Lab (R8's) as the cross-check.
  1. F1, the literal rule (h 150-230 deg, C* > 6) at alpha > 0 on the WHOLE graded layer (and inside R8's box x < 300, y < 1460), R8 and
     R9, both Labs; and on the set-B truth inside alpha > 0.
  2. What changed R8 -> R9 in the layer: RGB (which pixels; the same set as R8's literal hits in both Labs and as R9's mask file), alpha
     bytes, the shadow file (manifest-r9 against QA's R8 sha256 list); dL* on the changed pixels in both Labs; the new a*b* against the
     median a*b* of the radius-3 pixels that are neither flagged nor transparent (R8's method).
  3. The lock: the mask (alpha 255 eroded 5 x 5 in all three curtain layers of manifest-r9, their intersection, rows 100-1149), on the
     set-B variant truth of manifest-r9; L* = median L*; C*, h from the median a* and the median b*; each rounded half-up to 0.1 and
     compared with the lock, ends included. R8's truth by the same method for the delta.
  4. The wide rule (R8's detector: h 100-230, C* > 6, a* - median7(round a*) <= -8, alpha > 0) on R9: every hit with alpha < 128 (R9
     leaves 8, h 100-150, outside the designer's window) and with alpha >= 128; for each, how it shows in the scene: the set-B truth's
     pixel against the same scene with that layer pixel's a*b* set to its radius-3 neighbourhood median (L* kept), as CIEDE2000 and in
     8-bit levels; whether it lies in the camera frame (x >= 77.5).
  5. F2: the final-pass mask (work-r8/curtain3-speck-mask-final-pass.npy) against the speck mask (work-r8/curtain3-speck-mask.npy) and
     against R8 itself: on the ungraded sources work-r7 -> work-r8 curtains-v3, the a*b* change dab per pixel: inside each mask, and
     outside their union (only the L*-step's 8-bit rounding may move a*b* there); QA's R8 '37 px with dab > 3 outside the mask file'.
     The 'alpha_unchanged' correction of fix-r9.json: ungraded alpha and free-alpha files R7 == R8 (three curtains); graded alpha R7 -> R8
     changed px, max change, and whether any changed where the ungraded source alpha is not soft (0 < alpha < 255).
Writes data/curtains.json.     ~/.venvs/motion/bin/python3.12 -I r9_curtains.py
"""
import decimal
import hashlib
import json
import os

import cv2
import numpy as np
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
LD = os.path.join(P2, "layers")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r9")
SEL = os.path.join(REPO, "data/selections/living-room.warm-modern.json")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def u8(p):
    return np.asarray(Image.open(p))


M_ = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
WP = np.array([0.95047, 1.0, 1.08883])


def lab(c8):
    c = np.asarray(c8, np.float64) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = c @ M_.T / WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_cv(c8):
    c = np.asarray(c8, np.float32) / 255
    if c.ndim == 2:                                   # a list of pixels (n, 3)
        return cv2.cvtColor(c[None], cv2.COLOR_RGB2LAB)[0].astype(np.float64)
    return cv2.cvtColor(c, cv2.COLOR_RGB2LAB).astype(np.float64)


def de00(l1, l2):
    L1, a1, b1 = l1[..., 0], l1[..., 1], l1[..., 2]
    L2, a2, b2 = l2[..., 0], l2[..., 1], l2[..., 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dhp = h2p - h1p
    dhp = np.where(dhp > 180, dhp - 360, np.where(dhp < -180, dhp + 360, dhp))
    dhp = np.where(C1p * C2p == 0, 0, dhp)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    hbp = np.where(C1p * C2p == 0, hs, np.where(np.abs(h1p - h2p) > 180, np.where(hs < 360, hs + 360, hs - 360) / 2, hs / 2))
    T = 1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.2 * np.cos(np.radians(4 * hbp - 63))
    dTh = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dTh)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def ch(L):
    return np.hypot(L[..., 1], L[..., 2]), np.degrees(np.arctan2(L[..., 2], L[..., 1])) % 360


def literal(rgb, alpha, labf):
    L = labf(rgb)
    C, h = ch(L)
    return (alpha > 0) & (h >= 150) & (h <= 230) & (C > 6)


def med7(a):
    pad = np.pad(a, 3, mode="edge")
    return np.median(sliding_window_view(pad, (7, 7)), axis=(-2, -1))


BOX = (0, 0, 300, 1460)


def wide(rgb, alpha, labf=lab):
    x0, y0, x1, y1 = BOX
    L = labf(rgb[y0:y1, x0:x1])
    C, h = ch(L)
    ar = np.clip(np.round(L[..., 1] + 128), 0, 255)
    md = med7(ar) - 128
    w = np.zeros(alpha.shape, bool)
    w[y0:y1, x0:x1] = (alpha[y0:y1, x0:x1] > 0) & (h >= 100) & (h <= 230) & (C > 6) & (L[..., 1] - md <= -8)
    return w


def r1(v):
    return float(decimal.Decimal(repr(float(v))).quantize(decimal.Decimal("0.1"), rounding=decimal.ROUND_HALF_UP))


m8 = json.load(open(os.path.join(LD, "manifest-r8.json")))
m9 = json.load(open(os.path.join(LD, "manifest-r9.json")))
V8 = {v["id"]: v for vs in m8["variants"].values() for v in vs}
V9 = {v["id"]: v for vs in m9["variants"].values() for v in vs}
b9 = {l_["id"]: l_ for l_ in m9["layers"]}
G8, G9 = u8(os.path.join(LD, V8["curtains-v3"]["file"])), u8(os.path.join(LD, V9["curtains-v3"]["file"]))
T8 = u8(os.path.normpath(os.path.join(LD, V8["curtains-v3"]["truth"])))[..., :3]
T9 = u8(os.path.normpath(os.path.join(LD, V9["curtains-v3"]["truth"])))[..., :3]
a8, a9 = G8[..., 3], G9[..., 3]
H, W = a8.shape
res = {}

# ------------------------------------------------------------------ 1. F1, the literal rule
lit = {}
for tag, G, T in (("r8", G8, T8), ("r9", G9, T9)):
    for ln, f in (("qa_lab", lab), ("r8_opencv_lab", lab_cv)):
        m = literal(G[..., :3], G[..., 3], f)
        bx = np.zeros_like(m)
        bx[BOX[1]:BOX[3], BOX[0]:BOX[2]] = True
        lit[f"{tag} graded layer, {ln}"] = dict(whole_layer=int(m.sum()), in_r8_box=int((m & bx).sum()),
                                                alpha_range=[int(G[..., 3][m].min()), int(G[..., 3][m].max())] if m.any() else None)
        mt = literal(T, G[..., 3], f)
        lit[f"{tag} set-B truth inside alpha > 0, {ln}"] = int(mt.sum())
res["F1_literal"] = lit
print("F1", lit, flush=True)

# ------------------------------------------------------------------ 2. what changed
d = np.abs(G8[..., :3].astype(int) - G9[..., :3].astype(int)).max(2) > 0
hits8 = literal(G8[..., :3], a8, lab) | literal(G8[..., :3], a8, lab_cv)
mk9 = np.load(os.path.join(P2, "work-r9/curtain3-soft-edge-mask-r9.npy"))
ys, xs = np.nonzero(d)
L8q, L9q = lab(G8[..., :3][d]), lab(G9[..., :3][d])
L8c, L9c = lab_cv(G8[..., :3][d]), lab_cv(G9[..., :3][d])
# R8's method: the median a*b* of the radius-3 neighbours that are neither flagged nor transparent (in R8's OpenCV Lab, as fix_r8)
LCV = lab_cv(G8[..., :3])
nb = []
for y, x in zip(ys, xs):
    yy, xx = np.mgrid[max(0, y - 3):y + 4, max(0, x - 3):x + 4]
    ok = (np.hypot(yy - y, xx - x) <= 3) & (a8[yy, xx] > 0) & ~hits8[yy, xx]
    med = np.median(LCV[yy[ok], xx[ok]][:, 1:], axis=0)
    nb.append(med)
nb = np.array(nb)
ab_off = np.hypot(L9c[:, 1] - nb[:, 0], L9c[:, 2] - nb[:, 1])
_s9 = V9["curtains-v3"]["shadow"]
r8sh = {r["path"]: r["sha256_qa"] for r in json.load(open(os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r8/data/manifest.json")))["manifest_r8"]["rows"] if r.get("sha256_qa")}
res["changed"] = dict(
    rgb_changed_px=int(d.sum()), same_set_as_r8_literal_hits=bool((d == hits8).all()), same_set_as_r9_mask_file=bool((d == mk9).all()),
    r9_mask_file_px=int(mk9.sum()), alpha_bytes_identical=bool((a8 == a9).all()),
    shadow=dict(file=_s9, same_path_as_r8=_s9 == V8["curtains-v3"]["shadow"],
                sha_equals_qa_r8_list=sha(os.path.join(LD, _s9)) == r8sh.get(os.path.relpath(os.path.join(LD, _s9), REPO))),
    dL_qa_lab=dict(max_abs=round(float(np.abs(L9q[:, 0] - L8q[:, 0]).max()), 4)), dL_opencv_lab=dict(max_abs=round(float(np.abs(L9c[:, 0] - L8c[:, 0]).max()), 4)),
    new_ab_vs_neighbourhood_median=dict(max=round(float(ab_off.max()), 2), median=round(float(np.median(ab_off)), 2)),
    pixels=[dict(x=int(x), y=int(y), alpha=int(a8[y, x]), lab_r8=[round(float(v), 2) for v in L8q[i]], lab_r9=[round(float(v), 2) for v in L9q[i]],
                 hue_r9=round(float(np.degrees(np.arctan2(L9q[i, 2], L9q[i, 1])) % 360), 1), C_r9=round(float(np.hypot(L9q[i, 1], L9q[i, 2])), 2),
                 dL_qa=round(float(L9q[i, 0] - L8q[i, 0]), 4), scene_levels_max=int(np.abs(T9[y, x].astype(int) - T8[y, x].astype(int)).max()))
            for i, (y, x) in enumerate(zip(ys, xs))],
    in_camera_frame=int((xs >= 77.49).sum()))
res["changed"]["pass_"] = bool(res["changed"]["same_set_as_r8_literal_hits"] and res["changed"]["alpha_bytes_identical"] and res["changed"]["shadow"]["sha_equals_qa_r8_list"]
                               and res["changed"]["dL_qa_lab"]["max_abs"] <= 0.03 and res["changed"]["dL_opencv_lab"]["max_abs"] <= 0.03)
print("changed", {k: v for k, v in res["changed"].items() if k != "pixels"}, flush=True)

# ------------------------------------------------------------------ 3. the lock
sel = json.load(open(SEL))
pick = next(p for p in sel["slots"]["curtains"]["picks"] if "colour_2026_11_12" in p)
LOCK = pick["colour_2026_11_12"]["lock"]


def mask_of(A):
    m = cv2.erode((A == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    m[:100] = False
    m[1150:] = False
    return m


def lock_on(man, V, T):
    by = {l_["id"]: l_ for l_ in man["layers"]}
    same = mask_of(u8(os.path.join(LD, by["curtains"]["file"]))[..., 3]) & mask_of(u8(os.path.join(LD, V["curtains-v2"]["file"]))[..., 3]) & \
        mask_of(u8(os.path.join(LD, V["curtains-v3"]["file"]))[..., 3])
    out = {}
    for ln, f in (("qa", lab), ("opencv", lab_cv)):
        Lb = f(T[same])
        a, b = np.median(Lb[:, 1]), np.median(Lb[:, 2])
        v = dict(L=float(np.median(Lb[:, 0])), C=float(np.hypot(a, b)), h=float(np.degrees(np.arctan2(b, a)) % 360))
        out[ln] = dict(raw={k: round(x, 4) for k, x in v.items()}, rounded={k: r1(x) for k, x in v.items()},
                       pass_={k: bool(LOCK[k][0] <= r1(v[k]) <= LOCK[k][1]) for k in ("L", "C", "h")})
    out["mask_px"] = int(same.sum())
    return out


res["lock"] = dict(lock=LOCK, method=pick["colour_2026_11_12"]["measurement"], precision=pick["colour_2026_11_12"]["precision"],
                   r8=lock_on(m8, V8, T8), r9=lock_on(m9, V9, T9))
res["lock"]["pass_"] = all(res["lock"]["r9"]["qa"]["pass_"].values())
print("lock", json.dumps({k: res["lock"][k] for k in ("r8", "r9", "pass_")}), flush=True)

# ------------------------------------------------------------------ 4. the wide rule on R9: the soft-edge hits and the visible ones
w9 = wide(G9[..., :3], a9)
w8 = wide(G8[..., :3], a8)
w9cv = wide(G9[..., :3], a9, lab_cv)
w8cv = wide(G8[..., :3], a8, lab_cv)
hits = []
Lfull = lab(G9[..., :3])
for y, x in zip(*np.nonzero(w9 | w9cv)):
    yy, xx = np.mgrid[max(0, y - 3):y + 4, max(0, x - 3):x + 4]
    ok = (np.hypot(yy - y, xx - x) <= 3) & (a9[yy, xx] > 0) & ~(w9 | w9cv)[yy, xx]
    med_ab = np.median(Lfull[yy[ok], xx[ok]][:, 1:], axis=0)
    # the scene: out = below' + rgb * a; with the layer pixel's a*b* neutralised to the neighbourhood (L* kept), the scene changes by a * (rgb' - rgb)
    l0 = Lfull[y, x]
    l1 = np.array([l0[0], med_ab[0], med_ab[1]])
    rgb_new = np.clip(cv2.cvtColor(np.array([[[l1[0], l1[1], l1[2]]]], np.float32), cv2.COLOR_LAB2RGB)[0, 0] * 255, 0, 255)
    # (OpenCV's Lab<->RGB is close to QA's for this purpose: it only sizes the effect)
    al = a9[y, x] / 255
    t0 = T9[y, x].astype(float)
    t1 = np.clip(t0 + al * (rgb_new - G9[y, x, :3].astype(float)), 0, 255)
    C, h = ch(l0[None])
    tl = lab(T9[y, x][None].astype(np.uint8))[0]
    hits.append(dict(x=int(x), y=int(y), alpha=int(a9[y, x]), layer_lab=[round(float(v), 2) for v in l0], C=round(float(C[0]), 2), h=round(float(h[0]), 1),
                     qa_lab=bool(w9[y, x]), opencv_lab=bool(w9cv[y, x]), in_camera_frame=bool(x >= 77.49),
                     scene_lab=[round(float(v), 2) for v in tl], scene_h=round(float(np.degrees(np.arctan2(tl[2], tl[1])) % 360), 1),
                     scene_effect_levels=round(float(np.abs(t1 - t0).max()), 2), scene_effect_de00=round(float(de00(lab(t0[None].round().astype(np.uint8)), lab(t1[None].round().astype(np.uint8)))[0]), 2),
                     in_designer_window_h150_230=bool(150 <= h[0] <= 230)))
soft = [q for q in hits if q["alpha"] < 128]
vis = [q for q in hits if q["alpha"] >= 128]
res["wide_rule_r9"] = dict(
    counts=dict(r8_qa=dict(soft=int((w8 & (a8 < 128)).sum()), visible=int((w8 & (a8 >= 128)).sum())), r8_opencv=dict(soft=int((w8cv & (a8 < 128)).sum()), visible=int((w8cv & (a8 >= 128)).sum())),
                r9_qa=dict(soft=int((w9 & (a9 < 128)).sum()), visible=int((w9 & (a9 >= 128)).sum())), r9_opencv=dict(soft=int((w9cv & (a9 < 128)).sum()), visible=int((w9cv & (a9 >= 128)).sum()))),
    soft_edge=soft, visible_alpha_ge_128=vis,
    soft_edge_max_scene_effect=dict(levels=max([q["scene_effect_levels"] for q in soft], default=0), de00=max([q["scene_effect_de00"] for q in soft], default=0)))
print("wide", res["wide_rule_r9"]["counts"], res["wide_rule_r9"]["soft_edge_max_scene_effect"], flush=True)
for q in soft:
    print("   soft", q, flush=True)

# ------------------------------------------------------------------ 5. F2
U7 = u8(os.path.join(P2, "work-r7/layers/curtains-v3.png"))
U8 = u8(os.path.join(P2, "work-r8/layers/curtains-v3.png"))
spk = np.load(os.path.join(P2, "work-r8/curtain3-speck-mask.npy"))
fin = np.load(os.path.join(P2, "work-r8/curtain3-speck-mask-final-pass.npy"))
l7, l8 = lab(U7[..., :3]), lab(U8[..., :3])
dab = np.hypot(l8[..., 1] - l7[..., 1], l8[..., 2] - l7[..., 2])
on = U7[..., 3] > 0
uni = spk | fin
r8qa = json.load(open(os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r8/data/specks-detail.json")))["outside_mask_file"]["pixels"]
r8qa_set = {(p["x"], p["y"]) for p in r8qa}
fin_set = {(int(x), int(y)) for y, x in zip(*np.nonzero(fin))}
res["F2"] = dict(
    final_pass_px=int(fin.sum()), speck_px=int(spk.sum()), overlap=int((fin & spk).sum()), union=int(uni.sum()),
    dab_in_speck_mask=dict(min=round(float(dab[spk].min()), 2), median=round(float(np.median(dab[spk])), 2)),
    dab_in_final_pass=dict(min=round(float(dab[fin].min()), 2), median=round(float(np.median(dab[fin])), 2), max=round(float(dab[fin].max()), 2),
                           px_gt3=int((dab[fin] > 3).sum())),
    dab_outside_union=dict(max=round(float(dab[on & ~uni].max()), 2), p999=round(float(np.percentile(dab[on & ~uni], 99.9)), 2),
                           px_gt1=int((dab[on & ~uni] > 1).sum()), px_gt2=int((dab[on & ~uni] > 2).sum())),
    qa_r8_outside_mask_37_in_final_pass=len(r8qa_set & fin_set), qa_r8_outside_mask_37_total=len(r8qa_set),
    final_pass_px_not_in_qa_r8_37=sorted([list(p) for p in fin_set - r8qa_set]))
res["F2"]["final_pass_not_in_37_dab"] = [round(float(dab[y, x]), 2) for x, y in res["F2"]["final_pass_px_not_in_qa_r8_37"]]
print("F2", {k: v for k, v in res["F2"].items()}, flush=True)

au = {}
for nm, r7f, r8f in (("curtains (180502)", "curtains/curtains-aliexpress-linen-blend-s-fold-180502-r7.png", "curtains/curtains-aliexpress-linen-blend-s-fold-180502-r8.png"),
                     ("curtains-v2 (554205)", "curtains/curtains-aliexpress-beige-linen-sheer-curtains-554205-r7.png", "curtains/curtains-aliexpress-beige-linen-sheer-curtains-554205-r8.png"),
                     ("curtains-v3 (Linen)", "curtains/curtains-cj-japanese-linen-half-shade-r7.png", "curtains/curtains-cj-japanese-linen-half-shade-r8.png")):
    k = nm.split(" ")[0]
    s7, s8 = u8(os.path.join(P2, f"work-r7/layers/{k}.png"))[..., 3], u8(os.path.join(P2, f"work-r8/layers/{k}.png"))[..., 3]
    f7, f8 = u8(os.path.join(P2, f"work-r7/layers/{k}-free-alpha.png")), u8(os.path.join(P2, f"work-r8/layers/{k}-free-alpha.png"))
    g7, g8 = u8(os.path.join(LD, r7f))[..., 3].astype(int), u8(os.path.join(LD, r8f))[..., 3].astype(int)
    ch_ = g7 != g8
    au[nm] = dict(ungraded_alpha_same=bool((s7 == s8).all()), free_alpha_same=bool(np.array_equal(f7, f8)),
                  graded_alpha_changed_px=int(ch_.sum()), graded_alpha_max_change=int(np.abs(g7 - g8).max()),
                  changed_where_source_not_soft=int((ch_ & ~((s8 > 0) & (s8 < 255))).sum()))
res["alpha_unchanged_correction"] = dict(qa=au, r9_says={"curtains": [7, 15], "curtains-v2": [6, 20], "curtains-v3": [64, 12], "where_not_soft": 0})
print("alpha_unchanged", au, flush=True)
json.dump(res, open(os.path.join(OUT, "data/curtains.json"), "w"), indent=1)
print("written", flush=True)

# ------------------------------------------------------------------ follow-ups
# (a) the one pixel outside the speck masks whose a*b* moved > 3 between the ungraded R7 and R8 sources
outs = []
for y, x in zip(*np.nonzero(on & ~uni & (dab > 1))):
    outs.append(dict(x=int(x), y=int(y), alpha_r7=int(U7[y, x, 3]), alpha_r8=int(U8[y, x, 3]), rgb_r7=U7[y, x, :3].tolist(), rgb_r8=U8[y, x, :3].tolist(),
                     lab_r7=[round(float(v), 2) for v in l7[y, x]], lab_r8=[round(float(v), 2) for v in l8[y, x]], dab=round(float(dab[y, x]), 2),
                     in_qa_r8_37=(int(x), int(y)) in r8qa_set,
                     graded_r8_alpha=int(a8[y, x]), scene_levels_r8_vs_r7=None))
res["F2"]["outside_union_dab_gt1"] = outs
# (b) dL* of the 11 px: in both Labs; and whether an 8-bit value existed (within +-1 per channel of R9's) that keeps |dL*| <= 0.03 in BOTH Labs
#     and passes the literal rule in both
alt = []
for i, (y, x) in enumerate(zip(ys, xs)):
    base_rgb = G9[y, x, :3].astype(int)
    l8q, l8c = lab(G8[y, x, :3][None])[0], lab_cv(G8[y, x, :3][None])[0]
    best = None
    for dr_ in (-2, -1, 0, 1, 2):
        for dg in (-2, -1, 0, 1, 2):
            for db in (-2, -1, 0, 1, 2):
                c = np.clip(base_rgb + [dr_, dg, db], 0, 255).astype(np.uint8)
                q, cv_ = lab(c[None])[0], lab_cv(c[None])[0]
                okq = not ((150 <= np.degrees(np.arctan2(q[2], q[1])) % 360 <= 230) and np.hypot(q[1], q[2]) > 6)
                okc = not ((150 <= np.degrees(np.arctan2(cv_[2], cv_[1])) % 360 <= 230) and np.hypot(cv_[1], cv_[2]) > 6)
                e = max(abs(q[0] - l8q[0]), abs(cv_[0] - l8c[0]))
                if okq and okc and (best is None or e < best[0]):
                    best = (e, c.tolist())
    alt.append(dict(x=int(x), y=int(y), dL_qa=round(float(lab(G9[y, x, :3][None])[0][0] - l8q[0]), 4),
                    dL_opencv=round(float(lab_cv(G9[y, x, :3][None])[0][0] - l8c[0]), 4),
                    best_both_labs_within_pm2=round(float(best[0]), 4) if best else None))
res["changed"]["dL_per_pixel_and_alternative"] = alt
res["changed"]["dL_scene_effect_max_L"] = round(float(max(abs(q["dL_qa"]) * a8[q["y"], q["x"]] / 255 for q in alt)), 4)
print("outside union", outs, flush=True)
print("dL alt", alt, "scene", res["changed"]["dL_scene_effect_max_L"], flush=True)
json.dump(res, open(os.path.join(OUT, "data/curtains.json"), "w"), indent=1)
