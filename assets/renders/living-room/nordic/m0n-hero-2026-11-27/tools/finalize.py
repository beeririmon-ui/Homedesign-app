#!/usr/bin/env python3
"""finalize.py: the M0-N stack into the repo, with the shared finish (render-agent, 2026-11-27). 0 tokens.
  python3 finalize.py <scratch>
From <scratch>/stack (split.py) and the graded hero: bakes the shared finish's grain (assets/renders/tools/finish/finish.py
grain_field, seed 1540, 0.6 px, 1.4 levels midtone-weighted) and a 0.15-stop vignette (G1.9; as M0-W) into the plate and every layer
(both are functions of the canvas position only, so every combination composes the same); shadows and lights are not baked. Writes
plate-PN.png, hero-HN.png, layers/<slot>/<product>.png, shadows/<slot>/<product>.png, light/<product>.png, layers/manifest.json,
default-frame-m0n.png (1920 x 1080, composed from the files), checks-m0n.json (RND2) and qa-sheet-m0n.jpg."""
import hashlib
import importlib.util
import json
import os
import shutil
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(OUT, "..", "..", "..", "..", ".."))
spec = importlib.util.spec_from_file_location("finish", os.path.join(REPO, "assets/renders/tools/finish/finish.py"))
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import split  # noqa: E402

PRODUCT = {"curtains": "curtains-cj-japanese-linen-half-shade", "framed-art": "framed-art-cj-morandi-triptych-sage",
           "wall-decor": "wall-decor-aliexpress-natural-raffia-woven-bohemian-763597", "accent-sconces": "accent-sconces-aliexpress-indoor-stone-wall-lamp",
           "vase": "vase-cj-textured-white-stoneware", "rug": "rug-cj-braided-wool-natural", "floor-lamp": "floor-lamp-cj-black-drum-linen",
           "planter": "planter-cj-seagrass-belly", "sofa-cover": "sofa-cover-cj-cotton-muslin-fringe", "cushions": "set-A",
           "coffee-table": "coffee-table-idana-javorina-olia-natural", "basket": "basket-cj-jute-rope-cylinder",
           "magazine-holder": "magazine-holder-cj-felt-log-basket", "table-runner": "table-runner-cj-linen-look-sage-fringe",
           "tray": "pool-cj-travertine-organic-tray-24", "bowl": "bowl-cj-speckled-ivory-wide-bowl-21",
           "candle-holders": "candle-holders-cj-travertine-pedestal", "pouf": "pouf-cj-cotton-knit-ball-cover", "pendant": "pendant-cj-pleated-pumpkin-lantern-40"}
NOTE = {"cushions": "set A: cushions-cj-boucle-teddy (white, 50), cushions-cj-knitted-chenille-bean-green (45), cushions-cj-linen-look-charcoal (50; E1 edit)",
        "planter": "with the olive (filler); the wall seen between its branches comes with the layer",
        "vase": "with the eucalyptus stems (filler), on the window seat", "candle-holders": "with the two pillar candles (filler, 10 and 15, not lit: E1 edit)",
        "magazine-holder": "with plain folded paper (filler, no print: E2 edit)", "framed-art": "the three style-D prints inserted in code from the in-room SKU photo (prints.py), lit by the canvas the model drew",
        "curtains": "slot/engine rendered default (ch.7 had curtains-aliexpress-cotton-linen-curtain-look-902882)",
        "floor-lamp": "slot/engine rendered default, 'test only, not approved for sale' in the slot file (ch.7 had the wabi-sabi 217361)",
        "rug": "the table's and the throw's shadows on it are baked in the rug layer (they are product-on-product)",
        "pouf": "mask = the clay silhouette (grok gave no pouf segment)", "tray": "new slot (ch.7)", "coffee-table": "new slot (ch.7, FB12-T): not for sale until IDANA confirms in writing"}
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def finish_fields(h, w):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rho = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)) / np.sqrt(2.0)
    vig = (2.0 ** (-0.15 * np.clip(rho, 0, 1.15) ** 2.4)).astype(np.float32)
    g = F.grain_field((h, w), seed=1540, sigma_px=0.6)
    return vig, g


def bake(rgb8, vig, g):
    x = rgb8.astype(np.float32) / 255
    lin = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4) * vig[..., None]
    s = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
    y = s.mean(-1, keepdims=True)
    s = s * 255 + (1.4 * 4 * y * (1 - y)) * g[..., None]
    return np.clip(np.rint(s), 0, 255).astype(np.uint8)


def main(scr):
    st = os.path.join(scr, "stack")
    base8 = np.asarray(Image.open(os.path.join(st, "plate-registered.png")).convert("RGB"))
    h, w = base8.shape[:2]
    vig, g = finish_fields(h, w)
    Image.fromarray(bake(base8, vig, g)).save(os.path.join(OUT, "plate-PN.png"), optimize=True)
    shutil.copy(os.path.join(scr, "hn-graded.png"), os.path.join(OUT, "hero-HN.png"))
    srec = json.load(open(os.path.join(st, "split.json")))
    layers = []
    for k, z in split.ORDER:
        pid = PRODUCT[k]
        L = np.asarray(Image.open(os.path.join(st, "layers", k, "layer.png")).convert("RGBA")).copy()
        L[..., :3] = bake(L[..., :3], vig, g)
        L[L[..., 3] == 0] = 0
        for sub in ("layers", "shadows"):
            os.makedirs(os.path.join(OUT, sub, k), exist_ok=True)
        Image.fromarray(L).save(os.path.join(OUT, "layers", k, f"{pid}.png"), optimize=True)
        shutil.copy(os.path.join(st, "shadows", k, "shadow.png"), os.path.join(OUT, "shadows", k, f"{pid}.png"))
        ys, xs = np.nonzero(L[..., 3] > 0)
        layers.append(dict(slot=k, product=pid, z=z, shadow_z=z - 1, default=True, layer=f"layers/{k}/{pid}.png", shadow=f"shadows/{k}/{pid}.png",
                           sold=k != "coffee-table", source="hero-HN.png cut in code (tools/masks.py + split.py)", note=NOTE.get(k, ""),
                           alpha_px=srec["layers"][k]["alpha_px"], shadow_px=srec["layers"][k]["shadow_px"],
                           bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]))
    os.makedirs(os.path.join(OUT, "light"), exist_ok=True)
    lights = []
    for k in split.LAMPS:
        shutil.copy(os.path.join(st, "light", f"{k}.png"), os.path.join(OUT, "light", f"{PRODUCT[k]}.png"))
        lights.append(dict(file=f"light/{PRODUCT[k]}.png", z=90, blend="screen", lamps=[k], px=srec["lights"][k]["px"], reach_px=srec["lights"][k]["reach_px"]))
    # compose from the repo files (the manifest's formula)
    order = [(e["slot"], e["z"]) for e in layers]
    swap = {e["slot"]: (os.path.join(OUT, e["layer"]), os.path.join(OUT, e["shadow"])) for e in layers}
    lamp_files = {k: os.path.join(OUT, "light", f"{PRODUCT[k]}.png") for k in split.LAMPS}

    def comp(sw):
        B = np.asarray(Image.open(os.path.join(OUT, "plate-PN.png")).convert("RGB")).astype(np.float32) / 255
        acc, aa = B.copy(), np.zeros((h, w), np.float32)
        for k, _ in order:
            lp, sp = sw[k]
            if lp is None:
                continue
            acc = acc * (np.asarray(Image.open(sp).convert("RGB")).astype(np.float32) / 255)
            Lr = np.asarray(Image.open(lp).convert("RGBA")).astype(np.float32) / 255
            acc = acc * (1 - Lr[..., 3:4]) + Lr[..., :3] * Lr[..., 3:4]
            aa = 1 - (1 - aa) * (1 - Lr[..., 3])
        for k in split.LAMPS:
            Lg = np.asarray(Image.open(lamp_files[k]).convert("RGB")).astype(np.float32) / 255 * (1 - aa)[..., None]
            acc = 1 - (1 - acc) * (1 - Lg)
        return np.clip(np.rint(acc * 255), 0, 255).astype(np.uint8)

    full = comp(swap)
    frame = cv2.resize(full, (1920, 1080), interpolation=cv2.INTER_AREA)
    Image.fromarray(frame).save(os.path.join(OUT, "default-frame-m0n.png"), optimize=True)
    # RND2: hiding one product changes only its own region (its layer, its shadow and the lamps' reach under its alpha)
    rnd2 = {}
    for k in ("bowl", "pouf", "framed-art"):
        sw = dict(swap)
        sw[k] = (None, None)
        c2 = comp(sw)
        ch = np.abs(c2.astype(int) - full.astype(int)).max(-1) > 0
        e = next(x for x in layers if x["slot"] == k)
        reg = (np.asarray(Image.open(os.path.join(OUT, e["layer"])))[..., 3] > 0) | (np.asarray(Image.open(os.path.join(OUT, e["shadow"]))).min(-1) < 255)
        reg = split.dil(reg, 1)
        rnd2[k] = dict(changed_px=int(ch.sum()), changed_outside_its_region_px=int((ch & ~reg).sum()))
    hero = np.asarray(Image.open(os.path.join(OUT, "hero-HN.png")).convert("RGB")).astype(int)
    d = np.abs(full.astype(int) - hero).max(-1)
    top = np.zeros((h, w), bool)
    for e in layers:
        top |= np.asarray(Image.open(os.path.join(OUT, e["layer"])))[..., 3] == 255
    checks = dict(rnd2_hide_one=rnd2, stack_vs_hero=dict(mean=round(float(d.mean()), 2), product_px_mean=round(float(d[top].mean()), 2),
                  note="the products are the hero's pixels + the finish (grain, 0.15 stop vignette); the room between them is the plate in the hero's light"),
                  registration_plate_to_hero=srec["registration"])
    man = dict(id="nordic-living-room-m0n-2026-11-27", room="living-room", style="nordic", frame="M0-N", canvas=[w, h], frame_box=[0, 0, w, h],
               base="../plate-PN.png", camera=dict(loc=[0.60, 5.35, 1.00], yaw=8.0, lens=28.0, u0=0.5, v0=0.5, status="PROPOSAL (fb23 camera-m0n-proposal.json)"),
               compose="../plate-PN.png; per layer in z order: shadow (multiply), then the layer (straight alpha); lights (screen, z 90) times (1 - every alpha)",
               status="M0-N hero (brief nordic-m0n-hero-2026-11-27, FB24). Not QA'd; HD_PUBLIC=0 only.",
               method="clay v2 (tools/clay_m0n_v2.py) -> P-N seedream 2K -> H-N seedream 2K (9 refs) -> E1, E2 nano 2K group edits -> prints in code -> grade.py -> grok segment map (0) + masks.py -> split.py -> finalize.py (shared finish grain, 0.15 stop vignette)",
               grade=dict(file="tools/grade.py", xs=[0.0, 4.5, 25.0, 50.0, 69.0, 87.0, 96.0, 100.0], ys=[7.0, 10.5, 27.5, 49.0, 66.5, 86.5, 95.5, 99.0], a_shift=1.6, b_shift=4.5),
               layers=layers, light=lights, influence_radius_px=split.RADIUS, not_in_frame=["wall-sconce (its light only: on the armchair, in the hero)"],
               fillers=["olive (planter)", "eucalyptus stems (vase)", "pillar candles 10 and 15, not lit (candle-holders)", "plain folded paper (magazine-holder)"],
               files=dict(hero="../hero-HN.png", plate="../plate-PN.png", default_frame="../default-frame-m0n.png", checks="../checks-m0n.json", sheet="../qa-sheet-m0n.jpg", jobs="../jobs-m0n.json"))
    json.dump(man, open(os.path.join(OUT, "layers", "manifest.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(checks, open(os.path.join(OUT, "checks-m0n.json"), "w"), indent=1)
    # QA sheet: the magazine frame next to the new tour frame (x1), then x2 crops and the plate
    mag = Image.open(os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06/nordic-A-fin2.png")).convert("RGB").resize((1280, 720), Image.LANCZOS)
    new = Image.fromarray(frame).resize((1280, 720), Image.LANCZOS)
    S = Image.new("RGB", (2600, 720 + 60 + 560 + 60 + 420 + 40), (246, 244, 240))
    dr = ImageDraw.Draw(S)
    try:
        fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    except OSError:
        fnt = ImageFont.load_default()
    S.paste(mag, (13, 50))
    S.paste(new, (1307, 50))
    dr.text((13, 12), "the approved magazine frame (nordic-A-fin2.png)", fill=(40, 40, 40), font=fnt)
    dr.text((1307, 12), "M0-N, the new tour frame (default-frame-m0n.png, from the layers)", fill=(40, 40, 40), font=fnt)
    crops = [((1480, 760, 2120, 1240), "x2 table group (E1)"), ((640, 1150, 1180, 1530), "x2 holder (E2)"), ((1150, 400, 1880, 760), "x2 prints (code)"),
             ((1880, 300, 2560, 1260), "x1 floor lamp, basket")]
    x = 13
    y0 = 720 + 60 + 50
    for (box, lab) in crops:
        c = Image.fromarray(full).crop(box)
        c.thumbnail((640, 520), Image.LANCZOS)
        S.paste(c, (x, y0))
        dr.text((x, y0 - 34), lab, fill=(40, 40, 40), font=fnt)
        x += c.width + 14
    pl = Image.open(os.path.join(OUT, "plate-PN.png")).convert("RGB").resize((640, 360), Image.LANCZOS)
    y1 = y0 + 520 + 60
    S.paste(pl, (13, y1))
    dr.text((13, y1 - 34), "P-N, the plate (base of the stack)", fill=(40, 40, 40), font=fnt)
    hr = Image.open(os.path.join(OUT, "hero-HN.png")).convert("RGB").resize((640, 360), Image.LANCZOS)
    S.paste(hr, (667, y1))
    dr.text((667, y1 - 34), "H-N, the hero (graded, edits, prints)", fill=(40, 40, 40), font=fnt)
    S = S.crop((0, 0, 2600, y1 + 380))
    S.save(os.path.join(OUT, "qa-sheet-m0n.jpg"), quality=88)
    print(json.dumps(checks))


if __name__ == "__main__":
    main(sys.argv[1])
