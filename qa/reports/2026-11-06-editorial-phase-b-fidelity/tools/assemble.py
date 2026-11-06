"""
qa-agent 2026-11-06: product-fidelity record for the editorial phase B (six frames; modern-country not fetched). Same format as
qa/reports/2026-11-06-editorial-test-fidelity.json; plus, for the three finished frames, the ED1 -> phase B comparison and the
code-fix traces in Nordic A. Judged by eye at 100 % (overlays/*.jpg) against the cards and the supplier crops render-agent made
(session scratchpad ed2-crops/, viewed only). Writes qa/reports/2026-11-06-editorial-phase-b-fidelity.json. Usage: python3.12 -I assemble.py
"""
import json
import os

REPO = "/home/user/homedesign-app"
Y, P, N = "yes", "partly", "no"


def row(card, present, faithful, why, ed1=None, fix=None):
    return dict(card=card, present=present, faithful=faithful, why=why, ed1=ed1, fix=fix)


frames = {
    "nordic-A-fin": dict(file="assets/renders/editorial-phase-b-2026-11-06/nordic-A-fin.png", base="ED1 nordic-A-gpt-image-2-5 + one seedream pass + code (wall lights x0.36, pendant x0.7)", rows=[
        row("fixed furniture: sofa, coffee table, armchair (board)", True, Y, "as the board", Y),
        row("cushions-cj-boucle-teddy", True, Y, "white boucle", Y),
        row("cushions-cj-knitted-chenille-bean-green", True, P, "sage, but a plush fuzzy surface, not the knitted chenille's raised grid", P, "targeted pass"),
        row("cushions-cj-linen-look-charcoal", True, P, "still a long lumbar; the card is 50 x 50 (the pass left it)", P, "targeted pass, mask on the cushion only"),
        row("sofa-cover-cj-cotton-muslin-fringe", True, Y, "crinkled muslin, fringe", Y),
        row("table-runner-cj-linen-look-sage-fringe", True, Y, "sage, fringe, across and hanging", Y),
        row("candle-holders-cj-travertine-pedestal", True, Y, "the pedestal pair", Y),
        row("bowl-cj-glutinous-white-belly-bowl-21", True, P, "warm-white speckled, right; still deeper than the card (H/D ~0.4 against 0.30)", P, "targeted pass (or code: a vertical squash about the foot)"),
        row("framed-art-aliexpress-minimal-geometric-triptych-prints", True, Y, "three different prints, black frames, mats", Y),
        row("accent-sconces-cj-travertine-block-updown-8x16", True, Y, "the flat block, now about 7.3 x 18 cm against the nearest 50 cm frame (code x0.36): within +-15 %", P),
        row("pendant-cj-silk-ribbed-pumpkin-40", True, Y, "form right; about 0.7x the ED1 size, now plausibly ~40 cm", P),
        row("rug-cj-braided-wool-natural", True, P, "cream with fine parallel tonal lines, but still a looped pile, not the flat braid", N, "own pass, or accepted as a direction"),
        row("basket-cj-jute-rope-cylinder", True, Y, "jute rope cylinder with loop handles, in the corner", N),
        row("planter-cj-seagrass-belly", True, Y, "exactly one, with the olive tree", P),
    ], generic=["window seat with a cushion and books", "door", "olive tree", "pillar candles (filler)", "open magazine (images only)", "cup"],
       code_fix_traces=["right wall light: the old, larger light's footprint stays as a paler rectangle with a hard right and bottom edge round the small light (canvas ~x 2095-2205, "
                        "y 350-570), visible at 100 % without any stretch (overlays/nordicA-right-light-before-after.jpg, nordicA-right-light-stretch.jpg); and the sun stripe below "
                        "keeps the notch the old light's shadow cut into it - a shadow that no longer has a light to belong to",
                        "pendant: under the smaller pendant a soft darker smudge where the old one hung and a pale blotch below-left of it (canvas ~x 1190-1400, y 210-300); "
                        "faint at 100 %, plain at x4 contrast (overlays/nordicA-pendant-before-after.jpg, nordicA-pendant-stretch.jpg)",
                        "left wall light: its glow re-scaled cleanly; no hard edge found (overlays/nordicA-left-light-before-after.jpg)"]),
    "nordic-B-fin": dict(file="assets/renders/editorial-phase-b-2026-11-06/nordic-B-fin.png", base="ED1 nordic-B-nano-banana-2 + one seedream pass", rows=[
        row("fixed furniture: armchair (board)", True, Y, "unchanged", Y),
        row("vase-aliexpress-vintage-distressed-clay-vase-589009", True, Y, "unchanged", Y),
        row("basket-cj-jute-rope-cylinder", True, Y, "unchanged", Y),
        row("magazine-holder-cj-felt-log-basket", True, Y, "unchanged", Y),
        row("wall-decor-cj-corn-husk-round-38", True, Y, "unchanged; the rim still darker and wider than 'a thin honey rim' (a note)", Y),
        row("rug-cj-braided-wool-natural", True, Y, "now a flat weave in fine tone-on-tone cream lines", N),
        row("sofa-cover-cj-cotton-muslin-fringe", True, Y, "new: ivory muslin waffle with a short fringe over the armchair's arm, replacing the generic taupe throw", None),
        row("curtains-aliexpress-linen-blend-s-fold-180502", True, P, "natural linen sheers, plausible; the heading out of frame", P),
    ], generic=["plain magazines", "eucalyptus"]),
    "warm-modern-A-fin": dict(file="assets/renders/editorial-phase-b-2026-11-06/warm-modern-A-fin.png", base="ED1 warm-modern-A-gpt-image-2-5 + one seedream pass", rows=[
        row("framed-art-aliexpress-frameless-minimalist-wall-art-631735", True, Y, "unchanged", Y),
        row("accent-sconces-aliexpress-travertine-cylinder-walnut-choice", True, Y, "straight cylinder on walnut", Y),
        row("floor-lamp-cj-pleated-walnut-stem-158", True, Y, "unchanged; the brass still reads polished (a note: warm-modern allows brushed brass, not polished gold)", Y, "code (soften the speculars)"),
        row("pendant-cj-tiered-fabric-drum", True, P, "still three tiers stepping down; the card photo has 4-5 rings, widest in the middle (the pass left it)", P, "targeted pass with the card photo and the ring count in words"),
        row("cushions-cj-boucle-teddy (White, Milk tea)", True, Y, "two white boucle and, new, a light milk-tea boucle on the right", P),
        row("cushions-cj-knitted-chenille-bean-green (Camel)", True, Y, "camel, textured", Y),
        row("sofa-cover-cj-cotton-muslin-fringe (Flax)", True, Y, "flax muslin over the left arm", Y),
        row("candle-holders-cj-travertine-pedestal", True, Y, "the pedestal pair", Y),
        row("bowl-cj-matte-black-bowl-20", True, Y, "exactly one now", Y),
        row("vase-cj-textured-white-stoneware", True, Y, "new: tall, crinkle-relief white, as the card photo", P),
        row("rug-cj-braided-wool-natural", True, P, "tonal cream ribs now, still chunky", N, "own pass or accept"),
    ], generic=["curved greige boucle sofa", "walnut coffee table", "round travertine side table", "walnut tray, figs, mug", "open book (images only)", "olive branch"]),
    "boho-A": dict(file="assets/renders/editorial-phase-b-2026-11-06/boho-A.png", base="gpt-image-2-5, new", rows=[
        row("wall-decor-aliexpress-natural-raffia-woven-bohemian-763597", True, P, "raffia fringe sun with a cowrie ring and a coiled centre, as the card photo; it reads about twice the card's 30 cm against the frames beside it (if those generic frames are ~50 x 70)", None, "code (scale about its centre, fill the wall)"),
        row("wall-sconce-aliexpress-rattan-bamboo-wall-lamp-671943 (x2)", True, Y, "woven bamboo ball on a wooden arm and round wood plate, glowing from inside, as the card photo", None),
        row("table-runner-aliexpress-boho-macrame-table-runners-263532", True, Y, "macrame with a jute centre stripe and a long fringe", None),
        row("cushions-cj-washed-cotton-frayed (Rust Orange) x2", True, Y, "rust, frayed edge", None),
        row("cushions-cj-sandstone-chenille-flange (olive)", True, Y, "olive nubby chenille with a flat flange", None),
        row("sofa-cover-cj-washed-hemp-throw (Raw Jute)", True, Y, "washed hemp in raw jute, draped", None),
        row("planter-zendrop-seagrass-belly-basket-45", True, P, "seagrass belly with the black base and a bird-of-paradise; but drawn smaller than the XL basket beside it, while the cards say 45 x 36 against 38 x 33 (the prompt itself asked for 'one larger basket')", None, "accept, or fix the prompt"),
        row("basket-cj-seagrass-belly-xl", True, P, "natural seagrass belly with handles; drawn the larger of the two (cards: the smaller)", None),
        row("pouf-cj-cotton-knit-ball-cover (natural)", True, Y, "chunky natural knit ball", None),
    ], generic=["kilim rug", "earth-tone triptych", "rattan dome pendant", "mango-wood bowl", "brass candle holders", "glass teapot and tea glasses (clear glass, a prop)", "plants", "French doors, tiles"],
       note="the look is very golden, close to the HDR the guardrail excludes (not a product matter)"),
    "mediterranean-A": dict(file="assets/renders/editorial-phase-b-2026-11-06/mediterranean-A.png", base="gpt-image-2-5, new", rows=[
        row("framed-art-aliexpress-mediterranean-wabi-sabi-poster-802890 (3 of 6)", True, Y, "olive tree, vases with an arch, arched stairs with a palm, in thin oak frames, as the card photo", None),
        row("magazine-holder-cj-arch-iron-cane", True, Y, "arched black iron frame with a cane sling, X stretcher; magazines without readable text", None),
        row("candle-holders-cj-travertine-pedestal", True, Y, "the pedestal pair (no candles)", None),
        row("bowl-cj-speckled-ivory-wide-bowl-21", True, P, "speckled ivory, right; but a deeper rounded bowl, not the wide conical 'rain hat' (D21.3 x H5.2) with the exposed brown clay rim", None, "targeted pass"),
        row("basket-zendrop-seagrass-belly-38x34", True, Y, "exactly one, folded collar, loop handles (with a plant)", None),
        row("cushions-cj-washed-cotton-frayed (Earthy Orange)", True, Y, "terracotta, frayed", None),
        row("cushions-cj-washed-cotton-frayed (Moss Green 30x50)", True, Y, "moss lumbar, frayed", None),
        row("cushions-cj-washed-cotton-frayed (White)", True, P, "white frayed squares are there, but they cannot be told from the bench's generic ivory back cushions beside them: a look-alike risk", None, "targeted pass (bench cushions plain, no fringe)"),
        row("sofa-cover-cj-cotton-muslin-fringe", True, Y, "crinkled muslin, fringe", None),
        row("vase-aliexpress-vintage-distressed-clay-vase-589009", True, Y, "the cream ribbed clay vase on the sill with olive branches", None),
    ], generic=["cane dome pendant", "jute rug", "plaster bench and its back cushions (see the white cushion)", "oak table", "straw hat", "figs", "the plant in the basket"]),
    "japandi-A": dict(file="assets/renders/editorial-phase-b-2026-11-06/japandi-A.png", base="nano-banana-2, new", rows=[
        row("framed-art-aliexpress-japanese-wabi-sabi-tree-176323 (3 of the series)", True, Y, "bare-tree prints and a dark panel, in thin black frames", None),
        row("pendant-cj-pleated-pumpkin-lantern-40", True, P, "a tall pleated paper egg (H/W ~1.3), as the reference crop render-agent sent; the card says a 40 x 25 pumpkin, 'closed rounded lantern form'. Either the crop is another variant of the listing or the card's dimensions are wrong: to settle on the card's own images (sourcing)", None, "sourcing first, then a pass if needed"),
        row("vase-cj-black-matte-stoneware-jar-30", True, P, "black matte sandy jar with a short neck, right; squat (H/W ~1.5) against the card's tapered 30 x 15", None, "targeted pass"),
        row("candle-holders-aliexpress-matte-black-iron-pillar-set2", True, Y, "exactly two low black plates on small feet, with pillar candles", None),
        row("bowl-cj-matte-black-bowl-20", True, Y, "matte black deep bowl", None),
        row("accent-sconces-aliexpress-travertine-cylinder-walnut-choice (x2)", True, P, "travertine cylinders on walnut plates, right; they look large next to the frames (about half a frame's width); not measurable (the art has no card dimensions)", None, "code if confirmed"),
        row("cushions-cj-washed-cotton-frayed (moss)", True, Y, "moss, frayed", None),
        row("cushions-cj-linen-look-charcoal (ink)", True, Y, "ink, linen look, square", None),
        row("cushions-aliexpress-fashion-modern-wabi-sabi-464203", True, P, "brown nubby weave, close to the card photo's family; reads boucle-like (the card has no colour or texture text)", None),
        row("bedspread-cj-six-layer-gauze-quilt (Beige Khaki)", True, Y, "puckered gauze with crinkle lines, beige-khaki; folded on the arm, not in a straight line", None),
    ], generic=["paper column floor lantern on a wooden tripod (close to the forbidden Noguchi Akari floor columns in feel: for the designer)", "ink planter with the olive tree", "tea set and tray", "sofa, table, step"]),
}
for k, v in frames.items():
    rs = v["rows"]
    v["counts"] = dict(rows=len(rs), present=sum(r["present"] for r in rs), yes=sum(r["faithful"] == Y for r in rs), partly=sum(r["faithful"] == P for r in rs), no=sum(r["faithful"] == N for r in rs))
compare = {
    "nordic-A-fin": dict(fixed=["the jute rope basket in (was missing); exactly one seagrass planter (was doubled: the look-alike is gone)", "wall lights to ~7 x 18 cm (were ~2.6-3x)",
                                "pendant ~0.7x (was ~50-65 cm)", "rug: from a deep pile to fine tonal lines (still pile)"],
                         unchanged=["the charcoal lumbar (card 50 x 50)", "the sage cushion's surface", "the bowl's depth (0.5 -> 0.4, card 0.30)"], new=["the code-fix traces round the right wall light and under the pendant"]),
    "nordic-B-fin": dict(fixed=["the rug: now flat tonal lines (was a looped diamond knit)", "the generic taupe throw (a look-alike) replaced by our muslin throw"], unchanged=["the corn-husk round's rim (a note)"], new=[]),
    "warm-modern-A-fin": dict(fixed=["the second black bowl (a look-alike) removed", "the vase: tall crinkle-relief white (was speckled, squat)", "the milk-tea boucle cushion added"],
                              unchanged=["the pendant's three tiers", "the floor lamp's polished-looking brass"], improved=["the rug: tonal cream ribs (still chunky)"], new=[]),
}
out = dict(report="qa/reports/2026-11-06-editorial-phase-b-fidelity.md", by="qa-agent", date="2026-11-06",
           scope="editorial phase B (ED2, ED3): product fidelity only; no lock, grading targets or density. modern-country-A was not fetched (var2 sign-in), so six frames",
           inputs="assets/renders/editorial-phase-b-2026-11-06/ (six frames, raws, jobs.json with render-agent's notes and code fixes); briefs/render-editorial-phase-b-2026-11-06.md; data/products cards; supplier crops in the session scratchpad (ed2-crops/, viewed only)",
           text_logos_brands="none readable in any frame: the magazines show images; no logos, no signage (the harbour town in boho has no text)",
           forbidden="nothing from the house-wide lists on our products; generic props: a clear-glass teapot and glasses in boho (a prop, not a product); the japandi floor column lantern is close in feel to the Akari floor lamps the japandi brief names as forbidden copies (generic, for the designer)",
           look_alikes="ED1's two (the second seagrass basket, the second black bowl) and the taupe throw are gone. New: in mediterranean the bench's generic ivory back cushions cannot be told from our white frayed cushion",
           frames=frames, ed1_comparison=compare,
           fixes=dict(code_0_tokens=["Nordic A: rebuild the wall round the right light (radial glow, no rectangle) and close the old shadow's notch in the sun stripe; re-fill the plaster under the pendant",
                                     "warm modern: soften the brass speculars to brushed", "boho: the raffia sun to the card's 30 cm (if the frames are 50 x 70)", "japandi: the wall lights if a size reference confirms them large"],
                      one_targeted_pass=["Nordic A: the charcoal cushion to a 50 x 50 square, the sage cushion's chenille grid, the bowl's depth (one pass, masked to the table and the cushions)",
                                         "warm modern: the pendant's rings from the card photo (twice left by an unmasked pass: mask it)", "mediterranean: the rain-hat bowl with the brown rim; the bench cushions plain",
                                         "japandi: the jar's proportion"],
                      not_one_pass=["the rugs' remaining pile (Nordic A, warm modern): a whole surface; accept as a direction or a pass of its own",
                                    "japandi pendant: first a sourcing answer (egg variant or 40 x 25 pumpkin)", "boho planter / basket sizes: the prompt asked for the larger basket; accept or change the prompt"]))
json.dump(out, open(os.path.join(REPO, "qa/reports/2026-11-06-editorial-phase-b-fidelity.json"), "w"), indent=1, ensure_ascii=False)
for k, v in frames.items():
    print(k, v["counts"])
