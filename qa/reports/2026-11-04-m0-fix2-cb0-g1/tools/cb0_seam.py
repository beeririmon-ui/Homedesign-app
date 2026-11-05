"""
qa-agent 2026-11-04: CB-0 b1r3, the seam at canvas u 0.3034 (B1 coverage edge, 60 px smootherstep inside it)
and the left part kept from the old CB-0. Lab per row band in 30 px column bins across the seam (graded v5 and raw),
step at the seam vs the wall's own gradient beside it. Also the overlap record re-read. Writes data/cb0-seam.json.
Usage: python3.12 -I cb0_seam.py
"""
import json
import os
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-04-m0-fix2-cb0-g1")
R = os.path.join(REPO, "assets/renders/poses/nordic/v7")


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], -1)


def profile(path, seam_x, rows, bins):
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.float64)
    out = []
    for (y0, y1) in rows:
        rowv = []
        for (x0, x1) in bins:
            p = lab(im[y0:y1, x0:x1].reshape(-1, 3)).mean(0)
            rowv.append([round(float(v), 2) for v in p])
        out.append({"rows": [y0, y1], "bins": [[x0 - seam_x, x1 - seam_x] for x0, x1 in bins], "lab": rowv})
    return out


if __name__ == "__main__":
    W = 2736
    seam = int(round(0.3034 * W))  # 830: B1's coverage starts here; the blend runs 60 px to its right
    bins = [(seam + d, seam + d + 10) for d in range(-160, 170, 10)]
    rows = [(150, 350), (350, 600), (600, 850), (850, 1100), (1100, 1300)]
    res = {"seam_canvas_x": seam, "blend_px": [seam, seam + 60]}
    for tag, f in (("graded_v5", "pose-cb-0-v7-graded-b1r3-v5.png"), ("raw", "pose-cb-0-v7-b1r3.png")):
        pr = profile(os.path.join(R, f), seam, rows, bins)
        steps = []
        for r in pr:
            L = np.array([v[0] for v in r["lab"]])
            ab = np.array([[v[1], v[2]] for v in r["lab"]])
            # left of the seam: bins ending <= 0; right of the blend: bins starting >= 60
            centres = np.array([(b[0] + b[1]) / 2 for b in r["bins"]])
            lm = (centres > -125) & (centres < -5)
            rm = (centres > 65) & (centres < 155)  # the corner is at +253, the skirting reaches +150 in the low rows
            # linear fits on each side, extrapolated to the blend centre (x = 30)
            pl = np.polyfit(centres[lm], L[lm], 1)
            prr = np.polyfit(centres[rm], L[rm], 1)
            stepL = float(np.polyval(prr, 30) - np.polyval(pl, 30))
            pa = [np.polyfit(centres[m], ab[m, k], 1) for m in (lm, rm) for k in (0, 1)]
            da = float(np.polyval(pa[2], 30) - np.polyval(pa[0], 30))
            db = float(np.polyval(pa[3], 30) - np.polyval(pa[1], 30))
            steps.append({"rows": r["rows"], "step_L": round(stepL, 2), "step_a": round(da, 2), "step_b": round(db, 2),
                          "step_dE": round(float(np.sqrt(stepL ** 2 + da ** 2 + db ** 2)), 2),
                          "slope_L_left_per_100px": round(float(pl[0] * 100), 2), "slope_L_right_per_100px": round(float(prr[0] * 100), 2)})
        res[tag] = {"profiles": pr, "steps_at_seam": steps}
    json.dump(res, open(os.path.join(OUT, "data/cb0-seam.json"), "w"), indent=1)
    for tag in ("graded_v5", "raw"):
        print(tag)
        for s in res[tag]["steps_at_seam"]:
            print("  ", s)
        for r in res[tag]["profiles"]:
            print("   rows", r["rows"], "L", [v[0] for v in r["lab"]][::3])
