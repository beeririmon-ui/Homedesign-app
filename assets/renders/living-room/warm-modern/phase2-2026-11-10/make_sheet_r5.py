#!/usr/bin/env python3
"""
make_sheet_r5.py: the R5 review sheet and crops (render-agent, 2026-11-11). 0 tokens.
  phase2-r5-variants-sheet.jpg  the full r5 default scene (set B) and, per slot, each variant on the default scene with set B (its truth),
                                as crops side by side (the default first), labelled with the card id
  crops-r5/                     each R5 fix and each variant at 100 % and x3 (before / after for the fixes; default / variant for the slots)
  python3 make_sheet_r5.py
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GRD = os.path.join(HERE, "graded")
MAN = json.load(open(os.path.join(HERE, "layers/manifest-r5.json")))
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
SMALL = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
BOX = {"curtains": (0, 380, 330, 1530), "framed-art": (1480, 470, 2200, 830), "accent-sconces": (1360, 430, 2360, 640),
       "vase": (560, 820, 790, 1110), "pendant": (1500, 0, 1900, 420), "planter": (880, 700, 1220, 1250)}


def label(im, txt, sub=""):
    d = ImageDraw.Draw(im)
    d.text((8, 6), txt, fill=(255, 255, 255), font=FONT, stroke_width=2, stroke_fill=(0, 0, 0))
    if sub:
        d.text((8, 30), sub, fill=(255, 255, 255), font=SMALL, stroke_width=2, stroke_fill=(0, 0, 0))
    return im


def crop_slot(im, k):
    if k == "accent-sconces":                                  # the two lamps side by side (the wall between them is the art's)
        a, b = im.crop((1370, 450, 1500, 640)), im.crop((2210, 420, 2360, 640))
        out = Image.new("RGB", (a.width + b.width + 4, max(a.height, b.height)), (30, 30, 30))
        out.paste(a, (0, 0))
        out.paste(b, (a.width + 4, 0))
        return out
    return im.crop(BOX[k])


def fit(im, h):
    return im.resize((max(1, int(im.width * h / im.height)), h), Image.LANCZOS)


def main():
    S = Image.open(os.path.join(GRD, "default-scene-r5-set-B-graded-v3c.png")).convert("RGB")
    R4 = Image.open(os.path.join(GRD, "default-scene-r4-set-B-graded-v3c.png")).convert("RGB")
    rows = [label(fit(S, 760), "R5 default scene, set B (12 defaults)", "curtains cream, rods silver, lamp wisp out, vase at the clay point, planter whole")]
    by = {l_["id"]: l_ for l_ in MAN["layers"]}
    H = 300
    for k in ("vase", "planter", "curtains", "framed-art", "accent-sconces", "pendant"):
        tiles = []
        x0, y0, x1, y1 = BOX[k]
        tiles.append(label(fit(crop_slot(R4, k), H), f"{k}: r4", "before R5"))
        tiles.append(label(fit(crop_slot(S, k), H), f"{k}: default (r5)", by[k]["product"]["card_id"][:42]))
        for v in MAN["variants"].get(k, []):
            T = Image.open(os.path.join(GRD, f"variant-r5-{v['id']}-set-B-graded-v3c.png")).convert("RGB")
            tiles.append(label(fit(crop_slot(T, k), H), f"{k}: {v['variant']}", v["product"]["card_id"][:42]))
        w = sum(t.width for t in tiles) + 6 * (len(tiles) - 1)
        row = Image.new("RGB", (w, H), (30, 30, 30))
        x = 0
        for t in tiles:
            row.paste(t, (x, 0))
            x += t.width + 6
        rows.append(row)
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, sum(r.height for r in rows) + 8 * (len(rows) - 1)), (30, 30, 30))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 8
    sheet.save(os.path.join(HERE, "phase2-r5-variants-sheet.jpg"), quality=88)
    # crops: 100 % and x3
    cd = os.path.join(HERE, "crops-r5")
    os.makedirs(cd, exist_ok=True)
    det = {"curtains-post-x3": (110, 1120, 300, 1300), "magazine-holder-rods-x3": (900, 1380, 1240, 1530), "floor-lamp-wisp-x3": (2380, 700, 2480, 810),
           "vase-foot-x3": (600, 860, 740, 1080), "planter-x3": (930, 1000, 1140, 1200), "pendant-canopy-cord-x3": (1600, 0, 1760, 220)}
    for k, b in BOX.items():
        S.crop(b).save(os.path.join(cd, f"{k}-default-100.png"))
        for v in MAN["variants"].get(k, []):
            T = Image.open(os.path.join(GRD, f"variant-r5-{v['id']}-set-B-graded-v3c.png")).convert("RGB")
            T.crop(b).save(os.path.join(cd, f"{v['id']}-100.png"))
    for n, b in det.items():
        a, c = R4.crop(b), S.crop(b)
        im = Image.new("RGB", (a.width * 2 + 4, a.height), (30, 30, 30))
        im.paste(a, (0, 0))
        im.paste(c, (a.width + 4, 0))
        im.resize((im.width * 3, im.height * 3), Image.NEAREST).save(os.path.join(cd, f"{n}-r4-vs-r5.png"))
    json.dump(dict(note="R5 crops: <slot>-default-100.png / <variant>-100.png at 100 % on set B; *-r4-vs-r5.png the fixes at x3 (left r4, right r5)",
                   boxes=BOX, details=det), open(os.path.join(cd, "crops-r5.json"), "w"), indent=1)
    print(sheet.size)


if __name__ == "__main__":
    main()
