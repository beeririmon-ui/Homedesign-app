#!/usr/bin/env python3
"""
interp60.py: optical-flow frame interpolation to 60 fps, and a test harness that measures any interpolator
against exact frames (brief §8.1.2: render at the model's rate, interpolate to 60 fps locally, check edges and fine
textures before the sequences are cut).

The exact reference comes from a code pan (pan_reproject.py): it can be rendered at any frame rate, so a 24 fps
clip of it can be interpolated to 60 fps and compared frame by frame with the true 60 fps frames.

Interpolators
  dis           built in: OpenCV DIS optical flow both ways, Super-SloMo flow approximation for the in-between time,
                backward warping of both neighbours, forward-backward consistency weights (occlusions)
  minterpolate  ffmpeg's motion-compensated interpolation (mci, aobmc, bidirectional), as a baseline
  any other     --candidate NAME=DIR: frames written by RIFE or FILM (0001.png ... at 60 fps, same window)

Commands
  pantest   render the exact 24 and 60 fps frames of a pan window, run dis + minterpolate (+ candidates), report
  retime    frames at fractional source positions (a progress table), from a 24 fps clip: the step that turns a
            model clip into frames uniform in path progress at 60 fps
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pan_reproject as pr  # noqa: E402


# ----------------------------------------------------------------------------------------------------------------
# DIS interpolation
# ----------------------------------------------------------------------------------------------------------------
_DIS = None


def _flow(a8: np.ndarray, b8: np.ndarray, scale: float = 0.5) -> np.ndarray:
    global _DIS
    if _DIS is None:
        _DIS = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        _DIS.setUseSpatialPropagation(True)
    ga = cv2.cvtColor(a8, cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor(b8, cv2.COLOR_RGB2GRAY)
    if scale != 1.0:
        ga = cv2.resize(ga, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        gb = cv2.resize(gb, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    f = _DIS.calc(ga, gb, None)
    if scale != 1.0:
        f = cv2.resize(f, (a8.shape[1], a8.shape[0]), interpolation=cv2.INTER_LINEAR) / scale
    return f


def _backwarp(img: np.ndarray, flow: np.ndarray) -> np.ndarray:
    h, w = flow.shape[:2]
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(img, gx + flow[..., 0], gy + flow[..., 1], cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def dis_interpolate(I0: np.ndarray, I1: np.ndarray, tau: float, flows=None) -> np.ndarray:
    """Frame at time tau (0..1) between I0 and I1 (float RGB 0..1)."""
    a8, b8 = pr.to8(I0), pr.to8(I1)
    F01, F10 = flows if flows is not None else (_flow(a8, b8), _flow(b8, a8))
    t = tau
    Ft0 = -(1 - t) * t * F01 + t * t * F10
    Ft1 = (1 - t) * (1 - t) * F01 - t * (1 - t) * F10
    W0 = _backwarp(I0, Ft0)
    W1 = _backwarp(I1, Ft1)
    # forward-backward consistency of each source at the sample point: low where a pixel is occluded
    e0 = np.linalg.norm(F01 + _backwarp(F10, F01), axis=2)
    e1 = np.linalg.norm(F10 + _backwarp(F01, F10), axis=2)
    v0 = _backwarp(np.exp(-e0 / 1.5)[..., None].astype(np.float32), Ft0)
    v1 = _backwarp(np.exp(-e1 / 1.5)[..., None].astype(np.float32), Ft1)
    v0 = v0.reshape(v0.shape[0], v0.shape[1], 1)
    v1 = v1.reshape(v1.shape[0], v1.shape[1], 1)
    wa = (1 - t) * v0 + 1e-4
    wb = t * v1 + 1e-4
    return np.clip((wa * W0 + wb * W1) / (wa + wb), 0, 1)


def retime(frames: list[np.ndarray], positions: list[float]) -> list[np.ndarray]:
    """Frames at fractional positions of a clip (0 = first frame). Flows are computed once per neighbour pair."""
    cache: dict[int, tuple] = {}
    out = []
    for x in positions:
        x = min(max(x, 0.0), len(frames) - 1.0)
        i = int(math.floor(x))
        tau = x - i
        if tau < 1e-6 or i >= len(frames) - 1:
            out.append(frames[min(i, len(frames) - 1)].copy())
            continue
        if i not in cache:
            a8, b8 = pr.to8(frames[i]), pr.to8(frames[i + 1])
            cache = {i: (_flow(a8, b8), _flow(b8, a8))}
        out.append(dis_interpolate(frames[i], frames[i + 1], tau, cache[i]))
    return out


# ----------------------------------------------------------------------------------------------------------------
# metrics
# ----------------------------------------------------------------------------------------------------------------
def masks(ref8: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    g = cv2.cvtColor(ref8, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1)
    mag = np.sqrt(gx * gx + gy * gy)
    edges = mag > np.percentile(mag, 92)
    mu = cv2.blur(g, (7, 7))
    sd = np.sqrt(np.maximum(cv2.blur(g * g, (7, 7)) - mu * mu, 0))
    ed = cv2.dilate(edges.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    tex = (sd > np.percentile(sd, 80)) & ~ed
    return edges, tex


def compare(ref: np.ndarray, test: np.ndarray, edges: np.ndarray, tex: np.ndarray) -> dict:
    d = np.abs(ref.astype(np.float32) - test.astype(np.float32)).mean(axis=2)
    mse = float((d ** 2).mean())
    return dict(psnr=round(10 * math.log10(255 ** 2 / max(mse, 1e-9)), 2), mae=round(float(d.mean()), 3),
                mae_edges=round(float(d[edges].mean()), 3), mae_texture=round(float(d[tex].mean()), 3),
                p999=round(float(np.percentile(d, 99.9)), 1), share_over_25=round(float((d > 25).mean()), 5))


# ----------------------------------------------------------------------------------------------------------------
# pantest
# ----------------------------------------------------------------------------------------------------------------
def pantest(a_path, a_cam, b_path, b_cam, out_dir, size=(1920, 1080), deg_per_s=8.0, t0=1.5, dur=1.0,
            candidates: dict | None = None, keep_frames: bool = False) -> dict:
    w, h = size
    os.makedirs(out_dir, exist_ok=True)
    work = os.path.join(out_dir, "frames")
    for sub in ("src24", "exact60", "dis60", "minterp60"):
        os.makedirs(os.path.join(work, sub), exist_ok=True)
    pan = pr.Pan(pr.load(a_path), a_cam, pr.load(b_path), b_cam, kind="master")
    T = abs(pan.dyaw) / deg_per_s
    n24 = int(round(dur * 24)) + 1
    n60 = int(round(dur * 60)) + 1
    src = []
    for k in range(n24):
        img, _ = pan.frame((t0 + k / 24) / T, w, h)
        src.append(img)
        Image.fromarray(pr.to8(img)).save(os.path.join(work, "src24", f"{k + 1:04d}.png"), compress_level=1)
    exact = []
    for j in range(n60):
        img, _ = pan.frame((t0 + j / 60) / T, w, h)
        exact.append(pr.to8(img))
        Image.fromarray(exact[-1]).save(os.path.join(work, "exact60", f"{j + 1:04d}.png"), compress_level=1)
    # dis
    dis = retime(src, [j * 24 / 60 for j in range(n60)])
    for j, img in enumerate(dis):
        Image.fromarray(pr.to8(img)).save(os.path.join(work, "dis60", f"{j + 1:04d}.png"), compress_level=1)
    # ffmpeg minterpolate
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", os.path.join(work, "src24", "%04d.png"),
                    "-vf", "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
                    "-frames:v", str(n60), os.path.join(work, "minterp60", "%04d.png")], check=True)
    sets = {"dis": os.path.join(work, "dis60"), "minterpolate": os.path.join(work, "minterp60")}
    sets.update(candidates or {})
    rep: dict = dict(window=dict(t0_s=t0, dur_s=dur, pan_deg=abs(pan.dyaw), render_deg_per_s=deg_per_s,
                                 px_per_source_frame=round(math.radians(deg_per_s / 24) * pr.FX_REL * w, 2)),
                     size=[w, h], methods={})
    worst_block = None
    acc_err = None
    for name, d in sets.items():
        rows = []
        for j in range(n60):
            if (j * 24) % 60 == 0:
                continue                                 # coincides with a source frame
            p = os.path.join(d, f"{j + 1:04d}.png")
            if not os.path.exists(p):
                continue
            test = np.asarray(Image.open(p).convert("RGB"))
            e, t = masks(exact[j])
            rows.append(dict(frame=j + 1, **compare(exact[j], test, e, t)))
            if name == "dis":
                err = np.abs(exact[j].astype(np.float32) - test.astype(np.float32)).mean(axis=2)
                acc_err = err if acc_err is None else acc_err + err
        if rows:
            keys = [k for k in rows[0] if k != "frame"]
            rep["methods"][name] = dict(frames=len(rows), mean={k: round(float(np.mean([r[k] for r in rows])), 3) for k in keys},
                                        worst={k: (min if k == "psnr" else max)(r[k] for r in rows) for k in keys})
    # the duplicate-frame baseline: what 60 fps playback of the 24 fps clip without interpolation would show
    rows = []
    for j in range(n60):
        if (j * 24) % 60 == 0:
            continue
        test = pr.to8(src[int(round(j * 24 / 60))])
        e, t = masks(exact[j])
        rows.append(compare(exact[j], test, e, t))
    rep["methods"]["nearest (no interpolation)"] = dict(frames=len(rows), mean={k: round(float(np.mean([r[k] for r in rows])), 3) for k in rows[0]})
    # sheet: the block where dis errs most, exact | dis | minterpolate | |dis - exact| x4
    if acc_err is not None:
        bs = 160
        be = cv2.resize(acc_err, (w // bs, h // bs), interpolation=cv2.INTER_AREA)
        by, bx = np.unravel_index(np.argmax(be), be.shape)
        cx, cy = int((bx + 0.5) * bs), int((by + 0.5) * bs)
        x0, y0 = max(0, min(w - 360, cx - 180)), max(0, min(h - 240, cy - 120))
        j = 1                                                     # frame 2: source position 0.4 (mid-way)
        tiles = []
        for name in ("exact", "dis", "minterpolate"):
            img = exact[j] if name == "exact" else np.asarray(Image.open(os.path.join(sets[name], f"{j + 1:04d}.png")).convert("RGB"))
            tiles.append(img[y0:y0 + 240, x0:x0 + 360])
        dimg = np.asarray(Image.open(os.path.join(sets["dis"], f"{j + 1:04d}.png")).convert("RGB")).astype(np.float32)
        dd = np.clip(np.abs(dimg - exact[j].astype(np.float32)) * 4, 0, 255).astype(np.uint8)[y0:y0 + 240, x0:x0 + 360]
        tiles.append(dd)
        sheet = np.concatenate([np.concatenate(tiles[:2], axis=1), np.concatenate(tiles[2:], axis=1)], axis=0)
        sheet = cv2.resize(sheet, (sheet.shape[1] * 2, sheet.shape[0] * 2), interpolation=cv2.INTER_NEAREST)
        sp = os.path.join(out_dir, "interp60-worst-block.png")
        Image.fromarray(sheet).save(sp)
        rep["sheet"] = dict(file=sp, frame=j + 1, crop=[x0, y0, 360, 240], layout="exact | dis / minterpolate | |dis-exact| x4")
        worst_block = [int(x0), int(y0)]
    # the 60 fps clip of the dis result, for the eye
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "60", "-i", os.path.join(sets["dis"], "%04d.png"),
                    "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-an", os.path.join(out_dir, "interp60-dis.mp4")], check=True)
    rep["clip"] = os.path.join(out_dir, "interp60-dis.mp4")
    if not keep_frames:
        shutil.rmtree(work, ignore_errors=True)
    with open(os.path.join(out_dir, "interp60.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pantest")
    p.add_argument("--a", required=True)
    p.add_argument("--a-cam", required=True)
    p.add_argument("--b", required=True)
    p.add_argument("--b-cam", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--size", default="1920x1080")
    p.add_argument("--t0", type=float, default=1.5, help="start of the 1 s window in the constant-speed clip")
    p.add_argument("--candidate", action="append", default=[], help="NAME=DIR of 60 fps frames from RIFE / FILM")
    p.add_argument("--keep-frames", action="store_true")
    p = sub.add_parser("retime")
    p.add_argument("--src", required=True, help="dir of 0001.png ... (the model clip at its own rate)")
    p.add_argument("--positions", required=True, help="JSON list of fractional source positions, one per output frame")
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "pantest":
        w, h = (int(x) for x in a.size.split("x"))
        cands = dict(c.split("=", 1) for c in a.candidate)
        rep = pantest(a.a, pr.parse_cam(a.a_cam), a.b, pr.parse_cam(a.b_cam), a.out, (w, h), t0=a.t0, candidates=cands,
                      keep_frames=a.keep_frames)
        print(json.dumps(rep, indent=1))
        return 0
    if a.cmd == "retime":
        names = sorted(f for f in os.listdir(a.src) if f.endswith(".png"))
        frames = [pr.load(os.path.join(a.src, f)) for f in names]
        pos = json.load(open(a.positions))
        os.makedirs(a.out, exist_ok=True)
        for k, img in enumerate(retime(frames, pos)):
            Image.fromarray(pr.to8(img)).save(os.path.join(a.out, f"{k + 1:04d}.png"))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
