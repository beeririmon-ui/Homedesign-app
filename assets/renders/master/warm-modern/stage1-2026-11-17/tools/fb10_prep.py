#!/usr/bin/env python3
"""
fb10_prep.py: the three FB9/FB10 passes on MB0 (13.10; render-agent, 2026-11-18; 0 tokens). Each pass's input is the approved composite
(mb0-defaults.png) with flat placeholders where the products go (their projected boxes, from the camera and the card sizes), and a
reference board of the SKU photos (the board stays in the scratchpad: supplier photos never enter the repo).
  python3 fb10_prep.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import compose_defaults as C  # noqa: E402

PICKS = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/"
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-master/fb10/"
F, CX, HZ, CAM = C.F, C.CX, C.HZ, C.CAM


def px(X, Y, Z):
    return C.proj(X, Y, Z)


def box_on(X0, X1, Y, Z0, Z1):
    x0, y1 = px(X0, Y, Z0)
    x1, y0 = px(X1, Y, Z1)
    return [round(x0), round(y0), round(x1), round(y1)]


PASSES = {
    "p1-wall": dict(
        items={"wall-shelf": dict(kind="shelf"),
               "framed-art": dict(box=box_on(-1.24, -0.70, 17.72, 1.50, 2.24), kind="frame"),
               "framed-art-2": dict(box=box_on(-0.64, -0.20, 17.72, 1.50, 1.84), kind="frame"),
               "shelf-vase-left": dict(box=box_on(-1.51, -1.29, 17.78, 1.50, 1.82), kind="vase-dark"),
               "shelf-vase-right": dict(box=box_on(-0.11, 0.11, 17.78, 1.50, 1.83), kind="vase-white")},
        refs=["51fa028b_b3a612e6-5115-4823-9a62-531484d9db5f_trans.jpeg", "de5b1274_6a045c32-af57-4e53-80dd-211b74b54df8_trans.jpeg"],
        zone=(847, 60, 1873, 530)),
    "p2-corner": dict(
        items={"planter": dict(box=box_on(1.24, 1.66, 17.92, 0.0, 0.355), kind="pot"),
               "magazine-holder": dict(box=box_on(0.82, 1.17, 18.55, 0.0, 0.275), kind="holder")},
        refs=["6bde6ef7_564d83ce-d066-4da9-ab34-952570829362.jpg", "dce84844_63b2b670-cee7-4caa-a84b-1dcdbbdd76f8.jpg"],
        zone=(2283, 260, 2720, 1530)),
    "p3-islands": dict(
        items={"bedside-carafe": dict(box=box_on(0.265, 0.415, 17.80, 0.55, 0.79), kind="pitcher"),
               "trinket-dish": dict(box=box_on(-1.85, -1.75, 17.93, 0.57, 0.595), kind="dish")},
        refs=["024df36f_bf476452-1265-4a56-97cd-190f98e87005.jpg", "33039093_d2de0c80-3921-4551-80a8-5817ef6af558.jpg"],
        zone=None),
}


def draw(dr, it):
    k = it["kind"]
    x0, y0, x1, y1 = it.get("box", (0, 0, 0, 0))
    if k == "shelf":
        a, _ = px(-1.60, 17.90, 1.50)
        b, _ = px(0.20, 17.90, 1.50)
        _, t = px(0, 17.90, 1.50)
        _, m = px(0, 17.90, 1.46)
        _, w = px(0, 17.66, 1.46)
        dr.rectangle([a, t, b, m], fill=(92, 62, 42))
        dr.polygon([(a, m), (b, m), (px(0.20, 17.66, 1.46)[0], w), (px(-1.60, 17.66, 1.46)[0], w)], fill=(64, 44, 31))
        it["box"] = [round(a), round(t), round(b), round(w)]
    elif k == "frame":
        dr.rectangle([x0, y0, x1, y1], fill=(88, 60, 40))
        bw = max(4, round((x1 - x0) * 3 / 54))
        dr.rectangle([x0 + bw, y0 + bw, x1 - bw, y1 - bw], fill=(216, 200, 174))
    elif k == "vase-dark":
        cx = (x0 + x1) / 2
        dr.polygon([(x0 + 6, y0 + 8), (x1 - 6, y0 + 8), (cx + (x1 - x0) * 0.36, y1), (cx - (x1 - x0) * 0.36, y1)], fill=(46, 43, 40))
        dr.line([(cx, y0 + 8), (cx - 30, y0 - 90), (cx - 55, y0 - 150)], fill=(70, 52, 38), width=3)
    elif k == "vase-white":
        cx = (x0 + x1) / 2
        dr.polygon([(cx - 14, y0), (cx + 14, y0), (x1, y0 + (y1 - y0) * 0.25), (cx + (x1 - x0) * 0.22, y1), (cx - (x1 - x0) * 0.22, y1),
                    (x0, y0 + (y1 - y0) * 0.25)], fill=(236, 230, 219))
    elif k == "pot":
        dr.rectangle([x0, y0, x1, y1], fill=(170, 160, 146))
        cx = (x0 + x1) / 2
        dr.ellipse([cx - 120, y0 - 640, cx + 100, y0 - 120], fill=(86, 104, 70))
        dr.line([(cx, y0), (cx, y0 - 200)], fill=(90, 70, 50), width=6)
    elif k == "holder":
        dr.rectangle([x0, y0, x1, y1], outline=(30, 30, 32), width=6)
        dr.rectangle([x0 + 20, y0 + 40, x1 - 20, y1 - 10], fill=(176, 104, 52))
    elif k == "pitcher":
        cx = (x0 + x1) / 2
        dr.polygon([(cx - 12, y0), (cx + 12, y0), (x1 - 8, y0 + (y1 - y0) * 0.45), (cx + 30, y1), (cx - 30, y1), (x0 + 8, y0 + (y1 - y0) * 0.45)],
                   fill=(184, 168, 149))
    elif k == "dish":
        dr.rectangle([x0, y0, x1, y1], fill=(222, 210, 190))


def board(files, out):
    ims = [Image.open(PICKS + f).convert("RGB") for f in files]
    H = 700
    ims = [i.resize((int(i.width * H / i.height), H)) for i in ims]
    b = Image.new("RGB", (sum(i.width for i in ims) + 20 * (len(ims) - 1), H), "white")
    x = 0
    for i in ims:
        b.paste(i, (x, 0))
        x += i.width + 20
    b.save(out)


def main():
    os.makedirs(SCR, exist_ok=True)
    base = Image.open(os.path.join(ST, "mb0-defaults.png")).convert("RGB")
    rec = {}
    for name, p in PASSES.items():
        im = base.copy()
        dr = ImageDraw.Draw(im)
        for slot, it in p["items"].items():
            draw(dr, it)
        if name == "p2-corner":                           # the crown goes behind the lamp: the lamp layer back over it
            man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
            ll = [l for l in man["layers"] if l["slot"] == "floor-lamp"][0]
            lamp = Image.open(os.path.join(ST, ll["layer"]))
            im.paste(lamp.convert("RGB"), (0, 0), lamp.split()[3])
        out = os.path.join(ST, "inputs", f"fb10-{name}-input.png")
        im.save(out)
        board(p["refs"], SCR + f"board-{name}.png")
        rec[name] = {s: it["box"] for s, it in p["items"].items()}
    json.dump(rec, open(os.path.join(ST, "fb10", "placeholders.json"), "w"), indent=1)
    print(json.dumps(rec))


if __name__ == "__main__":
    main()
