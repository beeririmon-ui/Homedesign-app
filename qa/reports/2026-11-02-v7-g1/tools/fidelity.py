"""
G1.1-G1.3 fidelity sheets for every master: each product's clay box cut from the graded render (box + 40 % margin, the clay box
drawn in red, the +-15 % band in yellow), and under it the frame's reference images as the render-agent listed them
(refs/index-v7.json). The eye verdict per product is written in the report. Also an estimate of the drawn object's extent
inside the expanded box (pixels that differ from the ring background by dE > 10): informational, confounded where the
background is textured. Writes overlays/fidelity-<id>.jpg and data/fidelity-<id>.json.
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

IDX = json.load(open(os.path.join(C.REPO, "assets/renders/house-nordic-v7-2026-11-02/refs/index-v7.json")))
TILE = 300


def tile(img, label, sub=""):
    h, w = img.shape[:2]
    s = TILE / max(h, w)
    im = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
    canvas = np.full((TILE + 36, TILE, 3), 245, np.uint8)
    y0, x0 = (TILE - im.shape[0]) // 2, (TILE - im.shape[1]) // 2
    canvas[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = im
    cv2.putText(canvas, label[:30], (3, TILE + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (20, 20, 20), 1)
    cv2.putText(canvas, sub[:34], (3, TILE + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (90, 90, 90), 1)
    return canvas


def grid(tiles, cols=6):
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    blank = np.full_like(tiles[0], 255)
    return np.concatenate([np.concatenate(r + [blank] * (cols - len(r)), axis=1) for r in rows], axis=0)


def extent(img8, box, margin=0.5):
    """Bounding box of pixels inside the expanded box that differ from the ring background (dE > 10), as a ratio to the clay box."""
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
    return dict(found=True, width_ratio=round((x1 - x0) / max(1, bw * W), 2), height_ratio=round((y1 - y0) / max(1, bh * H), 2),
                centre_du=round(((x0 + x1) / 2 / W - (u0 + u1) / 2) / bw, 2), centre_dv=round(((y0 + y1) / 2 / H - (v0 + v1) / 2) / bh, 2),
                touches_expanded_box=bool(xs.min() == 0 or ys.min() == 0 or xs.max() == X1 - X0 - 1 or ys.max() == Y1 - Y0 - 1))


def run(fid):
    d = C.load(fid)
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
    refs = IDX["frames"].get(fid) or []
    rtiles = []
    for i, r in enumerate(refs):
        f = r.get("file")
        if f and os.path.exists(os.path.join(C.REPO, f)):
            im = cv2.imread(os.path.join(C.REPO, f))
            if im is not None:
                rtiles.append(tile(im, f"ref {i + 1}: " + (r.get("note") or "")[:22], (r.get("note") or "")[22:56]))
    sheet = grid(tiles) if tiles else None
    if rtiles:
        rg = grid(rtiles)
        if sheet is not None and rg.shape[1] != sheet.shape[1]:
            wmax = max(rg.shape[1], sheet.shape[1])
            sheet = np.pad(sheet, ((0, 0), (0, wmax - sheet.shape[1]), (0, 0)), constant_values=255)
            rg = np.pad(rg, ((0, 0), (0, wmax - rg.shape[1]), (0, 0)), constant_values=255)
        bar = np.full((30, sheet.shape[1], 3), 200, np.uint8)
        cv2.putText(bar, f"{fid}: render crops (red = clay box, yellow = +-15 %) above; the frame's supplier references below", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        sheet = np.concatenate([sheet, bar, rg], axis=0)
    cv2.imwrite(os.path.join(C.OUT, "overlays", f"fidelity-{fid}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
    json.dump(dict(frame=fid, products=rec, refs=[dict(n=i + 1, note=r.get("note"), file=r.get("file")) for i, r in enumerate(refs)]),
              open(os.path.join(C.OUT, "data", f"fidelity-{fid}.json"), "w"), indent=1, ensure_ascii=False)
    print(fid, len(tiles), "product tiles,", len(rtiles), "refs;", {k.split('/')[-1]: (v['extent_estimate'] or {}).get('width_ratio') for k, v in rec.items()})


if __name__ == "__main__":
    for f in (sys.argv[1:] or C.MASTERS):
        run(f)
