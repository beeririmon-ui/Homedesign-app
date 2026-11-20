#!/usr/bin/env python3
"""
work_prints.py: the 386242 prints set into the W0 frames in code (render-agent, 2026-11-20; 0 tokens), MB1's method (mb1_prints.py):
the model drew the frames with blank canvases (#D8C8AE, never the art). Per frame: the canvas is the blank in the frame layer (Lab
within 10 of its median, the largest piece); the flat print (the listing file, its white margin and drop shadow cropped 4 px inside the
print's edge) is cover-fitted to the canvas's quad (the camera's projection of the clay canvas, moved and scaled to the blank's bounds
as the edit drew it) and lit by the canvas's own light in the edit (its linear colour over #D8C8AE's, 1.5 px blur), so the window's
fall-off, the frame's inner shadow and the room's warmth carry onto it. Only the canvas pixels of the frame layers change.
  - framed-art (the sample slot): V1 08 in the default layer; V2 01 and V3 02 as variant layers of the same frame (same shadow);
  - framed-art-2: 03 (portrait) in the default layer.
Rights: usage_rights unclear (ch. 4): room exposure only, no close-up, no WK-z.
  python3 work_prints.py            (after work_compose.py pA-wall and pC-sides; then work_compose.py compose and work_variants.py)
"""
import json
import os
import shutil
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import work_common as M  # noqa: E402

C = M.C
H, W = M.H, M.W
ST = M.ST
CANVAS_ALBEDO = np.array([216, 200, 174]) / 255
LAND = (38, 125, 766, 668)            # the landscape prints' area in the 800 x 800 listing files, 4 px inside the edge
PORT = (130, 40, 676, 768)            # the portrait 03
FILES = {"08": ("e1cd7118_Sabff5188ff2c40d0a5e0885cf7cda14a8.jpg", LAND), "01": ("861b3959_S0c6d91355e12444388ff139962b388021.jpg", LAND),
         "02": ("3c7ae46f_S31ea5f0037c44870a4ca50c90fe2d0fbN.jpg", LAND), "03": ("a8f677a3_S665556398d754e26acbb536bb1e1d2f1r.jpg", PORT)}
XR = 0.649 - 0.03 + 0.010                                       # the right-wall canvas face (the clay)
FRAMES = {"framed-art": dict(quad3=[(-1.025, 6.37, 1.38), (-0.625, 6.37, 1.38), (-0.625, 6.37, 1.08), (-1.025, 6.37, 1.08)],
                             default="08", variants=["01", "02"], size_m=(0.40, 0.30)),
          "framed-art-2": dict(quad3=[(XR, 7.10, 1.62), (XR, 7.40, 1.62), (XR, 7.40, 1.22), (XR, 7.10, 1.22)],
                               default="03", variants=[], size_m=(0.30, 0.40))}
CARD = "framed-art-aliexpress-misty-landscape-386242-work"


def canvas_mask(rgb, a):
    lab = C.to_lab(rgb)
    opaque = a > 0.99
    # (2026-11-20, after the restart) 9, not 22: the bone mat reads about 18 from #D8C8AE and the canvas about 4, so at 22 the mat (the
    # larger area) pulled the median between the two and the mask took the mat too
    cand = opaque & (np.linalg.norm(lab - C.to_lab(CANVAS_ALBEDO[None, None, :])[0, 0][None, None, :], axis=-1) < 9)
    med = np.median(lab[cand], 0)
    cv = opaque & (np.linalg.norm(lab - med[None, None, :], axis=-1) < 8)
    cv = cv2.morphologyEx(cv.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(3)).astype(bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(cv.astype(np.uint8), connectivity=8)
    cv = lb == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    # (2026-11-20, after the restart) open by 4 px and keep the largest piece again: a few stray mat pixels joined to the canvas by
    # thin bridges set the bounds at the mat's outer edge (1226-1497 for a canvas at 1262-1454), so the print would have covered the mat
    cv = cv2.morphologyEx(cv.astype(np.uint8), cv2.MORPH_OPEN, C.disk(4)).astype(bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(cv.astype(np.uint8), connectivity=8)
    cv = lb == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return C.ero(cv, 1), med


def fit_quad(quad, cv):
    """move and scale the analytic quad so its bounds are the blank's bounds (the edit drew the canvas a few px off the clay)"""
    ys, xs = np.nonzero(cv)
    bx0, bx1, by0, by1 = xs.min() - 1, xs.max() + 2, ys.min() - 1, ys.max() + 2
    q = np.array(quad, np.float64)
    qx0, qx1, qy0, qy1 = q[:, 0].min(), q[:, 0].max(), q[:, 1].min(), q[:, 1].max()
    sx, sy = (bx1 - bx0) / (qx1 - qx0), (by1 - by0) / (qy1 - qy0)
    out = np.stack([bx0 + (q[:, 0] - qx0) * sx, by0 + (q[:, 1] - qy0) * sy], 1)
    return out.astype(np.float32), dict(analytic_bounds=[round(float(v), 1) for v in (qx0, qy0, qx1, qy1)],
                                        blank_bounds=[int(bx0), int(by0), int(bx1), int(by1)], scale=[round(float(sx), 4), round(float(sy), 4)])


def set_print(rgb, a, cv, quad, key, size_m):
    f, box = FILES[key]
    pr = C.load(M.PICKS + f)[box[1]:box[3], box[0]:box[2]]
    ph, pw = pr.shape[:2]
    cw, chh = size_m
    k = max(cw / pw, chh / ph)
    sw, sh = cw / k, chh / k
    ox, oy = (pw - sw) / 2, (ph - sh) / 2
    src = np.float32([[ox, oy], [ox + sw, oy], [ox + sw, oy + sh], [ox, oy + sh]])
    Hm = cv2.getPerspectiveTransform(src, quad)
    warped = cv2.warpPerspective(C.lin(pr).astype(np.float32), Hm, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
    light = C.blur(C.lin(rgb), 1.5) / C.lin(CANVAS_ALBEDO)[None, None, :]
    lit = C.srgb(np.clip(warped * light, 0, 1))
    w = C.blur(cv.astype(np.float64), 0.7) * cv
    out = rgb * (1 - w[..., None]) + lit * w[..., None]
    rgba8 = np.dstack([C.q(out), C.q(a)])
    rgba8[..., :3][rgba8[..., 3] == 0] = 0
    return rgba8, dict(file=f.split("_")[0] + " (listing file, scratchpad only)", print_px=[pw, ph], window_px=[round(sw, 1), round(sh, 1)],
                       canvas_light_p5_p50_p95=[round(float(v), 3) for v in np.percentile(C.luma(light[cv]), [5, 50, 95])])


def main():
    mp = os.path.join(ST, "layers", "manifest.json")
    man = json.load(open(mp))
    rec = {}
    raw_dir = os.path.join(M.SCR, "blank-frames")
    os.makedirs(raw_dir, exist_ok=True)
    for slot, F in FRAMES.items():
        l = [x for x in man["layers"] if x["slot"] == slot and x.get("default")][0]
        lp = os.path.join(ST, l["layer"])
        blank = os.path.join(raw_dir, os.path.basename(lp))       # the blank-canvas layer as work_compose.py wrote it
        rgba = np.asarray(Image.open(blank)).astype(np.float64) / 255
        rgb, a = rgba[..., :3], rgba[..., 3]
        cv, med = canvas_mask(rgb, a)
        quad, qrec = fit_quad([M.proj(*p) for p in F["quad3"]], cv)
        r = dict(canvas_px=int(cv.sum()), canvas_Lab_in_edit=[round(float(v), 1) for v in med], quad=[[round(float(v), 1) for v in q] for q in quad], **qrec)
        rgba8, pr = set_print(rgb, a, cv, quad, F["default"], F["size_m"])
        Image.fromarray(rgba8, "RGBA").save(lp)
        r[F["default"]] = pr
        l["print"] = f"386242-{F['default']} set in code (tools/work_prints.py) from the flat file"
        l["closeup"] = False
        l["closeup_note"] = "386242: usage_rights unclear (ch. 4): room exposure only, no close-up, no WK-z"
        man["layers"] = [x for x in man["layers"] if not (x["slot"] == slot and not x.get("default"))]
        for v in F["variants"]:
            rgba_v, pv = set_print(rgb, a, cv, quad, v, F["size_m"])
            pid = f"{CARD}-{v}-30x40"
            vp = os.path.join(ST, "layers", slot, pid + ".png")
            Image.fromarray(rgba_v, "RGBA").save(vp)
            sp = os.path.join(ST, "shadows", slot, pid + ".png")
            shutil.copy(os.path.join(ST, l["shadow"]), sp)
            man["layers"].append(dict(l, product=pid, default=False, layer=os.path.relpath(vp, ST), shadow=os.path.relpath(sp, ST),
                                      print=f"386242-{v} set in code (tools/work_prints.py) from the flat file",
                                      source="the default frame layer (pA-wall) with another print of the same listing, in code: 0 tokens",
                                      variant_of=l["product"]))
            r[v] = pv
        rec[slot] = r
    man["layers"].sort(key=lambda x: (x["z"], x["slot"], not x.get("default")))
    json.dump(man, open(mp, "w"), indent=1)
    rp = os.path.join(ST, "w0-compose.json")
    rr = json.load(open(rp))
    rr["prints"] = rec
    json.dump(rr, open(rp, "w"), indent=1)
    print(json.dumps(rec)[:1500])


if __name__ == "__main__":
    main()
