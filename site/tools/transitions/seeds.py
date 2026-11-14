#!/usr/bin/env python3
"""
seeds.py: the images the arrival's stills and clips start from, cut or reprojected in code so that what two pictures
share is the SAME pixels in both. 0 var2 tokens.

  frame        the 16:9 camera frame of a still at 1920 x 1080: what the video model gets as a first or last frame
               (the same resampling the end locks use, so the clip's ends and the stills agree to the pixel)
  clip1-first  the first frame of clip 1: D0o with the door leaf at 90 degrees, composed in code from D0's leaf
  hd           the seed of the HD still: its canvas with the part HDx already shows (the right 28 %) filled by HDx
               reprojected (exact: same point), plus the mask of that part. render-agent renders the rest on the clay
               and keeps the seeded part ("HD built from HDx").
  hdx          the seed of the HDx still: the living room seen through the opening = base.png reprojected through
               the M0 depth map, plus the mask of what base.png really shows from there (the rest is new: the hall,
               and the living-room floor in front of M0's frame)

  python3 seeds.py frame --still HDx.png --canvas tall --out hdx-frame.png
  python3 seeds.py clip1-first --d0 D0.png --d0o D0o.png --out clip1-first.png
  python3 seeds.py hd --hdx HDx.png --out DIR
  python3 seeds.py hdx --base base.png --depth assets/renders/living-room/warm-modern/depth.png --out DIR [--w 2496 --h 1664]
"""
from __future__ import annotations

import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camgeo as cg  # noqa: E402
import turn_door as td  # noqa: E402

OVS_X = cg.BASE_BOX[0] / (cg.BASE_BOX[2] - cg.BASE_BOX[0])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("frame")
    f.add_argument("--still", required=True)
    f.add_argument("--canvas", default="base", choices=["base", "tall", "frame"])
    f.add_argument("--w", type=int, default=1920)
    f.add_argument("--out", required=True)
    c = sub.add_parser("clip1-first")
    c.add_argument("--d0", required=True)
    c.add_argument("--d0o", required=True)
    c.add_argument("--canvas", default="base", choices=["base", "tall", "frame"])
    c.add_argument("--w", type=int, default=1920)
    c.add_argument("--out", required=True)
    h = sub.add_parser("hd")
    h.add_argument("--hdx", required=True)
    h.add_argument("--out", required=True)
    x = sub.add_parser("hdx")
    x.add_argument("--base", required=True)
    x.add_argument("--depth", required=True, help="the room depth map (depth.png with its depth.json), or a clay depth pass with --clay-pass")
    x.add_argument("--clay-pass", action="store_true")
    x.add_argument("--w", type=int, default=2496)
    x.add_argument("--h", type=int, default=1664)
    x.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "frame":
        im = td.load(a.still)
        cvs = td.canvas_for(a.canvas, im.shape[1], im.shape[0])
        td.save(a.out, cvs.crop_frame(im, a.w))
        return 0
    if a.cmd == "clip1-first":
        d0, d0o = td.load(a.d0), td.load(a.d0o)
        cvs = td.canvas_for(a.canvas, d0.shape[1], d0.shape[0])
        td.save(a.out, cvs.crop_frame(td.door_frame(d0o, d0, cg.D0, cvs, 90.0), a.w))
        return 0
    if a.cmd == "hd":
        hdx = td.load(a.hdx)
        cvs = td.canvas_for("tall", hdx.shape[1], hdx.shape[0])
        img, cov = cg.rot_warp(hdx, cg.HDX, cvs, cg.HD, cvs)
        os.makedirs(a.out, exist_ok=True)
        td.save(os.path.join(a.out, "hd-seed.png"), np.where(cov[..., None], img, 0.5))
        cv2.imwrite(os.path.join(a.out, "hd-seed-mask.png"), np.where(cov, 255, 0).astype(np.uint8))
        us, _ = cvs.uv()
        cols = np.where(cov.any(axis=0))[0]
        print(f"HDx fills HD's canvas from u = {us[0, cols.min()]:.3f} to {us[0, cols.max()]:.3f} ({cov.mean():.1%} of the canvas)")
        return 0
    if a.cmd == "hdx":
        base = td.load(a.base)
        bcv = td.canvas_for("base", base.shape[1], base.shape[0])
        if a.clay_pass:
            depth, valid = cg.load_depth_png(a.depth)
        else:
            depth, valid = cg.load_room_depth(a.depth)
        if depth.shape[:2] != base.shape[:2]:
            depth = cv2.resize(depth, (base.shape[1], base.shape[0]), interpolation=cv2.INTER_NEAREST)
            valid = cv2.resize(valid.astype(np.uint8), (base.shape[1], base.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        tcv = cg.Canvas.tall(a.w, a.h, OVS_X)
        img, ok, dd = cg.dibr(base, depth, cg.M0, bcv, cg.HDX, tcv, depth_valid=valid)
        # only what lies in the living room (beyond the wall plane Y 6.20) counts: the hall is new
        us, vs = tcv.uv()
        P = cg.HDX.unproject(us, vs, np.where(np.isfinite(dd), dd, 1.0))
        ok &= np.isfinite(dd) & (P[..., 1] < 6.20)
        ok = cv2.erode(ok.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        os.makedirs(a.out, exist_ok=True)
        td.save(os.path.join(a.out, "hdx-seed.png"), np.where(ok[..., None], img, 0.5))
        cv2.imwrite(os.path.join(a.out, "hdx-seed-mask.png"), np.where(ok, 255, 0).astype(np.uint8))
        fb = [int(round(b)) for b in tcv.box]
        print(f"base.png fills {ok[fb[1]:fb[3], fb[0]:fb[2]].mean():.1%} of HDx's 16:9 frame ({ok.mean():.1%} of the canvas)")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
