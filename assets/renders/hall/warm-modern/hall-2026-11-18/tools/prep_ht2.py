#!/usr/bin/env python3
"""
prep_ht2.py: the model input and the masks of HT2 (route 12.1: ht.png + the walnut bench), render-agent 2026-11-18. 0 tokens.
  the mask  = the clay's bench (id 100 of wm-hall-2026-11-18/HT) and its contact shadow (where the clay with the bench is darker than the
              clay of 2026-11-16 without it, > 3 %, connected to the bench), dilated 12 px (route 12.1)
  the input = ht.png outside the mask, byte for byte; inside it:
    - floor and stone: ht.png times the clay's shading ratio (with / without the bench), smoothed, so the contact shadow and the darker
      zone under the seat edge are where the clay puts them
    - the bench: the clay's bench in linear light, scaled by (HT's walnut lining / the clay's walnut lining), so that its light relative to
      the lining is the clay's; then the lining's chroma; the front face held inside 0 to -2/3 stop under the lining (route 12.1)
  python3 prep_ht2.py <work_dir>   ->  ht2-input.png, ht2-mask.png (the 12 px mask), ht2-core.png (bench + shadow), prep-ht2.json
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402

N = "HT"


def lining_mask(cls, name=N, u=(0.814, 0.850)):
    m = np.isin(cls, (20, 21, 22)) & K.uvbox(name, u[0], u[1], 0.0, 1.0) & K.zband(name, 0.40, 1.65)
    return m


def masks(name, ids, near_px=(150, 260), thr=0.97, dil=12, old_name=None, top_z=None, z_fall=0.08, base_band=(400, 800), box=None, reach=0.20):
    """The object (clay ids) and its shading (the clay with it / the clay of 2026-11-16 without it), and the 12 px mask.
    The ratio is taken against its own median 400-800 px away (the two clays differ by about 1 % everywhere), and above `top_z` (the
    object's top) it fades over `z_fall` m: the clay's pale floor overstates the bounce the object takes away (route 12.1: a short contact
    shadow on the floor under the seat and a soft darker zone on the stone just below the seat edge; nothing is said above it). Beyond
    `near_px` it fades out by a smoothstep, so no shadow edge is left in the stone."""
    cls = K.clay_id(name)
    obj = np.isin(cls, ids)
    new = K.to_lin(K.rgb(K.clay_png(name))) @ K.W709
    old = K.to_lin(K.rgb(K.clay_png(old_name or name, old=True))) @ K.W709
    R = np.where(obj, 1.0, new / np.maximum(old, 1e-5))
    d = cv2.distanceTransform((~obj).astype(np.uint8), cv2.DIST_L2, 5)
    base = float(np.median(R[(d >= base_band[0]) & (d < base_band[1])]))
    R = np.minimum(R / base, 1.0)
    w = np.ones_like(R)
    if top_z is not None:
        P, ok = K.world(name)
        w = np.where(ok & (P[..., 2] > top_z), np.exp(-(P[..., 2] - top_z) / z_fall), 1.0)
    t = np.clip((d - near_px[0]) / float(near_px[1] - near_px[0]), 0, 1)
    w = w * (1 - t * t * (3 - 2 * t))
    if box is not None:                                   # the object's world box: the shadow fades out `reach` m from it
        P, ok = K.world(name)
        lo, hi = np.array(box[0]), np.array(box[1])
        q = np.maximum(np.maximum(lo - P, P - hi), 0)
        dw = np.sqrt((q * q).sum(-1))
        tw = np.clip(dw / reach, 0, 1)
        w = w * np.where(ok, 1 - tw * tw * (3 - 2 * tw), 0)
    R = 1 - (1 - R) * w
    Rs = np.where(obj, 1.0, cv2.GaussianBlur(R.astype(np.float32), (0, 0), 2.0))
    sh = (Rs < thr) & ~obj
    n, lab = cv2.connectedComponents((sh | obj).astype(np.uint8))
    keep_l = set(np.unique(lab[obj]).tolist()) - {0}
    sh &= np.isin(lab, list(keep_l))
    core = obj | sh
    # close the holes (a stone patch under the seat the ratio left out)
    inv = (~core).astype(np.uint8)
    n2, lab2, st, _ = cv2.connectedComponentsWithStats(inv)
    H, W = core.shape
    for k in range(1, n2):
        x, y, ww, hh, area = st[k]
        if x > 0 and y > 0 and x + ww < W and y + hh < H or (area < 20000 and not (x == 0 or x + ww == W)):
            core[lab2 == k] = True
    sh = core & ~obj
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * dil + 1, 2 * dil + 1))
    mask = cv2.dilate(core.astype(np.uint8), k) > 0
    return cls, obj, sh, core, mask, np.clip(Rs, 0.2, 1.0), dict(ratio_baseline=round(base, 4), top_z=top_z, z_fall_m=z_fall, near_px=list(near_px), box=box, reach_m=reach)


def walnut(inp_lin, clay_lin, obj, cls, normal, name, ref_still_lin, lin_u, front_band=(-2 / 3, 0.0)):
    """The clay's walnut object, carried to the still's lining level and chroma."""
    lm = lining_mask(cls, name, lin_u)
    Yc = clay_lin @ K.W709
    Ys = ref_still_lin @ K.W709
    g = float(np.median(Ys[lm]) / np.median(Yc[lm]))
    out = clay_lin * g
    front = obj & (normal[..., 0] > 0.7) if normal is not None else obj
    rep = dict(lining_px=int(lm.sum()), lining_still_Y=round(float(np.median(Ys[lm])), 4), lining_clay_Y=round(float(np.median(Yc[lm])), 4), gain=round(g, 4))
    if front.any():
        fs = float(np.log2(np.median((out @ K.W709)[front]) / np.median(Ys[lm])))
        rep["front_vs_lining_from_clay"] = round(fs, 3)
        tgt = min(max(fs, front_band[0] + 0.05), front_band[1] - 0.05)
        out = out * 2 ** (tgt - fs)
        rep["front_vs_lining_in_input"] = round(tgt, 3)
    lab = K.lab_from_lin(out)
    ls = K.lab_from_lin(ref_still_lin)
    a0, b0 = float(np.median(ls[lm][:, 1])), float(np.median(ls[lm][:, 2]))
    lab[obj, 1] = a0 + (lab[obj, 1] - lab[obj, 1].mean()) * 0.3
    lab[obj, 2] = b0 + (lab[obj, 2] - lab[obj, 2].mean()) * 0.3
    out[obj] = K.lin_from_lab(lab[obj])
    rep["lining_ab"] = [round(a0, 2), round(b0, 2)]
    rep["object_L_median"] = round(float(np.median(K.lab_from_lin(out)[obj][:, 0])), 1)
    return out, rep


def normals(name):
    p = os.path.join(K.SCR, "clay", "scratch", "passes", name + ".npz")
    if not os.path.exists(p):
        return None
    z = np.load(p)
    return z["normal"].astype(np.float32) / 127.0


def main(work, delineate=False, tag="ht2"):
    ht8 = K.rgb8(os.path.join(K.PREV, "ht.png"))
    ht = ht8.astype(np.float64) / 255
    cls, obj, sh, core, mask, R, mrep = masks(N, (K.BENCH_ID,), thr=0.95, top_z=0.45, box=((0.81, 6.70, 0.0), (1.21, 7.50, 0.45)), reach=0.20)
    ht_lin = K.to_lin(ht)
    clay_lin = K.to_lin(K.rgb(K.clay_png(N)))
    nrm = normals(N)
    res = ht_lin.copy()
    inside = mask & ~obj
    res[inside] = ht_lin[inside] * R[inside][:, None]
    b, rep = walnut(res, clay_lin, obj, cls, nrm, N, ht_lin, (0.814, 0.850))
    res[obj] = b[obj]
    if delineate:
        # fix 1 (HT2 r1 drew the bench frontally, its front-left corner at u 0.506 for 0.542): the faces of the clay bench told apart in
        # the input: the outer side of the left end panel (normal +Y) a little lighter, (the clay's edges darkened was tried and dropped)
        side = obj & (nrm[..., 1] > 0.7)
        res[side] *= 1.30
        rep["delineate"] = dict(plus_y_faces_px=int(side.sum()), gain=1.30, note="the +Y faces: the outer side of the left end panel and the inner "
                                "face of the right one; edge lines tried and dropped (they read as a moulding on the seat's front edge)")
    out = np.where(mask[..., None], K.to_srgb(res), ht)
    out8 = np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)
    out8[~mask] = ht8[~mask]
    K.save(os.path.join(work, tag + "-input.png"), out8)
    K.save(os.path.join(work, "ht2-mask.png"), np.where(mask, 255, 0).astype(np.uint8))
    K.save(os.path.join(work, "ht2-core.png"), np.where(core, 255, 0).astype(np.uint8))
    ys, xs = np.nonzero(obj)
    u0, v0 = K.uv_of_px(N, xs.min(), ys.min())
    u1, v1 = K.uv_of_px(N, xs.max() + 1, ys.max() + 1)
    rep.update(shading=mrep, mask_px=int(mask.sum()), bench_px=int(obj.sum()), shadow_px=int(sh.sum()), min_shading_ratio=round(float(R[sh].min()), 3) if sh.any() else None,
               bench_bbox_uv=[round(u0, 4), round(v0, 4), round(u1, 4), round(v1, 4)],
               outside_mask_max_diff_levels=int(np.abs(out8.astype(int) - ht8.astype(int))[~mask].max()), normals=nrm is not None)
    K.dump(os.path.join(work, "prep-" + tag + ".json"), rep)
    print(rep)


if __name__ == "__main__":
    main(sys.argv[1], delineate="--delineate" in sys.argv, tag=next((a.split("=")[1] for a in sys.argv if a.startswith("--tag=")), "ht2"))
