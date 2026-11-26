"""HT2 / HDx2: the living room through the opening, re-fed from M0-W (H-W based default frame) by forward warp on the clay depths (0 tokens)"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common16 import *
M0W = "/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25"
HALL = "/home/user/homedesign-app/assets/blockout/house/framing/wm-hall-2026-11-18"
LIVING = list(range(30, 44))


def axes(yaw):
    y = np.radians(yaw)
    return np.array([-np.sin(y), -np.cos(y)]), np.array([np.cos(y), -np.sin(y)])


def m0w_points():
    dj = json.load(open(f"{M0W}/m0w-depth.json")); cam = dj["camera"]
    img = np.asarray(Image.open(f"{M0W}/default-frame-m0w.png").convert("RGB"))
    enc = np.asarray(Image.open(f"{M0W}/m0w-depth.png")).astype(np.float64)
    fb = dj["frame_box"]; fbw, fbh = fb[2] - fb[0], fb[3] - fb[1]
    h, w = img.shape[:2]
    j, i = np.mgrid[0:h, 0:w].astype(np.float64)
    u, v = (i + .5) / w, (j + .5) / h
    cx = np.clip(np.rint(fb[0] + u * fbw - .5), 0, enc.shape[1] - 1).astype(int); cy = np.clip(np.rint(fb[1] + v * fbh - .5), 0, enc.shape[0] - 1).astype(int)
    e = enc[cy, cx]
    dn, df = dj["d_near_m"], dj["d_far_m"]
    d = np.where(e > 0, 1.0 / ((e - 1) / 65534.0 * (1 / dn - 1 / df) + 1 / df), 0.0)
    # a product pixel whose clay depth is the wall behind it (the render's silhouette is wider than the proxy) takes the depth of the nearest proxy pixel of the same product: no smear onto the wall
    mp = f"{M0W}/layers/manifest.json"; man = json.load(open(mp))
    rows = sorted([l_ for l_ in man["layers"] if l_.get("default") and l_.get("layer")], key=lambda l_: l_["z"])
    fixes = {}
    for l_ in rows:
        a = np.asarray(Image.open(F._resolve(os.path.dirname(mp), l_["layer"])).convert("RGBA"))[..., 3][cy, cx]
        m = (a > 100) & (d > 0)
        if m.sum() < 50:
            continue
        p80 = float(np.percentile(d[m], 80))
        fix = m & (d > p80 + 0.25)
        okm = m & ~fix
        if fix.any() and okm.any():
            _, lbl = cv2.distanceTransformWithLabels((~okm).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
            yy, xx = np.nonzero(okm)
            lut_ = np.zeros(lbl.max() + 1, np.int64); lut_[lbl[yy, xx]] = yy * d.shape[1] + xx
            src = lut_[lbl[fix]]
            d[fix] = d.ravel()[src]
        fixes[l_["slot"]] = int(fix.sum())
    m0w_points.fixes = fixes
    k = cam["lens"] / 36.0; asp = fbw / fbh
    f, r = axes(cam["yaw"]); C = np.array(cam["loc"])
    x = (u - cam["u0"]) * d / k
    Z = C[2] - (v - cam["v0"]) * d / (k * asp)
    X = C[0] + d * f[0] + x * r[0]; Y = C[1] + d * f[1] + x * r[1]
    return img, d, np.stack([X, Y, Z], -1), dict(cam=cam, fb=fb, u=u, v=v)


def project(P, cam, fb):
    f, r = axes(cam["yaw"]); C = np.array(cam["loc"])
    D = P[..., :2] - C[:2]
    d = D @ f; x = D @ r
    k = cam["lens"] / 36.0; fbw, fbh = fb[2] - fb[0], fb[3] - fb[1]
    u = cam["u0"] + k * x / np.maximum(d, 1e-6); v = cam["v0"] + k * (fbw / fbh) * (C[2] - P[..., 2]) / np.maximum(d, 1e-6)
    return fb[0] + u * fbw, fb[1] + v * fbh, d


def living_view(frame):
    meta = json.load(open(f"{HALL}/clay-meta.json"))["frames"][frame]
    cam = meta["camera"]; fb = meta["canvas"]["frame_box"]
    ids = np.asarray(Image.open(f"{HALL}/{frame}-id.png")); Zc = np.asarray(Image.open(f"{HALL}/{frame}-depth.png")).astype(np.float64) / 5000.0
    H, W = ids.shape
    src, d0, P, sm = m0w_points()
    ok = d0 > 0
    X, Y, dh = project(P, cam, fb)
    xi, yi = np.rint(X - .5).astype(int), np.rint(Y - .5).astype(int)
    ok &= (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H) & (dh > 0.3)
    xi, yi, dh2, cols = xi[ok], yi[ok], dh[ok], src[ok]
    live = np.isin(ids[yi, xi], LIVING) & (dh2 <= Zc[yi, xi] + 0.25)
    xi, yi, dh2, cols = xi[live], yi[live], dh2[live], cols[live]
    order = np.argsort(-dh2)
    zb = np.full((H, W), np.inf); V = np.zeros((H, W, 3), np.float64); cov = np.zeros((H, W), bool)
    V[yi[order], xi[order]] = cols[order]; zb[yi[order], xi[order]] = dh2[order]; cov[yi[order], xi[order]] = True
    region = np.isin(ids, LIVING)
    # the view out through the M0-W glazing: direction only (far)
    out_hd = ids == 0
    # close 1-2 px gaps inside the covered area
    gaps = region & ~cov
    small = gaps & (cv2.dilate(cov.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & (cv2.erode(cov.astype(np.uint8) | (~region).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
    V8 = np.clip(V, 0, 255).astype(np.uint8)
    V8 = cv2.inpaint(V8, small.astype(np.uint8), 2, cv2.INPAINT_TELEA)
    cov2 = cov | small
    rec = dict(source="assets/renders/living-room/warm-modern/fb13-2026-11-25/default-frame-m0w.png (H-W based), depth m0w-depth.png",
               method="forward warp of every M0-W pixel through the plan projection (house-plan conventions.projection) into the hall clay camera; z-buffer; only where the hall clay sees the living room (ids 30-43) and not behind its surface",
               camera=cam, region_px=int(region.sum()), covered_px=int(cov2.sum()), holes_px=int((region & ~cov2).sum()), outside_px_in_view=int(out_hd.sum()))
    return V8, cov2, region, rec, ids


def fill_view(V8, cov, region, ids, old8):
    """holes (what M0-W does not see: the ceiling, the floor by the opening, the top band) = the old pixels, moved per surface to the new light"""
    Lv, Lo = lab(V8), lab(old8)
    fill = Lo.copy(); shifts = {}
    core = cv2.erode(cov.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    base_shift = None
    def nblur(x, m, sg=40.0):
        w = cv2.GaussianBlur(m.astype(np.float64), (0, 0), sg)
        return cv2.GaussianBlur(x * m, (0, 0), sg) / np.maximum(w, 1e-6), w
    for k in [31, 30, 32, 33, 37, 38, 39, 34, 35, 36, 40, 41, 42, 43]:
        mk = ids == k
        if not mk.any():
            continue
        m = core & mk
        if m.sum() > 400:
            sh = [float(np.median(Lv[..., i][m]) - np.median(Lo[..., i][m])) for i in range(3)]
            if k == 31:
                base_shift = sh
        else:
            sh = base_shift or [0.0, 0.0, 0.0]
        shifts[k] = [round(s_, 2) for s_ in sh]
        for i in range(3):
            if m.sum() > 400:
                NL, wN = nblur(Lv[..., i].astype(np.float64), m)
                OL, _ = nblur(Lo[..., i].astype(np.float64), mk)
                t = np.clip(wN / 0.25, 0, 1)
                loc = t * (NL - OL) + (1 - t) * sh[i]
            else:
                loc = np.full(ids.shape, sh[i])
            fill[..., i][mk] += loc[mk]
    fill8 = np.clip(cv2.cvtColor(fill.astype(np.float32), cv2.COLOR_LAB2RGB) * 255.0, 0, 255)
    c = cov.astype(np.float64)
    wb = cv2.GaussianBlur(c, (0, 0), 3.0)
    Vext = cv2.GaussianBlur(V8.astype(np.float64) * c[..., None], (0, 0), 3.0) / np.maximum(wb[..., None], 1e-6)
    Vuse = np.where(cov[..., None], V8.astype(np.float64), Vext)
    w = np.clip(wb * 2 - 0.5, 0, 1) * (wb > 0.02)
    w = np.where(core, 1.0, w)
    view = w[..., None] * Vuse + (1 - w[..., None]) * fill8
    return view, dict(per_surface_lab_shift_old_to_new=shifts, hole_fill="the old pixels' detail + the new light's low frequency (normalized blur, 40 px) per surface, else the surface's median shift", seam_feather_sigma_px=3.0)
