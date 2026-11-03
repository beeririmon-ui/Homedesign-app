#!/usr/bin/env python3
"""
References for the v8 retakes (render-agent, 2026-11-03; 0 var2 tokens): the hard cut-outs of recipe v8 2.1 (docs/render-recipe-
nordic-v8-2026-11-03.md) from the graded-v3 stills, as the prompt headers list them (pose-w0-in-v7-r2-v8.txt, pose-k-girl-0-v7-r2-v8.txt,
b1-v7-r3-v8.txt, b2-v7-r3-v8.txt), plus the two new product images (floor planter, toilet brush) cropped to the product as refs_v7.py
does. Files under refs/retakes-2026-11-03/, index in refs/index-retakes-2026-11-03.json (window, size, sha256, var2_url after the upload).
Usage: python3 prep_retakes.py <set> [<set> ...]   sets: w0in kgirl0 b1 b2 products   (b2 needs b1-v7-r3-graded-v3.png)
"""
import hashlib
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "refs", "retakes-2026-11-03")
IDX = os.path.join(HERE, "refs", "index-retakes-2026-11-03.json")
DL = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/dl-r3"
MAXPX = 1536

CROPS = {
    "w0in": ("assets/renders/work/nordic/v7/w0-v7-graded-fix-v3.png", [
        ("w0in-1-desk-top", (0.30, 0.70, 0.46, 0.66), "desk top, drawer front and pen cup"),
        ("w0in-2-shelf", (0.32, 0.68, 0.14, 0.27), "shelf with both felt bins"),
        ("w0in-3-plant", (0.17, 0.35, 0.21, 0.87), "the plant in its seagrass belly basket"),
        ("w0in-4-under-desk", (0.34, 0.67, 0.65, 0.88), "under the desk: rope basket, kraft bin, skirting, planks"),
        ("w0in-5-chair", (0.43, 0.57, 0.54, 0.99), "chair back"),
        ("w0in-6-right-corner", (0.70, 0.97, 0.50, 1.00), "wall, skirting and planks at the right corner")]),
    "kgirl0": ("assets/renders/girl/nordic/v7/k-girl-v7-graded-fix-v3.png", [
        ("kgirl0-1-desk-doll-band", (0.60, 0.93, 0.33, 0.95), "desk, doll, band, blush skirting and planks"),
        ("kgirl0-2-prints", (0.71, 0.91, 0.05, 0.30), "the two prints"),
        ("kgirl0-3-ledges", (0.41, 0.57, 0.12, 0.38), "ledges with the picture books"),
        ("kgirl0-4-bed-foot", (0.43, 0.60, 0.52, 0.88), "bed foot with the folded muslin"),
        ("kgirl0-5-wall-band-line", (0.57, 0.70, 0.10, 0.52), "white upper wall and the crisp band line")]),
    "b1": ("assets/renders/bath/nordic/v7/b1-v7-graded-v3.png", [
        ("b1r3-1-wc-ledge", (0.12, 0.45, 0.40, 0.97), "WC block with the limestone ledge, candle, diffuser and roll stand"),
        ("b1r3-2-shower-corner", (0.52, 0.80, 0.05, 0.72), "shower corner with the curtain, niche and dispensers")]),
    "b2": ("assets/renders/bath/nordic/v7/b1-v7-r3-graded-v3.png", [
        ("b2r3-1-b1r3-shower-planter", (0.44, 0.82, 0.03, 0.77), "B1 r3: the shower corner with the curtain, niche, dispensers and the planter (window ends above the invented plinth under the basket in B1 r3)"),
        ("b2r3-2-b1r3-planter", (0.46, 0.60, 0.42, 0.775), "B1 r3: the basket and fern alone (without the invented plinth below y 0.775)")]),
    "b2v7": ("assets/renders/bath/nordic/v7/b2-v7-graded-v3.png", [
        ("b2r3-3-b2v7-vanity-mirror", (0.46, 0.90, 0.03, 1.00), "B2 v7: vanity, mirror and the sconce pair")]),
}
PRODUCTS = {
    "planter-seagrass-30": (os.path.join(DL, "planter", "src.jpg"), "https://ae01.alicdn.com/kf/Sc380b4c7230f4fb8b34543507a5494d5S.jpg",
                            "floor-planter-aliexpress-seagrass-straight-planter-basket-30, SKU 12000060921446349 (30 x 30), the in_room SKU image"),
    "toilet-brush-black": (os.path.join(DL, "brush", "src.jpg"), "https://ae01.alicdn.com/kf/Sd3e09523bada4a169e7737f1b0519f42A.jpg",
                           "toilet-brush-aliexpress-matte-black-steel-cylinder-245996, black SKU 12000051218554542 (8 x 38), the in_room SKU image"),
}


def crop_product(im, pad=0.08):
    import numpy as np
    im = im.convert("RGB")
    a = np.asarray(im).astype(float)
    bg = np.median(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]), axis=0)
    m = np.abs(a - bg).sum(2) > 40
    if m.mean() < 0.01 or m.mean() > 0.97:
        return im
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    side = min(max(x1 - x0, y1 - y0) * (1 + 2 * pad), max(im.size))
    bx0, by0 = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
    bx1, by1 = int(min(im.size[0], cx + side / 2)), int(min(im.size[1], cy + side / 2))
    return im.crop((bx0, by0, bx1, by1))


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main(sets):
    os.makedirs(OUT, exist_ok=True)
    idx = json.load(open(IDX)) if os.path.exists(IDX) else {"date": "2026-11-03", "rule": "recipe v8 2.1: cut-outs carry look only; sizes and u/v are in the prompt line", "refs": {}}
    for s in sets:
        if s == "products":
            for k, (src, url, note) in PRODUCTS.items():
                im = Image.open(src)
                im.load()
                c = crop_product(im)
                c.thumbnail((1024, 1024), Image.LANCZOS)
                out = os.path.join(OUT, k + ".jpg")
                c.save(out, quality=90)
                idx["refs"][k] = dict(kind="product", src=url, note=note, file=os.path.relpath(out, REPO), source_size=list(im.size), size=list(c.size), sha256=sha(out),
                                      var2_url=idx["refs"].get(k, {}).get("var2_url"), usage="internal render reference only (usage_rights unclear)")
                print("product", k, im.size, "->", c.size)
            continue
        src, items = CROPS[s]
        im = Image.open(os.path.join(REPO, src)).convert("RGB")
        W, H = im.size
        for k, (x0, x1, y0, y1), note in items:
            c = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
            c.thumbnail((MAXPX, MAXPX), Image.LANCZOS)
            out = os.path.join(OUT, k + ".jpg")
            c.save(out, quality=92)
            idx["refs"][k] = dict(kind="cut-out", src=src, window_uv=[x0, x1, y0, y1], note=note, file=os.path.relpath(out, REPO), size=list(c.size), sha256=sha(out),
                                  var2_url=idx["refs"].get(k, {}).get("var2_url"))
            print("crop", k, c.size)
    json.dump(idx, open(IDX, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
