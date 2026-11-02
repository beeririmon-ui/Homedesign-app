#!/usr/bin/env python3
"""
v7 references (render-agent, 2026-11-02). The ordered reference list of every v7 frame, as its prompt header names it
(assets/prompts/recipe-v5.nordic/<frame>-v7.txt, "References after the clay"), resolved to var2 URLs:
  - refs already prepared and uploaded in Phase B are reused from assets/renders/house-nordic-2026-10-25/refs/index.json (same crop);
  - the 6 new supplier images are downloaded (curl, into the scratchpad), cropped to the product (Phase B crop_product), saved here
    under refs/, and uploaded separately (var2 request_upload + PUT, put_ref.py);
  - the frame references (the sofa crop of the M0 clay, the M0 / H0 / D1 / B1 v7 crops) are filled in after those renders.
usage_rights is "unclear" on every card: internal render references only.
  python3 -I refs_v7.py           (writes refs/index-v7.json)
"""
import hashlib, io, json, os, subprocess, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PB = os.path.join(REPO, "assets", "renders", "house-nordic-2026-10-25", "refs", "index.json")
DL = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/dl-v7"
OUTJ = os.path.join(HERE, "refs", "index-v7.json")
NEW = {
    "cube": ("https://oss-cf.cjdropshipping.com/product/2025/09/29/07/4a5d60a0-dbb3-45ef-b088-e573776da8ff_trans.jpeg", "travertine cube 12 (m0-v7 ref 5; one cube)"),
    "lantern50": ("https://oss-cf.cjdropshipping.com/product/2025/07/16/10/c4df701a-6ab2-46a2-a97e-1ca25b5f52dd_trans.jpeg", "silk pumpkin lantern 50 (d1-v7 ref 1)"),
    "styleA": ("https://ae01.alicdn.com/kf/Sfd7516861e3a4b26a9c7bdc3662641e7V.jpg", "slotted wood paper towel stand, Style A (d2-v7 ref 6)"),
    "linen_white": ("https://oss-cf.cjdropshipping.com/product/2026/03/11/09/aa270f9e-1c8d-48cf-8921-02329dd7b103.jpg", "washed linen set, White (k-boy-v7 ref 2)"),
    "bear": ("https://ae01.alicdn.com/kf/S82f97d2fbec243c3b324a947c067afe5i.jpg", "063285 bear SKU (k-boy-v7 ref 5)"),
    "linen_natural": ("https://oss-cf.cjdropshipping.com/product/2026/03/11/09/8c48234d-61d5-4c20-b60e-3eb48a01a47d.jpg", "washed linen set, Natural Linen (k-girl-v7 ref 3)"),
}


def crop_product(im, pad=0.08):
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


def main():
    os.makedirs(DL, exist_ok=True)
    idx = json.load(open(OUTJ)) if os.path.exists(OUTJ) else {"new": {}, "frames": {}}
    for k, (url, note) in NEW.items():
        if k in idx["new"] and idx["new"][k].get("file"):
            continue
        d = os.path.join(DL, k)
        os.makedirs(d, exist_ok=True)
        raw = os.path.join(d, "src" + os.path.splitext(url)[1])
        r = subprocess.run(["curl", "-sS", "-L", "--max-time", "60", "-o", raw, url], capture_output=True, text=True)
        try:
            im = Image.open(raw)
            im.load()
        except Exception as e:  # noqa: BLE001
            idx["new"][k] = dict(src=url, note=note, error=f"download/open failed: {r.stderr.strip()[:200]} {e}")
            print("MISSING", k, url)
            continue
        crop = crop_product(im)
        crop.thumbnail((1024, 1024), Image.LANCZOS)
        out = os.path.join(HERE, "refs", f"{k}.jpg")
        crop.save(out, quality=90)
        idx["new"][k] = dict(src=url, note=note, file=os.path.relpath(out, REPO), source_size=list(im.size), crop_size=list(crop.size),
                             sha256=hashlib.sha256(open(out, "rb").read()).hexdigest(), var2_url=None,
                             usage="internal render reference only (usage_rights unclear on every card)")
        print("new", k, im.size, "->", crop.size)
    json.dump(idx, open(OUTJ, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
