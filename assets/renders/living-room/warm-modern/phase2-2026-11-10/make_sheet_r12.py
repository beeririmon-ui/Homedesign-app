#!/usr/bin/env python3
"""
make_sheet_r12.py: the sheet of phase 2 after the reserve passes R1 / R2 (render-agent, 2026-11-11). The full default scene with set B
(every default that passes, one v3c grade), sets A and C on it, the three new layers at 100 %, and the two raw passes with the tinted
clay outlines (red) where they failed. No supplier image is on the sheet. Writes phase2-reserve-r12-sheet.jpg (a new file).
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_sheet as MS  # noqa: E402  (frame, label, fonts)


def outlined(raw, npz, keys, crop):
    z = np.load(os.path.join(HERE, npz))
    r = np.asarray(Image.open(os.path.join(HERE, raw)).convert("RGB")).copy()
    for k in keys:
        m = (z[f"sil_{k}"].astype(np.float32) > 0.5).astype(np.uint8)
        e = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((4, 4), np.uint8)).astype(bool)
        r[e] = (230, 30, 30)
    return Image.fromarray(r).crop(crop)


def main():
    G = os.path.join(HERE, "graded")
    Wd = 1960
    big = (Wd - 20, int((Wd - 20) * 9 / 16))
    t2 = ((Wd - 30) // 2, int((Wd - 30) // 2 * 9 / 16))
    crop_h = 330
    fail_h = 520
    H = 90 + big[1] + 60 + t2[1] + 60 + crop_h + 70 + fail_h + 170
    im = Image.new("RGB", (Wd, H), (250, 249, 247))
    d = ImageDraw.Draw(im)
    MS.label(d, 10, 18, Wd - 20, "הסלון במודרני חם, הכלי: שלב 2 אחרי הרזרבה R1 ו-R2 (9 מתוך 12 ברירות מחדל בשכבות)", MS.FB)
    y = 80
    MS.label(d, 10, y, Wd - 20, "הסצנה המלאה של ברירות המחדל עם סט B, בגריידינג v3c אחד. חדש: וילון, מחזיק עיתונים Orange, קערה (מיקום זמני, WM-T2)")
    im.paste(MS.frame(os.path.join(G, "default-scene-r12-set-B-graded-v3c.png")).resize(big, Image.LANCZOS), (10, y + 34))
    y += 34 + big[1] + 20
    for i, (t, f) in enumerate([("סט A על הסצנה", "default-scene-r12-set-A-graded-v3c.png"), ("סט C על הסצנה", "default-scene-r12-set-C-graded-v3c.png")]):
        x = Wd - 10 - (i + 1) * t2[0] - i * 10
        MS.label(d, x, y, t2[0], t, MS.FS)
        im.paste(MS.frame(os.path.join(G, f)).resize(t2, Image.LANCZOS), (x, y + 28))
    y += 28 + t2[1] + 20
    MS.label(d, 10, y, Wd - 20, "100%: הווילון מאחורי הכורסה, מחזיק העיתונים (הרגל מחוץ לפריים, לפי התוכנית), הקערה ליד הפמוטים", MS.FS)
    full = Image.open(os.path.join(G, "default-scene-r12-set-B-graded-v3c.png")).convert("RGB")
    boxes = [(60, 760, 420, 1300), (900, 1330, 1240, 1530), (1880, 1180, 2140, 1400)]
    x = Wd - 10
    for b in boxes:
        c = full.crop(b)
        c = c.resize((max(1, int(c.size[0] * crop_h / c.size[1])), crop_h), Image.LANCZOS)
        x -= c.size[0]
        im.paste(c, (x, y + 28))
        x -= 10
    y += 28 + crop_h + 30
    MS.label(d, 10, y, Wd - 20, "לא נכנס: נכשל בנאמנות גם במעבר הרזרבה (אין מעבר שלישי). המעבר הגולמי, קווי ה-clay באדום", MS.FS, fill=(160, 0, 0))
    tiles = [("R1 גולמי: העציץ גדול פי 1.37, הסל לפני העציץ אבל כ-30 ס\"מ מהמקום", "raw/r1-seedream.png", "work-reserve/ph-r1.npz",
              ("planter", "basket"), (860, 560, 1260, 1290)),
             ("R2 גולמי: התלויה ברוחב 50 ס\"מ, אבל תלויה כ-10 ס\"מ נמוך מ-1.90", "raw/r2-seedream.png", "work-reserve/ph-r2.npz",
              ("pendant",), (1400, 40, 1940, 520))]
    x = Wd - 10
    for t, raw, npz, keys, crop in tiles:
        c = outlined(raw, npz, keys, crop)
        c = c.resize((max(1, int(c.size[0] * fail_h / c.size[1])), fail_h), Image.LANCZOS)
        x -= max(c.size[0], 700)
        MS.label(d, x, y + 30, max(c.size[0], 700), t, MS.FS)
        im.paste(c, (x + max(c.size[0], 700) - c.size[0], y + 62))
        x -= 20
    y += 62 + fail_h + 20
    MS.label(d, 10, y, Wd - 20, "R1 ו-R2: ‏1,300 טוקנים, הרזרבה כולה", MS.FS)
    d.text((10, y + 32), "R1 650 + R2 650 | swap-diff 0 px outside every region | recomposite p99.9 0-1, max 3-4 (gate 2 / 6) | "
           "shell lock pass, worst p90 9.0 px", fill=(0, 0, 0), font=MS.FS)
    p = os.path.join(HERE, "phase2-reserve-r12-sheet.jpg")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    im.save(p, quality=90)
    print(p, im.size)


if __name__ == "__main__":
    main()
