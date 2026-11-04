"""
The two disputes of render-agent (2026-11-04) against QA's 11-03 named edges, settled line by line:
  (1) B2 r3: the vanity's right side ("-43") and the mirror head ("-34"): render-agent says parallel edges and a sloped line
      averaged against the reflected ceiling.
  (2) W0-in r2: the chair-back top ("-6" on 11-03): render-agent says the clay chair top is at 835, not 800.
Method: for each line, the gradient profile across it in a narrow band (a few columns / rows), in the clay, the raw retake and
the -fix.png, at 1920 x 1080 of the 16:9 frame; every local peak above 35 % of the band's strongest is listed with its strength,
so the lines are paired by position and order, not by "the strongest peak in a window". For the mirror head, per column
(6 px wide) the first strong edge from the top. Writes data/disputes.json and overlays/dispute-<name>.jpg (the crops of
clay / raw / fix side by side with the peaks drawn).
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

W, H = 1920, 1080


def gray(img):
    return cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)


def peaks(prof, lo, hi, rel=0.35, sep=4):
    seg = prof[lo:hi]
    if len(seg) < 3:
        return []
    thr = rel * seg.max()
    out = []
    for i in range(1, len(seg) - 1):
        if seg[i] >= thr and seg[i] >= seg[i - 1] and seg[i] >= seg[i + 1]:
            if out and i + lo - out[-1][0] < sep:
                if seg[i] > out[-1][1]:
                    out[-1] = (i + lo, float(seg[i]))
                continue
            out.append((i + lo, float(seg[i])))
    return [(p, round(s, 1)) for p, s in out]


def profile(g, orient, span, lo, hi):
    if orient == "h":                          # horizontal line: rows, averaged over columns span
        c0, c1 = int(span[0] * W), int(span[1] * W)
        return np.abs(np.diff(cv2.GaussianBlur(g, (0, 0), 1.0)[:, c0:c1], axis=0)).mean(1)
    r0, r1 = int(span[0] * H), int(span[1] * H)
    return np.abs(np.diff(cv2.GaussianBlur(g, (0, 0), 1.0)[r0:r1], axis=1)).mean(0)


def three(sid):
    d = C.load(sid)
    b = C.load(C.FIXES[sid][10])
    return gray(C.at(d["clay"], W, H)), gray(C.at(b["raw"], W, H)), gray(C.at(d["raw"], W, H)), C.at(d["clay"], W, H), C.at(b["raw"], W, H), C.at(d["raw"], W, H)


def line_peaks(imgs, orient, span, lo, hi, rel=0.35):
    return {k: peaks(profile(g, orient, span, lo, hi), lo, hi, rel) for k, g in zip(("clay", "raw", "fix"), imgs)}


def crop_sheet(cols, name, box, marks):
    x0, x1, y0, y1 = box
    tiles = []
    for (k, img) in cols:
        c = (np.clip(img[y0:y1, x0:x1], 0, 1) * 255).astype(np.uint8).copy()
        c = cv2.cvtColor(c, cv2.COLOR_RGB2BGR)
        for (orient, pos, col) in marks.get(k, []):
            if orient == "h":
                cv2.line(c, (0, pos - y0), (x1 - x0, pos - y0), col, 1)
            else:
                cv2.line(c, (pos - x0, 0), (pos - x0, y1 - y0), col, 1)
        s = 2 if (x1 - x0) < 400 else 1
        c = cv2.resize(c, ((x1 - x0) * s, (y1 - y0) * s), interpolation=cv2.INTER_NEAREST)
        cv2.putText(c, k, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
        tiles.append(c)
    hmax = max(t.shape[0] for t in tiles)
    sheet = np.concatenate([np.pad(t, ((0, hmax - t.shape[0]), (0, 8), (0, 0)), constant_values=255) for t in tiles], axis=1)
    cv2.imwrite(os.path.join(C.OUT, "overlays", f"dispute-{name}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])


out = {}
# --- (2) W0-in: horizontal lines in the column band of the chair (u 0.42-0.58) and of the desk right of the chair (u 0.68-0.80) ----
gc, gr, gf, cc, rr, ff = three("W0-in r2 fix")
w = {}
w["chair band u 0.42-0.58 rows 700-960"] = line_peaks((gc, gr, gf), "h", (0.42, 0.58), 700, 960)
w["desk right of the chair u 0.68-0.80 rows 640-960"] = line_peaks((gc, gr, gf), "h", (0.68, 0.80), 640, 960)
w["desk left of the chair u 0.20-0.33 rows 640-960"] = line_peaks((gc, gr, gf), "h", (0.20, 0.33), 640, 960)
w["chair left edge rows 0.82-0.98, cols 600-760"] = line_peaks((gc, gr, gf), "v", (0.82, 0.98), 600, 760)
w["chair right edge rows 0.82-0.98, cols 1160-1320"] = line_peaks((gc, gr, gf), "v", (0.82, 0.98), 1160, 1320)
w["desk right outer edge rows 0.80-0.95, cols 1500-1660"] = line_peaks((gc, gr, gf), "v", (0.80, 0.95), 1500, 1660)
out["W0-in"] = w
marks = {k: [("h", p, (0, 0, 255) if k == "clay" else (0, 160, 0)) for p, s in w["chair band u 0.42-0.58 rows 700-960"][k]] for k in ("clay", "raw", "fix")}
crop_sheet([("clay", cc), ("raw", rr), ("fix", ff)], "W0-in-chair-top", (int(0.36 * W), int(0.64 * W), 640, 1000), marks)
# --- (1) B2: the vanity's right side, rows 0.60-0.90, columns 1480-1660; and the mirror head per column --------------------------
gc, gr, gf, cc, rr, ff = three("B2 r3 fix")
b = {}
b["vanity right side rows 0.60-0.90 cols 1480-1660"] = line_peaks((gc, gr, gf), "v", (0.60, 0.90), 1480, 1660, rel=0.25)
b["vanity right side rows 0.62-0.70 (drawer front) cols 1480-1660"] = line_peaks((gc, gr, gf), "v", (0.62, 0.70), 1480, 1660, rel=0.25)
b["vanity right side rows 0.80-0.90 (open shelf) cols 1480-1660"] = line_peaks((gc, gr, gf), "v", (0.80, 0.90), 1480, 1660, rel=0.25)
b["vanity left side rows 0.60-0.90 cols 860-1000"] = line_peaks((gc, gr, gf), "v", (0.60, 0.90), 860, 1000, rel=0.25)
head = {}
for x in (1090, 1150, 1250, 1350, 1450, 1540):
    col = {}
    for k, g in (("clay", gc), ("raw", gr), ("fix", gf)):
        prof = np.abs(np.diff(cv2.GaussianBlur(g, (0, 0), 1.0)[:, x - 3:x + 3], axis=0)).mean(1)
        pk = peaks(prof, 20, 220, rel=0.30)
        col[k] = pk
    head[str(x)] = col
b["mirror head per column (rows 20-220, peaks >= 30 % of the column's strongest)"] = head
out["B2"] = b
mk = {k: [("v", p, (0, 0, 255) if k == "clay" else (0, 160, 0)) for p, s in b["vanity right side rows 0.60-0.90 cols 1480-1660"][k]] for k in ("clay", "raw", "fix")}
crop_sheet([("clay", cc), ("raw", rr), ("fix", ff)], "B2-vanity-right", (1440, 1700, int(0.55 * H), int(0.95 * H)), mk)
mk = {k: [("h", head[str(x)][k][0][0], (0, 0, 255) if k == "clay" else (0, 160, 0)) for x in (1090,) if head[str(x)][k]] for k in ("clay", "raw", "fix")}
crop_sheet([("clay", cc), ("raw", rr), ("fix", ff)], "B2-mirror-head", (1040, 1600, 0, 260), {})
json.dump(out, open(os.path.join(C.OUT, "data", "disputes.json"), "w"), indent=1)
for room, v in out.items():
    print("=====", room)
    for k, x in v.items():
        if isinstance(x, dict) and "clay" in x:
            print(" ", k)
            for kk in ("clay", "raw", "fix"):
                print("     ", kk, x[kk])
        else:
            print(" ", k)
            for col, y in x.items():
                print("     x", col, {kk: y[kk][:4] for kk in ("clay", "raw", "fix")})
