#!/usr/bin/env python3
"""
Whole-house clay blockout from the approved house plan (docs/house-plan.json, or docs/proposals/house-plan.json
v0.2 when the v1.0 copy does not exist yet; same geometry).

The living room is built by the approved v4.1 code (../living-room/build_v4.py: V4Shell, armchair, sofa, table,
16 slot proxies, camera rig), unchanged except: (1) the v4 stand-in vestibule boxes are not built (the real hall
is), (2) the right wall gets O-living-dining (Y 2.97-4.57, 0-2.40, skirting cut). Every other room is built here
from the plan JSON: wall solids are a non-overlapping grid decomposition of the footprint blocks minus the room
rectangles, with openings and windows cut as z-intervals; ceilings, cornice / skirting / shadow gap, windows of the
living-window family, door leaves, fixed furniture and simple slot proxies (positions from the plan where given,
otherwise derived and marked "derived").

Outputs (assets/blockout/house/)
  plan.png                       orthographic top view of the 3D model cut at 1.50 m + cameras, cones, paths
  <room>-clay.png                2048x1152, 64 samples, master camera, shell + fixed furniture + proxies
  transitions/<T>-sheet.jpg      frames every 0.5 m (pans every <= 15 deg) along each transition
  selfcheck.json                 HC1-HC7, expected vs measured u per camera, M0 pixel comparison
Run
  python3 build_house.py                       # everything
  python3 build_house.py --only plan,clays     # parts: m0cmp, plan, clays, sheets
  python3 build_house.py --res 960 --samples 16 --sheet-res 320 --out /tmp/x   # preview
  python3 build_house.py --framing <option-id|room|all|sheets>   # framing proposal options -> framing/ (framing.py);
                                               # without the flag nothing changes: the approved plan geometry
Passes (EXR) go to a temp dir outside the repo and are deleted at the end.
Same conventions as the living room: metres, X right as M0 sees it, Y from the living back wall toward the
entrance, Z up; camera mirrored (scale.x = -1); Cycles CPU, seed 7, no adaptive sampling, sky only.
"""
import argparse
import json
import math
import os
import random
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LR = os.path.join(REPO, "assets", "blockout", "living-room")
sys.path.insert(0, LR)
import bpy  # noqa: E402
import numpy as np  # noqa: E402
import build_v4 as b4  # noqa: E402
from mathutils import Vector  # noqa: E402

ba, bs = b4.ba, b4.bs
P = bs.proj
M = ba.M
TOP = 3.15                     # top of every wall solid and ceiling slab
PLAN_PATHS = [os.path.join(REPO, "docs", "house-plan.json"), os.path.join(REPO, "docs", "proposals", "house-plan.json")]
LIVING_EXCL = ((-2.77, 2.65), (-0.15, 6.35))      # region built by V4Shell (walls incl. left wall 0.47)
OPENING_LD = dict(y0=2.97, y1=4.57, z1=2.40)

EXTRA_PAL = dict(tile="#D3CFC9", door="#D6D1CA", oak_door="#B5A48D", sanitary="#E6E3DE", kit="#CFC9C1",
                 bed="#D8D2C9")
IDX = dict(wall=100, floor=101, ceiling=102, trim=103, door=105, threshold=106)
WIN_IDX0 = 150                # + k per house window
FUR_IDX0 = 110
PROXY_IDX0 = 200


def r4(x):
    return ba.r4(x)


def load_plan():
    for p in PLAN_PATHS:
        if os.path.exists(p):
            return p, json.load(open(p))
    raise SystemExit("no house-plan.json")


# ---------------------------------------------------------------------------------------
# projection by the plan equations (independent of Blender)
# ---------------------------------------------------------------------------------------
def plan_u(cam, p):
    y = math.radians(cam["yaw"])
    f = (-math.sin(y), -math.cos(y))
    r = (math.cos(y), -math.sin(y))
    dx, dy = p[0] - cam["loc"][0], p[1] - cam["loc"][1]
    d = f[0] * dx + f[1] * dy
    x = r[0] * dx + r[1] * dy
    return cam["u0"] + 0.6667 * x / d if d > 1e-6 else None


# ---------------------------------------------------------------------------------------
# living room (v4.1) with the dining opening
# ---------------------------------------------------------------------------------------
class LivingShell(b4.V4Shell):
    with_opening = True

    def vestibule(self):          # the real hall is built from the plan
        pass

    def build(self):              # = build_alts.Shell.build, right wall with O-living-dining
        cfg = self.cfg
        xl, xr, yb, yf, h, t = self.xl, self.xr, self.yb, self.yf, self.h, self.t
        win, door = cfg["window"], cfg["door"]
        g = "shell"
        bs.box("floor_base", xl - t["left"], xr + t["right"], yb - t["back"], yf + t["front"], -0.12, -0.002,
               M["floor_gap"], g, pidx=ba.SHELL_IDX["floor"])
        bs.box("ceiling", xl - t["left"], xr + t["right"], yb - t["back"], yf + t["front"], h, h + 0.15,
               M["ceiling"], g, pidx=ba.SHELL_IDX["ceiling"])
        self.planks()
        lin = 0.0
        wopen = (win["a0"], win["a1"], win["z0"], win["z1"])
        for w in ("left", "right", "back"):
            if w == "right" and self.with_opening:
                self.wall(w, (OPENING_LD["y0"], OPENING_LD["y1"], 0.0, OPENING_LD["z1"]))
            else:
                self.wall(w, wopen if win["wall"] == w else None, pad=lin)
        self.wall("front", (door["x0"], door["x1"], 0.0, door["h"]))
        self.vestibule()
        self.window(lin)
        self.skirting()
        if cfg.get("cornice"):
            self.cornice(cfg["cornice"]["h"])

    def skirting(self):
        if not self.with_opening:
            return super().skirting()
        sk, d = self.cfg["skirting"], self.cfg["door"]
        h, ps = sk["h"], ba.SHELL_IDX["skirting"]
        n0, n1, mat = -0.015, 0.0, M["moulding"]
        self.wbox("skirt_back", "back", self.xl, self.xr, n0, n1, 0, h, mat, ps)
        self.wbox("skirt_left", "left", self.yb, self.yf, n0, n1, 0, h, mat, ps)
        self.wbox("skirt_right_a", "right", self.yb, OPENING_LD["y0"], n0, n1, 0, h, mat, ps)
        self.wbox("skirt_right_b", "right", OPENING_LD["y1"], self.yf, n0, n1, 0, h, mat, ps)
        self.wbox("skirt_front_a", "front", self.xl, d["x0"], n0, n1, 0, h, mat, ps)
        self.wbox("skirt_front_b", "front", d["x1"], self.xr, n0, n1, 0, h, mat, ps)


# ---------------------------------------------------------------------------------------
# house geometry from the plan
# ---------------------------------------------------------------------------------------
def opening_rects(plan):
    """Openings and windows as plan rectangles with the cut z-range. Living openings are excluded (V4Shell)."""
    rooms = {r["id"]: r for r in plan["rooms"]}
    out = []
    for o in plan["openings"]:
        if o["id"] in ("O-entry-living", "O-living-dining"):
            continue
        if "plane_x" in o:
            xr, yr = tuple(o["plane_x"]), tuple(o["y"])
        else:
            xr, yr = tuple(o["x"]), tuple(o["plane_y"])
        z = tuple(o.get("z", (0.0, 2.40)))
        out.append(dict(id=o["id"], kind="door", x=xr, y=yr, z=z, type=o["type"]))
    for w in plan["windows"]:
        if w["id"] == "W-living" or ("plane_x" not in w and "plane_y" not in w):
            continue
        room = rooms[w["room"]]
        t = w.get("wall_t", 0.35)
        if "plane_x" in w:
            px = w["plane_x"]
            xr = (px - t, px) if abs(px - room["x"][0]) < 1e-6 else (px, px + t)
            yr = tuple(w["y"])
        else:
            py = w["plane_y"]
            yr = (py - t, py) if abs(py - room["y"][0]) < 1e-6 else (py, py + t)
            xr = tuple(w["x"])
        out.append(dict(id=w["id"], kind="window", x=xr, y=yr, z=(w["sill"], w["head"]), room=w["room"],
                        facade=w["facade"], glass=w.get("glass", "")))
    return out


def inside(p, xr, yr, eps=1e-9):
    return xr[0] - eps <= p[0] <= xr[1] + eps and yr[0] - eps <= p[1] <= yr[1] + eps


def wall_solids(plan, opens):
    """Grid decomposition of (blocks - rooms - living region) into boxes with z-intervals. Returns list of
    (x0, x1, y0, y1, z0, z1)."""
    blocks = [(tuple(b["x"]), tuple(b["y"])) for b in plan["footprint"]["outer_blocks"]]
    rooms = [(tuple(r["x"]), tuple(r["y"])) for r in plan["rooms"]]
    xs, ys = set(), set()
    for xr, yr in blocks + rooms + [LIVING_EXCL]:
        xs.update(xr)
        ys.update(yr)
    for o in opens:
        xs.update(o["x"])
        ys.update(o["y"])
    xs, ys = sorted(xs), sorted(ys)
    rows = []
    for j in range(len(ys) - 1):
        y0, y1 = ys[j], ys[j + 1]
        if y1 - y0 < 1e-6:
            continue
        cells = []
        for i in range(len(xs) - 1):
            x0, x1 = xs[i], xs[i + 1]
            if x1 - x0 < 1e-6:
                continue
            c = ((x0 + x1) / 2, (y0 + y1) / 2)
            solid = any(inside(c, *b) for b in blocks) and not any(inside(c, *r, eps=-1e-9) for r in rooms) \
                and not inside(c, *LIVING_EXCL, eps=-1e-9)
            if not solid:
                cells.append(None)
                continue
            prof = ((0.0, TOP),)
            for o in opens:
                if o["x"][1] - o["x"][0] < 1e-6 or o["y"][1] - o["y"][0] < 1e-6:
                    continue
                if inside(c, o["x"], o["y"], eps=-1e-9):
                    z0, z1 = o["z"]
                    if o["kind"] == "window":
                        z0 = z0 - 0.025          # sill board sits on top (no coplanar faces)
                    prof = tuple(iv for iv in (((0.0, z0) if z0 > 0 else None), (z1, TOP)) if iv)
            cells.append((x0, x1, prof))
        # merge runs along X with the same profile
        k = 0
        while k < len(cells):
            if cells[k] is None:
                k += 1
                continue
            x0, x1, prof = cells[k]
            m = k + 1
            while m < len(cells) and cells[m] is not None and cells[m][2] == prof and abs(cells[m][0] - x1) < 1e-9:
                x1 = cells[m][1]
                m += 1
            rows.append([x0, x1, y0, y1, prof])
            k = m
    # merge along Y (same x-range and profile, adjacent)
    rows.sort(key=lambda r: (r[0], r[1], r[4], r[2]))
    merged = []
    for r in rows:
        if merged and merged[-1][0] == r[0] and merged[-1][1] == r[1] and merged[-1][4] == r[4] \
                and abs(merged[-1][3] - r[2]) < 1e-9:
            merged[-1][3] = r[3]
        else:
            merged.append(list(r))
    out = []
    for x0, x1, y0, y1, prof in merged:
        for z0, z1 in prof:
            out.append((x0, x1, y0, y1, z0, z1))
    return out


def side_box(name, R, side, s0, s1, n0, n1, z0, z1, mat, pidx, group="shell"):
    """Box against a room side: s along the side, n outward from the room face into the wall."""
    (x0, x1), (y0, y1) = R
    if side == "x0":
        return bs.box(name, x0 - n1, x0 - n0, s0, s1, z0, z1, mat, group, pidx=pidx)
    if side == "x1":
        return bs.box(name, x1 + n0, x1 + n1, s0, s1, z0, z1, mat, group, pidx=pidx)
    if side == "y0":
        return bs.box(name, s0, s1, y0 - n1, y0 - n0, z0, z1, mat, group, pidx=pidx)
    return bs.box(name, s0, s1, y1 + n0, y1 + n1, z0, z1, mat, group, pidx=pidx)


def side_cuts(R, side, opens, doors_only=True):
    """Spans along a room side interrupted by openings on that side (doors; also windows if not doors_only)."""
    (x0, x1), (y0, y1) = R
    face = {"x0": x0, "x1": x1, "y0": y0, "y1": y1}[side]
    cuts = []
    for o in opens:
        if doors_only and o["kind"] != "door":
            continue
        if side in ("x0", "x1"):
            if (abs(o["x"][0] - face) < 1e-6 or abs(o["x"][1] - face) < 1e-6) and o["y"][1] > y0 and o["y"][0] < y1:
                cuts.append((max(o["y"][0], y0), min(o["y"][1], y1), o))
        else:
            if (abs(o["y"][0] - face) < 1e-6 or abs(o["y"][1] - face) < 1e-6) and o["x"][1] > x0 and o["x"][0] < x1:
                cuts.append((max(o["x"][0], x0), min(o["x"][1], x1), o))
    return sorted(cuts, key=lambda c: c[0])


def spans(lo, hi, cuts):
    out, s = [], lo
    for a, b, _ in cuts:
        if a > s + 1e-6:
            out.append((s, a))
        s = max(s, b)
    if hi > s + 1e-6:
        out.append((s, hi))
    return out


def room_rect(r):
    return (tuple(r["x"]), tuple(r["y"]))


def planks(R, name, seed, tiles=False):
    (x0, x1), (y0, y1) = R
    rnd = random.Random(seed)
    gap = 0.003
    if tiles:
        tw, tl = 0.60, 1.20
        x, i = x0, 0
        while x < x1 - 1e-6:
            y = y0 - (0.6 if i % 2 else 0.0)
            while y < y1 - 1e-6:
                ya, yb = max(y, y0), min(y + tl, y1)
                if yb - ya > 0.02:
                    bs.box(f"{name}_tile", x + gap / 2, min(x + tw, x1) - gap / 2, ya + gap / 2, yb - gap / 2,
                           -0.012, 0.0, M["tile"], "floor", pidx=IDX["floor"])
                y += tl
            x += tw
            i += 1
        return
    w, (lmin, lmax) = 0.25, (3.0, 4.0)
    x, col = x0, 0
    while x < x1 - 1e-6:
        y = y0 - rnd.uniform(0, lmax)
        while y < y1:
            L = rnd.uniform(lmin, lmax)
            ya, yb = max(y, y0), min(y + L, y1)
            if yb - ya > 0.05:
                bs.box(f"{name}_plank{col}", x + gap / 2, min(x + w, x1) - gap / 2, ya + gap / 2, yb - gap / 2,
                       -0.012, 0.0, rnd.choice(M["planks"]), "floor", pidx=IDX["floor"])
            y += L
        x += w
        col += 1


def house_window(o, k, R):
    """Living-window family: frame in the outer plane, painted reveal, inner sill proud 4 cm."""
    (rx0, rx1), (ry0, ry1) = R
    if abs(o["x"][1] - rx0) < 1e-6:
        side, a0, a1 = "x0", o["y"][0], o["y"][1]
    elif abs(o["x"][0] - rx1) < 1e-6:
        side, a0, a1 = "x1", o["y"][0], o["y"][1]
    elif abs(o["y"][1] - ry0) < 1e-6:
        side, a0, a1 = "y0", o["x"][0], o["x"][1]
    else:
        side, a0, a1 = "y1", o["x"][0], o["x"][1]
    t = (o["x"][1] - o["x"][0]) if side in ("x0", "x1") else (o["y"][1] - o["y"][0])
    z0, z1 = o["z"]
    fw, fd, rev = 0.06, 0.07, t
    pw, g, mm = WIN_IDX0 + k, "window", M["moulding"]
    n0, n1 = rev - fd, rev                     # frame inside the wall, flush with the outer plane
    nm = o["id"]

    def wb(n, s0, s1, a, b, za, zb, mat=mm, pidx=pw):
        return side_box(f"{nm}_{n}", R, side, s0, s1, a, b, za, zb, mat, pidx, g)
    wb("frame_bottom", a0, a1, n0, n1, z0, z0 + fw)
    wb("frame_top", a0, a1, n0, n1, z1 - fw, z1)
    wb("frame_a", a0, a0 + fw, n0, n1, z0 + fw, z1 - fw)
    wb("frame_b", a1 - fw, a1, n0, n1, z0 + fw, z1 - fw)
    mull = (a1 - a0) >= 1.39
    m = (a0 + a1) / 2
    panes = ((a0 + fw, m - 0.03), (m + 0.03, a1 - fw)) if mull else ((a0 + fw, a1 - fw),)
    if mull:
        wb("mullion", m - 0.03, m + 0.03, n0, n1, z0 + fw, z1 - fw)
    s = 0.02
    for q, (p0, p1) in enumerate(panes):
        sn0, sn1 = n0 + 0.015, n0 + 0.055
        wb(f"sash{q}_b", p0, p1, sn0, sn1, z0 + fw, z0 + fw + s)
        wb(f"sash{q}_t", p0, p1, sn0, sn1, z1 - fw - s, z1 - fw)
        wb(f"sash{q}_l", p0, p0 + s, sn0, sn1, z0 + fw + s, z1 - fw - s)
        wb(f"sash{q}_r", p1 - s, p1, sn0, sn1, z0 + fw + s, z1 - fw - s)
    e = 0.002
    wb("reveal_a", a0, a0 + e, 0, n0, z0, z1)
    wb("reveal_b", a1 - e, a1, 0, n0, z0, z1)
    wb("reveal_top", a0, a1, 0, n0, z1 - e, z1)
    wb("sill", a0 - 0.05, a1 + 0.05, -0.04, t, z0 - 0.025, z0, mm, IDX["trim"])
    return dict(side=side, a=(a0, a1), mullion=mull)


def build_house_shell(plan, opens):
    g = "shell"
    solids = wall_solids(plan, opens)
    for i, (x0, x1, y0, y1, z0, z1) in enumerate(solids):
        # walls stand on the slab (from -0.12), so nothing under them is open to the sky
        bs.box(f"hwall_{i}", x0, x1, y0, y1, -0.12 if z0 <= 0 else z0, z1, M["wall"], g, pidx=IDX["wall"])
    bb = plan["footprint"]["outer_bbox"]
    bs.box("ground_slab", bb["x"][0] - 0.2, bb["x"][1] + 0.2, bb["y"][0] - 0.2, bb["y"][1] + 0.2, -0.40, -0.1201,
           M["floor_gap"], g, pidx=IDX["floor"])
    info = dict(wall_boxes=len(solids))
    seeds = 20
    for r in plan["rooms"]:
        if r["id"] == "living":
            continue
        R = room_rect(r)
        (x0, x1), (y0, y1) = R
        h = r["h"]
        bs.box(f"{r['id']}_floor_base", x0, x1, y0, y1, -0.12, -0.012, M["floor_gap"], g, pidx=IDX["floor"])
        planks(R, r["id"], seeds, tiles=(r["id"] == "bath"))
        seeds += 1
        bs.box(f"{r['id']}_ceiling", x0, x1, y0, y1, h, TOP, M["ceiling"], "ceiling", pidx=IDX["ceiling"])
        for side in ("x0", "x1", "y0", "y1"):
            lo, hi = (y0, y1) if side in ("x0", "x1") else (x0, x1)
            cuts = side_cuts(R, side, opens)
            # living-dining opening on the dining side (x0 of kitchen-dining)
            if r["id"] == "kitchen-dining" and side == "x0":
                cuts = sorted(cuts + [(OPENING_LD["y0"], OPENING_LD["y1"], None)], key=lambda c: c[0])
            if r["id"] == "hall" and side == "y0":          # living double door (built by V4Shell)
                cuts = sorted(cuts + [(0.95, 2.15, None)], key=lambda c: c[0])
            full_open = [c for c in cuts if c[2] is not None and c[2]["z"][1] >= h - 0.31]
            # skirting (cut at doors)
            for k, (s0, s1) in enumerate(spans(lo, hi, cuts)):
                side_box(f"{r['id']}_skirt_{side}{k}", R, side, s0, s1, -0.015, 0.0, 0, 0.15, M["moulding"], IDX["trim"])
            if h >= 2.99:
                for k, (s0, s1) in enumerate(spans(lo, hi, [c for c in full_open if c[2]["z"][1] >= h - 0.01])):
                    side_box(f"{r['id']}_cornice_{side}{k}", R, side, s0, s1, -0.045, 0.0, h - 0.10, h,
                             M["moulding"], IDX["trim"])
                    side_box(f"{r['id']}_cornice2_{side}{k}", R, side, s0, s1, -0.02, 0.0, h - 0.125, h - 0.10,
                             M["moulding"], IDX["trim"])
            else:      # 2.70 rooms: shadow gap at the ceiling (dark 2 cm band, flush)
                for k, (s0, s1) in enumerate(spans(lo, hi, [c for c in full_open if c[2]["z"][1] >= h - 0.03])):
                    side_box(f"{r['id']}_sgap_{side}{k}", R, side, s0, s1, -0.0015, 0.0, h - 0.02, h,
                             M["shadow_gap"], IDX["trim"])
    # hall cut of the living double door on the hall side (front wall Y 6.20-6.35 seen from the hall)
    # corridor bulkhead toward the 3.00 hall is the corridor ceiling slab face at Y 9.80 (z 2.70-3.15).
    # door thresholds (planks through the wall) for open doors
    for o in opens:
        if o["kind"] == "door" and o["x"][1] - o["x"][0] > 1e-6 \
                and o["y"][1] - o["y"][0] > 1e-6:
            bs.box(f"{o['id']}_threshold", o["x"][0], o["x"][1], o["y"][0], o["y"][1], -0.012, 0.0,
                   M["planks"][1], "floor", pidx=IDX["threshold"])
            bs.box(f"{o['id']}_threshold_base", o["x"][0], o["x"][1], o["y"][0], o["y"][1], -0.12, -0.012,
                   M["floor_gap"], g, pidx=IDX["threshold"])
    # living double-door threshold Y 6.25-6.35 (the living planks stop at Y 6.25)
    bs.box("O-entry-living_threshold", 0.95, 2.15, 6.25, 6.35, -0.012, 0.0, M["planks"][1], "floor",
           pidx=IDX["threshold"])
    # living-dining threshold strip X 2.52-2.65 (the living planks stop at X 2.52)
    bs.box("O-living-dining_threshold", 2.52, 2.65, OPENING_LD["y0"], OPENING_LD["y1"], -0.012, 0.0,
           M["planks"][2], "floor", pidx=IDX["threshold"])
    # windows
    rooms = {r["id"]: r for r in plan["rooms"]}
    wins = {}
    k = 0
    for o in opens:
        if o["kind"] == "window":
            wins[o["id"]] = dict(house_window(o, k, room_rect(rooms[o["room"]])), pidx=WIN_IDX0 + k,
                                 facade=o["facade"], room=o["room"])
            k += 1
    info["windows"] = wins
    return info


# ---------------------------------------------------------------------------------------
# doors (leaves), fixed furniture, proxies
# ---------------------------------------------------------------------------------------
LEAVES = [
    # (name, x0, x1, y0, y1, z1, note)
    ("leaf_living_dining_a", 2.65, 2.69, 2.17, 2.97, 2.40, "O-living-dining leaf folded 180 deg on the dining side"),
    ("leaf_living_dining_b", 2.65, 2.69, 4.57, 5.37, 2.40, "O-living-dining leaf folded 180 deg on the dining side"),
    ("leaf_hall_work", -0.25, 0.65, 9.00, 9.04, 2.40, "O-hall-work, open 90 deg into the work room, hinge west jamb (plan)"),
    ("leaf_corridor_boy", 0.65, 1.55, 13.53, 13.57, 2.40, "assumed: open 90 deg into the room, hinge on the 0.20 return"),
    ("leaf_corridor_girl", 0.65, 1.55, 17.16, 17.20, 2.40, "assumed: as boy (+3.63)"),
    ("leaf_corridor_bath", 3.25, 4.25, 13.39, 13.43, 2.40, "assumed: open 90 deg into the bath, hinge on the 0.20 return"),
    ("leaf_corridor_master", 2.78, 2.82, 17.66, 18.56, 2.40, "assumed: open 90 deg into the master, hinge on the east (X 2.78) jamb"),
]


def build_doors():
    out = []
    for n, x0, x1, y0, y1, z1, note in LEAVES:
        out.append(bs.box(n, x0, x1, y0, y1, 0.0, z1, M["door"], "doors", pidx=IDX["door"]))
    # closed doors
    out.append(bs.box("front_door_closed", 3.65, 3.70, 7.10, 8.10, 0.0, 2.40, M["oak_door"], "doors", pidx=IDX["door"]))
    out.append(bs.box("laundry_door_flush", 3.096, 3.10, 14.30, 15.10, 0.0, 2.40, M["door"], "doors", pidx=IDX["door"]))
    return out


def _legs_table(name, x0, x1, y0, y1, h, mat, top=0.035, leg=0.05, inset=0.06):
    parts = [bs.box(name + "_top", x0, x1, y0, y1, h - top, h, mat, "furniture", bevel=0.004, seg=1)]
    for lx in (x0 + inset, x1 - inset - leg):
        for ly in (y0 + inset, y1 - inset - leg):
            parts.append(bs.box(name + "_leg", lx, lx + leg, ly, ly + leg, 0, h - top, mat, "furniture"))
    return parts


def _chair(name, cx, cy, face, mat):
    """Dining chair 0.45 x 0.45, seat 0.46, back 0.82 on the side opposite to 'face' (+y/-y/+x/-x)."""
    s = 0.225
    parts = _legs_table(name, cx - s, cx + s, cy - s, cy + s, 0.46, mat, top=0.04, leg=0.035, inset=0.02)
    bt = 0.03
    if face == "+y":
        parts.append(bs.box(name + "_back", cx - s, cx + s, cy - s, cy - s + bt, 0.46, 0.82, mat, "furniture"))
    elif face == "-y":
        parts.append(bs.box(name + "_back", cx - s, cx + s, cy + s - bt, cy + s, 0.46, 0.82, mat, "furniture"))
    elif face == "+x":
        parts.append(bs.box(name + "_back", cx - s, cx - s + bt, cy - s, cy + s, 0.46, 0.82, mat, "furniture"))
    else:
        parts.append(bs.box(name + "_back", cx + s - bt, cx + s, cy - s, cy + s, 0.46, 0.82, mat, "furniture"))
    return parts


def _bed(name, x0, x1, y0, y1, head_side, h=0.45, head_h=1.05, mat=None):
    mat = mat or M["bed"]
    parts = [bs.box(name + "_base", x0, x1, y0, y1, 0.08, h - 0.20, M["wood"], "furniture"),
             bs.box(name + "_mattress", x0 + 0.02, x1 - 0.02, y0 + 0.02, y1 - 0.02, h - 0.20, h, mat, "furniture",
                    bevel=0.04)]
    hb = 0.06
    if head_side == "y0":
        parts.append(bs.box(name + "_head", x0, x1, y0 - 0.0, y0 + hb, 0.0, head_h, M["wood"], "furniture", bevel=0.01))
    elif head_side == "x0":
        parts.append(bs.box(name + "_head", x0, x0 + hb, y0, y1, 0.0, head_h, M["wood"], "furniture", bevel=0.01))
    return parts


def fixed_furniture():
    """Fixed furniture (not products). Positions from the plan text where given; sizes are blockout assumptions."""
    F = {}
    W, K = M["wood"], M["kit"]
    # kitchen-dining: table centre (4.30, 1.70) long axis X; kitchen run on the south wall X 7.25;
    # tall units on the west wall Y 6.20, X 3.95-7.25.
    t = _legs_table("dining_table", 3.30, 5.30, 1.225, 2.175, 0.75, W)
    for i, cx in enumerate((3.70, 4.30, 4.90)):
        t += _chair(f"dchair_e{i}", cx, 0.95, "-y", W)
        t += _chair(f"dchair_w{i}", cx, 2.45, "+y", W)
    F["dining-table+chairs"] = dict(room="kitchen-dining", parts=t, src="plan: centre (4.30, 1.70), long axis X; size assumed 2.00 x 0.95, 6 chairs")
    kp = [bs.box("kit_counter", 6.63, 7.25, 0.40, 4.00, 0.0, 0.90, K, "furniture"),
          bs.box("kit_worktop", 6.60, 7.25, 0.40, 4.00, 0.90, 0.94, M["moulding"], "furniture"),
          bs.box("kit_wall_units", 6.90, 7.25, 0.40, 4.00, 1.50, 2.40, K, "furniture"),
          bs.box("kit_tall_s", 6.63, 7.25, 4.00, 5.58, 0.0, 2.40, K, "furniture"),
          bs.box("kit_tall_w", 3.95, 7.25, 5.58, 6.20, 0.0, 2.40, K, "furniture")]
    F["kitchen-run"] = dict(room="kitchen-dining", parts=kp, src="plan: south wall X 7.25 (tall + counter), west wall Y 6.20 X 3.95-7.25 (tall); depths/heights assumed")
    # hall: console X 2.30-3.10 on the front wall (Y 6.35); bench on the left wall (X 0.80), Y 6.35-7.98
    F["hall-console"] = dict(room="hall", parts=_legs_table("console", 2.30, 3.10, 6.35, 6.70, 0.80, W, leg=0.035, inset=0.03),
                             src="plan: X 2.30-3.10 on the front wall; depth 0.35 h 0.80 assumed")
    F["hall-bench"] = dict(room="hall", parts=[bs.box("bench_seat", 0.80, 1.20, 6.55, 7.75, 0.40, 0.45, W, "furniture"),
                                               bs.box("bench_end_a", 0.80, 1.20, 6.55, 6.59, 0.0, 0.40, W, "furniture"),
                                               bs.box("bench_end_b", 0.80, 1.20, 7.71, 7.75, 0.0, 0.40, W, "furniture")],
                           src="plan: bench on the solid left wall Y 6.35-7.98; size assumed")
    # work: desk under the north window, shelves on the east wall (Y 6.35)
    F["work-desk"] = dict(room="work", parts=_legs_table("desk", -2.30, -1.70, 7.05, 8.45, 0.75, W) +
                          _chair("desk_chair", -1.40, 7.75, "-x", W), src="plan: desk under the window; size assumed")
    F["work-shelves"] = dict(room="work", parts=[bs.box("shelf_unit", -2.15, -1.30, 6.35, 6.70, 0.0, 2.00, W, "furniture")],
                             src="plan: shelves on the east wall, visible X -2.30..-1.25; size assumed")
    # kids: bed 90x200 along the east wall, head north; desk under the window; wardrobe on the south wall
    for kid, dy in (("boy", 0.0), ("girl", 3.63)):
        y0 = 10.25 + dy
        parts = _bed(f"{kid}_bed", -2.30, -0.30, y0, y0 + 0.95, "x0", h=0.42, head_h=0.85)
        parts += _legs_table(f"{kid}_desk", -2.30, -1.80, y0 + 1.15, y0 + 2.15, 0.65, W, leg=0.035, inset=0.03)
        parts += [bs.box(f"{kid}_wardrobe", 0.95, 1.55, y0 + 0.20, y0 + 2.00, 0.0, 2.20, M["kit"], "furniture")]
        F[f"{kid}-bed+desk+wardrobe"] = dict(room=kid, parts=parts,
                                             src="plan: bed 90x200 on the east wall head north, desk/play under the window, wardrobe on the south wall (out of frame); sizes assumed")
    # master: bed head on Y 17.66 centre X -0.25; nightstands; wardrobes on the west wall (kept clear of MB0)
    parts = _bed("master_bed", -1.15, 0.65, 17.66, 19.76, "y0", h=0.50, head_h=1.15)
    parts += [bs.box("ns_a", -1.70, -1.20, 17.66, 18.06, 0.0, 0.55, W, "furniture"),
              bs.box("ns_b", 0.70, 1.20, 17.66, 18.06, 0.0, 0.55, W, "furniture"),
              bs.box("wardrobes", -2.30, 1.15, 21.06, 21.66, 0.0, 2.40, M["kit"], "furniture")]
    F["master-bed+nightstands+wardrobes"] = dict(room="master", parts=parts,
                                                 src="plan: bed head on Y 17.66, centre X -0.25; wardrobes on the west wall; 180x210, wardrobe X -2.30..1.15 (stops before MB0) assumed")
    # bath: double vanity on the east wall under the window, shower on the south wall, WC on the west wall
    parts = [bs.box("vanity", 3.70, 5.30, 9.95, 10.45, 0.30, 0.85, W, "furniture"),
             bs.box("vanity_top", 3.68, 5.32, 9.95, 10.47, 0.85, 0.88, M["sanitary"], "furniture"),
             bs.box("shower_tray", 5.25, 6.25, 11.80, 13.59, 0.0, 0.02, M["sanitary"], "furniture"),
             bs.box("shower_screen", 5.24, 5.26, 11.80, 12.70, 0.02, 2.00, M["curtain"], "furniture"),
             bs.box("wc", 4.75, 5.10, 13.00, 13.59, 0.0, 0.40, M["sanitary"], "furniture"),
             bs.box("wc_cistern", 4.70, 5.15, 13.45, 13.59, 0.40, 1.10, M["sanitary"], "furniture")]
    F["bath-fixtures"] = dict(room="bath", parts=parts,
                              src="plan: vanity on the east wall under the window, shower on the south wall, WC on the west wall; sizes and X/Y assumed (WC kept clear of the assumed door leaf)")
    roots = {}
    for i, (k, v) in enumerate(F.items()):
        pidx = FUR_IDX0 + i
        for p in v["parts"]:
            p.pass_index = pidx
        roots[k] = dict(room=v["room"], pidx=pidx, parts=v["parts"], src=v["src"])
    return roots


def house_proxies():
    """Slot proxies outside the living room. src 'plan' = position stated in the plan, 'derived' = placed here."""
    G = "proxies"
    out = {}
    O, T, Rg, C, A, Hd = M["obj"], M["textile"], M["rug"], M["curtain"], M["art"], M["holder"]

    def cyl(n, c, r, z0, z1, mat=O):
        return bs.cone(n, c[0], c[1], z0, z1, r, r, mat, G, verts=48)

    def bx(n, x0, x1, y0, y1, z0, z1, mat=O, bevel=0.0):
        return bs.box(n, x0, x1, y0, y1, z0, z1, mat, G, bevel=bevel)

    def put(room, slot, objs, src):
        out[f"{room}/{slot}"] = dict(room=room, slot=slot, objs=objs, src=src)

    # hall
    put("hall", "framed-art", [bx("h_art", 2.42, 2.98, 6.35, 6.38, 1.30, 1.85, A)], "derived (console vignette, plan)")
    put("hall", "table-lamp", [cyl("h_lamp", (2.47, 6.52), 0.12, 1.05, 1.30, C), cyl("h_lamp_b", (2.47, 6.52), 0.06, 0.80, 1.05, Hd)], "derived (console vignette, plan)")
    put("hall", "console-vessel", [cyl("h_vessel", (2.97, 6.50), 0.07, 0.80, 1.12)], "derived (console vignette, plan)")
    put("hall", "key-tray", [bx("h_tray", 2.66, 2.84, 6.44, 6.56, 0.80, 0.83, Hd)], "derived (console vignette, plan)")
    put("hall", "runner-rug", [bx("h_runner", 1.70, 2.50, 6.75, 9.45, 0.0, 0.012, Rg)], "derived")
    put("hall", "ceiling-light", [cyl("h_ceil", (2.20, 8.05), 0.20, 2.80, 2.97)], "derived")
    put("hall", "bench-cushion", [bx("h_cush", 0.82, 1.18, 6.58, 7.72, 0.45, 0.50, T, 0.015)], "derived (bench, plan)")
    put("hall", "basket", [cyl("h_basket", (1.00, 7.15), 0.16, 0.0, 0.30)], "derived (under the bench)")
    put("hall", "wall-hooks", [bx("h_hooks", 0.80, 0.86, 6.75, 7.55, 1.65, 1.72, Hd)], "derived (left wall, plan)")
    # kitchen-dining
    put("kitchen-dining", "dining-pendant", [cyl("d_pend", (4.30, 1.70), 0.30, 1.52, 1.80), cyl("d_cord", (4.30, 1.70), 0.004, 1.80, 3.0, Hd)],
        "plan (over the table centre, bottom 0.77 above the top)")
    put("kitchen-dining", "table-runner", [bx("d_runner", 3.55, 5.05, 1.55, 1.85, 0.75, 0.754, T)], "derived")
    put("kitchen-dining", "centerpiece-vase", [cyl("d_vase", (4.30, 1.70), 0.08, 0.754, 1.05)], "derived")
    put("kitchen-dining", "candle-holders", [cyl("d_cand_a", (3.92, 1.68), 0.04, 0.754, 0.98), cyl("d_cand_b", (4.02, 1.76), 0.04, 0.754, 0.92)], "derived")
    put("kitchen-dining", "bowl", [cyl("d_bowl", (4.75, 1.70), 0.13, 0.754, 0.84)], "derived")
    put("kitchen-dining", "curtains", [bx("d_curt_a", 2.73, 2.95, 0.0, 0.12, 0.01, 2.85, C, 0.02),
                                       bx("d_curt_b", 4.75, 4.97, 0.0, 0.12, 0.01, 2.85, C, 0.02),
                                       bx("d_rod", 2.70, 5.00, 0.05, 0.07, 2.87, 2.89, Hd)], "derived (window from the plan)")
    put("kitchen-dining", "seat-pads", [bx(f"d_pad{i}{s}", cx - 0.20, cx + 0.20, cy - 0.20, cy + 0.20, 0.46, 0.48, T)
                                        for i, cx in enumerate((3.70, 4.30, 4.90)) for s, cy in (("e", 0.95), ("w", 2.45))], "derived (chairs)")
    # work
    put("work", "desk-lamp", [cyl("w_lamp", (-2.10, 8.25), 0.09, 1.10, 1.25, C), cyl("w_lamp_b", (-2.10, 8.25), 0.07, 0.75, 1.10, Hd)], "derived")
    put("work", "shelf-boxes", [bx("w_box_a", -2.05, -1.75, 6.38, 6.66, 1.00, 1.22), bx("w_box_b", -1.70, -1.40, 6.38, 6.66, 0.30, 0.52)], "derived (shelves)")
    put("work", "desk-tray", [bx("w_tray", -2.15, -1.90, 7.30, 7.62, 0.75, 0.78, Hd)], "derived")
    put("work", "magazine-holder", [bx("w_mag", -2.25, -1.95, 8.55, 8.80, 0.0, 0.42, Hd)], "derived")
    put("work", "planter", [cyl("w_pot", (-0.20, 6.62), 0.18, 0.0, 0.40), cyl("w_plant", (-0.20, 6.62), 0.30, 0.40, 1.30, M["crown"])], "derived")
    put("work", "framed-art", [bx("w_art", -1.10, -0.40, 6.35, 6.38, 1.25, 1.85, A)], "derived")
    put("work", "rug", [bx("w_rug", -1.70, -0.10, 7.20, 9.40, 0.0, 0.012, Rg)], "derived")
    put("work", "curtains", [bx("w_curt_a", -2.30, -2.18, 6.93, 7.15, 0.01, 2.85, C, 0.02),
                             bx("w_curt_b", -2.30, -2.18, 8.35, 8.57, 0.01, 2.85, C, 0.02),
                             bx("w_rod", -2.25, -2.23, 6.90, 8.60, 2.87, 2.89, Hd)], "derived (window from the plan)")
    put("work", "basket", [cyl("w_basket", (-0.70, 6.60), 0.17, 0.0, 0.32)], "derived")
    # corridor
    put("corridor", "runner-rug", [bx("c_runner", 2.00, 2.80, 10.10, 17.20, 0.0, 0.012, Rg)], "derived")
    put("corridor", "ceiling-lights", [cyl("c_light_a", (2.40, 11.70), 0.17, 2.58, 2.70), cyl("c_light_b", (2.40, 15.10), 0.17, 2.58, 2.70)], "derived")
    put("corridor", "gallery-art", [bx(f"c_art{i}", 1.70, 1.73, a, b, 1.30, 1.85, A) for i, (a, b) in
                                    enumerate(((13.95, 14.50), (14.72, 15.27), (15.45, 16.00)))], "plan (left wall Y 13.9-16.0)")
    # kids (identical, +3.63)
    for kid, dy in (("boy", 0.0), ("girl", 3.63)):
        y0 = 10.25 + dy
        put(kid, "bedding", [bx(f"{kid}_duvet", -2.05, -0.30, y0 + 0.02, y0 + 0.97, 0.42, 0.50, T, 0.02)], "derived (bed)")
        put(kid, "cushions", [bx(f"{kid}_cush", -2.24, -2.08, y0 + 0.15, y0 + 0.80, 0.42, 0.75, T, 0.03)], "derived (bed)")
        put(kid, "rug", [cyl(f"{kid}_rug", (-0.90, y0 + 1.75), 0.70, 0.0, 0.012, Rg)], "derived")
        put(kid, "curtains", [bx(f"{kid}_curt_a", -2.30, -2.18, y0 + 0.28, y0 + 0.50, 0.01, 2.85, C, 0.02),
                              bx(f"{kid}_curt_b", -2.30, -2.18, y0 + 1.90, y0 + 2.12, 0.01, 2.85, C, 0.02),
                              bx(f"{kid}_rod", -2.25, -2.23, y0 + 0.25, y0 + 2.15, 2.87, 2.89, Hd)], "derived (window from the plan)")
        put(kid, "wall-lamp", [bx(f"{kid}_wlamp", -1.75, -1.60, y0, y0 + 0.12, 1.15, 1.32, Hd)], "derived")
        put(kid, "pendant", [cyl(f"{kid}_pend", (-0.40, y0 + 1.74), 0.22, 2.45, 2.70), cyl(f"{kid}_pcord", (-0.40, y0 + 1.74), 0.004, 2.70, 3.0, Hd)], "derived")
        put(kid, "shape-shelf", [bx(f"{kid}_shelf", -1.20, -0.60, y0, y0 + 0.15, 1.45, 1.85)], "derived")
        put(kid, "framed-prints", [bx(f"{kid}_print{i}", a, a + 0.30, y0, y0 + 0.02, 1.05, 1.40, A) for i, a in enumerate((-0.40, 0.00, 0.40))], "derived")
        put(kid, "toy-basket", [cyl(f"{kid}_tbasket", (-1.95, y0 + 2.55), 0.17, 0.0, 0.32)], "derived")
        put(kid, "soft-toy", [cyl(f"{kid}_toy", (-0.55, y0 + 0.50), 0.09, 0.50, 0.75, T)], "derived")
        put(kid, "desk-lamp", [cyl(f"{kid}_dlamp", (-2.12, y0 + 1.30), 0.08, 0.90, 1.05, C), cyl(f"{kid}_dlamp_b", (-2.12, y0 + 1.30), 0.06, 0.65, 0.90, Hd)], "derived")
        put(kid, "wall-hooks", [bx(f"{kid}_hooks", 0.05, 0.75, y0, y0 + 0.06, 1.10, 1.17, Hd)], "derived")
        if kid == "boy":
            put(kid, "play-structure", [bs.cone("boy_teepee", -1.05, y0 + 2.75, 0.0, 1.60, 0.60, 0.04, T, G, verts=5)], "derived")
        else:
            put(kid, "play-structure", [bs.cone("girl_canopy", -2.00, y0 + 0.475, 0.95, 2.95, 0.55, 0.03, C, G, verts=32)],
                "plan (ceiling hook over the bed head)")
    # master
    put("master", "bedding", [bx("m_duvet", -1.12, 0.62, 18.30, 19.78, 0.50, 0.58, T, 0.02)], "derived (bed)")
    put("master", "pillowcases", [bx(f"m_pillow{i}", a, a + 0.70, 17.75, 18.20, 0.50, 0.66, T, 0.04) for i, a in enumerate((-1.05, -0.15))], "derived (bed)")
    put("master", "throw", [bx("m_throw", -1.16, 0.66, 19.35, 19.75, 0.58, 0.61, T)], "derived (bed)")
    put("master", "cushions", [bx("m_cush", -0.55, 0.05, 18.20, 18.32, 0.58, 0.95, T, 0.03)], "derived (bed)")
    put("master", "bedside-sconces", [bx("m_sconce_a", -1.52, -1.38, 17.66, 17.78, 1.25, 1.43, Hd), bx("m_sconce_b", 0.88, 1.02, 17.66, 17.78, 1.25, 1.43, Hd)],
        "plan (sconce pair on the bed wall)")
    put("master", "framed-art", [bx("m_art", -0.85, 0.35, 17.66, 17.69, 1.40, 2.00, A)], "plan (picture on the bed wall)")
    put("master", "curtains", [bx("m_curt_a", -2.30, -2.18, 17.88, 18.10, 0.01, 2.85, C, 0.02),
                               bx("m_curt_b", -2.30, -2.18, 19.60, 19.82, 0.01, 2.85, C, 0.02),
                               bx("m_rod", -2.25, -2.23, 17.85, 19.85, 2.87, 2.89, Hd)], "derived (window from the plan)")
    put("master", "rug", [bx("m_rug", -1.75, 1.25, 18.70, 20.90, 0.0, 0.012, Rg)], "derived")
    put("master", "nightstand-vase", [cyl("m_vase", (-1.55, 17.90), 0.06, 0.55, 0.80)], "derived")
    put("master", "candle-holders", [cyl("m_cand_a", (0.98, 17.92), 0.035, 0.55, 0.72), cyl("m_cand_b", (1.08, 17.86), 0.035, 0.55, 0.66)], "derived")
    put("master", "planter", [cyl("m_pot", (-1.95, 20.35), 0.18, 0.0, 0.40), cyl("m_plant", (-1.95, 20.35), 0.32, 0.40, 1.40, M["crown"])], "derived")
    put("master", "basket", [cyl("m_basket", (0.95, 20.10), 0.18, 0.0, 0.35)], "derived")
    put("master", "pendant", [cyl("m_pend", (0.40, 19.66), 0.25, 2.45, 2.75), cyl("m_pcord", (0.40, 19.66), 0.004, 2.75, 3.0, Hd)], "derived")
    # bath
    put("bath", "towels", [bx("b_towel", 6.18, 6.23, 10.60, 11.20, 1.00, 1.55, T)], "derived")
    put("bath", "bath-mat", [bx("b_mat", 3.95, 5.05, 10.55, 11.15, 0.0, 0.012, Rg)], "derived")
    put("bath", "dispenser-set", [cyl("b_disp_a", (3.85, 10.10), 0.035, 0.88, 1.08), cyl("b_disp_b", (5.15, 10.10), 0.035, 0.88, 1.08)], "derived")
    put("bath", "vanity-tray", [bx("b_vtray", 4.30, 4.60, 10.00, 10.15, 0.88, 0.90, Hd)], "derived")
    put("bath", "storage-basket", [cyl("b_sbasket", (5.65, 10.25), 0.16, 0.0, 0.32)], "derived")
    put("bath", "towel-ladder", [bx("b_ladder", 6.10, 6.25, 10.45, 10.95, 0.0, 1.65, M["wood"])], "derived")
    put("bath", "wall-sconces", [bx("b_sconce_a", 3.70, 3.82, 9.95, 10.07, 1.75, 1.93, Hd), bx("b_sconce_b", 5.08, 5.20, 9.95, 10.07, 1.75, 1.93, Hd)], "derived")
    put("bath", "robe-hooks", [bx("b_hooks", 5.40, 5.70, 13.53, 13.59, 1.65, 1.72, Hd)], "derived")
    put("bath", "planter", [cyl("b_pot", (5.12, 10.25), 0.08, 0.88, 1.05), cyl("b_plant", (5.12, 10.25), 0.15, 1.05, 1.40, M["crown"])], "derived")
    for i, (k, v) in enumerate(sorted(out.items())):
        v["pidx"] = PROXY_IDX0 + i
        for o in v["objs"]:
            o.pass_index = v["pidx"]
    return out


# ---------------------------------------------------------------------------------------
# scene assembly
# ---------------------------------------------------------------------------------------
def build_scene(cfg, plan, a, opening=True, house=True, proxies=True, res=None, samples=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bs.COLL.clear()
    ba.mats()
    for k, v in EXTRA_PAL.items():
        M[k] = bs.make_mat(k, v, 0.9)
    LivingShell.with_opening = opening
    if house:
        LivingShell(cfg).build()
    else:
        b4.V4Shell(cfg).build()                 # the approved v4.1 living room as committed (with vestibule)
    roots = b4.build_furniture(cfg)
    cam = ba.build_camera(cfg)
    S = dict(roots=roots, cam=cam, house=None, fur={}, prox={}, lslots={}, opens=[])
    if house:
        opens = opening_rects(plan)
        S["opens"] = opens
        S["house"] = build_house_shell(plan, opens)
        build_doors()
        S["fur"] = fixed_furniture()
        if proxies:
            S["lslots"] = ba.build_slots(cfg)
            S["prox"] = house_proxies()
    bs.build_world(a.sky)
    bpy.context.scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.93, 0.95, 0.99, 1.0)
    bs.setup_render(res or a.res, samples or a.samples, a.exposure)
    bpy.context.scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.context.view_layer.update()
    return S


def set_view(cam, loc, yaw, u0=0.52, v0=0.46):
    cam.location = (loc[0], loc[1], loc[2] if len(loc) > 2 else 1.20)
    cam.rotation_euler = (math.radians(90), 0, math.radians(180 - yaw))
    cam.data.shift_x = -(u0 - 0.5)
    cam.data.shift_y = (v0 - 0.5) * 9 / 16
    bpy.context.view_layer.update()


def render_simple(path):
    sc = bpy.context.scene
    sc.use_nodes = False
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------------------
# cameras and measurements
# ---------------------------------------------------------------------------------------
ROOM_CAM = [("living", "M0"), ("hall", "H0"), ("kitchen-dining", "D0"), ("work", "W0"), ("corridor", "C0"),
            ("boy", "K-boy"), ("girl", "K-girl"), ("master", "MB0"), ("bath", "B0")]


def cams_from_plan(plan):
    C = {}
    for c in plan["cameras"]:
        C[c["id"]] = dict(id=c["id"], room=c["room"], loc=list(c["loc"]), yaw=c["yaw_deg_left"],
                          u0=c.get("u0", 0.52), v0=c.get("v0", 0.46), frame=c.get("frame", ""))
    return C


# features per camera: (key, world point(s), expected u from the plan text, kind)
#   kind 'corner': vertical corner line, measured also in pixels from the normal pass (walls n1 | n2)
def camera_features(cid):
    F = {
        "M0": [("back-left corner (-2.30, 0)", (-2.30, 0.0), 0.431, "corner", ((1, 0, 0), (0, 1, 0))),
               ("O-living-dining nearest jamb (2.50, 4.57) [out of frame: u > 1]", (2.50, 4.57), None, "out_right", None),
               ("back-right corner (2.50, 0) [right wall out of frame]", (2.50, 0.0), None, "out_right", None)],
        "H0": [("living double door jamb X 0.95 (hall face Y 6.35)", (0.95, 6.35), 0.395, "point", None),
               ("living double door jamb X 2.15 (hall face Y 6.35)", (2.15, 6.35), 0.636, "point", None),
               ("work door east jamb (0.80, 8.10) [out of frame by >= 0.02]", (0.80, 8.10), None, "out_left", None),
               ("console left end (2.30, 6.70)", (2.30, 6.70), 0.66, "point", None),
               ("console right end (3.10, 6.70)", (3.10, 6.70), 0.91, "point", None)],
        "D0": [("SE corner (7.25, 0)", (7.25, 0.0), 0.75, "corner", ((0, 1, 0), (-1, 0, 0))),
               ("east window jamb X 2.95", (2.95, 0.0), 0.04, "point", None),
               ("east window centre (3.85, 0)", (3.85, 0.0), 0.28, "point", None),
               ("east window jamb X 4.75", (4.75, 0.0), 0.46, "point", None),
               ("table centre (4.30, 1.70)", (4.30, 1.70), 0.62, "point", None)],
        "W0": [("NE corner (-2.30, 6.35)", (-2.30, 6.35), 0.70, "corner", ((1, 0, 0), (0, 1, 0))),
               ("window jamb Y 8.35", (-2.30, 8.35), 0.10, "point", None),
               ("window centre Y 7.75", (-2.30, 7.75), 0.35, "point", None),
               ("window jamb Y 7.15", (-2.30, 7.15), 0.53, "point", None)],
        "C0": [("girl door east jamb (1.70, 16.26) [out of frame ~0.05]", (1.70, 16.26), -0.05, "out_left", None),
               ("girl door east jamb, room face (1.55, 16.26)", (1.55, 16.26), None, "out_left", None)],
        "K-boy": [("NE corner (-2.30, 10.25)", (-2.30, 10.25), 0.60, "corner", ((1, 0, 0), (0, 1, 0))),
                  ("window west jamb (-2.30, 12.15)", (-2.30, 12.15), 0.22, "point", None)],
        "K-girl": [("NE corner (-2.30, 13.88)", (-2.30, 13.88), 0.60, "corner", ((1, 0, 0), (0, 1, 0))),
                   ("window west jamb (-2.30, 15.78)", (-2.30, 15.78), 0.22, "point", None)],
        "MB0": [("NE corner (-2.30, 17.66)", (-2.30, 17.66), 0.34, "corner", ((1, 0, 0), (0, 1, 0))),
                ("corridor door jamb X 1.88, master face (1.88, 17.66) [out by >= 0.02]", (1.88, 17.66), None, "out_right", None),
                ("corridor door jamb X 1.88, corridor face (1.88, 17.51)", (1.88, 17.51), None, "out_right", None)],
        "B0": [("SE corner (6.25, 9.95)", (6.25, 9.95), 0.73, "corner", ((0, 1, 0), (-1, 0, 0))),
               ("fluted window jamb X 3.95", (3.95, 9.95), 0.08, "point", None),
               ("fluted window centre X 4.45", (4.45, 9.95), 0.30, "point", None),
               ("fluted window jamb X 4.95", (4.95, 9.95), 0.52, "point", None)],
    }
    return F.get(cid, [])


EDGES = {   # (wall axis, plane value, frame side, expected coordinate along the wall, label)
    "H0": [("x", 0.80, "left", 7.98, "left edge meets the hall left wall (X 0.80) at Y")],
    "W0": [("x", -2.30, "left", 8.54, "left edge meets the north wall (X -2.30) at Y"),
           ("y", 6.35, "right", -1.25, "right edge meets the east wall (Y 6.35) at X")],
    "K-boy": [("x", -2.30, "left", 12.83, "left edge meets the north wall (X -2.30) at Y")],
    "K-girl": [("x", -2.30, "left", 16.46, "left edge meets the north wall (X -2.30) at Y (12.83 + 3.63)")],
    "M0": [("x", -2.30, "left", 3.738, "left edge meets the left wall at Y (v4-spec)")],
}


def pixel_corner(normal, cam, p, n1, n2, z, idx=None):
    """Corner column from the normal pass at the row where the corner line has height z."""
    H, W = normal.shape[:2]
    u, v, d = P(cam, (p[0], p[1], z))
    if d <= 0 or not (0 <= v < 1):
        return "out of frame"
    ri = min(H - 1, int(v * H))
    row = normal[ri]
    a = row @ np.array(n1, float)
    b = row @ np.array(n2, float)
    if idx is not None:                       # walls only (house walls 100, living walls 5-7)
        wall = np.isin(idx[ri], [IDX["wall"], 5, 6, 7, 10])
        a = np.where(wall, a, 0.0)
        b = np.where(wall, b, 0.0)
    c0 = int(round(u * W))
    best = None
    # the normal pass is sample-averaged: an edge pixel holds f*n1 + (1-f)*n2, so the boundary is sub-pixel
    for lo, hi in ((a, b), (b, a)):
        for c in range(max(1, c0 - 40), min(W - 4, c0 + 40)):
            if lo[c - 1] > 0.98 and lo[c] <= 0.98:
                k = c
                frac = 0.0
                while k < W and hi[k] <= 0.98 and k - c < 3:
                    if lo[k] + hi[k] < 0.9:
                        break
                    frac += lo[k]
                    k += 1
                if k < W and hi[k] > 0.98:
                    pos = c + frac
                    if best is None or abs(pos - u * W) < abs(best - u * W):
                        best = pos
    return None if best is None else best / W


def edge_wall_entry(cam, C, wall, side):
    """Where the frame edge (u=0 left / u=1 right) meets a wall plane at camera height: returns coordinate."""
    yaw = math.radians(C["yaw"])
    f = np.array([-math.sin(yaw), -math.cos(yaw)])
    r = np.array([math.cos(yaw), -math.sin(yaw)])
    uu = 0.0 if side == "left" else 1.0
    dirv = f + r * (uu - C["u0"]) / 0.6667
    axis, val = wall
    cx, cy = C["loc"][0], C["loc"][1]
    k = 0 if axis == "x" else 1
    t = (val - (cx, cy)[k]) / dirv[k]
    q = (cx + t * dirv[0], cy + t * dirv[1])
    return q[1 - k], t


def measure_camera(S, C, normal, idx, W, H):
    cam = S["cam"]
    rows = []
    for key, p, exp, kind, ns in camera_features(C["id"]):
        u_bl = P(cam, (p[0], p[1], 1.20))[0]
        u_pl = plan_u(C, p)
        it = dict(feature=key, expected_u=exp, plan_eq_u=r4(u_pl) if u_pl is not None else None, blender_u=r4(u_bl))
        if kind == "corner":
            zs = (2.60, 2.45, 2.25, 1.95, 1.60, 1.30, 0.90)
            pu = [pixel_corner(normal, cam, p, ns[0], ns[1], z, idx) for z in zs]
            it["pixel_u_by_z"] = {f"{z:.2f}": (r4(x) if isinstance(x, float) else (x or "occluded")) for z, x in zip(zs, pu)}
            pu = [x if isinstance(x, float) else None for x in pu]
            it["pixel_u_measured"] = bool(any(x is not None for x in pu))
            ut, ub = P(cam, (p[0], p[1], 0.0))[0], P(cam, (p[0], p[1], 2.70))[0]
            it["plumb_du_floor_to_2.70"] = r4(abs(ut - ub))
            it["ok"] = bool(exp is not None and abs(u_bl - exp) <= 0.02 and
                            all(x is None or abs(x - u_bl) <= 0.002 for x in pu))
            it["tolerance"] = 0.02
        elif kind == "out_left":
            it["out_of_frame_by"] = r4(-u_bl)
            it["ok"] = bool(u_bl <= -0.02 or (exp is not None and abs(u_bl - exp) <= 0.02))
        elif kind == "out_right":
            it["out_of_frame_by"] = r4(u_bl - 1.0)
            it["ok"] = bool(u_bl >= 1.02)
        else:
            it["ok"] = bool(exp is None or abs(u_bl - exp) <= 0.02)
            it["tolerance"] = 0.02
        if exp is not None:
            it["dev"] = r4(u_bl - exp)
        rows.append(it)
    for axis, val, side, exp, lab in EDGES.get(C["id"], []):
        q, t = edge_wall_entry(cam, C, (axis, val), side)
        pt = (val, q, 1.2) if axis == "x" else (q, val, 1.2)
        rows.append(dict(feature=lab, expected=exp, plan_eq=r4(q), blender_u_at_point=r4(P(cam, pt)[0]),
                         dev_m=r4(q - exp), ok=bool(abs(q - exp) <= 0.03)))
    return rows


def visible_slots(S, idx, room):
    """Visible product-slot proxies (living 16 + house), bbox in frame and edge margins."""
    H, W = idx.shape
    out = []
    items = []
    for n, d in S["lslots"].items():
        items.append((f"living/{n}", d["pidx"], "living v4-spec"))
    for n, d in S["prox"].items():
        items.append((n, d["pidx"], d["src"]))
    for name, pidx, src in items:
        m = idx == pidx
        if name == "living/planter":
            m = m | (idx == ba.CROWN_IDX)
        npx = int(m.sum())
        if npx < 20:
            continue
        ys, xs = np.nonzero(m)
        bb = [xs.min() / W, (xs.max() + 1) / W, ys.min() / H, (ys.max() + 1) / H]
        margin = min(bb[0], 1 - bb[1], bb[2], 1 - bb[3])
        own = name.split("/")[0] == room
        out.append(dict(slot=name, own_room=own, src=src, px=npx, bbox_uv=r4(bb), min_edge_margin=r4(margin),
                        within_0_05_of_edge=bool(margin < 0.05)))
    return out


# ---------------------------------------------------------------------------------------
# transitions
# ---------------------------------------------------------------------------------------
def transition_poses(T, cams, plan):
    """Pose list [(x, y, yaw, seg_label, s_m)] for a transition: dolly samples every 0.5 m (+ end), pans <= 15 deg."""
    from_id = T["from"].split()[-1]
    to_id = T["to"].split()[-1]
    c = cams[from_id]
    x, y, yaw = c["loc"][0], c["loc"][1], c["yaw"]
    poses = [(x, y, yaw, "start " + from_id, 0.0)]
    segs = []
    for si, sg in enumerate(T["segments"]):
        lab = sg.get("id", sg["type"]) + f"#{si + 1}"
        if sg["type"] == "pan":
            a0, a1 = sg["yaw"]
            if abs(a0 - yaw) > 1e-6:
                segs.append(dict(seg=lab, issue=f"pan starts at yaw {a0}, previous yaw {yaw}"))
            n = max(1, math.ceil(abs(a1 - a0) / 15.0 - 1e-9))
            for k in range(1, n + 1):
                poses.append((x, y, a0 + (a1 - a0) * k / n, lab, 0.0))
            yaw = a1
            segs.append(dict(seg=lab, type="pan", at=[r4(x), r4(y)], yaw=[a0, a1]))
            continue
        frm = sg.get("from")
        to = sg.get("to")
        if isinstance(to, str):
            to = cams[to]["loc"][:2]
        if frm is None:
            frm = (x, y)
        if math.dist(frm, (x, y)) > 0.005:
            segs.append(dict(seg=lab, issue=f"segment starts at {frm}, camera is at {(round(x, 3), round(y, 3))}"))
        if abs(sg["yaw"] - yaw) > 1e-6:
            segs.append(dict(seg=lab, issue=f"segment yaw {sg['yaw']} != current yaw {yaw}"))
        L = math.dist(frm, to)
        n = int(math.floor(L / 0.5 + 1e-9))
        ss = [0.5 * k for k in range(1, n + 1)]
        if L - (ss[-1] if ss else 0) > 0.02:
            ss.append(L)
        for s in ss:
            t = s / L
            poses.append((frm[0] + (to[0] - frm[0]) * t, frm[1] + (to[1] - frm[1]) * t, sg["yaw"], lab, s))
        hd = math.degrees(math.atan2(-(to[0] - frm[0]), -(to[1] - frm[1])))
        segs.append(dict(seg=lab, type=sg["type"], from_=r4(list(frm)), to=r4(list(to)), len_m=r4(L),
                         len_plan=sg.get("len_m"), path_dir_deg_left=round(hd, 2), yaw=sg["yaw"],
                         oblique_deg=round(((hd - sg["yaw"] + 180) % 360) - 180, 2), through=sg.get("through")))
        x, y, yaw = to[0], to[1], sg["yaw"]
    ce = cams[to_id]
    end_err = dict(pos_m=r4(math.dist((x, y), ce["loc"][:2])), yaw_deg=r4(yaw - ce["yaw"]))
    # principal point: linear from the start camera u0 to the end camera u0 over the frame index
    n = max(1, len(poses) - 1)
    poses = [p + (c["u0"] + (ce["u0"] - c["u0"]) * k / n,) for k, p in enumerate(poses)]
    return poses, segs, end_err


def obstacles():
    """Plan rectangles of every mesh that occupies the camera band z 0.9-1.5 (walls, jambs, doors, furniture,
    proxies). Axis-aligned world bounding boxes of the evaluated meshes."""
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.name.startswith("plank") or "_plank" in ob.name or "_tile" in ob.name:
            continue
        cname = ob.users_collection[0].name if ob.users_collection else ""
        if cname in ("floor", "ceiling"):
            continue
        ev = ob.evaluated_get(dg)
        mw = ev.matrix_world
        cs = [mw @ Vector(c) for c in ev.bound_box]
        xs, ys, zs = [c.x for c in cs], [c.y for c in cs], [c.z for c in cs]
        if max(zs) < 0.9 or min(zs) > 1.5:
            continue
        out.append((min(xs), max(xs), min(ys), max(ys), ob.name, cname))
    return out


def rect_dist(p, r):
    dx = max(r[0] - p[0], 0, p[0] - r[1])
    dy = max(r[2] - p[1], 0, p[1] - r[3])
    return math.hypot(dx, dy)


def seg_clearance(a, b, obs, step=0.01):
    L = math.dist(a, b)
    n = max(1, int(L / step))
    best = (1e9, None)
    for k in range(n + 1):
        t = k / n
        p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        for r in obs:
            d = rect_dist(p, r)
            if d < best[0]:
                best = (d, r)
    return best


def jamb_clearance(a, b, opens_all):
    """For openings crossed by segment a-b: min distance from the segment to the opening's jamb corners."""
    out = []
    for o in opens_all:
        (x0, x1), (y0, y1) = o["x"], o["y"]
        # crossing test: Liang-Barsky clip of the segment against the (possibly zero-thickness) rectangle
        t0_, t1_ = 0.0, 1.0
        dx, dy = b[0] - a[0], b[1] - a[1]
        hit = True
        for p_, q_ in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
            if abs(p_) < 1e-12:
                if q_ < -1e-9:
                    hit = False
                    break
                continue
            r_ = q_ / p_
            if p_ < 0:
                t0_ = max(t0_, r_)
            else:
                t1_ = min(t1_, r_)
        if not hit or t0_ > t1_ + 1e-12:
            continue
        tm = (t0_ + t1_) / 2
        cross = (a[0] + dx * tm, a[1] + dy * tm)
        corners = [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]
        best = 1e9
        for c in corners:
            # distance from corner to segment
            ax, ay, bx_, by_ = a[0], a[1], b[0], b[1]
            vx, vy = bx_ - ax, by_ - ay
            t = max(0, min(1, ((c[0] - ax) * vx + (c[1] - ay) * vy) / (vx * vx + vy * vy)))
            best = min(best, math.dist(c, (ax + t * vx, ay + t * vy)))
        out.append(dict(opening=o["id"], crossing=r4(list(cross)), min_jamb_clearance_m=r4(best), ok=bool(best >= 0.15)))
    return out


def all_openings_for_hc1(plan):
    out = []
    for o in plan["openings"]:
        if "plane_x" in o:
            out.append(dict(id=o["id"], x=tuple(o["plane_x"]), y=tuple(o["y"])))
        else:
            out.append(dict(id=o["id"], x=tuple(o["x"]), y=tuple(o["plane_y"])))
    return out


# ---------------------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------------------
def label_tile(img, text, fnt):
    from PIL import ImageDraw
    dr = ImageDraw.Draw(img)
    w = dr.textlength(text, font=fnt)
    dr.rectangle((0, 0, w + 10, fnt.size + 8), fill=(255, 255, 255))
    dr.text((5, 3), text, fill=(20, 20, 20), font=fnt)


def make_sheet(tiles, title, out_path, cols=5):
    from PIL import Image, ImageDraw
    tw, th = tiles[0][0].size
    rows = math.ceil(len(tiles) / cols)
    pad, head = 6, 44
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, head + rows * (th + pad) + pad), (245, 244, 241))
    dr = ImageDraw.Draw(sheet)
    dr.text((10, 10), title, fill=(20, 20, 20), font=ba.font(20))
    f = ba.font(13, bold=False)
    for k, (im, lab) in enumerate(tiles):
        im = im.copy()
        label_tile(im, lab, f)
        sheet.paste(im, (pad + (k % cols) * (tw + pad), head + (k // cols) * (th + pad)))
    sheet.save(out_path, quality=88)


def render_plan_png(S, plan, cams, trans_poses, out_path, ppm=110):
    """Orthographic top view from the 3D model: camera inside the volume at z 1.50 looking down, so everything
    above 1.50 is clipped (walls cut at 1.50 read dark, windows and doors as gaps). Ceilings hidden."""
    from PIL import Image, ImageDraw
    sc = bpy.context.scene
    for o in bpy.data.objects:
        if o.users_collection and o.users_collection[0].name == "ceiling" or o.name == "ceiling":
            o.hide_render = True
    x0, x1, y0, y1 = -3.0, 7.95, -0.70, 22.35
    W, H = int(round((x1 - x0) * ppm)), int(round((y1 - y0) * ppm))
    cd = bpy.data.cameras.new("cam_plan")
    cd.type = "ORTHO"
    cd.ortho_scale = max(x1 - x0, y1 - y0)
    cd.sensor_fit = "AUTO"
    cd.clip_start, cd.clip_end = 0.001, 10.0
    pc = bpy.data.objects.new("cam_plan", cd)
    pc.location = ((x0 + x1) / 2, (y0 + y1) / 2, 1.50)
    sc.collection.objects.link(pc)
    keep = (sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples)
    sc.camera = pc
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.cycles.samples = 24
    tmp = out_path + ".tmp.png"
    render_simple(tmp)
    sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples = keep
    for o in bpy.data.objects:
        o.hide_render = False
    img = Image.open(tmp).convert("RGB").transpose(Image.FLIP_TOP_BOTTOM)     # Y down = plan convention
    os.remove(tmp)

    def Q(x, y):
        return ((x - x0) * ppm, (y - y0) * ppm)
    dr = ImageDraw.Draw(img, "RGBA")
    f, fs, fb = ba.font(18), ba.font(14, bold=False), ba.font(22)
    for r in plan["rooms"]:
        cx, cy = (r["x"][0] + r["x"][1]) / 2, (r["y"][0] + r["y"][1]) / 2
        lab = f"{r['id']}  {r['x'][1] - r['x'][0]:.2f} x {r['y'][1] - r['y'][0]:.2f} x {r['h']:.2f}"
        q = Q(cx, cy)
        w = dr.textlength(lab, font=fs)
        dr.rectangle((q[0] - w / 2 - 4, q[1] - 10, q[0] + w / 2 + 4, q[1] + 10), fill=(255, 255, 255, 200))
        dr.text((q[0] - w / 2, q[1] - 9), lab, fill=(30, 30, 30), font=fs)
    cols = [(200, 60, 40), (40, 110, 190), (40, 150, 80), (170, 80, 170), (220, 140, 20), (30, 160, 170),
            (120, 90, 50), (90, 90, 200)]
    for k, (tid, poses) in enumerate(trans_poses.items()):
        col = cols[k % len(cols)]
        pts = [Q(p[0], p[1]) for p in poses]
        if len(pts) > 1:
            dr.line(pts, fill=col + (255,), width=3)
        for q in pts:
            dr.ellipse((q[0] - 3, q[1] - 3, q[0] + 3, q[1] + 3), fill=col + (255,))
        q = pts[len(pts) // 2]
        dr.text((q[0] + 6, q[1] - 18), tid, fill=col, font=fs)
    for room, cid in ROOM_CAM:
        C = cams[cid]
        yaw = math.radians(C["yaw"])
        f2 = np.array([-math.sin(yaw), -math.cos(yaw)])
        r2 = np.array([math.cos(yaw), -math.sin(yaw)])
        o = np.array(C["loc"][:2])
        L = 2.2
        el = o + L * (f2 + r2 * (0 - C["u0"]) / 0.6667) / np.linalg.norm(f2 + r2 * (0 - C["u0"]) / 0.6667)
        er = o + L * (f2 + r2 * (1 - C["u0"]) / 0.6667) / np.linalg.norm(f2 + r2 * (1 - C["u0"]) / 0.6667)
        dr.polygon([Q(*o), Q(*el), Q(*er)], fill=(255, 200, 40, 70), outline=(180, 120, 0, 255))
        q = Q(*o)
        dr.ellipse((q[0] - 6, q[1] - 6, q[0] + 6, q[1] + 6), fill=(20, 20, 20))
        dr.text((q[0] + 8, q[1] + 4), cid, fill=(0, 0, 0), font=f)
    # scale bar, north arrow, title
    q0 = Q(-2.6, 22.15)
    dr.line([q0, (q0[0] + 2 * ppm, q0[1])], fill=(0, 0, 0), width=4)
    dr.text((q0[0], q0[1] - 24), "2 m", fill=(0, 0, 0), font=fs)
    qn = Q(5.5, 21.6)
    dr.line([qn, (qn[0] - 60, qn[1])], fill=(0, 0, 0), width=3)
    dr.polygon([(qn[0] - 70, qn[1]), (qn[0] - 56, qn[1] - 7), (qn[0] - 56, qn[1] + 7)], fill=(0, 0, 0))
    dr.text((qn[0] - 92, qn[1] - 10), "N", fill=(0, 0, 0), font=fb)
    dr.text((10, 8), "House blockout plan: 3D model cut at 1.50 m (ortho). -Y (east) up, -X (north) left.",
            fill=(0, 0, 0), font=f)
    img.save(out_path)
    return dict(px=[W, H], ppm=ppm, extent_x=[x0, x1], extent_y=[y0, y1])


# ---------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------
def render_passes(path, tmp, samples=None):
    return b4.render(path, tmp, samples=samples)


def img_diff(pa, pb):
    from PIL import Image
    A = np.asarray(Image.open(pa).convert("RGB")).astype(np.int16)
    B = np.asarray(Image.open(pb).convert("RGB")).astype(np.int16)
    d = np.abs(A - B).max(axis=2)
    out = dict(identical=bool((d == 0).all()), max_abs_diff_8bit=int(d.max()), mean_abs_diff_8bit=round(float(np.abs(A - B).mean()), 4),
               px_gt_2=round(float((d > 2).mean()), 6), px_gt_5=round(float((d > 5).mean()), 6),
               px_gt_10=round(float((d > 10).mean()), 6))
    LA = (A * [0.2126, 0.7152, 0.0722]).sum(2)
    LB = (B * [0.2126, 0.7152, 0.0722]).sum(2)
    out["mean_luma_a_b"] = [round(float(LA.mean()), 3), round(float(LB.mean()), 3)]
    # right third (side of the opening)
    W = A.shape[1]
    out["mean_luma_right_quarter_a_b"] = [round(float(LA[:, 3 * W // 4:].mean()), 3), round(float(LB[:, 3 * W // 4:].mean()), 3)]
    # systematic part: 64x64 px block means of the luma difference (noise averages out)
    k = 64
    Hh, Ww = LA.shape
    bl = (LB - LA)[:Hh // k * k, :Ww // k * k].reshape(Hh // k, k, Ww // k, k).mean((1, 3))
    out["block64_luma_diff_8bit"] = dict(min=round(float(bl.min()), 2), max=round(float(bl.max()), 2),
                                         mean=round(float(bl.mean()), 2), blocks_brighter_than_0_5=int((bl > 0.5).sum()))
    return out, d


def summarize(rep, plan):
    """HC1-HC7 from the measurements already in rep."""
    out = []
    T = rep.get("transitions", {})
    jam, worst = [], None
    for tid, t in T.items():
        for sg in t["segments"]:
            for j in sg.get("jambs", []):
                jam.append(dict(transition=tid, seg=sg["seg"], **j))
                if worst is None or j["min_jamb_clearance_m"] < worst["min_jamb_clearance_m"]:
                    worst = dict(transition=tid, seg=sg["seg"], **j)
    issues = [dict(transition=tid, **i) for tid, t in T.items() for i in t["segments"] if "issue" in i]
    ends = {tid: t["end_pose_error"] for tid, t in T.items()}
    out.append(dict(id="HC1", check=plan["blockout_checks"][0], result="pass" if jam and all(j["ok"] for j in jam) else "fail",
                    worst=worst, crossings=jam, path_issues=issues, end_pose_errors=ends))
    C = rep.get("cameras", {})
    hc2 = {}
    for cid, c in C.items():
        corners = [f for f in c["features"] if "plumb_du_floor_to_2.70" in f]
        own_edge = [s["slot"] for s in c["slots_in_frame"] if s["own_room"] and s["within_0_05_of_edge"]]
        own_edge_plan = [s["slot"] for s in c["slots_in_frame"] if s["own_room"] and s["within_0_05_of_edge"]
                         and (s["src"].startswith("plan") or s["src"].startswith("living"))]
        hc2[cid] = dict(corner_ok=all(f["ok"] for f in corners) if corners else None,
                        corner=[dict(feature=f["feature"], expected=f["expected_u"], blender=f["blender_u"],
                                     pixels=f.get("pixel_u_by_z")) for f in corners],
                        plumb_max_du=max([f["plumb_du_floor_to_2.70"] for f in corners], default=None),
                        own_slots_within_0_05=own_edge, of_which_plan_or_living_positions=own_edge_plan)
    ok2 = all(v["corner_ok"] in (True, None) for v in hc2.values())
    out.append(dict(id="HC2", check=plan["blockout_checks"][1],
                    result=("pass (corners, plumb)" if ok2 else "fail (corner u)") + "; slot edge margins: see per_camera (derived proxies are report-only)",
                    per_camera=hc2))
    h0 = C.get("H0", {}).get("features", [])
    out.append(dict(id="HC3", check=plan["blockout_checks"][2],
                    result="pass" if h0 and all(f["ok"] for f in h0 if ("work door" in f["feature"] or "right end" in f["feature"] or "left edge" in f["feature"])) else "fail",
                    items=[f for f in h0 if ("work door" in f["feature"] or "console" in f["feature"] or "left edge" in f["feature"])],
                    console_right_margin=next((r4(1 - f["blender_u"]) for f in h0 if "right end" in f["feature"]), None)))
    c0 = C.get("C0", {})
    gj = [f for f in c0.get("features", []) if "girl door" in f["feature"]]
    ls = c0.get("living_slice", {})
    out.append(dict(id="HC4", check=plan["blockout_checks"][3],
                    result="pass" if gj and all(f["blender_u"] < 0 for f in gj) and ls.get("px", 0) > 500 else "fail",
                    girl_jamb=gj, living_slice=ls))
    mb = [f for f in C.get("MB0", {}).get("features", []) if "corridor door" in f["feature"]]
    out.append(dict(id="HC5", check=plan["blockout_checks"][4], result="pass" if mb and all(f["ok"] for f in mb) else "fail", items=mb))
    wins = {cid: c["windows_in_frame"] for cid, c in C.items()}
    bad = [(cid, w) for cid, ws in wins.items() for w in ws if not any(k in w["facade"] for k in ("north", "east"))]
    out.append(dict(id="HC6", check=plan["blockout_checks"][5], result="pass" if not bad else "fail", windows_in_frames=wins,
                    plan_window_facades={w["id"]: w["facade"] for w in plan["windows"]}))
    m0 = rep.get("HC7_m0_pixels", {}).get("comparisons", {})
    op = next((v for k, v in m0.items() if "opening alone" in k), None)
    out.append(dict(id="HC7", check=plan["blockout_checks"][6],
                    result=("pass" if op and op["identical"] else ("report: see comparisons" if op else "not run")),
                    opening_alone=op,
                    geometry=next((f for f in C.get("M0", {}).get("features", []) if "O-living-dining" in f["feature"]), None)))
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if "--framing" in argv:          # proposal options (docs/proposals/house-framing.json): see framing.py
        import framing
        return framing.main(argv)
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=2048)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--sheet-res", type=int, default=480)
    ap.add_argument("--sheet-samples", type=int, default=16)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--only", default="m0cmp,plan,clays,sheets")
    ap.add_argument("--cams", default="")
    ap.add_argument("--trans", default="")
    a = ap.parse_args(argv)
    parts = set(a.only.split(","))
    os.makedirs(a.out, exist_ok=True)
    plan_path, plan = load_plan()
    spec = json.load(open(b4.SPEC_PATH))
    cfg = b4.v4_config(spec)
    cams = cams_from_plan(plan)
    tmp = tempfile.mkdtemp(prefix="house-passes-")
    sc_path = os.path.join(a.out, "selfcheck.json")
    rep = json.load(open(sc_path)) if os.path.exists(sc_path) else {}
    rep.update(plan=os.path.relpath(plan_path, REPO), plan_version=plan["version"],
               living=f"v4-spec.json {spec['version'][:40]}... built by build_v4.py code")
    t0 = time.time()

    # ---- HC7: M0 pixel comparison ------------------------------------------------------
    if "m0cmp" in parts:
        res = {}
        paths = {}
        for tag, kw in (("v41_rebuild", dict(house=False)), ("house_no_opening", dict(opening=False, proxies=False)),
                        ("house_with_opening", dict(opening=True, proxies=False))):
            S = build_scene(cfg, plan, a, **kw)
            set_view(S["cam"], cfg["camera"]["loc"], cfg["camera"]["yaw"], cfg["camera"]["u0"], cfg["camera"]["v0"])
            p = os.path.join(tmp, f"m0_{tag}.png")
            render_passes(p, os.path.join(tmp, "p"))
            paths[tag] = p
            print("rendered", tag, round(time.time() - t0), flush=True)
        committed = os.path.join(LR, "v4.1", "clay.png")
        pairs = {"committed v4.1/clay.png vs v4.1 rebuilt now (reproducibility)": (committed, paths["v41_rebuild"]),
                 "v4.1 rebuilt vs house without O-living-dining (rest of the house)": (paths["v41_rebuild"], paths["house_no_opening"]),
                 "house without vs with O-living-dining (the opening alone)": (paths["house_no_opening"], paths["house_with_opening"]),
                 "committed v4.1/clay.png vs house with the opening (total)": (committed, paths["house_with_opening"])}
        from PIL import Image
        for k, (pa, pb) in pairs.items():
            res[k], d = img_diff(pa, pb)
        _, dtot = img_diff(paths["v41_rebuild"], paths["house_with_opening"])
        Image.fromarray(np.clip(dtot * 10, 0, 255).astype(np.uint8)).save(os.path.join(tmp, "m0_diff_x10.png"))
        shutil.copy(os.path.join(tmp, "m0_diff_x10.png"), os.path.join(a.out, "m0-diff-x10.png"))
        shutil.copy(paths["house_with_opening"], os.path.join(a.out, "living-m0-empty-house.png"))
        rep["HC7_m0_pixels"] = dict(render="2048x1152, 64 samples, seed 7, as v4.1/clay.png (shell + sofa, table, armchair, no proxies)",
                                    comparisons=res, diff_image="m0-diff-x10.png (|v4.1 rebuilt - house with opening| x10)",
                                    empty_m0_in_house="living-m0-empty-house.png")
    # ---- full scene ---------------------------------------------------------------------
    S = build_scene(cfg, plan, a)
    cam = S["cam"]
    rep["model"] = dict(wall_boxes=S["house"]["wall_boxes"], windows={k: dict(v) for k, v in S["house"]["windows"].items()},
                        fixed_furniture={k: dict(room=v["room"], src=v["src"]) for k, v in S["fur"].items()},
                        door_leaves=[dict(name=n, rect=[x0, x1, y0, y1], note=nt) for n, x0, x1, y0, y1, _, nt in LEAVES],
                        proxies={k: v["src"] for k, v in S["prox"].items()})
    obs = obstacles()
    # ---- clays + per camera checks -------------------------------------------------------
    if "clays" in parts:
        cam_rep = rep.get("cameras", {})
        sel = set(a.cams.split(",")) if a.cams else None
        for room, cid in ROOM_CAM:
            if sel and cid not in sel:
                continue
            C = cams[cid]
            set_view(cam, C["loc"], C["yaw"], C["u0"], C["v0"])
            p = os.path.join(a.out, f"{room}-clay.png")
            depth, idx, normal = render_passes(p, os.path.join(tmp, "p"))
            H, W = idx.shape
            feats = measure_camera(S, C, normal, idx, W, H)
            slots = visible_slots(S, idx, room)
            wins = []
            for wid, w in S["house"]["windows"].items():
                n = int((idx == w["pidx"]).sum())
                if n > 50:
                    wins.append(dict(window=wid, facade=w["facade"], px=n))
            if int((idx == ba.SHELL_IDX["window"]).sum()) > 50:
                wins.append(dict(window="W-living", facade="north", px=int((idx == ba.SHELL_IDX["window"]).sum())))
            cl = min((rect_dist(C["loc"][:2], r[:4]), r[4]) for r in obs)
            from PIL import Image
            rgb = np.asarray(Image.open(p).convert("RGB")).astype(float)
            L = (rgb * [0.2126, 0.7152, 0.0722]).sum(2)
            cam_rep[cid] = dict(room=room, image=os.path.basename(p), loc=C["loc"], yaw_deg_left=C["yaw"], u0=C["u0"],
                                v0=C["v0"], frame_text=C["frame"], features=feats, windows_in_frame=wins,
                                slots_in_frame=slots, camera_clearance_m=dict(min=r4(cl[0]), nearest=cl[1]),
                                mean_luma_8bit=round(float(L.mean()), 1),
                                sky_px_fraction=round(float((idx == 0).mean()), 5),
                                principal_point_uv=r4(list(P(cam, (C["loc"][0] - 5 * math.sin(math.radians(C["yaw"])),
                                                                     C["loc"][1] - 5 * math.cos(math.radians(C["yaw"])), 1.20))[:2])))
            if cid == "C0":
                liv = [bs.PASS_INDEX[n] for n in ("sofa", "coffee-table", "armchair")] + \
                      [d["pidx"] for d in S["lslots"].values()] + [ba.CROWN_IDX] + list(range(1, 15))
                lm = np.isin(idx, liv)
                ys, xs = np.nonzero(lm)
                det = {}
                for n in ("floor-lamp", "basket", "sofa"):
                    pid = S["lslots"][n]["pidx"] if n in S["lslots"] else bs.PASS_INDEX[n]
                    det[n] = int((idx == pid).sum())
                cam_rep[cid]["living_slice"] = dict(px=int(lm.sum()), frac=round(float(lm.mean()), 5),
                                                    bbox_uv=r4([xs.min() / W, (xs.max() + 1) / W, ys.min() / H, (ys.max() + 1) / H]) if len(xs) else None,
                                                    px_by_object=det)
            print("clay", cid, round(time.time() - t0), flush=True)
            rep["cameras"] = cam_rep
            json.dump(rep, open(sc_path, "w"), indent=2, ensure_ascii=False)
    # ---- transitions ---------------------------------------------------------------------
    trans_poses, trans_rep = {}, rep.get("transitions", {})
    hc1_open = all_openings_for_hc1(plan)
    for T in plan["transitions"]:
        poses, segs, end_err = transition_poses(T, cams, plan)
        trans_poses[T["id"]] = poses
        moves = []
        for sg in segs:
            if "from_" in sg:
                jc = jamb_clearance(sg["from_"], sg["to"], hc1_open)
                d, r = seg_clearance(sg["from_"], sg["to"], obs)
                walls = [o for o in obs if o[5] in ("shell", "window")]
                dw, rw = seg_clearance(sg["from_"], sg["to"], walls)
                sg.update(jambs=jc, min_clearance_any_m=r4(d), nearest_any=r[4] if r else None,
                          min_clearance_walls_m=r4(dw), nearest_wall=rw[4] if rw else None)
            moves.append(sg)
        frames = []
        for k, (x, y, yaw, lab, s, u0) in enumerate(poses):
            cl = min((rect_dist((x, y), r[:4]), r[4]) for r in obs)
            frames.append(dict(k=k, x=r4(x), y=r4(y), yaw=r4(yaw), u0=r4(u0), seg=lab, s_m=r4(s), clearance_m=r4(cl[0]),
                               nearest=cl[1]))
        trans_rep[T["id"]] = dict(from_=T["from"], to=T["to"], segments=moves, end_pose_error=end_err, frames=frames,
                                  sheet=f"transitions/{T['id']}-sheet.jpg")
    rep["transitions"] = trans_rep
    if "sheets" in parts:
        from PIL import Image
        os.makedirs(os.path.join(a.out, "transitions"), exist_ok=True)
        sc = bpy.context.scene
        keep = (sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples)
        sc.render.resolution_x, sc.render.resolution_y = a.sheet_res, int(round(a.sheet_res * 9 / 16))
        sc.cycles.samples = a.sheet_samples
        sel = set(a.trans.split(",")) if a.trans else None
        for T in plan["transitions"]:
            if sel and T["id"] not in sel:
                continue
            tiles = []
            for fr in trans_rep[T["id"]]["frames"]:
                set_view(cam, (fr["x"], fr["y"], 1.20), fr["yaw"], fr["u0"])
                fp = os.path.join(tmp, f"fr_{fr['k']:03d}.png")
                render_simple(fp)
                lab = f"{fr['k']:02d} {fr['seg']} s={fr['s_m']:.2f} ({fr['x']:.2f},{fr['y']:.2f}) yaw {fr['yaw']:.0f}  clr {fr['clearance_m']:.2f}"
                tiles.append((Image.open(fp).convert("RGB"), lab))
            make_sheet(tiles, f"{T['id']}: {T['from']} -> {T['to']}  ({len(tiles)} frames; dolly every 0.5 m, pans <= 15 deg; clr = 2D clearance to nearest solid in the camera band z 0.9-1.5)",
                       os.path.join(a.out, "transitions", f"{T['id']}-sheet.jpg"))
            print("sheet", T["id"], len(tiles), round(time.time() - t0), flush=True)
        sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples = keep
    if "plan" in parts:
        rep["plan_png"] = render_plan_png(S, plan, cams, trans_poses, os.path.join(a.out, "plan.png"))
    rep["checks"] = summarize(rep, plan)
    rep["runtime_s"] = round(time.time() - t0)
    json.dump(rep, open(sc_path, "w"), indent=2, ensure_ascii=False)
    shutil.rmtree(tmp, ignore_errors=True)
    print("done", round(time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
