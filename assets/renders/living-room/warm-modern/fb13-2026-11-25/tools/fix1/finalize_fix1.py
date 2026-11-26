"""finalize_fix1.py: write the fix1 files into fb13-2026-11-25/ (new names only; the stage-A files stay for rollback), the manifest-fix1,
the checks, the QA sheet, the jobs record, and the assets/manifest.json entries (re-read just before writing)."""
import json, os, sys, hashlib, shutil
import cv2, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fix1/tools')
import stack as ST
S = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fix1/'
O = S + 'out/stack-fix1/'
D = ST.FB13 + '/'
REPO = '/home/user/homedesign-app/'
REL = 'assets/renders/living-room/warm-modern/fb13-2026-11-25'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rd = lambda p, m: np.asarray(Image.open(p).convert(m))
man = json.load(open(D + 'layers/manifest.json'))
P = {'planter': 'planter-cj-cement-ribbed-belly', 'magazine-holder': 'magazine-holder-cj-gunmetal-leather-strap',
     'curtains': 'curtains-aliexpress-linen-blend-s-fold-180502', 'rug': 'rug-cj-braided-wool-natural'}
files = {f'layers/planter/{P["planter"]}-fix1.png': O + 'layer-planter.png', f'shadows/planter/{P["planter"]}-fix1.png': O + 'shadow-planter.png',
         f'layers/magazine-holder/{P["magazine-holder"]}-fix1.png': O + 'layer-magazine-holder.png',
         f'shadows/magazine-holder/{P["magazine-holder"]}-fix1.png': O + 'shadow-magazine-holder.png',
         f'layers/curtains/{P["curtains"]}.png': O + 'layer-curtains.png', f'shadows/curtains/{P["curtains"]}.png': O + 'shadow-curtains.png',
         f'layers/rug/{P["rug"]}-fix1.png': O + 'layer-rug.png'}
for i, lt in enumerate(man['light']):
    files[lt['file'].replace('.png', '-fix1.png')] = O + f'light-{i}.png'
for rel, src in files.items():
    os.makedirs(os.path.dirname(D + rel), exist_ok=True)
    Image.open(src).save(D + rel, optimize=True)
# ---- the new stack from the repo files (the frame is built from them)
man2 = json.loads(json.dumps(man))
man2['id'] = 'wm-living-room-m0w-fb13-fix1-2026-11-26'
man2['status'] = ('FB13 M0-W fix1 (the owner, 2026-11-26: "the tree in the pot looks like leaves floating in the air, there is no curtain, and the '
                  'newspaper holder is cut"): the olive, the curtain and the holder. Not QA\'d; HD_PUBLIC=0 only. Rollback: manifest.json + ../default-frame-m0w.png')
man2['method'] = man['method'] + '. fix1: four nano-banana-2 2K edits of crops of hero-HW.png (E1 olive, E2 curtain, E3 holder at its new place, E4 the old holder out), registered (SIFT affine) and tone-matched, pasted into their own regions -> ../hero-HW-fix1.png; the changed layers cut from it; shadows solved against the compose formula (tools/fix1/extract_fix1.py)'
lay2 = []
ex = json.load(open(O + 'extract.json')); meas = json.load(open(O + 'measure.json')); rnd = json.load(open(O + 'rnd2.json'))
def stats(lp, sp):
    a = rd(D + lp, 'RGBA')[..., 3]; s = rd(D + sp, 'RGB')
    ys, xs = np.nonzero(a)
    return dict(alpha_px=int((a > 0).sum()), shadow_px=int((s < 255).any(2).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())])
cur = dict(slot='curtains', product=P['curtains'], z=10, shadow_z=9, default=True, layer=f'layers/curtains/{P["curtains"]}.png',
           shadow=f'shadows/curtains/{P["curtains"]}.png', sold=True, option=dict(style='s-fold', size='132x270'), sku='12000059196236244',
           source='hero-HW-fix1.png (nano-banana-2 2K edit E2 of hero-HW.png) cut in code',
           note='the sheer linen at the left glazing edge, half drawn, the sun through it; alpha by its own hem; the vase (z 16) stands in front of its leading edge; '
                'its shadow file is neutral (sheer: the sun patch on the wall is kept as it was). The stack sits in view (about Y 1.75-2.0), not at the slot\'s Y 2.65-2.95: for the designer')
lay2.append(dict(cur, **stats(cur['layer'], cur['shadow'])))
for l in man['layers']:
    l = dict(l)
    if l['slot'] == 'planter':
        l.update(layer=f'layers/planter/{P["planter"]}-fix1.png', shadow=f'shadows/planter/{P["planter"]}-fix1.png',
                 source='hero-HW-fix1.png: the pot is the stage-A layer below the rim, pixel for pixel; the olive (filler) and its leaf shadow from nano edit E1')
    if l['slot'] == 'magazine-holder':
        l.update(layer=f'layers/magazine-holder/{P["magazine-holder"]}-fix1.png', shadow=f'shadows/magazine-holder/{P["magazine-holder"]}-fix1.png',
                 source='hero-HW-fix1.png (nano edit E3: on the oak floor right of the floor lamp, between the skirting and the rug) cut in code; '
                        'refit in code x0.92 about its feet line and centred between the lamp and the frame edge (F3 0.02 / edge 0.02; the card is 35 cm wide)',
                 refit=ex.get('holder_refit'))
    if l['slot'] == 'rug':
        l.update(layer=f'layers/rug/{P["rug"]}-fix1.png', source=l['source'] + '; fix1: under the old holder place, the rug from nano edit E4')
    l.update(stats(l['layer'], l['shadow']))
    lay2.append(l)
man2['layers'] = lay2
for lt in man2['light']:
    lt['file'] = lt['file'].replace('.png', '-fix1.png')
    lt['note'] = 'fix1: filled from the wall around under the old olive\'s floating leaves only (never seen before; now open wall)'
man2['not_in_frame'] = ['wall-sconce (window wall, out of frame)']
man2['moved_for_the_frame'] = dict(man['moved_for_the_frame'], magazine_holder=dict(
    to='about (1.92, 0.33), right of the floor lamp on the oak floor between the skirting and the rug (estimated from the image)',
    was=[-0.68, 2.25], why='fix1: cut by the bottom edge; no place on the left passes F3 and >= 90 % visible (armchair, basket, planter and the sofa fill the floor strip)'))
man2['rnd2'] = dict(rnd, rule='outside the changed layers\' alpha, shadow and light: the stage-A stack, pixel for pixel; hiding one product changes its own region only')
man2['files'] = dict(hero='../hero-HW-fix1.png', default_frame='../default-frame-m0w-fix1.png', checks='../checks-m0w-fix1.json',
                     sheet='../qa-sheet-m0w-fix1.jpg', jobs='../jobs-fix1.json', tools='../tools/fix1/', rollback='manifest.json')
json.dump(man2, open(D + 'layers/manifest-fix1.json', 'w'), indent=1, ensure_ascii=False)
m2, base, lays, lights = ST.load('layers/manifest-fix1.json')
canvas = ST.compose(base, lays, lights)
fr = ST.frame(canvas, m2)
Image.fromarray(fr).save(D + 'default-frame-m0w-fix1.png', optimize=True)
again = rd(S + 'out/default-frame-m0w-fix1.png', 'RGB')
rep_files = dict(frame_from_repo_files_vs_scratch_build_max_diff=int(np.abs(fr.astype(int) - again.astype(int)).max()))
# ---- the hero record: the edits; the holder's zone as the stack shows it (the refit), de-finished
hero_rec = rd(S + 'out/hero-fix1.png', 'RGB').astype(np.float32) / 255
sys.path.insert(0, '/home/user/homedesign-app/assets/renders/tools/finish')
import finish as F
H, W = 1530, 2720
FB = man['frame_box']
x0, y0, x1, y1 = FB
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
rho = np.hypot((xx - (x0 + x1) / 2) / ((x1 - x0) / 2), (yy - (y0 + y1) / 2) / ((y1 - y0) / 2)) / np.sqrt(2.0)
V = (2.0 ** (-0.15 * np.clip(rho, 0, 1.15) ** 2.4)).astype(np.float32)
Lb = F.Lstar(base) / 100.0
GR = F.grain_field((H, W)) * 1.2 * np.clip(4 * Lb * (1 - Lb), 0.25, 1.0)
srgb2lin = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
lin2srgb = lambda a: np.where(a <= 0.0031308, a * 12.92, 1.055 * np.clip(a, 0, None) ** (1 / 2.4) - 0.055)
unb = np.clip(lin2srgb(srgb2lin(np.clip((canvas.astype(np.float32) - GR[..., None]) / 255.0, 0, 1)) / V[..., None]), 0, 1)
zone = np.zeros((H, W), bool); zone[1100:1460, 2280:2642] = True
hero_rec[zone] = unb[zone]
Image.fromarray(np.rint(hero_rec * 255).astype(np.uint8)).save(D + 'hero-HW-fix1.png', optimize=True)
# ---- raw returns and tools
for nm in ['e1-olive', 'e2-curtain', 'e3-holder', 'e4-holderout']:
    shutil.copyfile(S + f'ret/{nm}-nano.jpg', D + f'raw/fix1-{nm}-nano.jpg')
os.makedirs(D + 'tools/fix1', exist_ok=True)
for t in ['stack.py', 'reg.py', 'hero_fix1.py', 'extract_fix1.py', 'compose_fix1.py', 'measure_fix1.py', 'finalize_fix1.py']:
    shutil.copyfile(S + 'tools/' + t, D + 'tools/fix1/' + t)
# ---- the QA sheet: before / after at x1, then x2 of each fix
old_fr = rd(D + 'default-frame-m0w.png', 'RGB')
crops = [('E1 the olive and its leaf shadow', (440, 250, 920, 610)), ('E2 the curtain (the vase in front)', (0, 380, 480, 740)),
         ('E3 the holder, new place', (1440, 720, 1920, 1080)), ('E4 the old holder place (bottom edge)', (330, 720, 810, 1080))]
Wd = 3840
sheet = Image.new('RGB', (Wd, 40 + 1080 + 2 * (40 + 720)), (24, 24, 24))
d = ImageDraw.Draw(sheet)
d.text((10, 12), 'BEFORE: default-frame-m0w.png (x1)', fill=(235, 235, 235)); d.text((1930, 12), 'AFTER: default-frame-m0w-fix1.png (x1)', fill=(235, 235, 235))
sheet.paste(Image.fromarray(old_fr), (0, 40)); sheet.paste(Image.fromarray(fr), (1920, 40))
for i, (lab, (a, b, c, e)) in enumerate(crops):
    r, col = divmod(i, 2)
    oy = 40 + 1080 + r * 760; ox = col * 1920
    d.text((ox + 10, oy + 12), lab + ': before | after (x2)', fill=(235, 235, 235))
    for j, im in enumerate((old_fr, fr)):
        cimg = Image.fromarray(im[b:e, a:c]).resize(((c - a) * 2, (e - b) * 2), Image.NEAREST)
        sheet.paste(cimg.crop((0, 0, 960, 720)), (ox + j * 960, oy + 40))
sheet.save(D + 'qa-sheet-m0w-fix1.jpg', quality=88)
# ---- checks
reg = json.load(open(S + 'ret/reg.json'))
reg['e4-holderout'] = ex.get('e4_registration')
checks = dict(rnd2=rnd, files=rep_files, light=meas['light'], holder=meas['holder'], curtain=meas['curtain'], olive=meas['olive'],
              extract={k: v for k, v in ex.items() if k != 'e4_registration'}, registration=reg,
              fidelity=dict(planter='the pot is the stage-A layer below the rim, byte for byte (planter_body_below_mouth_identical)',
                            magazine_holder='gunmetal arched tubes, cognac straps with rivets, two newspapers (CJYD201631004DW, Orange small). Size: nano drew it about '
                                            '0.38 m wide x 0.40 m high; refit x0.92 to the card\'s 35 cm width; the height stays about 0.37 m against the card\'s 27.5 cm '
                                            '(the card notes a 350 x 190 x 275 mm carton): for sourcing / the designer',
                            curtains='off-white oat linen-blend sheer with slub and vertical yarn lines, S-fold, light-filtering (card #EDE7DB), the sun through it',
                            olive='filler, not sold: a potted olive standard, trunk and branches carry every leaf; top 43 px higher than stage A (~8 cm), crown ~0.8 m wide'))
json.dump(checks, open(D + 'checks-m0w-fix1.json', 'w'), indent=1, default=str)
print(json.dumps(rep_files))
