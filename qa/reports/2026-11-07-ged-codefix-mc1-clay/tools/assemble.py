"""qa-agent 2026-11-07: the machine record of qa/reports/2026-11-07-ged-codefix-mc1-clay.md. Reads data/diffs.json and data/clay-wm-r1.json.
Usage: python3.12 -I assemble.py"""
import json
import os

REPO = "/home/user/homedesign-app"
HERE = os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay")
D = json.load(open(os.path.join(HERE, "data/diffs.json")))
C = json.load(open(os.path.join(HERE, "data/clay-wm-r1.json")))
R = "assets/renders/editorial-phase-b-2026-11-06/"


def chk(id_, verdict, note):
    return dict(check=id_, verdict=verdict, note=note)


frames = {
    "boho-A-fin4": dict(
        file=R + "boho-A-fin4.png", against=R + "boho-A-fin2.png", records=[R + "codefix3.json", R + "codefix4.json"], state="not_yet",
        checks=[
            chk("G-ED.8", "pass", "two components only: the seam band [375,232,421,481] (4,081 px) and the basket [2003,755,2293,1088] (62,333 px)"),
            chk("G-ED.9", "fail", "the seam at x~399 is gone (clean at x2). The door behind the basket is not: square, misaligned plank pieces and light/dark blocks on the jamb (x~2190-2250, y~740-870) and at the panel edge (x~2295-2310, y~840-890), visible at 100%; the wall fill above the old basket is grainy only in the stretch"),
            chk("G-ED.4", "pass (edge)", "basket 198 x 188 px against the planter's 200 x 212 (basket ~3% nearer): width ratio ~0.96 against the cards' 0.84 (+14%), height ~0.86 against 0.92 (-6%); inside +-15%"),
            chk("G-ED.2", "fail (new)", "basket-cj-seagrass-belly-xl: three handles (left, centre, right); the card's belly basket has two. Present since the base frame; missed in phase B"),
            chk("G-ED.10", "open", "the golden, near-HDR look from phase B: needs master-designer's written verdict"),
        ],
        rows_changed=[dict(card="basket-cj-seagrass-belly-xl", faithful="partly", why="size now right; three handles against two"),
                      dict(card="planter-zendrop-seagrass-belly-basket-45", faithful="yes", why="two handles; now the larger of the two, as in the cards")],
        counts=dict(rows=9, yes=8, partly=1, no=0),
        left=[dict(what="redo the door fill behind the basket, following the planks (columns along the stiles and the panel edge, the sun stripes continued)", who="render-agent", cost="0 (code); if it fails, a local pass ~650 with the manager's approval"),
              dict(what="take out the basket's centre handle (plain wall behind it)", who="render-agent", cost="0"),
              dict(what="G-ED.10 written verdict", who="master-designer", cost="0")]),
    "mediterranean-A-ed5": dict(
        file=R + "mediterranean-A-ed5.png", against=R + "mediterranean-A-ed4.png", records=[R + "codefix3.json"], state="not_yet",
        checks=[
            chk("G-ED.8", "pass", "0 px outside the recorded boxes (left and middle cushions, the rim band)"),
            chk("G-ED.9", "pass", "the rim echo is gone, clean at x4; the cushions' Lab shift keeps the crinkle, no halo"),
            chk("G-ED.6", "fail", "the two generic bench cushions are sand now (Lab shift), but keep the frayed flange, and its top edge stays light (render-agent's open point). Same material and edge as our cushions-cj-washed-cotton-frayed, whose options include beige-like colours (Rice Soup Jiao Fringe, Apricot Ice Cream). Bible 1.9: a generic item of the same category only if clearly different in material AND colour"),
        ],
        rows_changed=[dict(card="cushions-cj-washed-cotton-frayed (White)", faithful="yes (product)", why="ours is unchanged; the look-alike is the generic pair")],
        counts=dict(rows=10, yes=9, partly=1, no=0),
        left=[dict(what="the bench cushions: plain sand linen with no flange (a local pass), or declare them ours in a listed colour (then G-ED.1-5 and a hotspot)", who="master-designer decides; render-agent", cost="~650 for the pass, or 0"),
              dict(what="G-ED.10 / G-ED.13 written verdict", who="master-designer", cost="0")]),
    "japandi-A-ed5": dict(
        file=R + "japandi-A-ed5.png", against=R + "japandi-A-ed4.png", records=[R + "codefix3.json"], state="not_yet",
        checks=[
            chk("G-ED.8", "pass", "one component round the jar [586,911,748,1148] against ed4 and [588,913,748,1148] against the original"),
            chk("G-ED.9", "pass", "the rim wings and the two notches are gone; the base is rounded with a contact shadow. The grain under the base shows only at x4 and matches the sill's own grain (high-pass sd 13.4 against 12.6 below it): a note"),
            chk("G-ED.2/4", "pass", "vase-cj-black-matte-stoneware-jar-30: H/W 2.05 (card 2.0)"),
            chk("G-ED.12", "fail (unchanged)", "raw 2.09% clipped, mostly the paper pendant (gate report 2026-11-07)"),
        ],
        rows_changed=[dict(card="vase-cj-black-matte-stoneware-jar-30", faithful="yes", why="2.05, clean")],
        counts=dict(rows=10, yes=7, partly=3, no=0),
        left=[dict(what="the pendant after the sourcing answer, and the tripod column lantern replaced (designer: reads as a copy, G-ED.15); re-measure G-ED.12 on the new raw", who="sourcing-agent, then render-agent; owner JP1", cost="650-1,300"),
              dict(what="the sconces and the wabi-sabi cushion stay 'partly'", who="master-designer", cost="0")]),
    "warm-modern-A-ed5": dict(
        file=R + "warm-modern-A-ed5.png", against=R + "warm-modern-A-ed4.png", records=[R + "codefix3.json"], state="final_test",
        checks=[
            chk("G-ED.8", "pass", "one component [1337,177,1585,249], the lower rings only"),
            chk("G-ED.9", "pass", "at x4 a short broken line where ring 5 hangs under ring 4's rim and a 3-4 px notch at ring 5's right end; nothing at 100%. The glow under the pendant is ED4's, unchanged"),
            chk("G-ED.2", "pass", "pendant-cj-tiered-fabric-drum: 5 rings, the widest third, 2 below it, as the card"),
        ],
        rows_changed=[dict(card="pendant-cj-tiered-fabric-drum", faithful="yes", why="5 rings")],
        counts=dict(rows=11, yes=10, partly=1, no=0),
        left=[dict(what="the rug stays 'partly' (EDR1 failed; the designer's note, hotspot only via the close-up)", who="—", cost="0"),
              dict(what="G-ED.10 / G-ED.13 written verdict before the manager shows it", who="master-designer", cost="0")]),
    "modern-country-A-mc1": dict(
        file=R + "modern-country-A-mc1.png", against=R + "modern-country-A.png", records=[R + "codefix3.json", R + "codefix4.json", R + "mc1.json"], state="almost",
        checks=[
            chk("G-ED.8", "pass", "fix1: curtains, cups, the glyph; fix2: the rug only; MC1 table and sill: 0 px outside the saved masks (also 0 with the mask grown 2 px)"),
            chk("G-ED.9", "fail", "the table pass's mask edges at x~1120 and x~1626: vertical tone steps of 11-15 levels on the table apron (y 1240-1340) and the rug (y 1460-1500), visible at 100%. The glyph's inpaint ring shows only at x4; the glass beside the new vase is smoother (stretch only)"),
            chk("G-ED.7", "pass", "the cups are plain off-white, no speckle, no tan rim; the set reading is gone. A faint warm rim on cup 1 at x3 only"),
            chk("G-ED.3", "pass", "curtains: L* 73-75 against the plaster's 69-75 (before 53-55), b* 12 against 19-26: the card's off-white, a little cooler than the milk wall"),
            chk("G-ED.4 runner", "pass", "~328 px at the bowl's contact row against the bowl's 220 px: 1.49 (cards 33 / 21.3 = 1.55); ~31-33 cm against the ~100 px cups; 13 tassels (card ~12)"),
            chk("G-ED.4 bowl", "partly", "wide open bowl with a thin tan rim, ~220 px = ~21-22 cm; H/D ~0.31 against the card's 0.244 (+27%)"),
            chk("G-ED.2/4 clay vase", "partly", "tall neckless cream ovoid with fine horizontal grooves, no lug, no pits; but H/W ~1.64 (132 x 216 px) against ~2.1 (L 31 x 15), widest at the middle where the card is widest at the shoulder; height 1.32 x the column vase (cards 1.26)"),
            chk("legs on the rug", "note", "the light line at the leg edges is the base frame's own (+15-25 levels in fix1 too); the fade lifted the shadow beside one leg (52 -> 78 at y~1510)"),
        ],
        rows_changed=[
            dict(card="vase-aliexpress-vintage-distressed-clay-vase-589009", faithful="partly", why="right family; H/W 1.64 against 2.1, widest at the middle", was="no"),
            dict(card="bowl-cj-speckled-ivory-wide-bowl-21", faithful="partly", why="open, rim right; H/D 0.31 against 0.244", was="partly (0.45)"),
            dict(card="table-runner-cj-linen-look-sage-fringe", faithful="yes", why="~33 cm", was="partly (x1.4)"),
            dict(card="curtains-aliexpress-linen-blend-s-fold-180502", faithful="yes, as the listing's 'Pull Pleated Tape' option", why="tone fixed; the heading is that option, so the hotspot must name it", was="partly"),
        ],
        look_alikes="the cups: fixed (G-ED.7 pass)",
        counts=dict(rows=7, yes=5, partly=2, no=0),
        left=[dict(what="blend the low frequencies across the table pass's two mask edges (~40 px)", who="render-agent", cost="0"),
              dict(what="the bowl's body x0.78 in height about the rim, the table filled behind", who="render-agent (or the owner accepts it with the note)", cost="0"),
              dict(what="the clay vase x0.80 in width about its axis, the glass and mullion filled as with the jar", who="render-agent (or accept with the note)", cost="0"),
              dict(what="the curtain hotspot names the 'Pull Pleated Tape' option", who="frontend-dev", cost="0")]),
}

record = dict(
    report="qa/reports/2026-11-07-ged-codefix-mc1-clay.md", by="qa-agent", date="2026-11-07",
    brief="briefs/qa-ged-codefix-mc1-clay-2026-11-07.md (+ the coordinator's update on part 2: house plan 1.3.2 / WMC1-WMC5; the r2 verdicts wait for r2)",
    gate="docs/ops/quality-gate-g-ed-2026-11-07.md",
    part1=dict(frames=frames, unchanged=dict(nordic_A="final_test (rug 'partly' stays: EDR1 failed, mc1.json 'rugs')", nordic_B="final_test"),
               edr1="failed twice in one round (mc1.json rugs: no frame composited); the Nordic A and warm-modern rugs stay 'partly'", diffs=D),
    part2=dict(scope="r1 only, per the coordinator's update: projection, QA's named-edge tool, render-agent's findings; no tangency or reference verdict until r2",
               clay="assets/blockout/house/framing/warm-modern-r1/", measurements=C,
               summary=dict(
                   projection="QA's own projection from the plan's camera record equals render-agent's to 4 decimals on all six named endpoints",
                   named_edges="7 of 8 named plan lines sit on the clay's edges within 0-4 px at 1920 (head 0, bench front top 0, bench corner 0, track band 0, ceiling -0.5, bench top at the wall 3, back jamb 4 = the plaster wrap); the back-wall floor line reads -7 px (fewer strong samples, the sofa and rug in front): not a projection error, re-read on r2",
                   findings={"pot vs back stack 9 px (M0)": "confirmed: 9 px at 3840 (0.0023); WMC1 removes the back stack",
                             "crown r 0.40 through the wall, 1.4 cm from the glass": "confirmed by the plan (X -2.40, 0.10 through; Y to 0.87, 0.12 past the jamb; 1.4 cm at Y 0.75) and the index (crown touches the back stack, 1 px); WMC2 r 0.28",
                             "M0p rounded corner along the left edge": "confirmed: tangent u 0.0053; at R 0.30 (WMC3) u -0.0108, outside. Bench back corner u 0.0021 -> -0.0116 at WMC4",
                             "armchair and basket vs magazine holder 0.0176 / 0.0177": "confirmed as tangents (QA on the index: 58 px = 0.0151 and 72 px = 0.0187 of the width, both < 0.02). NOT covered by WMC1-WMC5: still open for r2",
                             "vase on the bench clearance 89 px": "confirmed: 89 px (0.023 of the width), clear"},
                   for_r2=["the two magazine-holder tangents", "WMC2's own check: the basket in front of the pot, pot rim v ~0.700 against the basket top ~0.704",
                           "the back-wall floor line re-read", "then the tangency verdict and 'may serve as reference'"],
                   reference_verdict="not given on r1 (superseded by 1.3.2); waits for r2 and, for the paid shell step, the owner's WMP2")),
)
json.dump(record, open(os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay.json"), "w"), ensure_ascii=False, indent=1)
print({k: (v["state"], v["counts"]) for k, v in frames.items()})
