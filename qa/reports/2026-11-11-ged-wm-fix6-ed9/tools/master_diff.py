"""
qa-agent 2026-11-11: G-ED.8 on warm-modern-MB-A-fix6 against fix5 (the frame QA checked in round 5), with QA's own code.
  1. every px that changed (8-bit, any channel > 0, and > 2 levels), against render-agent's (b) mask raw/fix6-b-region.png;
  2. outside the mask: the original L* (fix5) of every changed px (the toe may only touch L* < 20);
  3. the toe as it landed, read from the px outside the mask: median L*(fix6) per 0.25-L* bin of L*(fix5), monotone or not,
     the lift by L*, the hue shift and the chroma ratio;
  4. (b) alone inside the mask: the toe read in 3. is taken off (QA's empirical toe, not render-agent's), the rest is (b);
     its footprint outside QA's box (x 2215-2330, y 840-925), at L* >= 20, and how it ends at the mask's edge;
  5. the cushion (QA's lumbar mask from round 5, and the same recipe re-run on fix5), the duvet below the contact line,
     and the ring band above the right pillowcase (the designer: (b)'s mask does not touch it).
Usage: ~/.venvs/motion/bin/python -I master_diff.py. Writes data/master-diff.json, data/master-toe-curve.json,
data/qa-lumbar-mask-fix5.png, data/b-only-dL.npy (the (b) residual in L*, for b_edges.py).
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MB, OUT, R5, lab, load, r, hue  # noqa: E402

f5 = load(os.path.join(MB, "warm-modern-MB-A-fix5.png"))
f6 = load(os.path.join(MB, "warm-modern-MB-A-fix6.png"))
reg = np.asarray(Image.open(os.path.join(MB, "raw/fix6-b-region.png"))) > 0
comp = np.asarray(Image.open(os.path.join(MB, "raw/P6b-comp-mask.png"))) > 127
H, W = f5.shape[:2]
l5, l6 = lab(f5), lab(f6)
L5, L6 = l5[..., 0], l6[..., 0]
d = np.abs(f6.astype(int) - f5.astype(int)).max(2)
ch0, ch2 = d > 0, d > 2
ge20 = L5 >= 20
out = {"pair": "warm-modern-MB-A-fix5.png -> warm-modern-MB-A-fix6.png"}
ys, xs = np.nonzero(reg)
out["b_mask"] = dict(px=int(reg.sum()), bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                     binary=True, components=int(cv2.connectedComponents(reg.astype(np.uint8))[0] - 1))
out["changed"] = dict(gt0=int(ch0.sum()), gt2=int(ch2.sum()), max_level=int(d.max()))
o = ch0 & ~reg
out["outside_b_mask"] = dict(changed_gt0=int(o.sum()), changed_gt2=int((ch2 & ~reg).sum()),
                             at_L5_ge_20_gt0=int((o & ge20).sum()), at_L5_ge_20_gt2=int((ch2 & ~reg & ge20).sum()),
                             max_L5_of_changed=r(L5[o].max()), max_level=int(d[o].max()),
                             px_L5_lt_20_unchanged=int((~reg & ~ge20 & ~ch0).sum()), px_L5_lt_20=int((~reg & ~ge20).sum()))
i = ch0 & reg
out["inside_b_mask"] = dict(changed_gt0=int(i.sum()), changed_gt2=int((ch2 & reg).sum()),
                            at_L5_ge_20_gt0=int((i & ge20).sum()), at_L5_ge_20_gt2=int((ch2 & reg & ge20).sum()),
                            max_level=int(d[i].max()), max_L5_of_changed=r(L5[i].max()),
                            mask_px_unchanged=int((reg & ~ch0).sum()))

# 3. the toe as it landed (outside the (b) mask), from QA's own reading
sel = ~reg & (L5 < 20)
bins = np.arange(0, 20.25, 0.25)
idx = np.digitize(L5[sel], bins) - 1
med = np.full(len(bins) - 1, np.nan)
for k in range(len(bins) - 1):
    v = L6[sel][idx == k]
    if v.size >= 20:
        med[k] = np.median(v)
ctr = (bins[:-1] + bins[1:]) / 2
ok = ~np.isnan(med)
mono_drops = np.diff(med[ok])
curve = dict(bins_with_20px=int(ok.sum()), monotone_drops_gt_0_05=int((mono_drops < -0.05).sum()),
             largest_drop=r(mono_drops.min()) if mono_drops.size else 0,
             lift_by_L={f"{v:g}": r(np.interp(v, ctr[ok], med[ok]) - v) for v in (1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 19.5)})
# above 20 nothing moves: the same table from px at L5 in [20, 22)
s20 = ~reg & (L5 >= 20) & (L5 < 22)
curve["lift_at_L_20_22_mean"] = r((L6[s20] - L5[s20]).mean(), 4)
own = sel & ch0 & (L5 >= 5) & (np.hypot(l5[..., 1], l5[..., 2]) >= 6)
dh = (hue(l6[..., 1], l6[..., 2]) - hue(l5[..., 1], l5[..., 2]) + 180) % 360 - 180
cr = np.hypot(l6[..., 1], l6[..., 2]) / np.maximum(np.hypot(l5[..., 1], l5[..., 2]), 1e-6)
curve["hue_shift_deg_L5_ge_5_C_ge_6"] = {f"p{q}": r(np.percentile(dh[own], q)) for q in (1, 5, 50, 95, 99)} | {"px": int(own.sum())}
curve["chroma_ratio_L5_ge_5_C_ge_6"] = {f"p{q}": r(np.percentile(cr[own], q), 3) for q in (1, 5, 50, 95, 99)}
chf = sel & ch0
curve["share_changed_px_with_C_down_gt_0_5"] = r(((np.hypot(l6[..., 1], l6[..., 2]) < np.hypot(l5[..., 1], l5[..., 2]) - 0.5) & chf).sum() / max(chf.sum(), 1), 4)
json.dump(dict(curve=curve, table=[[r(c), r(m)] for c, m in zip(ctr[ok], med[ok])]), open(os.path.join(OUT, "data", "master-toe-curve.json"), "w"), indent=1)
out["toe_read_outside_mask"] = curve

# 4. (b) alone: take QA's empirical toe off inside the mask
toeL = np.where(L5 < 20, np.interp(L5, ctr[ok], med[ok]), L5)
bres = np.where(reg, L6 - toeL, 0.0)
np.save(os.path.join(OUT, "data", "b-only-dL.npy"), bres.astype(np.float32))
bfoot = reg & ((bres > 0.5) | (ch0 & ge20))
qa_box = np.zeros((H, W), bool)
qa_box[840:926, 2215:2331] = True
des_box = np.zeros((H, W), bool)
des_box[820:926, 2210:2331] = True
ys, xs = np.nonzero(bfoot)
out["b_only"] = dict(
    rule="inside the mask, L*(fix6) minus QA's empirical toe of L*(fix5) > 0.5, or any change at L*(fix5) >= 20",
    px=int(bfoot.sum()), bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
    outside_qa_box=int((bfoot & ~qa_box).sum()), outside_designer_box=int((bfoot & ~des_box).sum()),
    at_L5_ge_20=int((bfoot & ge20).sum()), at_L5_ge_20_changed_gt2=int((bfoot & ge20 & ch2).sum()),
    dL_p50_p90_max=[r(np.percentile(bres[bfoot], 50)), r(np.percentile(bres[bfoot], 90)), r(bres[bfoot].max())],
    dL_at_L5_ge_20_p50_p90_max=[r(np.percentile(bres[bfoot & ge20], q)) for q in (50, 90)] + [r(bres[bfoot & ge20].max())],
    L5_of_changed_at_ge_20_p50_p90_max=[r(np.percentile(L5[bfoot & ge20], q)) for q in (50, 90)] + [r(L5[bfoot & ge20].max())])
# where in the mask the half-shadow (L* >= 20) changes sit
hs = bfoot & ge20
ys, xs = np.nonzero(hs)
out["b_only"]["half_shadow_bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
out["b_only"]["half_shadow_x_ge_2330"] = int((xs >= 2330).sum())
out["b_only"]["half_shadow_y_lt_840"] = int((ys < 840).sum())

# 5a. the cushion: QA's round-5 lumbar mask (on fix4) and the same recipe on fix5
lum4 = np.asarray(Image.open(os.path.join(R5, "data/qa-lumbar-mask.png"))) > 127


def lumbar_mask(rgb):
    f = rgb.astype(np.int16)
    Y = f.mean(2)
    rr, gg = f[..., 0], f[..., 1]
    box = np.zeros((H, W), bool)
    box[798:929, 1850:2236] = True
    m = box & (Y > 72) & ((rr - gg) < 0.28 * Y + 8)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = (lbl == k).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    ff = m.copy()
    cv2.floodFill(ff, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    return (m | (1 - ff)).astype(bool) & box


lum5 = lumbar_mask(f5)
Image.fromarray(lum5.astype(np.uint8) * 255).save(os.path.join(OUT, "data", "qa-lumbar-mask-fix5.png"))
cush = {}
for name, lm in (("round5_mask_fix4", lum4), ("same_recipe_on_fix5", lum5)):
    e = dict(px=int(lm.sum()), b_mask_overlap=int((lm & reg).sum()), changed_gt0=int((ch0 & lm).sum()),
             changed_gt0_at_L5_ge_20=int((ch0 & lm & ge20).sum()), b_only_px=int((bfoot & lm).sum()))
    for rr_ in (1, 2, 3):
        ring = cv2.dilate(lm.astype(np.uint8), np.ones((2 * rr_ + 1, 2 * rr_ + 1), np.uint8)).astype(bool) & ~lm
        e[f"ring_{rr_}px_b_only"] = int((bfoot & ring).sum())
        e[f"ring_{rr_}px_b_mask_overlap"] = int((reg & ring).sum())
    if (ch0 & lm).any():
        e["changed_L5_max"] = r(L5[ch0 & lm].max())
    cush[name] = e
out["cushion"] = cush
# the distance from the cushion's right edge to the mask's left edge, per row
gaps = []
for y in range(830, 921, 10):
    xl = np.nonzero(lum5[y])[0]
    xm = np.nonzero(reg[y])[0]
    if xl.size and xm.size:
        gaps.append([y, int(xl.max()), int(xm.min()), int(xm.min() - xl.max())])
out["cushion"]["right_edge_vs_mask_left_edge_per_row"] = gaps

# 5b. the duvet: the contact line per column on fix5 (lowest caramel px, or the cushion's lowest px), then below it + 2
r5_, g5_ = f5[..., 0].astype(int), f5[..., 1].astype(int)
Y5 = f5.astype(int).mean(2)
car = ((r5_ - g5_) > 0.28 * Y5 + 8) & (Y5 < 150)
line = np.full(W, -1)
for x in range(1460, 2680):
    c = []
    cl = np.nonzero(car[860:1000, x])[0]
    ll = np.nonzero(lum5[860:1000, x])[0]
    if cl.size:
        c.append(860 + int(cl.max()))
    if ll.size:
        c.append(860 + int(ll.max()))
    if c:
        line[x] = max(c)
duv = np.zeros((H, W), bool)
for x in np.nonzero(line >= 0)[0]:
    duv[line[x] + 3:1086, x] = True
ys_m = np.nonzero(reg)[0]
out["duvet_below_contact_plus_2px"] = dict(px=int(duv.sum()), b_mask_overlap=int((reg & duv).sum()), b_only_px=int((bfoot & duv).sum()),
                                          changed_gt0=int((ch0 & duv).sum()), changed_gt0_at_L5_ge_20=int((ch0 & duv & ge20).sum()),
                                          mask_lowest_y=int(ys_m.max()),
                                          contact_line_under_mask_x2215_2500=[int(line[2215:2501].min()), int(line[2215:2501].max())])

# 5c. the ring band above the right pillowcase (round 5: 12 px below the P6b comp mask's top edge, x 2080-2440)
band = np.zeros((H, W), bool)
for x in range(2080, 2441):
    col = np.nonzero(comp[640:800, x])[0]
    if col.size:
        t = 640 + int(col.min())
        band[t:t + 14, x] = True
out["ring_band"] = dict(px=int(band.sum()), b_mask_overlap=int((band & reg).sum()), b_only_px=int((band & bfoot).sum()),
                        changed_gt0_at_L5_ge_20=int((band & ch0 & ge20).sum()),
                        band_lowest_y=int(np.nonzero(band)[0].max()), mask_top_y=int(np.nonzero(reg)[0].min()))

# connected areas of the change at > 2 levels and L*(fix5) >= 20 (only (b) may change there): 15 px dilation
m20 = (ch2 & ge20).astype(np.uint8)
n, lbl, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(m20, np.ones((15, 15), np.uint8)), connectivity=8)
out["areas_gt2_at_L5_ge_20"] = [dict(bbox=[int(st[k, 0]), int(st[k, 1]), int(st[k, 0] + st[k, 2]), int(st[k, 1] + st[k, 3])],
                                     px=int((m20.astype(bool) & (lbl == k)).sum()),
                                     inside_b_mask=int((m20.astype(bool) & (lbl == k) & reg).sum())) for k in range(1, n)]
json.dump(out, open(os.path.join(OUT, "data", "master-diff.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
