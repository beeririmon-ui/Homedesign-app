#!/usr/bin/env python3
"""Contact sheets of the v7 test (render-agent, 2026-11-02):
  assets/renders/house-nordic-sheet-v7-2026-11-02.jpg         the 11 master frames (graded), house-plan order, 4 per row, labelled
  assets/renders/house-nordic-poses-sheet-v7-2026-11-02.jpg   the transition poses (graded), in transition order, 4 per row, labelled
A frame or pose without an accepted render gets a grey tile that says why (jobs.json sheet_label).
  python3 sheet_v7.py"""
import json, os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
MASTERS = [("M0", "living room"), ("D1", "kitchen-dining, arrival"), ("D2", "kitchen-dining, pan"), ("H0", "hall (site opening frame)"),
           ("C0", "corridor"), ("MB0", "master bedroom"), ("K-boy", "boy's room"), ("K-girl", "girl's room"), ("B1", "bath, arrival"),
           ("B2", "bath, pan"), ("W0", "work room")]
POSES = [("H0x", "T-E0: end of the hall pan, dolly start"), ("M0p", "T-LD: end of pan P0"), ("M0x", "T-LD: end of pan P1, dolly start"),
         ("PD-35", "T-LD: dolly end, pan P2 start"), ("H0e", "T-HW / T-HC: end of the hall pan"), ("W0-in", "T-HW: slide end, pull-back start"),
         ("S1prime", "rail station S1' (T-HC, T-CBoy, T-CBath)"), ("R2m", "rail checkpoint R2m"), ("K-boy-0", "T-CBoy: slide end, pan start"),
         ("K-girl-0", "T-CGirl: slide end, pan start"), ("CB-0", "T-CBath: slide end, pan start"), ("MB-in", "T-CM: pull-back end, slide start")]
NOJOB = {'R2m': 'not needed for route R (motion-agent: V6 retry only); clay not rendered, 0 tokens'}
J = json.load(open(os.path.join(HERE, 'jobs.json')))
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
except Exception:
    font = small = ImageFont.load_default()


def accepted(fid):
    js = [j for j in J['jobs'] if j['frame'] == fid and j.get('status') == 'done']
    s = [j for j in js if j.get('sheet')]
    return (s or js or [None])[-1]


def build(items, out, title):
    TW, TH, PAD, LAB, cols = 960, 540, 14, 72, 4
    rows = (len(items) + cols - 1) // cols
    sh = Image.new("RGB", (PAD + cols * (TW + PAD), 60 + PAD + rows * (TH + LAB + PAD)), (24, 24, 24))
    dr = ImageDraw.Draw(sh)
    dr.text((PAD, 14), title, fill=(235, 235, 235), font=font)
    for k, (fid, label) in enumerate(items):
        x = PAD + (k % cols) * (TW + PAD)
        y = 60 + PAD + (k // cols) * (TH + LAB + PAD)
        j = accepted(fid)
        path = None
        if j:
            fp = os.path.join(REPO, j['out_dir'], j['id'] + '-frame.png')          # overscan stills: the 16:9 frame (centre crop)
            path = fp if os.path.exists(fp) else os.path.join(REPO, j['out_dir'], j['id'] + '-graded.png')
        if path and os.path.exists(path):
            im = Image.open(path).convert("RGB")
            w, h = im.size
            s = min(TW / w, TH / h)
            im = im.resize((int(w * s), int(h * s)), Image.LANCZOS)
            sh.paste(im, (x + (TW - im.size[0]) // 2, y + LAB + (TH - im.size[1]) // 2))
            sub = j.get('sheet_label') or f"gpt-image-2-5 sunburst 2K  attempt {j['attempt']}"
        else:
            dr.rectangle((x, y + LAB, x + TW, y + LAB + TH), fill=(60, 60, 60))
            js = [b for b in J['jobs'] if b['frame'] == fid]
            dr.text((x + 20, y + LAB + TH // 2 - 10), "not rendered: " + ((js[-1].get('sheet_label') or js[-1].get('status', '')) if js else NOJOB.get(fid, 'no job')), fill=(200, 200, 200), font=small)
            sub = ""
        dr.text((x + 6, y + 6), f"{fid}  |  {label}", fill=(245, 245, 245), font=font)
        if sub:
            dr.text((x + 6, y + 40), sub[:110], fill=(255, 230, 150), font=small)
    sh.save(out, quality=86)
    print(out, sh.size)


build(MASTERS, os.path.join(REPO, 'assets', 'renders', 'house-nordic-sheet-v7-2026-11-02.jpg'),
      "Nordic house, v7 master frames (gpt-image-2-5 sunburst 2K, image-to-image from the round-4 clay), graded. House-plan order. 2026-11-02. Test, not site assets.")
build(POSES, os.path.join(REPO, 'assets', 'renders', 'house-nordic-poses-sheet-v7-2026-11-02.jpg'),
      "Nordic house, v7 transition poses for route R (image-to-image from the round-4 pose clays, masters as references), graded. 2026-11-02. Test.")
