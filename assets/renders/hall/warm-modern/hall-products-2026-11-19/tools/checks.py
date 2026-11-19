#!/usr/bin/env python3
"""
checks.py: the measurements for QA of the HT2 / HDx2 product pass, render-agent 2026-11-19. 0 tokens. Reads the written files only.
  - positions (u, v of each alpha at 50 %) against 4.4 / 8.1
  - the throw's thickness at the front (8.1: 7-9 cm, 3.5-4.5 % of the frame's height) and its drop (about 15 cm)
  - colours in the scene (Lab medians on each alpha's solid core) against house20-photo-check.json, with the still's cast
    (ht2.png's plaster against #ECE5DA: about -13 deg of hue)
  - 8.2: the lamp's walnut block against the seat (hue within 10 deg, C*/L* at most 25 % above the seat's)
  - the black point (the 16:9 frame's p0.1 before / after) and the walnut floor (12.7: >= 8 L* over it)
  - how much of the basket the throw's panel hides
  python3 checks.py  ->  OUT/checks.json
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose as C  # noqa: E402
import geo as G  # noqa: E402

K = G.K


def lab_med(rgb8, m):
    lab = K.lab_from_lin(K.to_lin(rgb8[m] / 255.0))
    a, b = float(np.median(lab[:, 1])), float(np.median(lab[:, 2]))
    L = float(np.median(lab[:, 0]))
    Cc = float(np.hypot(a, b))
    return dict(L=round(L, 1), C=round(Cc, 1), h=round(float(np.degrees(np.arctan2(b, a))), 1), C_over_L=round(Cc / max(L, 1e-3), 3), px=int(m.sum()))


def main():
    O = G.OUT
    man = json.load(open(os.path.join(O, "layers", "manifest.json")))
    fin = C.rgb8(os.path.join(O, "ht2-products.png"))
    base = C.rgb8(C.BASE)
    cv = K.canvas("HT")
    rep = dict(frame="HT2", positions={}, colours={})
    alphas = {}
    for e in man["layers"]:
        A = np.asarray(Image.open(os.path.join(O, e["layer"])))[..., 3]
        alphas[e["slot"]] = A
        ys, xs = np.nonzero(A >= 128)
        u0, v0 = K.uv_of_px("HT", xs.min() - 0.5, ys.min() - 0.5)
        u1, v1 = K.uv_of_px("HT", xs.max() + 0.5, ys.max() + 0.5)
        rep["positions"][e["slot"]] = dict(u=[round(u0, 4), round(u1, 4)], v=[round(v0, 4), round(v1, 4)])
    rep["positions"]["designer_4_4"] = {"wall-sconce": "u 0.638-0.654, v 0.21-0.33 (stone-plane mapping; the cylinder stands 4.5 cm off the stone)",
                                        "wall-hooks": "u 0.48-0.57, v 0.28-0.31", "bench-throw": "u 0.555-0.652, v 0.77-0.88 (with the old 30x35 fold)",
                                        "basket": "u 0.62-0.70, v 0.88-0.98 (centred at Y 7.10: the clay gives u 0.589-0.674)"}
    # the throw: thickness at the front and the drop, from the clay landmarks the remap lands on (compose.THROW_KNOTS)
    fh = cv.fh
    front_px = C.THROW_KNOTS[2][0] - C.THROW_KNOTS[1][0]
    drop_px = C.THROW_KNOTS[-1][0] - C.THROW_KNOTS[2][0]
    cg = K.cg
    px_per_m = cg.KV * fh / (3.60 - 1.21)                          # vertical px per metre at the seat's front edge (X 1.21)
    rep["throw"] = dict(front_canvas_px=round(front_px, 1), front_frame_pct=round(100 * front_px / fh, 2), front_cm=round(100 * front_px / px_per_m, 1),
                        target="7-9 cm, 3.5-4.5 % of the frame height (8.1)", drop_canvas_px=round(drop_px, 1),
                        drop_cm=round(100 * drop_px / (cg.KV * fh / (3.60 - 1.222)), 1), drop_target="about 15 cm",
                        bare_walnut_cm=round(100 * (G.THROW["y"][0] - 6.70), 1))
    # colours (in the scene), each alpha's solid core (255, eroded 2)
    k = np.ones((5, 5), np.uint8)
    cores = {s: cv2.erode((A == 255).astype(np.uint8), k) > 0 for s, A in alphas.items()}
    cyl = G.cylinder_alpha()[0] >= 1.0
    cyl = cv2.erode(cyl.astype(np.uint8), k) > 0
    blk = (alphas["wall-sconce"] == 255) & ~(G.cylinder_alpha()[0] > 0)
    cast = C.scene_cast(base / 255.0)
    rep["colours"] = {
        "scene_cast_deg": round(cast, 1),
        "lamp_travertine": dict(scene=lab_med(fin, cyl), photo="A 28: L* 76.3, C* 19.0, h 74 (lit); card hex #D8C3A5 L* 80 C* 18 h 81"),
        "lamp_walnut_block": dict(scene=lab_med(fin, blk), photo="L* 32.5, C* 38.4, h 61 (lit by its own lamp)"),
        "pegs": dict(scene=lab_med(fin, cores["wall-hooks"]), photo="block L* 49.5 C* 13.7 h 50 (SKU); row of 4: L* 24.2 C* 20.7 h 48"),
        "throw": dict(scene=lab_med(fin, cores["bench-throw"]), photo="khaki: L* 64-75, C* 8-11, h 79-80 (SKU, real close-up, bed)"),
        "basket": dict(scene=lab_med(fin, cores["basket"]), photo="cream: L* 82.8, C* 11.5, h 85 (shade side, real photo)"),
        "seat_top_ht2": dict(L=51.7, C=26.28, h=57.2, C_over_L=0.509, source="ht2-lock.json seat_hue_vs_lining_12_7_2"),
    }
    bl = rep["colours"]["lamp_walnut_block"]["scene"]
    rep["check_8_2_block_vs_seat"] = dict(dh_deg=round(bl["h"] - 57.2, 1), C_over_L_vs_seat_pct=round(100 * (bl["C_over_L"] / 0.509 - 1), 1),
                                          rule="back to the designer if |dh| > 10 or C*/L* (or L*) more than 25 % above the seat's, at x1",
                                          passes=bool(abs(bl["h"] - 57.2) <= 10 and bl["C_over_L"] <= 0.509 * 1.25))
    # black point: the 16:9 frame, before / after
    x0, y0, x1, y1 = (int(round(v)) for v in cv.box)
    Lb = K.lab_from_lin(K.to_lin(base[y0:y1, x0:x1] / 255.0))[..., 0]
    Lf = K.lab_from_lin(K.to_lin(fin[y0:y1, x0:x1] / 255.0))[..., 0]
    rep["black_point"] = dict(frame_p01_before=round(float(np.percentile(Lb, 0.1)), 2), frame_p01_after=round(float(np.percentile(Lf, 0.1)), 2),
                              frame_p05_before=round(float(np.percentile(Lb, 0.5)), 2), frame_p05_after=round(float(np.percentile(Lf, 0.5)), 2),
                              walnut_floor=C.WALNUT_FLOOR, tone=man.get("tone"))
    # the basket under the throw's panel
    _, bfull, _ = G.render("basket")
    bfull &= ~G.bench_mask()
    fr = np.zeros(bfull.shape, bool)
    fr[y0:y1, x0:x1] = True
    hidden = bfull & (alphas["bench-throw"] >= 128) & fr
    rep["basket_hidden_by_panel_pct_in_frame"] = round(100 * hidden.sum() / max((bfull & fr).sum(), 1), 1)
    # HDx2
    mh = json.load(open(os.path.join(O, "hdx2", "manifest.json")))
    fh2 = C.rgb8(os.path.join(O, "hdx2-products.png"))
    A2 = np.asarray(Image.open(os.path.join(O, "hdx2", mh["layers"][0]["layer"])))[..., 3]
    rep["hdx2"] = dict(lamp_uv=mh["lamp_uv"], method=mh["method"], rnd2=mh["rnd2"],
                       lamp_scene=lab_med(fh2, cv2.erode((A2 == 255).astype(np.uint8), k) > 0))
    rep["rnd2_ht2"] = man["rnd2"]
    K.dump(os.path.join(O, "checks.json"), rep)
    print(json.dumps(rep, indent=1)[:6000])


if __name__ == "__main__":
    main()
