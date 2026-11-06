#!/usr/bin/env python3
"""
style_previews.py: five style previews of the living room at M0 1.2 (briefs/render-style-previews-2026-11-06.md with
docs/style-previews-2026-11-06.md; decisions STY1, STY2; render-agent, 2026-11-06). A TEST only: nothing here goes to the site, the slot
layers or QA'd assets. One seedream-5-pro image-to-image pass per style (650 each, 3,250 at most, no reserve) on the round-5b clay with a
proxy in every in-frame slot (house plan 1.2.5). Supplier images are passed by URL only, never saved in the repo.
  clay      the base: round-5b M0 clay + 17 slot proxies (the products-pass reference 2 r2 + the planter with its olive tree, the triptych's
            three frames, the wall round; japandi: the wall round off) -> style-previews-2026-11-06/clay-17-slots.png (+ -japandi.png)
  prompts   assets/prompts/style-previews-2026-11-06/<style>.txt
  fetch <style> <url>   raw -> <style>-raw.png (canvas 2736 x 1539), lock_v2, the shell lock, the floor patch dE against the Nordic frame
  grade <style>         grading v6 adapted (grade_v6_m0.py's chain, the style's wall target and white balance) -> <style>-graded.png
  sheet                 contact-sheet.png (3 x 2: Nordic, warm modern, boho / japandi, Mediterranean, modern country), report.json
"""
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m0_products_pass as PP  # noqa: E402

REPO = PP.REPO
DATE = "2026-11-06"
OD_REL = "assets/renders/living-room/style-previews-2026-11-06/"
OD = os.path.join(REPO, OD_REL)
DL = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/dl-styles/"
STYLES = ["warm-modern", "boho", "japandi", "mediterranean", "modern-country"]
NAMES = {"warm-modern": "warm modern", "boho": "boho", "japandi": "japandi", "mediterranean": "Mediterranean", "modern-country": "modern country"}
REFS = {"warm-modern": ["https://ae01.alicdn.com/kf/S10d0636d85e5451e9a3d169fff6378f5F.jpg", "https://ae01.alicdn.com/kf/S2d1e17ab3231455d8a8f4887ab14385bL.jpg",
                        "https://oss-cf.cjdropshipping.com/product/2024/12/18/12/e4e7068f-30f1-45b6-9c55-94b11028ae7d_trans.jpeg",
                        "https://cf.cjdropshipping.com/quick/product/635be4cd-9b07-4238-bb0f-e709154b4740.jpg", "https://cf.cjdropshipping.com/quick/product/558bb2f9-874e-45ce-9e69-c92b69ec061b.jpg"],
        "boho": ["https://ae01.alicdn.com/kf/S03bee60876b4459faeb2167e220265833.jpg", "https://ae01.alicdn.com/kf/S2d7a3e8af13b4d0cbdccb856effde73bW.jpg",
                 "https://file.zendrop.com/products/83/7e/a75cb5e948b7b3280683b19ab275_import.webp", "https://cf.cjdropshipping.com/quick/product/402a7e02-8541-471e-b8f3-ff673f869a3d.jpg",
                 "https://ae01.alicdn.com/kf/S78bd15642a1148c3a52d67daadde117fR.jpg"],
        "japandi": ["https://ae01.alicdn.com/kf/Sb1be1732de90438e845c9c7a7c4f0e51a.jpg", "https://cf.cjdropshipping.com/quick/product/82e47b21-45f9-4973-b808-e93df5a70283.jpg",
                    "https://oss-cf.cjdropshipping.com/product/2026/01/13/02/497c2dc1-c03b-4108-a49b-eb1fc2b2330a_trans.jpeg", "https://ae01.alicdn.com/kf/S2d1e17ab3231455d8a8f4887ab14385bL.jpg",
                    "https://ae01.alicdn.com/kf/S933d194167a24cfa9480d1d58b8cb6252.jpg"],
        "mediterranean": ["https://ae01.alicdn.com/kf/S7b598ab9cc354d58b90c5459bf0cde21I.jpg", "https://cf.cjdropshipping.com/c7ad75db-6cfb-418f-8e6f-70efac5d77c9.jpg",
                          "https://ae01.alicdn.com/kf/S55561bdb1c504f3b83d801383fcfaec73.jpg", "https://cf.cjdropshipping.com/quick/product/402a7e02-8541-471e-b8f3-ff673f869a3d.jpg",
                          "https://file.zendrop.com/products/83/7e/a75cb5e948b7b3280683b19ab275_import.webp"],
        "modern-country": ["https://ae01.alicdn.com/kf/S41cc0edc5846434bb204687ac3813130K.jpg", "https://ae01.alicdn.com/kf/S55561bdb1c504f3b83d801383fcfaec73.jpg",
                           "https://cf.cjdropshipping.com/quick/product/2736eed6-7f8e-49d7-8652-d9e719a72430.jpg", "https://cf.cjdropshipping.com/quick/product/7b0ee726-ee08-48bc-bc82-1e04156ec05a.jpg",
                           "https://file.zendrop.com/products/83/7e/a75cb5e948b7b3280683b19ab275_import.webp"]}
REF_CARDS = {"warm-modern": ["framed-art-aliexpress-frameless-minimalist-wall-art-631735", "accent-sconces-aliexpress-travertine-cylinder-walnut-choice",
                             "floor-lamp-cj-pleated-walnut-stem-158", "cushions-cj-boucle-teddy (White)", "pendant-cj-tiered-fabric-drum"],
             "boho": ["wall-decor-aliexpress-natural-raffia-woven-bohemian-763597", "wall-sconce-aliexpress-rattan-bamboo-wall-lamp-671943",
                      "planter-zendrop-seagrass-belly-basket-45", "cushions-cj-washed-cotton-frayed (Rust Orange)", "table-runner-aliexpress-boho-macrame-table-runners-263532"],
             "japandi": ["framed-art-aliexpress-japanese-wabi-sabi-tree-176323", "vase-cj-black-matte-stoneware-jar-30", "pendant-cj-pleated-pumpkin-lantern-40",
                         "accent-sconces-aliexpress-travertine-cylinder-walnut-choice", "candle-holders-aliexpress-matte-black-iron-pillar-set2"],
             "mediterranean": ["framed-art-aliexpress-mediterranean-wabi-sabi-poster-802890", "magazine-holder-cj-arch-iron-cane", "vase-aliexpress-vintage-distressed-clay-vase-589009",
                               "cushions-cj-washed-cotton-frayed (Earthy Orange)", "basket-zendrop-seagrass-belly-38x34"],
             "modern-country": ["cushions-aliexpress-farmhouse-floral-pillow-covers-166217", "vase-aliexpress-vintage-distressed-clay-vase-589009",
                                "table-runner-cj-linen-look-sage-fringe (4 Light Green)", "bowl-cj-speckled-ivory-wide-bowl-21", "basket-zendrop-seagrass-belly-38x34"]}
# the brief's grading table (test values): white balance (STY2: 4400 K in boho, Mediterranean, modern country), the wall target by the corner
GRADE = {"warm-modern": dict(kelvin=4600, wall=(88, 92)), "boho": dict(kelvin=4400, wall=(87, 92)), "japandi": dict(kelvin=4600, wall=(88, 92)),
         "mediterranean": dict(kelvin=4400, wall=(89, 93)), "modern-country": dict(kelvin=4400, wall=(89, 93))}
SHELL_BLOCK = ("The attached clay render IS the camera and the layout. Turn it into a real photograph without moving the camera: same position, same 24 mm lens, "
               "same horizon, same perspective, same framing. Every architectural line stays exactly where it is in the clay (x, y are fractions of the image "
               "from the top-left): the back wall's floor line runs from (0.40, 0.75) to (0.95, 0.86), its skirting top from (0.40, 0.72) to (0.95, 0.81); the "
               "cornice of the back wall from (0.47, 0.13) to (0.74, 0.06); the room corner is the vertical line at x 0.37; the window spans x 0.06-0.30 in the "
               "left wall, its sill top from (0.13, 0.65) to (0.28, 0.61). Keep every furniture block and every grey object block where and as large as the clay "
               "shows it: each block is one object of the room. Never enlarge anything. The floor stays wide whitened oak planks #D6BF9E. The window view: "
               "bare winter birches, pale sky, no snow, no sun.")
COMMON = ("Restyle this living room as a {STYLE} interior. Keep the camera, the walls, the window, the floor, every piece of furniture and every object "
          "position exactly as in the clay layout. Change only materials, colours and the small objects listed. Winter afternoon daylight from the left "
          "window, soft, no sun. All lamps on, warm 2700 K: the pendant, the two wall lights and the floor lamp right of the sofa; no visible cast shadow "
          "from the lamps. Matte materials. No text, no people. No new furniture, no arched window, no rounded sofa arms.")
STYLE_TEXT = {
    "warm-modern": ("Bone limewash walls #ECE5DA with soft trowel movement; window frame dark bronze. Sofa upholstered in greige boucle, walnut coffee table, "
                    "armchair with walnut frame and bone boucle cushions. Travertine cylinder wall lights on walnut plates glowing up and down beside an abstract "
                    "triptych in walnut frames with an espresso line. Tonal cushions bone, milk-tea and camel, flax muslin throw on the right arm. Ribbed concrete "
                    "planter with an olive tree, textured white stoneware vase with a dry olive branch on the sill, natural braided wool rug, jute rope basket, "
                    "leather-strap magazine holder, black matte bowl and travertine candle holders on the bare walnut table (no runner), tiered fabric drum "
                    "pendant, walnut floor lamp with pleated shade, round greige boucle pouf. Plaster relief disc on the wall."),
    "boho": ("Chalk-cream walls #F0E7D8. Oat linen-look curtains with small tassels puddling on the floor. Earth-tone abstract triptych (arch, sun, organic "
             "shape in terracotta, sand and olive) in wood frames; raffia sun on the wall; woven bamboo ball wall lights. Washed hemp throw in raw jute draped "
             "over the sofa, rust frayed cotton cushions and an olive lumbar cushion. Seagrass belly basket with a bird-of-paradise plant and a second "
             "seagrass belly basket beside it. Flat-woven kilim rug in sand with rust diamonds. Macrame-and-jute runner, mango-wood bowl and aged-brass candle "
             "holders on the oak table. Woven rattan dome pendant and a rattan-shade floor lamp with an inner diffuser, glowing without patterned shadows. "
             "Natural knit pouf, rattan magazine basket, clay vase with dried pampas on the sill."),
    "japandi": ("Washi-paper walls #EFE9DF. Sofa in raw linen, armchair frame in smoked walnut with stone linen cushions. Wabi-sabi tree triptych in thin "
                "matte black frames; the wall to the left is intentionally bare. Travertine cylinder wall lights on walnut plates. Black matte stoneware jar "
                "with one branch on the sill. Pleated paper lantern pendant, a low paper column floor lantern on a dark wooden tripod. Ink clay planter with an "
                "olive tree, seagrass belly basket, light-wood folding magazine stand. On the bare oak table (no runner) only a black matte bowl and two low "
                "black iron plates with pillar candles. Cushions: one moss frayed cotton, one ink linen-look, a beige gauze quilt folded in a straight line. "
                "Cream tone-on-tone striped low-pile rug, round raw-linen pouf. Restraint and empty space."),
    "mediterranean": ("Warm limewash walls #F1EBE0 with visible trowel movement in the raking window light. Sand linen curtains. Triptych of limewashed "
                      "walls, olive branches, jars and an arch in thin oak frames; the wall to the left is bare. Travertine block wall lights. Clay vase with "
                      "olive branches on the sill. Sand linen loosely draped over the sofa, cushions in white, terracotta and moss with a muslin throw. "
                      "Terracotta pot with an olive tree, seagrass belly basket, arched iron magazine holder with cane mesh. Beige linen-look runner, speckled "
                      "ivory bowl and travertine candle holders on the oak table. Woven cane dome pendant with a linen lining, a thin black floor lamp with a "
                      "linen drum shade, a sand linen pouf, natural braided wool rug. No blue."),
    "modern-country": ("Warm milk walls #F3ECDF. Triptych of vintage oil landscapes in thin walnut frames with ivory mats. Small antique-brass wall lights "
                       "with pleated shades; a woven wicker wall basket. Natural washed linen draped over the sofa with a small ruffled edge, block-print "
                       "floral cushions in sage and clay rose, a tone-on-tone check cushion; armchair with honey-oak frame and plain natural linen cushions; "
                       "honey-oak coffee table with a sage linen runner, a speckled ivory bowl and antique-brass chamberstick candle holders with lit taper "
                       "candles. Clay vase with garden stems on the sill. Terracotta pot with an olive tree, one seagrass belly basket, a wicker magazine "
                       "basket, a piped linen pouf. Vintage-wash wool rug in cream, sage and faded rose. Pleated fabric pendant with a brass neck, "
                       "antique-brass floor lamp with a pleated empire shade.")}
NORDIC_RAW = os.path.join(REPO, "assets/renders/living-room/nordic/v9/m0-1-2-products-fix.png")
FLOOR_PATCH = (0.41, 0.46, 0.765, 0.785)          # canvas uv: the free floor between the rug and the window wall, right of the basket


def prompt(style):
    return SHELL_BLOCK + "\n\n" + COMMON.replace("{STYLE}", NAMES[style]) + "\n\n" + STYLE_TEXT[style] + \
        "\n\nThe five product photos attached show the exact items to use for the art, the wall lights, the lamps, cushions, runner, vase, basket or planter they name: match their form, colour and material."


def write_prompts():
    pd = os.path.join(REPO, "assets/prompts/style-previews-2026-11-06")
    os.makedirs(pd, exist_ok=True)
    for st in STYLES:
        p = prompt(st)
        hdr = (f"# {st}: style preview of the living room, M0 1.2 (briefs/render-style-previews-2026-11-06.md, STY1 / STY2; render-agent {DATE}). TEST only.\n"
               f"# Model: seedream-5-pro, image-to-image, 2K, aspect_ratio auto, 650 tokens. image_url: {OD_REL}clay-17-slots{'-japandi' if st == 'japandi' else ''}.png\n"
               f"# image_refs (5, by URL, never saved): " + ", ".join(REF_CARDS[st]) + "\n# Strip every # line before sending. Body " + str(len(p)) + " characters.\n\n")
        open(os.path.join(pd, st + ".txt"), "w").write(hdr + p + "\n")
        print(st, len(p))


# ---------------------------------------------------------------------------------------------------------------
# the base clay with 17 slot proxies
# ---------------------------------------------------------------------------------------------------------------
def extra_proxies(with_round=True):
    F = {}
    pot = PP.cyl_faces((-2.00, 0.47), 0.20, 0.0, 0.42, 0.55)
    trunk = PP.cyl_faces((-2.00, 0.47), 0.025, 0.42, 1.05, 0.40)
    canopy = PP.ellipsoid_faces((-2.00, 0.47), 0.33, 0.40, 1.40, 0.62)
    F["planter"] = pot + trunk + canopy
    art = []
    import art_m0_12 as A
    for (X0, X1, Z0, Z1) in A.frame_rects():
        art += PP.box_faces(((X0 + X1) / 2, 0.015), (1.0, 0.0), X1 - X0, 0.03, Z1 - Z0, Z0, 0.70)
    F["framed-art"] = art
    if with_round:
        th = [2 * math.pi * i / 48 for i in range(48)]
        F["wall-decor"] = [([np.array([-1.20 + 0.19 * math.cos(t), 0.02, 1.20 + 0.19 * math.sin(t)]) for t in th], 0.60)]
    return F


def clay(with_round=True):
    """reference 2 r2's drawing (m0_products_pass.ref2) with the three extra slots; one depth buffer"""
    base = np.asarray(Image.open(PP.REF2).convert("RGB")).astype(np.float32)          # the clay + the four products-pass proxies
    H, W = base.shape[:2]
    dep = cv2.resize(np.load(PP.DEPTH), (W, H), interpolation=cv2.INTER_NEAREST)
    out = base.copy()
    Ldir = np.array([-0.75, 0.35, 0.55])
    Ldir /= np.linalg.norm(Ldir)
    zall = dep.astype(np.float32).copy()
    rec, covs = {}, {}
    for name, faces in sorted(extra_proxies(with_round).items(), key=lambda kv: -np.mean([PP.proj(p)[2] for poly, _ in kv[1] for p in poly])):
        zbuf = np.full((H, W), np.inf, np.float32)
        layer = np.zeros((H, W, 3), np.float32)
        for poly, grey in faces:
            pr = [PP.proj(p) for p in poly]
            uv = np.array([[(u * 3840 + 116) / 4072 * W, (v * 2160 + 65) / 2290 * H] for u, v, _ in pr])
            d = float(np.mean([q[2] for q in pr]))
            n = np.cross(poly[1] - poly[0], poly[2] - poly[0])
            n = n / (np.linalg.norm(n) + 1e-9)
            camv = np.array(PP.CAM["loc"]) - np.mean(poly, 0)
            if np.dot(n, camv) < 0:
                n = -n
            shade = 0.55 + 0.45 * max(0.0, float(np.dot(n, Ldir)))
            m = np.zeros((H, W), np.uint8)
            cv2.fillPoly(m, [np.round(uv * 4).astype(np.int32)], 1, shift=2)
            tol = 0.12 if name in ("wall-decor", "framed-art") else 0.03         # flat on the receding wall: its depth varies across it
            m = m.astype(bool) & (d < zbuf) & (d < zall + tol)
            zbuf[m] = d
            layer[m] = np.clip(grey * shade, 0, 1) * 255
        cov = np.isfinite(zbuf)
        out[cov] = layer[cov]
        zall[cov] = np.minimum(zall[cov], zbuf[cov])
        covs[name] = cov
        ys, xs = np.nonzero(cov)
        rec[name] = dict(visible_canvas_uv=[round(xs.min() / W, 3), round(xs.max() / W, 3), round(ys.min() / H, 3), round(ys.max() / H, 3)] if cov.any() else None)
    os.makedirs(OD, exist_ok=True)
    p = os.path.join(OD, "clay-17-slots" + ("" if with_round else "-japandi") + ".png")
    Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8)).resize((2736, 1539), Image.LANCZOS).save(p)
    # the object index for grading: the M0 clay index + every added proxy (the four products-pass proxies redrawn here for their masks)
    I = cv2.imread(os.path.join(REPO, "assets/renders/living-room/nordic/v9/m0-clay-r5b-index.png"), cv2.IMREAD_UNCHANGED).astype(np.int32)
    ref2 = np.asarray(Image.open(PP.REF2).convert("RGB")).astype(np.float32)
    clay0 = np.asarray(Image.open(PP.CLAY).convert("RGB")).astype(np.float32)
    prod4 = (np.abs(ref2 - clay0).max(2) > 3)
    ids = {"framed-art": 607, "wall-decor": 608, "planter": 606}
    big = np.zeros((H, W), np.int32)
    big[prod4] = 600
    for k, m in covs.items():
        big[m] = ids[k]
    small = cv2.resize(big.astype(np.uint16), (2736, 1539), interpolation=cv2.INTER_NEAREST).astype(np.int32)
    I = np.where(small > 0, small, I)
    ip = p.replace(".png", "-index.png")
    cv2.imwrite(ip, I.astype(np.uint16))
    cl = json.load(open(os.path.join(REPO, "assets/renders/living-room/nordic/v9/m0-clay-r5b-index.json")))
    for k, v in {600: "products-pass proxies (holder, basket, floor lamp, pouf)", 606: "planter + olive tree", 607: "triptych frames", 608: "wall round"}.items():
        cl["classes"][str(k)] = dict(name=v, kind="product", registry="style_previews.py proxy")
    cl["what"] = "the M0 clay index + the style clay's added proxies (style_previews.py)"
    json.dump(cl, open(ip.replace(".png", ".json"), "w"), indent=1)
    return p, rec


def make_clays():
    p1, r1 = clay(True)
    p2, r2 = clay(False)
    json.dump(dict(what="the style previews' base: the round-5b M0 clay + a proxy in every in-frame slot (house plan 1.2.5): the 11 clay placeholders, the "
                        "products-pass proxies (holder at (-0.54, 2.52), basket, floor lamp, pouf), the planter with its olive tree at (-2.00, 0.47), the "
                        "triptych's three 50 x 70 frames at (0.20, 1.475), the wall round at (-1.20, 1.20) (japandi: off); 2736 x 1539",
                   date=DATE, with_round=r1, japandi=r2, outputs=[os.path.relpath(p1, REPO), os.path.relpath(p2, REPO)],
                   note="the runner placeholder of the clay stays (the clay draws it as a flat slab on the table); warm modern and japandi: 'no runner' in the prompt"),
              open(os.path.join(OD, "clay-17-slots.json"), "w"), indent=1)
    print(p1, p2, json.dumps(r1))




# ---------------------------------------------------------------------------------------------------------------
# after the passes (0 tokens)
# ---------------------------------------------------------------------------------------------------------------
JOBS = {"warm-modern": ("06bffa3b-40bd-4034-b89b-b66a09dd9572", "seedream5p-6b52e2f39e5925d96a823f7d38d048f6-0-1793993753895-8337aa01.png"),
        "boho": ("7dbd123c-334a-4766-a2f2-7431cfc13ec8", "seedream5p-ec837bf43ae94651589fc4c8f86c56d7-0-1793993765825-0f886d98.png"),
        "japandi": ("a6a4e80a-478c-447e-ac29-a4c429982b3e", "seedream5p-8399b48a4eb632353735b468b441cc79-0-1793993773442-ff12644a.png"),
        "mediterranean": ("11d06c8a-5bf8-470c-a59b-bdbee057f62a", "seedream5p-19d6bfeeef6151b201ae150b3ce783eb-0-1793993773063-da3dae5c.png"),
        "modern-country": ("926b8deb-bdc2-414b-aa15-6fcf239cb51e", "seedream5p-f659367a34ce3032332223148a227238-0-1793993781281-f1f4f931.png")}
URL0 = "https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/"
REPORT = os.path.join(OD, "report.json")
JR = os.path.join(OD, "jobs.json")


def lab_mean(img01, box):
    H, W = img01.shape[:2]
    u0, u1, v0, v1 = box
    p = img01[int(v0 * H):int(v1 * H), int(u0 * W):int(u1 * W)].reshape(-1, 3).mean(0)
    return cv2.cvtColor(p.reshape(1, 1, 3).astype(np.float32), cv2.COLOR_RGB2LAB)[0, 0]


def fetch(style):
    import fix_m0_12 as M
    import shell_lock_m0 as SL
    os.makedirs(DL, exist_ok=True)
    dl = os.path.join(DL, style + ".png")
    if not os.path.exists(dl):
        subprocess.run(["curl", "-sS", "-L", "--max-time", "240", "-o", dl, URL0 + JOBS[style][1]], check=True)
    im0 = Image.open(dl).convert("RGB")
    raw = os.path.join(OD, style + "-raw.png")
    im0.resize((2736, 1539), Image.LANCZOS).save(raw)
    PL = M._pipeline()
    jid = "style-" + style
    PL.VF.RETAKES[jid] = PL.JOBS["m0-v8b"]
    J = json.load(open(JR)) if os.path.exists(JR) else dict(jobs=[])
    if not any(j["id"] == jid for j in J["jobs"]):
        J["jobs"].append(dict(id=jid, out_dir=OD_REL))
        json.dump(J, open(JR, "w"), indent=1)
    PL.VF.RETAKES_JOBS = JR
    lk = PL.LK.run_frame(jid, render_path=raw, out_path=os.path.join(DL, style + "-lock-v2.json"), overlay_path=os.path.join(OD, style + "-lock-v2.jpg"), date=DATE)
    s, v = lk["summary"], lk["verdict"]
    sh = SL.measure(raw, style)
    a = np.asarray(Image.open(raw)).astype(np.float32) / 255
    nd = np.asarray(Image.open(NORDIC_RAW)).astype(np.float32) / 255
    l1, l2 = lab_mean(a, FLOOR_PATCH), lab_mean(nd, FLOOR_PATCH)
    dE = float(np.linalg.norm(l1 - l2))
    rep = json.load(open(REPORT)) if os.path.exists(REPORT) else dict(date=DATE, brief="briefs/render-style-previews-2026-11-06.md", decision="STY1 / STY2",
                                                                      note="TEST only: not for the site, the slot layers or QA'd assets", styles={})
    rep["styles"][style] = dict(tokens=650, model="seedream-5-pro i2i 2K auto", placeholder_id=JOBS[style][0], url=URL0 + JOBS[style][1],
                                prompt=f"assets/prompts/style-previews-2026-11-06/{style}.txt", reference_urls=REFS[style], reference_cards=REF_CARDS[style],
                                base=OD_REL + "clay-17-slots" + ("-japandi" if style == "japandi" else "") + ".png",
                                lock_v2=dict(shift_px=s["register_shift_px"], scale_pct=s["register_scale_pct"], band_after=s["worst_band_px_after_register"],
                                             tile_after=s["worst_tile_ecc_px_after_register"], fixed_edges_worst_px=s["fixed_edges_worst_px"], fixed_ratios=s["fixed_ratios"],
                                             verdict={k: v[k] for k in ("global_pass", "residual_pass", "edges_pass", "pass")}),
                                lock_brief=dict(shift_le_2=bool(max(abs(x) for x in s["register_shift_px"]) <= 2.0), edges_le_9_6=bool((s["fixed_edges_worst_px"] or 0) <= 9.6)),
                                shell=dict(raw_max_px=sh["raw_max_px"], after_affine_px=sh["global_affine"]["residual_max_px"], per_line=sh["per_line"],
                                           vanishing_point=sh["back_wall_vanishing_point"], verdict=sh["verdict"]),
                                floor_patch=dict(box_canvas_uv=list(FLOOR_PATCH), lab_style=[round(float(x), 2) for x in l1], lab_nordic=[round(float(x), 2) for x in l2],
                                                 dE=round(dE, 2), ok=bool(dE <= 3.0), against=os.path.relpath(NORDIC_RAW, REPO)),
                                raw=OD_REL + style + "-raw.png", lock_overlay=OD_REL + style + "-lock-v2.jpg")
    json.dump(rep, open(REPORT, "w"), indent=1, ensure_ascii=False)
    print(style, json.dumps(dict(lock=rep["styles"][style]["lock_v2"], shell=rep["styles"][style]["shell"]["raw_max_px"], dE=round(dE, 2))))


def grade(style):
    """grading v6 adapted (test values): the v6 chain (grade_v6_m0.py) with the style clay's object index, no code-placed art (the style's own
    art is masked by grabCut and gets the product exposure), the wall targets re-based on the style's wall L (the brief's table: by the corner;
    the centre 1.8 under it, the right end 7.3 under it, as the Nordic Bible fall-off), the window wall 84, the floor patch 72 (the oak), the
    rest at the product +0.2; then the white balance: 4400 K styles warmed from the 4600 K grade (linear gains R 1.025, B 0.96, roll-off again)"""
    import grade_v6_m0 as G
    G.SRC = os.path.join(OD, style + "-raw.png")
    G.INDEX = os.path.join(OD, "clay-17-slots" + ("-japandi" if style == "japandi" else "") + "-index.png")
    G.SP = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/v6-style-" + style + "/"
    os.makedirs(G.SP, exist_ok=True)
    G.HEM_POLY = [(0, 0), (1, 0), (1, 1)]
    G.art_round_masks = lambda H, W: (np.zeros((H, W), bool), np.zeros((H, W), bool))
    G.art_curve = lambda sr, Mk, P: (sr, dict(skipped="no code-placed art in a style preview"))
    a = G.load(G.SRC)
    H, W = a.shape[:2]
    G.masks(a)
    Mk, mrec = G.load_masks()
    X, Z = G.wall_xz(H, W)
    xc, f, prec = G.wall_profile(G.s2l(a), Mk, X, Z)
    lo, hi = GRADE[style]["wall"]
    T = dict(corner=(lo + hi) / 2, centre=(lo + hi) / 2 - 1.8, right=(lo + hi) / 2 - 7.3, window=84.0, floor=72.0)
    P = json.loads(json.dumps(G.P0))
    P.update(rug=0.2, table=0.2, glow=0.5)
    pts = {k: [(u, v) for nm, (u, v), rng, grp in G.WALL_PTS if grp == k] for k in ("corner", "centre", "right", "window")}

    def rd(g):
        out = {k: float(np.mean([G.hsl(G.patch(g, u, v))[2] for u, v in pts[k]])) for k in pts}
        fp = G.boxm(H, W, FLOOR_PATCH)
        out["floor"] = float(np.median(G.Lmap(g)[fp]))
        return out
    hist = []
    for it in range(4):
        g, rec = G.grade(a, Mk, P, X, (xc, f))
        m = rd(g)
        hist.append({k: round(v, 1) for k, v in m.items()})
        print(style, it, hist[-1], flush=True)
        P["wall_ctrl"] = [G.step(m["corner"], T["corner"], P["wall_ctrl"][0]), G.step(m["centre"], T["centre"], P["wall_ctrl"][1]),
                          G.step(m["right"], T["right"], P["wall_ctrl"][2])]
        P["window_wall"] = G.step(m["window"], T["window"], P["window_wall"])
        P["floor"] = float(np.clip(G.step(m["floor"], T["floor"], P["floor"]), -0.5, 1.5))
    g, rec = G.grade(a, Mk, P, X, (xc, f))
    wb = None
    if GRADE[style]["kelvin"] == 4400:
        import process_v8 as PV
        lin = G.s2l(g) * np.array([1.025, 1.0, 0.96])
        g = np.clip(G.l2s(PV.rolloff(lin, 0.94, 0.97)), 0, 1).astype(np.float32)
        wb = "4400 K: linear gains R 1.025, G 1, B 0.96 after the 4600 K grade, roll-off again (approximate, test values)"
    out = os.path.join(OD, style + "-graded.png")
    Image.fromarray((g * 255 + 0.5).astype(np.uint8)).save(out)
    g8 = np.asarray(Image.open(out)).astype(np.float32) / 255
    m = rd(g8)
    L = G.Lmap(g8)
    lamp = (Mk["I"] == 600) & (G.boxm(H, W, (0.80, 1.0, 0.0, 1.0)))
    shade = lamp & (L > np.percentile(L[lamp], 70)) if lamp.any() else lamp
    ys, xs = np.nonzero(lamp) if lamp.any() else (np.array([0]), np.array([0]))
    wall = np.zeros((H, W), bool)
    wall[int(0.36 * H):int(0.42 * H), max(0, xs.min() - 140):max(1, xs.min() - 40)] = True
    wall &= Mk["shell"] > 0.9
    lamp_rec = dict(shade_L=round(float(np.median(L[shade])), 1) if shade.any() else None, wall_L=round(float(np.median(L[wall])), 1) if wall.any() else None)
    if lamp_rec["shade_L"] is not None and lamp_rec["wall_L"] is not None:
        lamp_rec["diff"] = round(lamp_rec["shade_L"] - lamp_rec["wall_L"], 1)
        lamp_rec["ok"] = bool(lamp_rec["diff"] >= 6)
    rep = json.load(open(REPORT))
    rep["styles"][style]["graded"] = dict(path=OD_REL + style + "-graded.png", chain="grade_v6_m0.py (v6) adapted, test values", targets=T, white_balance=wb or "4600 K (shared)",
                                          measured={k: round(v, 1) for k, v in m.items()}, wall_range=[lo, hi], corner_ok=bool(lo <= m["corner"] <= hi),
                                          frame_mean_L=round(float(L.mean()), 1), max_L=round(float(L.max()), 1), floor_lamp=lamp_rec,
                                          params={k: (round(v, 3) if isinstance(v, float) else v) for k, v in P.items() if k in ("wall_ctrl", "window_wall", "floor", "ceiling", "products")},
                                          iterations=hist, not_applied="the brief's black point L 11-14 for warm modern (the v6 toe 12-15 is used); per-style saturation beyond the v6 chroma rules")
    json.dump(rep, open(REPORT, "w"), indent=1, ensure_ascii=False)
    print(style, json.dumps(rep["styles"][style]["graded"]["measured"]), lamp_rec)


def sheet():
    """six frames, 3 x 2, 1368 px each, labelled under the frame; Nordic = the graded v5 M0 1.2 (the products pass has not passed QA yet)"""
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    nordic = os.path.join(REPO, "assets/renders/living-room/nordic/v9/m0-1-2-shell-seedream-graded-fix-v5.png")
    items = [("Nordic (graded v5, the current M0 1.2)", nordic)] + [(NAMES[s_], os.path.join(OD, s_ + "-graded.png")) for s_ in STYLES]
    rep = json.load(open(REPORT))
    w, h = 1368, 770
    out = Image.new("RGB", (3 * w + 40, 2 * (h + 80) + 70), (255, 255, 255))
    d = ImageDraw.Draw(out)
    d.text((10, 18), f"Living room M0 1.2, five style previews ({DATE}, STY1 / STY2): TEST, not for site", fill=(0, 0, 0), font=f)
    for i, (name, path) in enumerate(items):
        im = Image.open(path).convert("RGB")
        W, H = im.size
        im = im.crop((int(round(116 / 4072 * W)), int(round(65 / 2290 * H)), int(round(3956 / 4072 * W)), int(round(2225 / 2290 * H)))).resize((w, h), Image.LANCZOS)
        x, y = 10 + (i % 3) * (w + 10), 70 + (i // 3) * (h + 80)
        out.paste(im, (x, y))
        sub = "TEST, not for site"
        st_ = [k for k, v in NAMES.items() if v == name]
        if st_ and st_[0] in rep["styles"]:
            r = rep["styles"][st_[0]]
            sub += f"   lock_v2 {'pass' if r['lock_v2']['verdict']['pass'] else 'FAIL'}, shell {r['shell']['raw_max_px']} px, floor dE {r['floor_patch']['dE']}"
        d.text((x, y + h + 8), name, fill=(0, 0, 0), font=f)
        d.text((x, y + h + 42), sub, fill=(90, 90, 90), font=fs)
    p = os.path.join(OD, "contact-sheet.png")
    out.save(p)
    rep["contact_sheet"] = OD_REL + "contact-sheet.png"
    json.dump(rep, open(REPORT, "w"), indent=1, ensure_ascii=False)
    print(p)


if __name__ == "__main__":
    w = sys.argv[1]
    if w == "clay":
        make_clays()
    if w == "prompts":
        write_prompts()
    if w == "fetch":
        for st in (sys.argv[2:] or STYLES):
            fetch(st)
    if w == "grade":
        for st in (sys.argv[2:] or STYLES):
            grade(st)
    if w == "sheet":
        sheet()
