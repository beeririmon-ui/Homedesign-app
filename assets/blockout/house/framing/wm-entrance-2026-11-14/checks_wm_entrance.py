#!/usr/bin/env python3
"""
checks_wm_entrance.py: the measurements on the warm-modern entrance clay (framing_wm_entrance.py), render-agent, 2026-11-14. No Blender.
Reads the delivered passes of this folder (<id>.png, <id>-depth.png, <id>-id.png), docs/house-plan.json, the M0 furn clay and base.png.
Writes selfcheck.json (per-frame records, the designer's projected values against the clay, the path events, the seam with M0) and
contact-sheet.jpg.

  python3 checks_wm_entrance.py            # everything
  python3 checks_wm_entrance.py --no-sheet
"""
import argparse
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
HOUSE = os.path.abspath(os.path.join(HERE, "..", ".."))
REPO = os.path.abspath(os.path.join(HOUSE, "..", "..", ".."))
PLAN_JSON = os.path.join(REPO, "docs", "house-plan.json")
BASE_PNG = os.path.join(REPO, "assets", "renders", "living-room", "warm-modern", "phase2-2026-11-10", "layers", "base.png")
M0_FURN = os.path.join(HOUSE, "framing", "warm-modern-r4", "layers", "furn", "M0.png")
SCRATCH = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-entrance"

CANVAS = (2720, 1530)
M0_CANVAS, M0_CROP = (4072, 2290), (116, 65, 3956, 2225)
OX, OY = M0_CROP[0] * CANVAS[0] / M0_CANVAS[0], M0_CROP[1] * CANVAS[1] / M0_CANVAS[1]
FX, FY = (M0_CROP[2] - M0_CROP[0]) * CANVAS[0] / M0_CANVAS[0], (M0_CROP[3] - M0_CROP[1]) * CANVAS[1] / M0_CANVAS[1]
K_U, K_V = 24.0 / 36.0, 24.0 / 36.0 * 16.0 / 9.0
OPEN = dict(x0=0.95, x1=2.15, y0=6.20, y1=6.35, h=2.40)
DINING = dict(x=2.50, x_out=2.65, y0=2.97, y1=4.57)
HALL = dict(x=(0.80, 3.60), y=(6.35, 9.80))
LIVING = dict(x=(-2.30, 2.50), y=(0.0, 6.20), h=3.0)
HALL_WALLS, LINING, LIVING_ALL = (11, 12, 13), (20, 21, 22, 23, 24), tuple(range(30, 44)) + (0, 50)


def r4(x):
    return None if x is None else round(float(x), 4)


# ---------------------------------------------------------------------------------------------------------------
# cameras (the same derivation as framing_wm_entrance.plan_frames)
# ---------------------------------------------------------------------------------------------------------------
def plan_frames():
    plan = json.load(open(PLAN_JSON))
    C = {c["id"]: c for c in plan["cameras"]}
    T = next(t for t in plan["transitions"] if t["id"] == "T-E0")
    dolly = T["segments"][1]
    h0, h0x, m0 = C["H0"], C["H0x"], C["M0"]
    p0, p1 = h0["loc"], m0["loc"]
    sa, sb = (h0["u0"], h0["v0"]), (m0["u0"], m0["v0"])
    length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    F = {"H0": dict(loc=p0, yaw=h0["yaw_deg_left"], u0=sa[0], v0=sa[1], s=None),
         "H0x-a": dict(loc=p0, yaw=h0x["yaw_deg_left"], u0=sa[0], v0=sa[1], s=0.0),
         "H0x-b": dict(loc=p0, yaw=h0x["yaw_deg_left"], u0=sb[0], v0=sb[1], s=0.0)}
    for k in range(12):
        t = k / 11
        loc = [p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t, p0[2]]
        F[f"a/S{k:02d}"] = dict(loc=loc, yaw=dolly["yaw"], u0=sa[0] + (sb[0] - sa[0]) * t, v0=sa[1] + (sb[1] - sa[1]) * t, s=length * t)
        F[f"b/S{k:02d}"] = dict(loc=loc, yaw=dolly["yaw"], u0=sb[0], v0=sb[1], s=length * t)
    return F, dict(p0=p0, p1=p1, sa=sa, sb=sb, length=length, yaw=dolly["yaw"], plan=plan, T=T, cams=C)


def cam_at(P, s, variant):
    t = s / P["length"]
    sa, sb = P["sa"], P["sb"]
    u0, v0 = (sa[0] + (sb[0] - sa[0]) * t, sa[1] + (sb[1] - sa[1]) * t) if variant == "a" else sb
    return dict(loc=[P["p0"][0] + (P["p1"][0] - P["p0"][0]) * t, P["p0"][1] + (P["p1"][1] - P["p0"][1]) * t, P["p0"][2]],
                yaw=P["yaw"], u0=u0, v0=v0, s=s)


def uv(f, p):
    """The house plan's projection: u = u0 + 0.6667 x/d, v = v0 + 1.1852 (Hc - Z)/d."""
    y = math.radians(f["yaw"])
    fw, rt = (-math.sin(y), -math.cos(y)), (math.cos(y), -math.sin(y))
    dx, dy = p[0] - f["loc"][0], p[1] - f["loc"][1]
    d = fw[0] * dx + fw[1] * dy
    x = rt[0] * dx + rt[1] * dy
    z = p[2] if len(p) > 2 else f["loc"][2]
    return f["u0"] + K_U * x / d, f["v0"] + K_V * (f["loc"][2] - z) / d, d


def slope(f, p):
    """x / d of a plan point (the tangent of its angle right of the heading); None behind the camera plane."""
    y = math.radians(f["yaw"])
    dx, dy = p[0] - f["loc"][0], p[1] - f["loc"][1]
    d = -math.sin(y) * dx - math.cos(y) * dy
    return None if d <= 1e-6 else (math.cos(y) * dx - math.sin(y) * dy) / d


def ray_dir(f, u):
    """Plan direction of the frame column u."""
    y = math.radians(f["yaw"])
    t = (u - f["u0"]) / K_U
    return (-math.sin(y) + t * math.cos(y), -math.cos(y) - t * math.sin(y))


def bisect(fn, lo, hi, n=60):
    flo = fn(lo)
    if flo * fn(hi) > 0:
        return None
    for _ in range(n):
        mid = (lo + hi) / 2
        if fn(mid) * flo > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---------------------------------------------------------------------------------------------------------------
# passes
# ---------------------------------------------------------------------------------------------------------------
class Passes:
    def __init__(self, fid, f, folder=HERE):
        self.fid, self.f = fid, f
        self.cls = np.asarray(Image.open(os.path.join(folder, fid + "-id.png")))
        self.depth = np.asarray(Image.open(os.path.join(folder, fid + "-depth.png"))).astype(np.float64) / 1000.0
        self.png = os.path.join(folder, fid + ".png")
        assert self.cls.shape == (CANVAS[1], CANVAS[0]) == self.depth.shape, (fid, self.cls.shape)
        self._w = None

    def px(self, u):
        return OX + u * FX

    def py(self, v):
        return OY + v * FY

    def u(self, px):
        return (px - OX) / FX

    def v(self, py):
        return (py - OY) / FY

    def row(self, v):
        return int(min(CANVAS[1] - 1, max(0, math.floor(self.py(v)))))

    def col(self, u):
        return int(min(CANVAS[0] - 1, max(0, math.floor(self.px(u)))))

    def world(self):
        if self._w is None:
            f = self.f
            u = (np.arange(CANVAS[0]) + 0.5 - OX) / FX
            v = (np.arange(CANVAS[1]) + 0.5 - OY) / FY
            y = math.radians(f["yaw"])
            d = np.where(self.depth < 65.0, self.depth, np.nan)
            xc = (u[None, :] - f["u0"]) * d / K_U
            self._w = (f["loc"][0] - d * math.sin(y) + xc * math.cos(y), f["loc"][1] - d * math.cos(y) - xc * math.sin(y),
                       f["loc"][2] - (v[:, None] - f["v0"]) * d / K_V)
        return self._w

    def step_x(self, row, a, b, lo=0, hi=None):
        """First boundary on a row (pixel edge x, sub-pixel = edge between two pixels) where the id goes from the set a to the set b."""
        c = self.cls[row]
        hi = CANVAS[0] - 1 if hi is None else hi
        for x in range(max(0, lo), min(CANVAS[0] - 1, hi)):
            if c[x] in a and c[x + 1] in b:
                return x + 1
        return None

    def step_y(self, col, a, b, lo=0, hi=None):
        c = self.cls[:, col]
        hi = CANVAS[1] - 1 if hi is None else hi
        for y in range(max(0, lo), min(CANVAS[1] - 1, hi)):
            if c[y] in a and c[y + 1] in b:
                return y + 1
        return None

    def lum(self):
        rgb = np.asarray(Image.open(self.png).convert("RGB")).astype(np.float64)
        return rgb @ np.array([0.2126, 0.7152, 0.0722])


def row_entry(P, cid, lo, hi, n=1):
    return None


# ---------------------------------------------------------------------------------------------------------------
# 1. the designer's projected values against the clay
# ---------------------------------------------------------------------------------------------------------------
def table_designer(F, PF, PS):
    rows = []

    def add(key, frame, designer, clay, unit, method, note="", tol=None):
        diff = None
        if isinstance(designer, (int, float)) and isinstance(clay, (int, float)):
            diff = clay - designer
        rows.append(dict(key=key, frame=frame, designer=designer, clay=r4(clay) if isinstance(clay, float) else clay, diff=r4(diff),
                         unit=unit, method=method, note=note, tol=tol,
                         flag=bool(diff is not None and tol is not None and abs(diff) > tol)))

    h0, hxa, hxb = F["H0"], F["H0x-a"], F["H0x-b"]
    A, XA, XB = PS["H0"], PS["H0x-a"], PS["H0x-b"]
    O = OPEN

    def openings(Pp, f, tag, d_vals, who):
        hr = Pp.row(f["v0"])                                    # the row at the camera height (Z 1.20)
        xc = Pp.step_x(hr, (11,), (12,))
        xl = Pp.step_x(hr, (12,), LINING + LIVING_ALL)          # hall front wall -> the reveal (X 0.95, Y 6.35)
        xv = Pp.step_x(hr, LINING, LIVING_ALL, lo=xl or 0)      # reveal -> the living room (X 0.95, Y 6.20)
        xr = Pp.step_x(hr, LIVING_ALL + LINING, (12,), lo=xv or 0)  # the view -> hall front wall (X 2.15, Y 6.35)
        m = "id pass, row at Z 1.20; pixel edge"
        if d_vals.get("corner") is not None:
            add(f"corner X 0.80 / Y 6.35, u ({tag})", Pp.fid, d_vals["corner"], Pp.u(xc) if xc else None, "u", m, who, 0.003)
        add(f"opening, left jamb at the hall face (0.95, 6.35), u ({tag})", Pp.fid, d_vals["l"], Pp.u(xl) if xl else None, "u", m, who, 0.003)
        if d_vals.get("j") is not None:
            add(f"walnut jamb ends / the view starts (0.95, 6.20), u ({tag})", Pp.fid, d_vals["j"], Pp.u(xv) if xv else None, "u", m, who, 0.003)
        add(f"opening, right edge at the hall face (2.15, 6.35), u ({tag})", Pp.fid, d_vals["r"], Pp.u(xr) if xr else None, "u", m, who, 0.003)
        return xc, xl, xv, xr, hr

    xc, xl, xv, xr, hr = openings(A, h0, "H0", dict(corner=0.199, l=0.228, j=0.248, r=0.484), "designer 1.2; QA list +-0.01")
    add("opening centre: the door's centre point (1.55, 6.35), u (H0)", "H0", 0.351, uv(h0, (1.55, 6.35))[0], "u",
        "plan projection, confirmed by the Blender camera (camera_vs_plan_projection)", "plan 6.3 / cameras.H0", 0.003)
    if xl and xr:
        add("opening centre: the middle of the two edges in the image, u (H0)", "H0", None, (A.u(xl) + A.u(xr)) / 2, "u", "id pass",
            "the image midpoint is not the door's centre point (perspective): 0.356 against 0.351")
    # left margin / right margin: where the frame edges meet the walls
    X, Y, Z = A.world()
    add("left frame edge meets the left wall at Y (H0)", "H0", 7.29, float(Y[hr, A.col(0.0)]), "m", "depth pass, frame column u 0, row at Z 1.20",
        "plan cameras.H0 / designer 1.2", 0.02)
    add("right frame edge meets the right wall at Y (H0)", "H0", 7.40, float(Y[hr, A.col(1.0) - 1]), "m", "depth pass, frame column u 1", "designer 1.2 (projection)", 0.02)
    x13 = A.step_x(hr, (12,), (13,), lo=xr or 0)
    add("corner X 3.60 / Y 6.35, u (H0)", "H0", 0.86, A.u(x13) if x13 else None, "u", "id pass, row at Z 1.20", "designer 1.2 (projection)", 0.003)
    add("front door, near jamb (3.60, 7.80), u (H0)", "H0", 1.13, uv(h0, (3.60, 7.80))[0], "u", "plan projection; the canvas ends at u 1.030",
        "outside the frame and the overscan; no door pixel in any frame (pass indices)", 0.01)
    # verticals: floor line at the two jambs (motion-agent's check value), the head
    for lab, pt, dv in (("floor at the left jamb (0.95, 6.35, 0), v (H0)", (0.95, 6.35, 0.0), 0.929), ("floor at the right edge (2.15, 6.35, 0), v (H0)", (2.15, 6.35, 0.0), 0.971)):
        u_, v_, _ = uv(h0, pt)
        add(lab, "H0", dv, v_, "v", "plan projection = Blender camera", "motion-agent 0 (designer: 'the clay shows the floor higher')", 0.003)
    # the floor line measured on the id pass: skirting foot under the hall front wall, at the columns next to the opening
    for lab, u_at, dv in (("floor line under the front wall, just left of the opening, v (H0)", 0.214, None),
                          ("floor line under the front wall, just right of the opening, v (H0)", 0.50, None)):
        c = A.col(u_at)
        yb = A.step_y(c, (14,), (10,))
        if yb:
            Xw, Yw = float(X[yb - 1, c]), float(Y[yb - 1, c])
            add(lab, "H0", r4(uv(h0, (Xw, 6.335, 0.0))[1]), A.v(yb), "v", "id pass: skirting foot (the skirting is 1.5 cm proud: Y 6.335); "
                "designer column = the plan projection of that point", "the measured floor line in the clay", 0.003)
    vL, vR = uv(h0, (0.95, 6.35, 2.40))[1], uv(h0, (2.15, 6.35, 2.40))[1]
    c = A.col(A.u(xl) + 0.004) if xl else None
    yh = A.step_y(c, (12,), LINING + LIVING_ALL) if c else None
    add("head of the opening (Z 2.40) at the left jamb, v (H0)", "H0", "-0.05 .. +0.01", A.v(yh) if yh else vL, "v",
        "id pass (in the overscan)" if yh else "plan projection", f"projection: {vL:.4f} at the left jamb, {vR:.4f} at the right edge; the head is above the frame along its whole length")
    # where the head leaves the canvas (top edge of the overscan)
    top = A.cls[0]
    xs = [x for x in range(CANVAS[0] - 1) if top[x] in LINING + LIVING_ALL]
    if xs:
        add("head inside the overscan (above v 0) from the left jamb to u (H0)", "H0", None, A.u(max(xs) + 1), "u", "id pass, top row of the canvas (v -0.030)",
            "to the right of this the head is above the canvas too")
    # the two points of clean plaster
    for lab, pt, dv, want in (("wall-sconce point (0.80, 6.95, 1.94) (H0)", (0.80, 6.95, 1.94), (0.09, 0.106), 11),
                              ("pendant hang point (0.20, 1.72, 3.00) (H0)", (0.20, 1.72, 3.00), (0.425, 0.18), 35)):
        u_, v_, d_ = uv(h0, pt)
        cx, cy = A.col(u_), A.row(v_)
        seen = bool(abs(A.depth[cy, cx] - d_) < 0.05)
        add(lab + ", u", "H0", dv[0], u_, "u", "plan projection = Blender camera", "", 0.003)
        add(lab + ", v", "H0", dv[1], v_, "v", "plan projection = Blender camera",
            f"the pixel shows id {int(A.cls[cy, cx])} ({'the point itself: bare plaster' if seen and int(A.cls[cy, cx]) == want else 'NOT the point: hidden'}), "
            f"depth {A.depth[cy, cx]:.3f} against {d_:.3f}", 0.004)
    # the living ceiling strip in the view
    cols = [A.col(u_) for u_ in np.linspace(A.u(xv) + 0.01, A.u(xr) - 0.01, 12)] if xv and xr else []
    lows = [max(np.nonzero(np.isin(A.cls[:, c], (35, 36)))[0]) for c in cols if np.isin(A.cls[:, c], (35, 36)).any()]
    tops = [min(np.nonzero(np.isin(A.cls[:, c], (35, 36)))[0]) for c in cols if np.isin(A.cls[:, c], (35, 36)).any()]
    if lows:
        add("living ceiling in the view, lowest v (H0)", "H0", 0.23, A.v(max(lows) + 1), "v", "id pass, 12 columns of the view", "designer 1.2: 'about v 0-0.23'", 0.01)
        add("living ceiling in the view, highest v (H0)", "H0", 0.0, A.v(min(tops)), "v", "id pass", "the ceiling fills the view up to the canvas top (the soffit is above it)")
    # plank lines
    for lab, f, dv in (("plank lines converge at (H0)", h0, (0.66, 0.46)), ("plank lines converge at (M0)", F["b/S11"], (0.78, 0.50))):
        u_ = f["u0"] + K_U * math.tan(math.radians(f["yaw"]))
        add(lab + ", u", "H0" if f is h0 else "b/S11", dv[0], u_, "u", "vanishing point of -Y: u0 + 0.6667 tan(yaw)", "", 0.005)
        add(lab + ", v", "H0" if f is h0 else "b/S11", dv[1], f["v0"], "v", "v0", "", 0.005)
    # shares of the frame
    fb = (slice(int(round(OY)), int(round(OY + FY))), slice(int(round(OX)), int(round(OX + FX))))
    cl = A.cls[fb]
    add("quiet plaster (hall walls) share of the frame (H0)", "H0", 0.50, float(np.isin(cl, HALL_WALLS).mean()), "share", "id pass, inside the camera frame",
        "designer 1.2: 'the empty space is about 50 %'", 0.08)
    add("the living view share of the frame (H0)", "H0", None, float(np.isin(cl, tuple(range(30, 44)) + (0,)).mean()), "share", "id pass")
    # ---- H0x ----
    openings(XA, hxa, "H0x-a", dict(l=0.395, r=0.636), "designer 3.1")
    openings(XB, hxb, "H0x-b", dict(l=0.345, r=0.586), "motion-agent 1")
    for Pp, f, dv, who in ((XA, hxa, 7.98, "designer 3.1 / plan rooms.hall"), (XB, hxb, 7.85, "motion-agent 1")):
        Xw, Yw, _ = Pp.world()
        r_ = Pp.row(f["v0"])
        add(f"left frame edge meets the left wall at Y ({Pp.fid})", Pp.fid, dv, float(Yw[r_, Pp.col(0.0)]), "m", "depth pass, frame column u 0", who, 0.02)
        add(f"left CANVAS edge (overscan, u -0.030) meets the left wall at Y ({Pp.fid})", Pp.fid, None, float(Yw[r_, 0]), "m", "depth pass, canvas column 0",
            "the work-room door jamb is at Y 8.10")
    Xw, Yw, _ = XA.world()
    add("right frame edge rests on the front wall at X (H0x-a)", "H0x-a", 3.39, float(Xw[XA.row(hxa["v0"]), XA.col(1.0) - 1]), "m", "depth pass, frame column u 1", "designer 3.1", 0.02)
    Xw, Yw, _ = XB.world()
    add("right frame edge rests on the front wall at X (H0x-b)", "H0x-b", None, float(Xw[XB.row(hxb["v0"]), XB.col(1.0) - 1]), "m", "depth pass, frame column u 1")
    for Pp, f in ((XA, hxa), (XB, hxb)):
        vl = uv(f, (0.95, 6.35, 2.40))[1]
        xl_ = Pp.step_x(Pp.row(f["v0"]), (12,), LINING + LIVING_ALL)
        c = Pp.col(Pp.u(xl_) + 0.004) if xl_ else None
        yh = Pp.step_y(c, (12,), LINING + LIVING_ALL) if c else None
        add(f"top-left corner of the opening in the frame: head v at the left jamb ({Pp.fid})", Pp.fid, "in frame", Pp.v(yh) if yh else None, "v", "id pass",
            f"projection {vl:.4f}; head at the right edge {uv(f, (2.15, 6.35, 2.40))[1]:.4f}")
    # motion-agent: how much of H0x does H0 cover
    for tag, f in (("H0x-a", hxa), ("H0x-b", hxb)):
        uu, vv = np.meshgrid(np.linspace(0, 1, 801), np.linspace(0, 1, 451))
        t, w = (uu - f["u0"]) / K_U, (f["v0"] - vv) / K_V
        a = math.radians(f["yaw"] - h0["yaw"])
        d2, x2 = math.cos(a) + t * math.sin(a), -math.sin(a) + t * math.cos(a)
        u2, v2 = h0["u0"] + K_U * x2 / d2, h0["v0"] - K_V * w / d2
        inside = (u2 >= 0) & (u2 <= 1) & (v2 >= 0) & (v2 <= 1)
        add(f"share of {tag} that H0 covers", tag, 0.84 if tag == "H0x-b" else None, float(inside.mean()), "share", "rotation of 13 deg about the lens, both frames",
            "motion-agent 2: 84 % (strip of 16 % on the left, about 1 % at the top)" if tag == "H0x-b" else "", 0.02)
    return rows


# ---------------------------------------------------------------------------------------------------------------
# 2. the path: events along the dolly, both shift variants (analytic, from the plan's geometry)
# ---------------------------------------------------------------------------------------------------------------
def dining_share(f, canvas=False):
    """Width (in frame units of u) of the O-living-dining hole (wall plane X 2.50, Y 2.97-4.57) that the frame shows, through the
    entrance opening when the camera is still behind it."""
    lo, hi = ((-OX / FX, (CANVAS[0] - OX) / FX) if canvas else (0.0, 1.0))
    lo, hi = (lo - f["u0"]) / K_U, (hi - f["u0"]) / K_U
    cy = f["loc"][1]
    for yy in (OPEN["y1"], OPEN["y0"]):
        if cy > yy + 1e-9:
            a, b = slope(f, (OPEN["x0"], yy)), slope(f, (OPEN["x1"], yy))
            if a is None or b is None:
                return 0.0
            lo, hi = max(lo, a), min(hi, b)
    a = slope(f, (DINING["x"], DINING["y0"]))
    b = slope(f, (DINING["x"], DINING["y1"]))
    if a is None:
        return 0.0
    lo, hi = max(lo, a), (hi if b is None else min(hi, b))
    return max(0.0, hi - lo) * K_U


def path_events(PF):
    P = PF
    L = P["length"]
    out = dict(length_m=r4(L), plan_len_m=P["T"]["segments"][1]["len_m"],
               path_heading_deg=r4(math.degrees(math.atan2(-(P["p1"][0] - P["p0"][0]), -(P["p1"][1] - P["p0"][1])))), camera_yaw=P["yaw"])
    dx, dy = (P["p1"][0] - P["p0"][0]) / L, (P["p1"][1] - P["p0"][1]) / L
    s_face, s_liv = (OPEN["y1"] - P["p0"][1]) / dy, (OPEN["y0"] - P["p0"][1]) / dy
    x_face, x_liv = P["p0"][0] + dx * s_face, P["p0"][0] + dx * s_liv
    nrm = (-dy, dx)
    clr = lambda p: abs((p[0] - P["p0"][0]) * nrm[0] + (p[1] - P["p0"][1]) * nrm[1])
    out["wall"] = dict(s_hall_face=r4(s_face), s_living_face=r4(s_liv), x_at_hall_face=r4(x_face), x_at_living_face=r4(x_liv),
                       designer=dict(s=[2.97, 3.13], x=1.553), motion_agent=dict(x=[1.62, 1.55]),
                       jamb_clearance_m=dict(right_jamb_hall_edge=r4(clr((OPEN["x1"], OPEN["y1"]))), right_jamb_living_edge=r4(clr((OPEN["x1"], OPEN["y0"]))),
                                             left_jamb_hall_edge=r4(clr((OPEN["x0"], OPEN["y1"]))), left_jamb_living_edge=r4(clr((OPEN["x0"], OPEN["y0"]))),
                                             plan_min=P["T"]["min_jamb_clearance_m"]))
    out["right_jamb_reveal_seen_from_s"] = dict(clay=r4((OPEN["x1"] - P["p0"][0]) / dx), designer=1.7)
    for var in ("a", "b"):
        E = {}
        cam = lambda s: cam_at(P, s, var)
        # the head (Z 2.40): its hall-face edge and the soffit's far edge leave the top of the frame at their left ends
        E["head_hall_edge_leaves_top_s"] = r4(bisect(lambda s: uv(cam(s), (OPEN["x0"], OPEN["y1"], OPEN["h"]))[1], 0.0, 2.5))
        E["soffit_far_edge_leaves_top_s"] = r4(bisect(lambda s: uv(cam(s), (OPEN["x0"], OPEN["y0"], OPEN["h"]))[1], 0.0, 2.5))
        # jambs: the hall-face edge reaches the frame edge (the jamb starts to be cut), the living-face edge reaches it (the jamb is out)
        E["left_jamb_cut_from_s"] = r4(bisect(lambda s: uv(cam(s), (OPEN["x0"], OPEN["y1"]))[0], 0.0, s_face - 0.01))
        E["left_jamb_out_at_s"] = r4(bisect(lambda s: uv(cam(s), (OPEN["x0"], OPEN["y0"]))[0], 0.0, s_liv - 0.01))
        E["right_jamb_cut_from_s"] = r4(bisect(lambda s: uv(cam(s), (OPEN["x1"], OPEN["y1"]))[0] - 1.0, 0.0, s_face - 0.01))
        E["right_jamb_out_at_s"] = r4(bisect(lambda s: uv(cam(s), (OPEN["x1"], OPEN["y0"]))[0] - 1.0, 0.0, s_liv - 0.01))
        # the dining opening in the frame
        ss = np.arange(0.0, L + 1e-9, 0.005)
        sh = np.array([dining_share(cam(s)) for s in ss])
        shc = np.array([dining_share(cam(s), canvas=True) for s in ss])
        on = np.nonzero(sh > 1e-4)[0]
        onc = np.nonzero(shc > 1e-4)[0]
        E["dining_opening_in_frame"] = dict(
            from_s=r4(ss[on[0]]) if len(on) else None, to_s=r4(ss[on[-1]]) if len(on) else None,
            max_share_of_frame_width=r4(sh.max()), at_s=r4(ss[sh.argmax()]),
            in_canvas_from_s=r4(ss[onc[0]]) if len(onc) else None, in_canvas_to_s=r4(ss[onc[-1]]) if len(onc) else None,
            share_at_stations={f"S{k:02d}": r4(dining_share(cam(L * k / 11))) for k in range(12)},
            designer="never enters (3.3: more than 50 deg from the axis, HC7)", motion_agent="outside at every point")
        # the window wall's front strip, one metre before M0
        c = cam(L - 1.0)
        d0 = ray_dir(c, 0.0)
        tt = (LIVING["x"][0] - c["loc"][0]) / d0[0]
        E["left_edge_meets_window_wall_at_Y_one_metre_before_M0"] = dict(clay=r4(c["loc"][1] + tt * d0[1]), designer=3.5)
        # the end: where the frame edges land at M0
        c = cam(L)
        d1 = ray_dir(c, 1.0)
        tt = (LIVING["y"][0] - c["loc"][1]) / d1[1]
        E["M0_right_edge_meets_back_wall_at_X"] = dict(clay=r4(c["loc"][0] + tt * d1[0]), plan=1.94)
        out["variant_" + var] = E
    out["designer_says"] = dict(head="leaves the top margin in the first half metre", jambs="both leave in the last 0.5 m before the wall plane, together (the 'wipe')")
    out["motion_agent_says"] = dict(head="first 0.4 m", right_jamb=[2.14, 2.20], left_jamb=[2.39, 2.61], wall=[2.97, 3.13])
    return out


# ---------------------------------------------------------------------------------------------------------------
# 3. verticals, emptiness, stations
# ---------------------------------------------------------------------------------------------------------------
def verticals(PS):
    """U14: a vertical building edge must stay in one pixel column. Measured on id-pass boundaries at 9 rows."""
    out = {}
    for fid, a, b, lab in (("H0", (11,), (12,), "hall corner X 0.80 / Y 6.35"), ("H0", (12,), LINING + LIVING_ALL, "left jamb, hall face"),
                           ("H0", (12,), (13,), "hall corner X 3.60 / Y 6.35"), ("H0x-a", (11,), (12,), "hall corner X 0.80 / Y 6.35"),
                           ("H0x-a", (12,), LINING + LIVING_ALL, "left jamb, hall face"), ("H0x-b", (11,), (12,), "hall corner X 0.80 / Y 6.35"),
                           ("H0x-b", (12,), LINING + LIVING_ALL, "left jamb, hall face"), ("b/S04", (12,), LINING + LIVING_ALL, "left jamb, hall face"),
                           ("b/S11", (39,), (32, 31, 37), "glazing front jamb / window wall"), ("b/S11", (0,), (39,), "mullion edge")):
        if fid not in PS:
            continue
        Pp = PS[fid]
        xs = []
        for v in np.linspace(0.10, 0.80, 9):
            x = Pp.step_x(Pp.row(v), a, b)
            if x is not None:
                xs.append(x)
        if len(xs) >= 5:
            out[f"{fid}: {lab}"] = dict(rows=len(xs), column_px_min=int(min(xs)), column_px_max=int(max(xs)), spread_px=int(max(xs) - min(xs)))
    worst = max((v["spread_px"] for v in out.values()), default=None)
    return dict(edges=out, worst_spread_px=worst, rule="tilt 0, roll 0 (rotation set to (90, 0, 180 - yaw) deg); spread over v 0.10-0.80 must be <= 1 px",
                pass_=bool(worst is not None and worst <= 1))


# ---------------------------------------------------------------------------------------------------------------
# 4. the seam with M0
# ---------------------------------------------------------------------------------------------------------------
PAIRS = {(31, 35): "back wall | ceiling", (31, 38): "back wall | skirting top", (38, 30): "skirting foot | floor", (31, 41): "back wall | sofa",
         (30, 41): "floor | sofa", (30, 42): "floor | coffee table", (41, 42): "sofa | coffee table", (30, 43): "floor | armchair",
         (40, 43): "bench | armchair", (39, 43): "glazing | armchair", (32, 39): "window wall | glazing frame", (0, 39): "sky | glazing frame",
         (36, 35): "dropped band | ceiling", (36, 32): "dropped band | window wall", (36, 39): "dropped band | glazing", (36, 31): "dropped band | back wall",
         (39, 40): "glazing | bench", (30, 40): "floor | bench", (32, 40): "window wall | bench", (31, 43): "back wall | armchair",
         (32, 43): "window wall | armchair", (31, 42): "back wall | coffee table", (32, 38): "window wall | skirting", (37, 38): "rounded corner | skirting",
         (37, 40): "rounded corner | bench", (37, 35): "rounded corner | ceiling", (37, 36): "rounded corner | band", (0, 43): "sky | armchair",
         (0, 40): "sky | bench", (40, 38): "bench | skirting"}


def structure_samples(cls, step=16):
    """Sample points on the id-pass boundaries: (x, y, nx, ny, pair). The normal comes from the local direction of the boundary."""
    Hh, Ww = cls.shape
    pts = []
    hx = cls[:, :-1] != cls[:, 1:]                 # boundary between x and x+1: point (x+1, y+0.5)
    hy = cls[:-1, :] != cls[1:, :]                 # boundary between y and y+1: point (x+0.5, y+1)
    B = np.zeros((Hh, Ww), bool)
    B[:, 1:] |= hx
    B[1:, :] |= hy
    ys, xs = np.nonzero(hx)
    for x, y in zip(xs, ys):
        if (y % step) == 0:
            pts.append((x + 1.0, y + 0.5, tuple(sorted((int(cls[y, x]), int(cls[y, x + 1]))))))
    ys, xs = np.nonzero(hy)
    for x, y in zip(xs, ys):
        if (x % step) == 0:
            pts.append((x + 0.5, y + 1.0, tuple(sorted((int(cls[y, x]), int(cls[y + 1, x]))))))
    out = []
    r = 7
    for (x, y, pair) in pts:
        xi, yi = int(x), int(y)
        if xi < r + 12 or yi < r + 12 or xi >= Ww - r - 12 or yi >= Hh - r - 12:
            continue
        win = B[yi - r:yi + r + 1, xi - r:xi + r + 1]
        py_, px_ = np.nonzero(win)
        if len(px_) < 6:
            continue
        c = np.cov(np.vstack([px_, py_]).astype(float))
        w, v = np.linalg.eigh(c)
        if w[1] < 4.0 * max(w[0], 1e-6):           # not a clean line here (a corner, a T): skip
            continue
        t = v[:, 1]
        out.append((x, y, -t[1], t[0], pair))
    return out


def bilinear(img, x, y):
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def edge_offsets(samples, lum, search=8.0, min_grad=1.5):
    """Along each sample's normal: where is the strongest luminance step of the image, within +-search px. Image arrays are indexed at
    pixel centres, so the canvas point (x, y) is the array position (x - 0.5, y - 0.5)."""
    ks = np.arange(-search - 1.0, search + 1.0 + 1e-9, 0.5)
    res = []
    for (x, y, nx, ny, pair) in samples:
        prof = bilinear(lum, x - 0.5 + ks * nx, y - 0.5 + ks * ny)
        g = np.abs(np.convolve(prof, [1, 0, -1], mode="same"))[2:-2]       # derivative over 1 px
        kk = ks[2:-2]
        i = int(g.argmax())
        if g[i] < min_grad or i in (0, len(g) - 1) or g[i] < 2.5 * np.median(g):
            res.append((x, y, pair, None))
            continue
        den = g[i - 1] - 2 * g[i] + g[i + 1]
        sub = 0.0 if abs(den) < 1e-9 else 0.5 * (g[i - 1] - g[i + 1]) / den
        res.append((x, y, pair, float(kk[i] + 0.5 * sub)))
    return res


def summarise_offsets(res, limit=2.0):
    by = {}
    for (x, y, pair, off) in res:
        by.setdefault(pair, []).append((x, y, off))
    lines = {}
    worst = None
    for pair, L_ in sorted(by.items()):
        offs = [(x, y, o) for x, y, o in L_ if o is not None]
        if len(L_) < 8:
            continue
        name = PAIRS.get(pair, f"id {pair[0]} | id {pair[1]}")
        if len(offs) < max(6, 0.3 * len(L_)):
            lines[name] = dict(samples=len(L_), measured=len(offs), note="edge not readable in this image (no clear luminance step)")
            continue
        a = np.array([o for _, _, o in offs])
        i = int(np.abs(a).argmax())
        p90 = float(np.percentile(np.abs(a), 90))
        lines[name] = dict(samples=len(L_), measured=len(offs), median_px=round(float(np.median(a)), 2), p90_abs_px=round(p90, 2),
                           max_abs_px=round(float(np.abs(a).max()), 2), max_at_px=[round(offs[i][0]), round(offs[i][1])],
                           max_at_uv=[round((offs[i][0] - OX) / FX, 3), round((offs[i][1] - OY) / FY, 3)], over_limit=bool(p90 > limit))
        if worst is None or p90 > worst[1]:
            worst = (name, p90)
    allo = np.array([o for (_, _, _, o) in res if o is not None])
    return dict(lines=lines, all_samples=len(res), all_measured=int(len(allo)), median_abs_px=round(float(np.median(np.abs(allo))), 2) if len(allo) else None,
                p90_abs_px=round(float(np.percentile(np.abs(allo), 90)), 2) if len(allo) else None,
                p99_abs_px=round(float(np.percentile(np.abs(allo), 99)), 2) if len(allo) else None,
                share_within_2px=round(float((np.abs(allo) <= limit).mean()), 4) if len(allo) else None,
                worst_line_by_p90=dict(line=worst[0], p90_abs_px=round(worst[1], 2)) if worst else None)


def plank_joints(lum, P11, floor_id=30):
    """Joint lines of the floor in an M0 image: every floor pixel votes its high-passed luminance into a histogram over the world X
    (planks run along Y, so a joint is a line of constant X). Returns the period and phase of the dips."""
    X, Y, Z = P11.world()
    m = (P11.cls == floor_id) & np.isfinite(X) & (Y > 0.25) & (Y < 3.2)
    hp = lum - (np.cumsum(np.pad(lum, ((0, 0), (16, 16)), mode="edge"), axis=1)[:, 32:] - np.cumsum(np.pad(lum, ((0, 0), (16, 16)), mode="edge"), axis=1)[:, :-32]) / 32.0
    bw = 0.004
    xs = X[m]
    lo, hi = -2.2, 2.2
    b = np.floor((xs - lo) / bw).astype(int)
    ok = (b >= 0) & (b < int((hi - lo) / bw))
    n = int((hi - lo) / bw)
    s = np.bincount(b[ok], weights=hp[m][ok], minlength=n)
    c = np.bincount(b[ok], minlength=n)
    prof = np.where(c > 200, s / np.maximum(c, 1), np.nan)
    valid = np.isfinite(prof)
    if valid.sum() < 100:
        return dict(note="floor not readable")
    p = np.where(valid, prof, 0.0)
    p = p - p[valid].mean()
    best = None
    scores = {}
    for per in np.arange(0.12, 0.40, 0.001):
        ph = (np.arange(n) * bw + lo) / per * 2 * math.pi
        cs, sn = (p * np.cos(ph) * valid).sum(), (p * np.sin(ph) * valid).sum()
        amp = math.hypot(cs, sn) / valid.sum()
        scores[round(per, 3)] = amp
        if best is None or amp > best[1]:
            best = (per, amp, math.atan2(sn, cs))
    per, amp, phase = best
    # dips (dark joints): cos(2 pi x / per - phase) = -1  ->  x = per (phase + pi) / (2 pi) + k per
    x0 = per * (phase + math.pi) / (2 * math.pi)
    k = np.round((np.arange(-2.2, 2.2, per) - x0) / per)
    joints = sorted(set(round(float(x0 + kk * per), 3) for kk in k if -2.2 <= x0 + kk * per <= 2.2))
    top = sorted(scores.items(), key=lambda q: -q[1])[:1]
    med = float(np.median(list(scores.values())))
    return dict(period_m=round(float(per), 3), amplitude=round(float(amp), 3), peak_over_median=round(float(amp / max(med, 1e-9)), 1),
                joint_x_m=joints, x_range_seen=[round(float(np.nanmin(np.where(valid, np.arange(n) * bw + lo, np.nan))), 2),
                                                round(float(np.nanmax(np.where(valid, np.arange(n) * bw + lo, np.nan))), 2)],
                method="floor pixels of M0 vote a 32 px high-passed luminance into 4 mm bins of world X (depth pass of station 11); period by the strongest harmonic 12-40 cm")


def seam(PS, F):
    P11 = PS["b/S11"]
    out = dict(camera_station_11=dict(loc=[r4(x) for x in F["b/S11"]["loc"]], yaw=F["b/S11"]["yaw"], u0=F["b/S11"]["u0"], v0=F["b/S11"]["v0"]),
               camera_M0_plan="(0.83, 4.64, 1.20), yaw 25, 24 mm, u0 0.47, v0 0.50")
    samples = structure_samples(P11.cls)
    lum11 = P11.lum()
    furn = np.asarray(Image.open(M0_FURN).convert("RGB").resize(CANVAS, Image.LANCZOS)).astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    base_rgb = np.asarray(Image.open(BASE_PNG).convert("RGB")).astype(np.float64)
    base = base_rgb @ np.array([0.2126, 0.7152, 0.0722])
    o_self = edge_offsets(samples, lum11)
    o_furn = edge_offsets(samples, furn)
    o_base = edge_offsets(samples, base, min_grad=2.5)
    out["structure_samples"] = len(samples)
    out["station11_own_lit_clay"] = summarise_offsets(o_self)
    out["vs_M0_clay_furn_layer"] = summarise_offsets(o_furn)
    out["vs_base_png"] = summarise_offsets(o_base)
    # station 11 against the M0 clay, the direct way: where each sample's step sits in the two clays
    d = [(x, y, pair, b - a) for (x, y, pair, a), (_, _, _, b) in zip(o_self, o_furn) if a is not None and b is not None]
    out["station11_vs_M0_clay_same_edge"] = summarise_offsets(d)
    dd = np.array([o for (_, _, _, o) in d])
    i = int(np.abs(dd).argmax())
    out["station11_vs_M0_clay_same_edge"]["largest"] = dict(px=round(float(dd[i]), 2), at_px=[round(d[i][0]), round(d[i][1])], line=PAIRS.get(d[i][2], str(d[i][2])))
    diff = np.abs(lum11 - furn)
    out["station11_vs_M0_clay_pixels"] = dict(mean_abs_diff_levels=round(float(diff.mean()), 2), p99_abs_diff_levels=round(float(np.percentile(diff, 99)), 1),
                                              note="8-bit luminance; the M0 clay was scaled from 4072 x 2290 with Lanczos, 16 samples each, different noise")
    out["floor_joints"] = dict(base_png=plank_joints(base, P11), station_11_clay=plank_joints(lum11, P11),
                               clay_model="X = -2.32 + 0.22 k (build_alts.Shell.planks: the first board starts 2 cm under the window wall)")
    return out, (samples, o_furn, o_base)


# ---------------------------------------------------------------------------------------------------------------
# 5. contact sheet
# ---------------------------------------------------------------------------------------------------------------
def font(sz):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def tile(path, w, label, sub="", frame_box=True):
    im = Image.open(path).convert("RGB")
    h = round(w * im.size[1] / im.size[0])
    im = im.resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    if frame_box:
        k = w / CANVAS[0]
        d.rectangle([OX * k, OY * k, (OX + FX) * k, (OY + FY) * k], outline=(210, 60, 40), width=1)
    d.rectangle([0, 0, w, 20 + (16 if sub else 0)], fill=(20, 20, 20))
    d.text((6, 3), label, fill=(255, 255, 255), font=font(13))
    if sub:
        d.text((6, 20), sub, fill=(200, 200, 200), font=font(11))
    return im


def depth_tile(path, w, label):
    d = np.asarray(Image.open(path)).astype(np.float64) / 1000.0
    g = np.clip(1.0 - np.minimum(d, 10.0) / 10.0, 0, 1)
    im = Image.fromarray((g * 255).astype(np.uint8)).convert("RGB").resize((w, round(w * d.shape[0] / d.shape[1])), Image.BILINEAR)
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, w, 20], fill=(20, 20, 20))
    dr.text((6, 3), label, fill=(255, 255, 255), font=font(13))
    return im


def contact_sheet(F, events, out_path):
    pad, head = 8, 54
    w3 = 900
    h3 = round(w3 * CANVAS[1] / CANVAS[0])
    w6 = (3 * w3 + 2 * pad - 5 * pad) // 6
    h6 = round(w6 * CANVAS[1] / CANVAS[0])
    Wd = 3 * w3 + 4 * pad
    Hd = head + (h3 + pad) * 2 + 4 * (h6 + pad) + 2 * 26 + pad
    sh = Image.new("RGB", (Wd, Hd), (244, 243, 240))
    d = ImageDraw.Draw(sh)
    d.text((pad, 8), "Warm-modern entrance, clay (structure only) and the T-E0 stations. render-agent 2026-11-14, 0 tokens. Canvas of base.png 2720 x 1530; "
                     "red box = the camera frame.", fill=(15, 15, 15), font=font(17))
    d.text((pad, 30), "Top: H0, H0x-a (shift 0.52 / 0.46), H0x-b (shift 0.47 / 0.50) with id and depth passes below. Then 12 stations, variant b (shift of M0) and "
                      "variant a (shift linear in the distance). Purple in the id pass = the dining room through O-living-dining.", fill=(60, 60, 60), font=font(13))
    y = head
    for i, fid in enumerate(("H0", "H0x-a", "H0x-b")):
        f = F[fid]
        sh.paste(tile(os.path.join(HERE, fid + ".png"), w3, f"{fid}   yaw {f['yaw']}   shift {f['u0']:.2f} / {f['v0']:.2f}"), (pad + i * (w3 + pad), y))
    y += h3 + pad
    wq = (w3 - pad) // 2
    hq = round(wq * CANVAS[1] / CANVAS[0])
    for i, fid in enumerate(("H0", "H0x-a", "H0x-b")):
        sh.paste(tile(os.path.join(HERE, fid + "-id.png"), wq, f"{fid} id"), (pad + i * (w3 + pad), y))
        sh.paste(depth_tile(os.path.join(HERE, fid + "-depth.png"), wq, f"{fid} depth (0-10 m)"), (pad + i * (w3 + pad) + wq + pad, y))
    y += max(hq, 0) + pad
    y = head + (h3 + pad) + hq + pad
    for var, title in (("b", "Stations, variant b: shift 0.47 / 0.50 throughout (S00 = H0x-b, S11 = M0)"),
                       ("a", "Stations, variant a: shift from 0.52 / 0.46 to 0.47 / 0.50, linear in the distance (S00 = H0x-a, S11 = M0)")):
        d.text((pad, y + 4), title, fill=(15, 15, 15), font=font(15))
        y += 26
        for k in range(12):
            fid = f"{var}/S{k:02d}"
            f = F[fid]
            dn = events[f"variant_{var}"]["dining_opening_in_frame"]["share_at_stations"][f"S{k:02d}"]
            sub = f"shift {f['u0']:.3f} / {f['v0']:.3f}" + (f"   dining opening {dn * 100:.1f} % of the width" if dn > 0 else "")
            t = tile(os.path.join(HERE, fid + ".png"), w6, f"S{k:02d}   s {f['s']:.2f} m", sub)
            sh.paste(t, (pad + (k % 6) * (w6 + pad), y + (k // 6) * (h6 + pad)))
        y += 2 * (h6 + pad)
    sh = sh.crop((0, 0, Wd, y + pad))
    sh.save(out_path, quality=88)
    return out_path


# ---------------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-sheet", action="store_true")
    ap.add_argument("--no-seam", action="store_true")
    a = ap.parse_args()
    F, PF = plan_frames()
    have = [fid for fid in F if os.path.exists(os.path.join(HERE, fid + "-id.png"))]
    PS = {fid: Passes(fid, F[fid]) for fid in have}
    sc_path = os.path.join(HERE, "selfcheck.json")
    old = json.load(open(sc_path)) if os.path.exists(sc_path) else {}
    rep = {}
    meta_p = os.path.join(SCRATCH, "meta.json")
    rep.update(json.load(open(meta_p)) if os.path.exists(meta_p) else {k: old[k] for k in old if k not in ("frames", "designer_values", "path", "verticals", "seam_M0", "summary")})
    frames = dict(old.get("frames", {}))
    for fid in F:
        p = os.path.join(SCRATCH, "frames", fid.replace("/", "_") + ".json")
        if os.path.exists(p):
            frames[fid] = json.load(open(p))
            frames[fid].pop("npz", None)
    for dst, src in (("a/S00", "H0x-a"), ("b/S00", "H0x-b"), ("a/S11", "b/S11")):
        if src in frames:
            frames[dst] = dict(frames[src], frame=dst, copy_of=src)
    rep["frames"] = {k: frames[k] for k in F if k in frames}
    rep["cameras"] = {k: dict(loc=[r4(x) for x in v["loc"]], yaw=v["yaw"], lens=24, u0=round(v["u0"], 6), v0=round(v["v0"], 6), s_m=r4(v["s"])) for k, v in F.items()}
    rep["depth_pass"] = "16-bit PNG, value = planar depth (along the optical axis, the plan's d) in millimetres; 65535 = beyond 65.5 m or sky"
    rep["designer_values"] = table_designer(F, PF, PS)
    rep["path"] = path_events(PF)
    rep["verticals"] = verticals(PS)
    na = {k: v.get("not_allowed_px") for k, v in rep["frames"].items() if v.get("not_allowed_px")}
    osc = {k: v.get("outside_scope_px") for k, v in rep["frames"].items() if v.get("outside_scope_px")}
    seam_res = None
    if not a.no_seam and "b/S11" in PS:
        rep["seam_M0"], seam_res = seam(PS, F)
    elif "seam_M0" in old:
        rep["seam_M0"] = old["seam_M0"]
    rep["summary"] = dict(
        frames_rendered=len([k for k in rep["frames"]]), camera_vs_plan_projection_max=max((v.get("camera_vs_plan_projection_max_px_or_mm", 0) for v in rep["frames"].values()), default=None),
        frames_with_not_allowed_surfaces=na, frames_showing_the_dining_room_px=osc,
        verticals_worst_spread_px=rep["verticals"]["worst_spread_px"],
        designer_values_flagged=[r["key"] for r in rep["designer_values"] if r["flag"]])
    json.dump(rep, open(sc_path, "w"), indent=1, ensure_ascii=False)
    if not a.no_sheet and all(os.path.exists(os.path.join(HERE, fid + ".png")) for fid in F):
        contact_sheet(F, rep["path"], os.path.join(HERE, "contact-sheet.jpg"))
    print(json.dumps(rep["summary"], indent=1, ensure_ascii=False))
    return rep, seam_res


if __name__ == "__main__":
    main()
