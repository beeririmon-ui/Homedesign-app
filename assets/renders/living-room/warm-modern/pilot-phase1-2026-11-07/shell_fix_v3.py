#!/usr/bin/env python3
"""
shell_fix_v3.py: master-designer's pilot review (docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md section 13), render-agent, 2026-11-07.
0 var2 tokens. shell-v3.png = shell-v2.png (the bench of v2, accepted) with the back wall rebuilt from shell.png (the step-2 raw):
  (2) the back wall back down, with its plaster movement: v2 brought the wall's low frequencies (blur 12 px) to one flat field, so the
      lime-plaster cloud went and the centre read as white paper (L* 93.3). v3 works on the very low frequencies only (normalised blur
      50 px inside the wall mask): the field T(x, v) = the v2 plateau shape (per-column plateau level, -4 L* toward the ceiling) plus a
      smooth correction along x through the designer's targets, measured at the Bible points: the corner (-1.75, 0, 1.60) ~83, the
      centre behind the art (0.20, 0, 1.95) 89.5, the right end (1.85, 0, 1.60) 85. Everything finer than 50 px (the plaster movement)
      stays the raw's own; its mid-frequency range is checked against the Bible's 3 L* and compressed only if it exceeds it.
      On L* only; where the wall is lifted its a*, b* follow the lit plaster's (no peach).
  (3) the wedge's residual over the triptych and sconce area (frame u 0.45-0.85, v 0.15-0.45): the max L* change over 120 px must be
      <= 2.5; if not, that area alone is flattened further (its low frequencies from 25 px).
  the bench slab's mask is written to masks/stone.png for the display grade (b* cap 12, pilot_wm.py grade).
Then the composites on shell-v3 with the SAME layers, the shell lock, the swap-diff, the grade and the sheet are re-run by pilot_wm.py.
  python3 shell_fix_v3.py
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lock_wm  # noqa: E402
import pilot_wm as P  # noqa: E402
from shell_fix import poly  # noqa: E402

TARGETS = {"back_wall_by_corner(-1.75,0,1.60)": ((-1.75, 0.0, 1.60), 83.0), "back_wall_centre(0.20,0,1.95)": ((0.20, 0.0, 1.95), 89.5),
           "back_wall_right(1.85,0,1.60)": ((1.85, 0.0, 1.60), 85.0)}
ART_AREA = (0.45, 0.85, 0.15, 0.45)          # frame uv: u0, u1, v0, v1
MOVE_MAX = 3.0


def px_of(P3, size):
    W, H = size
    u, v, _ = lock_wm.r1.project(lock_wm.CAM, *P3)
    return int((116 + u * 3840) / 4072 * W), int((65 + v * 2160) / 2290 * H)


def main():
    size = P.work_size()
    W, H = size
    raw = P.load(os.path.join(HERE, "shell.png"))
    v2 = P.load(os.path.join(HERE, "shell-v2.png"))
    idx = np.load(os.path.join(P.SCRATCH, "wm-r4-shell-idx/M0.npz"))["idx"]
    lab_idx = lambda k_: cv2.resize((idx == k_).astype(np.uint8), size, interpolation=cv2.INTER_NEAREST).astype(bool)
    wall = lab_idx(5)
    k = cv2.erode(wall.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(np.float32)
    sel = k > 0
    nb = lambda x, sg: cv2.GaussianBlur(x * k, (0, 0), sg) / np.maximum(cv2.GaussianBlur(k, (0, 0), sg), 1e-4)
    lab = cv2.cvtColor(raw, cv2.COLOR_RGB2LAB)
    L = lab[..., 0].astype(np.float32)
    LF = nb(L, 50)
    # the plateau shape (as v2)
    cols = np.nonzero(sel.any(0))[0]
    f = np.zeros(W, np.float32)
    ytop, ybot = np.zeros(W, np.float32), np.zeros(W, np.float32)
    for x in cols:
        rr = np.nonzero(sel[:, x])[0]
        ytop[x], ybot[x] = rr.min(), rr.max()
        lower = rr[rr >= ytop[x] + 0.4 * (ybot[x] - ytop[x])]
        f[x] = np.percentile(LF[lower, x], 80) if len(lower) > 10 else 0
    for arr in (f, ytop, ybot):
        arr[: cols.min()] = arr[cols.min()]
        arr[cols.max() + 1:] = arr[cols.max()]
    f = cv2.GaussianBlur(f.reshape(1, -1), (0, 0), 30).ravel()
    yy = np.arange(H, dtype=np.float32)[:, None]
    v = np.clip((yy - ytop[None, :]) / np.maximum(ybot - ytop, 1)[None, :], 0, 1)
    B = f[None, :] - 4.0 * (1 - v) ** 2
    # (3) the art / sconce area
    fu0, fu1, fv0, fv1 = ART_AREA
    ax0, ax1 = int((116 + fu0 * 3840) / 4072 * W), int((116 + fu1 * 3840) / 4072 * W)
    ay0, ay1 = int((65 + fv0 * 2160) / 2290 * H), int((65 + fv1 * 2160) / 2290 * H)

    def step120(Lmap):
        Ls = nb(Lmap.astype(np.float32), 12)
        worst, where = 0.0, None
        for x in range(ax0, ax1, 8):
            rr = np.nonzero(sel[ay0:ay1, x])[0] + ay0
            if len(rr) < 130:
                continue
            p_ = Ls[rr, x]
            d_ = np.abs(p_[120:] - p_[:-120])
            if d_.max() > worst:
                worst, where = float(d_.max()), ["column", int(x), int(rr[int(np.argmax(d_))])]
        for y in range(ay0, ay1, 8):
            cc = np.nonzero(sel[y, ax0:ax1])[0] + ax0
            if len(cc) < 130:
                continue
            p_ = Ls[y, cc]
            d_ = np.abs(p_[120:] - p_[:-120])
            if d_.max() > worst:
                worst, where = float(d_.max()), ["row", int(y), int(cc[int(np.argmax(d_))])]
        return round(worst, 2), where
    # the plaster movement: the raw's L* finer than 50 px (mid frequencies LF8 - LF50, and the grain); its range against the Bible's 3 L*
    LF8 = nb(L, 8)
    mid = LF8 - LF
    rng = (float(np.percentile(mid[sel], 2)), float(np.percentile(mid[sel], 98)))
    squeeze = min(1.0, MOVE_MAX / max(abs(rng[0]), abs(rng[1]), 1e-3))
    # the target field: the plateau shape B + a smooth correction c(x) through the designer's three points, solved by measuring the
    # points' patches (the raw movement included) and correcting c three times; inside the art area the x-profile's slope is limited
    # to 2.2 L* per 120 px (the bright strip by the corner eased there), outside it eased back over 150 px
    pts = sorted((px_of(P3, size), t, name) for name, (P3, t) in TARGETS.items())
    xs_ = np.array([p_[0] for p_, _, _ in pts], np.float32)
    cs_ = np.array([t - B[p_[1], p_[0]] for p_, t, _ in pts], np.float32)
    rad = max(4, int(0.006 * W))
    slope = 2.2 / 120.0
    yref = int((ay0 + ay1) / 2)
    for it in range(4):
        c = np.interp(np.arange(W), xs_, cs_).astype(np.float32)
        c = cv2.GaussianBlur(c.reshape(1, -1), (0, 0), 40).ravel()
        T = B + c[None, :]
        Tx = T[yref].copy()
        Tc = Tx.copy()
        xc = (ax0 + ax1) // 2
        for x in range(xc - 1, ax0 - 1, -1):
            Tc[x] = np.clip(Tc[x], Tc[x + 1] - slope, Tc[x + 1] + slope)
        for x in range(xc + 1, ax1 + 1):
            Tc[x] = np.clip(Tc[x], Tc[x - 1] - slope, Tc[x - 1] + slope)
        dlt = np.zeros(W, np.float32)
        dlt[ax0:ax1 + 1] = (Tc - Tx)[ax0:ax1 + 1]
        dlt[: ax0] = dlt[ax0] * np.clip(1 - (ax0 - np.arange(ax0)) / 150.0, 0, 1)
        dlt[ax1 + 1:] = dlt[ax1] * np.clip(1 - (np.arange(ax1 + 1, W) - ax1) / 150.0, 0, 1)
        T = T + dlt[None, :]
        newL = T + mid * squeeze + (L - LF8)
        meas = np.array([float(np.median(newL[p_[1] - rad:p_[1] + rad, p_[0] - rad:p_[0] + rad])) for p_, _, _ in pts], np.float32)
        tg = np.array([t for _, t, _ in pts], np.float32)
        if np.abs(meas - tg).max() < 0.3:
            break
        cs_ = cs_ + (tg - meas)
    s_raw = step120(np.where(wall, L, 0))
    s_v3 = step120(np.where(wall, newL, 0))
    extra = False
    area = np.zeros((H, W), bool)
    area[ay0:ay1, ax0:ax1] = True
    area &= wall
    if s_v3[0] > 2.5:                                 # still over: flatten the area only, from 25 px, ramped in over 60 px
        extra = True
        LF25 = nb(newL.astype(np.float32), 25)
        Tn = nb(T.astype(np.float32), 25)
        ramp = cv2.GaussianBlur(area.astype(np.float32), (0, 0), 30)
        newL = newL - (LF25 - Tn) * ramp
        s_v3 = step120(np.where(wall, newL, 0))
    # apply on L* in the wall (ramp at the wall's edge), a*, b* follow the lit plaster where lifted
    ramp_w = cv2.GaussianBlur(cv2.erode(wall.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32), (0, 0), 6)
    out_lab = lab.copy()
    out_lab[..., 0] = np.clip(L + (newL - L) * ramp_w, 0, 100)
    lift = (newL - L) * ramp_w
    for ch in (1, 2):
        cf = nb(lab[..., ch].astype(np.float32), 12)
        plate = np.zeros(W, np.float32)
        for x in cols:
            rr = np.nonzero(sel[:, x])[0]
            lower = rr[rr >= ytop[x] + 0.4 * (ybot[x] - ytop[x])]
            plate[x] = np.median(cf[lower, x]) if len(lower) > 10 else 0
        plate[: cols.min()] = plate[cols.min()]
        plate[cols.max() + 1:] = plate[cols.max()]
        plate = cv2.GaussianBlur(plate.reshape(1, -1), (0, 0), 30).ravel()
        out_lab[..., ch] = lab[..., ch] + (plate[None, :] - cf) * np.clip(lift / 8.0, 0, 1) * ramp_w
    wall_rgb = np.clip(cv2.cvtColor(out_lab, cv2.COLOR_LAB2RGB), 0, 1)
    out = np.where(wall[..., None], wall_rgb, v2).astype(np.float32)
    P.save(os.path.join(HERE, "shell-v3.png"), out)
    # the stone mask for the display grade (the same geometry as shell_fix.py)
    top = poly([(-2.65, 0.75, 0.45), (-2.30, 0.75, 0.45), (-2.30, 1.00, 0.45), (-1.98, 1.00, 0.45), (-1.98, 2.85, 0.45), (-2.65, 2.85, 0.45)], size)
    front = poly([(-1.98, 1.00, 0.45), (-1.98, 2.85, 0.45), (-1.98, 2.85, 0.37), (-1.98, 1.00, 0.37)], size)
    sm = np.zeros((H, W), np.uint8)
    cv2.fillPoly(sm, [np.round(top).astype(np.int32)], 1)
    cv2.fillPoly(sm, [np.round(front).astype(np.int32)], 1)
    stone = sm.astype(bool) & (lab_idx(520) | lab_idx(12) | lab_idx(14))
    os.makedirs(os.path.join(HERE, "masks"), exist_ok=True)
    Image.fromarray((stone * 255).astype(np.uint8)).save(os.path.join(HERE, "masks/stone.png"))
    # records
    Lo = P.Lstar(out).astype(np.float32)
    mid_after = nb(Lo, 8) - nb(Lo, 50)
    d = np.abs(out - v2).max(2) * 255
    rec = dict(date="2026-11-07", by="render-agent", tokens=0, base="shell-v2.png (bench) + shell.png (the back wall)", out="shell-v3.png",
               source="docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md section 13 (master-designer)",
               back_wall=dict(targets={k_: t for k_, (_, t) in TARGETS.items()},
                              L_points=dict(raw=P.points_L(raw, size), v2=P.points_L(v2, size), v3=P.points_L(out, size)),
                              movement_mid_freq_p2_p98=dict(raw=[round(rng[0], 2), round(rng[1], 2)], squeeze=round(squeeze, 3),
                                                            v3=[round(float(np.percentile(mid_after[sel], 2)), 2), round(float(np.percentile(mid_after[sel], 98)), 2)],
                                                            rule="Bible: soft movement up to 3 L*"),
                              v2_movement_mid_freq_p2_p98=[round(float(np.percentile((nb(P.Lstar(v2).astype(np.float32), 8) - nb(P.Lstar(v2).astype(np.float32), 50))[sel], q)), 2) for q in (2, 98)],
                              method="low frequencies (50 px) to T = plateau shape + a smooth x-correction through the targets; finer movement and grain from the raw; L* only, a*/b* follow where lifted"),
               art_sconce_area=dict(frame_uv=list(ART_AREA), max_dL_over_120px=dict(raw=s_raw[0], v3=s_v3[0], where_v3=s_v3[1], limit=2.5,
                                                                         passes=bool(s_v3[0] <= 2.5)),
                                    slope_limit_in_area="2.2 L* per 120 px on the target's x-profile", extra_flatten_applied=extra),
               stone_mask="masks/stone.png (for the display grade's b* cap 12)",
               px_changed_vs_v2=int((d > 0.5).sum()), px_changed_vs_v2_outside_wall=int((d[~wall] > 0.5).sum()))
    lk = lock_wm.run(os.path.join(HERE, "shell-v3.png"), P.CLAY_SHELL, os.path.join(HERE, "shell-v3-lock.json"), os.path.join(HERE, "shell-v3-lock.jpg"), "shell")
    rec["lock"] = dict(summary=lk["summary"], verdict=lk["verdict"],
                       named={k_: dict(median=v_["raw"].get("median_px"), p90=v_["raw"].get("p90_abs_px"), n=v_["raw"].get("counted"))
                              for k_, v_ in lk["named_lines"].items()})
    # composites on shell-v3 with the same layers
    F = np.asarray(Image.open(os.path.join(HERE, "fixed-furniture.png"))).astype(np.float32) / 255
    S = np.asarray(Image.open(os.path.join(HERE, "fixed-furniture-shadow.png")).convert("L")).astype(np.float32) / 255
    fa = F[..., 3:4]
    base3 = out * S[..., None] * (1 - fa) + F[..., :3] * fa
    P.save(os.path.join(HERE, "shell-furniture-v3.png"), base3)
    comps = {}
    for s_ in "ABC":
        Lr = np.asarray(Image.open(os.path.join(HERE, f"layers/cushions/set-{s_}.png"))).astype(np.float32) / 255
        Sh = np.asarray(Image.open(os.path.join(HERE, f"shadows/cushions/set-{s_}.png")).convert("L")).astype(np.float32) / 255
        ca = Lr[..., 3:4]
        P.save(os.path.join(HERE, f"composite-set-{s_}-v3.png"), base3 * Sh[..., None] * (1 - ca) + Lr[..., :3] * ca)
        comps[s_] = f"composite-set-{s_}-v3.png"
    rec["composites_v3"] = dict(base="shell-furniture-v3.png", sets=comps, note="the same layers and shadows; only the shell behind them is v3")
    json.dump(rec, open(os.path.join(HERE, "shell-fix-v3.json"), "w"), indent=1, ensure_ascii=False)
    # crops: the back wall raw | v2 | v3 (half size)
    cr = os.path.join(HERE, "shell-fix-before-after")
    os.makedirs(cr, exist_ok=True)
    tiles = [Image.open(os.path.join(HERE, n)).convert("RGB").crop((1084, 0, 2720, 1260)).resize((818, 630)) for n in ("shell.png", "shell-v2.png", "shell-v3.png")]
    im = Image.new("RGB", (818, 630 * 3 + 20), (255, 255, 255))
    for i, t in enumerate(tiles):
        im.paste(t, (0, i * 640))
    im.save(os.path.join(cr, "back-wall-raw-v2-v3.jpg"), quality=92)
    print(json.dumps({k_: v_ for k_, v_ in rec.items() if k_ in ("back_wall", "art_sconce_area", "px_changed_vs_v2_outside_wall")}, indent=1))
    print(json.dumps(rec["lock"]["summary"]), json.dumps(rec["lock"]["verdict"]))


if __name__ == "__main__":
    main()
