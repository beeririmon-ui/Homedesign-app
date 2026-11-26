"""psheet.py: qa-sheet-pecan.jpg: set B's throw before (stage-A knit) and after (Pecan muslin), x2 of the frame (1920 x 1080), the whole
frames at x0.47, and the SKU photo (Pecan, CJYD205807508HS)"""
import sys
sys.dont_write_bytecode = True
from PIL import Image, ImageDraw, ImageFont
PC = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/pecan/'
O = Image.open(PC + 'out/frame-old.png').convert('RGB'); N = Image.open(PC + 'out/frame-new.png').convert('RGB')
sku = Image.open(PC + '../wm-pilot-refs/B-sofa-cover-cj-cotton-muslin-fringe-pecan.jpg').convert('RGB')
box = (1225, 670, 1685, 1080)                       # the changed area (frame px 1234-1665 x 695-1079), inside the frame
w, h = box[2] - box[0], box[3] - box[1]
P = 16; HD = 34
try:
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
except Exception:
    font = ImageFont.load_default()
W = 2 * (2 * w) + 3 * P
small = (2 * w, int(2 * w * 1080 / 1920))
skuh = small[1]
H = HD + 2 * h + P + HD + small[1] + P + HD + skuh + P
sh = Image.new('RGB', (W, H), (245, 243, 240)); dr = ImageDraw.Draw(sh)
y = 0
dr.text((P, y + 6), 'BEFORE x2: set B, the stage-A knit (default-frame-m0w-fix1.png)', fill=(30, 30, 30), font=font)
dr.text((2 * P + 2 * w, y + 6), 'AFTER x2: the Pecan muslin (default-frame-m0w-fix1-pecan.png)', fill=(30, 30, 30), font=font)
y += HD
for i, im in enumerate((O, N)):
    sh.paste(im.crop(box).resize((2 * w, 2 * h), Image.LANCZOS), (P + i * (2 * w + P), y))
y += 2 * h + P
dr.text((P, y + 6), 'BEFORE x0.48 (the whole frame)', fill=(30, 30, 30), font=font)
dr.text((2 * P + 2 * w, y + 6), 'AFTER x0.48', fill=(30, 30, 30), font=font)
y += HD
for i, im in enumerate((O, N)):
    sh.paste(im.resize(small, Image.LANCZOS), (P + i * (2 * w + P), y))
y += small[1] + P
dr.text((P, y + 6), 'The SKU: sofa-cover-cj-cotton-muslin-fringe, Pecan 150 x 200, CJYD205807508HS (supplier photo, reference only)', fill=(30, 30, 30), font=font)
y += HD
sh.paste(sku.resize((skuh, skuh), Image.LANCZOS), (P, y))
sh.save(PC + 'out/qa-sheet-pecan.jpg', quality=90, optimize=True)
print(sh.size)
