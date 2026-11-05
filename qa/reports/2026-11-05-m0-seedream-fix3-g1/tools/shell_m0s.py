"""
qa-agent 2026-11-05: the room shell of M0 1.2 from seedream-5-pro (raw and composite) against the round-5b clay, with QA's own
named-edge reading: the same 19 shell points as on 11-04 (shell_m0.py: back-wall floor line and skirting top at x 760 / 860 /
1780 / 1880, cornice at x 900-1450, room corner at four heights, window sill at x 200 / 400 / 520) plus the window head and the
window's right (rear) jamb. Per point: the gradient profile (+-15 px across), the clay peak nearest the clay reference, then
EVERY render peak within +-20 px of it, paired with the nearest (the list is kept, so a mis-pair is visible). Then: offsets, the
back-wall vanishing point, one homography / the back wall's homography on the window wall / one affine (as on 11-04).
Writes data/m0s-shell-<id>.json. Usage: ~/.venvs/motion/bin/python -I shell_m0s.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

R = "/home/user/homedesign-app/"
OUT = R + "qa/reports/2026-11-05-m0-seedream-fix3-g1"
W, H = 1920, 1080
CLAY = "assets/blockout/house/framing/round5b/M0.png"
FILES = {"M0 seedream raw": "assets/renders/living-room/nordic/v9/m0-shell-seedream.png",
         "M0 seedream fix": "assets/renders/living-room/nordic/v9/m0-1-2-shell-seedream-fix.png"}
# line -> list of (orientation, fixed coordinate, clay reference); 'h' = a horizontal line read in a column, 'v' = a vertical line read in a row
PTS = {
    "back wall floor line": [("h", 760, 824), ("h", 860, 835), ("h", 1780, 936), ("h", 1880, 947)],
    "back wall skirting top": [("h", 760, 788), ("h", 860, 797), ("h", 1780, 885), ("h", 1880, 895)],
    "back wall cornice": [("h", 900, 119), ("h", 1000, 104), ("h", 1100, 89), ("h", 1450, 35)],
    "room corner": [("v", 150, 698), ("v", 250, 698), ("v", 350, 698), ("v", 450, 698)],
    "window sill top edge": [("h", 200, 711), ("h", 400, 684), ("h", 520, 669)],
}
PLANE = {"back wall floor line": "back", "back wall skirting top": "back", "back wall cornice": "back", "room corner": "both", "window sill top edge": "window"}


def crop16(a):
    h, w = a.shape[:2]
    sx, sy = w / 4072, h / 2290
    return a[int(round(65 * sy)):int(round(2225 * sy)), int(round(116 * sx)):int(round(3956 * sx))]


def g(p):
    a = np.asarray(Image.open(R + p).convert("RGB"))
    a = cv2.resize(crop16(a), (W, H), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), 1.0)


def peaks(prof, lo, hi, rel=0.25):
    lo, hi = max(1, lo), min(len(prof) - 1, hi)
    seg = prof[lo:hi]
    thr = rel * seg.max()
    out = []
    for i in range(1, len(seg) - 1):
        if seg[i] >= thr and seg[i] >= seg[i - 1] and seg[i] >= seg[i + 1]:
            # sub-pixel by a parabola
            a_, b_, c_ = seg[i - 1], seg[i], seg[i + 1]
            den = a_ - 2 * b_ + c_
            off = 0.5 * (a_ - c_) / den if den != 0 else 0.0
            out.append((round(float(i + lo + off), 2), round(float(seg[i]), 1)))
    return out


def profile(img, o, fixed):
    if o == "h":
        return np.abs(np.diff(img[:, fixed - 15:fixed + 16].mean(1)))
    return np.abs(np.diff(img[fixed - 15:fixed + 16, :].mean(0)))


def read(gc, gr, win=20):
    res = {}
    for ln, pts in PTS.items():
        res[ln] = []
        for o, fixed, ref in pts:
            pc, prr = profile(gc, o, fixed), profile(gr, o, fixed)
            cp = peaks(pc, ref - 8, ref + 9, rel=0.5)
            c = min(cp, key=lambda t: abs(t[0] - ref))[0] if cp else float(ref)
            rp = peaks(prr, int(c) - win, int(c) + win + 1)
            if ln == 'room corner':
                near = [t for t in rp if abs(t[0] - c) <= 6]
                r = max(near, key=lambda t: t[1])[0] if near else None
            else:
                r = min(rp, key=lambda t: abs(t[0] - c))[0] if rp else None
            res[ln].append(dict(o=o, at=fixed, clay=float(c), render_peaks=rp, render=None if r is None else float(r), d=None if r is None else round(float(r - c), 2)))
    return res


def xy(p, which):
    v = p[which]
    return (p["at"], v) if p["o"] == "h" else (v, p["at"])


def fits(res):
    def arr(lines, which):
        return np.array([xy(p, which) for ln in lines for p in res[ln] if p["render"] is not None], np.float64)
    allL = list(PTS)
    back = ["back wall floor line", "back wall skirting top", "back wall cornice", "room corner"]
    out = {}
    Hm, _ = cv2.findHomography(arr(allL, "clay"), arr(allL, "render"), 0)
    Hb, _ = cv2.findHomography(arr(back, "clay"), arr(back, "render"), 0)

    def resid(Hx, lines):
        s, d = arr(lines, "clay"), arr(lines, "render")
        pr_ = cv2.perspectiveTransform(s.reshape(-1, 1, 2), Hx).reshape(-1, 2)
        return round(float(np.max(np.hypot(*(pr_ - d).T))), 2)
    out["homography_all_planes_max_px"] = resid(Hm, allL)
    out["back_wall_homography_on_back_max_px"] = resid(Hb, back)
    out["back_wall_homography_on_window_wall_max_px"] = resid(Hb, ["window sill top edge"])
    A, _ = cv2.estimateAffine2D(arr(allL, "clay"), arr(allL, "render"), method=cv2.LMEDS)
    pa = cv2.transform(arr(allL, "clay").reshape(-1, 1, 2), A).reshape(-1, 2)
    out["affine_all_planes_max_px"] = round(float(np.max(np.hypot(*(pa - arr(allL, "render")).T))), 2)
    # a vertical-only affine (y' = a y + b x + c), as render-agent's global affine
    s, d = arr(allL, "clay"), arr(allL, "render")
    M = np.c_[s[:, 1], s[:, 0], np.ones(len(s))]
    hm = [p["o"] == "h" for ln in allL for p in res[ln] if p["render"] is not None]
    hm = np.array(hm)
    coef, *_ = np.linalg.lstsq(M[hm], d[hm, 1], rcond=None)
    ry = d[hm, 1] - M[hm] @ coef
    out["vertical_affine_on_horizontal_lines"] = dict(scale_pct=round((coef[0] - 1) * 100, 3), shear=round(float(coef[1]), 5), offset_px=round(float(coef[2]), 2),
                                                      residual_max_px=round(float(np.max(np.abs(ry))), 2))
    # back-wall vanishing point: floor line and cornice
    def vp(which):
        f, c = res["back wall floor line"], res["back wall cornice"]
        (x1, y1), (x2, y2) = xy(f[0], which), xy(f[-1], which)
        (x3, y3), (x4, y4) = xy(c[0], which), xy(c[-1], which)
        m1, m2 = (y2 - y1) / (x2 - x1), (y4 - y3) / (x4 - x3)
        x = (y3 - y1 + m1 * x1 - m2 * x3) / (m1 - m2)
        return [round(float(x), 0), round(float(y1 + m1 * (x - x1)), 0)]
    out["back_wall_vanishing_point"] = dict(clay=vp("clay"), render=vp("render"))
    return out


if __name__ == "__main__":
    gc = g(CLAY)
    allrep = {}
    for k, f in FILES.items():
        res = read(gc, g(f), win=55 if 'gpt' in k else 20)
        rep = dict(still=f, clay=CLAY, points=res, fits=fits(res))
        ds = [abs(p["d"]) for ln in res for p in res[ln] if p["d"] is not None]
        rep["max_abs_px"] = max(ds)
        rep["per_line_d"] = {ln: [p["d"] for p in res[ln]] for ln in res}
        allrep[k] = rep
        print(k, "| max", rep["max_abs_px"], "|", rep["per_line_d"], "|", json.dumps(rep["fits"]))
    json.dump(allrep, open(os.path.join(OUT, "data", "m0s-shell.json"), "w"), indent=1)
