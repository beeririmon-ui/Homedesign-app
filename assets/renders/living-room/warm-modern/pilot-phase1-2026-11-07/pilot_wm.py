#!/usr/bin/env python3
"""
pilot_wm.py: the warm-modern tool pilot, phase 1 (briefs/render-warm-modern-pilot-phase1-2026-11-07.md; owner TS1, WMB1, WMP2),
render-agent, 2026-11-07. The code side of steps 2-4 (the var2 calls themselves are made by render-agent with var2_estimate_cost first;
this script prepares their inputs and processes their results). TEST, not for the site until QA and owner approval 3. New files only.

Layer model (skeleton spec, layers.ts: product at slot z, its shadow at z-1 multiply):
  shell.png                      step 2: the seedream shell on the r4 SHELL layer clay (empty room, lamps off), lock_wm.py against it
  fixed-furniture.png            step 3: RGBA, the furniture of the seedream furniture pass, alpha = the r4 FURN layer clay's index mask
                                 (sofa 1, table 2, armchair 3; Bible drums / plinth in the clay), antialiased and snapped to the render
  fixed-furniture-shadow.png     step 3: multiply layer (RGB = multiplier, white = none) = the clay ratio furn / shell outside the furniture
                                 (the furniture's shadow and contact occlusion on the shell, 0 tokens, "made in code")
  shell-furniture.png            shell x shadow, furniture over it (the base of step 4)
  layers/cushions/set-<X>.png    step 4: RGBA cushions + throw of set X, extracted against shell-furniture.png
  shadows/cushions/set-<X>.png   step 4: multiply layer of set X (its contact shadows on the sofa), outside its alpha
  composite-set-<X>.png          base x shadow X, layer X over it
Working canvas: the seedream output size of the overscan canvas (4072 x 2290 -> 2720 x 1530 expected; the 16:9 frame inside it).

  python3 pilot_wm.py shell-fetch <result_url> <placeholder_id> <task_id>
  python3 pilot_wm.py furn-input | furn-fetch <url> <pid> <tid>
  python3 pilot_wm.py cush-input | cush-prompt <A|B|C> | cush-fetch <A|B|C> <url> <pid> <tid>
  python3 pilot_wm.py swap | grade | sheet
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lock_wm  # noqa: E402

SCRATCH = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
R4 = os.path.join(REPO, "assets/blockout/house/framing/warm-modern-r4")
CLAY_SHELL = os.path.join(R4, "layers/shell/M0.png")
CLAY_FURN = os.path.join(R4, "layers/furn/M0.png")
CLAY_FULL = os.path.join(R4, "M0.png")
IDX_FURN = os.path.join(SCRATCH, "wm-r4-furn-idx/M0.npz")
IDX_FULL = os.path.join(SCRATCH, "wm-r4-idx/M0.npz")
PROMPTS = os.path.join(REPO, "assets/prompts/warm-modern-pilot-phase1-2026-11-07")
RAW = os.path.join(HERE, "raw")
JOBS = os.path.join(HERE, "jobs.json")
CANVAS = (4072, 2290)
FURN_IDX = {"sofa": 1, "coffee-table": 2, "armchair": 3}
CUSH_IDX = 42
REFS = json.load(open(os.path.join(SCRATCH, "wm-pilot-refs/uploaded.json"))) if os.path.exists(os.path.join(SCRATCH, "wm-pilot-refs/uploaded.json")) else {}

CUSHION_SETS = {
    "A": [("50 x 50 cm square", "cushions-cj-boucle-teddy", "White", "A-cushions-cj-boucle-teddy-white-crop.png",
           "an off-white bone boucle (teddy) cushion with a dense looped texture, knife edge, no piping"),
          ("45 x 45 cm square", "cushions-cj-knitted-chenille-bean-green", "21 Camel", "A-cushions-cj-knitted-chenille-bean-green-21-camel-color-crop.png",
           "a knitted chenille cushion in a warm taupe-camel, a fine soft woven grid with a velvety sheen, knife edge"),
          ("30 x 50 cm lumbar", "cushions-cj-boucle-teddy", "Milk Tea", "A-cushions-cj-boucle-teddy-milk-tea-color-crop.png",
           "a lumbar boucle (teddy) cushion in a pale milk-tea beige, the same looped texture as the white one"),
          ("150 x 200 cm throw", "sofa-cover-cj-cotton-muslin-fringe", "Flax", "A-sofa-cover-cj-cotton-muslin-fringe-flax-brown-crop.png",
           "a crinkled cotton muslin (double gauze) throw in sandy flax beige with a short frayed fringe")],
    "B": [("50 x 50 cm square", "cushions-aliexpress-textured-boucle-throw-pillow", "Oatmeal", "B-cushions-aliexpress-textured-boucle-throw-pillow-oatmeal-crop.png",
           "a textured boucle cushion in oatmeal, a soft grey-taupe with a fine looped texture, knife edge"),
          ("45 x 45 cm square", "cushions-cj-wide-stripe-corduroy-light-green", "Camel", "B-cushions-cj-wide-stripe-corduroy-light-green-camel-crop.png",
           "a wide-wale corduroy cushion in camel, chunky soft vertical ribs, knife edge"),
          ("30 x 50 cm lumbar", "cushions-cj-linen-look-charcoal", "Beige", "B-cushions-cj-linen-look-charcoal-beige-crop.png",
           "a lumbar cushion in a linen-look weave, warm greige beige with a fine slubby texture"),
          ("150 x 200 cm throw", "sofa-cover-cj-cotton-muslin-fringe", "Pecan", "B-sofa-cover-cj-cotton-muslin-fringe-pecan-crop.png",
           "a crinkled cotton muslin throw in pecan, a warm mid brown, with a short frayed fringe")],
    "C": [("50 x 50 cm square", "cushions-cj-boucle-teddy", "Light Brown", "C-cushions-cj-boucle-teddy-light-brown-crop.png",
           "a boucle (teddy) cushion in light brown, a warm tan with a dense looped texture, knife edge"),
          ("45 x 45 cm square", "cushions-cj-corduroy-patchwork", "Dark Coffee", "C-cushions-cj-corduroy-patchwork-dark-coffee-crop.png",
           "a corduroy patchwork cushion in dark coffee, a deep warm brown, four quadrants of ribs at right angles, a flange edge"),
          ("30 x 50 cm lumbar", "cushions-cj-linen-look-ivory", "Light Beige Gray", "C-cushions-cj-linen-look-ivory-light-beige-gray-crop.png",
           "a lumbar cushion in a linen-look weave, a pale light beige-grey with a fine slubby texture"),
          ("150 x 200 cm throw", "sofa-cover-cj-cotton-muslin-fringe", "Clay", "C-sofa-cover-cj-cotton-muslin-fringe-clay-crop.png",
           "a crinkled cotton muslin throw in clay, a deep chocolate brown, with a short frayed fringe")],
}


# ------------------------------------------------------------------------------------------------- helpers
def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0


def save(p, a, alpha=None):
    a8 = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    if alpha is not None:
        a8 = np.dstack([a8, (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)])
    Image.fromarray(a8).save(p)


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def l2s(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def lum(a):
    return (s2l(a) * [0.2126, 0.7152, 0.0722]).sum(2)


def Lstar(a):
    Y = lum(a)
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


def jobs():
    if os.path.exists(JOBS):
        return json.load(open(JOBS))
    return dict(date="2026-11-07", brief="briefs/render-warm-modern-pilot-phase1-2026-11-07.md", decisions=["TS1", "WMB1", "WMP2"],
                budget=dict(phase1=3250, reserve_with_coordinator_approval=1300), note="TEST, not for the site until QA and owner approval 3",
                references={}, jobs=[])


def job_put(rec):
    J = jobs()
    J["jobs"] = [j for j in J["jobs"] if j["id"] != rec["id"]] + [rec]
    J["tokens_total"] = sum(j.get("tokens", 0) for j in J["jobs"])
    json.dump(J, open(JOBS, "w"), indent=1, ensure_ascii=False)


def fetch_raw(url, name):
    os.makedirs(RAW, exist_ok=True)
    p = os.path.join(RAW, name)
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "180", "-o", p, "-w", "%{http_code}", url], capture_output=True, text=True)
    if r.stdout.strip() != "200":
        raise SystemExit(f"download failed {r.stdout} {r.stderr}")
    return p


def work_size():
    p = os.path.join(HERE, "shell.png")
    if os.path.exists(p):
        return Image.open(p).size
    return (2720, 1530)


def to_work(a, size, interp=cv2.INTER_AREA):
    return cv2.resize(a, size, interpolation=interp)


def idx_masks(npz, size, ids):
    idx = np.load(npz, allow_pickle=True)["idx"]
    out = {}
    for k, v in ids.items():
        m = (idx == v).astype(np.float32)
        out[k] = cv2.resize(m, size, interpolation=cv2.INTER_AREA)
    return out


def register(img, ref, scale=0.5):
    """ECC affine of img onto ref (Sobel edge maps at half size); returns the warped img and the matrix (img coords from ref coords)."""
    h, w = ref.shape[:2]
    def edges(a):
        g = cv2.cvtColor((np.clip(a, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        g = cv2.resize(g, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        g = cv2.GaussianBlur(g, (0, 0), 1.0)
        return np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    M = np.eye(2, 3, dtype=np.float32)
    try:
        _, M = cv2.findTransformECC(edges(ref), edges(img), M, cv2.MOTION_AFFINE,
                                    (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    except cv2.error:
        pass
    M2 = M.copy()
    M2[:, 2] /= scale
    warped = cv2.warpAffine(img, M2, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    return warped, M2


def guided(I, p, r, eps):
    mI = cv2.boxFilter(I, -1, (r, r))
    mp = cv2.boxFilter(p, -1, (r, r))
    cov = cv2.boxFilter(I * p, -1, (r, r)) - mI * mp
    var = cv2.boxFilter(I * I, -1, (r, r)) - mI * mI
    a = cov / (var + eps)
    b = mp - a * mI
    return cv2.boxFilter(a, -1, (r, r)) * I + cv2.boxFilter(b, -1, (r, r))


def frame_uv_box(mask, size):
    ys, xs = np.nonzero(mask > 0.5)
    if not len(xs):
        return None
    W, H = size
    fu = lambda x: (x / W * CANVAS[0] - 116) / 3840
    fv = lambda y: (y / H * CANVAS[1] - 65) / 2160
    return [round(fu(xs.min()), 4), round(fu(xs.max()), 4), round(fv(ys.min()), 4), round(fv(ys.max()), 4)]


# ------------------------------------------------------------------------------------------------- step 2
def shell_fetch(url, pid, tid):
    p = fetch_raw(url, "wm-pilot-shell-seedream.png")
    raw = Image.open(p).convert("RGB")
    size = raw.size
    out = os.path.join(HERE, "shell.png")
    raw.save(out)
    rep = lock_wm.run(out, CLAY_SHELL, os.path.join(HERE, "shell-lock.json"), os.path.join(HERE, "shell-lock.jpg"), "shell")
    full = lock_wm.run(out, CLAY_FULL, os.path.join(HERE, "shell-lock-vs-r4-full-clay.json"), None, "shell")
    a = load(out)
    Ls = Lstar(a)
    rec = dict(id="wm-pilot-shell", step=2, model="seedream-5-pro i2i 2K", aspect_ratio="auto", tokens=650, estimate=650,
               placeholder_id=pid, task_id=tid, url=url, returned_px=list(size), raw=os.path.relpath(p, REPO), out=os.path.relpath(out, REPO),
               image_url_local=os.path.relpath(CLAY_SHELL, REPO), prompt=os.path.relpath(os.path.join(PROMPTS, "shell.txt"), REPO), image_refs=0,
               lock=dict(summary=rep["summary"], verdict=rep["verdict"], lock_v2_register=rep["lock_v2"]["register"],
                         record="shell-lock.json", overlay="shell-lock.jpg"),
               lock_vs_full_r4_clay=dict(summary=full["summary"], verdict=full["verdict"]),
               L_points=points_L(a, size), black_point_p005=round(float(np.percentile(Ls, 0.5)), 1), status="fetched")
    job_put(rec)
    print(json.dumps(rec["lock"], indent=1), json.dumps(rec["L_points"]))


def points_L(a, size):
    """Bible points: the back wall by the corner (-1.75, 0, 1.60), the window wall between the glazing edge (Y 0.75) and the corner
    (-2.30, 0.30, 1.60) [L 80-88, measured between Y 0.75 and the corner, Bible warm-modern 'light'], the back-wall centre."""
    W, H = size
    out = {}
    for k, P in {"back_wall_by_corner(-1.75,0,1.60)": (-1.75, 0.0, 1.60), "window_wall(-2.30,0.30,1.60)": (-2.30, 0.30, 1.60),
                 "window_wall(-2.30,0.55,1.60)": (-2.30, 0.55, 1.60), "back_wall_centre(0.20,0,1.95)": (0.20, 0.0, 1.95),
                 "back_wall_right(1.85,0,1.60)": (1.85, 0.0, 1.60)}.items():
        u, v, _ = lock_wm.r1.project(lock_wm.CAM, *P)
        x = int(((116 + u * 3840) / CANVAS[0]) * W)
        y = int(((65 + v * 2160) / CANVAS[1]) * H)
        r = max(4, int(0.006 * W))
        out[k] = round(float(np.median(Lstar(a[max(0, y - r):y + r, max(0, x - r):x + r]))), 1)
    return out


# ------------------------------------------------------------------------------------------------- step 3
def furn_layers(size):
    shell_c = to_work(load(CLAY_SHELL), size)
    furn_c = to_work(load(CLAY_FURN), size)
    m = idx_masks(IDX_FURN, size, FURN_IDX)
    mf = np.clip(m["sofa"] + m["coffee-table"] + m["armchair"], 0, 1)
    hard = cv2.dilate((mf > 0.02).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    k = (~hard).astype(np.float32)
    def nblur(x, sig):                                          # normalised blur outside the furniture (no furniture leaks in)
        return cv2.GaussianBlur(x * k, (0, 0), sig) / np.maximum(cv2.GaussianBlur(k, (0, 0), sig), 1e-4)
    ratio = (nblur(lum(furn_c).astype(np.float32), 4.0) + 1e-4) / (nblur(lum(shell_c).astype(np.float32), 4.0) + 1e-4)
    d = 1.0 - np.clip(ratio, 0.25, 1.0)
    d = d * np.clip((d - 0.012) / 0.03, 0, 1) ** 2               # soft floor: the clays' denoise / plank-joint noise is not a shadow
    dist = cv2.distanceTransform((~hard).astype(np.uint8), cv2.DIST_L2, 5)
    w = np.clip(1.0 - dist / 320.0, 0, 1) ** 1.5                 # a shadow lives near the furniture that casts it (soft falloff)
    dw = (d * w).astype(np.float32)
    # under the furniture's edge ring (and under the furniture) the shadow continues from the floor / wall next to it (normalised blur
    # from outside), so no light rim shows where the render's silhouette sits a pixel inside the clay's
    fillv = cv2.GaussianBlur(dw * k, (0, 0), 6.0) / np.maximum(cv2.GaussianBlur(k, (0, 0), 6.0), 1e-4)
    dw = np.where(hard, fillv, dw)
    ratio = 1.0 - cv2.GaussianBlur(dw, (0, 0), 3.0)
    ratio_out = ratio                                            # under the furniture the furniture layer covers it
    return shell_c, furn_c, m, mf, ratio_out.astype(np.float32)


def furn_input():
    size = work_size()
    shell = load(os.path.join(HERE, "shell.png"))
    shell_c, furn_c, m, mf, S = furn_layers(size)
    shadowed = shell * S[..., None]
    inp = shadowed * (1 - mf[..., None]) + furn_c * mf[..., None]
    save(os.path.join(HERE, "furniture-input.png"), inp)
    save(os.path.join(HERE, "fixed-furniture-shadow.png"), np.repeat(S[..., None], 3, 2))
    print("furniture-input.png", size, "shadow px < 0.97:", int((S < 0.97).sum()))


def furn_fetch(url, pid, tid):
    size = work_size()
    p = fetch_raw(url, "wm-pilot-furniture-seedream.png")
    out = load(p)
    if out.shape[1::-1] != size:
        out = to_work(out, size, cv2.INTER_LANCZOS4)
    inp = load(os.path.join(HERE, "furniture-input.png"))
    reg, M = register(out, inp)
    shell = load(os.path.join(HERE, "shell.png"))
    shell_c, furn_c, m, mf, S = furn_layers(size)
    # alpha: the clay mask, snapped to the render's own edges by a guided filter (r 4, the render as guide), clamped to +-3 px of the clay
    g = cv2.cvtColor((reg * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    a = np.clip(guided(g, mf.astype(np.float32), 9, 1e-3), 0, 1)
    inner = cv2.erode((mf > 0.5).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    outer = cv2.dilate((mf > 0.02).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    a = np.where(inner, 1.0, np.where(outer, a, 0.0)).astype(np.float32)
    # shadow strength: the clay's pale floor and walls bounce more light than the oak and plaster, so its shadows are lighter. The shape
    # stays the clay's; its tone curve is matched to the render's own shadows: a monotone LUT S -> R by quantile matching over the
    # pixels where the clay sees a shadow (outside the furniture, S < 0.97), R = render / shell luminance there, LUT(1) = 1, floor 0.22
    R = (lum(reg) + 1e-4) / (lum(shell) + 1e-4)
    sel = (S < 0.97) & (a < 0.01) & (R > 0.02)
    if sel.sum() > 500:
        qs = np.linspace(0, 1, 41)
        xs_, ys_ = np.quantile(S[sel], qs), np.quantile(np.clip(R[sel], 0.02, 1.0), qs)
        ys_ = np.maximum.accumulate(np.minimum(ys_, xs_))          # monotone, never lighter than the clay's own shadow
        xs_, ys_ = np.append(xs_, 1.0), np.append(ys_, 1.0)
        xs_, idx_u = np.unique(xs_, return_index=True)
        ys_ = ys_[idx_u]
        t = np.clip((S - 0.80) / 0.17, 0, 1)
        t = t * t * (3 - 2 * t)                                    # faint shadows (S 0.80-0.97) ease back to the clay's own value: no edge
        S = (np.interp(S, xs_, ys_) * (1 - t) + S * t).astype(np.float32)
        S = np.maximum(S, 0.22)
        gam = dict(lut_S=[round(float(v), 3) for v in xs_[::5]], lut_R=[round(float(v), 3) for v in ys_[::5]])
    else:
        gam = dict(lut="none (too few shadow pixels)")
    save(os.path.join(HERE, "fixed-furniture-shadow.png"), np.repeat(S[..., None], 3, 2))
    base = shell * S[..., None]
    comp = base * (1 - a[..., None]) + reg * a[..., None]
    save(os.path.join(HERE, "fixed-furniture.png"), reg, alpha=a)
    save(os.path.join(HERE, "shell-furniture.png"), comp)
    rep = lock_wm.run(p if out.shape[1::-1] == size else os.path.join(HERE, "shell-furniture.png"), CLAY_FURN,
                      os.path.join(HERE, "furniture-lock.json"), os.path.join(HERE, "furniture-lock.jpg"), "furn",
                      selfcheck=os.path.join(R4, "layers/furn/selfcheck-render-A.json"))
    # how far the model moved the shell outside the furniture (it is discarded, reported only)
    zone = ~cv2.dilate((mf > 0.02).astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    dshell = np.abs(Lstar(reg) - Lstar(base))[zone]
    rec = dict(id="wm-pilot-furniture", step=3, model="seedream-5-pro i2i 2K", aspect_ratio="auto", tokens=650, estimate=650,
               placeholder_id=pid, task_id=tid, url=url, returned_px=list(Image.open(p).size), raw=os.path.relpath(p, REPO),
               image_url_local="furniture-input.png", prompt=os.path.relpath(os.path.join(PROMPTS, "furniture.txt"), REPO), image_refs=0,
               register_to_input=np.round(M, 4).tolist(),
               outputs=dict(layer="fixed-furniture.png", shadow="fixed-furniture-shadow.png", composite="shell-furniture.png"),
               furniture_lock=dict(fixed_edges={k: dict(width_ratio=v.get("width_ratio"), height_ratio=v.get("height_ratio"), worst_edge_px=v.get("worst_edge_px"))
                                                for k, v in (rep["lock_v2"]["fixed_edges"] or {}).items()},
                                   register=rep["lock_v2"]["register"], record="furniture-lock.json"),
               shell_drift_outside_furniture_L=dict(median=round(float(np.median(dshell)), 2), p95=round(float(np.percentile(dshell, 95)), 2),
                                                    note="the model's redraw of the shell; discarded: the shell stays the step-2 pixels"),
               shadow=dict(tone=gam, fit_px=int(sel.sum()), px_below_0_97=int((S < 0.97).sum()), min=round(float(S.min()), 3),
                           method="clay ratio furn / shell (normalised blur 4 px, soft floor 1.2-4 %, falloff 320 px, filled under the edge ring), "
                                  "tone curve matched to the render's own shadows (quantile LUT, eased back to the clay value over S 0.80-0.97, floor 0.22)"),
               L_points=points_L(comp, size), status="fetched")
    job_put(rec)
    print(json.dumps(rec["furniture_lock"]["fixed_edges"], indent=1), json.dumps(rec["shell_drift_outside_furniture_L"]), json.dumps(rec["shadow"]))


# ------------------------------------------------------------------------------------------------- step 4
def cush_input():
    size = work_size()
    base = load(os.path.join(HERE, "shell-furniture.png"))
    full = to_work(load(CLAY_FULL), size)
    mc = idx_masks(IDX_FULL, size, {"c": CUSH_IDX})["c"]
    inp = base * (1 - mc[..., None]) + full * mc[..., None]
    save(os.path.join(HERE, "cushions-input.png"), inp)
    print("cushions-input.png", size, "proxy px", int((mc > 0.5).sum()), "box", frame_uv_box(mc, size))


def cush_prompt(s):
    t = open(os.path.join(PROMPTS, "cushions-template.txt")).read()
    items = []
    for i, (size_, card, colour, ref, desc) in enumerate(CUSHION_SETS[s], 1):
        items.append(f"{i}. {size_}: {desc} (reference image {i}).")
    body = t.replace("<ITEMS>", "\n".join(items)).replace("<SET>", s)
    hdr = [l for l in body.splitlines() if l.startswith("#")]
    hdr.append(f"# set {s}: " + "; ".join(f"{c} {col}" for _, c, col, _, _ in CUSHION_SETS[s]))
    txt = "\n".join(hdr) + "\n\n" + "\n".join(l for l in body.splitlines() if not l.startswith("#")).strip() + "\n"
    p = os.path.join(PROMPTS, f"cushions-{s}.txt")
    open(p, "w").write(txt)
    send = "\n".join(l for l in txt.splitlines() if not l.startswith("#")).strip()
    refs = [REFS[r]["public_url"] for _, _, _, r, _ in CUSHION_SETS[s]]
    print(json.dumps(dict(prompt_file=os.path.relpath(p, REPO), chars=len(send), refs=refs)))
    return send, refs


def cush_fetch(s, url, pid, tid):
    size = work_size()
    p = fetch_raw(url, f"wm-pilot-cushions-{s}-seedream.png")
    out = load(p)
    if out.shape[1::-1] != size:
        out = to_work(out, size, cv2.INTER_LANCZOS4)
    base = load(os.path.join(HERE, "shell-furniture.png"))
    inp = load(os.path.join(HERE, "cushions-input.png"))
    reg, M = register(out, inp)
    W, H = size
    mfull = idx_masks(IDX_FURN, size, {"sofa": 1})["sofa"]
    mc = idx_masks(IDX_FULL, size, {"c": CUSH_IDX})["c"]
    # the zone: the sofa and the proxies, widened (cushions lean out of the clay blocks; the throw hangs down the right arm)
    ys, xs = np.nonzero((mfull > 0.5) | (mc > 0.5))
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    zone = np.zeros((H, W), bool)
    zone[max(0, y0 - int(0.06 * H)):min(H, y1 + int(0.02 * H)), max(0, x0 - int(0.01 * W)):min(W, x1 + int(0.04 * W))] = True
    # difference against the base (no proxies): Lab distance, smoothed; product = strong difference, shadow = darkening with little chroma
    lab_o = cv2.cvtColor(reg, cv2.COLOR_RGB2LAB)
    lab_b = cv2.cvtColor(base, cv2.COLOR_RGB2LAB)
    dE = np.sqrt(((lab_o - lab_b) ** 2).sum(2))
    dE = cv2.GaussianBlur(dE, (0, 0), 1.5)
    dC = np.sqrt(((lab_o[..., 1:] - lab_b[..., 1:]) ** 2).sum(2))
    ratio = (lum(reg) + 1e-4) / (lum(base) + 1e-4)
    seed = (dE > 14) & zone
    seed = cv2.morphologyEx(seed.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(seed)
    keep = np.zeros_like(seed, bool)
    for i in range(1, n):
        if st[i, 4] >= 0.0004 * W * H:
            keep |= lab == i
    keep = cv2.morphologyEx(keep.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)).astype(bool)
    # holes inside the product filled; then a soft edge from a GrabCut-free guided filter on the render
    cnts, _ = cv2.findContours(keep.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    fill = np.zeros((H, W), np.uint8)
    cv2.drawContours(fill, cnts, -1, 1, -1)
    g = cv2.cvtColor((reg * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    a = np.clip(guided(g, fill.astype(np.float32), 5, 2e-3), 0, 1) * zone
    a = np.where(cv2.erode(fill, np.ones((5, 5), np.uint8)).astype(bool), 1.0, a).astype(np.float32)
    # leftover clay proxy (model kept a block): reported, not hidden
    proxy_left = float(((mc > 0.5) & (a < 0.5) & (dE > 6)).sum()) / max(1.0, float((mc > 0.5).sum()))
    # shadow: darkening outside the product, inside the zone, low chroma change
    sh = np.where(zone & (a < 0.5) & (dC < 6), np.clip(ratio, 0.35, 1.0), 1.0).astype(np.float32)
    sh = cv2.GaussianBlur(sh, (0, 0), 2.0)
    sh = np.where(sh > 0.985, 1.0, sh)
    sh = sh * (1 - a) + a                                      # under the product the product decides
    comp = base * sh[..., None] * (1 - a[..., None]) + reg * a[..., None]
    os.makedirs(os.path.join(HERE, "layers/cushions"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "shadows/cushions"), exist_ok=True)
    save(os.path.join(HERE, f"layers/cushions/set-{s}.png"), reg, alpha=a)
    save(os.path.join(HERE, f"shadows/cushions/set-{s}.png"), np.repeat(sh[..., None], 3, 2))
    save(os.path.join(HERE, f"composite-set-{s}.png"), comp)
    drift = np.abs(Lstar(reg) - Lstar(base))[~cv2.dilate(zone.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)]
    # product colour per item region is read by eye from the crops (sheet); the layer's own numbers:
    rec = dict(id=f"wm-pilot-cushions-{s}", step=4, slot="cushions", set=s,
               items=[dict(size=z, card=c, colour=col, ref=REFS.get(r, {}).get("public_url")) for z, c, col, r, _ in CUSHION_SETS[s]],
               model="seedream-5-pro i2i 2K", aspect_ratio="auto", tokens=650, estimate=650, placeholder_id=pid, task_id=tid, url=url,
               returned_px=list(Image.open(p).size), raw=os.path.relpath(p, REPO), image_url_local="cushions-input.png",
               prompt=os.path.relpath(os.path.join(PROMPTS, f"cushions-{s}.txt"), REPO), image_refs=4, register_to_input=np.round(M, 4).tolist(),
               layer=dict(file=f"layers/cushions/set-{s}.png", alpha_px=int((a > 0.5).sum()), box_frame_uv=frame_uv_box(a, size),
                          slot_box_frame_uv=[0.484, 0.901, 0.566, 0.898], proxy_area_left_uncovered_and_changed=round(proxy_left, 4)),
               shadow=dict(file=f"shadows/cushions/set-{s}.png", px_below_0_97=int((sh < 0.97).sum()), min=round(float(sh.min()), 3)),
               composite=f"composite-set-{s}.png",
               model_drift_outside_zone_L=dict(median=round(float(np.median(drift)), 2), p95=round(float(np.percentile(drift, 95)), 2),
                                               note="discarded: the base stays the step-3 pixels"),
               status="fetched")
    job_put(rec)
    print(json.dumps(rec["layer"]), json.dumps(rec["shadow"]), json.dumps(rec["model_drift_outside_zone_L"]))


def swap():
    """studio rule ו.5 in the tool: swapping set X for set Y changes nothing outside the two products and their shadows."""
    base = load(os.path.join(HERE, "shell-furniture.png"))
    sets = [s for s in "ABC" if os.path.exists(os.path.join(HERE, f"layers/cushions/set-{s}.png"))]
    out = {}
    def comp(s):
        L = np.asarray(Image.open(os.path.join(HERE, f"layers/cushions/set-{s}.png"))).astype(np.float32) / 255
        S = np.asarray(Image.open(os.path.join(HERE, f"shadows/cushions/set-{s}.png")).convert("L")).astype(np.float32) / 255
        a = L[..., 3:4]
        return base * S[..., None] * (1 - a) + L[..., :3] * a, (a[..., 0] > 1 / 255) | (S < 254 / 255)
    C = {s: comp(s) for s in sets}
    for i, s in enumerate(sets):
        for t in sets[i + 1:]:
            (cs, ms), (ct, mt) = C[s], C[t]
            d = np.abs(cs - ct).max(2) * 255
            outside = ~(ms | mt)
            out[f"{s}->{t}"] = dict(changed_px=int((d > 0.5).sum()), changed_outside_products_and_shadows=int((d[outside] > 0.5).sum()),
                                    union_px=int((ms | mt).sum()))
        cs, ms = C[s]
        d0 = np.abs(cs - base).max(2) * 255
        out[f"base->{s}"] = dict(changed_outside=int((d0[~ms] > 0.5).sum()))
    J = jobs()
    J["swap_diff"] = dict(rule="studio rule ו.5 (tool): a swap changes nothing outside the products and their shadows", pairs=out)
    json.dump(J, open(JOBS, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1))


def corner_gain(size):
    """one global exposure for the whole pilot (every layer composite shares it): the back wall by the corner (-1.75, 0, 1.60) of the
    step-2 shell to L 90 (Bible 1.8 B1 (1): 90-94; ARC2 = the Nordic light)."""
    a = load(os.path.join(HERE, "shell.png"))
    W, H = size
    u, v, _ = lock_wm.r1.project(lock_wm.CAM, -1.75, 0.0, 1.60)
    x, y = int((116 + u * 3840) / CANVAS[0] * W), int((65 + v * 2160) / CANVAS[1] * H)
    r = max(4, int(0.006 * W))
    Y = float(np.median(lum(a[y - r:y + r, x - r:x + r])))
    Yt = ((90.0 + 16) / 116) ** 3
    return Yt / Y, Y


def grade():
    """The pilot's display grade (the layers themselves stay ungraded; the tool applies one chain to the stack):
    (1) exposure: one global linear gain for every composite, from the shell's back wall by the corner to L 90 (corner_gain), with a
        highlight shoulder above L 88 (the glass and the bright wash keep detail; nothing above L 97);
    (2) WM-G1, the black point L 11-14 (Nordic 12-15): a toe on L* only (hue and chroma kept); the darkest 0.5 % is moved to 12.5 when
        it is outside 11-14, fading out by L 25.
    Written as *-graded.png next to each composite; the ungraded composite stays. The Nordic v6 fall-off table (a low-frequency
    exposure map along the back wall) is NOT applied: reported for the designer."""
    size = work_size()
    g, Y0 = corner_gain(size)
    knee, top = ((88.0 + 16) / 116) ** 3, ((97.0 + 16) / 116) ** 3
    out = dict(_exposure=dict(gain=round(g, 4), stops=round(float(np.log2(g)), 3), corner_Y_before=round(Y0, 4), knee_L=88, shoulder_max_L=97))
    for name in ["shell.png", "shell-furniture.png"] + [f"composite-set-{s}.png" for s in "ABC"]:
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            continue
        a = load(p)
        lin = s2l(a) * g
        Y = (lin * [0.2126, 0.7152, 0.0722]).sum(2)
        Yc = np.where(Y > knee, knee + (top - knee) * (1 - np.exp(-(Y - knee) / (top - knee))), Y)
        lin = lin * (Yc / np.maximum(Y, 1e-6))[..., None]
        e = np.clip(l2s(np.clip(lin, 0, 1)), 0, 1).astype(np.float32)
        lab = cv2.cvtColor(e, cv2.COLOR_RGB2LAB)
        L = lab[..., 0]
        bp = float(np.percentile(L, 0.5))
        rec = dict(black_point_p005_after_exposure=round(bp, 2))
        if not 11.0 <= bp <= 14.0:
            tgt = 12.5
            k = np.clip(1 - (L - bp) / max(25.0 - bp, 1e-3), 0, 1) ** 2
            lab[..., 0] = np.where(L < 25.0, L + (tgt - bp) * k, L)
            e = np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0, 1)
        rec["black_point_p005_final"] = round(float(np.percentile(cv2.cvtColor(e, cv2.COLOR_RGB2LAB)[..., 0], 0.5)), 2)
        rec["clipped_254_pct"] = round(float(((e * 255) >= 254).any(2).mean() * 100), 3)
        rec["L_points_final"] = points_L(e, size)
        q = p.replace(".png", "-graded.png")
        save(q, e)
        rec["out"] = os.path.basename(q)
        out[name] = rec
    J = jobs()
    J["grade_pilot"] = dict(rule="exposure: the corner to L 90, one gain for all, shoulder L 88-97; WM-G1 black point L 11-14 (toe on L* only)",
                            files=out)
    json.dump(J, open(JOBS, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1))


def sheet():
    from PIL import ImageDraw, ImageFont
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    tiles = [("clay r4, shell layer", CLAY_SHELL), ("clay r4, furniture layer", CLAY_FURN), ("step 2: shell (seedream)", os.path.join(HERE, "shell.png")),
             ("step 3: shell + furniture + code shadow", os.path.join(HERE, "shell-furniture.png"))]
    tiles += [(f"step 4: cushions set {s}", os.path.join(HERE, f"composite-set-{s}.png")) for s in "ABC"]
    tiles += [("shell lock overlay (red = clay line, green = render edge)", os.path.join(HERE, "shell-lock.jpg"))]
    tiles = [t for t in tiles if os.path.exists(t[1])]
    tw, th = 960, 540
    cols = 2
    rows = (len(tiles) + 1) // 2
    im = Image.new("RGB", (cols * tw + 30, rows * (th + 40) + 70), (250, 249, 247))
    d = ImageDraw.Draw(im)
    d.text((15, 15), "Warm-modern tool pilot, phase 1 (TEST, not for the site; awaiting qa-agent, master-designer, owner approval 3)", fill=(0, 0, 0), font=fb)
    for i, (t, p) in enumerate(tiles):
        r, c = divmod(i, cols)
        x, y = 10 + c * (tw + 10), 60 + r * (th + 40)
        a = Image.open(p).convert("RGB")
        if abs(a.size[0] / a.size[1] - CANVAS[0] / CANVAS[1]) < 0.004 and a.size[0] != 1920:
            w0, h0 = a.size
            a = a.crop((round(116 / 4072 * w0), round(65 / 2290 * h0), round(3956 / 4072 * w0), round(2225 / 2290 * h0)))
        im.paste(a.resize((tw, th), Image.LANCZOS), (x, y + 30))
        d.text((x, y + 4), t, fill=(0, 0, 0), font=f)
    p = os.path.join(HERE, "pilot-phase1-sheet.jpg")
    im.save(p, quality=90)
    print(p)


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"shell-fetch": lambda: shell_fetch(*args), "furn-input": furn_input, "furn-fetch": lambda: furn_fetch(*args),
     "cush-input": cush_input, "cush-prompt": lambda: cush_prompt(*args), "cush-fetch": lambda: cush_fetch(*args),
     "swap": swap, "grade": grade, "sheet": sheet}[cmd]()
