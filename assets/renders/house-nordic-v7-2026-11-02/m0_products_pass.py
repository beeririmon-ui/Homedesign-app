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
REF2 = os.path.join(OD, "m0-products-pass-ref2-clay-r2.png")     # r2 (2026-11-06): the holder at house plan 1.2.5 (r1 had it on the basket)
HOLDER_XY = (-0.54, 2.52)                                           # house plan 1.2.5 / slots 1.8 (1.2.4: (-0.95, 1.90))
CAM = A.CAMS["m0-v8b-r2"]
# the brief's boxes, 16:9 frame uv [u0, u1, v0, v1]
BOX_FRAME = {"magazine-holder": (0.335, 0.421, 0.848, 1.0), "basket": (0.350, 0.401, 0.686, 0.822), "floor-lamp shade": (0.885, 0.949, 0.389, 0.484),
             "floor-lamp (pole and base)": (0.905, 0.930, 0.484, 0.895), "pouf": (0.905, 1.0, 0.956, 1.0), "runner (clay box, + the front overhang)": (0.496, 0.604, 0.767, 0.90)}
CARDS = {"magazine-holder": ("magazine-holder-cj-felt-log-basket", "https://oss-cf.cjdropshipping.com/product/2026/02/11/05/4f328aff-7577-4c86-91b2-87c83bc0c692_fine.jpeg"),
         "basket": ("basket-cj-jute-rope-cylinder", "https://cf.cjdropshipping.com/16d626dd-b2ac-4e75-895b-bedd311c32a7_trans.jpeg"),
         "floor-lamp": ("floor-lamp-cj-black-drum-linen", "https://oss-cf.cjdropshipping.com/product/2025/08/05/06/fbdc89df-9c40-4528-9989-0eb259135e9c.jpg"),
         "pouf": ("pouf-cj-cotton-knit-ball-cover", "https://cf.cjdropshipping.com/quick/product/70d42577-2db2-4854-8e4e-00363593d8d7.jpg"),
         "runner": ("table-runner-cj-linen-look-sage-fringe", "https://cf.cjdropshipping.com/quick/product/2736eed6-7f8e-49d7-8652-d9e719a72430.jpg")}


def frame_to_canvas(u, v, W=2736, H=1539):
    return (u * 3840 + 116) / 4072 * W, (v * 2160 + 65) / 2290 * H


def box_canvas(b, W=2736, H=1539):
    """frame uv box -> canvas px; a box that reaches the frame's edge runs on to the canvas edge (the overscan shows the rest of the object)"""
    x0, y0 = frame_to_canvas(b[0], b[2], W, H)
    x1, y1 = frame_to_canvas(b[1], b[3], W, H)
    if b[1] >= 0.999:
        x1 = W
    if b[3] >= 0.999:
        y1 = H
    if b[0] <= 0.001:
        x0 = 0
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
    P["magazine-holder"] = box_faces(HOLDER_XY, view, 0.45, 0.32, 0.40, 0.012, 0.32)                     # long side along the line of sight
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
    sil = {}
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
        sil[name] = cov
    names = list(sil)
    ov = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a_, b_ = rec[names[i]]["projected_frame_uv"], rec[names[j]]["projected_frame_uv"]
            du = min(a_[1], b_[1]) - max(a_[0], b_[0])
            dv = min(a_[3], b_[3]) - max(a_[2], b_[2])
            ov[f"{names[i]} / {names[j]}"] = dict(box_overlap=bool(du > 0 and dv > 0), gap_u=round(-du, 3), gap_v=round(-dv, 3),
                                                   silhouette_overlap_px=int((sil[names[i]] & sil[names[j]]).sum()))
    rec["_pairs"] = ov
    Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8)).save(REF2)
    json.dump(dict(what="reference 2 of the M0 1.2 products pass: the round-5b M0 clay with the four product proxies at their plan points (house plan 1.2.4, "
                        "slots 1.7), drawn by the 1.2.3 camera, occluded by the clay's own depth pass", date=DATE, clay=os.path.relpath(CLAY, REPO),
                   proxies=dict(holder=f"box 45 x 32 x 40 at {HOLDER_XY} (house plan 1.2.5), long side along the 25 deg line of sight, grey 0.32",
                                basket="cylinder d 35 h 39 at (-1.70, 0.75) + two 9 cm loop handles, grey 0.62",
                                floor_lamp="base d 26, pole d 2.5 to 1.25, drum shade d 36 from 1.25 to 1.55 at (1.52, 0.20), black / near-white",
                                pouf="ball d 45 h 36 at (1.45, 2.00), grey 0.80"),
                   boxes=rec, brief_boxes_frame_uv={k: list(v) for k, v in BOX_FRAME.items()}),
              open(REF2.replace(".png", ".json"), "w"), indent=1)
    print(json.dumps(rec, indent=0))




# ---------------------------------------------------------------------------------------------------------------
# after the pass (0 tokens)
# ---------------------------------------------------------------------------------------------------------------
PASS_ID = "m0-products-pass"
JID = "m0-1-2-products"
URL = ("https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/"
       "seedream5p-e90303cde5e804cc76371fc53b3f2732-0-1793992356950-9aae431d.png")
DL = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/dl-products/"
LAMP_LIGHT_ZONE = (0.78, 1.0, 0.25, 0.92)
LAMP_LIGHT_GAIN = 1.8          # the pass's lamp light, as a power of its brightening ratio (1.0 gave a pool of +1.4 L on the sofa's end; the Bible's
                               # floor lamp adds 20-25 % with a 70 cm pool)          # canvas uv: the floor lamp's light on the wall behind it, the sofa's right end and the throw


def load01(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0


def zones(W=2736, H=1539, grow=0.15):
    """canvas px boxes of the products (the brief's frame boxes +-15 % of their size, the brief's tolerance) and the runner area"""
    out = {}
    for k, b in BOX_FRAME.items():
        x0, x1, y0, y1 = box_canvas(b, W, H)
        gx, gy = (x1 - x0) * grow, (y1 - y0) * grow
        out[k] = (max(0, int(x0 - gx)), min(W, int(x1 + gx)), max(0, int(y0 - gy)), min(H, int(y1 + gy)))
    return out


def register_to_base(p, b):
    """one affine (ECC on the gray, half size, the product zones masked out): the pass onto the base's pixel grid"""
    H, W = b.shape[:2]
    g = lambda x: cv2.resize(cv2.cvtColor((x * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY), (W // 2, H // 2), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    m = np.ones((H, W), np.uint8)
    for (x0, x1, y0, y1) in zones(W, H).values():
        m[y0:y1, x0:x1] = 0
    x0, x1, y0, y1 = (int(LAMP_LIGHT_ZONE[0] * W), int(LAMP_LIGHT_ZONE[1] * W), int(LAMP_LIGHT_ZONE[2] * H), int(LAMP_LIGHT_ZONE[3] * H))
    m[y0:y1, x0:x1] = 0
    m2 = cv2.resize(m, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST)
    A_ = np.eye(2, 3, dtype=np.float32)
    cc, A_ = cv2.findTransformECC(g(b), g(p), A_, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), m2, 5)
    A_[:, 2] *= 2
    out = cv2.warpAffine(p, A_, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    return np.clip(out, 0, 1), dict(ecc=round(float(cc), 4), affine_inverse_map=np.round(A_, 5).tolist(),
                                    shift_px=[round(float(A_[0, 2]), 2), round(float(A_[1, 2]), 2)],
                                    scale_pct=[round((float(np.hypot(A_[0, 0], A_[1, 0])) - 1) * 100, 3), round((float(np.hypot(A_[0, 1], A_[1, 1])) - 1) * 100, 3)])


def nothing_else_moved(p, b):
    H, W = b.shape[:2]
    m = np.ones((H, W), bool)
    for (x0, x1, y0, y1) in zones(W, H).values():
        m[y0:y1, x0:x1] = False
    fx0, fy0 = int(round(116 / 4072 * W)), int(round(65 / 2290 * H))
    fx1, fy1 = int(round(3956 / 4072 * W)), int(round(2225 / 2290 * H))
    fr = np.zeros((H, W), bool)
    fr[fy0:fy1, fx0:fx1] = True
    d = np.abs(p - b) * 255
    lz = np.zeros((H, W), bool)
    x0, x1, y0, y1 = (int(LAMP_LIGHT_ZONE[0] * W), int(LAMP_LIGHT_ZONE[1] * W), int(LAMP_LIGHT_ZONE[2] * H), int(LAMP_LIGHT_ZONE[3] * H))
    lz[y0:y1, x0:x1] = True
    out = dict(rule="mean |delta| per channel <= 2 outside the four product boxes (+-15 %) and the runner area (the brief), on the 16:9 frame",
               outside_mean_per_channel=[round(float(d[..., c][m & fr].mean()), 2) for c in range(3)],
               outside_without_the_lamp_light_zone=[round(float(d[..., c][m & fr & ~lz].mean()), 2) for c in range(3)],
               outside_p99=round(float(np.percentile(d.max(2)[m & fr], 99)), 1))
    regions = {"walls left of the art (u 0.38-0.55, v 0.10-0.45)": (0.38, 0.55, 0.10, 0.45), "triptych (u 0.55-0.80, v 0.33-0.53)": (0.55, 0.80, 0.33, 0.53),
               "sofa and cushions (u 0.47-0.80, v 0.58-0.78)": (0.47, 0.80, 0.58, 0.78), "window (u 0.10-0.26, v 0.06-0.58)": (0.10, 0.26, 0.06, 0.58),
               "armchair (u 0.03-0.31, v 0.70-0.97)": (0.03, 0.31, 0.70, 0.97), "rug centre (u 0.45-0.85, v 0.88-0.97)": (0.45, 0.85, 0.88, 0.97)}
    for k, (u0, u1, v0, v1) in regions.items():
        r = np.zeros((H, W), bool)
        r[int(v0 * H):int(v1 * H), int(u0 * W):int(u1 * W)] = True
        r &= m
        out[k] = round(float(d.max(2)[r].mean()), 2)
    out["pass"] = bool(max(out["outside_mean_per_channel"]) <= 2.0)
    return out


def fetch():
    import subprocess
    sys.path.insert(0, HERE)
    import fix_m0_12 as M
    import m0_model_test as T
    os.makedirs(os.path.join(OD, "raw"), exist_ok=True)
    os.makedirs(DL, exist_ok=True)
    dl = os.path.join(DL, PASS_ID + ".png")
    if not os.path.exists(dl):
        subprocess.run(["curl", "-sS", "-L", "--max-time", "240", "-o", dl, URL], check=True)
    raw = os.path.join(OD, "raw", PASS_ID + ".png")
    open(raw, "wb").write(open(dl, "rb").read())
    im0 = Image.open(dl).convert("RGB")
    norm = os.path.join(OD, PASS_ID + ".png")
    im0.resize((2736, 1539), Image.LANCZOS).save(norm)
    p, b = load01(norm), load01(BASE)
    pr, reg = register_to_base(p, b)
    Image.fromarray((pr * 255 + 0.5).astype(np.uint8)).save(os.path.join(OD, PASS_ID + "-reg.png"))
    nem_raw, nem = nothing_else_moved(p, b), nothing_else_moved(pr, b)
    PL = M._pipeline()
    PL.VF.RETAKES[PASS_ID] = PL.JOBS["m0-v8b"]
    J = T.jr()
    if not any(j["id"] == PASS_ID for j in J["jobs"]):
        J["jobs"].append(dict(id=PASS_ID, out_dir=OD_REL, model="seedream-5-pro", tokens=650, status="products pass (M0S2), fetched"))
        T.save_jr(J)
    PL.VF.RETAKES_JOBS = T.JR
    lk = PL.LK.run_frame(PASS_ID, render_path=norm, out_path=os.path.join(OD, PASS_ID + "-lock-v2.json"), overlay_path=os.path.join(OD, PASS_ID + "-lock-v2.jpg"), date=DATE)
    s, v = lk["summary"], lk["verdict"]
    rec = dict(asset_id=PASS_ID, date=DATE, tokens=650, model="seedream-5-pro", type="image-to-image", resolution="2K", aspect_ratio="auto",
               placeholder_id="095d0fa5-d6b9-496c-981f-54369bc32862", task_id="e90303cde5e804cc76371fc53b3f2732", url=URL, returned_px=list(im0.size),
               prompt="assets/prompts/recipe-v5.nordic/m0-products-pass.txt", image_url=("var2 upload of " + OD_REL + "m0-1-2-shell-seedream-fix.png (sha256 aca9366f5eca7219...)"),
               image_refs=dict(ref2="var2 upload of " + OD_REL + "m0-products-pass-ref2-clay-r2.png (2736 x 1539)", cards={k: v_[1] for k, v_ in CARDS.items()}),
               lock_v2=dict(shift_px=s["register_shift_px"], scale_pct=s["register_scale_pct"], band_after=s["worst_band_px_after_register"],
                            tile_after=s["worst_tile_ecc_px_after_register"], fixed_edges_worst_px=s["fixed_edges_worst_px"], fixed_ratios=s["fixed_ratios"],
                            verdict={k: v[k] for k in ("global_pass", "residual_pass", "edges_pass", "pass")}),
               register_to_base=reg, nothing_else_moved_raw=nem_raw, nothing_else_moved_after_register=nem, raw=os.path.relpath(raw, REPO), normalised=OD_REL + PASS_ID + ".png")
    json.dump(rec, open(os.path.join(OD, PASS_ID + ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(lock=rec["lock_v2"], reg=reg, nem_raw=nem_raw, nem=nem), indent=1))


def tone_lut(p, b, mask):
    """per channel, the pass value -> the base value on the unchanged area (median per 4-level bin, monotone, smoothed): the pass's global
    tone and white balance carried to the base's (the pass came out ~14 levels darker)"""
    luts = []
    for c in range(3):
        x = (p[..., c][mask] * 255).astype(np.int32)
        y = b[..., c][mask] * 255
        xs, ys = [], []
        for v in range(0, 256, 4):
            sel = (x >= v) & (x < v + 4)
            if sel.sum() > 200:
                xs.append(v + 2)
                ys.append(float(np.median(y[sel])))
        ys = np.maximum.accumulate(np.array(ys))
        lut = np.interp(np.arange(256), [0] + xs + [255], [0] + list(ys) + [max(255.0, ys[-1])])
        lut = cv2.GaussianBlur(lut.reshape(1, -1).astype(np.float32), (0, 0), 3).ravel()
        luts.append(np.clip(lut, 0, 255) / 255.0)
    return luts


def apply_lut(img, luts):
    out = np.empty_like(img)
    for c in range(3):
        out[..., c] = np.interp(img[..., c] * 255, np.arange(256), luts[c])
    return out


def guided1(I, pm, r, eps):
    k = (2 * r + 1, 2 * r + 1)
    mI, mp = cv2.blur(I, k), cv2.blur(pm, k)
    a_ = (cv2.blur(I * pm, k) - mI * mp) / (cv2.blur(I * I, k) - mI * mI + eps)
    b_ = mp - a_ * mI
    return cv2.blur(a_, k) * I + cv2.blur(b_, k)


def silhouette(img, rect, iters=6):
    """grabCut in the pass, initialised with the product's zone rectangle; the largest component, holes filled"""
    H, W = img.shape[:2]
    x0, x1, y0, y1 = rect
    m = np.zeros((H, W), np.uint8)
    bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    r = (max(1, x0), max(1, y0), min(W - 2, x1) - max(1, x0), min(H - 2, y1) - max(1, y0))
    cv2.grabCut((img * 255).astype(np.uint8), m, r, bg, fg, iters, cv2.GC_INIT_WITH_RECT)
    s = ((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)).astype(np.uint8)
    s = cv2.morphologyEx(s, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(s)
    if n <= 1:
        return s.astype(bool)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    s = (lab == k).astype(np.uint8)
    inv = 1 - s
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 4000 and st[i, cv2.CC_STAT_LEFT] > 0 and st[i, cv2.CC_STAT_TOP] > 0:
            s[lab == i] = 1
    return s.astype(bool)


def lay():
    b = load01(BASE)
    pr = load01(os.path.join(OD, PASS_ID + "-reg.png"))
    H, W = b.shape[:2]
    Z = zones(W, H)
    keep = np.ones((H, W), bool)
    for (x0, x1, y0, y1) in Z.values():
        keep[max(0, y0 - 40):y1 + 40, max(0, x0 - 40):x1 + 40] = False
    lz = np.zeros((H, W), bool)
    lz[int(LAMP_LIGHT_ZONE[2] * H):int(LAMP_LIGHT_ZONE[3] * H), int(LAMP_LIGHT_ZONE[0] * W):int(LAMP_LIGHT_ZONE[1] * W)] = True
    keep &= ~lz
    def s2l(x):
        return np.where(x <= 0.04045, x / 12.92, ((np.clip(x, 0, None) + 0.055) / 1.055) ** 2.4)

    def l2s(x):
        return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)
    lp, lb = s2l(pr), s2l(b)
    sel = keep & (pr.min(2) > 0.25) & (pr.max(2) < 0.95)
    gains = [float(np.median(lb[..., c][sel] / np.maximum(lp[..., c][sel], 1e-4))) for c in range(3)]
    pt = np.clip(l2s(lp * np.array(gains)), 0, 1).astype(np.float32)
    luts = None
    gray = cv2.cvtColor((pt * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    rec = dict(tone=dict(how="one gain per channel in linear light, the median base / pass ratio on the unchanged area (outside every product zone + 40 px and the "
                                 "lamp's light zone; pass values 0.25-0.95): the pass came out ~14 levels darker", gains_rgb=[round(g, 4) for g in gains]),
               products={})
    alpha = np.zeros((H, W), np.float32)
    lz_ = box_canvas((0.865, 0.975, 0.36, 0.93), W, H)                 # the lamp as rendered (shade to u 0.958) with a margin
    hz_ = box_canvas((0.265, 0.46, 0.80, 1.0), W, H)                    # the holder as rendered (~1.5x its box: frame u 0.28-0.44), whole
    rects = {"magazine-holder": hz_, "basket": Z["basket"], "pouf": Z["pouf"], "floor-lamp": lz_}
    sils = {}
    for k, r in rects.items():
        sm = silhouette(pt, r)
        sils[k] = sm
        print(k, r, int(sm.sum()), flush=True)
        ys, xs = np.nonzero(sm)
        fu = [round(((x / W) * 4072 - 116) / 3840, 3) for x in (xs.min(), xs.max())]
        fv = [round(((y / H) * 2290 - 65) / 2160, 3) for y in (ys.min(), ys.max())]
        bb = BOX_FRAME["floor-lamp shade"] if k == "floor-lamp" else BOX_FRAME[k]
        if k == "floor-lamp":
            bb = (BOX_FRAME["floor-lamp shade"][0], BOX_FRAME["floor-lamp shade"][1], BOX_FRAME["floor-lamp shade"][2], BOX_FRAME["floor-lamp (pole and base)"][3])
        wb, hb = bb[1] - bb[0], bb[3] - bb[2]
        within = all([fu[0] >= bb[0] - 0.15 * wb, fu[1] <= bb[1] + 0.15 * wb, fv[0] >= bb[2] - 0.15 * hb, fv[1] <= bb[3] + 0.15 * hb])
        rec["products"][k] = dict(rendered_frame_uv=[fu[0], fu[1], fv[0], fv[1]], brief_box=list(bb), within_15pct=bool(within), px=int(sm.sum()))
        alpha = np.maximum(alpha, sm.astype(np.float32))
    # the runner: the new one (grabCut in the pass) and where the old one lay (the base's sage pixels on the table), the pass in their union
    rz = box_canvas((0.48, 0.62, 0.767, 0.97), W, H)                    # the runner area down to its front fringe as rendered
    new_r = silhouette(pt, rz)
    hb_ = cv2.cvtColor(b, cv2.COLOR_RGB2HLS)
    old_r = np.zeros((H, W), bool)
    x0, x1, y0, y1 = rz
    sub = hb_[y0:y1, x0:x1]
    old_r[y0:y1, x0:x1] = (sub[..., 0] >= 55) & (sub[..., 0] <= 110) & (sub[..., 2] > 0.04)
    old_r = cv2.morphologyEx(old_r.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)).astype(bool)
    run = cv2.dilate((new_r | old_r).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    ys, xs = np.nonzero(new_r)
    rec["products"]["runner"] = dict(rendered_frame_uv=[round(((xs.min() / W) * 4072 - 116) / 3840, 3), round(((xs.max() / W) * 4072 - 116) / 3840, 3),
                                                        round(((ys.min() / H) * 2290 - 65) / 2160, 3), round(((ys.max() / H) * 2290 - 65) / 2160, 3)],
                                     clay_area="canvas " + str(list(BOX_FRAME["runner (clay box, + the front overhang)"])), px=int(new_r.sum()), old_runner_px=int(old_r.sum()))
    alpha = np.maximum(alpha, run.astype(np.float32))
    sils["runner"] = new_r
    # each product's region: its grabCut core grown by everything the pass changed around it (|pass - base| > 0.12, blurred 2 px: handles,
    # fringe, magazines, contact shadows), connected to the core, inside its zone; closed, filled, grown 6 px, feathered 4 px
    D = cv2.GaussianBlur(np.abs(pt - b).max(2), (0, 0), 2)
    reg = np.zeros((H, W), np.uint8)
    zone_of = dict(rects, runner=rz)
    for k, core in sils.items():
        x0, x1, y0, y1 = zone_of[k]
        x0, y0 = max(0, x0 - 20), max(0, y0 - 20)
        x1, y1 = min(W, x1 + 20), min(H, y1 + 20)
        cand = np.zeros((H, W), np.uint8)
        cand[y0:y1, x0:x1] = ((D[y0:y1, x0:x1] > 0.12) | core[y0:y1, x0:x1]).astype(np.uint8)
        cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        n, lab = cv2.connectedComponents(cand)
        keepc = np.zeros(n, bool)
        keepc[np.unique(lab[core])] = True
        keepc[0] = False
        m = keepc[lab].astype(np.uint8)
        grow = {"basket": 17, "magazine-holder": 41, "pouf": 41, "floor-lamp": 41, "runner": 41}[k]
        m &= cv2.dilate(core.astype(np.uint8), np.ones((grow, grow), np.uint8))        # no stray change far from the product
        if k == "basket":                                                              # the pass put a wall socket beside its handles: growth only
            ys_ = np.nonzero(core)[0]                                                  # in the lower part (the floor shadow)
            top = int(ys_.min() + 0.45 * (ys_.max() - ys_.min()))
            m[:top] &= core[:top].astype(np.uint8)
        if k == "floor-lamp":                                                          # the lamp alone: its shade (the linen's texture, convex), the
            x0_, x1_, y0_, y1_ = zone_of[k]                                            # dark pole and base; its light on the wall comes as light below
            Lp = cv2.cvtColor((pt * 255).astype(np.uint8), cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32) / 2.55
            tex = cv2.GaussianBlur(np.abs(Lp - cv2.GaussianBlur(Lp, (0, 0), 1.5)), (0, 0), 3)
            sub = tex[y0_:y1_, x0_:x1_]
            ring = np.ones_like(sub, bool)
            ring[6:-6, 6:-6] = False
            tm = (sub > max(3 * np.median(sub[ring]), 0.6)).astype(np.uint8)
            tm = cv2.morphologyEx(tm, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
            n3, lab3, st3, _ = cv2.connectedComponentsWithStats(tm)
            shade = np.zeros((H, W), np.uint8)
            if n3 > 1:
                kk = 1 + int(np.argmax(st3[1:, cv2.CC_STAT_AREA]))
                cnts, _ = cv2.findContours(cv2.erode((lab3 == kk).astype(np.uint8), np.ones((5, 5), np.uint8)), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                hull = cv2.convexHull(max(cnts, key=cv2.contourArea)) + np.array([[x0_, y0_]])
                cv2.fillConvexPoly(shade, hull.astype(np.int32), 1)
            dark = np.zeros((H, W), np.uint8)
            dark[y0_:y1_, x0_:x1_] = (pt[y0_:y1_, x0_:x1_].max(2) < 0.30).astype(np.uint8)
            n4, lab4 = cv2.connectedComponents(dark)
            keep4 = np.zeros(n4, bool)
            keep4[np.unique(lab4[(core | shade.astype(bool)) & (dark > 0)])] = True
            keep4[[i for i in range(n4) if (lab4 == i).sum() < 40]] = False
            keep4[0] = False
            m = shade | keep4[lab4].astype(np.uint8)                                  # not grabCut's core: it took in the glow on the wall
        inv = 1 - m
        n2, lab2, st2, _ = cv2.connectedComponentsWithStats(inv)
        for i in range(1, n2):
            if st2[i, cv2.CC_STAT_AREA] < 6000:
                m[lab2 == i] = 1
        if k == "runner":
            m |= old_r.astype(np.uint8)
        reg |= m
        rec["products"][k]["region_px"] = int(m.sum())
    lampm = np.zeros((H, W), np.uint8)
    reg = cv2.dilate(reg, np.ones((7, 7), np.uint8))
    a_soft = cv2.GaussianBlur(reg.astype(np.float32), (0, 0), 2.5)
    a_soft = np.maximum(a_soft, cv2.erode(reg, np.ones((9, 9), np.uint8)).astype(np.float32))
    alpha = reg.astype(np.float32)
    Yb = (b * np.array([0.2126, 0.7152, 0.0722])).sum(2)
    Yp = (pt * np.array([0.2126, 0.7152, 0.0722])).sum(2)
    outm = 1.0 - cv2.dilate(reg, np.ones((7, 7), np.uint8)).astype(np.float32)

    def nblur(Yx, sg):
        return cv2.GaussianBlur(Yx * outm, (0, 0), sg) / np.maximum(cv2.GaussianBlur(outm, (0, 0), sg), 1e-3)
    out = b.copy()
    # the floor lamp's light: the pass's own low-pass brightening (>= 1) in a soft zone round the lamp (the wall behind it, the sofa's right end, the throw)
    yy, xx = np.mgrid[0:H, 0:W]
    lx0, lx1, ly0, ly1 = LAMP_LIGHT_ZONE
    cx, cy = (lx0 + lx1) / 2 * W, (ly0 + ly1) / 2 * H
    zone = np.exp(-0.5 * (((xx - cx) / ((lx1 - lx0) * W * 0.45)) ** 2 + ((yy - cy) / ((ly1 - ly0) * H * 0.45)) ** 2)).astype(np.float32)
    ratL = np.clip(nblur(Yp, 25) / np.maximum(nblur(Yb, 25), 1e-3), 1.0, 1.8) ** LAMP_LIGHT_GAIN
    out = out * (1 + zone * (ratL - 1) * (1 - a_soft))[..., None]
    rec["lamp_light"] = dict(zone_canvas_uv=list(LAMP_LIGHT_ZONE), gain_exponent=LAMP_LIGHT_GAIN, ratio_max=round(float((zone * (ratL - 1)).max() + 1), 3),
                             how="base x (1 + zone x (low-pass sigma 25 of pass / base, clipped 1-1.8 - 1)): the lamp's glow and pool carried as light, the base's detail kept")
    out = out * (1 - a_soft[..., None]) + pt * a_soft[..., None]
    out = np.clip(out, 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(OD, JID + "-fix.png"))
    np.savez_compressed(DL + "lay-masks.npz", alpha=a_soft.astype(np.float16), region=reg.astype(bool), **{k: v for k, v in sils.items()})
    prod_regions = {}
    for k in ("magazine-holder", "basket", "pouf", "floor-lamp"):
        prod_regions[k] = cv2.dilate(sils[k].astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & (reg > 0)
    np.savez_compressed(DL + "new-products.npz", **prod_regions)
    # the composite's records: the triptych and the round are the base's (copied, for grading v6's masks)
    nb = json.load(open(os.path.join(OD, "m0-1-2-shell-seedream-fix.json")))
    nbb = json.load(open(os.path.join(OD, "m0-1-2-shell-seedream-fix-base.json")))
    nem = nothing_else_moved(out, b)
    note = dict(asset_id=JID + "-fix", date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/m0_products_pass.py",
                base=OD_REL + "m0-1-2-shell-seedream-fix.png", products_from=OD_REL + PASS_ID + ".png (registered: " + PASS_ID + "-reg.png)",
                how=("the base everywhere; from the pass (one linear-light gain per channel onto the base's tone) only the four products and the runner: each "
                     "product's grabCut core grown by what the pass changed round it (|delta| > 0.12: handles, fringe, magazines, contact shadows), inside its zone, "
                     "grown 6 px, feathered 4 px; the runner also where the old one lay; the floor lamp's light as the pass's low-pass brightening (products left "
                     "out) in a soft zone round it"), **rec, nothing_else_moved_after_lay=nem,
                placement=nb["placement"], prints=nb.get("prints"), wall_round_from="m0-1-2-shell-seedream-fix-base.json", output=OD_REL + JID + "-fix.png")
    json.dump(note, open(os.path.join(OD, JID + "-fix.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(dict(asset_id=JID + "-fix-base", note="the round of the base (for grade_v6_m0's masks)", wall_round=nbb["wall_round"]),
              open(os.path.join(OD, JID + "-fix-base.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(products=rec["products"], tone=rec["tone"]["gains_rgb"], lamp=rec["lamp_light"]["ratio_max"], nem=nem), indent=0)[:3000])


def grade():
    """grading v6 (grade_v6_m0.py) on the laid composite, the four new products in the product mask (<= +0.2 stop); + the brief's QA values"""
    import grade_v6_m0 as G
    G.JID = JID
    G.SRC = os.path.join(OD, JID + "-fix.png")
    G.V5 = os.path.join(OD, "m0-1-2-shell-seedream-graded-fix-v5.png")
    G.SP = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/v6-products/"
    G.SHEET = os.path.join(REPO, "assets/renders/house-nordic-m0-products-pass-sheet-2026-11-06.jpg")
    os.makedirs(G.SP, exist_ok=True)
    a = G.load(G.SRC)
    Mk, mrec = G.masks(a)
    d = dict(np.load(G.SP + "masks.npz"))
    npd = dict(np.load(DL + "new-products.npz"))
    shell, I, ol = d["shell"].copy(), d["I"].copy(), d["obj_label"].copy()
    ids = {"magazine-holder": 601, "basket": 602, "pouf": 603, "floor-lamp": 604}
    gray = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    La = G.Lmap(a)
    npd["floor-lamp shade"] = npd["floor-lamp"] & (La > 65)
    ids["floor-lamp shade"] = 605
    for k, i in ids.items():
        m = npd[k]
        I[m] = i
        ol[m] = i
        soft = np.clip(guided1(gray, m.astype(np.float32), 2, 1e-4), 0, 1)
        shell = np.minimum(shell, 1 - soft)
    kinds = d["shell_kind"]
    np.savez_compressed(G.SP + "masks.npz", shell=shell.astype(np.float32), art=d["art"], rnd=d["rnd"], cubes=d["cubes"], shell_kind=kinds, obj_label=ol, I=I)
    rec = json.load(open(G.SP + "masks.json"))
    rec["new_products"] = dict(how="the four products laid from the pass (m0-1-2-products-fix.json regions) set to product (+0.2 stop at most), ids 601-604",
                               px={k: int(npd[k].sum()) for k in ids})
    json.dump(rec, open(G.SP + "masks.json", "w"), indent=1)
    s2l = lambda x: np.where(x <= 0.04045, x / 12.92, ((np.clip(x, 0, None) + 0.055) / 1.055) ** 2.4)
    hold = float(np.median(La[npd["magazine-holder"] & (La < 60)]))
    shd = float(np.median(La[npd["floor-lamp shade"]]))
    G.P0["obj_stops"] = {"601": float(np.clip(np.log2(s2l(0.275) / s2l(hold / 100)), 0.2, 1.3)),
                         "605": float(np.clip(np.log2(s2l(0.99) / s2l(shd / 100)) + 0.2, 0.3, 1.5))}
    rec["new_products"]["obj_stops"] = dict(G.P0["obj_stops"], why=("601 the holder to its card's charcoal (#45474B, L 27; at +0.2 it read 20); 605 the floor-lamp "
                                                                   "shade as an emitter (Bible lamps: shade L 93-97), not a product colour"),
                                            holder_raw_L=round(hold, 1), shade_raw_L=round(shd, 1))
    json.dump(rec, open(G.SP + "masks.json", "w"), indent=1)
    G.run()
    qa_products()


def qa_products():
    """the brief's QA values on the graded frame"""
    import grade_v6_m0 as G
    G.SP = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/v6-products/"
    d = dict(np.load(G.SP + "masks.npz"))
    npd = dict(np.load(DL + "new-products.npz"))
    g = G.load(os.path.join(OD, JID + "-graded-fix-v6.png"))
    H, W = g.shape[:2]
    L = G.Lmap(g)
    hls = cv2.cvtColor(g, cv2.COLOR_RGB2HLS)
    qa = {}
    h_, s_, l_ = G.hsl(g[npd["magazine-holder"] & (L < 60)].mean(0))
    qa["charcoal holder (its felt, L < 60): L [25-35]"] = dict(H=h_, S=s_, L=l_, ok=bool(25 <= l_ <= 35))
    bm = npd["basket"]
    h_, s_, l_ = G.hsl(g[bm].mean(0))
    qa["jute basket: H [25-40], S [25-55]"] = dict(H=h_, S=s_, L=l_, ok=bool(25 <= h_ <= 40 and 25 <= s_ <= 55))
    lm = npd["floor-lamp"]
    ys, xs = np.nonzero(lm & (L > 70))
    shade = lm & (L > 70)
    shade_L = float(np.median(L[shade]))
    x0, x1 = xs.min(), xs.max()
    wall = np.zeros((H, W), bool)
    wall[int(0.36 * H):int(0.42 * H), max(0, x0 - 140):x0 - 40] = True
    wall &= ~lm
    wL = float(np.median(L[wall]))
    qa["floor-lamp shade: median L, the wall left of it, difference [>= 6]"] = dict(shade=round(shade_L, 1), wall=round(wL, 1), diff=round(shade_L - wL, 1), ok=bool(shade_L - wL >= 6))
    b0 = G.load(os.path.join(OD, "m0-1-2-shell-seedream-graded-fix-v6.png"))
    sofa_end = np.zeros((H, W), bool)
    sofa_end[int(0.62 * H):int(0.80 * H), int(0.80 * W):int(0.88 * W)] = True
    sofa_end &= (d["I"] == 1) | (d["I"] == 41)
    dL = float(np.median(L[sofa_end]) - np.median(G.Lmap(b0)[sofa_end]))
    qa["pool on the sofa's right end and the throw: L over the Nordic v6 without the lamp"] = dict(delta_L=round(dL, 1), ok=bool(dL >= 2))
    walls = np.isin(d["I"], [5, 6]) & (d["shell"] > 0.95)
    lzm = np.zeros((H, W), bool)
    lzm[int(LAMP_LIGHT_ZONE[2] * H):int(LAMP_LIGHT_ZONE[3] * H), int(LAMP_LIGHT_ZONE[0] * W):int(LAMP_LIGHT_ZONE[1] * W)] = True
    cubes_z = cv2.dilate(d["cubes"].astype(np.uint8), np.ones((161, 101), np.uint8)).astype(bool)
    wm = float(np.percentile(L[walls & ~lzm & ~cubes_z], 99.5))
    gl = cv2.erode((d["I"] == 0).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    gl[:, :int(0.10 * W)] = False
    g50 = float(np.median(L[gl]))
    qa["walls p99.5 outside the cube washes and the floor lamp's light zone [<= 94]; the glass p50 over it [>= 3]"] = dict(
        walls_p99_5=round(wm, 1), glass_p50=round(g50, 1), margin=round(g50 - wm, 1), ok=bool(wm <= 94 and g50 - wm >= 3))
    n = json.load(open(os.path.join(OD, JID + "-measurements-fix-v6.json")))
    n["products_pass_qa"] = qa
    n["note_products"] = "the laid composite m0-1-2-products-fix.png (m0_products_pass.py lay); v5 column = the Nordic seedream composite's v5 (this composite has no v5)"
    json.dump(n, open(os.path.join(OD, JID + "-measurements-fix-v6.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(qa, indent=1))


def sheet3():
    """the brief's hand-over sheet: v5 / the pass laid, ungraded / the pass graded v6, with the products' QA lines"""
    from PIL import ImageDraw, ImageFont
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
    items = [("v5 (the composite before the pass, as delivered 11-05)", os.path.join(OD, "m0-1-2-shell-seedream-graded-fix-v5.png")),
             ("the products pass laid on the base, ungraded", os.path.join(OD, JID + "-fix.png")),
             ("the products pass, graded v6", os.path.join(OD, JID + "-graded-fix-v6.png"))]
    w, h = 1280, 720
    out = Image.new("RGB", (3 * w + 40, h + 60 + 260), (255, 255, 255))
    d = ImageDraw.Draw(out)
    d.text((10, 14), f"M0 1.2 products pass (M0S2 a, {DATE}): v5 | laid, ungraded | graded v6. Not QA'd.", fill=(0, 0, 0), font=f)
    for i, (t, p_) in enumerate(items):
        im = Image.open(p_).convert("RGB")
        W, H = im.size
        im = im.crop((int(round(116 / 4072 * W)), int(round(65 / 2290 * H)), int(round(3956 / 4072 * W)), int(round(2225 / 2290 * H)))).resize((w, h), Image.LANCZOS)
        out.paste(im, (10 + i * (w + 10), 50))
        d.text((14 + i * (w + 10), 50 + h + 6), t, fill=(0, 0, 0), font=fs)
    n = json.load(open(os.path.join(OD, JID + "-measurements-fix-v6.json")))
    lay = json.load(open(os.path.join(OD, JID + "-fix.json")))
    y = 50 + h + 40
    lines = [f"{k}: {v.get('rendered_frame_uv')} vs box {v.get('brief_box', v.get('clay_area'))}, within 15 %: {v.get('within_15pct', '-')}" for k, v in lay["products"].items()]
    lines += [f"{k}: {json.dumps({kk: vv for kk, vv in v.items() if kk != 'ok'})} -> {'ok' if v.get('ok') else 'NOT MET'}" for k, v in n["products_pass_qa"].items()]
    for ln in lines:
        d.text((14, y), ln[:230], fill=(0, 0, 0), font=fs)
        y += 24
    p = os.path.join(REPO, "assets/renders/house-nordic-m0-products-pass-v5-raw-v6-2026-11-06.jpg")
    out.save(p, quality=88)
    print(p)


if __name__ == "__main__":
    w = sys.argv[1]
    if w == "ref2":
        ref2()
    if w == "fetch":
        fetch()
    if w == "lay":
        lay()
    if w == "grade":
        grade()
    if w == "qa":
        qa_products()
    if w == "sheet3":
        sheet3()
