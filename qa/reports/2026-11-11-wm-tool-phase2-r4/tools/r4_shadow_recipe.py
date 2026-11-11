#!/usr/bin/env python3
"""
qa-agent 2026-11-11: render-agent's report of a shadow-recipe bug: extract.shadow_one measures the contact shadow as a ratio of LINEAR-light
luminances (pilot_wm.lum = s2l(rgb) . Rec.709), and the stack applies that ratio as a multiply on sRGB-ENCODED values (stack.compose,
the manifest's formula, the site's mix-blend multiply). In linear light an encoded multiply by s is about s^2.4, so the shadow comes out
deeper than the render drew it. QA's questions: is it real, how big is it on the display, and where?

  A. The size, per layer, on the r4 display (set B; the cushions on A/B/C): B = QA's recomposite of the r4 stack WITHOUT that product
     (graded, 8-bit), s = the product's shadow file / 255; shown = B . s (what the site does), meant = l2s(s2l(B) . s) (the same ratio in
     linear light, what the recipe measured). dL* = L*(shown) - L*(meant), only where that shadow is visible in the final scene (no layer
     above it, not under the product). Reported: px, p50 / p95 / max of |dL*|, px over 2 and over 5 L*, and the same within 4 px of the
     product. The fixed furniture's shadow of phase 1 (baked into the approved base.png): shell-v3 . S against l2s(s2l(shell-v3) . S),
     outside the furniture (the phase-1 recipe has the same form: furn_input's LUT is a linear luminance ratio, applied encoded).
  B. A check against the renders: for products whose raw render is on disk, the r3 scene (shadow_one as is) and the raw render
     (registered here with the pass's recorded matrix, the residual shift re-measured on the crop, gain-matched per channel on a ring
     12-60 px beyond the shadow, outside every product) in that product's visible shadow (s < 0.97): median L*(scene) - L*(raw), against
     the median predicted dL*. If the recipe over-darkens, scene - raw is negative, near the prediction.
Writes data/shadow-recipe.json.   ~/.venvs/motion/bin/python -I r4_shadow_recipe.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r4")
LD = os.path.join(P2, "layers")


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def l2s(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def Lstar01(rgb01):
    return cv2.cvtColor(np.clip(rgb01, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)[..., 0]


def u8(p):
    return np.asarray(Image.open(p))


def stats(d, m):
    v = np.abs(d[m])
    if not v.size:
        return None
    return dict(px=int(v.size), p50=round(float(np.median(v)), 2), p95=round(float(np.percentile(v, 95)), 2), max=round(float(v.max()), 2),
                px_over_2=int((v > 2).sum()), px_over_5=int((v > 5).sum()), sign_shown_minus_meant_median=round(float(np.median(d[m])), 2))


def run(tag):
    man = json.load(open(os.path.join(LD, f"manifest-{tag}.json")))
    byid = {l_["id"]: l_ for l_ in man["layers"]}
    order = man["compose"]["order"]
    products = [i for i in order if i != "base" and not i.endswith("-shadow")]
    base = u8(os.path.join(LD, "base.png"))[..., :3].astype(np.float32)
    lay, shd = {}, {}
    for pid in products:
        if pid == "cushions":
            continue
        lay[pid] = u8(os.path.join(LD, byid[pid]["file"]))
        shd[pid] = u8(os.path.join(LD, byid[pid + "-shadow"]["file"]))[..., :3]
    for s in "ABC":
        lay["set-" + s] = u8(os.path.join(LD, man["slot_cushions"]["sets"][s]["layer"]))
        shd["set-" + s] = u8(os.path.join(LD, man["slot_cushions"]["sets"][s]["shadow"]))[..., :3]

    def below_of(s, upto):
        out = base.copy()
        for pid in products:
            if pid == upto:
                break
            k = "set-" + s if pid == "cushions" else pid
            rgb = lay[k][..., :3].astype(np.float32)
            a = lay[k][..., 3:4].astype(np.float32) / 255.0
            out = np.clip(np.floor(out * shd[k].astype(np.float32) / 255.0 * (1 - a) + rgb * a + 0.5), 0, 255)
        return out
    return man, products, lay, shd, below_of


res = {"A_display_size": {}}
man, products, lay, shd, below_of = run("r4")
for s in ("B", "A", "C"):
    for pid in products:
        if s != "B" and pid != "cushions":
            continue
        k = "set-" + s if pid == "cushions" else pid
        sh = shd[k].astype(np.float32) / 255.0
        a = lay[k][..., 3].astype(np.float32) / 255.0
        vis = (sh.min(2) < 0.995) & (a == 0)
        idx = products.index(pid)
        for up in products[idx + 1:]:
            ku = "set-" + s if up == "cushions" else up
            vis &= lay[ku][..., 3] == 0
        if not vis.any():
            res["A_display_size"][f"{pid} [set {s}]"] = dict(px=0, note="no visible shadow")
            continue
        B = below_of(s, pid) / 255.0
        shown = B * sh
        meant = l2s(s2l(B) * sh)
        d = Lstar01(shown) - Lstar01(meant)
        dist = cv2.distanceTransform((a == 0).astype(np.uint8), cv2.DIST_L2, 5)
        rec = dict(all=stats(d, vis), within_4px=stats(d, vis & (dist <= 4)),
                   shadow_min=round(float(sh.min()), 3), shadow_p5_in_visible=round(float(np.percentile(sh.min(2)[vis], 5)), 3))
        res["A_display_size"][f"{pid} [set {s}]"] = rec
        print(pid, s, rec)

# the fixed furniture's shadow, phase 1 (approved base)
shell = u8(os.path.join(P1, "shell-v3.png"))[..., :3].astype(np.float32) / 255
S = u8(os.path.join(P1, "fixed-furniture-shadow.png"))
S = (S[..., 0] if S.ndim == 3 else S).astype(np.float32) / 255
fa = u8(os.path.join(P1, "fixed-furniture.png"))[..., 3]
vis = (S < 0.995) & (fa == 0)
d = Lstar01(shell * S[..., None]) - Lstar01(l2s(s2l(shell) * S[..., None]))
res["A_display_size"]["fixed furniture (phase 1, in base.png)"] = dict(all=stats(d, vis), shadow_min=round(float(S.min()), 3),
                                                                        note="ungraded shell; the grade is near identity above L* 25")
print("furniture", res["A_display_size"]["fixed furniture (phase 1, in base.png)"])

# B. against the raw renders (r3 scene: shadow_one as is)
J = {}
for f in ("jobs.json", "jobs-reserve.json", "jobs-r3.json"):
    J.update({j["id"]: j for j in json.load(open(os.path.join(P2, f)))["jobs"]})
CHECK = {"basket": "wm-ph2-fix-r3a-planter-basket", "planter": "wm-ph2-fix-r3a-planter-basket", "magazine-holder": "wm-ph2-reserve-r1-window-floor",
         "bowl": "wm-ph2-reserve-r2-table-ceiling", "rug": "wm-ph2-step1-rug", "candle-holders": "wm-ph2-step3-wall-table",
         "framed-art": "wm-ph2-step3-wall-table", "curtains": "wm-ph2-reserve-r1-window-floor"}
man3, products3, lay3, shd3, below3 = run("r3")
S3 = u8(os.path.join(P2, "graded/default-scene-r3-set-B-graded-v3c.png"))[..., :3].astype(np.float32)
allprod = np.zeros(S3.shape[:2], bool)
for k, v in lay3.items():
    if not k.startswith("set-") or k == "set-B":
        allprod |= v[..., 3] > 0
H, W = allprod.shape
res["B_against_raw"] = {}
for pid, jid in CHECK.items():
    j = J[jid]
    raw = u8(os.path.join(REPO, j["raw"]))[..., :3].astype(np.float32)
    reg = cv2.warpAffine(raw, np.array(j["register_to_input"], np.float32), (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                         borderMode=cv2.BORDER_REFLECT)
    sh = shd3[pid].astype(np.float32).min(2) / 255
    a = lay3[pid][..., 3]
    vis = (sh < 0.97) & ~allprod
    if vis.sum() < 30:
        res["B_against_raw"][pid] = dict(px=int(vis.sum()), note="too few visible shadow px")
        continue
    ys, xs = np.nonzero(vis)
    pad = 70
    X0, Y0, X1, Y1 = max(0, xs.min() - pad), max(0, ys.min() - pad), min(W, xs.max() + pad), min(H, ys.max() + pad)
    g1 = cv2.cvtColor(S3[Y0:Y1, X0:X1], cv2.COLOR_RGB2GRAY)
    g2 = cv2.cvtColor(reg[Y0:Y1, X0:X1], cv2.COLOR_RGB2GRAY)
    hp = lambda x: x - cv2.GaussianBlur(x, (0, 0), 3)  # noqa: E731
    bg = (~allprod[Y0:Y1, X0:X1]).astype(np.float32)
    win = cv2.createHanningWindow((X1 - X0, Y1 - Y0), cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(hp(g1) * bg, hp(g2) * bg, win)
    reg2 = cv2.warpAffine(reg, np.float32([[1, 0, -dx], [0, 1, -dy]]), (W, H), flags=cv2.INTER_LINEAR)
    shadowish = cv2.dilate((sh < 0.995).astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
    ring = (cv2.dilate((sh < 0.995).astype(np.uint8), np.ones((121, 121), np.uint8)) > 0) & ~shadowish & ~allprod
    if ring.sum() < 200:
        ring = ~shadowish & ~allprod
        ring[:Y0], ring[Y1:], ring[:, :X0], ring[:, X1:] = False, False, False, False
    gain = np.array([np.median(S3[..., c][ring]) / max(np.median(reg2[..., c][ring]), 1) for c in range(3)], np.float32)
    rr = np.clip(reg2 * gain, 0, 255) / 255
    Ls, Lr = Lstar01(S3 / 255), Lstar01(rr)
    B = below3("B", pid) / 255.0
    meant = l2s(s2l(B) * sh[..., None])
    Lm = Lstar01(meant)
    dist = cv2.distanceTransform((a == 0).astype(np.uint8), cv2.DIST_L2, 5)
    near = vis & (dist <= 6)
    rec = dict(raw=j["raw"].split("/")[-1], residual_shift_px=[round(float(dx), 2), round(float(dy), 2)], response=round(float(resp), 3),
               ring_px=int(ring.sum()), ring_check_median_dL=round(float(np.median((Ls - Lr)[ring])), 2), shadow_px=int(vis.sum()),
               scene_minus_raw_median=round(float(np.median((Ls - Lr)[vis])), 2), predicted_shown_minus_meant_median=round(float(np.median((Ls - Lm)[vis])), 2),
               meant_minus_raw_median=round(float(np.median((Lm - Lr)[vis])), 2))
    if near.sum() >= 20:
        rec.update(near6_px=int(near.sum()), near6_scene_minus_raw_median=round(float(np.median((Ls - Lr)[near])), 2),
                   near6_predicted_median=round(float(np.median((Ls - Lm)[near])), 2), near6_meant_minus_raw_median=round(float(np.median((Lm - Lr)[near])), 2))
    res["B_against_raw"][pid] = rec
    print("raw", pid, rec)
json.dump(res, open(os.path.join(OUT, "data/shadow-recipe.json"), "w"), indent=1)
