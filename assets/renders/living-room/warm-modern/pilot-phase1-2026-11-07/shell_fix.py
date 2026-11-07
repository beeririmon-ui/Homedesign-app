#!/usr/bin/env python3
"""
shell_fix.py: master-designer's two code fixes of the pilot shell (docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md section 11),
render-agent, 2026-11-07. 0 var2 tokens. shell.png (step 2, kept as it is) -> shell-v2.png; then the step-3 / step-4 composites are
rebuilt on it with the SAME layers (fixed-furniture.png + its shadow, layers/cushions/set-X.png + their shadows): only what is behind
the layers changes.
  (a) the window-light wedge on the back wall to delta L* <= 2: see the comment in main() (target field f(x) + g(v), the low
      frequencies brought to it by a luminance-only gain inside the wall mask of the r4 shell clay, index 5; the plaster texture kept).
  (b) the bench stone: the porous travertine look out and the tone toward #D8C8AE (limestone, Bible 1.0): the slab's top and its 8 cm
      front edge (projected from the plan: X -2.65..-1.98, Y 1.00..3.60, Z 0.45 / X -1.98, Z 0.37..0.45, inside the r4 index 520), pores =
      pixels darker than the local median (7 px) by > 3.5 L* (grown 1 px), filled from the median plus the stone's own fine grain;
      then the slab's a*, b* moved half way to #D8C8AE's (1.4, 15.0) by the median shift, L kept (the light on the slab stays; the full move reads yellow on the lit slab).
  python3 shell_fix.py
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

TARGET_HEX = "#D8C8AE"


def to_px(u, v, size):
    W, H = size
    return ((116 + u * 3840) / 4072 * W, (65 + v * 2160) / 2290 * H)


def poly(pts3, size):
    out = []
    for X, Y, Z in pts3:
        u, v, _ = lock_wm.r1.project(lock_wm.CAM, X, Y, Z)
        out.append(to_px(u, v, size))
    return np.array(out, np.float32)


def main():
    size = P.work_size()
    W, H = size
    a = P.load(os.path.join(HERE, "shell.png"))
    idx = np.load(os.path.join(P.SCRATCH, "wm-r4-shell-idx/M0.npz"))["idx"]
    lab_idx = lambda k: cv2.resize((idx == k).astype(np.uint8), size, interpolation=cv2.INTER_NEAREST).astype(bool)
    rec = dict(date="2026-11-07", by="render-agent", tokens=0, base="shell.png (step 2, kept)", out="shell-v2.png",
               source="docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md section 11 (master-designer)")
    out = a.copy()
    # ---------------- (a) the wedge
    # The back wall's low frequencies (normalised blur 12 px inside the wall mask) show a lit plateau (L* ~94-96) under a soft diagonal
    # edge (the window head's shadow line, ~8-10 L over 150-200 px, running down to the right): the "wedge". Target field
    # T(x, y) = f(x) + g(v): f = the plateau level of each column (80th percentile of the column's lower 60 %, smoothed 30 px: the falloff
    # along the wall and the bright strip by the corner stay), g = a gentle fall toward the ceiling, -4 L at the top of the wall
    # (quadratic in the wall's height fraction v). The low frequencies are brought to T (both ways, clamped +-14 L); a luminance-only
    # shift on L* only: a*, b* and the plaster's fine texture kept.
    wall = lab_idx(5)
    k = cv2.erode(wall.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(np.float32)
    L = P.Lstar(a).astype(np.float32)
    nb = lambda x, sg: cv2.GaussianBlur(x * k, (0, 0), sg) / np.maximum(cv2.GaussianBlur(k, (0, 0), sg), 1e-4)
    LF = nb(L, 12)
    sel = k > 0
    cols = np.nonzero(sel.any(0))[0]
    f = np.zeros(W, np.float32)
    ytop = np.zeros(W, np.float32)
    ybot = np.zeros(W, np.float32)
    for x in cols:
        rr = np.nonzero(sel[:, x])[0]
        ytop[x], ybot[x] = rr.min(), rr.max()
        lower = rr[rr >= ytop[x] + 0.4 * (ybot[x] - ytop[x])]
        f[x] = np.percentile(LF[lower, x], 80) if len(lower) > 10 else 0
    for arr in (ytop, ybot):
        arr[: cols.min()] = arr[cols.min()]
        arr[cols.max() + 1:] = arr[cols.max()]
    f[: cols.min()] = f[cols.min()]
    f[cols.max() + 1:] = f[cols.max()]
    f = cv2.GaussianBlur(f.reshape(1, -1), (0, 0), 30).ravel()
    yy = np.arange(H, dtype=np.float32)[:, None]
    v = np.clip((yy - ytop[None, :]) / np.maximum(ybot - ytop, 1)[None, :], 0, 1)
    T = f[None, :] - 4.0 * (1 - v) ** 2
    dL = np.where(sel, np.clip(T - LF, -14, 14), 0.0).astype(np.float32)
    # the step across the old edge, before: LF on both sides of the diagonal (60 px above / below the steepest point of each column)
    def step_across(LFm):
        out_ = []
        for x in range(int(cols.min()) + 40, int(cols.max()) - 40, 40):
            rr = np.nonzero(sel[:, x])[0]
            if len(rr) < 200:
                continue
            prof = cv2.GaussianBlur(LFm[rr, x].reshape(-1, 1), (0, 0), 6).ravel()
            gy = np.gradient(prof)
            i = int(np.argmax(np.abs(gy[20:-20]))) + 20
            lo, hi = max(0, i - 60), min(len(rr) - 1, i + 60)
            out_.append(abs(float(prof[hi] - prof[lo])))
        return round(float(np.max(out_)), 2), round(float(np.median(out_)), 2)
    st_before = step_across(LF)
    ramp = cv2.GaussianBlur(cv2.erode(wall.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32), (0, 0), 6)
    dLs = cv2.GaussianBlur(dL, (0, 0), 6) * ramp
    # applied on L* only (a*, b* kept): an RGB gain would raise the plaster's chroma with its lightness (peach at the lifted top)
    labw = cv2.cvtColor(out, cv2.COLOR_RGB2LAB)
    labw[..., 0] = np.clip(labw[..., 0] + dLs, 0, 100)
    # where the wall is lifted, its low-frequency a*, b* follow to the lit plaster's (the shaded top carried b* ~10, which reads peach
    # once it is light): the plateau's median a*, b* of the column, weighted by the lift (full from +8 L)
    for c in (1, 2):
        cf = nb(labw[..., c].astype(np.float32), 12)
        plate = np.zeros(W, np.float32)
        for x in cols:
            rr = np.nonzero(sel[:, x])[0]
            lower = rr[rr >= ytop[x] + 0.4 * (ybot[x] - ytop[x])]
            plate[x] = np.median(cf[lower, x]) if len(lower) > 10 else 0
        plate[: cols.min()] = plate[cols.min()]
        plate[cols.max() + 1:] = plate[cols.max()]
        plate = cv2.GaussianBlur(plate.reshape(1, -1), (0, 0), 30).ravel()
        wgt = np.clip(dLs / 8.0, 0, 1)
        labw[..., c] = labw[..., c] + (plate[None, :] - cf) * wgt * ramp
    out = np.where(wall[..., None], np.clip(cv2.cvtColor(labw, cv2.COLOR_LAB2RGB), 0, 1), out).astype(np.float32)
    gain = np.where(wall, 1.0 + dLs / 100.0, 1.0).astype(np.float32)          # for the record only (px changed)
    LF2 = nb(P.Lstar(out).astype(np.float32), 12)
    res2 = np.abs(LF2 - T)[k > 0.5]
    st_after = step_across(LF2)
    rec["wedge"] = dict(before=dict(step_across_edge_max_L=st_before[0], step_across_edge_median_L=st_before[1],
                                    abs_dev_from_target_p99_L=round(float(np.percentile(np.abs(LF - T)[k > 0.5], 99)), 2)),
                        after=dict(step_across_edge_max_L=st_after[0], step_across_edge_median_L=st_after[1],
                                   abs_dev_from_target_p99_L=round(float(np.percentile(res2, 99)), 2)),
                        px_changed=int((np.abs(dLs) > 0.2).sum()), dL_range=[round(float(dLs[wall].min()), 2), round(float(dLs[wall].max()), 2)],
                        rule="delta L* <= 2: the step across the wedge's edge (120 px across the steepest point of each column) and the low frequencies against the target field",
                        L_points_before=P.points_L(a, size), L_points_after=P.points_L(out, size))
    # ---------------- (b) the bench stone
    top = poly([(-2.65, 0.75, 0.45), (-2.30, 0.75, 0.45), (-2.30, 1.00, 0.45), (-1.98, 1.00, 0.45), (-1.98, 2.85, 0.45), (-2.65, 2.85, 0.45)], size)
    front = poly([(-1.98, 1.00, 0.45), (-1.98, 2.85, 0.45), (-1.98, 2.85, 0.37), (-1.98, 1.00, 0.37)], size)
    sm = np.zeros((H, W), np.uint8)
    cv2.fillPoly(sm, [np.round(top).astype(np.int32)], 1)
    cv2.fillPoly(sm, [np.round(front).astype(np.int32)], 1)
    stone = sm.astype(bool) & (lab_idx(520) | lab_idx(12) | lab_idx(14))      # the slab, and its run into the reveal (Y 0.75-1.00)
    stone &= ~lab_idx(4)                                         # never the glazing
    Ls = P.Lstar(out).astype(np.float32)
    loc = cv2.medianBlur(np.clip(Ls * 2.55, 0, 255).astype(np.uint8), 7).astype(np.float32) / 2.55
    pores = stone & ((loc - Ls) > 3.5)
    pores = cv2.dilate(pores.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & stone
    o8 = (out * 255).astype(np.uint8)
    med = cv2.medianBlur(cv2.medianBlur(o8, 7), 5).astype(np.float32) / 255
    hp = out - cv2.GaussianBlur(out, (0, 0), 1.2)
    ok = stone & ~pores
    sd = float(hp[ok].std()) if ok.sum() > 100 else 0.004
    rng = np.random.default_rng(11)
    nz = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.8)
    nz *= sd / max(float(nz.std()), 1e-6)
    fill = np.clip(med + nz[..., None], 0, 1)
    out = np.where(pores[..., None], fill, out).astype(np.float32)
    lab = cv2.cvtColor(out, cv2.COLOR_RGB2LAB)
    tgt = cv2.cvtColor(np.float32([[[int(TARGET_HEX[1:3], 16) / 255, int(TARGET_HEX[3:5], 16) / 255, int(TARGET_HEX[5:7], 16) / 255]]]),
                       cv2.COLOR_RGB2LAB)[0, 0]
    m_ab = np.median(lab[stone][:, 1:], 0)
    soft = cv2.GaussianBlur(stone.astype(np.float32), (0, 0), 1.0) * stone        # never outside the stone
    MOVE = 0.5                                                   # half way: the slab is lit (L* ~90), the full chroma of #D8C8AE (L 81) reads yellow there
    lab2 = lab.copy()
    lab2[..., 1] += (tgt[1] - m_ab[0]) * soft * MOVE
    lab2[..., 2] += (tgt[2] - m_ab[1]) * soft * MOVE
    out = np.where(stone[..., None], np.clip(cv2.cvtColor(lab2, cv2.COLOR_LAB2RGB), 0, 1), out).astype(np.float32)   # the Lab round trip only on the stone
    Ls2 = P.Lstar(out).astype(np.float32)
    loc2 = cv2.medianBlur(np.clip(Ls2 * 2.55, 0, 255).astype(np.uint8), 7).astype(np.float32) / 2.55
    rec["bench"] = dict(stone_px=int(stone.sum()), pores_px=int(pores.sum()), grain_sd=round(sd, 4),
                        pores_left_px=int((stone & ((loc2 - Ls2) > 3.5)).sum()),
                        ab_before=[round(float(v), 2) for v in m_ab], ab_target=[round(float(tgt[1]), 2), round(float(tgt[2]), 2)],
                        ab_after=[round(float(v), 2) for v in np.median(cv2.cvtColor(out, cv2.COLOR_RGB2LAB)[stone][:, 1:], 0)],
                        L_median=round(float(np.median(Ls2[stone])), 1), target=TARGET_HEX,
                        chroma_move=0.5,
                        method="pores > 3.5 L* under the 7 px local median, grown 1 px, filled from a 7+5 median plus the stone's grain; a*, b* median moved half way to the target (lit slab), L kept")
    P.save(os.path.join(HERE, "shell-v2.png"), out)
    d = np.abs(out - a).max(2) * 255
    rec["px_changed_total"] = int((d > 0.5).sum())
    rec["px_changed_outside_wall_and_stone"] = int((d[~(wall | stone)] > 0.5).sum())  # must be 0
    # ---------------- the lock again, then the composites on shell-v2 with the same layers
    lk = lock_wm.run(os.path.join(HERE, "shell-v2.png"), P.CLAY_SHELL, os.path.join(HERE, "shell-v2-lock.json"), os.path.join(HERE, "shell-v2-lock.jpg"), "shell")
    rec["lock_v2_shell"] = dict(summary=lk["summary"], verdict=lk["verdict"],
                                named={k_: dict(median=v["raw"].get("median_px"), p90=v["raw"].get("p90_abs_px"), n=v["raw"].get("counted"))
                                       for k_, v in lk["named_lines"].items()})
    F = np.asarray(Image.open(os.path.join(HERE, "fixed-furniture.png"))).astype(np.float32) / 255
    S = np.asarray(Image.open(os.path.join(HERE, "fixed-furniture-shadow.png")).convert("L")).astype(np.float32) / 255
    fa = F[..., 3:4]
    base2 = out * S[..., None] * (1 - fa) + F[..., :3] * fa
    P.save(os.path.join(HERE, "shell-furniture-v2.png"), base2)
    comps = {}
    for s in "ABC":
        lp = os.path.join(HERE, f"layers/cushions/set-{s}.png")
        if not os.path.exists(lp):
            continue
        Lr = np.asarray(Image.open(lp)).astype(np.float32) / 255
        Sh = np.asarray(Image.open(os.path.join(HERE, f"shadows/cushions/set-{s}.png")).convert("L")).astype(np.float32) / 255
        ca = Lr[..., 3:4]
        c = base2 * Sh[..., None] * (1 - ca) + Lr[..., :3] * ca
        P.save(os.path.join(HERE, f"composite-set-{s}-v2.png"), c)
        comps[s] = f"composite-set-{s}-v2.png"
    rec["composites_v2"] = dict(base="shell-furniture-v2.png", sets=comps, note="the same layers and shadows; only the shell behind them is v2")
    json.dump(rec, open(os.path.join(HERE, "shell-fix.json"), "w"), indent=1, ensure_ascii=False)
    # before / after crops
    cr = os.path.join(HERE, "shell-fix-before-after")
    os.makedirs(cr, exist_ok=True)
    A8, B8 = Image.open(os.path.join(HERE, "shell.png")).convert("RGB"), Image.open(os.path.join(HERE, "shell-v2.png")).convert("RGB")
    bx, by_, bx1, by1 = [int(v) for v in (top[:, 0].min(), min(top[:, 1].min(), front[:, 1].min()), top[:, 0].max(), front[:, 1].max())]
    for name, box in (("back-wall-wedge", (1084, 0, 2720, 1260)), ("bench-100", (max(0, bx), max(0, by_ - 20), min(W, bx1), min(H, by1 + 20)))):
        pa, pb = A8.crop(box), B8.crop(box)
        if name == "back-wall-wedge":
            pa, pb = pa.resize((pa.width // 2, pa.height // 2)), pb.resize((pb.width // 2, pb.height // 2))
        im = Image.new("RGB", (pa.width, pa.height * 2 + 10), (255, 255, 255))
        im.paste(pa, (0, 0))
        im.paste(pb, (0, pa.height + 10))
        im.save(os.path.join(cr, name + ".jpg"), quality=92)
    print(json.dumps({k_: v for k_, v in rec.items() if k_ in ("wedge", "bench", "px_changed_total", "px_changed_outside_wall_and_stone")}, indent=1))
    print(json.dumps(rec["lock_v2_shell"]["summary"]), json.dumps(rec["lock_v2_shell"]["verdict"]))


if __name__ == "__main__":
    main()
