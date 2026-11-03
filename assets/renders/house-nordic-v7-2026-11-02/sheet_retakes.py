#!/usr/bin/env python3
"""Contact sheet of the four v8 retakes of 2026-11-03 next to their predecessors (render-agent, 0 tokens):
  assets/renders/house-nordic-retakes-sheet-2026-11-03.jpg: one row per frame: predecessor (v7, graded v3) | retake (graded v3) | lock overlay.
  python3 sheet_retakes.py"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
JR = json.load(open(os.path.join(HERE, "jobs-retakes-2026-11-03.json")))
ROWS = [("W0-in", "pose-w0-in-v7", "pose-w0-in-v7-r2", "assets/renders/poses/nordic/v7/", "T-HW: slide end, pull-back start (v7 attempt copied the W0 master framing)"),
        ("K-girl-0", "pose-k-girl-0-v7", "pose-k-girl-0-v7-r2", "assets/renders/poses/nordic/v7/", "T-CGirl: slide end, pan start (v7 attempt copied the K-girl master framing)"),
        ("B1", "b1-v7", "b1-v7-r3", "assets/renders/bath/nordic/v7/", "bath, arrival (+ floor planter, + toilet brush: V7Q3)"),
        ("B2", "b2-v7", "b2-v7-r3", "assets/renders/bath/nordic/v7/", "bath, pan (+ the floor planter at the left edge: V7Q3)")]
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
except Exception:
    font = small = ImageFont.load_default()


def pick(out_dir, fid, suffixes):
    for s in suffixes:
        p = os.path.join(REPO, out_dir, fid + s)
        if os.path.exists(p):
            return p
    return None


TW, TH, PAD, LAB = 880, 495, 14, 78
cols = 3
sh = Image.new("RGB", (PAD + cols * (TW + PAD), 60 + PAD + len(ROWS) * (TH + LAB + PAD)), (24, 24, 24))
dr = ImageDraw.Draw(sh)
dr.text((PAD, 14), "Nordic house, v8 retakes of 2026-11-03 (gpt-image-2-5 sunburst 2K, recipe v8): predecessor v7 (graded v3) | retake (graded v3) | retake lock_v2 overlay. Test, not site assets.", fill=(235, 235, 235), font=font)
for r, (frame, old, new, od, label) in enumerate(ROWS):
    y = 60 + PAD + r * (TH + LAB + PAD)
    job = next((j for j in JR["jobs"] if j["id"] == new), {})
    tiles = [(pick(od, old, ["-frame-v3.png", "-graded-v3.png"]), f"{frame} v7: {old}", label),
             (pick(od, new, ["-frame-v3.png", "-graded-v3.png"]), f"{frame} retake: {new}", (f"lock_v2 {'PASS' if (job.get('lock_v2') or {}).get('pass') else 'FAIL'}: shift {(job.get('lock_v2') or {}).get('shift_px')} scale% {(job.get('lock_v2') or {}).get('scale_pct')} "
                                                                                             f"resid band {(job.get('lock_v2') or {}).get('band_after')} tile {(job.get('lock_v2') or {}).get('tile_after')} edges {(job.get('lock_v2') or {}).get('edges_worst_px')} px; "
                                                                                             f"grade v3 {(job.get('grade_v3') or {}).get('stops')} stop -> L {(job.get('grade_v3') or {}).get('measured')}") if job else "not rendered"),
             (pick(od, new, ["-lock-v2.jpg"]), f"{frame} retake: clay edges (red) over the still", "G1.4: register <= 9.6 px / 0.5 %; <= 2 px per strip after register; fixed edges +-19 px, ratios 0.95-1.05")]
    for c, (path, title, sub) in enumerate(tiles):
        x = PAD + c * (TW + PAD)
        if path and os.path.exists(path):
            im = Image.open(path).convert("RGB")
            w, h = im.size
            s = min(TW / w, TH / h)
            im = im.resize((int(w * s), int(h * s)), Image.LANCZOS)
            sh.paste(im, (x + (TW - im.size[0]) // 2, y + LAB + (TH - im.size[1]) // 2))
        else:
            dr.rectangle((x, y + LAB, x + TW, y + LAB + TH), fill=(60, 60, 60))
            dr.text((x + 20, y + LAB + TH // 2 - 10), "missing: " + (path or title), fill=(200, 200, 200), font=small)
        dr.text((x + 6, y + 6), title, fill=(245, 245, 245), font=font)
        dr.text((x + 6, y + 36), sub[:95], fill=(255, 230, 150), font=small)
        if len(sub) > 95:
            dr.text((x + 6, y + 56), sub[95:190], fill=(255, 230, 150), font=small)
out = os.path.join(REPO, "assets", "renders", "house-nordic-retakes-sheet-2026-11-03.jpg")
sh.save(out, quality=86)
print(out, sh.size)
