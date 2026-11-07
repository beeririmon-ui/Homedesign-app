#!/usr/bin/env python3
"""
lock_wm.py: the warm-modern pilot's lock (briefs/render-warm-modern-pilot-phase1-2026-11-07.md, M0S1 method), render-agent, 2026-11-07.
0 var2 tokens. A render (any size, overscan canvas or 16:9 frame) against a clay of the same camera (M0 1.2):
  1. lock_v2 (assets/renders/house-nordic-v7-2026-11-02/lock_v2.py, edges v3, unchanged): ECC register (shift, scale), bands and tiles
     after register, box edges of the clay selfcheck's architecture / furniture boxes (warm-modern r4 selfcheck, given per call).
  2. NAMED LINES: QA's 3D lines of the warm-modern plan (qa/reports/2026-11-07-ged-codefix5-clay-r3/tools/clay_wm_r3.py LINES, the shell
     ones; the back-wall floor line INCLUDED after WMC10, house plan 1.3.5), plus the two glazing mullions (frame plane X -2.65), projected
     with QA's projection (clay_wm_r1.project). For each line, samples every ~12 px along it: a 1-D gradient profile across the line
     (31 px band along it) in the clay and in the render; the clay edge = its strongest peak within +-6 px of the projected line, the
     render offset = normalised cross-correlation of the profiles (+-40 px), counted when r >= 0.5 and the clay edge has strength.
     Per line: median, IQR, max |d| at 1920, raw and after undoing lock_v2's global affine (what code may apply to the whole frame).
Verdict (G1.4 master as in M0S1; the proposal's row 2: register shift <= 2 px, edges <= 9.6 px): every named line's p90 |d| <= 9.6 px
after the global affine, the affine's shift <= 9.6 px and scale within 0.5 % recorded (code applies it).
  python3 lock_wm.py <render> <clay> <out.json> [--overlay out.jpg] [--boxes shell|furn|all] [--selfcheck path]
"""
import argparse
import importlib.util
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "assets/renders/house-nordic-v7-2026-11-02"))
import lock_v2 as L2  # noqa: E402

spec = importlib.util.spec_from_file_location("qa_r1", os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py"))
r1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r1)
CAM = r1.CAM["M0"]
W, H = 1920, 1080
LIMIT = 9.6
SELFCHECK = os.path.join(REPO, "assets/blockout/house/framing/warm-modern-r4/selfcheck-render-A.json")

# QA's shell lines (clay_wm_r3.py LINES without the curtain stack, which is a product) + the two mullions in the frame plane (X -2.65, as the r4 clay checks)
LINES = {
    "glazing back jamb (X -2.30, Y 0.75)": ((-2.30, 0.75, 0.50), (-2.30, 0.75, 2.65)),
    "glazing head (Z 2.70)": ((-2.30, 0.80, 2.70), (-2.30, 2.60, 2.70)),
    "bench front top edge (X -1.98, Z 0.45)": ((-1.98, 1.05, 0.45), (-1.98, 2.60, 0.45)),
    "bench back-end front corner (X -1.98, Y 1.00)": ((-1.98, 1.00, 0.03), (-1.98, 1.00, 0.42)),
    "bench back-end top edge (Y 1.00, Z 0.45)": ((-2.28, 1.00, 0.45), (-2.00, 1.00, 0.45)),
    "back wall ceiling line (Y 0, Z 3.00)": ((-1.80, 0.0, 3.0), (1.90, 0.0, 3.0)),
    "back wall floor line (Y 0, Z 0; WMC10)": ((-1.60, 0.0, 0.0), (1.90, 0.0, 0.0)),
    "ceiling band bottom edge (X -2.05, Z 2.82)": ((-2.05, 0.40, 2.82), (-2.05, 3.60, 2.82)),
    "mullion (Y 1.45, frame plane X -2.65)": ((-2.65, 1.45, 0.50), (-2.65, 1.45, 2.65)),
    "mullion (Y 2.15, frame plane X -2.65)": ((-2.65, 2.15, 0.50), (-2.65, 2.15, 2.65)),
}
# lines that furniture covers in a furnished frame are measured only where the clay shows them (the clay of the same layer)


def frame16(img):
    h, w = img.shape[:2]
    if abs(w / h - 4072 / 2290) < 0.004 and w != 1920:
        x0, y0 = int(round(116 / 4072 * w)), int(round(65 / 2290 * h))
        x1, y1 = int(round(3956 / 4072 * w)), int(round(2225 / 2290 * h))
        img = img[y0:y1, x0:x1]
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0


def gray(img):
    g = cv2.cvtColor(np.clip(img * 255, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    return cv2.GaussianBlur(g, (0, 0), 1.0)


def xcorr(pc, pr, half=40):
    n = len(pc)
    c0 = n // 2
    a = pc[half:n - half].astype(np.float64)
    if a.std() < 1e-6:
        return None, 0.0
    a = (a - a.mean()) / a.std()
    best, bo = -1.0, 0
    for o in range(-half, half + 1):
        b = pr[half + o:n - half + o].astype(np.float64)
        if b.std() < 1e-6:
            continue
        b = (b - b.mean()) / b.std()
        r = float((a * b).mean())
        if r > best:
            best, bo = r, o
    return bo, best


def line_samples(P0, P1, step_px=12):
    u0, v0, _ = r1.project(CAM, *P0)
    u1, v1, _ = r1.project(CAM, *P1)
    x0, y0, x1, y1 = u0 * W, v0 * H, u1 * W, v1 * H
    n = max(2, int(np.hypot(x1 - x0, y1 - y0) / step_px))
    t = np.linspace(0.04, 0.96, n)
    xs, ys = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
    horiz = abs(x1 - x0) >= abs(y1 - y0)
    return xs, ys, horiz, (u0, v0, u1, v1)


def measure_line(gc, gr, P0, P1, keep=None):
    xs, ys, horiz, uv = line_samples(P0, P1)
    offs, rs, used = [], [], []
    half, span, band = 40, 52, 15
    for x, y in zip(xs, ys):
        xi, yi = int(round(x)), int(round(y))
        if not (span + 2 <= (yi if horiz else xi) < (H if horiz else W) - span - 2):
            continue
        if not (band <= (xi if horiz else yi) < (W if horiz else H) - band):
            continue
        if keep is not None and not keep[min(max(yi, 0), H - 1), min(max(xi, 0), W - 1)]:
            continue
        if horiz:
            pc = np.abs(np.diff(gc[yi - span:yi + span + 1, xi - band:xi + band + 1], axis=0)).mean(1)
            pr = np.abs(np.diff(gr[yi - span:yi + span + 1, xi - band:xi + band + 1], axis=0)).mean(1)
        else:
            pc = np.abs(np.diff(gc[yi - band:yi + band + 1, xi - span:xi + span + 1], axis=1)).mean(0)
            pr = np.abs(np.diff(gr[yi - band:yi + band + 1, xi - span:xi + span + 1], axis=1)).mean(0)
        c = len(pc) // 2
        if pc[c - 6:c + 7].max() < 1.0:            # no clay edge at this sample (hidden or too soft)
            continue
        o, r = xcorr(pc, pr, half)
        if o is None or r < 0.5:
            continue
        offs.append(o)
        rs.append(r)
        used.append((xi, yi))
    if not offs:
        return dict(samples=len(xs), counted=0, uv=[round(v, 4) for v in uv], horizontal=horiz)
    a = np.abs(np.array(offs, float))
    return dict(samples=len(xs), counted=len(offs), median_px=float(np.median(offs)), iqr_px=[float(np.percentile(offs, 25)), float(np.percentile(offs, 75))],
                p90_abs_px=round(float(np.percentile(a, 90)), 2), max_abs_px=float(a.max()), mean_r=round(float(np.mean(rs)), 3),
                uv=[round(v, 4) for v in uv], horizontal=horiz, points=used, offsets=offs)


def boxes_from_selfcheck(path, which):
    sc = json.load(open(path))["frames"]["M0"]
    kinds = {"shell": ("architecture",), "furn": ("furniture",), "all": ("architecture", "furniture")}[which]
    out = {}
    for nm, b in sc["boxes"].items():
        if b["kind"] in kinds and b["px"] / (4072 * 2290) >= 0.002:
            u0, u1, v0, v1 = b["box"]
            # canvas uv -> 16:9 frame uv
            fu = lambda u: (u * 4072 - 116) / 3840
            fv = lambda v: (v * 2290 - 65) / 2160
            out[nm] = (b["kind"], (fu(u0), fu(u1), fv(v0), fv(v1)))
    return out


def run(render_path, clay_path, out_path, overlay=None, which="shell", selfcheck=SELFCHECK, lines=None, keep_mask=None):
    r, c = frame16(load(render_path)), frame16(load(clay_path))
    rep = L2.lock_v2(r, c, "M0", boxes_from_selfcheck(selfcheck, which), True, frame_id="wm-pilot")
    M = np.array(rep["register"]["affine"], np.float32)      # clay -> render
    reg = cv2.warpAffine(r, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    gc, gr, gg = gray(c), gray(r), gray(reg)
    named = {}
    for nm, (P0, P1) in (lines or LINES).items():
        raw = measure_line(gc, gr, P0, P1, keep_mask)
        aff = measure_line(gc, gg, P0, P1, keep_mask)
        named[nm] = dict(raw={k: v for k, v in raw.items() if k not in ("points", "offsets")},
                         after_affine={k: v for k, v in aff.items() if k not in ("points", "offsets")}, _pts=raw.get("points"), _offs=raw.get("offsets"))
    worst_raw = max([v["raw"].get("p90_abs_px", 0) for v in named.values() if v["raw"].get("counted")] or [None])
    worst_aff = max([v["after_affine"].get("p90_abs_px", 0) for v in named.values() if v["after_affine"].get("counted")] or [None])
    uncounted = [k for k, v in named.items() if not v["raw"].get("counted")]
    sh = rep["register"]["shift_px"]
    sc = rep["register"]["scale"]
    out = dict(render=os.path.relpath(render_path, REPO), clay=os.path.relpath(clay_path, REPO), size=[W, H], boxes=which,
               method="lock_wm: lock_v2 edges v3 + QA's warm-modern named lines (3D, QA's projection), per-sample xcorr across the line",
               lock_v2=dict(register=rep["register"], summary=rep.get("summary"), verdict=rep.get("verdict"), fixed_edges=rep.get("fixed_edges")),
               named_lines={k: dict(raw=v["raw"], after_affine=v["after_affine"]) for k, v in named.items()},
               summary=dict(named_worst_p90_raw_px=worst_raw, named_worst_p90_after_affine_px=worst_aff, named_not_measured=uncounted,
                            shift_px=sh, scale=sc),
               verdict=dict(named_raw_pass=bool(worst_raw is not None and worst_raw <= LIMIT),
                            named_after_affine_pass=bool(worst_aff is not None and worst_aff <= LIMIT),
                            shift_le_9_6=bool(max(abs(sh[0]), abs(sh[1])) <= LIMIT), scale_within_0_5pct=bool(max(abs(sc[0] - 1), abs(sc[1] - 1)) <= 0.005),
                            rule="G1.4 master (M0S1): every named line within 9.6 px (p90 of its samples) raw or after one global affine (code)"))
    out["verdict"]["pass"] = bool(out["verdict"]["named_after_affine_pass"] and out["verdict"]["shift_le_9_6"])
    json.dump(out, open(out_path, "w"), indent=1)
    if overlay:
        im = (np.clip(r, 0, 1) * 255).astype(np.uint8).copy()
        cl = (np.clip(c, 0, 1) * 255).astype(np.uint8)
        im = cv2.addWeighted(im, 0.75, cl, 0.25, 0)
        for nm, v in named.items():
            uv = v["raw"]["uv"]
            cv2.line(im, (int(uv[0] * W), int(uv[1] * H)), (int(uv[2] * W), int(uv[3] * H)), (230, 40, 40), 1, cv2.LINE_AA)
            for (x, y), o in zip(v["_pts"] or [], v["_offs"] or []):
                if v["raw"]["horizontal"]:
                    cv2.circle(im, (x, y + o), 2, (40, 200, 60) if abs(o) <= LIMIT else (250, 160, 0), -1)
                else:
                    cv2.circle(im, (x + o, y), 2, (40, 200, 60) if abs(o) <= LIMIT else (250, 160, 0), -1)
        Image.fromarray(im).save(overlay, quality=90)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("render")
    ap.add_argument("clay")
    ap.add_argument("out")
    ap.add_argument("--overlay")
    ap.add_argument("--boxes", default="shell", choices=["shell", "furn", "all"])
    ap.add_argument("--selfcheck", default=SELFCHECK)
    a = ap.parse_args()
    o = run(a.render, a.clay, a.out, a.overlay, a.boxes, a.selfcheck)
    print(json.dumps(o["summary"]), json.dumps(o["verdict"]))
    for k, v in o["named_lines"].items():
        print(f"  {k:48s} raw med {v['raw'].get('median_px')} p90 {v['raw'].get('p90_abs_px')} n {v['raw'].get('counted')}/{v['raw'].get('samples')}"
              f" | aff med {v['after_affine'].get('median_px')} p90 {v['after_affine'].get('p90_abs_px')}")
