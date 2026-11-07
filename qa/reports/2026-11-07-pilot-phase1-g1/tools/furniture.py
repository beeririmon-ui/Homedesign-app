"""
qa-agent 2026-11-07: the fixed furniture of the warm-modern pilot on the clay silhouettes (G1.3 / G1.4 for fixed furniture) and its
shadow layer. Clay: render-agent's r4 furniture index pass (session scratchpad wm-r4-furn-idx/M0.npz, first-hit ids 1 sofa, 2 coffee table,
3 armchair; the whole 3 % canvas) resized to the pilot's 2720 x 1530. Render: the alpha of fixed-furniture.png. Per object: IoU, and the
render outline's distance to the clay outline (median, p90, max px at 2720 and at 1920). Shadow: fixed-furniture-shadow.png statistics
under each object. Writes data/furniture.json and overlays/furniture-outlines.jpg. Usage: ~/.venvs/motion/bin/python -I furniture.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")
IDX = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-r4-furn-idx/M0.npz"
W, H = 2720, 1530
idx = cv2.resize(np.load(IDX)["idx"].astype(np.int32), (W, H), interpolation=cv2.INTER_NEAREST)
lay = np.asarray(Image.open(os.path.join(P, "fixed-furniture.png")))
alpha = lay[..., 3] > 127
shadow = np.asarray(Image.open(os.path.join(P, "fixed-furniture-shadow.png")).convert("L")).astype(float)
names = {1: "sofa", 2: "coffee table", 3: "armchair"}
clay_all = np.isin(idx, list(names))
out = dict(alpha_px=int(alpha.sum()), clay_px=int(clay_all.sum()), iou_all=round(float((alpha & clay_all).sum() / (alpha | clay_all).sum()), 4))
# assign render pixels to the nearest clay object
dts, labs = [], []
for k in names:
    dts.append(cv2.distanceTransform((~(idx == k)).astype(np.uint8), cv2.DIST_L2, 5))
near = np.argmin(np.stack(dts), 0)
ids = np.array(list(names))[near]
objs = {}
for k, nm in names.items():
    c = idx == k
    r = alpha & (ids == k)
    ce = cv2.Canny(c.astype(np.uint8) * 255, 50, 150) > 0
    re = cv2.Canny(r.astype(np.uint8) * 255, 50, 150) > 0
    # outline distance, only where the outline is not the frame edge
    inner = np.zeros_like(ce)
    inner[3:-3, 3:-3] = True
    dt_c = cv2.distanceTransform((~ce).astype(np.uint8), cv2.DIST_L2, 5)
    d = dt_c[re & inner]
    objs[nm] = dict(clay_px=int(c.sum()), render_px=int(r.sum()), iou=round(float((c & r).sum() / max((c | r).sum(), 1)), 4),
                    render_outline_to_clay_outline_px_2720=dict(median=round(float(np.median(d)), 1), p90=round(float(np.percentile(d, 90)), 1), max=round(float(d.max()), 1)),
                    p90_px_1920=round(float(np.percentile(d, 90)) * 1920 / W, 1),
                    shadow_under_L=dict(min=round(float(shadow[cv2.dilate(c.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0].min()), 1)))
out["objects"] = objs
out["shadow_layer"] = dict(min=float(shadow.min()), p1=float(np.percentile(shadow, 1)), share_below_250=round(float((shadow < 250).mean() * 100), 2),
                           share_below_250_outside_furniture_band=round(float(((shadow < 250) & ~(cv2.dilate(clay_all.astype(np.uint8), np.ones((121, 121), np.uint8)) > 0)).mean() * 100), 3))
json.dump(out, open(os.path.join(OUT, "data", "furniture.json"), "w"), indent=1)
img = cv2.cvtColor(np.asarray(Image.open(os.path.join(P, "shell-furniture-v2.png")).convert("RGB")), cv2.COLOR_RGB2BGR)
for k in names:
    cs, _ = cv2.findContours((idx == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(img, cs, -1, (0, 0, 255), 2)
rs, _ = cv2.findContours(alpha.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cv2.drawContours(img, rs, -1, (0, 255, 0), 1)
cv2.imwrite(os.path.join(OUT, "overlays", "furniture-outlines.jpg"), cv2.resize(img, (1920, 1080)), [cv2.IMWRITE_JPEG_QUALITY, 85])
sh = cv2.applyColorMap((255 - shadow).clip(0, 255).astype(np.uint8) * 3, cv2.COLORMAP_INFERNO)
cv2.imwrite(os.path.join(OUT, "overlays", "furniture-shadow-layer.jpg"), cv2.resize(sh, (1360, 765)), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(json.dumps(out, indent=1))
