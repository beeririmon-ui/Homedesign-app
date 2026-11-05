"""
qa-agent 2026-11-05: CB-0 b1r3f3: the vertical seam (Lab step beyond the wall's own gradient, the 11-04 method: 10 px bins,
line fits left -125..-5 / right +65..+155 of B1's coverage edge, extrapolated to the blend's centre; the blend is now 150 px,
so the right window starts at +155), the upper wedge against the B1 wall below it, the source map (high-pass correlation with
the old CB-0) and a contrast-stretched view. Writes data/cb0-seam.json, overlays/cb0-source-map.jpg, overlays/g112-CB-0-seam-stretch.jpg.
Usage: ~/.venvs/motion/bin/python -I cb0_seam.py
"""
import importlib.util
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-05-m0-seedream-fix3-g1")
R = os.path.join(REPO, "assets/renders/poses/nordic/v7")
_s = importlib.util.spec_from_file_location("seam1104", os.path.join(REPO, "qa/reports/2026-11-04-m0-fix2-cb0-g1/tools/cb0_seam.py"))
S4 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(S4)


def steps(path, seam, right=(155, 245)):
    bins = [(seam + d, seam + d + 10) for d in range(-160, 260, 10)]
    rows = [(150, 350), (350, 600), (600, 850), (850, 1100), (1100, 1300)]
    pr = S4.profile(path, seam, rows, bins)
    out = []
    for r in pr:
        L = np.array([v[0] for v in r["lab"]]); ab = np.array([[v[1], v[2]] for v in r["lab"]])
        c = np.array([(b[0] + b[1]) / 2 for b in r["bins"]])
        lm, rm = (c > -125) & (c < -5), (c > right[0]) & (c < right[1])
        mid = 75
        pl, prr = np.polyfit(c[lm], L[lm], 1), np.polyfit(c[rm], L[rm], 1)
        da = np.polyval(np.polyfit(c[rm], ab[rm, 0], 1), mid) - np.polyval(np.polyfit(c[lm], ab[lm, 0], 1), mid)
        db = np.polyval(np.polyfit(c[rm], ab[rm, 1], 1), mid) - np.polyval(np.polyfit(c[lm], ab[lm, 1], 1), mid)
        sL = np.polyval(prr, mid) - np.polyval(pl, mid)
        out.append(dict(rows=r["rows"], step_L=round(float(sL), 2), step_dE=round(float(np.sqrt(sL ** 2 + da ** 2 + db ** 2)), 2)))
    return out


def residual(path, seam):
    """plain wall rows 150-850, x seam-125 .. seam+200 (the corner is at +245): L* in 5 px bins minus a quadratic fit (the wall's
    own smooth gradient); a seam shows as a bump. max |residual| and its position per row band."""
    im = np.asarray(Image.open(path).convert("RGB")).astype(float)
    out = []
    for y0, y1 in ((150, 350), (350, 600), (600, 850)):
        xs = np.arange(seam - 125, seam + 200, 5)
        L = np.array([S4.lab(im[y0:y1, x:x + 5].reshape(-1, 3)).mean(0)[0] for x in xs])
        c = xs + 2.5 - seam
        q = np.polyfit(c, L, 2)
        r = L - np.polyval(q, c)
        i = int(np.argmax(np.abs(r)))
        out.append(dict(rows=[y0, y1], max_abs_residual_Lstar=round(float(abs(r[i])), 2), at_px_from_edge=float(c[i]), rms=round(float(np.sqrt((r ** 2).mean())), 2)))
    return out


def wedge(path):
    im = np.asarray(Image.open(path).convert("RGB")).astype(float)
    def p(x0, x1, y0, y1):
        return S4.lab(im[y0:y1, x0:x1].reshape(-1, 3)).mean(0)
    a, b = p(900, 1050, 0, 120), p(900, 1050, 200, 320)
    return dict(top_wedge=[round(float(x), 2) for x in a], b1_wall_below=[round(float(x), 2) for x in b], dE=round(float(np.linalg.norm(a - b)), 2))


if __name__ == "__main__":
    seam = int(round(0.3034 * 2736))
    res = {}
    for tag, f in (("b1r3 (11-04)", "pose-cb-0-v7-graded-b1r3-v5.png"), ("b1r3f3", "pose-cb-0-v7-graded-b1r3f3-v5.png")):
        res[tag] = dict(seam_residual=residual(os.path.join(R, f), seam), wedge=wedge(os.path.join(R, f)))
        print(tag, res[tag])
    # source map of b1r3f3 against the old CB-0 (where the old pixels survive)
    a = cv2.imread(os.path.join(R, "pose-cb-0-v7-b1r3f3.png"), 0).astype(np.float32)
    b = cv2.imread(os.path.join(R, "pose-cb-0-v7.png"), 0).astype(np.float32)
    ha, hb = a - cv2.GaussianBlur(a, (0, 0), 3), b - cv2.GaussianBlur(b, (0, 0), 3)
    bx = lambda x: cv2.boxFilter(x, -1, (31, 31))  # noqa: E731
    rho = (bx(ha * hb) - bx(ha) * bx(hb)) / np.sqrt((bx(ha * ha) - bx(ha) ** 2) * (bx(hb * hb) - bx(hb) ** 2) + 1e-6)
    old = rho > 0.9
    res["old_share"] = round(float(old.mean()), 4)
    vis = cv2.cvtColor(cv2.imread(os.path.join(R, "pose-cb-0-v7-graded-b1r3f3-v5.png")), cv2.COLOR_BGR2RGB)
    ov = vis.copy(); ov[old] = (0.5 * ov[old] + 0.5 * np.array([255, 0, 255])).astype(np.uint8)
    Image.fromarray(ov).resize((1368, 770)).save(os.path.join(OUT, "overlays", "cb0-source-map.jpg"), quality=85)
    c = vis[:, 200:1150].astype(float)
    m = c.reshape(-1, 3).mean(0)
    s = np.clip((c - m) * 4 + 128, 0, 255).astype(np.uint8)
    out = np.concatenate([vis[:, 200:1150], np.full((vis.shape[0], 10, 3), 40, np.uint8), s], 1)
    Image.fromarray(out).resize((out.shape[1] // 2, out.shape[0] // 2)).save(os.path.join(OUT, "overlays", "g112-CB-0-seam-stretch.jpg"), quality=88)
    json.dump(res, open(os.path.join(OUT, "data", "cb0-seam.json"), "w"), indent=1)
