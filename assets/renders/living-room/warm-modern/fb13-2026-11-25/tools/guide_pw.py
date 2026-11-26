#!/usr/bin/env python3
"""guide_pw.py: the seedream input of the plate P-W = the M0-W clay plate at v0 0.555 (clay_hw.py: the empty room with the sofa and
the armchair, the calm winter sun, no lamps), brought to the photograph's materials in code. Canvas 2720 x 1530. Scratch only."""
import json
import os

import cv2
import numpy as np
from PIL import Image

SP = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fb13-hero"
OUT = os.path.join(SP, "out")
FB13 = "/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25"
FB = (77.4852652259332, 43.427947598253276, 2642.5147347740667, 1486.5720524017468)

srgb2lin = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
lin2srgb = lambda a: np.where(a <= 0.0031308, a * 12.92, 1.055 * np.clip(a, 0, None) ** (1 / 2.4) - 0.055)
to_lab = lambda rgb: cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)
from_lab = lambda lab: np.clip(cv2.cvtColor(lab.astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)


def blur_masked(img, m, sigma):
    num = cv2.GaussianBlur(img * m[..., None] if img.ndim == 3 else img * m, (0, 0), sigma)
    den = cv2.GaussianBlur(m, (0, 0), sigma)
    return num / np.maximum(den[..., None] if img.ndim == 3 else den, 1e-4), den


def shifted_map(path, W, H, scale):
    a = np.asarray(Image.open(path)).astype(np.float32) / scale
    a = cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)
    dy = 0.035 * (FB[3] - FB[1]) * H / 1530.0
    return cv2.warpAffine(a, np.float32([[1, 0, 0], [0, 1, dy]]), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def chroma(img, m, ka, kb, dL=0.0, a0=None, b0=None):
    lab = to_lab(img)
    if a0 is not None:
        ma, mb_ = float(np.median(lab[..., 1][m])), float(np.median(lab[..., 2][m]))
        lab[..., 1] = np.where(m, a0 + ka * (lab[..., 1] - ma), lab[..., 1])
        lab[..., 2] = np.where(m, b0 + kb * (lab[..., 2] - mb_), lab[..., 2])
    else:
        lab[..., 1] = np.where(m, lab[..., 1] * ka, lab[..., 1])
        lab[..., 2] = np.where(m, lab[..., 2] * kb, lab[..., 2])
    lab[..., 0] = np.where(m, lab[..., 0] + dL, lab[..., 0])
    return from_lab(lab)


SUN_WARM = (1.2, 8.5)                                    # a*, b* added in full sun: Lab about (90, 2, 13), a warm white-gold
EXPO = dict(xs=[0, 40, 69.9, 85.0, 94.5, 100], ys=[0, 44.5, 76.5, 90.0, 95.5, 100])   # the plate's shade to L 76.5, its sun to 90


def materials(img, idx, log=None, key="", sunmap=None, expo=True):
    """the clay's neutral shell -> the photograph's materials (the same code for the plate and for the full clay)"""
    H, W = idx.shape
    wall = np.isin(idx, [5, 6, 521, 522, 14])
    L = to_lab(img)[..., 0]
    back = idx == 5
    # the shaded plaster of the back wall: the mode of its L (the sun patch and the sconce pools are the minority)
    Lb = L[back]
    sh_L = float(np.percentile(Lb, 30))
    shade = back & (np.abs(L - sh_L) < 3.0)
    med = np.median(img[shade], axis=0)
    tgt = from_lab(np.float32([[[float(np.median(L[shade])), 1.6, 7.5]]]))[0, 0]         # bone plaster in open shade
    wb = srgb2lin(tgt) / srgb2lin(med)
    img = np.clip(lin2srgb(srgb2lin(img) * wb), 0, 1).astype(np.float32)
    # the sun: warm white-gold, not orange (the owner, 2026-11-26). After the balance the clay's sun is cooler than the shade, so the
    # warmth is put back by the amount of sun: on the plaster from its own luminance over the shade, on the sofa from the clay's sun map
    lab = to_lab(img)
    L_sh = float(np.median(lab[..., 0][shade]))
    sunny = wall & (lab[..., 0] > L_sh + 5.0)
    if log is not None and sunny.any():
        log[key + "sun_plaster_Lab_before"] = [round(float(v), 2) for v in np.median(lab[sunny], axis=0)]
    t = np.clip((lab[..., 0] - L_sh - 2.0) / 10.0, 0, 1) * wall
    if sunmap is not None:
        t = np.maximum(t, np.clip(sunmap / 0.6, 0, 1) * (idx == 1))
    t = cv2.GaussianBlur(t.astype(np.float32), (0, 0), 1.5)
    lab[..., 1] += SUN_WARM[0] * t
    lab[..., 2] += SUN_WARM[1] * t
    img = from_lab(lab)
    # the smoked-oak floor: a quiet brown
    img = chroma(img, idx == 8, 0.55, 0.62, dL=-7.0)
    # the sofa: greige boucle, its clay facets smoothed
    sofa = idx == 1
    img = chroma(img, sofa, 0.5, 0.5, dL=-6.5, a0=2.5, b0=11.0)
    sm, _ = blur_masked(img, sofa.astype(np.float32), 4.0)
    soft_m = cv2.GaussianBlur(sofa.astype(np.float32), (0, 0), 1.0)[..., None]
    img = img * (1 - soft_m) + sm * soft_m
    rs = np.random.RandomState(1126)
    grain = cv2.GaussianBlur(rs.randn(H, W).astype(np.float32), (0, 0), 1.1) * 0.035
    img = np.clip(img + grain[..., None] * cv2.GaussianBlur(sofa.astype(np.float32), (0, 0), 1.0)[..., None], 0, 1)
    # outside the glazing: a pale, milky winter sky and a soft back-lit garden (no orange, no deep blue)
    outside = ((idx == 0) | ((idx >= 700) & (idx < 800))) & (np.arange(W)[None, :] < 0.2 * W)
    om = cv2.GaussianBlur(outside.astype(np.float32), (0, 0), 1.0)[..., None]
    lab = to_lab(img)
    lab[..., 1] = lab[..., 1] * 0.5 + 0.8
    lab[..., 2] = lab[..., 2] * 0.5 + 4.0
    lab[..., 0] = 100 - (100 - lab[..., 0]) * 0.85
    pale = from_lab(lab)
    img = (img * (1 - om) + pale * om).astype(np.float32)
    if expo:
        lab = to_lab(img)
        lab[..., 0] = np.interp(lab[..., 0], EXPO["xs"], EXPO["ys"])
        img = from_lab(lab).astype(np.float32)
    if log is not None:
        lab = to_lab(img)
        log[key + "wb_gains"] = [round(float(v), 4) for v in wb]
        log[key + "shade_plaster_Lab"] = [round(float(v), 2) for v in np.median(lab[shade], axis=0)]
        if sunny.any():
            log[key + "sun_plaster_Lab"] = [round(float(v), 2) for v in np.median(lab[sunny], axis=0)]
            log[key + "sun_plaster_L_p90"] = round(float(np.percentile(lab[..., 0][sunny], 90)), 2)
        log[key + "L_p0.5"] = round(float(np.percentile(lab[..., 0], 0.5)), 2)
    return img


def main():
    plate = np.asarray(Image.open(os.path.join(OUT, "clay-B-plate.png")).convert("RGB")).astype(np.float32) / 255.0
    idx_p = np.load(os.path.join(OUT, "passes-plate.npz"))["idx"]
    log = {}
    sun = shifted_map(os.path.join(FB13, "m0w-sun.png"), plate.shape[1], plate.shape[0], 255.0)
    g = materials(plate, idx_p, log, "plate_", sunmap=sun)
    Image.fromarray(np.rint(g * 255).astype(np.uint8)).save(os.path.join(OUT, "pw-input.png"), optimize=True)
    Image.fromarray(np.rint(g * 255).astype(np.uint8)).resize((1360, 765), Image.LANCZOS).save(os.path.join(OUT, "pw-input-small.jpg"), quality=90)
    json.dump(log, open(os.path.join(OUT, "pw-input.json"), "w"), indent=1)
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
