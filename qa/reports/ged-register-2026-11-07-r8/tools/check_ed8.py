"""
qa-agent 2026-11-07: warm-modern-A-ed8 (CAM1: set B's camel corduroy in place of the '21 Camel' chenille; render-agent, cam1.json) against ed7.
(1) G-ED.8: changed pixels, their bounding box, and how many lie outside the old cushion's outline grown 3 px (render-agent's
    raw/cam1-mask-cushion.png, read only) - and, independently, outside a 6 px dilation of the changed area's own filled outline; changes on
    the white bouclé's own pixels (its light surface, L* > 60 inside its box, outside the old camel outline).
(2) G-ED.3: the new cushion's lit face (top 15 % L*) against the White bouclé's lit face in the same frame, and the SKU photo's camel
    corduroy against its own white (view only, scratchpad wm-pilot-refs/); hue, chroma, and dE76 of the two relations.
(3) G-ED.4: the cushion's width and height against the White bouclé (50 x 50) at the same lean.
(4) crops: 100 % (ed7 | ed8 | photo), x3 of the ribs, x4 of the edges (white cushion side, candles side).
Usage: ~/.venvs/motion/bin/python -I check_ed8.py. Writes data/ed8.json and overlays/ed8-*.jpg.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
E = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r8")
REF = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-pilot-refs/"


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def litface(v, q=85):
    t = v[v[:, 0] >= np.percentile(v[:, 0], q)]
    m = np.median(t, 0)
    return [round(float(x), 1) for x in m] + [round(float(np.hypot(m[1], m[2])), 1), round(float(np.degrees(np.arctan2(m[2], m[1]))), 1)]


a = np.asarray(Image.open(os.path.join(E, "warm-modern-A-ed7.png")).convert("RGB"))
b = np.asarray(Image.open(os.path.join(E, "warm-modern-A-ed8.png")).convert("RGB"))
d = np.abs(a.astype(int) - b.astype(int)).max(2) > 0
ys, xs = np.nonzero(d)
old = np.asarray(Image.open(os.path.join(E, "raw/cam1-mask-cushion.png")).convert("L")) > 127
old3 = cv2.dilate(old.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
filled = cv2.morphologyEx(d.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
cs, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
big = max(cs, key=cv2.contourArea)
blob = np.zeros(d.shape, np.uint8)
cv2.drawContours(blob, [big], -1, 1, -1)
LA, LB = lab(a.astype(float)), lab(b.astype(float))
wbox = (880, 650, 1060, 920)
wm = np.zeros(d.shape, bool)
wm[wbox[1]:wbox[3], wbox[0]:wbox[2]] = True
white_surface = wm & (LA[..., 0] > 60) & ~old3
out = dict(changed_px=int(d.sum()), bbox=[int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())],
           outside_old_outline_grown_3px=int((d & ~old3).sum()), outside_own_blob_grown_6px=int((d & ~(cv2.dilate(blob, np.ones((13, 13), np.uint8)) > 0)).sum()),
           components=len(cs), white_boucle_surface_px=int(white_surface.sum()), white_boucle_surface_changed=int((white_surface & d).sum()))
# the new cushion: the changed area (eroded), its lit face; the White boucle's lit face (its box, outside the old camel outline)
cm = cv2.erode((d & old3).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
out["camel_lit_ed8"] = litface(LB[cm])
out["camel_median_ed8"] = [round(float(x), 1) for x in np.median(LB[cm], 0)]
out["white_lit"] = litface(LB[white_surface])
ph = lab(np.asarray(Image.open(REF + "B-cushions-cj-wide-stripe-corduroy-light-green-camel-crop.png").convert("RGB")).astype(float))
H, W = ph.shape[:2]
pc = ph[H // 4:3 * H // 4, W // 4:3 * W // 4].reshape(-1, 3)
out["photo_camel_lit"] = litface(pc)
allp = ph.reshape(-1, 3)
out["photo_white"] = litface(allp, 95)
rel_f = [out["camel_lit_ed8"][i] - out["white_lit"][i] for i in range(3)]
rel_p = [out["photo_camel_lit"][i] - out["photo_white"][i] for i in range(3)]
out["frame_camel_minus_white"] = [round(x, 1) for x in rel_f]
out["photo_camel_minus_white"] = [round(x, 1) for x in rel_p]
out["relation_dE76"] = round(float(np.linalg.norm(np.array(rel_f) - np.array(rel_p))), 1)
out["hue_frame_vs_photo_deg"] = [out["camel_lit_ed8"][4], out["photo_camel_lit"][4]]
# size: the filled outline of the change against the White boucle's (by its light pixels in its box)
x, y, w, h = cv2.boundingRect(big)
wb = (wm & (LB[..., 0] > 60)).astype(np.uint8)
wcs, _ = cv2.findContours(cv2.morphologyEx(wb, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
wx, wy, ww, wh = cv2.boundingRect(max(wcs, key=cv2.contourArea))
out["size"] = dict(camel_box_px=[w, h], white_box_px=[ww, wh], width_ratio=round(w / ww, 2), height_ratio=round(h / wh, 2),
                   note="both cushions 50 x 50 on the card, side by side at the same lean; the white box is cut by the box's own edges if it reaches them")
json.dump(out, open(os.path.join(OUT, "data", "ed8.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
box = (xs.min() - 40, ys.min() - 40, xs.max() + 40, ys.max() + 40)
A, Bi = Image.fromarray(a).crop(box), Image.fromarray(b).crop(box)
P = Image.open(REF + "B-cushions-cj-wide-stripe-corduroy-light-green-camel-crop.png").convert("RGB")
P = P.resize((int(P.width * A.height / P.height), A.height))
o = Image.new("RGB", (A.width * 2 + P.width + 20, A.height), (40, 40, 40))
o.paste(A, (0, 0))
o.paste(Bi, (A.width + 10, 0))
o.paste(P, (2 * A.width + 20, 0))
o.save(os.path.join(OUT, "overlays", "ed8-cushion-100.jpg"), quality=90)
cx, cy = (xs.min() + xs.max()) // 2, (ys.min() + ys.max()) // 2
Image.fromarray(b).crop((cx - 80, cy - 60, cx + 80, cy + 60)).resize((480, 360), Image.NEAREST).save(os.path.join(OUT, "overlays", "ed8-ribs-x3.jpg"), quality=90)
# edges: the right side (towards the white cushion) and the left/bottom
ry = cy
rx = int(xs[ys == ry].max()) if (ys == ry).any() else xs.max()
lx = int(xs[ys == ry].min()) if (ys == ry).any() else xs.min()
t1 = Image.fromarray(b).crop((rx - 40, ry - 40, rx + 40, ry + 40)).resize((320, 320), Image.NEAREST)
t2 = Image.fromarray(b).crop((lx - 40, ry - 40, lx + 40, ry + 40)).resize((320, 320), Image.NEAREST)
t3 = Image.fromarray(b).crop((cx - 40, ys.min() - 30, cx + 40, ys.min() + 50)).resize((320, 320), Image.NEAREST)
o = Image.new("RGB", (980, 320), (40, 40, 40))
for i, t in enumerate((t1, t2, t3)):
    o.paste(t, (i * 330, 0))
o.save(os.path.join(OUT, "overlays", "ed8-edges-x4.jpg"), quality=90)
