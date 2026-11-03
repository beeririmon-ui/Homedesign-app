#!/usr/bin/env python3
"""
The 22 kept v7 stills (11 masters, 11 poses) of the Nordic walk-through test, as one registry for the zero-token
pipeline scripts (lock_v2.py, process_v8.py, regrade_v7.py, fix_v7.py). render-agent, 2026-11-03.

id          the job id in jobs.json (the kept attempt, per its verdict: r2 for M0, H0, MB0; attempt 1 for W0)
frame       the clay selfcheck key (assets/blockout/house/framing/round4/selfcheck.json -> frames)
clay        the round-4 clay still, relative to the round-4 folder
pan         True when the still is an endpoint of a pan built in code (docs/transitions-render-plan-2026-11-02.md
            section 5: T-E0 H0-H0x, T-LD M0-M0p-M0x and PD-35-D1, P-D D1-D2, T-HC H0e-H0, T-CGirl K-girl-0-K-girl,
            T-CBoy K-boy-0-K-boy, T-CBath CB-0-B1, P-B B1-B2, T-HW H0-H0e). Gate G1.4 then asks <= 2 px per strip
            after register; a still that is only a video endpoint (C0, S1', W0, W0-in, MB0, MB-in) gets 0.5 % (9.6 px).
overscan    the still is a 4072x2290-equivalent canvas (output 2736x1539) whose 16:9 frame is the centre crop
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
R4 = os.path.join(REPO, "assets", "blockout", "house", "framing", "round4")
CANVAS = (4072, 2290)
CROP = (116, 65, 3956, 2225)          # canvas -> 16:9 frame (plan.json overscan.crop_box_px)

FRAMES = {
    # id            frame      kind      clay                   pan    overscan  room
    "m0-v7-r2":        ("M0",       "master", "M0.png",              True,  False, "living-room"),
    "d1-v7":           ("D1",       "master", "D1.png",              True,  False, "kitchen-dining"),
    "d2-v7":           ("D2",       "master", "D2.png",              True,  True,  "kitchen-dining"),
    "h0-v7-r2":        ("H0",       "master", "H0.png",              True,  False, "hall"),
    "c0-v7":           ("C0",       "master", "C0.png",              False, False, "corridor"),
    "mb0-v7-r2":       ("MB0",      "master", "MB0.png",             False, False, "master"),
    "k-boy-v7":        ("K-boy",    "master", "K-boy.png",           True,  True,  "boy"),
    "k-girl-v7":       ("K-girl",   "master", "K-girl.png",          True,  True,  "girl"),
    "b1-v7":           ("B1",       "master", "B1.png",              True,  True,  "bath"),
    "b2-v7":           ("B2",       "master", "B2.png",              True,  True,  "bath"),
    "w0-v7":           ("W0",       "master", "W0.png",              False, False, "work"),
    "pose-h0x-v7":     ("H0x",      "pose",   "poses/H0x.png",       True,  False, "hall"),
    "pose-m0p-v7":     ("M0p",      "pose",   "poses/M0p.png",       True,  True,  "living-room"),
    "pose-m0x-v7":     ("M0x",      "pose",   "poses/M0x.png",       True,  True,  "living-room"),
    "pose-pd-35-v7":   ("PD-35",    "pose",   "poses/PD-35.png",     True,  True,  "kitchen-dining"),
    "pose-h0e-v7":     ("H0e",      "pose",   "poses/H0e.png",       True,  False, "hall"),
    "pose-w0-in-v7":   ("W0-in",    "pose",   "poses/W0-in.png",     False, False, "work"),
    "pose-s1prime-v7": ("S1prime",  "pose",   "poses/S1prime.png",   False, False, "corridor"),
    "pose-k-boy-0-v7": ("K-boy-0",  "pose",   "poses/K-boy-0.png",   True,  True,  "boy"),
    "pose-k-girl-0-v7": ("K-girl-0", "pose",  "poses/K-girl-0.png",  True,  True,  "girl"),
    "pose-cb-0-v7":    ("CB-0",     "pose",   "poses/CB-0.png",      True,  True,  "bath"),
    "pose-mb-in-v7":   ("MB-in",    "pose",   "poses/MB-in.png",     False, False, "master"),
}

# M0's living-room furniture is not boxed in the round-4 selfcheck; these are the pilot's boxes on the same camera
# (process_v7.py M0_REGIONS, the same QA used in qa/reports/2026-11-02-v7-g1/tools/common.py)
M0_FURNITURE = {"sofa (fixed-product)": (0.5208, 0.8396, 0.5509, 0.7949),
                "coffee table (fixed-product)": (0.512, 0.762, 0.6787, 0.8699),
                "armchair (fixed-product)": (0.1896, 0.3867, 0.6218, 0.9056)}


def jobs():
    return json.load(open(os.path.join(HERE, "jobs.json")))


def job(fid):
    return next(j for j in jobs()["jobs"] if j["id"] == fid)


def out_dir(fid):
    return os.path.join(REPO, job(fid)["out_dir"])


def selfcheck():
    return json.load(open(os.path.join(R4, "selfcheck.json")))["frames"]


def canvas_uv_to_frame(u, v):
    x0, y0, x1, y1 = CROP
    return ((u * CANVAS[0] - x0) / (x1 - x0), (v * CANVAS[1] - y0) / (y1 - y0))


def box_to_frame(b, overscan):
    """A selfcheck box (u0, u1, v0, v1 of the canvas) as fractions of the 16:9 frame."""
    if not overscan:
        return tuple(b)
    u0, v0 = canvas_uv_to_frame(b[0], b[2])
    u1, v1 = canvas_uv_to_frame(b[1], b[3])
    return (u0, u1, v0, v1)


def frame_box_px(w, h):
    """The 16:9 frame inside a canvas of w x h pixels (4072x2290 scaled)."""
    sx, sy = w / CANVAS[0], h / CANVAS[1]
    x0, y0, x1, y1 = CROP
    return (int(round(x0 * sx)), int(round(y0 * sy)), int(round(x1 * sx)), int(round(y1 * sy)))


def fixed_boxes(frame, overscan):
    """Clay boxes of the fixed furniture / architecture / windows / doors / mirrors, in 16:9-frame uv."""
    sc = selfcheck()[frame]
    W, H = sc["resolution"]
    out = {}
    for nm, b in sc.get("boxes", {}).items():
        if b["kind"] not in ("furniture", "architecture", "window", "door", "mirror"):
            continue
        if b["px"] / (W * H) < 0.002:
            continue
        out[nm] = (b["kind"], box_to_frame(b["box"], overscan))
    if frame == "M0":
        for nm, b in M0_FURNITURE.items():
            out[nm] = ("furniture", b)
    return out


def product_boxes(frame):
    sc = selfcheck()[frame]
    return {nm: b["box"] for nm, b in sc.get("boxes", {}).items() if b["kind"] in ("proxy", "proxy-transit")}
