"""MB1 comparison sheet: the two new master-bedroom base frames next to MB0 v7 and the living-room frames of the same style."""
import sys
from PIL import Image, ImageDraw, ImageFont, features
ROOT = "/home/user/homedesign-app/assets/renders/"
OUT = ROOT + "master/editorial-2026-11-07/sheet.jpg"
cols = [  # (column title, [(file, label)])
    ("נורדי", [("master/editorial-2026-11-07/nordic/nordic-MB-A.png", "חדר שינה הורים · MB-A חדש (gpt-image-2-5, 600)"),
               ("master/nordic/v7/mb0-v7-r2-graded-v5.png", "חדר שינה הורים · MB0 v7 הישן"),
               ("editorial-phase-b-2026-11-06/nordic-A-fin2.png", "סלון · נורדי A (fin2)")]),
    ("מודרני חם", [("master/editorial-2026-11-07/warm-modern/warm-modern-MB-A.png", "חדר שינה הורים · MB-A חדש (gpt-image-2-5, 600)"),
                   ("editorial-phase-b-2026-11-06/warm-modern-A-ed7.png", "סלון · מודרני חם A (ed7, קו ed5)"),
                   (None, "")]),
]
TW, TH, PAD, LAB, HEAD = 1280, 720, 24, 46, 70
fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
rtl = (lambda t: t) if features.check("raqm") else (lambda t: t[::-1])  # with raqm PIL lays out RTL itself
W = PAD + len(cols) * (TW + PAD)
H = HEAD + 3 * (TH + LAB + PAD) + PAD
sheet = Image.new("RGB", (W, H), (246, 244, 240))
d = ImageDraw.Draw(sheet)
for ci, (title, items) in enumerate(cols):
    x = PAD + ci * (TW + PAD)
    d.text((x + TW, 18), rtl(title), font=fb, fill=(30, 30, 30), anchor="ra")
    for ri, (fn, lab) in enumerate(items):
        y = HEAD + ri * (TH + LAB + PAD)
        if fn is None:
            continue
        im = Image.open(ROOT + fn).convert("RGB")
        s = min(TW / im.width, TH / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        sheet.paste(im, (x + (TW - im.width) // 2, y + (TH - im.height) // 2))
        d.text((x + TW, y + TH + 10), rtl(lab), font=f, fill=(50, 50, 50), anchor="ra")
# legend in the empty cell
x, y = PAD + TW + PAD, HEAD + 2 * (TH + LAB + PAD)
lines = ["MB1 · 2026-11-07 · פריימי בסיס בלבד, לפני QA",
         "1,200 טוקנים (600 + 600) · מבחן, לא לאתר",
         "המוצרים לפי MB-Q1: 11 בנורדי, 12 במודרני החם"]
for i, t in enumerate(lines):
    d.text((x + TW, y + 40 + i * 44), rtl(t), font=f, fill=(70, 70, 70), anchor="ra")
sheet.save(OUT, quality=88)
print(OUT, sheet.size)
