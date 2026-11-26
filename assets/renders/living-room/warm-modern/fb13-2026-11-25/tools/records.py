#!/usr/bin/env python3
"""records.py: FB13 stage A steps 2-6: the layers' manifest, the jobs record and the prompts, the tools, the raw returns kept, the
entries of assets/manifest.json. (The README section is written by hand.)"""
import hashlib, json, os, shutil
import cv2, numpy as np
from PIL import Image
import hwlib as L
from extract import ORDER, LAMPS, PRODUCT, RADIUS

D = L.FB13
REL = "assets/renders/living-room/warm-modern/fb13-2026-11-25"
PR = os.path.join(L.REPO, "assets/prompts/warm-modern-fb13-2026-11-25")
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
B = "https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/"
parts = json.load(open(os.path.join(L.OUT, "manifest-parts.json")))
prep = json.load(open(os.path.join(L.OUT, "prep", "prep.json")))
chk = json.load(open(os.path.join(D, "checks-m0w.json")))
ext = json.load(open(os.path.join(L.OUT, "stack", "extract.json")))
# ---- the tools and the raw returns
os.makedirs(os.path.join(D, "tools"), exist_ok=True)
for f in ("clay_hw.py", "guide_pw.py", "guide_hw.py", "guide_hw_geom.py", "hwlib.py", "lock.py", "prints.py", "prep.py", "masks.py", "extract.py", "check.py",
          "finalize.py", "sheet.py", "records.py"):
    shutil.copy(os.path.join(L.SP, "code", f), os.path.join(D, "tools", f))
os.makedirs(os.path.join(D, "raw"), exist_ok=True)
raws = {"pw-seedream-r2.png": "plate-PW-seedream-r2.png", "hw-seedream-r1.png": "hero-HW-seedream-r1.png", "e1-table-nano.jpg": "e1-table-nano.jpg",
        "e2-notable-nano.jpg": "e2-notable-nano.jpg", "e3-rugend-nano.jpg": "e3-rugend-nano.jpg"}
for a, b in raws.items():
    shutil.copy(os.path.join(L.SP, "raw", a), os.path.join(D, "raw", b))
Image.open(os.path.join(L.SP, "raw", "pw-seedream-r1.png")).convert("RGB").resize((1360, 765), Image.LANCZOS).save(os.path.join(D, "raw", "plate-PW-seedream-r1-rejected.jpg"), quality=88)
shutil.copy(os.path.join(L.OUT, "pw-input.png"), os.path.join(D, "raw", "plate-PW-input-r2.png"))
shutil.copy(os.path.join(L.OUT, "hw-input.png"), os.path.join(D, "raw", "hero-HW-input.png"))
# ---- the prompts
os.makedirs(PR, exist_ok=True)
pf = {"pw.txt": "pw-r1.txt", "pw-retry.txt": "pw-r2.txt", "hw.txt": "hw.txt", "e1-table.txt": "e1-table.txt", "e2-notable.txt": "e2-notable.txt", "e3-rugend.txt": "e3-rugend.txt"}
for a, b in pf.items():
    shutil.copy(os.path.join(L.SP, "prompts", a), os.path.join(PR, b))
psha = lambda f: hashlib.sha256(open(os.path.join(PR, f)).read().rstrip("\n").encode()).hexdigest()
SK = dict(olia=B + "3976a397-7284-4367-99c6-7f2d05398da3.png", rug=B + "cd8d73bb-aeea-4d55-aa6e-7a98b72f43f3.png", boucle=B + "3af0d106-21b0-4384-a661-2b0b8d30652b.png",
          corduroy=B + "58594f22-7ae3-45cd-83d6-a983aee8b480.png", linen=B + "18762c34-194d-40f0-a02b-f6c19122b3fe.png", throw=B + "cb0ab2fb-c995-4c25-aa12-fbbd2fa5f42b.png",
          holder=B + "95b556a1-5ea2-4548-8133-747bd6a3470b.png", lamps=B + "0bb7c4d0-3aa0-4470-aca7-295deec887b5.png", small=B + "5df7017a-75c0-402c-9090-a892d30a60da.png")
MAT = [B + "1ecd0123-aaf2-4aa2-8fc8-a3e1a5906921.png", B + "d73694dd-0e48-464c-96fc-aaf48fd2be2c.png", B + "c8094822-97c8-4495-b21c-4ccb8a2ff4ab.png", B + "7797cccf-74e3-4bc7-a50f-181fbe474ab4.png"]
common = dict(seed=None, seed_note="var2 exposes no seed for seedream-5-pro or nano-banana-2: the prompt, the input, the references and the settings are kept",
              references_policy="supplier images are references only (cropped in the scratchpad, uploaded to var2, never stored in the repo); the material references of the "
                                "plate are crops of our own approved plate (phase2 base-fb12s0.png) and of the first plate return")
jobs = [
 dict(id="wm-fb13-pw-r1", what="P-W, the empty-room plate (first send)", model="seedream-5-pro", type="image-to-image", resolution="2K", aspect_ratio="auto", tokens=650,
      prompt="pw-r1.txt", prompt_sha256=psha("pw-r1.txt"), image_url=B + "22935396-2a7b-4db9-a44d-d883680329fd.png", image_sha256="46779e7d79f837a1bcf2c040168e53474612a5f33643ad001af35dfd4ab7c016",
      image_refs=[dict(url=MAT[0], what="our armchair (crop of phase2 base-fb12s0.png)"), dict(url=MAT[1], what="the sofa's boucle (same)"), dict(url=MAT[2], what="floor and plaster (same)"), dict(url=MAT[3], what="glazing and bench (same)")],
      idempotency_key="wm-fb13-pw-seedream-2k-20261126", placeholder_id="97a4ddd8-a762-4c4a-b23f-aafcc50d812f", task_id="75771cf5c5210eecea2e38e56a252bb7",
      url=B + "seedream5p-75771cf5c5210eecea2e38e56a252bb7-0-1795687694115-2fc5db79.png", returned_px=[2720, 1530], raw="raw/plate-PW-seedream-r1-rejected.jpg (1360 px copy)",
      raw_sha256="bac9c148f91169fc32d28d471485ba5b8a574692a3a8b75df6c83740eb35b935",
      verdict="NOT USED: a fine photograph, but the camera was not kept (the clay's lines 73 px right and 88 px up, the ceiling in the frame): the prompt said 'a rough "
              "computer layout' and the sofa of the input was blurred. Its sofa is the form reference of r2"),
 dict(id="wm-fb13-pw-r2", what="P-W, the empty-room plate (the retry: the pilot's camera lock, the clay's named lines in the prompt)", model="seedream-5-pro", type="image-to-image",
      resolution="2K", aspect_ratio="auto", tokens=650, prompt="pw-r2.txt", prompt_sha256=psha("pw-r2.txt"), image_url=B + "7b360e87-6c8d-4c82-ba55-619035ff9a01.png",
      image_sha256="793d536fa5918bb95f3b611d2a0c2cb2b26a799cd9eda8c157ae0495a685bbf5", image_local="raw/plate-PW-input-r2.png",
      image_refs=[dict(url=B + "b8869473-9b2d-4d6e-82f0-fa42a0c9823f.png", what="the sofa of the r1 return (crop): the rounded seamless arms"), dict(url=MAT[0], what="our armchair"),
                  dict(url=MAT[2], what="floor and plaster"), dict(url=MAT[3], what="glazing and bench")],
      idempotency_key="wm-fb13-pw-seedream-2k-20261126-r2", placeholder_id="571c77a5-8300-4f24-a956-9c9a80d0de80", task_id="8061627a780923bd72f2ba4f062f37ff",
      url=B + "seedream5p-8061627a780923bd72f2ba4f062f37ff-0-1795688144485-20b72c1b.png", returned_px=[2720, 1530], raw="raw/plate-PW-seedream-r2.png",
      raw_sha256="9bf117a7a2c6c80410976cbc4e903d6fe183ce53622439e0a64d3c2d6287ea5e",
      verdict="USED: the camera kept (the clay's boundaries 2-4 px median from the frame's edges, global shift 4, -3 px)"),
 dict(id="wm-fb13-hw-r1", what="H-W, the hero: every default product in one light, on the plate", model="seedream-5-pro", type="image-to-image", resolution="2K", aspect_ratio="auto",
      tokens=650, prompt="hw.txt", prompt_sha256=psha("hw.txt"), image_url=B + "05cc5f32-54e3-46a9-8c73-c93621577ac2.png",
      image_sha256="646de30426968be4ef148b77666eef6078b233c63d33666d54e0150113a16c6e", image_local="raw/hero-HW-input.png",
      image_refs=[dict(n=2, url=SK["olia"], card="coffee-table-idana-javorina-olia-natural", what="board: studio shot, rolled edge close-up, the unit in a home"),
                  dict(n=3, url=SK["rug"], card="rug-cj-braided-wool-natural", what="close-up of the braided weave"),
                  dict(n=4, url=SK["boucle"], card="cushions-aliexpress-textured-boucle-throw-pillow (Oatmeal 50x50)"),
                  dict(n=5, url=SK["corduroy"], card="cushions-cj-wide-stripe-corduroy-light-green (Camel)"),
                  dict(n=6, url=SK["linen"], card="cushions-cj-linen-look-charcoal (Beige 30x50)"),
                  dict(n=7, url=SK["throw"], card="sofa-cover-cj-cotton-muslin-fringe (Pecan)"),
                  dict(n=8, url=SK["holder"], card="magazine-holder-cj-gunmetal-leather-strap"),
                  dict(n=9, url=SK["lamps"], what="board: accent-sconces-aliexpress-travertine-cylinder-walnut-choice, floor-lamp-cj-pleated-walnut-stem-158 (two photos), pendant-cj-tiered-fabric-drum"),
                  dict(n=10, url=SK["small"], what="board: vase-cj-textured-white-stoneware, planter-cj-cement-ribbed-belly, basket-cj-jute-rope-cylinder, bowl-cj-matte-black-bowl-20, candle-holders-cj-travertine-pedestal")],
      idempotency_key="wm-fb13-hw-seedream-2k-20261126", placeholder_id="9b50043d-b6ea-4935-bd72-9e8fa542318f", task_id="81fe1034beaf19a3346f401c522c079c",
      url=B + "seedream5p-81fe1034beaf19a3346f401c522c079c-0-1795688639921-ee16981b.png", returned_px=[2720, 1530], raw="raw/hero-HW-seedream-r1.png",
      raw_sha256="650e3d520c18073779629ca2dc09328850254f53285d686823c7c0e87509024c",
      verdict="USED. The gate: passed except two regions, both mended by group edits (below): the table came out with square ends (not the Olia's rolled bend) and the rug's "
              "right end with a flat band and a loose extra piece"),
 dict(id="wm-fb13-e1-table", what="group edit: the table's two ends rolled (the Olia), on a 1088 x 612 crop of the hero sent at x2", model="nano-banana-2", type="image-to-image", resolution="2K",
      aspect_ratio="16:9", tokens=400, prompt="e1-table.txt", prompt_sha256=psha("e1-table.txt"), image_url=B + "8292589d-a63f-4b81-bb99-d2f343d6748b.png",
      image_sha256="8e982d75d5d674440b513e372e756a89eaab175c4200d3a9103898b6c6222bd2", crop_canvas_px=[1016, 918, 2104, 1530], image_refs=[dict(url=SK["olia"], card="coffee-table-idana-javorina-olia-natural")],
      idempotency_key="wm-fb13-e1-table-nano-2k-20261126", placeholder_id="618c249c-34fb-4625-94e5-539b4f948c69", task_id="609a913c9f0a62b6ea4433723cbaeee3",
      url=B + "nano2-609a913c9f0a62b6ea4433723cbaeee3-0-1795689135917-dc4a6ebb.jpg", returned_px=[2752, 1536], raw="raw/e1-table-nano.jpg", raw_sha256=sha(os.path.join(D, "raw", "e1-table-nano.jpg")),
      verdict="USED: the table group and its own shadows only (prep.py: registered by SIFT, 0.55 px; tone-matched on the pixels the edit left alone)"),
 dict(id="wm-fb13-e2-notable", what="H-W without the table group (FB12-T): what lies under and behind the table, in the hero's light; the same crop", model="nano-banana-2", type="image-to-image",
      resolution="2K", aspect_ratio="16:9", tokens=400, prompt="e2-notable.txt", prompt_sha256=psha("e2-notable.txt"), image_url=B + "8292589d-a63f-4b81-bb99-d2f343d6748b.png",
      image_sha256="8e982d75d5d674440b513e372e756a89eaab175c4200d3a9103898b6c6222bd2", crop_canvas_px=[1016, 918, 2104, 1530], image_refs=[],
      idempotency_key="wm-fb13-e2-notable-nano-2k-20261126", placeholder_id="ceefe833-cbc6-4270-ad22-2554798c1fc2", task_id="fa6f5a2eb05d2f2bd57ef34b530654da",
      url=B + "nano2-fa6f5a2eb05d2f2bd57ef34b530654da-0-1795689161456-873cc2c8.jpg", returned_px=[2752, 1536], raw="raw/e2-notable-nano.jpg", raw_sha256=sha(os.path.join(D, "raw", "e2-notable-nano.jpg")),
      verdict="USED: the rug and the throw's end under the table, and the table's shadow on them (the hero over this frame)"),
 dict(id="wm-fb13-e3-rugend", what="group edit: the rug's right end plain (no band, no extra piece), on a 1088 x 612 crop sent at x2", model="nano-banana-2", type="image-to-image", resolution="2K",
      aspect_ratio="16:9", tokens=400, prompt="e3-rugend.txt", prompt_sha256=psha("e3-rugend.txt"), image_url=B + "8c8a5104-69e0-4aa5-b26a-8bcc72e98b27.png",
      image_sha256="fbf968ae17e171aeb0cdcbb4a58c4f09629f68ba25f5d72e58937ad2a1277e29", crop_canvas_px=[1632, 918, 2720, 1530], image_refs=[dict(url=SK["rug"], card="rug-cj-braided-wool-natural")],
      idempotency_key="wm-fb13-e3-rugend-nano-2k-20261126", placeholder_id="19fc2e5a-915c-4404-9ad6-3eedc32feffb", task_id="293475d4579d6930f91156235ed38ed5",
      url=B + "nano2-293475d4579d6930f91156235ed38ed5-0-1795689176772-0e82c2d9.jpg", returned_px=[2752, 1536], raw="raw/e3-rugend-nano.jpg", raw_sha256=sha(os.path.join(D, "raw", "e3-rugend-nano.jpg")),
      verdict="USED: the rug's right end only"),
]
rec = dict(id="wm-fb13-stage-a-hero-2026-11-26", brief="briefs/wm-fb13-stage-a-hero-2026-11-26.md", source="docs/proposals/wm-fb13-living-wow-2026-11-25.md 3.2 steps 2-6; "
           "the coordinator's notes of 2026-11-26 (the owner: the sun a third calmer; docs/proposals/wm-fb16-house-light-2026-11-26.md)", date="2026-11-26", author="render-agent",
           camera=dict(id="M0-W", loc=[0.95, 5.55, 1.05], yaw_deg_left=14.0, lens=35.0, u0=0.5, v0=0.555), **common,
           estimate=dict(tool="var2_estimate_cost", seedream_5_pro_i2i_2K=650, nano_banana_2_i2i_2K=400),
           jobs=jobs, segment_maps=[dict(model="grok-imagine-image-2", type="segment-map", tokens=0, of="the hero return", segment_map_id="897974b0-18f0-41fb-b7d2-fa37b4c5ae43", segments=35),
                                    dict(model="grok-imagine-image-2", type="segment-map", tokens=0, of="the table edit's return", segment_map_id="c1e00ce5-ab1a-4336-be6b-25d71af17966", segments=20)],
           tokens=dict(plate_r1=650, plate_r2=650, hero=650, edits=1200, segment_maps=0, total=3150, cap_this_run=3950, stage_a_before=750, stage_a_total=3900, stage_a_cap=6500),
           edits_registration={k: {kk: prep[k][kk] for kk in ("inliers", "residual_px_median", "tone_gain_offset", "unchanged_share")} for k in ("e1", "e2", "e3")},
           plate_to_hero=prep["plate_to_hero"], tone_match={k: v for k, v in prep["tone_match"].items() if k != "L_curve"}, tone_dark_anchor=prep["tone_dark_anchor"], prints=prep["prints"])
json.dump(rec, open(os.path.join(PR, "wm-fb13-stage-a-hero.json"), "w"), indent=1, ensure_ascii=False)
json.dump(rec, open(os.path.join(D, "jobs-hero.json"), "w"), indent=1, ensure_ascii=False)
# ---- the layers' manifest (the v2 form of the other rooms)
t, y = L.tone_curve(L.GRADE["xs"], L.GRADE["ys"])
man = dict(id="wm-living-room-m0w-fb13-stage-a-2026-11-26", room="living-room", style="warm-modern", frame="M0-W", canvas=[L.W, L.H], frame_box=[round(v, 4) for v in L.FB],
           base="../plate-PW.png", camera=dict(loc=[0.95, 5.55, 1.05], yaw=14.0, lens=35.0, u0=0.5, v0=0.555, status="PROPOSAL (camera-m0w-proposal.json has v0 0.52; v0 0.555 by the concepts' brief)"),
           compose="../plate-PW.png; per layer in z order: shadow (multiply), then the layer (straight alpha); lights (screen, z 90) times (1 - every alpha)",
           status="FB13 stage A, steps 2-6: the default stack of M0-W. Not QA'd; HD_PUBLIC=0 only; not in data/slots or docs/house-plan (the manager, after approval 3). "
                  "No cushion sets A / C yet (step 7).",
           method="tools/extract.py: the plate is the base; every product is cut from the ONE hero render (hero-HW.png); shadows = the hero over the plate, darker (multiply); "
                  "the lamps' light = the hero over the plate, brighter (screen)",
           grade=dict(L.GRADE, curve_at={str(v): round(float(np.interp(v, t, y)), 1) for v in (3.6, 26.7, 50, 65.5, 77.5, 93, 96)}),
           layers=parts["layers"], light=parts["light"], influence_radius_px=RADIUS,
           fillers=dict(planter="the olive tree (filler) is in the planter's layer; its leaf shadow on the plaster is in the planter's shadow",
                        vase="the dry branch (filler) is in the vase's layer", candle_holders="the candles (filler) are in the layer", magazine_holder="the newspapers (filler) are in the layer",
                        framed_art="the three prints are set in code into the frames (tools/prints.py): TL2356-1 / -2 / -3, lit by the canvas's own light in the hero"),
           cushions=dict(set="B", products=["cushions-aliexpress-textured-boucle-throw-pillow (Oatmeal 50x50)", "cushions-cj-wide-stripe-corduroy-light-green (Camel)",
                                             "cushions-cj-linen-look-charcoal (Beige 30x50)", "sofa-cover-cj-cotton-muslin-fringe (Pecan)"]),
           coffee_table=dict(note="FB12-T: a swappable layer; the rug's layer under it comes from the hero rendered without the table group (E2) and carries no table shadow; "
                                  "'not yet for sale' until IDANA's written approval"),
           not_in_frame=["curtains (the stack is left of the frame)", "wall-sconce (window wall, out of frame)"],
           moved_for_the_frame=dict(magazine_holder=dict(to=[-0.68, 2.25], was=[-0.47, 2.57], why="25 % visible at v0 0.555; for the designer"),
                                    planter=[-1.34, 0.549], basket=[-1.8, 1.05]),
           rnd2=dict(chk["rnd2"], rule="outside every alpha, shadow and light: plate-PW.png, pixel for pixel; hiding one product changes its own region only"),
           files=dict(hero="../hero-HW.png", default_frame="../default-frame-m0w.png", checks="../checks-m0w.json", sheet="../qa-sheet-m0w.jpg", jobs="../jobs-hero.json", tools="../tools/"))
json.dump(man, open(os.path.join(D, "layers", "manifest.json"), "w"), indent=1, ensure_ascii=False)
# ---- assets/manifest.json (re-read, then append or replace by id)
mp = os.path.join(L.REPO, "assets/manifest.json")
M = json.load(open(mp))
ids = {a["id"]: i for i, a in enumerate(M["assets"])}
def put(aid, rel, kind, model, tokens=0, status=None):
    p = os.path.join(L.REPO, rel)
    e = dict(id=aid, path=rel, kind=kind, room="living-room", style="warm-modern", created="2026-11-26", model=model, recipe=REL + "/tools/ (README.md)", tokens=tokens,
             status=status or "FB13 stage A, M0-W default stack: not QA'd, HD_PUBLIC=0 only", prompts="assets/prompts/warm-modern-fb13-2026-11-25/wm-fb13-stage-a-hero.json",
             sha256=sha(p), bytes=os.path.getsize(p))
    if aid in ids:
        M["assets"][ids[aid]] = e
    else:
        ids[aid] = len(M["assets"])
        M["assets"].append(e)
put("wm-m0w-plate-pw", REL + "/plate-PW.png", "plate: the empty room (sofa, armchair), the calm winter sun, no lamps; graded, finished; the base of the stack, 2720 x 1530", "seedream-5-pro i2i 2K + code", 1300)
put("wm-m0w-hero-hw", REL + "/hero-HW.png", "hero: every default product in one light (one render, two group edits, the prints in code), graded, 2720 x 1530; the truth the layers are cut from", "seedream-5-pro i2i 2K + nano-banana-2 2K edits + code", 1850)
put("wm-m0w-default-frame", REL + "/default-frame-m0w.png", "default frame rebuilt from the layers, 1920 x 1080", "code (0 tokens)")
put("wm-m0w-qa-sheet", REL + "/qa-sheet-m0w.jpg", "QA sheet: x1, x2 crops, old M0 beside new", "code (0 tokens)")
put("wm-m0w-layers-manifest", REL + "/layers/manifest.json", "the layers' manifest of M0-W (v2 form)", "code (0 tokens)")
for m in parts["layers"]:
    put(f"wm-m0w-layer-{m['slot']}", REL + "/" + m["layer"], f"product layer (straight alpha, 2720 x 1530): {m['slot']} / {m['product']}", "cut from hero-HW.png in code")
    put(f"wm-m0w-shadow-{m['slot']}", REL + "/" + m["shadow"], f"shadow layer (multiply): {m['slot']}", "the hero over the plate, in code")
for m in parts["light"]:
    put(f"wm-m0w-light-{m['lamps'][0]}", REL + "/" + m["file"], f"light layer (screen): {m['lamps'][0]}", "the hero over the plate, in code")
json.dump(M, open(mp, "w"), indent=1, ensure_ascii=False)
# the band edge's softness on the plate (10-90 % width of the sun patch's left edge, rows 600-800 of the canvas)
P = L.to_lab(L.rd(os.path.join(D, "plate-PW.png")))[..., 0]
prof = cv2.GaussianBlur(P[600:800, 880:1020].mean(0).reshape(1, -1), (0, 0), 1.0).ravel()
lo, hi = prof.min(), prof.max()
xs = np.arange(len(prof))
w = float(np.abs(np.interp(lo + 0.9 * (hi - lo), prof if prof[-1] > prof[0] else prof[::-1], xs) - np.interp(lo + 0.1 * (hi - lo), prof if prof[-1] > prof[0] else prof[::-1], xs)))
print("sun edge 10-90 % width px", round(w, 1), "L", round(float(lo), 1), "->", round(float(hi), 1))
print("assets", len(M["assets"]), "manifest layers", len(man["layers"]))
