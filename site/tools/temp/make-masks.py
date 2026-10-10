"""
Product silhouettes for the TEMPORARY room layers (until render-agent delivers real per-variant layers with alpha).

The temporary variants are recolourings of the one styled preview. A variant swap may change nothing outside the
product's own shape (docs/studio-rules.md ו.5), so every slot needs its real silhouette, not a box and not a
"differs from the background" guess. This script segments each product with GrabCut, seeded by the slot shapes in
living-room.nordic.json and by the hand hints in living-room.masks.json (definite product / definite background,
traced by eye on the 1920 frame), then cleans the result (holes, specks) and writes one full-frame mask per slot:

    tools/temp/masks/living-room/<slot>.png      1920×1080, 8-bit, 255 = product, binary (edges are anti-aliased by
                                                 make-temp-assets.ts at each output width)
    tools/temp/masks/living-room/outlines.json   per slot: the outline (simplified contours, frame coordinates) for the
                                                 hover/focus glow, and the anchor for the resting marker: the point
                                                 deepest inside the silhouette (max of the distance transform), so the
                                                 marker always sits on the product itself, never between two parts

Run:  python3 -I tools/temp/make-masks.py [--slot <id>] [--views <dir>]
      (needs numpy and opencv-python-headless; the masks are committed, so the site build does not need Python)
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
SITE = HERE.parent.parent
REPO = SITE.parent
W, H = 1920, 1080

temp = json.loads((HERE / "living-room.nordic.json").read_text())
hints = json.loads((HERE / "living-room.masks.json").read_text())
manifest = json.loads((REPO / "assets/manifest.json").read_text())
src = next(a["path"] for a in manifest["assets"] if a["id"] == temp["source_manifest_id"])
img = cv2.resize(cv2.imread(str(REPO / src)), (W, H), interpolation=cv2.INTER_AREA)
OUT = HERE / "masks" / temp["room"]
OUT.mkdir(parents=True, exist_ok=True)

args = sys.argv[1:]
only = args[args.index("--slot") + 1] if "--slot" in args else None
views = Path(args[args.index("--views") + 1]) if "--views" in args else None


def px_box(b):
    return int(round(b[0] * W)), int(round(b[1] * W)), int(round(b[2] * H)), int(round(b[3] * H))


def paint_shapes(m, shapes, value):
    """shapes: boxes [u0,u1,v0,v1], ellipses {"e":[cu,cv,ru,rv]}, polygons {"p":[[u,v],...]}"""
    for s in shapes:
        if isinstance(s, dict) and "p" in s:
            pts = np.array([[round(u * W), round(v * H)] for u, v in s["p"]], np.int32)
            cv2.fillPoly(m, [pts], value)
        elif isinstance(s, dict) and "e" in s:
            cu, cv, ru, rv = s["e"]
            cv2.ellipse(m, (round(cu * W), round(cv * H)), (round(ru * W), round(rv * H)), 0, 0, 360, value, -1)
        else:
            x0, x1, y0, y1 = px_box(s)
            m[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] = value


def slot_shapes(t):
    return list(t.get("boxes", [])) + [{"e": e} for e in t.get("ellipses", [])]


def segment(slot_id, t, h, done):
    if "shape" in h:
        return refine(h, done)
    shapes = slot_shapes(t)
    region = np.zeros((H, W), np.uint8)
    paint_shapes(region, shapes + h.get("fg", []) + h.get("extend", []), 1)
    ys, xs = np.nonzero(region)
    pad = int(h.get("pad", 0.01) * W)
    x0, x1 = max(0, xs.min() - pad), min(W, xs.max() + pad + 1)
    y0, y1 = max(0, ys.min() - pad), min(H, ys.max() + pad + 1)

    gc = np.full((H, W), cv2.GC_BGD, np.uint8)
    gc[y0:y1, x0:x1] = cv2.GC_PR_BGD
    pr = np.zeros((H, W), np.uint8)
    paint_shapes(pr, shapes + h.get("extend", []), 1)
    gc[pr == 1] = cv2.GC_PR_FGD
    bg = np.zeros((H, W), np.uint8)
    paint_shapes(bg, h.get("bg", []), 1)
    # products in front of this one (higher z) that the hints name: their final masks are background here
    for other in h.get("behind", []):
        if other in done:
            bg |= cv2.dilate(done[other], np.ones((3, 3), np.uint8)) // 255
    fg = np.zeros((H, W), np.uint8)
    paint_shapes(fg, h.get("fg", []), 1)
    gc[bg == 1] = cv2.GC_BGD
    gc[(fg == 1) & (bg == 0)] = cv2.GC_FGD

    if h.get("mode") == "hints":  # no GrabCut: the traced polygons are the silhouette
        m = ((fg == 1) & (bg == 0)).astype(np.uint8)
    else:
        m0 = max(0, y0 - 20), min(H, y1 + 20), max(0, x0 - 20), min(W, x1 + 20)
        crop = img[m0[0]:m0[1], m0[2]:m0[3]]
        cm = gc[m0[0]:m0[1], m0[2]:m0[3]].copy()
        bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        cv2.grabCut(crop, cm, None, bgd, fgd, h.get("iters", 6), cv2.GC_INIT_WITH_MASK)
        m = np.zeros((H, W), np.uint8)
        m[m0[0]:m0[1], m0[2]:m0[3]] = ((cm == cv2.GC_FGD) | (cm == cv2.GC_PR_FGD)).astype(np.uint8)

    # clean: drop specks, fill holes smaller than ~0.03% of the frame, smooth the outline by one pixel
    k = np.ones((3, 3), np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= h.get("min_area", 60):
            keep[lab == i] = 1
    inv = 1 - keep
    n, lab, stats, _ = cv2.connectedComponentsWithStats(inv, 4)
    for i in range(1, n):
        x, y, w_, h_, a = stats[i]
        touches = x == 0 or y == 0 or x + w_ >= W or y + h_ >= H
        if not touches and a < h.get("max_hole", 600):
            keep[lab == i] = 1
    keep[bg == 1] = 0
    return keep * 255


def behind_mask(h, done):
    bg = np.zeros((H, W), np.uint8)
    paint_shapes(bg, h.get("bg", []), 1)
    for other in h.get("behind", []):
        if other in done:
            bg |= (cv2.dilate(done[other], np.ones((3, 3), np.uint8)) > 0).astype(np.uint8)
    return bg


def refine(h, done):
    """Traced silhouette ("shape": boxes, ellipses or polygons) refined by GrabCut in a narrow band around its outline:
    pixels more than `band` px inside are product, more than `band` px outside are not. "soft" shapes (thin parts such
    as handles, tassels, table legs) are left to GrabCut entirely; "soft_all" leaves the whole shape to GrabCut, with
    only the "fg" hints fixed. "bg" and the masks of the products in front ("behind") are never product."""
    poly = np.zeros((H, W), np.uint8)
    paint_shapes(poly, h["shape"], 1)
    soft = np.zeros((H, W), np.uint8)
    paint_shapes(soft, h.get("soft", []), 1)
    fg = np.zeros((H, W), np.uint8)
    paint_shapes(fg, h.get("fg", []), 1)
    band = int(h.get("band", 3))
    bg = behind_mask(h, done)
    if band <= 0 and not soft.any():
        m = poly | fg
    else:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * max(band, 2) + 1, 2 * max(band, 2) + 1))
        inner = cv2.erode(poly, k)
        outer = cv2.dilate(poly | soft, k)
        gc = np.full((H, W), cv2.GC_BGD, np.uint8)
        gc[outer == 1] = cv2.GC_PR_BGD
        gc[(poly | soft) == 1] = cv2.GC_PR_FGD
        if not h.get("soft_all"):
            gc[inner == 1] = cv2.GC_FGD
        gc[fg == 1] = cv2.GC_FGD
        gc[bg == 1] = cv2.GC_BGD
        ys, xs = np.nonzero(outer)
        y0, y1, x0, x1 = max(0, ys.min() - 30), min(H, ys.max() + 30), max(0, xs.min() - 30), min(W, xs.max() + 30)
        cm = gc[y0:y1, x0:x1].copy()
        bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        cv2.grabCut(img[y0:y1, x0:x1], cm, None, bgd, fgd, h.get("iters", 5), cv2.GC_INIT_WITH_MASK)
        m = np.zeros((H, W), np.uint8)
        m[y0:y1, x0:x1] = ((cm == cv2.GC_FGD) | (cm == cv2.GC_PR_FGD)).astype(np.uint8)
    m[bg == 1] = 0
    # GrabCut tends to give the bright rim of a product (its lit top edge) to the background: grow the result by one
    # pixel, but never past the traced outline (+1 px)
    one = np.ones((3, 3), np.uint8)
    m = cv2.dilate(m, one) & cv2.dilate(poly | soft | fg, one)
    m[bg == 1] = 0
    # one-pixel smoothing of the outline; drop specks and fill pinholes
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < h.get("min_area", 40):
            m[lab == i] = 0
    m[bg == 1] = 0
    return m * 255


def overlay(slot_id, m, t, h):
    ys, xs = np.nonzero(m)
    if not len(xs):
        return
    pad = 30
    x0, x1 = max(0, xs.min() - pad), min(W, xs.max() + pad)
    y0, y1 = max(0, ys.min() - pad), min(H, ys.max() + pad)
    crop = img[y0:y1, x0:x1].copy()
    mm = m[y0:y1, x0:x1]
    tint = crop.copy()
    tint[mm > 0] = (0.55 * tint[mm > 0] + 0.45 * np.array([255, 60, 200])).astype(np.uint8)
    cnts, _ = cv2.findContours(mm, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(tint, cnts, -1, (0, 255, 255), 1)
    both = np.concatenate([crop, np.full((crop.shape[0], 6, 3), 0, np.uint8), tint], 1)
    s = min(3.0, 1500 / both.shape[1])
    both = cv2.resize(both, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST if s > 1 else cv2.INTER_AREA)
    cv2.imwrite(str(views / f"{slot_id}.png"), both)


order = sorted(temp["slots"].items(), key=lambda kv: -hints.get(kv[0], {}).get("z", 0))
done = {}
for slot_id, t in order:
    if not slot_shapes(t) or t.get("visible") is False:
        continue
    if only and slot_id != only and slot_id not in hints.get(only, {}).get("behind", []):
        p = OUT / f"{slot_id}.png"
        if p.exists():
            done[slot_id] = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        continue
    h = hints.get(slot_id, {})
    m = segment(slot_id, t, h, done)
    done[slot_id] = m
    cv2.imwrite(str(OUT / f"{slot_id}.png"), m, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    if views:
        views.mkdir(parents=True, exist_ok=True)
        overlay(slot_id, m, t, h)
    print(f"{slot_id}: {int((m > 0).sum())} px")


# ---------- outlines and anchors (from the final masks, so the same step works on delivered alpha later) ----------
outlines = {}
for p in sorted(OUT.glob("*.png")):
    m = (cv2.imread(str(p), cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8)
    if not m.any():
        continue
    # the frame edge counts as outside: a product cut by the frame keeps its anchor inside the picture
    dist = cv2.distanceTransform(np.pad(m, 1), cv2.DIST_L2, 5)[1:-1, 1:-1]
    # among the deepest points (within 10% of the max) take the one nearest their centre: the middle of a long
    # panel rather than its top end
    cy, cx = np.nonzero(dist >= 0.9 * dist.max())
    k = int(np.argmin((cx - cx.mean()) ** 2 + (cy - cy.mean()) ** 2))
    y, x = int(cy[k]), int(cx[k])
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    paths = []
    for c in sorted(cnts, key=cv2.contourArea, reverse=True):
        if cv2.contourArea(c) < 120:
            continue
        a = cv2.approxPolyDP(c, 1.2, True)[:, 0, :]
        paths.append([[round(float(px) / W, 4), round(float(py) / H, 4)] for px, py in a])
    ys, xs = np.nonzero(m)
    outlines[p.stem] = {
        "anchor": [round(float(x) / W, 4), round(float(y) / H, 4)],
        "depth_px": round(float(dist[y, x]), 1),
        "bbox": [round(xs.min() / W, 4), round((xs.max() + 1) / W, 4), round(ys.min() / H, 4), round((ys.max() + 1) / H, 4)],
        "paths": paths,
    }
(OUT / "outlines.json").write_text(json.dumps(outlines, separators=(",", ":")))
print(f"outlines: {len(outlines)} slots, {sum(len(o['paths']) for o in outlines.values())} paths")
