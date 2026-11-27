#!/usr/bin/env python3
"""
corr.py: the code steps of the warm-modern corridor stills CM and CK (FB21), render-agent 2026-11-27. 0 var2 tokens.
  python3 corr.py measure            HC's per-surface transfer (hc.png over its clay HC.png): ratio and colour of every corridor surface
  python3 corr.py refeed CK|CM       the rooms seen through the open doors, from their own display frames (FB21 section 2):
                                       living room  <- default-frame-m0w-fix1-pecan.png (fb19-tools/refeed.py's ray-cast, pecan stack)
                                       boy room     <- K-boy-defaults-fb16-finish.png + depth-fb17 (camgeo.dibr)
                                       bath         <- b1-defaults-fb16-finish.png + depth-fb17 (camgeo.dibr)
                                     CM: no source frame sees the bedroom's south wall (MB0 and MB1 both look -Y): the model draws it
  python3 corr.py prep CK|CM         the model input: the clay with HC's transfer per surface, the refed rooms pasted in
Cameras (FB21 2): CM (2.45, 14.40, 1.20) yaw 180, CK (2.45, 14.20, 1.20) yaw 0; 24 mm, shift 0.50/0.50, canvas 2720 x 1530 (base box).
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
CLAY = os.path.join(OUT, "clay")
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
WORK = os.path.join(SCR, "corr")
sys.path.insert(0, os.path.join(REPO, "site/tools/transitions"))
import camgeo as cg  # noqa: E402

R = os.path.join(REPO, "assets/renders")
HCDIR = os.path.join(R, "hall/warm-modern/hall-2026-11-18")
HC_CLAY = os.path.join(REPO, "assets/blockout/house/framing/wm-hall-2026-11-18")
CV = cg.Canvas.base(2720)
CAMS = dict(CM=cg.Cam((2.45, 14.40, 1.20), 180.0, 0.50, 0.50), CK=cg.Cam((2.45, 14.20, 1.20), 0.0, 0.50, 0.50))
HC_CAM = cg.Cam((2.462, 8.15, 1.20), 180.0, 0.50, 0.50)
HC_CV = cg.Canvas(2496, 1664, (71.11, 170.0, 2424.89, 1494.0))
SOURCES = dict(
    boy=dict(img=os.path.join(R, "boy/warm-modern/stage1-2026-11-24/K-boy-defaults-fb16-finish.png"),
             depth=os.path.join(R, "boy/warm-modern/stage1-2026-11-24/depth-fb17.png"), cam=cg.Cam((1.1, 13.0, 1.0), 33.0, 0.52, 0.44),
             box=dict(x=(-2.31, 1.55), y=(10.24, 13.74))),
    bath=dict(img=os.path.join(R, "bath/warm-modern/b1-2026-11-19/b1-defaults-fb16-finish.png"),
              depth=os.path.join(R, "bath/warm-modern/b1-2026-11-19/depth-fb17.png"), cam=cg.Cam((3.8, 13.2, 1.15), -22.0, 0.52, 0.46),
              box=dict(x=(3.25, 6.26), y=(9.94, 13.60))))
PECAN = os.path.join(R, "living-room/warm-modern/fb13-2026-11-25/default-frame-m0w-fix1-pecan.png")


# ---- io / colour ----------------------------------------------------------------------------------------------------------------
def rgb(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float64) / 255.0


def save(p, a):
    a = np.asarray(a)
    if a.dtype != np.uint8:
        a = np.clip(np.rint(a * 255.0), 0, 255).astype(np.uint8)
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    Image.fromarray(a).save(p, optimize=True)


def lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


W709 = np.array([0.2126, 0.7152, 0.0722])
_M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
_WP = np.array([0.95047, 1.0, 1.08883])


def lab(l):
    xyz = l @ _M.T / _WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


# ---- clay --------------------------------------------------------------------------------------------------------------------------
def clay(name):
    """clay rgb (0-1), float planar depth (scratch npz of clay_cm_ck.py, else the 16-bit pass), world points, valid."""
    img = rgb(os.path.join(CLAY, name + ".png"))
    npz = os.path.join(SCR, "clay/passes", name + ".npz")
    if os.path.exists(npz):
        d = np.load(npz)["depth"].astype(np.float64)
    else:
        d, _ = cg.load_depth_png(os.path.join(CLAY, name + "-depth.png"))
        d = d.astype(np.float64)
    ok = np.isfinite(d) & (d > 0) & (d < 1e4)
    U, V = CV.uv()
    P = CAMS[name].unproject(U, V, np.where(ok, d, 1.0))
    return img, d, P, ok


def hc_world():
    d, ok = cg.load_depth_png(os.path.join(HC_CLAY, "HC-depth.png"))
    U, V = HC_CV.uv()
    return HC_CAM.unproject(U, V, np.where(ok, d, 1.0)), ok


WALNUT_PIDX = (310, 700, 740, 741, 742)   # portal linings, the living opening's soffit, bench, console, the corridor door linings


def groups(P, ok, img, idx=None):
    """surfaces by world position (the corridor is outside the clay's id scope); walnut by pass index (CM/CK) or, on HC's clay (no
    passes kept), by its brown in the clay"""
    X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
    if idx is None:
        L = lab(lin(img))
        walnut = ok & (L[..., 2] > 12) & (L[..., 0] < 58) & (L[..., 1] > 4)
    else:
        walnut = ok & np.isin(idx, WALNUT_PIDX)
    corr = ok & (X > 1.69) & (X < 3.11) & (Y > 9.79) & (Y < 17.52)
    G = {}
    G["walnut"] = walnut
    G["floor"] = ok & (Z < 0.004) & ~walnut if idx is not None else corr & (Z < 0.004) & ~walnut
    G["slot"] = ok & (X < 2.005) & (X > 1.69) & (Z > 2.703) & (Y > 9.9) & (Y < 17.3)
    G["ceiling"] = corr & (Z > 2.695) & ~G["slot"] & ~walnut
    G["skirting"] = corr & (Z >= 0.004) & (Z < 0.16) & ~walnut
    G["slot_wall"] = corr & (np.abs(X - 1.70) < 0.012) & (Z >= 0.16) & (Z < 2.69) & ~walnut
    G["opp_wall"] = corr & (np.abs(X - 3.10) < 0.012) & (Z >= 0.16) & (Z < 2.69) & ~walnut
    G["end_wall"] = corr & (np.abs(Y - 17.51) < 0.012) & (Z >= 0.16) & ~walnut
    G["bedroom"] = ok & (Y > 17.53) & ~walnut
    G["hall"] = ok & (Y < 9.95) & (Y > 6.34) & (X > 0.79) & (X < 3.61) & ~walnut
    G["living"] = ok & (Y < 6.34) & ~walnut
    G["boy"] = ok & (X < 1.55) & (Y > 10.24) & (Y < 13.74) & ~walnut
    G["girl"] = ok & (X < 1.55) & (Y > 13.87) & (Y < 17.37) & ~walnut
    G["bath"] = ok & (X > 3.25) & (Y > 9.94) & (Y < 13.60) & ~walnut
    return G


def erode(m, r):
    return cv2.erode(m.astype(np.uint8), np.ones((2 * r + 1, 2 * r + 1), np.uint8)) > 0


# ---- measure: HC's transfer -------------------------------------------------------------------------------------------------------
def measure():
    hc = rgb(os.path.join(HCDIR, "hc.png"))
    hcc = rgb(os.path.join(HC_CLAY, "HC.png"))
    P, ok = hc_world()
    G = groups(P, ok, hcc)
    lh, lc = lin(hc), lin(hcc)
    Yh, Yc = lh @ W709, lc @ W709
    out = {}
    for k, m in G.items():
        m = erode(m, 6)
        n = int(m.sum())
        if n < 400:
            continue
        ratio = float(np.median(Yh[m] / np.maximum(Yc[m], 1e-4)))
        col = np.median(lh[m] / np.maximum(Yh[m], 1e-4)[:, None], 0)
        out[k] = dict(px=n, ratio=round(ratio, 4), chroma_rgb_over_Y=[round(float(c), 4) for c in col],
                      hc_lab_median=[round(float(v), 2) for v in np.median(lab(lh[m]), 0)],
                      hc_Y_median=round(float(np.median(Yh[m])), 4), clay_Y_median=round(float(np.median(Yc[m])), 4))
    # mid height of the two corridor walls (FB21 1: each wall within +-1/6 stop of the same wall in HC)
    X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
    for k in ("slot_wall", "opp_wall"):
        m = erode(G[k], 6) & (Z > 0.8) & (Z < 1.6)
        out[k]["mid_Y_median"] = round(float(np.median(Yh[m])), 4)
        out[k]["mid_L_median"] = round(float(np.median(lab(lh[m])[..., 0])), 2)
    os.makedirs(WORK, exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "hc-transfer.json"), "w"), indent=1)
    print(json.dumps({k: (v["px"], v["ratio"], v["hc_lab_median"]) for k, v in out.items()}, indent=0))
    return out


# ---- refeed -------------------------------------------------------------------------------------------------------------------------
def refeed_dibr(name, key, d_dst, P, ok):
    S = SOURCES[key]
    img = rgb(S["img"]).astype(np.float32)
    dep, val = cg.load_room_depth(S["depth"])
    out, valid, _ = cg.dibr(img, dep, S["cam"], CV, CAMS[name], CV, interp=cv2.INTER_CUBIC, tol=0.04, depth_valid=val)
    b = S["box"]
    X, Y = P[..., 0], P[..., 1]
    m = ok & (X > b["x"][0]) & (X < b["x"][1]) & (Y > b["y"][0]) & (Y < b["y"][1])
    # where the source does not see what the destination sees (disocclusion): the same world point read back through the clay
    # depth of the destination (static walls and floor of the room), else inpaint
    u2, v2, d2 = S["cam"].project(P)
    mx, my = CV.px(u2, v2)
    back = cv2.remap(img, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    sdep = cv2.remap(np.where(val, dep, 1e9).astype(np.float32), mx.astype(np.float32), my.astype(np.float32), cv2.INTER_NEAREST,
                     borderValue=1e9)
    seen = cg.inside(mx, my, CV.w, CV.h, 1.0) & (d2 > 0.05) & (np.abs(sdep - d2) < 0.05 * np.maximum(d2, 0.1) + 0.02)
    res = np.where(valid[..., None], out, np.where(seen[..., None], back, np.nan))
    hole = m & ~np.isfinite(res[..., 0])
    HOLES[:] |= hole
    res = np.where(np.isfinite(res), res, 0).astype(np.float32)
    if hole.any():
        res8 = np.clip(res * 255 + 0.5, 0, 255).astype(np.uint8)
        res = cv2.inpaint(res8, (hole * 255).astype(np.uint8), 5, cv2.INPAINT_TELEA).astype(np.float32) / 255
    rec = dict(source=os.path.relpath(S["img"], REPO), depth=os.path.relpath(S["depth"], REPO), camera=dict(loc=S["cam"].loc, yaw=S["cam"].yaw,
               u0=S["cam"].u0, v0=S["cam"].v0), mask_px=int(m.sum()), dibr_px=int((valid & m).sum()), backmap_px=int((~valid & seen & m).sum()),
               inpaint_px=int(hole.sum()))
    return np.clip(res, 0, 1), m, rec


def refeed_living(name):
    """fb19-tools/refeed.py's ray-cast (room box, sofa box, armchair billboard, product billboards) for the CK camera, with the stack of
    the pecan frame (manifest-wheel-pecan.json reproduces default-frame-m0w-fix1-pecan.png to 0 levels). Frame space 1920 x 1080."""
    sys.path.insert(0, os.path.join(REPO, "assets/prompts/transitions.warm-modern/fb19-tools"))
    import refeed as RF  # noqa: E402  (not edited)
    orig = RF.ST.load
    RF.ST.load = lambda p="layers/manifest.json", skip=(): orig("layers/manifest-wheel-pecan.json", skip)
    c = CAMS[name]
    RF.VIEWS[name] = dict(cam=dict(loc=c.loc, yaw=c.yaw, lens=24.0, u0=c.u0, v0=c.v0), ids=os.path.join(CLAY, name + "-id.png"),
                          fb=list(cg.BASE_BOX), base=os.path.join(CLAY, name + ".png"))
    r = RF.build(name)
    img = np.clip(r["img"] / 255.0, 0, 1)
    return img, r["om"], r["ok"], r["rec"]


def frame_to_canvas(a, interp=cv2.INTER_CUBIC):
    """1920 x 1080 frame -> the 2720 x 1530 canvas (the frame box; outside it, replicated)."""
    x0, y0, x1, y1 = CV.box
    sx, sy = 1920 / (x1 - x0), 1080 / (y1 - y0)
    A = np.float32([[sx, 0, -x0 * sx + 0.5 * sx - 0.5], [0, sy, -y0 * sy + 0.5 * sy - 0.5]])
    return cv2.warpAffine(np.asarray(a, np.float32), A, (CV.w, CV.h), flags=interp | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)


def heal(fill, holes, regions, img, name):
    """The holes of the refeed (what no display frame sees: a room's ceiling and upper walls, the floor just inside the door) drawn in
    code: the destination clay's shading per surface (floor / wall / ceiling by the clay normals) times a gain read on a ring of the refed
    pixels around the hole, then a multiplicative correction diffused in from the ring (normalised convolution, coarse to fine), so the
    hole meets the refeed without a seam. No product is drawn: the holes hold only plaster, ceiling and floor."""
    npz = os.path.join(SCR, "clay/passes", name + ".npz")
    nz = np.load(npz)["normal"][..., 2].astype(np.float32) / 127.0
    cls = np.where(nz > 0.7, 0, np.where(nz < -0.7, 2, 1))
    cl = lin(img).astype(np.float32)
    fl = lin(fill.astype(np.float64)).astype(np.float32)
    out = fl.copy()
    rec = {}
    for key, reg in regions.items():
        h = holes & reg
        if not h.any():
            continue
        ring = cv2.dilate(h.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool) & ~h & reg
        if ring.sum() < 50:
            ring = reg & ~h
        g_all = np.median(fl[ring] / np.maximum(cl[ring], 1e-4), 0)
        for c in (0, 1, 2):
            hc = h & (cls == c)
            if not hc.any():
                continue
            rc = ring & (cls == c) & (cl.min(-1) > 1e-4)
            g = np.median(fl[rc] / cl[rc], 0) if rc.sum() > 50 else g_all
            est = cl * g[None, None]
            corr = np.ones_like(cl)
            corr[rc] = fl[rc] / np.maximum(est[rc], 1e-5)
            w = rc.astype(np.float32)
            c_est = np.ones_like(cl)
            for sig in (120, 60, 30, 15, 7):
                bw = cv2.GaussianBlur(w, (0, 0), sig)
                bc = cv2.GaussianBlur(corr * w[..., None], (0, 0), sig)
                okk = bw > 1e-3
                c_est = np.where(okk[..., None], bc / np.maximum(bw, 1e-6)[..., None], c_est)
            out[hc] = est[hc] * np.clip(c_est[hc], 0.3, 3)
        rec[key] = dict(hole_px=int(h.sum()), ring_px=int(ring.sum()), gain_all=[round(float(v), 3) for v in g_all])
    return np.clip(srgb(out), 0, 1).astype(np.float32), rec


def refeed(name):
    img, d, P, ok = clay(name)
    G = groups(P, ok, img)
    fill = np.zeros(img.shape, np.float32)
    mask = np.zeros(img.shape[:2], bool)
    global HOLES
    HOLES = np.zeros(img.shape[:2], bool)
    rec = {}
    if name == "CK":
        for key in ("boy", "bath"):
            r, m, rr = refeed_dibr(name, key, d, P, ok)
            fill = np.where(m[..., None], r, fill)
            mask |= m
            rec[key] = rr
        li, om, lok, lrec = refeed_living(name)
        lc = frame_to_canvas(li)
        okc = frame_to_canvas(lok.astype(np.float32), cv2.INTER_LINEAR) > 0.5
        m = G["living"] & okc
        miss = G["living"] & ~okc
        HOLES[:] |= miss
        fill = np.where(m[..., None], lc, fill)
        mask |= G["living"]
        if miss.any():
            f8 = np.clip(fill * 255 + 0.5, 0, 255).astype(np.uint8)
            fill = np.where(miss[..., None], cv2.inpaint(f8, (miss * 255).astype(np.uint8), 5, cv2.INPAINT_TELEA) / 255.0, fill)
        rec["living"] = dict(source=os.path.relpath(PECAN, REPO), method="fb19-tools/refeed.py build() for the CK camera, stack "
                             "manifest-wheel-pecan.json (= the pecan frame, 0 levels)", mask_px=int(G["living"].sum()), raycast_px=int(m.sum()),
                             inpaint_px=int(miss.sum()), anchors=lrec.get("anchors"))
    if name == "CK":
        X, Y = P[..., 0], P[..., 1]
        regs = dict(boy=mask & (X < 1.55), bath=mask & (X > 3.25), living=mask & (Y < 6.34))
        fill, rec["heal"] = heal(fill, HOLES, regs, img, name)
    else:
        rec["bedroom"] = "no display frame sees the bedroom's south wall (MB0 and MB1 both look -Y): drawn by the model (FB21 2)"
    os.makedirs(WORK, exist_ok=True)
    np.savez_compressed(os.path.join(WORK, f"refeed-{name}.npz"), fill=np.clip(fill * 255 + 0.5, 0, 255).astype(np.uint8), mask=mask, holes=HOLES)
    rec["mask_px_total"] = int(mask.sum())
    json.dump(rec, open(os.path.join(WORK, f"refeed-{name}.json"), "w"), indent=1, default=str)
    print(json.dumps({k: (v if isinstance(v, (str, int)) else {kk: vv for kk, vv in v.items() if kk != "anchors"}) for k, v in rec.items()}, indent=0))
    return fill, mask, rec


# ---- prep: the model input ----------------------------------------------------------------------------------------------------------
def prep(name):
    T = json.load(open(os.path.join(HERE, "hc-transfer.json")))
    img, d, P, ok = clay(name)
    idx = np.load(os.path.join(SCR, "clay/passes", name + ".npz"))["idx"]
    G = groups(P, ok, img, idx)
    lc = lin(img)
    Yc = lc @ W709
    out = lc.copy()
    done = np.zeros(Yc.shape, bool)
    use = dict(walnut="walnut", floor="floor", slot="slot", ceiling="ceiling", skirting="skirting", slot_wall="slot_wall",
               opp_wall="opp_wall", end_wall="end_wall", bedroom="bedroom", hall="hall", girl="opp_wall", boy="bedroom", bath="bedroom",
               living="bedroom")
    for k in ("floor", "bedroom", "hall", "living", "boy", "girl", "bath", "end_wall", "ceiling", "skirting", "slot_wall", "opp_wall", "slot",
              "walnut"):
        m = G[k] & ~done if k != "walnut" else G[k]
        t = T.get(use[k]) or T["opp_wall"]
        col = np.array(t["chroma_rgb_over_Y"])
        y = Yc[m] * t["ratio"]
        out[m] = y[:, None] * col[None]
        done |= m
    rest = ok & ~done
    t = T["opp_wall"]
    out[rest] = (Yc[rest] * t["ratio"])[:, None] * np.array(t["chroma_rgb_over_Y"])[None]
    o = srgb(out)
    sl = G["slot"]
    o[sl] = np.minimum(o[sl], 250 / 255)
    f = os.path.join(WORK, f"refeed-{name}.npz")
    if os.path.exists(f):
        z = np.load(f)
        m = z["mask"]
        o = np.where(m[..., None], z["fill"] / 255.0, o)
    p = os.path.join(OUT, "inputs", f"{name}-input.png")
    save(p, o)
    print(p, {k: int(v.sum()) for k, v in G.items()})


# ---- finish: register, refill the openings, the house toe, checks ---------------------------------------------------------------------
def register(raw, ref, keep):
    """ECC homography of the model output onto the model input (gradient magnitude, at half size, on the corridor surfaces only)."""
    def grad(a):
        g = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        g = cv2.GaussianBlur(g, (0, 0), 1.5)
        return cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    s = 0.5
    A = cv2.resize(grad(ref), None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    B = cv2.resize(grad(raw), None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    M = cv2.resize(keep.astype(np.uint8), None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
    Wm = np.eye(3, dtype=np.float32)
    cc, Wm = cv2.findTransformECC(A, B, Wm, cv2.MOTION_HOMOGRAPHY, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), M, 5)
    S = np.diag([1 / s, 1 / s, 1]).astype(np.float64)
    H = S @ Wm.astype(np.float64) @ np.linalg.inv(S)      # ref px -> raw px
    pts = np.float64([[x, y] for x in (300, 1360, 2420) for y in (200, 765, 1330)])
    q = cv2.perspectiveTransform(pts[None], H)[0]
    shift = np.hypot(*(q - pts).T)
    return H, float(cc), dict(ecc=round(float(cc), 4), shift_px_at_9_points=[round(float(v), 1) for v in shift])


def lines(img, name):
    """the vertical jamb lines on the row through the eye height (v = 0.5): x of the strongest luminance steps inside the frame"""
    y = int(round(CV.box[1] + 0.5 * CV.fh))
    row = cv2.GaussianBlur(cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), 1.2)[y - 20:y + 21].mean(0)
    g = np.abs(np.diff(row))
    xs = [int(x) for x in np.argsort(-g)[:200]]
    pk = []
    for x in xs:
        if g[x] < 6 or any(abs(x - p) < 12 for p in pk):
            continue
        pk.append(x)
    return sorted(pk)[:14]


EDGES = dict(  # vertical edges at eye height (Z 1.20) that lock each still: (label, X, Y)
    CK=[("boy far jamb, room side", 1.55, 12.63), ("boy far jamb, corridor side", 1.70, 12.63), ("portal left, corridor side", 1.70, 9.95),
        ("portal left, hall side", 1.70, 9.80), ("portal right, hall side", 3.10, 9.80), ("portal right, corridor side", 3.10, 9.95),
        ("bath far jamb, corridor side", 3.10, 12.39), ("bath far jamb, room side", 3.25, 12.39)],
    CM=[("bedroom jamb left (X 2.90), corridor side", 2.90, 17.51), ("bedroom jamb right (X 2.00), corridor side", 2.00, 17.51),
        ("girl far jamb, corridor side", 1.70, 17.16), ("girl far jamb, room side", 1.55, 17.16), ("girl near jamb, corridor side", 1.70, 16.26)])


def lock(name, ref, img, win=140):
    """for each lock edge: its projection, the strongest luminance step near it in the input (ref) and in img, and img - ref in px"""
    cam = CAMS[name]
    y = int(round(CV.box[1] + 0.5 * CV.fh))
    def prof(a):
        g = cv2.cvtColor((np.clip(a, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        r = cv2.GaussianBlur(g, (0, 0), 1.0)[y - 30:y + 31].mean(0)
        return np.abs(np.gradient(r))
    pr, pi = prof(ref), prof(img)
    out = []
    for lab_, X, Y in EDGES[name]:
        u, v, d = cam.project(np.array([X, Y, 1.20]))
        x = float(CV.px(u, v)[0])
        if not (0 < x < CV.w):
            continue
        a, b = max(0, int(x - 30)), min(CV.w, int(x + 30))
        xr = a + int(np.argmax(pr[a:b]))
        a2, b2 = max(0, xr - win), min(CV.w, xr + win)
        seg = pi[a2:b2]
        # the step in img nearest to xr among the strong ones (>= 35 % of the window max)
        cand = np.nonzero(seg >= 0.35 * seg.max())[0] + a2
        xi = int(cand[np.argmin(np.abs(cand - xr))]) if len(cand) else -1
        out.append(dict(edge=lab_, projected_x=round(x, 1), input_x=xr, img_x=xi, offset_px=xi - xr))
    return out


def finish(name, raw_path, tag="r1"):
    sys.path.insert(0, os.path.join(HCDIR, "tools"))
    import tone as TN  # noqa: E402  (the WM-G1 toe, not edited)
    T = json.load(open(os.path.join(HERE, "hc-transfer.json")))
    inp = rgb(os.path.join(OUT, "inputs", f"{name}-input.png"))
    raw0 = rgb(raw_path)
    raw = cv2.resize(raw0, (CV.w, CV.h), interpolation=cv2.INTER_CUBIC if raw0.shape[1] < CV.w else cv2.INTER_AREA)
    img, d, P, ok = clay(name)
    idx = np.load(os.path.join(SCR, "clay/passes", name + ".npz"))["idx"]
    G = groups(P, ok, img, idx)
    z = np.load(os.path.join(WORK, f"refeed-{name}.npz"))
    fill, mask = z["fill"] / 255.0, z["mask"]
    keep = ok & ~cv2.dilate(mask.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    H, cc, reg = register(raw, inp, keep)
    reg["lines_input_x"] = lines(inp, name)
    reg["lines_raw_x"] = lines(raw, name)
    lk = lock(name, inp, raw)
    if max(abs(e["offset_px"]) for e in lk) <= 2:      # locked as returned: no resampling
        warped = raw.copy()
        reg["applied"] = "none: every lock edge within 2 px of the input as returned"
    else:
        warped = np.clip(cv2.warpPerspective(raw, H, (CV.w, CV.h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                                             borderMode=cv2.BORDER_REPLICATE), 0, 1)
        reg["applied"] = "ECC homography"
    reg["lines_registered_x"] = lines(warped, name)
    reg["lock_raw"] = lock(name, inp, raw)
    reg["lock_registered"] = lock(name, inp, warped)
    # the openings: the refeed, feathered 1.2 px
    a = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 1.2)[..., None]
    a = np.where(mask[..., None], np.maximum(a, 0.5), a) if mask.any() else a
    comp = warped * (1 - a) + fill * a
    # the house toe (WM-G1, tone.py's curve) outside the refed rooms, A set for the frame's p0.1 at L* 11.8 (HC's)
    fbm = np.zeros(mask.shape, bool)
    x0, y0, x1, y1 = (int(round(v)) for v in CV.box)
    fbm[y0:y1, x0:x1] = True
    L = lab(lin(comp))[..., 0]
    p01 = float(np.percentile(L[fbm], 0.1))
    A = 0.0
    if p01 < 11.0:
        lo, hi = 0.0, 14.9
        for _ in range(40):
            A = (lo + hi) / 2
            if float(np.percentile(TN.f(L[fbm], A), 0.1)) < 11.8:
                lo = A
            else:
                hi = A
        A = round((lo + hi) / 2, 2)
        comp, moved = TN.apply(comp, A, mask=~mask)
    out = np.clip(comp, 0, 1)
    # checks
    lo_ = lin(out)
    Yo = lo_ @ W709
    Lo = lab(lo_)
    X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
    ch = dict(raw=os.path.basename(raw_path), raw_px=list(raw0.shape[1::-1]), registration=reg, toe_A=A, frame_p01_before=round(p01, 2))
    ch["frame_p01"] = round(float(np.percentile(Lo[..., 0][fbm], 0.1)), 2)
    ch["frame_p05"] = round(float(np.percentile(Lo[..., 0][fbm], 0.5)), 2)
    walls = {}
    for k in ("slot_wall", "opp_wall"):
        m = erode(G[k], 6) & (Z > 0.8) & (Z < 1.6) & fbm
        if m.sum() < 200:
            continue
        y = float(np.median(Yo[m]))
        walls[k] = dict(px=int(m.sum()), L=round(float(np.median(Lo[..., 0][m])), 2), stops_vs_HC=round(float(np.log2(y / T[k]["mid_Y_median"])), 3),
                        within_1_6=bool(abs(np.log2(y / T[k]["mid_Y_median"])) <= 1 / 6 + 1e-9))
    ch["walls_mid_vs_HC"] = walls
    med = {}
    for k in ("slot_wall", "opp_wall", "floor", "ceiling", "end_wall", "bedroom", "hall", "living", "boy", "bath", "girl", "walnut"):
        m = erode(G[k], 3) & fbm
        if m.sum() > 300:
            med[k] = round(float(np.median(Lo[..., 0][m])), 2)
    ch["L_median_by_surface"] = med
    end = "bedroom" if name == "CM" else "living"
    ch["end"] = dict(surface=end, L=med.get(end), brightest_by_median=bool(med.get(end, 0) >= max(v for k, v in med.items() if k != end)))
    sl = G["slot"] & fbm
    if sl.sum():
        ch["slot"] = dict(px=int(sl.sum()), ch255_pct_of_frame=round(100 * float(((out * 255).round().max(-1)[fbm] >= 255).mean()), 4),
                          b_median=round(float(np.median(Lo[..., 2][sl])), 2), L_median=round(float(np.median(Lo[..., 0][sl])), 2))
    wn = erode(G["walnut"], 2) & fbm
    ch["walnut"] = dict(L_median=round(float(np.median(Lo[..., 0][wn])), 2), over_black_p05=round(float(np.median(Lo[..., 0][wn])) - ch["frame_p05"], 2))
    fl = erode(G["floor"], 3) & fbm & (X > 1.7) & (X < 3.1) & (Y > 9.8) & (Y < 17.5)
    ch["corridor_floor_lab"] = [round(float(v), 2) for v in np.median(Lo[fl], 0)]
    ch["hc_floor_lab"] = T["floor"]["hc_lab_median"]
    ch["refeed_px"] = int(mask.sum())
    save(os.path.join(OUT, f"{name}-{tag}.png") if tag != "final" else os.path.join(OUT, f"{name}.png"), out)
    frame = CV.crop_frame(out.astype(np.float32), 1920, 1080)
    save(os.path.join(OUT, f"{name}-frame.png") if tag == "final" else os.path.join(WORK, f"{name}-{tag}-frame.png"), frame)
    save(os.path.join(WORK, f"{name}-{tag}-registered-raw.png"), warped)
    json.dump(ch, open(os.path.join(HERE if tag == "final" else WORK, f"{name}-checks.json" if tag == "final" else f"{name}-{tag}-checks.json"), "w"),
              indent=1)
    print(json.dumps(ch, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "measure":
        measure()
    elif cmd == "refeed":
        refeed(sys.argv[2])
    elif cmd == "prep":
        prep(sys.argv[2])
    elif cmd == "finish":
        finish(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "r1")
