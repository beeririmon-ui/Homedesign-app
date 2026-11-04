#!/usr/bin/env python3
"""
gen_m0_v8_prompts.py: the three v8 prompts of briefs/render-m0-new-camera-2026-11-03.md task 3 (render-agent, 2026-11-03; 0 tokens),
written from the round-5 clay's own boxes (framing/round5/selfcheck.json; canvas fractions, as the attached overscan clay), so a clay
re-render after the designer's F3 answer only needs a rerun of this script:
  assets/prompts/recipe-v5.nordic/m0-v8.txt, assets/prompts/poses-v7.nordic/pose-m0p-v8.txt, assets/prompts/poses-v7.nordic/pose-m0x-v8.txt
Recipe v8 (docs/render-recipe-nordic-v8-2026-11-03.md 2.1-2.2): no whole master as a reference; hard cut-outs of the fixed furniture
with sizes and clay u/v in the prompt line; the SCALE paragraph. TR3 test defaults (no snow, no floor lamp, transition-only slots
empty); Bible 1.8.1 light (winter daylight, the two B1 targets; the exposure asked in the prompt, B3, after QA's 2026-11-03 grading
note); product lines in the wow pass order (m0-v7 letters kept). var2 caps the prompt at 4,000 characters: checked here.
  python3 -I gen_m0_v8_prompts.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
R5 = os.path.join(REPO, "assets", "blockout", "house", "framing", "round5")
SC = json.load(open(os.path.join(R5, "selfcheck.json")))["frames"]
CHECKS = "assets/blockout/house/framing/round5/clay-checks-2026-11-03.json"


def B(fid, key):
    return SC[fid]["boxes"][key]["box"]


def f(x):
    return f"{min(max(x, 0.0), 1.0):.2f}"


def span(b, axis="x"):
    return f"{f(b[0])}-{f(b[1])}" if axis == "x" else f"{f(b[2])}-{f(b[3])}"


def canvas_u(u):
    return (u * 3840 + 116) / 4072


def canvas_v(v):
    return (v * 2160 + 65) / 2290


SOFA, TABLE, CHAIR = "sofa 220x92x78 (fixed-product)", "coffee table 140x70 h38 (fixed-product)", "armchair 72x78 h70 (fixed-product)"
BLUEPRINT = ("Use the attached clay render as the exact blueprint. Keep every wall, opening, window, cornice, skirting, floor and ceiling line, the camera, "
             "and the position, size and angle of every furniture piece and built-in exactly as in the clay. Move, resize, add or remove nothing. Each "
             "placeholder shape marks one product below; render it there at the stated size. Only turn the clay into real materials and light. x, y are "
             "fractions of the image from the top-left.")
SCALE_TAIL = ("Furniture is small in this 24 mm frame by design: never enlarge a piece to fill the frame or to match a cut-out; if a piece looks too small, "
              "keep the clay's size.")
LIGHT = ("2. LIGHT. Winter daylight, no sun: soft north light from the left window; outside, bare birches and pale sky, no snow, no buildings. Exposed "
         "bright, for white: the back wall by the corner almost white, just under the glowing window reveals; the window wall in soft shade, a clear "
         "half stop darker than the back wall, never grey. The glass is the brightest, with detail. Long soft shadows right and toward the camera; "
         "dense contact shadows. Real contrast, never milky. "
         "4600 K: walls a clean warm white, never cream, yellow, pink or grey. Lamps 2700 K, low, shadowless: {lamps}")
MATERIALS = ("3. MATERIALS. Matte mineral paint #F4F1EC, faint chalky movement. Wide oiled white-oak planks, pale honey #D6BF9E. Sofa: slubby oatmeal "
             "cotton-linen #E6DCCB, tapered oak legs. Table and armchair frame: oiled oak #C8A27A, satin, a long soft highlight on the "
             "table top. Armchair cushions: mist-grey wool boucle #D9D6D0.")
NOT = ("5. NOT IN FRAME: {extra}floor lamp, wall lamp, basket, plant, pouf, magazines, books, cable, text, people, snow. No sun patches, beams, bloom, "
       "haze, halos, HDR, grain or vignette.")
CUBES_TXT = "two 12 cm cubes of warm honed travertine, open pores, light out of top and bottom"
PEND_TXT = "a flat ribbed warm-white silk lantern, 40 cm, on a thin black cord from the top edge"
RUG_TXT = "white hand-woven flat wool, tone-on-tone diamond weave, fine grey flecks"
CUSH = ["i. CUSHION, sofa left: 50 cm warm-white boucle.", "j. CUSHION before it: 45 cm sage chenille knit.", "k. LUMBAR, right seat: 30 x 50 charcoal linen-look."]


def m0():
    s, t, a = B("M0", SOFA), B("M0", TABLE), B("M0", CHAIR)
    cb, pe, cu = B("M0", "living/accent-sconces"), B("M0", "living/pendant"), B("M0", "living/curtains")
    va, ru, cs, th = B("M0", "living/vase"), B("M0", "living/rug"), B("M0", "living/cushions"), B("M0", "living/sofa-cover")
    rn, ch, bo = B("M0", "living/table-runner"), B("M0", "living/candle-holders"), B("M0", "living/bowl")
    win = (canvas_u(0.034), canvas_u(0.292))
    scale = (f"SCALE: the clay is also the size of everything: the 220 cm sofa spans x {span(s)}, back top y {f(s[2])}, legs at y {f(s[3])}; the 140 x 70 cm "
             f"coffee table spans x {span(t)}, far edge y {f(t[2])}, legs cut by the bottom edge; the 72 cm armchair spans x {f(a[0])}-{f(a[1])} from y "
             f"{f(a[2])} down, cut by the left and bottom edges; the window x {f(win[0])}-{f(win[1])}. " + SCALE_TAIL)
    body = [BLUEPRINT, "", scale, "",
            "1. PHOTO. Top Scandinavian interiors magazine: a Copenhagen living room, 3 pm mid-winter, 24 mm shift lens at 1.2 m, level, straight verticals, "
            "all sharp. Close and generous: the armchair the cut foreground, the low silk pendant glowing over the table.", "",
            "CUT-OUTS. Images 1-3: cut-outs of a photograph of this room from one metre farther back (1 sofa with cushions and throw, 2 coffee table group, "
            "3 armchair): materials, colour, grain and light only, never framing, position or size. Images 4-13: close-ups of the exact products: match form, "
            "colour and texture.", "",
            LIGHT.format(lamps="the pendant glows from inside with a soft pool on the bare table centre; the cubes wash short soft fans up and down the wall."), "",
            MATERIALS, "",
            "4. PRODUCTS, one per line, each on its clay placeholder:",
            f"b. TRAVERTINE CUBES at the two ends of x {span(cb)}, y {span(cb, 'y')}: {CUBES_TXT}.",
            f"c. PENDANT, x {span(pe)}, y {span(pe, 'y')}: {PEND_TXT}.",
            f"d. CURTAINS, x {span(cu)}: sheer natural linen-blend, S-fold, slim black rod, backlit, hems on the floor, front panel cut by the edge.",
            f"e. VASE on the sill, x {span(va)}, y {span(va, 'y')}: a 31 cm cream distressed clay jar, 3-4 eucalyptus stems.",
            f"h. RUG under the table, x {span(ru)} from y {f(ru[2])} down: {RUG_TXT}.",
            *CUSH,
            f"l. THROW over the right arm, x {span(th)}: thin crinkled cream cotton muslin, short frayed fringe.",
            f"m. RUNNER across the table's left third, x {span(rn)}: sage-grey linen-look, fringed ends.",
            f"n. CANDLE HOLDERS, x {span(ch)}: two hand-sized travertine pedestals, unlit candles 15 and 10 cm.",
            f"o. BOWL beside them, x {span(bo)}: 21 cm warm-white matte belly bowl, empty.", "",
            NOT.format(extra="anything on the wall above the sofa but the two cubes (no art, frame, mirror or wall decor), ")]
    head = [
        "# m0-v8: the living room at the M0 1.2.1 camera, recipe v8 (render-agent, 2026-11-03; briefs/render-m0-new-camera-2026-11-03.md task 3). recipe B "
        "(gpt-image-2-5, quality sunburst, 2K, 16:9, image-to-image), one attempt; a second only on a lock_v2 scale failure (the reserve). Generated by "
        "assets/renders/house-nordic-v7-2026-11-02/gen_m0_v8_prompts.py from the round-5 clay boxes. Strip every # line before sending.",
        "# Clay (image_url): assets/blockout/house/framing/round5/M0.png (framing_r5.py + tone_r5_fixed.py: camera (0.83, 4.64, 1.20), yaw 25, 24 mm, u0 0.47, "
        "v0 0.50, house plan 1.2.1; round-4 light and the round-4 M0 post, +1 stop; overscan 3 %, canvas 4072 x 2290: positions are fractions of that canvas). "
        "Placeholders: accent pair, pendant (shade bottom 1.90, V7Q7 b), curtains, vase, rug (Bible test envelope 290 x 240), cushions, throw, runner, holders, bowl.",
        "# References after the clay (13): 1-3 = cut-outs of the old M0 r2 graded v3 (look only; its furniture is 1.16-1.29x the 1.1 clay, so no size): 1 sofa, "
        "2 coffee table group, 3 armchair (refs/index-m0-1-2-2026-11-03.json); 4-13 = the m0-v7 close-ups (refs/index-v7.json frames.M0): cube, pendant, jar, "
        "NYOKO stand-in, boucle cushion, sage knit, muslin throw, sage runner, travertine holders, bowl. No whole master.",
        "# Explicitly empty in the test (V7Q5 b: sourcing tasks): framed-art (RND2: card incomplete: no shipping quote, no retail price, rights unclear), pouf "
        "(no approved product), wall-decor, planter; floor-lamp (TR3); wall-sconce, basket, magazine-holder are transition-only (TR3). Lit: pendant + travertine "
        "pair (2 typologies, TR3 / Bible 1.8.1 S12).",
        "# QA (brief 5): lock_v2 at G1.4 (M0 is a video endpoint of T-E0 and the start of P0: 0.5 % per strip); fixed edges from the clay boxes (sofa, table, "
        "armchair) and ratios 0.95-1.05; products in their clay boxes +-15 %; grading v3 --exposure bible (corner L 92-95 target 93, window wall 80-88, wall "
        "H 32-40 and C* <= 7 after the grade per QA 2026-11-03 §4); window p99 <= 97, zero 255; the forbidden list.",
        f"# Clay checks and the open F3 points (pouf margin, armchair left edge, rug corner, table / sofa sliver): {CHECKS}.",
    ]
    return head, body


def m0p():
    s, t, cb, pe = B("M0p", SOFA), B("M0p", TABLE), B("M0p", "living/accent-sconces"), B("M0p", "living/pendant")
    ru, cs, th = B("M0p", "living/rug"), B("M0p", "living/cushions"), B("M0p", "living/sofa-cover")
    rn, ch, bo = B("M0p", "living/table-runner"), B("M0p", "living/candle-holders"), B("M0p", "living/bowl")
    scale = (f"SCALE: the clay is also the size of everything: the 220 cm sofa spans x {span(s)}, back top y {f(s[2])}, legs at y {f(s[3])}; the 140 x 70 cm "
             f"coffee table spans x {span(t)}, far edge y {f(t[2])}, cut by the bottom edge; the back-right corner and the right wall as the clay draws them. "
             + SCALE_TAIL)
    body = [BLUEPRINT, "", scale, "",
            "1. PHOTO. One frame of a slow pan in the same Copenhagen living room, 3 pm mid-winter, turned to face the sofa wall squarely: 24 mm shift lens at "
            "1.2 m, level, straight verticals, all sharp. The sofa and the glowing pendant on the left half, the bare back-right corner and the right wall on "
            "the right.", "",
            "CUT-OUTS. Images 1-3 are cut-outs of a photograph of this room from the same point, turned 25 degrees to the left: 1 sofa wall with cubes and "
            "pendant, 2 coffee table group, 3 floor, rug edge and skirting at the right. They give materials, colour, grain and light only, never framing, "
            "position or size. Images 4-12 are close-ups of the exact products: match their form, colour and texture.", "",
            LIGHT.format(lamps="the pendant glows from inside with a soft pool on the bare table centre; the cubes wash short soft fans up and down the wall."), "",
            MATERIALS, "",
            "4. PRODUCTS, one per line, each on its clay placeholder:",
            f"b. TRAVERTINE CUBES at the two ends of x {span(cb)}, y {span(cb, 'y')}: {CUBES_TXT}.",
            f"c. PENDANT, x {span(pe)}, y {span(pe, 'y')}: {PEND_TXT}.",
            f"h. RUG under the table, x {span(ru)} from y {f(ru[2])} down: {RUG_TXT}.",
            *CUSH,
            f"l. THROW over the right arm, x {span(th)}: thin crinkled cream cotton muslin, short frayed fringe.",
            f"m. RUNNER across the table's left third, x {span(rn)}: sage-grey linen-look, fringed ends.",
            f"n. CANDLE HOLDERS, x {span(ch)}: two hand-sized travertine pedestals, unlit candles 15 and 10 cm.",
            f"o. BOWL beside them, x {span(bo)}: 21 cm warm-white matte belly bowl, empty.", "",
            NOT.format(extra="anything on the wall above the sofa but the two cubes (no art, frame, mirror or wall decor), anything in the back-right corner, ")]
    head = [
        "# pose-m0p-v8: transition pose M0p (end of P0, T-LD) at the M0 1.2.1 point, recipe v8 (render-agent, 2026-11-03; brief task 3). recipe B, one "
        "attempt, no second attempt in this brief. Generated by gen_m0_v8_prompts.py. Strip every # line before sending.",
        "# Clay (image_url): assets/blockout/house/framing/round5/poses/M0p.png (camera (0.83, 4.64, 1.20), yaw 0, u0 0.47, v0 0.50, the shift constant through "
        "the pans; overscan 3 %, canvas 4072 x 2290: positions are fractions of that canvas).",
        "# References (12): 1-3 = cut-outs of the NEW M0 (m0-v8 graded v3, after its lock_v2), never the whole frame: 1 sofa wall with cubes and pendant "
        "(frame uv x 0.45-0.92, y 0.25-0.95), 2 coffee table group (x 0.44-0.81, y 0.70-1.00), 3 floor, rug edge and skirting at the right (x 0.85-1.00, "
        "y 0.55-1.00); 4-12 = the m0-v8 close-ups without the jar (cube, pendant, NYOKO, boucle, sage knit, throw, runner, holders, bowl).",
        "# Empty: basket at (2.10, 0.45) and the floor lamp (TR3: transition-only / no floor lamp in the test); window out of view.",
        "# QA: lock_v2 at G1.4 as a pan endpoint (2 px per strip after register); products +-15 %; grading v3 with M0's group (own wall point by the corner).",
    ]
    return head, body


def m0x():
    s, th, cb = B("M0x", SOFA), B("M0x", "living/sofa-cover"), B("M0x", "living/accent-sconces")
    ru, dt, dp = B("M0x", "living/rug"), B("M0x", "dining table 160x85 (fixed)"), B("M0x", "kitchen-dining/dining-pendant")
    be, kr = B("M0x", "dining bench (fixed)"), B("M0x", "kitchen run (fixed): lower units, sink, hob, plastered hood, oak shelves, tall units, coffee niche, oven")
    scale = (f"SCALE: the clay is also the size of everything: the living sofa's right end at the left edge, x 0.00-{f(s[1])}; the partition wall and the "
             f"opening to the dining room exactly where the clay draws them; through the opening the 160 x 85 cm oak dining table x {span(dt)}, y {span(dt, 'y')}, "
             f"the bench x {span(be)}, the kitchen run from x {f(kr[0])}. " + SCALE_TAIL)
    body = [BLUEPRINT, "", scale, "",
            "1. PHOTO. One frame of a slow pan in the same Copenhagen house, 3 pm mid-winter, turned from the living room toward the open doorway to the "
            "dining room: 24 mm shift lens at 1.2 m, level, straight verticals, all sharp. The end of the sofa on the left, the plain partition wall, and "
            "through the doorway the dining table under its glowing lantern on the right third.", "",
            "CUT-OUTS. Images 1-2 are cut-outs of a photograph of the living room from the same point: 1 the sofa's right end with the throw and the "
            "lumbar cushion, 2 floor, rug and skirting. Image 3 is a cut-out of a photograph of the dining room: render exactly that table, lantern, bench, "
            "cushion pad, runner, vase, holders, rug and kitchen through the opening. Cut-outs give materials, colour and light only, never framing, position "
            "or size. Images 4-6 are close-ups of the exact products: match their form, colour and texture.", "",
            LIGHT.format(lamps="the living cube washes a short soft fan up and down the wall; through the opening the silk lantern glows over the table and a "
                         "warm line of LED light runs under the kitchen shelf.").replace("the back wall by the corner almost white, just under the glowing "
                         "window reveals; the window wall in soft shade, a clear half stop darker than the back wall, never grey. The glass is the brightest, "
                         "with detail.", "the partition wall clean white in soft side light; the dining "
                         "window, seen through the opening, the brightest, with detail."), "",
            MATERIALS, "",
            "4. PRODUCTS, one per line, each on its clay placeholder:",
            f"b. TRAVERTINE CUBE at x {span(cb)}, y {span(cb, 'y')}: one 12 cm cube of warm honed travertine, light out of top and bottom.",
            f"h. RUG at the bottom left, x {span(ru)}: {RUG_TXT}.",
            f"k-l. On the sofa end, x {span(th)}: the 30 x 50 charcoal linen-look lumbar and the thin cream cotton muslin throw with a short fringe over the arm.",
            f"p. THROUGH THE OPENING: the dining room of cut-out 3; the lantern x {span(dp)}.", "",
            NOT.format(extra="art or decor on the partition wall, ")]
    head = [
        "# pose-m0x-v8: transition pose M0x (end of P1, T-LD) at the M0 1.2.1 point, recipe v8 (render-agent, 2026-11-03; brief task 3). recipe B, one "
        "attempt, no second attempt in this brief. Generated by gen_m0_v8_prompts.py. Strip every # line before sending.",
        "# Clay (image_url): assets/blockout/house/framing/round5/poses/M0x.png (camera (0.83, 4.64, 1.20), yaw -35, u0 0.47, v0 0.50; the dining = the round-4 "
        "D1 placeholders; overscan 3 %, canvas 4072 x 2290: positions are fractions of that canvas).",
        "# References (6): 1-2 = cut-outs of the NEW M0 (m0-v8 graded v3, after its lock_v2): 1 sofa right end with throw and lumbar (frame uv x 0.75-0.93, "
        "y 0.55-0.95), 2 floor, rug and skirting (x 0.55-0.85, y 0.85-1.00); 3 = d1-3-dining-through-opening (D1 v7 graded v3, the left 75 %, uploaded and "
        "verified); 4-6 = cube, NYOKO, throw (refs/index-v7.json frames.M0).",
        "# QA: lock_v2 at G1.4 as a pan endpoint (2 px per strip after register); the dining object for object as D1 v7; no living wall in frame: grading v3 "
        "inherits M0's stops (one exposure per camera point).",
    ]
    return head, body


OUT = {"m0-v8": ("assets/prompts/recipe-v5.nordic/m0-v8.txt", m0), "pose-m0p-v8": ("assets/prompts/poses-v7.nordic/pose-m0p-v8.txt", m0p),
       "pose-m0x-v8": ("assets/prompts/poses-v7.nordic/pose-m0x-v8.txt", m0x)}
if __name__ == "__main__":
    for jid, (path, fn) in OUT.items():
        head, body = fn()
        text = "\n".join(body)
        assert text.isascii(), f"{jid}: non-ASCII in the prompt body"
        head.append(f"# Prompt body: {len(text)} characters (var2 limit 4,000).")
        open(os.path.join(REPO, path), "w", encoding="utf-8").write("\n".join(head) + "\n\n" + text + "\n")
        print(jid, len(text), "chars", "OK" if len(text) <= 4000 else "TOO LONG", "->", path)
