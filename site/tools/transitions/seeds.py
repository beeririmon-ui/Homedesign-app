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
  ht           (2026-11-17) the seed of the HT still (the threshold, the end of clip 1a and the start of clip 1b): the
               far wall = HD carried back to HT through its depth (a plane: exact), so that HT and HD show the SAME
               plaster and stone; the corner, the walnut lining and the living room = HDx, then base.png, through
               their depths. Priority HD > HDx > base.png; a source map says which pixel came from where. With it,
               clip 1b can be built in code (wm-arrival-from-door-2026-11-14.md section 10).

  python3 seeds.py frame --still HDx.png --canvas tall --out hdx-frame.png
  python3 seeds.py clip1-first --d0 D0.png --d0o D0o.png --out clip1-first.png
  python3 seeds.py hd --hdx HDx.png --out DIR
  python3 seeds.py hdx --base base.png --depth assets/renders/living-room/warm-modern/depth.png --out DIR [--w 2496 --h 1664]
  python3 seeds.py ht --hd HD.png --hdx HDx.png --base base.png --clay assets/blockout/house/framing/wm-door-2026-11-16 --out DIR
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
    t = sub.add_parser("ht")
    t.add_argument("--hd", required=True, help="the HD still (3:2 canvas)")
    t.add_argument("--hdx", required=True, help="the HDx still (3:2 canvas)")
    t.add_argument("--base", required=True, help="base.png (the M0 plate)")
    t.add_argument("--clay", required=True, help="the clay folder with HD-depth.png and HDx-depth.png (the stills are locked to it)")
    t.add_argument("--m0-depth", default="assets/renders/living-room/warm-modern/depth.png")
    t.add_argument("--w", type=int, default=2720)
    t.add_argument("--h", type=int, default=1530)
    t.add_argument("--out", required=True)
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
    if a.cmd == "ht":
        hcv = cg.Canvas(a.w, a.h, cg.Canvas.base(a.w).box)
        filled = np.zeros((a.h, a.w), bool)
        seed = np.full((a.h, a.w, 3), 0.5, np.float32)
        src = np.zeros((a.h, a.w, 3), np.uint8)
        stats = {}

        def depth_for(path, shape, room=False):
            depth, valid = cg.load_room_depth(path) if room else cg.load_depth_png(path)
            if depth.shape[:2] != shape[:2]:
                depth = cv2.resize(depth, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
                valid = cv2.resize(valid.astype(np.uint8), (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST) > 0
            return depth, valid

        for name, still, cam, canvas, dpath, room, keep, colour in (
                ("HD", a.hd, cg.HD, "tall", os.path.join(a.clay, "HD-depth.png"), False, lambda P: P[..., 0] < 0.85, (255, 0, 0)),
                ("HDx", a.hdx, cg.HDX, "tall", os.path.join(a.clay, "HDx-depth.png"), False, lambda P: np.ones(P.shape[:2], bool), (0, 255, 0)),
                ("base.png", a.base, cg.M0, "base", a.m0_depth, True, lambda P: P[..., 1] < 6.20, (0, 0, 255))):
            im = td.load(still)
            scv = td.canvas_for(canvas, im.shape[1], im.shape[0])
            depth, valid = depth_for(dpath, im.shape, room)
            img, ok, dd = cg.dibr(im, depth, cam, scv, cg.HT, hcv, depth_valid=valid)
            us, vs = hcv.uv()
            P = cg.HT.unproject(us, vs, np.where(np.isfinite(dd), dd, 1.0))
            ok &= np.isfinite(dd) & keep(P)
            ok = cv2.erode(ok.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
            new = ok & ~filled
            seed[new] = img[new]
            src[new] = colour
            filled |= new
            fb = [int(round(b)) for b in hcv.box]
            stats[name] = round(float(new[fb[1]:fb[3], fb[0]:fb[2]].mean()), 4)
        os.makedirs(a.out, exist_ok=True)
        td.save(os.path.join(a.out, "ht-seed.png"), seed)
        cv2.imwrite(os.path.join(a.out, "ht-seed-mask.png"), np.where(filled, 255, 0).astype(np.uint8))
        cv2.imwrite(os.path.join(a.out, "ht-seed-source.png"), cv2.cvtColor(src, cv2.COLOR_RGB2BGR))
        fb = [int(round(b)) for b in hcv.box]
        print(f"HT's 16:9 frame: from HD {stats['HD']:.1%}, from HDx {stats['HDx']:.1%}, from base.png {stats['base.png']:.1%}; "
              f"new {1 - filled[fb[1]:fb[3], fb[0]:fb[2]].mean():.1%}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
