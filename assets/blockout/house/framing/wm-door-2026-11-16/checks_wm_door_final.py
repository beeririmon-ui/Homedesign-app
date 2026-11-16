#!/usr/bin/env python3
"""
checks_wm_door_final.py: the measurements on the FINAL entrance clay (framing_wm_door_final.py), render-agent, 2026-11-16. 0 tokens.
Reads the passes of this folder and of ../wm-door-2026-11-14/ (the gate: the geometry did not move), and the scene-linear beauty EXRs in
the scratchpad (read with bpy, so run it with the python that has bpy). Writes selfcheck.json and contact-sheet.jpg.

  python3 checks_wm_door_final.py            # everything that is rendered
  python3 checks_wm_door_final.py --d0       # the gate and the D0 table only (printed)
"""
import argparse
import importlib.util
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(HERE, "..", "wm-door-2026-11-14")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SCRATCH = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-door-final"
CONCEPTS = os.path.join(REPO, "assets", "renders", "hall", "warm-modern", "concepts-middle-2026-11-15")
BASE_BACK_WALL = 0.751          # base.png back wall, display-decoded linear median (wm-door-2026-11-14 README)

_spec = importlib.util.spec_from_file_location("checks_old", os.path.join(OLD, "checks_wm_door.py"))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
Passes, uv, r4, K_U, K_V = C.Passes, C.uv, C.r4, C.K_U, C.K_V

COURSE_TOPS = [0.40, 0.70, 0.85, 1.25, 1.45, 1.60, 2.00, 2.15, 2.40]
DESIGNER_JOINT_V = [0.755, 0.652, 0.600, 0.463, 0.394, 0.343, 0.205, 0.154, 0.068]
STONE, REVEAL_ST, JOINT, PLANTER, BENCH, CAP, HERBS, LAMP, SOIL, MAT, PANEL, SLOT, OLIVE, RECESS = 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97
LEAF = (70, 71)
D0F = C.D0


def frames():
    F, L = C.frames()
    return F, L


# ---------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------
def lin_display(png):
    rgb = np.asarray(Image.open(png).convert("RGB")).astype(np.float64) / 255
    l = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return l @ np.array([0.2126, 0.7152, 0.0722]), rgb


def scene_Y(fid):
    p = os.path.join(SCRATCH, "beauty", fid.replace("/", "_") + ".exr")
    if not os.path.exists(p):
        return None
    try:
        import bpy
    except ImportError:
        return None
    img = bpy.data.images.load(p)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[::-1][..., :3] @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def lstar(Y):
    f = np.where(Y > 216 / 24389, np.cbrt(Y), (24389 / 27 * Y + 16) / 116)
    return 116 * f - 16


def grid(P):
    u = (np.arange(P.W) + 0.5 - P.ox) / P.fx
    v = (np.arange(P.H) + 0.5 - P.oy) / P.fy
    return np.meshgrid(u, v)


def boxm(U, V, u0, u1, v0, v1):
    return (U >= u0) & (U < u1) & (V >= v0) & (V < v1)


def runs(col_ids, target):
    """Centre rows of runs of `target` along a 1-D id array."""
    out, start = [], None
    for i, c in enumerate(col_ids):
        if c == target and start is None:
            start = i
        elif c != target and start is not None:
            out.append((start + i - 1) / 2.0)
            start = None
    if start is not None:
        out.append((start + len(col_ids) - 1) / 2.0)
    return out


def row(rows, key, designer, clay, unit, method, tol=0.01, note="", gate=False):
    diff = None
    if isinstance(designer, (int, float)) and isinstance(clay, (int, float)):
        diff = clay - designer
    rows.append(dict(key=key, designer=designer, clay=r4(clay) if isinstance(clay, float) else clay, diff=r4(diff), unit=unit, method=method,
                     tol=tol, over=bool(diff is not None and abs(diff) > tol), note=note, gate=gate))


# ---------------------------------------------------------------------------------------------------------------
# 1. the gate: the 2026-11-14 lines, on the old and the new clay
# ---------------------------------------------------------------------------------------------------------------
def gate_lines(P, door_wall_ids, reveal_ids):
    """The named lines of the D0 lock (lock_d0.py), in canvas pixels, from an id pass."""
    c = P.cls
    rv = int(round(1050 * P.H / 1530))

    def vstep(r_, a, b, lo=0):
        rr = c[r_]
        for x in range(lo, P.W - 1):
            if rr[x] in a and rr[x + 1] in b:
                return x + 1
        return None

    def hstep(col, a, b, lo=0):
        cc = c[:, col]
        for y in range(lo, P.H - 1):
            if cc[y] in a and cc[y + 1] in b:
                return y + 1
        return None
    W_, R_ = door_wall_ids, reveal_ids
    lc = vstep(rv, (62, RECESS), W_)
    ol = vstep(rv, W_, R_)
    ll = vstep(rv, R_, LEAF, lo=ol)
    lr = vstep(rv, LEAF + (72,), R_, lo=ll + 10)
    orr = vstep(rv, R_, W_, lo=lr)
    rc = vstep(int(round(P.oy + 0.30 * P.fy)), W_, (63, RECESS), lo=orr)       # above the herbs (the planter and the herbs stand in front of the corner below v 0.50)
    cx = (ol + orr) // 2
    oh = hstep(cx, W_, R_ + (99,))
    lt = hstep(cx, R_ + (99,), LEAF, lo=oh)
    lb = hstep(cx, LEAF, (10, 60, 64, 85, JOINT), lo=lt + 10)
    fl = hstep(int(round(1500 * P.W / 2720)), W_ + (66,), (60,), lo=int(1000 * P.H / 1530))
    fl2 = hstep(int(round(400 * P.W / 2720)), W_ + (66,), (60,), lo=int(1000 * P.H / 1530))
    return {"left corner (X 3.95 / Y 9.60)": lc, "outer opening, left (Y 8.80)": ol, "leaf, left": ll, "leaf, right": lr,
            "outer opening, right (Y 7.80)": orr, "right corner (X 3.95 / Y 6.55)": rc, "outer opening, head (Z 2.40)": oh, "leaf, top": lt,
            "leaf, bottom": lb, "floor line, door wall left of the door": fl2, "floor line, door wall right of the door": fl}


def gate(F):
    new = Passes("D0-closed", F["D0-closed"], folder=HERE)
    old = Passes("D0-closed", F["D0-closed"], folder=OLD)
    a = gate_lines(old, (61,), (64,))
    b = gate_lines(new, (STONE, JOINT), (REVEAL_ST, 64))
    lines = {k: dict(old_px=a[k], new_px=b[k], diff_px=(None if a[k] is None or b[k] is None else b[k] - a[k])) for k in a}
    le = new.extent(LEAF)
    rect = dict(designer=[0.2441, 0.4224, 0.0997, 0.8603], clay=[r4(x) for x in le],
                diff_px=[r4((x - y) * (new.fx if i < 2 else new.fy)) for i, (x, y) in enumerate(zip(le, (0.2441, 0.4224, 0.0997, 0.8603)))])
    dep = {}
    for fid in ("D0-closed", "D0-none", "D0-open", "HD", "HDx", "HT"):
        po, pn = os.path.join(OLD, fid + "-depth.png"), os.path.join(HERE, fid + "-depth.png")
        if os.path.exists(po) and os.path.exists(pn):
            do = np.asarray(Image.open(po)).astype(np.int32)
            dn = np.asarray(Image.open(pn)).astype(np.int32)
            co = np.asarray(Image.open(os.path.join(OLD, fid + "-id.png")))
            same = np.isin(co, (11, 12, 13, 17, 30, 31, 32, 33, 34, 35, 39, 41, 42, 43, 60, 62, 63, 75, 76))     # surfaces ch. 11 does not touch
            cn = np.asarray(Image.open(os.path.join(HERE, fid + "-id.png")))
            un = same & ~np.isin(cn, (STONE, REVEAL_ST, JOINT, PLANTER, BENCH, CAP, HERBS, LAMP, SOIL, MAT, PANEL, SLOT, RECESS))
            dd = np.abs(dn - do)[un] / 5000.0
            dep[fid] = dict(px_compared=int(un.sum()), depth_equal_within_1mm=r4(float((dd <= 0.001).mean())), max_mm=r4(float(dd.max()) * 1000) if dd.size else None)
    worst = max(abs(v["diff_px"]) for v in lines.values() if v["diff_px"] is not None)
    return dict(lines_old_vs_new_px=lines, worst_px=worst, leaf_rectangle=rect,
                untouched_surfaces_depth_old_vs_new=dep,
                passed=bool(worst <= 2 and all(abs(x) <= 2 for x in rect["diff_px"]) and all(v["diff_px"] is not None for v in lines.values())),
                rule="brief step 1: the geometry does not move; the stone face stays on X 3.95; the leaf's rectangle (u 0.2441-0.4224, v 0.0997-0.8603) "
                     "within 2 px. The named lines of the D0 lock found in the old (2026-11-14) and the new id pass, in canvas px at 2720 x 1530")


# ---------------------------------------------------------------------------------------------------------------
# 2. D0: the designer's ch. 11 numbers against the clay
# ---------------------------------------------------------------------------------------------------------------
def d0_table(F):
    P = Passes("D0-closed", F["D0-closed"], folder=HERE)
    f = P.f
    X, Y, Z = P.world()
    U, V = grid(P)
    fb = boxm(U, V, 0, 1, 0, 1)
    c = P.cls
    rows = []
    # 11.1.1: what is in the frame
    e = P.extent((STONE, REVEAL_ST, JOINT))
    row(rows, "door wall limestone incl. reveal: u left", 0.080, e[0], "u", "id pass extent (84, 85, 86) in the frame")
    row(rows, "door wall limestone: u right", 0.669, e[1], "u", "id pass")
    row(rows, "door wall limestone: v bottom (floor line)", 0.892, e[3], "v", "id pass")
    row(rows, "door wall limestone: v top", 0.0, e[2], "v", "id pass", tol=0.002)
    le = P.extent(LEAF)
    for k, d, x in zip(("leaf u left", "leaf u right", "leaf v top", "leaf v bottom"), (0.244, 0.422, 0.100, 0.860), le):
        row(rows, k, d, x, "u" if "u " in k else "v", "id pass extent (70, 71)", tol=0.002)
    lm = P.extent((LAMP,))
    row(rows, "wall light body: u left", 0.498, lm[0], "u", "id pass extent (91: body, plate, arm, diffusers)")
    row(rows, "wall light body: u right", 0.518, lm[1], "u", "id pass")
    row(rows, "wall light body: v top", 0.226, lm[2], "v", "id pass")
    row(rows, "wall light body: v bottom", 0.313, lm[3], "v", "id pass")
    cu, cv_, _ = uv(f, (4.02, 7.40, 1.80))
    row(rows, "wall light centre u (projection of the built centre)", 0.508, cu, "u", "plan projection of (4.02, 7.40, 1.80)")
    row(rows, "wall light centre v", 0.270, cv_, "v", "plan projection")
    lamp_px = int(((c == LAMP) & fb).sum())
    row(rows, "wall light: share of the frame (V7Q6 counts at 0.15 % with 6 % height)", 0.0017, lamp_px / fb.sum(), "share", "id pass", tol=0.0006)
    row(rows, "wall light: height share of the frame", 0.087, lm[3] - lm[2], "share", "id pass", tol=0.01)
    pl = ((c == PLANTER) | (c == SOIL) | ((c == CAP) & (X < 4.755))) & fb
    ys, xs = np.nonzero(pl)
    row(rows, "planter: u left", 0.573, P.u(xs.min()), "u", "id pass (87, 92, and 89 at X < 4.755)")
    row(rows, "planter: u right", 0.763, P.u(xs.max() + 1), "u", "id pass")
    for nm, p, d in (("planter rim, top back corner (3.95, 7.05, 0.70): v", (3.95, 7.05, 0.70), 0.652),
                     ("planter rim, top front corner (4.75, 7.05, 0.70): v", (4.75, 7.05, 0.70), 0.704)):
        row(rows, nm, d, uv(f, p)[1], "v", "plan projection of the built corner (the herbs hide the rim's top edge in the id pass)")
    he = P.extent((HERBS,))
    row(rows, "herbs: u left", 0.55, he[0], "u", "id pass (90)", tol=0.02, note="designer: 'about'")
    row(rows, "herbs: u right", 0.78, he[1], "u", "id pass", tol=0.02, note="designer: 'about'")
    row(rows, "herbs: v top", 0.50, he[2], "v", "id pass", tol=0.02, note="designer: 'up to about'")
    seat = (c == CAP) & (X > 4.752) & (Z > 0.445) & fb          # the seat's top face (its 8 cm front face lies left of it)
    ys0 = np.nonzero(seat.any(1))[0].min()
    xs = np.nonzero(seat[ys0 + 2])[0]
    row(rows, "bench seat, far edge at the planter: v", 0.815, P.v(ys0), "v", "id pass: first row of the seat's top face")
    if len(xs):
        row(rows, "bench seat, far edge: u left (Y 7.05)", 0.637, P.u(xs.min()), "u", "id pass, 2 rows under the far edge")
        row(rows, "bench seat, far edge: u right (Y 6.55)", 0.763, P.u(xs.max() + 1), "u", "id pass")
    rb = P.row(1.0) - 1
    xs = np.nonzero(seat[rb])[0]
    if len(xs):
        row(rows, "bench seat (top face) at the bottom edge: u left", 0.789, P.u(xs.min()), "u", "id pass, bottom row of the frame; the slab's front face reaches further left")
        row(rows, "bench seat at the bottom edge: u right", 0.984, P.u(xs.max() + 1), "u", "id pass")
    sx = X[seat]
    row(rows, "bench seat seen: X near", 4.75, float(np.nanmin(sx)), "m", "depth pass on the seat pixels")
    row(rows, "bench seat seen: X far (designer 5.69)", 5.69, float(np.nanmax(sx)), "m", "depth pass on the seat pixels", tol=0.02)
    me = P.extent((MAT,))
    for k, d, x in zip(("doormat u left", "doormat u right", "doormat v top", "doormat v bottom"), (0.220, 0.430, 0.892, 0.979), me):
        row(rows, k, d, x, "u" if "u " in k else "v", "id pass (93)")
    rw = P.extent((63,))
    row(rows, "right wall: u left (the corner, above the herbs)", 0.669, rw[0], "u", "id pass (63)")
    row(rows, "olive in the frame (px)", 0, int(((c == OLIVE) & fb).sum()), "px", "id pass", tol=0)
    row(rows, "olive in the canvas (px)", 0, int((c == OLIVE).sum()), "px", "id pass", tol=0)
    sx_, sy_, sz_ = 5.094, 6.55, 1.117
    su, sv_, _ = uv(f, (sx_, sy_, sz_))
    row(rows, "olive shadow: the crown axis on the right wall, u", 0.82, su, "u", "sun ray through the crown centre (8.20, 10.00, 2.90) -> (5.09, 6.55, 1.12)")
    row(rows, "olive shadow: the crown axis on the right wall, v", 0.52, sv_, "v", "same")
    bw = P.extent((75, 76))
    row(rows, "bath window: u left", 0.053, bw[0], "u", "id pass")
    row(rows, "bath window: u right", 0.080, bw[1], "u", "id pass")
    row(rows, "bath window: v top", 0.12, bw[2], "v", "id pass")
    row(rows, "bath window: v bottom", 0.56, bw[3], "v", "id pass")
    ys = np.nonzero(c[:, P.col(0.55)] == 60)[0]
    row(rows, "floor: v top (court floor at the door wall, column u 0.55)", 0.892, P.v(ys.min()) if len(ys) else None, "v", "id pass (60); the reveal floor runs on to the leaf (v 0.860)")
    # 11.1.2: the joints of the door wall
    jl = []
    for ucol, side in ((0.157, "left of the door (Y 9.2)"), (0.466, "right of the door (Y 7.6)")):
        col = P.col(ucol)
        found = [P.v(r_ + 0.5) for r_ in runs(c[:, col], JOINT)]
        for zt, dv in zip(COURSE_TOPS, DESIGNER_JOINT_V):
            if zt == 2.40 and ucol > 0.3 and False:
                continue
            near = min(found, key=lambda q: abs(q - dv)) if found else None
            if zt == 2.40:
                note = "Z 2.40 = the head of the opening; beside the door a joint"
            else:
                note = ""
            row(jl, f"joint Z {zt:.2f}, {side}: v", dv, near, "v", f"id pass, runs of 86 in the column u {ucol}", tol=3 / P.fy, note=note)
    rows += jl
    for k in (2, 4, 6, 8):
        z0, z1 = [(0.40, 0.70), (0.85, 1.25), (1.45, 1.60), (2.00, 2.15)][(k // 2) - 1]
        r_ = P.row(uv(f, (3.95, 7.0, (z0 + z1) / 2))[1])
        xs = runs(c[r_, P.col(0.50):P.col(0.66)], JOINT)
        hj = [P.u(P.col(0.50) + x + 0.5) for x in xs]
        row(rows, f"head joint Y 7.05 in course {k}: u", 0.573, (min(hj, key=lambda q: abs(q - 0.573)) if hj else None), "u",
            "id pass, runs of 86 along a row in the course", tol=3 / P.fx)
    # shares
    sh = {k: float(np.isin(c[fb.astype(bool)], v).mean()) for k, v in (("stone", (STONE, REVEAL_ST, JOINT, 60, CAP)), ("plaster", (61, 62, 63, 64, 66, PLANTER, BENCH, RECESS)),
                                                                          ("walnut", LEAF), ("green", (HERBS, SOIL)), ("coir", (MAT,)), ("bronze", (72, 75, LAMP)),
                                                                          ("fluted glass", (76,)))}
    for k, d in (("stone", 0.42), ("plaster", 0.35), ("walnut", 0.135), ("green", 0.04), ("coir", 0.02), ("bronze", 0.006)):
        row(rows, f"share of the frame: {k}", d, sh[k], "share", "id pass", tol=0.03, note="designer: 'approximately'")
    phone = dict(leaf_px_at_391x220=[round((le[1] - le[0]) * 391), round((le[3] - le[2]) * 220)], designer_leaf="70 x 167",
                 lamp_px=[round((lm[1] - lm[0]) * 391, 1), round((lm[3] - lm[2]) * 220, 1)], designer_lamp="8 x 19",
                 herbs_px=[round((he[1] - he[0]) * 391), round((1.0 - he[2]) * 220)], designer_herbs="a patch of about 75")
    return rows, phone


# ---------------------------------------------------------------------------------------------------------------
# 3. the sun on D0 (the -sun.png pass) against 11.1.8
# ---------------------------------------------------------------------------------------------------------------
def sun_d0(F):
    P = Passes("D0-closed", F["D0-closed"], folder=HERE)
    sp = os.path.join(HERE, "D0-closed-sun.png")
    if not os.path.exists(sp):
        return None
    s = np.asarray(Image.open(sp)).astype(np.float32)
    sun = s > 64
    c = P.cls
    U, V = grid(P)
    fb = boxm(U, V, 0, 1, 0, 1)
    X, Y, Z = P.world()
    out = {}
    line = {}
    for u0 in (0.68, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99):
        col = P.col(u0)
        rw = (c[:, col] == 63) & sun[:, col]
        ys = np.nonzero(rw)[0]
        line[f"u {u0}"] = r4(P.v(ys.min())) if len(ys) else None
    out["sun line on the right wall (top-most sunlit v per column; the olive's lace can lower it locally)"] = line
    out["designer: below a diagonal from about (0.67, 0.40) at the corner up to the top edge near the right edge"] = True
    m = (c == STONE) & sun & fb
    out["sun on the door-wall stone: px"] = int(m.sum())
    if m.any():
        out["sun on the door-wall stone: Y from the corner (m)"] = [r4(float(np.nanmin(Y[m]))), r4(float(np.nanmax(Y[m])))]
        out["designer: allowed a strip of about 10 cm at the right corner, behind the herbs"] = True
    for nm, ids in (("leaf", LEAF + (72,)), ("reveal (jambs, head)", (REVEAL_ST, 64)), ("doormat", (MAT,)), ("door-wall stone left of the planter (Y > 7.07)", None)):
        mm = (np.isin(c, ids) if ids else ((c == STONE) & (Y > 7.07))) & sun & fb
        out[f"sun on the {nm}: px (designer: none)"] = int(mm.sum())
    for nm, mm in (("bench seat", (c == CAP) & (X > 4.745)), ("herbs", c == HERBS), ("front face of the built body (planter + bench plaster)", np.isin(c, (PLANTER, BENCH))),
                   ("right wall", c == 63), ("floor", c == 60)):
        t = (mm & fb).sum()
        out[f"sunlit share of the {nm}"] = r4(float((mm & fb & sun).sum() / t)) if t else None
    return out


# ---------------------------------------------------------------------------------------------------------------
# 4. light: 11.1.8 and 11.5.2 (display-decoded linear, as QA and the 2026-11-14 clay; and scene-linear from the EXR)
# ---------------------------------------------------------------------------------------------------------------
def light(F):
    out = {}
    P = Passes("D0-closed", F["D0-closed"], folder=HERE)
    Yd, rgb = lin_display(P.png)
    Ys = scene_Y("D0-closed")
    c = P.cls
    U, V = grid(P)
    fb = boxm(U, V, 0, 1, 0, 1)
    s = np.asarray(Image.open(os.path.join(HERE, "D0-closed-sun.png"))).astype(np.float32)
    rw = c == 63
    ref = float(np.percentile(s[rw & (s > 64)], 95))
    shade = rw & boxm(U, V, 0.68, 0.74, 0.10, 0.30) & (s <= 64)
    lit = rw & (s >= 0.85 * ref) & (U > 0.70) & fb
    st = c == STONE
    beside = st & (boxm(U, V, 0.56, 0.60, 0.05, 0.48) | boxm(U, V, 0.43, 0.45, 0.05, 0.48))
    up = st & boxm(U, V, 0.488, 0.528, 0.05, 0.215)
    dn = st & boxm(U, V, 0.488, 0.528, 0.325, 0.48)
    leaf = c == 70

    def ratios(Yv, tag):
        r = {}
        sh, li = float(np.median(Yv[shade])), float(np.median(Yv[lit]))
        r["shaded plaster (right wall u 0.68-0.74, v 0.10-0.30)"] = r4(sh)
        r["sunlit plaster (right wall, direct sun >= 85 %, u > 0.70)"] = r4(li)
        r["sun over shade, stops (designer 1.3-2.0)"] = round(math.log2(li / sh), 2)
        b = float(np.median(Yv[beside]))
        r["wall-light fan up: p98 over the stone beside, stops (designer 1.0-1.5)"] = round(math.log2(float(np.percentile(Yv[up], 98)) / b), 2)
        r["wall-light fan down: p98 over the stone beside, stops"] = round(math.log2(float(np.percentile(Yv[dn], 98)) / b), 2)
        r["door-wall stone over the shaded plaster, stops (designer: about -0.4 in albedo, not graded)"] = round(math.log2(float(np.median(Yv[st & fb])) / sh), 2)
        r["leaf under the shaded plaster, stops"] = round(math.log2(sh / float(np.median(Yv[leaf]))), 2)
        if tag == "display":
            r["shaded plaster vs base.png back wall, stops (designer +-1/3)"] = round(math.log2(sh / BASE_BACK_WALL), 2)
            r["sunlit plaster: any channel at 255 (share; designer: none burnt)"] = r4(float((rgb[lit].max(1) >= 0.999).mean()))
            r["sunlit plaster: highest channel (0-255)"] = int(round(float(rgb[lit].max()) * 255))
            r["leaf L* median (still: 28-35)"] = round(float(np.median(lstar(Yd[leaf]))), 1)
            r["frame L* p0.5 (black point; still: 11-14)"] = round(float(np.percentile(lstar(Yd[fb]), 0.5)), 1)
        return r
    out["D0-closed"] = dict(display=ratios(Yd, "display"), scene=(ratios(Ys, "scene") if Ys is not None else None),
                            regions=dict(shaded_px=int(shade.sum()), sunlit_px=int(lit.sum()), fan_up_px=int(up.sum()), fan_down_px=int(dn.sum()), beside_px=int(beside.sum())))
    # D0o: the hall through the door, on the jib door u 0.28-0.36, v 0.40-0.55 (D0-none), against the court's shaded plaster
    for fid in ("D0-none", "D0-open"):
        Pn = Passes(fid, F[fid], folder=HERE)
        Yn, _ = lin_display(Pn.png)
        Ysn = scene_Y(fid)
        cn = Pn.cls
        Un, Vn = grid(Pn)
        jb = (cn == 82) & boxm(Un, Vn, 0.28, 0.36, 0.40, 0.55)
        sh_n = (cn == 63) & boxm(Un, Vn, 0.68, 0.74, 0.10, 0.30) & (s <= 64)
        rec = dict(display=round(math.log2(float(np.median(Yn[sh_n])) / float(np.median(Yn[jb]))), 2))
        if Ysn is not None:
            rec["scene"] = round(math.log2(float(np.median(Ysn[sh_n])) / float(np.median(Ysn[jb]))), 2)
        rec["designer"] = "0.52 +-1/6 (the 2026-11-14 clay's display-decoded value)"
        out[f"{fid}: court shaded plaster over the hall (jib door), stops"] = rec
    # HDx: living over hall
    Px = Passes("HDx", F["HDx"], folder=HERE)
    Yx, _ = lin_display(Px.png)
    Ysx = scene_Y("HDx")
    cx = Px.cls
    Ux, Vx = grid(Px)
    fbx = boxm(Ux, Vx, 0, 1, 0, 1)
    hall_all = np.isin(cx, (10, 11, 12, 13, 14, 15, 17, PANEL, JOINT, 20, 21, 22, 23, 24)) & fbx
    hall_w = np.isin(cx, (11, 12, 13, PANEL, JOINT)) & fbx
    liv_all = np.isin(cx, tuple(range(30, 44))) & fbx
    liv_w = np.isin(cx, (31, 32, 33, 34)) & fbx
    po = Passes("HDx", F["HDx"], folder=OLD)
    Yo, _ = lin_display(po.png)
    co = po.cls
    old_h = np.isin(co, (10, 11, 12, 13, 14, 15, 17, 20, 21, 22, 23, 24)) & fbx
    old_hw = np.isin(co, (11, 12, 13)) & fbx
    old_l = np.isin(co, tuple(range(30, 44))) & fbx
    old_lw = np.isin(co, (31, 32, 33, 34)) & fbx
    rec = dict(designer="2/3 +-1/6, as today",
               display_all_surfaces=round(math.log2(float(np.median(Yx[liv_all])) / float(np.median(Yx[hall_all]))), 2),
               display_walls=round(math.log2(float(np.median(Yx[liv_w])) / float(np.median(Yx[hall_w]))), 2),
               today_display_all_surfaces=round(math.log2(float(np.median(Yo[old_l])) / float(np.median(Yo[old_h]))), 2),
               today_display_walls=round(math.log2(float(np.median(Yo[old_lw])) / float(np.median(Yo[old_hw]))), 2))
    if Ysx is not None:
        rec["scene_all_surfaces"] = round(math.log2(float(np.median(Ysx[liv_all])) / float(np.median(Ysx[hall_all]))), 2)
    out["HDx: living over hall, stops"] = rec
    # HT vs HD: the far wall
    far = {}
    for fid in ("HT", "HD"):
        Pq = Passes(fid, F[fid], folder=HERE)
        Yq, _ = lin_display(Pq.png)
        Uq, Vq = grid(Pq)
        fq = boxm(Uq, Vq, 0, 1, 0, 1)
        far[fid] = {k: float(np.median(Yq[(Pq.cls == i) & fq])) for k, i in (("plaster", 11), ("jib", 82), ("stone", PANEL))}
    out["HT vs HD: far wall, stops (designer: within 1/6)"] = {k: round(math.log2(far["HT"][k] / far["HD"][k]), 2) for k in far["HT"]}
    return out


# ---------------------------------------------------------------------------------------------------------------
# 5. inside: 11.5.2
# ---------------------------------------------------------------------------------------------------------------
def inside(F):
    rows = []
    # D0o = the clay D0-none
    P = Passes("D0-none", F["D0-none"], folder=HERE)
    c = P.cls
    cx = P.col(0.33)
    col = c[:, cx]
    ys = np.nonzero(col == 15)[0]
    if len(ys):
        row(rows, "D0o: hall ceiling v top (at the head of the opening)", 0.106, P.v(ys.min()), "v", "id pass column u 0.33 (15)", note="the head of the opening hides the ceiling above")
        row(rows, "D0o: hall ceiling v bottom", 0.141, P.v(ys.max() + 1), "v", "id pass")
    ys = np.nonzero(col == SLOT)[0]
    row(rows, "D0o: slot (well + opal) v top", 0.141, P.v(ys.min()) if len(ys) else None, "v", "id pass column u 0.33 (95)")
    row(rows, "D0o: slot v bottom", 0.157, P.v(ys.max() + 1) if len(ys) else None, "v", "id pass")
    rr = c[P.row(0.45)]
    for nm, d, a, b in (("jib seam (Y 9.00)", 0.274, (11,), (82, 83)), ("jib seam (Y 8.10)", 0.365, (82, 83), (11,))):
        xs = [x + 1 for x in range(P.col(0.25), P.col(0.40)) if rr[x] in a and rr[x + 1] in b]
        row(rows, f"D0o: {nm} u", d, P.u(xs[0]) if xs else None, "u", "id pass row v 0.45")
    xs = np.nonzero(np.isin(rr, (PANEL, JOINT)))[0]
    xs = xs[(xs > P.col(0.38)) & (xs < P.col(0.43))]
    row(rows, "D0o: stone panel seen inside the right jamb, u left", 0.400, P.u(xs.min()) if len(xs) else None, "u", "id pass row v 0.45 (94, 86)")
    row(rows, "D0o: stone panel, u right (behind the jamb)", 0.422, P.u(xs.max() + 1) if len(xs) else None, "u", "id pass")
    ys = np.nonzero(c[:, P.col(0.30)] == 10)[0]
    row(rows, "D0o: oak floor v top (at the far wall)", 0.696, P.v(ys.min()) if len(ys) else None, "v", "id pass column u 0.30 (10)")
    ys = np.nonzero(c[:, P.col(0.26)] == 14)[0]
    row(rows, "D0o: skirting v top (u 0.26)", 0.669, P.v(ys.min()) if len(ys) else None, "v", "id pass column u 0.26 (14)")
    ys = np.nonzero(np.isin(c[:, P.col(0.41)], (14,)))[0]
    row(rows, "D0o: skirting on the stone (px; designer: none)", 0, int(len(ys)), "px", "id pass column u 0.41", tol=0)
    pj = [P.v(r_ + 0.5) for r_ in runs(c[:, P.col(0.41)], JOINT)]
    row(rows, "D0o: panel joints v (designer: 0.192 0.264 0.309 0.336 0.408 0.435 0.471 0.543 0.570 0.624)", "list", " ".join(f"{x:.3f}" for x in pj), "v", "id pass column u 0.41")
    # HT
    P = Passes("HT", F["HT"], folder=HERE)
    c = P.cls
    r0 = c[P.row(0.45)]
    xs = np.nonzero(np.isin(r0, (PANEL, JOINT)))[0]
    xs = xs[(xs >= P.col(0.0)) & (xs < P.col(1.0))]
    row(rows, "HT: stone panel u left", 0.456, P.u(xs.min()) if len(xs) else None, "u", "id pass row v 0.45")
    row(rows, "HT: stone panel u right (the corner)", 0.790, P.u(xs.max() + 1) if len(xs) else None, "u", "id pass")
    for nm, d, ids in (("HT: front wall plaster (12) u left", 0.790, (12,)), ("HT: walnut lining u left", 0.814, (20, 21, 22, 23)), ("HT: living u left", 0.850, tuple(range(30, 44)))):
        xs = np.nonzero(np.isin(r0, ids))[0]
        xs = xs[(xs >= P.col(0.6)) & (xs < P.col(1.0))]
        row(rows, nm, d, P.u(xs.min()) if len(xs) else None, "u", "id pass row v 0.45")
    rvj = P.row(uv(P.f, (0.81, 7.0, 0.55))[1])
    hj = [P.u(P.col(0.55) + x + 0.5) for x in runs(c[rvj, P.col(0.55):P.col(0.75)], JOINT)]
    row(rows, "HT: head joint Y 7.05 (course 2) u", 0.623, hj[0] if hj else None, "u", "id pass row in course 2", tol=0.01)
    for nm, d, a, b in (("HT: jib seam (Y 9.00) u", 0.158, (11,), (82, 83)), ("HT: jib seam (Y 8.10) u", 0.372, (82, 83), (11,))):
        xs = [x + 1 for x in range(P.col(0.05), P.col(0.45)) if r0[x] in a and r0[x + 1] in b]
        row(rows, nm, d, P.u(xs[0]) if xs else None, "u", "id pass row v 0.45")
    pj = [P.v(r_ + 0.5) for r_ in runs(c[:, P.col(0.70)], JOINT)]
    row(rows, "HT: panel joints v (designer: 0.076 0.140 0.310 0.374 0.459 0.629 0.692 0.820)", "list", " ".join(f"{x:.3f}" for x in pj if -0.2 < x < 1.2), "v", "id pass column u 0.70")
    ys = np.nonzero(c[:, P.col(0.70)] == 14)[0]
    row(rows, "HT: skirting on the stone (px; designer: none)", 0, int(len(ys)), "px", "id pass column u 0.70", tol=0)
    # HD
    P = Passes("HD", F["HD"], folder=HERE)
    c = P.cls
    r0 = c[P.row(0.45)]
    xs = np.nonzero(np.isin(r0, (PANEL, JOINT)))[0]
    row(rows, "HD: stone panel u left", 0.521, P.u(xs.min()) if len(xs) else None, "u", "id pass row v 0.45")
    row(rows, "HD: stone panel to the canvas edge", "1.03", r4(P.u(xs.max() + 1)) if len(xs) else None, "u", "id pass")
    rvj = P.row(uv(P.f, (0.81, 7.0, 1.05))[1])
    hj = [P.u(P.col(0.6) + x + 0.5) for x in runs(c[rvj, P.col(0.6):P.W - 1], JOINT)]
    row(rows, "HD: head joint Y 7.05 (course 4) u", 0.804, hj[0] if hj else None, "u", "id pass row in course 4")
    pj = [P.v(r_ + 0.5) for r_ in runs(c[:, P.col(0.9)], JOINT)]
    row(rows, "HD: panel joints v in the canvas (designer frame: 0.193 0.301 0.444 0.731 0.839; canvas -0.094, 1.054)", "list", " ".join(f"{x:.3f}" for x in pj), "v",
        "id pass column u 0.90")
    for nm, d, a, b in (("HD: jib seam (Y 9.00) u", 0.019, (11,), (82, 83)), ("HD: jib seam (Y 8.10) u", 0.380, (82, 83), (11,))):
        xs = [x + 1 for x in range(0, P.col(0.5)) if r0[x] in a and r0[x + 1] in b]
        row(rows, nm, d, P.u(xs[0]) if xs else None, "u", "id pass row v 0.45")
    bad = int(np.isin(c, (10, 14, 15, 12, 13, SLOT)).sum())
    row(rows, "HD: floor, skirting, ceiling, slot or corner in the canvas (px)", 0, bad, "px", "id pass", tol=0)
    # HDx
    P = Passes("HDx", F["HDx"], folder=HERE)
    c = P.cls
    r0 = c[P.row(0.45)]
    xs = np.nonzero(np.isin(r0, (PANEL, JOINT)))[0]
    xs = xs[xs >= P.col(0.0)]
    row(rows, "HDx: far-wall stone u right (the corner)", 0.259, P.u(xs.max() + 1) if len(xs) else None, "u", "id pass row v 0.45")
    xs = np.nonzero(r0 == 12)[0]
    xs = xs[(xs > P.col(0.2)) & (xs < P.col(0.35))]
    row(rows, "HDx: front-wall plaster return u right", 0.291, P.u(xs.max() + 1) if len(xs) else None, "u", "id pass row v 0.45")
    xs = np.nonzero(np.isin(r0, (20,)))[0]
    row(rows, "HDx: walnut (left jamb) u right", 0.319, P.u(xs.max() + 1) if len(xs) else None, "u", "id pass row v 0.45")
    rvj = P.row(0.30)
    hj = [P.u(x + 0.5) for x in runs(c[rvj, :P.col(0.25)], JOINT)]
    row(rows, "HDx: a head joint near the left edge, u (designer about 0.064)", 0.064, min(hj, key=lambda q: abs(q - 0.064)) if hj else None, "u", "id pass row v 0.30",
        tol=0.02, note="designer: 'about'")
    Xh, Yh, Zh = P.world()
    row(rows, "HDx: skirting on the stone (px; skirting pixels on the far wall, X < 0.815)", 0, int(((c == 14) & (Xh < 0.815)).sum()), "px",
        "id + depth pass (the front-wall skirting is 15 mm proud and shows a few px left of the corner line)", tol=0)
    return rows


# ---------------------------------------------------------------------------------------------------------------
# 6. joints near a frame or canvas edge (11.2 item 18), the S1 events (11.1.10), and the olive in every frame
# ---------------------------------------------------------------------------------------------------------------
def tangency(F):
    out = {}
    for fid, xw in (("D0-closed", 3.95), ("HD", 0.81), ("HT", 0.81)):
        f = F[fid]
        Cv = C.REG if f["canvas"] == "reg" else C.TALL
        oy, fy, H = Cv["box"][1], Cv["box"][3] - Cv["box"][1], Cv["canvas"][1]
        d = f["loc"][0] - xw
        rec = []
        for z in [0.005] + COURSE_TOPS + [2.80, 3.00 if xw < 1 else 2.99]:
            v = f["v0"] + K_V * (f["loc"][2] - z) / d
            py = oy + v * fy
            dist = min(abs(py - 0), abs(py - H), abs(py - oy), abs(py - (oy + fy)))
            if -0.0 <= py <= H:
                rec.append(dict(z=z, v=r4(v), px=round(py, 1), nearest_edge_px=round(dist, 1), under_15=bool(dist < 15)))
        out[fid] = rec
    return out


def s1_events(F, L):
    xc = lambda s: D0F["loc"][0] - s
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
    ev = {"doormat (its far edge X 3.95, Z 0.015) leaves the bottom": (leave((3.95, 8.30, 0.015), "bottom"), 0.72),
          "the seat's corner (4.75, 7.05, 0.45) leaves the bottom": (leave((4.75, 7.05, 0.45), "bottom"), 0.94),
          "the planter's corner (4.75, 7.05, 0.70) leaves the right edge": (leave((4.75, 7.05, 0.70), "right"), 1.50),
          "the wall light's top (4.07, 7.40, 1.925) leaves the top": (leave((4.07, 7.40, 1.925), "top"), 1.59),
          "the wall light's bottom (3.97, 7.40, 1.675) leaves the top": (leave((3.97, 7.40, 1.675), "top"), 2.21),
          "the herbs' last point, at the back against the door wall (4.05, 7.03, 0.90), leaves the right edge": (leave((4.05, 7.03, 0.90), "right"), 2.35)}
    return {k: dict(clay_s_m=v[0], designer_s_m=v[1], diff_m=r4(v[0] - v[1]) if v[0] is not None else None) for k, v in ev.items()}


def ids_in_frames(F):
    out = {}
    for fid in F:
        p = os.path.join(HERE, fid + "-id.png")
        if not os.path.exists(p):
            continue
        P = Passes(fid, F[fid], folder=HERE)
        fb = P.frame()
        cl = P.cls[fb]
        out[fid] = dict(olive_px_canvas=int((P.cls == OLIVE).sum()),
                        in_frame={nm: r4(float(np.isin(cl, ids).mean())) for nm, ids in (("doormat", (MAT,)), ("seat+rim", (CAP,)), ("planter", (PLANTER,)),
                                                                                          ("wall light", (LAMP,)), ("herbs", (HERBS,)), ("door-wall stone", (STONE, REVEAL_ST, JOINT)),
                                                                                          ("hall panel", (PANEL,)), ("slot", (SLOT,)))},
                        undefined_px=int(np.isin(P.cls, (98, 99)).sum()))
    return out


# ---------------------------------------------------------------------------------------------------------------
# 7. the sheet: the new D0 beside M3 and M2 (11.2 item 20), then the rest
# ---------------------------------------------------------------------------------------------------------------
def sheet(F, PS, out_path):
    pad, w4 = 8, 660
    Wd = 4 * w4 + 5 * pad
    sh = Image.new("RGB", (Wd, 3400), (244, 243, 240))
    d = ImageDraw.Draw(sh)
    d.text((pad, 8), "Warm-modern FINAL entrance clay (ENT2: M3 with M2's stone door wall, no sidelight; master-designer ch. 11). render-agent 2026-11-16, 0 tokens. "
                     "Red box = the camera frame.", fill=(15, 15, 15), font=C.font(17))
    d.text((pad, 30), "Row 1: the new D0 clay, the concepts M3 and M2 (text-to-image, not locked), the 2026-11-14 clay. Row 2: D0 no leaf / open, the direct-sun pass, HT. "
                      "Row 3: HD, HDx (3:2), HD57. Then clip 1.", fill=(60, 60, 60), font=C.font(13))
    y = 54

    def ext(path, label, w=w4):
        t = Image.open(path).convert("RGB")
        t = t.resize((w, round(w * t.size[1] / t.size[0])), Image.LANCZOS)
        dd = ImageDraw.Draw(t)
        dd.rectangle([0, 0, w, 20], fill=(20, 20, 20))
        dd.text((6, 3), label, fill=(255, 255, 255), font=C.font(13))
        return t
    tiles = [C.tile(PS["D0-closed"], w4, "NEW D0 clay (ch. 11), leaf closed"), ext(os.path.join(CONCEPTS, "M3.jpg"), "concept M3 'the built bench' (flux-2, not locked)"),
             ext(os.path.join(CONCEPTS, "M2.jpg"), "concept M2 'the stone wall' (flux-2, not locked)"), C.tile(Passes("D0-closed", F["D0-closed"], folder=OLD), w4, "2026-11-14 clay (before ch. 11)")]
    x, hmax = pad, 0
    for t in tiles:
        sh.paste(t, (x, y))
        hmax = max(hmax, t.size[1])
        x += w4 + pad
    y += hmax + pad
    row2 = [C.tile(PS["D0-none"], w4, "D0, no leaf (the clay of D0o)"), C.tile(PS["D0-open"], w4, "D0, leaf open 90")]
    sp = os.path.join(HERE, "D0-closed-sun.png")
    if os.path.exists(sp):
        row2.append(ext(sp, "D0: direct sun only (white = sun; the olive's lace)"))
    row2.append(C.tile(PS["HT"], w4, "HT, the door's sill"))
    x, hmax = pad, 0
    for t in row2:
        sh.paste(t, (x, y))
        hmax = max(hmax, t.size[1])
        x += w4 + pad
    y += hmax + pad
    x, hmax = pad, 0
    for fid, lab in (("HD", "HD (3:2): the stone panel, the jib door"), ("HDx", "HDx (3:2): the stone on the left wall"), ("HD57", "HD57 yaw 57.5 (reserve)")):
        if fid in PS:
            t = C.tile(PS[fid], w4, lab)
            sh.paste(t, (x, y))
            hmax = max(hmax, t.size[1])
        x += w4 + pad
    y += hmax + pad
    d.text((pad, y + 4), "Clip 1: D0 (leaf open) -> HD, 12 stations every 0.449 m", fill=(15, 15, 15), font=C.font(15))
    y += 26
    w6 = (Wd - 7 * pad) // 6
    th = 0
    for k in range(12):
        fid = f"c1/S{k:02d}"
        if fid not in PS:
            continue
        t = C.tile(PS[fid], w6, f"S{k:02d}  s {F[fid]['s']:.2f} m")
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
    rep = {}
    mp = os.path.join(SCRATCH, "meta.json")
    if os.path.exists(mp):
        m = json.load(open(mp))
        rep.update({k: m[k] for k in ("stage", "date", "clip1_length_m", "canvases", "render", "light", "build_notes", "ids", "courses", "heads_court",
                                        "heads_hall", "planter", "bench", "lamp", "doormat", "olive", "panel", "slot", "flutes") if k in m})
    rep["depth_pass"] = "16-bit PNG; planar depth in metres = value / 5000; 65535 = sky; at the pixel centres"
    rep["gate"] = gate(F)
    rows, phone = d0_table(F)
    rep["D0_designer_ch11"] = rows
    rep["D0_phone_391x220"] = phone
    rep["D0_sun"] = sun_d0(F)
    if a.d0:
        print(json.dumps(rep["gate"], indent=1))
        for r in rows:
            print(f"{r['key'][:70]:70s} {str(r['designer']):>8s} {str(r['clay']):>10s} {str(r['diff']):>9s} {'OVER' if r['over'] else ''}")
        print(json.dumps(rep["D0_sun"], indent=1))
        return
    rep["light"] = light(F)
    rep["inside_ch11_5_2"] = inside(F)
    rep["joints_near_an_edge"] = tangency(F)
    rep["S1_events_ch11_1_10"] = s1_events(F, L)
    rep["frames"] = ids_in_frames(F)
    frames_rec = {}
    for fid in F:
        p = os.path.join(SCRATCH, "frames", fid.replace("/", "_") + ".json")
        if os.path.exists(p):
            r = json.load(open(p))
            r.pop("npz", None)
            frames_rec[fid] = r
    rep["render_records"] = frames_rec
    over = [r["key"] for r in rows + rep["inside_ch11_5_2"] if r["over"]]
    rep["summary"] = dict(gate_passed=rep["gate"]["passed"], gate_worst_px=rep["gate"]["worst_px"], ch11_values_over_tolerance=over,
                          olive_px_anywhere=sum(v["olive_px_canvas"] for v in rep["frames"].values()),
                          undefined_px={k: v["undefined_px"] for k, v in rep["frames"].items() if v["undefined_px"]})
    json.dump(rep, open(os.path.join(HERE, "selfcheck.json"), "w"), indent=1, ensure_ascii=False)
    PS = {fid: Passes(fid, F[fid], folder=HERE) for fid in F if os.path.exists(os.path.join(HERE, fid + "-id.png"))}
    if all(k in PS for k in ("D0-closed", "D0-none", "D0-open", "HT")):
        sheet(F, PS, os.path.join(HERE, "contact-sheet.jpg"))
    print(json.dumps(rep["summary"], indent=1))


if __name__ == "__main__":
    main()
