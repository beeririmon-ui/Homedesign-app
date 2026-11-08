"""qa-agent, 2026-11-07 (interface track S3-S5): G-ED.17 and G-ED.18 on every dot of the living-room story pages, boho fin7
and mediterranean ed7 included. A copy of the S1/S2 tool: the built pages come from QA's snapshot of web/dist ($QA_DIST), the output goes to
the S4 folder.

    QA_DIST=<snapshot of site/web/dist> STORY_JSON=<git show 65f95d32:data/story/story.json> python3 qa/reports/2026-11-07-site-track-qa-s3-s5/tools/ged17_18_story_s4.py

Reads (read only)
  data/story/story.json (or $STORY_JSON)                   the points and boxes (by eye), per pair and frame
  site/web/dist/story/living-room/<style>/index.html      the built pages' data blocks: verdict, dot, phone dot, crop
  qa/reports/2026-11-07-site-track-qa-s1-s2/data/hit-test-story.json   the dots as rendered (tools/hit-test-story.mjs)
  QA_BOX / IN_CROP_PART / ON_PRODUCT below: qa-agent's own reading at 100% / x2 / x3 (rounds 1-2 and, for mc1, today)
Writes
  data/ged17-18-story.json, overlays/<style>-<frame>-dots-boxes.jpg, overlays/<style>-<frame>-phone-390.jpg
"""
import json, os, re
from PIL import Image, ImageDraw, ImageFont

REPO = '/home/user/homedesign-app'
Q = f'{REPO}/qa/reports/2026-11-07-site-track-qa-s3-s5'
DIST = os.environ.get('QA_DIST', f'{REPO}/site/web/dist')
# the data file as built (the tree moves on while QA runs): STORY_JSON, e.g. `git show 0db47449:data/story/story.json`
story = json.load(open(os.environ.get('STORY_JSON', f'{REPO}/data/story/story.json')))
hit = json.load(open(f'{Q}/data/hit-test-story.json'))
PHONE_CSS, MIN_LONG, MIN_SHORT, COVER = 390, 44, 24, 1.5

QA_BOX = {  # [u0, u1, v0, v1] where qa-agent's reading differs from the data file's box
    ('nordic', 'A', 'pendant-cj-silk-ribbed-pumpkin-40'): [0.447, 0.555, 0.040, 0.137],
    ('nordic', 'A', 'sofa-cover-cj-cotton-muslin-fringe'): [0.6415, 0.875, 0.546, 0.794],
    ('nordic', 'B', 'sofa-cover-cj-cotton-muslin-fringe'): [0.717, 0.877, 0.569, 0.918],
    ('warm-modern', 'A', 'floor-lamp-cj-pleated-walnut-stem-158'): [0.885, 0.982, 0.19, 0.742],
    ('warm-modern', 'A', 'accent-sconces-aliexpress-travertine-cylinder-walnut-choice'): [0.7482, 0.7868, 0.230, 0.328],
    ('warm-modern', 'A', 'pendant-cj-tiered-fabric-drum'): [0.475, 0.595, 0.0, 0.145],
}
IN_CROP_PART = {  # frame px [x0, x1, y0, y1] of what the phone crop really carries, where the box overstates it
    ('nordic', 'B', 'sofa-cover-cj-cotton-muslin-fringe'): [1950, 2298, 870, 1405],
    ('warm-modern', 'A', 'sofa-cover-cj-cotton-muslin-fringe'): [911, 1003, 900, 1180],
}
SECOND_SCONCE = {('nordic', 'A'): [2077, 2118, 405, 490]}
NOTES = {
    ('modern-country', 'A', 'cushions-aliexpress-farmhouse-floral-pillow-covers-166217'): 'S1/S2: box right at 100% on mc1; mc1 -> fix4 changes 0 px in this box',
    ('modern-country', 'A', 'table-runner-cj-linen-look-sage-fringe'): 'the dot (1382, 1190) on the runner, ~20 px under the brass candlestick bases (generic)',
    ('modern-country', 'A', 'sill-vase-cj-cream-fluted-column-25'): 'outside the 4:5 crop (u 0.776-0.802 vs 0.295-0.745)',
}
WHOLE = {'planter-cj-seagrass-belly': 'not whole: the basket and the sofa arm cover it', 'rug-cj-braided-wool-natural': 'not whole: cut by the frame edges'}

out = {'thresholds': {'phone_css': PHONE_CSS, 'min_long_css': MIN_LONG, 'min_short_css': MIN_SHORT, 'coverage_min_pct': COVER}, 'pages': {}, 'coverage': {}}
try:
    FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    SMALL = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
except OSError:
    FONT = SMALL = ImageFont.load_default()
os.makedirs(f'{Q}/overlays', exist_ok=True)

for key, pair in story['pairs'].items():
    room, style = key.split('/')
    html = open(f'{DIST}/story/{room}/{style}/index.html', encoding='utf8').read()
    data = json.loads(re.search(r'<script type="application/json" id="st-data">\s*(.*?)\s*</script>', html, re.S).group(1))
    built_frames = {f['id']: f for f in data['frames']}
    page = {'frames_in_data': [f['id'] for f in pair['frames']], 'frames_on_page': list(built_frames), 'typographic': not built_frames, 'rows': []}
    for f in pair['frames']:
        if f['id'] not in built_frames:
            continue
        bf = built_frames[f['id']]
        assert f['qa_key'] == (re.search(r'/([^/]+)\.png', f['src']).group(1)), f['src']
        im = Image.open(f'{REPO}/{f["src"]}').convert('RGB')
        page.setdefault('frame_files', {})[f['id']] = f['src']
        W, H = im.size
        c0, c1 = round(bf['crop'][0] * W), round(bf['crop'][1] * W)
        css = PHONE_CSS / (c1 - c0)
        hp = {m['item']: m for m in hit['phone_390'][f'/story/{room}/{style}/#{f["id"]}']['marks']}
        hd = {m['item']: m for m in hit['desk_1280'][f'/story/{room}/{style}/#{f["id"]}']['marks']}
        ov = im.copy()
        d = ImageDraw.Draw(ov, 'RGBA')
        d.rectangle([0, 0, c0, H], fill=(0, 0, 0, 90))
        d.rectangle([c1, 0, W, H], fill=(0, 0, 0, 90))
        d.rectangle([c0, 0, c1, H], outline=(255, 0, 255, 255), width=5)
        ph = im.crop((c0, 0, c1, H)).resize((780, 975), Image.LANCZOS)
        dp = ImageDraw.Draw(ph, 'RGBA')
        for iid in bf['items']:
            it = data['items'][iid]
            p = it['product']
            k3 = (style, f['id'], p)
            box = QA_BOX.get(k3, it['box'])
            bx = IN_CROP_PART.get(k3) or [box[0] * W, box[1] * W, box[2] * H, box[3] * H]
            a, b = max(bx[0], c0), min(bx[1], c1)
            size = (round((b - a) * css, 1), round((bx[3] - bx[2]) * css, 1)) if b > a else None
            ok = bool(size) and max(size) >= MIN_LONG and min(size) >= MIN_SHORT
            area = round((box[1] - box[0]) * (box[3] - box[2]) * 100, 2)
            row = {'item': iid, 'frame': f['id'], 'product': p, 'verdict': it['faithful'], 'dot': it['dot'], 'box_data': it['box'], 'box_qa': box,
                   'phone_in_crop': size is not None, 'phone_visible_css': size, 'phone_size_ok': ok, 'phone_dot': it['phone'], 'phone_note': it['phone_note'],
                   'phone_390_hit_own': hp[iid]['hit_own_button'] if iid in hp else None, 'desk_1280_shown': iid in hd,
                   'desk_1280_hit_own': hd[iid]['hit_own_button'] if iid in hd else None, 'area_pct_bbox': area, 'note': NOTES.get(k3, '')}
            if k3[:2] in SECOND_SCONCE and p.startswith('accent-sconces'):
                s2 = SECOND_SCONCE[k3[:2]]
                row['second_of_pair_css'] = (round((s2[1] - s2[0]) * css, 1), round((s2[3] - s2[2]) * css, 1))
            if not it['dot']:
                row['G-ED.17'] = None
            elif it['phone']:
                row['G-ED.17'] = 'pass' if ok and row['phone_390_hit_own'] else 'FAIL'
            else:
                row['G-ED.17'] = 'no phone dot: ' + ('below 44x24' if size else 'outside the crop') + (' (page agrees)' if it['phone_note'] else ' (PAGE DISAGREES)')
            page['rows'].append(row)
            if it['dot']:
                coverage = out['coverage'].setdefault(style, {})
                coverage.setdefault(p, []).append({'frame': f['id'], 'area_pct_bbox': area})
            # overlay
            col = (0, 230, 0, 255) if it['dot'] else (170, 170, 170, 255)
            d.rectangle([it['box'][0] * W, it['box'][2] * H, it['box'][1] * W, it['box'][3] * H], outline=col, width=3)
            if box != it['box']:
                d.rectangle([box[0] * W, box[2] * H, box[1] * W, box[3] * H], outline=(255, 220, 0, 255), width=2)
            n = iid.split('-')[-1]
            d.text((it['box'][0] * W + 4, it['box'][2] * H + 2), n if it['dot'] else f'{n} ({it["faithful"][:6]}: no dot)', fill=col, font=FONT)
            if it['dot']:
                x, y = it['u'] * W, it['v'] * H
                rt = 23 * W / 1280
                d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=(255, 40, 40, 255), width=4)
                d.ellipse([x - rt, y - rt, x + rt, y + rt], outline=(255, 40, 40, 150), width=2)
                if it['phone']:
                    px, py = c0 + it['phone']['u'] * (c1 - c0), it['phone']['v'] * H
                    rp = 23 / css
                    d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=(0, 140, 255, 255))
                    d.ellipse([px - rp, py - rp, px + rp, py + rp], outline=(0, 140, 255, 200), width=3)
                    qx, qy = it['phone']['u'] * 780, it['phone']['v'] * 975
                    dp.ellipse([qx - 46, qy - 46, qx + 46, qy + 46], outline=(0, 140, 255, 255), width=3)
                    dp.ellipse([qx - 7, qy - 7, qx + 7, qy + 7], fill=(0, 140, 255, 255))
                    dp.text((qx + 50, qy - 12), n, fill=(255, 255, 255), font=FONT, stroke_width=2, stroke_fill=(0, 0, 0))
                elif size and not ok:
                    d.text((it['box'][0] * W, it['box'][3] * H + 6), f'G-ED.17: {size[0]:.0f}x{size[1]:.0f} CSS < 44x24', fill=(255, 140, 0), font=SMALL, stroke_width=2, stroke_fill=(0, 0, 0))
        d.rectangle([0, 0, 1080, 120], fill=(20, 20, 20, 200))
        for i, t in enumerate([f'{style} {f["id"]} ({f["qa_key"]}): G-ED.17 overlay, qa-agent 2026-11-07 (interface track S3-S5)',
                               'green: data-file box with a dot | grey: no dot | yellow: qa-agent box where it differs',
                               'red ring: desktop dot + 46 CSS target at 1280 | blue disc: phone dot + 46 CSS target at 390',
                               f'magenta: the phone 4:5 crop, u {bf["crop"][0]:.3f}-{bf["crop"][1]:.3f} (outside dimmed)']):
            d.text((10, 8 + i * 27), t, fill=(255, 255, 255), font=SMALL if i else FONT)
        ov.resize((W // 2, H // 2), Image.LANCZOS).save(f'{Q}/overlays/{style}-{f["id"]}-dots-boxes.jpg', quality=88)
        ph.save(f'{Q}/overlays/{style}-{f["id"]}-phone-390.jpg', quality=88)
    out['pages'][key] = page

for st, prods in out['coverage'].items():
    rows = {}
    for p, apps in prods.items():
        best = max(a['area_pct_bbox'] for a in apps)
        status = 'pass' if best >= COVER and p not in WHOLE else ('open: "whole" needs a ruling or a close-up' if best >= COVER else 'fail: needs a layer-2 close-up')
        rows[p] = {'frames': apps, 'best_pct_bbox': best, 'status': status, 'note': WHOLE.get(p, '')}
    out['coverage'][st] = {'products_with_dot': len(rows), 'pass': sum(r['status'] == 'pass' for r in rows.values()), 'rows': rows}
json.dump(out, open(f'{Q}/data/ged17-18-story.json', 'w'), ensure_ascii=False, indent=1)
for key, pg in out['pages'].items():
    print(key, 'typographic' if pg['typographic'] else '', [(r['item'], r['G-ED.17'], r['phone_visible_css']) for r in pg['rows'] if r['dot']])
print({st: (v['pass'], v['products_with_dot']) for st, v in out['coverage'].items()})
