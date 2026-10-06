#!/usr/bin/env python3
"""Draw the proposed house plan from docs/proposals/house-plan.json (0 credits).

Outputs (next to this script): plan.png, plan-walk.png, clay-axo.png
Plan orientation per the JSON conventions: -Y (east) up, -X (north) left.
Run:  python3 draw_plan.py      (needs matplotlib, python-bidi)
"""
import json, math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Arc, FancyArrowPatch, Circle
from matplotlib import patheffects as pe
try:
    from bidi.algorithm import get_display
except ImportError:
    get_display = lambda s: s

HERE = os.path.dirname(os.path.abspath(__file__))
J = json.load(open(os.path.join(HERE, "..", "house-plan.json"), encoding="utf-8"))
plt.rcParams["font.family"] = "DejaVu Sans"

def he(s):
    # matplotlib 3.11 (verified here) applies the bidi algorithm itself; feeding it
    # python-bidi output reverses the text twice. Older versions need python-bidi.
    if NATIVE_BIDI:
        return s
    return get_display(s)


NATIVE_BIDI = tuple(int(v) for v in matplotlib.__version__.split(".")[:2]) >= (3, 11)
ROOMS = {r["id"]: r for r in J["rooms"]}
OPEN = {o["id"]: o for o in J["openings"]}
CAMS = {c["id"]: c for c in J["cameras"]}

# palette
WALL = "#2b2b2b"
MAMAD = "#4a4a4a"
FLOOR = "#ffffff"
LIVING = "#f4e9cf"
NOBUILD = "#eeeeee"
PORCH = "#e8efe4"
GLASS = "#7fb3d5"
INK = "#222222"
MUTED = "#777777"
BG = "#fbfaf7"

XL, XR = -4.2, 9.0   # page left/right  (X)
YT, YB = -2.6, 23.6  # page top/bottom  (Y)

def heading(yaw):
    a = math.radians(yaw)
    return (-math.sin(a), -math.cos(a))


def new_fig(extra_bottom_in=0.0, title=""):
    W_in = 12.0
    ppm = W_in / (XR - XL)          # inches per metre
    plan_h = (YB - YT) * ppm
    head = 1.0
    H_in = head + plan_h + extra_bottom_in
    fig = plt.figure(figsize=(W_in, H_in), dpi=200, facecolor=BG)
    ax = fig.add_axes([0, (extra_bottom_in) / H_in, 1, plan_h / H_in])
    ax.set_xlim(XL, XR)
    ax.set_ylim(YB, YT)  # inverted: +Y down, -Y (east) up
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor(BG)
    fig.text(0.97, 1 - 0.45 / H_in, he(title), ha="right", va="center", fontsize=26, weight="bold", color=INK)
    fig.text(0.97, 1 - 0.85 / H_in,
             he("הצעה (גרסה " + J["version"].split()[0] + "), הפתח סלון-אוכל מאושר. מידות פנים במטרים, לפי house-plan.json"),
             ha="right", va="center", fontsize=12, color=MUTED)
    return fig, ax, H_in


def rect(ax, x, y, **kw):
    ax.add_patch(Rectangle((x[0], y[0]), x[1] - x[0], y[1] - y[0], **kw))


def draw_base(ax, faded=False):
    a = 0.55 if faded else 1.0
    fp = J["footprint"]
    # porch (outside)
    p = fp["porch"]
    rect(ax, p["x"], p["y"], facecolor=PORCH, edgecolor="#9db08f", lw=1, hatch="///", alpha=a, zorder=1)
    # garden strip along north
    ax.text(-3.35, 11.0, he("גינה (צפון)"), rotation=90, ha="center", va="center", fontsize=16,
            color="#6d8f5e", alpha=a, zorder=1)
    # wall mass = outer blocks (+ bath east wall strip, missing from the JSON blocks, see README)
    for b in fp["outer_blocks"]:
        rect(ax, b["x"], b["y"], facecolor=WALL, edgecolor="none", alpha=a, zorder=2)
    rect(ax, [3.60, 6.60], [9.80, 9.95], facecolor=WALL, edgecolor="none", alpha=a, zorder=2)
    # mamad walls: slightly different tone
    m = ROOMS["work-mamad"]
    rect(ax, [m["x"][0] - 0.0, m["x"][1] + 0.30], [m["y"][0] - 0.30, m["y"][1] + 0.30],
         facecolor=MAMAD, edgecolor="none", alpha=a, zorder=2.1)
    # rooms
    for r in J["rooms"]:
        fc = FLOOR
        if r["id"] == "living":
            fc = LIVING
        elif not r.get("build", True):
            fc = NOBUILD
        rect(ax, r["x"], r["y"], facecolor=fc, edgecolor="none", zorder=3)
    # re-draw walls that the mamad patch covered inside rooms (rooms on top already)
    # openings
    for o in J["openings"]:
        draw_opening(ax, o)
    # windows
    for w in J["windows"]:
        draw_window(ax, w)
    # living room highlight frame
    L = ROOMS["living"]
    rect(ax, L["x"], L["y"], facecolor="none", edgecolor="#c9a227", lw=4, zorder=6)


def draw_opening(ax, o):
    oid = o["id"]
    closed = "closed" in o["type"]
    if "plane_y" in o:
        y0, y1 = o["plane_y"]
        x0, x1 = o["x"]
        if y1 - y0 < 1e-6:
            return  # hall-corridor: no wall there at all
        rect(ax, [x0, x1], [y0 - 0.01, y1 + 0.01], facecolor=FLOOR, edgecolor="none", zorder=4)
        if closed:
            ax.plot([x0, x1], [(y0 + y1) / 2] * 2, color=INK, lw=3, zorder=5)
        span_axis = "x"
    else:
        x0, x1 = o["plane_x"]
        y0, y1 = o["y"]
        rect(ax, [x0 - 0.01, x1 + 0.01], [y0, y1], facecolor=FLOOR, edgecolor="none", zorder=4)
        if closed:
            ax.plot([(x0 + x1) / 2] * 2, [y0, y1], color=INK, lw=3, zorder=5)
        span_axis = "y"
    # door swings (open doors): (hinge point, closed-leaf direction, open-leaf direction)
    sw = DOOR_SWINGS.get(oid)
    if sw:
        for (hx, hy), w, t1, t2, a1 in sw:
            ax.add_patch(Arc((hx, hy), 2 * w, 2 * w, theta1=t1, theta2=t2,
                             color=MUTED, lw=1.0, ls="--", zorder=5))
            ax.plot([hx, hx + w * math.cos(math.radians(a1))], [hy, hy + w * math.sin(math.radians(a1))],
                    color=INK, lw=2.0, zorder=5)
    # front door: solid leaf + label
    if oid == "O-front-door":
        pass


# Door swing sketches: (hinge, leaf width, arc theta1, arc theta2, open-leaf angle). Data-space angles:
# 0 = +X (south), 90 = +Y (west); the axis is drawn with +Y down.
DOOR_SWINGS = {
    "O-entry-living": [((0.95, 6.35), 0.60, 0, 90, 90), ((2.15, 6.35), 0.60, 90, 180, 90)],
    "O-living-dining": [((2.65, 2.97), 0.80, 0, 90, 0), ((2.65, 4.57), 0.80, 270, 360, 0)],
    # opens out into the hall, hinge on the west jamb (Y 8.24), leaf parks along the hall wall toward +Y
    "O-hall-mamad": [((0.80, 8.24), 0.80, 270, 450, 90)],
    "O-corridor-boy": [((1.55, 13.63), 0.90, 180, 270, 180)],
    "O-corridor-girl": [((1.55, 17.27), 0.90, 180, 270, 180)],
    "O-corridor-bath": [((3.25, 13.49), 1.00, 270, 360, 0)],
    "O-corridor-master": [((2.78, 17.66), 0.90, 90, 180, 90)],
    "O-master-ensuite": [((3.25, 20.60), 0.90, 270, 360, 0)],
}


def draw_window(ax, w):
    if "plane_x" in w:
        x = w["plane_x"]
        y0, y1 = w["y"]
        rect(ax, [x - 0.35, x], [y0, y1], facecolor=FLOOR, edgecolor="none", zorder=4)
        for xx in (x - 0.35, x - 0.175, x):
            ax.plot([xx, xx], [y0, y1], color=GLASS if xx == x - 0.175 else INK, lw=2.5 if xx == x - 0.175 else 1.2, zorder=5)
        ax.plot([x - 0.35, x], [y0, y0], color=INK, lw=1.2, zorder=5)
        ax.plot([x - 0.35, x], [y1, y1], color=INK, lw=1.2, zorder=5)
    elif "plane_y" in w:
        y = w["plane_y"]
        x0, x1 = w["x"]
        t = 0.35 if y <= 0.01 else 0.15
        yo = y - t
        rect(ax, [x0, x1], [yo, y], facecolor=FLOOR, edgecolor="none", zorder=4)
        for yy in (yo, (yo + y) / 2, y):
            mid = abs(yy - (yo + y) / 2) < 1e-9
            ax.plot([x0, x1], [yy, yy], color=GLASS if mid else INK, lw=2.5 if mid else 1.2, zorder=5)
        ax.plot([x0, x0], [yo, y], color=INK, lw=1.2, zorder=5)
        ax.plot([x1, x1], [yo, y], color=INK, lw=1.2, zorder=5)


LABELS = {
    # id: (offset in m from centre, font scale)
    "living": (0, 0, 1.0),
    "kitchen-dining": (0, 0, 1.0),
    "hall": (0, -0.35, 0.8),
    "work-mamad": (0, 0, 0.8),
    "corridor": (0, 0, 0.75),
    "boy": (0, 0, 1.0),
    "girl": (0, 0, 1.0),
    "master": (0, 0, 1.0),
    "bath": (0, 0, 0.9),
    "laundry": (0, 0, 0.6),
    "ensuite-wic": (0, 0, 0.8),
}


def room_labels(ax, faded=False, positions=None):
    for r in J["rooms"]:
        cx = (r["x"][0] + r["x"][1]) / 2
        cy = (r["y"][0] + r["y"][1]) / 2
        dx, dy, s = LABELS.get(r["id"], (0, 0, 1))
        if positions and r["id"] in positions:
            cx, cy = positions[r["id"]]
        else:
            cx += dx; cy += dy
        W = r["x"][1] - r["x"][0]
        D = r["y"][1] - r["y"][0]
        area = W * D
        col = INK if r.get("build", True) else MUTED
        alpha = 0.55 if faded else 1.0
        name = r["name_he"]
        if r["id"] == "corridor" and positions and "corridor" not in positions:
            continue
        if r["id"] == "corridor":
            ax.text(cx, cy, he(name), rotation=90, ha="center", va="center", fontsize=15 * s * 1.3,
                    weight="bold", color=col, alpha=alpha, zorder=7)
            ax.text(cx + 0.42, cy, f"1.40 × 7.71   ·   {area:.1f} " + he("מ\"ר"), rotation=90, ha="center",
                    va="center", fontsize=10, color=col, alpha=alpha, zorder=7)
            continue
        lines = [(he(name), 17 * s, "bold")]
        lines.append((f"{W:.2f} × {D:.2f}", 12 * s, "normal"))
        lines.append((he(f"{area:.1f} מ\"ר"), 12 * s, "normal"))
        if r["id"] == "living":
            lines.append((he("מאושר, ללא שינוי"), 12, "bold"))
        if not r.get("build", True):
            lines.append((he("(לא נבנה)" if r["id"] == "laundry" else "(אדריכלות בלבד, לא נבנה)"), 9 if r["id"] == "laundry" else 10, "normal"))
        if r["id"] == "work-mamad":
            lines.append((he("קירות בטון 0.30"), 10, "normal"))
        step = 0.42
        y = cy - step * (len(lines) - 1) / 2
        for txt, fs, wt in lines:
            c = "#8a6d0b" if (r["id"] == "living" and "מאושר" in get_display(txt)) else col
            ax.text(cx, y, txt, ha="center", va="center", fontsize=fs, weight=wt, color=c, alpha=alpha,
                    zorder=7, path_effects=[pe.withStroke(linewidth=3, foreground="white")])
            y += step
    # porch
    p = J["footprint"]["porch"]
    ax.text((p["x"][0] + p["x"][1]) / 2 + 0.25, (p["y"][0] + p["y"][1]) / 2 + 0.9,
            he("חצר כניסה מקורה") + "\n" + he("(חוץ)"), ha="center", va="center", fontsize=13,
            color="#4d6b40", zorder=7, path_effects=[pe.withStroke(linewidth=4, foreground=PORCH)])


def north_arrow(ax, x, y):
    # north = -X (left on the page), east = -Y (up)
    r = 0.7
    ax.add_patch(Circle((x, y), r, facecolor="white", edgecolor=INK, lw=1.2, zorder=8))
    ax.add_patch(Polygon([[x - r + 0.05, y], [x + 0.25, y - 0.2], [x + 0.25, y + 0.2]], closed=True,
                         facecolor=INK, zorder=9))
    ax.text(x - 0.2, y - 0.38, he("צפון"), ha="center", va="center", fontsize=13, weight="bold", zorder=9)
    ax.text(x, y - r - 0.1, he("מזרח"), ha="center", va="bottom", fontsize=11, color=MUTED, zorder=9)
    ax.text(x, y + r + 0.1, he("מערב"), ha="center", va="top", fontsize=11, color=MUTED, zorder=9)
    ax.text(x + r + 0.08, y + 0.45, he("דרום"), ha="center", va="center", fontsize=11, color=MUTED, zorder=9)


def scale_bar(ax, x, y):
    for i in range(5):
        rect(ax, [x + i, x + i + 1], [y, y + 0.18], facecolor=INK if i % 2 == 0 else "white",
             edgecolor=INK, lw=1, zorder=8)
    for i in range(6):
        ax.text(x + i, y + 0.35, str(i), ha="center", va="top", fontsize=11, zorder=8)
    ax.text(x + 5.35, y + 0.09, he("מ'"), ha="left", va="center", fontsize=12, zorder=8)


def overall_dims(ax):
    fp = J["footprint"]["outer_bbox"]
    x0, x1 = fp["x"]; y0, y1 = fp["y"]
    yy = y0 - 0.9
    ax.annotate("", (x0, yy), (x1, yy), arrowprops=dict(arrowstyle="<->", color=MUTED, lw=1), zorder=8)
    ax.text((x0 + x1) / 2, yy - 0.15, f"{x1 - x0:.2f} " + he("מ' (חוץ)"), ha="center", va="bottom",
            fontsize=11, color=MUTED)
    xx = x1 + 0.7
    ax.annotate("", (xx, y0), (xx, y1), arrowprops=dict(arrowstyle="<->", color=MUTED, lw=1), zorder=8)
    ax.text(xx + 0.15, (y0 + y1) / 2 + 4, f"{y1 - y0:.2f} " + he("מ' (חוץ)"), rotation=90, ha="left",
            va="center", fontsize=11, color=MUTED)


def legend_plan(fig, H_in, extra):
    items = [
        (WALL, "קיר"), (MAMAD, "קיר ממ\"ד (בטון 0.30)"), (GLASS, "חלון"),
        (LIVING, "סלון מאושר"), (NOBUILD, "חדר שלא נבנה (רק אדריכלות)"), (PORCH, "חוץ / חצר מקורה"),
    ]
    for i, (col, t) in enumerate(items):
        r, c = divmod(i, 3)
        x = 0.97 - c * 0.31
        y = (extra - 0.3 - r * 0.38) / H_in
        fig.text(x, y, "      ", ha="right", va="center", fontsize=12,
                 bbox=dict(boxstyle="square,pad=0.1", fc=col, ec=INK, lw=0.6))
        fig.text(x - 0.05, y, he(t), ha="right", va="center", fontsize=13)
    fig.text(0.97, (extra - 1.15) / H_in,
             he("דלת: קו שחור עבה = עלה הדלת, קשת מקווקוות = כיוון הפתיחה. קו שחור בתוך הקיר = דלת סגורה (כניסה ראשית, כביסה)."),
             ha="right", va="center", fontsize=11, color=MUTED)


def front_door_tag(ax):
    o = OPEN["O-front-door"]
    yc = sum(o["y"]) / 2
    ax.annotate("", (3.62, yc), (4.9, yc), arrowprops=dict(arrowstyle="-|>", color="#4d6b40", lw=2.5,
                                                            mutation_scale=22), zorder=8)
    ax.text(4.95, yc + 0.0, he("דלת הכניסה"), ha="left", va="center", fontsize=13, weight="bold",
            color="#4d6b40", zorder=8, path_effects=[pe.withStroke(linewidth=4, foreground=PORCH)])


# ---------------------------------------------------------------- plan.png
def make_plan():
    extra = 1.5
    fig, ax, H = new_fig(extra, "תוכנית הבית המוצעת")
    draw_base(ax)
    room_labels(ax)
    front_door_tag(ax)
    north_arrow(ax, 7.85, 17.5)
    scale_bar(ax, 2.5, 22.75)
    overall_dims(ax)
    legend_plan(fig, H, extra)
    out = os.path.join(HERE, "plan.png")
    fig.savefig(out, dpi=200, facecolor=BG)
    plt.close(fig)
    return out


# ---------------------------------------------------------------- plan-walk.png
MASTER_CAMS = ["M0", "D0", "H0", "W0", "C0", "K-boy", "K-girl", "MB0", "B0"]
CAM_HE = {"M0": "סלון", "D0": "אוכל", "H0": "כניסה", "W0": "עבודה", "C0": "מסדרון", "K-boy": "ילד",
          "K-girl": "ילדה", "MB0": "הורים", "B0": "מקלחת"}
CAM_LABEL_OFF = {"M0": (0.25, 0.45), "D0": (0.45, 0.35), "H0": (0.55, 0.30), "W0": (0.3, 0.55),
                 "C0": (0.0, 0.62), "K-boy": (0.15, 0.55), "K-girl": (0.15, 0.55), "MB0": (0.45, 0.45),
                 "B0": (0.55, 0.40)}

TCOL = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02", "#a6761d", "#1f78b4", "#e31a1c"]
WALK = [  # (number, transition id, Hebrew label)
    (1, "T-E0", "כניסה ← סלון (מאושר)"),
    (2, "T-LD", "סלון ← פינת אוכל (2 סיבובים במקום + דולי)"),
    (3, "T-HW", "כניסה ← חדר עבודה/ממ\"ד (סיבוב + דולי)"),
    (4, "T-HC", "כניסה ← מסדרון (סיבוב + נסיגה לאחור במסילה)"),
    (5, "T-CBoy", "מסדרון ← חדר ילד (מסילה עד S1, סיבוב 60°, דולי)"),
    (6, "T-CBath", "מסדרון ← מקלחת (מסילה עד S1, סיבוב 35°, דולי)"),
    (7, "T-CGirl", "מסדרון ← חדר ילדה (סיבוב 60°, דולי)"),
    (8, "T-CM", "מסדרון ← חדר הורים (נסיגה לאחור, סיבוב 35°)"),
]


def cone(ax, c, color, L=1.15, half=36):
    x, y = c["loc"][0], c["loc"][1]
    pts = [(x, y)]
    for k in range(-half, half + 1, 4):
        fx, fy = heading(c["yaw_deg_left"] + k)
        pts.append((x + L * fx, y + L * fy))
    ax.add_patch(Polygon(pts, closed=True, facecolor=color, edgecolor=color, alpha=0.28, lw=1, zorder=9))
    fx, fy = heading(c["yaw_deg_left"])
    ax.plot([x, x + L * fx], [y, y + L * fy], color=color, lw=1.2, ls=":", zorder=9)
    ax.add_patch(Circle((x, y), 0.11, facecolor="white", edgecolor=INK, lw=1.8, zorder=10))
    ax.add_patch(Circle((x, y), 0.05, facecolor=INK, zorder=11))


def arrow(ax, p, q, color, dashed=False, lw=3.2):
    a = FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=24, color=color, lw=lw,
                        ls=(0, (4, 2.5)) if dashed else "-", zorder=12, shrinkA=0, shrinkB=2)
    ax.add_patch(a)


def pan_arc(ax, c, y0, y1, color, r=0.45):
    # y in yaw degrees; draw arc of heading directions with an arrow head at y1
    n = 24
    pts = []
    for i in range(n + 1):
        yy = y0 + (y1 - y0) * i / n
        fx, fy = heading(yy)
        pts.append((c[0] + r * fx, c[1] + r * fy))
    xs, ys = zip(*pts)
    ax.plot(xs[:-2], ys[:-2], color=color, lw=2.6, zorder=12, solid_capstyle="round")
    ax.add_patch(FancyArrowPatch(pts[-3], pts[-1], arrowstyle="-|>", mutation_scale=16, color=color, lw=2.6,
                                 zorder=12, shrinkA=0, shrinkB=0))


def badge(ax, x, y, n, color):
    ax.add_patch(Circle((x, y), 0.27, facecolor=color, edgecolor="white", lw=2.5, zorder=14))
    ax.text(x, y, str(n), ha="center", va="center", fontsize=15, weight="bold", color="white", zorder=15)


def make_walk():
    extra = 4.2
    fig, ax, H = new_fig(extra, "סיור בבית: מצלמות ומסלולי מעבר")
    draw_base(ax, faded=True)
    room_labels(ax, faded=True, positions={
        "living": (0.1, 2.6), "kitchen-dining": (5.6, 4.6), "hall": (1.45, 9.25), "work-mamad": (-1.0, 9.0),
        "boy": (-0.8, 11.3), "girl": (-0.8, 14.9), "master": (-0.6, 20.3),
        "bath": (5.15, 12.95), "laundry": (4.1, 14.55), "ensuite-wic": (4.75, 18.6)})
    front_door_tag(ax)
    north_arrow(ax, 7.85, 17.5)
    scale_bar(ax, 2.5, 22.75)

    # rail
    rl = J["rail"]
    h0, c0 = CAMS["H0e"]["loc"], CAMS["C0"]["loc"]
    ax.plot([h0[0], c0[0]], [h0[1], c0[1]], color="#bbbbbb", lw=10, solid_capstyle="round", zorder=8, alpha=0.8)
    for st in rl["stations"]:
        c = CAMS[st["id"]]["loc"]
        ax.add_patch(Rectangle((c[0] - 0.12, c[1] - 0.12), 0.24, 0.24, facecolor="#555", edgecolor="white",
                               lw=1.5, zorder=9))
    s1 = CAMS["S1"]["loc"]
    ax.text(s1[0] + 0.62, s1[1] - 0.05, "S1", fontsize=11, weight="bold", color="#555", zorder=9)
    ax.text(2.05, 11.2, he("מסילה"), rotation=90, fontsize=11, color="#666", ha="center", va="center", zorder=9)

    # cameras
    for cid in MASTER_CAMS:
        cone(ax, CAMS[cid], "#c0392b" if cid == "M0" else "#34495e")
    for cid in MASTER_CAMS:
        c = CAMS[cid]["loc"]
        ox, oy = CAM_LABEL_OFF[cid]
        ax.text(c[0] + ox, c[1] + oy, cid, ha="center", va="center", fontsize=11, weight="bold", color=INK,
                zorder=13, path_effects=[pe.withStroke(linewidth=3, foreground="white")])

    T = {t["id"]: t for t in J["transitions"]}
    loc2 = lambda cid: tuple(CAMS[cid]["loc"][:2])
    badge_pos = {}
    for n, tid, _ in WALK:
        col = TCOL[n - 1]
        t = T[tid]
        start_cam = t["from"].split()[-1]
        cur = loc2(start_cam)
        for seg in t["segments"]:
            if seg["type"] == "pan":
                pan_arc(ax, cur, seg["yaw"][0], seg["yaw"][1], col,
                        r=0.45 if seg["yaw"][0] in (0, 25) and seg["yaw"][1] in (0, 25, 30, -35, 60) else 0.62)
            elif seg["type"] in ("dolly", "pull-back"):
                if "from" in seg:
                    p = tuple(seg["from"]); q = tuple(seg["to"])
                else:  # rail move to a station
                    p = cur; q = loc2(seg["to"])
                    # offset a little so it does not hide the rail
                    off = -0.32 if tid == "T-CBoy" else 0.32
                    p = (p[0] + off, p[1]); q = (q[0] + off, q[1])
                arrow(ax, p, q, col, dashed=(seg["type"] == "pull-back"))
                badge_pos.setdefault(n, ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2))
                cur = tuple(seg["to"]) if "from" in seg else loc2(seg["to"])
    # badge placement tweaks (keep off walls/cones)
    tweak = {1: (-0.25, 0.0), 2: (0.15, -0.15), 3: (0.0, -0.25), 4: (0.33, -1.2), 5: (0.0, 0.0), 6: (0.0, 0.0),
             7: (0.0, -0.25), 8: (0.25, 0.0)}
    for n, (x, y) in badge_pos.items():
        dx, dy = tweak.get(n, (0, 0))
        badge(ax, x + dx, y + dy, n, TCOL[n - 1])
    # entry step 0
    o = OPEN["O-front-door"]; yc = sum(o["y"]) / 2
    badge(ax, 4.35, yc - 0.55, 0, "#4d6b40")

    # legend (bottom)
    y0 = (extra - 0.45) / H
    fig.text(0.97, y0, he("סדר ההליכה"), ha="right", va="center", fontsize=17, weight="bold")
    rows = [(0, "#4d6b40", "נכנסים מדלת הכניסה לחלל הכניסה (H0, פריים הפתיחה של האתר)")] + \
           [(n, TCOL[n - 1], t) for n, _, t in WALK]
    for i, (n, col, t) in enumerate(rows):
        col_i, row_i = divmod(i, 5)
        xx = 0.97 - col_i * 0.5
        yy = y0 - (0.5 + row_i * 0.38) / H
        fig.text(xx - 0.012, yy, str(n), ha="center", va="center", fontsize=11, weight="bold", color="white",
                 bbox=dict(boxstyle="circle,pad=0.3", fc=col, ec="white"))
        fig.text(xx - 0.035, yy, he(t), ha="right", va="center", fontsize=12)
    yk = y0 - (0.5 + 5 * 0.38 + 0.25) / H
    key = [
        "חרוט = הפריים הראשי של החדר: מאיפה המצלמה מצלמת ולאן היא מביטה (שדה ראייה 72°, עדשה 24 מ\"מ). אדום = M0 בסלון, המאושר.",
        "חץ רציף = הליכה קדימה (דולי). חץ מקווקו = נסיגה לאחור כשהמצלמה ממשיכה להביט קדימה (pull-back, החלטה U4).",
        "קשת עם חץ = סיבוב במקום (pan). פס אפור = המסילה במסדרון, ריבועים = תחנות. כל מעבר אפשר לנגן גם הפוך (חזרה).",
    ]
    for i, k in enumerate(key):
        fig.text(0.97, yk - i * 0.34 / H, he(k), ha="right", va="center", fontsize=11.5, color="#444")
    out = os.path.join(HERE, "plan-walk.png")
    fig.savefig(out, dpi=200, facecolor=BG)
    plt.close(fig)
    return out


# ---------------------------------------------------------------- clay-axo.png (roofless axonometric)
def make_axo():
    """Walls rasterised on a 5 cm grid, merged into boxes, drawn with a painter's algorithm."""
    import numpy as np
    g = 0.05
    fp = J["footprint"]["outer_bbox"]
    X0, X1 = fp["x"]; Y0, Y1 = fp["y"]
    nx = int(round((X1 - X0) / g)); ny = int(round((Y1 - Y0) / g))
    xs = X0 + (np.arange(nx) + 0.5) * g
    ys = Y0 + (np.arange(ny) + 0.5) * g
    XX, YY = np.meshgrid(xs, ys, indexing="ij")
    inside = lambda x, y: (XX > x[0]) & (XX < x[1]) & (YY > y[0]) & (YY < y[1])
    wall = np.zeros((nx, ny), bool)
    for b in J["footprint"]["outer_blocks"]:
        wall |= inside(b["x"], b["y"])
    wall |= inside([3.60, 6.60], [9.80, 9.95])
    for r in J["rooms"]:
        wall &= ~inside(r["x"], r["y"])
    H = np.where(wall, 3.0, 0.0)
    for r in J["rooms"]:
        pass
    # openings: door height 2.4 cut to lintel -> show as low gap (height 0) for clarity
    for o in J["openings"]:
        if "plane_y" in o:
            m = inside(o["x"], [o["plane_y"][0] - 0.01, o["plane_y"][1] + 0.01])
        else:
            m = inside([o["plane_x"][0] - 0.01, o["plane_x"][1] + 0.01], o["y"])
        z = o.get("z", [0, 2.4])[1]
        H[m & wall] = -z  # negative = opening (lintel above)
    for w in J["windows"]:
        if "plane_x" in w:
            m = inside([w["plane_x"] - 0.36, w["plane_x"]], w["y"])
        elif "plane_y" in w:
            t = 0.36 if w["plane_y"] <= 0.01 else 0.16
            m = inside(w["x"], [w["plane_y"] - t, w["plane_y"]])
        else:
            continue
        H[m & wall] = 100 + w["sill"]  # encoded window
    # projection: viewer north-east of the house and above; looking mostly south (+X)
    al, el = math.radians(28), math.radians(58)
    CUT = 1.5  # walls cut at 1.5 m so the rooms read from above
    F = (math.cos(al), math.sin(al)); R = (-math.sin(al), math.cos(al))
    def P(x, y, z):
        return (R[0] * x + R[1] * y, (F[0] * x + F[1] * y) * math.sin(el) + z * math.cos(el))
    depth = lambda x, y: F[0] * x + F[1] * y
    boxes = []
    # merge runs along y for each x column with equal code
    for i in range(nx):
        j = 0
        while j < ny:
            h = H[i, j]
            if h == 0:
                j += 1; continue
            k = j
            while k + 1 < ny and H[i, k + 1] == h:
                k += 1
            boxes.append((i, j, k, h))
            j = k + 1
    # merge identical runs in adjacent columns
    merged = {}
    for (i, j, k, h) in boxes:
        key = (j, k, h)
        merged.setdefault(key, []).append(i)
    rects = []
    for (j, k, h), cols in merged.items():
        cols.sort()
        s = cols[0]; prev = s
        for c in cols[1:] + [None]:
            if c is not None and c == prev + 1:
                prev = c; continue
            rects.append((X0 + s * g, X0 + (prev + 1) * g, Y0 + j * g, Y0 + (k + 1) * g, h))
            if c is not None:
                s = prev = c
    segs = []
    for (x0, x1, y0, y1, h) in rects:
        if h >= 100:
            segs.append((x0, x1, y0, y1, 0, h - 100, "wall"))
            segs.append((x0, x1, y0, y1, h - 100, CUT, "glass"))
        elif h < 0:
            continue  # door opening: lintel is above the cut
        else:
            segs.append((x0, x1, y0, y1, 0, CUT, "wall"))
    fig = plt.figure(figsize=(12, 9), dpi=200, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 0.93]); ax.axis("off"); ax.set_aspect("equal")
    # floors
    for r in J["rooms"]:
        x, y = r["x"], r["y"]
        col = "#efe3c4" if r["id"] == "living" else ("#e6e6e6" if not r.get("build", True) else "#f3efe8")
        ax.add_patch(Polygon([P(x[0], y[0], 0), P(x[1], y[0], 0), P(x[1], y[1], 0), P(x[0], y[1], 0)],
                             closed=True, facecolor=col, edgecolor="#cfc8bb", lw=0.5, zorder=0))
    # painter: viewer is at -X, -Y; draw far (large x+y) first
    segs.sort(key=lambda s: (-depth(s[0], s[2]), s[4]))
    for (x0, x1, y0, y1, z0, z1, kind) in segs:
        top = "#fbfaf6" if kind == "wall" else "#bcd7ea"
        sideA = "#d9d4ca" if kind == "wall" else "#9fc3dc"  # faces -X (north)
        sideB = "#c7c1b5" if kind == "wall" else "#8bb3cf"  # faces -Y (east)
        alpha = 1.0 if kind == "wall" else 0.75
        fA = [P(x0, y0, z0), P(x0, y1, z0), P(x0, y1, z1), P(x0, y0, z1)]
        fB = [P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)]
        fT = [P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)]
        for f, c in ((fA, sideA), (fB, sideB), (fT, top)):
            ax.add_patch(Polygon(f, closed=True, facecolor=c, edgecolor=c, lw=0.3, alpha=alpha))
    # labels
    for r in J["rooms"]:
        if not r.get("build", True):
            continue
        cx = (r["x"][0] + r["x"][1]) / 2; cy = (r["y"][0] + r["y"][1]) / 2
        u, v = P(cx, cy, 0)
        ax.text(u, v, he(r["name_he"]), ha="center", va="center", fontsize=13, weight="bold", color=INK,
                zorder=50, path_effects=[pe.withStroke(linewidth=3, foreground="white")])
    allp = [P(x, y, z) for x in (X0, X1) for y in (Y0, Y1) for z in (0, CUT)]
    us, vs = zip(*allp)
    ax.set_xlim(min(us) - 0.5, max(us) + 0.5); ax.set_ylim(min(vs) - 0.5, max(vs) + 0.5)
    fig.text(0.97, 0.965, he("מבט clay מלמעלה, בלי גג, קירות חתוכים בגובה 1.5 מ' (מבט מצפון-מזרח)"), ha="right", va="center",
             fontsize=18, weight="bold")
    out = os.path.join(HERE, "clay-axo.png")
    fig.savefig(out, dpi=200, facecolor=BG)
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(make_plan())
    print(make_walk())
    try:
        print(make_axo())
    except Exception as e:  # optional deliverable
        print("axo skipped:", e)
