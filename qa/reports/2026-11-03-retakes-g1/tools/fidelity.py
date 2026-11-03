"""
G1.1-G1.3 fidelity on the four retakes: a sheet per still with every product's clay box cut from the graded-v3 render
(box + 40 % margin, the clay box in red, the +-15 % band in yellow) and, under it, the references the render-agent sent
(refs/index-retakes-2026-11-03.json: cut-outs of the accepted masters and the two new product cards), plus an extent
estimate of the drawn object inside the expanded box on plain backgrounds (pixels that differ from the ring background by
dE > 10). Then the measurements the brief asks for on the two new bath products and the invented plinth of B1 r3:
  planter  the basket's silhouette (seagrass hue) and the grey stone cylinder under it, column by column: top / bottom rows
           of the basket and of the plinth in the frame, against the clay's pot box (B1 r3: pot y 0.75-0.877 of the canvas)
  brush    the matte-black cylinder (L < 25) in / around its clay box: height and width against the box and the card (8 x 38 cm)
Writes overlays/fidelity-<id>.jpg, data/fidelity-<id>.json, data/bath-products.json.
"""
import colorsys
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

IDX = json.load(open(os.path.join(C.REPO, "assets/renders/house-nordic-v7-2026-11-02/refs/index-retakes-2026-11-03.json")))["refs"]
REFS = {"W0-in r2": [k for k in IDX if k.startswith("w0in")], "K-girl-0 r2": [k for k in IDX if k.startswith("kgirl0")],
        "B1 r3": [k for k in IDX if k.startswith("b1r3")] + ["planter-seagrass-30", "toilet-brush-black"],
        "B2 r3": [k for k in IDX if k.startswith("b2r3")] + ["planter-seagrass-30"]}
TILE = 300


def tile(img, label, sub=""):
    h, w = img.shape[:2]
    s = TILE / max(h, w)
    im = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
    canvas = np.full((TILE + 36, TILE, 3), 245, np.uint8)
    y0, x0 = (TILE - im.shape[0]) // 2, (TILE - im.shape[1]) // 2
    canvas[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = im
    cv2.putText(canvas, label[:32], (3, TILE + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (20, 20, 20), 1)
    cv2.putText(canvas, sub[:36], (3, TILE + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (90, 90, 90), 1)
    return canvas


def grid(tiles, cols=6):
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    blank = np.full_like(tiles[0], 255)
    return np.concatenate([np.concatenate(r + [blank] * (cols - len(r)), axis=1) for r in rows], axis=0)


def extent(img8, box, margin=0.5):
    H, W = img8.shape[:2]
    u0, u1, v0, v1 = box
    bw, bh = (u1 - u0), (v1 - v0)
    X0, X1 = int(max(0, u0 - margin * bw) * W), int(min(1, u1 + margin * bw) * W)
    Y0, Y1 = int(max(0, v0 - margin * bh) * H), int(min(1, v1 + margin * bh) * H)
    if X1 - X0 < 8 or Y1 - Y0 < 8:
        return None
    lab = cv2.cvtColor(img8[Y0:Y1, X0:X1], cv2.COLOR_RGB2LAB).astype(np.float32)
    ring = np.concatenate([lab[:3].reshape(-1, 3), lab[-3:].reshape(-1, 3), lab[:, :3].reshape(-1, 3), lab[:, -3:].reshape(-1, 3)])
    bg = np.median(ring, axis=0)
    de = np.sqrt(((lab - bg) ** 2).sum(2))
    m = (de > 10).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    ys, xs = np.nonzero(m)
    if len(xs) < 20:
        return dict(found=False)
    x0, x1, y0, y1 = xs.min() + X0, xs.max() + X0, ys.min() + Y0, ys.max() + Y0
    return dict(found=True, extent_uv=[round(x0 / W, 4), round(x1 / W, 4), round(y0 / H, 4), round(y1 / H, 4)],
                width_ratio=round((x1 - x0) / max(1, bw * W), 2), height_ratio=round((y1 - y0) / max(1, bh * H), 2),
                centre_du=round(((x0 + x1) / 2 / W - (u0 + u1) / 2) / bw, 2), centre_dv=round(((y0 + y1) / 2 / H - (v0 + v1) / 2) / bh, 2),
                touches_expanded_box=bool(xs.min() == 0 or ys.min() == 0 or xs.max() == X1 - X0 - 1 or ys.max() == Y1 - Y0 - 1))


def run(sid):
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
        e = extent(img8, box)
        rec[nm] = dict(box_uv=[round(x, 4) for x in box], box_px=[int(bw * W), int(bh * H)], visible_pct_clay=vis, extent_estimate=e)
        sub = f"{int(bw * W)}x{int(bh * H)}px" + (f" est {e['width_ratio']}x{e['height_ratio']}" if e and e.get("found") else "")
        tiles.append(tile(cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), nm.split("/", 1)[-1], sub))
    rtiles = []
    for i, k in enumerate(REFS[sid]):
        r = IDX[k]
        f = r.get("file")
        if f and os.path.exists(os.path.join(C.REPO, f)):
            im = cv2.imread(os.path.join(C.REPO, f))
            if im is not None:
                rtiles.append(tile(im, f"ref {i + 1}: {k}"[:32], (r.get("note") or "")[:36]))
    sheet = grid(tiles) if tiles else None
    if rtiles:
        rg = grid(rtiles)
        if sheet is not None and rg.shape[1] != sheet.shape[1]:
            wmax = max(rg.shape[1], sheet.shape[1])
            sheet = np.pad(sheet, ((0, 0), (0, wmax - sheet.shape[1]), (0, 0)), constant_values=255)
            rg = np.pad(rg, ((0, 0), (0, wmax - rg.shape[1]), (0, 0)), constant_values=255)
        bar = np.full((30, sheet.shape[1], 3), 200, np.uint8)
        cv2.putText(bar, f"{sid}: render crops (red = clay box, yellow = +-15 %) above; the references the render-agent sent below", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        sheet = np.concatenate([sheet, bar, rg], axis=0)
    cv2.imwrite(os.path.join(C.OUT, "overlays", f"fidelity-{C.fn(sid)}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
    json.dump(dict(frame=sid, products=rec, refs=REFS[sid]), open(os.path.join(C.OUT, "data", f"fidelity-{C.fn(sid)}.json"), "w"), indent=1, ensure_ascii=False)
    print(sid, len(tiles), "product tiles,", len(rtiles), "refs;", {k.split('/')[-1]: ((v['extent_estimate'] or {}).get('width_ratio'), (v['extent_estimate'] or {}).get('height_ratio')) for k, v in rec.items()})
    return rec


def hsl_img(a):
    out = np.zeros_like(a)
    mx, mn = a.max(2), a.min(2)
    L = (mx + mn) / 2
    S = np.where(mx == mn, 0, np.where(L <= 0.5, (mx - mn) / (mx + mn + 1e-6), (mx - mn) / (2 - mx - mn + 1e-6)))
    hsv = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    Hh = hsv[..., 0].astype(np.float32) * 2
    return Hh, S * 100, L * 100


def bath_products():
    """Planter, plinth and brush in B1 r3 (and the planter in B2 r3), measured on the graded-v3 canvas (box coordinates)."""
    out = {}
    for sid in ("B1 r3", "B2 r3"):
        d = C.load(sid, raw=False)
        a = d["graded_canvas"]
        Hc, Wc = a.shape[:2]
        Hh, S, L = hsl_img(a)
        sc = d["sc"]
        rec = {}
        pb = sc["boxes"]["bath/floor-planter"]["box"]
        u0, u1, v0, v1 = pb
        X0, X1 = int(u0 * Wc), int(u1 * Wc)
        # seagrass basket: warm tan, H 20-45, S 25-70, L 35-75 ; stone plinth: low chroma S < 14, L 55-85 ; fern: H 60-170
        reg = slice(int((v0 - 0.02) * Hc), int(min(1, v1 + 0.08) * Hc)), slice(max(0, X0 - int(0.03 * Wc)), min(Wc, X1 + int(0.03 * Wc)))
        h, s, l = Hh[reg], S[reg], L[reg]
        basket = (h >= 20) & (h <= 45) & (s >= 25) & (s <= 75) & (l >= 30) & (l <= 78)
        plinth = (s < 14) & (l >= 50) & (l <= 85)
        fern = (h >= 60) & (h <= 170) & (s >= 8)
        basket = cv2.morphologyEx(basket.astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
        fern = cv2.morphologyEx(fern.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        n, lab, stats, _ = cv2.connectedComponentsWithStats(basket)
        if n > 1:
            i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            bx, by, bw, bh = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            by0, by1 = reg[0].start + by, reg[0].start + by + bh
            bx0, bx1 = reg[1].start + bx, reg[1].start + bx + bw
            # the plinth: low-chroma stone directly under the basket, within the basket's columns
            cols = slice(bx0 + bw // 4, bx1 - bw // 4)
            rows = slice(by1, min(Hc, by1 + int(0.25 * Hc)))
            pl = plinth[rows.start - reg[0].start:rows.stop - reg[0].start, cols.start - reg[1].start:cols.stop - reg[1].start]
            frac = pl.mean(1)
            run_ = np.where(frac > 0.6)[0]
            plinth_h = 0
            if len(run_):
                # the first contiguous run from the basket bottom
                k = 0
                while k < len(frac) and frac[k] > 0.5:
                    k += 1
                plinth_h = k
            pot_box_h = (v1 - v0) * Hc
            # the clay's pot (cylinder) is the lower part of the planter box: from the prompt header, pot y 0.75-0.877 (B1 r3) / the lower 27 % (B2)
            pot_v = (0.75, 0.877) if sid == "B1 r3" else (v1 - 0.27 * (v1 - v0), v1)
            pot_px = (pot_v[1] - pot_v[0]) * Hc
            fy, fx = np.nonzero(fern)
            rec["planter"] = dict(clay_box_uv=[round(x, 4) for x in pb], clay_pot_v=[round(x, 4) for x in pot_v],
                                  basket_uv=[round(bx0 / Wc, 4), round(bx1 / Wc, 4), round(by0 / Hc, 4), round(by1 / Hc, 4)],
                                  basket_px=[int(bw), int(bh)], basket_width_over_pot_box=round(bw / ((u1 - u0) * Wc), 2) if sid == "B1 r3" else None,
                                  basket_height_over_pot_box=round(bh / pot_px, 2), basket_bottom_minus_pot_bottom_px=int(by1 - pot_v[1] * Hc),
                                  basket_top_minus_pot_top_px=int(by0 - pot_v[0] * Hc),
                                  plinth_rows_under_basket_px=int(plinth_h), plinth_height_over_pot_box=round(plinth_h / pot_px, 2),
                                  plinth_height_cm_if_pot_is_30=round(30 * plinth_h / pot_px, 1),
                                  basket_plus_plinth_height_cm_if_pot_is_30=round(30 * (bh + plinth_h) / pot_px, 1),
                                  fern_top_v=round((reg[0].start + fy.min()) / Hc, 4) if len(fy) else None, fern_top_minus_box_top_px=int(reg[0].start + fy.min() - v0 * Hc) if len(fy) else None,
                                  basket_median_HSL=[round(float(np.median(h[basket > 0])), 1), round(float(np.median(s[basket > 0])), 1), round(float(np.median(l[basket > 0])), 1)],
                                  fern_median_HSL=[round(float(np.median(h[fern > 0])), 1), round(float(np.median(s[fern > 0])), 1), round(float(np.median(l[fern > 0])), 1)] if len(fy) else None)
        if sid == "B1 r3":
            bb = sc["boxes"]["bath/toilet-brush"]["box"]
            u0, u1, v0, v1 = bb
            reg2 = slice(int((v0 - 0.06) * Hc), int(min(1, v1 + 0.04) * Hc)), slice(int((u0 - 0.03) * Wc), int((u1 + 0.03) * Wc))
            dark = (L[reg2] < 28).astype(np.uint8)
            dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            n, lab, stats, _ = cv2.connectedComponentsWithStats(dark)
            if n > 1:
                i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
                x, y, w, hh = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
                # the cylinder (holder) width: the widest row of the component's lower half
                comp = (lab == i)
                rows_w = comp[hh // 2 + y:y + hh].sum(1)
                cyl_w = int(np.percentile(rows_w[rows_w > 0], 90)) if (rows_w > 0).any() else 0
                bx0, bx1, by0, by1 = reg2[1].start + x, reg2[1].start + x + w, reg2[0].start + y, reg2[0].start + y + hh
                box_h, box_w = (v1 - v0) * Hc, (u1 - u0) * Wc
                rec["brush"] = dict(clay_box_uv=[round(x_, 4) for x_ in bb], box_px=[int(box_w), int(box_h)],
                                    render_uv=[round(bx0 / Wc, 4), round(bx1 / Wc, 4), round(by0 / Hc, 4), round(by1 / Hc, 4)],
                                    render_px=[int(w), int(hh)], cylinder_width_px=cyl_w,
                                    height_ratio_to_box=round(hh / box_h, 2), cylinder_width_ratio_to_box=round(cyl_w / box_w, 2),
                                    top_minus_box_top_px=int(by0 - v0 * Hc), bottom_minus_box_bottom_px=int(by1 - v1 * Hc),
                                    card="toilet-brush-aliexpress-matte-black-steel-cylinder-245996: 8 x 38 cm; the clay box is D8 x H38 at (4.70, 10.30)",
                                    median_L_of_body=round(float(np.median(L[reg2][comp])), 1))
            # the roll stand beside it for scale: the clay box of the stand
            sbx = sc["boxes"]["bath/toilet-paper-stand"]["box"]
            rec["stand_box_height_px"] = int((sbx[3] - sbx[2]) * Hc)
            rec["brush_box_over_stand_box"] = round(((bb[3] - bb[2]) / (sbx[3] - sbx[2])), 3)
        out[sid] = rec
        print(sid, json.dumps(rec, ensure_ascii=False)[:1500])
    json.dump(out, open(os.path.join(C.OUT, "data", "bath-products.json"), "w"), indent=1, ensure_ascii=False)
    return out


if __name__ == "__main__":
    for f in (sys.argv[1:] or C.RETAKES):
        run(f)
    bath_products()
