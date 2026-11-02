#!/usr/bin/env python3
"""Pose prompts for route R (render-agent, 2026-11-02), by the rule of docs/transitions-plan-2026-11-02.md section 3 ("the prompt of
a pose"): the room's v7 prompt as it is (the same lock paragraph, light and materials), with three changes:
  (1) the PHOTO line replaced by the plan's sentence ("A frame from a camera move through the same house: ..."),
  (2) only the product lines whose placeholder shows in the pose clay (round-4 selfcheck boxes, >= MIN_PX pixels), each re-boxed to
      its x / y in the pose canvas (the master's boxes do not hold in another view),
  (3) the master(s) attached as reference 1 (and 2, 3 for the rooms seen through a door), then the product references of the lines kept.
Frame-specific coordinates outside the product lines (the M0 sofa arms) are replaced by "exactly the clay's block". Vista lines name
the reference of the neighbouring room. Writes assets/prompts/poses-v7.nordic/<pose>.txt (with a # header) and poses.json here.
  python3 -I gen_poses.py
"""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
PR = os.path.join(REPO, 'assets', 'prompts', 'recipe-v5.nordic')
OUTP = os.path.join(REPO, 'assets', 'prompts', 'poses-v7.nordic')
SC = json.load(open(os.path.join(REPO, 'assets', 'blockout', 'house', 'framing', 'round4', 'selfcheck.json')))['frames']
IDX = json.load(open(os.path.join(HERE, 'refs', 'index-v7.json')))
MIN_PX = 4000            # placeholder pixels in the 4072 / 3840 clay for a line to stay (about 0.05 % of the frame)

# base prompt: line letter -> (slot key, index of its product reference in refs/index-v7.json frames[base], 1-based or None)
LINES = {
    'M0': {'a': ('living/framed-art', 2), 'b': ('living/accent-sconces', 5), 'c': ('living/pendant', 6), 'd': ('living/curtains', None),
           'e': ('living/vase', 11), 'f': ('living/wall-sconce', 3), 'g': ('living/basket', 7), 'h': ('living/rug', 4),
           'i': ('living/cushions', 13), 'j': ('living/cushions', 14), 'k': ('living/cushions', None), 'l': ('living/sofa-cover', 8),
           'm': ('living/table-runner', 12), 'n': ('living/candle-holders', 9), 'o': ('living/bowl', 10)},
    'D1': {'a': ('kitchen-dining/dining-pendant', 1), 'b': ('kitchen-dining/table-runner', 2), 'c': ('kitchen-dining/centerpiece-vase', 3),
           'd': ('kitchen-dining/candle-holders', 4), 'e': ('kitchen-dining/curtains', 5), 'f': ('kitchen-dining/bench-pad', 6),
           'g': ('kitchen-dining/dining-rug', 12), 'h': ('kitchen-dining/framed-art', 7), 'i': ('kitchen-dining/condiment-set', 8),
           'j': ('kitchen-dining/bowl', 9), 'k': ('kitchen-dining/tableware-set', 10), 'l': ('kitchen-dining/mug-set', 11),
           'm': ('kitchen-dining/kitchen-runner', 13)},
    'H0': {'a': ('hall/framed-art', 2), 'b': ('hall/console-vessel', 3), 'c': ('hall/key-tray', 4), 'd': ('hall/wall-hooks', 5),
           'e': ('hall/wall-sconce', 6), 'f': ('hall/bench-cushion', 7), 'g': ('hall/bench-throw', 8), 'h': ('hall/basket', 9), 'i': ('VISTA', None)},
    'C0': {'a': ('corridor/gallery-art', 3), 'b': ('corridor/ceiling-lights', 4), 'c': ('VISTA', None)},
    'MB0': {'a': ('master/framed-art', 1), 'b': ('master/bedside-sconces', 2), 'c': ('master/curtains', 3), 'd': ('master/sill-vase', 4),
            'e': ('master/planter', 5), 'f': ('master/nightstand-vase', 6), 'g': ('master/trinket-dish', 7), 'h': ('master/candle-holders', 8),
            'i': ('master/pillowcases', 9), 'j': ('master/bedding', 10), 'k': ('master/cushions', 11), 'l': ('master/throw', 12)},
    'K-boy': {'a': ('boy/bookshelf', 1), 'b': ('boy/rug', 8), 'c': ('boy/bedding', 2), 'd': ('boy/bedspread', 3), 'e': ('boy/cushions', 4),
              'f': ('boy/soft-toy', 5), 'g': ('boy/toy-basket', 6), 'h': ('boy/toy-cars', 7)},
    'K-girl': {'a': ('girl/framed-prints', 1), 'b': ('girl/bookshelf', 2), 'c': ('girl/rug', 9), 'd': ('girl/bedding', 3), 'e': ('girl/bedspread', 4),
               'f': ('girl/cushions', 5), 'g': ('girl/soft-toy', 6), 'h': ('girl/toy-basket', 8), 'i': ('girl/doll', 7)},
    'B1': {'a': ('bath/shower-curtain', 1), 'b': ('bath/wall-sconce', 2), 'c': ('bath/bath-mat', 3), 'd': ('bath/toilet-paper-stand', 4),
           'e': ('bath/reed-diffuser', 5), 'f': ('bath/candle', 6), 'g': ('bath/shower-dispensers', 7)},
    'W0': {'a': ('work/curtains', 1), 'b': ('work/rug', 7), 'c': ('work/basket', 2), 'd': ('work/waste-basket', 3), 'e': ('work/planter', 4),
           'f': ('work/shelf-boxes', 5), 'g': ('work/desk-organizer', 6)},
}
PFILE = {'M0': 'm0-v7.txt', 'D1': 'd1-v7.txt', 'H0': 'h0-v7.txt', 'C0': 'c0-v7.txt', 'MB0': 'mb0-v7.txt', 'K-boy': 'k-boy-v7.txt',
         'K-girl': 'k-girl-v7.txt', 'B1': 'b1-v7.txt', 'W0': 'w0-v7.txt'}
HEIGHT = {'M0': '1.2', 'D1': '1.1', 'H0': '1.2', 'C0': '1.2', 'MB0': '1.2', 'K-boy': '1.0', 'K-girl': '1.0', 'B1': '1.15', 'W0': '1.1'}
# pose -> base prompt, master references (frame keys of the accepted v7 graded files, in order), vista line
POSES = {
    'H0x': ('H0', ['H0mid', 'M0crop'], 'i'),          # masters as crops from 22:40 on: whole-frame masters pulled W0-in / K-girl-0 / M0p to the master framing
    'H0e': ('H0', ['H0mid', 'M0crop'], 'i'),
    'M0p': ('M0', ['M0', 'D1'], 'THROUGH THE OPENING on the right, if the clay shows it: exactly the dining room and kitchen of reference 2.'),
    'M0x': ('M0', ['M0', 'D1'], 'THROUGH THE OPENING: exactly the dining room and kitchen of reference 2, the oak table under the flat silk lantern, the bench, the white kitchen run; the frame between the two rooms in oiled oak.'),
    'PD-35': ('D1', ['D1'], None),
    'W0-in': ('W0', ['W0'], None),
    'S1prime': ('C0', ['C0vista', 'H0crop', 'M0crop'], 'c'),
    'K-boy-0': ('K-boy', ['K-boy'], None),
    'K-girl-0': ('K-girl', ['K-girl'], None),
    'CB-0': ('B1', ['B1'], None),
    'MB-in': ('MB0', ['MB0right', 'C0vista'], 'THROUGH THE DOOR: exactly the corridor of reference 2, the gallery of three prints on its left wall, the paper lanterns, the glowing hall and living room at its end; the opening on the right a soft lit pass in the wall colour, nothing in it.'),
}
PAIRS = {'living/accent-sconces', 'master/bedside-sconces', 'bath/vanity-sconces'}
COORD_HEAD = re.compile(r',?\s*(?:at |plate )?\b[xy] \d\.\d+(?:(?:-| and )\d\.\d+)*')


def body(fname):
    txt = open(os.path.join(PR, fname), encoding='utf-8').read()
    b = [l for l in txt.split('\n') if not l.startswith('#')]
    while b and not b[0].strip():
        b.pop(0)
    while b and not b[-1].strip():
        b.pop()
    return b


def box_of(sc, key):
    b = sc.get('boxes', {}).get(key)
    if not b or b['px'] < MIN_PX:
        return None
    return b['box']


WHOLE = ('M0', 'D1', 'B1', 'K-boy', 'K-girl', 'W0', 'MB0', 'C0', 'H0', 'D2', 'B2')


def build(pose):
    base, masters, vista = POSES[pose]
    sc = SC[pose]
    lines = body(PFILE[base])
    out, refs, kept, dropped, used = [], [], [], [], set()
    master_n = len(masters)
    for l in lines:
        if l.startswith('1. PHOTO.'):
            if any(k not in WHOLE for k in masters):   # crops of the masters (from 22:40): they carry the look, not a framing to copy
                rest = f"; the neighbouring room{'s' if master_n > 2 else ''} as reference{'s' if master_n > 2 else ''} {', '.join(str(i) for i in range(2, master_n + 1))}" if master_n > 1 else ''
                out.append(f"1. PHOTO. A frame from a camera move through the same house: the same room, products, light and grade as the attached crops of the master photographs (reference 1{rest}). They are cut from photographs taken from other cameras and show the look only; the clay alone sets the framing, the position and the size of everything; render only what this clay shows. 24 mm shift lens at {HEIGHT[base]} m, level, straight verticals, all sharp.")
            elif master_n == 1:
                out.append(f"1. PHOTO. A frame from a camera move through the same house: the same room, products, light and grade as the attached master photograph (reference 1), which is taken from another camera; the clay alone sets the framing, the position and the size of everything; render only what this clay shows. 24 mm shift lens at {HEIGHT[base]} m, level, straight verticals, all sharp.")
            else:
                out.append(f"1. PHOTO. A frame from a camera move through the same house: the same room, products, light and grade as the attached master photographs (reference 1; the neighbouring room{'s' if master_n > 2 else ''} as reference{'s' if master_n > 2 else ''} {', '.join(str(i) for i in range(2, master_n + 1))}), taken from other cameras; the clay alone sets the framing, the position and the size of everything; render only what this clay shows. 24 mm shift lens at {HEIGHT[base]} m, level, straight verticals, all sharp.")
            continue
        m = re.match(r'^([a-o])\. (.*)$', l)
        if m and m.group(1) in LINES[base]:
            key, ref = LINES[base][m.group(1)]
            if key == 'VISTA':
                if vista == m.group(1):
                    t = l
                    # renumber the vista references: they now follow the master
                    t = t.replace('references 1 and 2', 'references 2 and 3').replace('of reference 1', 'of reference 2')
                    out.append(t)
                    kept.append(m.group(1) + ' (vista)')
                continue
            bb = box_of(sc, key)
            if bb is None:
                dropped.append(m.group(1))
                continue
            head, sep, tail = m.group(2).partition(':')
            head = COORD_HEAD.sub('', head).strip().rstrip(',')
            tail = re.sub(r'\bx \d\.\d+(?:-\d\.\d+)?,?\s*', '', tail) if re.search(r'\bx \d\.\d+', tail) else tail
            if key in used:                                  # a set split over several lines (cushions): the box once
                out.append(f"{m.group(1)}. {head}:{tail}")
            elif key in PAIRS:                               # a pair: one at each end of the group box
                out.append(f"{m.group(1)}. {head}, the pair at the two ends of x {bb[0]:.2f}-{bb[1]:.2f}, y {bb[2]:.2f}-{bb[3]:.2f}:{tail}")
            elif sum(1 for v in LINES[base].values() if v[0] == key) > 1:
                out.append(f"{m.group(1)}. {head}, the set of the next lines within x {bb[0]:.2f}-{bb[1]:.2f}, y {bb[2]:.2f}-{bb[3]:.2f}:{tail}")
            else:
                out.append(f"{m.group(1)}. {head}, x {bb[0]:.2f}-{bb[1]:.2f}, y {bb[2]:.2f}-{bb[3]:.2f}:{tail}")
            used.add(key)
            kept.append(m.group(1))
            if ref and ref not in refs:
                refs.append(ref)
            continue
        if l.startswith('5. NOT IN FRAME') and vista and len(vista) > 2:
            while out and not out[-1].strip():
                out.pop()
            last = max([k[0] for k in kept] or ['`'])
            out.append(f"{chr(ord(last) + 1)}. {vista}")
            out.append('')
        l = l.replace("exactly the clay's block, arms at x 0.52 and 0.84, as reference 1, never wider", "exactly the clay's block, never wider")
        out.append(l)
    text = '\n'.join(out)
    if pose == 'MB-in':   # one wall lamp, the planter and the nightstand seen from the door; the window and the bed are out of view
        text = re.sub(r'^2\. LIGHT\..*$', '2. LIGHT. Soft north daylight from the bedroom window, out of frame to the left, no sun. Exposed for white: the panelled wall clean white; the corridor through the door bright and still detailed, its roof slot glowing. The bedroom wall falls off half a stop to the right; fine shadow lines in the panelling grooves; the planter lit on its left face, darker on its right. Dense contact shadows under the nightstand and the planter. Ceiling a touch darker. Real contrast, never milky. 4600 K: whites white, never cream, pink or grey. Lamps 2700 K, low, shadowless: the wall lamp glows through its fabric and lays a small warm pool on the nightstand top and a soft fan on the panelling.', text, flags=re.M)
        text = text.replace('b. WALL LAMPS, just above the panelling cap, the pair at the two ends of x 0.08-0.13, y 0.37-0.45: two flush beige linen-look wave lamps, each half a nightstand\'s width, hardwired.',
                            'b. WALL LAMP, just above the panelling cap, x 0.08-0.13, y 0.37-0.45: one flush beige linen-look wave lamp, half the nightstand\'s width, hardwired (its pair is out of frame).')
        text = text.replace('e. PLANTER, cut by the right edge, x 0.19-0.36', 'e. PLANTER, standing free in front of the panelling, x 0.19-0.36')
        text = text.replace('h. CANDLE HOLDERS, right nightstand, x 0.08-0.13', 'h. CANDLE HOLDERS, on the nightstand, x 0.08-0.13')
        text = text.replace('rug, basket, ceiling lamp, socket,', 'rug, basket, bedroom ceiling lamp, window, socket,')
    if base == 'C0' and 'b' in dropped:   # the lanterns are out of this view: no lamp sentence, and the hall bench in the vista stays
        text = text.replace(' Lamps 2700 K, low, shadowless: the paper lanterns glow evenly; the far one lays a faint warm pool on the floor below it.', ' The corridor paper lanterns are above the frame, out of view.')
        text = text.replace('5. NOT IN FRAME: picture lights, runner or rug, stool, bench, plants,', '5. NOT IN FRAME: corridor lamps, picture lights, runner or rug, stool, plants,')
    if base == 'H0' and 'e' in dropped:   # the cube lamp is out of this view: no lamp sentence, or the model invents one
        text = text.replace(' One lamp, 2700 K, shadowless: the fabric cube glows evenly and fans soft warm light on the wall around it.', '')
    text = re.sub(r'\n{3,}', '\n\n', text)
    # references: masters first, then product references of the kept lines (<= 15 in all)
    fr_refs = []
    for mk in masters:
        fr_refs.append(('master', mk))
    prod = [('product', base, r) for r in refs][: 15 - len(fr_refs)]
    return text, fr_refs, prod, kept, dropped


def main():
    res = {}
    for pose in POSES:
        if pose not in SC or 'boxes' not in SC[pose]:
            print('skip', pose, '(no round-4 clay yet)')
            continue
        text, fr_refs, prod, kept, dropped = build(pose)
        base = POSES[pose][0]
        hdr = [f"# {pose}: transition pose, route R (docs/transitions-plan-2026-11-02.md section 3). render-agent, 2026-11-02, generated by assets/renders/house-nordic-v7-2026-11-02/gen_poses.py from {PFILE[base]}. Strip every # line before sending.",
               f"# Clay: assets/blockout/house/framing/round4/poses/{pose}.png (round 4; camera {SC[pose]['camera']['loc']}, yaw {SC[pose]['camera']['yaw']}, u0/v0 {SC[pose]['camera']['u0']}/{SC[pose]['camera']['v0']}; overscan {SC[pose].get('overscan', {}).get('on')}). Positions are fractions of that canvas.",
               f"# Product lines kept (placeholder in the pose clay): {', '.join(kept)}; dropped (not in this view): {', '.join(dropped) or 'none'}.",
               "# References after the clay: " + ' | '.join([f"{i + 1} = {k} v7 (graded)" if k in ('M0', 'D1', 'B1', 'K-boy', 'K-girl', 'W0', 'MB0', 'C0', 'H0') else f"{i + 1} = {k[:2] if k[1] != 'B' else 'MB0'} v7 crop ({k})" for i, (_, k) in enumerate(fr_refs)] +
                                                       [f"{len(fr_refs) + i + 1} = {base} ref {r}: {IDX['frames'][base][r - 1]['note'][:40]}" for i, (_, _, r) in enumerate(prod)])]
        open(os.path.join(OUTP, f'{pose}.txt'), 'w').write('\n'.join(hdr) + '\n' + text + '\n')
        frr = IDX.get('frame_refs', {})
        murls = [frr.get(k, {}).get('var2_url') for _, k in fr_refs]
        purls = [IDX['frames'][base][r - 1]['var2_url'] for _, _, r in prod]
        res[pose] = dict(base=base, prompt_file=f'assets/prompts/poses-v7.nordic/{pose}.txt', chars=len(text), masters=[k for _, k in fr_refs],
                         master_urls=murls, product_refs=purls, kept=kept, dropped=dropped, ready=all(murls))
        print(pose, len(text), 'chars | kept', kept, '| dropped', dropped, '| refs', len(fr_refs) + len(prod), '| masters ready', all(murls))
        # the pose job in jobs.json (created or refreshed while pending)
        J = json.load(open(os.path.join(HERE, 'jobs.json')))
        rooms = {'M0': 'living-room', 'D1': 'kitchen-dining', 'H0': 'hall', 'C0': 'corridor', 'MB0': 'master', 'K-boy': 'boy', 'K-girl': 'girl', 'B1': 'bath', 'W0': 'work'}
        jid = 'pose-' + pose.lower().replace("'", '') + '-v7'
        job = next((j for j in J['jobs'] if j['id'] == jid), None)
        if job is None:
            job = dict(id=jid, frame=pose, kind='pose', status='pending', attempt=1, credits=0, credits_estimated=600, date='2026-11-02',
                       model='gpt-image-2-5', quality='sunburst', idempotency_key=f'v7-{jid}-20261102-a1')
            J['jobs'].append(job)
        if job.get('status') == 'pending':
            ov = SC[pose].get('overscan', {})
            job.update(room=rooms[base], base=base, prompt_file=res[pose]['prompt_file'], out_dir='assets/renders/poses/nordic/v7/',
                       refs=murls + purls, masters=[k for _, k in fr_refs], overscan=dict(ov) if ov.get('on') else dict(on=False))
        json.dump(J, open(os.path.join(HERE, 'jobs.json'), 'w'), indent=1, ensure_ascii=False)
    old = json.load(open(os.path.join(HERE, 'poses.json'))) if os.path.exists(os.path.join(HERE, 'poses.json')) else {}
    old.update(res)
    json.dump(old, open(os.path.join(HERE, 'poses.json'), 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
