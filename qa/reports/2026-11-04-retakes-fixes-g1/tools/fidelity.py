"""
G1.1 / G1.3 on every object the code fixes scaled or moved, against its clay box +-15 %, on the graded-fix-v4 files:
  K-girl-0 r2 fix  the print pair and the doll: extent of the object on its plain wall (dE > 10 from the ring background)
  B1 r3 fix        the seagrass basket, the plinth rows and the fern (row profiles in the clay pot's columns, as on 11-03),
                   the brush (the matte-black component): height / width against the box and the holder / handle split
  B2 r3 fix        the planter (row profiles), the storage basket (extent on the shelf), the towel ring
  W0-in r2 fix     the pen cup (extent on the plain wall above the desk)
Also the fidelity sheets (crops with the clay box in red and +-15 % in yellow). Re-uses the 11-03 tools (imported, not edited).
Writes data/fidelity.json, overlays/fidelity-<id>.jpg.
"""
import importlib.util
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def _imp(name, rel):
    s = importlib.util.spec_from_file_location(name, os.path.join(C.REPO, rel))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


F3 = _imp("qa1103_fidelity", "qa/reports/2026-11-03-retakes-g1/tools/fidelity.py")
B3 = _imp("qa1103_bath", "qa/reports/2026-11-03-retakes-g1/tools/bath_products.py")


def sheet(sid):
    d = C.load(sid, raw=False)
    img8 = C.pr.to8(d["graded"])
    H, W = img8.shape[:2]
    tiles, rec = [], {}
    for nm, (kind, box, area, vis) in sorted(C.boxes(d).items()):
        if kind not in ("proxy", "proxy-transit"):
            continue
        u0, u1, v0, v1 = box
        bw, bh = (u1 - u0), (v1 - v0)
        X0, X1 = int(max(0, u0 - 0.4 * bw) * W), int(min(1, u1 + 0.4 * bw) * W)
        Y0, Y1 = int(max(0, v0 - 0.4 * bh) * H), int(min(1, v1 + 0.4 * bh) * H)
        if X1 - X0 < 4 or Y1 - Y0 < 4:
            continue
        crop = img8[Y0:Y1, X0:X1].copy()
        ox, oy = int(u0 * W) - X0, int(v0 * H) - Y0
        cv2.rectangle(crop, (ox, oy), (ox + int(bw * W), oy + int(bh * H)), (255, 60, 40), max(1, int(bw * W / 150)))
        px, py = int(0.15 * bw * W), int(0.15 * bh * H)
        cv2.rectangle(crop, (ox - px, oy - py), (ox + int(bw * W) + px, oy + int(bh * H) + py), (255, 210, 60), 1)
        e = F3.extent(img8, box)
        rec[nm] = dict(box_uv=[round(x, 4) for x in box], box_px=[int(bw * W), int(bh * H)], extent_estimate=e)
        sub = f"{int(bw * W)}x{int(bh * H)}px" + (f" est {e['width_ratio']}x{e['height_ratio']}" if e and e.get("found") else "")
        tiles.append(F3.tile(cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), nm.split("/", 1)[-1], sub))
    cv2.imwrite(os.path.join(C.OUT, "overlays", f"fidelity-{C.fn(sid)}.jpg"), F3.grid(tiles), [cv2.IMWRITE_JPEG_QUALITY, 82])
    return rec


def brush(sid):
    d = C.load(sid, raw=False)
    a = d["graded_canvas"]
    Hc, Wc = a.shape[:2]
    Hh, S, L = B3.hsl_rows(a)
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
    hold = np.nonzero(rows_w >= 0.7 * rows_w.max())[0]
    holder_h = int(hold.max() - hold.min() + 1) if len(hold) else 0
    box_h, box_w = (v1 - v0) * Hc, (u1 - u0) * Wc
    return dict(box_px=[int(box_w), int(box_h)], render_px=[int(w), int(hh)], height_ratio_to_box=round(hh / box_h, 2), holder_width_ratio_to_box=round(rows_w.max() / box_w, 2),
                holder_share_of_height=round(holder_h / hh, 2), handle_share_of_height=round(1 - holder_h / hh, 2),
                card="8 x 38 cm: holder 14.5 (38 %), handle 25 (66 % of the height above the holder's top)",
                top_minus_box_top_px=int(r0 + y - v0 * Hc), bottom_minus_box_bottom_px=int(r0 + y + hh - v1 * Hc))


def planter(sid, pot_cols, pot_v, box):
    draw = []
    r = B3.planter(sid, pot_cols, pot_v, box, draw)
    r.pop("row_labels_runs", None)
    return r, draw


if __name__ == "__main__":
    out = {}
    for sid in C.FIX_IDS:
        out[sid] = dict(sheet=sheet(sid))
    b1 = C.SC3["B1"]["boxes"]["bath/floor-planter"]["box"]
    b2 = C.SC3["B2"]["boxes"]["bath/floor-planter"]["box"]
    p1, d1 = planter("B1 r3 fix", (0.49, 0.555), (0.75, 0.877), b1)
    p2, d2 = planter("B2 r3 fix", (0.02, 0.12), (b2[3] - 0.27 * (b2[3] - b2[2]), b2[3]), b2)
    out["B1 r3 fix"]["planter"], out["B2 r3 fix"]["planter"] = p1, p2
    out["B1 r3 fix"]["brush"] = brush("B1 r3 fix")
    draws = d1 + d2
    hmax = max(c.shape[0] for c in draws)
    cv2.imwrite(os.path.join(C.OUT, "overlays", "bath-planters.jpg"),
                np.concatenate([np.pad(c, ((0, hmax - c.shape[0]), (0, 12), (0, 0)), constant_values=255) for c in draws], axis=1), [cv2.IMWRITE_JPEG_QUALITY, 85])
    json.dump(out, open(os.path.join(C.OUT, "data", "fidelity.json"), "w"), indent=1, ensure_ascii=False, default=float)
    for sid, v in out.items():
        print("==", sid)
        for nm, r in v["sheet"].items():
            e = r["extent_estimate"] or {}
            print(f"   {nm:32s} box {r['box_px']} est {e.get('width_ratio')} x {e.get('height_ratio')} centre ({e.get('centre_du')}, {e.get('centre_dv')}) touches {e.get('touches_expanded_box')}")
        for k in ("planter", "brush"):
            if k in v:
                print("  ", k, json.dumps(v[k], default=float)[:900])
