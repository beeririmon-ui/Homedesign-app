#!/usr/bin/env python3
"""
m0_products_pass.py: the M0 1.2 products pass (briefs/render-m0-products-pass-2026-11-05.md, owner decision M0S2 = (a); render-agent,
2026-11-06). One seedream-5-pro image-to-image pass (650 tokens) on the composite m0-1-2-shell-seedream-fix.png that adds the magazine holder,
the jute basket, the floor lamp and the pouf (the last two test only) and puts the runner to its card; then, in code (0 tokens):
  ref2      reference 2: the round-5b M0 clay with the four proxies at their plan points (house plan 1.2.4 / slots 1.7), drawn by the M0 1.2.3
            camera with the clay's own depth pass for occlusion -> v9/m0-products-pass-ref2-clay.png (+ .json)
  fetch     the pass -> raw/, normalised to the canvas -> v9/m0-products-pass.png; register to the base (one global affine), lock_v2, the
            "nothing else moved" check (mean |delta| per channel outside the product boxes and the runner area)
  lay       the pass's products (their boxes + contact shadows + the lamp's pool) laid back over the locked base -> m0-1-2-products-fix.png
  grade     grading v6 (grade_v6_m0.py) with the four new products in the product mask
Boxes: the brief's [u0, u1, v0, v1] are on the 16:9 frame (they match the plan projection to ~0.01); its "about px" values are those
fractions times 2736, i.e. not the canvas; here every box is carried to the canvas properly: x = (u * 3840 + 116) / 4072 * 2736.
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art_m0_12 as A  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATE = "2026-11-06"
OD_REL = "assets/renders/living-room/nordic/v9/"
OD = os.path.join(REPO, OD_REL)
BASE = os.path.join(OD, "m0-1-2-shell-seedream-fix.png")
CLAY = os.path.join(REPO, "assets/blockout/house/framing/round5b/M0.png")
DEPTH = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/m0-pass/depth.npy"   # m0_clay_passes.py render
REF2 = os.path.join(OD, "m0-products-pass-ref2-clay.png")
CAM = A.CAMS["m0-v8b-r2"]
# the brief's boxes, 16:9 frame uv [u0, u1, v0, v1]
BOX_FRAME = {"magazine-holder": (0.345, 0.411, 0.774, 1.0), "basket": (0.350, 0.401, 0.686, 0.822), "floor-lamp shade": (0.885, 0.949, 0.389, 0.484),
             "floor-lamp (pole and base)": (0.905, 0.930, 0.484, 0.895), "pouf": (0.905, 1.0, 0.915, 1.0), "runner (clay box, + the front overhang)": (0.496, 0.604, 0.767, 0.90)}
CARDS = {"magazine-holder": ("magazine-holder-cj-felt-log-basket", "https://oss-cf.cjdropshipping.com/product/2026/02/11/05/4f328aff-7577-4c86-91b2-87c83bc0c692_fine.jpeg"),
         "basket": ("basket-cj-jute-rope-cylinder", "https://cf.cjdropshipping.com/16d626dd-b2ac-4e75-895b-bedd311c32a7_trans.jpeg"),
         "floor-lamp": ("floor-lamp-cj-black-drum-linen", "https://oss-cf.cjdropshipping.com/product/2025/08/05/06/fbdc89df-9c40-4528-9989-0eb259135e9c.jpg"),
         "pouf": ("pouf-cj-cotton-knit-ball-cover", "https://cf.cjdropshipping.com/quick/product/70d42577-2db2-4854-8e4e-00363593d8d7.jpg"),
         "runner": ("table-runner-cj-linen-look-sage-fringe", "https://cf.cjdropshipping.com/quick/product/2736eed6-7f8e-49d7-8652-d9e719a72430.jpg")}


def frame_to_canvas(u, v, W=2736, H=1539):
    return (u * 3840 + 116) / 4072 * W, (v * 2160 + 65) / 2290 * H


def box_canvas(b, W=2736, H=1539):
    x0, y0 = frame_to_canvas(b[0], b[2], W, H)
    x1, y1 = frame_to_canvas(b[1], b[3], W, H)
    return int(math.floor(x0)), int(math.ceil(x1)), int(math.floor(y0)), int(math.ceil(min(y1, H)))


def proj(P, cam=CAM, fx=0.6667, fy=1.1852):
    """world (X, Y, Z) -> frame uv and the planar depth (the projection of art_m0_12.H_wall / tone_r4.project)"""
    X, Y, Z = P
    s, c = math.sin(math.radians(cam["yaw"])), math.cos(math.radians(cam["yaw"]))
    cx, cy, cz = cam["loc"]
    d = s * (cx - X) + c * (cy - Y)
    xc = c * (X - cx) - s * (Y - cy)
    return cam["u0"] + fx * xc / d, cam["v0"] + fy * (cz - Z) / d, d


# ---------------------------------------------------------------------------------------------------------------
# proxies (faces: list of (3D polygon, base grey))
# ---------------------------------------------------------------------------------------------------------------
def box_faces(c, ax, L, Wd, Hh, z0, grey):
    a = np.array([ax[0], ax[1], 0.0]) / np.hypot(*ax)
    b = np.array([-a[1], a[0], 0.0])
    o = np.array([c[0], c[1], z0])
    corners = {}
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (0, 1):
                corners[(i, j, k)] = o + i * a * L / 2 + j * b * Wd / 2 + np.array([0, 0, k * Hh])
    F = []
    for fx_, face in (((1, None, None), [(1, -1, 0), (1, 1, 0), (1, 1, 1), (1, -1, 1)]), ((-1, None, None), [(-1, -1, 0), (-1, 1, 0), (-1, 1, 1), (-1, -1, 1)]),
                      ((None, 1, None), [(-1, 1, 0), (1, 1, 0), (1, 1, 1), (-1, 1, 1)]), ((None, -1, None), [(-1, -1, 0), (1, -1, 0), (1, -1, 1), (-1, -1, 1)]),
                      ((None, None, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)])):
        F.append(([corners[q] for q in face], grey))
    return F


def cyl_faces(c, r, z0, z1, grey, n=48, top=True):
    F = []
    for i in range(n):
        t0, t1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        p = [np.array([c[0] + r * math.cos(t0), c[1] + r * math.sin(t0), z0]), np.array([c[0] + r * math.cos(t1), c[1] + r * math.sin(t1), z0]),
             np.array([c[0] + r * math.cos(t1), c[1] + r * math.sin(t1), z1]), np.array([c[0] + r * math.cos(t0), c[1] + r * math.sin(t0), z1])]
        F.append((p, grey))
    if top:
        F.append(([np.array([c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n), z1]) for i in range(n)], grey))
    return F


def ellipsoid_faces(c, rx, rz, zc, grey, n=32, m=16):
    F = []
    for i in range(n):
        for j in range(m):
            t0, t1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            p0, p1 = -math.pi / 2 + math.pi * j / m, -math.pi / 2 + math.pi * (j + 1) / m
            q = [(t0, p0), (t1, p0), (t1, p1), (t0, p1)]
            F.append(([np.array([c[0] + rx * math.cos(p) * math.cos(t), c[1] + rx * math.cos(p) * math.sin(t), zc + rz * math.sin(p)]) for t, p in q], grey))
    return F


def proxies():
    s, c = math.sin(math.radians(CAM["yaw"])), math.cos(math.radians(CAM["yaw"]))
    view = (-s, -c)                                                     # the camera's forward direction on the floor
    P = {}
    P["magazine-holder"] = box_faces((-0.95, 1.90), view, 0.45, 0.32, 0.40, 0.012, 0.32)                  # long side along the line of sight
    bas = cyl_faces((-1.70, 0.75), 0.175, 0.0, 0.39, 0.62)
    for k in (-1, 1):                                                   # two rope loop handles, +9 cm, on the sides seen from the camera
        hx, hy = -1.70 + k * 0.175 * c, 0.75 - k * 0.175 * s
        bas += box_faces((hx, hy), (s, c), 0.02, 0.10, 0.09, 0.39, 0.55)
    P["basket"] = bas
    P["floor-lamp"] = cyl_faces((1.52, 0.20), 0.13, 0.0, 0.02, 0.12) + cyl_faces((1.52, 0.20), 0.0125, 0.02, 1.25, 0.10) + \
        cyl_faces((1.52, 0.20), 0.18, 1.25, 1.55, 0.97)
    P["pouf"] = ellipsoid_faces((1.45, 2.00), 0.225, 0.18, 0.18, 0.80)
    return P


def ref2():
    clay = np.asarray(Image.open(CLAY).convert("RGB")).astype(np.float32)
    H, W = clay.shape[:2]
    dep = cv2.resize(np.load(DEPTH), (W, H), interpolation=cv2.INTER_NEAREST)
    out = clay.copy()
    Ldir = np.array([-0.75, 0.35, 0.55])
    Ldir /= np.linalg.norm(Ldir)
    rec = {}
    zall = dep.astype(np.float32).copy()                                   # one depth buffer: the clay, then every proxy face (nearest wins)
    order = sorted(proxies().items(), key=lambda kv: -np.mean([proj(p)[2] for poly, _ in kv[1] for p in poly]))
    for name, faces in order:
        layer = np.zeros((H, W, 3), np.float32)
        zbuf = np.full((H, W), np.inf, np.float32)
        allpts = []
        for poly, grey in faces:
            pr = [proj(p) for p in poly]
            uv = np.array([[(u * 3840 + 116) / 4072 * W, (v * 2160 + 65) / 2290 * H] for u, v, _ in pr])
            d = float(np.mean([q[2] for q in pr]))
            allpts.append(uv)
            if len(poly) >= 3:
                n = np.cross(poly[1] - poly[0], poly[2] - poly[0])
                n = n / (np.linalg.norm(n) + 1e-9)
                ctr = np.mean(poly, 0)
                camv = np.array([CAM["loc"][0], CAM["loc"][1], CAM["loc"][2]]) - ctr
                if np.dot(n, camv) < 0:
                    n = -n
                shade = 0.55 + 0.45 * max(0.0, float(np.dot(n, Ldir)))
            m = np.zeros((H, W), np.uint8)
            cv2.fillPoly(m, [np.round(uv * 4).astype(np.int32)], 1, shift=2)
            m = m.astype(bool) & (d < zbuf) & (d < zall + 0.02)
            zbuf[m] = d
            layer[m] = np.clip(grey * shade, 0, 1) * 255
        cov = np.isfinite(zbuf)
        out[cov] = layer[cov]
        zall[cov] = np.minimum(zall[cov], zbuf[cov])
        pts = np.vstack(allpts)
        fu = [(x / W * 4072 - 116) / 3840 for x in (pts[:, 0].min(), pts[:, 0].max())]
        fv = [(y / H * 2290 - 65) / 2160 for y in (pts[:, 1].min(), pts[:, 1].max())]
        vis = np.nonzero(cov)
        rec[name] = dict(projected_frame_uv=[round(fu[0], 3), round(fu[1], 3), round(fv[0], 3), round(fv[1], 3)],
                         visible_canvas_px=[int(vis[1].min()), int(vis[1].max()), int(vis[0].min()), int(vis[0].max())] if cov.any() else None,
                         visible_px=int(cov.sum()))
    Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8)).save(REF2)
    json.dump(dict(what="reference 2 of the M0 1.2 products pass: the round-5b M0 clay with the four product proxies at their plan points (house plan 1.2.4, "
                        "slots 1.7), drawn by the 1.2.3 camera, occluded by the clay's own depth pass", date=DATE, clay=os.path.relpath(CLAY, REPO),
                   proxies=dict(holder="box 45 x 32 x 40 at (-0.95, 1.90), long side along the 25 deg line of sight, grey 0.32",
                                basket="cylinder d 35 h 39 at (-1.70, 0.75) + two 9 cm loop handles, grey 0.62",
                                floor_lamp="base d 26, pole d 2.5 to 1.25, drum shade d 36 from 1.25 to 1.55 at (1.52, 0.20), black / near-white",
                                pouf="ball d 45 h 36 at (1.45, 2.00), grey 0.80"),
                   boxes=rec, brief_boxes_frame_uv={k: list(v) for k, v in BOX_FRAME.items()}),
              open(REF2.replace(".png", ".json"), "w"), indent=1)
    print(json.dumps(rec, indent=0))


if __name__ == "__main__":
    w = sys.argv[1]
    if w == "ref2":
        ref2()
