#!/usr/bin/env python3
"""
fin2_codefix.py: QA's zero-token code fixes on editorial phase B (qa/reports/2026-11-06-editorial-phase-b-fidelity.md), render-agent, 2026-11-06.
New files only (-fin2); the -fin files and the raws stay as they are.
  nordicA  the code-fix traces in Nordic A: (1) round the right wall light, the light hard-edged rectangle (the old lamp's footprint) and the
           old lamp's shading / the bite in the sun strip under it: the wall rebuilt as a smooth (harmonic) field from the plain wall round it,
           the lamp's own light and shading (measured on the seedream raw against that field) scaled x0.36 about its centre like the body, the
           sun stripes kept with the ambient change added; (2) under the pendant, the soft dark and pale patches: the low frequencies of the
           old pendant's hole re-solved as a harmonic field from its rim, the fill's fine grain kept
  wm       Warm modern A: the floor lamp's polished brass to the card's satin (matte) brass, #B8924E: highlights compressed, reflections
           smoothed along the part, saturation eased; nothing else
  boho     Boho A: the raffia sun to its card's 30 cm (x0.50 about its centre; it read about x2 against the frames), the wall behind
           refilled (harmonic low frequencies from the rim + plaster grain synthesised band by band to the wall's own measured spectrum),
           a soft contact shadow for the new size
  crops    before / after crops (100 %) for QA
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finish_phaseb import s2l, l2s, load01, knee, body_bbox, SCONCE_SCALE  # noqa: E402

RAW = os.path.join(HERE, "raw")
CROPS = os.path.join(HERE, "fin2-before-after")
REC = os.path.join(HERE, "fin2-codefix.json")


def save8(a, p):
    o8 = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(o8).save(p)
    return o8


def lum(lin):
    return lin[..., 0] * 0.2126 + lin[..., 1] * 0.7152 + lin[..., 2] * 0.0722


def nblur(img, w, s):
    """normalized convolution: blur of img over the pixels where w > 0 (w in [0, 1])"""
    w3 = w[..., None] if img.ndim == 3 else w
    num = cv2.GaussianBlur(img * w3, (0, 0), s)
    den = cv2.GaussianBlur(w.astype(np.float32), (0, 0), s)
    den3 = den[..., None] if img.ndim == 3 else den
    return num / np.maximum(den3, 1e-6), den


def harmonic(val, known, f=4, iters=3000):
    """membrane (Laplace) interpolation of val into the cells where known is False, solved at 1/f size; returns full size"""
    H, W = known.shape
    h, w = H // f, W // f
    v = cv2.resize(val, (w, h), interpolation=cv2.INTER_AREA)
    k = cv2.resize(known.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA) > 0.999
    if v.ndim == 2:
        v = v[..., None]
    u = v.copy()
    # start from a coarse normalized blur so it converges fast
    m0, _ = nblur(v, k.astype(np.float32), 8)
    u[~k] = m0[~k]
    for _ in range(iters):
        p = np.pad(u, ((1, 1), (1, 1), (0, 0)), mode="edge")
        avg = 0.25 * (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:])
        u = np.where(k[..., None], v, avg)
    out = cv2.resize(u, (W, H), interpolation=cv2.INTER_CUBIC)
    if out.ndim == 2:
        out = out[..., None]
    out = cv2.GaussianBlur(out, (0, 0), f)
    if out.ndim == 2:
        out = out[..., None]
    return np.where(known[..., None], val if val.ndim == 3 else val[..., None], out)


# ----------------------------------------------------------------------------------------------------------------------------------
def nordic_a():
    O = load01(os.path.join(RAW, "nordic-A-fin-seedream.png"))
    C = load01(os.path.join(RAW, "nordic-A-fin-codefix.png"))
    H, W = O.shape[:2]
    Ol, Cl = s2l(O), s2l(C)
    yy, xx = np.mgrid[0:H, 0:W]
    rec = {}
    # ---- (1) the right wall light ------------------------------------------------------------------------------------------------
    bx0, by0, bx1, by1 = body_bbox(O, (2020, 300, 2180, 600))        # the same body the first code fix found: 2048-2146 x 332-563
    cx, cy = 0.5 * (bx0 + bx1), 0.5 * (by0 + by1)
    X0, Y0, X1, Y1 = 1942, 168, 2322, 720                             # plain wall: right of the art frame, left of the door casing
    Z = np.zeros((H, W), bool)
    Z[205:600, 1996:2296] = True                                      # where the old lamp's light and shading reach (and the old rectangle)
    Z[239:572, 1989:2205] = True
    Z[560:662, 2030:2112] = True                                      # and its downlight on the wall left of the sun stripe
    body = np.zeros((H, W), bool)
    body[by0 - 4:by1 + 5, bx0 - 4:bx1 + 5] = True
    LO = cv2.cvtColor((O * 255).astype(np.uint8), cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32) * 100 / 255
    LOb = cv2.GaussianBlur(LO, (0, 0), 1.5)
    # sun: the stripes are 80-90 L* against a 55-65 wall; a soft weight across the penumbra
    sun_w = np.clip((LOb - 66.0) / 8.0, 0, 1)
    sun_w[:540] = 0
    # under the old lamp, its downlight merged with the stripe into a bright lobe flat-topped at the lamp's bottom (x 2058-2135, y 561-600,
    # fading by y 660): the lobe is lamp light (scaled with the lamp below), the stripe keeps its own edges: its top as read on
    # x 2150-2200 (y = 586 + 0.38 (x - 2150)) and its left edge at x 2100 (read on y 600-650), 5 / 4 px penumbra; the sun is never extended
    ytop = 586 + 0.38 * (xx - 2150)
    lim = np.clip((yy - ytop) / 5.0 + 0.5, 0, 1) * np.clip((xx - 2100) / 4.0 + 0.5, 0, 1)
    under = (xx >= 2030) & (xx < 2150) & (yy < 662)
    sun_w = np.where(under, sun_w * lim, sun_w)
    sun_core = sun_w > 0.02
    edges = np.abs(cv2.Laplacian(cv2.GaussianBlur(LO, (0, 0), 1.2), cv2.CV_32F, ksize=3)) > 4.0
    edges = cv2.dilate(edges.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    wall_O = ~(sun_core | body)
    WO, den = nblur(Ol, wall_O.astype(np.float32), 10)               # the wall's light without the sun stripes and the old body
    # the clean wall: harmonic from the plain wall round Z, solved on the box (its border reflects)
    sl = (slice(Y0, Y1), slice(X0, X1))
    known = (~Z & (den > 0.35) & ~edges)[sl]
    B = Ol.copy()
    B[sl] = harmonic(np.where(known[..., None], WO[sl], 0), known)
    WOs = np.where((den > 0.25)[..., None], WO, B)
    # the lamp's own effect on the wall (glow > 1, its shading < 1), inside Z only, scaled about the lamp's centre like the body
    wz = cv2.GaussianBlur(Z.astype(np.float32), (0, 0), 14)[..., None]
    E = 1 + (np.clip(WOs / np.maximum(B, 1e-5), 0.3, 4.0) - 1) * wz
    A = np.array([[SCONCE_SCALE, 0, cx - SCONCE_SCALE * cx], [0, SCONCE_SCALE, cy - SCONCE_SCALE * cy]], np.float32)
    Es = 1 + cv2.warpAffine(E - 1, A, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    T = B * Es
    # grain: the seedream wall's own fine grain (O / its sigma-2.5 blur); in a band 16 px round the old body (its rim light and contact
    # shadow) the same wall's grain from 150 px to the right (plain wall in shade), feathered
    G = np.clip(Ol / np.maximum(nblur(Ol, wall_O.astype(np.float32), 2.5)[0], 1e-5), 0.7, 1.4)
    band = cv2.dilate(body.astype(np.uint8), np.ones((33, 33), np.uint8)).astype(bool)
    Gd = np.roll(G, -150, axis=1)
    fb = cv2.GaussianBlur(band.astype(np.float32), (0, 0), 3)[..., None]
    G = G * (1 - fb) + Gd * fb
    sw = np.where(band[..., None], 0, sun_w[..., None])
    sw = np.maximum(sw, (sun_w * under)[..., None] * (~body)[..., None])
    new_wall = T * G
    new_sun = Ol + (T - WOs)
    new = (1 - sw) * new_wall + sw * new_sun
    M = cv2.dilate(Z.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
    inbox = np.zeros((H, W), bool)
    inbox[sl] = True
    M = cv2.GaussianBlur(M, (0, 0), 6)[..., None] * inbox[..., None]
    out = Cl * (1 - M) + new * M
    # the small body, as the first code fix placed it
    bm = np.zeros((H, W), np.float32)
    bm[by0:by1, bx0:bx1] = 1
    bal = cv2.GaussianBlur(bm, (0, 0), 0.7)
    body_a = np.clip(cv2.warpAffine(bal, A, (W, H), flags=cv2.INTER_AREA), 0, 1)[..., None]
    out = out * (1 - body_a) + Cl * body_a
    rec["right_wall_light"] = dict(body_px=[int(bx0), int(by0), int(bx1), int(by1)], scale=SCONCE_SCALE, centre=[round(cx, 1), round(cy, 1)],
                                   rebuilt_px=[1989, 205, 2296, 662], sun_stripe_under_lamp="top y = 586 + 0.38 (x - 2150), left edge x 2100 (cut only; the lobe was the old downlight)",
                                   how="harmonic clean wall from the plain wall round it (x 1942-2322, y 168-668); the lamp's light and shading "
                                       "(seedream wall / clean wall) scaled x0.36 about its centre; the wall's own fine grain (a 16 px band round the "
                                       "old body takes it from 150 px right); sun stripes kept with the ambient change added; small body pasted back")
    # ---- (2) under the pendant ---------------------------------------------------------------------------------------------------
    hole = np.zeros((H, W), np.uint8)
    cv2.ellipse(hole, (1362, 200), (216, 106), 0, 0, 360, 1, -1)
    hole = cv2.dilate(hole, np.ones((7, 7), np.uint8))
    hole = cv2.dilate(hole, np.ones((15, 15), np.uint8)).astype(bool)          # the first fix's hole
    hole[235:336, 1110:1250] = True                                            # and the left wall light's old up-glow corner that meets it
    hole[280:346, 1240:1660] = True                                            # and down to the art's top edges (the first fill bled there)
    # the new (x0.70) pendant and its cable, and the art frames (their top edges read per column on the frame): kept out
    pend = np.zeros((H, W), np.uint8)
    cv2.ellipse(pend, (1362, int(200 * 0.70)), (int(216 * 0.70) + 8, int(106 * 0.70) + 8), 0, 0, 360, 1, -1)
    pend[0:150, 1348:1377] = 1
    pend = pend.astype(bool)
    frames = ((xx >= 1252) & (xx <= 1452) & (yy >= 339 - 0.05 * (xx - 1260) - 3)) | ((xx >= 1468) & (yy >= 328 - 0.047 * (xx - 1480) - 3))
    frames |= yy >= 345
    LC = cv2.cvtColor((np.clip(l2s(out), 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32) * 100 / 255
    edgesC = np.abs(cv2.Laplacian(cv2.GaussianBlur(LC, (0, 0), 1.2), cv2.CV_32F, ksize=3)) > 4.0
    edgesC = cv2.dilate(edgesC.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    zone = hole & ~pend & ~frames
    zone_d = cv2.dilate(zone.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~pend & ~frames
    wallC = ~(pend | frames | edgesC)
    CL, denc = nblur(out, wallC.astype(np.float32), 10)
    sp = (slice(0, 360), slice(1040, 1700))
    known = (~zone_d & wallC & (denc > 0.35))[sp]
    TP = harmonic(np.where(known[..., None], CL[sp], 0), known)
    # the zone: the harmonic field times the fine grain only (out / its sigma-2.5 blur), so the mid-size remnants (the old shade's lit edge
    # at x 1170-1210) go too
    Gc = np.clip(out / np.maximum(nblur(out, wallC.astype(np.float32), 2.5)[0], 1e-5), 0.8, 1.25)
    newz = out.copy()
    newz[sp] = TP * Gc[sp]
    Mz = cv2.GaussianBlur(zone_d.astype(np.float32), (0, 0), 5)[..., None] * (~(pend | frames))[..., None]
    out = out * (1 - Mz) + newz * Mz
    rec["pendant_zone"] = dict(hole="the first fix's hole (ellipse (1362, 200) axes (216, 106) grown 7 + 15 px) and x 1110-1250 y 235-336, "
                                    "and x 1240-1660 y 280-346, minus the x0.70 pendant, cable and the art (top edges per column)",
                               how="replaced by a harmonic field from its rim times the fill's own fine grain (ratio to its sigma-2.5 blur)")
    o8 = save8(l2s(out), os.path.join(RAW, "nordic-A-fin2-codefix.png"))
    # nothing else moved: outside the two zones the file equals the -fin code fix
    moved = np.abs(o8.astype(np.int16) - (C * 255 + 0.5).astype(np.int16)).max(2) > 2
    allowed = cv2.dilate((M[..., 0] > 0.002).astype(np.uint8) | (Mz[..., 0] > 0.002).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    rec["nothing_else_moved"] = dict(px_changed_outside_zones=int((moved & ~allowed).sum()), px_changed_inside=int((moved & allowed).sum()))
    return rec


# ----------------------------------------------------------------------------------------------------------------------------------
def warm_modern():
    a = load01(os.path.join(RAW, "warm-modern-A-fin-seedream.png"))
    H, W = a.shape[:2]
    hsv = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    h, s, v = hsv[..., 0], hsv[..., 1] / 255, hsv[..., 2] / 255
    # the lamp's brass parts only: the upper stem, the collars, the pull chain, the base (boxes read on the frame)
    boxes = [(2528, 420, 2556, 600), (2522, 760, 2560, 790), (2522, 880, 2562, 905), (2578, 425, 2604, 560), (2462, 1070, 2632, 1145)]
    roi = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in boxes:
        roi[y0:y1, x0:x1] = True
    brass = roi & (h >= 12) & (h < 32) & (s > 0.68) & (v > 0.06)            # brass S 0.7-1.0; the wall and floor round it S 0.4-0.6
    brass = cv2.morphologyEx(brass.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    brass = cv2.morphologyEx(brass, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool) & roi
    al = cv2.GaussianBlur(brass.astype(np.float32), (0, 0), 0.8)[..., None]
    lin = s2l(a)
    # brushed: reflections smoothed along the part (vertical on the stem, horizontal on the base), done in a normalized blur on the brass only
    stem = np.zeros((H, W), bool)
    stem[:1060] = True
    kv = cv2.getGaussianKernel(31, 7)
    kh = cv2.getGaussianKernel(31, 7)
    num_v = cv2.sepFilter2D(lin * brass[..., None], -1, np.array([[1.0]]), kv)
    den_v = cv2.sepFilter2D(brass.astype(np.float32), -1, np.array([[1.0]]), kv)
    num_h = cv2.sepFilter2D(lin * brass[..., None], -1, kh, np.array([[1.0]]))
    den_h = cv2.sepFilter2D(brass.astype(np.float32), -1, kh, np.array([[1.0]]))
    along = np.where(stem[..., None], num_v / np.maximum(den_v[..., None], 1e-5), num_h / np.maximum(den_h[..., None], 1e-5))
    satin = 0.45 * lin + 0.55 * along
    # highlights compressed (specular peaks to a satin sheen), and the colour eased toward the card's #B8924E
    Y = lum(satin)[..., None]
    Yc = np.where(Y > 0.18, 0.18 + (Y - 0.18) * 0.55, Y)
    satin = satin * (Yc / np.maximum(Y, 1e-5))
    card = s2l(np.array([0xB8, 0x92, 0x4E], np.float32) / 255)
    chroma_card = card / lum(card[None, None])[0, 0]
    chroma = satin / np.maximum(lum(satin)[..., None], 1e-5)
    satin = lum(satin)[..., None] * (0.70 * chroma + 0.30 * chroma_card)
    out = lin * (1 - al) + satin * al
    o8 = save8(l2s(out), os.path.join(RAW, "warm-modern-A-fin2-codefix.png"))
    a8 = (a * 255 + 0.5).astype(np.uint8)
    moved = np.abs(o8.astype(np.int16) - a8.astype(np.int16)).max(2) > 2
    allowed = cv2.dilate((al[..., 0] > 0.002).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    Yb, Ya = lum(lin)[brass], lum(out)[brass]
    return dict(brass_px=int(brass.sum()), boxes=boxes, luminance_p99_before=round(float(np.percentile(Yb, 99)), 3),
                luminance_p99_after=round(float(np.percentile(Ya, 99)), 3),
                how="brass parts only (hue 12-32, S > 0.68 in the lamp's boxes): reflections smoothed along the part (sigma 7), "
                    "luminance above 0.18 (linear) x0.55, chroma 30 % toward the card's #B8924E",
                nothing_else_moved=dict(px_changed_outside=int((moved & ~allowed).sum()), px_changed_inside=int((moved & allowed).sum())))


# ----------------------------------------------------------------------------------------------------------------------------------
BOHO_SCALE = 0.42      # frame height 403 px; if the generic frames are 50 x 70 that is 5.76 px/cm: the sun read 407 px = 71 cm, 30 cm = 173 px


def boho():
    a = load01(os.path.join(RAW, "boho-A-gpt-image-2-5.png"))
    H, W = a.shape[:2]
    lin = s2l(a)
    cx, cy = 587.0, 369.0
    L = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32) * 100 / 255
    tex = cv2.GaussianBlur(np.abs(L - cv2.GaussianBlur(L, (0, 0), 1.5)), (0, 0), 3)    # raffia > 1, the plaster 0.3-0.4
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot(xx - cx, yy - cy)
    ang = np.arctan2(yy - cy, xx - cx)
    sconce = (xx < 399) & (yy > 225) & (yy < 485)                      # the bamboo wall light, its arm and plate
    frame = (xx > 798) & (yy > 165) & (yy < 590)
    raff = (tex > 1.0) & (r < 240) & ~sconce & ~frame
    # the sun's outer radius per angle (360 bins, 99th percentile of the raffia's radius), smoothed round the circle
    nb = 360
    bi = ((ang + np.pi) / (2 * np.pi) * nb).astype(int) % nb
    rout = np.zeros(nb)
    for b in range(nb):
        rr = r[(bi == b) & raff]
        rout[b] = np.percentile(rr, 99) if rr.size > 30 else 195
    rout = np.convolve(np.r_[rout[-5:], rout, rout[:5]], np.ones(11) / 11, mode="same")[5:-5]
    R = rout[bi]
    hole = (r < R + 24) & ~sconce & ~frame                       # with the old sun's soft shadow just outside its fringe
    # the old sun's alpha: solid inside, strand by strand in the fringe (local texture), so no wall comes along with it
    alpha = np.where(r < R - 28, 1.0, np.clip((tex - 0.6) / 0.8, 0, 1) * (r < R + 4))
    alpha = np.where(sconce | frame, 0, alpha).astype(np.float32)
    A = np.array([[BOHO_SCALE, 0, cx * (1 - BOHO_SCALE)], [0, BOHO_SCALE, cy * (1 - BOHO_SCALE)]], np.float32)
    sc = cv2.warpAffine(lin * alpha[..., None], A, (W, H), flags=cv2.INTER_AREA)
    sa = np.clip(cv2.warpAffine(alpha, A, (W, H), flags=cv2.INTER_AREA), 0, 1)
    # the wall behind: low frequencies harmonic from the rim (the light wall round it, the wall light's glow included)
    wl, den = nblur(lin, (~hole & ~sconce & ~frame).astype(np.float32), 12)
    sl = (slice(60, 700), slice(250, 900))
    known = (~hole & ~sconce & ~frame & (den > 0.3))[sl]
    low = lin.copy()
    low[sl] = harmonic(np.where(known[..., None], wl[sl], 0), known, f=4, iters=4000)
    # plaster texture: the real wall's, quilted from the plain strip above the art (x 800-1440, y 70-160): its ratio to its own sigma-40
    # light, laid in rows of 90 px (18 px cross-fades), each from a random offset, some mirrored; the light itself from the harmonic field
    donor_m = np.zeros((H, W), np.float32)
    donor_m[0:168, 430:1460] = 1
    dl, _ = nblur(lin, donor_m, 40)
    Gd = np.clip(lin / np.maximum(dl, 1e-5), 0.75, 1.3)[70:160, 800:1440]
    ys, xs = np.nonzero(hole)
    hy0, hy1, hx0, hx1 = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
    hh, ww = hy1 - hy0, hx1 - hx0
    rng = np.random.default_rng(23)
    TH, OV = 90, 18
    acc = np.zeros((hh, ww, 3), np.float32)
    wacc = np.zeros((hh, ww, 1), np.float32)
    tiles = []
    y = 0
    while y < hh:
        x0 = int(rng.integers(0, Gd.shape[1] - ww + 1))
        t = Gd[:, x0:x0 + ww]
        flip = bool(rng.integers(0, 2))
        if flip:
            t = t[:, ::-1]
        n = min(TH, hh - y)
        wv = np.ones((TH, 1, 1), np.float32)
        wv[:OV, 0, 0] = np.linspace(0.02, 1, OV) if y > 0 else 1
        wv[TH - OV:, 0, 0] = np.linspace(1, 0.02, OV)
        acc[y:y + n] += t[:n] * wv[:n]
        wacc[y:y + n] += wv[:n]
        tiles.append(dict(y=hy0 + y, donor_x=800 + x0, mirrored=flip))
        y += TH - OV
    Gt = np.ones((H, W, 3), np.float32)
    Gt[hy0:hy1, hx0:hx1] = acc / np.maximum(wacc, 1e-5)
    wall_new = low * Gt
    wh = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 5.0)[..., None] * (~sconce)[..., None]
    out = lin * (1 - wh) + wall_new * wh
    # a soft contact shadow for the new size (the light is from the wall light on the left: the shadow falls a little right and down)
    sh = cv2.GaussianBlur(cv2.warpAffine(sa, np.float32([[1, 0, 4], [0, 1, 5]]), (W, H)), (0, 0), 6)
    out = out * (1 - 0.20 * sh[..., None] * (1 - sa[..., None]))
    out = out * (1 - sa[..., None]) + np.clip(sc / np.maximum(sa[..., None], 1e-4), 0, 1) * sa[..., None]
    o8 = save8(l2s(out), os.path.join(RAW, "boho-A-fin2-codefix.png"))
    a8 = (a * 255 + 0.5).astype(np.uint8)
    moved = np.abs(o8.astype(np.int16) - a8.astype(np.int16)).max(2) > 2
    allowed = cv2.dilate(hole.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
    d_before = 2 * float(np.median(rout))
    return dict(centre_px=[cx, cy], scale=BOHO_SCALE, diameter_px_before=round(d_before, 1), diameter_px_after=round(d_before * BOHO_SCALE, 1),
                card_cm=30, plaster="the real wall's texture quilted from x 800-1440 y 70-160", plaster_rows=tiles,
                note="the frames are generic (no card size): at 70 cm for their 403 px height the sun read ~71 cm (x2.4) and now ~30 cm; "
                     "QA's estimate was 'about x2'",
                nothing_else_moved=dict(px_changed_outside=int((moved & ~allowed).sum()), px_changed_inside=int((moved & allowed).sum())))


# ----------------------------------------------------------------------------------------------------------------------------------
def finish_fin2():
    rec = {}
    for fid, raw in [("nordic-A-fin2", "raw/nordic-A-fin2-codefix.png"), ("warm-modern-A-fin2", "raw/warm-modern-A-fin2-codefix.png"),
                     ("boho-A-fin2", "raw/boho-A-fin2-codefix.png")]:
        a = load01(os.path.join(HERE, raw))
        o8 = save8(knee(a), os.path.join(HERE, fid + ".png"))
        rec[fid] = dict(raw=raw, px_at_255=int((o8.max(2) >= 255).sum()), how="a soft knee per channel 0.90 -> 0.985 only, as the -fin files")
    return rec


def crops():
    os.makedirs(CROPS, exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)

    def stretch(im):
        x = np.asarray(im).astype(np.float32)
        lo, hi = np.percentile(x, 1), np.percentile(x, 99.5)
        return Image.fromarray(np.clip((x - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8))

    sets = [("nordicA-right-light", "nordic-A-fin.png", "nordic-A-fin2.png", (1880, 180, 2420, 760), True),
            ("nordicA-pendant", "nordic-A-fin.png", "nordic-A-fin2.png", (1080, 0, 1660, 360), True),
            ("warm-modern-floor-lamp", "warm-modern-A-fin.png", "warm-modern-A-fin2.png", (2400, 380, 2680, 1160), False),
            ("boho-raffia-sun", "boho-A.png", "boho-A-fin2.png", (180, 60, 1060, 720), False)]
    out = []
    for name, b, a_, box, st in sets:
        B = Image.open(os.path.join(HERE, b)).convert("RGB").crop(box)
        Aa = Image.open(os.path.join(HERE, a_)).convert("RGB").crop(box)
        w, h = B.size
        rows = [(B, Aa)] + ([(stretch(B), stretch(Aa))] if st else [])
        im = Image.new("RGB", (2 * w + 30, len(rows) * (h + 34) + 10), (250, 249, 247))
        d = ImageDraw.Draw(im)
        for i, (p, q) in enumerate(rows):
            y = 10 + i * (h + 34)
            im.paste(p, (10, y + 24))
            im.paste(q, (20 + w, y + 24))
            tag = " (contrast stretched)" if i else " (100 %)"
            d.text((10, y), "before: " + b + tag, fill=(0, 0, 0), font=f)
            d.text((20 + w, y), "after: " + a_ + tag, fill=(0, 0, 0), font=f)
        p = os.path.join(CROPS, name + ".jpg")
        im.save(p, quality=92)
        out.append(os.path.relpath(p, HERE))
    return out


if __name__ == "__main__":
    what = sys.argv[1:] or ["all"]
    R = json.load(open(REC)) if os.path.exists(REC) else dict(date="2026-11-06", by="render-agent", qa="qa/reports/2026-11-06-editorial-phase-b-fidelity.md",
                                                              tokens=0, note="TEST, not for the site; new files only")
    if "nordicA" in what or "all" in what:
        R["nordic-A-fin2"] = nordic_a()
        print(json.dumps(R["nordic-A-fin2"], indent=0))
    if "wm" in what or "all" in what:
        R["warm-modern-A-fin2"] = warm_modern()
        print(json.dumps(R["warm-modern-A-fin2"], indent=0))
    if "boho" in what or "all" in what:
        R["boho-A-fin2"] = boho()
        print(json.dumps(R["boho-A-fin2"], indent=0))
    if "finish" in what or "all" in what:
        R["finishing"] = finish_fin2()
    if "crops" in what or "all" in what:
        R["crops"] = crops()
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
