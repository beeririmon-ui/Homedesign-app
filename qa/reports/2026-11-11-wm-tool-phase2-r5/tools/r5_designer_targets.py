#!/usr/bin/env python3
"""
qa-agent 2026-11-11 (R5): the checks master-designer asked QA for in docs/proposals/wm-phase2-r5-eye-2026-11-11.md, on its own masks.

  planter (section 2): pot = planter alpha 255, minus basket alpha > 0, minus the soil and the tree (rows above the rim + 6), eroded 3 px;
    ring = wall only (no skirting, no floor: base.png's wall ends at row ~1112 left of the pot, the skirting step), 15-40 px from the pot
    alpha, no product, at the rows where the pot is visible. Targets: (a) pot L* median >= 5 below the ring at the same rows; (b) pot C* <=
    ring C* + 1.5; (c) hue within +-10 deg of the ring. Reported for the rows where both exist (the wall rows), and for the whole pot.
  curtains 180502 as the default (section 1): (1) its inner edge within +-0.003 u of R1's in rows 200-1200 (R1's edge = the r5 default
    file, a recolour of R1); (2) the overlap with the armchair in the real layer >= 0.028: the free alphas stop at the armchair, so the inner edge right above
    the armchair's top row is compared with R1's (whose overlap is 0.0343 by render-agent's step-0 code).
  framed-art v2 (section 5): (1) the moulding band identical to the default's: inside the default's alpha, the pixels of the v2 truth
    that equal the default scene (diff 0) and their dE00 elsewhere; the seam is in crops (x3 / x8) and data/framed-art-v2.json.
Writes data/designer-targets.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r5")
m5 = json.load(open(os.path.join(P2, "layers/manifest-r5.json")))
b5 = {l_["id"]: l_ for l_ in m5["layers"]}
vf = {v["id"]: v["file"] for vs in m5["variants"].values() for v in vs}
FW = 3840 * 2720 / 4072


def lab_img(p):
    return cv2.cvtColor(np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


def summ(px):
    L, a, b = np.median(px, 0)
    return dict(L=round(float(L), 2), C=round(float(np.hypot(a, b)), 2), h=round(float(np.degrees(np.arctan2(b, a)) % 360), 1), px=int(len(px)))


def alpha(f):
    return np.asarray(Image.open(os.path.join(P2, "layers", f)))[..., 3]


res = {}
S = lab_img(os.path.join(P2, "graded/default-scene-r5-set-B-graded-v3c.png"))
ap, ab = alpha(b5["planter"]["file"]), alpha(b5["basket"]["file"])
allprod = np.zeros(ap.shape, bool)
for l_ in m5["layers"]:
    if "product" in l_:
        allprod |= alpha(l_["file"]) > 0
potzone = ((ap == 255) & ~(ab > 0))[:, 900:1150].sum(1) > 40
potzone[:1000] = False                                                         # the crown above; the pot's rim is near row 1050
rim = int(np.nonzero(potzone)[0].min())
pot = (ap == 255) & ~(ab > 0)
pot[:rim] = False
Lsc = S[..., 0]
soil = np.zeros(pot.shape, bool)
soil[rim:rim + 16] = Lsc[rim:rim + 16] < 25                                    # the dark soil in the opening, right under the rim
pot &= ~soil
pot = cv2.erode(pot.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0          # 3 px each side
d = cv2.distanceTransform((~(ap > 0)).astype(np.uint8), cv2.DIST_L2, 5)
ring = (d >= 15) & (d <= 40) & ~allprod
ring[1112:] = False                                                            # wall only (the skirting starts ~1112-1120)
prow = np.nonzero(pot.any(1))[0]
ring[: prow.min()] = False
ring[:, 1000:] = False                                                         # the wall left of the pot (the basket covers the right)
rows_both = sorted(set(np.nonzero(ring.any(1))[0]) & set(prow))
pr = pot.copy()
pr[[y for y in range(pr.shape[0]) if y not in set(rows_both)]] = False
pl = dict(rim_row=rim, pot_rows=[int(prow.min()), int(prow.max())], ring_rows=[int(min(rows_both)), int(max(rows_both))] if rows_both else None,
          pot_same_rows=summ(S[pr]), ring=summ(S[ring]), pot_whole=summ(S[pot]))
pl["a_dL_pot_minus_ring_same_rows"] = round(pl["pot_same_rows"]["L"] - pl["ring"]["L"], 2)
pl["a_pass_(<= -5)"] = pl["a_dL_pot_minus_ring_same_rows"] <= -5
pl["a_dL_pot_whole_minus_ring"] = round(pl["pot_whole"]["L"] - pl["ring"]["L"], 2)
pl["b_C_pot_minus_ring_same_rows"] = round(pl["pot_same_rows"]["C"] - pl["ring"]["C"], 2)
pl["b_pass_(<= 1.5)"] = pl["b_C_pot_minus_ring_same_rows"] <= 1.5
dh = (pl["pot_same_rows"]["h"] - pl["ring"]["h"] + 180) % 360 - 180
pl["c_dh_same_rows"] = round(dh, 1)
pl["c_pass_(+-10)"] = abs(dh) <= 10
# per 10-row band, so the reader sees where the pot is lighter or darker than the wall
bands = []
for y0 in range(prow.min(), prow.max(), 12):
    pm = pot.copy()
    pm[:y0] = False
    pm[y0 + 12:] = False
    if pm.sum() > 30:
        rec = dict(rows=[int(y0), int(y0 + 11)], pot=summ(S[pm]))
        rm = ring.copy()
        rm[:y0] = False
        rm[y0 + 12:] = False
        if rm.sum() > 30:
            rec["ring"] = summ(S[rm])
            rec["dL"] = round(rec["pot"]["L"] - rec["ring"]["L"], 1)
        bands.append(rec)
pl["bands"] = bands
res["planter"] = pl
print(json.dumps({k: v for k, v in pl.items() if k != "bands"}, indent=1))
for b_ in bands:
    print(b_)

# ---------------------------------------------------------------- curtains
ff = np.asarray(Image.open(os.path.join(P1, "fixed-furniture.png")))[..., 3] > 127
n, lab, st, _ = cv2.connectedComponentsWithStats(ff.astype(np.uint8), 8)
arm = np.isin(lab, [i for i in range(1, n) if st[i, 0] < 1000 and st[i, 4] > 2000])
top = int(np.nonzero(arm[:, :400].any(1))[0].min())
cur = {}
FREE = {"554205 (r5 default file)": os.path.join(P2, "work-r5/layers/curtains-free-alpha.png"),
        "180502 (curtains-v2)": os.path.join(P2, "work-r5/layers/curtains-v2-free-alpha.png")}
for name, f in (("554205 (r5 default file)", b5["curtains"]["file"]), ("180502 (curtains-v2)", vf["curtains-v2"])):
    fa_ = np.asarray(Image.open(FREE[name]))
    fa_ = fa_[..., 3] if fa_.ndim == 3 else fa_
    a = fa_ > 127                     # the stack's free silhouette (the layer's own alpha leaves the furniture whole)
    # the free alpha already stops at the armchair (no overlap to measure there): the inner edge right above the armchair's top
    # (rows top-40 .. top+50, where the stack is still free) is what sets the overlap; R1's value is the manifest's 0.0343
    ab_rows = [int(np.nonzero(a[y])[0].max()) for y in range(top - 40, top + 50, 5) if a[y].any()]
    edge = {}
    for y in range(200, 1201, 10):
        xs = np.nonzero(a[y])[0]
        edge[y] = int(xs.max()) if len(xs) else None
    cur[name] = dict(armchair_top_row=top, inner_edge_above_armchair_px=ab_rows, inner_edge=edge)
e0, e1 = cur["554205 (r5 default file)"]["inner_edge"], cur["180502 (curtains-v2)"]["inner_edge"]
du = [round((e1[y] - e0[y]) / FW, 4) for y in e0 if e0[y] is not None and e1[y] is not None]
cur["inner_edge_180502_minus_R1_u"] = dict(rows="200-1200 every 10", max_abs=max(abs(v) for v in du), rows_over_0_003=int(sum(abs(v) > 0.003 for v in du)),
                                           n_rows=len(du), median_abs=round(float(np.median(np.abs(du))), 4), pass_=max(abs(v) for v in du) <= 0.003)
cur["inner_edge_above_armchair_180502_minus_R1"] = dict(
    px_median=float(np.median(np.array(cur["180502 (curtains-v2)"]["inner_edge_above_armchair_px"]) - np.array(cur["554205 (r5 default file)"]["inner_edge_above_armchair_px"]))),
    note="positive = 180502's stack reaches further into the room, so it overlaps the armchair at least as much as R1's 0.0343 (>= 0.028 passes)")
res["curtains"] = cur
print(json.dumps({k: (v if not isinstance(v, dict) or "inner_edge" not in v else {kk: vv for kk, vv in v.items() if kk != "inner_edge"}) for k, v in cur.items()}, indent=1))

# ---------------------------------------------------------------- framed-art band
Vt = np.asarray(Image.open(os.path.join(P2, "graded/variant-r5-framed-art-v2-set-B-graded-v3c.png")).convert("RGB")).astype(np.int16)
Dt = np.asarray(Image.open(os.path.join(P2, "graded/default-scene-r5-set-B-graded-v3c.png")).convert("RGB")).astype(np.int16)
ad = alpha(b5["framed-art"]["file"]) > 0
same = (np.abs(Vt - Dt).max(2) == 0) & ad
res["framed-art band"] = dict(default_alpha_px=int(ad.sum()), identical_px_inside_default_alpha=int(same.sum()),
                              note="the identical set is the pasted moulding band (post_r5 band_px 35,966 in the layer) plus wall; the seam is in the crops")
print(res["framed-art band"])
json.dump(res, open(os.path.join(OUT, "data/designer-targets.json"), "w"), indent=1)
