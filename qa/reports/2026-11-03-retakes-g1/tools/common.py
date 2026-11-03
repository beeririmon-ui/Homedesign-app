"""
qa-agent, G1 on the v8 retakes of 2026-11-03 and the grading v3 of the v7 set: shared registry and loaders.
Read-only on assets/; everything written goes under qa/reports/2026-11-03-retakes-g1/.
Run with ~/.venvs/motion/bin/python (OpenCV, numpy, Pillow). No network, no installs, no var2.
The frame geometry (overscan canvas 4072x2290 -> 16:9 crop) is the same as qa/reports/2026-11-02-v7-g1/tools/common.py.
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-03-retakes-g1")
R4 = os.path.join(REPO, "assets/blockout/house/framing/round4")
R3 = os.path.join(R4, "r3-2026-11-03")
sys.path.insert(0, os.path.join(REPO, "site/tools/transitions"))
import pan_reproject as pr  # noqa: E402

SC4 = json.load(open(os.path.join(R4, "selfcheck.json")))["frames"]
SC3 = json.load(open(os.path.join(R3, "selfcheck.json")))["frames"]
PLAN = json.load(open(os.path.join(R4, "plan.json")))
PLAN3 = json.load(open(os.path.join(R3, "plan.json")))
CANVAS = (4072, 2290)
CROP = (116, 65, 3956, 2225)

P = "assets/renders"
# id: (frame key, kind, graded-v3 file, raw normalised file (geometry), clay file, selfcheck ("r4" | "r3"), cam (yaw, u0, v0), overscan, room, base)
STILLS = {
    # the four v8 retakes (jobs-retakes-2026-11-03.json)
    "W0-in r2":    ("W0-in",    "retake", f"{P}/poses/nordic/v7/pose-w0-in-v7-r2-graded-v3.png",    f"{P}/poses/nordic/v7/pose-w0-in-v7-r2.png",    "poses/W0-in.png",    "r4", (0, .50, .46),  False, "work", "W0"),
    "K-girl-0 r2": ("K-girl-0", "retake", f"{P}/poses/nordic/v7/pose-k-girl-0-v7-r2-graded-v3.png", f"{P}/poses/nordic/v7/pose-k-girl-0-v7-r2.png", "poses/K-girl-0.png", "r4", (0, .50, .46),  True,  "girl", "K-girl"),
    "B1 r3":       ("B1",       "retake", f"{P}/bath/nordic/v7/b1-v7-r3-graded-v3.png",             f"{P}/bath/nordic/v7/b1-v7-r3.png",             "r3-2026-11-03/B1.png", "r3", (-22, .52, .46), True, "bath", "B1"),
    "B2 r3":       ("B2",       "retake", f"{P}/bath/nordic/v7/b2-v7-r3-graded-v3.png",             f"{P}/bath/nordic/v7/b2-v7-r3.png",             "r3-2026-11-03/B2.png", "r3", (-57, .52, .46), True, "bath", "B1"),
    # the 11 v7 masters, graded v3
    "M0":     ("M0",     "master", f"{P}/living-room/nordic/v7/m0-v7-r2-graded-v3.png",  f"{P}/living-room/nordic/v7/m0-v7-r2.png",  "M0.png",     "r4", (25, .52, .46),  False, "living", "M0"),
    "D1":     ("D1",     "master", f"{P}/kitchen-dining/nordic/v7/d1-v7-graded-v3.png", f"{P}/kitchen-dining/nordic/v7/d1-v7.png", "D1.png",     "r4", (-56, .52, .43), False, "kitchen-dining", "D1"),
    "D2":     ("D2",     "master", f"{P}/kitchen-dining/nordic/v7/d2-v7-graded-v3.png", f"{P}/kitchen-dining/nordic/v7/d2-v7.png", "D2.png",     "r4", (-91, .52, .43), True,  "kitchen-dining", "D1"),
    "H0":     ("H0",     "master", f"{P}/hall/nordic/v7/h0-v7-r2-graded-v3.png",        f"{P}/hall/nordic/v7/h0-v7-r2.png",        "H0.png",     "r4", (12, .52, .46),  False, "hall", "H0"),
    "C0":     ("C0",     "master", f"{P}/corridor/nordic/v7/c0-v7-graded-v3.png",       f"{P}/corridor/nordic/v7/c0-v7.png",       "C0.png",     "r4", (0, .50, .46),   False, "corridor", "C0"),
    "MB0":    ("MB0",    "master", f"{P}/master/nordic/v7/mb0-v7-r2-graded-v3.png",     f"{P}/master/nordic/v7/mb0-v7-r2.png",     "MB0.png",    "r4", (0, .50, .46),   False, "master", "MB0"),
    "K-boy":  ("K-boy",  "master", f"{P}/boy/nordic/v7/k-boy-v7-graded-v3.png",         f"{P}/boy/nordic/v7/k-boy-v7.png",         "K-boy.png",  "r4", (33, .52, .44),  True,  "boy", "K-boy"),
    "K-girl": ("K-girl", "master", f"{P}/girl/nordic/v7/k-girl-v7-graded-v3.png",       f"{P}/girl/nordic/v7/k-girl-v7.png",       "K-girl.png", "r4", (33, .52, .44),  True,  "girl", "K-girl"),
    "B1":     ("B1",     "master", f"{P}/bath/nordic/v7/b1-v7-graded-v3.png",           f"{P}/bath/nordic/v7/b1-v7.png",           "B1.png",     "r4", (-22, .52, .46), True,  "bath", "B1"),
    "B2":     ("B2",     "master", f"{P}/bath/nordic/v7/b2-v7-graded-v3.png",           f"{P}/bath/nordic/v7/b2-v7.png",           "B2.png",     "r4", (-57, .52, .46), True,  "bath", "B1"),
    "W0":     ("W0",     "master", f"{P}/work/nordic/v7/w0-v7-graded-v3.png",           f"{P}/work/nordic/v7/w0-v7.png",           "W0.png",     "r4", (0, .50, .46),   False, "work", "W0"),
    # the four zero-token code fixes, graded v3
    "K-boy fix":   ("K-boy",   "fix", f"{P}/boy/nordic/v7/k-boy-v7-graded-fix-v3.png",          None, "K-boy.png",         "r4", (33, .52, .44), True,  "boy", "K-boy"),
    "K-girl fix":  ("K-girl",  "fix", f"{P}/girl/nordic/v7/k-girl-v7-graded-fix-v3.png",        None, "K-girl.png",        "r4", (33, .52, .44), True,  "girl", "K-girl"),
    "W0 fix":      ("W0",      "fix", f"{P}/work/nordic/v7/w0-v7-graded-fix-v3.png",            None, "W0.png",            "r4", (0, .50, .46),  False, "work", "W0"),
    "K-boy-0 fix": ("K-boy-0", "fix", f"{P}/poses/nordic/v7/pose-k-boy-0-v7-graded-fix-v3.png", None, "poses/K-boy-0.png", "r4", (0, .50, .46),  True,  "boy", "K-boy"),
    # the 11 v7 poses, graded v3
    "H0x":      ("H0x",      "pose", f"{P}/poses/nordic/v7/pose-h0x-v7-graded-v3.png",      f"{P}/poses/nordic/v7/pose-h0x-v7.png",      "poses/H0x.png",      "r4", (25, .52, .46),  False, "hall", "H0"),
    "M0p":      ("M0p",      "pose", f"{P}/poses/nordic/v7/pose-m0p-v7-graded-v3.png",      f"{P}/poses/nordic/v7/pose-m0p-v7.png",      "poses/M0p.png",      "r4", (0, .52, .46),   True,  "living", "M0"),
    "M0x":      ("M0x",      "pose", f"{P}/poses/nordic/v7/pose-m0x-v7-graded-v3.png",      f"{P}/poses/nordic/v7/pose-m0x-v7.png",      "poses/M0x.png",      "r4", (-35, .52, .46), True,  "living", "M0"),
    "PD-35":    ("PD-35",    "pose", f"{P}/poses/nordic/v7/pose-pd-35-v7-graded-v3.png",    f"{P}/poses/nordic/v7/pose-pd-35-v7.png",    "poses/PD-35.png",    "r4", (-35, .52, .46), True,  "kitchen-dining", "D1"),
    "H0e":      ("H0e",      "pose", f"{P}/poses/nordic/v7/pose-h0e-v7-graded-v3.png",      f"{P}/poses/nordic/v7/pose-h0e-v7.png",      "poses/H0e.png",      "r4", (0, .50, .46),   False, "hall", "H0"),
    "W0-in":    ("W0-in",    "pose", f"{P}/poses/nordic/v7/pose-w0-in-v7-graded-v3.png",    f"{P}/poses/nordic/v7/pose-w0-in-v7.png",    "poses/W0-in.png",    "r4", (0, .50, .46),   False, "work", "W0"),
    "S1'":      ("S1prime",  "pose", f"{P}/poses/nordic/v7/pose-s1prime-v7-graded-v3.png",  f"{P}/poses/nordic/v7/pose-s1prime-v7.png",  "poses/S1prime.png",  "r4", (0, .50, .46),   False, "corridor", "C0"),
    "K-boy-0":  ("K-boy-0",  "pose", f"{P}/poses/nordic/v7/pose-k-boy-0-v7-graded-v3.png",  f"{P}/poses/nordic/v7/pose-k-boy-0-v7.png",  "poses/K-boy-0.png",  "r4", (0, .50, .46),   True,  "boy", "K-boy"),
    "K-girl-0": ("K-girl-0", "pose", f"{P}/poses/nordic/v7/pose-k-girl-0-v7-graded-v3.png", f"{P}/poses/nordic/v7/pose-k-girl-0-v7.png", "poses/K-girl-0.png", "r4", (0, .50, .46),   True,  "girl", "K-girl"),
    "CB-0":     ("CB-0",     "pose", f"{P}/poses/nordic/v7/pose-cb-0-v7-graded-v3.png",     f"{P}/poses/nordic/v7/pose-cb-0-v7.png",     "poses/CB-0.png",     "r4", (0, .50, .46),   True,  "bath", "B1"),
    "MB-in":    ("MB-in",    "pose", f"{P}/poses/nordic/v7/pose-mb-in-v7-graded-v3.png",    f"{P}/poses/nordic/v7/pose-mb-in-v7.png",    "poses/MB-in.png",    "r4", (0, .50, .46),   False, "master", "MB0"),
}
RETAKES = [k for k, v in STILLS.items() if v[1] == "retake"]
V3_ROWS = [k for k, v in STILLS.items() if v[1] in ("master", "fix", "pose")]       # the 26 rows of regrade-v3-summary.json

# the render-agent id of every still (regrade-v3-summary.json rows / jobs)
AGENT_ID = {"W0-in r2": "pose-w0-in-v7-r2", "K-girl-0 r2": "pose-k-girl-0-v7-r2", "B1 r3": "b1-v7-r3", "B2 r3": "b2-v7-r3",
            "M0": "m0-v7-r2", "D1": "d1-v7", "D2": "d2-v7", "H0": "h0-v7-r2", "C0": "c0-v7", "MB0": "mb0-v7-r2", "K-boy": "k-boy-v7",
            "K-girl": "k-girl-v7", "B1": "b1-v7", "B2": "b2-v7", "W0": "w0-v7", "K-boy fix": "k-boy-v7", "K-girl fix": "k-girl-v7",
            "W0 fix": "w0-v7", "K-boy-0 fix": "pose-k-boy-0-v7", "H0x": "pose-h0x-v7", "M0p": "pose-m0p-v7", "M0x": "pose-m0x-v7",
            "PD-35": "pose-pd-35-v7", "H0e": "pose-h0e-v7", "W0-in": "pose-w0-in-v7", "S1'": "pose-s1prime-v7", "K-boy-0": "pose-k-boy-0-v7",
            "K-girl-0": "pose-k-girl-0-v7", "CB-0": "pose-cb-0-v7", "MB-in": "pose-mb-in-v7"}

M0_FURNITURE = {"sofa (fixed-product)": (0.5208, 0.8396, 0.5509, 0.7949),
                "coffee table (fixed-product)": (0.512, 0.762, 0.6787, 0.8699),
                "armchair (fixed-product)": (0.1896, 0.3867, 0.6218, 0.9056)}


def fn(x):
    return x.replace("'", "prime").replace(" ", "_")


def rgb(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0


def crop_canvas(img):
    h, w = img.shape[:2]
    sx, sy = w / CANVAS[0], h / CANVAS[1]
    x0, y0, x1, y1 = CROP
    return img[int(round(y0 * sy)):int(round(y1 * sy)), int(round(x0 * sx)):int(round(x1 * sx))]


def canvas_uv_to_frame(u, v):
    x0, y0, x1, y1 = CROP
    return ((u * CANVAS[0] - x0) / (x1 - x0), (v * CANVAS[1] - y0) / (y1 - y0))


def box_to_frame(b, ovs):
    if not ovs:
        return tuple(b)
    u0, v0 = canvas_uv_to_frame(b[0], b[2])
    u1, v1 = canvas_uv_to_frame(b[1], b[3])
    return (u0, u1, v0, v1)


def selfcheck(sid):
    frame, kind, g, r, clay, sc, cam, ovs, room, base = STILLS[sid]
    return (SC3 if sc == "r3" else SC4)[frame]


def load(sid, raw=True):
    """graded-v3 (and the raw normalised still) and the clay, all as 16:9 frames (overscan cropped)."""
    frame, kind, g, r, clay, sc, cam, ovs, room, base = STILLS[sid]
    d = dict(id=sid, frame=frame, kind=kind, cam=pr.Cam(*cam), ovs=ovs, room=room, base=base, sc=selfcheck(sid),
             graded_file=g, raw_file=r, clay_file=os.path.join("assets/blockout/house/framing/round4", clay))
    gi = rgb(os.path.join(REPO, g))
    ci = rgb(os.path.join(R4, clay))
    ri = rgb(os.path.join(REPO, r)) if (raw and r) else None
    d["graded_size"] = list(gi.shape[:2][::-1])
    if ovs:
        d["graded_canvas"] = gi
        d["graded"], d["clay"] = crop_canvas(gi), crop_canvas(ci)
        d["raw"] = crop_canvas(ri) if ri is not None else None
        fp = os.path.join(REPO, g.replace("-graded-v3.png", "-frame-v3.png").replace("-graded-fix-v3.png", "-frame-fix-v3.png"))
        if os.path.exists(fp):
            fr = rgb(fp)
            d["frame_file"] = os.path.relpath(fp, REPO)
            d["frame_file_matches_crop"] = bool(fr.shape == d["graded"].shape and float(np.abs(fr - d["graded"]).max()) < 2 / 255)
            d["frame_file_max_diff"] = round(float(np.abs(fr - d["graded"]).max()) * 255, 2) if fr.shape == d["graded"].shape else None
    else:
        d["graded"], d["clay"], d["raw"] = gi, ci, ri
    return d


def at(img, w=1920, h=1080):
    return pr.fit(img, w, h)


def boxes(d):
    """Clay boxes in 16:9-frame uv: name -> (kind, (u0,u1,v0,v1), area_frac_of_canvas, visible_pct)."""
    sc = d["sc"]
    W, H = sc["resolution"]
    iv = sc.get("items_visible", {})
    out = {}
    for nm, b in sc.get("boxes", {}).items():
        vis = iv.get(nm, {}).get("visible_pct")
        out[nm] = (b["kind"], box_to_frame(b["box"], d["ovs"]), b["px"] / (W * H), vis)
    if d["frame"] == "M0":
        for nm, b in M0_FURNITURE.items():
            out[nm] = ("furniture", b, None, None)
    return out


def agent_measurements(sid):
    frame, kind, g, r, clay, sc, cam, ovs, room, base = STILLS[sid]
    m = g.replace("-graded-v3.png", "-measurements-v3.json").replace("-graded-fix-v3.png", "-measurements-fix-v3.json")
    p = os.path.join(REPO, m)
    if not os.path.exists(p) and kind == "fix":
        p = os.path.join(REPO, g.replace("-graded-fix-v3.png", "-measurements-v3.json"))
    return json.load(open(p)) if os.path.exists(p) else None


def agent_lock(sid):
    frame, kind, g, r, clay, sc, cam, ovs, room, base = STILLS[sid]
    if not r:
        return None
    p = os.path.join(REPO, r.replace(".png", "-lock-v2.json"))
    return json.load(open(p)) if os.path.exists(p) else None


for _d in ("data", "overlays"):
    os.makedirs(os.path.join(OUT, _d), exist_ok=True)
