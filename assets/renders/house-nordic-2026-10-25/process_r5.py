#!/usr/bin/env python3
"""
Phase B draft processing (render-agent, 2026-10-25): the recipe-v5 pipeline of assets/renders/living-room/nordic/recipe-v5/process.py,
generalised to every frame of the house.

For one draft: (1) copy the raw as var2 returned it to <out_dir>/raw/, (2) normalise to exact 16:9 by a non-uniform resize (no crop, as
pilot v4.1), (3) clay lock: phase correlation of gradient maps against the clay resized to the output, on the whole frame and on the
boxes of the fixed furniture, windows and openings read from the round-3 clay selfcheck, (4) ONE global grade per
docs/render-recipe-nordic-2026-10-24.md 2.6 (white balance to H 36 on the hero-wall patch, exposure capped at +-0.2 stop toward the
frame's target L, chroma -10 %, roll-off from L 94, S curve 0.12, black point to L 12.5 only if below 12; no grain, no vignette,
no local correction), (5) L / S / H readings on the wall, ceiling and floor patches of the clay selfcheck, before and after, (6) a
box overlay (<aid>-boxes.png): the clay's placeholder boxes drawn on the graded draft with the slot names, for the +-15 % product
check, and a lock overlay (<aid>-lock.png): the clay's edges in red over the draft.

  python3 process_r5.py <aid> <raw_path> <clay_path> <frame> <out_dir> [<round3 selfcheck.json>]
M0 (m0-v6) uses the pilot's M0 regions and patches (no round-3 selfcheck).
"""
import colorsys
import json
import os
import shutil
import sys

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image, ImageDraw, ImageFilter, ImageFont

aid, raw_path, clay_path, frame, out_dir = sys.argv[1:6]
sc_path = sys.argv[6] if len(sys.argv) > 6 else None
os.makedirs(os.path.join(out_dir, "raw"), exist_ok=True)
raw_copy = os.path.join(out_dir, "raw", aid + os.path.splitext(raw_path)[1].lower())
if os.path.abspath(raw_copy) != os.path.abspath(raw_path):
    shutil.copyfile(raw_path, raw_copy)

# per-frame grade targets: the hero-wall patch is pulled toward target_L (capped +-0.2 stop); Bible: back wall by the window 92-95 (M0),
# hall/corridor ~2/3 stop under the living (B5) -> 80-84, lamp-lit bath 84-88
TARGET_L = {"M0": 93.0, "H0": 82.0, "C0": 82.0, "B1": 86.0, "B2": 86.0}
target_L = TARGET_L.get(frame, 90.0)


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def l2s(x):
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


Y = np.array([0.2126, 0.7152, 0.0722])
im0 = Image.open(raw_path).convert("RGB")
W0, H0 = im0.size
W = W0
H = int(round(W * 9 / 16))
resized = H != H0
im = im0.resize((W, H), Image.LANCZOS) if resized else im0
im.save(os.path.join(out_dir, aid + ".png"))
a = np.asarray(im, float) / 255.0
clay_im = Image.open(clay_path).convert("L").resize((W, H), Image.LANCZOS)
cg = np.asarray(clay_im, float)


def grad(g):
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1] = g[2:] - g[:-2]
    return np.hypot(gx, gy)


def phase_shift(A, B, maxfrac=0.06):
    h, w = A.shape
    win = np.outer(np.hanning(h), np.hanning(w))
    FA = np.fft.fft2((A - A.mean()) * win)
    FB = np.fft.fft2((B - B.mean()) * win)
    R = FA * np.conj(FB)
    R /= (np.abs(R) + 1e-9)
    r = np.fft.ifft2(R).real
    my, mx = int(maxfrac * H), int(maxfrac * W)
    r2 = np.fft.fftshift(r)
    cy, cx = h // 2, w // 2
    sub = r2[max(0, cy - my):cy + my + 1, max(0, cx - mx):cx + mx + 1]
    iy, ix = np.unravel_index(np.argmax(sub), sub.shape)
    dy = iy + max(0, cy - my) - cy
    dx = ix + max(0, cx - mx) - cx
    return int(dx), int(dy), float(sub.max())


def ncc_at(A, gi, box, dx, dy):
    u0, u1, v0, v1 = box
    x0, x1, y0, y1 = int(u0 * W), int(u1 * W), int(v0 * H), int(v1 * H)
    ys, xs = y0 + dy, x0 + dx
    if ys < 0 or xs < 0 or ys + (y1 - y0) > H or xs + (x1 - x0) > W:
        return None
    Bq = gi[ys:ys + (y1 - y0), xs:xs + (x1 - x0)]
    A = (A - A.mean()) / (A.std() + 1e-9)
    Bq = (Bq - Bq.mean()) / (Bq.std() + 1e-9)
    return float((A * Bq).mean())


gc = grad(cg)
gi = grad(np.asarray(im.convert("L"), float))

# ---- regions, patches and product boxes ------------------------------------------------------------------------
M0_REGIONS = {"frame": (0.05, 0.95, 0.05, 0.95), "corner+cornice": (0.40, 0.50, 0.0, 0.62), "window": (0.17, 0.40, 0.0, 0.62),
              "sofa": (0.5208, 0.8396, 0.5509, 0.7949), "table": (0.512, 0.762, 0.6787, 0.8699), "armchair": (0.1896, 0.3867, 0.6218, 0.9056),
              "ceiling-band": (0.55, 0.95, 0.0, 0.15), "floor/skirting-right": (0.84, 0.99, 0.60, 0.95)}
M0_PTS = {"back wall near corner (0.467,0.385) [target 92-95]": (0.467, 0.385), "back wall behind sofa (0.69,0.22) [88-91]": (0.69, 0.22),
          "back wall right edge (0.97,0.31) [82-86]": (0.97, 0.31), "window wall (0.10,0.30)": (0.10, 0.30), "ceiling (0.55,0.04)": (0.55, 0.04),
          "sofa back (0.70,0.60)": (0.70, 0.60), "armchair seat (0.31,0.75)": (0.31, 0.75), "table top oak (0.62,0.715)": (0.62, 0.715)}
product_boxes = {}
if frame == "M0" or not sc_path:
    regions = dict(M0_REGIONS)
    pts = dict(M0_PTS)
    wb_pt = (0.467, 0.385)
    win_box = (0.19, 0.375, 0.025, 0.553)
else:
    sc = json.load(open(sc_path))["frames"][frame]
    regions = {"frame": (0.05, 0.95, 0.05, 0.95), "upper-left": (0.02, 0.50, 0.02, 0.50), "upper-right": (0.50, 0.98, 0.02, 0.50),
               "lower-left": (0.02, 0.50, 0.50, 0.98), "lower-right": (0.50, 0.98, 0.50, 0.98), "ceiling-band": (0.1, 0.9, 0.0, 0.14),
               "floor-band": (0.1, 0.9, 0.84, 1.0)}
    for nm, b in sc.get("boxes", {}).items():
        u0, u1, v0, v1 = b["box"]
        if b["kind"] in ("proxy", "proxy-transit"):
            product_boxes[nm] = b["box"]                       # every placeholder, the small counter / shelf items included
        if (u1 - u0) * (v1 - v0) < 0.004:
            continue                                           # lock regions need texture: skip the tiny boxes
        if b["kind"] in ("furniture", "window", "door", "architecture", "mirror"):
            regions[nm] = (max(0, u0 - 0.02), min(1, u1 + 0.02), max(0, v0 - 0.02), min(1, v1 + 0.02))
    pts = {}
    for k, v in sc.get("wall_patches", {}).items():
        if "L_hsl" in v:
            pts[f"{k} ({v['u']:.3f},{v['v']:.3f}) clay L {v['L_hsl']}"] = (v["u"], v["v"])
    wb = sc.get("wall_patches", {}).get("hero_wall_mid", {})
    wb_pt = (wb["u"], wb["v"]) if "L_hsl" in wb else (0.5, 0.3)
    win_box = None
    for nm, b in sc.get("boxes", {}).items():
        if b["kind"] == "window":
            win_box = tuple(b["box"])
    if frame == "H0":
        win_box = (0.26, 0.44, 0.05, 0.95)       # the living seen through the door = the brightest area
    if win_box is None:
        win_box = (0.0, 1.0, 0.0, 1.0)

lock = {}
for k, box in regions.items():
    u0, u1, v0, v1 = box
    x0, x1, y0, y1 = int(u0 * W), int(u1 * W), int(v0 * H), int(v1 * H)
    if x1 - x0 < 24 or y1 - y0 < 24:
        continue
    A = gc[y0:y1, x0:x1]
    B = gi[y0:y1, x0:x1]
    dx, dy, pk = phase_shift(A, B)
    n = ncc_at(A, gi, box, dx, dy)
    lock[k] = {"du": round(dx / W, 4), "dv": round(dy / H, 4), "peak": round(pk, 3), "ncc": None if n is None else round(n, 3)}
worst = max(max(abs(v["du"]), abs(v["dv"])) for v in lock.values())
worst_strong = max([max(abs(v["du"]), abs(v["dv"])) for v in lock.values() if v["peak"] >= 0.03] or [0.0])


def hsl_of(rgb):
    h, l, s = colorsys.rgb_to_hls(*[float(x) for x in rgb])
    return (round(h * 360, 1), round(s * 100, 1), round(l * 100, 1))


def patch(arr, u, v, w=0.01):
    hw = max(2, int(w * W / 2))
    x = int(u * W)
    y = int(v * H)
    return arr[max(0, y - hw):y + hw + 1, max(0, x - hw):x + hw + 1].reshape(-1, 3).mean(0)


def Lmap(arr):
    return (arr.max(2) + arr.min(2)) / 2 * 100


def measure(arr):
    out = {k: hsl_of(patch(arr, *p)) for k, p in pts.items()}
    L = Lmap(arr)
    wx0, wx1, wy0, wy1 = int(win_box[0] * W), int(win_box[1] * W), int(win_box[2] * H), int(win_box[3] * H)
    wl = L[wy0:wy1, wx0:wx1]
    sat = arr.max(2) >= 254.5 / 255
    out["brightest area (window / door): L p50 / p99 / max"] = (round(float(np.median(wl)), 1), round(float(np.percentile(wl, 99)), 1), round(float(wl.max()), 1))
    out["pixels with a 255 channel: inside / outside that area"] = (int(sat[wy0:wy1, wx0:wx1].sum()), int(sat.sum() - sat[wy0:wy1, wx0:wx1].sum()))
    k = max(4, int(0.005 * W))
    pm = sliding_window_view(L, (k, k))[::4, ::4].mean((2, 3))
    out["darkest 0.5% patch L [12-15]"] = round(float(pm.min()), 1)
    out["frame mean L"] = round(float(L.mean()), 1)
    if frame == "M0":
        reg = arr[int(0.87 * H):int(0.99 * H), int(0.42 * W):int(0.98 * W)].reshape(-1, 3)[::29]
        hls = np.array([colorsys.rgb_to_hls(*c) for c in reg])
        out["floor median HSL (u0.42-0.98,v0.87-0.99) [H30-40 S30-45 L68-78]"] = (round(float(np.median(hls[:, 0])) * 360, 1), round(float(np.median(hls[:, 2])) * 100, 1), round(float(np.median(hls[:, 1])) * 100, 1))
        Lm = np.asarray(Image.fromarray(L.astype(np.float32)).filter(ImageFilter.MedianFilter(3)))
        r = Lm[int(0.76 * H):int(0.83 * H), int(0.52 * W):int(0.84 * W)]
        out["contact shadow under sofa: min L / p1"] = (round(float(r.min()), 1), round(float(np.percentile(r, 1)), 1))
    return out


before = measure(a)

# ---- grade (recipe 2.6) ----------------------------------------------------------------------------------------
lin = s2l(a)
g = {}
cur = patch(a, *wb_pt)
h, l, s = colorsys.rgb_to_hls(*cur)
tgt = np.array(colorsys.hls_to_rgb(36 / 360, l, s))
cur_l, tgt_l = s2l(cur), s2l(tgt)
gain = (tgt_l / tgt_l.dot(Y)) / (cur_l / cur_l.dot(Y))
gain = np.clip(gain, 0.9, 1.1)
g["white_balance"] = {"patch": wb_pt, "H_before": round(h * 360, 1), "H_target": 36, "gains_rgb": [round(float(x), 4) for x in gain], "gain_clip": "0.9-1.1"}
lin = lin * gain
pl = s2l(patch(l2s(lin), *wb_pt)).dot(Y)
tl = s2l(np.array([target_L / 100] * 3)).dot(Y)
need = float(np.log2(tl / max(pl, 1e-6)))
stops = float(np.clip(need, -0.2, 0.2))
g["exposure"] = {"patch": wb_pt, "target_L": target_L, "needed_stops": round(need, 3), "applied_stops": round(stops, 3),
                 "flag": ("DARK: needs more than +0.2 stop, not lifted further" if need > 0.2 else ("bright: needs more than -0.2 stop" if need < -0.2 else "within cap"))}
lin = lin * 2 ** stops
lum = (lin * Y).sum(2, keepdims=True)
lin = lum + 0.90 * (lin - lum)
g["saturation"] = "chroma x0.90 (linear, toward luminance)"
k_knee = float(s2l(np.array(0.94)))
cap = float(s2l(np.array(0.9725)))
m = lin.max(2, keepdims=True)
mc = np.where(m > k_knee, k_knee + (cap - k_knee) * (1 - np.exp(-(m - k_knee) / (cap - k_knee))), m)
lin = lin * np.where(m > 0, mc / np.maximum(m, 1e-6), 1)
g["highlight_rolloff"] = {"knee_L": 94, "asymptote_L": 97.25, "on": "max channel, hue kept"}
sr = np.clip(l2s(lin), 0, 1)
mix = 0.12
sr = (1 - mix) * sr + mix * (sr * sr * (3 - 2 * sr))
g["s_curve"] = {"mix": mix, "shape": "smoothstep blend"}
Lg = Lmap(sr)
kk = max(4, int(0.005 * W))
dmin = float(sliding_window_view(Lg, (kk, kk))[::4, ::4].mean((2, 3)).min())
if dmin < 12.0:
    bp = (0.125 - dmin / 100) / (1 - dmin / 100)
    sr = bp + (1 - bp) * sr
    g["black_point"] = {"darkest_patch_L_before": round(dmin, 1), "lift_to_L": 12.5, "blend": round(float(bp), 4)}
else:
    g["black_point"] = {"darkest_patch_L_before": round(dmin, 1), "lift": "none (already >= 12)"}
g["grain"] = "none"
g["vignette"] = "none"
graded = np.clip(sr, 0, 1)
gim = Image.fromarray((graded * 255 + 0.5).astype(np.uint8))
gim.save(os.path.join(out_dir, aid + "-graded.png"))
after = measure(graded)

# ---- overlays for QA: product boxes (+-15 %) and clay edges -------------------------------------------------------
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(14, W // 110))
except Exception:
    font = ImageFont.load_default()
ov = gim.copy()
dr = ImageDraw.Draw(ov, "RGBA")
for nm, (u0, u1, v0, v1) in sorted(product_boxes.items()):
    x0, y0, x1, y1 = u0 * W, v0 * H, u1 * W, v1 * H
    dr.rectangle((x0, y0, x1, y1), outline=(255, 70, 40, 230), width=max(2, W // 900))
    pw, ph = (x1 - x0) * 0.15, (y1 - y0) * 0.15          # the +-15 % tolerance band (of the box size)
    dr.rectangle((x0 - pw, y0 - ph, x1 + pw, y1 + ph), outline=(255, 200, 60, 160), width=1)
    lab = nm.split("/", 1)[-1]
    tw = dr.textlength(lab, font=font)
    dr.rectangle((x0, max(0, y0 - font.size - 4), x0 + tw + 8, max(0, y0 - font.size - 4) + font.size + 4), fill=(255, 255, 255, 210))
    dr.text((x0 + 4, max(0, y0 - font.size - 4) + 1), lab, fill=(180, 30, 10, 255), font=font)
ov.save(os.path.join(out_dir, aid + "-boxes.png"))
edges = (gc > np.percentile(gc, 97)).astype(np.uint8)
edge_im = Image.fromarray(edges * 255).filter(ImageFilter.MaxFilter(3))
lk = gim.copy()
red = Image.new("RGB", (W, H), (255, 30, 30))
lk.paste(red, (0, 0), Image.fromarray((np.asarray(edge_im) * 0.75).astype(np.uint8)))
lk.save(os.path.join(out_dir, aid + "-lock.png"))

res = {"asset_id": aid, "frame": frame, "raw": raw_copy, "returned_size_px": [W0, H0], "normalised_size_px": [W, H],
       "resize_16_9": ("non-uniform resize %dx%d -> %dx%d (%+.2f%% vertical), no crop" % (W0, H0, W, H, (H / H0 - 1) * 100)) if resized else "none needed",
       "clay": clay_path, "clay_selfcheck": sc_path, "clay_lock": lock, "clay_lock_worst_abs_shift": round(worst, 4),
       "clay_lock_worst_abs_shift_strong_peaks": round(worst_strong, 4), "clay_lock_pass_0_02_strong_peaks": bool(worst_strong <= 0.02),
       "clay_lock_note": "regions = whole frame, quadrants, ceiling/floor bands and the clay boxes of fixed furniture / windows / openings; "
                         "peaks below ~0.03 are unreliable (weak texture), so the verdict is visual (<aid>-lock.png) with the strong-peak number as support",
       "product_boxes_clay": product_boxes, "product_box_rule": "each product inside its clay box +-15 % of the box size (<aid>-boxes.png); read visually",
       "grade_target_L": target_L, "measure_before": before, "grade": g, "measure_after": after}
json.dump(res, open(os.path.join(out_dir, aid + "-measurements.json"), "w"), indent=1, ensure_ascii=False)
print("==", aid, W0, "x", H0, "->", W, "x", H, "| lock worst", round(worst, 4), "strong", round(worst_strong, 4),
      "PASS" if worst_strong <= 0.02 else "CHECK", "| exposure", g["exposure"]["needed_stops"], "->", g["exposure"]["applied_stops"],
      g["exposure"]["flag"], "| WB H", g["white_balance"]["H_before"], "| black", g["black_point"])
for k, v in lock.items():
    print("   lock", k, v)
for k in before:
    print("   %-78s %s -> %s" % (k[:78], before[k], after[k]))
