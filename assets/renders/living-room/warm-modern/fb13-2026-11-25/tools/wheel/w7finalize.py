"""w7finalize.py: the wheel's files into the FB13 folder; layers/manifest-wheel.json (fix1 + the cushions' wheel B / A / C); the checks;
the job record (also under assets/prompts/); the scripts into tools/wheel/"""
import os, json, shutil, hashlib
W7 = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wheel7/'
REPO = '/home/user/homedesign-app'
REL = 'assets/renders/living-room/warm-modern/fb13-2026-11-25'
FB13 = REPO + '/' + REL + '/'
PR = REPO + '/assets/prompts/warm-modern-fb13-2026-11-25/'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
U = 'https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/'
copies = {
    'out/set-A-layer.png': 'layers/cushions/set-A.png', 'out/set-C-layer.png': 'layers/cushions/set-C.png',
    'out/set-A-shadow.png': 'shadows/cushions/set-A.png', 'out/set-C-shadow.png': 'shadows/cushions/set-C.png',
    'out/frame-A.png': 'default-frame-m0w-wheel-A.png', 'out/frame-C.png': 'default-frame-m0w-wheel-C.png',
    'out/qa-sheet-m0w-wheel.jpg': 'qa-sheet-m0w-wheel.jpg',
    'ret/setA-nano.jpg': 'raw/wheel-setA-nano.jpg', 'ret/setC-nano.jpg': 'raw/wheel-setC-nano.jpg',
}
for s, d in copies.items():
    shutil.copyfile(W7 + s, FB13 + d)
os.makedirs(FB13 + 'tools/wheel', exist_ok=True)
for f in ('segplace.py', 'w7reg.py', 'w7build.py', 'w7compose.py', 'w7diag.py', 'w7sheet.py', 'w7finalize.py'):
    shutil.copyfile(W7 + 'tools/' + f, FB13 + 'tools/wheel/' + f)
for f in ('wheel-e1-set-A.txt', 'wheel-e2-set-C.txt'):
    shutil.copyfile(W7 + 'prompts/' + f, PR + f)
reg = json.load(open(W7 + 'out/reg.json'))
bld = {k: json.load(open(W7 + f'out/build-{k}.json')) for k in 'AC'}
chk = json.load(open(W7 + 'out/checks.json'))
v3c = json.load(open(REPO + '/assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07/layers-v3c/manifest.json'))['sets']
# ---------------- the job record
refs = {'A': [('3e28f153-f773-4031-887d-54a9aaff1d21.png', 'cushions-cj-knitted-chenille-bean-green', 'CJYD282217003CX', 'image 2: the left cushion (21 Camel, reads taupe), cropped to the front cushion'),
              ('9a0cb854-e70a-403f-988d-2bc0748da2b7.png', 'cushions-cj-boucle-teddy', 'CJZT228600103CX', 'image 3: the right cushion (White 50x50), cactus cropped out'),
              ('5d626e89-de85-4b9d-a2cc-df68f6120502.png', 'cushions-cj-boucle-teddy', 'CJZT228600126ZA', 'image 4: the lumbar (Milk Tea 30x50; the SKU photo shows the square)'),
              ('1e10bb8a-40bd-45b6-b9f6-55d5e8ae4e2c.png', 'sofa-cover-cj-cotton-muslin-fringe', 'CJYD205807538LO', 'image 5: the throw (Flax brown 150x200), the person cropped out')],
        'C': [('0ef9496b-0973-4fc2-89b1-a27de1b360f9.png', 'cushions-cj-corduroy-patchwork', 'CJZT189401910JQ', 'image 2: the left cushion (Dark Coffee 45x45), cropped to the cushion'),
              ('8b088655-e262-4ee5-a969-4d78178d8081.png', 'cushions-cj-boucle-teddy', 'CJZT228600133GT', 'image 3: the right cushion (Light Brown 50x50), cactus cropped out'),
              ('64ce530b-b3bf-403b-bbdf-200194014eb6.png', 'cushions-cj-linen-look-ivory', 'CJZT242978810JQ', 'image 4: the lumbar (Light Beige Gray; the SKU photo shows squares)'),
              ('02baa8f4-a8eb-4ef1-9740-1d3f158f5c77.png', 'sofa-cover-cj-cotton-muslin-fringe', 'CJYD205807510JQ', 'image 5: the throw (Clay 150x200)')]}
ret = {'A': dict(pid='1b0120b6-241e-4b31-8bbf-bcc0a3cd2978', task='9436e9f1469768300b5beacfef91dcb3', url=U + 'nano2-9436e9f1469768300b5beacfef91dcb3-0-1795708412002-61a6531c.jpg',
                 seg='950bc5f0-3b7d-4474-ae7b-63eb795e571a', seg_idx=dict(left=[4, 9], right=[6, 10], lumbar=[5, 7, 8], throw=[3])),
       'C': dict(pid='e6cbf467-2c5d-47c9-9ff6-2668292cf0e9', task='841d0ec80b365ea6d3021bcb765fc922', url=U + 'nano2-841d0ec80b365ea6d3021bcb765fc922-0-1795708415525-b022e073.jpg',
                 seg='f7bba09f-eae2-45b8-89ce-6bb866916cce', seg_idx=dict(left=[1, 5, 8], right=[2, 6, 9], lumbar=[3, 4, 7], throw=[10]))}
jobs = []
for i, k in enumerate('AC'):
    pf = f'wheel-e{i + 1}-set-{k}.txt'
    jobs.append(dict(
        id=f'wm-m0w-wheel7-e{i + 1}-set-{k}', what=f'set {k} (three cushions and the throw) in place of set B, on the fix1 hero',
        model='nano-banana-2', type='image-to-image', resolution='2K', aspect_ratio='16:9', tokens=400,
        prompt=pf, prompt_sha256=sha(PR + pf),
        image_url=U + '2818558c-7639-45f2-814d-c8fa34dd2875.png', image_sha256=sha(W7 + 'send/cush-crop-x2.png'),
        image_source='hero-HW-fix1.png crop, x2 Lanczos', crop_canvas_px=[1120, 810, 2400, 1530], sent_px=[2560, 1440],
        image_refs=[dict(url=U + f, card=c, sku=s, what=w) for f, c, s, w in refs[k]],
        idempotency_key=f'wm-m0w-wheel7-e{i + 1}-set-{k}-nano-2k-20261126', placeholder_id=ret[k]['pid'], task_id=ret[k]['task'], url=ret[k]['url'],
        raw=f'raw/wheel-set{k}-nano.jpg', raw_sha256=sha(W7 + f'ret/set{k}-nano.jpg'),
        registration={kk: v for kk, v in reg[k].items() if kk != 'A'},
        segment_map=dict(model='grok-imagine-image-2', type='segment-map', tokens=0, segment_map_id=ret[k]['seg'], used_indexes=ret[k]['seg_idx'],
                         note='bbox cut-outs placed in the return by masked template matching (rms 0), then carried by the registration'),
        verdict='USED: the three cushions and the throw. True to the SKU photos in colour and weave; the throw reads as crinkled muslin with a '
                'frayed fringe (not a knit). The edit draped the throw further than set B, onto the rug in front of the arm and under the table. '
                'The left 45 x 45 cushion was drawn at the 50 x 50 width: one recorded refit in code (see the manifest)'))
rec = dict(id='wm-m0w-wheel7-2026-11-26', step='M0-W stage A step 7 (docs/proposals/wm-fb13-living-wow-2026-11-25.md 3.2): the sample slot\'s wheel',
           date='2026-11-26', author='render-agent', owner_words='הסלון נראה מדהים (2026-11-26, the new living room approved)',
           camera=dict(id='M0-W', loc=[0.95, 5.55, 1.05], yaw_deg_left=14.0, lens=35.0, u0=0.5, v0=0.555),
           seed=None, seed_note='var2 exposes no seed for nano-banana-2: the prompt, the input crop (sha256), the references and the settings are kept',
           estimate=dict(tool='var2_estimate_cost', nano_banana_2_i2i_2K=400), tokens_total=800, cap=1000,
           stage_a_tokens=dict(before=5500, after=6300, cap=6500),
           not_done=dict(set_B_throw_muslin='not in this pass: a third nano edit is 400, so 1,200 > the cap of 1,000; set B keeps its stage-A throw (reads knitted)'),
           references_policy='supplier images are references only (cropped in the scratchpad, uploaded to var2, never stored in the repo)', jobs=jobs)
json.dump(rec, open(FB13 + 'jobs-wheel.json', 'w'), indent=1, ensure_ascii=False)
json.dump(rec, open(PR + 'wm-m0w-wheel.json', 'w'), indent=1, ensure_ascii=False)
# ---------------- the checks
chk_out = dict(id='wm-m0w-wheel7-checks-2026-11-26', B_default=dict(stack='layers/manifest-fix1.json (unchanged)', reproduces_default_frame_m0w_fix1=chk['B_stack_vs_stored_default_frame']),
               rnd2_rule='A and C differ from B only inside the union of the two sets\' alpha and shadow; hiding a set changes its own region only; '
                         'every other layer, shadow and light byte-identical to fix1',
               sets={k: chk[k] for k in 'AC'}, B_F3_gap_frame_widths=chk['B_F3_gap_frame_widths'],
               build={k: bld[k] for k in 'AC'},
               notes=['F3 in frame widths (2565 canvas px): the holder 0.0244 (A) / 0.0208 (C) against 0.0417 for B: the muslin throws reach further right; candle holders x set 0.003 as B (0.002, the table stands in front)',
                      'stack_vs_edit: the set\'s opaque, visible pixels against the edit (baked), outside the refitted left cushion',
                      'the sofa between the pieces is the plate in the edit\'s light (as stage A): its boucle grain differs from the edit\'s where set B\'s throw used to cover the right arm'])
json.dump(chk_out, open(FB13 + 'checks-m0w-wheel.json', 'w'), indent=1, ensure_ascii=False)
# ---------------- the manifest
man = json.load(open(FB13 + 'layers/manifest-fix1.json'))
man['id'] = 'wm-living-room-m0w-fb13-wheel-2026-11-26'
man['status'] = ('FB13 M0-W step 7, the sample slot\'s wheel (cushions: B default, A, C), on the fix1 stack. Not QA\'d; HD_PUBLIC=0 only. '
                 'Rollback: manifest-fix1.json (identical but for the wheel)')
def products(k):
    out = []
    for p in v3c[k]['products']:
        q = {kk: p[kk] for kk in ('card_id', 'card', 'role', 'option', 'sku') if kk in p}
        if p.get('sku_candidates'):
            q['sku_candidates'] = p['sku_candidates']
        if p.get('note'):
            q['note'] = p['note']
        out.append(q)
    return out
sets = {}
B = [l for l in man['layers'] if l['slot'] == 'cushions'][0]
sets['B'] = dict(layer=B['layer'], shadow=B['shadow'], default=True, products=products('B'), alpha_px=B['alpha_px'], shadow_px=B['shadow_px'], bbox_px=B['bbox_px'],
                 source=B['source'], default_frame='../default-frame-m0w-fix1.png',
                 fidelity_open='the Pecan throw reads knitted (stage-A layer); the card is a crinkled cotton muslin: not refitted in this pass (budget)')
for i, k in enumerate('AC'):
    b = bld[k]
    sets[k] = dict(layer=f'layers/cushions/set-{k}.png', shadow=f'shadows/cushions/set-{k}.png', default=False, products=products(k),
                   alpha_px=b['alpha_px'], alpha_255_px=b['alpha_255_px'], shadow_px=b['shadow_px'], bbox_px=b['bbox_px'],
                   source=f'nano-banana-2 2K edit of hero-HW-fix1.png (raw/wheel-set{k}-nano.jpg, jobs-wheel.json e{i + 1}) cut in code (tools/wheel/w7build.py)',
                   refit=b['refit_left'], default_frame=f'../default-frame-m0w-wheel-{k}.png')
sets['C']['fidelity_open'] = ('the lumbar: the selection names Light Beige Gray 30x50 (as rendered, as the approved pilot), but the card lists 45x45 only '
                              '(with insert): sourcing to confirm a 30x50 exists')
man['cushions'] = dict(set='B', wheel=dict(slot='cushions', z=55, shadow_z=54, default='B', order=['B', 'A', 'C'], sets=sets,
                                           swap='replace the cushions entry\'s layer and shadow with the set\'s; nothing else changes (RND2: checks-m0w-wheel.json)'),
                       products=man['cushions']['products'])
man['method_wheel'] = ('tools/wheel/: each set = one nano-banana-2 2K edit of a 1280 x 720 crop of hero-HW-fix1.png (sent x2), registered (SIFT affine, '
                       'prep.py) and tone-fitted; the pieces\' masks from grok segment-map (0 tokens); alpha as stage A (4 px fringe of the edit\'s room, '
                       'anti-aliased against another product, 4 px on under the table); the set\'s pixels = the edit baked with the stage-A finish, the lamps\' '
                       'screen solved out and the higher layers\' (the table\'s) shadow divided out; its shadow = low-pass luma(edit) / luma(the stack '
                       'without the cushions), darker only, in a 90 px zone of influence (stage A\'s radius); one recorded refit (the left cushion to 45/50)')
man['files'] = dict(man['files'], wheel=dict(default_frames={'B': '../default-frame-m0w-fix1.png', 'A': '../default-frame-m0w-wheel-A.png', 'C': '../default-frame-m0w-wheel-C.png'},
                                              sheet='../qa-sheet-m0w-wheel.jpg', checks='../checks-m0w-wheel.json', jobs='../jobs-wheel.json', tools='../tools/wheel/'))
man['rnd2_wheel'] = {k: {kk: chk[k][kk] for kk in ('canvas_changed_vs_B_px', 'changed_outside_A_or_B_regions_px', 'hide_set_changed_outside_its_region_px')} for k in 'AC'}
json.dump(man, open(FB13 + 'layers/manifest-wheel.json', 'w'), indent=1, ensure_ascii=False)
print('ok')
