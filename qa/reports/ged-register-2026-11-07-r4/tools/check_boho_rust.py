"""
qa-agent 2026-11-07: boho-A-fin7, the two rust cushions (G-ED.6: a second unit of our product, or an imitation?). The right one carries the
story point (data/story/story.json, living-room/boho frame A, cushions-cj-washed-cotton-frayed, option rust-orange, box u 0.45-0.537,
v 0.458-0.596); the left one (u 0.165-0.315, v 0.465-0.6) has none. Per cushion: median Lab of the face (the box's inner half), hue,
and a 100 % / x3 crop of each, with the frayed edge, side by side. The brief (briefs/render-editorial-phase-b-2026-11-06.md, the products
table and the boho prompt) asks for "Rust Orange x2" / "two rust frayed cotton cushions".
Usage: ~/.venvs/motion/bin/python -I check_boho_rust.py. Writes data/boho-rust.json and overlays/boho-rust-pair.jpg.
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
E = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r4")


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


im = Image.open(os.path.join(E, "boho-A-fin7.png")).convert("RGB")
W, H = im.size
a = np.asarray(im).astype(float)
boxes = {"right (story point)": (0.45, 0.537, 0.458, 0.596), "left (no point)": (0.165, 0.315, 0.465, 0.6)}
out, tiles = {}, []
for n, (u0, u1, v0, v1) in boxes.items():
    x0, x1, y0, y1 = int(u0 * W), int(u1 * W), int(v0 * H), int(v1 * H)
    cx0, cx1 = x0 + (x1 - x0) // 4, x1 - (x1 - x0) // 4
    cy0, cy1 = y0 + (y1 - y0) // 4, y1 - (y1 - y0) // 4
    m = np.median(lab(a[cy0:cy1, cx0:cx1].reshape(-1, 3)), 0)
    out[n] = dict(box_px=[x0, x1, y0, y1], face_lab=[round(float(v), 1) for v in m], C=round(float(np.hypot(m[1], m[2])), 1),
                  h_ab=round(float(np.degrees(np.arctan2(m[2], m[1]))), 1))
    c = im.crop((x0 - 10, y0 - 10, x1 + 10, y1 + 10))
    tiles.append(c.resize((int(c.width * 300 / c.height), 300)))
    e = im.crop((x0, y0, x0 + 80, y0 + 60)).resize((320, 240), Image.NEAREST)
    tiles.append(e)
L1, L2 = out["right (story point)"]["face_lab"], out["left (no point)"]["face_lab"]
out["dE76_left_vs_right"] = round(float(np.linalg.norm(np.array(L1) - np.array(L2))), 1)
out["d_hue_deg"] = round(out["left (no point)"]["h_ab"] - out["right (story point)"]["h_ab"], 1)
json.dump(out, open(os.path.join(OUT, "data", "boho-rust.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
o = Image.new("RGB", (sum(t.width for t in tiles) + 10 * len(tiles), 300), (40, 40, 40))
x = 0
for t in tiles:
    o.paste(t, (x, 0))
    x += t.width + 10
o.save(os.path.join(OUT, "overlays", "boho-rust-pair.jpg"), quality=90)
