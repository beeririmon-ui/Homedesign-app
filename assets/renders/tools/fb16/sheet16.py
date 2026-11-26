import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common16 import *
from PIL import ImageDraw, ImageFont
REPO = "/home/user/homedesign-app"
FB = [77.4853, 43.4279, 2642.5147, 1486.5721]
def fnt(s):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", s)
    except OSError:
        return ImageFont.load_default()
def fv(p, fb=FB):
    im = Image.open(p).convert("RGB")
    if im.size == (1920, 1080):
        return im
    return im.crop(tuple(int(round(v)) for v in fb)).resize((1920, 1080), Image.BICUBIC)
tiles = [("M0-W  default frame (the reference)", f"{R}/living-room/warm-modern/fb13-2026-11-25/default-frame-m0w.png", None),
         ("M0-W  hero H-W", f"{R}/living-room/warm-modern/fb13-2026-11-25/hero-HW.png", None),
         ("D0  as approved (not touched)", f"{R}/hall/warm-modern/door-2026-11-16/d0.png", None)]
for k in ["HT2", "HDx2", "D1", "D2", "W0", "K-boy", "K-girl", "MB0", "MB1", "B1", "B2"]:
    fc = F.ROOMS[k]; p = os.path.join(R, fc["out_dir"], fc["out_name"] + "-fb16-frame.png")
    cp = os.path.join(R, fc["out_dir"], fc["out_name"] + "-fb16-checks.json")
    lab_ = ""
    if os.path.exists(cp):
        c = json.load(open(cp)); a = c["after"]
        lab_ = f"plaster L {a['plaster'][0]:.1f} b* {a['plaster'][2]:.1f} | black {a['black_p05']:.1f}"
    tiles.append((f"{k}  fb16", p if os.path.exists(p) else None, lab_))
tw, th, cols, pad, lh = 1280, 720, 4, 16, 44
rows = (len(tiles) + cols - 1) // cols
S = Image.new("RGB", (cols * (tw + pad) + pad, 90 + rows * (th + lh + pad) + pad), (245, 243, 240))
d = ImageDraw.Draw(S)
d.text((pad, 22), "FB16, the house at 15:40: every warm-modern frame at x1 (1280 x 720 of the 1920 frame). Not QA'd, HD_PUBLIC=0. render-agent 2026-11-26", fill=(30, 30, 30), font=fnt(34))
for i, (name, p, lab_) in enumerate(tiles):
    x = pad + (i % cols) * (tw + pad); y = 90 + (i // cols) * (th + lh + pad)
    if p:
        S.paste(fv(p).resize((tw, th), Image.LANCZOS), (x, y + lh))
    d.text((x, y + 6), name + ("   " + lab_ if lab_ else ""), fill=(30, 30, 30), font=fnt(26))
out = f"{REPO}/assets/renders/house-light-fb16.jpg"
S.save(out, quality=86, optimize=True)
print(out, S.size, os.path.getsize(out))
