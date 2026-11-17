#!/usr/bin/env python3
"""
checks_wm_master.py: the contact sheet of the warm-modern master clay (render-agent, 2026-11-17; 0 tokens). No bpy.
Tiles: MB0-plate, MB0 (defaults), MB0-shell, the MB0 id pass, the MB0-plate structure edges, and MB0-plate with the lock target's lines
(lock-target.json: green where the depth pass sees the line, red where something stands in front of it).

  python3 checks_wm_master.py
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
    tiles = [tile("MB0-plate.png", "MB0-plate: the empty plate (shell + walnut bed and nightstands; every lamp off)"),
             tile("MB0.png", "MB0: the defaults of 3.2 + 12.2 as envelope boxes (cones and floor lamp lit)"),
             tile("MB0-shell.png", "MB0-shell: the shell alone (plate / shell = the fixed furniture's shadow)"),
             tile("MB0-id.png", "MB0 id pass (legend: selfcheck.json ids)"),
             tile("MB0-plate-edges.png", "MB0-plate structure edges"),
             tile("MB0-plate.png", "MB0-plate + lock target (green seen, red covered; blue = the 16:9 frame)", draw_lock=True)]
    sheet = Image.new("RGB", (TW * 2, TH * 3), (20, 20, 20))
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % 2) * TW, (k // 2) * TH))
    sheet.save(os.path.join(HERE, "contact-sheet.jpg"), quality=88)
    print("contact-sheet.jpg")


if __name__ == "__main__":
    main()
