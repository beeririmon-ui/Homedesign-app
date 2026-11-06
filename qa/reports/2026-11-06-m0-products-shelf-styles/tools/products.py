"""
qa-agent 2026-11-06: the products pass laid in code on the locked seedream base (m0_products_pass.py lay).
(1) nothing else moved: |products-fix - base| per region (raw, canvas), with the product zones (box +-15 % and the agent's rendered
    extents) and the lamp's light zone out; a difference map (overlays/products-diff.jpg);
(2) each product's drawn extent from the changed pixels (|delta| > 12 levels, the largest components in the product's zone),
    against its box (slots 1.8 / house plan 1.2.5, canvas uv) and the card;
(3) box overlays and 100 % / 200 % crops of each product on the graded v6 (G1.12 at the lay-back seams);
(4) the lamp: the shade against the wall left of it, and the light the lay added (products-fix / base) on the sofa's right end.
Writes data/products.json, overlays/products-*.jpg. Usage: ~/.venvs/motion/bin/python -I products.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-06-m0-products-shelf-styles")
V9 = os.path.join(REPO, "assets/renders/living-room/nordic/v9")
BASE, FIX, GR = f"{V9}/m0-1-2-shell-seedream-fix.png", f"{V9}/m0-1-2-products-fix.png", f"{V9}/m0-1-2-products-graded-fix-v6.png"
GR_BASE = f"{V9}/m0-1-2-shell-seedream-graded-fix-v5.png"
W, H = 2736, 1539
BOX = {"magazine-holder": [0.335, 0.421, 0.848, 1.0], "basket": [0.35, 0.401, 0.686, 0.822], "pouf": [0.905, 1.0, 0.956, 1.0],
       "floor-lamp": [0.885, 0.949, 0.389, 0.881], "table-runner": [0.472, 0.593, 0.78, 0.9]}
ZONE = {"magazine-holder": [0.27, 0.45, 0.80, 1.0], "basket": [0.33, 0.42, 0.66, 0.84], "pouf": [0.87, 1.0, 0.92, 1.0],
        "floor-lamp": [0.85, 0.99, 0.34, 0.94], "table-runner": [0.46, 0.63, 0.75, 1.0]}
REG = {"walls left of the art (u 0.38-0.55, v 0.10-0.45)": [0.38, 0.55, 0.10, 0.45], "triptych (u 0.55-0.80, v 0.33-0.53)": [0.55, 0.80, 0.33, 0.53],
       "sofa and cushions (u 0.47-0.80, v 0.58-0.78)": [0.47, 0.80, 0.58, 0.78], "window (u 0.10-0.26, v 0.06-0.58)": [0.10, 0.26, 0.06, 0.58],
       "armchair (u 0.03-0.31, v 0.70-0.97)": [0.03, 0.31, 0.70, 0.97], "rug left of the runner (u 0.35-0.46, v 0.86-0.98)": [0.35, 0.46, 0.86, 0.98],
       "rug right of the runner (u 0.63-0.85, v 0.88-0.98)": [0.63, 0.85, 0.88, 0.98], "coffee table top right of the runner (u 0.60-0.75, v 0.78-0.86)": [0.60, 0.75, 0.78, 0.86],
       "ceiling (u 0.40-0.90, v 0.00-0.08)": [0.40, 0.90, 0.0, 0.08]}


def px(b):
    return int(b[0] * W), int(b[1] * W), int(b[2] * H), int(b[3] * H)


if __name__ == "__main__":
    a = np.asarray(Image.open(BASE).convert("RGB")).astype(np.float32)
    b = np.asarray(Image.open(FIX).convert("RGB")).astype(np.float32)
    d = np.abs(b - a)
    dm = d.mean(2)
    out = {"regions_mean_abs_delta": {}}
    for n, r in REG.items():
        x0, x1, y0, y1 = px(r)
        out["regions_mean_abs_delta"][n] = round(float(dm[y0:y1, x0:x1].mean()), 2)
    excl = np.zeros((H, W), bool)
    for n, z in ZONE.items():
        x0, x1, y0, y1 = px(z)
        excl[y0:y1, x0:x1] = True
    lampzone = np.zeros((H, W), bool)
    x0, x1, y0, y1 = px([0.78, 1.0, 0.25, 0.92])
    lampzone[y0:y1, x0:x1] = True
    fr = np.zeros((H, W), bool)
    fr[44:1495, 78:2658] = True
    m1 = fr & ~excl
    m2 = fr & ~excl & ~lampzone
    out["outside_product_zones"] = dict(mean_per_channel=[round(float(d[..., c][m1].mean()), 2) for c in range(3)],
                                        without_lamp_light_zone=[round(float(d[..., c][m2].mean()), 2) for c in range(3)],
                                        share_over_6_levels_without_lamp_zone=round(float((dm[m2] > 6).mean()), 4),
                                        p99_without_lamp_zone=round(float(np.percentile(dm[m2], 99)), 1))
    # where outside the zones the delta is > 6: the largest components
    big = ((dm > 6) & m2).astype(np.uint8)
    big = cv2.morphologyEx(big, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(big)
    comps = sorted([(int(st[i, 4]), [round(st[i, 0] / W, 3), round((st[i, 0] + st[i, 2]) / W, 3), round(st[i, 1] / H, 3), round((st[i, 1] + st[i, 3]) / H, 3)])
                    for i in range(1, n)], reverse=True)[:8]
    out["outside_changed_components_px_box"] = comps
    vis = np.clip(dm * 6, 0, 255).astype(np.uint8)
    vis = cv2.applyColorMap(vis, cv2.COLORMAP_INFERNO)
    for nm, z in BOX.items():
        x0, x1, y0, y1 = px(z)
        cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 255, 0), 3)
    cv2.imwrite(os.path.join(OUT, "overlays", "products-diff.jpg"), cv2.resize(vis, (W // 2, H // 2)), [cv2.IMWRITE_JPEG_QUALITY, 85])
    # each product's drawn extent: changed pixels in its zone
    ext = {}
    for nm, z in ZONE.items():
        x0, x1, y0, y1 = px(z)
        mk = (dm[y0:y1, x0:x1] > 12).astype(np.uint8)
        mk = cv2.morphologyEx(mk, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        mk = cv2.morphologyEx(mk, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(mk)
        if n <= 1:
            ext[nm] = None
            continue
        keep = [i for i in range(1, n) if st[i, 4] >= 0.08 * st[1:, 4].max()]
        xs0 = min(st[i, 0] for i in keep); xs1 = max(st[i, 0] + st[i, 2] for i in keep)
        ys0 = min(st[i, 1] for i in keep); ys1 = max(st[i, 1] + st[i, 3] for i in keep)
        e = [round((x0 + xs0) / W, 4), round((x0 + xs1) / W, 4), round((y0 + ys0) / H, 4), round((y0 + ys1) / H, 4)]
        bx = BOX[nm]
        ext[nm] = dict(changed_extent_uv=e, box_uv=bx, width_ratio=round((e[1] - e[0]) / (bx[1] - bx[0]), 2), height_ratio=round((e[3] - e[2]) / (bx[3] - bx[2]), 2),
                       note="changed pixels include the product's contact shadow and what it uncovered / covered: an upper bound")
    out["changed_extents"] = ext
    # overlays with the boxes on the graded v6, 100 % crops per product
    g = Image.open(GR).convert("RGB")
    gb = Image.open(GR_BASE).convert("RGB")
    dr = ImageDraw.Draw(g)
    for nm, z in BOX.items():
        x0, x1, y0, y1 = px(z)
        dr.rectangle([x0, y0, x1, y1], outline=(0, 255, 0), width=3)
        dr.text((x0 + 4, y0 + 4), nm, fill=(0, 255, 0))
        if ext.get(nm):
            e = ext[nm]["changed_extent_uv"]
            dr.rectangle([int(e[0] * W), int(e[2] * H), int(e[1] * W), int(e[3] * H)], outline=(255, 0, 255), width=2)
    g.resize((W // 2, H // 2)).save(os.path.join(OUT, "overlays", "products-boxes.jpg"), quality=85)
    g2 = Image.open(GR).convert("RGB")
    for nm, z in ZONE.items():
        x0, x1, y0, y1 = px(z)
        pad = 30
        box = (max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad))
        c1, c2 = gb.crop(box), g2.crop(box)
        im = Image.new("RGB", (c1.width * 2 + 10, c1.height), (40, 40, 40))
        im.paste(c1, (0, 0)); im.paste(c2, (c1.width + 10, 0))
        im.save(os.path.join(OUT, "overlays", f"g112-products-{nm}.jpg"), quality=90)
    # the lamp: shade vs the wall left of it; light added on the sofa's right end (fix / base in linear light)
    gg = np.asarray(Image.open(GR).convert("RGB")).astype(np.float32) / 255

    def L(p):
        return float((p.max(-1) + p.min(-1)).mean() / 2 * 100)
    lamp = dict(shade_L=None)
    x0, x1, y0, y1 = px([0.895, 0.94, 0.40, 0.47])
    lamp["shade_L_graded"] = round(L(gg[y0:y1, x0:x1]), 1)
    x0, x1, y0, y1 = px([0.84, 0.875, 0.40, 0.47])
    lamp["wall_left_L_graded"] = round(L(gg[y0:y1, x0:x1]), 1)
    lin = lambda x: np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)  # noqa: E731
    for nm, z in {"sofa right end + throw (u 0.78-0.86, v 0.60-0.75)": [0.78, 0.86, 0.60, 0.75], "wall right of the triptych (u 0.82-0.88, v 0.30-0.45)": [0.82, 0.88, 0.30, 0.45],
                  "floor / rug under the lamp (u 0.86-0.95, v 0.86-0.93)": [0.86, 0.95, 0.86, 0.93]}.items():
        x0, x1, y0, y1 = px(z)
        r = lin(b[y0:y1, x0:x1] / 255).mean() / max(lin(a[y0:y1, x0:x1] / 255).mean(), 1e-6)
        lamp[f"light added (fix / base, linear): {nm}"] = round(float(np.log2(r)), 3)
    out["lamp"] = lamp
    json.dump(out, open(os.path.join(OUT, "data", "products.json"), "w"), indent=1)
    print(json.dumps(out, indent=1)[:4000])
