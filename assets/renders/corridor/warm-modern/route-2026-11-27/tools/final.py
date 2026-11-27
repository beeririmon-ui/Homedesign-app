#!/usr/bin/env python3
"""
final.py: CM and CK from their r2 renders to the delivered stills (render-agent, 2026-11-27). 0 var2 tokens; pointwise or masked by the
clay's geometry, nothing redrawn by a model.
  CK  1. the hall console: r2 drew a low bench in its place (the shape moved, FB21 2: "the code replaces it"). The bench is inpainted out
         and r1's console (the drum console, as HDx2) is set on the clay's console box (one affine, r1 bbox -> clay bbox), tone-matched to
         r2 on the plaster around it.
      2. an invented pale wood strip on the corridor's left wall (Y 11.99-12.37, x 650-790): drawn again from the model input's
         geometry (wall / skirting / floor by the clay), times r2's own light diffused in from its edges, plus r2's plaster grain.
  both 3. levels by region (FB21 1): the corridor's walls, floor, ceiling and slot to HC's same walls (mean of the two walls' stops vs
         HC to 0); CK's hall (seen through the portal) to the same wall in HDx2 fb19 (L* 68.6); CM's bedroom (through the door) to HC's
         bedroom (L* 80.7) under a soft shoulder. The floor blends between regions over 0.6 m of world Y, so no line crosses the oak.
      4. the oak to HC's oak: a* and b* scaled to HC's corridor floor medians, L* to HC's (40.0).
      5. CK: the refeed (corr.py refeed) in the openings, feathered 1.2 px; the slot's core rolled off under 255.
      6. the WM-G1 toe (hall tools/tone.py, not edited) on the model part only, A for p0.1 = 11.8 there.
  python3 final.py CK|CM   -> ../CK.png (canvas 2720 x 1530), ../CK-frame.png (1920 x 1080), CK-checks.json
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import corr as C  # noqa: E402

SCR = C.SCR
RAW = {k: os.path.join(C.SRC, f"{k.lower()}-r2-model.png") for k in ("CK", "CM")}
R1_CK = os.path.join(C.SRC, "ck-r1-model.png")
HDX2_FRONT_WALL_L = 68.6         # hdx2-products-fb19-frame.png, the hall front wall (Y 6.35) at Z 0.9-1.6, measured through its depth-fb17
HC_BEDROOM_L = 80.7              # hc-transfer.json "bedroom"
W709 = C.W709


def Y_of(l):
    return l @ W709


def L_to_Y(L):
    return ((L + 16) / 116) ** 3 if L > 8 else L / 903.3


def set_Y(l, m, gain):
    """multiply linear rgb by gain (array or scalar) where m"""
    g = np.broadcast_to(gain, m.shape)
    l[m] = l[m] * g[m][:, None]


def shoulder(y, k=0.62, top=0.93):
    """soft shoulder above k (linear Y): continuous slope 1 at k, asymptote `top` (L* ~97, nothing clips)"""
    s = top - k
    return np.where(y < k, y, k + s * np.tanh((y - k) / s))


def patch(img_l, guide_l, hole, cls, ring_w=25, grain=True):
    """img_l inside `hole` from the guide's shading per class times img/guide diffused in from a ring (normalised convolution, coarse
    to fine), plus img's own grain (its high-pass from the ring, mirrored across the hole's edge). Linear rgb."""
    out = img_l.copy()
    ring = cv2.dilate(hole.astype(np.uint8), np.ones((2 * ring_w + 1, 2 * ring_w + 1), np.uint8)).astype(bool) & ~hole
    for c in np.unique(cls[hole]):
        hc = hole & (cls == c)
        rc = ring & (cls == c) & (guide_l.min(-1) > 1e-4)
        if rc.sum() < 30:
            rc = ring & (guide_l.min(-1) > 1e-4)
        ratio = np.ones_like(img_l)
        ratio[rc] = img_l[rc] / guide_l[rc]
        w = rc.astype(np.float32)
        c_est = np.median(ratio[rc], 0)[None, None] * np.ones_like(img_l)
        for sig in (90, 45, 22, 11, 5):
            bw = cv2.GaussianBlur(w, (0, 0), sig)
            bc = cv2.GaussianBlur(ratio * w[..., None], (0, 0), sig)
            ok = bw > 2e-3
            c_est = np.where(ok[..., None], bc / np.maximum(bw, 1e-6)[..., None], c_est)
        out[hc] = guide_l[hc] * c_est[hc]
    # grain: r2's own plaster high-pass, clipped to +-0.012 (no edges), from the same rows mirrored about the hole's right edge, only
    # where the source pixel is the same class
    ys, xs = np.nonzero(hole)
    x0, x1 = xs.min(), xs.max()
    width = x1 - x0 + 1
    if grain:
        hp = np.clip(img_l - cv2.GaussianBlur(img_l, (0, 0), 3), -0.012, 0.012)
        mir = np.clip(x1 + 1 + (x1 - np.arange(x0, x1 + 1)), 0, img_l.shape[1] - 1)
        g = np.zeros_like(img_l)
        same = cls[:, mir] == cls[:, x0:x1 + 1]
        g[:, x0:x1 + 1] = hp[:, mir] * same[..., None]
        out[hole] = np.clip(out[hole] + g[hole], 0, 1)
    return out, dict(hole_px=int(hole.sum()), ring_px=int(ring.sum()), x=[int(x0), int(x1)], width=int(width))


def rowfill(a, hole, dark=None):
    """each row of `hole` linearly interpolated between the nearest pixels outside it on that row (the hall's front wall faces the camera,
    so a row is one depth: plaster, skirting and the wall-floor line stay straight)"""
    out = a.copy()
    H, W = hole.shape
    for y in np.nonzero(hole.any(1))[0]:
        row = hole[y]
        xs = np.nonzero(row)[0]
        # runs
        splits = np.nonzero(np.diff(xs) > 1)[0]
        for seg in np.split(xs, splits + 1):
            x0, x1 = seg[0] - 1, seg[-1] + 1
            if x0 < 0 or x1 >= W:
                v = a[y, x1] if x0 < 0 else a[y, x0]
                out[y, seg] = v
                continue
            va = np.median(a[y, max(0, x0 - 4):x0 + 1], 0)
            vb = np.median(a[y, x1:min(W, x1 + 5)], 0)
            if dark is not None and (dark[y, max(0, x0 - 4):x0 + 1].any() or dark[y, x1:min(W, x1 + 5)].any()):
                v = vb if dark[y, max(0, x0 - 4):x0 + 1].any() and not dark[y, x1:min(W, x1 + 5)].any() else va
                out[y, seg] = v                       # an anchor on walnut or a shadow gap: the other one only
                continue
            t = (seg - x0) / (x1 - x0)
            out[y, seg] = va[None] * (1 - t)[:, None] + vb[None] * t[:, None]
    return out


def console_ck(l, idx, P, ok, nz):
    """r2 drew a low bench where the fixed console stands (FB21 2: the code replaces it when the shape moved). The console is drawn from
    the clay: its exact silhouette (pass index 741) and Cycles shading, in walnut at HDx2's level (drums ~L* 19-22 as hdx2-lock), with the
    wood grain of r1's console (its high-pass, by the bbox affine); its contact shadows are the clay's (the clay over the clay with the
    console interpolated out, darker only). The bench is removed by row interpolation (a frontal wall)."""
    clay_l = C.lin(C.rgb(os.path.join(C.CLAY, "CK.png")))
    cm = idx == 741
    ys, xs = np.nonzero(cm)
    bc = [xs.min(), xs.max() + 1, ys.min(), ys.max() + 1]
    # 1. the bench out
    L2 = C.lab(l)
    zone = np.zeros(l.shape[:2], bool)
    zone[900:1046, 1360:1592] = True
    bench = zone & (L2[..., 0] < 40) & (L2[..., 2] > 4)
    bench = cv2.dilate(bench.astype(np.uint8), np.ones((13, 13), np.uint8)).astype(bool) & zone
    hole = bench | cv2.dilate(cm.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    l2 = rowfill(l, hole, dark=C.lab(l)[..., 0] < 45)
    sm = cv2.GaussianBlur(l2, (0, 0), sigmaX=0.1, sigmaY=1.5)        # residual row noise out, inside the hole only
    l2 = np.where(hole[..., None], sm, l2)
    # 2. the clay's contact shadow
    big = cv2.dilate(cm.astype(np.uint8), np.ones((51, 51), np.uint8)).astype(bool)
    big[:bc[2] + 10] = False                                        # below the console's top only
    big[:, :bc[0] - 30] = False
    big[:, bc[1] + 30:] = False
    clay_un = rowfill(clay_l, big | cm, dark=C.lab(clay_l)[..., 0] < 30)
    ring = big & ~cv2.dilate(cm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    ratio = np.ones(cm.shape, np.float32)
    ratio[ring] = np.clip(Y_of(clay_l[ring]) / np.maximum(Y_of(clay_un[ring]), 1e-4), 0.35, 1.0)
    ratio = cv2.GaussianBlur(ratio, (0, 0), 1.2) ** 0.4
    l2 = l2 * ratio[..., None]
    # 3. the console: clay shading -> walnut
    yc = Y_of(clay_l)
    drums = cm & (np.arange(cm.shape[0])[:, None] > bc[2] + 0.12 * (bc[3] - bc[2]))
    g = L_to_Y(21.0) / np.median(yc[drums])
    Lc = C.lab(np.repeat((yc * g)[..., None], 3, -1))[..., 0]
    # grain: r1's console high-pass in L*, mapped bbox to bbox
    r1 = C.lin(C.rgb(R1_CK))
    L1 = C.lab(r1)[..., 0]
    m1 = np.zeros(cm.shape, bool)
    sub = (slice(850, 1015), slice(1395, 1580))
    m1[sub] = (L1[sub] < 46) & (C.lab(r1[sub])[..., 2] > 8)
    m1 = cv2.morphologyEx(m1.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m1.astype(np.uint8))
    m1 = lab == (1 + int(np.argmax(st[1:, 4])))
    y1s, x1s = np.nonzero(m1)
    b1 = [x1s.min(), x1s.max() + 1, y1s.min(), y1s.max() + 1]
    sx, sy = (bc[1] - bc[0]) / (b1[1] - b1[0]), (bc[3] - bc[2]) / (b1[3] - b1[2])
    A = np.float32([[sx, 0, bc[0] - sx * b1[0]], [0, sy, bc[2] - sy * b1[2]]])
    hp = (L1 - cv2.GaussianBlur(L1, (0, 0), 2.5)) * m1
    hpw = cv2.warpAffine(hp.astype(np.float32), A, (cm.shape[1], cm.shape[0]), flags=cv2.INTER_LINEAR)
    Lc = Lc + np.clip(hpw, -6, 6)
    lab_c = np.stack([Lc, Lc * 10.57 / 31.32, Lc * 16.63 / 31.32], -1)     # HC's walnut chroma per L*
    col = np.clip(lab_to_lin(lab_c), 0, 1)
    a = cv2.GaussianBlur(cm.astype(np.float32), (0, 0), 0.6)[..., None]
    a = np.where(cm[..., None], np.maximum(a, 0.5), a)
    out = l2 * (1 - a) + col * a
    rec = dict(method="clay silhouette and shading (pass 741), walnut at HDx2's drum level, r1's grain; clay contact shadow; bench out by row "
                      "interpolation", clay_bbox=[int(v) for v in bc], r1_bbox=[int(v) for v in b1], gain=round(float(g), 3), bench_px=int(bench.sum()),
               console_px=int(cm.sum()), shadow_min=round(float(ratio.min()), 3))
    return out, rec


def regions(name, P, ok, G, mask):
    X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
    hall = ok & (Y < 9.80) & (Y > 6.0) & ~mask
    bed = ok & (Y > 17.53) & ~mask
    if name == "CM":                         # only what the camera sees through the bedroom door (X 2.00-2.90, head 2.40 at Y 17.51)
        Cc = np.array(C.CAMS["CM"].loc)
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (17.51 - Cc[1]) / (Y - Cc[1])
            Xc = Cc[0] + t * (X - Cc[0])
            Zc = Cc[2] + t * (P[..., 2] - Cc[2])
        bed &= (Xc > 1.99) & (Xc < 2.91) & (Zc < 2.41)
    corr = ok & ~hall & ~bed & ~mask
    # world-Y blend weights on the floor across the thresholds (0.6 m)
    w_hall = np.where(hall, 1.0, 0.0)
    w_bed = np.where(bed, 1.0, 0.0)
    fl = ok & (Z < 0.004) & ~mask
    t = np.clip((10.10 - Y) / 0.6, 0, 1)
    w_hall = np.where(fl & (Y < 10.10) & (Y > 9.50), t, w_hall)
    t2 = np.clip((Y - 17.36) / 0.3, 0, 1)
    w_bed = np.where(fl & (Y > 17.36) & (Y < 17.66), t2, w_bed)
    return corr, hall, bed, w_hall, w_bed


def stops_vs_hc(l, G, P, T, fbm):
    Z = P[..., 2]
    out = {}
    for k in ("slot_wall", "opp_wall"):
        m = C.erode(G[k], 6) & (Z > 0.8) & (Z < 1.6) & fbm
        if m.sum() > 200:
            out[k] = float(np.log2(np.median(Y_of(l[m])) / T[k]["mid_Y_median"]))
    return out


CM_ROWS = [(0, 170), (105, 231), (140, 264), (338, 406), (369, 438), (1047, 1048), (1529, 1529)]
# (output row = the clay's, r2 row): the bedroom door's head lining top and bottom, the bedroom cornice's two lines, the bedroom floor line
# (measured on the vertical luminance profile at x 1300-1500 of the input and of r2); row 0 takes r2's end wall just under r2's ceiling
# line (~165): r2 drew the bedroom door 23 cm low and a corridor ceiling and slot the clay does not see (FB21 3, rejection 8)


def vertical_fix(l, pts=CM_ROWS, sigma=12.0):
    """r2's rows remapped onto the clay's: a monotone piecewise-linear map through the matched lines, Gaussian-smoothed (sigma 12 rows),
    the same for every column (vertical lines stay where they are; x is untouched)"""
    H, W = l.shape[:2]
    o = np.array([p[0] for p in pts], float)
    r = np.array([p[1] for p in pts], float)
    f = np.interp(np.arange(H), o, r)
    k = int(4 * sigma)
    pad = np.concatenate([np.full(k, f[0] - (f[1] - f[0]) * np.arange(k, 0, -1)), f, np.full(k, f[-1])])
    g = np.exp(-0.5 * (np.arange(-k, k + 1) / sigma) ** 2)
    fs = np.convolve(pad, g / g.sum(), mode="valid")
    fs = np.maximum.accumulate(fs)
    mx = np.tile(np.arange(W, dtype=np.float32), (H, 1))
    my = np.tile(fs.astype(np.float32)[:, None], (1, W))
    out = cv2.remap(l.astype(np.float32), mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    resid = {int(a): round(float(fs[int(a)] - b), 2) for a, b in pts}
    return np.clip(out, 0, 1), dict(control_rows_out_to_r2=pts, sigma_rows=sigma, residual_at_controls=resid)


def main(name):
    T = json.load(open(os.path.join(HERE, "hc-transfer.json")))
    img, d, P, ok = C.clay(name)
    idx = np.load(C.PASSES.format(name))["idx"]
    nz = np.load(C.PASSES.format(name))["normal"][..., 2] / 127.0
    G = C.groups(P, ok, img, idx)
    X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
    inp_l = C.lin(C.rgb(os.path.join(C.OUT, "inputs", f"{name}-input.png")))
    l = C.lin(C.rgb(RAW[name]))
    z = np.load(os.path.join(C.SRC, f"refeed-{name}.npz"))
    fill, mask = z["fill"] / 255.0, z["mask"]
    x0, y0, x1, y1 = (int(round(v)) for v in C.CV.box)
    fbm = np.zeros(mask.shape, bool)
    fbm[y0:y1, x0:x1] = True
    rec = dict(still=name, raw=os.path.basename(RAW[name]), lock=C.lock(name, C.rgb(os.path.join(C.OUT, "inputs", f"{name}-input.png")), C.rgb(RAW[name])))
    if name == "CM":
        l, rec["vertical_fix"] = vertical_fix(l)
    if name == "CK":
        l, rec["console"] = console_ck(l, idx, P, ok, nz)
        band = np.zeros(mask.shape, bool)
        band[0:1530, 648:792] = True
        band &= ok & (np.abs(X - 1.70) < 0.02) & ~mask                       # the left wall's plaster, skirting and nothing else
        cls = np.where(nz > 0.7, 0, np.where(Z < 0.16, 1, 2))
        l, rec["band"] = patch(l, inp_l, band, cls)
    # 3. levels by region
    corr, hall, bed, w_hall, w_bed = regions(name, P, ok, G, mask)
    s = stops_vs_hc(l, G, P, T, fbm)
    g_corr = 2 ** (-np.mean(list(s.values())))
    gain = np.full(mask.shape, g_corr)
    rec["levels"] = dict(walls_stops_vs_HC_before=s, corridor_gain_stops=round(float(np.log2(g_corr)), 3))
    if name == "CK":
        fw = ok & (np.abs(Y - 6.35) < 0.03) & (Z > 0.9) & (Z < 1.6) & ~mask & (idx != 741)
        g_hall = L_to_Y(HDX2_FRONT_WALL_L) / np.median(Y_of(l[fw]))
        hw = (hall & (Z >= 0.004)).astype(np.float32)                 # the hall's walls, ceiling and console; its floor stays with the oak
        hw = cv2.GaussianBlur(hw, (0, 0), 0.7)
        gain = gain * (1 - hw) + g_hall * hw
        rec["levels"]["hall_front_wall_L_before"] = round(float(np.median(C.lab(l[fw])[..., 0])), 2)
        rec["levels"]["hall_gain_stops"] = round(float(np.log2(g_hall)), 3)
    lo = l.copy()
    set_Y(lo, ok & ~mask, gain)
    if name == "CM":
        bw = bed & (np.abs(Y - 21.66) < 0.03) & (Z > 0.5) & (Z < 2.0)
        if bw.sum() < 500:
            bw = bed & (nz < 0.5) & (nz > -0.5)
        target = L_to_Y(HC_BEDROOM_L)
        lo_b = l * g_corr
        yb = np.median(Y_of(lo_b[bw]))
        g_bed = 1.0
        for _ in range(30):                      # the gain whose shouldered median lands on the target
            yy = shoulder(Y_of(lo_b[bw]) * g_bed)
            g_bed *= (target / max(np.median(yy), 1e-5)) ** 0.8
        yall = Y_of(lo_b)
        ynew = shoulder(yall * g_bed)
        ratio = np.where(yall > 1e-5, ynew / np.maximum(yall, 1e-5), g_bed)
        wb = cv2.GaussianBlur(w_bed.astype(np.float32), (0, 0), 0.8)
        r_eff = 1 + (ratio - 1) * wb
        m = ok & ~mask & (wb > 0)
        lo[m] = lo_b[m] * r_eff[m][:, None]
        rec["levels"]["bedroom_back_wall_L_before"] = round(float(C.lab(np.array([[[yb] * 3]]))[0, 0, 0]), 2)
        rec["levels"]["bedroom_gain_stops"] = round(float(np.log2(g_bed)), 3)
    # every highlight of the model part under the same soft shoulder (nothing at 255 outside the refed rooms)
    yl = lo.max(-1)                                                  # on the largest channel, so a warm white cannot clip in red
    sh = np.where(yl > 1e-5, shoulder(yl, 0.70, 0.965) / np.maximum(yl, 1e-5), 1.0)
    mm = ok & ~mask
    lo[mm] = lo[mm] * sh[mm][:, None]
    l = np.clip(lo, 0, 1)
    # 4. the oak to HC's oak (CK: L* and chroma on the corridor floor; CM sees only the 0.27 m before the door, inside the warm spill,
    #    and the bedroom's floor: a* to HC's, b* at most HC's + 3, the spill allowance of FB21 1)
    fl = ok & (Z < 0.004) & ~mask & ~np.isin(idx, C.WALNUT_PIDX)
    flc = fl & (X > 1.7) & (X < 3.1) & (Y > 9.8) & (Y < 17.5) & fbm
    ref = flc if name == "CK" else (fl & fbm)
    Lb = C.lab(l)
    med = np.median(Lb[ref], 0)
    tgt = np.array(T["floor"]["hc_lab_median"], float)
    gL = L_to_Y(tgt[0]) / L_to_Y(med[0]) if name == "CK" else 1.0
    tb = tgt[2] if name == "CK" else min(med[2], tgt[2] + 3.0)
    lf = l[fl] * gL
    lab_f = C.lab(lf)
    lab_f[:, 1] *= tgt[1] / med[1]
    lab_f[:, 2] *= tb / med[2]
    l[fl] = np.clip(lab_to_lin(lab_f), 0, 1)
    rec["oak"] = dict(measured_on="corridor floor" if name == "CK" else "every visible floor", before=[round(float(v), 2) for v in med],
                      target=[round(float(tgt[0]), 2) if name == "CK" else "kept", round(float(tgt[1]), 2), round(float(tb), 2)],
                      L_gain_stops=round(float(np.log2(gL)), 3), a_scale=round(float(tgt[1] / med[1]), 3), b_scale=round(float(tb / med[2]), 3))
    # CM: the spill at the bedroom door on the corridor's oak (the 0.27 m in view before the door and the threshold) at most +1/3 stop
    #     over HC's corridor oak (FB21 1): a smooth cap on the low-passed luminance, the planks' texture kept
    if name == "CM":
        sp = ok & (Z < 0.004) & (Y > 16.5) & (Y < 17.70) & ~mask
        capY = L_to_Y(T["floor"]["hc_lab_median"][0]) * 2 ** (1 / 3)
        yl = Y_of(l)
        lp = cv2.GaussianBlur(np.where(sp, yl, 0).astype(np.float32), (0, 0), 6) / np.maximum(
            cv2.GaussianBlur(sp.astype(np.float32), (0, 0), 6), 1e-4)
        gcap = np.where(sp, np.minimum(1.0, capY / np.maximum(lp, 1e-5)), 1.0).astype(np.float32)
        gcap = cv2.GaussianBlur(gcap, (0, 0), 2)
        before = float(np.percentile(C.lab(l[sp])[..., 0], 95))
        l[sp] = l[sp] * gcap[sp][:, None]
        rec["spill_cap"] = dict(px=int(sp.sum()), cap_L=round(float(C.lab(np.array([[[capY] * 3]]))[0, 0, 0]), 2), p95_L_before=round(before, 2),
                                p95_L_after=round(float(np.percentile(C.lab(l[sp])[..., 0], 95)), 2))
    # the walls' colour to HC's same wall (and CK's hall wall to HDx2's): additive a*, b* per plane, plaster and skirting
    shifts = {}
    planes = dict(slot_wall=ok & (np.abs(X - 1.70) < 0.02) & (Z >= 0.004) & (Z < 2.70) & ~mask & ~np.isin(idx, C.WALNUT_PIDX),
                  opp_wall=ok & (np.abs(X - 3.10) < 0.02) & (Z >= 0.004) & (Z < 2.70) & ~mask & ~np.isin(idx, C.WALNUT_PIDX))
    tg = dict(slot_wall=T["slot_wall"]["hc_lab_median"], opp_wall=T["opp_wall"]["hc_lab_median"])
    if name == "CK":
        planes["hall_walls"] = ok & (Y < 9.80) & (Y > 6.0) & (Z >= 0.004) & ~mask & ~np.isin(idx, C.WALNUT_PIDX) & (nz < 0.5) & (nz > -0.5)
        tg["hall_walls"] = [HDX2_FRONT_WALL_L, 1.98, 8.19]
    Lb = C.lab(l)
    for k, m in planes.items():
        mm = C.erode(m, 4) & (Z > 0.8) & (Z < 1.6) & fbm if k != "hall_walls" else C.erode(m, 4) & fbm
        if mm.sum() < 300:
            continue
        md = np.median(Lb[mm], 0)
        da, db = tg[k][1] - md[1], tg[k][2] - md[2]
        lb_ = Lb[m]
        lb_[:, 1] += da
        lb_[:, 2] += db
        l[m] = np.clip(lab_to_lin(lb_), 0, 1)
        shifts[k] = dict(before=[round(float(v), 2) for v in md], d_a=round(float(da), 2), d_b=round(float(db), 2))
    rec["wall_colour"] = shifts
    # the floor edge pixels next to the skirting carry both: one px feather of the floor mask
    out = C.srgb(l)
    # 5. refeed, slot
    if mask.any():
        a = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 1.2)[..., None]
        a = np.where(mask[..., None], np.maximum(a, 0.5), a)
        out = out * (1 - a) + fill * a
    slot_any = (G["slot"] | (ok & (X < 2.05) & (X > 1.65) & (Z > 2.69))) & ok
    sl = cv2.dilate(slot_any.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    if sl.any():
        mx = out.max(-1)
        k0 = 0.90
        new = np.where(mx > k0, k0 + (0.975 - k0) * np.tanh((mx - k0) / (0.975 - k0)), mx)
        sc = np.where(mx > 1e-4, new / np.maximum(mx, 1e-4), 1)
        out[sl] = out[sl] * sc[sl][:, None]
        # the slot white-warm as HC's (b* 1.2), never blue (FB21 1)
        core = slot_any & fbm
        if core.sum() > 50:
            lb_ = C.lab(C.lin(out[sl]))
            db = T["slot"]["hc_lab_median"][2] - float(np.median(C.lab(C.lin(out[core]))[..., 2]))
            if db > 0:
                lb_[:, 2] += db
                out[sl] = np.clip(C.srgb(np.clip(lab_to_lin(lb_), 0, 1)), 0, 1)
            rec["slot_b_shift"] = round(db, 2) if db > 0 else "none needed (the well's median b* is above HC's slot)"
    # 6a. the walnut at least 8 L* over the black point (FB21 1): tone.py's curve shape with a 45 knee, on the clay's walnut only
    wm = np.isin(idx, C.WALNUT_PIDX) & ok & ~mask
    wf = cv2.GaussianBlur(wm.astype(np.float32), (0, 0), 0.7)
    lb = C.lab(C.lin(out))
    model = fbm & ~mask
    p05 = 12.0                                # the house black point (WM-G1 / FB16: L* 11-12) + 9
    core = C.erode(wm, 2) & fbm
    target = p05 + 9.0
    Aw = 0.0
    def lift(Lv, Av):                         # a bump: 0 at black and at the knee, A at L* 22.5 (the deepest gaps keep the black point)
        x = np.clip(Lv / 45.0, 0, 1)
        return Lv + Av * 4 * x * (1 - x)
    if np.median(lb[..., 0][core]) < target:
        lo_, hi_ = 0.0, 30.0
        for _ in range(40):
            Aw = (lo_ + hi_) / 2
            if np.median(lift(lb[..., 0][core], Aw)) < target:
                lo_ = Aw
            else:
                hi_ = Aw
        Aw = (lo_ + hi_) / 2
        m = wf > 0
        L0 = lb[..., 0][m]
        d = (lift(L0, Aw) - L0) * wf[m]
        nb = lb[m].copy()
        nb[:, 0] += d
        nb[:, 1] += d * 5.1 / 14.4
        nb[:, 2] += d * 6.4 / 14.4
        out[m] = np.clip(C.srgb(np.clip(lab_to_lin(nb), 0, 1)), 0, 1)
    rec["walnut_lift"] = dict(A=round(float(Aw), 2), curve="L + A*4x(1-x), x = L/45", target_median=round(target, 2))
    # 6. toe on the model part
    sys.path.insert(0, os.path.join(C.HCDIR, "tools"))
    import tone as TN  # noqa: E402
    model = fbm & ~mask
    Lm = C.lab(C.lin(out))[..., 0]
    p01 = float(np.percentile(Lm[model], 0.1))
    A = 0.0
    if p01 < 11.0:
        lo_, hi_ = 0.0, 14.9
        for _ in range(40):
            A = (lo_ + hi_) / 2
            if float(np.percentile(TN.f(Lm[model], A), 0.1)) < 11.8:
                lo_ = A
            else:
                hi_ = A
        A = round((lo_ + hi_) / 2, 2)
        out, _ = TN.apply(out, A, mask=~mask)
    out = np.clip(out, 0, 1)
    rec["toe"] = dict(A=A, model_p01_before=round(p01, 2))
    # checks
    lo = C.lin(out)
    Lo = C.lab(lo)
    Lf = Lo[..., 0]
    ch = dict(frame_p01=round(float(np.percentile(Lf[fbm], 0.1)), 2), frame_p05=round(float(np.percentile(Lf[fbm], 0.5)), 2),
              model_part_p01=round(float(np.percentile(Lf[model], 0.1)), 2), model_part_p05=round(float(np.percentile(Lf[model], 0.5)), 2))
    ch["walls_mid_stops_vs_HC"] = {k: round(v, 3) for k, v in stops_vs_hc(lo, G, P, T, fbm).items()}
    ch["walls_within_1_6"] = all(abs(v) <= 1 / 6 for v in ch["walls_mid_stops_vs_HC"].values())
    for k in ("slot_wall", "opp_wall"):
        m = C.erode(G[k], 6) & (Z > 0.8) & (Z < 1.6) & fbm
        if m.sum() > 200:
            ch[f"{k}_lab"] = [round(float(v), 2) for v in np.median(Lo[m], 0)]
            ch[f"{k}_lab_HC"] = T[k]["hc_lab_median"]
    flc2 = flc & ~mask
    ch["corridor_oak_lab"] = [round(float(v), 2) for v in np.median(Lo[flc2], 0)]
    ch["corridor_oak_lab_HC"] = T["floor"]["hc_lab_median"]
    wn = C.erode(G["walnut"], 2) & fbm & ~mask
    ch["walnut_L"] = round(float(np.median(Lf[wn])), 2)
    ch["walnut_over_black_p05"] = round(ch["walnut_L"] - ch["frame_p05"], 2)
    med = {}
    for k in ("slot_wall", "opp_wall", "floor", "ceiling", "end_wall", "bedroom", "hall", "living", "boy", "bath", "girl"):
        m = C.erode(G[k], 3) & fbm
        if m.sum() > 300:
            med[k] = round(float(np.median(Lf[m])), 2)
    ch["L_median_by_surface"] = med
    mid = {}
    for k in ("slot_wall", "opp_wall", "end_wall", "hall", "girl", "boy", "bath"):
        m = C.erode(G[k], 3) & fbm & (Z > 0.5) & (Z < 2.0)
        if m.sum() > 300:
            mid[k] = round(float(np.median(Lf[m])), 2)
    ch["L_median_mid_height"] = mid
    if name == "CK":
        fw = ok & (np.abs(Y - 6.35) < 0.03) & (Z > 0.9) & (Z < 1.6) & ~mask & (idx != 741) & fbm
        ch["hall_front_wall_lab"] = [round(float(v), 2) for v in np.median(Lo[fw], 0)]
        lw = G["living"] & (Y < 0.05) & fbm
        ch["living_back_wall_L_median"] = round(float(np.median(Lf[lw])), 2) if lw.sum() > 50 else None
        ch["living_back_wall_L_p90"] = round(float(np.percentile(Lf[lw], 90)), 2) if lw.sum() > 50 else None
        end_val = ch["living_back_wall_L_median"]
        others = {k: v for k, v in mid.items() if k not in ("living",)}
    else:
        bw = G["bedroom"] & (np.abs(Y - 21.66) < 0.03) & (Z > 0.5) & (Z < 2.0) & fbm
        ch["bedroom_back_wall_L_median"] = round(float(np.median(Lf[bw])), 2)
        end_val = ch["bedroom_back_wall_L_median"]
        others = {k: v for k, v in mid.items() if k not in ("bedroom",)}
    ch["end_brightest_by_median"] = dict(end=end_val, max_other=max(others.values()), ok=bool(end_val >= max(others.values())))
    ch["ch255_pct_of_frame"] = round(100 * float(((out * 255).round().max(-1)[fbm] >= 255).mean()), 4)
    if (G["slot"] & fbm).sum():
        ch["slot_lab_median"] = [round(float(v), 2) for v in np.median(Lo[G["slot"] & fbm], 0)]
    rec["checks"] = ch
    C.save(os.path.join(C.OUT, f"{name}.png"), out)
    C.save(os.path.join(C.OUT, f"{name}-frame.png"), C.CV.crop_frame(out.astype(np.float32), 1920, 1080))
    json.dump(rec, open(os.path.join(HERE, f"{name}-checks.json"), "w"), indent=1, default=float)
    print(json.dumps(rec, indent=1, default=float))


def lab_to_lin(lb):
    fy = (lb[..., 0] + 16) / 116
    fx = fy + lb[..., 1] / 500
    fz = fy - lb[..., 2] / 200
    def inv(f):
        return np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27))
    xyz = np.stack([inv(fx), inv(fy), inv(fz)], -1) * C._WP
    return xyz @ np.linalg.inv(C._M).T


if __name__ == "__main__":
    main(sys.argv[1])
