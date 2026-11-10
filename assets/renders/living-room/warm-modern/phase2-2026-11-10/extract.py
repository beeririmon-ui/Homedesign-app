"""
extract.py: the result side of phase2_wm.py (render-agent, 2026-11-10). For one seedream pass:
  (1) download the result into raw/ and resample it to the 2720 x 1530 work size if needed;
  (2) ECC affine onto the pass's input (phase 1's register());
  (3) a local tone match of the render to the scene below (per channel, linear light, a gain field from a normalised 60 px blur of
      below / render OUTSIDE every product zone of the pass; as phase 1's cush_fetch v2), so the products sit in the base's exposure;
  (4) per product, the cut: GrabCut in a box round the product's zone (the step-0 placeholder grown by a margin), seeded by the
      placeholder and by the low-frequency Lab difference to the scene below (sure-foreground: the placeholder's core where the render
      changed; sure-background: the zone's outer ring where it did not); components kept only where they touch the placeholder; thin
      parts (lamp stem, pendant cord) added from the difference inside the placeholder; what stands in front of the product removed
      (the base's fixed furniture for the rug, curtains and floor lamp; nearer products of the same pass); a soft edge from a guided
      filter on the render (r 3), 1 in the eroded core, 0 beyond 3 px of the cut;
  (5) per product, the shadow (multiply, grey): the darkening of the tone-matched render against the scene below in a band round the
      product, only on the surfaces it can fall on (named per product below), never on another product or on the furniture in front;
      1 - blur(d, 3 px) with a soft floor (darkening under 2 % is grain, not shadow);
  (6) the ungraded composite: below x shadow, product over it, in the slot z order.
Outside every product and its shadow the scene below is kept pixel for pixel: only the cuts are taken from the render.
"""
import json
import os
import subprocess

import cv2
import numpy as np
from PIL import Image

import phase2_wm as W
from phase2_wm import PW

# per product: zone margin (px), shadow band radius (px), the surfaces its shadow may fall on, thin parts, z
SPEC = {
    "rug": dict(margin=22, band=10, onto="floor", z=20),
    "curtains": dict(margin=40, band=34, onto="floor_wall_bench", z=10),
    "vase": dict(margin=18, band=26, onto="bench_wall", z=16, thin=True),
    "planter": dict(margin=26, band=40, onto="floor_wall", z=32, thin=True),
    "basket": dict(margin=18, band=36, onto="floor_wall_planter", z=60),
    "magazine-holder": dict(margin=18, band=36, onto="floor", z=60),
    "floor-lamp": dict(margin=16, band=40, onto="floor_wall", z=30, thin=True),
    "framed-art": dict(margin=16, band=14, onto="wall", z=12),
    "accent-sconces": dict(margin=12, band=14, onto="wall", z=12),
    "pendant": dict(margin=16, band=0, onto="none", z=80, thin=True),
    "bowl": dict(margin=12, band=22, onto="table", z=65),
    "candle-holders": dict(margin=12, band=22, onto="table", z=65),
}
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
IDX_FULL = os.path.join(SCR, "wm-r4-idx/M0.npz")
IDX_FURN = os.path.join(SCR, "wm-r4-furn-idx/M0.npz")


def dil(m, r):
    if r <= 0:
        return m.astype(bool)
    return cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)


def ero(m, r):
    if r <= 0:
        return m.astype(bool)
    return cv2.erode(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)


def surfaces():
    """coarse surface masks at the work size from the r4 clay's shell index (the shell is the same architecture as v3)"""
    z = np.load(IDX_FULL, allow_pickle=True)["idx"]
    f = np.load(IDX_FURN, allow_pickle=True)["idx"]
    r = lambda m: cv2.resize(m.astype(np.uint8), W.SIZE, interpolation=cv2.INTER_NEAREST).astype(bool)  # noqa: E731
    # the clay's furniture-only pass carries the shell indices where no furniture stands (the proxies are not in it)
    floor = r(np.isin(f, [8, 11]))
    wall = r(np.isin(f, [5, 6, 7, 11, 14, 521]))
    bench = r(f == 520)
    table = r(f == 2)
    return dict(floor=floor, wall=wall, bench=bench, table=table)


def fetch_raw(url, name):
    os.makedirs(W.RAW, exist_ok=True)
    p = os.path.join(W.RAW, name)
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "240", "-o", p, "-w", "%{http_code}", url], capture_output=True, text=True)
    if r.stdout.strip() != "200":
        raise SystemExit(f"download failed {r.stdout} {r.stderr}")
    return p


def tone_match(reg, below, zone):
    """per channel, linear light: the gain below / render from normalised blurs OUTSIDE the zones; 60 px where that has support,
    blended to 240 px and then to the frame's median gain inside large zones (the rug, the curtains), so it never extrapolates wildly"""
    k = (~dil(zone, 15)).astype(np.float32)
    lb, lr = PW.s2l(below), PW.s2l(reg)
    G = np.ones_like(lb)
    w60, w240 = cv2.GaussianBlur(k, (0, 0), 60), cv2.GaussianBlur(k, (0, 0), 240)
    t60 = np.clip((w60 - 0.05) / 0.25, 0, 1)
    t240 = np.clip((w240 - 0.02) / 0.10, 0, 1)
    for c in range(3):
        g60 = cv2.GaussianBlur(lb[..., c] * k, (0, 0), 60) / np.maximum(w60, 1e-4) / np.maximum(cv2.GaussianBlur(lr[..., c] * k, (0, 0), 60) / np.maximum(w60, 1e-4), 1e-4)
        g240 = cv2.GaussianBlur(lb[..., c] * k, (0, 0), 240) / np.maximum(w240, 1e-4) / np.maximum(cv2.GaussianBlur(lr[..., c] * k, (0, 0), 240) / np.maximum(w240, 1e-4), 1e-4)
        gm = float(np.median(lb[..., c][k > 0]) / max(np.median(lr[..., c][k > 0]), 1e-4))
        g = g240 * t240 + gm * (1 - t240)
        g = g60 * t60 + g * (1 - t60)
        G[..., c] = np.clip(g, 0.6, 1.6)
    return np.clip(PW.l2s(lr * G), 0, 1).astype(np.float32), G


def lab_diff(a, b, sig=1.5):
    bl = lambda x: cv2.GaussianBlur(x, (0, 0), sig)  # noqa: E731
    return np.sqrt(((cv2.cvtColor(bl(a), cv2.COLOR_RGB2LAB) - cv2.cvtColor(bl(b), cv2.COLOR_RGB2LAB)) ** 2).sum(2))


def cut_one(k, regt, below, V, zone, front, dE):
    """the product's hard cut (bool) and its soft alpha"""
    H, Wd = V.shape
    ph = V > 0.5
    ys, xs = np.nonzero(zone)
    pad = 30
    x0, x1, y0, y1 = max(0, xs.min() - pad), min(Wd, xs.max() + pad), max(0, ys.min() - pad), min(H, ys.max() + pad)
    sub = (regt[y0:y1, x0:x1] * 255).astype(np.uint8)
    z_, ph_, dE_, fr_ = zone[y0:y1, x0:x1], ph[y0:y1, x0:x1], dE[y0:y1, x0:x1], front[y0:y1, x0:x1]
    gc = np.full(z_.shape, cv2.GC_BGD, np.uint8)
    gc[z_] = cv2.GC_PR_BGD
    gc[dil(ph_, 3) & (dE_ > 4)] = cv2.GC_PR_FGD
    core = ero(ph_, 6) & (dE_ > 9)
    if core.sum() < 50:
        core = ero(ph_, 3) & (dE_ > 6)
    gc[core] = cv2.GC_FGD
    gc[z_ & ~dil(ph_, max(6, SPEC[k]["margin"] // 2)) & (dE_ < 3)] = cv2.GC_BGD
    gc[fr_] = cv2.GC_BGD
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(sub, gc, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        pass
    f = np.isin(gc, (cv2.GC_FGD, cv2.GC_PR_FGD))
    if SPEC[k].get("thin"):
        f |= dil(ph_, 3) & (dE_ > 7)                # stems, cords, branches: thinner than GrabCut keeps
    f = cv2.morphologyEx(f.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)).astype(bool) & z_ & ~fr_
    n, lab, st, _ = cv2.connectedComponentsWithStats(f.astype(np.uint8), connectivity=8)
    keep = np.zeros_like(f)
    for i in range(1, n):
        comp = lab == i
        if (comp & dil(ph_, 2)).any() and st[i, 4] >= 12:
            keep |= comp
    # fill holes (enclosed background inside the product)
    inv = (~keep).astype(np.uint8)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]])))
    for i in range(1, n2):
        if i not in border and st2[i, 4] < 4000 and not SPEC[k].get("thin"):
            keep |= lab2 == i
    fill = np.zeros(V.shape, bool)
    fill[y0:y1, x0:x1] = keep
    g = cv2.cvtColor((regt * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    a = np.clip(PW.guided(g, fill.astype(np.float32), 3, 1e-3), 0, 1)
    a = np.where(ero(fill, 2), 1.0, a)
    a = np.where(dil(fill, 3) & ~front, a, 0.0).astype(np.float32)
    return fill, a


def shadow_one(k, a, regt, below, surf, others):
    sp = SPEC[k]
    if sp["band"] <= 0 or sp["onto"] == "none":
        return np.ones(a.shape, np.float32)
    onto = np.zeros(a.shape, bool)
    for s in sp["onto"].split("_"):
        if s in surf:
            onto |= surf[s]
        elif s == "planter":
            onto |= others.get("planter", np.zeros_like(onto))
    band = dil(a > 0.02, sp["band"]) & (a < 0.5) & onto & ~surf["front"]
    for j, m in others.items():
        if j != "planter" or "planter" not in sp["onto"]:
            band &= ~(m > 0.02)
    ratio = (cv2.GaussianBlur(PW.lum(regt).astype(np.float32), (0, 0), 3) + 1e-4) / (cv2.GaussianBlur(PW.lum(below).astype(np.float32), (0, 0), 3) + 1e-4)
    d = 1 - np.clip(ratio, 0.35, 1.0)
    d = d * np.clip((d - 0.02) / 0.04, 0, 1) ** 2
    d = np.where(band, d, 0.0).astype(np.float32)
    sh = 1 - cv2.GaussianBlur(d, (0, 0), 3.0)
    return (sh * (1 - a) + a).astype(np.float32)


def fetch(step, url, pid, tid):
    slots = W.GROUPS[step]
    p = fetch_raw(url, f"step{step}-seedream.png")
    out = PW.load(p)
    returned = list(Image.open(p).size)
    if out.shape[1::-1] != W.SIZE:
        out = cv2.resize(out, W.SIZE, interpolation=cv2.INTER_LANCZOS4)
    inp = PW.load(os.path.join(W.INP, f"step{step}-input.png"))
    below = W.below_for(step)
    reg, M = PW.register(out, inp)
    V = W.vis_masks(slots)
    zones = {k: dil(V[k] > 0.02, SPEC[k]["margin"]) for k in slots}
    Z = np.zeros(V[slots[0]].shape, bool)
    for z in zones.values():
        Z |= z
    regt, G = tone_match(reg, below, Z)
    dE = lab_diff(regt, below)
    fa = W.furn_alpha()
    surf = surfaces()
    surf["front"] = fa > 0.02
    # the cuts, nearest first: a nearer product's pixels are never a farther one's
    depth = json.load(open(os.path.join(W.STEP0, "f3-checks.json")))["placeholders"]
    order = sorted(slots, key=lambda k: depth[k]["depth_m"]) if step != 1 else slots
    taken = np.zeros(Z.shape, bool)
    cuts, alphas = {}, {}
    for k in order:
        front = taken.copy()
        if k in W.BEHIND_FURNITURE:
            front |= fa > 0.5
        if k == "rug":
            fill, a = cut_rug(regt, below, V[k], zones[k], fa, dE)
        else:
            fill, a = cut_one(k, regt, below, V[k], zones[k], front, dE)
        if k in W.BEHIND_FURNITURE:
            a = a * (1 - fa)
        cuts[k], alphas[k] = fill, a
        taken |= fill
    shadows = {}
    for k in slots:
        others = {j: alphas[j] for j in slots if j != k}
        shadows[k] = shadow_one(k, alphas[k], regt, below, surf, others)
    # the ungraded composite, slot z order
    comp = below.copy()
    os.makedirs(os.path.join(W.WORK, "layers"), exist_ok=True)
    os.makedirs(os.path.join(W.WORK, "shadows"), exist_ok=True)
    recs = {}
    for k in sorted(slots, key=lambda k: SPEC[k]["z"]):
        a, sh = alphas[k], shadows[k]
        comp = comp * sh[..., None] * (1 - a[..., None]) + regt * a[..., None]
        PW.save(os.path.join(W.WORK, "layers", f"{k}.png"), regt, alpha=a)
        PW.save(os.path.join(W.WORK, "shadows", f"{k}.png"), np.repeat(sh[..., None], 3, 2))
        ph = V[k] > 0.5
        ys, xs = np.nonzero(a > 0.5)
        recs[k] = dict(alpha_px=int((a > 0.5).sum()), soft_px=int(((a > 0.02) & (a < 0.98)).sum()),
                       box_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None,
                       placeholder_px=int(ph.sum()), placeholder_covered=round(float((ph & (a > 0.5)).sum() / max(1, ph.sum())), 3),
                       outside_placeholder_px=int(((a > 0.5) & ~dil(ph, 2)).sum()),
                       shadow_px_below_0_97=int((sh < 0.97).sum()), shadow_min=round(float(sh.min()), 3))
    PW.save(os.path.join(W.WORK, f"composite-step{step}.png"), comp)
    far = ~dil(Z, 40)
    drift = np.abs(PW.Lstar(reg) - PW.Lstar(below))[far]
    drift_t = np.abs(PW.Lstar(regt) - PW.Lstar(below))[far]
    names = {1: "step1-rug", 2: "step2-window-floor", 3: "step3-wall-table"}
    rec = dict(id=f"wm-ph2-{names[step]}", step=step, slots=slots, model="seedream-5-pro i2i 2K", aspect_ratio="auto", tokens=650, estimate=650,
               placeholder_id=pid, task_id=tid, url=url, returned_px=returned, raw=W.rel(p), image_url_local=W.rel(os.path.join(W.INP, f"step{step}-input.png")),
               prompt=W.rel(os.path.join(W.PROMPTS, f"{names[step]}.txt")), register_to_input=np.round(M, 4).tolist(),
               tone_gain_median=[round(float(np.median(G[..., c][Z])), 4) for c in range(3)],
               model_drift_outside_zones_L=dict(raw_median=round(float(np.median(drift)), 2), raw_p95=round(float(np.percentile(drift, 95)), 2),
                                                after_tone_match_median=round(float(np.median(drift_t)), 2),
                                                note="the model's redraw outside the products; discarded (the scene below is kept)"),
               products=recs, composite=W.rel(os.path.join(W.WORK, f"composite-step{step}.png")), status="fetched")
    J = W.jobs()
    prev = next((j for j in J["jobs"] if j["id"] == rec["id"]), {})
    for key in ("refs", "estimate_call", "prompt_chars", "idempotency_key"):
        if key in prev:
            rec[key] = prev[key]
    W.job_put(rec)
    print(json.dumps({k: v for k, v in rec.items() if k in ("register_to_input", "model_drift_outside_zones_L", "products", "tone_gain_median")}, indent=1))


def cut_rug(regt, below, V, zone, fa, dE):
    """the rug: the render follows the placeholder's outline (checked on the sheet), so its alpha is the placeholder's soft
    silhouette snapped to the render's own edge by a guided filter (r 9, the render as guide; as phase 1's furniture), 1 inside
    6 px of the outline, 0 beyond 6 px. Under the furniture the caller removes it (x (1 - furniture alpha)); shadowed rug under the
    armchair and the table is rug, not floor, so no colour model decides there"""
    S = W.sil("rug")
    ph = S > 0.5
    g = cv2.cvtColor((regt * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    a = np.clip(PW.guided(g, S.astype(np.float32), 9, 1e-3), 0, 1)
    a = np.where(ero(ph, 6), 1.0, np.where(dil(ph, 6), a, 0.0)).astype(np.float32)
    return a > 0.5, a


def swap():
    """per product on the ungraded stack: adding it changes nothing outside its alpha > 0 or shadow < 1 (rule ו.5)"""
    out = {}
    for k in SPEC:
        lp = os.path.join(W.WORK, "layers", f"{k}.png")
        if not os.path.exists(lp):
            continue
        L = np.asarray(Image.open(lp)).astype(np.float32) / 255
        S = np.asarray(Image.open(os.path.join(W.WORK, "shadows", f"{k}.png")).convert("L")).astype(np.float32) / 255
        a = L[..., 3]
        out[k] = dict(region_px=int(((a > 0) | (S < 1)).sum()))
    print(json.dumps(out, indent=1))
