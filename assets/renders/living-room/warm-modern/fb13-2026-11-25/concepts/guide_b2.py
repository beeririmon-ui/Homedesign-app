#!/usr/bin/env python3
"""guide_b2.py: the input of concept B's retry = concept A's own frame (A-r1, flux-2) re-lit in code by the clay's light ratio
(M0-W clay B / clay A at v0 0.555: the last winter sun's patch, the glazing bars' and the olive's shadows, the exposure), registered to
A-r1 by SIFT + RANSAC (reg.py). So A and B show the same room and differ by the light only. Scratch only.
  python3 -P guide_b2.py <scratch>"""
import json, sys
import numpy as np, cv2
from PIL import Image
SP = sys.argv[1]
lin = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
srgb = lambda a: np.where(a <= 0.0031308, a * 12.92, 1.055 * np.clip(a, 0, None) ** (1 / 2.4) - 0.055)
rd = lambda p: np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0
r1 = rd(SP + "/dl/A-r1.jpg")
cA, cB = rd(SP + "/out/clay-frame-A.png"), rd(SP + "/out/clay-frame-B.png")
Hm = np.float64(json.load(open(SP + "/out/reg-A.json"))["homography"])
S = np.float64([[1344 / 1920, 0, 0], [0, 756 / 1080, 0], [0, 0, 1]])
T = Hm @ S                                                   # guide frame 1920 x 1080 -> A-r1 1344 x 768
lw = np.float32([0.2126, 0.7152, 0.0722])
ratio = (lin(cB) @ lw) / np.maximum(lin(cA) @ lw, 0.004)          # luminance only: the proxies' colours stay out of it
ratio = cv2.GaussianBlur(np.clip(ratio, 0.35, 3.0), (0, 0), 1.6)
sunw = np.clip((ratio - 1.10) / 0.35, 0, 1)[..., None]              # where the sun falls: warm gold; the shade: a little warm
ratio = ratio ** 1.2                                                  # the README's finding: the sun about 2 x against the sky
ratio = ratio[..., None] * ((1 - sunw) * np.float32([1.03, 1.0, 0.95]) + sunw * np.float32([1.12, 1.0, 0.76]))
rw = cv2.warpPerspective(ratio, T, (1344, 768), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
# the glazing wall is drawn differently in A-r1 (the frame further right): only the low frequencies of the ratio there
xs = np.arange(1344, dtype=np.float32)[None, :, None]
wl = np.clip((300 - xs) / 80.0, 0, 1)
rw = rw * (1 - wl) + cv2.GaussianBlur(rw, (0, 0), 30.0) * wl
# 1. the plaster's trowel marks down to a soft movement (the wall and the reveal, away from everything that stands on them)
z = np.load(SP + "/out/passes555.npz")["idx"]
FB = (77.4852652259332, 43.427947598253276, 2642.5147347740667, 1486.5720524017468)
sc = 2048 / 2720
f = [v * sc for v in FB]
C = np.float64([[1920 / (f[2] - f[0]), 0, -f[0] * 1920 / (f[2] - f[0])], [0, 1080 / (f[3] - f[1]), -f[1] * 1080 / (f[3] - f[1])], [0, 0, 1]])
wall = np.isin(z, [5, 6, 7, 11]).astype(np.uint8)
wall = cv2.warpPerspective(wall, T @ C, (1344, 768), flags=cv2.INTER_NEAREST)
wall = cv2.erode(wall, np.ones((25, 25), np.uint8)).astype(np.float32)
lab = cv2.cvtColor(r1, cv2.COLOR_RGB2LAB)
gradient = cv2.GaussianBlur(lab[..., 0], (0, 0), 9.0)
detail = lab[..., 0] - gradient
# not where an object stands in A-r1 itself (strong detail or colour): only the plaster's own low-contrast marks
plaster = wall * (np.abs(detail) < 7).astype(np.float32) * (np.hypot(lab[..., 1] - 1.5, lab[..., 2] - 5) < 9).astype(np.float32)
plaster = cv2.GaussianBlur(cv2.erode(plaster, np.ones((5, 5), np.uint8)), (0, 0), 3.0)
lab[..., 0] = lab[..., 0] - 0.6 * detail * plaster
base = np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0, 1)
# 2. the wall socket flux-2 invented (right wall, above the skirting): gone
m = np.zeros((768, 1344), np.uint8)
m[618:648, 1306:1338] = 255
base = cv2.inpaint(np.rint(base * 255).astype(np.uint8), m, 5, cv2.INPAINT_TELEA).astype(np.float32) / 255.0
# 3. the light; the Olia keeps its light natural oak (it stands in the shade in B: no darker than 0.95 of A's)
labb = cv2.cvtColor(base, cv2.COLOR_RGB2LAB)
oak = ((labb[..., 1] > 5) & (labb[..., 2] > 16) & (labb[..., 0] > 38)).astype(np.float32)
box_ = np.zeros((768, 1344), np.float32)
box_[588:760, 530:970] = 1.0
oak = cv2.GaussianBlur(cv2.morphologyEx(oak * box_, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)), (0, 0), 2.0)[..., None]
rw = rw * (1 - oak) + np.maximum(rw, np.float32([0.98, 0.95, 0.90])) * oak
out = np.clip(srgb(lin(base) * rw), 0, 1)
# the sky and the garden behind the glass: pale gold back light (the glass as A-r1 drew it)
g = np.zeros((768, 1344), np.float32)
g[0:522, 52:178] = 1.0
g = cv2.GaussianBlur(g, (0, 0), 2.0)[..., None]
gold = np.clip(srgb(lin(base) * np.float32([1.10, 0.95, 0.66])), 0, 1)
out = out * (1 - g) + gold * g
# 4. plaster above the pendant: the frame 10 px down
pad = 10
out = np.vstack([np.repeat(out[:1], pad, axis=0), out[:-pad]])
Image.fromarray(np.rint(out * 255).astype(np.uint8)).save(SP + "/out/guide-B2.png", optimize=True)
Image.fromarray(np.rint(out * 255).astype(np.uint8)).save(SP + "/out/guide-B2.jpg", quality=92)
print("ratio p1/p50/p99", [round(float(v), 3) for v in np.percentile(rw.mean(-1), [1, 50, 99])], "plaster px", int((plaster > 0.5).sum()))
