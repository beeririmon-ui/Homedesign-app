"""
qa-agent 2026-11-07: the pilot's three cushion sets against their SKU photos (view only, session scratchpad wm-pilot-refs/ and
chenille-colours/). Per item: the product's outline from cushion-polys.json on composite-set-<S>-v2-graded.png beside the SKU crop at
the same height; median Lab of the product (its outline eroded 6 px) and of the SKU crop's centre; each against a neutral in its own
picture (the composite: the sofa's griege boucle seat; the photo: its lightest 10 %, the white backdrop or sofa).
Writes data/cushions.json and overlays/cushions-set-<S>.jpg. Usage: ~/.venvs/motion/bin/python -I cushions.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")
REF = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-pilot-refs/"
POLYS = json.load(open(os.path.join(P, "cushion-polys.json")))
REFS = {
    "A": {"chenille": "A-cushions-cj-knitted-chenille-bean-green-21-camel-color-crop.png", "White": "A-cushions-cj-boucle-teddy-white-crop.png",
          "Milk Tea": "A-cushions-cj-boucle-teddy-milk-tea-color-crop.png", "Flax": "A-sofa-cover-cj-cotton-muslin-fringe-flax-brown-crop.png"},
    "B": {"corduroy Camel": "B-cushions-cj-wide-stripe-corduroy-light-green-camel-crop.png", "Oatmeal": "B-cushions-aliexpress-textured-boucle-throw-pillow-oatmeal-crop.png",
          "Beige": "B-cushions-cj-linen-look-charcoal-beige-crop.png", "Pecan": "B-sofa-cover-cj-cotton-muslin-fringe-pecan-crop.png"},
    "C": {"Light Brown": "C-cushions-cj-boucle-teddy-light-brown-crop.png", "Dark Coffee": "C-cushions-cj-corduroy-patchwork-dark-coffee-crop.png",
          "Light Beige Gray": "C-cushions-cj-linen-look-ivory-light-beige-gray-crop.png", "Clay": "C-sofa-cover-cj-cotton-muslin-fringe-clay-crop.png"},
}


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def med(px):
    m = np.median(lab(px.astype(float)), 0)
    return [round(float(v), 1) for v in m] + [round(float(np.hypot(m[1], m[2])), 1), round(float(np.degrees(np.arctan2(m[2], m[1]))), 1)]


out = {}
for S in ("A", "B", "C"):
    comp = Image.open(os.path.join(P, f"composite-set-{S}-v2-graded.png")).convert("RGB")
    arr = np.asarray(comp)
    ox, oy = POLYS[S]["origin"]
    seat = arr[1150:1190, 1700:1900].reshape(-1, 3)   # the sofa's griege boucle seat, the same in every set
    neutral = med(seat)
    tiles, res = [], {}
    for item, poly in POLYS[S].items():
        if item == "origin" or not isinstance(poly, list):
            continue
        pts = np.array([[ox + x, oy + y] for x, y in poly], np.int32)
        m = np.zeros(arr.shape[:2], np.uint8)
        cv2.fillPoly(m, [pts], 1)
        mi = cv2.erode(m, np.ones((13, 13), np.uint8)) > 0
        ks = [k for k in REFS[S] if k.lower() in item.lower()]
        key = max(ks, key=len) if ks else None
        rec = dict(frame=med(arr[mi]), sofa_seat_neutral=neutral)
        rec["frame_minus_neutral"] = [round(rec["frame"][i] - neutral[i], 1) for i in range(3)]
        x0, y0, w, h = cv2.boundingRect(pts)
        crop = comp.crop((x0, y0, x0 + w, y0 + h))
        if key:
            ref = Image.open(REF + REFS[S][key]).convert("RGB")
            ra = np.asarray(ref)
            cy, cx = ra.shape[0] // 2, ra.shape[1] // 2
            centre = ra[cy - ra.shape[0] // 6:cy + ra.shape[0] // 6, cx - ra.shape[1] // 6:cx + ra.shape[1] // 6].reshape(-1, 3)
            Ls = lab(ra.reshape(-1, 3).astype(float))[:, 0]
            light = ra.reshape(-1, 3)[Ls >= np.percentile(Ls, 90)]
            rec["sku_photo"] = REFS[S][key]
            rec["photo"] = med(centre)
            rec["photo_light10_neutral"] = med(light)
            rec["photo_minus_neutral"] = [round(rec["photo"][i] - rec["photo_light10_neutral"][i], 1) for i in range(3)]
            hh = 260
            tiles += [crop.resize((max(1, int(crop.width * hh / crop.height)), hh)), ref.resize((max(1, int(ref.width * hh / ref.height)), hh))]
        res[item] = rec
    out[S] = res
    if tiles:
        o = Image.new("RGB", (sum(t.width for t in tiles) + 12 * len(tiles), 260), (40, 40, 40))
        x = 0
        for i, t in enumerate(tiles):
            o.paste(t, (x, 0))
            x += t.width + (24 if i % 2 else 4)
        o.save(os.path.join(OUT, "overlays", f"cushions-set-{S}.jpg"), quality=88)
json.dump(out, open(os.path.join(OUT, "data", "cushions.json"), "w"), indent=1)
for S, r in out.items():
    for item, rec in r.items():
        print(S, item[:38].ljust(38), "frame", rec["frame"], "rel", rec["frame_minus_neutral"], "| photo", rec.get("photo"), "rel", rec.get("photo_minus_neutral"))
