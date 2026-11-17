#!/usr/bin/env python3
"""
repair_strip_1a.py: clip 1a (D0o + leaf -> HT, kling-3-omni take 1), the living room seen past the walnut edge, repainted
from the real stills through their clay depth. 0 var2 tokens. Brief: briefs/wm-clip1a-strip-repair-2026-11-17.md.

The model drew a plain wall where the living room shows through O-entry-living (right of the walnut lining, about x 1580-
1740 of 1920), and HT has the north window with the birches; the end lock melted one into the other (bank frames 130-141).
From the frame where the living room enters from behind the door's right reveal (about bank frame 118, 3.16 m), every bank
frame gets, inside the clay's own mask of the living room (the clay depth pass rendered at that frame's camera: points with
Y < 6.27, past the walnut lining's hall half), the living room as the real stills show it:

  sources  HT (its clay depth; the window glass on the plane of its frame, as clip 1b; only HT's 16:9 frame is read, the
           margin from x 2643 is unfinished, HT-L2), then HDx (from the junction, through its clay depth), then base.png
           (M0, through the room depth map). HT's living room was seeded from HDx and base.png (seeds.py ht), so the three
           agree; where two meet, a 6 px feather.
  register the model's own walnut edge (the dark-to-bright step at the strip's left border) against the clay's, per frame,
           smoothed over the frames: the mask and the paint move with the clip's edge, so the border is the clip's line.
  holes    a pixel of the mask that no still shows keeps the clip (a local dissolve over 6 px); counted per frame.
  the end  frame 143 is HT itself (the end lock) and is not touched.

  python3 repair_strip_1a.py --bank DIR --clay DIR --out DIR --report repair.json [--from 118]
  python3 repair_strip_1a.py check --bank DIR --before DIR --repair repair.json --out check.json
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble as asm  # noqa: E402
import camgeo as cg  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
HALL = os.path.join(REPO, "assets/renders/hall/warm-modern/hall-2026-11-17")
CLAY_DOOR = os.path.join(REPO, "assets/blockout/house/framing/wm-door-2026-11-16")
LIV = os.path.join(REPO, "assets/renders/living-room/warm-modern")
W, H = 1920, 1080
L1A, N = 3.80, 143
Y_CUT = 6.20            # HT shows the whole reveal of O-entry-living (Y 6.20-6.35) in walnut: past it, the living room
FEATHER = 1.5
SEAM = 6.0
OVS = cg.BASE_BOX[0] / (cg.BASE_BOX[2] - cg.BASE_BOX[0])


def cam_at(k: int) -> cg.Cam:
    s = L1A * (k - 1) / (N - 1)
    return cg.D0.moved(loc=(cg.D0.loc[0] - s, cg.D0.loc[1], cg.D0.loc[2]))


def rgb(p):
    return cv2.cvtColor(cv2.imread(p, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def sources():
    out = []
    ht = rgb(os.path.join(HALL, "ht.png"))
    cvb = cg.Canvas(ht.shape[1], ht.shape[0], cg.Canvas.base(ht.shape[1]).box)
    d, v = cg.load_depth_png(os.path.join(CLAY_DOOR, "HT-depth.png"))
    asm.glass_plane(d, v, cvb)
    x0, y0, x1, y1 = cvb.box
    v[:, :int(np.ceil(x0))] = False                     # HT-L2: only the 16:9 frame of HT is read
    v[:, int(np.floor(x1)):] = False
    out.append(dict(name="HT", cam=cg.HT, cv=cvb, img=ht, depth=d, valid=v))
    hdx = rgb(os.path.join(HALL, "hdx.png"))
    cvt = cg.Canvas.tall(hdx.shape[1], hdx.shape[0], OVS)
    d, v = cg.load_depth_png(os.path.join(CLAY_DOOR, "HDx-depth.png"))
    asm.glass_plane(d, v, cvt, inside_frame_only=False)            # HDx's margin is finished (the turn reads it)
    out.append(dict(name="HDx", cam=cg.HDX, cv=cvt, img=hdx, depth=d, valid=v))
    base = rgb(os.path.join(LIV, "phase2-2026-11-10/layers/base.png"))
    cvm = cg.Canvas(base.shape[1], base.shape[0], cg.Canvas.base(base.shape[1]).box)
    d, v = cg.load_room_depth(os.path.join(LIV, "depth.png"))
    if d.shape != base.shape[:2]:
        d = cv2.resize(d, (base.shape[1], base.shape[0]), interpolation=cv2.INTER_NEAREST)
        v = cv2.resize(v.astype(np.uint8), (base.shape[1], base.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    d = np.where(v, d, 0).astype(np.float32)
    asm.glass_plane(d, v, cvm, inside_frame_only=False)            # the window reaches the edge of M0's frame
    out.append(dict(name="base.png", cam=cg.M0, cv=cvm, img=base, depth=d, valid=v))
    return out


def clay_mask(clay_dir: str, k: int, cam: cg.Cam) -> np.ndarray:
    d, v = cg.load_depth_png(os.path.join(clay_dir, f"k{k:03d}-depth.png"))
    fr = cg.Canvas.frame(W, H)
    us, vs = fr.uv()
    P = cam.unproject(us, vs, np.where(v, d, 1.0))
    return v & (P[..., 1] < Y_CUT)


def walnut_edge(img8_gray: np.ndarray) -> int:
    """The clip's walnut band (the darkest 30 px band in x 1300-1720, rows 200-800) and its right edge (the largest rise)."""
    g = cv2.GaussianBlur(img8_gray.astype(np.float32), (0, 0), 1.2)
    prof = g[200:800, :].mean(axis=0)
    band = np.convolve(prof, np.ones(30) / 30, mode="same")
    wl = 1300 + int(np.argmin(band[1300:1720]))
    return wl + int(np.argmax(np.diff(prof[wl:wl + 80])))


def reveal_edge(img8_gray: np.ndarray, wr: int) -> int:
    """The clip's right door reveal (a near stone face entering from the right): its left edge, the largest fall of the column
    profile right of the walnut edge + 40 px."""
    g = cv2.GaussianBlur(img8_gray.astype(np.float32), (0, 0), 1.2)
    prof = g[200:800, :].mean(axis=0)
    p2 = cv2.GaussianBlur(prof[wr + 40:1916].reshape(1, -1), (0, 0), 2).ravel()
    return wr + 40 + int(np.argmin(np.diff(p2)))


def left_border(mask: np.ndarray) -> np.ndarray:
    """Per row, the first mask column (nan where the row has none)."""
    has = mask.any(axis=1)
    x = np.argmax(mask, axis=1).astype(np.float64)
    return np.where(has, x, np.nan)


def edge_offset(img: np.ndarray, xb: np.ndarray, rows: range, search: int = 24) -> float | None:
    """The clip's dark-to-bright step (the walnut's right edge) near the clay's border, per row band: the median offset."""
    g = cv2.GaussianBlur(cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), 1.2)
    offs = []
    for r0 in rows:
        xs = xb[r0:r0 + 24]
        if np.isnan(xs).any():
            continue
        c = int(round(float(np.median(xs))))
        if c - search - 2 < 0 or c + search + 2 >= W:
            continue
        prof = g[r0:r0 + 24, c - search:c + search + 1].mean(axis=0)
        gr = np.diff(prof)
        j = int(np.argmax(gr))
        if gr[j] > 6:
            offs.append(j + 0.5 - search)
    return float(np.median(offs)) if len(offs) >= 3 else None


def shift_x(a: np.ndarray, dx: float) -> np.ndarray:
    M = np.float32([[1, 0, dx], [0, 1, 0]])
    return cv2.warpAffine(a, M, (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def stills_view(cam: cg.Cam, src: list):
    """The view from cam out of the real stills in priority order (HT, HDx, base.png), SEAM px blends where a later one meets
    an earlier one. Returns (image, covered)."""
    fr = cg.Canvas.frame(W, H)
    out = np.zeros((H, W, 3), np.float32)
    cov = np.zeros((H, W), bool)
    use = {}
    for st in src:
        im, ok, _ = cg.dibr(st["img"], st["depth"], st["cam"], st["cv"], cam, fr, depth_valid=st["valid"])
        if not ok.any():
            continue
        new = ok & ~cov
        if cov.any():
            inside = cv2.distanceTransform(cov.astype(np.uint8), cv2.DIST_L2, 3)
            wa = np.clip(inside / SEAM, 0, 1)[..., None]
            both = (ok & cov)[..., None]
            out = np.where(both, wa * out + (1 - wa) * im, out)
        out = np.where(new[..., None], im, out)
        use[st["name"]] = new
        cov |= ok
    return out, cov, use


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bank", required=True)
    ap.add_argument("--clay", required=True, help="clay depth passes at the bank cameras, k%%03d-depth.png (1920 x 1080 frame)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--sweep", default="125,132", help="the clip's reveal follows its own edge to the first frame, then leaves the frame by the second")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    names = sorted(f for f in os.listdir(a.bank) if f.endswith(".png") and f[:4].isdigit())
    assert len(names) == N, f"{a.bank}: {len(names)} frames, expected {N}"
    src = sources()
    ks0, ks1 = (int(x) for x in a.sweep.split(","))
    masks, wr, rv = {}, {}, {}
    for k in range(100, N):
        m = clay_mask(a.clay, k, cam_at(k))
        if m.sum() > 50:
            masks[k] = m
    k0 = min(masks)
    for k in masks:
        g = cv2.cvtColor(cv2.imread(os.path.join(a.bank, names[k - 1])), cv2.COLOR_BGR2GRAY)
        wr[k] = walnut_edge(g)
        rv[k] = reveal_edge(g, wr[k])
    ks = sorted(masks)
    border = {k: float(np.nanmedian(left_border(masks[k])[200:800])) for k in ks}
    dx_raw = np.array([wr[k] + 0.5 - border[k] for k in ks])
    dx_fit = np.polyval(np.polyfit(ks, dx_raw, 2), ks)
    dx = {k: float(v) for k, v in zip(ks, dx_fit)}
    # the clip's reveal edge, smoothed, to the start of the sweep; then a constant acceleration out of the frame
    kr = [k for k in ks if ks0 - 1 <= k <= N - 2]
    rfit = np.polyfit(kr, [rv[k] for k in kr], 2)
    for _ in range(2):                                    # drop the frames where the fall found something else
        res = np.array([rv[k] - np.polyval(rfit, k) for k in kr])
        kr = [k for k, r_ in zip(kr, res) if abs(r_) <= 15]
        rfit = np.polyfit(kr, [rv[k] for k in kr], 2)
    xr_model = {k: float(np.polyval(rfit, k)) for k in ks}
    v0 = float(np.polyval(np.polyder(rfit), ks0))
    T = ks1 - ks0
    acc = 2 * (W + 40 - xr_model[ks0] - v0 * T) / (T * T)
    xr = {}
    for k in ks:
        if k <= ks0:
            xr[k] = xr_model[k]
        else:
            t = k - ks0
            xr[k] = max(xr_model[k], xr_model[ks0] + v0 * t + 0.5 * acc * t * t) if k < ks1 else W + 40.0
    rep = dict(tool="repair_strip_1a.py", date="2026-11-17", first_frame=k0, y_cut=Y_CUT, sources_order=[s_["name"] for s_ in src],
               registration=dict(dx_measured={k: round(float(v), 1) for k, v in zip(ks, dx_raw)}, dx_used={k: round(dx[k], 1) for k in ks},
                                 note="dx: the clip's walnut edge minus the clay's (px), a quadratic fit over the frames"),
               reveal=dict(clip_edge_measured={k: rv[k] for k in ks}, clip_edge_fit=[round(float(c), 3) for c in rfit], sweep=[ks0, ks1],
                           accel_px_per_frame2=round(acc, 2), edge_used={k: round(xr[k], 1) for k in ks},
                           note="the clip's right door reveal lingers in the frame to bank 139 (the clay's leaves by ~130); it follows the clip to "
                                f"{ks0}, then leaves at a constant acceleration (its speed at the exit ~{v0 + acc * T:.0f} px a frame, the clay's own)"),
               frames={})
    rev_img = rgb(os.path.join(a.bank, names[ks0 - 1]))
    for k in range(1, N + 1):
        srcp = os.path.join(a.bank, names[k - 1])
        dst = os.path.join(a.out, names[k - 1])
        if k not in masks or k == N:
            shutil.copyfile(srcp, dst)
            continue
        img = rgb(srcp)
        cam = cam_at(k)
        view, cov, use = stills_view(cam, src)
        view = shift_x(view, dx[k])
        cov = shift_x(cov.astype(np.float32), dx[k]) > 0.5
        m = shift_x(masks[k].astype(np.float32), dx[k]) > 0.5
        X = np.arange(W, dtype=np.float32)[None, :]
        # the clip's reveal, moved to its edge of this frame
        shift = xr[k] - xr_model[k]
        base = img.copy()
        if k > ks0:
            # the reveal as the clip drew it at the sweep's first frame (from ~129 the clip melts it), moved to this frame's edge
            moved = shift_x(rev_img, xr[k] - xr_model[ks0])
            base = np.where((X >= xr[k] + 6.0)[..., None], moved, img)
        # what is painted: the living room left of the reveal, and everything the reveal uncovers (from its clip edge to its new edge)
        cut = xr[k] + 6.0                                   # past the clip's dark contour line along the reveal's edge
        uncovered = (X >= xr_model[k]) & (X < cut) if k < ks1 else (X >= min(xr_model[k], W - 1))
        region = (m & (X < cut)) | np.broadcast_to(uncovered, (H, W))
        hole = region & ~cov
        # holes: in the clip's sane part (left of its reveal) the clip's own pixels; where the reveal was, inpainted from the paint
        hole_keep = hole & (X < xr_model[k])
        hole_inp = hole & ~hole_keep
        paintv = np.where(cov[..., None], view, base)
        if hole_inp.any():
            v8 = np.clip(np.rint(paintv * 255), 0, 255).astype(np.uint8)
            v8 = cv2.inpaint(v8, hole_inp.astype(np.uint8) * 255, 5, cv2.INPAINT_TELEA)
            paintv = v8.astype(np.float32) / 255
        lay = (region & ~hole_keep).astype(np.float32)
        alpha = cv2.GaussianBlur(lay, (0, 0), FEATHER)
        if hole_keep.any():                                # the clip's own wall and floor meet the paint over 24 px, not on a line
            alpha *= np.clip(cv2.distanceTransform((~hole_keep).astype(np.uint8), cv2.DIST_L2, 3) / 24.0, 0, 1)
        # the floor line (where the living room's floor meets the hall's, the paint's lower border): a 40 px vertical blend
        col_has = region.any(axis=0)
        bottom = np.where(col_has, H - 1 - np.argmax(region[::-1, :], axis=0), -1)
        rr = np.arange(H, dtype=np.float32)[:, None]
        floorcols = (bottom > 0) & (bottom < H - 5) & (X[0] < xr[k])
        ramp = np.clip((bottom[None, :] + 10 - rr) / 40.0, 0, 1)
        zone = floorcols[None, :] & (rr > bottom[None, :] - 30) & (rr <= bottom[None, :] + 10) & cov
        alpha = np.where(zone, ramp, alpha)
        # the strip enters behind the reveal mostly where no still sees it (the clip's own wall): the paint comes in over 5 frames
        alpha *= float(np.clip((k - ks0 + 2) / 5.0, 0, 1)) ** 2 * (3 - 2 * float(np.clip((k - ks0 + 2) / 5.0, 0, 1))) if k < ks0 + 3 else 1.0
        res = base * (1 - alpha[..., None]) + paintv * alpha[..., None]
        if k <= ks0:
            # the clip's own black contour along the reveal's edge (a melt line, 4-8 px, frames ~121-125, before the sweep): inpainted
            r8 = np.clip(np.rint(res * 255), 0, 255).astype(np.uint8)
            gl = cv2.cvtColor(r8, cv2.COLOR_RGB2GRAY)
            band = np.broadcast_to(np.abs(X - xr_model[k]) <= 7, (H, W))
            line = band & (gl < 120)
            line = cv2.dilate(line.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
            if line.any():
                res = cv2.inpaint(r8, line.astype(np.uint8) * 255, 4, cv2.INPAINT_TELEA).astype(np.float32) / 255
            if k == ks0:
                rev_img = res.copy()                       # the frozen reveal of the sweep: without the contour line
        tot = float(region.sum()) or 1.0
        rep["frames"][k] = dict(region_px=int(region.sum()), holes_kept_clip_frac=round(float(hole_keep.sum()) / tot, 4),
                                holes_inpainted_frac=round(float(hole_inp.sum()) / tot, 4), dx=round(dx[k], 1), reveal_edge=round(xr[k], 1),
                                reveal_shift=round(shift, 1), sources={n: round(float((u & region).sum()) / tot, 4) for n, u in use.items()})
        cv2.imwrite(dst, cv2.cvtColor(np.clip(np.rint(res * 255), 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
    for fn in os.listdir(a.bank):
        if not (fn.endswith(".png") and fn[:4].isdigit()):
            shutil.copyfile(os.path.join(a.bank, fn), os.path.join(a.out, fn))
    fr = rep["frames"]
    rep["summary"] = dict(frames_painted=len(fr), first=k0, last=max(fr), method="projection from the real stills (HT, HDx, base.png) through the clay depth",
                          holes_kept_clip_max=max(v["holes_kept_clip_frac"] for v in fr.values()),
                          holes_inpainted_max=max(v["holes_inpainted_frac"] for v in fr.values()),
                          dx_range=[round(min(v["dx"] for v in fr.values()), 1), round(max(v["dx"] for v in fr.values()), 1)])
    json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps(rep["summary"], indent=1))
    return 0


# ----------------------------------------------------------------------------------------------------------------
def check_main(argv=None) -> int:
    """The border self-check on the repaired bank (checks 5 and 6 of walk_test.py cannot see a border painted from the clay that
    measures it). Each measure is taken on the repaired bank and, at the same place, on the bank before the repair (the clip's
    own level of the same thing), per painted frame:
      outline  along the paint's left border (the walnut edge) and along the moving reveal's edge: a narrow line (<= 3 px)
               darker or brighter than both sides, in 8-bit levels (an uncovered old edge or a halo of the paint)
      tab      the walnut edge as drawn (its dark-to-bright step, per 30-row band, rows 150-950) against its own straight fit: the
               largest residual in px (a tab or a kink)
      jamb     the drawn walnut edge against the paint's border (px): where they part
      floor    the luminance step across the hall / living floor line (the paint's lower border, where it ends above the frame
               bottom), levels
      flash    the strip's mean luminance frame by frame: the largest second difference (a flicker), levels"""
    ap = argparse.ArgumentParser(description="repair_strip_1a.py check")
    ap.add_argument("--bank", required=True, help="the repaired bank")
    ap.add_argument("--before", required=True, help="the bank before the repair")
    ap.add_argument("--repair", required=True)
    ap.add_argument("--clay", required=True)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rep = json.load(open(a.repair))
    fr = {int(k): v for k, v in rep["frames"].items()}
    names = sorted(f for f in os.listdir(a.bank) if f.endswith(".png") and f[:4].isdigit())

    def outline(g, cx, rows):
        dips = []
        for r0 in rows:
            if cx < 14 or cx > W - 15:
                continue
            prof = g[r0:r0 + 30, cx - 12:cx + 13].mean(axis=0)
            for c0 in range(9, 16):
                line = prof[c0 - 1:c0 + 2]
                left, right = prof[c0 - 8:c0 - 3].mean(), prof[c0 + 4:c0 + 9].mean()
                dips.append(float(max(min(left, right) - line.min(), line.max() - max(left, right))))
        return round(max(dips), 1) if dips else None

    def edge_line(g, cx):
        xs, ys = [], []
        for r0 in range(150, 950, 30):
            prof = cv2.GaussianBlur(g[r0:r0 + 30, cx - 25:cx + 26].mean(axis=0).reshape(1, -1), (0, 0), 1.0).ravel()
            gr = np.diff(prof)
            j = int(np.argmax(gr))
            if gr[j] > 6:
                xs.append(cx - 25 + j + 0.5)
                ys.append(r0 + 15)
        if len(xs) < 6:
            return None, None
        c = np.polyfit(ys, xs, 1)
        return round(float(np.max(np.abs(np.array(xs) - np.polyval(c, ys)))), 1), float(np.median(xs))

    out = dict(frames=[])
    la, lb = [], []
    for k in sorted(fr):
        gA = cv2.cvtColor(cv2.imread(os.path.join(a.bank, names[k - 1])), cv2.COLOR_BGR2GRAY).astype(np.float32)
        gB = cv2.cvtColor(cv2.imread(os.path.join(a.before, names[k - 1])), cv2.COLOR_BGR2GRAY).astype(np.float32)
        m = shift_x(clay_mask(a.clay, k, cam_at(k)).astype(np.float32), fr[k]["dx"]) > 0.5
        cx = int(round(float(np.nanmedian(left_border(m)[200:800]))))
        rec = dict(frame=k)
        for tag, g in (("after", gA), ("before", gB)):
            rec[f"outline_{tag}"] = outline(g, cx, range(150, 920, 30))
            tab, xe = edge_line(g, cx)
            rec[f"tab_px_{tag}"] = tab
            if tag == "after":
                rec["jamb_vs_border_px"] = None if xe is None else round(abs(xe - cx), 1)
        xe = fr[k].get("reveal_edge")
        if xe is not None and 30 < xe + 6 < W - 30:
            rec["reveal_outline_after"] = outline(gA, int(round(xe + 6)), range(120, 900, 30))
            xm = fr[k]["reveal_edge"] - fr[k]["reveal_shift"]
            rec["reveal_outline_before"] = outline(gB, int(round(xm)), range(120, 900, 30))
        bottom = np.array([np.max(np.nonzero(m[:, c])[0]) if m[:, c].any() else -1 for c in range(W)])
        cols = np.nonzero((bottom > 20) & (bottom < H - 20))[0]
        if len(cols) > 10:
            for tag, g in (("after", gA), ("before", gB)):
                above = np.mean([g[bottom[c] - 12:bottom[c] - 3, c].mean() for c in cols])
                below = np.mean([g[bottom[c] + 3:bottom[c] + 12, c].mean() for c in cols])
                rec[f"floor_step_{tag}"] = round(float(above - below), 1)
        la.append(float(gA[m].mean()) if m.any() else np.nan)
        lb.append(float(gB[m].mean()) if m.any() else np.nan)
        out["frames"].append(rec)

    def flash(x):
        x = np.array(x)
        x = x[np.isfinite(x)]
        return round(float(np.max(np.abs(np.diff(x, 2)))), 2) if len(x) > 3 else None
    F = out["frames"]
    mx = lambda key: max((f[key] for f in F if f.get(key) is not None), default=None, key=abs)
    out["summary"] = dict(frames=len(F),
                          outline_after_max=mx("outline_after"), outline_before_max=mx("outline_before"),
                          frames_outline_new=[f["frame"] for f in F if (f.get("outline_after") or 0) > (f.get("outline_before") or 0) + 6],
                          reveal_outline_after_max=mx("reveal_outline_after"), reveal_outline_before_max=mx("reveal_outline_before"),
                          tab_px_after_max=mx("tab_px_after"), tab_px_before_max=mx("tab_px_before"),
                          jamb_vs_border_px_max=mx("jamb_vs_border_px"),
                          floor_step_after_max=mx("floor_step_after"), floor_step_before_max=mx("floor_step_before"),
                          strip_flash_after=flash(la), strip_flash_before=flash(lb))
    print(json.dumps(out["summary"], indent=1))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        sys.exit(check_main(sys.argv[2:]))
    sys.exit(main())
