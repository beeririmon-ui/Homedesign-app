"""qa-agent 2026-11-07: G-ED.8 / G-ED.9 on modern-country-A fix3 -> fix4 (codefix6: the sofa fleck, the line left of the vase, grain on the
mullion strip). Writes data/fix4.json and overlays/fix4-*.jpg. Usage: ~/.venvs/motion/bin/python -I check_fix4.py"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
R = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/ged-register-2026-11-07")
A = np.asarray(Image.open(os.path.join(R, "modern-country-A-fix3.png")).convert("RGB")).astype(np.int16)
B = np.asarray(Image.open(os.path.join(R, "modern-country-A-fix4.png")).convert("RGB")).astype(np.int16)
d = np.abs(A - B).max(2)
ch = d > 2
n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(ch.astype(np.uint8), np.ones((15, 15), np.uint8)))
comps = sorted([dict(px=int(((lab == i) & ch).sum()), box=[int(st[i, 0]), int(st[i, 1]), int(st[i, 0] + st[i, 2]), int(st[i, 1] + st[i, 3])]) for i in range(1, n)], key=lambda c: -c["px"])
zones = [[1195, 1099, 1208, 1113], [1860, 585, 1905, 700], [1988, 541, 2010, 698]]
z = np.zeros(ch.shape, bool)
for x0, y0, x1, y1 in zones:
    z[y0:y1, x0:x1] = True
LB = np.asarray(Image.open(os.path.join(R, "modern-country-A-fix4.png")).convert("L")).astype(float)
LA = np.asarray(Image.open(os.path.join(R, "modern-country-A-fix3.png")).convert("L")).astype(float)
spot = dict(fix3_min=float(LA[1098:1112, 1194:1210].min()), fix4_min=float(LB[1098:1112, 1194:1210].min()), fix4_median=float(np.median(LB[1090:1120, 1185:1220])))
g3, g4 = np.abs(np.diff(LA, axis=1)), np.abs(np.diff(LB, axis=1))
line = dict(fix3=[int(g3[y, 1870:1900].max()) for y in range(590, 700, 10)], fix4=[int(g4[y, 1870:1900].max()) for y in range(590, 700, 10)])
mull = dict(fix3_sd=round(float(LA[560:690, 1995:2008].std()), 2), fix4_sd=round(float(LB[560:690, 1995:2008].std()), 2),
            fix4_flat_run_max=int(max(np.diff(np.flatnonzero(np.diff(LB[620, 1990:2012]) != 0)).tolist() or [0])))
out = dict(changed_px=int(ch.sum()), components=comps[:6], changed_outside_zones_px=int((ch & ~z).sum()), spot=spot, vase_left_line_max_dx=line, mullion=mull)
json.dump(out, open(os.path.join(OUT, "data", "fix4.json"), "w"), indent=1)
img3, img4 = Image.open(os.path.join(R, "modern-country-A-fix3.png")).convert("RGB"), Image.open(os.path.join(R, "modern-country-A-fix4.png")).convert("RGB")
for tag, box, s in (("fix4-spot-x5", (1170, 1085, 1240, 1130), 5), ("fix4-vase-x3", (1860, 520, 2040, 720), 3), ("fix4-table-sill-100", (1000, 450, 2240, 1250), 1)):
    a, b = img3.crop(box), img4.crop(box)
    w, h = a.width * s, a.height * s
    o = Image.new("RGB", (2 * w + 8, h), (40, 40, 40))
    o.paste(a.resize((w, h), Image.NEAREST if s > 1 else Image.BICUBIC), (0, 0))
    o.paste(b.resize((w, h), Image.NEAREST if s > 1 else Image.BICUBIC), (w + 8, 0))
    if o.width > 2000:
        o = o.resize((2000, int(o.height * 2000 / o.width)))
    o.save(os.path.join(OUT, "overlays", tag + ".jpg"), quality=90)
print(json.dumps(out, indent=0))
