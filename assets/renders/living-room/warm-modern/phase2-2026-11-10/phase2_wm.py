#!/usr/bin/env python3
"""
phase2_wm.py: the warm-modern living-room tool, phase 2, steps 1-3 (briefs/render-wm-tool-phase2-2026-11-10.md; owner PH2-WM; plan
docs/proposals/warm-modern-tool-phase2-2026-11-07.md sections 2-3). render-agent, 2026-11-10. The code side of the three seedream passes
(the var2 calls are made by render-agent, var2_estimate_cost before each): it builds each pass's input, and processes each result into
ungraded per-product layers and shadows. grade_cut.py then grades and cuts the v3c layers. New files only; phase 1 is read, never written.

Working space: the ungraded v3 space of phase 1 at the seedream size of the M0 1.2 overscan canvas (2720 x 1530; the 16:9 camera frame
inside it). The base is phase 1's shell-furniture-v3.png (shell v3, the code furniture shadow, the fixed furniture); every pass adds its
products on top of what the earlier passes made, and everything outside a product and its shadow stays the base's own pixels.

  python3 phase2_wm.py input 1|2|3                     the pass's input (inputs/step<N>-input.png)
  python3 phase2_wm.py fetch 1|2|3 <url> <pid> <tid>   download the result into raw/, register, tone-match, cut every product
  python3 phase2_wm.py swap                            swap-diff on the ungraded stack (per product: only its region changes)
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 5))
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
sys.path.insert(0, P1)
import pilot_wm as PW  # noqa: E402  (read-only use of phase 1's helpers: load, save, register, guided, lum, Lstar, s2l, l2s)

STEP0 = os.path.join(HERE, "step0")
INP, RAW, WORK = os.path.join(HERE, "inputs"), os.path.join(HERE, "raw"), os.path.join(HERE, "work")
PROMPTS = os.path.join(REPO, "assets/prompts/warm-modern-phase2-2026-11-10")
JOBS = os.path.join(HERE, "jobs.json")
SIZE = (2720, 1530)
W_, H_ = SIZE
PH = json.load(open(os.path.join(STEP0, "placeholders.json")))
GROUPS = {1: ["rug"], 2: ["curtains", "vase", "planter", "basket", "magazine-holder", "floor-lamp"],
          3: ["framed-art", "accent-sconces", "pendant", "bowl", "candle-holders"]}
# items that stand behind the fixed furniture somewhere (their alpha never covers the furniture of the base)
BEHIND_FURNITURE = {"rug", "curtains", "floor-lamp"}
CLAY = np.array([0.80, 0.785, 0.76], np.float32)


def rel(p):
    return os.path.relpath(p, REPO)


def furn_alpha():
    return np.asarray(Image.open(os.path.join(P1, "fixed-furniture.png")))[..., 3].astype(np.float32) / 255


def sil(slot):
    """the placeholder's full silhouette (step 0), at the work size, soft (area-resampled)"""
    z = np.load(os.path.join(STEP0, "placeholders.npz"))
    return cv2.resize(z[f"sil_{slot}"].astype(np.float32), SIZE, interpolation=cv2.INTER_AREA)


def vis_masks(slots):
    """visible placeholder parts at the work size: nearer placeholders cover farther ones (step 0 depths), and the base's own
    furniture (phase 1's fixed-furniture alpha) covers the items standing behind it"""
    fa = furn_alpha()
    deps = {k: PH["defaults"][k].get("depth_m") for k in slots}
    rec = json.load(open(os.path.join(STEP0, "f3-checks.json")))["placeholders"]
    deps = {k: rec[k]["depth_m"] for k in slots}
    S = {k: sil(k) for k in slots}
    out = {}
    for k in slots:
        v = S[k].copy()
        for j in slots:
            if j != k and (deps[j] < deps[k] or k == "rug"):
                v = v * (1 - S[j])
        if k in BEHIND_FURNITURE:
            v = v * (1 - fa)
        out[k] = np.clip(v, 0, 1)
    return out


def jobs():
    if os.path.exists(JOBS):
        return json.load(open(JOBS))
    return dict(date="2026-11-10", brief="briefs/render-wm-tool-phase2-2026-11-10.md", decision="PH2-WM (owner, 2026-11-10, up to 9,740)",
                plan="docs/proposals/warm-modern-tool-phase2-2026-11-07.md sections 2-3", budget=dict(this_brief=1950, reserve_with_manager_approval=1300),
                references_policy="supplier images are references only: cropped in the scratchpad and uploaded to var2, never stored in the repo",
                jobs=[])


def job_put(rec):
    J = jobs()
    J["jobs"] = [j for j in J["jobs"] if j["id"] != rec["id"]] + [rec]
    J["tokens_total"] = sum(j.get("tokens", 0) for j in J["jobs"])
    json.dump(J, open(JOBS, "w"), indent=1, ensure_ascii=False)


# ------------------------------------------------------------------------------------------------- inputs
def below_for(step):
    """the ungraded scene a pass is drawn on: the base for step 1, the step-1 composite (base + rug) for steps 2 and 3"""
    if step == 1:
        return PW.load(os.path.join(P1, "shell-furniture-v3.png"))
    return PW.load(os.path.join(WORK, "composite-step1.png"))


def shade_of(below, m):
    """the scene's own low-frequency light under a placeholder (so the clay keeps the room's shadows), plus a soft left-lit falloff"""
    Lb = PW.lum(below).astype(np.float32)
    Lb = cv2.GaussianBlur(Lb, (0, 0), 6.0)
    ref = float(np.median(Lb[m > 0.5])) if (m > 0.5).any() else 0.5
    return np.clip(Lb / max(ref, 1e-3), 0.35, 1.25)


def make_input(step):
    os.makedirs(INP, exist_ok=True)
    below = below_for(step)
    V = vis_masks(GROUPS[step])
    out = below.copy()
    rep = {}
    for k in sorted(V, key=lambda k: -json.load(open(os.path.join(STEP0, "f3-checks.json")))["placeholders"][k]["depth_m"]):
        m = V[k]
        sh = shade_of(below, m)
        if k == "rug":
            clay = CLAY[None, None, :] * (0.92 * sh[..., None])
        else:
            # a plain matte clay with a gentle light from the left window (lighter left, darker right edge of each separate shape);
            # wall pieces a shade darker so they read against the pale plaster
            tone = {"accent-sconces": 0.66, "framed-art": 0.74}.get(k, 1.0)
            n, lab = cv2.connectedComponents((m > 0.02).astype(np.uint8))
            g = np.ones(m.shape, np.float32)
            for i in range(1, n):
                ys, xs = np.nonzero(lab == i)
                x0, x1 = xs.min(), xs.max() + 1
                gx = np.clip(1.06 - 0.16 * (np.arange(W_, dtype=np.float32) - x0) / max(1, x1 - x0), 0.85, 1.06)
                g[lab == i] = np.broadcast_to(gx[None, :], m.shape)[lab == i]
            clay = (CLAY * tone)[None, None, :] * np.clip(0.55 + 0.45 * sh, 0.5, 1.1)[..., None] * g[..., None]
        out = out * (1 - m[..., None]) + np.clip(clay, 0, 1) * m[..., None]
        ys, xs = np.nonzero(m > 0.5)
        rep[k] = dict(px=int((m > 0.5).sum()), box_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1])
    p = os.path.join(INP, f"step{step}-input.png")
    PW.save(p, out)
    json.dump(dict(step=step, below=rel(os.path.join(P1, "shell-furniture-v3.png")) if step == 1 else rel(os.path.join(WORK, "composite-step1.png")),
                   placeholders=rep, note="plain clay placeholders of the defaults (step 0), visible parts only; the rest is the scene itself"),
              open(os.path.join(INP, f"step{step}-input.json"), "w"), indent=1)
    print(p, json.dumps(rep))


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "input":
        make_input(int(args[0]))
    elif cmd == "fetch":
        import extract  # noqa: E402
        extract.fetch(int(args[0]), *args[1:4])
    elif cmd == "swap":
        import extract  # noqa: E402
        extract.swap()
    else:
        raise SystemExit(__doc__)
