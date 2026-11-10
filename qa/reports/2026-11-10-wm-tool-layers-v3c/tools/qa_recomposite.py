#!/usr/bin/env python3
"""
qa_recomposite.py: qa-agent's independent check of the warm-modern tool layers in the v3c grade (2026-11-10).

Written from scratch by qa-agent. It does not import or copy render-agent's build/verify code; it reads only the
image files and manifest.json (for the file names, the order and the blends), and computes everything itself.

Paths (all on 8-bit sRGB values, as the browser does):
  P1 straight-exact     out = round( (B*S*(255-a) + 255*L*a) / 255^2 )             one rounding, integer arithmetic
  P2 straight-8bit      m = round(B*S/255) -> uint8 ; out = round((m*(255-a) + L*a)/255)  8-bit intermediate
  P3 pillow             ImageChops.multiply(B, S) then Image.alpha_composite(., L)   third-party library reference
  P4 browser-premul     Lp = round(L*a/255) (premultiply on decode/upload) ; m = round(B*S/255) into RGBA8 ;
                        out = round(Lp + m*(255-a)/255)                              the engine's GL path (gl.ts: premultiplied
                                                                                     ImageBitmaps, multiply = DST_COLOR / 1-SRC_A,
                                                                                     normal = ONE / 1-SRC_A, RGBA8 target)
  P5 premul-truncate    as P4 but every division truncates (a cheap CPU raster)      worst-case rounding envelope

Region of set X (computed here): layer alpha > 0  OR  any shadow channel < 255.
Outputs JSON to the path given as the first argument.
"""
import hashlib
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageChops

REPO = "/home/user/homedesign-app"
PILOT = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
LAYERS = os.path.join(PILOT, "layers-v3c")
SETS = ["A", "B", "C"]


def load(p):
    im = Image.open(p)
    im.load()
    return im


def u8(im):
    return np.asarray(im).copy()


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# ---------- colour: sRGB -> Lab (D65) and CIEDE2000 ----------
def srgb_to_lab(rgb):
    c = rgb.astype(np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ M.T
    xyz /= np.array([0.95047, 1.0, 1.08883])
    e = 216 / 24389
    k = 24389 / 27
    f = np.where(xyz > e, np.cbrt(xyz), (k * xyz + 16) / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], -1)


def de2000(lab1, lab2):
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]
    C1 = np.hypot(a1, b1)
    C2 = np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1
    dCp = C2p - C1p
    dh = h2p - h1p
    dh = np.where(C1p * C2p == 0, 0, np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)))
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lbp = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    hs = h1p + h2p
    hbp = np.where(C1p * C2p == 0, hs, np.where(np.abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    T = 1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63))
    dth = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


# ---------- compositing paths ----------
def rdiv(num, den):
    """round(num/den), half up, integers >= 0"""
    return (2 * num + den) // (2 * den)


def p1(B, S, L, A):
    a = A[..., None].astype(np.int64)
    num = B.astype(np.int64) * S.astype(np.int64) * (255 - a) + 255 * L.astype(np.int64) * a
    return rdiv(num, 65025).astype(np.uint8)


def p2(B, S, L, A):
    a = A[..., None].astype(np.int64)
    m = rdiv(B.astype(np.int64) * S.astype(np.int64), 255)
    return rdiv(m * (255 - a) + L.astype(np.int64) * a, 255).astype(np.uint8)


def p3(Bim, Sim, Lim):
    m = ImageChops.multiply(Bim.convert("RGB"), Sim.convert("RGB")).convert("RGBA")
    return np.asarray(Image.alpha_composite(m, Lim.convert("RGBA")).convert("RGB")).copy()


def p4(B, S, L, A):
    a = A[..., None].astype(np.int64)
    Lp = rdiv(L.astype(np.int64) * a, 255)
    m = rdiv(B.astype(np.int64) * S.astype(np.int64), 255)
    return rdiv(255 * Lp + m * (255 - a), 255).astype(np.uint8)


def p5(B, S, L, A):
    a = A[..., None].astype(np.int64)
    Lp = (L.astype(np.int64) * a) // 255
    m = (B.astype(np.int64) * S.astype(np.int64)) // 255
    return (Lp + (m * (255 - a)) // 255).astype(np.uint8)


def stats(out, T, region):
    d3 = np.abs(out.astype(np.int16) - T.astype(np.int16))
    d = d3.max(2)
    yx = np.unravel_index(int(np.argmax(d)), d.shape)
    r = dict(
        max=int(d.max()), max_at_xy=[int(yx[1]), int(yx[0])],
        p99_9_region=float(np.percentile(d[region], 99.9)), p99_region=float(np.percentile(d[region], 99)),
        p99_9_canvas=float(np.percentile(d, 99.9)), max_outside_region=int(d[~region].max()) if (~region).any() else 0,
        mean_region=round(float(d[region].mean()), 4),
        px_gt0=int((d > 0).sum()), px_gt1=int((d > 1).sum()), px_gt2=int((d > 2).sum()), px_ge3=int((d >= 3).sum()),
        px_ge4=int((d >= 4).sum()), px_gt6=int((d > 6).sum()), px_gt0_outside_region=int(((d > 0) & ~region).sum()),
        region_px=int(region.sum()), canvas_px=int(d.size))
    return r, d


def main(out_json):
    man = json.load(open(os.path.join(LAYERS, "manifest.json")))
    res = dict(tool="qa/reports/2026-11-10-wm-tool-layers-v3c/tools/qa_recomposite.py", author="qa-agent", date="2026-11-10",
               manifest_order=man["compose"]["order"], manifest_blends={l["id"]: l["blend"] for l in man["layers"]})
    Bim = load(os.path.join(LAYERS, "base.png"))
    B = u8(Bim)
    approved_base = u8(load(os.path.join(PILOT, "shell-furniture-v3-graded-v3c.png")))
    res["base"] = dict(mode=Bim.mode, size=list(Bim.size), same_pixels_as_approved=bool(np.array_equal(B, approved_base)),
                       sha256=sha(os.path.join(LAYERS, "base.png")),
                       approved_sha256=sha(os.path.join(PILOT, "shell-furniture-v3-graded-v3c.png")))
    R4, R1, REG, T, D = {}, {}, {}, {}, {}
    res["sets"] = {}
    for s in SETS:
        st = man["sets"][s]
        Lim = load(os.path.join(LAYERS, st["layer"]))
        Sim = load(os.path.join(LAYERS, st["shadow"]))
        LA = u8(Lim)
        L, A = LA[..., :3], LA[..., 3]
        S = u8(Sim)
        Tc = u8(load(os.path.join(PILOT, f"composite-set-{s}-v3-graded-v3c.png")))
        a0 = u8(load(os.path.join(PILOT, f"layers/cushions/set-{s}.png")))[..., 3]
        sh0 = u8(load(os.path.join(PILOT, f"shadows/cushions/set-{s}.png")).convert("RGB")).min(2)
        region = (A > 0) | (S < 255).any(2)
        cut = (a0 > 0) | (sh0 < 255)
        outs = dict(P1_straight_exact=p1(B, S, L, A), P2_straight_8bit=p2(B, S, L, A), P3_pillow=p3(Bim, Sim, Lim),
                    P4_browser_premultiplied=p4(B, S, L, A), P5_premultiplied_truncate=p5(B, S, L, A))
        r = dict(layer_mode=Lim.mode, shadow_mode=Sim.mode, layer_size=list(Lim.size), shadow_size=list(Sim.size),
                 region_px=int(region.sum()), alpha_gt0_px=int((A > 0).sum()), alpha_255_px=int((A == 255).sum()),
                 alpha_soft_px=int(((A > 0) & (A < 255)).sum()), shadow_lt255_px=int((S < 255).any(2).sum()),
                 shadow_lt255_under_alpha255_px=int(((S < 255).any(2) & (A == 255)).sum()),
                 region_outside_approved_cut_px=int((region & ~cut).sum()),
                 approved_cut_px=int(cut.sum()), approved_cut_outside_region_px=int((cut & ~region).sum()),
                 approved_composite_vs_base_outside_region_px=int(((Tc != B).any(2) & ~region).sum()),
                 paths={})
        # alpha raised vs the approved cut
        diffA = A.astype(int) - a0.astype(int)
        r["alpha_vs_approved_cut"] = dict(raised_px=int((diffA > 0).sum()), lowered_px=int((diffA < 0).sum()),
                                          raised_from_zero_px=int(((diffA > 0) & (a0 == 0)).sum()),
                                          raise_median=float(np.median(diffA[diffA > 0])) if (diffA > 0).any() else 0.0,
                                          raise_max=int(diffA.max()))
        for k, o in outs.items():
            sres, d = stats(o, Tc, region)
            r["paths"][k] = sres
            if k == "P4_browser_premultiplied":
                D[s] = d
        # where are the residual pixels (P4)?
        d = D[s]
        zones = dict(alpha255=(A == 255), soft=(A > 0) & (A < 255), shadow_band=(A == 0) & (S < 255).any(2), outside=~region)
        r["residual_by_zone_P4"] = {z: dict(px_gt0=int(((d > 0) & m).sum()), px_ge2=int(((d >= 2) & m).sum()), px_ge3=int(((d >= 3) & m).sum()),
                                            max=int(d[m].max()) if m.any() else 0) for z, m in zones.items()}
        # brighten-only residual: approved above base x shadow in a channel, shadow 255 there
        m8 = rdiv(B.astype(np.int64) * S.astype(np.int64), 255)
        need_brighten = ((Tc.astype(np.int64) > m8) & (S == 255)).any(2) & zones["shadow_band"]
        r["shadow_band_needs_brighten_px"] = int(need_brighten.sum())
        r["shadow_band_needs_brighten_and_residual_px"] = int((need_brighten & (d > 0)).sum())
        # visibility: dE00 of the residual pixels (P4 vs approved)
        o4 = outs["P4_browser_premultiplied"]
        idx = d > 0
        lab_o, lab_t = srgb_to_lab(o4[idx]), srgb_to_lab(Tc[idx])
        de = de2000(lab_t, lab_o)
        r["residual_dE00_P4"] = dict(n=int(idx.sum()), max=round(float(de.max()), 3), p99=round(float(np.percentile(de, 99)), 3),
                                     mean=round(float(de.mean()), 3), n_gt1=int((de > 1).sum()), n_gt2=int((de > 2).sum()),
                                     dL_max=round(float(np.abs(lab_o[:, 0] - lab_t[:, 0]).max()), 3),
                                     L_of_target_at_ge3=[round(float(x), 1) for x in np.percentile(srgb_to_lab(Tc[d >= 3])[:, 0], [0, 50, 100])] if (d >= 3).any() else [])
        # clustering of residual pixels
        for thr in (2, 3):
            n, lab, st_cc, _ = cv2.connectedComponentsWithStats((d >= thr).astype(np.uint8), connectivity=8)
            sizes = sorted([int(x) for x in st_cc[1:, cv2.CC_STAT_AREA]], reverse=True)
            r[f"residual_ge{thr}_components"] = dict(n=n - 1, largest=sizes[:5], singletons=int(sum(1 for x in sizes if x == 1)))
        res["sets"][s] = r
        R4[s], R1[s], REG[s], T[s] = outs["P4_browser_premultiplied"], outs["P1_straight_exact"], region, Tc
        np.save(os.path.join(os.environ.get("QA_SCRATCH", "/tmp"), f"qa_wm_v3c_resid_{s}.npy"), D[s])

    # ---------- swap-diff ----------
    sw = {}
    for s in SETS:
        for name, R in (("P1", R1), ("P4", R4)):
            ch = (R[s] != B).any(2)
            sw.setdefault(f"base->{s}", {})[name] = dict(changed_px=int(ch.sum()), changed_outside_region_px=int((ch & ~REG[s]).sum()),
                                                         region_px=int(REG[s].sum()))
        ch = (T[s] != B).any(2)
        dd = np.abs(T[s].astype(int) - B.astype(int)).max(2)
        sw[f"base->{s}"]["approved"] = dict(changed_outside_region_px=int((ch & ~REG[s]).sum()),
                                            max_level_outside_region=int(dd[~REG[s]].max()))
    for i, s in enumerate(SETS):
        for t in SETS[i + 1:]:
            u = REG[s] | REG[t]
            e = {}
            for name, R in (("P1", R1), ("P4", R4)):
                ch = (R[s] != R[t]).any(2)
                e[name] = dict(changed_px=int(ch.sum()), changed_outside_union_px=int((ch & ~u).sum()), union_px=int(u.sum()))
            ch = (T[s] != T[t]).any(2)
            dd = np.abs(T[s].astype(int) - T[t].astype(int)).max(2)
            e["approved"] = dict(changed_px=int(ch.sum()), changed_outside_union_px=int((ch & ~u).sum()),
                                 max_level_outside_union=int(dd[~u].max()))
            sw[f"{s}<->{t}"] = e
    res["swap_diff"] = sw
    json.dump(res, open(out_json, "w"), indent=1)
    for s in SETS:
        print("set", s, {k: (v["p99_9_region"], v["p99_9_canvas"], v["max"], v["px_ge3"]) for k, v in res["sets"][s]["paths"].items()})
    print("swap", {k: {n: (x.get("changed_outside_region_px", x.get("changed_outside_union_px"))) for n, x in v.items()} for k, v in sw.items()})


if __name__ == "__main__":
    main(sys.argv[1])
