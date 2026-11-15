#!/usr/bin/env python3
"""
checks_wm_door.py: the measurements on the court and front-door clay (framing_wm_door.py), render-agent, 2026-11-14. No Blender.
Reads the passes of this folder (<id>.png, <id>-depth.png, <id>-id.png) and the entrance clay (../wm-entrance-2026-11-14/).
Writes selfcheck.json and contact-sheet.jpg.

  python3 checks_wm_door.py              # everything that is rendered
  python3 checks_wm_door.py --d0         # the D0 table and the gate only (printed)
"""
import argparse
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
ENT = os.path.join(HERE, "..", "wm-entrance-2026-11-14")
SCRATCH = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-door"
K_U, K_V = 24.0 / 36.0, 24.0 / 36.0 * 16.0 / 9.0
DEPTH_UNITS_PER_M = 5000.0
REG = dict(canvas=(2720, 1530), box=(77.4882, 43.4301, 2642.5118, 1486.5699))
TALL = dict(canvas=(2496, 1664), box=(71.11, 170.00, 2424.89, 1494.00))
D0 = dict(loc=[7.40, 8.15, 1.20], yaw=90.0, u0=0.36, v0=0.48)
HDL = [2.462, 8.15, 1.20]
COURT_WALLS, REVEAL, LEAF = (61, 62, 63), (64,), (70, 71)
HALL_FRONT, OPENING = (12,), (20, 21, 22, 23, 24) + tuple(range(30, 44)) + (0, 50)


def r4(x):
    return None if x is None else round(float(x), 4)


def frames():
    F = {"D0-closed": dict(D0, canvas="reg"), "D0-none": dict(D0, canvas="reg"), "D0-open": dict(D0, canvas="reg"),
         "HD": dict(loc=HDL, yaw=90.0, u0=0.36, v0=0.48, canvas="tall"), "HDx": dict(loc=HDL, yaw=25.0, u0=0.47, v0=0.50, canvas="tall"),
         "HD57": dict(loc=HDL, yaw=57.5, u0=0.415, v0=0.49, canvas="reg"), "HT": dict(loc=[3.60, 8.15, 1.20], yaw=90.0, u0=0.36, v0=0.48, canvas="reg")}
    L = math.hypot(HDL[0] - D0["loc"][0], HDL[1] - D0["loc"][1])
    for k in range(12):
        t = k / 11
        F[f"c1/S{k:02d}"] = dict(loc=[D0["loc"][0] + (HDL[0] - D0["loc"][0]) * t, 8.15, 1.20], yaw=90.0, u0=0.36, v0=0.48, canvas="reg", s=L * t)
    for f in F.values():
        f.setdefault("s", None)
    return F, L


def uv(f, p):
    y = math.radians(f["yaw"])
    dx, dy = p[0] - f["loc"][0], p[1] - f["loc"][1]
    d = -math.sin(y) * dx - math.cos(y) * dy
    x = math.cos(y) * dx - math.sin(y) * dy
    z = p[2] if len(p) > 2 else f["loc"][2]
    return f["u0"] + K_U * x / d, f["v0"] + K_V * (f["loc"][2] - z) / d, d


class Passes:
    def __init__(self, fid, f, folder=HERE):
        self.fid, self.f = fid, f
        C = REG if f["canvas"] == "reg" else TALL
        self.W, self.H = C["canvas"]
        b = C["box"]
        self.ox, self.oy, self.fx, self.fy = b[0], b[1], b[2] - b[0], b[3] - b[1]
        self.cls = np.asarray(Image.open(os.path.join(folder, fid + "-id.png")))
        d16 = np.asarray(Image.open(os.path.join(folder, fid + "-depth.png")))
        self.depth = np.where(d16 == 65535, np.inf, d16.astype(np.float64) / DEPTH_UNITS_PER_M)
        self.png = os.path.join(folder, fid + ".png")
        assert self.cls.shape == (self.H, self.W), (fid, self.cls.shape)

    def u(self, px):
        return (px - self.ox) / self.fx

    def v(self, py):
        return (py - self.oy) / self.fy

    def row(self, v):
        return int(min(self.H - 1, max(0, math.floor(self.oy + v * self.fy))))

    def col(self, u):
        return int(min(self.W - 1, max(0, math.floor(self.ox + u * self.fx))))

    def frame(self):
        return (slice(int(round(self.oy)), int(round(self.oy + self.fy))), slice(int(round(self.ox)), int(round(self.ox + self.fx))))

    def world(self):
        f = self.f
        u = (np.arange(self.W) + 0.5 - self.ox) / self.fx
        v = (np.arange(self.H) + 0.5 - self.oy) / self.fy
        y = math.radians(f["yaw"])
        d = np.where(np.isfinite(self.depth), self.depth, np.nan)
        xc = (u[None, :] - f["u0"]) * d / K_U
        return (f["loc"][0] - d * math.sin(y) + xc * math.cos(y), f["loc"][1] - d * math.cos(y) - xc * math.sin(y),
                f["loc"][2] - (v[:, None] - f["v0"]) * d / K_V)

    def step_x(self, row, a, b, lo=0, hi=None):
        c = self.cls[row]
        for x in range(max(0, lo), min(self.W - 1, self.W - 1 if hi is None else hi)):
            if c[x] in a and c[x + 1] in b:
                return x + 1
        return None

    def step_y(self, col, a, b, lo=0, hi=None):
        c = self.cls[:, col]
        for y in range(max(0, lo), min(self.H - 1, self.H - 1 if hi is None else hi)):
            if c[y] in a and c[y + 1] in b:
                return y + 1
        return None

    def extent(self, ids, inside_frame=True):
        m = np.isin(self.cls, ids)
        if inside_frame:
            fb = self.frame()
            mm = np.zeros_like(m)
            mm[fb] = m[fb]
            m = mm
        ys, xs = np.nonzero(m)
        if not len(xs):
            return None
        return [self.u(xs.min()), self.u(xs.max() + 1), self.v(ys.min()), self.v(ys.max() + 1)]

    def share(self, ids):
        return float(np.isin(self.cls[self.frame()], ids).mean())


# ---------------------------------------------------------------------------------------------------------------
# D0: the designer's section 3.2, value by value, and the gate
# ---------------------------------------------------------------------------------------------------------------
def table_d0(P, gate_tol=0.02):
    rows = []
    f = P.f

    def add(key, designer, clay, unit, method, note="", tol=gate_tol, gate=True):
        diff = clay - designer if isinstance(designer, (int, float)) and isinstance(clay, (int, float)) else None
        rows.append(dict(key=key, designer=designer, clay=r4(clay) if isinstance(clay, float) else clay, diff=r4(diff), unit=unit, method=method,
                         note=note, over_gate=bool(gate and diff is not None and abs(diff) > tol)))

    X, Y, Z = P.world()
    r0 = P.row(f["v0"])
    add("left frame edge meets the court's left wall at X", 4.72, float(X[r0, P.col(0.0)]), "m", "depth pass, frame column u 0, row v0")
    lc = P.step_x(P.row(0.7), (62,), (61,))
    add("left corner X 3.95 / Y 9.60, u", 0.080, P.u(lc) if lc else None, "u", "id pass, row v 0.7 (below the window)")
    e = P.extent((75, 76))
    if e:
        add("bath window (frame + glass), u left", 0.053, e[0], "u", "id pass, extent in the frame")
        add("bath window, u right", 0.080, e[1], "u", "id pass", "its right side is the corner")
        add("bath window, v top", 0.12, e[2], "v", "id pass", "Z 2.15 at the far jamb X 4.25")
        add("bath window, v bottom", 0.55, e[3], "v", "id pass", "Z 1.00 at the corner X 3.95")
    ol = P.step_x(r0, (61,), REVEAL + LEAF + (72, 66, 60))
    orr = P.step_x(r0, REVEAL + LEAF + (72,), (61,), lo=ol or 0)
    add("outer opening (X 3.95), u left (Y 8.80)", 0.234, P.u(ol) if ol else None, "u", "id pass, row v0, door wall -> reveal")
    add("outer opening (X 3.95), u right (Y 7.80)", 0.428, P.u(orr) if orr else None, "u", "id pass, row v0, reveal -> door wall")
    if ol and orr:
        cmid = (P.u(ol) + P.u(orr)) / 2
        add("door centre (Y 8.30), u (left third 0.333)", 0.331, cmid, "u", "id pass: middle of the outer opening (a frontal plane: exact)")
        c = P.col(cmid)
        hy = P.step_y(c, (61,), REVEAL + LEAF)
        fy_ = P.step_y(c, REVEAL + LEAF + (60, 66), (61,), lo=P.row(0.5))
        add("outer opening, head v (Z 2.40)", 0.068, P.v(hy) if hy else None, "v", "id pass, column at the door centre")
        add("outer opening, floor v (Z 0)", 0.892, P.v(fy_) if fy_ else uv(f, (3.95, 8.30, 0.0))[1], "v",
            "id pass" if fy_ else "plan projection (the stone runs on into the reveal: no id step at X 3.95 on the door axis)")
    le = P.extent(LEAF)
    if le:
        add("leaf (X 3.66), u left", 0.244, le[0], "u", "id pass, leaf extent")
        add("leaf, u right", 0.422, le[1], "u", "id pass")
        add("leaf, v top", 0.100, le[2], "v", "id pass")
        add("leaf, v bottom", 0.860, le[3], "v", "id pass")
        add("leaf rectangle for motion-agent: u 0.2441-0.4224, v 0.0997-0.8603 (left)", 0.2441, le[0], "u", "id pass", tol=0.002)
        add("leaf rectangle: right", 0.4224, le[1], "u", "id pass", tol=0.002)
        add("leaf rectangle: top", 0.0997, le[2], "v", "id pass", tol=0.002)
        add("leaf rectangle: bottom", 0.8603, le[3], "v", "id pass", tol=0.002)
        add("vanishing point (0.36, 0.48) inside the leaf", "inside", "inside" if (le[0] < f["u0"] < le[1] and le[2] < f["v0"] < le[3]) else "OUTSIDE",
            "", "u0 / v0 against the leaf extent", gate=False)
    he = P.extent((72,))
    if he:
        add("pull, u (centre)", 0.405, (he[0] + he[1]) / 2, "u", "id pass, pull extent (bar + standoffs)")
        add("pull, v top", 0.43, he[2], "v", "id pass")
        add("pull, v bottom", 0.62, he[3], "v", "id pass")
    rc = P.step_x(r0, (61,), (63,), lo=orr or 0)
    add("right corner X 3.95 / Y 6.55, u (right third 0.667)", 0.669, P.u(rc) if rc else None, "u", "id pass, row v0")
    add("right frame edge on the court's right wall at X", 5.73, float(X[r0, P.col(1.0) - 1]), "m", "depth pass, frame column u 1")
    c55 = P.col(0.55)
    fl = P.step_y(c55, (61, 66), (60,), lo=P.row(0.5))
    add("floor line at the door wall, v", 0.892, P.v(fl) if fl else None, "v", "id pass, column u 0.55: plaster / foot line -> stone",
        "the 1 cm dark line sits above it (v of its top {:.4f})".format(P.v(P.step_y(c55, (61,), (66,), lo=P.row(0.5)) or 0)))
    rb = P.row(1.0) - 1
    add("court floor seen to X (bottom frame edge, centre)", 4.67, float(X[rb, P.col(0.5)]), "m", "depth pass, bottom row of the frame")
    rt = P.row(0.0)
    add("top frame edge on the door wall at Z", 2.60, float(Z[rt, c55]), "m", "depth pass, top row of the frame, u 0.55")
    fb = P.frame()
    ids = set(np.unique(P.cls[fb]).tolist())
    add("court ceiling or sky in the frame (px)", 0, int(np.isin(P.cls[fb], (65, 0, 67)).sum()), "px", "id pass inside the frame", tol=0)
    add("court ceiling or sky in the canvas overscan (px)", 0, int(np.isin(P.cls, (65, 0, 67)).sum()), "px", "id pass, whole canvas", gate=False)
    sh = {k: P.share(v) for k, v in (("plaster", COURT_WALLS + REVEAL + (66,)), ("stone", (60,)), ("walnut", LEAF), ("bronze", (72, 75)),
                                      ("fluted glass", (76,)))}
    add("plaster share of the frame (designer: about 60 %)", 0.60, sh["plaster"], "share", "id pass", gate=False)
    add("stone + walnut share (designer: about 30 %)", 0.30, sh["stone"] + sh["walnut"], "share", "id pass", gate=False)
    add("bronze share (designer: under 1 %)", 0.01, sh["bronze"], "share", "id pass", gate=False)
    comp = dict(door_on_left_third=bool(ol and orr and abs((P.u(ol) + P.u(orr)) / 2 - 1 / 3) <= 0.02),
                corner_on_right_third=bool(rc and abs(P.u(rc) - 2 / 3) <= 0.02),
                vanishing_point_inside_the_door=bool(le and le[0] < f["u0"] < le[1] and le[2] < f["v0"] < le[3]),
                leaf_rectangle_within_0_002=bool(le and all(abs(a - b) <= 0.002 for a, b in zip(le, (0.2441, 0.4224, 0.0997, 0.8603)))),
                no_ceiling_or_sky=bool(not ids & {0, 65, 67}))
    over = [r["key"] for r in rows if r["over_gate"]]
    gate = dict(composition=comp, values_over_0_02=over, passed=bool(all(comp.values()) and not over),
                rule="brief 2: the composition holds (door on the left third, corner on the right third, vanishing point inside the door, the "
                     "leaf's rectangle) and no value off by more than 0.02 of the frame")
    return rows, gate, sorted(ids)


def light_d0(P):
    rgb = np.asarray(Image.open(P.png).convert("RGB")).astype(np.float64)
    lin = np.where(rgb / 255 <= 0.04045, rgb / 255 / 12.92, ((rgb / 255 + 0.055) / 1.055) ** 2.4) @ np.array([0.2126, 0.7152, 0.0722])
    out = {}
    for c, n in ((61, "door wall"), (62, "left wall"), (63, "right wall"), (60, "stone"), (70, "leaf"), (11, "hall far wall (through the door)"), (82, "jib door")):
        m = P.cls == c
        if m.sum() > 50:
            out[n] = round(float(np.median(lin[m])), 4)
    if "door wall" in out and "hall far wall (through the door)" in out:
        out["court_over_hall_stops"] = round(math.log2(out["door wall"] / out["hall far wall (through the door)"]), 2)
    if "door wall" in out and "leaf" in out:
        out["court_over_leaf_stops"] = round(math.log2(out["door wall"] / out["leaf"]), 2)
    return out


# ---------------------------------------------------------------------------------------------------------------
# clip 1: the path events (analytic, the plan's projection) and what each station shows on its right side
# ---------------------------------------------------------------------------------------------------------------
def clip1_events(L):
    xc = lambda s: D0["loc"][0] - s
    f = lambda s: dict(loc=[xc(s), 8.15, 1.20], yaw=90.0, u0=0.36, v0=0.48)

    def leave(p, edge):
        lo, hi = 0.0, L
        def g(s):
            u_, v_, d = uv(f(s), p)
            if d <= 1e-6:
                return 1.0
            return {"top": -v_, "bottom": v_ - 1, "left": -u_, "right": u_ - 1}[edge]
        if g(lo) * g(hi) > 0:
            return None
        for _ in range(60):
            m = (lo + hi) / 2
            if g(m) * g(lo) > 0:
                lo = m
            else:
                hi = m
        return round((lo + hi) / 2, 3)
    # the front wall Y 6.35 (and the opening at X 0.95-2.15 in it) is seen past the right jamb's inner edge (3.60, 7.80) once
    # Xp <= Xc - (Xc - 3.60) * 1.80 / 0.35
    enter = lambda xp: round(D0["loc"][0] - (18.514285714 - xp) / 4.142857143, 3)
    ev = {"outer opening head (X 3.95, Z 2.40) leaves the top": (leave((3.95, 8.30, 2.40), "top"), 0.49),
          "outer opening floor (X 3.95, Z 0) leaves the bottom": (leave((3.95, 8.30, 0.0), "bottom"), 0.71),
          "left jamb: the arris (3.95, 8.80) leaves the left edge": (leave((3.95, 8.80, 1.2), "left"), 2.25),
          "left jamb: the leaf line (3.60, 8.80) leaves the left edge": (leave((3.60, 8.80, 1.2), "left"), 2.60),
          "right jamb: the arris (3.95, 7.80) leaves the right edge": (leave((3.95, 7.80, 1.2), "right"), 3.09),
          "right jamb: the inner edge (3.60, 7.80) leaves the right edge": (leave((3.60, 7.80, 1.2), "right"), 3.44),
          "the hall corner (0.80, 6.35) appears past the right jamb": (enter(0.80), None),
          "the opening to the living (0.95, 6.35) appears past the right jamb": (enter(0.95), 3.16),
          "the open leaf's far end (2.60, 8.74) leaves the left edge": (leave((2.60, 8.74, 1.2), "left"), 3.71),
          "the hall floor at the far wall (0.80, Z 0) leaves the bottom": (leave((0.80, 8.15, 0.0), "bottom"), 3.86),
          "the opening to the living (0.95, 6.35) leaves the right edge": (leave((0.95, 6.35, 1.2), "right"), None),
          "the hall corner (0.80, 6.35) leaves the right edge": (leave((0.80, 6.35, 1.2), "right"), 4.73)}
    return {k: dict(clay_s_m=v[0], motion_agent_s_m=v[1], diff_m=r4(v[0] - v[1]) if (v[0] is not None and v[1] is not None) else None) for k, v in ev.items()}


def stations(F, PS):
    out = {}
    for k in range(12):
        fid = f"c1/S{k:02d}"
        if fid not in PS:
            continue
        P = PS[fid]
        fb = P.frame()
        cl = P.cls[fb]
        right = {}
        for nm, ids in (("hall front wall (Y 6.35)", HALL_FRONT), ("walnut lining of O-entry-living", (20, 21, 22, 23, 24)),
                        ("living room seen through it", tuple(range(30, 44)) + (0, 50)), ("hall right wall (X 3.60, inside face)", (13,)),
                        ("front-door reveal, plaster (jambs and head)", (64,)), ("court", (60, 61, 62, 63, 65, 66, 67))):
            m = np.isin(cl, ids)
            if m.any():
                xs = np.nonzero(m.any(0))[0]
                right[nm] = dict(share_of_frame=round(float(m.mean()), 4), u=[round(float(xs.min() / cl.shape[1]), 3), round(float((xs.max() + 1) / cl.shape[1]), 3)])
        out[fid] = dict(s_m=r4(F[fid]["s"]), camera_x=r4(F[fid]["loc"][0]),
                        front_wall_and_opening_share=round(float(np.isin(cl, HALL_FRONT + OPENING).mean()), 4),
                        what_is_seen=right,
                        shares=dict(court=round(float(np.isin(cl, (60, 61, 62, 63, 64, 65, 66, 67, 75, 76)).mean()), 4),
                                    hall=round(float(np.isin(cl, (10, 11, 12, 13, 14, 15, 17, 25, 82, 83)).mean()), 4),
                                    leaf=round(float(np.isin(cl, (70, 71, 72)).mean()), 4)))
    return out


# ---------------------------------------------------------------------------------------------------------------
# the turn point: HD, HDx (3:2), HD57, HT
# ---------------------------------------------------------------------------------------------------------------
def turn_point(F, PS):
    out = {}
    for fid in ("HD", "HDx", "HD57", "HT"):
        if fid not in PS:
            continue
        P = PS[fid]
        fb = P.frame()
        ids_f = set(np.unique(P.cls[fb]).tolist())
        ids_c = set(np.unique(P.cls).tolist())
        X, Y, Z = P.world()
        rec = dict(ids_in_frame=sorted(ids_f), ids_in_canvas=sorted(ids_c),
                   front_door_or_leaf_px_in_canvas=int(np.isin(P.cls, (70, 71, 72)).sum()))
        if fid == "HD":
            wall = P.cls == 11
            zz = Z[wall | (P.cls == 82)]
            rec.update(wall_Z_in_canvas=[r4(np.nanmin(zz)), r4(np.nanmax(zz))], designer_Z_in_frame="0.5-1.9", motion_agent_Z_in_canvas="0.29-2.05",
                       floor_ceiling_corner_px_in_canvas=int(np.isin(P.cls, (10, 14, 15, 12, 13)).sum()),
                       jib_seams_u=[r4(uv(P.f, (0.80, 9.00, 1.2))[0]), r4(uv(P.f, (0.80, 8.10, 1.2))[0])],
                       corner_Y635_u=r4(uv(P.f, (0.80, 6.35, 1.2))[0]))
            r0 = P.row(P.f["v0"])
            xs = [x for x in range(P.W - 1) if P.cls[r0, x] != P.cls[r0, x + 1]]
            rec["id_steps_on_the_v0_row_u"] = [round(P.u(x + 1), 4) for x in xs]
        if fid == "HDx":
            top = P.cls[0]
            rec["soffit_or_lining_in_the_canvas_top_row_px"] = int(np.isin(top, (20, 21, 22, 23)).sum())
            rec["head_corner_at_the_left_jamb_v"] = r4(uv(P.f, (0.95, 6.35, 2.40))[1])
            rec["canvas_top_v"] = r4(-P.oy / P.fy)
            r0 = P.row(P.f["v0"])
            st = [x for x in range(P.W - 1) if P.cls[r0, x] != P.cls[r0, x + 1]]
            rec["id_steps_on_the_v0_row_u"] = [round(P.u(x + 1), 4) for x in st]
            rec["opening_u_hall_face"] = [r4(uv(P.f, (0.95, 6.35))[0]), r4(uv(P.f, (2.15, 6.35))[0])]
        if fid == "HT":
            fbm = np.zeros(P.cls.shape, bool)
            fbm[fb] = True
            for nm, ids in (("front wall + lining + living (right side)", HALL_FRONT + OPENING), ("hall far wall", (11, 82, 83)), ("floor", (10, 25))):
                m = np.isin(P.cls, ids) & fbm
                if m.any():
                    xs = np.nonzero(m.any(0))[0]
                    rec[nm] = dict(share=round(float(m.sum() / fbm.sum()), 4), u=[round(P.u(xs.min()), 3), round(P.u(xs.max() + 1), 3)])
            rec["far_wall_distance_m"] = r4(F["HT"]["loc"][0] - 0.80)
        out[fid] = rec
    return out


def reproject_edges(A, B):
    """Structure edges of A lifted with A's depth and projected into B; the distance (px) to B's nearest structure edge, where B sees the
    same point (depth agrees within 1 cm + 1 %)."""
    import cv2
    EA = np.asarray(Image.open(A.png.replace(".png", "-edges.png"))) < 128
    EB = np.asarray(Image.open(B.png.replace(".png", "-edges.png"))) < 128
    X, Y, Z = A.world()
    ys, xs = np.nonzero(EA & np.isfinite(A.depth))
    f = B.f
    y = math.radians(f["yaw"])
    dx, dy = X[ys, xs] - f["loc"][0], Y[ys, xs] - f["loc"][1]
    d = -math.sin(y) * dx - math.cos(y) * dy
    ok = d > 0.1
    u_ = f["u0"] + K_U * (math.cos(y) * dx - math.sin(y) * dy) / np.where(ok, d, 1)
    v_ = f["v0"] + K_V * (f["loc"][2] - Z[ys, xs]) / np.where(ok, d, 1)
    px, py = B.ox + u_ * B.fx, B.oy + v_ * B.fy
    ok &= (px >= 2) & (px < B.W - 2) & (py >= 2) & (py < B.H - 2)
    pxi, pyi = np.floor(px[ok]).astype(int), np.floor(py[ok]).astype(int)
    seen = np.abs(B.depth[pyi, pxi] - d[ok]) < 0.01 + 0.01 * d[ok]
    dt = cv2.distanceTransform((~EB).astype(np.uint8), cv2.DIST_L2, 5)
    dist = dt[pyi[seen], pxi[seen]]
    if not len(dist):
        return dict(src=A.fid, dst=B.fid, edge_px_projected=0, note="no structure edge of the source lies in what the destination sees")
    return dict(src=A.fid, dst=B.fid, edge_px_projected=int(seen.sum()), median_px=r4(np.median(dist)), p90_px=r4(np.percentile(dist, 90)),
                share_within_2px=r4((dist <= 2.0).mean()), max_px=r4(dist.max()),
                note="pixel-centre sampling on both sides puts a perfect match at 0-1 px")


def entrance_frames():
    p0, p1 = (2.877, 9.039), (0.83, 4.64)
    out = {}
    for k in range(12):
        t = k / 11
        out[f"b/S{k:02d}"] = dict(loc=[p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t, 1.20], yaw=25.0, u0=0.47, v0=0.50, canvas="reg")
    out["b/S00"] = dict(out["b/S00"])
    return out


def hdx_on_the_line(F):
    p0, p1 = np.array((2.877, 9.039)), np.array((0.83, 4.64))
    q = np.array(HDL[:2])
    t = float(np.dot(q - p0, p1 - p0) / np.dot(p1 - p0, p1 - p0))
    off = float(np.linalg.norm(p0 + t * (p1 - p0) - q))
    return dict(s_from_H0x_m=r4(t * np.linalg.norm(p1 - p0)), off_the_line_m=r4(off), designer_s=0.981,
                between="b/S02 (s 0.882) and b/S03 (s 1.323)")


def font(sz):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def tile(P, w, label, sub=""):
    im = Image.open(P.png).convert("RGB")
    h = round(w * im.size[1] / im.size[0])
    im = im.resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    k = w / P.W
    d.rectangle([P.ox * k, P.oy * k, (P.ox + P.fx) * k, (P.oy + P.fy) * k], outline=(210, 60, 40), width=1)
    d.rectangle([0, 0, w, 20 + (16 if sub else 0)], fill=(20, 20, 20))
    d.text((6, 3), label, fill=(255, 255, 255), font=font(13))
    if sub:
        d.text((6, 20), sub, fill=(200, 200, 200), font=font(11))
    return im


def contact_sheet(F, PS, st, out_path):
    pad, head = 8, 54
    w4 = 660
    Wd = 4 * w4 + 5 * pad
    sh = Image.new("RGB", (Wd, 3000), (244, 243, 240))
    d = ImageDraw.Draw(sh)
    d.text((pad, 8), "Warm-modern court and front door, clay, and the S1 cameras. render-agent 2026-11-14, 0 tokens (the D0 still is in assets/renders/hall/"
                     "warm-modern/door-2026-11-14/). Red box = the camera frame.", fill=(15, 15, 15), font=font(17))
    d.text((pad, 30), "Row 1: D0 closed / no leaf / open, the D0 still (graded). Row 2: HD, HDx (3:2 canvas), HD57 (reserve), HT. Then clip 1, stations S00-S11.",
           fill=(60, 60, 60), font=font(13))
    y = head
    row1 = [("D0-closed", "D0, leaf closed"), ("D0-none", "D0, no leaf"), ("D0-open", "D0, leaf open 90")]
    x = pad
    hmax = 0
    for fid, lab in row1:
        if fid in PS:
            t = tile(PS[fid], w4, lab)
            sh.paste(t, (x, y))
            hmax = max(hmax, t.size[1])
        x += w4 + pad
    still = os.path.join(HERE, "..", "..", "..", "..", "renders", "hall", "warm-modern", "door-2026-11-14", "d0-graded.png")
    if os.path.exists(still):
        P = PS.get("D0-closed")
        t = Image.open(still).convert("RGB").resize((w4, round(w4 * 1530 / 2720)), Image.LANCZOS)
        dd = ImageDraw.Draw(t)
        dd.rectangle([0, 0, w4, 20], fill=(20, 20, 20))
        dd.text((6, 3), "D0 still (seedream-5-pro, r1 + paving fix), display grade", fill=(255, 255, 255), font=font(13))
        sh.paste(t, (x, y))
    y += hmax + pad
    x = pad
    hmax = 0
    for fid, lab in (("HD", "HD (3:2) yaw 90"), ("HDx", "HDx (3:2) yaw 25"), ("HD57", "HD57 yaw 57.5 (reserve)"), ("HT", "HT, the door's sill, leaf open")):
        if fid in PS:
            t = tile(PS[fid], w4, lab)
            sh.paste(t, (x, y))
            hmax = max(hmax, t.size[1])
        x += w4 + pad
    y += hmax + pad
    d.text((pad, y + 4), "Clip 1: D0 (leaf open) -> HD, 12 stations every 0.449 m, yaw 90, shift 0.36 / 0.48; the share of the frame that the hall's front wall, "
                         "the opening and the living room take", fill=(15, 15, 15), font=font(15))
    y += 26
    w6 = (Wd - 7 * pad) // 6
    for k in range(12):
        fid = f"c1/S{k:02d}"
        if fid not in PS:
            continue
        sub = f"front wall + opening {st[fid]['front_wall_and_opening_share'] * 100:.1f} %" if fid in st else ""
        t = tile(PS[fid], w6, f"S{k:02d}  s {F[fid]['s']:.2f} m", sub)
        sh.paste(t, (pad + (k % 6) * (w6 + pad), y + (k // 6) * (t.size[1] + pad)))
        th = t.size[1]
    y += 2 * (th + pad)
    sh.crop((0, 0, Wd, y + pad)).save(out_path, quality=88)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d0", action="store_true")
    a = ap.parse_args()
    F, L = frames()
    sc_path = os.path.join(HERE, "selfcheck.json")
    meta_p = os.path.join(SCRATCH, "meta.json")
    rep = {}
    if os.path.exists(meta_p):
        m = json.load(open(meta_p))
        rep.update({k: m[k] for k in ("stage", "date", "clip1_length_m", "canvases", "render", "light", "build_notes", "ids", "door", "court", "stone", "pull", "jib")})
    rep["depth_pass"] = "16-bit PNG; planar depth in metres = value / 5000; 65535 = sky; at the pixel centres"
    rep["cameras"] = {k: dict(loc=[r4(x) for x in v["loc"]], yaw=v["yaw"], lens=24, u0=v["u0"], v0=v["v0"], canvas=v["canvas"], s_m=r4(v["s"])) for k, v in F.items()}
    have = {fid: Passes(fid, F[fid]) for fid in F if os.path.exists(os.path.join(HERE, fid + "-id.png"))}
    frames_rec = {}
    for fid in F:
        p = os.path.join(SCRATCH, "frames", fid.replace("/", "_") + ".json")
        if os.path.exists(p):
            r = json.load(open(p))
            r.pop("npz", None)
            frames_rec[fid] = r
    if "D0-open" in frames_rec:
        frames_rec["c1/S00"] = dict(frames_rec["D0-open"], frame="c1/S00", copy_of="D0-open")
    rep["frames"] = frames_rec
    rows, gate, ids = table_d0(have["D0-closed"])
    rep["D0_designer_values"] = rows
    rep["D0_gate"] = gate
    rep["D0_light_linear_medians"] = {k: light_d0(have[k]) for k in ("D0-closed", "D0-open", "D0-none") if k in have}
    if a.d0:
        for r in rows:
            print(r["key"], r["designer"], r["clay"], r["diff"], "OVER" if r["over_gate"] else "")
        print(json.dumps(gate, indent=1))
        return
    rep["clip1_events"] = clip1_events(L)
    st = stations(F, have)
    rep["clip1_stations"] = st
    rep["turn_point"] = turn_point(F, have)
    rep["HDx_on_the_T-E0_line"] = hdx_on_the_line(F)
    EF = entrance_frames()
    rp = []
    for k in ("b/S02", "b/S03"):
        if "HDx" in have and os.path.exists(os.path.join(ENT, k + "-id.png")):
            B = Passes(k, EF[k], folder=ENT)
            rp.append(reproject_edges(have["HDx"], B))
            rp.append(reproject_edges(B, have["HDx"]))
    rep["HDx_vs_entrance_stations"] = rp
    if "HD" in have and "HDx" in have:
        rep["HD_vs_HDx"] = [reproject_edges(have["HDx"], have["HD"]), reproject_edges(have["HD"], have["HDx"])]
    seen = {}
    for r in frames_rec.values():
        for i, c in r.get("pass_indices_px", {}).items():
            seen.setdefault(str(i), 0)
            seen[str(i)] = max(seen[str(i)], c)
    rep["pass_indices_seen_max_px"] = seen
    rep["summary"] = dict(frames=sorted(frames_rec), D0_gate_passed=gate["passed"], D0_values_over_0_02=gate["values_over_0_02"],
                          not_allowed_px={k: v.get("not_allowed_px") for k, v in frames_rec.items() if v.get("not_allowed_px")},
                          camera_vs_plan_projection_max={k: v.get("camera_vs_plan_projection_max_px_or_mm") for k, v in frames_rec.items()})
    json.dump(rep, open(sc_path, "w"), indent=1, ensure_ascii=False)
    if all(f"c1/S{k:02d}" in have for k in range(12)):
        contact_sheet(F, have, st, os.path.join(HERE, "contact-sheet.jpg"))
    print(json.dumps(rep["summary"], indent=1))


if __name__ == "__main__":
    main()
