"""qa-agent, 2026-11-07: G-ED.17 and G-ED.18 on the story prototype's hotspots, and the overlays.

    python3 -I qa/reports/2026-11-07-site-story-prototype-qa/tools/ged17_18.py

Inputs (read only)
  site/tools/test-page/story-hotspots.json          frontend-dev's points and boxes (by eye)
  site/.generated/test-page.story.json              the built page's items: dot, phone dot, crop (npm run test:story)
  qa/reports/2026-11-07-editorial-fin2-ed4-country.json   the fidelity verdicts (G-ED.5)
  qa/reports/2026-11-07-site-story-prototype-qa/data/hit-test-dots.json   the dots as rendered (tools/hit-test-dots.mjs)
  QA_BOX and ON_PRODUCT below: qa-agent's own reading of each product at 100% / x2 / x3 (scratch zooms, by eye)
Outputs
  data/ged17-18.json, overlays/*.jpg
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

REPO = '/home/user/homedesign-app'
Q = f'{REPO}/qa/reports/2026-11-07-site-story-prototype-qa'
hot = json.load(open(f'{REPO}/site/tools/test-page/story-hotspots.json'))
built = json.load(open(f'{REPO}/site/.generated/test-page.story.json'))
fid = json.load(open(f'{REPO}/qa/reports/2026-11-07-editorial-fin2-ed4-country.json'))
hit = json.load(open(f'{Q}/data/hit-test-dots.json'))

PHONE_CSS = 390
MIN_LONG, MIN_SHORT = 44, 24
COVER_MIN = 1.5  # % of the frame (G-ED.18; Bible 1.9 "כלל הכיסוי")

# qa-agent's boxes, [u0, u1, v0, v1] of the whole frame, where they differ from frontend-dev's box; everything else
# was read at 100% and agrees with frontend-dev's box within a few pixels
QA_BOX = {
    ('nordic-A', 'pendant-cj-silk-ribbed-pumpkin-40'): ([0.447, 0.555, 0.040, 0.137], 'the shade only (the cord is not the product to touch): y 62-209'),
    ('nordic-A', 'sofa-cover-cj-cotton-muslin-fringe'): ([0.6415, 0.875, 0.546, 0.794], 'the fringe reaches y ~1215 and the arm drape x ~2380: frontend-dev box cuts ~37 px of fringe'),
    ('nordic-B', 'sofa-cover-cj-cotton-muslin-fringe'): ([0.717, 0.877, 0.569, 0.918], 'agrees'),
    ('warm-modern-A', 'floor-lamp-cj-pleated-walnut-stem-158'): ([0.885, 0.982, 0.19, 0.742], 'the shade reaches x ~2671: frontend-dev box cuts ~45 px (~17%) of the shade on the right'),
}
# what the phone crop really carries of a product, where the box overstates it (frame px, [x0, x1, y0, y1])
IN_CROP_PART = {
    ('nordic-B', 'sofa-cover-cj-cotton-muslin-fringe'): ([1950, 2244, 870, 1405], 'the fold on the seat (x 1950-2125, y 1000-1075) and the drape over the arm up to the crop edge (x 2125-2244)'),
    ('warm-modern-A', 'sofa-cover-cj-cotton-muslin-fringe'): ([911, 1003, 900, 1180], 'only the right edge of the drape is in the crop'),
}
# the second sconce of the pair (Nordic A): the point is on the left one; the right one, measured for the phone
SECOND_SCONCE = [2077, 2118, 405, 490]
# where the dot sits, read at 100% / x2 / x3 on the frame (desktop = the point; phone = the built phone dot)
ON_PRODUCT = {
    ('nordic-A', 'sofa-cover-cj-cotton-muslin-fringe'): ('yes, near the top edge of the throw (19 px below it, the charcoal cushion just above)', 'yes, same point'),
    ('nordic-B', 'sofa-cover-cj-cotton-muslin-fringe'): ('yes, on the drape over the arm', 'EDGE: on the lower edge of the fold, where it meets the boucle seat (x 2101, y 1071); move to the middle of the fold (u 0.765, v 0.677) or onto the drape'),
    ('nordic-B', 'rug-cj-braided-wool-natural'): ('yes (on desktop the cover crop hides it)', 'yes'),
    ('warm-modern-A', 'sofa-cover-cj-cotton-muslin-fringe'): ('yes', 'yes, ~20 px inside the right edge of the drape'),
    ('warm-modern-A', 'accent-sconces-aliexpress-travertine-cylinder-walnut-choice'): ('yes, on the travertine cylinder', 'yes, on the walnut plate right of the cylinder'),
    ('warm-modern-A', 'cushions-cj-boucle-teddy'): ('yes', 'yes'),
}
# the designer's proposed phone crop centres (docs/proposals/story-page-design-notes-2026-11-07.md §3), checked too
PROPOSED_CROP_U = {'nordic-A': 0.60, 'nordic-B': 0.62, 'warm-modern-A': 0.56}


def verdict_of(qa_key, product):
    for r in fid['frames'][qa_key]['rows']:
        if r['card'].split(' ')[0] == product:
            return r['faithful']
    return 'not in table'


def crop_of(W, H, u):
    cw = round(H * 0.8)
    cl = round(min(W - cw, max(0, u * W - cw / 2)))
    return cl, cl + cw


def phone_dot(box, u, v, c0, c1):
    """the page's own rule (tools/make-story-page.ts phoneDot), in frame units"""
    a, b = max(box[0], c0), min(box[1], c1)
    if b <= a:
        return None
    m = 23 / PHONE_CSS
    cu = (u - c0) / (c1 - c0)
    uu = cu if m <= cu <= 1 - m else ((a + b) / 2 - c0) / (c1 - c0)
    uu = min(1 - m, max(m, uu))
    return c0 + uu * (c1 - c0), v


def phone_size(box_px, crop_px):
    x0, x1, y0, y1 = box_px
    a, b = max(x0, crop_px[0]), min(x1, crop_px[1])
    if b <= a:
        return None
    css = PHONE_CSS / (crop_px[1] - crop_px[0])
    return round((b - a) * css, 1), round((y1 - y0) * css, 1)


def size_ok(s):
    return s is not None and max(s) >= MIN_LONG and min(s) >= MIN_SHORT


out = {'thresholds': {'phone_css': PHONE_CSS, 'min_long_css': MIN_LONG, 'min_short_css': MIN_SHORT, 'coverage_min_pct': COVER_MIN,
                      'note': 'frames are 2720x1530 (not 2736x1536): the 4:5 crop is 1224 px, 0.3186 CSS per frame px; 44 CSS = 138 px, 24 CSS = 75 px'},
       'frames': {}, 'coverage': {}}
coverage = {}
for fr, f in hot['frames'].items():
    src = f'{REPO}/{f["src"]}'
    im = Image.open(src).convert('RGB')
    W, H = im.size
    bf = next(x for x in built['frames'] if x['id'] == fr)
    c0, c1 = bf['crop']
    crop_px = (round(c0 * W), round(c1 * W))
    pc0, pc1 = crop_of(W, H, PROPOSED_CROP_U[fr])
    rows = []
    for iid in bf['items']:
        it = built['items'][iid]
        p = it['product']
        key = (fr, p)
        fe_box = it['box']
        qa_box, qa_note = QA_BOX.get(key, (fe_box, 'agrees with frontend-dev at 100%'))
        bx = [qa_box[0] * W, qa_box[1] * W, qa_box[2] * H, qa_box[3] * H]
        fe_px = [fe_box[0] * W, fe_box[1] * W, fe_box[2] * H, fe_box[3] * H]
        inter = max(0, min(bx[1], fe_px[1]) - max(bx[0], fe_px[0])) * max(0, min(bx[3], fe_px[3]) - max(bx[2], fe_px[2]))
        qa_area = (bx[1] - bx[0]) * (bx[3] - bx[2])
        covers = round(inter / qa_area, 3)
        v = verdict_of(f['qa_key'], p)
        part_px = IN_CROP_PART.get(key, (bx, None))[0]
        s_now = phone_size(part_px, crop_px)
        s_prop = phone_size(bx if key not in IN_CROP_PART else [part_px[0], bx[1], part_px[2], part_px[3]], (pc0, pc1))
        if p.startswith('accent-sconces-cj-travertine-block'):
            s_second = phone_size(SECOND_SCONCE, crop_px)
        else:
            s_second = None
        pd_prop = phone_dot(fe_box, it['u'], it['v'], pc0 / W, pc1 / W) if v == 'yes' else None  # what the page would do
        area_pct = round(qa_area / (W * H) * 100, 2)
        on_desk, on_phone = ON_PRODUCT.get(key, ('yes', 'yes' if it['phone'] else None))
        h390 = hit['phone_390'][fr]['marks']
        hd = [m for m in hit['desk_1280'][fr]['marks'] if m['item'] == iid]
        hd14 = [m for m in hit['desk_1440'][fr]['marks'] if m['item'] == iid]
        hp = [m for m in h390 if m['item'] == iid]
        row = {
            'item': iid,
            'product': p,
            'fidelity': v,
            'dot_on_page': it['dot'],
            'only_yes_rule': (it['dot'] == (v == 'yes')),
            'point_uv': [it['u'], it['v']],
            'box_frontend': fe_box,
            'box_qa': qa_box,
            'box_note': qa_note,
            'frontend_box_covers_qa_box': covers,
            'desktop_dot_on_product': on_desk if it['dot'] else None,
            'desktop_1280': ({'shown': True, 'hit_own_button': hd[0]['hit_own_button'], 'under_top_band': hd[0]['under_top_band'], 'hit': hd[0]['hit']} if hd else {'shown': False}) if it['dot'] else None,
            'desktop_1440': ({'shown': True, 'hit_own_button': hd14[0]['hit_own_button'], 'under_top_band': hd14[0]['under_top_band'], 'hit': hd14[0]['hit']} if hd14 else {'shown': False}) if it['dot'] else None,
            'phone': None,
        }
        if v == 'yes':
            in_crop = s_now is not None
            row['phone'] = {
                'crop_u': [round(c0, 4), round(c1, 4)],
                'in_crop': in_crop,
                'visible_part_css': s_now,
                'visible_part_note': IN_CROP_PART.get(key, (None, None))[1],
                'size_ok': size_ok(s_now),
                'second_of_pair_css': s_second,
                'sharp': True,
                'dot_built': it['phone'],
                'dot_on_product': on_phone,
                'hit_own_button_390': hp[0]['hit_own_button'] if hp else None,
                'G-ED.17': ('pass' if in_crop and size_ok(s_now) and (on_phone or '').startswith('yes') else
                            'pass, dot on the edge' if in_crop and size_ok(s_now) else
                            'no dot: below 44x24' if in_crop else 'no dot: outside the 4:5 crop'),
                'with_proposed_crop': {'crop_u': [round(pc0 / W, 4), round(pc1 / W, 4)], 'visible_part_css': s_prop, 'size_ok': size_ok(s_prop),
                                       'phone_dot_uv': [round(pd_prop[0], 4), round(pd_prop[1], 4)] if pd_prop else None},
            }
        rows.append(row)
        if v == 'yes':
            st = 'nordic' if fr.startswith('nordic') else 'warm-modern'
            coverage.setdefault(st, {}).setdefault(p, []).append({'frame': fr, 'area_pct_bbox': area_pct, 'sharp': True})
    # pairwise phone distances (built dots, CSS) and desktop (rendered)
    out['frames'][fr] = {'src': f['src'], 'size': [W, H], 'crop_px': crop_px, 'proposed_crop_px': [pc0, pc1], 'rows': rows,
                         'phone_390_min_pair_css': min((((a['cx'] - b['cx']) ** 2 + (a['cy'] - b['cy']) ** 2) ** 0.5
                                                         for i, a in enumerate(hit['phone_390'][fr]['marks']) for b in hit['phone_390'][fr]['marks'][i + 1:]), default=None),
                         'desk_1280_min_pair_css': min((((a['cx'] - b['cx']) ** 2 + (a['cy'] - b['cy']) ** 2) ** 0.5
                                                         for i, a in enumerate(hit['desk_1280'][fr]['marks']) for b in hit['desk_1280'][fr]['marks'][i + 1:]), default=None)}

# G-ED.18: per style, every product with a dot at least once whole, sharp and >= 1.5% of the frame (bbox: an upper bound)
WHOLE_NOTE = {
    'planter-cj-seagrass-belly': 'not whole: the jute basket covers its left side and the sofa arm its right',
    'rug-cj-braided-wool-natural': 'not whole: cut by the frame edges (as any rug in a wide frame)',
}
for st, prods in coverage.items():
    res = {}
    for p, apps in prods.items():
        best = max(apps, key=lambda a: a['area_pct_bbox'])
        ok = best['area_pct_bbox'] >= COVER_MIN
        status = ('pass' if ok and p not in WHOLE_NOTE else
                  'open: size and sharpness pass, "whole" needs a master-designer ruling or a close-up' if ok else
                  'fail: below 1.5% in every frame of the set, needs a layer-2 close-up')
        res[p] = {'appearances': apps, 'best_pct_bbox': best['area_pct_bbox'], 'status': status, 'pass': status == 'pass',
                  'note': WHOLE_NOTE.get(p, '')}
    out['coverage'][st] = {'products_with_dot': len(res), 'pass': sum(1 for r in res.values() if r['pass']), 'rows': res}

os.makedirs(f'{Q}/data', exist_ok=True)
json.dump(out, open(f'{Q}/data/ged17-18.json', 'w'), ensure_ascii=False, indent=1)

# ---------------- overlays ----------------
try:
    FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    SMALL = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
except OSError:
    FONT = SMALL = ImageFont.load_default()
os.makedirs(f'{Q}/overlays', exist_ok=True)
css_px = lambda crop: (crop[1] - crop[0]) / PHONE_CSS  # frame px per CSS on the phone
for fr, F in out['frames'].items():
    im = Image.open(f'{REPO}/{F["src"]}').convert('RGB')
    W, H = im.size
    ov = im.copy()
    d = ImageDraw.Draw(ov, 'RGBA')
    c0, c1 = F['crop_px']
    # outside the phone crop: dimmed
    d.rectangle([0, 0, c0, H], fill=(0, 0, 0, 90))
    d.rectangle([c1, 0, W, H], fill=(0, 0, 0, 90))
    d.rectangle([c0, 0, c1, H], outline=(255, 0, 255, 255), width=5)
    d.text((c0 + 10, H - 40), f'phone 4:5 crop u {c0 / W:.3f}-{c1 / W:.3f} (built)', fill=(255, 0, 255), font=FONT)
    p0, p1 = F['proposed_crop_px']
    if (p0, p1) != (c0, c1):
        for y in range(0, H, 40):
            d.line([(p0, y), (p0, y + 20)], fill=(255, 160, 255, 255), width=3)
            d.line([(p1, y), (p1, y + 20)], fill=(255, 160, 255, 255), width=3)
        d.text((p0 + 10, H - 70), f'designer proposal u {p0 / W:.3f}-{p1 / W:.3f}', fill=(255, 160, 255), font=SMALL)
    k = css_px((c0, c1))
    for r in F['rows']:
        fe = r['box_frontend']
        box = [fe[0] * W, fe[2] * H, fe[1] * W, fe[3] * H]
        yes = r['fidelity'] == 'yes'
        col = (0, 230, 0, 255) if yes else (170, 170, 170, 255)
        d.rectangle(box, outline=col, width=3)
        if r['box_qa'] != fe:
            q = r['box_qa']
            d.rectangle([q[0] * W, q[2] * H, q[1] * W, q[3] * H], outline=(255, 220, 0, 255), width=2)
        n = r['item'].split('-')[-1]
        tag = n if yes else f'{n} (partly: no dot)'
        if r['phone'] and r['phone']['G-ED.17'].startswith('no dot: below'):
            tag += f'  FAIL 17: {r["phone"]["visible_part_css"][0]:.0f}x{r["phone"]["visible_part_css"][1]:.0f} CSS'
        d.text((box[0] + 4, box[1] + 2), n if yes else tag, fill=col if yes else (230, 230, 230, 255), font=FONT)
        notes = []
        if r['phone'] and r['phone']['G-ED.17'].startswith('no dot: below'):
            notes.append(f'G-ED.17 FAIL: {r["phone"]["visible_part_css"][0]:.0f}x{r["phone"]["visible_part_css"][1]:.0f} CSS < 44x24')
            if r['phone'].get('second_of_pair_css'):
                sc2 = r['phone']['second_of_pair_css']
                d.rectangle([SECOND_SCONCE[0], SECOND_SCONCE[2], SECOND_SCONCE[1], SECOND_SCONCE[3]], outline=(255, 60, 60, 255), width=3)
                d.text((SECOND_SCONCE[0] - 40, SECOND_SCONCE[3] + 6), f'2nd sconce {sc2[0]:.0f}x{sc2[1]:.0f} CSS', fill=(255, 60, 60), font=SMALL, stroke_width=2, stroke_fill=(0, 0, 0))
        if r['desktop_1280'] and r['desktop_1280'].get('under_top_band'):
            notes.append('desktop 1280/1440: dot under the top band' if r['desktop_1280'].get('hit') else 'desktop 1280: target top under the band')
        if r['phone'] and r['phone']['G-ED.17'] == 'pass, dot on the edge':
            notes.append('phone dot on the edge of the fold')
        for j, t in enumerate(notes):
            d.text((box[0], box[3] + 6 + j * 24), t, fill=(255, 140, 0), font=SMALL, stroke_width=2, stroke_fill=(0, 0, 0))
        if not yes:
            continue
        # desktop dot: red; its 46 CSS target at a 1280 display of the full frame width
        x, y = r['point_uv'][0] * W, r['point_uv'][1] * H
        rt = 23 * W / 1280
        dc = (255, 40, 40, 255)
        if r['desktop_1280'] and r['desktop_1280'].get('under_top_band'):
            dc = (255, 140, 0, 255)
        d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=dc, width=4)
        d.ellipse([x - rt, y - rt, x + rt, y + rt], outline=dc[:3] + (150,), width=2)
        # phone dot: blue, its 46 CSS target at 390 CSS
        if r['phone'] and r['phone']['dot_built']:
            px = c0 + r['phone']['dot_built']['u'] * (c1 - c0)
            py = r['phone']['dot_built']['v'] * H
            rp = 23 * k
            pcol = (0, 140, 255, 255) if r['phone']['G-ED.17'] == 'pass' else (255, 140, 0, 255)
            d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=pcol)
            d.ellipse([px - rp, py - rp, px + rp, py + rp], outline=pcol[:3] + (200,), width=3)
    # legend
    lx = W - 1030 if fr == 'nordic-B' else 0
    d.rectangle([lx, 0, lx + 1020, 150], fill=(20, 20, 20, 200))
    lines = [f'{fr}: G-ED.17 / G-ED.18 overlay (qa-agent 2026-11-07)',
             'green box: frontend-dev touch box ("yes", dot) | grey: "partly", no dot | yellow: qa-agent box where it differs',
             'red ring: desktop dot + 46 CSS target at 1280 | orange: dot under the desktop top band',
             'blue disc: phone dot + 46 CSS target at 390 | orange disc: phone dot on the product edge',
             'magenta: phone 4:5 crop as built (outside dimmed) | dashed pink: designer proposal']
    for i, t in enumerate(lines):
        d.text((lx + 10, 8 + i * 28), t, fill=(255, 255, 255), font=SMALL if i else FONT)
    ov.resize((W // 2, H // 2), Image.LANCZOS).save(f'{Q}/overlays/{fr}-dots-boxes.jpg', quality=88)
    # the phone view: the 4:5 crop at 2x of 390 CSS, the phone dots and their 46 CSS targets
    ph = im.crop((c0, 0, c1, H)).resize((780, 975), Image.LANCZOS)
    dp = ImageDraw.Draw(ph, 'RGBA')
    sc = 780 / (c1 - c0)
    for r in F['rows']:
        if not (r['phone'] and r['phone']['dot_built']):
            continue
        px = r['phone']['dot_built']['u'] * 780
        py = r['phone']['dot_built']['v'] * 975
        pcol = (0, 140, 255, 255) if r['phone']['G-ED.17'] == 'pass' else (255, 140, 0, 255)
        dp.ellipse([px - 46, py - 46, px + 46, py + 46], outline=pcol, width=3)
        dp.ellipse([px - 7, py - 7, px + 7, py + 7], fill=pcol)
        dp.text((px + 50, py - 12), r['item'].split('-')[-1], fill=(255, 255, 255), font=FONT, stroke_width=2, stroke_fill=(0, 0, 0))
    ph.save(f'{Q}/overlays/{fr}-phone-390.jpg', quality=88)
print(json.dumps({fr: {r['item']: (r['phone'] or {}).get('G-ED.17') for r in F['rows']} for fr, F in out['frames'].items()}, indent=1))
print(json.dumps({st: {p: (c['best_pct_bbox'], c['status']) for p, c in v['rows'].items()} for st, v in out['coverage'].items()}, indent=1, ensure_ascii=False))
