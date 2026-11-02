"""
qa-agent, G1 on the Nordic v7 test set (2026-11-02): shared frame registry and loaders.
Read-only on assets/; everything written goes under qa/reports/2026-11-02-v7-g1/.
Run with ~/.venvs/motion/bin/python (OpenCV, numpy, Pillow). No network, no installs.
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-02-v7-g1")
R4 = os.path.join(REPO, "assets/blockout/house/framing/round4")
sys.path.insert(0, os.path.join(REPO, "site/tools/transitions"))
import pan_reproject as pr  # noqa: E402

SC = json.load(open(os.path.join(R4, "selfcheck.json")))["frames"]
PLAN = json.load(open(os.path.join(R4, "plan.json")))
CANVAS = (4072, 2290)
CROP = (116, 65, 3956, 2225)          # canvas -> the 16:9 frame (plan.json overscan.crop_box_px)
OVS_V = 65 / 2160                      # vertical overscan of the 16:9 frame, per side (0.0301)

# id: kind, render prefix (the kept attempt, per jobs.json), clay file, selfcheck key, camera (yaw, u0, v0), overscan, room
FRAMES = {
    "M0":       ("master", "assets/renders/living-room/nordic/v7/m0-v7-r2",   "M0.png",               "M0",       (25, .52, .46),  False, "living"),
    "D1":       ("master", "assets/renders/kitchen-dining/nordic/v7/d1-v7",   "D1.png",               "D1",       (-56, .52, .43), False, "kitchen-dining"),
    "D2":       ("master", "assets/renders/kitchen-dining/nordic/v7/d2-v7",   "D2.png",               "D2",       (-91, .52, .43), True,  "kitchen-dining"),
    "H0":       ("master", "assets/renders/hall/nordic/v7/h0-v7-r2",          "H0.png",               "H0",       (12, .52, .46),  False, "hall"),
    "C0":       ("master", "assets/renders/corridor/nordic/v7/c0-v7",         "C0.png",               "C0",       (0, .50, .46),   False, "corridor"),
    "MB0":      ("master", "assets/renders/master/nordic/v7/mb0-v7-r2",       "MB0.png",              "MB0",      (0, .50, .46),   False, "master"),
    "K-boy":    ("master", "assets/renders/boy/nordic/v7/k-boy-v7",           "K-boy.png",            "K-boy",    (33, .52, .44),  True,  "boy"),
    "K-girl":   ("master", "assets/renders/girl/nordic/v7/k-girl-v7",         "K-girl.png",           "K-girl",   (33, .52, .44),  True,  "girl"),
    "B1":       ("master", "assets/renders/bath/nordic/v7/b1-v7",             "B1.png",               "B1",       (-22, .52, .46), True,  "bath"),
    "B2":       ("master", "assets/renders/bath/nordic/v7/b2-v7",             "B2.png",               "B2",       (-57, .52, .46), True,  "bath"),
    "W0":       ("master", "assets/renders/work/nordic/v7/w0-v7",             "W0.png",               "W0",       (0, .50, .46),   False, "work"),
    "H0x":      ("pose",   "assets/renders/poses/nordic/v7/pose-h0x-v7",      "poses/H0x.png",        "H0x",      (25, .52, .46),  False, "hall"),
    "M0p":      ("pose",   "assets/renders/poses/nordic/v7/pose-m0p-v7",      "poses/M0p.png",        "M0p",      (0, .52, .46),   True,  "living"),
    "M0x":      ("pose",   "assets/renders/poses/nordic/v7/pose-m0x-v7",      "poses/M0x.png",        "M0x",      (-35, .52, .46), True,  "living"),
    "PD-35":    ("pose",   "assets/renders/poses/nordic/v7/pose-pd-35-v7",    "poses/PD-35.png",      "PD-35",    (-35, .52, .46), True,  "kitchen-dining"),
    "H0e":      ("pose",   "assets/renders/poses/nordic/v7/pose-h0e-v7",      "poses/H0e.png",        "H0e",      (0, .50, .46),   False, "hall"),
    "W0-in":    ("pose",   "assets/renders/poses/nordic/v7/pose-w0-in-v7",    "poses/W0-in.png",      "W0-in",    (0, .50, .46),   False, "work"),
    "S1'":      ("pose",   "assets/renders/poses/nordic/v7/pose-s1prime-v7",  "poses/S1prime.png",    "S1prime",  (0, .50, .46),   False, "corridor"),
    "K-boy-0":  ("pose",   "assets/renders/poses/nordic/v7/pose-k-boy-0-v7",  "poses/K-boy-0.png",    "K-boy-0",  (0, .50, .46),   True,  "boy"),
    "K-girl-0": ("pose",   "assets/renders/poses/nordic/v7/pose-k-girl-0-v7", "poses/K-girl-0.png",   "K-girl-0", (0, .50, .46),   True,  "girl"),
    "CB-0":     ("pose",   "assets/renders/poses/nordic/v7/pose-cb-0-v7",     "poses/CB-0.png",       "CB-0",     (0, .50, .46),   True,  "bath"),
    "MB-in":    ("pose",   "assets/renders/poses/nordic/v7/pose-mb-in-v7",    "poses/MB-in.png",      "MB-in",    (0, .50, .46),   False, "master"),
}
MASTERS = [k for k, v in FRAMES.items() if v[0] == "master"]
POSES = [k for k, v in FRAMES.items() if v[0] == "pose"]

# M0 has no living-room furniture boxes in the round-4 selfcheck; process_v7.py uses these (the pilot's boxes, same camera)
M0_FURNITURE = {"sofa (fixed-product)": (0.5208, 0.8396, 0.5509, 0.7949),
                "coffee table (fixed-product)": (0.512, 0.762, 0.6787, 0.8699),
                "armchair (fixed-product)": (0.1896, 0.3867, 0.6218, 0.9056)}


def rgb(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0


def crop_canvas(img):
    """16:9 frame inside a 4072x2290-equivalent canvas, at the image's own scale."""
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


def load(fid):
    """The kept render (graded), its raw-normalised twin and its clay, all as 16:9 frames (overscan cropped)."""
    kind, pref, clay, sck, cam, ovs, room = FRAMES[fid]
    g = rgb(os.path.join(REPO, pref + "-graded.png"))
    n = rgb(os.path.join(REPO, pref + ".png"))
    c = rgb(os.path.join(R4, clay))
    d = dict(id=fid, kind=kind, cam=pr.Cam(*cam), ovs=ovs, room=room, sc=SC[sck],
             graded_canvas=g if ovs else None, clay_canvas=c if ovs else None)
    if ovs:
        d["graded"], d["norm"], d["clay"] = crop_canvas(g), crop_canvas(n), crop_canvas(c)
        fp = os.path.join(REPO, pref + "-frame.png")
        if os.path.exists(fp):
            fr = rgb(fp)
            d["frame_file_matches_crop"] = bool(fr.shape == d["graded"].shape and float(np.abs(fr - d["graded"]).max()) < 2 / 255)
            d["frame_file_shape"] = list(fr.shape[:2])
    else:
        d["graded"], d["norm"], d["clay"] = g, n, c
    return d


def at(img, w=1920, h=1080):
    return pr.fit(img, w, h)


def boxes(d):
    """Clay boxes in 16:9-frame uv: dict name -> (kind, (u0,u1,v0,v1), area_frac_of_canvas, visible_pct)."""
    sc = d["sc"]
    W, H = sc["resolution"]
    iv = sc.get("items_visible", {})
    out = {}
    for nm, b in sc.get("boxes", {}).items():
        vis = iv.get(nm, {}).get("visible_pct")
        out[nm] = (b["kind"], box_to_frame(b["box"], d["ovs"]), b["px"] / (W * H), vis)
    if d["id"] == "M0":
        for nm, b in M0_FURNITURE.items():
            out[nm] = ("furniture", b, None, None)
    return out
