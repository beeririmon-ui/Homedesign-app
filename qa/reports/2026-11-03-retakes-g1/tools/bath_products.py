"""
The two new bath products (V7Q3, test only) and the invented plinth of B1 r3, measured on the graded-v3 canvas by row profiles
in the column band of the clay's pot: for every row the median HSL across the band classifies the row as fern (green hue),
basket (warm, saturated seagrass), plinth (low-chroma stone), floor (limestone-look tile) or wall. The contiguous row runs give
the basket's and the plinth's top / bottom in the frame, against the clay's pot cylinder (B1 r3 prompt: pot y 0.75-0.877 of the
canvas = a 30 cm pot) and the floor-planter box. The brush: the matte-black component in / around its clay box (D8 x H38).
Writes data/bath-products.json and overlays/bath-products.jpg (the two crops with the measured rows drawn).
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def hsl_rows(a):
    mx, mn = a.max(2), a.min(2)
    L = (mx + mn) / 2
    S = np.where(mx == mn, 0, np.where(L <= 0.5, (mx - mn) / (mx + mn + 1e-6), (mx - mn) / (2 - mx - mn + 1e-6)))
    hsv = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    return hsv[..., 0].astype(np.float32) * 2, S * 100, L * 100


def classify(h, s, l):
    if 55 <= h <= 170 and s >= 8:
        return "fern"
    if 12 <= h <= 48 and s >= 22 and l <= 80:
        return "basket"
    if s < 16 and 45 <= l <= 88:
        return "stone"
    return "other"


def runs(labels, want):
    out, start = [], None
    for i, x in enumerate(labels + ["end"]):
        if x == want and start is None:
            start = i
        elif x != want and start is not None:
            out.append((start, i - 1))
            start = None
    return out


def planter(sid, pot_cols, pot_v, box, draw):
    d = C.load(sid, raw=False)
    a = d["graded_canvas"]
    Hc, Wc = a.shape[:2]
    Hh, S, L = hsl_rows(a)
    x0, x1 = int(pot_cols[0] * Wc), int(pot_cols[1] * Wc)
    y0, y1 = int((box[2] - 0.03) * Hc), int(min(1, box[3] + 0.06) * Hc)
    labels = []
    for y in range(y0, y1):
        h, s, l = float(np.median(Hh[y, x0:x1])), float(np.median(S[y, x0:x1])), float(np.median(L[y, x0:x1]))
        labels.append(classify(h, s, l))
    # smooth: a run shorter than 6 rows takes its neighbours' label
    lab = labels[:]
    for i in range(1, len(lab) - 1):
        if lab[i] != lab[i - 1] and lab[i] != lab[i + 1] and lab[i - 1] == lab[i + 1]:
            lab[i] = lab[i - 1]
    bk = [r for r in runs(lab, "basket") if r[1] - r[0] >= 20]
    st = [r for r in runs(lab, "stone") if r[1] - r[0] >= 8]
    fr = [r for r in runs(lab, "fern") if r[1] - r[0] >= 10]
    rec = dict(frame=sid, pot_cols=list(pot_cols), clay_pot_v=list(pot_v), clay_box_uv=list(box), rows_scanned=[y0, y1])
    if bk:
        b0, b1 = bk[-1][0] + y0, bk[-1][1] + y0
        rec["basket_rows"] = [b0, b1]
        rec["basket_v"] = [round(b0 / Hc, 4), round(b1 / Hc, 4)]
        pot_px = (pot_v[1] - pot_v[0]) * Hc
        rec["pot_box_px"] = int(pot_px)
        rec["basket_height_px"] = b1 - b0
        rec["basket_height_over_pot_box"] = round((b1 - b0) / pot_px, 2)
        rec["basket_bottom_minus_pot_bottom_px"] = int(b1 - pot_v[1] * Hc)
        rec["basket_top_minus_pot_top_px"] = int(b0 - pot_v[0] * Hc)
        # the plinth: a stone run that starts within 12 rows under the basket's bottom
        pl = [r for r in st if 0 <= r[0] + y0 - b1 <= 12]
        if pl:
            p0, p1 = pl[0][0] + y0, pl[0][1] + y0
            rec["plinth_rows"] = [p0, p1]
            rec["plinth_v"] = [round(p0 / Hc, 4), round(p1 / Hc, 4)]
            rec["plinth_height_px"] = p1 - p0
            rec["plinth_height_over_pot_box"] = round((p1 - p0) / pot_px, 2)
            rec["plinth_height_cm_at_pot_scale_30"] = round(30 * (p1 - p0) / pot_px, 1)
            rec["basket_plus_plinth_cm_at_pot_scale_30"] = round(30 * (p1 - b0) / pot_px, 1)
            rec["plinth_bottom_minus_pot_bottom_px"] = int(p1 - pot_v[1] * Hc)
        else:
            rec["plinth_rows"] = None
        # basket width at its mid row
        ym = (b0 + b1) // 2
        row = np.array([classify(float(Hh[ym, x]), float(S[ym, x]), float(L[ym, x])) == "basket" for x in range(max(0, x0 - int(0.06 * Wc)), min(Wc, x1 + int(0.06 * Wc)))])
        xs = np.nonzero(row)[0]
        if len(xs):
            wx0, wx1 = xs.min() + max(0, x0 - int(0.06 * Wc)), xs.max() + max(0, x0 - int(0.06 * Wc))
            rec["basket_width_px_mid"] = int(wx1 - wx0)
            rec["basket_width_over_pot_cols"] = round((wx1 - wx0) / (x1 - x0), 2)
            rec["basket_u_mid"] = [round(wx0 / Wc, 4), round(wx1 / Wc, 4)]
        rec["basket_median_HSL"] = [round(float(np.median(Hh[b0:b1, x0:x1])), 1), round(float(np.median(S[b0:b1, x0:x1])), 1), round(float(np.median(L[b0:b1, x0:x1])), 1)]
    if fr:
        f0 = fr[0][0] + y0
        rec["fern_top_v"] = round(f0 / Hc, 4)
        rec["fern_top_minus_box_top_px"] = int(f0 - box[2] * Hc)
        rec["fern_median_HSL"] = [round(float(np.median(Hh[f0:f0 + 60, x0:x1])), 1), round(float(np.median(S[f0:f0 + 60, x0:x1])), 1), round(float(np.median(L[f0:f0 + 60, x0:x1])), 1)]
    rec["row_labels_runs"] = {k: [[r[0] + y0, r[1] + y0] for r in runs(lab, k)] for k in ("fern", "basket", "stone")}
    # draw
    X0, X1 = max(0, x0 - int(0.12 * Wc)), min(Wc, x1 + int(0.12 * Wc))
    crop = (a[y0 - int(0.02 * Hc):y1, X0:X1] * 255).astype(np.uint8).copy()
    oy, ox = y0 - int(0.02 * Hc), X0
    cv2.rectangle(crop, (x0 - ox, int(pot_v[0] * Hc) - oy), (x1 - ox, int(pot_v[1] * Hc) - oy), (255, 60, 40), 2)
    if bk:
        cv2.line(crop, (0, rec["basket_rows"][0] - oy), (crop.shape[1], rec["basket_rows"][0] - oy), (0, 180, 0), 2)
        cv2.line(crop, (0, rec["basket_rows"][1] - oy), (crop.shape[1], rec["basket_rows"][1] - oy), (0, 180, 0), 2)
    if rec.get("plinth_rows"):
        cv2.line(crop, (0, rec["plinth_rows"][1] - oy), (crop.shape[1], rec["plinth_rows"][1] - oy), (0, 0, 255), 2)
    cv2.putText(crop, f"{sid}: red = clay pot box, green = basket rows, blue = plinth bottom", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    draw.append(cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    return rec


def brush(draw):
    d = C.load("B1 r3", raw=False)
    a = d["graded_canvas"]
    Hc, Wc = a.shape[:2]
    Hh, S, L = hsl_rows(a)
    bb = d["sc"]["boxes"]["bath/toilet-brush"]["box"]
    u0, u1, v0, v1 = bb
    r0, r1, c0, c1 = int((v0 - 0.08) * Hc), int(min(1, v1 + 0.04) * Hc), int((u0 - 0.03) * Wc), int((u1 + 0.03) * Wc)
    dark = (L[r0:r1, c0:c1] < 28).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(dark)
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, hh = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
    comp = lab == i
    rows_w = comp.sum(1)
    holder_rows = np.nonzero(rows_w >= 0.7 * rows_w.max())[0]
    holder_h = int(holder_rows.max() - holder_rows.min() + 1) if len(holder_rows) else 0
    handle_h = int(hh - holder_h)
    box_h, box_w = (v1 - v0) * Hc, (u1 - u0) * Wc
    rec = dict(clay_box_uv=[round(x_, 4) for x_ in bb], box_px=[int(box_w), int(box_h)], render_uv=[round((c0 + x) / Wc, 4), round((c0 + x + w) / Wc, 4), round((r0 + y) / Hc, 4), round((r0 + y + hh) / Hc, 4)],
               render_px=[int(w), int(hh)], holder_width_px=int(rows_w.max()), holder_height_px=holder_h, handle_height_px=handle_h,
               height_ratio_to_box=round(hh / box_h, 2), holder_width_ratio_to_box=round(rows_w.max() / box_w, 2),
               height_cm_at_box_scale_38=round(38 * hh / box_h, 1), holder_width_cm_at_box_scale_8=round(8 * rows_w.max() / box_w, 1),
               holder_height_cm_at_box_scale_38=round(38 * holder_h / box_h, 1), handle_height_cm_at_box_scale_38=round(38 * handle_h / box_h, 1),
               card="toilet-brush-aliexpress-matte-black-steel-cylinder-245996, black SKU: 8 x 38 cm (holder 14.5, handle 25)",
               top_minus_box_top_px=int(r0 + y - v0 * Hc), bottom_minus_box_bottom_px=int(r0 + y + hh - v1 * Hc), median_L_body=round(float(np.median(L[r0:r1, c0:c1][comp])), 1))
    crop = (a[r0:r1, c0 - int(0.02 * Wc):c1 + int(0.02 * Wc)] * 255).astype(np.uint8).copy()
    ox = c0 - int(0.02 * Wc)
    cv2.rectangle(crop, (int(u0 * Wc) - ox, int(v0 * Hc) - r0), (int(u1 * Wc) - ox, int(v1 * Hc) - r0), (255, 60, 40), 2)
    cv2.rectangle(crop, (c0 + x - ox, y), (c0 + x + w - ox, y + hh), (0, 180, 0), 2)
    cv2.putText(crop, "brush: red = clay box D8xH38, green = black component", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
    draw.append(cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    return rec


if __name__ == "__main__":
    draw = []
    out = {}
    b1 = C.SC3["B1"]["boxes"]["bath/floor-planter"]["box"]
    b2 = C.SC3["B2"]["boxes"]["bath/floor-planter"]["box"]
    out["B1 r3 planter"] = planter("B1 r3", (0.49, 0.555), (0.75, 0.877), b1, draw)
    out["B2 r3 planter"] = planter("B2 r3", (0.02, 0.12), (b2[3] - 0.27 * (b2[3] - b2[2]), b2[3]), b2, draw)
    out["B1 r3 brush"] = brush(draw)
    hmax = max(c.shape[0] for c in draw)
    sheet = np.concatenate([np.pad(c, ((0, hmax - c.shape[0]), (0, 12), (0, 0)), constant_values=255) for c in draw], axis=1)
    cv2.imwrite(os.path.join(C.OUT, "overlays", "bath-products.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
    json.dump(out, open(os.path.join(C.OUT, "data", "bath-products.json"), "w"), indent=1, ensure_ascii=False)
    for k, v in out.items():
        print(k, json.dumps({a: b for a, b in v.items() if a != "row_labels_runs"}, ensure_ascii=False))
