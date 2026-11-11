#!/usr/bin/env python3
"""
make_sheet.py: the checkpoint sheet of phase 2, steps 1-3 (render-agent, 2026-11-11). Every tile is from the one v3c display grade,
except the two raw passes (marked as raw), which show why six products wait for a retake. No supplier image is on the sheet.
Writes phase2-steps1-3-sheet.jpg.
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pilot-phase1-2026-11-07"))
import pilot_wm as PW  # noqa: E402

FB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
FS = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
RTL = (lambda t: t) if __import__("PIL.features", fromlist=["check"]).check("raqm") else PW._rtl


def frame(p):
    a = Image.open(p).convert("RGB")
    w, h = a.size
    return a.crop((round(116 / 4072 * w), round(65 / 2290 * h), round(3956 / 4072 * w), round(2225 / 2290 * h)))


def outlined(raw, labels):
    z = np.load(os.path.join(HERE, "step0/placeholders.npz"))["work"]
    r = np.asarray(Image.open(raw).convert("RGB")).copy()
    for v in labels:
        m = (z == v).astype(np.uint8)
        e = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8)).astype(bool)
        r[e] = (230, 30, 30)
    a = Image.fromarray(r)
    w, h = a.size
    return a.crop((round(116 / 4072 * w), round(65 / 2290 * h), round(3956 / 4072 * w), round(2225 / 2290 * h)))


def label(d, x, y, w, t, font=F, fill=(0, 0, 0)):
    s = RTL(t)
    d.text((x + w - d.textlength(s, font=font), y), s, fill=fill, font=font)


def main():
    G = os.path.join(HERE, "graded")
    Wd = 1960
    big = (Wd - 20, int((Wd - 20) * 9 / 16))
    t3 = ((Wd - 40) // 3, int((Wd - 40) // 3 * 9 / 16))
    t2 = ((Wd - 30) // 2, int((Wd - 30) // 2 * 9 / 16))
    crop_h = 300
    H = 90 + big[1] + 60 + t3[1] + 60 + t2[1] + 60 + crop_h + 60 + t2[1] + 120
    im = Image.new("RGB", (Wd, H), (250, 249, 247))
    d = ImageDraw.Draw(im)
    label(d, 10, 18, Wd - 20, "הסלון במודרני חם, הכלי: שלב 2, צעדים 0–3, לנקודת הבדיקה (חלקי: 6 מתוך 12 ברירות מחדל)", FB)
    y = 80
    label(d, 10, y, Wd - 20, "הסצנה של ברירות המחדל עם סט B, בגריידינג v3c אחד")
    im.paste(frame(os.path.join(G, "default-scene-set-B-graded-v3c.png")).resize(big, Image.LANCZOS), (10, y + 34))
    y += 34 + big[1] + 20
    tiles = [("צעד 1: השטיח", "step1-rug-set-B-graded-v3c.png"), ("צעד 2: האגרטל ומנורת הרגל", "step2-window-floor-set-B-graded-v3c.png"),
             ("צעד 3: ההדפסים, מנורות הקיר והפמוטים", "step3-wall-table-set-B-graded-v3c.png")]
    for i, (t, f) in enumerate(tiles):
        x = Wd - 10 - (i + 1) * t3[0] - i * 10
        label(d, x, y, t3[0], t, FS)
        im.paste(frame(os.path.join(G, f)).resize(t3, Image.LANCZOS), (x, y + 28))
    y += 28 + t3[1] + 20
    for i, (t, f) in enumerate([("סט A על הסצנה החדשה", "default-scene-set-A-graded-v3c.png"), ("סט C על הסצנה החדשה", "default-scene-set-C-graded-v3c.png")]):
        x = Wd - 10 - (i + 1) * t2[0] - i * 10
        label(d, x, y, t2[0], t, FS)
        im.paste(frame(os.path.join(G, f)).resize(t2, Image.LANCZOS), (x, y + 28))
    y += 28 + t2[1] + 20
    label(d, 10, y, Wd - 20, "100%: השטיח, האגרטל, מנורת הרגל, הדפס, מנורת קיר, הפמוטים", FS)
    full = Image.open(os.path.join(G, "default-scene-set-B-graded-v3c.png")).convert("RGB")
    boxes = [(1500, 1250, 1900, 1530), (600, 790, 760, 1100), (2300, 560, 2580, 1350), (1700, 500, 1960, 800), (2250, 480, 2320, 600), (1700, 1100, 1900, 1290)]
    x = Wd - 10
    for b in boxes:
        c = full.crop(b)
        c = c.resize((max(1, int(c.size[0] * crop_h / c.size[1])), crop_h), Image.LANCZOS)
        x -= c.size[0]
        im.paste(c, (x, y + 28))
        x -= 10
    y += 28 + crop_h + 20
    label(d, 10, y, Wd - 20, "לא נכנס, ממתין למעבר תיקון (רזרבה, באישור המנהל): המעבר הגולמי עם קווי ה-clay באדום", FS, fill=(160, 0, 0))
    for i, (t, raw, labs) in enumerate([("צעד 2 גולמי: וילון רחב פי 2, סל ליד העציץ, מחזיק עיתונים גבוה מרוחב", "raw/step2-seedream.png", (2, 4, 5, 6)),
                                        ("צעד 3 גולמי: קערה בקצה השני של השולחן, תלויה ~66 ס\"מ", "raw/step3-seedream.png", (10, 11))]):
        x = Wd - 10 - (i + 1) * t2[0] - i * 10
        label(d, x, y + 28, t2[0], t, FS)
        im.paste(outlined(os.path.join(HERE, raw), labs).resize(t2, Image.LANCZOS), (x, y + 60))
    p = os.path.join(HERE, "phase2-steps1-3-sheet.jpg")
    im.save(p, quality=90)
    print(p, im.size)


if __name__ == "__main__":
    main()
