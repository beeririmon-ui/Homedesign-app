#!/usr/bin/env python3
"""
make_sheet_r4.py: the sheet of phase 2 after the code fixes R4 (render-agent, 2026-11-11). The FULL default scene with set B (all 12 defaults,
the one v3c grade), sets A and C on it, and the five fixes before (r3) / after (r4) from the graded scenes: the floor lamp's shade toned
off, the pendant's canopy, the basket's right edge, the planter's left side and bottom, and the vase scaled to the card (with the card's
outline at its own base and at the plan point). Hebrew captions laid out right to left by raqm (direction="rtl", so mixed Hebrew / Latin
runs keep their order). No supplier image is on the sheet. Writes phase2-r4-default-scene-sheet.jpg (a new file).
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_crops_r4 as MC  # noqa: E402
import make_sheet as MS  # noqa: E402  (frame)

FB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 23)
FS = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
G = os.path.join(HERE, "graded")


def label(d, x, y, w, t, font=F, fill=(0, 0, 0)):
    """right-aligned, right to left (raqm does the bidi; digits and Latin runs keep their order)"""
    tw = d.textlength(t, font=font, direction="rtl")
    d.text((x + w - tw, y), t, fill=fill, font=font, direction="rtl")


def tiles_row(im, d, y, Wd, caption, crops, h):
    """a caption, then tiles placed right to left at height h, each with its small label"""
    for line in ([caption] if isinstance(caption, str) else caption):
        label(d, 10, y, Wd - 20, line, F)
        y += 34
    x = Wd - 10
    for name, arr in crops:
        t = Image.fromarray(arr)
        z = h / t.size[1]
        t = t.resize((max(1, int(t.size[0] * z)), h), Image.NEAREST if z >= 3 else Image.LANCZOS)
        x -= t.size[0]
        label(d, x, y, t.size[0], f"{name} (×{z:.1f})", FS, (60, 60, 60))
        im.paste(t, (x, y + 26))
        x -= 14
    return y + 26 + h + 26


def main():
    fx = json.load(open(os.path.join(HERE, "work-r4/fix-r4.json")))
    man = json.load(open(os.path.join(HERE, "layers/manifest-r4.json")))
    by = {l_["id"]: l_ for l_ in man["layers"]}
    v = json.load(open(os.path.join(HERE, "layers/verify-layers-r4.json")))
    lk = json.load(open(os.path.join(HERE, "lock-and-grade-check-r4.json")))["default_scene_r4_set_B"]["lock_F3"]
    ed = json.load(open(os.path.join(HERE, "crops-r4/edges-r4.json")))["edges"]
    b = np.asarray(Image.open(os.path.join(G, "default-scene-r3-set-B-graded-v3c.png")).convert("RGB"))
    a = np.asarray(Image.open(os.path.join(G, "default-scene-r4-set-B-graded-v3c.png")).convert("RGB"))

    def c(img, box):
        x0, y0, x1, y1 = box
        return img[y0:y1, x0:x1]

    Wd = 1960
    big = (Wd - 20, int((Wd - 20) * 9 / 16))
    t2 = ((Wd - 30) // 2, int((Wd - 30) // 2 * 9 / 16))
    H = 90 + big[1] + 60 + t2[1] + 60 + 5 * 560 + 200
    im = Image.new("RGB", (Wd, H), (250, 249, 247))
    d = ImageDraw.Draw(im)
    label(d, 10, 18, Wd - 20, "הסלון במודרני חם, הכלי: שלב 2 אחרי תיקוני הקוד R4 (0 טוקנים, בלי var2)", FB)
    y = 80
    label(d, 10, y, Wd - 20, "הסצנה המלאה של ברירות המחדל עם סט B, בגריידינג v3c אחד. תוקנו: אהיל מנורת הרגל, החיבור של התלויה לתקרה, "
                             "שפת הסל, שפות העציץ, מידת האגרטל")
    im.paste(MS.frame(os.path.join(G, "default-scene-r4-set-B-graded-v3c.png")).resize(big, Image.LANCZOS), (10, y + 34))
    y += 34 + big[1] + 20
    for i, (t, f) in enumerate([("סט A על הסצנה", "default-scene-r4-set-A-graded-v3c.png"), ("סט C על הסצנה", "default-scene-r4-set-C-graded-v3c.png")]):
        x = Wd - 10 - (i + 1) * t2[0] - i * 10
        label(d, x, y, t2[0], t, FS)
        im.paste(MS.frame(os.path.join(G, f)).resize(t2, Image.LANCZOS), (x, y + 28))
    y += 28 + t2[1] + 30
    lamp = by["floor-lamp"]["fix_r4"]["remeasured"]["fabric_only"]
    tg = {k.split(" ")[0]: v_["value"] for k, v_ in lamp["targets"].items()}
    y = tiles_row(im, d, y, Wd,
                  ["1. מנורת הרגל: האהיל כבוי, לפי היעדים של המעצב (§5). הצווארון, המוט, הבסיס והשרשרת לא השתנו.",
                   f"השליש השמאלי בהיר מהימני ב-{tg['1']:.2f} (יעד: לפחות 5). התחתית כהה מהשליש הימני ב-{-tg['2']:.2f} (לפחות 5). "
                   f"השמאלי מעל הקיר ב-{tg['3a']:.2f} (לכל היותר 4). הימני מתחת לקיר ב-{-tg['3b']:.2f} (לא מעליו).",
                   f"b* מעל הקיר ב-{tg['4a']:.2f} (לכל היותר 4). פיקסלים חמים מעל הסף: {tg['4b']} (אפס). פסי הקפלים: סטיית התקן "
                   f"{lamp['highpass_std']:.2f} מול {by['floor-lamp']['fix_r4']['remeasured']['r3_for_comparison']['fabric_only']['highpass_std']:.2f} ב-r3."],
                  [("לפני (r3)", c(b, (2270, 540, 2600, 780))), ("אחרי (r4)", c(a, (2270, 540, 2600, 780))),
                   ("אחרי: הצווארון והשרשרת לא השתנו", c(a, (2380, 660, 2480, 712)))], 420)
    y = tiles_row(im, d, y, Wd, "2. התלויה: החיבור לתקרה נחתך מחדש מהרינדור הגולמי R3b, דיסק אחד שלם (היה חצי דיסק וסהר נפרד)",
                  [("לפני", c(b, (1625, 0, 1730, 62))), ("אחרי", c(a, (1625, 0, 1730, 62))), ("אחרי", c(a, (1560, 0, 1800, 160)))], 420)
    e = ed["basket right edge"]
    y = tiles_row(im, d, y, Wd,
                  f"3. הסל: הקו הבהיר בשפה הימנית. הצל של הסל נמשך עד השפה. מדד QA מול הגולמי: {e['r3_vs_raw']['cut_made_bright_px']} → "
                  f"{e['r4_vs_raw']['cut_made_bright_px']} פיקסלי קו, הרצף {e['r3_vs_raw']['bright_longest_run_px']} → {e['r4_vs_raw']['bright_longest_run_px']}",
                  [("לפני", c(b, (1095, 1060, 1160, 1250))), ("אחרי", c(a, (1095, 1060, 1160, 1250))),
                   ("אחרי", c(a, (880, 980, 1200, 1280)))], 420)
    e = ed["planter left side and bottom"]
    y = tiles_row(im, d, y, Wd,
                  f"4. העציץ: השפה הכהה והרוח. השפה השמאלית נחתכה מחדש, הסהר האפור שליד הפה הוסר, והצל נמשך עד השפה. "
                  f"רצף כהה {e['r3']['dark_longest_run_px']} → {e['r4']['dark_longest_run_px']}",
                  [("לפני", c(b, (935, 1035, 1005, 1205))), ("אחרי", c(a, (935, 1035, 1005, 1205)))], 420)
    vz = fx["vase"]
    vo = MC.vase_outlines(c(a, (560, 780, 780, 1120)), (560, 780, 780, 1120))
    y = tiles_row(im, d, y, Wd,
                  f"5. האגרטל: המידה תוקנה, המיקום ממתין למעצב. {vz['before_cm']['height']}×{vz['before_cm']['width']} ס\"מ ← "
                  f"{vz['after_cm']['height']}×{vz['after_cm']['width']} (הכרטיס 32×16), סביב הבסיס שלו. סגול: הכרטיס במקום שלו; תכלת: נקודת התוכנית",
                  [("לפני", c(b, (560, 780, 780, 1120))), ("אחרי", c(a, (560, 780, 780, 1120))), ("אחרי, עם קווי הכרטיס", vo)], 420)
    rc = v["checks"]["recomposite"]
    p999 = max(rc[s][p]["p99_9_region"] for s in rc for p in rc[s])
    mx = max(rc[s][p]["max"] for s in rc for p in rc[s])
    sw = max(x_.get("changed_outside_region", x_.get("changed_outside_union", 0)) for x_ in v["checks"]["swap_diff"].values())
    worst = max(l_["p90_abs_px"] for l_ in lk["lines"].values())
    gr = max(abs(x_["residual_median"]) for x_ in v["checks"]["one_v3c_grade"]["products"].values())
    d.text((10, y + 6), f"R4: 0 tokens | swap-diff {sw} px outside every region | recomposite p99.9 <= {p999:.0f}, max {mx:.0f} (gate 2 / 6) | "
           f"one v3c grade: |residual median| <= {gr:.2f} | shell lock {'pass' if lk['verdict']['pass_'] else 'FAIL'}, worst p90 {worst:.1f} px | "
           f"verify {'pass' if v['pass'] else 'FAIL'}", fill=(0, 0, 0), font=FS)
    im = im.crop((0, 0, Wd, y + 40))
    p = os.path.join(HERE, "phase2-r4-default-scene-sheet.jpg")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    im.save(p, quality=90)
    print(p, im.size)


if __name__ == "__main__":
    main()
