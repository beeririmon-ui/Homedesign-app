"""
qa-agent 2026-11-06: product-fidelity record for the ED1 editorial test (five frames). No G1.4, no grading targets, no density, by
design (ED1). Coverage per frame: card id, present, faithful (yes / partly / no), why. Judged by eye at 100-200 % (overlays/*.jpg)
against the cards (data/products) and the supplier crops render-agent made (session scratchpad ed-crops/, viewed, not copied).
Writes qa/reports/2026-11-06-editorial-test-fidelity.json. Usage: python3.12 -I assemble.py
"""
import json
import os

REPO = "/home/user/homedesign-app"
Y, P, N, A = "yes", "partly", "no", None


def row(card, present, faithful, why, fix=None):
    return dict(card=card, present=present, faithful=faithful, why=why, fix=fix)


FURN = [row("fixed furniture: sofa 220x92x78 (board)", True, Y, "cream, track arms, as the board"),
        row("fixed furniture: coffee table 140x70 h38 (board)", True, Y, "oak, rounded ends, as the board"),
        row("fixed furniture: armchair 72x78 h70 (board)", True, Y, "oak frame, boucle cushions (foreground, cut)")]
frames = {
    "nordic-A-nano-banana-2": dict(file="assets/renders/editorial-test-2026-11-06/nordic/nordic-A-nano-banana-2.jpg", rows=FURN + [
        row("cushions-cj-boucle-teddy", True, Y, "white looped boucle, square"),
        row("cushions-cj-knitted-chenille-bean-green", True, Y, "sage, bubbly knit"),
        row("cushions-cj-linen-look-charcoal", True, P, "colour and linen look right, but drawn as a long lumbar; the card is a 50 x 50 square", "targeted pass"),
        row("sofa-cover-cj-cotton-muslin-fringe", True, Y, "crinkled white muslin with a short fringe"),
        row("table-runner-cj-linen-look-sage-fringe", True, Y, "sage slub linen, knotted fringe, across the table and hanging"),
        row("candle-holders-cj-travertine-pedestal", True, N, "three plain travertine cylinders of three heights; the card is a pair of pedestals (flared cup, conical base)", "targeted pass"),
        row("bowl-cj-glutinous-white-belly-bowl-21", False, N, "missing (a cup and an open magazine instead)", "targeted pass"),
        row("framed-art-aliexpress-minimal-geometric-triptych-prints", True, Y, "three different prints (two squares, the dot on the fold, three bars) in thin black frames with white mats, as the listing shows"),
        row("accent-sconces-cj-travertine-block-updown-8x16", True, N, "a curved, U-shaped travertine shade, not the flat 8 x 16 block; about 21-26 x 31-37 cm by the 50 cm frames beside it (about 2x)", "targeted pass (or code resize + reshape)"),
        row("pendant-cj-silk-ribbed-pumpkin-40", True, P, "the flattened ribbed pumpkin with the metal ring is right; it reads about 55-70 cm against the sofa behind it (card 40)", "code (scale about the cord)"),
        row("rug-cj-braided-wool-natural", True, N, "a chunky looped berber with raised diamond lines; the card is a flat braided weave in tone-on-tone horizontal bands", "own pass (a whole surface)"),
        row("basket-cj-jute-rope-cylinder", False, N, "missing: a second seagrass belly basket stands where it should be", "targeted pass"),
        row("planter-cj-seagrass-belly", True, P, "right weave and handles with the olive tree, but twice: the empty second one reads as our product", "targeted pass (the jute basket in its place)"),
    ], generic=["window seat with a cushion", "panelled door", "olive tree", "pillar candles (filler, not sold)", "open magazine (images only, no legible text)", "cup and saucer"]),
    "nordic-A-gpt-image-2-5": dict(file="assets/renders/editorial-test-2026-11-06/nordic/nordic-A-gpt-image-2-5.jpg", rows=FURN + [
        row("cushions-cj-boucle-teddy", True, Y, "white boucle"),
        row("cushions-cj-knitted-chenille-bean-green", True, P, "sage, but a crushed smooth fabric rather than the knitted chenille's raised grid", "targeted pass"),
        row("cushions-cj-linen-look-charcoal", True, P, "a long lumbar; the card is 50 x 50", "targeted pass"),
        row("sofa-cover-cj-cotton-muslin-fringe", True, Y, "crinkled muslin, fringe"),
        row("table-runner-cj-linen-look-sage-fringe", True, Y, "sage, fringe, hanging over the front"),
        row("candle-holders-cj-travertine-pedestal", True, Y, "the pedestal pair with the flared cup; a little tall for their width (H/W ~2 against 1.6)"),
        row("bowl-cj-glutinous-white-belly-bowl-21", True, P, "warm-white speckled matte, right; deeper than the card's flat belly (H/D ~0.5 against 0.30)", "targeted pass"),
        row("framed-art-aliexpress-minimal-geometric-triptych-prints", True, Y, "three different prints, black frames, white mats"),
        row("accent-sconces-cj-travertine-block-updown-8x16", True, P, "the flat travertine block with lit pores, as the supplier photo; about 21 x 50 cm by the frames (card 8 x 16: ~2.6-3x)", "code (scale down, fill the wall)"),
        row("pendant-cj-silk-ribbed-pumpkin-40", True, P, "form right; reads about 50-65 cm against the sofa (card 40)", "code"),
        row("rug-cj-braided-wool-natural", True, N, "a deep cream loop / shag pile, not the flat braided bands", "own pass"),
        row("basket-cj-jute-rope-cylinder", False, N, "missing: two seagrass belly baskets in the corner", "targeted pass"),
        row("planter-cj-seagrass-belly", True, P, "right, with the olive tree, but doubled by an empty second basket", "targeted pass"),
    ], generic=["window seat with a cushion and books", "door", "olive tree", "pillar candles (filler)", "open magazine (images only)", "cup"]),
    "nordic-B-nano-banana-2": dict(file="assets/renders/editorial-test-2026-11-06/nordic/nordic-B-nano-banana-2.jpg", rows=[
        row("fixed furniture: armchair 72x78 h70 (board)", True, Y, "oak frame, boucle cushions"),
        row("vase-aliexpress-vintage-distressed-clay-vase-589009", True, Y, "the tall cream clay vase with fine horizontal ribbing, eucalyptus"),
        row("basket-cj-jute-rope-cylinder", True, Y, "jute rope cylinder with two loop handles, very close"),
        row("magazine-holder-cj-felt-log-basket", True, Y, "charcoal felt, light-wood bars, cognac tabs, the front pocket; plain magazines; W/H ~1.35 against 45/40 (within ~20 %)"),
        row("wall-decor-cj-corn-husk-round-38", True, Y, "cream corn-husk coil with a braided rim, about 38-40 cm against the 35 cm basket; the rim darker and wider than 'a thin honey rim' (a note)"),
        row("rug-cj-braided-wool-natural", True, N, "cream, but a looped knit with raised diamond lines, not the flat braided bands", "own pass"),
        row("curtains-aliexpress-linen-blend-s-fold-180502", True, P, "natural linen sheer panels (not referenced); the S-fold heading is out of frame: colour and slub plausible, not verifiable"),
    ], generic=["a taupe fringed throw on the armchair (no card: it can read as ours)", "plain magazines in the holder", "eucalyptus"]),
    "warm-modern-A-nano-banana-2": dict(file="assets/renders/editorial-test-2026-11-06/warm-modern/warm-modern-A-nano-banana-2.jpg", rows=[
        row("framed-art-aliexpress-frameless-minimalist-wall-art-631735", True, Y, "the three brown / beige abstracts in thin light-oak frames, very close"),
        row("accent-sconces-aliexpress-travertine-cylinder-walnut-choice", True, N, "a tapered cone (a candlestick shape) on walnut; the card is a straight D6.5 x H16 cylinder", "targeted pass"),
        row("floor-lamp-cj-pleated-walnut-stem-158", True, Y, "pleated cream cone shade, walnut stem, brass collars and base, pull chain; the brass reads polished (forbidden: polished gold; allowed: brushed brass)"),
        row("pendant-cj-tiered-fabric-drum", True, P, "a three-tier drum getting smaller downwards; the card's photo has 4-5 rings with the widest in the middle (the prompt said three-tier)", "targeted pass"),
        row("cushions-cj-boucle-teddy (White, Milk tea)", True, N, "greige boucle, the sofa's own colour and texture (forbidden by the warm-modern rule: a plain cushion like the fabric); no white, no milk tea", "targeted pass"),
        row("cushions-cj-knitted-chenille-bean-green (Camel)", False, N, "missing", "targeted pass"),
        row("sofa-cover-cj-cotton-muslin-fringe (Flax)", False, N, "missing", "targeted pass"),
        row("candle-holders-cj-travertine-pedestal", True, Y, "the pedestal pair"),
        row("bowl-cj-matte-black-bowl-20", True, Y, "matte black, deep, on a foot ring"),
        row("vase-cj-textured-white-stoneware", True, P, "crinkle-textured white, right; a squat jar (H/W ~1.25) against the card's 16 x 32", "targeted pass"),
        row("rug-cj-braided-wool-natural", True, N, "a flat jute / sisal look in beige-brown, not the cream braided wool", "own pass"),
    ], generic=["curved greige boucle sofa (the hero, no card)", "walnut coffee table", "travertine side table", "walnut tray, figs, mug", "open book (images only)", "olive branch"]),
    "warm-modern-A-gpt-image-2-5": dict(file="assets/renders/editorial-test-2026-11-06/warm-modern/warm-modern-A-gpt-image-2-5.jpg", rows=[
        row("framed-art-aliexpress-frameless-minimalist-wall-art-631735", True, Y, "very close"),
        row("accent-sconces-aliexpress-travertine-cylinder-walnut-choice", True, Y, "straight travertine cylinder on a walnut block, light out of the bottom; size not checkable (the art card has no dimensions)"),
        row("floor-lamp-cj-pleated-walnut-stem-158", True, Y, "pleated shade, walnut stem, brass, pull chain"),
        row("pendant-cj-tiered-fabric-drum", True, P, "three tiers getting smaller downwards, as in nano (card photo: 4-5 rings, widest in the middle)", "targeted pass"),
        row("cushions-cj-boucle-teddy (White, Milk tea)", True, P, "two white boucle, right; no milk tea", "targeted pass"),
        row("cushions-cj-knitted-chenille-bean-green (Camel)", True, Y, "camel, textured knit"),
        row("sofa-cover-cj-cotton-muslin-fringe (Flax)", True, Y, "flax crinkled muslin over the left arm"),
        row("candle-holders-cj-travertine-pedestal", True, Y, "the pedestal pair"),
        row("bowl-cj-matte-black-bowl-20", True, Y, "matte black, wide, about 21 cm against the mug"),
        row("vase-cj-textured-white-stoneware", True, P, "speckled cream stoneware, round-shouldered: not the crinkle texture; squat against 16 x 32", "targeted pass"),
        row("rug-cj-braided-wool-natural", True, N, "a chunky jute / wool loop, darker than the cream braided wool", "own pass"),
    ], generic=["curved greige boucle sofa", "oval walnut coffee table on plinths", "round travertine side table (foreground)", "a second, ribbed black bowl on the side table (no card: reads as a second product)", "walnut tray, figs, mug", "open book (images only)", "olive branch"]),
}
for k, v in frames.items():
    rs = v["rows"]
    v["counts"] = dict(rows=len(rs), present=sum(r["present"] for r in rs), faithful_yes=sum(r["faithful"] == Y for r in rs),
                       partly=sum(r["faithful"] == P for r in rs), no=sum(r["faithful"] == N for r in rs))
out = dict(report="qa/reports/2026-11-06-editorial-test-fidelity.md", by="qa-agent", date="2026-11-06", scope="ED1 editorial test: product fidelity only (no G1.4, grading targets or density, by design)",
           inputs="assets/renders/editorial-test-2026-11-06/ (five finished frames, raws, jobs.json with render-agent's notes); docs/creative-review-2026-11-06.md 2a, 3.7, 4.0; data/products cards; "
                  "the supplier crops render-agent prepared (session scratchpad ed-crops/, viewed only)",
           text_logos_brands="none legible in any frame: the open magazines / books show photographs only (one illegible caption line in warm-modern nano); no logos, no brand copy",
           forbidden="Nordic list (Bible 'אסור'): nothing found (no mirrors, chrome, gloss, polished stone). Warm-modern draft list: the greige cushion on the greige sofa (nano) breaks its "
                     "cushion rule; the floor lamp's brass reads polished in nano (polished gold forbidden, brushed brass allowed) - a note",
           frames=frames,
           best_bases=dict(nordic="nordic-B (only the rug) and nordic-A-gpt (sconce size in code; the jute basket, the charcoal cushion and the bowl's depth in one targeted pass; the rug its own)",
                           warm_modern="gpt-image-2-5 (pendant tiers, the vase and milk tea in one pass; the rug its own); nano has five no's"),
           one_targeted_pass_can_fix="local objects: swaps and additions (candle holders, bowl, the jute basket for the second seagrass basket, the charcoal square, the sconce form, "
                                     "the warm-modern cushions, throw, vase, pendant tiers). Pure size errors (sconces, pendant) are cheaper in code, as the wall round was. "
                                     "The rug is a whole surface under the furniture and the light: not one local fix; its own pass or accepted as a direction")
json.dump(out, open(os.path.join(REPO, "qa/reports/2026-11-06-editorial-test-fidelity.json"), "w"), indent=1, ensure_ascii=False)
for k, v in frames.items():
    print(k, v["counts"])
