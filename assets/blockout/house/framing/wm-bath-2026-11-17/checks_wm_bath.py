#!/usr/bin/env python3
"""
checks_wm_bath.py: the contact sheet of the warm-modern bath clay (render-agent, 2026-11-17; 0 tokens). No bpy.
Tiles: B2-plate, B2 (defaults), B2-shell, the B2 id pass, the B2 structure edges, and B2 with the lock target's lines
(lock-target.json: green where the depth pass sees the line, red where something stands in front of it).

  python3 checks_wm_bath.py
"""
import json
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
TW, TH = 900, 506


def tile(path, label, draw_lock=False):
    im = Image.open(os.path.join(HERE, path)).convert("RGB")
    if draw_lock:
        lt = json.load(open(os.path.join(HERE, "lock-target.json")))
        d = ImageDraw.Draw(im)
        for name, L in lt["lines"].items():
            s = L["samples"]
            for a, b in zip(s, s[1:]):
                d.line([(a[0], a[1]), (b[0], b[1])], fill=(0, 200, 0) if (a[2] and b[2]) else (220, 0, 0), width=3)
        x0, y0, x1, y1 = lt["frame_box"]
        d.rectangle([x0, y0, x1, y1], outline=(0, 120, 255), width=3)
    im = im.resize((TW, TH))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, TW, 22], fill=(0, 0, 0))
    d.text((6, 5), label, fill=(255, 255, 255))
    return im


def main():
    tiles = [tile("B2-plate.png", "B2-plate: output 1, the empty plate (shell + vanity; product lamps off)"),
             tile("B2.png", "B2: the 0א defaults (Style B sconces 8x8x16 up-down, floor planter, ring A3 at Y 13.07, curtain at X 5.34)"),
             tile("B2-shell.png", "B2-shell: the shell alone (plate / shell = the vanity's shadow)"),
             tile("B2-id.png", "B2 id pass (legend: selfcheck.json ids)"),
             tile("B2-plate-edges.png", "B2-plate structure edges"),
             tile("B2.png", "B2 + lock target (green seen, red covered; blue = the 16:9 frame)", draw_lock=True)]
    sheet = Image.new("RGB", (TW * 2, TH * 3), (20, 20, 20))
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % 2) * TW, (k // 2) * TH))
    sheet.save(os.path.join(HERE, "contact-sheet.jpg"), quality=88)
    print("contact-sheet.jpg")


if __name__ == "__main__":
    main()
