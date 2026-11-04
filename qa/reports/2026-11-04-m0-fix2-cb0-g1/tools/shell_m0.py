"""
M0 1.2: is the room shell of the paid render drawn in another perspective, and can a code warp fix it?
Correspondences clay -> render (16:9 frame at 1920 x 1080) on the shell lines, each read from the gradient-peak lists of
peaks_probe.py (the strongest clay edge of the line in a narrow window, the render edge of the same line by position and order;
the window sill and the right skirting checked on 2x crops, overlays/m0-shell-*.jpg):
  back wall: floor line and skirting top at x 760, 860 (left of the sofa) and 1780, 1880 (right), cornice at x 900-1450,
             the room corner (back wall / window wall) at three heights
  window wall: the sill's top edge at x 200, 400, 520, the corner
Then: (1) the offsets; (2) the vanishing behaviour (slopes of the back wall's horizontal lines); (3) homographies: one for the
whole shell, one per plane, and the back wall's homography applied to the window wall (a single homography explains every
plane only if the render differs by a rotation / focal change about the same centre; a different camera position leaves
plane-dependent residuals = parallax).
Writes data/m0-shell.json and overlays/m0-shell-*.jpg.
"""
import json
import os
import sys

import cv2
import numpy as np

OUT = "/home/user/homedesign-app/qa/reports/2026-11-04-m0-fix2-cb0-g1"
PTS = {
    "back wall floor line": [((760, 824), (760, 808)), ((860, 835), (860, 816)), ((1780, 936), (1780, 893)), ((1880, 947), (1880, 901))],
    "back wall skirting top": [((760, 788), (760, 778)), ((860, 797), (860, 785.5)), ((1780, 885), (1780, 851)), ((1880, 895), (1880, 859))],
    "back wall cornice": [((900, 119), (900, 103)), ((1000, 104), (1000, 90)), ((1100, 89), (1100, 76)), ((1450, 35), (1450, 30))],
    "room corner": [((698, 250), (703, 250)), ((698, 450), (703, 450)), ((698, 650), (703, 650))],
    "window sill top edge": [((200, 711), (200, 683)), ((400, 684), (400, 654)), ((520, 669), (520, 638))],
}
PLANE = {"back wall floor line": "back", "back wall skirting top": "back", "back wall cornice": "back", "room corner": "both", "window sill top edge": "window"}


def arr(lines, side):
    return np.array([p[side] for ln in lines for p in PTS[ln]], np.float64)


def fit(lines):
    src, dst = arr(lines, 0), arr(lines, 1)
    Hm, _ = cv2.findHomography(src, dst, 0)
    return Hm


def resid(Hm, lines):
    out = {}
    for ln in lines:
        s = np.array([p[0] for p in PTS[ln]], np.float64).reshape(-1, 1, 2)
        d = np.array([p[1] for p in PTS[ln]], np.float64)
        pr = cv2.perspectiveTransform(s, Hm).reshape(-1, 2)
        out[ln] = [round(float(np.hypot(*(pr[i] - d[i]))), 1) for i in range(len(d))]
    return out


if __name__ == "__main__":
    rep = dict(offsets_px={ln: [dict(at=p[0], clay=p[0][1] if ln != "room corner" else p[0][0], render=p[1][1] if ln != "room corner" else p[1][0],
                                     d=round((p[1][1] - p[0][1]) if ln != "room corner" else (p[1][0] - p[0][0]), 1)) for p in pts] for ln, pts in PTS.items()})
    sl = {}
    for ln in ("back wall floor line", "back wall skirting top"):
        a, b = PTS[ln][0], PTS[ln][-1]
        sl[ln] = dict(clay=round((b[0][1] - a[0][1]) / (b[0][0] - a[0][0]), 4), render=round((b[1][1] - a[1][1]) / (b[1][0] - a[1][0]), 4))
    a, b = PTS["back wall cornice"][0], PTS["back wall cornice"][-1]
    sl["back wall cornice"] = dict(clay=round((b[0][1] - a[0][1]) / (b[0][0] - a[0][0]), 4), render=round((b[1][1] - a[1][1]) / (b[1][0] - a[1][0]), 4))
    rep["slopes"] = sl
    # where the back wall's floor line and cornice meet (the horizontal vanishing point of the back wall), clay vs render
    def vp(side):
        f, c = PTS["back wall floor line"], PTS["back wall cornice"]
        (x1, y1), (x2, y2) = f[0][side], f[-1][side]
        (x3, y3), (x4, y4) = c[0][side], c[-1][side]
        m1, m2 = (y2 - y1) / (x2 - x1), (y4 - y3) / (x4 - x3)
        x = (y3 - y1 + m1 * x1 - m2 * x3) / (m1 - m2)
        return [round(x, 0), round(y1 + m1 * (x - x1), 0)]
    rep["back_wall_vanishing_point"] = dict(clay=vp(0), render=vp(1))
    # wall height at the two ends (floor line - cornice, extrapolated)
    all_lines = list(PTS)
    back = ["back wall floor line", "back wall skirting top", "back wall cornice", "room corner"]
    win = ["window sill top edge", "room corner"]
    Hall, Hback = fit(all_lines), fit(back)
    rep["homography_all_planes"] = dict(H=np.round(Hall, 6).tolist(), residual_px=resid(Hall, all_lines))
    rep["homography_back_wall"] = dict(H=np.round(Hback, 6).tolist(), residual_px=resid(Hback, back), applied_to_window_wall=resid(Hback, ["window sill top edge"]))
    A, _ = cv2.estimateAffine2D(arr(all_lines, 0), arr(all_lines, 1), method=cv2.LMEDS)
    pa = cv2.transform(arr(all_lines, 0).reshape(-1, 1, 2), A).reshape(-1, 2)
    rep["affine_all_planes"] = dict(A=np.round(A, 5).tolist(), residual_px_max=round(float(np.hypot(*(pa - arr(all_lines, 1)).T).max()), 1))
    json.dump(rep, open(os.path.join(OUT, "data", "m0-shell.json"), "w"), indent=1)
    print(json.dumps(rep["offsets_px"]))
    print("slopes", rep["slopes"])
    print("VP", rep["back_wall_vanishing_point"])
    print("H all planes residual", rep["homography_all_planes"]["residual_px"])
    print("H back wall residual", rep["homography_back_wall"]["residual_px"], "| applied to the window wall", rep["homography_back_wall"]["applied_to_window_wall"])
    print("affine all planes max residual", rep["affine_all_planes"]["residual_px_max"])
