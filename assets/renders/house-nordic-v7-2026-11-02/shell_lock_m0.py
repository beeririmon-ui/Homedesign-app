#!/usr/bin/env python3
"""
shell_lock_m0.py: the M0 1.2 room shell of a render against the round-5b clay, on QA's named shell lines (qa/reports/2026-11-04-m0-fix2-cb0-g1,
tools/shell_m0.py: the same points, clay values in the 16:9 frame at 1920 x 1080), measured automatically (render-agent, 2026-11-05):
  each horizontal line (floor line, skirting top, cornice, window sill top edge): in a 31 px column band at each x, the |d/dy| peak of the
  clay's sign within +-SEARCH px of the clay's row, ranked by strength x proximity; the room corner and the window jambs: |d/dx| peaks in a
  41 px row band. Then (1) the raw offsets, (2) the back wall's vanishing point (floor line x cornice), (3) one global affine (what code may
  apply to the whole frame) and its residuals, (4) one homography for all planes and the back wall's homography on the window wall
  (parallax test, as QA). Pass (G1.4 master, 0.5 % of the frame = 9.6 px at 1920): every named line within 9.6 px after the global affine,
  the affine's scale within 0.995-1.005 is not required (code applies it), shift <= 9.6 recorded.
  python3 shell_lock_m0.py <still.png> [--label X] [--out json]
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CLAY = os.path.join(REPO, "assets/blockout/house/framing/round5b/M0.png")
SEARCH = 60
LIMIT = 9.6
# QA's points (clay side), 1920 x 1080 frame px: (x, y) for horizontal lines, (x, y) with the x measured for the corner
H_LINES = {"back wall floor line": [(760, 824), (860, 835), (1780, 936), (1880, 947)],
           "back wall skirting top": [(760, 788), (860, 797), (1780, 885), (1880, 895)],
           "back wall cornice": [(900, 119), (1000, 104), (1100, 89), (1450, 35)],
           "window sill top edge": [(200, 711), (400, 684), (520, 669)]}
V_LINES = {"room corner": [(698, 150), (698, 250), (698, 350), (698, 450)]}      # QA's 650 is behind the armchair / curtain in renders
PLANE = {"back wall floor line": "back", "back wall skirting top": "back", "back wall cornice": "back", "room corner": "both",
         "window sill top edge": "window", "window jamb": "window"}


def frame16(path):
    from PIL import Image
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    H, W = im.shape[:2]
    if abs(W / H - 4072 / 2290) < 0.01:          # overscan canvas -> the 16:9 frame
        x0, y0 = int(round(116 / 4072 * W)), int(round(65 / 2290 * H))
        x1, y1 = int(round(3956 / 4072 * W)), int(round(2225 / 2290 * H))
        im = im[y0:y1, x0:x1]
    return cv2.resize(im, (1920, 1080), interpolation=cv2.INTER_AREA)


def grads(img):
    g = cv2.GaussianBlur(cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), 1.2)
    return cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)


def peaks(p):
    return [i for i in range(1, len(p) - 1) if abs(p[i]) >= abs(p[i - 1]) and abs(p[i]) >= abs(p[i + 1])]


def subpix(p, i):
    den = p[i - 1] - 2 * p[i] + p[i + 1]
    return 0.5 * (p[i - 1] - p[i + 1]) / den if den != 0 else 0.0


def find(prof_c, prof_r, i0, search=SEARCH):
    """the clay's edge at i0 (its sign, refined to the clay's own peak within 6 px), the render's edge of that sign near it"""
    lo = max(1, i0 - 6)
    pc = prof_c[lo:i0 + 7]
    ic = lo + int(np.argmax(np.abs(pc)))
    sign = np.sign(prof_c[ic])
    yc = ic + subpix(prof_c, ic)
    a, b = max(1, ic - search), min(len(prof_r) - 1, ic + search)
    cand = [i for i in peaks(prof_r[a - 1:b + 1]) if np.sign(prof_r[a - 1 + i]) == sign]
    if not cand:
        return yc, None, 0.0
    m = max(abs(prof_r[a - 1 + i]) for i in cand)
    best = max(cand, key=lambda i: abs(prof_r[a - 1 + i]) / m - 0.35 * abs(a - 1 + i - ic) / search)
    j = a - 1 + best
    return yc, j + subpix(prof_r, j), float(abs(prof_r[j]) / max(abs(prof_c[ic]), 1e-3))


def measure(path, label=None):
    c, r = frame16(CLAY), frame16(path)
    gxc, gyc = grads(c)
    gxr, gyr = grads(r)
    pts, rows = [], []
    # the floor line and the skirting top as a pair: both of the clay's signs, their gap 0.6-1.6x the clay's, the best joint score
    pair = {}
    for (xf, yf), (xs_, ys_) in zip(H_LINES["back wall floor line"], H_LINES["back wall skirting top"]):
        pc, pr = gyc[:, xf - 15:xf + 16].mean(1), gyr[:, xf - 15:xf + 16].mean(1)
        icf = max(1, yf - 6) + int(np.argmax(np.abs(pc[max(1, yf - 6):yf + 7])))
        ics = max(1, ys_ - 6) + int(np.argmax(np.abs(pc[max(1, ys_ - 6):ys_ + 7])))
        sf, ss = np.sign(pc[icf]), np.sign(pc[ics])
        gap = icf - ics
        a, b = max(1, ics - SEARCH), min(len(pr) - 2, icf + SEARCH)
        pk = [i for i in peaks(pr[a - 1:b + 1])]
        pk = [a - 1 + i for i in pk]
        m = max([abs(pr[i]) for i in pk] + [1e-3])
        best = None
        for i_f in [i for i in pk if np.sign(pr[i]) == sf]:
            for i_s in [i for i in pk if np.sign(pr[i]) == ss and 0.6 * gap <= i_f - i <= 1.6 * gap]:
                sc = (abs(pr[i_f]) + abs(pr[i_s])) / m - 0.35 * (abs(i_f - icf) + abs(i_s - ics)) / SEARCH
                if best is None or sc > best[0]:
                    best = (sc, i_f, i_s)
        if best:
            pair[("back wall floor line", xf)] = (float(icf + subpix(pc, icf)), float(best[1] + subpix(pr, best[1])), float(abs(pr[best[1]]) / max(abs(pc[icf]), 1e-3)))
            pair[("back wall skirting top", xs_)] = (float(ics + subpix(pc, ics)), float(best[2] + subpix(pr, best[2])), float(abs(pr[best[2]]) / max(abs(pc[ics]), 1e-3)))
    for ln, ps in H_LINES.items():
        for (x, y) in ps:
            pc, pr = gyc[:, x - 15:x + 16].mean(1), gyr[:, x - 15:x + 16].mean(1)
            if (ln, x) in pair:
                yc, yr, rel = pair[(ln, x)]
            elif ln in ("back wall floor line", "back wall skirting top"):
                yc, yr, rel = find(pc, pr, y)[0], None, 0.0
            else:
                yc, yr, rel = find(pc, pr, y)
            rows.append(dict(line=ln, at_x=x, clay=round(float(yc), 2), render=(round(float(yr), 2) if yr is not None else None),
                             d=(round(float(yr - yc), 2) if yr is not None else None), rel_strength=round(rel, 2)))
            if yr is not None:
                pts.append((ln, (x, yc), (x, yr)))
    for ln, ps in V_LINES.items():
        for (x, y) in ps:
            pc, pr = gxc[y - 20:y + 21].mean(0), gxr[y - 20:y + 21].mean(0)
            xc, xr, rel = find(pc, pr, x)
            rows.append(dict(line=ln, at_y=y, clay=round(float(xc), 2), render=(round(float(xr), 2) if xr is not None else None),
                             d=(round(float(xr - xc), 2) if xr is not None else None), rel_strength=round(rel, 2)))
            if xr is not None:
                pts.append((ln, (xc, y), (xr, y)))
    src = np.array([p[1] for p in pts], np.float64)
    dst = np.array([p[2] for p in pts], np.float64)
    names = [p[0] for p in pts]
    raw = np.hypot(*(dst - src).T)
    A, _ = cv2.estimateAffine2D(src, dst, method=cv2.LMEDS)
    pa = cv2.transform(src.reshape(-1, 1, 2), A).reshape(-1, 2)
    ra = np.hypot(*(pa - dst).T)
    Hall, _ = cv2.findHomography(src, dst, 0)
    rh = np.hypot(*(cv2.perspectiveTransform(src.reshape(-1, 1, 2), Hall).reshape(-1, 2) - dst).T)
    back = [i for i, n in enumerate(names) if PLANE[n] in ("back", "both")]
    win = [i for i, n in enumerate(names) if PLANE[n] == "window"]
    Hb, _ = cv2.findHomography(src[back], dst[back], 0)
    rbw = np.hypot(*(cv2.perspectiveTransform(src[win].reshape(-1, 1, 2), Hb).reshape(-1, 2) - dst[win]).T) if win else np.array([])

    def vp(side):
        f = [p for p in pts if p[0] == "back wall floor line"]
        co = [p for p in pts if p[0] == "back wall cornice"]
        if len(f) < 2 or len(co) < 2:
            return None
        (x1, y1), (x2, y2) = f[0][side], f[-1][side]
        (x3, y3), (x4, y4) = co[0][side], co[-1][side]
        m1, m2 = (y2 - y1) / (x2 - x1), (y4 - y3) / (x4 - x3)
        x = (y3 - y1 + m1 * x1 - m2 * x3) / (m1 - m2)
        return [round(float(x), 0), round(float(y1 + m1 * (x - x1)), 0)]
    per_line = {}
    for n in dict.fromkeys(names):
        idx = [i for i, m in enumerate(names) if m == n]
        per_line[n] = dict(raw_max=round(float(raw[idx].max()), 2), after_affine_max=round(float(ra[idx].max()), 2))
    sx, sy = float(np.hypot(A[0, 0], A[1, 0])), float(np.hypot(A[0, 1], A[1, 1]))
    rep = dict(still=os.path.relpath(path, REPO), label=label, clay=os.path.relpath(CLAY, REPO), frame_px=[1920, 1080], limit_px=LIMIT,
               lines=rows, per_line=per_line, raw_max_px=round(float(raw.max()), 2), points=len(pts),
               global_affine=dict(A=np.round(A, 5).tolist(), scale=[round(sx, 4), round(sy, 4)], shift_px=[round(float(A[0, 2]), 2), round(float(A[1, 2]), 2)],
                                  residual_max_px=round(float(ra.max()), 2)),
               homography_all_planes_residual_max_px=round(float(rh.max()), 2),
               back_wall_homography_on_window_wall_max_px=(round(float(rbw.max()), 2) if len(rbw) else None),
               back_wall_vanishing_point=dict(clay=vp(1), render=vp(2)),
               verdict=dict(raw_pass=bool(raw.max() <= LIMIT), after_global_affine_pass=bool(ra.max() <= LIMIT),
                            rule="G1.4 master: every named shell line within 9.6 px (0.5 % of 1920), raw or after one global affine (code)"))
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("still")
    ap.add_argument("--label")
    ap.add_argument("--out")
    a = ap.parse_args()
    rep = measure(a.still, a.label)
    if a.out:
        json.dump(rep, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: rep[k] for k in ("raw_max_px", "per_line", "global_affine", "homography_all_planes_residual_max_px",
                                          "back_wall_homography_on_window_wall_max_px", "back_wall_vanishing_point", "verdict")}, indent=1))
    for r in rep["lines"]:
        print(r)
