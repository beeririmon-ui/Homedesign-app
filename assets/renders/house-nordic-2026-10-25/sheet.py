#!/usr/bin/env python3
"""
assets/renders/house-nordic-sheet-2026-10-25.jpg: the 11 Phase B frames (graded drafts) in house-plan order, 4 per row, labelled
with the frame id and the room. A frame without a draft gets a grey tile that says so.
  python3 sheet.py [jobs.json]
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(REPO, "assets", "renders", "house-nordic-sheet-2026-10-25.jpg")
ORDER = [("M0", "living-room", "living room"), ("D1", "kitchen-dining", "kitchen-dining, arrival"), ("D2", "kitchen-dining", "kitchen-dining, pan"),
         ("H0", "hall", "hall (site opening frame)"), ("C0", "corridor", "corridor"), ("MB0", "master", "master bedroom"),
         ("K-boy", "boy", "boy's room"), ("K-girl", "girl", "girl's room"), ("B1", "bath", "bath, arrival"), ("B2", "bath", "bath, pan"),
         ("W0", "work", "work room")]
jobs = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "jobs.json")))
by_frame = {}
for j in jobs.get("jobs", []):
    if j.get("status") == "done":
        by_frame[j["frame"]] = j                      # the last done job of a frame (the retake when there is one)
TW, TH, PAD, LAB = 960, 540, 14, 44
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
except Exception:
    font = small = ImageFont.load_default()
cols = 4
rows = (len(ORDER) + cols - 1) // cols
sheet = Image.new("RGB", (PAD + cols * (TW + PAD), 60 + PAD + rows * (TH + LAB + PAD)), (24, 24, 24))
dr = ImageDraw.Draw(sheet)
dr.text((PAD, 14), "Nordic house, Phase B drafts (recipe B: gpt-image-2-5 sunburst 2K, image-to-image from the round-3 clay), graded. "
                   "House-plan order. 2026-10-25. Drafts for gate 2, not site assets.", fill=(235, 235, 235), font=font)
for k, (fid, room, label) in enumerate(ORDER):
    x = PAD + (k % cols) * (TW + PAD)
    y = 60 + PAD + (k // cols) * (TH + LAB + PAD)
    j = by_frame.get(fid)
    path = os.path.join(REPO, j["graded"]) if j and j.get("graded") else None
    if path and os.path.exists(path):
        im = Image.open(path).convert("RGB")
        w, h = im.size
        s = min(TW / w, TH / h)
        im = im.resize((int(w * s), int(h * s)), Image.LANCZOS)
        sheet.paste(im, (x + (TW - im.size[0]) // 2, y + LAB + (TH - im.size[1]) // 2))
        lk = j.get('lock', '?')
        lk = lk.get('visual', '?') if isinstance(lk, dict) else lk
        sub = f"{j['model']} {j.get('quality') or ''} 2K  attempt {j['attempt']}  lock {lk}  {j.get('products', {}).get('invented', '') if isinstance(j.get('products'), dict) else ''}"
    else:
        dr.rectangle((x, y + LAB, x + TW, y + LAB + TH), fill=(60, 60, 60))
        dr.text((x + 20, y + LAB + TH // 2 - 10), "no draft (see jobs.json)", fill=(200, 200, 200), font=small)
        sub = ""
    dr.text((x + 6, y + 6), f"{fid}  |  {label}", fill=(245, 245, 245), font=font)
    if sub:
        dr.text((x + 6, y + LAB + 6), sub[:120], fill=(255, 230, 150), font=small)
sheet.save(OUT, quality=86)
print(OUT, sheet.size, len(by_frame), "frames")
