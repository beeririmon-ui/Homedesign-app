#!/usr/bin/env python3
"""
compose_ht3.py: HT for QA round 2 (run 5, 0 tokens): the same r2 render and the seed rebuilt from the corner-healed HDx and HD r3.
  HT-M1  the stone: the seed is used only between the middles of the clay's joints at rows 245 and 1225 (whole courses; the switch
         sits inside the dark joint line), the courses above and below are the render's. The render's courses there are moved onto
         the clay by a vertical-only warp of the stone's columns: 4.7 px at the joint at 153, 3.9 at 245 (measured), and -5.0 at 1225
         easing to 0 at the floor line (so the floor line stays continuous with the plaster's). No grading.
  HT-M2  the armchair: in the margin right of the 16:9 frame (x >= 2643), over the rows of the render's round chair, the seed
         (base.png's walnut armchair, the window, the floor) wherever it exists, its holes (floor and bench M0 never saw) inpainted
         per clay surface, never from the render's chair; inside the frame (x 2626-2642) the render's chair edge is replaced by the
         render's own bench and floor, cloned from 20 px to the left.
  HT-M4  the mirrored trowel swirl at the bottom of the jib door: its fine texture (luminance high-pass, sigma 6) is replaced with
         the render's own unmirrored trowel texture from the plaster left of the door (the same rows, or rows above where the skirting
         is), its low-pass kept.
  plaster 120 px ramp, living room 40 px, other surfaces hard, as in r2.
  python3 compose_ht3.py <render_on_canvas.png> <seed_kept.png> <keep_mask.png> <out.png>
"""
import json
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K  # noqa: E402
from prep_d0o import to_lin, to_srgb  # noqa: E402
from ht_tools import cls_ht  # noqa: E402

W709 = np.array([0.2126, 0.7152, 0.0722])
rp, sp, kp, out = sys.argv[1:5]
r8 = np.asarray(Image.open(rp).convert("RGB"))
r = to_lin(r8.astype(np.float64) / 255)
s = to_lin(np.asarray(Image.open(sp).convert("RGB")).astype(np.float64) / 255)
keep = np.asarray(Image.open(kp)) > 127
cls = cls_ht()
H, W = cls.shape
cv = K.canvas("HT")
x_edge = int(round(cv.box[0] + 0.4555 * cv.fw))
x_corner = int(round(cv.box[0] + 0.7903 * cv.fw))
rep = {}

# --- HT-M1: the render's stone columns moved onto the clay (vertical only)
rows = np.arange(H, dtype=np.float64)
d = np.zeros(H)                                   # displacement: the image content at row y comes from row y - d(y)
d[rows <= 155] = 4.7
m = (rows > 155) & (rows <= 247)
d[m] = 4.7 + (3.9 - 4.7) * (rows[m] - 155) / (247 - 155)
m = (rows >= 1227) & (rows <= 1460)
d[m] = -5.0 * (1 - (rows[m] - 1227) / (1460 - 1227))
cols = np.zeros(W, bool); cols[x_edge:x_corner] = True
mapy = (rows - d)[:, None].repeat(W, 1).astype(np.float32)
mapx = np.arange(W, dtype=np.float32)[None, :].repeat(H, 0)
warped = cv2.remap(r.astype(np.float32), mapx, mapy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
st_cols = cols[None, :] & ((rows <= 247) | (rows >= 1227))[:, None]
r = np.where(st_cols[..., None], warped, r)
rep["M1_warp"] = dict(columns=[x_edge, x_corner], top="+4.7 px at 153, +3.9 at 245", bottom="-5.0 at 1225 easing to 0 at row 1460")

# --- seed weights
GROUPS = {"plaster": ((11, 82, 83, 14, 72), 120), "living": (tuple(range(30, 44)) + (0,), 40)}
dt = cv2.distanceTransform(keep.astype(np.uint8), cv2.DIST_L2, 5)
al = keep.astype(np.float64)
for name, (grp, rp_) in GROUPS.items():
    g_ = np.isin(cls, grp)
    same = g_ & (cv2.dilate((g_ & ~keep).astype(np.uint8), np.ones((2 * rp_ + 1,) * 2, np.uint8)) > 0)
    t = np.clip(dt / rp_, 0, 1)
    al = np.where(same & keep, t * t * (3 - 2 * t), al)
stone = np.isin(cls, (94, 86))
band = np.zeros((H, W), bool); band[247:1228] = True
al = np.where(stone, (keep & band).astype(np.float64), al)
rep["M1_seed_on_stone_rows"] = [247, 1227]

# --- HT-M2: the armchair region
x_fr = int(np.ceil(cv.box[2]))                     # 2643: the first column right of the 16:9 frame
R2 = np.zeros((H, W), bool); R2[860:1330, x_fr:] = True
al = np.where(R2, keep.astype(np.float64), al)
comp = r * (1 - al[..., None]) + s * al[..., None]
hole = R2 & ~keep
c8 = np.clip(np.rint(to_srgb(comp) * 255), 0, 255).astype(np.uint8)
bgr = cv2.cvtColor(c8, cv2.COLOR_RGB2BGR)
win = np.zeros((H, W), bool); win[700:1450, 2440:] = True
per_id = {}
for i in np.unique(cls[hole]):
    hi = hole & (cls == i)
    src_ok = win & (cls == i) & ~hole                      # only the same surface, never the render's chair (R2 & ~keep is all hole)
    if src_ok.sum() < 50:
        src_ok = win & ~hole & ~R2
    mask = (win & ~src_ok).astype(np.uint8) * 255         # everything but that surface's known pixels is unknown for this pass
    f = cv2.cvtColor(cv2.inpaint(bgr, mask, 9, cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB)
    comp[hi] = to_lin(f[hi].astype(np.float64) / 255)
    per_id[int(i)] = int(hi.sum())
# inside the frame: the render's chair edge (from x ~2630) replaced by the render's own bench and floor, cloned from 20 px left
strip = np.zeros((H, W), bool); strip[950:1172, 2626:x_fr] = True       # the rows of the render's chair at the frame edge (textured bouclé, 955-1155)
ys_, xs_ = np.nonzero(strip)
fb = cv2.GaussianBlur(strip.astype(np.float64), (0, 0), 2.0)[ys_, xs_]
comp[ys_, xs_] = comp[ys_, xs_] * (1 - fb[:, None]) + r[ys_, xs_ - 20] * fb[:, None]
rep["M2"] = dict(region="seed + per-surface inpainting at x >= 2643 (the margin), rows 860-1329; inside the frame x 2626-2642, rows 950-1171: the render's bench and floor cloned from 20 px left", from_seed_px=int((R2 & keep).sum()), inpainted_px=int(hole.sum()), inpainted_per_clay_id=per_id,
                 inpainted_inside_the_frame_px=int((hole[:, :int(cv.box[2])]).sum()))

# --- HT-M4: the swirl at the bottom of the jib door
door = cls == 82
krows = np.nonzero((keep & door).any(1))[0]
y_patch_bottom = int(krows.max())
zone = door.copy(); zone[: y_patch_bottom - 140] = False
Yc = comp @ W709
low = cv2.GaussianBlur(Yc, (0, 0), 6.0)
hp = Yc / np.maximum(low, 1e-6)
donor = np.isin(cls, (11,)) & (np.arange(W)[None, :] < 470) & (np.arange(W)[None, :] > 90)
det = np.ones((H, W))
ys, xs = np.nonzero(zone)
done = np.zeros(len(ys), bool)
for dy in (0, -110, -220, -330):
    for dx in (-400, -520, -640, -760, -300, -880):
        sx, sy = xs + dx, ys + dy
        ok = ~done & (sx >= 0) & (sy >= 0)
        ok[ok] &= donor[sy[ok], sx[ok]]
        det[ys[ok], xs[ok]] = hp[sy[ok], sx[ok]]
        done |= ok
fe = cv2.GaussianBlur(zone.astype(np.float64), (0, 0), 12.0) * zone          # fade the swap in from the zone's edges
fe = np.clip(fe * 2, 0, 1)
new_Y = low * det
ratio = np.where(Yc > 1e-6, new_Y / np.maximum(Yc, 1e-6), 1.0)
ratio = 1 + (ratio - 1) * fe
comp = np.clip(comp * ratio[..., None], 0, 1)
rep["M4"] = dict(zone_rows=[y_patch_bottom - 140, int(np.nonzero(zone.any(1))[0].max())], px=int(zone.sum()), donor_covered=round(float(done.mean()), 3))

K.save_rgb(out, to_srgb(comp))
print(json.dumps(rep))
