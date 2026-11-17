#!/usr/bin/env python3
"""
assemble.py: from a raw model clip (or from clay stations) to a "bank": the frames of one straight move, uniform in
DISTANCE along the line, with both ends locked to our stills. 0 var2 tokens. The bank is what export_arrival.py
plays at any speed, forward or backward.

  bank       raw clip + the walk test's progress table + the two end stills -> the bank
               1 end locks   frame 1 becomes the first still, frame N the last still, pixel for pixel; what the model
                             drew differently (position and colour) fades out over the neighbouring frames (no dissolve
                             of the whole picture: the model frame is first moved onto the still along the optical flow)
               2 grade       a gain per channel that takes the model's first frame to the first still and its last
                             frame to the last still, interpolated along the walk; then deflicker (frame brightness
                             follows its own smooth trend)
               3 resample    frames at equal steps of distance, taken at fractional positions of the clip with DIS
                             optical-flow interpolation (TR1: DIS only)
  clay-bank  the same bank from clay stations with depth passes (render-agent's framing folder), by depth
             reprojection from the two nearest stations: the animatic
  selftest   a model-like clip from the proxy house (uneven speed, flicker, a colour drift, end frames a few pixels
             and a few levels off) -> bank, against the exact frames

  python3 assemble.py bank --frames clip.mp4 --report walk.json --first A.png --last B.png --canvas-first tall
                           --canvas-last base --n 145 --out DIR
  python3 assemble.py clay-bank --stations DIR --prefix b/S --from-cam HDx --to-cam M0 --n 145 --w 960 --out DIR
  python3 assemble.py selftest --out DIR
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camgeo as cg  # noqa: E402

_DIS = None


def flow(a8: np.ndarray, b8: np.ndarray, scale: float = 0.5) -> np.ndarray:
    """DIS optical flow a -> b (pixels of a): b(x + f(x)) ~ a(x)."""
    global _DIS
    if _DIS is None:
        _DIS = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        _DIS.setUseSpatialPropagation(True)
    ga, gb = cv2.cvtColor(a8, cv2.COLOR_RGB2GRAY), cv2.cvtColor(b8, cv2.COLOR_RGB2GRAY)
    if scale != 1.0:
        ga = cv2.resize(ga, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        gb = cv2.resize(gb, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    f = _DIS.calc(ga, gb, None)
    if scale != 1.0:
        f = cv2.resize(f, (a8.shape[1], a8.shape[0]), interpolation=cv2.INTER_LINEAR) / scale
    return f


def backwarp(img: np.ndarray, f: np.ndarray) -> np.ndarray:
    h, w = f.shape[:2]
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(img, gx + f[..., 0], gy + f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def interpolate(I0: np.ndarray, I1: np.ndarray, tau: float, f01=None, f10=None) -> np.ndarray:
    """The frame at fraction tau between two frames (uint8 RGB): both neighbours warped along the flow to the
    in-between time, weighted by time and by forward-backward consistency (occlusions)."""
    if tau <= 1e-4:
        return I0
    if tau >= 1 - 1e-4:
        return I1
    f01 = flow(I0, I1) if f01 is None else f01
    f10 = flow(I1, I0) if f10 is None else f10
    # flow at the in-between time, approximated as in Super-SloMo
    ft0 = -(1 - tau) * tau * f01 + tau * tau * f10
    ft1 = (1 - tau) * (1 - tau) * f01 - tau * (1 - tau) * f10
    w0 = backwarp(I0, ft0).astype(np.float32)
    w1 = backwarp(I1, ft1).astype(np.float32)
    # consistency: where the two warps disagree strongly, trust the nearer frame
    d = np.abs(w0 - w1).mean(axis=2, keepdims=True)
    k = np.clip(d / 24.0, 0, 1)
    a = (1 - tau) * (1 - k) + (1.0 if tau < 0.5 else 0.0) * k
    return np.clip(a * w0 + (1 - a) * w1 + 0.5, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------------------------------------------------
def end_lock(frames: list[np.ndarray], first: np.ndarray | None, last: np.ndarray | None, n: int = 10) -> dict:
    """In place. frames: uint8 RGB. first / last: the stills at the same size (or None to leave that end)."""
    rep = {}
    for key, still, order in (("first", first, range(0, n + 1)), ("last", last, range(len(frames) - 1, len(frames) - n - 2, -1))):
        if still is None:
            continue
        idx = [i for i in order if 0 <= i < len(frames)]
        end = frames[idx[0]]
        g = flow(still, end)                                   # still(x) ~ end(x + g)
        moved = backwarp(end, g).astype(np.float32)
        resid = still.astype(np.float32) - moved               # what is still different after the move: colour, fine texture
        rep[key] = dict(shift_px_median=float(np.median(np.hypot(g[..., 0], g[..., 1]))), shift_px_p95=float(np.percentile(np.hypot(g[..., 0], g[..., 1]), 95)),
                        colour_resid_levels_mean=float(np.abs(resid).mean()))
        for k, i in enumerate(idx):
            if k == 0:
                frames[i] = still.copy()
                continue
            w = 1 - k / (n + 1)
            w = w * w * (3 - 2 * w)
            # the correction travels with the picture: frame i's point x shows the end frame's point x + h(x), so it
            # takes the move and the colour residual found there (2026-11-17: held still on screen, the residual of
            # a thin joint line stayed behind as a faint second line while the wall slid past it)
            h = flow(frames[i], end)                           # end(x + h) ~ frame i(x)
            frames[i] = np.clip(backwarp(frames[i], w * backwarp(g, h)).astype(np.float32) + w * backwarp(resid, h) + 0.5,
                                0, 255).astype(np.uint8)
    return rep


def robust_gain(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Per-channel gain that takes src to dst (medians of the mid-tones on a small copy)."""
    a = cv2.resize(src, (160, 90), interpolation=cv2.INTER_AREA).astype(np.float32)
    b = cv2.resize(dst, (160, 90), interpolation=cv2.INTER_AREA).astype(np.float32)
    g = []
    for c in range(3):
        m = (a[..., c] > 24) & (a[..., c] < 235)
        g.append(float(np.median(b[..., c][m] / np.maximum(a[..., c][m], 1.0))) if m.sum() > 100 else 1.0)
    return np.array(g, np.float32)


def exposure_track(frames: list[np.ndarray], work_w: int = 480) -> tuple[np.ndarray, dict]:
    """The clip's own exposure, frame by frame, measured on the SAME surfaces: each frame is moved onto the previous
    one along the optical flow, and the median log-ratio of the matched pixels (mid-tones, away from edges, flow
    consistent both ways) is that step's exposure change, per channel. In a real walk with the exposure locked a
    surface keeps its brightness, so every change found here is the model's breathing or flicker. Returns the
    cumulative log exposure (frames, 3), relative to frame 1."""
    E = np.zeros((len(frames), 3), np.float64)
    used = []
    prev = None
    for t, f in enumerate(frames):
        h = int(round(f.shape[0] * work_w / f.shape[1]))
        cur = cv2.resize(f, (work_w, h), interpolation=cv2.INTER_AREA)
        if prev is not None:
            f01 = flow(prev, cur, 1.0)
            f10 = flow(cur, prev, 1.0)
            back = backwarp(f10, f01)
            ok = np.hypot(*(f01 + back).transpose(2, 0, 1)) < 0.75
            cw = backwarp(cur, f01).astype(np.float32)
            pv = prev.astype(np.float32)
            g = cv2.cvtColor(prev, cv2.COLOR_RGB2GRAY).astype(np.float32)
            edge = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)) > 40
            ok &= ~cv2.dilate(edge.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
            ok &= (pv.min(axis=2) > 18) & (pv.max(axis=2) < 238) & (cw.min(axis=2) > 18) & (cw.max(axis=2) < 238)
            ok[:8], ok[-8:], ok[:, :8], ok[:, -8:] = False, False, False, False
            used.append(float(ok.mean()))
            if ok.sum() > 400:
                r = np.median(np.log(cw[ok]) - np.log(pv[ok]), axis=0)
            else:
                r = np.zeros(3)
            E[t] = E[t - 1] + r
        prev = cur
    return E, dict(matched_share_min=min(used) if used else None, matched_share_median=float(np.median(used)) if used else None)


def grade(frames: list[np.ndarray], s: np.ndarray, first: np.ndarray | None, last: np.ndarray | None) -> dict:
    """In place: (1) the model's own exposure changes are taken out (exposure_track: a surface keeps its brightness
    in a real walk, so the change from the hall to the brighter living room stays, because it is a change of WHAT
    is in frame, not of HOW it is exposed); (2) a gain per channel takes the first frame to the first still and the
    last frame to the last still, interpolated along the walk. Call BEFORE end_lock."""
    L = max(1e-6, float(s[-1] - s[0]))
    E, info = exposure_track(frames)
    corr = np.exp(-E).astype(np.float32)                                         # back to frame 1's exposure
    f_last = np.clip(frames[-1].astype(np.float32) * corr[-1][None, None], 0, 255).astype(np.uint8)
    g0 = robust_gain(frames[0], first) if first is not None else np.ones(3, np.float32)
    g1 = robust_gain(f_last, last) if last is not None else np.ones(3, np.float32)
    for i, f in enumerate(frames):
        p = float((s[i] - s[0]) / L)
        g = corr[i] * np.exp(np.log(g0) * (1 - p) + np.log(g1) * p)
        frames[i] = np.clip(f.astype(np.float32) * g[None, None] + 0.5, 0, 255).astype(np.uint8)
    return dict(gain_first=[round(float(x), 4) for x in g0], gain_last=[round(float(x), 4) for x in g1],
                exposure_drift_max_stops=round(float(np.abs(E).max() / math.log(2)), 4),
                exposure_end_stops=[round(float(x / math.log(2)), 4) for x in E[-1]], **info)


def monotone(s: np.ndarray, smooth: int = 5) -> np.ndarray:
    """A progress table fit for inversion: lightly smoothed, never falling, end values kept."""
    k = smooth // 2
    x = np.convolve(np.pad(s, (k, k), mode="edge"), np.ones(smooth) / smooth, mode="valid") if smooth > 1 else s.copy()
    x[0], x[-1] = s[0], s[-1]
    x = np.maximum.accumulate(x)
    # strictly rising by a hair so that the inverse exists
    return x + np.arange(len(x)) * 1e-7


def resample(frames: list[np.ndarray], s: np.ndarray, n: int, s0: float | None = None, s1: float | None = None) -> tuple[list[np.ndarray], list[float]]:
    """n frames at equal steps of distance from s0 to s1 (default: the clip's own ends)."""
    s = monotone(np.asarray(s, np.float64))
    s0 = float(s[0]) if s0 is None else s0
    s1 = float(s[-1]) if s1 is None else s1
    targets = np.linspace(s0, s1, n)
    pos = np.interp(targets, s, np.arange(len(s)))
    out, cache = [], {}
    for p in pos:
        i = int(min(len(frames) - 2, math.floor(p)))
        tau = float(p - i)
        if tau < 1e-3:
            out.append(frames[i])
            continue
        if tau > 1 - 1e-3:
            out.append(frames[i + 1])
            continue
        if i not in cache:
            cache.clear()
            cache[i] = (flow(frames[i], frames[i + 1]), flow(frames[i + 1], frames[i]))
        out.append(interpolate(frames[i], frames[i + 1], tau, *cache[i]))
    return out, [float(x) for x in pos]


def build_bank(frames: list[np.ndarray], s: np.ndarray, first: np.ndarray | None, last: np.ndarray | None, n: int,
               length: float | None = None, lock_n: int = 10) -> tuple[list[np.ndarray], dict]:
    frames = [f.copy() for f in frames]
    s = np.asarray(s, np.float64)
    rep = dict(source_frames=len(frames))
    rep["grade"] = grade(frames, s, first, last)
    rep["end_lock"] = end_lock(frames, first, last, lock_n)
    L = float(s[-1]) if length is None else length
    # the walk test measures every frame against the clay, so its positions are absolute: keep them. Only the two end
    # frames, which become the stills, are pinned to 0 and L (a model end frame a few pixels off reads as a few cm
    # off; shifting the whole table by that would make every frame lag).
    s = np.clip(np.asarray(s, np.float64).copy(), 0.0, L)
    s[0], s[-1] = 0.0, L
    bank, pos = resample(frames, s, n, 0.0, L)
    if first is not None:
        bank[0] = first.copy()
    if last is not None:
        bank[-1] = last.copy()
    rep.update(bank_frames=n, step_m=L / (n - 1), length_m=L,
               source_step_frames=dict(min=float(np.diff(pos).min()), max=float(np.diff(pos).max())))
    return bank, rep


# ----------------------------------------------------------------------------------------------------------------
# a bank from clay stations (the animatic)
# ----------------------------------------------------------------------------------------------------------------
def clay_view(stations: list[dict], cam: cg.Cam, out: cg.Canvas) -> tuple[np.ndarray, float]:
    """The view from `cam` by depth reprojection from the two stations nearest along the line.
    stations: dicts with cam, cv, img (float RGB), depth (float metres), valid (bool). Returns (image, hole fraction)."""
    dist = [float(np.linalg.norm(np.asarray(st["cam"].loc) - np.asarray(cam.loc))) for st in stations]
    order = np.argsort(dist)[:2]
    acc = np.zeros((out.h, out.w, 3), np.float32)
    wsum = np.zeros((out.h, out.w), np.float32)
    first = None
    for j in order:
        st = stations[j]
        if dist[j] < 1e-6 and st["cam"].yaw == cam.yaw and (st["cam"].u0, st["cam"].v0) == (cam.u0, cam.v0):
            return st["cv"].crop_frame(st["img"], out.w, out.h), 0.0
        img, valid, _ = cg.dibr(st["img"], st["depth"], st["cam"], st["cv"], cam, out, depth_valid=st["valid"])
        w = valid.astype(np.float32) / (dist[j] + 0.03)
        acc += img * w[..., None]
        wsum += w
        if first is None:
            first = img
    hole = wsum <= 0
    res = acc / np.maximum(wsum, 1e-6)[..., None]
    if hole.any():
        res[hole] = first[hole]                               # seen by neither station: the nearer station's stretch
    return np.clip(res, 0, 1), float(hole.mean())


def load_stations(folder: str, ids: list[str], cams: list[cg.Cam], canvas: str = "base") -> list[dict]:
    out = []
    for fid, cam in zip(ids, cams):
        p = os.path.join(folder, fid + ".png")
        img = cv2.cvtColor(cv2.imread(p, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        depth, valid = cg.load_depth_png(os.path.join(folder, fid + "-depth.png"))
        H, W = depth.shape
        cvs = cg.Canvas(W, H, cg.Canvas.base(W).box) if canvas == "base" else (cg.Canvas.frame(W, H) if canvas == "frame" else cg.Canvas.tall(W, H, cg.BASE_BOX[0] / (cg.BASE_BOX[2] - cg.BASE_BOX[0])))
        out.append(dict(id=fid, cam=cam, cv=cvs, img=img, depth=depth, valid=valid))
    return out


def write_frames(frames: list[np.ndarray], out_dir: str, ext: str = "png", quality: int = 95) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for i, f in enumerate(frames):
        cv2.imwrite(os.path.join(out_dir, f"{i + 1:04d}.{ext}"), cv2.cvtColor(f, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, quality])


# ----------------------------------------------------------------------------------------------------------------
def selftest(out_dir: str, w: int = 960, n_src: int = 61, n_bank: int = 49) -> dict:
    import proxy_house as ph
    import walk_test as wt
    os.makedirs(out_dir, exist_ok=True)
    fr = cg.Canvas.frame(w)
    rng = np.random.default_rng(5)
    rep = {}
    for route in ("clip2", "clip1"):
        c0, c1 = wt.ROUTES[route]
        ts = np.linspace(0, 1, n_src)
        prog = np.clip(np.maximum.accumulate(ts + 0.10 * np.sin(2 * np.pi * ts) * (1 - ts)), 0, 1)
        prog[-1] = 1.0
        L = float(np.linalg.norm(np.asarray(c1.loc) - np.asarray(c0.loc)))
        to8 = lambda x: np.clip(np.rint(x * 255), 0, 255).astype(np.uint8)
        raw = []
        for i, p in enumerate(prog):
            rgb, _ = ph.render(cg.lerp_cam(c0, c1, float(p)), fr, "open")
            drift = 1.0 + 0.05 * math.sin(math.pi * ts[i])                       # the model "breathes" in mid-clip
            flick = 1.0 + rng.normal(0, 0.008)
            tint = np.array([1.03, 1.0, 0.97], np.float32)                       # and is a little warm throughout
            raw.append(to8(rgb * drift * flick * tint[None, None]))
        # the model's end frames are a few pixels off the stills
        M = np.array([[1.004, 0, 2.5], [0, 1.004, -1.5]], np.float32)
        raw[0] = cv2.warpAffine(raw[0], M, (fr.w, fr.h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        raw[-1] = cv2.warpAffine(raw[-1], M, (fr.w, fr.h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        first, _ = ph.render(c0, fr, "open")
        last, _ = ph.render(c1, fr, "open")
        first8, last8 = to8(first), to8(last)
        R = wt.proxy_ruler(route, 12, w)
        r = wt.walk_test(raw, R)
        bank, brep = build_bank(raw, np.array(r["s_filled"]), first8, last8, n_bank, L)
        # against the exact frames at equal steps
        ps, worst, serr = [], 99.0, []
        for k in range(n_bank):
            ref, _ = ph.render(cg.lerp_cam(c0, c1, k / (n_bank - 1)), fr, "open")
            d = (bank[k].astype(np.float32) - to8(ref).astype(np.float32)) / 255.0
            ps.append(99.0 if float((d ** 2).mean()) < 1e-12 else 10 * math.log10(1.0 / float((d ** 2).mean())))
        r2 = wt.walk_test(bank, R)
        sb = np.array(r2["s_filled"])
        ideal = np.linspace(0, L, n_bank)
        # speed over 4-frame spans: the walk test's own scatter (a few mm per frame) is not a change of speed
        step = (sb[4:] - sb[:-4]) / 4.0
        mid = slice(1, len(step) - 1)
        lv = [float(b_.astype(np.float32).mean() - to8(ph.render(cg.lerp_cam(c0, c1, k / (n_bank - 1)), fr, "open")[0]).astype(np.float32).mean())
              for k, b_ in list(enumerate(bank))[::6]]
        rep[route] = dict(walk_test_raw=r["verdict"], walk_test_bank=r2["verdict"], bank=brep,
                          first_identical=bool(np.array_equal(bank[0], first8)), last_identical=bool(np.array_equal(bank[-1], last8)),
                          psnr_vs_exact=dict(min=round(min(ps[1:-1]), 2), mean=round(float(np.mean(ps[1:-1])), 2)),
                          raw_speed_max_over_min=round(float(np.diff(prog).max() / max(1e-9, np.diff(prog).min())), 2),
                          bank_position_error_m=dict(mean=round(float(np.abs(sb - ideal).mean()), 4), p90=round(float(np.percentile(np.abs(sb - ideal), 90)), 4),
                                                     max=round(float(np.abs(sb - ideal).max()), 4)),
                          bank_speed_dev_from_constant=dict(p90=round(float(np.percentile(np.abs(step[mid] / np.median(step[mid]) - 1), 90)), 4),
                                                            max=round(float(np.abs(step[mid] / np.median(step[mid]) - 1).max()), 4)),
                          bank_mean_level_vs_exact_every6=[round(x, 2) for x in lv])
        write_frames(bank[::6], os.path.join(out_dir, f"{route}-bank-every6"), "jpg", 90)
    with open(os.path.join(out_dir, "assemble-selftest.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bank")
    b.add_argument("--frames", required=True)
    b.add_argument("--report", required=True, help="walk_test.py report of this clip (its s_filled table)")
    b.add_argument("--first")
    b.add_argument("--last")
    b.add_argument("--canvas-first", default="base", choices=["base", "tall", "frame"])
    b.add_argument("--canvas-last", default="base", choices=["base", "tall", "frame"])
    b.add_argument("--n", type=int, required=True)
    b.add_argument("--w", type=int, default=1920)
    b.add_argument("--ext", default="png", choices=["png", "jpg"])
    b.add_argument("--out", required=True)
    c = sub.add_parser("clay-bank")
    c.add_argument("--stations", required=True)
    c.add_argument("--ids", required=True, help="comma list of frame ids in the folder, in path order (b/S00,...,b/S11)")
    c.add_argument("--line", default="t-e0", help="the line the stations sit on at even distance: t-e0 (H0x -> M0)")
    c.add_argument("--line-count", type=int, default=None, help="how many stations the line has in all (default: the number of ids)")
    c.add_argument("--line-first", type=int, default=0, help="the index on the line of the first id")
    c.add_argument("--shrink", type=float, default=1.0, help="work on the stations at this scale (0.5 for a quick animatic)")
    c.add_argument("--route", default="clip2", help="the part of the line to render: clip2 (HDx -> M0) or t-e0")
    c.add_argument("--n", type=int, required=True)
    c.add_argument("--w", type=int, default=960)
    c.add_argument("--ext", default="jpg", choices=["png", "jpg"])
    c.add_argument("--out", required=True)
    s = sub.add_parser("selftest")
    s.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    import walk_test as wt
    if a.cmd == "bank":
        frames = wt.read_frames(a.frames, a.w)
        h = frames[0].shape[0]
        rep_in = json.load(open(a.report))
        s = np.array(rep_in["s_filled"], np.float64)
        if len(s) != len(frames):
            raise SystemExit(f"the report has {len(s)} frames, the clip {len(frames)}")

        def still(path, canvas):
            if not path:
                return None
            im = cv2.cvtColor(cv2.imread(path, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
            H, W = im.shape[:2]
            cvs = {"frame": cg.Canvas.frame(W, H), "base": cg.Canvas(W, H, cg.Canvas.base(W).box),
                   "tall": cg.Canvas.tall(W, H, cg.BASE_BOX[0] / (cg.BASE_BOX[2] - cg.BASE_BOX[0]))}[canvas]
            return cvs.crop_frame(im, a.w, h)
        bank, rep = build_bank(frames, s, still(a.first, a.canvas_first), still(a.last, a.canvas_last), a.n, rep_in.get("length_m"))
        write_frames(bank, a.out, a.ext, 97)
        with open(os.path.join(a.out, "bank.json"), "w") as fh:
            json.dump(rep, fh, indent=1)
        print(json.dumps(rep, indent=1))
        return 0
    if a.cmd == "clay-bank":
        ids = a.ids.split(",")
        l0, l1 = wt.ROUTES[a.line]
        n_line = a.line_count or len(ids)
        cams = [cg.lerp_cam(l0, l1, (a.line_first + k) / (n_line - 1)) for k in range(len(ids))]
        st = load_stations(a.stations, ids, cams)
        if a.shrink != 1.0:
            for x in st:
                w2, h2 = int(round(x["cv"].w * a.shrink)), int(round(x["cv"].h * a.shrink))
                x["img"] = cv2.resize(x["img"], (w2, h2), interpolation=cv2.INTER_AREA)
                x["depth"] = cv2.resize(x["depth"], (w2, h2), interpolation=cv2.INTER_NEAREST)
                x["valid"] = cv2.resize(x["valid"].astype(np.uint8), (w2, h2), interpolation=cv2.INTER_NEAREST) > 0
                x["cv"] = cg.Canvas(w2, h2, tuple(b * a.shrink for b in x["cv"].box))
        r0, r1 = wt.ROUTES[a.route]
        out = cg.Canvas.frame(a.w)
        holes = []
        os.makedirs(a.out, exist_ok=True)
        for k in range(a.n):
            img, hole = clay_view(st, cg.lerp_cam(r0, r1, k / (a.n - 1)), out)
            holes.append(hole)
            cv2.imwrite(os.path.join(a.out, f"{k + 1:04d}.{a.ext}"), cv2.cvtColor(np.clip(np.rint(img * 255), 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
        rep = dict(frames=a.n, stations=ids, hole_frac_max=max(holes), hole_frac_mean=float(np.mean(holes)))
        with open(os.path.join(a.out, "bank.json"), "w") as fh:
            json.dump(rep, fh, indent=1)
        print(json.dumps(rep, indent=1))
        return 0
    if a.cmd == "selftest":
        print(json.dumps(selftest(a.out), indent=1))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
