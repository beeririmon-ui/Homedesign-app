"""FB16 house light pass (render-agent, 2026-11-26): L0 over the whole stack, in code, 0 tokens.
(a) the outside replaced in the plate (west / north plates, each window its own perspective crop), (b) window glow, (c) one house grade
(per-channel LUT to the spec's targets), (d) lamp glow. Never redraws a product. Usage: python3.12 -I -B fb16.py W0 [--no-test]"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common16 import *
from geom16 import *
import pasted_test as P
REPO = "/home/user/homedesign-app"
DATE = "2026-11-26"
BRIEF = "briefs/wm-fb16-house-light-pass-2026-11-26.md"
SPEC = "docs/proposals/wm-fb16-house-light-2026-11-26.md"
ODIR = f"{REPO}/assets/renders/outside/warm-modern/fb16-2026-11-26"
PLATES = {"west": dict(file="outside-west-fb16.jpg", yh=0.72, fp=1100.0, Lt=93.5, Lr=(90, 97), bt=13.5, br=(10, 18), amax=5.0),
          "north": dict(file="outside-north-fb16.jpg", yh=0.62, fp=1100.0, Lt=89.0, Lr=(85, 93), bt=5.0, br=(2, 8), amax=4.0)}
WARM = np.array([1.0, 0.87, 0.70])
BLACK_T = 11.5


def lab2rgb(L, a, b):
    x = np.array([[[L, a, b]]], np.float32)
    return np.clip(cv2.cvtColor(x, cv2.COLOR_LAB2RGB)[0, 0] * 255.0, 0, 255).astype(np.float64)


def pchip(xk, yk, x):
    xk, yk = np.asarray(xk, float), np.asarray(yk, float)
    h = np.diff(xk); d = np.diff(yk) / h
    m = np.zeros_like(yk); m[0], m[-1] = d[0], d[-1]
    for i in range(1, len(xk) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    i = np.clip(np.searchsorted(xk, x, side="right") - 1, 0, len(h) - 1)
    t = (x - xk[i]) / h[i]
    return ((2 * t**3 - 3 * t**2 + 1) * yk[i] + (t**3 - 2 * t**2 + t) * h[i] * m[i] + (-2 * t**3 + 3 * t**2) * yk[i + 1] + (t**3 - t**2) * h[i] * m[i + 1])


HI_L = (97.0, 96.0)


def grade_params(kin, kout, pin, pout, da, db):
    return dict(space="CIELAB (D65, sRGB 8-bit in and out)", L_knots_in=[0.0, round(kin, 3), round(pin, 3), HI_L[0], 100.0],
                L_knots_out=[0.0, round(kout, 3), round(pout, 3), HI_L[1], 100.0], L_interp="monotone cubic (Fritsch-Carlson)",
                ab="a' = a * (L'+16)/(L+16) + da * w(L'),  b' = b * (L'+16)/(L+16) + db * w(L');  w = smoothstep(15, 30, L') * (1 - smoothstep(92, 99, L'))",
                da=round(da, 3), db=round(db, 3))


def _Lcurve(gp, L):
    return pchip(gp["L_knots_in"], gp["L_knots_out"], np.clip(L, 0, 100))


def _w(L):
    sm = lambda e0, e1, x: np.clip((x - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((x - e0) / (e1 - e0), 0, 1))  # noqa
    return sm(15, 30, L) * (1 - sm(92, 99, L))


def apply_grade(img8, gp):
    Lb = lab(img8)
    L = Lb[..., 0].astype(np.float64)
    L2 = _Lcurve(gp, L)
    sc = (L2 + 16) / (L + 16); w = _w(L2)
    Lb[..., 0] = L2
    Lb[..., 1] = Lb[..., 1] * sc + gp["da"] * w
    Lb[..., 2] = Lb[..., 2] * sc + gp["db"] * w
    o = cv2.cvtColor(Lb.astype(np.float32), cv2.COLOR_LAB2RGB) * 255.0
    return np.clip(np.rint(o), 0, 255).astype(np.uint8)


def inv_grade(rgbf, gp):
    Lb = lab(np.clip(np.rint(rgbf), 0, 255).astype(np.uint8))
    L2 = Lb[..., 0].astype(np.float64)
    xs = np.linspace(0, 100, 4001); ys = _Lcurve(gp, xs); ys = np.maximum.accumulate(ys) + np.arange(len(xs)) * 1e-7
    L = np.interp(L2, ys, xs)
    sc = (L2 + 16) / (L + 16); w = _w(L2)
    Lb[..., 0] = L
    Lb[..., 1] = (Lb[..., 1] - gp["da"] * w) / sc
    Lb[..., 2] = (Lb[..., 2] - gp["db"] * w) / sc
    o = cv2.cvtColor(Lb.astype(np.float32), cv2.COLOR_LAB2RGB) * 255.0
    return np.clip(o, 0, 255)


def screen(img8, s):
    o = 255.0 - (255.0 - img8.astype(np.float64)) * (1.0 - s)
    return np.clip(np.rint(o), 0, 255).astype(np.uint8)


def fit_grade(img, pm, fm, t, black_t=BLACK_T):
    Lb = lab(img)
    kin = float(np.percentile(Lb[..., 0][fm], 0.5))
    pin = float(np.median(Lb[..., 0][pm]))
    kout, pout, da, db = black_t, t["L"], 0.0, 0.0
    a0, b0 = float(np.median(Lb[..., 1][pm])), float(np.median(Lb[..., 2][pm]))
    sc = (t["L"] + 16) / (pin + 16)
    da, db = t["a"] - a0 * sc, t["b"] - b0 * sc
    for it in range(8):
        gp = grade_params(kin, kout, pin, pout, da, db)
        m = measure(apply_grade(img, gp), pm, fm)
        eL, ea, eb, ek = t["L"] - m["plaster"][0], t["a"] - m["plaster"][1], t["b"] - m["plaster"][2], black_t - m["black_p05"]
        if max(abs(eL), abs(ea), abs(eb), abs(ek)) < 0.12:
            break
        pout, da, db, kout = pout + eL, da + ea, db + eb, kout + ek
    gp["fit"] = dict(iterations=it + 1, plaster_in_lab=[round(pin, 2), round(a0, 2), round(b0, 2)], black_in_p05=round(kin, 2), measured=m)
    return gp, gp["fit"]


def window_plane(cfg, cam, Z, ids, leg):
    wid = cfg.get("window_wall_ids") or [k for k, v in leg.items() if v.lower().startswith("plaster") and "window" in v.lower()]
    m = np.isin(ids, wid) & (Z > 0)
    ys, xs = np.nonzero(m)
    sel = np.random.default_rng(7).choice(len(xs), min(30000, len(xs)), replace=False)
    ys, xs = ys[sel], xs[sel]; z = Z[ys, xs]
    Pp = np.stack([(xs + .5 - cam["cx"]) / cam["f"] * z, -(ys + .5 - cam["cy_top"]) / cam["f"] * z, z], 1)
    c = Pp.mean(0); _, _, vt = np.linalg.svd(Pp - c, full_matrices=False); n = vt[2]
    if n @ (-c) < 0:
        n = -n
    return n, float(n @ c), dict(window_wall_ids=wid, normal_in=[round(float(v), 4) for v in n], rms_m=round(float(np.sqrt(np.mean(((Pp - c) @ n) ** 2))), 4))


def outside_alpha(ids, leg, base, oid=None, fid=None):
    oid = oid or [k for k, v in leg.items() if ("sky" in v.lower() or "outside" in v.lower())]
    fid = fid or [k for k, v in leg.items() if "window frame" in v.lower()]
    m = np.isin(ids, oid).astype(np.uint8)
    core = cv2.erode(m, np.ones((5, 5), np.uint8)) > 0
    band = (cv2.dilate(m, np.ones((7, 7), np.uint8)) > 0) & ~core
    nf = cv2.dilate(np.isin(ids, fid).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    Lb = lab(base)[..., 0]
    Lo, Lf = float(np.median(Lb[core])), float(np.median(Lb[np.isin(ids, fid)]))
    soft = np.clip((Lb - Lf - 6) / max(Lo - Lf - 12, 5), 0, 1)
    al = core.astype(np.float64)
    sel = band & nf; al[sel] = soft[sel]
    sel = band & ~nf; al[sel] = m[sel]
    al = cv2.GaussianBlur(al, (0, 0), 0.6)
    al[al < 0.02] = 0
    return al, dict(outside_ids=oid, frame_ids=fid, L_old_outside=round(Lo, 1), L_frame=round(Lf, 1), px=int((al > 0.5).sum()))


def sample_outside(kind, cam, n_in, al, az_off):
    pc = PLATES[kind]
    PL = np.asarray(Image.open(os.path.join(ODIR, pc["file"])).convert("RGB")).astype(np.float32)
    Hp, Wp = PL.shape[:2]
    ys, xs = np.nonzero(al > 0)
    y0, y1, x0, x1 = ys.min() - 8, ys.max() + 9, xs.min() - 8, xs.max() + 9
    y0, x0 = max(0, y0), max(0, x0); y1, x1 = min(al.shape[0], y1), min(al.shape[1], x1)
    v, u = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    r = np.stack([(u + .5 - cam["cx"]) / cam["f"], -(v + .5 - cam["cy_top"]) / cam["f"], np.ones_like(u)], -1)
    no = -n_in; nh = np.array([no[0], 0.0, no[2]]); nh /= np.linalg.norm(nh)
    right = np.array([nh[2], 0.0, -nh[0]])
    rf, rr = r @ nh, r @ right
    az = np.arctan2(rr, rf); el = np.arctan2(r[..., 1], np.hypot(rr, rf))
    mx = (Wp / 2 + pc["fp"] * (az + np.radians(az_off))).astype(np.float32)
    my = (pc["yh"] * Hp - pc["fp"] * np.tan(el)).astype(np.float32)
    O = cv2.remap(PL, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    O = cv2.GaussianBlur(O, (0, 0), 1.8)
    out = np.zeros(al.shape + (3,), np.float32); out[y0:y1, x0:x1] = O
    rec = dict(plate=os.path.relpath(os.path.join(ODIR, pc["file"]), REPO), mapping="cylindrical about the window's outward normal",
               fp_px_per_rad=pc["fp"], horizon_row=round(pc["yh"] * Hp, 1), az_offset_deg=az_off,
               az_deg=[round(float(np.degrees(az[al[y0:y1, x0:x1] > 0]).min()), 1), round(float(np.degrees(az[al[y0:y1, x0:x1] > 0]).max()), 1)],
               dof_sigma_px=1.8)
    return np.clip(out, 0, 255), rec


def calibrate_outside(Opost, al, kind):
    """the view is several stops brighter than the room: lift it (hazy, airy, like M0-W's olive), sky p90 -> the spec's L, warm the light part"""
    pc = PLATES[kind]
    Lb = lab(np.clip(Opost, 0, 255).astype(np.uint8))
    m = al > 0.5
    L = Lb[..., 0]
    p10, p90 = [float(np.percentile(L[m], q)) for q in (10, 90)]
    lo = pc["Lt"] - 30.0
    k = (pc["Lt"] - lo) / max(p90 - p10, 1.0)
    Ln = np.clip(lo + (L - p10) * k, 0, 99.0)
    w = np.clip((Ln - 70) / 20, 0, 1)
    sky = m & (Ln >= np.percentile(Ln[m], 70))
    as_, bs = float(np.median(Lb[..., 1][sky])), float(np.median(Lb[..., 2][sky]))
    Lb[..., 0] = Ln
    Lb[..., 1] = Lb[..., 1] * (1 - 0.35 * (1 - w)) + min(0.0, pc["amax"] - 1.0 - as_) * w
    Lb[..., 2] = Lb[..., 2] * (1 - 0.35 * (1 - w)) + (pc["bt"] - bs) * w
    o = cv2.cvtColor(Lb.astype(np.float32), cv2.COLOR_LAB2RGB) * 255.0
    return np.clip(o, 0, 255), dict(L_p10_p90_before=[round(p10, 1), round(p90, 1)], L_p10_p90_after=[round(lo, 1), pc["Lt"]], sky_ab_before=[round(as_, 1), round(bs, 1)],
                                    target_L=pc["Lt"], target_b=pc["bt"], note="lift: the view reads several stops over the room; dark canopy to about L lo, the sky to the spec")


def window_glow(cam, Z, al, n_in, d, H, W, s=4):
    Zs = Z[::s, ::s]
    Pp = backproject(Z, cam["f"], cam["cx"], cam["cy_top"], s)
    ys, xs = np.nonzero(al > 0.5)
    sel = np.random.default_rng(3).choice(len(xs), min(500, len(xs)), replace=False)
    r = np.stack([(xs[sel] + .5 - cam["cx"]) / cam["f"], -(ys[sel] + .5 - cam["cy_top"]) / cam["f"], np.ones(len(sel))], 1)
    t = d / (r @ n_in); S = r * t[:, None]; S = S[t > 0]

    def irr(Q):
        E = np.zeros(Q.shape[:-1]); dmin = np.full(Q.shape[:-1], np.inf)
        for i in range(0, len(S), 50):
            D = Q[..., None, :] - S[i:i + 50]
            d2 = (D ** 2).sum(-1)
            cs = np.clip((D @ n_in) / np.sqrt(d2 + 1e-9), 0, 1)
            E += (cs / (d2 + 0.04)).sum(-1)
            dmin = np.minimum(dmin, d2.min(-1))
        return E / len(S), np.sqrt(dmin)
    E, dmin = irr(Pp)
    Eref = irr((S.mean(0) + 1.0 * n_in)[None])[0][0]
    near = 1.0 / (1.0 + (dmin / 1.1) ** 4)
    g = np.clip(np.maximum(E / Eref, near), 0, 1.25)
    hole = (Zs <= 0) | (Zs > 12.9) | (al[::s, ::s] > 0)
    v = (~hole).astype(np.float64)
    gb = cv2.GaussianBlur(np.where(hole, 0, g), (0, 0), 6) / np.maximum(cv2.GaussianBlur(v, (0, 0), 6), 1e-6)
    g = np.where(hole, gb, g)   # inside the window the field continues from its edges: no step on a product standing in front of the glass
    g = cv2.resize(g.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    g = cv2.GaussianBlur(g, (0, 0), 25)
    return np.clip(g, 0, 1.25).astype(np.float64)


def glow_amp(p_rgb, dL, color=WARM):
    lo, hi = 0.0, 1.0
    L0 = lab(p_rgb.reshape(1, 1, 3).astype(np.uint8))[0, 0, 0]
    for _ in range(30):
        A = (lo + hi) / 2
        v = 255 - (255 - p_rgb) * (1 - A * color)
        if lab(np.clip(v, 0, 255).reshape(1, 1, 3).astype(np.uint8))[0, 0, 0] - L0 < dL:
            lo = A
        else:
            hi = A
    return (lo + hi) / 2


def lamp_restore(fin_pre, graded, a, Lpre, lo=84.0):
    """(d) on a lamp's own emitting pixels: the screen that gives back the pre-grade value (the lamp keeps its brightness: it is the source)"""
    w = (a.astype(np.float64) / 255.0) * np.clip((Lpre - lo) / 6, 0, 1)
    pre, post = fin_pre.astype(np.float64), graded.astype(np.float64)
    s = np.clip(1 - (255 - pre) / np.maximum(255 - post, 1), 0, 1) * w[..., None]
    return s


def sconce_glow(a, H, W, strength, color=np.array([1.0, 0.80, 0.55])):
    ys, xs = np.nonzero(a > 128)
    cy, cx = ys.mean(), xs.mean(); r = max(np.ptp(ys), np.ptp(xs)) / 2 + 1
    v, u = np.mgrid[0:H, 0:W]
    d2 = ((u - cx) ** 2 + ((v - cy) / 1.25) ** 2) / (3.2 * r) ** 2
    pool = np.exp(-d2) * strength
    body = cv2.GaussianBlur((a > 0).astype(np.float64) * (a / 255.0), (0, 0), 1.0) * 0.55
    s = np.clip(pool + body, 0, 0.9)
    return s[..., None] * color, dict(center=[round(float(cx), 1), round(float(cy), 1)], radius_px=round(float(r), 1))
