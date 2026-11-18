#!/usr/bin/env python3
"""
warp_ht2.py: HT2 from the r1 render with the clay's geometry, in code (render-agent, 2026-11-18). 0 tokens.
Why: both nano-banana-2 renders of HT2 (r1, fix1) drew the bench frontally: no outer side of the left end panel, the front-left corner of
the seat at u ~0.506 (r1) / ~0.48 (fix1) for the clay's 0.542 (route 12.1, rejection item 1), and in r1 the inner face of the right panel
near black (L* ~7). The material is good: walnut grain, the sheen of the seat, the edge highlight. So:
  - the bench: each face of the clay bench (wm-hall-2026-11-18/HT: id 100, its world points from the depth and its normals) takes the
    matching face of r1 through a homography (a plane to a plane: the seat top, the seat's front edge, the front edges of the two end
    panels); the outer side of the left end panel (the plane Y 7.50, which r1 does not show) takes r1's left panel front, and the inner face
    of the right panel takes r1's right panel front; both at the clay's light relative to the front edge next to them
  - around the bench and under the seat: ht.png times the clay's shading ratio (with / without the bench; prep_ht2.py), so the contact
    shadow and the stone and floor under the seat are HT's own pixels, darker where the clay says
  - outside the 12 px mask: ht.png byte for byte
  python3 warp_ht2.py <r1_on_canvas.png> <work_dir> <out.png> <report.json>
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402
from prep_ht2 import masks, normals  # noqa: E402

N = "HT"
CAM = K.CAMS[N]
B = dict(x=(0.81, 1.21), y=(6.70, 7.50), seat=0.45, slab=0.05, panel=0.05)

# r1's faces, measured on r1 resampled to the canvas (u, v of the 16:9 frame; luminance and b* profiles, see the README)
R1 = dict(top=[(0.5190, 0.8046), (0.7280, 0.8046), (0.7620, 0.8450), (0.5130, 0.8450)],          # back-left, back-right, front-right, front-left
          front=[(0.5190, 0.8455), (0.7570, 0.8455), (0.7570, 0.8680), (0.5190, 0.8680)],        # the seat's front edge band
          lpanel=[(0.5140, 0.8850), (0.5350, 0.8850), (0.5350, 1.0300), (0.5140, 1.0300)],       # left end panel, its front
          rpanel=[(0.7515, 0.8850), (0.7650, 0.8850), (0.7650, 1.0300), (0.7515, 1.0300)],       # right end panel, its front
          side=[(0.5185, 0.8850), (0.5310, 0.8850), (0.5310, 1.0300), (0.5185, 1.0300)])         # the middle of the left front: the sides' grain
# (inset 2-12 px from r1's edges, and the panels from v 0.885: no stone, and none of r1's rounded "waterfall" corners or its mitre line)


def proj(P):
    u, v, _ = CAM.project(np.asarray(P, float))
    return float(u), float(v)


def clay_quads():
    (x0, x1), (y0, y1), zs = B["x"], B["y"], B["seat"]
    zb = zs - B["slab"]
    t = B["panel"]
    zc = CAM.loc[2] - (1.03 - CAM.v0) * (CAM.loc[0] - x1) / K.cg.KV        # the height r1's panels reach at v 1.03 (the canvas bottom)
    Q = dict(top=[proj((x0, y1, zs)), proj((x0, y0, zs)), proj((x1, y0, zs)), proj((x1, y1, zs))],
             front=[proj((x1, y1, zs)), proj((x1, y0, zs)), proj((x1, y0, zb)), proj((x1, y1, zb))],
             lpanel=[proj((x1, y1, zb)), proj((x1, y1 - t, zb)), proj((x1, y1 - t, zc)), proj((x1, y1, zc))],
             rpanel=[proj((x1, y0 + t, zb)), proj((x1, y0, zb)), proj((x1, y0, zc)), proj((x1, y0 + t, zc))],
             # the outer side of the left panel (+ the seat's end), plane Y 7.50, from the panel front's texture: X runs along the width
             outer=[proj((x0, y1, zs)), proj((x1, y1, zs)), proj((x1, y1, zc)), proj((x0, y1, zc))],
             # the inner face of the right panel, plane Y 6.75, from the right panel front's texture
             inner=[proj((x0, y0 + t, zb)), proj((x1, y0 + t, zb)), proj((x1, y0 + t, zc)), proj((x0, y0 + t, zc))])
    return Q


def px(name, quad):
    cv = K.canvas(name)
    return np.float32([[u * cv.fw + cv.box[0] - 0.5, v * cv.fh + cv.box[1] - 0.5] for u, v in quad])


def face_masks():
    cls = K.clay_id(N)
    obj = cls == K.BENCH_ID
    P, ok = K.world(N)
    nrm = normals(N)
    X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
    nx, ny, nz = nrm[..., 0], nrm[..., 1], nrm[..., 2]
    zb = B["seat"] - B["slab"]
    zs_top = B["seat"]
    seat = obj & (Z >= zb - 0.004)
    pan = obj & ~seat
    left = Y > 7.10
    ptop = obj & (nz > 0.5) & (Z < zs_top - 0.01)                  # the panels' eased top edges, seen in the groove under the seat's front edge
    F = dict(top=seat & (nz > 0.5) & ~ptop,
             front=seat & ~(nz > 0.5) & (nx > 0.5),
             lpanel=(pan & left & (nx > 0.5)) | (ptop & left),
             rpanel=(pan & ~left & (nx > 0.5)) | (ptop & ~left),
             outer=obj & left & ~(nz > 0.5) & ~(nx > 0.5) & (ny > 0),
             inner=pan & ~left & ~(nx > 0.5) & (ny > 0))
    # the clay's eased edges leave a see-through notch where the seat's front edge meets each panel's (a few px): closed, filled as walnut
    closed = cv2.morphologyEx(obj.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))).astype(bool)
    obj = obj | closed
    rest = obj & ~np.any(np.stack(list(F.values())), 0)
    F["_groove"] = ptop
    return obj, F, rest, cls


def main(r1p, work, outp, repp):
    ht8 = K.rgb8(os.path.join(K.PREV, "ht.png"))
    ht = K.to_lin(ht8 / 255.0)
    r1 = K.to_lin(K.rgb(r1p)).astype(np.float32)
    cls, obj0, sh, core, mask, R, mrep = masks(N, (K.BENCH_ID,), thr=0.95, top_z=0.45, box=((0.81, 6.70, 0.0), (1.21, 7.50, 0.45)), reach=0.20)
    obj, F, rest, _ = face_masks()
    Q = clay_quads()
    H, W = obj.shape
    clay = K.to_lin(K.rgb(K.clay_png(N))) @ K.W709
    bench = np.zeros_like(r1)
    rep = dict(faces_px={k: int(v.sum()) for k, v in F.items()}, unassigned_px=int(rest.sum()))
    src_for = dict(top="top", front="front", lpanel="lpanel", rpanel="rpanel", outer="side", inner="side")
    groove = F.pop("_groove")
    for f, m in F.items():
        s = src_for[f]
        # target pixel -> the face's unit square (clamped inside, so that pixels on the eased edges and in the slab-to-panel groove, which
        # lie off the face's plane, never reach past r1's face) -> r1
        unit = np.float32([[0, 0], [1, 0], [1, 1], [0, 1]])
        Ht = cv2.getPerspectiveTransform(px(N, Q[f]), unit)
        Hs = cv2.getPerspectiveTransform(unit, px(N, R1[s]))
        ys, xs = np.nonzero(m)
        st = cv2.perspectiveTransform(np.stack([xs, ys], -1).astype(np.float32)[None], Ht)[0]
        st = np.clip(st, 0.015, 0.985)
        sxy = cv2.perspectiveTransform(st[None], Hs)[0]
        mx = np.full((H, W), -1, np.float32)
        my = np.full((H, W), -1, np.float32)
        mx[ys, xs], my[ys, xs] = sxy[:, 0], sxy[:, 1]
        warped = cv2.remap(r1, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        if f in ("outer", "inner"):
            # the clay's light on this face against the front edge next to it, applied to the front's texture
            ref = F["lpanel"] if f == "outer" else F["rpanel"]
            g = float(np.median(clay[m]) / np.median(clay[ref]))
            warped = warped * g
            rep[f + "_gain_from_clay"] = round(g, 3)
        bench[m] = warped[m]
    # the levels (route 12.1: the front 0 to 2/3 stop under the walnut lining; walnut at least 8 L* over the black point, ht.png's p0.1
    # = L* 12.7, so >= 20.7). r1 put the right end panel in the corner's shade (L* 14) and its inner face near black (L* 6); the clay puts
    # the right front at 0.72 of the left one and the inner face at 0.13 (L* 5.8 in the clay too): the floor of the rejection list wins.
    Yb = bench @ K.W709
    from prep_ht2 import lining_mask
    yl = float(np.median((ht @ K.W709)[lining_mask(cls, N, (0.814, 0.850))]))
    y_floor = ((20.7 + 16) / 116) ** 3 * 1.0
    y_front_min = yl * 2 ** (-2 / 3 + 0.03)
    lv = {}

    def set_level(f, y_t):
        g = y_t / float(np.median(Yb[F[f]]))
        bench[F[f]] *= g
        lv[f] = dict(gain=round(g, 3), L_star=round(float(K.lstar(y_t)), 1), vs_lining=round(float(np.log2(y_t / yl)), 3))
    yl_p = float(np.median(Yb[F["lpanel"]]))
    if yl_p < y_front_min:
        set_level("lpanel", y_front_min)
        yl_p = y_front_min
    c_l = float(np.median(clay[F["lpanel"]]))
    set_level("rpanel", max(yl_p * float(np.median(clay[F["rpanel"]])) / c_l, y_front_min))
    set_level("inner", max(yl_p * float(np.median(clay[F["inner"]])) / c_l, y_floor * 1.02))
    gshade = np.clip(clay / np.maximum(float(np.median(clay[F["lpanel"] & ~groove])), 1e-5), 0.35, 1.0)
    bench[groove] *= gshade[groove][:, None]
    rep["groove_px"] = int(groove.sum())
    rep["levels_set"] = dict(lining_Y=round(yl, 4), lining_L=round(float(K.lstar(yl)), 1), black_point_L_p01=12.7, walnut_floor_L=20.7, faces=lv)
    if rest.any():                                   # bevel pixels the rules leave out: their nearest assigned neighbour
        assigned = obj & ~rest
        filled = bench.copy()
        for _ in range(6):
            num = cv2.GaussianBlur(filled * assigned[..., None], (0, 0), 1.0)
            den = cv2.GaussianBlur(assigned.astype(np.float32), (0, 0), 1.0)[..., None]
            filled = np.where(assigned[..., None], filled, num / np.maximum(den, 1e-6))
            assigned = assigned | (den[..., 0] > 0.05)
        bench[rest] = filled[rest]
    base = ht.copy()
    inside = mask & ~obj
    base[inside] = ht[inside] * R[inside][:, None]
    al = cv2.GaussianBlur(obj.astype(np.float32), (0, 0), 0.6)
    al = np.where(obj, 1.0, np.clip(al * 2, 0, 1))[..., None] * mask[..., None]
    res = base * (1 - al) + bench * al
    o8 = np.clip(np.rint(K.to_srgb(res) * 255), 0, 255).astype(np.uint8)
    o8[~mask] = ht8[~mask]
    K.save(outp, o8)
    chk = K.rgb8(outp).astype(int)
    rep["outside_mask_max_diff_levels"] = int(np.abs(chk - ht8.astype(int))[~mask].max())
    rep["clay_quads_uv"] = {k: [[round(a, 4), round(b, 4)] for a, b in v] for k, v in Q.items()}
    rep["r1_quads_uv"] = R1
    rep["shading"] = mrep
    K.dump(repp, rep)
    print(rep)


if __name__ == "__main__":
    main(*sys.argv[1:5])
