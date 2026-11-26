"""pfinalize.py: fix1-pecan into the FB13 folder, NEW files only (frontend-dev reads this folder: nothing existing is overwritten or renamed);
layers/manifest-wheel-pecan.json (manifest-wheel.json with set B on the Pecan muslin); checks; the job record (also under assets/prompts/);
the scripts into tools/pecan/; the new files appended to assets/manifest.json"""
import os, json, shutil, hashlib, sys
PC = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/pecan/'
REPO = '/home/user/homedesign-app'
REL = 'assets/renders/living-room/warm-modern/fb13-2026-11-25'
FB13 = REPO + '/' + REL + '/'
PR = REPO + '/assets/prompts/warm-modern-fb13-2026-11-25/'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
U = 'https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/'
copies = {
    'out/set-B-pecan-layer.png': 'layers/cushions/set-B-fix1-pecan.png',
    'out/set-B-pecan-shadow.png': 'shadows/cushions/set-B-fix1-pecan.png',
    'out/frame-new.png': 'default-frame-m0w-fix1-pecan.png',
    'out/qa-sheet-pecan.jpg': 'qa-sheet-pecan.jpg',
    'ret/pecan-nano.jpg': 'raw/fix1-pecan-nano.jpg',
}
TOOLS = ('preg.py', 'pseg.py', 'pbuild.py', 'pcolour.py', 'psheet.py', 'pfinalize.py')
NEW = list(copies.values()) + ['layers/manifest-wheel-pecan.json', 'checks-m0w-pecan.json', 'jobs-pecan.json'] + ['tools/pecan/' + f for f in TOOLS]
clash = [p for p in NEW if os.path.exists(FB13 + p)] + [p for p in ('wm-m0w-pecan.json',) if os.path.exists(PR + p)]
if clash:
    sys.exit('refusing to overwrite: %s' % clash)
for s, d in copies.items():
    shutil.copyfile(PC + s, FB13 + d)
os.makedirs(FB13 + 'tools/pecan', exist_ok=True)
for f in TOOLS:
    shutil.copyfile(PC + 'tools/' + f, FB13 + 'tools/pecan/' + f)
reg = json.load(open(PC + 'out/reg.json'))
chk = json.load(open(PC + 'out/checks.json'))
col = json.load(open(PC + 'out/colour.json'))
b = chk['build']
STATUS = ('FB13 M0-W fix1-pecan: set B\'s throw re-cut as the Pecan muslin (the cushions untouched). Not QA\'d; HD_PUBLIC=0 only. '
          'Rollback: manifest-wheel.json (set B = layers/cushions/set-B.png, the stage-A knit)')
# ---------------- the job record
PROMPT = 'fix1-pecan-e1-throw.txt'
job = dict(
    id='wm-m0w-fix1-pecan-e1-throw', what='set B\'s throw only: the stage-A knit -> the Pecan cotton muslin of the card (crinkled, fringed), same drape',
    model='nano-banana-2', type='image-to-image', resolution='2K', aspect_ratio='16:9', tokens=400,
    prompt=PROMPT, prompt_sha256=sha(PR + PROMPT),
    image_url=U + '2818558c-7639-45f2-814d-c8fa34dd2875.png', image_sha256=sha(PC + 'send/cush-crop-x2.png'),
    image_source='hero-HW-fix1.png crop, x2 Lanczos (the same upload as the wheel\'s two edits; sha256 checked)',
    crop_canvas_px=[1120, 810, 2400, 1530], sent_px=[2560, 1440],
    image_refs=[dict(url=U + 'cb0ab2fb-c995-4c25-aa12-fbbd2fa5f42b.png', card='sofa-cover-cj-cotton-muslin-fringe', sku='CJYD205807508HS',
                     what='image 2: the throw (Pecan 150x200), the SKU photo cropped to the throw (the pilot\'s upload, sha256 7fb76793...)')],
    idempotency_key='wm-m0w-fix1-pecan-e1-throw-nano-2k-20261126', placeholder_id='549bc67f-42c5-4384-86a1-0f624e6b5787',
    task_id='9045a1108608a14dd7447f72768aca00', url=U + 'nano2-9045a1108608a14dd7447f72768aca00-0-1795716039128-20810908.jpg',
    raw='raw/fix1-pecan-nano.jpg', raw_sha256=sha(PC + 'ret/pecan-nano.jpg'),
    registration=reg,
    segment_map=dict(model='grok-imagine-image-2', type='segment-map', tokens=0, segment_map_id='7f719343-b119-42e1-9f63-97702468947c',
                     used_indexes=dict(cushions=[1, 2, 3, 4, 5, 6, 7, 8, 9], throw=[10], lamp=[17]),
                     note='bbox cut-outs placed in the return by masked template matching (rms 0), then carried by the registration; '
                          '1-3, 4-6 and 7-9 are the same three cushions under three names'),
    verdict=('USED: the throw. It reads as crinkled waffle cotton muslin with a frayed fringe (not a knit), in the Pecan hue (54.8 deg against '
             'the SKU\'s 54.3). The drape is the same (from behind the lumbar, across the seat front, over the right arm; one fall down behind '
             'the Olia to the rug, one down the arm\'s outer side to the floor by the lamp base), but fuller: the front fall is wider (it covers '
             'more of the arm\'s front face and shows under the table top) and its fringe lies about 15 canvas px (11 frame px) further onto the rug; the outer fall '
             'sits a little left, off the lamp pole. The cushions, sofa, table and lamp were left alone by the model (their pixels are not used)'))
rec = dict(id='wm-m0w-fix1-pecan-2026-11-26', step='M0-W set B fidelity fix: the Pecan throw read knitted (manifest-wheel.json fidelity_open; README step 7 open 1)',
           date='2026-11-26', author='render-agent', owner_words='the owner approved one nano 2K edit (400); stage A cap 6,700',
           camera=dict(id='M0-W', loc=[0.95, 5.55, 1.05], yaw_deg_left=14.0, lens=35.0, u0=0.5, v0=0.555),
           seed=None, seed_note='var2 exposes no seed for nano-banana-2: the prompt, the input crop (sha256), the reference and the settings are kept',
           estimate=dict(tool='var2_estimate_cost', nano_banana_2_i2i_2K=400), tokens_total=400, cap=400,
           stage_a_tokens=dict(before=6300, after=6700, cap=6700),
           retry=dict(used=False, why='not needed for the fabric; a retry for a tighter drape would be 7,100 > 6,700: the owner\'s approval first'),
           references_policy='supplier images are references only (cropped in the scratchpad, uploaded to var2, never stored in the repo)', jobs=[job])
json.dump(rec, open(FB13 + 'jobs-pecan.json', 'w'), indent=1, ensure_ascii=False)
json.dump(rec, open(PR + 'wm-m0w-pecan.json', 'w'), indent=1, ensure_ascii=False)
# ---------------- the checks
chk_out = dict(id='wm-m0w-pecan-checks-2026-11-26',
               old_stack=dict(stack='layers/manifest-wheel.json (unchanged)', reproduces_default_frame_m0w_fix1=chk['old_stack_vs_stored_default_frame_m0w_fix1']),
               rnd2=chk['rnd2'], build=b, fidelity_stack_vs_edit=chk['fidelity_stack_vs_edit'],
               colour=dict(throw_Lab_median_core=chk['colour_Lab_median'], same_measure_all_throws=col,
                           note='same measure for the three throws (lower falls, alpha 255, not under the table): Pecan (B new) dE00 3.44 = Clay (C) 3.44; '
                                'Flax (A) 1.61; hue within 0.5 deg. The room keeps more chroma than the exposure-dimmed SKU photo (warm grade and lamp), as in C. '
                                'The old knit scores 0.79 only because it is dark (L 14.7 against the SKU photo\'s 33; the new one 21.0)'),
               F3_gap_frame_widths=chk['F3_gap_frame_widths'],
               wheel_studio=dict(file='assets/renders/wheel-studio/warm-modern/living-room/cushions/set-B.png', changed=False,
                                 why='its throw already reads as crinkled waffle muslin with a frayed fringe (checked at 1024 px): no fix, 0 tokens'),
               notes=['RND2 regions: Z = (the old throw | the new throw, each dilated 6 px) minus the cushions (segment map); the shadow\'s zone = 90 px of '
                      'the throw (stage A\'s radius). Outside: set B\'s stage-A layer and shadow byte for byte; every other layer, shadow and light untouched',
                      'revealed_where_the_knit_was: the large per-pixel numbers are the sofa arm\'s boucle (the plate\'s grain against the boucle nano re-drew), '
                      'not missing fabric (checked at x3)',
                      'pole_patch: the floor-lamp layer had no pixels where the knit hid the lower pole; without them the pole would stop above the new '
                      'throw. The edit\'s pole there (270 px) is carried in set B\'s layer, inside the old throw\'s region; sets A and C are not affected',
                      'open (low, x4; faint at x2): the table layer\'s anti-aliased underside edge was mixed against the light boucle; over the dark throw '
                      'under the table it reads as a 1 px light line. Same class in A and C. The fix is in the table layer (outside this task)',
                      'open: the part of the throw behind the Olia\'s leg is in the layer only 4 px (as A and C); the stage-A knit had more under the table'])
json.dump(chk_out, open(FB13 + 'checks-m0w-pecan.json', 'w'), indent=1, ensure_ascii=False)
# ---------------- the manifest
man = json.load(open(FB13 + 'layers/manifest-wheel.json'))
man['id'] = 'wm-living-room-m0w-fb13-wheel-pecan-2026-11-26'
man['status'] = STATUS
src = 'nano-banana-2 2K edit of hero-HW-fix1.png (raw/fix1-pecan-nano.jpg, jobs-pecan.json) cut in code (tools/pecan/pbuild.py), the throw only; the cushions are set-B.png\'s'
for l in man['layers']:
    if l['slot'] == 'cushions':
        l.update(layer='layers/cushions/set-B-fix1-pecan.png', shadow='shadows/cushions/set-B-fix1-pecan.png', alpha_px=b['alpha_px'],
                 shadow_px=b['shadow_px'], bbox_px=b['bbox_px'], source=src)
B = man['cushions']['wheel']['sets']['B']
B.pop('fidelity_open', None)
B.update(layer='layers/cushions/set-B-fix1-pecan.png', shadow='shadows/cushions/set-B-fix1-pecan.png', alpha_px=b['alpha_px'],
         alpha_255_px=b['alpha_255_px'], shadow_px=b['shadow_px'], bbox_px=b['bbox_px'], source=src,
         default_frame='../default-frame-m0w-fix1-pecan.png',
         fidelity='the Pecan throw reads as crinkled cotton muslin with a frayed fringe, as the card (was: knitted, stage A). Drape kept, a little fuller (jobs-pecan.json verdict)',
         patch=dict(what='the floor lamp\'s lower pole, 270 px, from the edit', where='where the stage-A knit hid it and the new throw does not (the floor-lamp layer has no pixels there)',
                    why='without it the pole would stop short above the throw', note='inside the old throw\'s region; sets A and C are not affected'),
         rollback=dict(layer='layers/cushions/set-B.png', shadow='shadows/cushions/set-B.png', default_frame='../default-frame-m0w-fix1.png', manifest='manifest-wheel.json'))
man['method_pecan'] = ('tools/pecan/: one nano-banana-2 2K edit of the wheel\'s crop of hero-HW-fix1.png (the same upload), the throw only; registered '
                       '(SIFT affine, prep.py) and tone-fitted; masks from grok segment-map (0 tokens). Cut as tools/wheel/w7build.py, but only inside '
                       'Z = (old throw | new throw, 6 px) minus the cushions: there the edit\'s alpha (4 px fringe of the room, anti-aliased against another '
                       'product, 4 px on under the table) and pixels (the stage-A finish baked, the lamps\' screen solved out, the table\'s shadow divided out); '
                       'elsewhere set-B.png byte for byte. The shadow: set B\'s beyond 90 px of the throw, the new low-pass luma ratio within 45 px, '
                       'a log blend between, set B\'s under the cushions. One patch: the lamp\'s pole where the knit hid it')
man['files'] = dict(man['files'], pecan=dict(default_frame='../default-frame-m0w-fix1-pecan.png', sheet='../qa-sheet-pecan.jpg',
                                             checks='../checks-m0w-pecan.json', jobs='../jobs-pecan.json', tools='../tools/pecan/',
                                             rollback='manifest-wheel.json'))
man['files']['wheel'] = dict(man['files']['wheel'], default_frames=dict(man['files']['wheel']['default_frames'], B='../default-frame-m0w-fix1-pecan.png'))
man['rnd2_pecan'] = {k: chk['rnd2'][k] for k in ('layer_changed_px', 'layer_changed_outside_Z_px', 'layer_changed_in_cushions_px', 'shadow_changed_px',
                                                 'shadow_changed_outside_90px_of_throw_px', 'canvas_changed_px', 'canvas_changed_outside_throw_region_px',
                                                 'frame_changed_px', 'hide_set_changed_outside_its_region_px')}
json.dump(man, open(FB13 + 'layers/manifest-wheel-pecan.json', 'w'), indent=1, ensure_ascii=False)
# ---------------- assets/manifest.json: append the new files (indent 1, no trailing newline, as the file is)
AM = REPO + '/assets/manifest.json'
am = json.load(open(AM))
have = {a['id'] for a in am['assets']}
RECIPE = REL + '/tools/pecan/ (layers/manifest-wheel-pecan.json method_pecan)'
PRJ = 'assets/prompts/warm-modern-fb13-2026-11-25/wm-m0w-pecan.json'
ST_A = 'FB13 M0-W fix1-pecan, set B\'s throw as the Pecan muslin: not QA\'d, HD_PUBLIC=0 only; manifest-wheel.json and set-B.png kept for rollback'
ents = [
    ('wm-m0w-pecan-layers-manifest', 'layers/manifest-wheel-pecan.json', 'layers manifest: manifest-wheel.json with set B on the Pecan muslin throw', 'code (0 tokens)', 0),
    ('wm-m0w-pecan-layer-cushions-set-b', 'layers/cushions/set-B-fix1-pecan.png', 'cushions set B layer, the Pecan throw re-cut (straight alpha, z 55), 2720 x 1530', 'nano-banana-2 i2i 2K + code', 400),
    ('wm-m0w-pecan-shadow-cushions-set-b', 'shadows/cushions/set-B-fix1-pecan.png', 'cushions set B shadow, the Pecan throw (multiply, z 54), 2720 x 1530', 'code (0 tokens)', 0),
    ('wm-m0w-pecan-default-frame-b', 'default-frame-m0w-fix1-pecan.png', 'default frame with cushions set B (Pecan muslin), rebuilt from layers/manifest-wheel-pecan.json, 1920 x 1080', 'code (0 tokens)', 0),
    ('wm-m0w-pecan-qa-sheet', 'qa-sheet-pecan.jpg', 'QA sheet: set B\'s throw before and after at x2, the frames, the SKU photo', 'code (0 tokens)', 0),
    ('wm-m0w-pecan-checks', 'checks-m0w-pecan.json', 'checks: RND2, reproduction, fidelity to the edit, colour against the SKU, F3', 'code (0 tokens)', 0),
    ('wm-m0w-pecan-jobs', 'jobs-pecan.json', 'job record of the nano edit (prompt, input, reference, ids, registration, verdict)', 'record', 0),
    ('wm-m0w-pecan-raw', 'raw/fix1-pecan-nano.jpg', 'nano-banana-2 return, set B Pecan throw edit (2752 x 1536)', 'nano-banana-2 i2i 2K', 0),
]
added = []
for i, p, kind, model, tok in ents:
    if i in have:
        continue
    fp = FB13 + p
    am['assets'].append(dict(id=i, path=REL + '/' + p, kind=kind, room='living-room', style='warm-modern', created='2026-11-26', model=model,
                             recipe=RECIPE, tokens=tok, status=ST_A, prompts=PRJ, sha256=sha(fp), bytes=os.path.getsize(fp)))
    added.append(i)
open(AM, 'w').write(json.dumps(am, indent=1, ensure_ascii=False))
print('ok; assets added', added)
