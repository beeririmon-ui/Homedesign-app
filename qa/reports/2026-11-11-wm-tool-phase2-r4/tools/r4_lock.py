#!/usr/bin/env python3
"""
qa-agent 2026-11-11 (R4 box check): the shell lock of the r4 default scenes (and r3, for the before) against clay r4 (house plan 1.3.5), QA's nearest-peak reader of
qa/reports/2026-11-07-pilot-phase1-g1/tools/shell_lock.py (same projection, same named lines, same 1920 x 1080 scale, same rule:
every line p90 <= 9.6 px with >= 20 paired samples), with one addition: each sample is labelled by what covers the line there
(a phase-2 product's alpha, the fixed furniture's alpha, or nothing), so the lock is judged on the shell that is actually visible and a
product edge picked as the "nearest peak" is not read as shell drift.
Runs on base.png (= the approved v3c base) and the r3 and r4 default scenes A / B / C (copied from the checkpoint tool p2_lock.py; only the inputs and the output folder changed).
Writes data/lock.json.   ~/.venvs/motion/bin/python -I r4_lock.py
"""
import importlib.util
import json
import math
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
spec = importlib.util.spec_from_file_location("sl", os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1/tools/shell_lock.py"))
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r4")
man = json.load(open(os.path.join(P2, "layers/manifest-r4.json")))

W, H = 1920, 1080
prod = np.zeros((1530, 2720), np.float32)
for l_ in man["layers"]:
    if "product" in l_:
        prod = np.maximum(prod, np.asarray(Image.open(os.path.join(P2, "layers", l_["file"])))[..., 3].astype(np.float32))
for s in "ABC":
    prod = np.maximum(prod, np.asarray(Image.open(os.path.join(P2, "layers", man["slot_cushions"]["sets"][s]["layer"])))[..., 3].astype(np.float32))
prod = cv2.resize(prod, (W, H), interpolation=cv2.INTER_AREA) > 8
fur = np.asarray(Image.open(os.path.join(P1, "fixed-furniture.png")))[..., 3].astype(np.float32)
fur = cv2.resize(fur, (W, H), interpolation=cv2.INTER_AREA) > 8


def read(gc, gr, A, B, n=48, half=18, pair=10):
    rows = []
    for k in range(n):
        t = (k + 0.5) / n
        P0 = [A[i] + (B[i] - A[i]) * t for i in range(3)]
        P1_ = [A[i] + (B[i] - A[i]) * min(1, t + 0.01) for i in range(3)]
        u0, v0, d0 = sl.r1.project(sl.CAM, *P0)
        u1, v1, _ = sl.r1.project(sl.CAM, *P1_)
        u0, v0 = sl.canvas_uv(u0, v0)
        u1, v1 = sl.canvas_uv(u1, v1)
        if d0 <= 0.1 or not (0.02 < u0 < 0.98 and 0.02 < v0 < 0.98):
            continue
        x0, y0, x1, y1 = u0 * W, v0 * H, u1 * W, v1 * H
        Ln = math.hypot(x1 - x0, y1 - y0) or 1.0
        nx, ny = -(y1 - y0) / Ln, (x1 - x0) / Ln
        s_ = np.arange(-half - pair, half + pair + 1, dtype=np.float32)
        xs, ys = (x0 + nx * s_), (y0 + ny * s_)
        xi = np.clip(np.round(xs).astype(int), 0, W - 1)
        yi = np.clip(np.round(ys).astype(int), 0, H - 1)
        cover = "product" if prod[yi, xi][pair:pair + 2 * half + 1].any() else ("furniture" if fur[yi, xi][pair:pair + 2 * half + 1].any() else "none")
        xs, ys = xs.reshape(1, -1).astype(np.float32), ys.reshape(1, -1).astype(np.float32)
        pc = np.abs(np.gradient(cv2.remap(gc, xs, ys, cv2.INTER_LINEAR)[0]))
        pr = np.abs(np.gradient(cv2.remap(gr, xs, ys, cv2.INTER_LINEAR)[0]))
        core = pc[pair:pair + 2 * half + 1]
        if core.max() < 3 * max(float(np.median(pc)), 0.3):
            continue
        ic = pair + int(np.argmax(core))
        cand = [i for i in sl.peaks(pr) if abs(i - ic) <= pair and pr[i] > 2 * max(float(np.median(pr)), 0.3)]
        rows.append(dict(cover=cover, off=None if not cand else min(cand, key=lambda i: abs(i - ic)) - ic))
    return rows


def summ(rows, which=None):
    r = [x for x in rows if which is None or x["cover"] in which]
    got = [x["off"] for x in r if x["off"] is not None]
    if not got:
        return dict(samples=len(r), paired=0)
    a = np.abs(np.array(got, float))
    return dict(samples=len(r), paired=len(got), median_px=float(np.median(got)), p90_abs_px=float(np.percentile(a, 90)), max_abs_px=float(a.max()))


gc = sl.gray(Image.open(sl.CLAY).convert("RGB").resize((W, H), Image.LANCZOS))
out = {"method": __doc__.strip().splitlines()[1], "rule": "every named line p90 <= 9.6 px with >= 20 paired samples"}
files = {"base.png (approved v3c base)": os.path.join(P2, "layers/base.png")}
files.update({f"default-scene-{t}-set-{s}": os.path.join(P2, f"graded/default-scene-{t}-set-{s}-graded-v3c.png") for t in ("r3", "r4") for s in "BAC"})
for name, f in files.items():
    gr = sl.gray(Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS))
    rec = {}
    for ln, (A, B) in sl.LINES.items():
        rows = read(gc, gr, A, B)
        rec[ln] = dict(all=summ(rows), not_under_products=summ(rows, ("none", "furniture")), shell_only=summ(rows, ("none",)),
                       covered=dict(product=sum(x["cover"] == "product" for x in rows), furniture=sum(x["cover"] == "furniture" for x in rows)))
    allp = all(v["all"].get("p90_abs_px", 99) <= 9.6 and v["all"]["paired"] >= 20 for v in rec.values())
    nup = all(v["not_under_products"].get("p90_abs_px", 99) <= 9.6 and v["not_under_products"]["paired"] >= 20 for v in rec.values())
    out[name] = dict(lines=rec, pass_all_samples=bool(allp), pass_not_under_products=bool(nup),
                     worst_p90_all=max(v["all"].get("p90_abs_px", 99) for v in rec.values()),
                     worst_p90_not_under_products=max(v["not_under_products"].get("p90_abs_px", 99) for v in rec.values()))
json.dump(out, open(os.path.join(OUT, "data/lock.json"), "w"), indent=1)
for name in files:
    print(name, out[name]["pass_all_samples"], out[name]["worst_p90_all"], out[name]["pass_not_under_products"], out[name]["worst_p90_not_under_products"])
    for ln, v in out[name]["lines"].items():
        print("   ", ln, v["all"].get("p90_abs_px"), v["all"].get("paired"), "| not-under-products", v["not_under_products"].get("p90_abs_px"),
              v["not_under_products"].get("paired"), "| covered", v["covered"])
