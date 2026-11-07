"""
qa-agent 2026-11-07: G1.4 (shell lock) on the warm-modern pilot's shell-v2, with QA's own projection (house plan 1.3.5, the camera
record of docs/house-plan.json) and QA's named-edge reader, on every named line including the back-wall floor line (WMC10: the
skirting stands 1.5 cm proud, so the floor line is Y 0.015, Z 0). The same lines are read on the clay r4 shell layer (the reference)
and on shell-v2, raw (no affine): per line the median and p90 of |offset| in px at 1920. Writes data/shell-lock.json and
overlays/shell-v2-named-lines.jpg. Usage: ~/.venvs/motion/bin/python -I shell_lock.py
"""
import importlib.util
import json
import math
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
spec = importlib.util.spec_from_file_location("r1", os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py"))
r1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r1)
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
CLAY = os.path.join(REPO, "assets/blockout/house/framing/warm-modern-r4/layers/shell/M0.png")
CAM = r1.CAM["M0"]
LINES = {
    "glazing back jamb (X -2.30, Y 0.75)": ((-2.30, 0.75, 0.50), (-2.30, 0.75, 2.65)),
    "glazing head (Z 2.70)": ((-2.30, 0.80, 2.70), (-2.30, 2.60, 2.70)),
    "bench front top edge (X -1.98, Z 0.45)": ((-1.98, 1.05, 0.45), (-1.98, 2.60, 0.45)),
    "bench back-end front corner (X -1.98, Y 1.00)": ((-1.98, 1.00, 0.03), (-1.98, 1.00, 0.42)),
    "bench back-end top edge (Y 1.00, Z 0.45)": ((-2.28, 1.00, 0.45), (-2.00, 1.00, 0.45)),
    "back wall ceiling line (Y 0, Z 3.00)": ((-1.80, 0.0, 3.0), (1.90, 0.0, 3.0)),
    "back wall floor line (Y 0.015, Z 0; WMC10)": ((-1.60, 0.015, 0.0), (1.90, 0.015, 0.0)),
    "ceiling band bottom edge (X -2.05, Z 2.82)": ((-2.05, 0.40, 2.82), (-2.05, 3.60, 2.82)),
    "mullion (Y 1.45, frame plane X -2.65)": ((-2.65, 1.45, 0.55), (-2.65, 1.45, 2.60)),
    "mullion (Y 2.15, frame plane X -2.65)": ((-2.65, 2.15, 0.55), (-2.65, 2.15, 2.60)),
}


def gray(img):
    return cv2.GaussianBlur(np.asarray(img.convert("L")).astype(np.float32), (0, 0), 1.0)


def measure(g, W, H, A, B, n=48, half=None):
    half = half or int(round(20 * W / 3840))
    offs, strong = [], []
    for k in range(n):
        t = (k + 0.5) / n
        P0 = [A[i] + (B[i] - A[i]) * t for i in range(3)]
        P1 = [A[i] + (B[i] - A[i]) * min(1, t + 0.01) for i in range(3)]
        u0, v0, d0 = r1.project(CAM, *P0)
        u1, v1, _ = r1.project(CAM, *P1)
        if d0 <= 0.1 or not (0.01 < u0 < 0.99 and 0.01 < v0 < 0.99):
            continue
        x0, y0, x1, y1 = u0 * W, v0 * H, u1 * W, v1 * H
        L = math.hypot(x1 - x0, y1 - y0) or 1.0
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        s = np.arange(-half, half + 1, dtype=np.float32)
        prof = cv2.remap(g, (x0 + nx * s).reshape(1, -1).astype(np.float32), (y0 + ny * s).reshape(1, -1).astype(np.float32), cv2.INTER_LINEAR)[0]
        gr = np.abs(np.gradient(prof))
        i = int(np.argmax(gr))
        offs.append(float(s[i]))
        strong.append(gr[i] > 3 * max(float(np.median(gr)), 0.2))
    if not offs:
        return dict(in_frame=False)
    o = np.array(offs)[np.array(strong)] if any(strong) else np.array(offs)
    k = 1920 / W
    return dict(samples=len(offs), strong=int(sum(strong)), median_px_1920=round(float(np.median(o)) * k, 1),
                p90_abs_px_1920=round(float(np.percentile(np.abs(o), 90)) * k, 1))


def xcorr_line(gc, gr, A, B, n=48, half=30, search=12):
    """render vs clay at 1920 x 1080: per sample on the projected line, the gradient profiles across it (+-half px) in both, and the shift
    (+-search) that best aligns the render's to the clay's (normalised cross-correlation); kept when both profiles have a clear peak"""
    W, H = 1920, 1080
    shifts = []
    for k in range(n):
        t = (k + 0.5) / n
        P0 = [A[i] + (B[i] - A[i]) * t for i in range(3)]
        P1 = [A[i] + (B[i] - A[i]) * min(1, t + 0.01) for i in range(3)]
        u0, v0, d0 = r1.project(CAM, *P0)
        u1, v1, _ = r1.project(CAM, *P1)
        if d0 <= 0.1 or not (0.02 < u0 < 0.98 and 0.02 < v0 < 0.98):
            continue
        x0, y0, x1, y1 = u0 * W, v0 * H, u1 * W, v1 * H
        L = math.hypot(x1 - x0, y1 - y0) or 1.0
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        s_ = np.arange(-half - search, half + search + 1, dtype=np.float32)
        xs, ys = (x0 + nx * s_).reshape(1, -1).astype(np.float32), (y0 + ny * s_).reshape(1, -1).astype(np.float32)
        pc = np.abs(np.gradient(cv2.remap(gc, xs, ys, cv2.INTER_LINEAR)[0]))
        pr = np.abs(np.gradient(cv2.remap(gr, xs, ys, cv2.INTER_LINEAR)[0]))
        c = pc[search:search + 2 * half + 1]
        if c.max() < 3 * max(float(np.median(c)), 0.2) or pr.max() < 3 * max(float(np.median(pr)), 0.2):
            continue
        best, bs = -2, 0
        for sh in range(-search, search + 1):
            r = pr[search + sh:search + sh + 2 * half + 1]
            cc = np.corrcoef(c, r)[0, 1] if r.std() > 0 and c.std() > 0 else -1
            if cc > best:
                best, bs = cc, sh
        if best > 0.5:
            shifts.append(bs)
    if not shifts:
        return dict(samples=0)
    a_ = np.abs(np.array(shifts))
    return dict(samples=len(shifts), median_px=float(np.median(shifts)), p90_abs_px=float(np.percentile(a_, 90)))


def canvas_uv(u, v):
    """frame uv -> uv of the 3 % overscan canvas (the clay M0.png and the pilot renders are the whole canvas)"""
    return (116 + u * 3840) / 4072, (65 + v * 2160) / 2290


def peaks(prof, rel=0.25):
    thr = rel * prof.max()
    return [i for i in range(1, len(prof) - 1) if prof[i] >= thr and prof[i] >= prof[i - 1] and prof[i] >= prof[i + 1]]


def nearest_peak_line(gc, gr, A, B, n=48, half=18, pair=10):
    """at 1920 x 1080: per sample, the clay's strongest gradient peak within +-half of the projected line, then the render's nearest peak
    within +-pair of it (every render peak is considered, the nearest wins, as shell_m0s.py on 11-05); the offset render - clay"""
    W, H = 1920, 1080
    offs = []
    for k in range(n):
        t = (k + 0.5) / n
        P0 = [A[i] + (B[i] - A[i]) * t for i in range(3)]
        P1 = [A[i] + (B[i] - A[i]) * min(1, t + 0.01) for i in range(3)]
        u0, v0, d0 = r1.project(CAM, *P0)
        u1, v1, _ = r1.project(CAM, *P1)
        u0, v0 = canvas_uv(u0, v0)
        u1, v1 = canvas_uv(u1, v1)
        if d0 <= 0.1 or not (0.02 < u0 < 0.98 and 0.02 < v0 < 0.98):
            continue
        x0, y0, x1, y1 = u0 * W, v0 * H, u1 * W, v1 * H
        L = math.hypot(x1 - x0, y1 - y0) or 1.0
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        s_ = np.arange(-half - pair, half + pair + 1, dtype=np.float32)
        xs, ys = (x0 + nx * s_).reshape(1, -1).astype(np.float32), (y0 + ny * s_).reshape(1, -1).astype(np.float32)
        pc = np.abs(np.gradient(cv2.remap(gc, xs, ys, cv2.INTER_LINEAR)[0]))
        pr = np.abs(np.gradient(cv2.remap(gr, xs, ys, cv2.INTER_LINEAR)[0]))
        core = pc[pair:pair + 2 * half + 1]
        if core.max() < 3 * max(float(np.median(pc)), 0.3):
            continue
        ic = pair + int(np.argmax(core))
        cand = [i for i in peaks(pr) if abs(i - ic) <= pair and pr[i] > 2 * max(float(np.median(pr)), 0.3)]
        if not cand:
            offs.append(None)
            continue
        offs.append(min(cand, key=lambda i: abs(i - ic)) - ic)
    got = [o for o in offs if o is not None]
    if not got:
        return dict(samples=len(offs), paired=0)
    a_ = np.abs(np.array(got, float))
    return dict(samples=len(offs), paired=len(got), median_px=float(np.median(got)), p90_abs_px=float(np.percentile(a_, 90)), max_abs_px=float(a_.max()))


if __name__ == "__main__":
    clay = Image.open(CLAY).convert("RGB").resize((1920, 1080), Image.LANCZOS)
    gc = gray(clay)
    out = {"method": "render vs clay r4 shell layer at 1920 x 1080, no affine: per sample on each named plan line, the clay peak within +-18 px of the projection and the nearest render peak within +-10 px of it; median, p90 and max of |offset|; unpaired = no render edge within 10 px"}
    for name in ("shell-v2.png", "shell.png", "shell-furniture-v2.png"):
        gr = gray(Image.open(os.path.join(P, name)).convert("RGB").resize((1920, 1080), Image.LANCZOS))
        out[name] = {ln: nearest_peak_line(gc, gr, A, B) for ln, (A, B) in LINES.items()}
    out["plan_vs_clay"] = {ln: measure(gray(Image.open(CLAY).convert("RGB").crop((116, 65, 3956, 2225))), 3840, 2160, A, B) for ln, (A, B) in LINES.items()}
    sv = Image.open(os.path.join(P, "shell-v2.png")).convert("RGB")
    im = cv2.cvtColor(np.asarray(sv), cv2.COLOR_RGB2BGR)
    W, H = sv.size
    for ln, (A, B) in LINES.items():
        pts = []
        for k in range(60):
            t = k / 59
            Pt = [A[i] + (B[i] - A[i]) * t for i in range(3)]
            u, v, d = r1.project(CAM, *Pt)
            u, v = canvas_uv(u, v)
            if d > 0.1:
                pts.append((int(u * W), int(v * H)))
        for p, q in zip(pts[:-1], pts[1:]):
            cv2.line(im, p, q, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(OUT, "overlays", "shell-v2-named-lines.jpg"), cv2.resize(im, (1920, 1080)), [cv2.IMWRITE_JPEG_QUALITY, 85])
    json.dump(out, open(os.path.join(OUT, "data", "shell-lock.json"), "w"), indent=1)
    for name in ("shell-v2.png", "shell-furniture-v2.png", "plan_vs_clay"):
        print("==", name)
        for ln, m in out[name].items():
            print("  ", ln, m)
