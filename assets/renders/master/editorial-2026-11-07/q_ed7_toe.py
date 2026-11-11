#!/usr/bin/env python3
"""
q_ed7_toe.py: the Q-ED7 (a) toe lift for the warm-modern story frames; render-agent, 2026-11-11. One curve, shared by
mb1_fix8.py (master bedroom, warm-modern-MB-A-fix6.png) and ../../editorial-phase-b-2026-11-06/codefix_ed9.py (living room,
warm-modern-A-ed9.png), so both frames get exactly the same shape.

Source: docs/master-bedroom-comparison-2026-11-07.md §6 (master-designer, 2026-11-10, Q-ED7 ruling (a)); QA's numbers:
qa/reports/2026-11-10-ged-master-wm-fix5.json (G-ED.11) and the gate's tool qa/reports/2026-11-07-gate-g-ed/tools/guardrails.py.

The curve, on CIELAB L* only (D65, the gate's own formula):
    slope s(L) = s0 below L* 12, a smoothstep blend of the slope from s0 to 1 between 12 and 20, 1 from 20 up; f(20) = 20.
    So f(L) = L for L >= 20 (nothing at or above 20 moves), the lift is (1 - s0) * (16 - L) below 12 and fades to 0 at 20
    with a continuous slope and curvature (C2), and f is strictly monotone (slope >= s0 > 0): no level swaps, no crease flips.
    s0 is solved per frame so that the gate's p1 (L* at the 1st percentile of a quarter-size BILINEAR copy) lands on 9.0,
    the middle of the designer's 8.5-9.5.
Colour: hue and saturation kept.
    The new pixel is (chromaticity) x Y', with Y' from f, so its L* is f(L*) exactly (before 8-bit rounding).
    chromaticity: the pixel's own (linear RGB / Y), as an exposure change would keep it: hue and saturation kept, CIELAB
            chroma rises with L*. In 8 bits a near-black pixel's own chromaticity is quantisation, not colour: (2, 0, 1)
            reads as magenta and (4, 0, 0) as pure red once lifted. So below L* REL_HI the own chromaticity is blended
            (smoothstep from REL_HI down to REL_LO) with the LOCAL one: the luminance-weighted chromaticity of the RELIABLE
            dark pixels near it (L* 4-20, Gaussian sigma SIGMA_LOC), weighted by how many there are (coverage); where there
            are none (the body of the black bowl, the middle of a void) it falls back to the palette's own espresso,
            #2E2824 (docs/design-bible/warm-modern.md, accent: "espresso and dark bronze ... frame, bowl, jug"). So a
            lifted near-black reads as the espresso of the Bible or as the dimly lit material around it, never as the
            colour of its own quantisation noise and never as a neighbour's brown carried far into another object.
            (Tried first, rejected on the crops: a capped per-pixel gain, and a 7 x 7 average of all darks: magenta and
            red specks in the void under the master's nightstand, whose neighbourhood is all (1, 0, 0) / (2, 0, 1); then
            a multi-scale (sigma 6 / 20 / 60) reliable-dark average: it carried the walnut and the figs into the black
            bowl, C* 1.6 -> 7.3, chocolate rather than black-espresso; and a reliability band of L* 3-10: the walnut drum
            bases in deep shadow (L* 3-10) lost their own saturation and grain colour, flat and greyish.)
    hue:    where the own chromaticity is used (L* >= REL_HI and C* >= 6), the pixel keeps its own CIELAB hue angle (the gate's
            Lab) exactly; an exposure change alone drifts it by about +2 deg in Lab's linear segment.
    chroma: never below the pixel's own original C* (a guard for where the low-chroma espresso fallback blends in).
Pixels whose original L* >= 20 are copied byte for byte, so the count of changed pixels at L* >= 20 is 0 by construction.
"""
import cv2
import numpy as np
from PIL import Image

LO, HI = 12.0, 20.0          # lift below 12, soft blend to the identity up to 20 (designer, §6)
REL_LO, REL_HI = 2.0, 5.0    # own chromaticity trusted from L* 5 (sRGB values in the teens); fully local below L* 2 (8-bit quantisation)
SIGMA_LOC = 6.0              # px, the local chromaticity's Gaussian
REL_SRC = (4.0, 20.0)        # L* range of the pixels the local chromaticity is taken from
COVER_K = 0.001              # coverage = den / (den + COVER_K): den is the Gaussian mean of Y over reliable darks (about 10 % cover at L* 9)
PRIOR_SRGB = (0x2E, 0x28, 0x24)   # the Bible's espresso, the fallback chromaticity
P1_TARGET = 9.0              # middle of 8.5-9.5
WY = np.array([0.2126, 0.7152, 0.0722])


# ---------------------------------------------------------------- colour maths (the gate's guardrails.py formulas)
def s2l(c):
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def l2s(c):
    c = np.clip(c, 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def Lstar(Y):
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


def Yof(L):
    return np.where(L > 8.0, ((L + 16) / 116) ** 3, L / 903.3)


def lab(rgb8):
    """CIELAB D65 exactly as qa/reports/2026-11-07-gate-g-ed/tools/guardrails.py (input 0-255)"""
    c = s2l(np.asarray(rgb8, np.float64) / 255.0)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def L_of(rgb8):
    return Lstar(s2l(np.asarray(rgb8, np.float64) / 255.0) @ WY)


# ---------------------------------------------------------------- the curve
def curve(L, s0):
    L = np.asarray(L, np.float64)
    W = HI - LO
    u = np.clip((L - LO) / W, 0, 1)
    # f(L) = HI - integral_L^HI s(t) dt, with the smoothstep integral u^3 - u^4/2
    mid = HI - ((HI - L) * s0 + (1 - s0) * W * (0.5 - (u ** 3 - u ** 4 / 2)))
    f_lo = HI - W * (1 + s0) / 2
    low = f_lo - (LO - L) * s0
    return np.where(L >= HI, L, np.where(L >= LO, mid, low))


def lift_table(s0):
    return {f"{v:g}": round(float(curve(v, s0) - v), 2) for v in (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 19.5, 20, 30)}


# ---------------------------------------------------------------- apply
M_RGB2XYZ = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.9505, 1.0, 1.089])


def lab_lin(lin):
    xyz = lin @ M_RGB2XYZ.T / WHITE
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lin_from_lab(lb):
    """exact inverse of lab_lin (the gate's formula)"""
    fy = (lb[..., 0] + 16) / 116
    f = np.stack([fy + lb[..., 1] / 500, fy, fy - lb[..., 2] / 200], -1)
    t = np.where(f > 0.2068966, f ** 3, (f - 16 / 116) / 7.787)
    return (t * WHITE) @ np.linalg.inv(M_RGB2XYZ).T


def smoothstep(e0, e1, x):
    u = np.clip((x - e0) / (e1 - e0), 0, 1)
    return u * u * (3 - 2 * u)


def apply(rgb8, s0):
    """rgb8: H x W x 3 uint8. Returns (out uint8, info). Pixels with L* >= 20 are returned byte-identical."""
    rgb8 = np.asarray(rgb8, np.uint8)
    lin = s2l(rgb8.astype(np.float64) / 255.0)
    Y = lin @ WY
    L = Lstar(Y)
    sel = L < HI
    Yn = Yof(curve(L, s0))
    # chromaticities per unit Y: own, and local (luminance-weighted over the reliable darks; the Bible's espresso where none)
    src = (sel & (L >= REL_SRC[0])).astype(np.float64)
    num = np.stack([cv2.GaussianBlur(lin[..., i] * src, (0, 0), SIGMA_LOC) for i in range(3)], -1)
    den = cv2.GaussianBlur(Y * src, (0, 0), SIGMA_LOC)
    c_near = num / np.maximum(den, 1e-12)[..., None]
    p_lin = s2l(np.array(PRIOR_SRGB, np.float64) / 255.0)
    c_prior = p_lin / float(p_lin @ WY)
    cover = (den / (den + COVER_K))[..., None]
    c_loc = cover * c_near + (1 - cover) * c_prior
    c_own = np.where(Y[..., None] > 1e-9, lin / np.maximum(Y, 1e-9)[..., None], c_loc)
    r = smoothstep(REL_LO, REL_HI, L)[..., None]
    c = r * c_own + (1 - r) * c_loc
    lab_g = lab_lin(c * Yn[..., None])
    # hue lock to the pixel's own Lab hue where its own chromaticity is used and its chroma means something
    lab_o = lab_lin(lin)
    Co, Cg = np.hypot(lab_o[..., 1], lab_o[..., 2]), np.hypot(lab_g[..., 1], lab_g[..., 2])
    ug_raw = lab_g[..., 1:] / np.maximum(Cg, 1e-9)[..., None]
    Cg = np.maximum(Cg, Co)                                      # chroma never falls (the designer: "the chroma does not go down")
    lock = (r[..., 0] * smoothstep(2.0, 6.0, Co))[..., None]
    uo = lab_o[..., 1:] / np.maximum(Co, 1e-9)[..., None]
    ug = ug_raw
    u = lock * uo + (1 - lock) * ug
    u = u / np.maximum(np.linalg.norm(u, axis=-1, keepdims=True), 1e-9)
    new = lin_from_lab(np.concatenate([lab_g[..., :1], u * Cg[..., None]], -1))
    clipped = sel & ((new < -1e-6).any(-1) | (new > 1 + 1e-6).any(-1))
    out = (np.clip(l2s(new), 0, 1) * 255 + 0.5).astype(np.uint8)
    out = np.where(sel[..., None], out, rgb8)
    info = dict(px_in_toe=int(sel.sum()), px_chromaticity_partly_local=int((sel & (L < REL_HI)).sum()),
                px_chromaticity_fully_local=int((sel & (L <= REL_LO)).sum()), px_hue_locked=int((sel & (lock[..., 0] > 0.999)).sum()),
                px_gamut_clipped=int(clipped.sum()))
    return out, info


# ---------------------------------------------------------------- the gate's p1 / p5 (quarter-size bilinear copy)
def gate_percentiles(rgb8, qs=(0.5, 1, 5)):
    im = Image.fromarray(np.asarray(rgb8, np.uint8))
    w, h = im.size
    small = np.asarray(im.resize((w // 4, h // 4), Image.BILINEAR)).reshape(-1, 3).astype(float)
    L = lab(small)[:, 0]
    return {f"p{q:g}": round(float(np.percentile(L, q)), 2) for q in qs}


def full_percentiles(rgb8, qs=(0.5, 1, 5)):
    L = L_of(rgb8)
    return {f"p{q:g}": round(float(np.percentile(L, q)), 2) for q in qs}


def solve_s0(rgb8, target=P1_TARGET, tol=0.01):
    """bisection on s0 (lower s0 = stronger lift) until the gate's p1 of the result is within tol of target"""
    lo, hi = 0.2, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2
        p1 = gate_percentiles(apply(rgb8, mid)[0], (1,))["p1"]
        if abs(p1 - target) <= tol:
            return mid
        if p1 > target:
            lo = mid           # too much lift: raise s0
        else:
            hi = mid
    return mid


# ---------------------------------------------------------------- checks
def checks(before8, after8):
    b, a = np.asarray(before8, np.uint8), np.asarray(after8, np.uint8)
    lb, la = lab(b), lab(a)
    Lb = lb[..., 0]
    d = np.abs(a.astype(int) - b.astype(int)).max(2)
    ch = d > 0
    ge20 = Lb >= HI
    Cb, Ca = np.hypot(lb[..., 1], lb[..., 2]), np.hypot(la[..., 1], la[..., 2])
    hb, ha = np.degrees(np.arctan2(lb[..., 2], lb[..., 1])), np.degrees(np.arctan2(la[..., 2], la[..., 1]))
    dh = (ha - hb + 180) % 360 - 180

    def stats(v, m, qs=(1, 5, 50, 95, 99), nd=2):
        return {f"p{q}": round(float(np.percentile(v[m], q)), nd) for q in qs} | {"px": int(m.sum())} if m.any() else None
    own = ch & (Lb >= REL_HI) & (Cb >= 6)                 # own chromaticity, hue locked
    mix = ch & (Lb >= REL_LO) & (Lb < REL_HI) & (Cb >= 4)  # own blended with local
    magenta_new = ch & (Cb < 4) & (Ca >= 6) & (ha > -90) & (ha < -10)
    return dict(
        px_changed=int(ch.sum()),
        px_changed_at_L_ge_20=int((ch & ge20).sum()),
        px_changed_gt2_at_L_ge_20=int(((d > 2) & ge20).sum()),
        max_L_before_of_a_changed_px=round(float(Lb[ch].max()), 2) if ch.any() else None,
        max_abs_change_8bit=int(d.max()),
        hue_shift_deg_own_class_L_ge_5_C_ge_6=stats(dh, own),
        hue_shift_deg_mixed_class_L_2_5_C_ge_4=stats(dh, mix),
        chroma_ratio_own_class=stats(Ca / np.maximum(Cb, 1e-9), own, (1, 5, 50), 3),
        share_changed_px_C_fell_gt_0_5=round(float(((Ca < Cb - 0.5) & ch).sum() / max(ch.sum(), 1)), 4),
        new_magenta_px_from_near_neutral=int(magenta_new.sum()),
    )


# ---------------------------------------------------------------- before / after crops (shared by both scripts)
def crop_pair(before8, after8, box, scale, title, path, stretch=1.0):
    """before | after side by side, at 100 % (scale 1, the pixels as they are) or enlarged with NEAREST (scale 4)"""
    from PIL import ImageDraw, ImageFont
    x0, y0, x1, y1 = box
    def one(a):
        c = np.asarray(a, np.uint8)[y0:y1, x0:x1].astype(np.float64)
        c = np.clip(c * stretch, 0, 255).astype(np.uint8)
        im = Image.fromarray(c)
        return im if scale == 1 else im.resize(((x1 - x0) * scale, (y1 - y0) * scale), Image.NEAREST)
    a, b = one(before8), one(after8)
    pad, top = 12, 52
    sheet = Image.new("RGB", (max(a.width * 2 + pad * 3, 520), a.height + top + pad), (245, 244, 240))
    sheet.paste(a, (pad, top))
    sheet.paste(b, (a.width + pad * 2, top))
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except OSError:
        f = ImageFont.load_default()
    d = ImageDraw.Draw(sheet)
    d.text((pad, 6), title, fill=(30, 30, 30), font=f)
    d.text((pad, 26), f"x {x0}-{x1}, y {y0}-{y1} · {'100 %' if scale == 1 else f'x{scale} NEAREST'}"
                      f"{'' if stretch == 1 else f' · stretch x{stretch:g}'} · before | after", fill=(80, 80, 80), font=f)
    sheet.save(path, quality=95)
    return path


# ---------------------------------------------------------------- the gate's own tool, for the record
def gate_guardrails(paths):
    """runs qa/reports/2026-11-07-gate-g-ed/tools/guardrails.py's measure() (G-ED.11 split flag and shadow floor, G-ED.12 clipping)"""
    import importlib.util
    import os
    repo = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
    spec = importlib.util.spec_from_file_location("guardrails", os.path.join(repo, "qa/reports/2026-11-07-gate-g-ed/tools/guardrails.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    keys = ("shadow_floor_L_p0_5", "shadow_floor_L_p1", "shadows_10pct_Lab", "highlights_10pct_Lab", "split_flag", "clipped_254_pct", "near_clip_250_pct")
    return {os.path.basename(p): {k: v for k, v in g.measure(p, []).items() if k in keys} for p in paths}
