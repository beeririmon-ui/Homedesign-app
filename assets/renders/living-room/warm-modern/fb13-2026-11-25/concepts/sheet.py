#!/usr/bin/env python3
"""sheet.py: concepts-sheet.jpg (A and B side by side, labelled, <= 2400 px wide). python3 -P sheet.py <concept-A.png> <concept-B.png> <out.jpg>"""
import sys
from PIL import Image, ImageDraw, ImageFont
a, b, out = sys.argv[1:4]
A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
W = 2400
gap, pad, head = 24, 24, 92
w = (W - 2 * pad - gap) // 2
h = round(w * A.size[1] / A.size[0])
A, B = A.resize((w, h), Image.LANCZOS), B.resize((w, round(w * B.size[1] / B.size[0])), Image.LANCZOS)
sh = Image.new("RGB", (W, head + h + pad), (246, 243, 238))
sh.paste(A, (pad, head))
sh.paste(B, (pad + w + gap, head))
d = ImageDraw.Draw(sh)
f1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
ink, sub = (46, 40, 36), (110, 100, 92)
d.text((pad, 14), "A   Today's rules", font=f1, fill=ink)
d.text((pad, 58), "soft daylight, no direct sun, half a stop lower: the lamps carry the picture", font=f2, fill=sub)
d.text((pad + w + gap, 14), "B   The last winter sun  (the designer's pick)", font=f1, fill=ink)
d.text((pad + w + gap, 58), "low winter sun through the glazing, the olive's leaf shadow on the plaster, lamps on", font=f2, fill=sub)
sh.save(out, quality=90, optimize=True)
print(sh.size)
