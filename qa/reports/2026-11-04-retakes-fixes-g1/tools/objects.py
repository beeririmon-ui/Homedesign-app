"""
Direct size of the objects the code fixes scaled (QA, 2026-11-04), on the graded-fix-v4 canvas and, for comparison, on the
graded-v3 retake before the fix: per row, the background is the median colour of the columns just left and right of the object's
search window (the same surface at that row: wall, band or desk), and the object is every pixel more than dE 9 from it (CIELAB),
opened 3 px, largest component plus the components overlapping it. The body (without thin pencils / ears / hooks) = the rows whose
width is >= 55 % of the widest row. Ratios against the clay box (canvas uv of the selfcheck), +-15 % (G1.3, proposal).
Writes data/objects.json and overlays/objects.jpg.
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

# (still, label, selfcheck key, search window canvas uv (u0,u1,v0,v1), background columns margin (uv))
JOBS = [
    ("K-girl-0 r2 fix", "framed prints (pair)", "girl/framed-prints", (0.30, 0.52, 0.11, 0.345), 0.02),
    ("K-girl-0 r2", "framed prints (pair), before", "girl/framed-prints", (0.28, 0.56, 0.11, 0.42), 0.02),
    ("K-girl-0 r2 fix", "doll", "girl/doll", (0.26, 0.345, 0.42, 0.596), 0.02),
    ("K-girl-0 r2", "doll, before", "girl/doll", (0.255, 0.35, 0.40, 0.596), 0.02),
    ("W0-in r2 fix", "pen cup", "work/desk-organizer", (0.300, 0.372, 0.53, 0.70), 0.015),
    ("W0-in r2", "pen cup, before", "work/desk-organizer", (0.300, 0.380, 0.46, 0.68), 0.015),
    ("B2 r3 fix", "storage basket", "bath/storage-basket", (0.50, 0.73, 0.78, 0.99), 0.0),
    ("B2 r3 fix", "towel ring", "bath/towel-ring", (0.80, 0.90, 0.53, 0.60), 0.01),
]


def lab(a):
    return cv2.cvtColor(a.astype(np.float32), cv2.COLOR_RGB2LAB)


def measure(sid, label, key, win, margin, tiles):
    d = C.load(sid, raw=False)
    a = d["graded_canvas"] if d["ovs"] else d["graded"]
    Hc, Wc = a.shape[:2]
    sc = d["sc"]
    box = sc["boxes"][key]["box"]
    u0, u1, v0, v1 = win
    X0, X1, Y0, Y1 = int(u0 * Wc), int(u1 * Wc), int(v0 * Hc), int(v1 * Hc)
    m = max(4, int(margin * Wc))
    L = lab(a)
    reg = L[Y0:Y1, X0:X1]
    if margin > 0:
        bgcols = np.concatenate([L[Y0:Y1, max(0, X0 - m):X0], L[Y0:Y1, X1:min(Wc, X1 + m)]], axis=1)
        bg = np.median(bgcols, axis=1)[:, None, :]
    else:  # the storage basket fills the shelf: background = the shelf's back wall rows above the basket, per column
        bg = np.median(L[Y0 - 25:Y0 - 5, X0:X1], axis=0)[None, :, :]
    de = np.sqrt(((reg - bg) ** 2).sum(2))
    mk = cv2.morphologyEx((de > 9).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lb, st, _ = cv2.connectedComponentsWithStats(mk)
    if n <= 1:
        return dict(still=sid, label=label, found=False)
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = st[i, 0], st[i, 1], st[i, 2], st[i, 3]
    keep = np.zeros_like(mk)
    for j in range(1, n):
        xj, yj, wj, hj = st[j, 0], st[j, 1], st[j, 2], st[j, 3]
        if st[j, cv2.CC_STAT_AREA] >= 30 and not (xj > x + w or xj + wj < x or yj > y + h or yj + hj < y):
            keep |= (lb == j).astype(np.uint8)
    ys, xs = np.nonzero(keep)
    bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
    rw = keep.sum(1)
    body = np.nonzero(rw >= 0.55 * rw.max())[0]
    bo0, bo1 = body.min(), body.max()
    bw_box, bh_box = (box[1] - box[0]) * Wc, (box[3] - box[2]) * Hc
    rec = dict(still=sid, label=label, clay_box_uv=[round(x_, 4) for x_ in box], box_px=[int(bw_box), int(bh_box)],
               extent_uv=[round((X0 + bx0) / Wc, 4), round((X0 + bx1) / Wc, 4), round((Y0 + by0) / Hc, 4), round((Y0 + by1) / Hc, 4)],
               width_ratio=round((bx1 - bx0) / bw_box, 3), height_ratio=round((by1 - by0) / bh_box, 3),
               body_rows_uv=[round((Y0 + bo0) / Hc, 4), round((Y0 + bo1) / Hc, 4)], body_height_ratio=round((bo1 - bo0) / bh_box, 3),
               centre_du_box=round((((X0 + (bx0 + bx1) / 2) / Wc) - (box[0] + box[1]) / 2) / (box[1] - box[0]), 3),
               centre_dv_box=round((((Y0 + (by0 + by1) / 2) / Hc) - (box[2] + box[3]) / 2) / (box[3] - box[2]), 3),
               inside_15pct=bool(0.85 <= (bx1 - bx0) / bw_box <= 1.15 and 0.85 <= (by1 - by0) / bh_box <= 1.15))
    c = (np.clip(a[Y0:Y1, X0:X1], 0, 1) * 255).astype(np.uint8).copy()
    cv2.rectangle(c, (int(box[0] * Wc) - X0, int(box[2] * Hc) - Y0), (int(box[1] * Wc) - X0, int(box[3] * Hc) - Y0), (255, 60, 40), 2)
    cv2.rectangle(c, (bx0, by0), (bx1, by1), (0, 180, 0), 1)
    c = cv2.cvtColor(c, cv2.COLOR_RGB2BGR)
    s = 300 / max(c.shape[:2])
    c = cv2.resize(c, (int(c.shape[1] * s), int(c.shape[0] * s)), interpolation=cv2.INTER_AREA)
    t = np.full((336, 300, 3), 245, np.uint8)
    t[:c.shape[0], :c.shape[1]] = c
    cv2.putText(t, f"{sid}: {label}"[:40], (3, 314), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (20, 20, 20), 1)
    cv2.putText(t, f"w {rec['width_ratio']} h {rec['height_ratio']} (red clay, green found)", (3, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (90, 90, 90), 1)
    tiles.append(t)
    return rec


if __name__ == "__main__":
    tiles, out = [], []
    for j in JOBS:
        r = measure(*j, tiles)
        out.append(r)
        print(f"{r['still']:16s} {r['label']:30s} w {r.get('width_ratio')} h {r.get('height_ratio')} body h {r.get('body_height_ratio')} centre ({r.get('centre_du_box')}, {r.get('centre_dv_box')}) inside15 {r.get('inside_15pct')} extent {r.get('extent_uv')} box {r.get('clay_box_uv')}")
    cv2.imwrite(os.path.join(C.OUT, "overlays", "objects.jpg"), np.concatenate(tiles, axis=1), [cv2.IMWRITE_JPEG_QUALITY, 85])
    json.dump(out, open(os.path.join(C.OUT, "data", "objects.json"), "w"), indent=1)
