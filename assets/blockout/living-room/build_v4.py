#!/usr/bin/env python3
"""
Blockout v4 of the Nordic living room: alternative B as adopted (v4-spec.json), with the three
left-zone variants L0 / L1 / L2 (review-designer.md 8.3), plus the M0 input set for one variant.

Reuses build_alts.py (shell, slots, camera, readable warm-grey clay palette, plan) and
build_scene.py (geometry helpers, passes, EXR loader). Neither file is modified by this script.
Only the armchair is rebuilt here, because v4 makes the back-post length a parameter
(L0 0.50 as v3, L1/L2 0.455).

Outputs
  v4/<L0|L1|L2>/clay.png          2048x1152, 64 samples, shell + fixed furniture only (as M0)
  v4/<L0|L1|L2>/clay-proxies.png  same view with solid clay proxies of all 16 slots
  v4/<L0|L1|L2>/overlay.png       proxies render + outlines + labels + 3:5 mobile crop
  v4/<L0|L1|L2>/plan.png          top view with camera, FOV, E0 path
  v4/<L0|L1|L2>/selfcheck.json    expected (v4-spec) vs measured, checks C1-C20, mobile crop
  v4/compare.jpg                  L0 | L1 | L2: left-zone crops (u 0-0.55) and full frames with the 3:5 crop
  --m0 <variant>: the M0 input set at the top level (m0-clay-4k.png, m0-clay.png, m0-clay-overlay.png,
  m0-lines.png, m0-depth.png/.exr, m0-depth-nearbright.png, m0-camera.json, m0-selfcheck.json,
  plan.png, m0-blockout.blend). The M0 clay is EMPTY of products: shell + sofa, coffee table, armchair.

Run
  python3 build_v4.py                               # L0, L1, L2 (2K) + compare
  python3 build_v4.py --m0 L2                       # M0 set for L2 only (4K, 256 samples)
  python3 build_v4.py --variants L1 --res 960 --samples 16 --out /tmp/x   # preview
Passes (EXR) go to a temp dir outside the repo and are deleted at the end.
"""
import argparse
import json
import math
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import numpy as np  # noqa: E402
import build_alts as ba  # noqa: E402
from mathutils import Vector  # noqa: E402

bs = ba.bs
P = bs.proj
ASP = 9 / 16
SPEC_PATH = os.path.join(HERE, "v4-spec.json")
OUT_DIR = os.path.join(HERE, "v4")
TOL = 0.01
VARIANTS = ("L0", "L1", "L2")
TANG = 0.02


def r4(x):
    return ba.r4(x)


# ---------------------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------------------
def v4_config(spec, vid):
    sh = spec["shell"]
    w = sh["windows"][0]
    z0 = w["variant_L2"]["z0"] if vid == "L2" else w["z0"]
    win = dict(wall="left", a0=w["y0"], a1=w["y1"], mullion=w["mullion_y"], z0=z0, z1=w["z1"],
               mullion_w=w["mullion_w"], frame_w=w["frame_w"], reveal=w["reveal_depth"],
               sill_proud=w["sill_proud"], lining="paint", frame_plane_x=w["frame_plane_x"])
    c = spec["camera"]
    ff = spec["fixed_furniture"]
    ch = ff["armchair"]["variants"][vid]
    slots = {}
    for k, v in spec["slots"].items():
        s = dict(v)
        s["spec_status"] = v.get("status", "approx")
        # closed = decided product envelope -> drawn solid like firm
        s["status"] = "firm" if s["spec_status"] in ("firm", "closed") else "approx"
        if k == "magazine-holder":
            s["c"] = ((s["x"][0] + s["x"][1]) / 2, (s["y"][0] + s["y"][1]) / 2, (s["z"][0] + s["z"][1]) / 2)
            s["s"] = (s["x"][1] - s["x"][0], s["y"][1] - s["y"][0], s["z"][1] - s["z"][0])
        if k == "curtains":
            s["rod"] = dict(wall="left", a0=v["rod"]["y0"], a1=v["rod"]["y1"], z=v["rod"]["z"])
            s["stacks"] = v["stacks_y"]
        slots[k] = s
    mc = spec["mobile_crop"]
    cfg = dict(
        id=vid, name=f"v4 {vid}: {ch['note']}", room=dict(spec["room"]), door=dict(sh["door"]), window=win,
        skirting=dict(type="board", h=sh["skirting_h"]), cornice=sh["cornice"],
        planks=dict(w=sh["floor_planks"]["w"], len=sh["floor_planks"]["len"]),
        camera=dict(loc=list(c["loc"]), yaw=c["yaw_deg_left"], lens=c["lens"], shift_x=c["shift_x"],
                    shift_y=c["shift_y"], u0=c["u0"], v0=c["v0"]),
        h0=dict(spec["h0"]),
        sofa=dict(x0=ff["sofa"]["x0"], x1=ff["sofa"]["x1"]), table=dict(cx=ff["table"]["cx"], cy=ff["table"]["cy"]),
        chair=dict(cx=ch["cx"], cy=ch["cy"], yaw=ch["yaw_deg"], arm_front_inset=ch["arm_front_inset"],
                   post_len=0.50 if vid == "L0" else 0.455),
        dx=(ff["sofa"]["x0"] + ff["sofa"]["x1"]) / 2.0,
        slots=slots, expected=dict(spec["expected"]), checks=list(spec["checks"]),
        mobile_crop=[dict(name="3:5", center_u=(mc["u"][0] + mc["u"][1]) / 2, width=mc["u"][1] - mc["u"][0])],
        mobile=mc,
    )
    return cfg


# ---------------------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------------------
class V4Shell(ba.Shell):
    def vestibule(self):
        d = self.cfg["door"]
        hx0, hx1, hy1 = 0.80, 3.60, 9.80       # v4-spec h0.hall: X 0.80-3.60, Y 6.35-9.80
        hh = d["h"] + 0.30
        y0 = self.yf + self.t["front"]
        pf = ba.SHELL_IDX["front-wall"]
        M = ba.M
        bs.box("hall_floor", hx0 - 0.1, hx1 + 0.1, y0, hy1 + 0.1, -0.10, 0, M["floor_gap"], "shell", pidx=pf)
        bs.box("hall_ceiling", hx0 - 0.1, hx1 + 0.1, y0, hy1 + 0.1, hh, hh + 0.1, M["vest"], "shell", pidx=pf)
        bs.box("hall_left", hx0 - 0.1, hx0, y0, hy1, 0, hh, M["vest"], "shell", pidx=pf)
        bs.box("hall_right", hx1, hx1 + 0.1, y0, hy1, 0, hh, M["vest"], "shell", pidx=pf)
        bs.box("hall_back", hx0 - 0.1, hx1 + 0.1, hy1, hy1 + 0.1, 0, hh, M["vest"], "shell", pidx=pf)


def build_chair_v4(mclay, mwood, post_len):
    """build_scene.build_chair with the back-post length as a parameter (v3 = 0.50)."""
    C = bs.CHAIR
    box = bs.box
    g = "furniture"
    hd, hw = C["d"] / 2, C["w"] / 2
    parts = []
    lw = 0.045
    arm_z = 0.58
    for lx in (hd - 0.06, -hd + 0.06):
        for ly in (hw - 0.03, -hw + 0.03):
            parts.append(box("chair_leg", lx - lw / 2, lx + lw / 2, ly - lw / 2, ly + lw / 2, 0, arm_z - 0.03, mwood, g,
                             bevel=0.005, seg=1))
    for ly in (hw - 0.03, -hw + 0.03):
        parts.append(box("chair_arm", -hd + 0.02, hd - C["arm_front_inset"], ly - 0.03, ly + 0.03, arm_z - 0.03, arm_z,
                         mwood, g, bevel=0.006, seg=2))
        parts.append(box("chair_side_rail", -hd + 0.06, hd - 0.06, ly - 0.02, ly + 0.02, 0.20, 0.25, mwood, g))
    for lx in (hd - 0.06, -hd + 0.06):
        parts.append(box("chair_seat_rail", lx - 0.02, lx + 0.02, -hw + 0.03, hw - 0.03, 0.22, 0.28, mwood, g))
    parts.append(box("chair_seat", -hd + 0.18, hd - 0.02, -hw + 0.065, hw - 0.065, 0.27, C["seat_h"], mclay, g, bevel=0.03))
    tilt = math.radians(15)
    L, th = 0.41, 0.13
    bx, bz = -hd + 0.17, 0.34
    bc = box("chair_back", -th / 2, th / 2, -hw + 0.065, hw - 0.065, 0, L, mclay, g, bevel=0.035)
    bs._base_pivot(bc)
    bc.location = (bx, 0, bz)
    bc.rotation_euler = (0, -tilt, 0)
    parts.append(bc)
    for ly in (hw - 0.03, -hw + 0.03):
        p = box("chair_back_post", -0.02, 0.02, ly - 0.02, ly + 0.02, 0, post_len, mwood, g)
        bs.apply_scale(p)
        bs._base_pivot(p)
        p.location = (-hd + 0.06, ly, 0.26)
        p.rotation_euler = (0, -tilt, 0)
        parts.append(p)
    return bs.parent_group("armchair", parts, bs.PASS_INDEX["armchair"], loc=(C["cx"], C["cy"], 0), yaw_deg=C["yaw_deg"])


def build_furniture(cfg):
    bs.SOFA = dict(bs.SOFA, x0=cfg["sofa"]["x0"], x1=cfg["sofa"]["x1"])
    bs.TABLE = dict(bs.TABLE, cx=cfg["table"]["cx"], cy=cfg["table"]["cy"])
    bs.CHAIR = dict(bs.CHAIR, cx=cfg["chair"]["cx"], cy=cfg["chair"]["cy"], yaw_deg=cfg["chair"]["yaw"],
                    arm_front_inset=cfg["chair"]["arm_front_inset"])
    M = ba.M
    return {"sofa": bs.build_sofa(M["sofa"], M["wood"]), "coffee-table": bs.build_table(M["wood"]),
            "armchair": build_chair_v4(M["chair"], M["wood"], cfg["chair"]["post_len"])}


def build_base(cfg, a, res=None, samples=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bs.COLL.clear()
    ba.mats()
    V4Shell(cfg).build()
    roots = build_furniture(cfg)
    cam = ba.build_camera(cfg)
    bs.build_world(a.sky)
    bpy.context.scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.93, 0.95, 0.99, 1.0)
    bs.setup_render(res or a.res, samples or a.samples, a.exposure)
    bpy.context.scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.context.view_layer.update()
    return roots, cam


def render(path, tmp, samples=None, denoise=True):
    """Render the scene camera to path; EXR passes into tmp. Returns (depth, idx, normal)."""
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    sc = bpy.context.scene
    keep = (sc.cycles.samples, sc.cycles.use_denoising)
    if samples:
        sc.cycles.samples = samples
    sc.cycles.use_denoising = denoise
    bs.setup_compositor(tmp)
    sc.frame_set(1)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    sc.cycles.samples, sc.cycles.use_denoising = keep
    depth = bs.load_exr(os.path.join(tmp, "Depth_0001.exr"))
    idx = np.rint(bs.load_exr(os.path.join(tmp, "IndexOB_0001.exr"))).astype(np.int32)
    normal = bs.load_exr(os.path.join(tmp, "Normal_0001.exr"), channels=3)
    return depth, idx, normal


# ---------------------------------------------------------------------------------------
# geometry helpers for the checks
# ---------------------------------------------------------------------------------------
def uvq(cam, p):
    u, v, _ = P(cam, p)
    return (u, v * ASP)          # aspect-corrected (distances in frame widths)


def part_hulls(cam, root):
    """Projected convex hull per mesh child of root (aspect-corrected), with names."""
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for ch in root.children_recursive:
        if ch.type != "MESH":
            continue
        ev = ch.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        pts = [uvq(cam, mw @ v.co) for v in me.vertices]
        ev.to_mesh_clear()
        out.append((ch.name, bs._hull2d(pts)))
    return out


def inside_poly(poly, p, eps=0.0):
    """Strictly inside a convex CCW/CW polygon by more than eps."""
    n = len(poly)
    if n < 3:
        return False
    sgn = 0
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        cr = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1e-12
        d = cr / L
        if abs(d) <= eps:
            return False
        s = 1 if d > 0 else -1
        if sgn == 0:
            sgn = s
        elif s != sgn:
            return False
    return True


def contour_features(hulls, eps=0.0008):
    """Silhouette corners and near-vertical silhouette edges of a union of convex part hulls.
    A hull vertex is a contour corner when it is not inside any other part's hull.
    Returns corners [(u, vq, part)] and near-vertical edges [((u0, vq0), (u1, vq1), part, angle_deg)]."""
    corners, edges = [], []
    for k, (name, h) in enumerate(hulls):
        others = [hh for j, (_, hh) in enumerate(hulls) if j != k]
        n = len(h)
        for i in range(n):
            p = h[i]
            if any(inside_poly(o, p, eps) for o in others):
                continue
            # turning angle at the vertex: keep real corners (> 20 deg)
            a, b = h[i - 1], h[(i + 1) % n]
            v1 = (p[0] - a[0], p[1] - a[1])
            v2 = (b[0] - p[0], b[1] - p[1])
            n1, n2 = math.hypot(*v1), math.hypot(*v2)
            if n1 < 1e-9 or n2 < 1e-9:
                continue
            turn = math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))))
            if turn >= 20:
                corners.append((p[0], p[1], name))
        for i in range(n):
            a, b = h[i], h[(i + 1) % n]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 0.004:
                continue
            ang = math.degrees(math.atan2(abs(b[0] - a[0]), abs(b[1] - a[1])))
            if ang > 10:
                continue
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if any(inside_poly(o, mid, eps) for o in others):
                continue
            edges.append((a, b, name, round(ang, 1)))
    return corners, edges


def union_top(hulls, u):
    """Top (min vq) of the union of hulls at column u, or None."""
    best = None
    for _, h in hulls:
        n = len(h)
        for i in range(n):
            a, b = h[i], h[(i + 1) % n]
            if (a[0] - u) * (b[0] - u) <= 0 and a[0] != b[0]:
                t = (u - a[0]) / (b[0] - a[0])
                y = a[1] + t * (b[1] - a[1])
                best = y if best is None else min(best, y)
    return best


def line_features(line, corners, edges, vq_span_fn):
    """Distances from a vertical image line u=line_u (visible for vq in vq_span_fn(u)) to contour corners and
    near-vertical edges inside that span. Returns (min_dist, nearest item, crossing near-vertical edges)."""
    lu = line
    best, near = None, None
    for (u, vq, part) in corners:
        top, bot = vq_span_fn(u)
        if not (top <= vq <= bot):
            continue
        d = abs(u - lu)
        if best is None or d < best:
            best, near = d, dict(kind="corner", part=part, u=round(u, 4), v=round(vq / ASP, 4))
    for (a, b, part, ang) in edges:
        # clip the edge to the span (span evaluated at the edge's u; edges are near-vertical)
        um = (a[0] + b[0]) / 2
        top, bot = vq_span_fn(um)
        y0, y1 = sorted((a[1], b[1]))
        y0, y1 = max(y0, top), min(y1, bot)
        if y0 >= y1:
            continue
        # u along the clipped segment
        def u_at(y):
            if abs(b[1] - a[1]) < 1e-12:
                return a[0]
            return a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        ua, ub = u_at(y0), u_at(y1)
        d = 0.0 if (ua - lu) * (ub - lu) <= 0 else min(abs(ua - lu), abs(ub - lu))
        if best is None or d < best:
            best, near = d, dict(kind="near-vertical edge", part=part, u=[round(ua, 4), round(ub, 4)],
                                 v=[round(y0 / ASP, 4), round(y1 / ASP, 4)], angle_from_vertical_deg=ang)
    return best, near


# ---------------------------------------------------------------------------------------
# self-check (C1-C20, expected values)
# ---------------------------------------------------------------------------------------
def self_check(cfg, cam, roots, slots, idx, rgb, spec):
    H, W = idx.shape
    vid = cfg["id"]
    R, Wn, C = cfg["room"], cfg["window"], cfg["camera"]
    xl, yb, h = R["x_left"], R["y_back"], R["h"]
    cz = C["loc"][2]
    E = cfg["expected"]
    rep = dict(variant=vid, name=cfg["name"], spec="v4-spec.json (" + spec["version"] + ")", tolerance=TOL,
               method=("Geometry: pinhole projection of the evaluated Blender meshes through the render camera "
                       "(bpy world_to_camera_view; bevels included). Pixels: object-index pass of the render "
                       f"({W}x{H}, 1 px = {1 / W:.5f} frame widths). Distances between shapes are in frame widths, "
                       "with v scaled by 9/16 (isotropic). Positive gap = apart."),
               camera=dict(C, mirrored_scale_x=-1.0, blender_rotation_euler_deg=[90, 0, round(180 - C["yaw"], 4)]),
               window=dict(Wn), chair=dict(cfg["chair"]), image_px=[W, H],
               frame_values=[], checks=[], notes=[])
    fvs = rep["frame_values"]

    def fv(key, measured, how, exp_key=None):
        ek = exp_key or key
        ex = E.get(ek)
        item = dict(key=key, measured=r4(measured), how=how)
        if ex is not None:
            a_, b_ = np.array(measured, float).ravel(), np.array(ex, float).ravel()
            dev = float(np.max(np.abs(a_ - b_)))
            item.update(expected=ex, expected_key=ek, max_dev=round(dev, 4), ok=bool(dev <= TOL + 1e-9))
        fvs.append(item)
        return item

    checks = rep["checks"]

    def chk(cid, title, ok, measured, required, blocking, note="", expected=None):
        it = dict(id=cid, check=title, result=("pass" if ok else "fail") if ok is not None else "report",
                  measured=measured, required=required, blocking=blocking, note=note)
        if expected is not None:
            it["expected_spec"] = expected
        checks.append(it)

    sv = lambda n: ba.verts(slots[n]["main"])                    # noqa: E731
    fur = lambda n: bs.eval_world_verts(roots[n])                # noqa: E731
    bb = lambda pts: ba.bb(cam, pts)                             # noqa: E731
    hull = lambda pts: ba.hull(cam, pts)                         # noqa: E731
    masks = {n: idx == bs.PASS_INDEX[n] for n in roots}
    for n in slots:
        masks[n] = idx == slots[n]["pidx"]
    masks["planter-crown"] = idx == ba.CROWN_IDX
    pidx_of = lambda n: (ba.CROWN_IDX if n == "planter-crown" else (bs.PASS_INDEX[n] if n in roots else slots[n]["pidx"]))  # noqa: E731
    rep["visible_masks"] = {n: r4(ba.mask_bb(m)) for n, m in masks.items()}

    def sgap(a_, b_):
        if not masks[a_].any() or not masks[b_].any():
            return None
        return bs.silhouette_gap(idx, pidx_of(a_), pidx_of(b_))

    # ---------------- shell
    cu = P(cam, (xl, yb, 1.2))[0]
    fv("back_left_corner_u", cu, "projection of the back-left corner line")
    fv("left_wall_visible_to_y", ba.wall_entry(cam, xl, cz, "left", C["loc"][1] - 0.05),
       "metres: Y where the left frame edge meets the left wall at camera height (bisection)")
    acx = cfg["slots"]["framed-art"]["c"][0]
    fv("ceiling_band_at_art_y", P(cam, (acx, yb, h))[1], "v of the ceiling/wall line above the art centre")
    a0, a1, z0, z1 = Wn["a0"], Wn["a1"], Wn["z0"], Wn["z1"]
    fv("window_opening_wall_face_x", sorted([P(cam, (xl, a0, 1.0))[0], P(cam, (xl, a1, 1.0))[0]]),
       "opening edges at the wall face X=-2.30")
    fpx = Wn["frame_plane_x"]
    mw = Wn["mullion_w"]
    mull = sorted([P(cam, (fpx, Wn["mullion"] - mw / 2, 1.6))[0], P(cam, (fpx, Wn["mullion"] + mw / 2, 1.6))[0]])
    fv("window_mullion_frame_plane_x", mull, "mullion edges at the frame plane X=-2.65 (Y 1.77 / 1.83)")
    # pixel cross-check of the mullion: run of window-index pixels between sky pixels at z 1.6
    vrow = int(P(cam, (fpx, Wn["mullion"], 1.6))[1] * H)
    row = idx[vrow]
    c0 = int((mull[0] + mull[1]) / 2 * W)
    lo_, hi_ = c0, c0
    while lo_ > 0 and row[lo_ - 1] == ba.SHELL_IDX["window"]:
        lo_ -= 1
    while hi_ < W - 1 and row[hi_ + 1] == ba.SHELL_IDX["window"]:
        hi_ += 1
    rep["mullion_pixel_run"] = dict(row_v=r4(vrow / H), u=[r4(lo_ / W), r4((hi_ + 1) / W)],
                                    note="window-index pixels around the mullion at z 1.6, includes the 2 cm sash "
                                         "stiles on each side (glass edges)")
    head = sorted([P(cam, (xl, a1, z1))[1], P(cam, (xl, a0, z1))[1]])
    fv("window_head_y", head, "head at the wall face, front -> back")
    sill = sorted([P(cam, (xl, a1, z0))[1], P(cam, (xl, a0, z0))[1]])
    fv("window_sill_y_info", sill, "sill line at the wall face (info; L2 sill 0.75)")
    head_min = min(head)

    # ---------------- furniture
    fb = {n: bb(fur(n)) for n in roots}
    fv("sofa", fb["sofa"], "geometry projection incl. bevel [u0,u1,v0,v1]")
    fv("coffee-table_x", fb["coffee-table"][:2], "geometry projection")
    ek = "armchair_L0" if vid == "L0" else "armchair_L1"
    fv("armchair", fb["armchair"], "geometry projection [u0,u1,v0,v1]" +
       ("" if vid != "L2" else " (L2 = L1 chair; expected armchair_L1)"), exp_key=ek)
    # chair corners (sharp box corners from bound boxes)
    ch = roots["armchair"]
    parts = {o.name: o for o in ch.children_recursive}

    def corners_world(ob):
        return [ob.matrix_world @ Vector(c) for c in ob.bound_box]

    posts = sorted([o for o in parts.values() if o.name.startswith("chair_back_post")],
                   key=lambda o: P(cam, o.matrix_world.translation)[2])
    back = [o for o in parts.values() if o.name.startswith("chair_back") and not o.name.startswith("chair_back_post")][0]
    cw = corners_world(back)
    zmax = max(p.z for p in cw)
    top = [p for p in cw if p.z > zmax - 0.08]                      # the 4 top corners
    # near/far = camera depth; back/front = chair local x (front = +x local)
    inv = ch.matrix_world.inverted()
    top_sorted = sorted(top, key=lambda p: P(cam, p)[2])
    near2, far2 = top_sorted[:2], top_sorted[2:]
    nb = min(near2, key=lambda p: (inv @ p).x)
    fb_ = min(far2, key=lambda p: (inv @ p).x)
    ff_ = max(far2, key=lambda p: (inv @ p).x)

    def post_top(o):
        cs = corners_world(o)
        zz = max(p.z for p in cs)
        return sorted(P(cam, p)[0] for p in cs if p.z > zz - 0.03)

    legs_arms = [o for o in parts.values() if o.name.startswith(("chair_leg", "chair_arm"))]
    max_u_far = max(P(cam, p)[0] for p in ba.verts(legs_arms))
    npt, fpt = post_top(posts[0]), post_top(posts[1])
    corners_m = dict(near_post_top=[npt[0], npt[-1]], back_cushion_near_back_top=P(cam, nb)[0],
                     far_post_top=[fpt[0], fpt[-1]], back_cushion_far_back_top=P(cam, fb_)[0],
                     back_cushion_far_front_top=P(cam, ff_)[0], front_leg_and_arm_tip_far=max_u_far)
    post_top_z = max(p.z for p in corners_world(posts[0]))
    rep["armchair_heights_m"] = dict(post_top_z=r4(post_top_z), back_cushion_top_z_sharp=r4(zmax),
                                     post_below_cushion_top_m=r4(zmax - post_top_z))
    item = dict(key="armchair_corners_u", measured={k: r4(v) for k, v in corners_m.items()},
                how="sharp corners (object bound boxes, i.e. before the 3.5 cm cushion bevel) projected; "
                    "posts = top face u range; near/far by camera depth")
    if vid in ("L1", "L2"):
        ex = E["armchair_L1_corners_u"]
        devs = {k: round(float(np.max(np.abs(np.array(corners_m[k], float).ravel() - np.array(ex[k], float).ravel()))), 4)
                for k in ex}
        item.update(expected=ex, expected_key="armchair_L1_corners_u", max_dev=max(devs.values()), per_key_dev=devs,
                    ok=bool(max(devs.values()) <= TOL + 1e-9))
    fvs.append(item)

    # ---------------- slots
    sb = {n: bb(sv(n)) for n in slots}
    rep["slot_frame_boxes"] = {n: dict(box=r4(sb[n]), spec_status=cfg["slots"][n]["spec_status"] if n in cfg["slots"] else "approx",
                                       in_frame=bool(sb[n][1] > 0 and sb[n][0] < 1 and sb[n][3] > 0 and sb[n][2] < 1))
                               for n in slots}
    fv("framed-art", sb["framed-art"], "projection")
    fv("pendant", sb["pendant"], "projection of the shade")
    sc_ = cfg["slots"]["wall-sconce"]["c"]
    fv("wall-sconce_uv", list(P(cam, sc_)[:2]), "plate centre (u, v)")
    fv("planter_pot_x", sb["planter"][:2], "pot only")
    fv("wall-decor", sb["wall-decor"], "projection")
    fv("pouf", sb["pouf"], "projection (proxy h 0.36)")
    fv("magazine-holder", sb["magazine-holder"], "projection")
    fv("basket", sb["basket"], "projection")
    fl = cfg["slots"]["floor-lamp"]
    stem_u = P(cam, (fl["c"][0], fl["c"][1], 0.40))[0]
    fv("floor-lamp_stem_u", stem_u, "stem axis")
    fv("floor-lamp_shade", sb["floor-lamp"], "shade only")

    # ---------------- checks
    f = (-math.sin(math.radians(C["yaw"])), -math.cos(math.radians(C["yaw"])))
    pp = P(cam, (C["loc"][0] + 5 * f[0], C["loc"][1] + 5 * f[1], cz))
    chk("C1", "yaw sign: back-left corner at u 0.431", bool(abs(cu - 0.431) <= TOL), r4(cu), 0.431, True,
        "0.61 would mean the yaw sign is flipped")
    chk("C2", "principal point (u0, v0) = (0.52, 0.46) from the optical axis", bool(abs(pp[0] - 0.52) <= 0.003 and abs(pp[1] - 0.46) <= 0.003),
        r4(pp[:2]), "[0.52, 0.46] +-0.003", True)
    du = max(abs(P(cam, (x, y, 0))[0] - P(cam, (x, y, h))[0]) for x, y in ((xl, yb), (0.2, yb), (xl, 2.0), (fpx, 1.8)))
    chk("C3", "verticals plumb (tilt 0, roll 0)", bool(du < 1e-6), r4(du), "0", True,
        "max |du| between z 0 and z 3 of wall, corner and mullion verticals")

    # C4 armchair - planter
    chull_parts = part_hulls(cam, roots["armchair"])
    pot_h = hull(sv("planter"))
    g4 = sgap("armchair", "planter")
    # signed horizontal gap: pot left edge - chair right edge (rows where both are present, geometry)
    pot_u0 = sb["planter"][0]
    sgn = pot_u0 - fb["armchair"][1]
    hg = min(bs.poly_gap(hh, pot_h) for _, hh in chull_parts)
    ok4 = bool(g4 is not None and not g4["touching"] and g4["min_gap_frame_w"] >= TANG)
    chk("C4", "armchair-planter gap >= 0.02 (far front leg / arm tip vs pot)", ok4,
        dict(silhouette_gap_index_pass=g4 and g4["min_gap_frame_w"], touching=g4 and g4["touching"],
             signed_u_gap_pot_left_minus_chair_right=r4(sgn), hull_gap=r4(hg)),
        ">= 0.02", True, expected=cfg["checks"][3].get(vid))

    # C5 window lines vs armchair contour
    corners, nvedges = contour_features(chull_parts)
    s_ = 0.02           # sash stile
    gb_z = z0 + Wn["frame_w"] + s_          # glass bottom: top of the bottom sash rail
    head_z = z1 - Wn["frame_w"] - s_
    xs = fpx - 0.015                        # sash front face

    def gb_vq(u_, x_=xs, z_=gb_z):
        # v of the glass-bottom line at image column u (line along Y at x_, z_)
        lo, hi = a0 - 1.0, a1 + 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if P(cam, (x_, mid, z_))[0] > u_:
                lo = mid           # larger Y -> smaller u
            else:
                hi = mid
        return P(cam, (x_, (lo + hi) / 2, z_))[1] * ASP

    lines = {
        "mullion left edge (frame plane)": (mull[0], fpx, z0 + Wn["frame_w"]),
        "mullion right edge (frame plane)": (mull[1], fpx, z0 + Wn["frame_w"]),
        "glass edge left of mullion (sash)": (P(cam, (xs, Wn["mullion"] + mw / 2 + s_, 1.0))[0], xs, gb_z),
        "glass edge right of mullion (sash)": (P(cam, (xs, Wn["mullion"] - mw / 2 - s_, 1.0))[0], xs, gb_z),
        "back glass edge (frame plane)": (P(cam, (xs, a0 + Wn["frame_w"] + s_, 1.0))[0], xs, gb_z),
        "back jamb, wall face": (P(cam, (xl, a0, 1.0))[0], xl, z0),
        "back jamb, frame plane": (P(cam, (fpx, a0, 1.0))[0], fpx, z0),
        "front glass edge (frame plane)": (P(cam, (xs, a1 - Wn["frame_w"] - s_, 1.0))[0], xs, gb_z),
        "front jamb, frame plane": (P(cam, (fpx, a1, 1.0))[0], fpx, z0),
        "front jamb, wall face": (P(cam, (xl, a1, 1.0))[0], xl, z0),
    }
    # front curtain stack (hides lines left of its right edge)
    stack_f = [o for o in slots["curtains"]["main"] if o.name.startswith("px_curt1")]
    stack_b = [o for o in slots["curtains"]["main"] if o.name.startswith("px_curt0")]
    st_pts = ba.verts(stack_f)
    st_u = [P(cam, p)[0] for p in st_pts]
    stack_edge_u = max(st_u)
    stack_left_u = min(st_u)
    c5 = {}
    worst = None
    for nm, (lu, lx, lz) in lines.items():
        hidden = stack_left_u <= lu <= stack_edge_u

        def span(u_, lx=lx, lz=lz):
            return (gb_vq(u_, lx, z1) - 0.0, gb_vq(u_, lx, lz))
        d, near = line_features(lu, corners, nvedges, span)
        c5[nm] = dict(u=r4(lu), hidden_behind_front_stack=bool(hidden), min_dist=r4(d), nearest=near)
        if not hidden and d is not None and (worst is None or d < worst[0]):
            worst = (d, nm)
    # glass bottom / sill vs chair top (vertical relation)
    ucols = np.linspace(max(fb["armchair"][0], min(lines[k][0] for k in lines)), min(fb["armchair"][1], P(cam, (xl, a0, 1))[0]), 200)
    sp = Wn["sill_proud"]
    hlines = {"glass bottom (top of the bottom sash rail, z %.3f)" % gb_z: (xs, gb_z),
              "sill top edge at the wall face (z %.3f)" % z0: (xl, z0),
              "sill front top edge, proud %.2f (z %.3f)" % (sp, z0): (xl + sp, z0),
              "sill front bottom edge (z %.3f)" % (z0 - 0.025): (xl + sp, z0 - 0.025)}
    hres = {}
    for nm, (hx, hz) in hlines.items():
        ov = []
        for u_ in ucols:
            t = union_top(chull_parts, u_)
            if t is None:
                continue
            ov.append((gb_vq(u_, hx, hz) - t, u_))
        o = max(ov) if ov else (None, None)
        hres[nm] = dict(max_rise_above_line=r4(o[0]), at_u=r4(o[1]),
                        state=("none" if o[0] is None else "crossing (decisive)" if o[0] >= TANG else
                               "clear below" if o[0] <= -TANG else "TANGENT"))
    ogb = (list(hres.values())[0]["max_rise_above_line"], None)

    def vert_ok(o):
        return o is None or o >= TANG or o <= -TANG
    h_tan = [k for k, v in hres.items() if v["state"] == "TANGENT"]
    ok5 = bool((worst is None or worst[0] >= TANG) and not h_tan)
    chk("C5", "armchair vs window lines (mullion at frame plane, glass edges, jambs, glass bottom): no contour corner "
              "or near-vertical chair edge within 0.02", ok5,
        dict(closest_line=worst and worst[1], closest_dist=worst and r4(worst[0]), lines=c5,
             chair_top_vs_horizontal_lines=hres, horizontal_tangents=h_tan,
             contour_corners=len(corners), near_vertical_edges=len(nvedges)),
        ">= 0.02 from every visible vertical line; glass bottom and sill edges: rise >= 0.02 (decisive) or <= -0.02 (clear)", True,
        "contour = union of the projected convex hulls of the chair parts (evaluated meshes, bevel included); "
        "a corner/edge counts only inside the line's visible span (head to glass bottom / sill). "
        "max_rise_above_line < 0 = the chair top stays below the line by that much. v4 adds the sill edges "
        "(tangent_rule / M0-07 name the sill); the spec's C5 expectation covered the glass bottom only",
        expected=cfg["checks"][4].get(vid))

    # C6 armchair vs front curtain stack edge
    def span_all(u_):
        return (-1.0, 2.0)
    d6, n6 = line_features(stack_edge_u, corners, nvedges, span_all)
    chair_u = fb["armchair"][:2]
    straddle = [c for c in corners if abs(c[0] - stack_edge_u) < TANG]
    chk("C6", "armchair vs front curtain stack edge >= 0.02 or decisive crossing", bool(d6 is None or d6 >= TANG),
        dict(stack_edge_u=r4(stack_edge_u), min_dist=r4(d6), nearest=n6,
             corners_within_0_02=[dict(part=c[2], u=r4(c[0]), v=r4(c[1] / ASP)) for c in straddle],
             chair_u=r4(chair_u)), ">= 0.02", False, "soft fabric edge, judged by eye (non-blocking)",
        expected=cfg["checks"][5].get(vid))

    # C7 armchair bottom margin
    mb = ba.mask_bb(masks["armchair"])
    chk("C7", "armchair >= 0.05 from the bottom edge", bool(1 - fb["armchair"][3] >= 0.05),
        dict(geometry=r4(1 - fb["armchair"][3]), visible_mask=r4(1 - mb[3])), 0.05, True,
        expected=cfg["checks"][6].get(vid))

    # C8 pendant
    pend, art = sb["pendant"], sb["framed-art"]
    hp = cfg["slots"]["pendant"]["hang_point"]
    hang_v = P(cam, hp)[1]
    chk("C8", "pendant in the top third, >= 0.05 above the art; hanging point out of frame",
        bool(pend[3] <= 1 / 3 and art[2] - pend[3] >= 0.05 and hang_v < 0),
        dict(pendant_bottom_v=r4(pend[3]), art_top_v=r4(art[2]), gap=r4(art[2] - pend[3]), hang_v=r4(hang_v)),
        "bottom <= 0.333, gap >= 0.05, hang_v < 0", True, expected=cfg["checks"][7]["measured_B"])

    # C9 art vs sofa back
    sm = masks["sofa"]
    c0_, c1_ = int(max(0, art[0]) * W), int(min(1, art[1]) * W)
    rows = np.nonzero(sm[:, c0_:c1_].any(1))[0]
    stop = rows.min() / H if len(rows) else None
    sofa_geo_top = min(P(cam, p)[1] for p in fur("sofa") if art[0] <= P(cam, p)[0] <= art[1])
    chk("C9", "art bottom vs sofa back top >= 0.03", bool(stop is not None and stop - art[3] >= 0.03),
        dict(art_bottom_v=r4(art[3]), sofa_top_v_visible=r4(stop), gap=r4(stop - art[3]),
             gap_geometry=r4(sofa_geo_top - art[3])), 0.03, True,
        "visible sofa mask in the art's columns (cushion proxies excluded)", expected=cfg["checks"][8]["measured_B"])

    # C10 magazine holder
    mh = hull(sv("magazine-holder"))
    gcs = bs.poly_gap(mh, hull(ba.verts(stack_f)))
    mhb = sb["magazine-holder"]
    chk("C10", "magazine-holder: gap to the front curtain stack >= 0.02; left margin >= 0.05; bottom margin >= 0.05",
        bool(gcs >= 0.02 and mhb[0] >= 0.05 and 1 - mhb[3] >= 0.05),
        dict(stack_gap=r4(gcs), left=r4(mhb[0]), bottom=r4(1 - mhb[3]), stack_left_edge_u=r4(stack_left_u)),
        "0.02 / 0.05 / 0.05", True, expected=cfg["checks"][9]["expected"])

    # C11 pouf top vs lower edge of the table-top slab (Z 0.35)
    T = bs.TABLE
    pf = cfg["slots"]["pouf"]

    def slab_line_v(zz, u_lo, u_hi):
        a_, b_ = T["w"] / 2, T["d"] / 2
        best = None
        for i in range(2000):
            t = 2 * math.pi * i / 2000
            c, s = math.cos(t), math.sin(t)
            x = T["cx"] + a_ * math.copysign(abs(c) ** (2.0 / T["n"]), c)
            y = T["cy"] + b_ * math.copysign(abs(s) ** (2.0 / T["n"]), s)
            u_, v_, _ = P(cam, (x, y, zz))
            if u_lo <= u_ <= u_hi:
                best = v_ if best is None else max(best, v_)
        return best

    def pouf_top_v(zz):
        return min(P(cam, (pf["c"][0] + pf["r"] * math.cos(t), pf["c"][1] + pf["r"] * math.sin(t), zz))[1]
                   for t in np.linspace(0, 2 * math.pi, 720))
    pu0, pu1 = sb["pouf"][:2]
    tl = slab_line_v(T["h"] - T["top_t"], pu0, pu1)
    pt36, pt37 = pouf_top_v(pf["z1"]), pouf_top_v(pf["check_dashed_z1"])
    chk("C11", "pouf top (far rim) >= 0.02 below the lower edge of the table-top slab in the pouf's columns",
        bool(pt36 - tl >= 0.02),
        dict(table_line_v=r4(tl), pouf_top_v_h036=r4(pt36), gap_h036=r4(pt36 - tl), pouf_top_v_h037=r4(pt37),
             gap_h037=r4(pt37 - tl)), 0.02, True, "table line = slab lower edge Z 0.35 (review 8.4)",
        expected=cfg["checks"][10]["expected"])

    # C12 pouf margins, armchair, rug
    g12 = sgap("pouf", "armchair")
    gh12 = min(bs.poly_gap(hull(sv("pouf")), hh) for _, hh in chull_parts)
    rg = cfg["slots"]["rug"]
    rx0, rx1 = rg["c"][0] - rg["s"][0] / 2, rg["c"][0] + rg["s"][0] / 2
    ry0, ry1 = rg["c"][1] - rg["s"][1] / 2, rg["c"][1] + rg["s"][1] / 2
    on_rug = min(pf["c"][0] - pf["r"] - rx0, rx1 - pf["c"][0] - pf["r"], pf["c"][1] - pf["r"] - ry0, ry1 - pf["c"][1] - pf["r"])
    bot12 = 1 - sb["pouf"][3]
    ok12 = bool(bot12 >= 0.05 and gh12 >= 0.02 and on_rug >= 0.15)
    chk("C12", "pouf: bottom margin >= 0.05; gap to armchair >= 0.02; on the rug >= 15 cm from its edges", ok12,
        dict(bottom=r4(bot12), armchair_gap_hull=r4(gh12), armchair_gap_index_pass=g12 and g12["min_gap_frame_w"],
             armchair_touching_index_pass=g12 and g12["touching"], min_dist_to_rug_edge_m=r4(on_rug)),
        "0.05 / 0.02 / 0.15 m", True, expected=dict(bottom=cfg["checks"][11]["expected_bottom"], armchair="L0 0.040, L1 0.075"))

    # C13 wall decor
    pe = cfg["slots"]["planter"]
    crown_pts = [(pe["c"][0] + pe["envelope"]["r"] * math.cos(t_), pe["c"][1] + pe["envelope"]["r"] * math.sin(t_), z_)
                 for t_ in np.linspace(0, 2 * math.pi, 96) for z_ in (pe["envelope"]["z0"], pe["envelope"]["z1"])]
    wd = hull(sv("wall-decor"))
    g1, g2 = bs.poly_gap(wd, hull(crown_pts)), bs.poly_gap(wd, hull(sv("framed-art")))
    chk("C13", "wall-decor vs tree crown envelope (r 0.40, z 0.45-1.65) >= 0.03 and vs art >= 0.03",
        bool(g1 >= 0.03 and g2 >= 0.03), dict(crown=r4(g1), art=r4(g2)), 0.03, True,
        expected=cfg["checks"][12]["expected"])

    # C14 basket / sofa / lamp
    bk = cfg["slots"]["basket"]
    bkb = sb["basket"]
    g14s = bkb[0] - fb["sofa"][1]
    g14i = sgap("basket", "sofa")
    base_ring = [(fl["c"][0] + fl["base_r"] * math.cos(t), fl["c"][1] + fl["base_r"] * math.sin(t), z_)
                 for t in np.linspace(0, 2 * math.pi, 96) for z_ in (0.0, 0.02)]
    bh = hull(sv("basket"))
    base_in = all(inside_poly(bh, uvq(cam, p)) for p in base_ring)
    base_behind = all(math.hypot(p[0] - C["loc"][0], p[1] - C["loc"][1]) >
                      math.hypot(bk["c"][0] - C["loc"][0], bk["c"][1] - C["loc"][1]) - bk["r"] for p in base_ring)
    s_l, s_r = stem_u - bkb[0], bkb[1] - stem_u
    ok14 = bool(g14s >= 0.02 and s_l >= 0.02 and s_r >= 0.02 and base_in and base_behind)
    chk("C14", "basket vs sofa right edge >= 0.02; lamp stem >= 0.02 inside the basket; lamp base hidden behind the basket",
        ok14, dict(sofa_gap=r4(g14s), sofa_gap_index_pass=g14i and g14i["min_gap_frame_w"],
                   stem_to_basket_left=r4(s_l), stem_to_basket_right=r4(s_r),
                   lamp_base_inside_basket_silhouette=bool(base_in), lamp_base_behind_basket=bool(base_behind)),
        "0.02 / 0.02 / hidden", True, expected=cfg["checks"][13]["expected"])

    # C15, C16, C17
    chk("C15", "floor-lamp shade vs right edge >= 0.08", bool(1 - sb["floor-lamp"][1] >= 0.08), r4(1 - sb["floor-lamp"][1]),
        0.08, True, expected=cfg["checks"][14]["expected"])
    chk("C16", "window head >= 0.010 below the top edge", bool(head_min >= 0.010), r4(head_min), 0.010, True,
        expected=cfg["checks"][15]["measured_B"])
    e0 = ba.e0_path_B(cfg)
    chk("C17", "E0 path clears the jambs >= 0.15 m", bool(e0["min_clearance_m"] >= 0.15), e0, 0.15, True,
        expected=cfg["checks"][16]["measured_B"])

    # C18 planter vs back curtain stack edge
    g18 = bs.poly_gap(pot_h, hull(ba.verts(stack_b)))
    g18i = sgap("planter", "curtains")
    chk("C18", "planter vs back curtain stack edge (report)", None,
        dict(hull_gap=r4(g18), index_pass_gap_to_curtains=g18i and g18i["min_gap_frame_w"]), ">= 0.02 (known 0.013)",
        False, "soft edge, judged by eye", expected=cfg["checks"][17]["measured_B"])

    # C19 basket bottom vs rug back edge line
    rz = 0.012
    samples_ = []
    for t in np.linspace(0, 2 * math.pi, 1440):
        p = (bk["c"][0] + bk["r"] * math.cos(t), bk["c"][1] + bk["r"] * math.sin(t), 0.0)
        u_, v_, _ = P(cam, p)
        samples_.append((u_, v_, p))
    ucols = np.linspace(bkb[0], bkb[1], 120)
    d19 = []
    for u_ in ucols:
        vb = max((v_ for uu, v_, _ in samples_ if abs(uu - u_) < 0.0008), default=None)
        if vb is None:
            continue
        # rug back edge (Y ry0, z rz) at this u, only where the rug exists (X <= rx1)
        lo, hi = rx0, rx1 + 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if P(cam, (mid, ry0, rz))[0] < u_:
                lo = mid
            else:
                hi = mid
        xr_ = (lo + hi) / 2
        if xr_ > rx1:
            continue
        vr = P(cam, (xr_, ry0, rz))[1]
        d19.append((vr - vb, u_))
    m19 = min(d19, key=lambda t: abs(t[0])) if d19 else (None, None)
    chk("C19", "basket bottom vs rug back edge line (report)", None,
        dict(min_abs_dv=r4(m19[0]), at_u=r4(m19[1]), dv_range=r4([min(d[0] for d in d19), max(d[0] for d in d19)]) if d19 else None,
             note="dv = v(rug back edge) - v(basket bottom contour) in the basket's columns where the rug exists; "
                  "+ = rug edge below the basket bottom"),
        "report (expected 0.0015)", False, "both are floor-contact lines; judge by eye",
        expected=cfg["checks"][18]["expected"])

    # C20 tangents (< 0.02) between visible silhouettes
    big = ["sofa", "coffee-table", "armchair", "framed-art", "planter", "planter-crown", "floor-lamp", "pouf",
           "magazine-holder", "wall-decor", "basket", "rug", "curtains", "wall-sconce", "pendant"]
    tang = []
    for i in range(len(big)):
        for j in range(i + 1, len(big)):
            a_, b_ = big[i], big[j]
            if (a_, b_) == ("planter", "planter-crown"):
                continue
            ma_, mb_ = ba.mask_bb(masks[a_]), ba.mask_bb(masks[b_])
            if ma_ is None or mb_ is None:
                continue
            if ma_[0] > mb_[1] + 0.03 or mb_[0] > ma_[1] + 0.03 or ma_[2] > mb_[3] + 0.03 or mb_[2] > ma_[3] + 0.03:
                continue
            g_ = sgap(a_, b_)
            if g_ and (not g_["touching"]) and g_["min_gap_frame_w"] < 0.02:
                tang.append(dict(pair=f"{a_}|{b_}", gap=g_["min_gap_frame_w"], at=g_["closest_points_xy"]))
    chk("C20", "every pair of visible silhouettes closer than 0.02 (not touching)", None, tang, "report", False,
        "object-index pass; touching/overlapping pairs are occlusions and not listed")

    # ---------------- mobile crop 3:5
    mc = cfg["mobile"]
    cu0, cu1 = mc["u"]
    sofa_u = fb["sofa"][:2]
    shade = sb["floor-lamp"]
    mob = dict(crop_u=[cu0, cu1], width=r4(cu1 - cu0),
               art_left_margin=r4(art[0] - cu0), art_right_margin=r4(cu1 - art[1]),
               lamp_stem_to_right_edge=r4(cu1 - stem_u),
               **{"wall-decor_out_by": r4(cu0 - sb["wall-decor"][1])},
               sofa_left_cut_fraction=r4((cu0 - sofa_u[0]) / (sofa_u[1] - sofa_u[0])),
               sofa_right_end_to_right_edge=r4(cu1 - sofa_u[1]),
               shade_cut_fraction=r4(max(0.0, shade[1] - cu1) / (shade[1] - shade[0])),
               basket_cut_fraction=r4(max(0.0, bkb[1] - cu1) / (bkb[1] - bkb[0])),
               pendant_margins=r4([pend[0] - cu0, cu1 - pend[1]]),
               table_left_cut_fraction=r4(max(0.0, cu0 - fb["coffee-table"][0]) / (fb["coffee-table"][1] - fb["coffee-table"][0])))
    exp_m = mc["edges"]
    mob["vs_spec"] = {k: dict(expected=v, measured=mob[k], dev=r4(abs(mob[k] - v)), ok=bool(abs(mob[k] - v) <= TOL + 1e-9))
                      for k, v in exp_m.items()}
    mob["spec_contains"] = mc["contains"]
    mob["under_0_02"] = [k for k in ("art_left_margin", "lamp_stem_to_right_edge") if mob[k] < 0.02] + \
                        (["wall-decor just outside (%.4f)" % mob["wall-decor_out_by"]] if 0 <= mob["wall-decor_out_by"] < 0.02 else [])
    rep["mobile_crop_3_5"] = mob

    rep["luminance_L"] = ba.luminance_report(cfg, cam, rgb, idx) if rgb is not None else None
    fv_fail = [i["key"] for i in fvs if i.get("ok") is False]
    blk_fail = [c["id"] for c in checks if c["result"] == "fail" and c["blocking"]]
    soft_fail = [c["id"] for c in checks if c["result"] == "fail" and not c["blocking"]]
    rep["summary"] = dict(frame_values_outside_0_01=fv_fail, blocking_checks_failed=blk_fail,
                          nonblocking_checks_failed=soft_fail,
                          checks={c["id"]: c["result"] for c in checks},
                          tangents_lt_0_02=[t["pair"] for t in tang],
                          all_blocking_pass=not blk_fail, all_values_within_0_01=not fv_fail)
    return rep


# ---------------------------------------------------------------------------------------
# images
# ---------------------------------------------------------------------------------------
def make_overlay(cfg, cam, clay_path, idx, slots, out_path, fill_alpha=40, note=""):
    from PIL import Image, ImageDraw
    im = Image.open(clay_path).convert("RGB")
    W, H = im.size
    if idx.shape != (H, W):
        raise RuntimeError("index pass size mismatch")
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    yy, xx = np.mgrid[0:H, 0:W]
    dash = ((xx + yy) // max(7, W // 290)) % 2 == 0
    labels, hidden = [], []
    lwid = max(1, W // 1400)
    for name in ba.SLOT_ORDER:
        d = slots[name]
        m = idx == d["pidx"]
        if name == "planter":
            m = m | (idx == ba.CROWN_IDX)
        if not m.any():
            hidden.append(name)
            continue
        col = ba.COLORS[name]
        e = bs._edge(m)
        for _ in range(lwid):
            e = e | (np.roll(e, 1, 1) & m) | (np.roll(e, 1, 0) & m)
        if d["status"] != "firm":
            e = e & dash
        arr = np.zeros((H, W, 4), np.uint8)
        arr[e] = col + (255,)
        fill = np.zeros((H, W, 4), np.uint8)
        fill[m] = col + (fill_alpha,)
        lay = Image.alpha_composite(lay, Image.fromarray(fill))
        lay = Image.alpha_composite(lay, Image.fromarray(arr))
        ys, xs = np.nonzero(m)
        st = cfg["slots"].get(name, {}).get("spec_status", "approx")
        tag = name + (" ~" if st == "approx" else "")
        labels.append((int(np.median(xs)), int(ys.min()), tag, col))
    dr = ImageDraw.Draw(lay)
    for n in ("sofa", "coffee-table", "armchair"):
        col = (40, 90, 200)
        m = idx == bs.PASS_INDEX[n]
        if not m.any():
            continue
        e = bs._edge(m)
        ys, xs = np.nonzero(e)
        dr.point(list(zip(xs.tolist(), ys.tolist())), fill=col + (255,))
        ys, xs = np.nonzero(m)
        labels.append((int(np.median(xs)), int(np.median(ys)), n, col))
    fnt = ba.font(max(13, W // 105))
    placed = []
    for x, y, tag, col in sorted(labels, key=lambda t: t[1]):
        bbx = dr.textbbox((0, 0), tag, font=fnt)
        tw, th = bbx[2] - bbx[0], bbx[3] - bbx[1]
        x0, y0 = min(max(4, x - tw // 2), W - tw - 6), max(4, y - th - 8)
        for _ in range(30):
            if all(x0 + tw + 6 < a or x0 - 6 > c or y0 + th + 4 < b or y0 - 4 > d_ for a, b, c, d_ in placed):
                break
            y0 += th + 6
        placed.append((x0, y0, x0 + tw, y0 + th))
        dr.rectangle((x0 - 3, y0 - 2, x0 + tw + 3, y0 + th + 4), fill=(255, 255, 255, 215))
        dr.text((x0, y0 - bbx[1]), tag, fill=col + (255,), font=fnt)
    C = cfg["camera"]
    hy = P(cam, (C["loc"][0] - 5 * math.sin(math.radians(C["yaw"])), C["loc"][1] - 5 * math.cos(math.radians(C["yaw"])),
                 C["loc"][2]))[1] * H
    for x in range(0, W, max(24, W // 85)):
        dr.line([(x, hy), (x + max(12, W // 170), hy)], fill=(0, 0, 0, 130), width=max(1, W // 2000))
    lw = max(2, W // 700)
    u0, u1 = cfg["mobile"]["u"]
    x0, x1 = u0 * W, u1 * W
    dr.rectangle((x0, 1, x1, H - 2), outline=(255, 255, 255, 240), width=lw + 1)
    dr.rectangle((x0 - lw, 1 - lw, x1 + lw, H - 2 + lw), outline=(30, 30, 30, 200), width=1)
    leg = [f"v4 {cfg['id']}  overlay: solid = firm / closed, dashed + ~ = approx (relative to furniture)" + (f"  {note}" if note else ""),
           f"white frame = 3:5 mobile crop u {u0}-{u1} (full height); dotted line = horizon (camera z 1.20)"]
    if hidden:
        leg.append("not visible in this frame: " + ", ".join(hidden))
    f2 = ba.font(max(12, W // 140), bold=False)
    y = H - 10 - len(leg) * (f2.size + 6)
    for t in leg:
        bbx = dr.textbbox((10, y), t, font=f2)
        dr.rectangle((bbx[0] - 4, bbx[1] - 2, bbx[2] + 4, bbx[3] + 2), fill=(255, 255, 255, 210))
        dr.text((10, y), t, fill=(20, 20, 20, 255), font=f2)
        y += f2.size + 6
    Image.alpha_composite(im.convert("RGBA"), lay).convert("RGB").save(out_path)
    return hidden


def make_plan(cfg, cam, slots, out_path):
    from PIL import Image, ImageDraw
    res = ba.render_plan(dict(cfg, id="B"), cam, slots, out_path)     # "B" = room/hall extent of the B plan
    img = Image.open(out_path).convert("RGB")
    dr = ImageDraw.Draw(img)
    fnt = ba.font(20)
    R = cfg["room"]
    lbl = (f"v4 {cfg['id']}  room {R['x_right'] - R['x_left']:.2f} x {R['y_front'] - R['y_back']:.2f} x {R['h']:.2f} m"
           f"   armchair ({cfg['chair']['cx']}, {cfg['chair']['cy']})   sill {cfg['window']['z0']:.2f}")
    dr.rectangle((8, 8, 30 + dr.textlength(lbl, font=fnt), 40), fill=(255, 255, 255))
    dr.text((16, 12), lbl, fill=(20, 20, 20), font=fnt)
    img.save(out_path)
    return res


def make_compare(out_dir, cfgs):
    from PIL import Image, ImageDraw
    cols = list(VARIANTS)
    pad, title = 24, 58
    cw = 1024                       # full frame tile width
    ch = 576
    crop_w = int(round(cw * 0.55 / 0.55))   # left zone crop shown at the same tile width
    ft, fs = ba.font(32), ba.font(20, bold=False)
    zone_h = int(round(crop_w / (0.55 * 2048) * 1152))
    sheet_w = pad + len(cols) * (cw + pad)
    sheet_h = pad + title + zone_h + pad + title + ch + pad + 70
    sheet = Image.new("RGB", (sheet_w, sheet_h), (246, 244, 240))
    dr = ImageDraw.Draw(sheet)
    for i, c in enumerate(cols):
        src = os.path.join(out_dir, c, "clay-proxies.png")
        im = Image.open(src).convert("RGB")
        W, H = im.size
        x = pad + i * (cw + pad)
        # row 1: left zone u 0-0.55, full height
        z = im.crop((0, 0, int(round(0.55 * W)), H)).resize((crop_w, zone_h), Image.LANCZOS)
        sheet.paste(z, (x, pad + title))
        notes = {"L0": "L0  B as presented (reference)", "L1": "L1  armchair -24 cm X, posts 0.455",
                 "L2": "L2  = L1 + window sill 0.75 (needs user approval)"}
        dr.text((x, pad + 10), notes[c], fill=(25, 25, 25), font=ft)
        # row 2: full frame with the 3:5 crop
        y2 = pad + title + zone_h + pad
        f_ = im.resize((cw, ch), Image.LANCZOS)
        d2 = ImageDraw.Draw(f_)
        u0, u1 = cfgs[c]["mobile"]["u"]
        d2.rectangle((u0 * cw - 1, 0, u1 * cw + 1, ch - 1), outline=(40, 40, 40), width=1)
        d2.rectangle((u0 * cw, 1, u1 * cw, ch - 2), outline=(255, 255, 255), width=3)
        sheet.paste(f_, (x, y2 + title))
        sc = json.load(open(os.path.join(out_dir, c, "selfcheck.json")))
        s = sc["summary"]
        txt = (f"{c}: blocking fails {', '.join(s['blocking_checks_failed']) or 'none'}"
               f"   values >0.01: {', '.join(s['frame_values_outside_0_01']) or 'none'}")
        dr.text((x, y2 + 12), txt, fill=(25, 25, 25), font=fs)
    dr.text((pad, sheet_h - 50), "Row 1: left zone u 0.00-0.55, full height (clay with solid slot proxies). "
            "Row 2: full frame; white frame = 3:5 mobile crop u 0.567-0.9045.", fill=(70, 70, 70), font=fs)
    p = os.path.join(out_dir, "compare.jpg")
    sheet.save(p, quality=90)
    return p


# ---------------------------------------------------------------------------------------
# runs
# ---------------------------------------------------------------------------------------
def run_variant(cfg, a, spec, passes):
    from PIL import Image
    out = os.path.join(a.out, cfg["id"])
    os.makedirs(out, exist_ok=True)
    tmp = os.path.join(passes, cfg["id"])
    roots, cam = build_base(cfg, a)
    clay = os.path.join(out, "clay.png")
    _, idx_e, _ = render(clay, tmp)
    slots = ba.build_slots(cfg)
    bpy.context.view_layer.update()
    clayp = os.path.join(out, "clay-proxies.png")
    _, idx, _ = render(clayp, tmp)
    rgb = np.asarray(Image.open(clay).convert("RGB"))
    rep = self_check(cfg, cam, roots, slots, idx, rgb, spec)
    rep["empty_clay_object_indices"] = sorted(int(x) for x in np.unique(idx_e))
    rep["render"] = dict(engine="Cycles CPU 4.2", samples=a.samples, res=[a.res, int(round(a.res * 9 / 16))],
                         sky_strength=a.sky, exposure=a.exposure, view="AgX, Medium High Contrast", seed=7,
                         light="sky only, through the window (no sun, no lamps)", palette=ba.PAL,
                         clay="clay.png: shell + sofa, coffee table, armchair (as M0); clay-proxies.png: + 16 slot proxies")
    rep["overlay_not_visible"] = make_overlay(cfg, cam, clayp, idx, slots, os.path.join(out, "overlay.png"))
    rep["plan"] = make_plan(cfg, cam, slots, os.path.join(out, "plan.png"))
    with open(os.path.join(out, "selfcheck.json"), "w") as fh:
        json.dump(rep, fh, indent=2, ensure_ascii=False)
    return rep


def run_m0(cfg, a, spec, passes):
    """M0 input set for one variant, at the top level. Clay = shell + 3 fixed furniture pieces only."""
    from PIL import Image
    out = a.m0_out
    os.makedirs(out, exist_ok=True)
    tmp = os.path.join(passes, "m0")
    res = a.m0_res
    roots, cam = build_base(cfg, a, res=res, samples=a.m0_samples)
    clay4k = os.path.join(out, "m0-clay-4k.png")
    depth, idx_e, normal = render(clay4k, tmp)
    Image.open(clay4k).resize((2048, 1152), Image.LANCZOS).save(os.path.join(out, "m0-clay.png"))
    valid = np.isfinite(depth) & (depth < 1e3)
    mm = np.where(valid, np.clip(np.rint(depth * 1000.0), 0, 65534), 65535).astype(np.uint16)
    bs.write_png16(os.path.join(out, "m0-depth.png"), mm)
    invd = np.where(valid, 1.0 / np.maximum(depth, 0.05), 0.0)
    nb = np.clip(invd / invd[valid].max(), 0, 1)
    bs.write_png16(os.path.join(out, "m0-depth-nearbright.png"), np.rint(nb * 65535))
    shutil.copy(os.path.join(tmp, "Depth_0001.exr"), os.path.join(out, "m0-depth.exr"))
    bs.make_lines(depth, idx_e, normal, os.path.join(out, "m0-lines.png"))
    H, W = depth.shape
    C = cfg["camera"]
    yaw = math.radians(C["yaw"])
    f = (-math.sin(yaw), -math.cos(yaw), 0.0)

    def planar(p):
        return sum((p[i] - C["loc"][i]) * f[i] for i in range(3))

    dchk = {}
    for nm, p in (("back wall above the sofa (0.20, 0, 2.40)", (0.20, 0.0, 2.40)),
                  ("back wall near the corner (-2.00, 0, 2.20)", (-2.00, 0.0, 2.20)),
                  ("left wall front of the window (-2.30, 3.30, 2.00)", (-2.30, 3.30, 2.00)),
                  ("floor (0.20, 3.40, 0)", (0.20, 3.40, 0.0))):
        u, v, _ = P(cam, p)
        px = depth[min(H - 1, int(v * H)), min(W - 1, int(u * W))]
        dchk[nm] = dict(uv=r4([u, v]), measured_m=round(float(px), 4), expected_planar_m=round(planar(p), 4),
                        dev_m=round(abs(float(px) - planar(p)), 4))
    # edge sharpness: across every horizontal furniture/background transition with a depth jump > 0.3 m, the two
    # pixels must carry the depth of their own side (no blended in-between values)
    fur_m = np.isin(idx_e, [bs.PASS_INDEX[n] for n in roots])
    trans = fur_m[:, :-1] != fur_m[:, 1:]
    ys, xs = np.nonzero(trans)
    n_tr, n_mix = 0, 0
    for y, x in zip(ys, xs):
        if x < 1 or x + 2 >= W:
            continue
        a0_, a1_, b1_, b0_ = depth[y, x - 1], depth[y, x], depth[y, x + 1], depth[y, x + 2]
        if not (np.isfinite(a0_) and np.isfinite(b0_)) or abs(a0_ - b0_) < 0.3:
            continue
        n_tr += 1
        if abs(a1_ - a0_) > 0.05 * max(a0_, 0.1) and abs(a1_ - b0_) > 0.05 * max(b0_, 0.1):
            n_mix += 1
        elif abs(b1_ - b0_) > 0.05 * max(b0_, 0.1) and abs(b1_ - a0_) > 0.05 * max(a0_, 0.1):
            n_mix += 1
    edge_sharp = dict(transitions_checked=n_tr, pixels_with_blended_depth=n_mix,
                      ok=bool(n_tr > 0 and n_mix <= 0.002 * n_tr))
    blend = os.path.join(out, "m0-blockout.blend")
    # proxies for the overlay and the self-check (index pass only, 1 sample): not in the M0 clay
    slots = ba.build_slots(cfg)
    bpy.context.view_layer.update()
    _, idx, _ = render(os.path.join(tmp, "proxy-index.png"), tmp, samples=1, denoise=False)
    rgb = np.asarray(Image.open(clay4k).convert("RGB"))
    rep = self_check(cfg, cam, roots, slots, idx, rgb, spec)
    rep["m0"] = dict(
        variant=cfg["id"], clay="m0-clay-4k.png (3840x2160) / m0-clay.png (2048x1152 Lanczos): shell + sofa, coffee "
                                "table, armchair only. No slot products, no curtains, rug or lamps (m0-prompt 2.0 / M0-09)",
        object_indices_in_clay=sorted(int(x) for x in np.unique(idx_e)),
        object_indices_expected="0 sky, 1 sofa, 2 table, 3 armchair, 4 window, 5-12 shell, 13 cornice, 14 reveal",
        products_in_clay=bool(any(int(x) >= ba.SLOT_IDX0 for x in np.unique(idx_e))),
        depth_checks=dchk, depth_edge_sharpness=edge_sharp,
        depth_note="m0-depth.png uint16 mm, planar camera Z; 65535 = sky; Depth pass from Cycles (not filtered across "
                   "object edges: one sample per pixel for data passes)",
        overlay="m0-clay-overlay.png: the empty M0 clay with the 16 slot proxies as outlines + translucent fills "
                "(index pass of a proxy scene, 1 sample)")
    rep["render"] = dict(engine="Cycles CPU 4.2", samples=a.m0_samples, res=[res, int(round(res * 9 / 16))],
                         sky_strength=a.sky, exposure=a.exposure, view="AgX, Medium High Contrast", seed=7,
                         palette=ba.PAL)
    make_overlay(cfg, cam, clay4k, idx, slots, os.path.join(out, "m0-clay-overlay.png"), fill_alpha=70,
                 note="(proxies drawn on the empty M0 clay)")
    rep["plan"] = make_plan(cfg, cam, slots, os.path.join(out, "plan.png"))
    with open(os.path.join(out, "m0-selfcheck.json"), "w") as fh:
        json.dump(rep, fh, indent=2, ensure_ascii=False)
    # camera json
    Hh = int(round(res * 9 / 16))
    ppu, ppv, _ = P(cam, (C["loc"][0] + 5 * f[0], C["loc"][1] + 5 * f[1], C["loc"][2]))
    camj = dict(
        version="v4 / " + cfg["id"], location_m=list(C["loc"]), yaw_deg_left=C["yaw"],
        forward=[round(f[0], 5), round(f[1], 5), 0.0], right=[round(math.cos(yaw), 5), round(-math.sin(yaw), 5), 0.0],
        look="level (tilt 0, roll 0), heading from -Y turned 25 deg toward -X",
        blender_rotation_euler_deg=[90, 0, round(180 - C["yaw"], 4)], mirrored_scale_x=-1.0,
        lens_mm=C["lens"], sensor_mm=[36.0, 20.25], sensor_fit="HORIZONTAL",
        shift_x=C["shift_x"], shift_x_mm=round(C["shift_x"] * 36, 4), shift_y=C["shift_y"], shift_y_mm=round(C["shift_y"] * 36, 4),
        hfov_deg=round(math.degrees(2 * math.atan(18 / C["lens"])), 3), vfov_deg=round(math.degrees(2 * math.atan(10.125 / C["lens"])), 3),
        resolution=[res, Hh],
        intrinsics_px=dict(fx=C["lens"] / 36 * res, fy=C["lens"] / 36 * res, cx=round(ppu * res, 2), cy=round(ppv * Hh, 2)),
        principal_point_measured_uv=[round(ppu, 5), round(ppv, 5)],
        projection_24mm=spec["conventions"]["projection_24mm"],
        h0=cfg["h0"], window=dict(cfg["window"]), armchair=dict(cfg["chair"]),
        depth=dict(file="m0-depth.png", type="uint16", unit="mm", kind="planar camera Z (distance to the camera plane)",
                   sky_value=65535, exr="m0-depth.exr (float32 metres, same values)",
                   nearbright="m0-depth-nearbright.png: 1/depth normalised, 16-bit, near = bright, not metric"),
        note="cx, cy measured by projecting the optical axis (mirrored rig: shift_x < 0 moves the principal point right).")
    with open(os.path.join(out, "m0-camera.json"), "w") as fh:
        json.dump(camj, fh, indent=2)
    # blend: the M0 scene; proxies kept in their own collection, excluded from render
    for o in bpy.data.collections["proxies"].all_objects:
        o.hide_render = True
    bpy.data.collections["proxies"].hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    if os.path.exists(blend + "1"):
        os.remove(blend + "1")
    return rep


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--res", type=int, default=2048)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--m0", default="", help="variant for the top-level M0 input set (e.g. L2)")
    ap.add_argument("--m0-only", action="store_true")
    ap.add_argument("--m0-out", default=HERE)
    ap.add_argument("--m0-res", type=int, default=3840)
    ap.add_argument("--m0-samples", type=int, default=256)
    ap.add_argument("--passes-dir", default="")
    ap.add_argument("--compare-only", action="store_true")
    a = ap.parse_args(argv)
    spec = json.load(open(SPEC_PATH))
    cfgs = {v: v4_config(spec, v) for v in VARIANTS}
    passes = a.passes_dir or tempfile.mkdtemp(prefix="v4-passes-")
    os.makedirs(a.out, exist_ok=True)
    if not a.compare_only and not a.m0_only:
        for v in a.variants.split(","):
            rep = run_variant(cfgs[v], a, spec, passes)
            print(v, json.dumps(rep["summary"], ensure_ascii=False), flush=True)
    if all(os.path.exists(os.path.join(a.out, c, "selfcheck.json")) for c in VARIANTS) and not a.m0_only:
        print("compare:", make_compare(a.out, cfgs))
    if a.m0:
        rep = run_m0(cfgs[a.m0], a, spec, passes)
        print("M0", a.m0, json.dumps(rep["summary"], ensure_ascii=False), flush=True)
    if not a.passes_dir:
        shutil.rmtree(passes, ignore_errors=True)


if __name__ == "__main__":
    main()
