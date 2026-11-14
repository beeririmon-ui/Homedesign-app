#!/usr/bin/env python3
"""
turn_door.py: the two code-built parts of the arrival from the front door (storyboard S1,
docs/proposals/wm-front-door-2026-11-14.md 4.3): the 65 degree turn at HD from stills taken at one point, and the
front door leaf swinging open over D0o. 0 var2 tokens.

THE TURN. A pure rotation about the lens centre has no parallax: every in-between frame is an exact reprojection
of the stills (camgeo.rot_map). The stills are joined at seams that are FIXED IN THE WORLD (a yaw each), with a
feather of a few degrees, so a seam does not travel across the frame: it is a place on the wall, and it can be
judged once, on a still. The shift (principal point) goes from the first still's to the last still's with the
turn, linearly in the angle. Endpoints are exact: progress 0 is the first still's 16:9 frame, progress 1 the last
still's, pixel for pixel (the sources are pre-scaled so that their frame is the output size).

What the stills must cover (the reason for the tall canvas): a still is flat, so toward its edge it covers less
elevation: a ray at horizontal angle t from its axis and elevation e lands at v - v0 = -KV tan(e) / cos(t). A
turn frame that looks straight at a still's edge (t degrees off that still's axis) needs 1 / cos(t) times the
still's height there. Two stills 65 degrees apart meet at t = 32.5: 18.6 % more on each side of the horizon,
about 10 % of the frame height above and below. `coverage` prints the exact region per still.

THE DOOR. The leaf is a flat board on a vertical hinge, so its picture at any angle is an exact projective warp
of its picture when closed (from D0), drawn over the doorway of D0o and clipped to the opening at the leaf plane
(the plaster reveal in front of it hides it as in life). Angle 0 returns D0 itself.

  python3 turn_door.py coverage [--canvas base|tall] [--seam 57.5] [--feather 2]
  python3 turn_door.py turn --hd HD.png --hdx HDx.png --canvas tall --out DIR [--n 61] [--blur]
  python3 turn_door.py door --d0 D0.png --d0o D0o.png --canvas base --out DIR [--n 55]
  python3 turn_door.py selftest --out DIR          # on proxy_house.py stills, against exact renders; JSON report
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camgeo as cg  # noqa: E402

# front door, warm modern (wm-front-door-2026-11-14.md 1.1, 4.3; plan entry 1.3.9 proposed)
DOOR = dict(hinge=(3.60, 8.80), width=1.00, height=2.40, thick=0.06, reveal_plane_x=3.66, y=(7.80, 8.80),
            shade_stops_open=1.0, open_s=0.9)


# ----------------------------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------------------------
def load(path: str) -> np.ndarray:
    im = cv2.imread(path, cv2.IMREAD_COLOR)
    if im is None:
        raise SystemExit(f"cannot read {path}")
    return cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def save(path: str, img: np.ndarray) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    cv2.imwrite(path, cv2.cvtColor(np.clip(np.rint(img * 255.0), 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR))


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def canvas_for(name: str, w: int, h: int) -> cg.Canvas:
    """The canvas convention of a still, from its pixel size. base: the canvas of base.png. tall: frame centred,
    3.02 % horizontal overscan (the same as base.png), the rest of the height vertical overscan. frame: no overscan."""
    if name == "frame":
        return cg.Canvas.frame(w, h)
    if name == "base":
        c = cg.Canvas.base(w)
        return cg.Canvas(w, h, c.box)
    if name == "tall":
        return cg.Canvas.tall(w, h, cg.BASE_BOX[0] / (cg.BASE_BOX[2] - cg.BASE_BOX[0]))
    raise SystemExit("canvas: frame | base | tall")


# ----------------------------------------------------------------------------------------------------------------
# the turn
# ----------------------------------------------------------------------------------------------------------------
@dataclass
class Still:
    img: np.ndarray
    cam: cg.Cam
    cv: cg.Canvas
    name: str = ""


class Turn:
    """stills: ordered along the turn (first = start of the turn, last = its end), all at the same point.
    seams: world yaw of the seam between each neighbouring pair (default: the bisector of their axes).
    feather: half-width of the blend around a seam, degrees."""

    def __init__(self, stills: list[Still], seams: list[float] | None = None, feather: float = 2.0, out_w: int = 1920):
        assert len(stills) >= 2
        assert all(np.allclose(s.cam.loc, stills[0].cam.loc, atol=1e-6) for s in stills), "the stills must share one point"
        self.out = cg.Canvas.frame(out_w)
        self.feather = feather
        self.a, self.b = stills[0].cam, stills[-1].cam
        self.sign = 1.0 if self.b.yaw < self.a.yaw else -1.0          # +1: the turn goes to the right (yaw falls)
        self.seams = seams or [(stills[i].cam.yaw + stills[i + 1].cam.yaw) / 2 for i in range(len(stills) - 1)]
        # pre-scale every still so that its 16:9 frame is exactly the output size: the endpoints are then exact
        self.st = []
        for s in stills:
            k = out_w / s.cv.fw
            w, h = int(round(s.cv.w * k)), int(round(s.cv.h * k))
            if abs(k - 1) < 1e-9:
                img, cvs = s.img, s.cv
            else:
                img = cv2.resize(s.img, (w, h), interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
                # keep the frame box on whole pixels where the canvas allows it
                cvs = cg.Canvas(w, h, tuple(b * k for b in s.cv.box))
            self.st.append(Still(img, s.cam, cvs, s.name))
        self.first = self.st[0].cv.crop_frame(self.st[0].img, out_w)
        self.last = self.st[-1].cv.crop_frame(self.st[-1].img, out_w)

    def cam_at(self, p: float) -> cg.Cam:
        return cg.lerp_cam(self.a, self.b, float(p))

    def _weights(self, az: np.ndarray) -> list[np.ndarray]:
        """Partition of unity over the stills by world yaw."""
        n = len(self.st)
        w = [np.ones_like(az, np.float32) for _ in range(n)]
        for i, sy in enumerate(self.seams):
            # t = 0 on the side of still i, 1 on the side of still i+1
            t = smoothstep((self.sign * (sy - az) + self.feather) / (2 * self.feather)) if self.feather > 0 else (self.sign * (sy - az) > 0).astype(np.float32)
            for j in range(n):
                w[j] = w[j] * ((1 - t) if j <= i else t)
        return w

    def frame(self, p: float):
        """The turn at progress p in 0..1 of the angle. Returns (image, hole fraction, per-still use fraction)."""
        if p <= 0:
            return self.first.copy(), 0.0
        if p >= 1:
            return self.last.copy(), 0.0
        cam = self.cam_at(p)
        D = cg.rays(cam, self.out)
        az = (np.degrees(np.arctan2(-D[..., 0], -D[..., 1]))).astype(np.float32)        # world yaw of every pixel's ray
        W = self._weights(az)
        acc = np.zeros((self.out.h, self.out.w, 3), np.float32)
        wsum = np.zeros((self.out.h, self.out.w), np.float32)
        best = np.zeros((self.out.h, self.out.w, 3), np.float32)
        anycov = np.zeros((self.out.h, self.out.w), bool)
        for s, w in zip(self.st, W):
            if float(w.max()) <= 0:
                continue
            img, cov = cg.rot_warp(s.img, s.cam, s.cv, cam, self.out)
            ww = w * cov
            acc += img * ww[..., None]
            wsum += ww
            best = np.where((cov & ~anycov)[..., None], img, best)
            anycov |= cov
        hole = wsum < 1e-3
        out = acc / np.maximum(wsum, 1e-3)[..., None]
        # a pixel its own still does not cover: any still that does (reported as a fallback, not as a hole)
        fb = hole & anycov
        out[fb] = best[fb]
        true_hole = hole & ~anycov
        return np.clip(out, 0, 1), float(true_hole.mean())

    def frame_blur(self, p: float, dp: float, max_sub: int = 12):
        """Rotational motion blur: the mean of sub-frames over +-dp/2 of progress (dp = the spacing of the stored
        frames gives continuous coverage when the player blends neighbours). The endpoints stay exact."""
        if p <= 0 or p >= 1 or dp <= 0:
            return self.frame(p)
        px = abs(math.radians((self.b.yaw - self.a.yaw) * dp)) * cg.KU * self.out.w
        n = int(min(max_sub, max(1, math.ceil(px / 1.5))))
        if n == 1:
            return self.frame(p)
        acc, holes = 0.0, 0.0
        for k in range(n):
            f, h = self.frame(float(np.clip(p + dp * ((k + 0.5) / n - 0.5), 1e-6, 1 - 1e-6)))
            acc = acc + f
            holes = max(holes, h)
        return acc / n, holes


def coverage(cams: list[cg.Cam], seams: list[float] | None, feather: float, canvases: list[cg.Canvas] | None = None,
             n: int = 261, grid=(193, 109)) -> dict:
    """The region of each still (u, v in fractions of ITS 16:9 frame) that the turn reads, and, when canvases are
    given, the worst hole (fraction of the frame, and how far above / below the frame the missing rows are)."""
    a, b = cams[0], cams[-1]
    sign = 1.0 if b.yaw < a.yaw else -1.0
    seams = seams or [(cams[i].yaw + cams[i + 1].yaw) / 2 for i in range(len(cams) - 1)]
    fr = cg.Canvas.frame(grid[0], grid[1])
    need = [dict(u=[9.0, -9.0], v=[9.0, -9.0]) for _ in cams]
    worst = dict(hole_frac=0.0, at_p=None, rows_missing_top=0.0, rows_missing_bottom=0.0)
    for p in np.linspace(0, 1, n):
        cam = cg.lerp_cam(a, b, float(p))
        D = cg.rays(cam, fr)
        az = np.degrees(np.arctan2(-D[..., 0], -D[..., 1]))
        covered = np.zeros(az.shape, bool)
        for i, c in enumerate(cams):
            lo = seams[i] if i < len(seams) else None           # boundary toward the next still
            hi = seams[i - 1] if i > 0 else None                # boundary toward the previous still
            use = np.ones(az.shape, bool)
            if hi is not None:
                use &= sign * (hi - az) > -feather
            if lo is not None:
                use &= sign * (lo - az) < feather
            if not use.any():
                continue
            d = D @ c.f
            x = D @ c.r
            us = c.u0 + cg.KU * x / d
            vs = c.v0 - cg.KV * D[..., 2] / d
            need[i]["u"] = [min(need[i]["u"][0], float(us[use].min())), max(need[i]["u"][1], float(us[use].max()))]
            need[i]["v"] = [min(need[i]["v"][0], float(vs[use].min())), max(need[i]["v"][1], float(vs[use].max()))]
            if canvases is not None:
                ol, orr, ot, ob = canvases[i].ovs
                ok = use & (us >= -ol) & (us <= 1 + orr) & (vs >= -ot) & (vs <= 1 + ob)
                # core use (without the feather): a pixel is covered when the still that owns it covers it
                covered |= ok
        if canvases is not None:
            hole = ~covered
            if hole.mean() > worst["hole_frac"]:
                rows = np.where(hole.any(axis=1))[0]
                top = (rows[rows < grid[1] / 2].max() + 1) / grid[1] if (rows < grid[1] / 2).any() else 0.0
                bot = 1 - rows[rows >= grid[1] / 2].min() / grid[1] if (rows >= grid[1] / 2).any() else 0.0
                worst = dict(hole_frac=float(hole.mean()), at_p=float(p), rows_missing_top=float(top), rows_missing_bottom=float(bot))
    out = dict(seams_yaw=seams, feather_deg=feather,
               need=[dict(yaw=c.yaw, u=[round(x, 4) for x in nd["u"]], v=[round(x, 4) for x in nd["v"]],
                          overscan_needed=dict(left=round(max(0.0, -nd["u"][0]), 4), right=round(max(0.0, nd["u"][1] - 1), 4),
                                               top=round(max(0.0, -nd["v"][0]), 4), bottom=round(max(0.0, nd["v"][1] - 1), 4)))
                     for c, nd in zip(cams, need)])
    if canvases is not None:
        out["canvas_overscan"] = [[round(x, 4) for x in c.ovs] for c in canvases]
        out["worst_hole"] = worst
    return out


def overlap_deg(a: cg.Cam, b: cg.Cam, cva: cg.Canvas | None = None, cvb: cg.Canvas | None = None) -> float:
    """Degrees of yaw that both stills show (frames, or canvases when given). a is the still with the larger yaw."""
    oa = cva.ovs if cva else (0, 0, 0, 0)
    ob = cvb.ovs if cvb else (0, 0, 0, 0)
    return b.edges_yaw(ob[0], ob[1])[0] - a.edges_yaw(oa[0], oa[1])[1]


def build_from(dst: Still, src: Still, seam: float, feather: float) -> np.ndarray:
    """'HD built from HDx': the destination still with the side beyond the seam replaced by the source still
    reprojected (exact, same point). Inside the feather the two are blended; beyond it the source alone. Returns the
    destination canvas image. After this the two stills agree pixel for pixel across the seam."""
    sign = 1.0 if src.cam.yaw < dst.cam.yaw else -1.0
    D = cg.rays(dst.cam, dst.cv)
    az = np.degrees(np.arctan2(-D[..., 0], -D[..., 1])).astype(np.float32)
    img, cov = cg.rot_warp(src.img, src.cam, src.cv, dst.cam, dst.cv)
    t = smoothstep((sign * (seam - az) + feather) / (2 * feather)) * cov          # 1 on the source's side
    return dst.img * (1 - t[..., None]) + img * t[..., None]


def seam_match(dst: Still, src: Still, seam: float, band: float = 4.0, fall: float = 20.0) -> tuple[np.ndarray, dict]:
    """Bring the destination still's tone to the source's at the seam: a per-channel gain measured in the band
    around the seam where both show the wall, applied to the destination with a falloff of `fall` degrees away
    from the seam (so the destination's far side, the end frame of a clip, is not touched)."""
    sign = 1.0 if src.cam.yaw < dst.cam.yaw else -1.0
    D = cg.rays(dst.cam, dst.cv)
    az = np.degrees(np.arctan2(-D[..., 0], -D[..., 1])).astype(np.float32)
    img, cov = cg.rot_warp(src.img, src.cam, src.cv, dst.cam, dst.cv)
    m = cov & (np.abs(az - seam) < band)
    if m.sum() < 500:
        return dst.img, dict(gain=[1, 1, 1], px=int(m.sum()))
    g = np.array([np.median(img[..., c][m]) / max(1e-4, np.median(dst.img[..., c][m])) for c in range(3)], np.float32)
    w = smoothstep(1 - (sign * (az - seam)) / fall)[..., None]                    # 1 at the seam and beyond, 0 `fall` deg inside
    out = dst.img * (1 + (g[None, None] - 1) * w)
    return np.clip(out, 0, 1), dict(gain=[round(float(x), 4) for x in g], px=int(m.sum()))


# ----------------------------------------------------------------------------------------------------------------
# the door
# ----------------------------------------------------------------------------------------------------------------
def _leaf_points(theta_deg: float, door=DOOR):
    """World XY of the leaf's outside face (hinge-side edge, free edge) and of the hinge line, at an opening angle."""
    t = math.radians(theta_deg)
    hx, hy = door["hinge"]
    rot = lambda x, y: (hx + x * math.cos(t) + y * math.sin(t), hy - x * math.sin(t) + y * math.cos(t))
    return rot(door["thick"], 0.0), rot(door["thick"], -door["width"]), (hx, hy)


def _quad(cam: cg.Cam, cv: cg.Canvas, p0, p1, z0, z1):
    """Pixel corners of a vertical rectangle between the plan points p0 and p1: top-p0, top-p1, bottom-p1, bottom-p0."""
    P = np.array([[p0[0], p0[1], z1], [p1[0], p1[1], z1], [p1[0], p1[1], z0], [p0[0], p0[1], z0]])
    u, v, d = cam.project(P)
    if (d <= 0.02).any():
        return None
    x, y = cv.px(u, v)
    return np.stack([x, y], axis=1).astype(np.float32)


def door_frame(base: np.ndarray, d0: np.ndarray, cam: cg.Cam, cv: cg.Canvas, theta_deg: float, d0_cam: cg.Cam = cg.D0,
               d0_cv: cg.Canvas | None = None, door=DOOR) -> np.ndarray:
    """The leaf at `theta_deg` (0 closed, 90 open) drawn over `base` as seen by `cam`.
    base: D0o at rest (same camera as D0), or a frame of the walk-in clip while the camera already moves.
    d0: the closed-door still (the leaf's texture), taken with d0_cam on d0_cv.
    theta 0 with the D0 camera returns D0 itself."""
    d0_cv = d0_cv or cv
    if theta_deg <= 0 and cam == d0_cam and cv == d0_cv:
        return d0.copy()
    H, W = cv.h, cv.w
    y0, y1 = door["y"]
    zh = door["height"]
    # the opening at the leaf plane: the leaf and the hall are seen only through it
    q_open = _quad(cam, cv, (door["reveal_plane_x"], y1), (door["reveal_plane_x"], y0), 0.0, zh)
    if q_open is None:
        return base.copy()                                   # the camera is past the leaf plane
    mask = np.zeros((H, W), np.float32)
    cv2.fillConvexPoly(mask, np.round(q_open * 16).astype(np.int32), 1.0, lineType=cv2.LINE_AA, shift=4)
    out = base.copy()
    # texture of the closed leaf's outside face in D0
    q_src = _quad(d0_cam, d0_cv, (door["reveal_plane_x"], y1), (door["reveal_plane_x"], y0), 0.0, zh)
    # read the leaf 2 px inside its outline, so that the plaster of the reveal never bleeds onto the leaf's edge
    q_src = q_src + np.sign(q_src.mean(axis=0, keepdims=True) - q_src) * 2.0
    hinge_edge, free_edge, hinge = _leaf_points(theta_deg, door)
    shade = 2.0 ** (-door["shade_stops_open"] * min(1.0, theta_deg / 90.0))
    # 1) the hinge-side end of the leaf (its 6 cm thickness), seen once the leaf has turned
    q_end = _quad(cam, cv, hinge, hinge_edge, 0.0, zh)
    q_face = _quad(cam, cv, hinge_edge, free_edge, 0.0, zh)
    if q_face is None:
        return out
    face_w = abs(q_face[1, 0] - q_face[0, 0])
    if q_end is not None and abs(q_end[1, 0] - q_end[0, 0]) > 0.3:
        m = np.zeros((H, W), np.float32)
        cv2.fillConvexPoly(m, np.round(q_end * 16).astype(np.int32), 1.0, lineType=cv2.LINE_AA, shift=4)
        sx0, sy0 = q_src.min(axis=0)
        sx1, sy1 = q_src.max(axis=0)
        strip = d0[int(sy0):int(sy1) + 1, max(0, int(sx0)):max(0, int(sx0)) + max(2, int(0.06 * (sx1 - sx0)))]
        col = strip.reshape(-1, 3).mean(axis=0) * shade * 0.8 if strip.size else np.array([0.3, 0.2, 0.15], np.float32)
        m = (m * mask)[..., None]
        out = out * (1 - m) + col[None, None] * m
    # 2) the outside face
    if face_w > 0.3:
        Hm = cv2.getPerspectiveTransform(q_src, q_face)
        tex = cv2.warpPerspective(d0, Hm, (W, H), flags=cv2.INTER_AREA if face_w < 0.5 * abs(q_src[1, 0] - q_src[0, 0]) else cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_REPLICATE)
        m = np.zeros((H, W), np.float32)
        cv2.fillConvexPoly(m, np.round(q_face * 16).astype(np.int32), 1.0, lineType=cv2.LINE_AA, shift=4)
        m = (m * mask)[..., None]
        out = out * (1 - m) + tex * shade * m
    return np.clip(out, 0, 1)


def door_angle(t: float, open_s: float = DOOR["open_s"]) -> float:
    """Opening angle at time t: an object, not the camera, so it accelerates and settles like a real door
    (smootherstep: zero speed and zero acceleration at both ends)."""
    x = float(np.clip(t / open_s, 0.0, 1.0))
    return 90.0 * x * x * x * (x * (6 * x - 15) + 10)


# ----------------------------------------------------------------------------------------------------------------
# selftest on the proxy house
# ----------------------------------------------------------------------------------------------------------------
def psnr(a, b, m=None):
    d = (a - b) ** 2
    mse = float(d[m].mean()) if m is not None else float(d.mean())
    return 99.0 if mse < 1e-12 else 10 * math.log10(1.0 / mse)


def selftest(out_dir: str, w_still: int = 2496, out_w: int = 1280, n: int = 13) -> dict:
    import proxy_house as ph
    os.makedirs(out_dir, exist_ok=True)
    rep: dict = {"what": "the 65 deg turn HD -> HDx and the door, built by turn_door.py from proxy_house.py stills and compared "
                         "with exact proxy renders of the same in-between cameras", "out_w": out_w}
    tall = cg.Canvas.tall(w_still, int(round(w_still * 2 / 3)), cg.BASE_BOX[0] / (cg.BASE_BOX[2] - cg.BASE_BOX[0]))
    base = cg.Canvas.base(2720)
    cams3 = [cg.HD, cg.lerp_cam(cg.HD, cg.HDX, 0.5), cg.HDX]
    rep["geometry"] = dict(
        overlap_frame_deg=round(overlap_deg(cg.HD, cg.HDX), 2),
        overlap_base_canvas_deg=round(overlap_deg(cg.HD, cg.HDX, base, base), 2),
        two_stills_base_canvas=coverage([cg.HD, cg.HDX], None, 2.0, [base, base]),
        two_stills_tall_canvas=coverage([cg.HD, cg.HDX], None, 2.0, [tall, tall]),
        three_stills_base_canvas=coverage(cams3, None, 2.0, [base, base, base]))
    fr = cg.Canvas.frame(out_w)
    ps = [i / (n - 1) for i in range(n)]

    def run(tag, stills, seams=None, feather=2.0, keep=()):
        T = Turn(stills, seams, feather, out_w)
        rows, worst_hole = [], 0.0
        for i, p in enumerate(ps):
            f, hole = T.frame(p)
            ref, _ = ph.render(T.cam_at(p), fr, "open", ss=2)
            rows.append(psnr(f, ref))
            worst_hole = max(worst_hole, hole)
            if i in keep:
                save(os.path.join(out_dir, f"{tag}-p{p:.3f}.jpg"), f)
        return dict(psnr_min=round(min(rows[1:-1]), 2), psnr_mean=round(float(np.mean(rows[1:-1])), 2),
                    psnr_endpoints=[round(rows[0], 2), round(rows[-1], 2)], worst_hole_frac=round(worst_hole, 5))

    keep = (n // 2,)
    hd_t, _ = ph.render(cg.HD, tall, "open", ss=1)
    hdx_t, _ = ph.render(cg.HDX, tall, "open", ss=1)
    hd_b, _ = ph.render(cg.HD, base, "open", ss=1)
    hdx_b, _ = ph.render(cg.HDX, base, "open", ss=1)
    mid_b, _ = ph.render(cams3[1], base, "open", ss=1)
    rep["A_two_stills_tall_3x2"] = run("A-two-tall", [Still(hd_t, cg.HD, tall, "HD"), Still(hdx_t, cg.HDX, tall, "HDx")], keep=keep)
    rep["B_two_stills_base_16x9"] = run("B-two-base", [Still(hd_b, cg.HD, base, "HD"), Still(hdx_b, cg.HDX, base, "HDx")], keep=keep)
    rep["C_three_stills_base_16x9"] = run("C-three-base", [Still(hd_b, cg.HD, base, "HD"), Still(mid_b, cams3[1], base, "HD57"),
                                                           Still(hdx_b, cg.HDX, base, "HDx")], keep=keep)
    # the seam with two stills that do NOT agree (independent renders: another plaster texture and 4 % brighter)
    hd_other, _ = ph.render(cg.HD, tall, "open", seed=11, exposure=1.04)
    A = Still(hd_other, cg.HD, tall, "HD other seed")
    Bs = Still(hdx_t, cg.HDX, tall, "HDx")

    def seam_step(stills, feather):
        """Mean brightness step across the seam in the mid-turn frame (a band of 3 deg on each side), in 8-bit levels."""
        T = Turn(stills, None, feather, out_w)
        f, _ = T.frame(0.5)
        cam = T.cam_at(0.5)
        D = cg.rays(cam, fr)
        az = np.degrees(np.arctan2(-D[..., 0], -D[..., 1]))
        g = f.mean(axis=2)
        band = (D[..., 2] > -0.25) & (D[..., 2] < 0.25)
        left = g[band & (az > 57.5 + 0.2) & (az < 57.5 + 3.2)].mean()
        right = g[band & (az < 57.5 - 0.2) & (az > 57.5 - 3.2)].mean()
        # the sharpest column-to-column change inside the feather, against the same measure in the exact render
        col = g[int(fr.h * 0.3):int(fr.h * 0.7)].mean(axis=0)
        return dict(step_levels=round(float(abs(left - right) * 255), 2), max_col_jump_levels=round(float(np.abs(np.diff(col)).max() * 255), 2)), f

    rep["D_independent_stills"] = {}
    for tag, st, fe in (("hard_cut", [A, Bs], 0.0), ("feather_2deg", [A, Bs], 2.0)):
        r, f = seam_step(st, fe)
        rep["D_independent_stills"][tag] = r
        save(os.path.join(out_dir, f"D-{tag}.jpg"), f)
    g_img, g = seam_match(A, Bs, 57.5)
    r, f = seam_step([Still(g_img, cg.HD, tall), Bs], 2.0)
    rep["D_independent_stills"]["tone_matched_feather_2deg"] = dict(r, **g)
    save(os.path.join(out_dir, "D-tone-matched.jpg"), f)
    built = build_from(Still(g_img, cg.HD, tall), Bs, seam=52.0, feather=3.0)
    r, f = seam_step([Still(built, cg.HD, tall), Bs], 2.0)
    rep["D_independent_stills"]["HD_built_from_HDx"] = r
    save(os.path.join(out_dir, "D-built-from.jpg"), f)
    ref, _ = ph.render(cg.lerp_cam(cg.HD, cg.HDX, 0.5), fr, "open", ss=2)
    g = ref.mean(axis=2)
    col = g[int(fr.h * 0.3):int(fr.h * 0.7)].mean(axis=0)
    rep["D_independent_stills"]["exact_render_max_col_jump_levels"] = round(float(np.abs(np.diff(col)).max() * 255), 2)

    # the door: code leaf over D0o against the proxy's own open door (geometry of the sliver), and angle 0 = D0
    cvb = cg.Canvas.base(1360)
    d0, _ = ph.render(cg.D0, cvb, "closed", ss=2)
    d0o, _ = ph.render(cg.D0, cvb, "none", ss=2)
    dop, _ = ph.render(cg.D0, cvb, "open", ss=2)
    f0 = door_frame(d0o, d0, cg.D0, cvb, 0.0)
    f90 = door_frame(d0o, d0, cg.D0, cvb, 90.0)
    # where the leaf sits: columns that differ from the empty doorway
    def leaf_cols(img):
        diff = np.abs(img - d0o).mean(axis=2)
        cols = np.where(diff[int(cvb.h * 0.3):int(cvb.h * 0.7)].mean(axis=0) > 0.02)[0]
        return [float((cols.min() + 0.5 - cvb.box[0]) / cvb.fw), float((cols.max() + 0.5 - cvb.box[0]) / cvb.fw)] if cols.size else None
    rep["door"] = dict(theta0_equals_D0=bool(np.array_equal(f0, d0)), leaf_u_code_90=leaf_cols(f90), leaf_u_proxy_90=leaf_cols(dop),
                       outside_opening_changed_px=int((np.abs(f90 - d0).max(axis=2) > 1e-6)[:, :int(cvb.px(0.23, 0)[0])].sum()))
    strip = [door_frame(d0o, d0, cg.D0, cvb, a) for a in (0, 15, 35, 60, 90)]
    fbox = [int(round(b)) for b in cvb.box]
    crop = [s[fbox[1]:fbox[3], int(cvb.px(0.18, 0)[0]):int(cvb.px(0.48, 0)[0])] for s in strip]
    save(os.path.join(out_dir, "door-0-15-35-60-90.jpg"), np.hstack(crop))
    with open(os.path.join(out_dir, "turn-door-selftest.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    return rep


# ----------------------------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("coverage")
    c.add_argument("--canvas", default=None, choices=["base", "tall", "frame"])
    c.add_argument("--seam", type=float, default=None)
    c.add_argument("--feather", type=float, default=2.0)
    c.add_argument("--three", action="store_true", help="with the reserve still HD57 (yaw 57.5)")
    t = sub.add_parser("turn")
    t.add_argument("--hd", required=True)
    t.add_argument("--hdx", required=True)
    t.add_argument("--mid", help="the reserve still HD57")
    t.add_argument("--canvas", default="tall", choices=["base", "tall", "frame"])
    t.add_argument("--out", required=True)
    t.add_argument("--n", type=int, default=61, help="frames, uniform in the angle (frame 1 = HD, frame n = HDx)")
    t.add_argument("--w", type=int, default=1920)
    t.add_argument("--feather", type=float, default=2.0)
    t.add_argument("--seam", type=float, default=None)
    t.add_argument("--blur", action="store_true")
    t.add_argument("--match", action="store_true", help="tone-match HD to HDx at the seam first")
    t.add_argument("--allow-holes", action="store_true")
    d = sub.add_parser("door")
    d.add_argument("--d0", required=True)
    d.add_argument("--d0o", required=True)
    d.add_argument("--canvas", default="base", choices=["base", "tall", "frame"])
    d.add_argument("--out", required=True)
    d.add_argument("--n", type=int, default=55, help="frames over the opening time (0.9 s at 60 fps = 55)")
    d.add_argument("--w", type=int, default=1920)
    s = sub.add_parser("selftest")
    s.add_argument("--out", required=True)
    s.add_argument("--w", type=int, default=1280)
    a = ap.parse_args(argv)

    if a.cmd == "coverage":
        mid = cg.lerp_cam(cg.HD, cg.HDX, 0.5)
        cams = [cg.HD, mid, cg.HDX] if a.three else [cg.HD, cg.HDX]
        cvs = None
        if a.canvas:
            one = {"base": cg.Canvas.base(2720), "tall": cg.Canvas.tall(2496, 1664, cg.BASE_BOX[0] / (cg.BASE_BOX[2] - cg.BASE_BOX[0])),
                   "frame": cg.Canvas.frame(1920)}[a.canvas]
            cvs = [one] * len(cams)
        seams = [a.seam] if (a.seam is not None and not a.three) else None
        print(json.dumps(coverage(cams, seams, a.feather, cvs), indent=1))
        return 0
    if a.cmd == "turn":
        hd, hdx = load(a.hd), load(a.hdx)
        st = [Still(hd, cg.HD, canvas_for(a.canvas, hd.shape[1], hd.shape[0]), "HD")]
        if a.mid:
            m = load(a.mid)
            st.append(Still(m, cg.lerp_cam(cg.HD, cg.HDX, 0.5), canvas_for(a.canvas, m.shape[1], m.shape[0]), "HD57"))
        st.append(Still(hdx, cg.HDX, canvas_for(a.canvas, hdx.shape[1], hdx.shape[0]), "HDx"))
        info = {}
        if a.match and not a.mid:
            st[0].img, info = seam_match(st[0], st[1], a.seam or 57.5)
        T = Turn(st, [a.seam] if (a.seam is not None and not a.mid) else None, a.feather, a.w)
        worst = 0.0
        for i in range(a.n):
            p = i / (a.n - 1)
            f, hole = T.frame_blur(p, 1.0 / (a.n - 1)) if a.blur else T.frame(p)
            worst = max(worst, hole)
            save(os.path.join(a.out, f"{i + 1:04d}.png"), f)
        print(json.dumps(dict(frames=a.n, worst_hole_frac=worst, seam_match=info), indent=1))
        if worst > 0 and not a.allow_holes:
            print("the stills do not cover the turn (see `coverage`); nothing was filled in", file=sys.stderr)
            return 2
        return 0
    if a.cmd == "door":
        d0, d0o = load(a.d0), load(a.d0o)
        cvs = canvas_for(a.canvas, d0.shape[1], d0.shape[0])
        for i in range(a.n):
            th = door_angle(i / (a.n - 1) * DOOR["open_s"])
            f = door_frame(d0o, d0, cg.D0, cvs, th)
            save(os.path.join(a.out, f"{i + 1:04d}.png"), cvs.crop_frame(f, a.w))
        return 0
    if a.cmd == "selftest":
        rep = selftest(a.out, out_w=a.w)
        print(json.dumps(rep, indent=1))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
