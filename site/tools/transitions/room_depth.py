#!/usr/bin/env python3
"""
room_depth.py: the depth map of a room's main view for the site: assets/renders/<room>/<style>/depth.png, grey,
near = bright, with CRISP edges around the furniture (the zoom parallax, the landing of the arrival and the lock of
the next room's vista all lean on them). 0 var2 tokens.

Source: the clay's depth pass of the same camera on the same canvas (render-agent, 16-bit, metres = value / 5000).
The render is locked to the clay within a couple of pixels, but furniture in the render has its own outline (rounded
cushions, legs), so the clay's depth edges are SNAPPED to the picture:
  around every depth step, each pixel is given to the near side or to the far side, whichever its colour in the render
  agrees with (a joint bilateral vote over a 13 x 13 window); it then takes that side's depth. Where the two sides
  have the same colour (bouclé against plaster) the clay's edge is kept. No depth value is ever a mix of the two sides.

  python3 room_depth.py base --clay-depth b/S11-depth.png --image base.png --camera M0 --out assets/renders/living-room/warm-modern/depth.png
                             [--preview check.jpg]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camgeo as cg  # noqa: E402


def snap_edges(depth: np.ndarray, valid: np.ndarray, img: np.ndarray, radius: int = 6, step_rel: float = 0.06,
               step_abs: float = 0.08, sigma_c: float = 14.0 / 255.0, margin: float = 1.35) -> tuple[np.ndarray, np.ndarray, dict]:
    """depth (metres, float32), valid (bool: False = no surface), img (float RGB 0..1, same size).
    Returns (depth snapped, valid snapped, report)."""
    FAR = 1e3
    d = np.where(valid, depth, FAR).astype(np.float32)
    k = np.ones((2 * radius + 1, 2 * radius + 1), np.uint8)
    dn, df = cv2.erode(d, k), cv2.dilate(d, k)
    band = (df > dn * (1 + step_rel)) & (df - dn > step_abs)
    ys, xs = np.nonzero(band)
    if len(xs) == 0:
        return depth.copy(), valid.copy(), dict(band_px=0, moved_px=0)
    H, W = d.shape
    Ip = img[ys, xs]                                           # (n, 3)
    dnp, dfp = dn[ys, xs], df[ys, xs]
    mid = np.sqrt(dnp * np.minimum(dfp, dnp * 50))             # geometric middle: the split between the two sides
    wn = np.zeros(len(xs), np.float32)
    wf = np.zeros(len(xs), np.float32)
    sn = np.zeros(len(xs), np.float32)
    sf = np.zeros(len(xs), np.float32)
    for dy in range(-radius, radius + 1):
        yy = np.clip(ys + dy, 0, H - 1)
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > radius * radius:
                continue
            xx = np.clip(xs + dx, 0, W - 1)
            dq = d[yy, xx]
            c = img[yy, xx] - Ip
            w = np.exp(-(c * c).sum(axis=1) / (2 * sigma_c * sigma_c)).astype(np.float32)
            near = dq <= mid
            wn += np.where(near, w, 0)
            sn += np.where(near, w * dq, 0)
            wf += np.where(~near, w, 0)
            sf += np.where(~near, w * np.minimum(dq, FAR), 0)
    cur_near = d[ys, xs] <= mid
    to_near = wn > wf * margin
    to_far = wf > wn * margin
    new_near = np.where(to_near, True, np.where(to_far, False, cur_near))
    # the side's own depth: where the pixel already is on that side keep its value, else take the side's weighted mean
    val = np.where(new_near, sn / np.maximum(wn, 1e-6), sf / np.maximum(wf, 1e-6))
    keep = new_near == cur_near
    out = d.copy()
    out[ys, xs] = np.where(keep, d[ys, xs], val)
    moved = int((~keep).sum())
    vout = out < FAR * 0.5
    return np.where(vout, out, np.inf).astype(np.float32), vout, dict(band_px=int(len(xs)), moved_px=moved, to_near_px=int((~keep & new_near).sum()),
                                                                       to_far_px=int((~keep & ~new_near).sum()))


def edge_sharpness(depth: np.ndarray, valid: np.ndarray, step_rel: float = 0.06) -> dict:
    """How crisp the steps are: at a step, the share of pixels whose depth lies strictly between its two sides."""
    FAR = 1e3
    d = np.where(valid, depth, FAR).astype(np.float32)
    k3 = np.ones((3, 3), np.uint8)
    dn, df = cv2.erode(d, k3), cv2.dilate(d, k3)
    step = df > dn * (1 + step_rel)
    k7 = np.ones((7, 7), np.uint8)
    dn7, df7 = cv2.erode(d, k7), cv2.dilate(d, k7)
    between = step & (d > dn7 * 1.02) & (d < df7 / 1.02)
    return dict(step_px=int(step.sum()), between_px=int(between.sum()), between_share=float(between.sum() / max(1, step.sum())))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("base")
    b.add_argument("--clay-depth", required=True)
    b.add_argument("--image", required=True, help="the render the map belongs to (base.png), on the same canvas")
    b.add_argument("--camera", default="M0")
    b.add_argument("--out", required=True)
    b.add_argument("--preview")
    b.add_argument("--note", default="")
    a = ap.parse_args(argv)
    depth, valid = cg.load_depth_png(a.clay_depth)
    img = cv2.cvtColor(cv2.imread(a.image, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    if img.shape[:2] != depth.shape[:2]:
        raise SystemExit(f"the clay depth is {depth.shape[1]} x {depth.shape[0]}, the image {img.shape[1]} x {img.shape[0]}: they must share a canvas")
    before = edge_sharpness(depth, valid)
    snapped, vs, rep = snap_edges(depth, valid, img)
    after = edge_sharpness(snapped, vs)
    cam = {"M0": cg.M0, "HD": cg.HD, "HDx": cg.HDX, "D0": cg.D0}[a.camera]
    cvs = cg.Canvas(depth.shape[1], depth.shape[0], cg.Canvas.base(depth.shape[1]).box)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    info = cg.save_room_depth(a.out, snapped, vs, dict(
        camera=dict(id=a.camera, loc=list(cam.loc), yaw_deg_left=cam.yaw, lens_mm=24, u0=cam.u0, v0=cam.v0),
        canvas="the canvas of the image; the 16:9 camera frame at frame_box (pixels)", frame_box=[round(x, 2) for x in cvs.box],
        image=os.path.relpath(a.image, os.path.dirname(os.path.abspath(a.out))),
        source=dict(clay_depth=a.clay_depth, rule="clay depth pass, edges snapped to the image (site/tools/transitions/room_depth.py)"),
        covers="the room as the image shows it (the empty room for base.png): shell and fixed furniture, no product layers",
        snap=rep, crispness=dict(before=before, after=after), no_surface_px=int((~vs).sum()), note=a.note))
    # read back: the file must give the same metres
    back, vb = cg.load_room_depth(a.out)
    err = np.abs(back[vs] - snapped[vs]) / snapped[vs]
    info["roundtrip_rel_err_max"] = float(err.max())
    with open(os.path.splitext(a.out)[0] + ".json", "w") as fh:
        json.dump(info, fh, indent=1, ensure_ascii=False)
    if a.preview:
        # the depth steps drawn on the image: clay (red) and snapped (green)
        def steps(dd, vv):
            x = np.where(vv, dd, 1e3).astype(np.float32)
            k3 = np.ones((3, 3), np.uint8)
            return cv2.dilate(x, k3) > cv2.erode(x, k3) * 1.06
        pv = (img * 255).astype(np.uint8)
        pv[steps(depth, valid)] = (255, 40, 40)
        pv[steps(snapped, vs)] = (40, 230, 40)
        cv2.imwrite(a.preview, cv2.cvtColor(pv, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(json.dumps({k: info[k] for k in ("d_near_m", "d_far_m", "snap", "crispness", "no_surface_px", "roundtrip_rel_err_max")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
