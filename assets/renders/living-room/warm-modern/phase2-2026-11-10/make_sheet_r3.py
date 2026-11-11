#!/usr/bin/env python3
"""
make_sheet_r3.py: the sheet of phase 2 after the fix passes R3a / R3b (render-agent, 2026-11-11). The FULL default scene with set B (all 12
defaults, one v3c grade; the bowl marked provisional), sets A and C on it, the three new layers at 100 % from the graded scene, and the two
passes: input (photographic placeholder) and render, with the step-0 clay outlined in red. No supplier image is on the sheet.
Writes phase2-r3-default-scene-sheet.jpg (a new file).
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_sheet as MS  # noqa: E402  (frame, label, fonts)

FID = json.load(open(os.path.join(HERE, "work-r3/fidelity-r3.json")))["products"]


def outlined(img_path, npz, keys, crop, npy=False):
    z = np.load(os.path.join(HERE, npz))
    if npy:
        r = (np.clip(np.load(os.path.join(HERE, img_path)).astype(np.float32), 0, 1) * 255).astype(np.uint8)
    else:
        r = np.asarray(Image.open(os.path.join(HERE, img_path)).convert("RGB")).copy()
    for k in keys:
        m = (z[f"clay_{k}"].astype(np.float32) > 0.5).astype(np.uint8)
        e = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(bool)
        r[e] = (230, 30, 30)
    return Image.fromarray(r).crop(crop)


def main():
    G = os.path.join(HERE, "graded")
    Wd = 1960
    big = (Wd - 20, int((Wd - 20) * 9 / 16))
    t2 = ((Wd - 30) // 2, int((Wd - 30) // 2 * 9 / 16))
    crop_h = 420
    pass_h = 460
    H = 90 + big[1] + 60 + t2[1] + 60 + crop_h + 70 + pass_h + 70 + pass_h + 150
    im = Image.new("RGB", (Wd, H), (250, 249, 247))
    d = ImageDraw.Draw(im)
    MS.label(d, 10, 18, Wd - 20, "הסלון במודרני חם, הכלי: שלב 2 אחרי מעבר התיקון R3 (12 מתוך 12 ברירות מחדל בשכבות)", MS.FB)
    y = 80
    MS.label(d, 10, y, Wd - 20, "הסצנה המלאה של ברירות המחדל עם סט B, בגריידינג v3c אחד. חדש: עציץ וסל (R3a), תלויה (R3b). הקערה: מיקום זמני (WM-T2)")
    im.paste(MS.frame(os.path.join(G, "default-scene-r3-set-B-graded-v3c.png")).resize(big, Image.LANCZOS), (10, y + 34))
    y += 34 + big[1] + 20
    for i, (t, f) in enumerate([("סט A על הסצנה", "default-scene-r3-set-A-graded-v3c.png"), ("סט C על הסצנה", "default-scene-r3-set-C-graded-v3c.png")]):
        x = Wd - 10 - (i + 1) * t2[0] - i * 10
        MS.label(d, x, y, t2[0], t, MS.FS)
        im.paste(MS.frame(os.path.join(G, f)).resize(t2, Image.LANCZOS), (x, y + 28))
    y += 28 + t2[1] + 20
    MS.label(d, 10, y, Wd - 20, "100% מהסצנה המדורגת: העציץ מאחורי הסל (הסל מסתיר כ-75% ממנו, לפי התוכנית), והתלויה עם הכבל והחיבור לתקרה", MS.FS)
    full = Image.open(os.path.join(G, "default-scene-r3-set-B-graded-v3c.png")).convert("RGB")
    sx, sy = full.size[0] / 2720, full.size[1] / 1530
    boxes = [(880, 700, 1220, 1270), (1480, 0, 1880, 420)]
    x = Wd - 10
    for b in boxes:
        c = full.crop((round(b[0] * sx), round(b[1] * sy), round(b[2] * sx), round(b[3] * sy)))
        c = c.resize((max(1, int(c.size[0] * crop_h / c.size[1])), crop_h), Image.LANCZOS)
        x -= c.size[0]
        im.paste(c, (x, y + 28))
        x -= 10
    y += 28 + crop_h + 30
    pl, ba, pe = FID["planter"], FID["basket"], FID["pendant"]
    rows = [
        ("R3a: קלט (ממלא מקום צילומי על ה-clay), הרינדור, ה-clay באדום. "
         f"הסל {ba['body_width_cm']:.0f} ס\"מ, {ba['offset_vs_clay_same_method_cm']:.1f} ס\"מ מה-clay; העציץ: בטן {pl['belly_left_px']['delta_cm']:+.1f}, "
         f"שפה {pl['rim_top_delta_cm']:+.1f}, בסיס {pl['base_delta_cm']:+.1f} ס\"מ; הפתח כ-{pl['opening_cm_if_symmetric']['render']:.0f} מול 35.5 (חלקי)",
         [("inputs/r3a-input.png", False), ("work-r3/r3a-regt.npy", True)], "work-r3/ph-r3a.npz", ("pot", "basket_body"), (880, 700, 1220, 1270)),
        (f"R3b: קלט ורינדור. תחתית האהיל ב-{pe['shade_bottom_Z_fit_m']:.3f} (1.90 בתוכנית, R2 היה 1.80), רוחב {pe['width_cm']:.1f} ס\"מ, "
         f"מרכז {pe['centre_x_offset_cm']:+.1f} ס\"מ",
         [("inputs/r3b-input.png", False), ("work-r3/r3b-regt.npy", True)], "work-r3/ph-r3b.npz", ("shade",), (1460, 0, 1860, 440)),
    ]
    for t, srcs, npz, keys, crop in rows:
        MS.label(d, 10, y, Wd - 20, t, MS.FS)
        x = Wd - 10
        tiles = [outlined(p, npz, (), crop, npy) for p, npy in srcs[:1]] + [outlined(p, npz, keys, crop, npy) for p, npy in srcs[1:]] \
            + [outlined(srcs[1][0], npz, (), crop, True)]
        for c in tiles:
            c = c.resize((max(1, int(c.size[0] * pass_h / c.size[1])), pass_h), Image.LANCZOS)
            x -= c.size[0]
            im.paste(c, (x, y + 32))
            x -= 14
        y += 32 + pass_h + 38
    MS.label(d, 10, y, Wd - 20, "R3a ו-R3b: ‏1,300 טוקנים (650 + 650), שני מעברים, בלי שלישי", MS.FS)
    v = json.load(open(os.path.join(HERE, "layers/verify-layers-r3.json")))
    lk = json.load(open(os.path.join(HERE, "lock-and-grade-check-r3.json")))["default_scene_r3_set_B"]["lock_F3"]
    rc = v["checks"]["recomposite"]
    p999 = max(rc[s][p]["p99_9_region"] for s in rc for p in rc[s])
    mx = max(rc[s][p]["max"] for s in rc for p in rc[s])
    sw = max(x_.get("changed_outside_region", x_.get("changed_outside_union", 0)) for x_ in v["checks"]["swap_diff"].values())
    worst = max(l_["p90_abs_px"] for l_ in lk["lines"].values())
    d.text((10, y + 32), f"R3a 650 + R3b 650 | swap-diff {sw} px outside every region | recomposite p99.9 <= {p999:.0f}, max {mx:.0f} (gate 2 / 6) | "
           f"shell lock {'pass' if lk['verdict']['pass_'] else 'FAIL'}, worst p90 {worst:.1f} px", fill=(0, 0, 0), font=MS.FS)
    p = os.path.join(HERE, "phase2-r3-default-scene-sheet.jpg")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    im.save(p, quality=90)
    print(p, im.size)


if __name__ == "__main__":
    main()
