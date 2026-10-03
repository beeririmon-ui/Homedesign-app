#!/usr/bin/env python3
"""
Clay comparison of the living-room alternatives A, B, C (+ B-low) from alts-2026-10-03.json
(review-designer.md 7.11). Also re-renders the v3 baseline in the same clay style ("v3") so the
comparison sheet is like-for-like.

build_scene.py (v3) is NOT modified: it is imported only for its geometry helpers
(box, cone, superellipse slab, sofa / table / armchair builders, projection, EXR loader,
silhouette gap). Running build_scene.py on its own still reproduces v3 exactly.

Outputs (per alternative): alts/<id>/clay.png (2048x1152), overlay.png, plan.png, selfcheck.json
and alts/compare.jpg. Render passes (EXR) go to a temp dir outside the repo.

Run:
    python3 build_alts.py                      # all: v3 A B C B-low, 2048 px, 64 samples
    python3 build_alts.py --alts B --res 960 --samples 16 --out /tmp/x   # preview
    python3 build_alts.py --compare-only       # rebuild compare.jpg from existing renders
Same conventions as v3: metres, X right as the camera sees, Y toward the camera, Z up;
camera mirrored (scale.x = -1); Cycles CPU, fixed seed, no adaptive sampling.
"""
import argparse
import json
import math
import os
import random
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import numpy as np  # noqa: E402
import build_scene as bs  # noqa: E402  (v3 helpers; module-level code is constants only)

SPEC_PATH = os.path.join(HERE, "alts-2026-10-03.json")
OUT_DIR = os.path.join(HERE, "alts")
TOL_TASK = 0.01            # art-director acceptance tolerance
TOL_JSON = 0.02            # alts JSON tolerance_expected

# ---------------------------------------------------------------------------------------
# Readable clay palette (light warm greys, slightly different tones per family; no textures)
# ---------------------------------------------------------------------------------------
PAL = dict(
    wall="#DDD8D1", ceiling="#E7E3DD", moulding="#EEEAE4", floor_gap="#8F887F",
    planks=("#C3BAAE", "#BDB4A8", "#C0B7AB", "#B9B0A4"),
    sofa="#D4CEC5", wood="#B4A999", chair="#CDC9C3", oak_lining="#CBBBA5",
    textile="#D9D2C7", rug="#CBC3B6", curtain="#E4DFD7", obj="#C3BCB1", art="#C8C2B9",
    holder="#8E8A84", crown="#A9A69C", shadow_gap="#8A857E", vest="#D0CBC4",
)

SHELL_IDX = dict(bs.PASS_INDEX)
SHELL_IDX.update({"cornice": 13, "lining": 14})
SLOT_IDX0 = 30
SLOT_ORDER = ["framed-art", "pendant", "wall-sconce", "rug", "curtains", "planter", "floor-lamp",
              "basket", "pouf", "magazine-holder", "wall-decor", "sofa-cover", "cushions",
              "table-runner", "vase", "candle-holders"]
CROWN_IDX = 60             # planter envelope (tree crown), separate so the pot can be measured alone


# ---------------------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------------------
def v3_config():
    """v3 baseline expressed in the alternatives format (values from build_scene.py)."""
    F = bs.FUTURE
    return dict(
        id="v3", name="v3 baseline (approved M0, re-rendered in the comparison clay)",
        room=dict(bs.ROOM),
        door=dict(wall="front", x0=-0.45, x1=0.45, h=2.10),
        window=dict(wall="left", a0=0.60, a1=2.40, z0=0.45, z1=2.35, mullion=1.50, mullion_w=0.06,
                    frame_w=0.06, reveal=0.08, sill_proud=0.04, lining="paint"),
        skirting=dict(type="board", h=0.08), cornice=None, planks=dict(w=0.20, len=[1.8, 2.2]),
        camera=dict(loc=list(bs.CAM["loc"]), yaw=0.0, lens=24.0, shift_x=-0.040, shift_y=-0.0625,
                    u0=0.54, v0=0.3889),
        sofa=dict(x0=-1.10, x1=1.10), table=dict(cx=0.0, cy=1.72),
        chair=dict(cx=-1.230, cy=2.821, yaw=-25.0, arm_front_inset=0.0375),
        dx=0.0,
        slots={
            "framed-art": dict(F["framed-art"], status="firm"),
            "pendant": dict(F["pendant"], status="firm"),
            "wall-sconce": dict(F["wall-sconce"], status="firm"),
            "rug": dict(F["rug"], status="firm"),
            "curtains": dict(rod=dict(wall="left", a0=0.35, a1=2.60, z=2.55),
                             stacks=[[0.35, 0.75], [2.25, 2.60]], depth=0.14, status="firm"),
            "planter": dict(F["planter"], status="firm"),
            "floor-lamp": dict(F["floor-lamp"], status="firm"),
            "basket": dict(kind="cyl", c=(1.45, 0.80), r=0.20, z0=0.0, z1=0.45, status="approx"),
            "pouf": dict(F["pouf"], status="firm"),
            "magazine-holder": dict(F["magazine-holder"], status="firm"),
            "wall-decor": dict(kind="box", c=(1.8875, 2.00, 1.475), s=(0.025, 0.90, 0.95), status="approx"),
        },
        expected=dict(back_wall_x=[0.342, 0.749], back_wall_y=[0.095, 0.624], window_x=[0.211, 0.320],
                      sofa_x=[0.397, 0.683], **{"framed-art_x": [0.454, 0.626]}),
        checks=[], mobile_crop=[dict(name="sofa", center_u=0.54, width=0.316)],
    )


def alt_config(spec, aid):
    if aid == "B-low":
        cfg = alt_config(spec, "B")
        ov = spec["alternatives"]["B"]["optional_variant"]
        cfg["id"] = "B-low"
        cfg["name"] = "B with the camera at chest height (1.05 m, v0 0.48), clay only"
        cfg["camera"]["loc"][2] = ov["camera_z"]
        cfg["camera"]["v0"] = ov["v0"]
        cfg["camera"]["shift_y"] = round((ov["v0"] - 0.5) * 9 / 16, 6)
        cfg["expected_note"] = "B expected values are for z 1.20; B-low reports measured values and deltas only"
        return cfg
    a = spec["alternatives"][aid]
    sh = a["shell"]
    w = sh["windows"][0]
    if w["wall"] == "left":
        win = dict(wall="left", a0=w["y0"], a1=w["y1"], mullion=w["mullion_y"])
    else:
        win = dict(wall="back", a0=w["x0"], a1=w["x1"], mullion=w["mullion_x"])
    win.update(z0=w["z0"], z1=w["z1"], mullion_w=w["mullion_w"], frame_w=w["frame_w"],
               reveal=w["reveal_depth"], sill_proud=w["sill_proud"],
               lining="oak" if w.get("reveal_finish", "").startswith("oak") else "paint")
    if "skirting" in sh:
        sk = dict(type="shadow-gap", h=sh["skirting"]["h"], recess=sh["skirting"]["recess"])
    else:
        sk = dict(type="board", h=sh["skirting_h"])
    c = a["camera"]
    ff = a["fixed_furniture"]
    slots = {}
    for k, v in a["slots"].items():
        slots[k] = dict(v)
    cur = slots["curtains"]
    rod = cur["rod"]
    if rod["wall"] == "left":
        cur["rod"] = dict(wall="left", a0=rod["y0"], a1=rod["y1"], z=rod["z"])
        cur["stacks"] = cur.pop("stacks_y")
    else:
        cur["rod"] = dict(wall="back", a0=rod["x0"], a1=rod["x1"], z=rod["z"])
        cur["stacks"] = cur.pop("stacks_x")
    mc = a["mobile_crop"]
    mc = mc if isinstance(mc, list) else [dict(mc, name="main")]
    return dict(
        id=aid, name=a["name"], room=dict(a["room"]), door=dict(sh["door"]), window=win, skirting=sk,
        cornice=sh.get("cornice"), planks=dict(w=sh["floor_planks"]["w"], len=sh["floor_planks"]["len"]),
        camera=dict(loc=list(c["loc"]), yaw=c["yaw_deg_left"], lens=c["lens"], shift_x=c["shift_x"],
                    shift_y=c["shift_y"], u0=c["u0"], v0=c["v0"]),
        h0=a.get("h0"),
        sofa=dict(x0=ff["sofa"]["x0"], x1=ff["sofa"]["x1"]), table=dict(cx=ff["table"]["cx"], cy=ff["table"]["cy"]),
        chair=dict(cx=ff["armchair"]["cx"], cy=ff["armchair"]["cy"], yaw=ff["armchair"]["yaw_deg"],
                   arm_front_inset=ff["armchair"]["arm_front_inset"]),
        dx=(ff["sofa"]["x0"] + ff["sofa"]["x1"]) / 2.0,
        slots=slots, expected=dict(a["expected"]), checks=list(a["checks"]), mobile_crop=mc,
    )


# ---------------------------------------------------------------------------------------
# scene building
# ---------------------------------------------------------------------------------------
M = {}


def mats():
    M.clear()
    for k, v in PAL.items():
        if k == "planks":
            M["planks"] = [bs.make_mat(f"plank{i}", h, 0.85) for i, h in enumerate(v)]
        else:
            M[k] = bs.make_mat(k, v, 0.9)


class Shell:
    def __init__(self, cfg):
        self.cfg = cfg
        R = cfg["room"]
        self.xl, self.xr, self.yb, self.yf, self.h = R["x_left"], R["x_right"], R["y_back"], R["y_front"], R["h"]
        win = cfg["window"]
        self.t = {"left": 0.15, "right": 0.15, "back": 0.15, "front": 0.15}
        self.t[win["wall"]] = max(0.25, win["reveal"] + 0.12)

    def wbox(self, name, wall, s0, s1, n0, n1, z0, z1, mat, pidx, group="shell"):
        """Box in wall-local coords: s along the wall, n into the wall from the room face (outward)."""
        if wall == "left":
            return bs.box(name, self.xl - n1, self.xl - n0, s0, s1, z0, z1, mat, group, pidx=pidx)
        if wall == "right":
            return bs.box(name, self.xr + n0, self.xr + n1, s0, s1, z0, z1, mat, group, pidx=pidx)
        if wall == "back":
            return bs.box(name, s0, s1, self.yb - n1, self.yb - n0, z0, z1, mat, group, pidx=pidx)
        return bs.box(name, s0, s1, self.yf + n0, self.yf + n1, z0, z1, mat, group, pidx=pidx)

    def wall_span(self, wall):
        t = self.t
        if wall in ("left", "right"):
            return self.yb, self.yf
        return self.xl - t["left"], self.xr + t["right"]

    def wall(self, wall, opening=None, pad=0.0):
        s_lo, s_hi = self.wall_span(wall)
        pidx = SHELL_IDX[{"left": "left-wall", "right": "right-wall", "back": "back-wall", "front": "front-wall"}[wall]]
        t = self.t[wall]
        if wall in ("back", "front"):
            t_ext = t
        else:
            t_ext = t
        if opening is None:
            self.wbox(f"wall_{wall}", wall, s_lo, s_hi, 0, t_ext, 0, self.h, M["wall"], pidx)
            return
        a0, a1, z0, z1 = opening
        a0, a1, z0, z1 = a0 - pad, a1 + pad, z0 - pad, z1 + pad
        self.wbox(f"wall_{wall}_a", wall, s_lo, a0, 0, t_ext, 0, self.h, M["wall"], pidx)
        self.wbox(f"wall_{wall}_b", wall, a1, s_hi, 0, t_ext, 0, self.h, M["wall"], pidx)
        if z0 > 0:
            # stop under the sill (no coplanar faces with the sill top: they render black in Cycles)
            zb = z0 + pad - max(pad, 0.025) if wall != "front" else z0
            self.wbox(f"wall_{wall}_below", wall, a0, a1, 0, t_ext, 0, zb, M["wall"], pidx)
        if z1 < self.h:
            self.wbox(f"wall_{wall}_above", wall, a0, a1, 0, t_ext, z1, self.h, M["wall"], pidx)

    def build(self):
        cfg = self.cfg
        xl, xr, yb, yf, h, t = self.xl, self.xr, self.yb, self.yf, self.h, self.t
        win, door = cfg["window"], cfg["door"]
        g = "shell"
        # floor base (dark, shows through the plank joints) and ceiling
        bs.box("floor_base", xl - t["left"], xr + t["right"], yb - t["back"], yf + t["front"], -0.12, -0.002,
               M["floor_gap"], g, pidx=SHELL_IDX["floor"])
        bs.box("ceiling", xl - t["left"], xr + t["right"], yb - t["back"], yf + t["front"], h, h + 0.15,
               M["ceiling"], g, pidx=SHELL_IDX["ceiling"])
        self.planks()
        lin = 0.02 if win["lining"] == "oak" else 0.0
        wopen = (win["a0"], win["a1"], win["z0"], win["z1"])
        for w in ("left", "right", "back"):
            self.wall(w, wopen if win["wall"] == w else None, pad=lin)
        self.wall("front", (door["x0"], door["x1"], 0.0, door["h"]))
        self.vestibule()
        self.window(lin)
        self.skirting()
        if cfg.get("cornice"):
            self.cornice(cfg["cornice"]["h"])

    def planks(self):
        P = self.cfg["planks"]
        rnd = random.Random(11)
        w, (lmin, lmax) = P["w"], P["len"]
        gap = 0.003
        x = self.xl - 0.02
        col = 0
        while x < self.xr:
            y = self.yb - 0.02 - rnd.uniform(0, lmax)
            while y < self.yf + 0.05:
                L = rnd.uniform(lmin, lmax)
                y0, y1 = max(y, self.yb - 0.02), min(y + L, self.yf + 0.05)
                if y1 - y0 > 0.05:
                    bs.box(f"plank_{col}", x + gap / 2, min(x + w, self.xr + 0.02) - gap / 2, y0 + gap / 2,
                           y1 - gap / 2, -0.012, 0.0, rnd.choice(M["planks"]), "floor", pidx=SHELL_IDX["floor"])
                y += L
            x += w
            col += 1

    def vestibule(self):
        d = self.cfg["door"]
        yf, t = self.yf, self.t["front"]
        if self.cfg["id"] in ("B", "B-low"):
            hx0, hx1, hy1 = 0.80, 3.60, 9.80        # entrance hall containing the E0 path (JSON h0 note)
        else:
            hx0, hx1, hy1 = d["x0"] - 0.6, d["x1"] + 0.6, yf + t + 1.2
        hh = d["h"] + 0.30
        y0 = yf + t
        pf = SHELL_IDX["front-wall"]
        bs.box("hall_floor", hx0 - 0.1, hx1 + 0.1, y0, hy1 + 0.1, -0.10, 0, M["floor_gap"], "shell", pidx=pf)
        bs.box("hall_ceiling", hx0 - 0.1, hx1 + 0.1, y0, hy1 + 0.1, hh, hh + 0.1, M["vest"], "shell", pidx=pf)
        bs.box("hall_left", hx0 - 0.1, hx0, y0, hy1, 0, hh, M["vest"], "shell", pidx=pf)
        bs.box("hall_right", hx1, hx1 + 0.1, y0, hy1, 0, hh, M["vest"], "shell", pidx=pf)
        bs.box("hall_back", hx0 - 0.1, hx1 + 0.1, hy1, hy1 + 0.1, 0, hh, M["vest"], "shell", pidx=pf)

    def window(self, lin):
        W = self.cfg["window"]
        wall = W["wall"]
        a0, a1, z0, z1 = W["a0"], W["a1"], W["z0"], W["z1"]
        fw, fd, rev = W["frame_w"], 0.07, W["reveal"]
        pw, g = SHELL_IDX["window"], "window"
        n0, n1 = rev, rev + fd
        mm = M["moulding"]
        self.wbox("win_frame_bottom", wall, a0, a1, n0, n1, z0, z0 + fw, mm, pw, g)
        self.wbox("win_frame_top", wall, a0, a1, n0, n1, z1 - fw, z1, mm, pw, g)
        self.wbox("win_frame_a", wall, a0, a0 + fw, n0, n1, z0, z1, mm, pw, g)
        self.wbox("win_frame_b", wall, a1 - fw, a1, n0, n1, z0, z1, mm, pw, g)
        m, mw = W["mullion"], W["mullion_w"]
        self.wbox("win_mullion", wall, m - mw / 2, m + mw / 2, n0, n1, z0, z1, mm, pw, g)
        s = 0.02
        for k, (p, q) in enumerate(((a0 + fw, m - mw / 2), (m + mw / 2, a1 - fw))):
            sn0, sn1 = rev + 0.015, rev + 0.055
            self.wbox(f"win_sash{k}_b", wall, p, q, sn0, sn1, z0 + fw, z0 + fw + s, mm, pw, g)
            self.wbox(f"win_sash{k}_t", wall, p, q, sn0, sn1, z1 - fw - s, z1 - fw, mm, pw, g)
            self.wbox(f"win_sash{k}_l", wall, p, p + s, sn0, sn1, z0 + fw, z1 - fw, mm, pw, g)
            self.wbox(f"win_sash{k}_r", wall, q - s, q, sn0, sn1, z0 + fw, z1 - fw, mm, pw, g)
        # reveal lining (oak in C: 2 cm boards inside a 2 cm larger wall cut; painted otherwise)
        if lin > 0:
            pl, lm = SHELL_IDX["lining"], M["oak_lining"]
            self.wbox("lining_a", wall, a0 - lin, a0, 0, rev, z0 - lin, z1 + lin, lm, pl, g)
            self.wbox("lining_b", wall, a1, a1 + lin, 0, rev, z0 - lin, z1 + lin, lm, pl, g)
            self.wbox("lining_top", wall, a0, a1, 0, rev, z1, z1 + lin, lm, pl, g)
        else:
            # painted deep reveal in the moulding tone (separate tone from the wall face)
            pl = SHELL_IDX["lining"]
            e = 0.002
            self.wbox("reveal_a", wall, a0, a0 + e, 0, rev, z0, z1, mm, pl, g)
            self.wbox("reveal_b", wall, a1 - e, a1, 0, rev, z0, z1, mm, pl, g)
            self.wbox("reveal_top", wall, a0, a1, 0, rev, z1 - e, z1, mm, pl, g)
        # inner sill: top at z0, proud into the room, 5 cm ears past the opening
        self.wbox("win_sill", wall, a0 - 0.05, a1 + 0.05, -W["sill_proud"], self.t[wall], z0 - 0.025, z0,
                  M["oak_lining"] if lin > 0 else mm, SHELL_IDX["sill"], g)

    def skirting(self):
        sk = self.cfg["skirting"]
        d = self.cfg["door"]
        h = sk["h"]
        ps = SHELL_IDX["skirting"]
        if sk["type"] == "board":
            n0, n1, mat = -0.015, 0.0, M["moulding"]
        else:   # shadow gap: drawn as a dark 8 cm band flush with the wall face (clay approximation)
            n0, n1, mat = -0.0015, 0.0, M["shadow_gap"]
        for wall in ("back", "left", "right"):
            s_lo, s_hi = ((self.xl, self.xr) if wall == "back" else (self.yb, self.yf))
            self.wbox(f"skirt_{wall}", wall, s_lo, s_hi, n0, n1, 0, h, mat, ps)
        self.wbox("skirt_front_a", "front", self.xl, d["x0"], n0, n1, 0, h, mat, ps)
        self.wbox("skirt_front_b", "front", d["x1"], self.xr, n0, n1, 0, h, mat, ps)

    def cornice(self, ch):
        pc = SHELL_IDX["cornice"]
        for wall in ("back", "left", "right", "front"):
            s_lo, s_hi = ((self.xl, self.xr) if wall in ("back", "front") else (self.yb, self.yf))
            self.wbox(f"cornice_{wall}", wall, s_lo, s_hi, -0.045, 0.0, self.h - ch, self.h, M["moulding"], pc)
            self.wbox(f"cornice2_{wall}", wall, s_lo, s_hi, -0.02, 0.0, self.h - ch - 0.025, self.h - ch,
                      M["moulding"], pc)


def build_furniture(cfg):
    bs.SOFA = dict(bs.SOFA, x0=cfg["sofa"]["x0"], x1=cfg["sofa"]["x1"])
    bs.TABLE = dict(bs.TABLE, cx=cfg["table"]["cx"], cy=cfg["table"]["cy"])
    bs.CHAIR = dict(bs.CHAIR, cx=cfg["chair"]["cx"], cy=cfg["chair"]["cy"], yaw_deg=cfg["chair"]["yaw"],
                    arm_front_inset=cfg["chair"]["arm_front_inset"])
    return {"sofa": bs.build_sofa(M["sofa"], M["wood"]), "coffee-table": bs.build_table(M["wood"]),
            "armchair": bs.build_chair(M["chair"], M["wood"])}


def ellipsoid(name, c, r, z0, z1, mat, group):
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.scale = (r, r, (z1 - z0) / 2)
    ob.location = (c[0], c[1], (z0 + z1) / 2)
    ob.data.materials.append(mat)
    bs.coll(group).objects.link(ob)
    bpy.context.view_layer.update()
    bs.apply_scale(ob)
    mod = ob.modifiers.new("smooth", "SUBSURF")
    mod.levels = mod.render_levels = 1
    for p in me.polygons:
        p.use_smooth = True
    return ob


def build_slots(cfg):
    """Solid clay proxies for all 16 slots. Returns {slot: dict(root, status, main=[objs], extra=[objs])}."""
    g = "proxies"
    S = cfg["slots"]
    dx = cfg["dx"]
    T = bs.TABLE["h"]
    R = cfg["room"]
    out = {}

    def cyl(n, c, r, z0, z1, mat):
        return bs.cone(n, c[0], c[1], z0, z1, r, r, mat, g, verts=64)

    def bx(n, c, s, mat, bevel=0.0):
        return bs.box(n, c[0] - s[0] / 2, c[0] + s[0] / 2, c[1] - s[1] / 2, c[1] + s[1] / 2,
                      c[2] - s[2] / 2, c[2] + s[2] / 2, mat, g, bevel=bevel)

    def put(name, main, extra=(), status=None):
        out[name] = dict(main=list(main), extra=list(extra),
                         status=status or S.get(name, {}).get("status", "approx"))

    s = S["framed-art"]
    put("framed-art", [bx("px_art", s["c"], s["s"], M["art"])])
    s = S["pendant"]
    put("pendant", [cyl("px_pendant", s["c"], s["r"], s["z0"], s["z1"], M["obj"])],
        [cyl("px_cord", s["c"], 0.004, s["z1"], R["h"], M["holder"])])
    s = S["wall-sconce"]
    put("wall-sconce", [bx("px_sconce", s["c"], s["s"], M["holder"])])
    s = S["rug"]
    put("rug", [bx("px_rug", (s["c"][0], s["c"][1], 0.006), (s["s"][0], s["s"][1], 0.012), M["rug"])])
    # curtains: two stacks from the floor to just under the rod, + rod
    s = S["curtains"]
    rod = s["rod"]
    dep = s["depth"]
    objs = []
    for k, (a0, a1) in enumerate(s["stacks"]):
        if rod["wall"] == "left":
            objs.append(bs.box(f"px_curt{k}", R["x_left"], R["x_left"] + dep, a0, a1, 0.01, rod["z"] - 0.03,
                               M["curtain"], g, bevel=0.02))
        else:
            objs.append(bs.box(f"px_curt{k}", a0, a1, R["y_back"], R["y_back"] + dep, 0.01, rod["z"] - 0.03,
                               M["curtain"], g, bevel=0.02))
    if rod["wall"] == "left":
        rod_o = bs.box("px_rod", R["x_left"] + dep / 2 - 0.01, R["x_left"] + dep / 2 + 0.01, rod["a0"], rod["a1"],
                       rod["z"] - 0.01, rod["z"] + 0.01, M["holder"], g)
    else:
        rod_o = bs.box("px_rod", rod["a0"], rod["a1"], R["y_back"] + dep / 2 - 0.01, R["y_back"] + dep / 2 + 0.01,
                       rod["z"] - 0.01, rod["z"] + 0.01, M["holder"], g)
    put("curtains", objs, [rod_o])
    s = S["planter"]
    env = s["envelope"]
    crown = ellipsoid("px_crown", s["c"], env["r"], env["z0"] + 0.15, env["z1"], M["crown"], g)
    trunk = cyl("px_trunk", s["c"], 0.025, s["z1"], env["z0"] + 0.25, M["wood"])
    put("planter", [cyl("px_pot", s["c"], s["r"], s["z0"], s["z1"], M["obj"])], [trunk, crown])
    s = S["floor-lamp"]
    put("floor-lamp", [cyl("px_lamp_shade", s["c"], s["r"], s["z0"], s["z1"], M["curtain"])],
        [cyl("px_lamp_base", s["c"], s["base_r"], 0.0, 0.02, M["holder"]),
         cyl("px_lamp_stem", s["c"], 0.012, 0.02, s["z0"], M["holder"])])
    s = S["basket"]
    put("basket", [cyl("px_basket", s["c"], s["r"], s["z0"], s["z1"], M["obj"])])
    s = S["pouf"]
    put("pouf", [cyl("px_pouf", s["c"], s["r"], s["z0"], s["z1"], M["textile"])])
    s = S["magazine-holder"]
    put("magazine-holder", [bx("px_mh", s["c"], s["s"], M["holder"])])
    s = S["wall-decor"]
    put("wall-decor", [bx("px_walldecor", s["c"], s["s"], M["obj"])])
    # approximate proxies, v3 positions translated by dx (sofa axis)
    put("sofa-cover", [bs.box("px_throw", 0.60 + dx, 0.96 + dx, 0.40, 0.97, 0.44, 0.47, M["textile"], g)], status="approx")
    put("cushions", [bs.box("px_cush_a", -0.92 + dx, -0.42 + dx, 0.36, 0.50, 0.44, 0.90, M["textile"], g, bevel=0.04),
                     bs.box("px_cush_b", 0.42 + dx, 0.92 + dx, 0.36, 0.50, 0.44, 0.90, M["textile"], g, bevel=0.04),
                     bs.box("px_cush_c", 0.55 + dx, 0.85 + dx, 0.50, 0.62, 0.44, 0.74, M["textile"], g, bevel=0.03)],
        status="approx")
    put("table-runner", [bs.box("px_runner", -0.45 + dx, -0.13 + dx, 1.37, 2.07, T, T + 0.004, M["textile"], g)],
        status="approx")
    put("vase", [cyl("px_vase", (0.42 + dx, 1.76), 0.075, T, T + 0.30, M["obj"])], status="approx")
    put("candle-holders", [cyl("px_candle_a", (0.26 + dx, 1.64), 0.045, T, T + 0.27, M["obj"]),
                           cyl("px_candle_b", (0.30 + dx, 1.86), 0.045, T, T + 0.20, M["obj"])], status="approx")
    for i, name in enumerate(SLOT_ORDER):
        d = out[name]
        d["pidx"] = SLOT_IDX0 + i
        d["root"] = bs.parent_group("slot_" + name, d["main"] + d["extra"], d["pidx"], group=g)
    crown.pass_index = CROWN_IDX
    return out


def build_camera(cfg):
    C = cfg["camera"]
    cd = bpy.data.cameras.new("cam_main")
    cd.lens = C["lens"]
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width, cd.sensor_height = 36.0, 20.25
    cd.shift_x, cd.shift_y = C["shift_x"], C["shift_y"]
    cd.clip_start, cd.clip_end = 0.05, 100.0
    cam = bpy.data.objects.new("cam_main", cd)
    cam.location = C["loc"]
    # level camera looking -Y, then turned yaw_deg_left toward -X: forward = (-sin yaw, -cos yaw, 0)
    cam.rotation_euler = (math.radians(90), 0, math.radians(180 - C["yaw"]))
    cam.scale = (-1.0, 1.0, 1.0)          # mirrored rig, as v3
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


# ---------------------------------------------------------------------------------------
# measurement helpers
# ---------------------------------------------------------------------------------------
P = bs.proj
ASP = 9 / 16


def verts(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for ob in objs:
        if ob.type != "MESH":
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        pts.extend([ev.matrix_world @ v.co for v in me.vertices])
        ev.to_mesh_clear()
    return pts


def bb(cam, pts):
    (x0, x1), (y0, y1) = bs.bbox2d(cam, pts)
    return [x0, x1, y0, y1]


def hull(cam, pts):
    return bs._hull2d([(u, v * ASP) for u, v, _ in (P(cam, p) for p in pts)])


def r4(x):
    if isinstance(x, (list, tuple)):
        return [r4(v) for v in x]
    return None if x is None else round(float(x), 4)


def mask_bb(m):
    H, W = m.shape
    if not m.any():
        return None
    ys, xs = np.nonzero(m)
    return [xs.min() / W, (xs.max() + 1) / W, ys.min() / H, (ys.max() + 1) / H]


def wall_entry(cam, wall_x, cz, side, y_hi):
    """Y where the left (u=0) or right (u=1) frame edge meets a side wall at camera height."""
    lo, hi = 0.0, y_hi
    target = 0.0 if side == "left" else 1.0
    f = (lambda u: u > target) if side == "left" else (lambda u: u < target)
    if not f(P(cam, (wall_x, lo, cz))[0]):
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(P(cam, (wall_x, mid, cz))[0]):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def srgb_L(rgb):
    c = np.asarray(rgb, float) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    Y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


def poly_mask(poly_uv, W, H):
    from PIL import Image, ImageDraw
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).polygon([(u * W, v / ASP * H) for u, v in poly_uv], fill=1)
    return np.array(im, bool)


# ---------------------------------------------------------------------------------------
# self-check
# ---------------------------------------------------------------------------------------
def self_check(cfg, cam, roots, slots, idx, clay_rgb):
    H, W = idx.shape
    R, Wn, C = cfg["room"], cfg["window"], cfg["camera"]
    xl, xr, yb, yf, h = R["x_left"], R["x_right"], R["y_back"], R["y_front"], R["h"]
    cz = C["loc"][2]
    E = cfg["expected"] if cfg["id"] != "B-low" else {}
    EB = cfg.get("expected_ref", {})
    rep = dict(alternative=cfg["id"], name=cfg["name"], tolerance_task=TOL_TASK, tolerance_json=TOL_JSON,
               camera=dict(C, mirrored_scale_x=-1.0, blender_rotation_euler_deg=[90, 0, round(180 - C["yaw"], 4)]),
               room=R, image_px=[W, H], frame_values=[], checks=[], notes=[])
    if cfg.get("expected_note"):
        rep["notes"].append(cfg["expected_note"])
    M_ = {}       # measured values by expected key

    def fv(key, measured, how, exp=None):
        exp = E.get(key) if exp is None else exp
        if exp is None and key in EB:
            exp_ref = EB[key]
        else:
            exp_ref = None
        if isinstance(measured, (list, tuple)) and len(measured) == 2 and all(isinstance(x, (int, float)) for x in measured):
            measured = sorted(measured)
        elif isinstance(measured, (list, tuple)) and len(measured) == 2 and all(isinstance(x, (list, tuple)) for x in measured):
            measured = [sorted(x) for x in measured]
        M_[key] = measured
        item = dict(key=key, measured=r4(measured), how=how)
        ex = exp if exp is not None else exp_ref
        if ex is not None and not isinstance(ex, str):
            a = np.array(measured, float).ravel()
            b = np.array(ex, float).ravel()
            if a.shape == b.shape:
                dev = float(np.max(np.abs(a - b)))
                item.update(expected=ex, max_dev=round(dev, 4))
                if exp is not None:
                    item.update(ok_task_0_01=bool(dev <= TOL_TASK + 1e-9), ok_json_0_02=bool(dev <= TOL_JSON + 1e-9))
                else:
                    item["note"] = "delta vs B (z 1.20), informative"
        elif isinstance(ex, str):
            item["expected"] = ex
        rep["frame_values"].append(item)

    def chk(name, ok, measured, required, note=""):
        rep["checks"].append(dict(check=name, ok=ok, measured=measured, required=required, note=note))

    sv = lambda n: verts(slots[n]["main"])                       # noqa: E731
    fur = lambda n: bs.eval_world_verts(roots[n])                # noqa: E731
    # principal point / optical axis
    f = (-math.sin(math.radians(C["yaw"])), -math.cos(math.radians(C["yaw"])))
    ax = (C["loc"][0] + 5 * f[0], C["loc"][1] + 5 * f[1], cz)
    pp = P(cam, ax)
    rep["principal_point_measured"] = r4(pp[:2])
    chk("principal point (u0, v0) from the optical axis", bool(abs(pp[0] - C["u0"]) < 0.003 and abs(pp[1] - C["v0"]) < 0.003),
        r4(pp[:2]), [C["u0"], C["v0"]], "verifies the shift signs on the mirrored rig (tol 0.003)")
    # verticals plumb: same u at z 0 and z h for points on the back wall / left wall
    du = max(abs(P(cam, (x, y, 0))[0] - P(cam, (x, y, h))[0]) for x, y in ((xl, yb), (0.0, yb), (xl, 2.0)))
    chk("verticals plumb (tilt 0, roll 0)", bool(du < 1e-6), r4(du), "0", "max |du| between z 0 and z h of wall verticals")

    # --- shell
    tl, br = P(cam, (xl, yb, h)), P(cam, (xr, yb, 0))
    if cfg["camera"]["yaw"] == 0:
        fv("back_wall_x", [tl[0], br[0]], "projection of the back-wall corners")
        fv("back_wall_y", [tl[1], br[1]], "projection, back wall top/bottom")
        fv("ceiling_band_y", [0.0, tl[1]], "top edge to back-wall top")
        ye = wall_entry(cam, xl, cz, "left", C["loc"][1] - 0.05)
        fv("left_wall_visible_to_y", ye, "left frame edge meets the left wall (camera height)")
        ye = wall_entry(cam, xr, cz, "right", C["loc"][1] - 0.05)
        fv("right_wall_visible_to_y", ye, "right frame edge meets the right wall (camera height)")
    else:
        fv("back_left_corner_u", P(cam, (xl, yb, 1.2))[0], "projection of the back-left corner line")
        rc = P(cam, (xr, yb, 1.2))
        # where the right frame edge meets the back wall
        lo, hi = xl, xr
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if P(cam, (mid, yb, 1.2))[0] < 1 else (lo, mid)
        fv("back_wall_right", [rc[0], lo], "u of back-right corner; X where the right edge cuts the back wall",
           exp="")
        rep["frame_values"][-1]["expected"] = E.get("back_wall_right", "")
        ye = wall_entry(cam, xl, cz, "left", C["loc"][1] - 0.05)
        fv("left_wall_visible_to_y", ye, "left frame edge meets the left wall (camera height)")
        acx = cfg["slots"]["framed-art"]["c"][0]
        fv("ceiling_band_at_art_y", P(cam, (acx, yb, h))[1], "v of the ceiling line above the art centre")
        rep["ceiling_band_wedge"] = dict(at_corner=r4(P(cam, (xl, yb, h))[1]), at_right_edge=r4(P(cam, (lo, yb, h))[1]))
    if Wn["wall"] == "left":
        a, b = P(cam, (xl, Wn["a0"], Wn["z0"])), P(cam, (xl, Wn["a1"], Wn["z0"]))
        c, d = P(cam, (xl, Wn["a0"], Wn["z1"])), P(cam, (xl, Wn["a1"], Wn["z1"]))
        fv("window_x", [a[0], b[0]], "opening at the wall face")
        if "window_head_y" in E or cfg["id"] in ("B-low", "v3"):
            fv("window_head_y", [d[1], c[1]], "head, front edge -> back edge")
            fv("window_sill_y", [a[1], b[1]], "sill, back edge -> front edge")
        head_min = min(c[1], d[1])
        # head cut by the top edge?
        if head_min < 0:
            lo, hi = Wn["a0"], Wn["a1"]
            for _ in range(60):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if P(cam, (xl, mid, Wn["z1"]))[1] >= 0 else (lo, mid)
            cut = (Wn["a1"] - lo) / (Wn["a1"] - Wn["a0"])
            rep["window_head_cut"] = dict(from_y=r4(lo), fraction_of_length=r4(cut))
        else:
            cut = 0.0
            rep["window_head_cut"] = dict(from_y=None, fraction_of_length=0.0)
        win_u = tuple(sorted((a[0], b[0])))
        mull_u = [P(cam, (xl, Wn["mullion"] + s * Wn["mullion_w"] / 2, 1.0))[0] for s in (-1, 1)]
        sill_v = lambda u: a[1] + (b[1] - a[1]) * (u - a[0]) / (b[0] - a[0])   # noqa: E731
    else:
        a, b = P(cam, (Wn["a0"], yb, Wn["z0"])), P(cam, (Wn["a1"], yb, Wn["z1"]))
        fv("window", [[a[0], b[0]], [b[1], a[1]]], "opening on the back wall [[u0,u1],[v_head,v_sill]]")
        head_min = b[1]
        cut = 0.0
        win_u = tuple(sorted((a[0], b[0])))
        mull_u = [P(cam, (Wn["mullion"] + s * Wn["mullion_w"] / 2, yb, 1.0))[0] for s in (-1, 1)]
        sill_v = lambda u: a[1]   # noqa: E731

    # --- furniture
    fb = {n: bb(cam, fur(n)) for n in roots}
    fv("sofa_x", fb["sofa"][:2], "geometry projection (incl. bevel)")
    if "sofa_y" in E or cfg["id"] == "B-low":
        fv("sofa_y", fb["sofa"][2:], "geometry projection")
    fv("coffee-table_x", fb["coffee-table"][:2], "geometry projection") if ("coffee-table_x" in E or cfg["id"] == "B-low") else None
    fv("armchair_approx", [fb["armchair"][:2], fb["armchair"][2:]], "geometry projection (approx expected)")
    masks = {n: idx == bs.PASS_INDEX[n] for n in roots}
    for n in slots:
        masks[n] = idx == slots[n]["pidx"]
    masks["planter-crown"] = idx == CROWN_IDX
    rep["visible_masks"] = {n: r4(mask_bb(m)) for n, m in masks.items()}

    # --- slots
    sb = {n: bb(cam, sv(n)) for n in slots}
    rep["slot_frame_boxes"] = {n: dict(box=r4(sb[n]), status=slots[n]["status"],
                                       in_frame=bool(sb[n][1] > 0 and sb[n][0] < 1 and sb[n][3] > 0 and sb[n][2] < 1))
                               for n in slots}
    if cfg["id"] == "v3":
        fv("framed-art_x", sb["framed-art"][:2], "projection")
    else:
        fv("framed-art", [sb["framed-art"][:2], sb["framed-art"][2:]], "projection")
        fv("pendant", [sb["pendant"][:2], sb["pendant"][2:]], "projection of the shade")
    sc_ = cfg["slots"]["wall-sconce"]["c"]
    spp = P(cam, sc_)
    if "wall-sconce_u" in E:
        fv("wall-sconce_u", spp[0], "plate centre")
    elif cfg["id"] != "v3":
        fv("wall-sconce", [spp[0], spp[1]], "plate centre (u, v)")
    if "rug_front_y" in E:
        fv("rug_front_y", sb["rug"][3], "front edge of the rug")
    if cfg["id"] in ("C",):
        rep["frame_values"].append(dict(key="rug_front", measured=r4(sb["rug"][3]), expected=E.get("rug_front"),
                                        how="v of the rug front edge (>1 = below the frame)"))
    for key, n in (("planter", "planter"),):
        if key in E or cfg["id"] == "B-low":
            fv(key, sb[n][:2], "pot only")
    if cfg["id"] in ("B", "B-low"):
        fv("wall-decor", [sb["wall-decor"][:2], sb["wall-decor"][2:]], "projection")
        fv("pouf", [sb["pouf"][:2], sb["pouf"][2:]], "projection")
        fv("magazine-holder", [sb["magazine-holder"][:2], sb["magazine-holder"][2:]], "projection")
        fv("floor-lamp_shade_x", sb["floor-lamp"][:2], "shade only")
    if "wall-decor_x" in E:
        fv("wall-decor_x", sb["wall-decor"][:2], "projection")

    # --- common derived values
    pend, art = sb["pendant"], sb["framed-art"]
    hp = cfg["slots"]["pendant"]["c"]
    hang_v = P(cam, (hp[0], hp[1], h))[1]
    pend_ok = bool(pend[3] <= 1 / 3 and art[2] - pend[3] >= 0.05)
    lamp_shade = hull(cam, sv("floor-lamp"))
    _pe = cfg["slots"]["planter"]
    crown_pts = [(_pe["c"][0] + _pe["envelope"]["r"] * math.cos(t_), _pe["c"][1] + _pe["envelope"]["r"] * math.sin(t_), z_)
                 for t_ in np.linspace(0, 2 * math.pi, 96) for z_ in (_pe["envelope"]["z0"], _pe["envelope"]["z1"])]
    crown_mesh_pts = verts([o for o in slots["planter"]["extra"] if o.name.startswith("px_crown")])

    def hgap(a_, b_):
        return bs.poly_gap(a_, b_)

    gaps = {}

    def sgap(a_, b_):
        if not masks[a_].any() or not masks[b_].any():
            return None
        g_ = bs.silhouette_gap(idx, *(CROWN_IDX if x == "planter-crown" else (bs.PASS_INDEX[x] if x in roots else slots[x]["pidx"])
                                      for x in (a_, b_)))
        gaps[f"{a_}|{b_}"] = g_
        return g_

    def chair_window():
        ma = masks["armchair"]
        cols = np.nonzero(ma.any(0))[0]
        best, rows_over = -1.0, []
        for cidx in cols:
            u = (cidx + 0.5) / W
            if not (win_u[0] <= u <= win_u[1]):
                continue
            top = np.nonzero(ma[:, cidx])[0].min() / H
            ov = sill_v(u) - top
            best = max(best, ov)
        # rows where the chair silhouette is inside the window opening (above the sill)
        jambs = list(win_u) + mull_u
        dmin = None
        for r in range(H):
            v = (r + 0.5) / H
            xs = np.nonzero(ma[r])[0]
            if not len(xs):
                continue
            e0, e1 = xs.min() / W, (xs.max() + 1) / W
            for e in (e0, e1):
                if win_u[0] - 0.03 <= e <= win_u[1] + 0.03 and v <= sill_v(e):
                    d_ = min(abs(e - j) for j in jambs)
                    dmin = d_ if dmin is None else min(dmin, d_)
        return best, dmin

    ids = cfg["id"]
    if ids in ("A",):
        g_ = sgap("armchair", "sofa")
        chk("armchair-sofa gap >= 0.02", bool(g_ and not g_["touching"] and g_["min_gap_frame_w"] >= 0.02),
            g_ and g_["min_gap_frame_w"], 0.02, "silhouette gap, frame widths (object index pass)")
    if ids in ("A", "B", "B-low", "C"):
        mb = mask_bb(masks["armchair"])
        chk("armchair >= 0.05 from the bottom edge", bool(1 - mb[3] >= 0.05), r4(1 - mb[3]), 0.05)
    if ids == "A":
        ok = cut >= 0.15 or head_min >= 0
        chk("window head cut >= 15% of its length or fully in frame", bool(ok), rep["window_head_cut"], ">= 0.15")
    if ids in ("A", "B", "B-low", "C"):
        chk("pendant fully in the top third, >= 0.05 above the art", pend_ok,
            dict(pendant_bottom_v=r4(pend[3]), art_top_v=r4(art[2]), gap=r4(art[2] - pend[3]), pendant_top_v=r4(pend[2])),
            "bottom <= 0.333, gap >= 0.05")
        chk("hanging point out of frame", bool(hang_v < 0), r4(hang_v), "< 0", f"point ({hp[0]}, {hp[1]}, {h})")
    if ids == "A":
        gd = hgap(hull(cam, sv("wall-decor")), lamp_shade)
        chk("wall-decor vs floor-lamp shade gap >= 0.02", bool(gd >= 0.02), r4(gd), 0.02, "projected hull gap")
        fl = cfg["slots"]["floor-lamp"]
        base = [(fl["c"][0] + fl["base_r"] * math.cos(t), fl["c"][1] + fl["base_r"] * math.sin(t), 0.0)
                for t in np.linspace(0, 2 * math.pi, 96)]
        bv = bb(cam, base)[3]
        chk("pouf top vs floor-lamp base (report)", None, dict(lamp_base_bottom_v=r4(bv), pouf_top_v=r4(sb["pouf"][2]),
                                                              gap=r4(sb["pouf"][2] - bv)), "report (v3 rule: >= 0.02)")
        cu = P(cam, (xl, yb, 0.2))[0]
        chk("planter edge vs back-left corner line (report)", None,
            dict(corner_u=r4(cu), pot_u=r4(sb["planter"][:2]), left_edge_minus_corner=r4(sb["planter"][0] - cu)), "report")
        # E0: door jambs leave the frame along the 3.85 m dolly from H0
        rep["E0"] = e0_jambs(cfg, cam)
        e = rep["E0"]
        chk("E0: door jambs leave the frame at 70-80% of the dolly", bool(0.70 <= e["both_out_at_fraction"] <= 0.80),
            e, "0.70-0.80")
    if ids in ("B", "B-low"):
        cu = P(cam, (xl, yb, 1.2))[0]
        chk("yaw sign (back-left corner at u 0.431)", bool(abs(cu - 0.431) <= TOL_TASK) if ids == "B" else bool(abs(cu - 0.431) <= 0.02),
            r4(cu), 0.431, "~0.61 would mean the yaw sign is flipped")
        g_ = sgap("armchair", "planter")
        pot = hull(cam, sv("planter"))
        pm = poly_mask(pot, W, H)
        vis = float((pm & masks["planter"]).sum() / max(pm.sum(), 1))
        ca = mask_bb(masks["armchair"])
        ovl = min(ca[1], sb["planter"][1]) - max(ca[0], sb["planter"][0])
        ok = bool((g_ and g_["min_gap_frame_w"] >= 0.02) or (ovl >= 0.04 and vis >= 0.65))
        chk("armchair-planter: gap >= 0.02 or overlap >= 0.04 with >= 65% of the pot visible", ok,
            dict(silhouette_gap=g_ and g_["min_gap_frame_w"], horizontal_overlap=r4(ovl), pot_visible=r4(vis)),
            "gap >= 0.02 | (overlap >= 0.04 & visible >= 0.65)")
    if ids in ("B", "B-low", "C"):
        ov, dj = chair_window()
        chk("armchair overlaps the window bottom by >= 0.04", bool(ov >= 0.04), r4(ov), 0.04,
            "max over window columns of (sill line v - armchair top v)")
        chk("armchair silhouette vs jambs / mullion >= 0.02 (no tangent)", bool(dj is None or dj >= 0.02), r4(dj), 0.02,
            "armchair left/right silhouette edges inside the opening vs jamb and mullion lines")
    if ids in ("B", "B-low"):
        sm = masks["sofa"]
        c0, c1 = int(max(0, art[0]) * W), int(min(1, art[1]) * W)
        rows = np.nonzero(sm[:, c0:c1].any(1))[0]
        stop = rows.min() / H if len(rows) else None
        chk("art bottom vs sofa back top >= 0.03", bool(stop is not None and stop - art[3] >= 0.03),
            dict(art_bottom_v=r4(art[3]), sofa_top_v=r4(stop), gap=r4(stop - art[3]) if stop else None), 0.03,
            "sofa top = visible sofa mask in the art's columns")
        mh = hull(cam, sv("magazine-holder"))
        front_stack = [o for o in slots["curtains"]["main"] if o.name.startswith("px_curt1")]
        gcs = hgap(mh, hull(cam, verts(front_stack)))
        chk("magazine-holder vs curtain front stack >= 0.02 and left edge >= 0.05",
            bool(gcs >= 0.02 and sb["magazine-holder"][0] >= 0.05),
            dict(gap_to_front_stack=r4(gcs), left_margin=r4(sb["magazine-holder"][0])), "0.02 / 0.05")
        tt = [P(cam, p) for p in bs.eval_world_verts(roots["coffee-table"]) if p.z > bs.TABLE["h"] - 0.035]
        pu0, pu1 = sb["pouf"][:2]
        sel = [q[1] for q in tt if pu0 <= q[0] <= pu1]
        ttop = max(sel) if sel else max(q[1] for q in tt)
        chk("pouf top vs table top line >= 0.02", bool(sb["pouf"][2] - ttop >= 0.02),
            dict(pouf_top_v=r4(sb["pouf"][2]), table_top_front_v=r4(ttop), gap=r4(sb["pouf"][2] - ttop)), 0.02,
            "pouf top silhouette (far rim) vs the table-top front edge in the pouf's columns; +ve = pouf top below the line")
        wd = hull(cam, sv("wall-decor"))
        g1, g2 = hgap(wd, hull(cam, crown_pts)), hgap(wd, hull(cam, sv("framed-art")))
        g1m = hgap(wd, hull(cam, crown_mesh_pts))
        chk("wall-decor vs tree crown and art >= 0.03", bool(g1 >= 0.03 and g2 >= 0.03),
            dict(to_crown_envelope=r4(g1), to_crown_clay_ellipsoid=r4(g1m), to_art=r4(g2)), 0.03,
            "projected hull gaps; crown = JSON envelope cylinder r 0.40, z 0.45-1.65 (the clay shows a smaller ellipsoid)")
        chk("floor-lamp shade vs right edge >= 0.08", bool(1 - sb["floor-lamp"][1] >= 0.08), r4(1 - sb["floor-lamp"][1]), 0.08)
        chk("window head >= 0.010 below the top edge", bool(head_min >= 0.010), r4(head_min), 0.010)
        rep["E0"] = e0_path_B(cfg)
        chk("E0 path clears the jambs (>= 0.15 m) through the 1.20 opening", bool(rep["E0"]["min_clearance_m"] >= 0.15),
            rep["E0"], 0.15)
    if ids == "C":
        g_ = sgap("armchair", "planter")
        gh = hgap(hull(cam, fur("armchair")), hull(cam, sv("planter")))
        chk("armchair vs planter >= 0.02", bool(g_ and g_["min_gap_frame_w"] >= 0.02 and not g_["touching"]),
            dict(silhouette_gap_pot=g_ and g_["min_gap_frame_w"], hull_gap_pot=r4(gh)), 0.02)
        rv = sb["rug"][3]
        chk("rug front edge not within 0.02 of the bottom edge", bool(abs(rv - 1.0) >= 0.02), r4(rv), "|v - 1| >= 0.02")
        chk("pouf base >= 0.05 from the bottom edge", bool(1 - sb["pouf"][3] >= 0.05), r4(1 - sb["pouf"][3]), 0.05)
        chk("table right end >= 0.05 from the right edge", bool(1 - fb["coffee-table"][1] >= 0.05),
            r4(1 - fb["coffee-table"][1]), 0.05)
        wd = hull(cam, sv("wall-decor"))
        wj = P(cam, (Wn["a1"], yb, 1.0))[0]
        g_j = sb["wall-decor"][0] - wj
        sofa_back = [p for p in fur("sofa") if p.y < 0.40]
        g_s = hgap(wd, hull(cam, sofa_back))
        g_a = hgap(wd, hull(cam, sv("framed-art")))
        chk("wall-decor vs window jamb, sofa back and art >= 0.03", bool(min(g_j, g_s, g_a) >= 0.03),
            dict(to_window_jamb=r4(g_j), to_sofa_back=r4(g_s), to_art=r4(g_a)), 0.03)

    # --- luminance report (clay, sRGB L*)
    rep["luminance_L"] = luminance_report(cfg, cam, clay_rgb, idx)
    # --- tangents (< 0.02) between large items, visible silhouettes
    big = ["sofa", "coffee-table", "armchair", "framed-art", "planter", "planter-crown", "floor-lamp", "pouf",
           "magazine-holder", "wall-decor", "basket", "rug", "curtains"]
    tang = []
    for i in range(len(big)):
        for j in range(i + 1, len(big)):
            a_, b_ = big[i], big[j]
            if (a_, b_) in (("planter", "planter-crown"),):
                continue
            ma_, mb_ = mask_bb(masks[a_]), mask_bb(masks[b_])
            if ma_ is None or mb_ is None:
                continue
            if ma_[0] > mb_[1] + 0.03 or mb_[0] > ma_[1] + 0.03 or ma_[2] > mb_[3] + 0.03 or mb_[2] > ma_[3] + 0.03:
                continue
            key = f"{a_}|{b_}"
            g_ = gaps.get(key) or sgap(a_, b_)
            if g_ and (not g_["touching"]) and g_["min_gap_frame_w"] < 0.02:
                tang.append(dict(pair=key, gap=g_["min_gap_frame_w"], at=g_["closest_points_xy"]))
    rep["tangents_lt_0_02"] = tang
    rep["tangent_note"] = ("pairs whose visible silhouettes come within 0.02 frame widths without touching; "
                           "touching/overlapping pairs (occlusion) are not listed")
    fv_fail = [i["key"] for i in rep["frame_values"] if i.get("ok_task_0_01") is False]
    fv_fail2 = [i["key"] for i in rep["frame_values"] if i.get("ok_json_0_02") is False]
    ck_fail = [c["check"] for c in rep["checks"] if c["ok"] is False]
    rep["summary"] = dict(frame_values_outside_0_01=fv_fail, frame_values_outside_0_02=fv_fail2, checks_failed=ck_fail,
                          tangents=[t["pair"] for t in tang])
    return rep


def luminance_report(cfg, cam, rgb, idx):
    H, W = idx.shape
    R, Wn = cfg["room"], cfg["window"]
    xl, xr = R["x_left"], R["x_right"]
    sx = (cfg["sofa"]["x0"] + cfg["sofa"]["x1"]) / 2
    pts = {
        "sofa front (seat cushion face)": ((sx, 0.952, 0.37), bs.PASS_INDEX["sofa"]),
        "back wall above the sofa (z 2.30)": ((sx, 0.0, 2.30), bs.PASS_INDEX["back-wall"]),
        "back wall right (X xr-0.40, z 1.80)": ((xr - 0.40, 0.0, 1.80), bs.PASS_INDEX["back-wall"]),
    }
    if Wn["wall"] == "left":
        pts["left wall beside the window (front side)"] = ((xl, Wn["a1"] + 0.45, 1.60), bs.PASS_INDEX["left-wall"])
        pts["back wall near the window (X xl+0.40)"] = ((xl + 0.40, 0.0, 1.60), bs.PASS_INDEX["back-wall"])
    else:
        pts["back wall beside the window (X a1+0.25)"] = ((Wn["a1"] + 0.25, 0.0, 1.60), bs.PASS_INDEX["back-wall"])
    out = {}
    for k, (p, pi) in pts.items():
        u, v, _ = P(cam, p)
        if not (0.02 < u < 0.98 and 0.02 < v < 0.98):
            out[k] = None
            continue
        cx, cy = int(u * W), int(v * H)
        patch = rgb[max(0, cy - 6):cy + 7, max(0, cx - 6):cx + 7]
        ip = idx[max(0, cy - 6):cy + 7, max(0, cx - 6):cx + 7]
        sel = patch[ip == pi]
        out[k] = dict(L=round(float(srgb_L(sel).mean()), 1) if len(sel) else None, uv=r4([u, v]),
                      visible_px=int(len(sel)))
    return out


def e0_jambs(cfg, cam):
    """A: fraction of the straight 3.85 m dolly H0 -> M0 at which each door jamb leaves the frame."""
    C = cfg["camera"]
    d = cfg["door"]
    h0 = cfg["h0"]["loc"]
    m0 = C["loc"]
    L = math.dist(h0[:2], m0[:2])
    yf = cfg["room"]["y_front"]
    res = {}
    keep = tuple(cam.location)
    for name, x in (("left jamb", d["x0"]), ("right jamb", d["x1"])):
        t_out = None
        for k in range(0, 2001):
            t = k / 2000
            cam.location = (h0[0] + (m0[0] - h0[0]) * t, h0[1] + (m0[1] - h0[1]) * t, m0[2])
            bpy.context.view_layer.update()
            # room-side edge of the jamb (last to leave) at mid height
            u, v, dz = P(cam, (x, yf, 1.0))
            inside = dz > 0 and 0 <= u <= 1
            if not inside and t_out is None:
                t_out = t
        res[name] = round(t_out, 4) if t_out is not None else None
    cam.location = keep
    bpy.context.view_layer.update()
    return dict(dolly_m=round(L, 3), out_at_fraction=res, both_out_at_fraction=max(v for v in res.values() if v is not None),
                note="jamb = room-side edge of the opening (Y = y_front), same optics as M0")


def e0_path_B(cfg):
    C = cfg["camera"]
    h0 = cfg["h0"]["loc"]
    m0 = C["loc"]
    dx, dy = m0[0] - h0[0], m0[1] - h0[1]
    L = math.hypot(dx, dy)
    nx, ny = dx / L, dy / L
    d = cfg["door"]
    yf = cfg["room"]["y_front"]
    out = {}
    for x in (d["x0"], d["x1"]):
        for y in (yf, yf + 0.15):
            out[f"({x}, {y})"] = round(abs((x - h0[0]) * ny - (y - h0[1]) * nx), 4)
    t = (yf - h0[1]) / dy
    xc = h0[0] + dx * t
    return dict(dolly_m=round(L, 3), path_crosses_front_wall_at_x=round(xc, 4),
                clearance_m=out, min_clearance_m=min(out.values()))


# ---------------------------------------------------------------------------------------
# images
# ---------------------------------------------------------------------------------------
COLORS = {"framed-art": (225, 80, 60), "pendant": (235, 160, 20), "wall-sconce": (30, 150, 225),
          "rug": (50, 165, 85), "curtains": (120, 120, 200), "planter": (35, 130, 55), "floor-lamp": (165, 85, 215),
          "basket": (175, 120, 40), "pouf": (215, 70, 150), "magazine-holder": (70, 70, 80),
          "wall-decor": (200, 110, 30), "sofa-cover": (140, 100, 160), "cushions": (190, 60, 110),
          "table-runner": (90, 140, 150), "vase": (60, 120, 170), "candle-holders": (160, 60, 60)}


def font(sz, bold=True):
    from PIL import ImageFont
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else ""), sz)
    except Exception:
        return ImageFont.load_default()


def crop_boxes(cfg):
    out = []
    for mc in cfg["mobile_crop"]:
        out.append((mc["center_u"], mc["width"], mc.get("name", ""), False))
        if "0.34" in mc.get("note", ""):
            out.append((mc["center_u"], 0.34, "0.34", True))
    return out


def dashed_rect(dr, x0, y0, x1, y1, col, w, dash=14):
    for (a, b) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        L = math.dist(a, b)
        n = max(1, int(L // dash))
        for k in range(0, n, 2):
            p = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
            q = (a[0] + (b[0] - a[0]) * min(k + 1, n) / n, a[1] + (b[1] - a[1]) * min(k + 1, n) / n)
            dr.line([p, q], fill=col, width=w)


def make_overlay(cfg, cam, clay_path, idx, slots, out_path):
    from PIL import Image, ImageDraw
    im = Image.open(clay_path).convert("RGB")
    W, H = im.size
    if idx.shape != (H, W):
        raise RuntimeError("index pass size mismatch")
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    fnt = font(max(13, W // 105))
    yy, xx = np.mgrid[0:H, 0:W]
    dash = ((xx + yy) // 7) % 2 == 0
    labels = []
    hidden = []
    for name in SLOT_ORDER:
        d = slots[name]
        m = idx == d["pidx"]
        if name == "planter":
            m = m | (idx == CROWN_IDX)
        if not m.any():
            hidden.append(name)
            continue
        col = COLORS[name]
        e = bs._edge(m)
        e = e | np.roll(e, 1, 1) & m
        prov = d["status"] != "firm"
        if prov:
            e = e & dash
        ys, xs = np.nonzero(e)
        arr = np.zeros((H, W, 4), np.uint8)
        arr[ys, xs] = col + (255,)
        fill = np.zeros((H, W, 4), np.uint8)
        fill[m] = col + (40,)
        lay = Image.alpha_composite(lay, Image.fromarray(fill))
        lay = Image.alpha_composite(lay, Image.fromarray(arr))
        ys, xs = np.nonzero(m)
        tag = name + (" (prov.)" if d["status"] == "provisional" else (" ~" if d["status"] == "approx" else ""))
        labels.append((int(np.median(xs)), int(ys.min()), tag, col))
    dr = ImageDraw.Draw(lay)
    for n, col in (("sofa", (40, 90, 200)), ("coffee-table", (40, 90, 200)), ("armchair", (40, 90, 200))):
        m = idx == bs.PASS_INDEX[n]
        e = bs._edge(m)
        ys, xs = np.nonzero(e)
        dr.point(list(zip(xs.tolist(), ys.tolist())), fill=col + (255,))
        ys, xs = np.nonzero(m)
        labels.append((int(np.median(xs)), int(np.median(ys)), n, col))
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
    # horizon (camera height) and mobile crops
    hy = P(cam, (cfg["camera"]["loc"][0] - 5 * math.sin(math.radians(cfg["camera"]["yaw"])),
                 cfg["camera"]["loc"][1] - 5 * math.cos(math.radians(cfg["camera"]["yaw"])), cfg["camera"]["loc"][2]))[1] * H
    for x in range(0, W, 24):
        dr.line([(x, hy), (x + 12, hy)], fill=(0, 0, 0, 130), width=1)
    lw = max(2, W // 700)
    for cu, cw, nm, dsh in crop_boxes(cfg):
        x0, x1 = (cu - cw / 2) * W, (cu + cw / 2) * W
        if dsh:
            dashed_rect(dr, x0, 1, x1, H - 2, (255, 255, 255, 230), lw)
        else:
            dr.rectangle((x0, 1, x1, H - 2), outline=(255, 255, 255, 240), width=lw + 1)
            dr.rectangle((x0 - lw, 1 - lw, x1 + lw, H - 2 + lw), outline=(30, 30, 30, 200), width=1)
    # legend
    leg = [f"{cfg['id']}  overlay: solid = firm, dashed = provisional, ~ = approx (relative to furniture)",
           "white frame = 9:16 mobile crop (dashed = 0.34 width option); dotted line = horizon"]
    if hidden:
        leg.append("not visible in this frame: " + ", ".join(hidden))
    f2 = font(max(12, W // 140), bold=False)
    y = H - 10 - len(leg) * (f2.size + 6)
    for t in leg:
        bbx = dr.textbbox((10, y), t, font=f2)
        dr.rectangle((bbx[0] - 4, bbx[1] - 2, bbx[2] + 4, bbx[3] + 2), fill=(255, 255, 255, 210))
        dr.text((10, y), t, fill=(20, 20, 20, 255), font=f2)
        y += f2.size + 6
    Image.alpha_composite(im.convert("RGBA"), lay).convert("RGB").save(out_path)
    return hidden


def render_plan(cfg, cam, slots, out_path):
    from PIL import Image, ImageDraw
    sc = bpy.context.scene
    keep = (sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.use_nodes, sc.cycles.samples)
    sc.use_nodes = False
    sc.cycles.samples = 24
    hidden = []
    for ob in bpy.data.objects:
        if ob.name.startswith(("ceiling", "hall_ceiling", "cornice", "px_pendant", "px_cord", "px_crown", "px_rod")):
            ob.hide_render = True
            hidden.append(ob)
    R = cfg["room"]
    xl, xr, yb, yf = R["x_left"], R["x_right"], R["y_back"], R["y_front"]
    ext_y = 3.0 if cfg["id"] in ("B", "B-low") else 1.6
    cx, cy = (xl + xr) / 2, (yb - 0.4 + yf + ext_y) / 2
    span_y = yf + ext_y - (yb - 0.4)
    span_x = max(xr - xl + 1.2, 3.5 if cfg["id"] in ("B", "B-low") else 0) + 0.8
    resx = 1100
    resy = int(round(resx * span_y / span_x))
    cd = bpy.data.cameras.new("cam_plan")
    cd.type = "ORTHO"
    cd.ortho_scale = max(span_x, span_y)
    cd.sensor_fit = "AUTO"
    cp = bpy.data.objects.new("cam_plan", cd)
    cp.location = (cx, cy, 12.0)
    cp.rotation_euler = (0, 0, math.radians(180))
    cp.scale = (-1.0, 1.0, 1.0)
    sc.collection.objects.link(cp)
    sc.camera = cp
    sc.render.resolution_x, sc.render.resolution_y = resx, resy
    sc.render.filepath = out_path
    keep_exp = sc.view_settings.exposure
    sc.view_settings.exposure = keep_exp - 1.3
    bpy.ops.render.render(write_still=True)
    sc.view_settings.exposure = keep_exp
    img = Image.open(out_path).convert("RGB")
    dr = ImageDraw.Draw(img)
    fnt = font(20)

    def Q(x, y):
        u, v, _ = P(cp, (x, y, 1.0))
        return (u * img.size[0], v * img.size[1])
    dr.line([Q(xl, yb), Q(xr, yb), Q(xr, yf), Q(xl, yf), Q(xl, yb)], fill=(60, 60, 60), width=2)
    C = cfg["camera"]
    yaw = math.radians(C["yaw"])
    f = (-math.sin(yaw), -math.cos(yaw))
    r = (math.cos(yaw), -math.sin(yaw))
    k = 36.0 / C["lens"]
    c0 = C["loc"]
    D = 9.0
    red = (215, 55, 40)
    for u in (0.0, 1.0):
        s = (u - C["u0"]) * k
        dvec = (f[0] + r[0] * s, f[1] + r[1] * s)
        # clip the ray at the room's back/side walls for readability
        tmax = D
        for wall_x in (xl, xr):
            if abs(dvec[0]) > 1e-9:
                t = (wall_x - c0[0]) / dvec[0]
                if t > 0:
                    tmax = min(tmax, t)
        if dvec[1] < 0:
            tmax = min(tmax, (yb - c0[1]) / dvec[1])
        dr.line([Q(c0[0], c0[1]), Q(c0[0] + dvec[0] * tmax, c0[1] + dvec[1] * tmax)], fill=red, width=3)
    # optical axis to the back wall
    t = (yb - c0[1]) / f[1]
    dr.line([Q(c0[0], c0[1]), Q(c0[0] + f[0] * t, c0[1] + f[1] * t)], fill=red, width=1)
    q = Q(c0[0], c0[1])
    dr.ellipse((q[0] - 10, q[1] - 10, q[0] + 10, q[1] + 10), fill=red)
    dr.text((q[0] + 14, q[1] - 10), f"M0 cam z {c0[2]:.2f}", fill=red, font=fnt)
    # verify the plan FOV against the real camera (frame edge rays must project to u 0 / 1)
    chk = []
    for u in (0.0, 1.0):
        s = (u - C["u0"]) * k
        pnt = (c0[0] + 2 * (f[0] + r[0] * s), c0[1] + 2 * (f[1] + r[1] * s), c0[2])
        chk.append(round(P(cam, pnt)[0], 4))
    # H0 and E0 path
    if cfg.get("h0"):
        h0 = cfg["h0"]["loc"]
        dr.line([Q(h0[0], h0[1]), Q(c0[0], c0[1])], fill=(30, 30, 30), width=2)
        qh = Q(h0[0], h0[1])
        if 0 < qh[1] < img.size[1]:
            dr.ellipse((qh[0] - 7, qh[1] - 7, qh[0] + 7, qh[1] + 7), fill=(30, 30, 30))
            dr.text((qh[0] + 10, qh[1] - 10), "H0", fill=(30, 30, 30), font=fnt)
        else:
            dr.text((Q(c0[0], yf + ext_y - 0.3)[0] + 8, Q(0, yf + ext_y - 0.3)[1]), "E0 -> H0", fill=(30, 30, 30), font=fnt)
    # opening labels
    d = cfg["door"]
    dq = Q((d["x0"] + d["x1"]) / 2, yf + 0.08)
    dr.text((dq[0] - 30, dq[1] + 10), f"door {d['x1'] - d['x0']:.2f}", fill=(20, 20, 20), font=fnt)
    Wn = cfg["window"]
    if Wn["wall"] == "left":
        wq = Q(xl - 0.15, (Wn["a0"] + Wn["a1"]) / 2)
        dr.text((wq[0] - 70, wq[1]), "window", fill=(30, 110, 200), font=fnt)
        dr.line([Q(xl - 0.02, Wn["a0"]), Q(xl - 0.02, Wn["a1"])], fill=(30, 110, 200), width=5)
    else:
        wq = Q((Wn["a0"] + Wn["a1"]) / 2, yb + 0.15)
        dr.text((wq[0] - 35, wq[1]), "window", fill=(30, 110, 200), font=fnt)
        dr.line([Q(Wn["a0"], yb - 0.02), Q(Wn["a1"], yb - 0.02)], fill=(30, 110, 200), width=5)
    # slot footprints for elements hidden from the top (pendant, crown)
    for nm in ("pendant",):
        s = cfg["slots"][nm]
        pts = [Q(s["c"][0] + s["r"] * math.cos(a), s["c"][1] + s["r"] * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 48)]
        dr.line(pts + [pts[0]], fill=COLORS[nm], width=2)
    s = cfg["slots"]["planter"]
    e = s["envelope"]
    pts = [Q(s["c"][0] + e["r"] * math.cos(a), s["c"][1] + e["r"] * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 48)]
    for i in range(0, len(pts) - 1, 2):
        dr.line([pts[i], pts[i + 1]], fill=COLORS["planter"], width=2)
    room_lbl = f"{cfg['id']}  room {xr - xl:.2f} x {yf - yb:.2f} x {R['h']:.2f} m"
    dr.rectangle((8, 8, 30 + dr.textlength(room_lbl, font=fnt), 40), fill=(255, 255, 255))
    dr.text((16, 12), room_lbl, fill=(20, 20, 20), font=fnt)
    img.save(out_path)
    for ob in hidden:
        ob.hide_render = False
    sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.use_nodes, sc.cycles.samples = keep
    sc.render.filepath = ""
    return dict(fov_edge_rays_project_to_u=chk)


# ---------------------------------------------------------------------------------------
# main per alternative
# ---------------------------------------------------------------------------------------
def run_alt(cfg, a, passes_root):
    from PIL import Image
    out = os.path.join(a.out, cfg["id"])
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bs.COLL.clear()
    mats()
    Shell(cfg).build()
    roots = build_furniture(cfg)
    slots = build_slots(cfg)
    cam = build_camera(cfg)
    bs.build_world(a.sky)
    w = bpy.context.scene.world.node_tree.nodes["Background"]
    w.inputs["Color"].default_value = (0.93, 0.95, 0.99, 1.0)
    bs.setup_render(a.res, a.samples, a.exposure)
    sc = bpy.context.scene
    sc.view_settings.look = "AgX - Medium High Contrast" if a.look == "mhc" else "None"
    tmp = os.path.join(passes_root, cfg["id"])
    os.makedirs(tmp, exist_ok=True)
    bs.setup_compositor(tmp)
    bpy.context.view_layer.update()
    sc.frame_set(1)
    clay = os.path.join(out, "clay.png")
    sc.render.filepath = clay
    bpy.ops.render.render(write_still=True)
    idx = np.rint(bs.load_exr(os.path.join(tmp, "IndexOB_0001.exr"))).astype(np.int32)
    rgb = np.asarray(Image.open(clay).convert("RGB"))
    rep = self_check(cfg, cam, roots, slots, idx, rgb)
    rep["render"] = dict(engine="Cycles CPU", samples=a.samples, res=[a.res, int(round(a.res * 9 / 16))],
                         sky_strength=a.sky, exposure=a.exposure, view="AgX", seed=7,
                         light="sky only, through the window of the alternative (no sun, no lamps)",
                         palette=PAL)
    rep["overlay_not_visible"] = make_overlay(cfg, cam, clay, idx, slots, os.path.join(out, "overlay.png"))
    if not a.no_plan:
        rep["plan"] = render_plan(cfg, cam, slots, os.path.join(out, "plan.png"))
    with open(os.path.join(out, "selfcheck.json"), "w") as fh:
        json.dump(rep, fh, indent=2, ensure_ascii=False)
    return rep


# ---------------------------------------------------------------------------------------
# comparison sheet
# ---------------------------------------------------------------------------------------
def make_compare(out_dir, cfgs):
    from PIL import Image, ImageDraw
    cw, ch = 1024, 576
    pad, title = 24, 54
    cols = ["v3", "A", "B", "C"]
    have = {c: os.path.join(out_dir, c, "clay.png") for c in cols + ["B-low"]}
    sheet_w = pad + len(cols) * (cw + pad)
    row_h = title + ch + pad
    # row 2: B-low under B; mobile crops (9:16 strips) of the other columns
    sheet_h = pad + 2 * row_h + 40
    sheet = Image.new("RGB", (sheet_w, sheet_h), (246, 244, 240))
    dr = ImageDraw.Draw(sheet)
    ft, fs = font(34), font(20, bold=False)

    def tile(cid, x, y, label):
        im = Image.open(have[cid]).convert("RGB").resize((cw, ch), Image.LANCZOS)
        d2 = ImageDraw.Draw(im)
        for cu, wdt, nm, dsh in crop_boxes(cfgs[cid]):
            x0, x1 = (cu - wdt / 2) * cw, (cu + wdt / 2) * cw
            if dsh:
                dashed_rect(d2, x0, 1, x1, ch - 2, (255, 255, 255), 2, dash=10)
            else:
                d2.rectangle((x0 - 1, 0, x1 + 1, ch - 1), outline=(40, 40, 40), width=1)
                d2.rectangle((x0, 1, x1, ch - 2), outline=(255, 255, 255), width=3)
        sheet.paste(im, (x, y + title))
        dr.text((x, y + 8), label, fill=(25, 25, 25), font=ft)

    def crops(cid, x, y, label):
        im = Image.open(have[cid]).convert("RGB")
        W, H = im.size
        strips = []
        for cu, wdt, nm, dsh in crop_boxes(cfgs[cid]):
            if dsh:
                continue
            x0 = int(round((cu - wdt / 2) * W))
            x1 = int(round((cu + wdt / 2) * W))
            strips.append(im.crop((max(0, x0), 0, min(W, x1), H)).resize((int(ch * 9 / 16), ch), Image.LANCZOS))
        tw = sum(s.size[0] for s in strips) + 16 * (len(strips) - 1)
        xx = x + (cw - tw) // 2
        for s in strips:
            sheet.paste(s, (xx, y + title))
            xx += s.size[0] + 16
        dr.text((x, y + 8), label, fill=(25, 25, 25), font=ft)

    y1 = pad
    labels = {"v3": "v3", "A": "A", "B": "B", "C": "C"}
    for i, c in enumerate(cols):
        tile(c, pad + i * (cw + pad), y1, labels[c])
    y2 = pad + row_h
    for i, c in enumerate(cols):
        x = pad + i * (cw + pad)
        if c == "B" and os.path.exists(have["B-low"]):
            tile("B-low", x, y2, "B-low")
        else:
            crops(c, x, y2, c + "  9:16")
    if os.path.exists(have["B-low"]):
        pass
    dr.text((pad, sheet_h - 36), "white frame = 9:16 mobile crop (width 0.316 of the 16:9 master; dashed = 0.34 option). "
            "B-low = B with camera z 1.05. B mobile crops: see the outlines on B / B-low.", fill=(70, 70, 70), font=fs)
    p = os.path.join(out_dir, "compare.jpg")
    sheet.save(p, quality=90)
    return p


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--alts", default="v3,A,B,C,B-low")
    ap.add_argument("--res", type=int, default=2048)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--look", default="mhc", choices=["none", "mhc"])
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--passes-dir", default="")
    ap.add_argument("--no-plan", action="store_true")
    ap.add_argument("--compare-only", action="store_true")
    a = ap.parse_args(argv)
    with open(SPEC_PATH) as fh:
        spec = json.load(fh)
    cfgs = {"v3": v3_config()}
    for k in ("A", "B", "C", "B-low"):
        cfgs[k] = alt_config(spec, k)
    cfgs["B-low"]["expected_ref"] = dict(spec["alternatives"]["B"]["expected"])
    os.makedirs(a.out, exist_ok=True)
    if not a.compare_only:
        passes = a.passes_dir or tempfile.mkdtemp(prefix="alts-passes-")
        summ = {}
        for k in a.alts.split(","):
            rep = run_alt(cfgs[k], a, passes)
            summ[k] = rep["summary"]
            print(k, json.dumps(rep["summary"], ensure_ascii=False), flush=True)
        if not a.passes_dir:
            import shutil
            shutil.rmtree(passes, ignore_errors=True)
        print(json.dumps(summ, indent=1))
    if all(os.path.exists(os.path.join(a.out, c, "clay.png")) for c in ("v3", "A", "B", "C")):
        print("compare:", make_compare(a.out, cfgs))


if __name__ == "__main__":
    main()
