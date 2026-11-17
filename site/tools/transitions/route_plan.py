#!/usr/bin/env python3
"""
route_plan.py: the owner's route drawing (docs/proposals/wm-tour-route-2026-11-17.md, chapter 6), drawn from
docs/house-plan.json (1.1 geometry, never from docs/proposals/house-plan/). motion-agent, 2026-11-17. 0 var2 tokens.

North up (-X up, -Y to the right): the court and the door at the bottom, the living room top right, the rooms on the
left. Rooms as outlines with their names, openings as gaps with their ids (hidden leaves dashed), windows as a double
hairline, the two light slots dotted, the stations 1-10 with their rest cones (the real frame edges of each camera,
lens 24 and its shift), the route (solid = forward, dashed with chevrons = retreat or slide, the face toward the heart
of the house), the buttons of each station, and the status colours of chapter 6.6.

Sources other than house-plan.json (the plan's 1.3.6 text does not carry them yet):
  - the hall's light slot of the warm-modern entrance (X 0.80-1.10, Y 6.35-9.80), from the final entrance clay
    (assets/blockout/house/framing_wm_door_final.py, SLOT; designer chapter 11);
  - HX, HT, MB-in and the arc of clip 2's take 2, from the route proposal (2.1, 2.6, 4.1).
A self-check runs first: every station inside its room, every opening's faces on room faces (or the outside),
every window on an exterior face. It prints a JSON and exits 2 if anything is off.

  python3 site/tools/transitions/route_plan.py --out docs/proposals/wm-tour-route-2026-11-17/route-plan.png
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PLAN = os.path.join(REPO, "docs", "house-plan.json")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
KU = 0.6667

BG, INK = "#ECE5DA", "#2E2824"
GREEN, ORANGE, BLUE, GREY = "#4E8A5B", "#D9822B", "#3F6FB5", "#A39C92"
W, H = 2400, 1500
SCALE = 92.0
Y_RIGHT, X_TOP = -0.35, -2.65
OX, OY = 2230.0, 160.0

NAMES = {"living": "סלון", "kitchen-dining": "מטבח ופינת אוכל", "hall": "מבואה", "work": "חדר עבודה", "corridor": "מסדרון",
         "boy": "חדר ילד", "girl": "חדר ילדה", "master": "חדר שינה", "bath": "רחצה", "laundry": "כביסה", "ensuite-wic": "רחצה וארון של חדר השינה",
         "court": "חצר כניסה"}
NOT_IN_TOUR = {"laundry", "ensuite-wic"}
HALL_SLOT = dict(x=(0.80, 1.10), y=(6.35, 9.80))


def P(x: float, y: float) -> tuple[float, float]:
    """Plan (X, Y) -> drawing pixels: north (-X) up, -Y to the right."""
    return OX - (y - Y_RIGHT) * SCALE, OY + (x - X_TOP) * SCALE


def ang(yaw: float) -> float:
    """PIL angle (degrees, clockwise from 3 o'clock) of a plan heading: yaw 0 -> right (east), 90 -> up (north)."""
    return -yaw


def fdir(yaw: float) -> tuple[float, float]:
    r = math.radians(yaw)
    return -math.sin(r), -math.cos(r)


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def text(d: ImageDraw.ImageDraw, xy, s: str, size: int = 18, fill: str = INK, bold: bool = False, anchor: str = "mm"):
    he = any("\u0590" <= ch <= "\u05ff" for ch in s)
    d.text(xy, s, font=font(size, bold), fill=fill, anchor=anchor, direction="rtl" if he else "ltr", language="he" if he else "en")


def dashed(d, p0, p1, fill, width=2, dash=10, gap=7):
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1e-6:
        return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    s = 0.0
    while s < L:
        e = min(L, s + dash)
        d.line([(x0 + ux * s, y0 + uy * s), (x0 + ux * e, y0 + uy * e)], fill=fill, width=width)
        s = e + gap


def dotted(d, p0, p1, fill, r=2.6, step=11):
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0)
    n = max(1, int(L / step))
    for k in range(n + 1):
        x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def arrowhead(d, tip, direction, fill, size=16):
    dx, dy = direction
    L = math.hypot(dx, dy) or 1.0
    dx, dy = dx / L, dy / L
    nx, ny = -dy, dx
    bx, by = tip[0] - dx * size, tip[1] - dy * size
    d.polygon([tip, (bx + nx * size * 0.45, by + ny * size * 0.45), (bx - nx * size * 0.45, by - ny * size * 0.45)], fill=fill)


def chevron(d, at, direction, fill, size=11, width=3):
    dx, dy = direction
    L = math.hypot(dx, dy) or 1.0
    dx, dy = dx / L, dy / L
    nx, ny = -dy, dx
    tip = at
    a = (at[0] - dx * size + nx * size * 0.8, at[1] - dy * size + ny * size * 0.8)
    b = (at[0] - dx * size - nx * size * 0.8, at[1] - dy * size - ny * size * 0.8)
    d.line([a, tip, b], fill=fill, width=width)


# ----------------------------------------------------------------------------------------------------------------
def load():
    plan = json.load(open(PLAN))
    rooms = {r["id"]: dict(x=r["x"], y=r["y"]) for r in plan["rooms"]}
    rooms["court"] = dict(x=plan_porch(plan)["x"], y=plan_porch(plan)["y"])
    cams = {c["id"]: c for c in plan["cameras"]}
    return plan, rooms, cams


def plan_porch(plan):
    for k, v in plan.items():
        if isinstance(v, dict) and "porch" in v:
            return v["porch"]
    raise SystemExit("house-plan.json: no 'porch' (the entrance court)")


def opening_rect(o):
    if "plane_x" in o:
        return (o["plane_x"][0], o["plane_x"][1]), (o["y"][0], o["y"][1]), "x"
    return (o["x"][0], o["x"][1]), (o["plane_y"][0], o["plane_y"][1]), "y"


def inside(r, x, y, tol=1e-6):
    return r["x"][0] - tol <= x <= r["x"][1] + tol and r["y"][0] - tol <= y <= r["y"][1] + tol


def selfcheck(plan, rooms, stations, points) -> dict:
    out = dict(stations={}, openings={}, windows={})
    for sid, (room, x, y) in list(stations.items()) + list(points.items()):
        out["stations"][sid] = dict(room=room, inside=bool(inside(rooms[room], x, y)))
    faces_x = {}
    for rid, r in rooms.items():
        for xv in r["x"]:
            faces_x.setdefault(round(xv, 3), []).append((rid, r["y"]))
    faces_y = {}
    for rid, r in rooms.items():
        for yv in r["y"]:
            faces_y.setdefault(round(yv, 3), []).append((rid, r["x"]))
    outer = plan["footprint"]["outer_bbox"]
    for o in plan["openings"]:
        (a0, a1), (b0, b1), axis = opening_rect(o)
        if axis == "x":
            hits = [rid for f in (a0, a1) for rid, ys in faces_x.get(round(f, 3), []) if ys[0] - 1e-6 <= b0 and b1 <= ys[1] + 1e-6]
        else:
            hits = [rid for f in (b0, b1) for rid, xs in faces_y.get(round(f, 3), []) if xs[0] - 1e-6 <= a0 and a1 <= xs[1] + 1e-6]
        out["openings"][o["id"]] = dict(on_faces_of=sorted(set(hits)), ok=len(set(hits)) >= 2 or (o["id"] == "O-front-door" and "hall" in hits and "court" in hits))
    for w in plan["windows"]:
        if "plane_x" in w:
            ok = any(abs(w["plane_x"] - r["x"][0]) < 1e-6 and r["y"][0] - 1e-6 <= w["y"][0] and w["y"][1] <= r["y"][1] + 1e-6 for r in rooms.values())
        elif "plane_y" in w:
            ok = any(abs(w["plane_y"] - r["y"][0]) < 1e-6 and r["x"][0] - 1e-6 <= w["x"][0] and w["x"][1] <= r["x"][1] + 1e-6 for r in rooms.values())
        else:
            ok = None
        out["windows"][w["id"]] = ok
    out["outer_bbox"] = outer
    out["pass"] = all(v["inside"] for v in out["stations"].values()) and all(v["ok"] for v in out["openings"].values()) and \
        all(v is not False for v in out["windows"].values())
    return out


# ----------------------------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=os.path.join(REPO, "docs", "proposals", "wm-tour-route-2026-11-17", "route-plan.png"))
    a = ap.parse_args(argv)
    plan, rooms, cams = load()

    # stations 1-10 (chapter 6.3): plan point, rest yaw and shift of the rest frame
    def cam(cid):
        c = cams[cid]
        return c["loc"][0], c["loc"][1], c["yaw_deg_left"], c.get("u0", 0.5)
    st = [
        (1, "D0", "court", 7.40, 8.15, 90.0, 0.36, "הדלת"),
        (2, "HX", "hall", 2.462, 8.15, 25.0, 0.47, "הצומת"),
        (3, "M0", "living", *cam("M0"), "סלון"),
        (4, "PD", "kitchen-dining", *cam("D1"), "מטבח ופינת אוכל"),
        (5, "C0", "corridor", *cam("C0"), "מסדרון"),
        (6, "K-boy", "boy", *cam("K-boy"), "חדר ילד"),
        (7, "K-girl", "girl", *cam("K-girl"), "חדר ילדה"),
        (8, "CB", "bath", *cam("B1"), "רחצה"),
        (9, "MB0", "master", *cam("MB0"), "חדר שינה"),
        (10, "W0", "work", *cam("W0"), "חדר עבודה"),
    ]
    points = {"HT": ("hall", 3.60, 8.15), "S1'": ("corridor", 2.641, 13.00), "MB-in": ("master", 2.45, 21.05), "H0": ("hall", 2.877, 9.039)}
    chk = selfcheck(plan, rooms, {s[1]: (s[2], s[3], s[4]) for s in st}, points)
    print(json.dumps(chk, ensure_ascii=False, indent=1))
    if not chk["pass"]:
        print("route_plan: the self-check failed; nothing drawn", file=sys.stderr)
        return 2

    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im, "RGBA")

    # 1 rooms
    for rid, r in rooms.items():
        x0, y0 = P(r["x"][0], r["y"][1])
        x1, y1 = P(r["x"][1], r["y"][0])
        col = GREY if rid in NOT_IN_TOUR else INK
        if rid == "court":
            # open to the south (+X): three sides
            for p0, p1 in ((P(r["x"][0], r["y"][0]), P(r["x"][0], r["y"][1])), (P(r["x"][0], r["y"][0]), P(r["x"][1], r["y"][0])),
                           (P(r["x"][0], r["y"][1]), P(r["x"][1], r["y"][1]))):
                d.line([p0, p1], fill=col, width=3)
            dashed(d, P(r["x"][1], r["y"][0]), P(r["x"][1], r["y"][1]), GREY, 2)
        else:
            d.rectangle([x0, y0, x1, y1], outline=col, width=3)
    # 2 openings: a gap in both faces, jamb lines, the id; hidden leaves and closed doors dashed
    for o in plan["openings"]:
        (a0, a1), (b0, b1), axis = opening_rect(o)
        if axis == "x":
            p0, p1 = P(a0 - 0.012, b1), P(a1 + 0.012, b0)
            j = [(P(a0, b0), P(a1, b0)), (P(a0, b1), P(a1, b1))]
            mid = P((a0 + a1) / 2, (b0 + b1) / 2)
            span = (P((a0 + a1) / 2, b0), P((a0 + a1) / 2, b1))
        else:
            p0, p1 = P(a0, b1 + 0.012), P(a1, b0 - 0.012)
            j = [(P(a0, b0), P(a0, b1)), (P(a1, b0), P(a1, b1))]
            mid = P((a0 + a1) / 2, (b0 + b1) / 2)
            span = (P(a0, (b0 + b1) / 2), P(a1, (b0 + b1) / 2))
        d.rectangle([min(p0[0], p1[0]) - 2, min(p0[1], p1[1]) - 2, max(p0[0], p1[0]) + 2, max(p0[1], p1[1]) + 2], fill=BG)
        hidden = o["id"] in ("O-hall-work", "O-corridor-laundry")
        for q0, q1 in j:
            d.line([q0, q1], fill=INK, width=2)
        if hidden:
            dashed(d, span[0], span[1], INK, 2, 7, 5)
        lab = o["id"].replace("O-", "")
        off = (0, -16) if axis == "y" else (16, 0)
        d.text((mid[0] + off[0], mid[1] + off[1]), lab, font=font(12), fill="#6B625A", anchor="mm")
    # 3 windows: a double hairline on the exterior wall (warm-modern living window per style_shells_1_3_1)
    wm_living = plan.get("style_shells_1_3_1", {}).get("warm-modern", {}).get("living", {}).get("W-living", {})
    for w in plan["windows"]:
        if "plane_x" in w:
            ys = wm_living.get("y", w["y"]) if w["id"] == "W-living" else w["y"]
            xo = w["plane_x"] - 0.35 if w["plane_x"] < 0 else w["plane_x"] + 0.35
            for xx in (w["plane_x"] + (xo - w["plane_x"]) * 0.3, w["plane_x"] + (xo - w["plane_x"]) * 0.7):
                d.line([P(xx, ys[0]), P(xx, ys[1])], fill=INK, width=1)
            d.line([P(w["plane_x"], ys[0]), P(xo, ys[0])], fill=INK, width=1)
            d.line([P(w["plane_x"], ys[1]), P(xo, ys[1])], fill=INK, width=1)
        elif "plane_y" in w:
            t = w.get("wall_t", 0.35)
            yo = w["plane_y"] - t if w["plane_y"] <= 0.01 else w["plane_y"] + t * (1 if w["plane_y"] > 9 else -1)
            for yy in (w["plane_y"] + (yo - w["plane_y"]) * 0.3, w["plane_y"] + (yo - w["plane_y"]) * 0.7):
                d.line([P(w["x"][0], yy), P(w["x"][1], yy)], fill=INK, width=1)
    # 4 light slots, dotted
    for (x0, x1), (y0, y1) in ((HALL_SLOT["x"], HALL_SLOT["y"]), tuple((r["x"], r["y"]) for r in plan["roof_lights"] if r["id"] == "RL-corridor")[0]):
        for xx in (x0, x1):
            dotted(d, P(xx, y0), P(xx, y1), "#B08A4E")
    # 5 the route
    def seg(pts, col, kind="fwd", width=5):
        q = [P(*p) for p in pts]
        if kind == "fwd":
            d.line(q, fill=col, width=width, joint="curve")
            arrowhead(d, q[-1], (q[-1][0] - q[-2][0], q[-1][1] - q[-2][1]), col, 20)
        else:
            for k in range(len(q) - 1):
                dashed(d, q[k], q[k + 1], col, 4, 14, 9)
            # chevrons pointing back: toward where the camera faces (the heart of the house)
            L = sum(math.hypot(q[k + 1][0] - q[k][0], q[k + 1][1] - q[k][1]) for k in range(len(q) - 1))
            for frac in (0.3, 0.7):
                s, acc = frac * L, 0.0
                for k in range(len(q) - 1):
                    l = math.hypot(q[k + 1][0] - q[k][0], q[k + 1][1] - q[k][1])
                    if acc + l >= s:
                        t = (s - acc) / l
                        at = (q[k][0] + (q[k + 1][0] - q[k][0]) * t, q[k][1] + (q[k + 1][1] - q[k][1]) * t)
                        chevron(d, at, (q[k][0] - q[k + 1][0], q[k][1] - q[k + 1][1]), col)
                        break
                    acc += l

    def tag(p, s, col=INK, off=(0, 0)):
        x, y = P(*p)
        text(d, (x + off[0], y + off[1]), s, 13, col, True)

    HX, HT, D0, M0 = (2.462, 8.15), (3.60, 8.15), (7.40, 8.15), (0.83, 4.64)
    seg([D0, HT], ORANGE)
    seg([HT, HX], GREEN)
    tag(((5.5), 8.15), "T-D0 · 1a", ORANGE, (0, 18))
    tag((3.03, 8.15), "1b", GREEN, (-22, 0))
    seg([HX, M0], GREEN)
    # the arc of take 2 (2.6): 0.25 m toward the window at mid-way
    dx, dy = M0[0] - HX[0], M0[1] - HX[1]
    L = math.hypot(dx, dy)
    nx, ny = dy / L, -dx / L
    if nx > 0:
        nx, ny = -nx, -ny
    arc = [(HX[0] + dx * t + 0.25 * math.sin(math.pi * t) * nx, HX[1] + dy * t + 0.25 * math.sin(math.pi * t) * ny) for t in [k / 24 for k in range(25)]]
    seg(arc, BLUE, "fwd", 3)
    tag((1.95, 6.85), "T-E0 · קליפ 2", GREEN, (-10, 22))
    tag((1.02, 6.70), "טייק 2 בקשת", BLUE, (0, -4))
    seg([M0, (2.80, 3.80)], GREY)
    tag((1.85, 4.15), "T-LD", GREY, (0, -16))
    seg([M0, (1.62, 6.35), HX], GREEN, "back", 3)
    seg([HX, (2.43, 12.0), (2.397, 17.11)], GREY, "back")
    tag((2.43, 12.4), "T-HC", GREY, (-30, 0))
    seg([(2.397, 17.11), (2.641, 13.00)], GREY, "back", 3)
    seg([(2.641, 13.00), (1.10, 13.00)], GREY, "back", 3)
    seg([(2.641, 13.00), (3.80, 13.20)], GREY, "back", 3)
    tag((1.85, 13.0), "T-CBoy", GREY, (0, -16))
    tag((3.25, 13.1), "T-CBath", GREY, (0, -16))
    seg([(2.397, 17.11), (1.10, 16.63)], GREY, "back", 3)
    tag((1.75, 16.85), "T-CGirl", GREY, (0, 18))
    seg([(2.397, 17.11), (2.45, 21.05)], GREY, "back", 3)
    seg([(2.45, 21.05), (-0.70, 21.05)], GREY, "back", 3)
    tag((2.42, 19.4), "T-CM", GREY, (-26, 0))
    seg([HX, (0.72, 8.55), (-0.825, 9.85)], GREY, "back", 3)
    tag((0.05, 9.1), "T-HW", GREY, (0, -16))

    # 6 cones (the real frame edges at lens 24 and the shift), stations, points
    def cone(x, y, yaw, u0, col, dash=False, length=1.2, alpha=48):
        left = yaw + math.degrees(math.atan(u0 / KU))
        right = yaw - math.degrees(math.atan((1 - u0) / KU))
        c = P(x, y)
        pts = [c]
        for k in range(17):
            yy = left + (right - left) * k / 16
            f = fdir(yy)
            pts.append(P(x + f[0] * length, y + f[1] * length))
        if dash:
            dashed(d, pts[0], pts[1], col, 2, 8, 6)
            dashed(d, pts[0], pts[-1], col, 2, 8, 6)
            for k in range(1, len(pts) - 1):
                if k % 2:
                    d.line([pts[k], pts[k + 1]], fill=col, width=2)
        else:
            rgb = tuple(int(col[i:i + 2], 16) for i in (1, 3, 5))
            d.polygon(pts, fill=rgb + (alpha,), outline=col)

    status = {"D0": GREEN, "HX": BLUE, "M0": GREEN}
    for n, sid, room, x, y, yaw, u0, he in st:
        col = status.get(sid, GREY)
        cone(x, y, yaw, u0, col)
    cone(2.462, 8.15, 180.0, 0.50, BLUE, dash=True)
    cone(2.462, 8.15, 90.0, 0.36, GREEN, dash=True)
    cone(0.83, 4.64, -35.0, 0.52, INK, dash=True, length=1.6)
    # the look-around at HX: 90 deg to the left (to the corridor), then about 155 deg to the right (to the living room)
    cx, cy = P(*HX)
    for r_m, a0, a1, col in ((0.55, 90.0, 180.0, BLUE), (0.72, 180.0, 25.0, BLUE)):
        r = r_m * SCALE
        lo, hi = sorted((ang(a0), ang(a1)))
        d.arc([cx - r, cy - r, cx + r, cy + r], lo, hi, fill=col, width=3)
        e = math.radians(ang(a1))
        tip = (cx + r * math.cos(e), cy + r * math.sin(e))
        sgn = 1 if a1 > a0 else -1                     # yaw grows -> the PIL angle falls (counter-clockwise on screen)
        tang = (math.sin(e) * sgn, -math.cos(e) * sgn)
        arrowhead(d, tip, tang, col, 14)
    for n, sid, room, x, y, yaw, u0, he in st:
        col = status.get(sid, GREY)
        cx, cy = P(x, y)
        d.ellipse([cx - 17, cy - 17, cx + 17, cy + 17], fill=col, outline=INK, width=2)
        d.text((cx, cy), str(n), font=font(17, True), fill="white", anchor="mm")
    for pid, (room, x, y) in points.items():
        cx, cy = P(x, y)
        col = GREY if pid == "H0" else (GREEN if pid == "HT" else GREY)
        d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=col, outline=INK, width=1)
    text(d, (P(*points["HT"][1:])[0] + 52, P(*points["HT"][1:])[1]), "HT · HT2", 14, INK)
    text(d, (P(2.641, 13.0)[0] + 36, P(2.641, 13.0)[1] + 18), "S1'", 13, "#6B625A")
    text(d, (P(2.45, 21.05)[0], P(2.45, 21.05)[1] + 22), "MB-in", 13, "#6B625A")
    text(d, (P(2.877, 9.039)[0] - 190, P(2.877, 9.039)[1] + 60), "H0: בתוכנית, לא בסיור", 13, "#6B625A")
    d.line([P(2.877, 9.039), (P(2.877, 9.039)[0] - 120, P(2.877, 9.039)[1] + 52)], fill="#8E857B", width=1)

    # 7 room names
    for rid, r in rooms.items():
        cx, cy = P((r["x"][0] + r["x"][1]) / 2, (r["y"][0] + r["y"][1]) / 2)
        off = {"hall": (104, 106), "living": (90, -150), "kitchen-dining": (0, 140), "corridor": (-162, 40), "court": (70, -95), "work": (84, 70),
               "boy": (0, -70), "girl": (0, -70), "master": (67, 65), "bath": (40, 70)}.get(rid, (0, 0))
        col = GREY if rid in NOT_IN_TOUR else INK
        text(d, (cx + off[0], cy + off[1]), NAMES.get(rid, rid), 24 if rid not in NOT_IN_TOUR else 17, col, True)
        if rid in NOT_IN_TOUR:
            text(d, (cx + off[0], cy + off[1] + 22), "לא בסיור", 15, GREY)
    # 8 buttons of each station (2.5 and chapter 5), small
    buttons = {
        "D0": (["היכנסו ↑"], (70, 40)),
        "HX": (["סלון ↑", "חדרי השינה והרחצה ↶", "חדר העבודה ↰"], (-330, 560)),
        "M0": (["מטבח ופינת אוכל →", "מבואה ↓"], (-30, 105)),
        "PD": (["סלון ↓"], (0, 58)),
        "C0": (["מבואה ↑ · חדר ילד ← · רחצה → · חדר ילדה ← · חדר שינה ↓"], (-150, 118)),
        "K-boy": (["מסדרון ↓"], (0, 50)), "K-girl": (["מסדרון ↓"], (0, 50)), "CB": (["מסדרון ↓"], (0, 50)),
        "MB0": (["מסדרון →"], (0, 50)), "W0": (["מבואה →"], (0, 52)),
    }
    for n, sid, room, x, y, yaw, u0, he in st:
        lst, off = buttons[sid]
        cx, cy = P(x, y)
        bx, by = cx + off[0], cy + off[1]
        if sid in ("HX", "C0"):
            d.line([(cx, cy), (bx, by)], fill="#8E857B", width=1)
        h = 18 * len(lst) + 10
        wmax = max(d.textlength(s, font=font(14), direction="rtl", language="he") for s in lst) + 16
        d.rounded_rectangle([bx - wmax / 2, by - h / 2, bx + wmax / 2, by + h / 2], 6, fill=(255, 255, 255, 170), outline="#B9B0A4")
        for k, s in enumerate(lst):
            text(d, (bx, by - h / 2 + 14 + 18 * k), s, 14, INK)
    # 9 the two notes
    text(d, (P(0.83, 4.64)[0] + 235, P(0.83, 4.64)[1] + 118), "M0x: מכאן רואים את פינת האוכל", 15, INK)
    text(d, (P(*HX)[0] - 330, P(*HX)[1] + 488), "הצומת: ציר הדלת, הדרך לסלון וציר המסדרון", 16, INK, True)
    # 10 title, date, legend (right to left)
    text(d, (W - 60, 52), "הסיור בבית המודרני החם: המסלול המוצע", 40, INK, True, anchor="rm")
    text(d, (W - 60, 102), "17.11.2026 · מתוך תוכנית הבית 1.3.6 · צפון למעלה · 0 טוקנים", 18, "#6B625A", anchor="rm")
    ly = 1270
    items = [
        ("line", INK, "הולכים קדימה"), ("back", INK, "נסיגה או החלקה, הפנים אל לב הבית"),
        ("dot", GREEN, "רונדר ועבר QA"), ("dot", ORANGE, "רונדר, מחכה ל-QA (קליפ 1a)"), ("dot", BLUE, "חדש להגעה"), ("dot", GREY, "בהמשך"),
        ("cone", INK, "מה רואים במנוחה (הפריים, עדשה 24)"), ("dcone", INK, "מבט נוסף מאותה נקודה"),
        ("slot", "#B08A4E", "חריץ אור"), ("win", INK, "חלון"), ("hid", INK, "כנף נסתרת או סגורה"),
    ]
    x = W - 60
    row = 0
    for kind, col, s in items:
        tw = d.textlength(s, font=font(17), direction="rtl", language="he")
        need = tw + 70
        if x - need < 60:
            row += 1
            x = W - 60
        y = ly + row * 46
        sx = x - 30
        if kind == "line":
            d.line([(sx - 22, y), (sx + 22, y)], fill=col, width=5)
            arrowhead(d, (sx - 24, y), (-1, 0), col, 14)
        elif kind == "back":
            dashed(d, (sx - 24, y), (sx + 24, y), col, 4, 9, 6)
            chevron(d, (sx + 6, y), (1, 0), col)
        elif kind == "dot":
            d.ellipse([sx - 13, y - 13, sx + 13, y + 13], fill=col, outline=INK, width=2)
        elif kind in ("cone", "dcone"):
            pts = [(sx + 22, y + 10), (sx - 22, y - 8), (sx - 22, y + 28)]
            if kind == "cone":
                d.polygon(pts, fill=(46, 40, 36, 40), outline=col)
            else:
                dashed(d, pts[0], pts[1], col, 2, 6, 4)
                dashed(d, pts[0], pts[2], col, 2, 6, 4)
        elif kind == "slot":
            dotted(d, (sx - 24, y), (sx + 24, y), col)
        elif kind == "win":
            d.line([(sx - 24, y - 3), (sx + 24, y - 3)], fill=col, width=1)
            d.line([(sx - 24, y + 3), (sx + 24, y + 3)], fill=col, width=1)
        elif kind == "hid":
            dashed(d, (sx - 24, y), (sx + 24, y), col, 2, 7, 5)
        text(d, (sx - 40, y), s, 17, INK, anchor="rm")
        x = sx - 40 - tw - 50
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    im.save(a.out, optimize=True)
    print("wrote", a.out, im.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
