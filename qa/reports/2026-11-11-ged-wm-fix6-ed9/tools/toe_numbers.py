"""
qa-agent 2026-11-11: G-ED.8 for the toe on warm-modern-A-ed9 against ed8, and G-ED.11 / G-ED.12 on both frames (ed8 -> ed9 and
master fix5 -> fix6), with QA's own code and the gate's own tool.
  ed9 vs ed8: every changed px (8-bit, any channel > 0 / > 2), the original L* of each, the count at L* >= 20 (must be 0); the toe as
  it landed (median L*(ed9) per 0.25-L* bin of L*(ed8)), monotone or not, the lift by L*, hue shift and chroma ratio; connected areas
  of changes > 2 levels; the frame's median and p90 L* (full size), which DL1 reads.
  Both pairs: the gate's guardrails.py measure() (split flag, p0.5 / p1 on a quarter-size copy, the darkest / brightest 10 % Lab,
  clipped >= 254) and QA's own p0.5 / p1 / p5 on the same quarter-size copy; the p1 target 8.5-9.5, the p5 rise <= 3.
Usage: ~/.venvs/motion/bin/python -I toe_numbers.py. Writes data/ed9-diff.json, data/ed9-toe-curve.json, data/guardrails.json.
"""
import importlib.util
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LR, MB, OUT, REPO, gate_p, hue, lab, load, r  # noqa: E402

e8p, e9p = os.path.join(LR, "warm-modern-A-ed8.png"), os.path.join(LR, "warm-modern-A-ed9.png")
e8, e9 = load(e8p), load(e9p)
l8, l9 = lab(e8), lab(e9)
L8, L9 = l8[..., 0], l9[..., 0]
d = np.abs(e9.astype(int) - e8.astype(int)).max(2)
ch0, ch2 = d > 0, d > 2
ge20 = L8 >= 20
out = {"pair": "warm-modern-A-ed8.png -> warm-modern-A-ed9.png",
       "changed": dict(gt0=int(ch0.sum()), gt2=int(ch2.sum()), max_level=int(d.max())),
       "at_L8_ge_20": dict(changed_gt0=int((ch0 & ge20).sum()), changed_gt2=int((ch2 & ge20).sum())),
       "max_L8_of_changed": r(L8[ch0].max()),
       "px_L8_lt_20": int((~ge20).sum()), "px_L8_lt_20_unchanged": int((~ge20 & ~ch0).sum())}
n, lbl, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(ch2.astype(np.uint8), np.ones((15, 15), np.uint8)), connectivity=8)
out["areas_gt2_15px"] = dict(count=int(n - 1), largest_px=int(sorted(((ch2 & (lbl == k)).sum() for k in range(1, n)))[-1]) if n > 1 else 0)
sel = L8 < 20
bins = np.arange(0, 20.25, 0.25)
idx = np.digitize(L8[sel], bins) - 1
ctr = (bins[:-1] + bins[1:]) / 2
med = np.array([np.median(L9[sel][idx == k]) if (idx == k).sum() >= 20 else np.nan for k in range(len(bins) - 1)])
ok = ~np.isnan(med)
drops = np.diff(med[ok])
own = sel & ch0 & (L8 >= 5) & (np.hypot(l8[..., 1], l8[..., 2]) >= 6)
dh = (hue(l9[..., 1], l9[..., 2]) - hue(l8[..., 1], l8[..., 2]) + 180) % 360 - 180
cr = np.hypot(l9[..., 1], l9[..., 2]) / np.maximum(np.hypot(l8[..., 1], l8[..., 2]), 1e-6)
out["toe_read"] = dict(bins_with_20px=int(ok.sum()), monotone_drops_gt_0_05=int((drops < -0.05).sum()), largest_drop=r(drops.min()),
                       lift_by_L={f"{v:g}": r(np.interp(v, ctr[ok], med[ok]) - v) for v in (1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 19.5)},
                       hue_shift_deg_L8_ge_5_C_ge_6={f"p{q}": r(np.percentile(dh[own], q)) for q in (1, 5, 50, 95, 99)} | {"px": int(own.sum())},
                       chroma_ratio_L8_ge_5_C_ge_6={f"p{q}": r(np.percentile(cr[own], q), 3) for q in (1, 5, 50, 95, 99)},
                       share_changed_px_with_C_down_gt_0_5=r(((np.hypot(l9[..., 1], l9[..., 2]) < np.hypot(l8[..., 1], l8[..., 2]) - 0.5) & ch0).sum() / max(ch0.sum(), 1), 4))
out["frame_L_full_size"] = {k: dict(median=r(np.median(L)), p90=r(np.percentile(L, 90))) for k, L in (("ed8", L8), ("ed9", L9))}
json.dump(dict(table=[[r(c), r(m)] for c, m in zip(ctr[ok], med[ok])]), open(os.path.join(OUT, "data", "ed9-toe-curve.json"), "w"), indent=1)
json.dump(out, open(os.path.join(OUT, "data", "ed9-diff.json"), "w"), indent=1)
print(json.dumps(out, indent=1))

# G-ED.11 / G-ED.12 with the gate's own tool, and QA's percentiles
spec = importlib.util.spec_from_file_location("guardrails", os.path.join(REPO, "qa/reports/2026-11-07-gate-g-ed/tools/guardrails.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
gr = {}
for p in (e8p, e9p, os.path.join(MB, "warm-modern-MB-A-fix5.png"), os.path.join(MB, "warm-modern-MB-A-fix6.png")):
    m = g.measure(p, [])
    m["file"] = os.path.relpath(p, REPO)
    m["qa_quarter_size_percentiles"] = gate_p(load(p))
    full = lab(load(p))[..., 0]
    m["full_size_percentiles_info"] = {f"p{q:g}": r(np.percentile(full, q)) for q in (0.5, 1, 5)}
    m["full_size_median_p90"] = [r(np.median(full)), r(np.percentile(full, 90))]
    gr[os.path.basename(p)] = m
for a, b in (("warm-modern-A-ed8.png", "warm-modern-A-ed9.png"), ("warm-modern-MB-A-fix5.png", "warm-modern-MB-A-fix6.png")):
    pa, pb = gr[a]["qa_quarter_size_percentiles"], gr[b]["qa_quarter_size_percentiles"]
    gr[f"{b} vs {a}"] = dict(p1=pb["p1"], p1_in_8_5_9_5=bool(8.5 <= pb["p1"] <= 9.5), p1_rise=r(pb["p1"] - pa["p1"]),
                             p5_rise=r(pb["p5"] - pa["p5"]), p5_rise_le_3=bool(pb["p5"] - pa["p5"] <= 3),
                             split_flag=gr[b]["split_flag"], clipped_254_same=gr[a]["clipped_254_pct"] == gr[b]["clipped_254_pct"],
                             bible_floor_8=bool(pb["p1"] >= 8))
json.dump(gr, open(os.path.join(OUT, "data", "guardrails.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in gr.items() if " vs " in k}, indent=1))
for k, v in gr.items():
    if " vs " not in k:
        print(k, v["shadow_floor_L_p0_5"], v["shadow_floor_L_p1"], v["qa_quarter_size_percentiles"], v["full_size_percentiles_info"], v["shadows_10pct_Lab"], v["highlights_10pct_Lab"], v["clipped_254_pct"], v["full_size_median_p90"])
