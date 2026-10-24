# compare.jpg for gate 1: row 1 = the M0 drafts (graded) + the old pilot + the old styled preview; row 2 = H0 draft raw/graded + the two clays. Labels on each tile.
import os
from PIL import Image, ImageDraw, ImageFont
R = '/home/user/homedesign-app/'
D = R + 'assets/renders/living-room/nordic/recipe-v5/'
H = R + 'assets/renders/hall/nordic/recipe-v5/'
row1 = [('m0-A  flux-2 2K  (graded) - LOCK BROKEN', D + 'm0-A-graded.png'),
        ('m0-A retake  flux-2 2K  (graded)', D + 'm0-A-retake-graded.png'),
        ('m0-B  gpt-image-2-5 sunburst 2K  (graded)', D + 'm0-B-graded.png'),
        ('m0-C  nano-banana-2 2K  (graded)', D + 'm0-C-graded.png'),
        ('m0-A-styled  flux-2 2K  (graded) - added table, no products', D + 'm0-A-styled-graded.png'),
        ('OLD pilot v4.1 b-graded  nano-banana-2 (2026-10-04)', R + 'assets/renders/living-room/nordic/m0/pilot-v4.1/m0-pilot-b-graded.png'),
        ('OLD styled preview r2 (2026-10-06)', R + 'assets/renders/living-room/nordic/styled-preview-r2/styled-preview.png')]
row2 = [('h0-A  flux-2 2K  raw', H + 'h0-A.png'),
        ('h0-A  flux-2 2K  (graded) - placeholders rendered literally', H + 'h0-A-graded.png'),
        ('H0 clay  H-B-lit.png (input)', R + 'assets/blockout/house/framing/round2/H-B-lit.png'),
        ('M0 clay  m0-clay-4k.png (input)', R + 'assets/blockout/living-room/m0-clay-4k.png'),
        ('m0-B raw (before grade)', D + 'm0-B.png'),
        ('m0-C raw (before grade)', D + 'm0-C.png')]
TW, TH, PAD, LAB = 960, 540, 12, 34
font = ImageFont.load_default()
try:
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
except Exception:
    pass
rows = [[t for t in row1 if os.path.exists(t[1])], [t for t in row2 if os.path.exists(t[1])]]
ncol = max(len(r) for r in rows)
sheet = Image.new('RGB', (PAD + ncol * (TW + PAD), PAD + 2 * (TH + LAB + PAD)), (24, 24, 24))
dr = ImageDraw.Draw(sheet)
for ri, row in enumerate(rows):
    for ci, (label, path) in enumerate(row):
        im = Image.open(path).convert('RGB')
        w, h = im.size
        s = min(TW / w, TH / h)
        im = im.resize((int(w * s), int(h * s)), Image.LANCZOS)
        x = PAD + ci * (TW + PAD); y = PAD + ri * (TH + LAB + PAD)
        sheet.paste(im, (x + (TW - im.size[0]) // 2, y + LAB + (TH - im.size[1]) // 2))
        dr.text((x + 6, y + 6), label, fill=(235, 235, 235), font=font)
sheet.save(D + 'compare.jpg', quality=86)
print('compare.jpg', sheet.size, [len(r) for r in rows])
