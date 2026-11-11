#!/usr/bin/env python3
"""
qa-agent 2026-11-11, phase-2 checkpoint of the warm-modern living-room tool. Written from scratch (nothing imported or copied from
render-agent's code). Reads only the images and, from manifest-r3.json, the file names, the order and the blend of each layer.

  1. Recomposite base + 12 products (+ cushion set X) against graded/default-scene-r3-set-X-graded-v3c.png, X = A, B, C, three paths:
       P1  manifest formula, one rounding per product: round(below*sh/255*(1-a) + rgb*a)
       P2  two 8-bit passes: m = round(below*sh/255); out = round(m*(1-a) + rgb*a)
       P4  browser / gl.ts: ImageBitmap premultiplied (round(rgb*a/255)), multiply = round(src*dst/255),
           normal = round(src_pm + dst*(1-a/255)), RGBA8 target
     gate: p99.9 <= 2 and max <= 6 (worst channel per pixel, 8-bit levels).
  2. Swap-diff: every product toggled off with all others present (set B and A and C), and the set swaps with all products present;
     changed pixels outside the toggled product's own region (alpha > 0 or any shadow channel < 255) or the union of the two sets.
  3. Region hygiene: alpha islands, alpha / shadow farther than 40 px from the main alpha body, shadow-only pixels.
  4. One grade: the r3 scenes against the r12 and steps-1-3 scenes and the approved phase-1 set composites, outside every phase-2 region;
     base.png against the approved v3c base (bytes).
  5. Black point: L* p0.5 per set, and which layer owns the pixels under L* 11; texture (local std) in those pixels.
Writes data/integrity.json and overlays/regions-B.jpg.   ~/.venvs/motion/bin/python -I p2_integrity.py
"""
import hashlib
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-checkpoint")
L = os.path.join(P2, "layers")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def rd(p):
    return np.asarray(Image.open(p)).astype(np.float64)


def lab(rgb8):
    return cv2.cvtColor(rgb8.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)


man = json.load(open(os.path.join(L, "manifest-r3.json")))
order = man["compose"]["order"]
byid = {l_["id"]: l_ for l_ in man["layers"]}
sets = man["slot_cushions"]["sets"]
products = [i for i in order if i != "base" and not i.endswith("-shadow")]

base = rd(os.path.join(L, "base.png"))
H, W = base.shape[:2]
lay, shd = {}, {}
for pid in products:
    if pid == "cushions":
        continue
    lay[pid] = rd(os.path.join(L, byid[pid]["file"]))
    shd[pid] = rd(os.path.join(L, byid[pid + "-shadow"]["file"]))
for s in "ABC":
    lay["set-" + s] = rd(os.path.join(L, sets[s]["layer"]))
    shd["set-" + s] = rd(os.path.join(L, sets[s]["shadow"]))


def region(k):
    return (lay[k][..., 3] > 0) | (shd[k].min(2) < 255)


def stack(s, skip=(), path="P1"):
    out = base.copy()
    for pid in products:
        k = "set-" + s if pid == "cushions" else pid
        if k in skip or pid in skip:
            continue
        rgb, a8, sh = lay[k][..., :3], lay[k][..., 3:4], shd[k]
        a = a8 / 255.0
        if path == "P1":
            out = np.floor(out * sh / 255.0 * (1 - a) + rgb * a + 0.5)
        elif path == "P2":
            m = np.floor(out * sh / 255.0 + 0.5)
            out = np.floor(m * (1 - a) + rgb * a + 0.5)
        else:  # P4
            pm = np.floor(rgb * a + 0.5)
            m = np.floor(sh * out / 255.0 + 0.5)
            out = np.floor(pm + m * (1 - a) + 0.5)
        out = np.clip(out, 0, 255)
    return out


res = {"base_sha256": sha(os.path.join(L, "base.png")),
       "approved_base_sha256": sha(os.path.join(P1, "layers-v3c/base.png")),
       "approved_display_B_sha256": sha(os.path.join(P1, "shell-furniture-v3-graded-v3c.png"))}
res["base_same_bytes"] = res["base_sha256"] == res["approved_base_sha256"]

regions = {k: region(k) for k in lay}
allprod = np.zeros((H, W), bool)
for k in lay:
    allprod |= regions[k]

# 1. recomposite
rec = {}
graded = {s: rd(os.path.join(P2, f"graded/default-scene-r3-set-{s}-graded-v3c.png")) for s in "ABC"}
comps = {}
for s in "ABC":
    rec[s] = {}
    reg = np.zeros((H, W), bool)
    for k in lay:
        if k.startswith("set-") and k != "set-" + s:
            continue
        reg |= regions[k]
    for path in ("P1", "P2", "P4"):
        c = stack(s, path=path)
        if path == "P1":
            comps[s] = c
        d = np.abs(c - graded[s]).max(2)
        rec[s][path] = dict(p999_region=float(np.percentile(d[reg], 99.9)), p999_canvas=float(np.percentile(d, 99.9)),
                            max=float(d.max()), max_at=[int(v) for v in np.unravel_index(int(d.argmax()), d.shape)[::-1]],
                            px_gt0=int((d > 0).sum()), px_gt2=int((d > 2).sum()), px_gt6=int((d > 6).sum()),
                            outside_region_gt0=int(((d > 0) & ~reg).sum()))
        # which layer owns the >2 px
        if path == "P4":
            own = {}
            for k in lay:
                if k.startswith("set-") and k != "set-" + s:
                    continue
                n = int(((d > 2) & regions[k]).sum())
                if n:
                    own[k] = n
            rec[s][path]["gt2_by_layer"] = own
            np.save(os.path.join("/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad", f"qa_p2_resid_{s}.npy"), d.astype(np.uint8))
res["recomposite"] = rec
res["recomposite_pass"] = all(rec[s][p]["p999_region"] <= 2 and rec[s][p]["max"] <= 6 for s in "ABC" for p in ("P1", "P2", "P4"))

# 2. swap-diff
sw = {}
for s in "ABC":
    full = comps[s]
    for pid in products:
        if pid == "cushions":
            continue
        c = stack(s, skip=(pid,))
        ch = np.abs(c - full).max(2) > 0
        sw[f"{pid} [set {s}]"] = dict(changed=int(ch.sum()), changed_outside_region=int((ch & ~regions[pid]).sum()))
    c = stack(s, skip=("cushions",))
    ch = np.abs(c - full).max(2) > 0
    sw[f"cushions off [set {s}]"] = dict(changed=int(ch.sum()), changed_outside_region=int((ch & ~regions["set-" + s]).sum()))
for x, y in (("A", "B"), ("A", "C"), ("B", "C")):
    ch = np.abs(comps[x] - comps[y]).max(2) > 0
    u = regions["set-" + x] | regions["set-" + y]
    sw[f"set {x}<->{y} (all 12 present)"] = dict(changed=int(ch.sum()), changed_outside_union=int((ch & ~u).sum()))
res["swap_diff"] = sw
res["swap_diff_pass"] = all(v.get("changed_outside_region", v.get("changed_outside_union", 0)) == 0 for v in sw.values())

# 3. region hygiene
hyg = {}
for k in lay:
    a = (lay[k][..., 3] > 0).astype(np.uint8)
    n, lab_, st, _ = cv2.connectedComponentsWithStats(a, 8)
    sizes = sorted([int(v) for v in st[1:, cv2.CC_STAT_AREA]], reverse=True)
    main = (lab_ == (1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])))).astype(np.uint8) if n > 1 else a
    dist = cv2.distanceTransform(1 - main, cv2.DIST_L2, 5)
    sh = shd[k].min(2) < 255
    hyg[k] = dict(alpha_px=int(a.sum()), alpha_islands=n - 1, island_sizes_top5=sizes[:5],
                  alpha_px_gt40_from_main=int(((a > 0) & (dist > 40)).sum()),
                  shadow_px=int(sh.sum()), shadow_px_gt40_from_main=int((sh & (dist > 40)).sum()),
                  shadow_min=int(shd[k].min()), alpha_box=[int(v) for v in cv2.boundingRect(a)])
res["region_hygiene"] = hyg
# overlaps between product regions (alpha) - who covers whom
ov = {}
ks = [k for k in lay if not k.startswith("set-")] + ["set-B"]
for i, a in enumerate(ks):
    for b in ks[i + 1:]:
        n = int(((lay[a][..., 3] > 0) & (lay[b][..., 3] > 0)).sum())
        ns = int((regions[a] & regions[b]).sum())
        if ns:
            ov[f"{a} x {b}"] = dict(alpha_overlap=n, region_overlap=ns)
res["region_overlaps"] = ov

# 4. one grade: outside all phase-2 regions the scene equals the approved base / phase-1 composites
g = {}
for s in "ABC":
    r12 = rd(os.path.join(P2, f"graded/default-scene-r12-set-{s}-graded-v3c.png"))
    s13 = rd(os.path.join(P2, f"graded/default-scene-set-{s}-graded-v3c.png"))
    p1 = rd(os.path.join(P1, f"composite-set-{s}-v3-graded-v3c.png")) if os.path.exists(os.path.join(P1, f"composite-set-{s}-v3-graded-v3c.png")) else None
    r3new = regions["planter"] | regions["basket"] | regions["pendant"]
    d12 = np.abs(graded[s] - r12).max(2)
    rec_ = dict(r3_vs_r12_changed=int((d12 > 0).sum()), r3_vs_r12_changed_outside_R3_regions=int(((d12 > 0) & ~r3new).sum()))
    # R2/R1-era planter/basket/pendant were in r12? r12 had no planter/basket/pendant layers -> regions of r12 not needed
    d13 = np.abs(graded[s] - s13).max(2)
    rec_["r3_vs_steps13_changed_outside_all_regions"] = int(((d13 > 0) & ~allprod).sum())
    db = np.abs(graded[s] - base).max(2)
    rec_["r3_vs_base_changed_outside_all_regions"] = int(((db > 0) & ~allprod).sum())
    if p1 is not None:
        dp = np.abs(graded[s] - p1).max(2)
        rec_["r3_vs_phase1_composite_changed_outside_all_regions"] = int(((dp > 0) & ~allprod).sum())
        rec_["phase1_composite"] = f"composite-set-{s}-v3-graded-v3c.png"
    g[s] = rec_
res["one_grade"] = g

# 5. black point
bp = {}
Lb = lab(base.astype(np.uint8))[..., 0]
bp["base_p005"] = round(float(np.percentile(Lb, 0.5)), 2)
for s in "ABC":
    Ls = lab(graded[s].astype(np.uint8))[..., 0]
    low = Ls < 11
    own = {}
    for k in lay:
        if k.startswith("set-") and k != "set-" + s:
            continue
        n = int((low & (lay[k][..., 3] > 127)).sum())
        if n:
            own[k] = n
    own["base (no product alpha>127)"] = int((low & ~np.any([lay[k][..., 3] > 127 for k in lay if not (k.startswith("set-") and k != "set-" + s)], axis=0)).sum())
    std = cv2.blur(Ls ** 2, (9, 9)) - cv2.blur(Ls, (9, 9)) ** 2
    std = np.sqrt(np.clip(std, 0, None))
    bp[s] = dict(p005=round(float(np.percentile(Ls, 0.5)), 2), p001=round(float(np.percentile(Ls, 0.1)), 2), min=round(float(Ls.min()), 2),
                 px_below_11=int(low.sum()), pct_below_11=round(100 * float(low.mean()), 3), below_11_by_owner=own,
                 local_std9_in_below11_median=round(float(np.median(std[low])), 2) if low.any() else None,
                 flat_share_std_lt_0_5=round(float((std[low] < 0.5).mean()), 3) if low.any() else None,
                 clipped_254_pct=round(100 * float((graded[s] >= 254).any(2).mean()), 3),
                 base_and_furniture_only_p005=round(float(np.percentile(Ls[~allprod], 0.5)), 2))
    # the p0.5 without the dark products (bowl, magazine holder)
    m = ~(regions["bowl"] | regions["magazine-holder"])
    bp[s]["p005_without_bowl_and_magazine_holder"] = round(float(np.percentile(Ls[m], 0.5)), 2)
for s in "ABC":
    r12 = rd(os.path.join(P2, f"graded/default-scene-r12-set-{s}-graded-v3c.png"))
    bp[s]["r12_p005"] = round(float(np.percentile(lab(r12.astype(np.uint8))[..., 0], 0.5)), 2)
    s13 = rd(os.path.join(P2, f"graded/default-scene-set-{s}-graded-v3c.png"))
    bp[s]["steps13_p005"] = round(float(np.percentile(lab(s13.astype(np.uint8))[..., 0], 0.5)), 2)
    p1f = os.path.join(P1, f"composite-set-{s}-v3-graded-v3c.png")
    if os.path.exists(p1f):
        bp[s]["phase1_p005"] = round(float(np.percentile(lab(rd(p1f).astype(np.uint8))[..., 0], 0.5)), 2)
res["black_point"] = bp

# overlay of regions on set B
json.dump(res, open(os.path.join(OUT, "data/integrity.json"), "w"), indent=1)
ov_img = np.ascontiguousarray(graded["B"].astype(np.uint8))
cols = [(255, 0, 0), (0, 160, 255), (0, 200, 0), (255, 160, 0), (200, 0, 200), (0, 200, 200), (255, 255, 0), (120, 60, 255),
        (255, 80, 160), (80, 255, 120), (160, 120, 60), (255, 255, 255), (0, 0, 0), (90, 90, 255)]
for i, k in enumerate([k for k in lay if not (k.startswith("set-") and k != "set-B")]):
    e = cv2.morphologyEx(regions[k].astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    ov_img[e] = cols[i % len(cols)]
    ys, xs = np.nonzero(lay[k][..., 3] > 0)
    if len(xs):
        cv2.putText(ov_img, k, (int(xs.min()), max(20, int(ys.min()) - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cols[i % len(cols)], 2)
Image.fromarray(ov_img.astype(np.uint8)).save(os.path.join(OUT, "overlays/regions-B.jpg"), quality=88)
for s in "ABC":
    d = np.load(os.path.join("/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad", f"qa_p2_resid_{s}.npy"))
    m = np.full((H, W, 3), 255, np.uint8)
    m[d == 1] = (90, 140, 255)
    m[d == 2] = (255, 200, 0)
    m[d >= 3] = (230, 0, 0)
    Image.fromarray(m).save(os.path.join(OUT, f"overlays/residual-P4-set-{s}.png"), optimize=True)

json.dump(res, open(os.path.join(OUT, "data/integrity.json"), "w"), indent=1)
print(json.dumps({k: res[k] for k in ("base_same_bytes", "recomposite_pass", "swap_diff_pass")}, indent=1))
print(json.dumps(res["recomposite"], indent=1))
print(json.dumps(res["one_grade"], indent=1))
print(json.dumps(res["black_point"], indent=1))
