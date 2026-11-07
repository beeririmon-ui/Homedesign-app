#!/usr/bin/env python3
"""
shell_fix.py: master-designer's two code fixes of the pilot shell (docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md section 11),
render-agent, 2026-11-07. 0 var2 tokens. shell.png (step 2, kept as it is) -> shell-v2.png; then the step-3 / step-4 composites are
rebuilt on it with the SAME layers (fixed-furniture.png + its shadow, layers/cushions/set-X.png + their shadows): only what is behind
the layers changes.
  (a) the window-light wedge on the back wall to delta L* <= 2: the back wall's low-frequency L* (normalised blur 40 px inside the wall
      mask of the r4 shell clay, index 5) is modelled as a separable field f(X) + g(Z-row) (robust alternating medians: the falloff along
      the wall and the vertical gradient stay); the diagonal wedge is what the separable model cannot hold. A luminance-only gain (one
      factor for R, G, B: hue kept) brings the low frequencies to the model where they are brighter than it, ramped in over the wall
      mask's edge (skirting, ceiling line, corner kept). The plaster texture (high frequencies) is untouched.
  (b) the bench stone: the porous travertine look out and the tone toward #D8C8AE (limestone, Bible 1.0): the slab's top and its 8 cm
      front edge (projected from the plan: X -2.65..-1.98, Y 1.00..3.60, Z 0.45 / X -1.98, Z 0.37..0.45, inside the r4 index 520), pores =
      pixels darker than the local median (7 px) by > 3.5 L* (grown 1 px), filled from the median plus the stone's own fine grain;
      then the slab's a*, b* moved to #D8C8AE's (1.4, 15.0) by the median shift, L kept (the light on the slab stays).
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
    wall = lab_idx(5)
    k = cv2.erode(wall.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
    L = P.Lstar(a).astype(np.float32)
    nb = lambda x, s: cv2.GaussianBlur(x * k, (0, 0), s) / np.maximum(cv2.GaussianBlur(k, (0, 0), s), 1e-4)
    LF = nb(L, 40)
    sel = k > 0
    ys, xs = np.nonzero(sel)
    f = np.zeros(W, np.float32)
    g = np.zeros(H, np.float32)
    for _ in range(6):
        r = LF - g[:, None]
        for x in range(xs.min(), xs.max() + 1):
            col = sel[:, x]
            if col.sum() > 20:
                f[x] = np.median(r[col, x])
        r = LF - f[None, :]
        for y in range(ys.min(), ys.max() + 1):
            row = sel[y]
            if row.sum() > 20:
                g[y] = np.median(r[y, row])
    f = cv2.GaussianBlur(f.reshape(1, -1), (0, 0), 25).ravel()
    g = cv2.GaussianBlur(g.reshape(-1, 1), (0, 0), 25).ravel()
    model = f[None, :] + g[:, None]
    excess = np.where(sel, LF - model, 0.0)
    before = dict(max_excess_L=round(float(excess[sel].max()), 2), p99_excess_L=round(float(np.percentile(excess[sel], 99)), 2),
                  max_deficit_L=round(float(excess[sel].min()), 2))
    # gain on the low frequencies where the wall is brighter than the model (the wedge); ramp in over 30 px of the wall's edge
    ramp = cv2.GaussianBlur(cv2.erode(wall.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(np.float32), (0, 0), 10)
    exc = np.clip(excess, 0, None) * ramp
    Lt = np.clip(LF - exc, 0, 100)
    Y_of = lambda Ls: np.where(Ls > 8, ((Ls + 16) / 116) ** 3, Ls / 903.3)
    gain = np.where(wall, Y_of(Lt) / np.maximum(Y_of(LF), 1e-5), 1.0).astype(np.float32)
    lin = P.s2l(out) * gain[..., None]
    out = np.clip(P.l2s(lin), 0, 1).astype(np.float32)
    LF2 = nb(P.Lstar(out).astype(np.float32), 40)
    ex2 = np.where(sel, LF2 - model, 0.0)
    rec["wedge"] = dict(before=before, after=dict(max_excess_L=round(float(ex2[sel].max()), 2), p99_excess_L=round(float(np.percentile(ex2[sel], 99)), 2)),
                        px_changed=int((np.abs(gain - 1) > 0.002).sum()), max_gain_stops=round(float(np.log2(gain[wall].min())), 3),
                        rule="delta L* <= 2 against the separable wall field f(X) + g(row)",
                        L_points_before=P.points_L(a, size), L_points_after=P.points_L(out, size))
    # ---------------- (b) the bench stone
    top = poly([(-2.65, 1.00, 0.45), (-1.98, 1.00, 0.45), (-1.98, 3.60, 0.45), (-2.65, 3.60, 0.45)], size)
    front = poly([(-1.98, 1.00, 0.45), (-1.98, 3.60, 0.45), (-1.98, 3.60, 0.37), (-1.98, 1.00, 0.37)], size)
    sm = np.zeros((H, W), np.uint8)
    cv2.fillPoly(sm, [np.round(top).astype(np.int32)], 1)
    cv2.fillPoly(sm, [np.round(front).astype(np.int32)], 1)
    stone = sm.astype(bool) & (lab_idx(520) | cv2.dilate(lab_idx(520).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool))
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
    soft = cv2.GaussianBlur(stone.astype(np.float32), (0, 0), 1.0)
    lab2 = lab.copy()
    lab2[..., 1] += (tgt[1] - m_ab[0]) * soft
    lab2[..., 2] += (tgt[2] - m_ab[1]) * soft
    out = np.clip(cv2.cvtColor(lab2, cv2.COLOR_LAB2RGB), 0, 1).astype(np.float32)
    Ls2 = P.Lstar(out).astype(np.float32)
    loc2 = cv2.medianBlur(np.clip(Ls2 * 2.55, 0, 255).astype(np.uint8), 7).astype(np.float32) / 2.55
    rec["bench"] = dict(stone_px=int(stone.sum()), pores_px=int(pores.sum()), grain_sd=round(sd, 4),
                        pores_left_px=int((stone & ((loc2 - Ls2) > 3.5)).sum()),
                        ab_before=[round(float(v), 2) for v in m_ab], ab_target=[round(float(tgt[1]), 2), round(float(tgt[2]), 2)],
                        ab_after=[round(float(v), 2) for v in np.median(cv2.cvtColor(out, cv2.COLOR_RGB2LAB)[stone][:, 1:], 0)],
                        L_median=round(float(np.median(Ls2[stone])), 1), target=TARGET_HEX,
                        method="pores > 3.5 L* under the 7 px local median, grown 1 px, filled from a 7+5 median plus the stone's grain; a*, b* median shift to the target, L kept")
    P.save(os.path.join(HERE, "shell-v2.png"), out)
    d = np.abs(out - a).max(2) * 255
    rec["px_changed_total"] = int((d > 0.5).sum())
    rec["px_changed_outside_wall_and_stone"] = int((d[~(wall | stone)] > 0.5).sum())
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
