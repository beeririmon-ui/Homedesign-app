"""qa-agent, 2026-11-07: assembles the machine record for the fin2 / ED4 / modern-country fidelity check.

Reads (read only): the phase B record (rows of the frames this round did not touch), data/diffs.json
(from diffs.py: |after - before| > 2 levels, connected components on a 15 px dilation).
Writes qa/reports/2026-11-07-editorial-fin2-ed4-country.json. Usage: python3.12 -I assemble.py
"""
import copy
import json
import os

ROOT = "/home/user/homedesign-app"
HERE = os.path.join(ROOT, "qa/reports/2026-11-07-editorial-fin2-ed4-country")
R = "assets/renders/editorial-phase-b-2026-11-06/"
PB = json.load(open(os.path.join(ROOT, "qa/reports/2026-11-06-editorial-phase-b-fidelity.json")))
DIFFS = json.load(open(os.path.join(HERE, "data/diffs.json")))


def row(card, faithful, why, prev=None, fix=None, present=True):
    return dict(card=card, present=present, faithful=faithful, why=why, phase_b=prev, fix=fix)


def from_pb(frame, overrides):
    rows = copy.deepcopy(PB["frames"][frame]["rows"])
    out = []
    for i, r in enumerate(rows):
        prev = r["faithful"]
        r = {k: r[k] for k in ("card", "present", "faithful", "why", "fix")}
        r["phase_b"] = prev
        if i in overrides:
            r.update(overrides[i])
        out.append(r)
    return out


def counts(rows):
    c = dict(rows=len(rows), yes=0, partly=0, no=0)
    for r in rows:
        c[r["faithful"]] += 1
    return c


frames = {}

# ---------------- Nordic A: fin -> fin2 (code) -> ed4 (one masked pass) ----------------
nA = from_pb("nordic-A-fin", {
    2: dict(faithful="yes", why="ED4: sage chenille with the raised bubble grid, as p1-chenille-green; a lighter mint-sage, inside the card's family", fix=None),
    3: dict(faithful="yes", why="ED4: a square heathered slub-linen cushion (reads 50 x 50 at the same lean as the 45 x 45 sage one; width ratio 1.26 vs 1.11, inside +-15%); the back cushion behind it is continuous", fix=None),
    7: dict(faithful="yes", why="ED4: wider and shallower with a flared lip, H/D ~0.33 (card 0.30); warm white", fix=None),
})
frames["nordic-A-ed4"] = dict(
    file=R + "nordic-A-ed4.png", base="nordic-A-fin -> fin2 (code, 0 tokens) -> ED4 (seedream on crop [1180,650,2220,1235], 3 masked regions)",
    rows=nA, counts=counts(nA),
    fin2_traces=dict(
        right_wall_light="gone: no pale rectangle, no notch. New, minor: the sun patch under the light now starts at a straight vertical edge at x~2100 (a ~55-level step over ~6 px, y 586-660); it reads as a window-frame edge, not as a trace. A small bright tick under the light body. Faint diagonal strokes above the light only in the x4 stretch. Not blocking",
        pendant_zone="gone: no dark smudge, no pale blotch, clean even in the x4 stretch",
        outside_zones="two single pixels (1589,168) and (2293,201), 4-5 levels: immaterial"),
    ed4_mask_check=dict(changed_px=DIFFS["nordic-A fin2 -> ed4"]["changed_px"], components=DIFFS["nordic-A fin2 -> ed4"]["components"],
                        verdict="every change inside the three regions of crop_box [1180,650,2220,1235]; nothing outside moved; no seam at the mask edges at 100%"),
    final_test="ready",
)

# ---------------- Nordic B: not touched this round ----------------
nB = from_pb("nordic-B-fin", {})
frames["nordic-B-fin"] = dict(file=R + "nordic-B-fin.png", base="unchanged since phase B", rows=nB, counts=counts(nB),
                              final_test="ready (unchanged; the curtains' 'partly' is only that the S-fold heading is out of frame)")

# ---------------- Warm modern A: fin -> fin2 (brass) -> ed4 (pendant) ----------------
wm = from_pb("warm-modern-A-fin", {
    2: dict(faithful="yes", why="fin2: the brass now reads satin/brushed (p99 luminance 0.337 -> 0.272), no artefact at 100%", fix=None),
    3: dict(faithful="partly", why="ED4: now a stacked white fabric drum, widest ring third from the top, glow between the tiers, smaller, no longer crowds the art. But 6 rings with 3 below the widest; the card photo shows 2 below the widest (5 in all)",
            fix="code, 0 tokens: take out one lower ring and close the gap (plain wall behind); or show it with the note"),
})
frames["warm-modern-A-ed4"] = dict(
    file=R + "warm-modern-A-ed4.png", base="warm-modern-A-fin -> fin2 (brass, code) -> ED4 (seedream on crop [1000,0,1910,512], 1 masked region)",
    rows=wm, counts=counts(wm),
    fin2_traces=dict(brass="clean: 5 boxes only, 11403 px, no halo or banding"),
    ed4_mask_check=dict(changed_px=DIFFS["warm-modern-A fin2 -> ed4"]["changed_px"], components=DIFFS["warm-modern-A fin2 -> ed4"]["components"],
                        verdict="one component [1100,0,1827,262], inside region [1100,0,1820,255] (+ the 7 px dilation); nothing outside moved"),
    final_test="almost: the pendant has 6 rings, the card 5 (code fix, 0 tokens, or show with the note); the rug's chunky ribs stay as in phase B",
)

# ---------------- Boho A: -> fin2 (raffia x0.42) ----------------
bo = from_pb("boho-A", {
    0: dict(faithful="yes", why="fin2: ~166 px = the card's 30 cm against the frames; cowrie ring and coiled centre unchanged", fix=None),
})
frames["boho-A-fin2"] = dict(
    file=R + "boho-A-fin2.png", base="boho-A (gpt-image-2-5) -> fin2 (code: raffia x0.42 about its centre, plaster quilted from x 800-1440, y 70-160)",
    rows=bo, counts=counts(bo),
    fin2_traces=dict(
        seam="a straight vertical edge at x~398-400, y~250-460, where the zone cuts the bamboo light's glow: a 10-14 level step in 2 px; faint at 100%, plain in the stretch",
        ring="the old fringe's shadow: a darker ring at r 185-210 px from (587,369), 3-5 levels, mostly upper left (at y 200, x 420-450); visible only in the stretch",
        tick="a small grey dash at the raffia's lower right (~(650,440)); faint",
        verdict="the big trace (the oversized sun) is gone; the seam should be feathered (code, 0 tokens) before 'final test'"),
    diff_check=dict(changed_px=DIFFS["boho-A -> fin2"]["changed_px"], components=DIFFS["boho-A -> fin2"]["components"], verdict="one component inside the rebuilt zone; nothing outside moved"),
    final_test="not yet: feather the seam (code); the planter/basket sizes are still inverted (the prompt asked for it: accept or fix); the golden near-HDR look from phase B is unchanged",
)

# ---------------- Mediterranean A: -> ed4 (bowl) ----------------
me = from_pb("mediterranean-A", {
    3: dict(faithful="yes", why="ED4: a wide open cone with a thin flared rim and a thin tan clay line, H/D ~0.24 (card 21.3 x 5.2 = 0.244), sparse fine speckle as in the card photo; a little greyer in the shade (interior b* 17 vs 22 before). Trace: see ed4_traces", fix="code, 0 tokens: clean the ghost arc"),
})
frames["mediterranean-A-ed4"] = dict(
    file=R + "mediterranean-A-ed4.png", base="mediterranean-A (gpt-image-2-5) -> ED4 (seedream on crop [900,1000,1620,1405], ellipse region)",
    rows=me, counts=counts(me),
    ed4_traces=dict(ghost_arc="an echo of the old, deeper bowl's rim on the wall to the right of the new rim: a thin bright/dark doublet, +10-18 / -10 levels, from ~(1410,1150) to ~(1475,1200). Inside the mask (seedream drew it). Faint at 100%, plain at x4"),
    ed4_mask_check=dict(changed_px=DIFFS["mediterranean-A -> ed4"]["changed_px"], components=DIFFS["mediterranean-A -> ed4"]["components"],
                        verdict="one component inside the ellipse region (canvas [1008,1118,1504,1350]); nothing outside moved"),
    final_test="not yet: the white frayed cushion still cannot be told from the bench's generic ivory cushions (look-alike, from phase B); and the bowl's ghost arc (code)",
)

# ---------------- Japandi A: -> ed4 (jar, code) ----------------
ja = from_pb("japandi-A", {
    2: dict(faithful="yes", why="ED4 (code, x0.76 about x 666): H/W 1.57 -> 2.06 (card 30 x 15 = 2.0); matte sandy black, short neck, the branch untouched. But the code left traces (ed4_traces)",
            fix="code, 0 tokens: redo the fill round the narrowed jar"),
})
frames["japandi-A-ed4"] = dict(
    file=R + "japandi-A-ed4.png", base="japandi-A (nano-banana-2) -> ED4 (code: the jar x0.76; the seedream result unused)",
    rows=ja, counts=counts(ja),
    ed4_traces=dict(
        rim_wings="the old, wider rim still shows on both sides of the new one, dark against the bright window: x~622-632 and x~700-710, y~929-934. Visible at 100%",
        notches="dark notches where the old outline met the window frame: x~621 and x~710-715, y~1057-1070",
        base="the right bottom edge is a straight vertical cut, the contact shadow there is gone, a light sliver under the base (x~666-680, y~1129-1131) and a grey smudge to its right (x~715-730, y~1117-1127)",
        window_fill="the landscape refilled beside the jar is smeared but reads as out-of-focus glass; acceptable"),
    ed4_mask_check=dict(changed_px=DIFFS["japandi-A -> ed4"]["changed_px"], components=DIFFS["japandi-A -> ed4"]["components"],
                        verdict="one component round the jar [586,911,746,1140]; nothing outside moved (the traces are inside it)"),
    final_test="not yet: the jar's code traces (0 tokens); the pendant still waits for the sourcing answer (egg vs the card's 40 x 25 pumpkin); the sconces and the wabi-sabi cushion stay 'partly'",
)

# ---------------- Modern country A: new ----------------
mc = [
    row("cushions-aliexpress-farmhouse-floral-pillow-covers-166217 (pair)", "yes",
        "exactly two, square; cream ground, clay-rose flower heads on sage stems in offset rows, ~6-7 motifs across, as the card photo. Trace: a small invented insect-like glyph between motifs on the right cushion (~(1594-1608, 864-879)), reads as a fly at 100%",
        fix="code, 0 tokens: clone the ground over the glyph"),
    row("cushions-cj-chenille-check-milky-white", "yes",
        "one, square, milky white tone-on-tone raised check, ~22 checks across (card ~2 cm squares)"),
    row("vase-aliexpress-vintage-distressed-clay-vase-589009", "no",
        "a different vase: an amphora with a short neck and rolled lip, a small lug on the left shoulder and brown pits; squat, H/W ~1.55. The card (room SKU L, 31 x 15, H/W ~2.1) is a tall neckless ovoid with fine horizontal combed lines, no lug, no pits",
        fix="one targeted pass on the sill with the card crop, masked to the vase"),
    row("sill-vase-cj-cream-fluted-column-25", "yes",
        "fluted column, smooth knop, flared turned foot, cream glaze; a little stockier (H/W ~2.4 to the foot vs 2.9); height 0.72 of the clay vase (cards 0.80)"),
    row("table-runner-cj-linen-look-sage-fringe (4 Light Green)", "partly",
        "slub linen-look in grey-sage with brown flecks, short knotted tassels (13 across, card ~12), as the card photo. But too wide: ~457 px at the bowl's contact row against the bowl's 195 px and the cups' ~100 px, i.e. ~45-48 cm against the card's 33 (x1.4)",
        fix="the table pass (with the bowl), or accept with a note"),
    row("bowl-cj-speckled-ivory-wide-bowl-21", "partly",
        "speckled ivory with the tan rim, ~20 cm wide (right); but a deep rounded bowl, H/D ~0.45, not the wide 'rain-hat' cone (21.3 x 5.2 = 0.24). The same miss as mediterranean in phase B, fixed there by ED4",
        fix="the table pass (as mediterranean ED4)"),
    row("curtains-aliexpress-linen-blend-s-fold-180502 (pair)", "partly",
        "a pair, floor length, slub linen texture; but oatmeal/flax ~16 L* darker than the plaster beside it, where the card's #EDE7DB is close to a milk wall; a gathered pinch heading on a pole instead of the room SKU's S-fold; the sheerness cannot be seen (they hang beside the glass)",
        fix="code, 0 tokens: lift the two panels toward #EDE7DB; the heading: accept as a variant of the listing or a pass"),
]
frames["modern-country-A"] = dict(
    file=R + "modern-country-A.png", base="gpt-image-2-5 sunburst 2K, new (fetched at 0 tokens; soft knee on the highlights only)",
    rows=mc, counts=counts(mc),
    count_checks=dict(
        floral_pair="2", check_cushion="1", vases_on_sill="2", runner="1", bowls="1", seagrass_basket="exactly 1 (generic; at 100% it has three handles, a generation slip)",
        cups="3 (the prompt asked for 2)"),
    look_alikes=[dict(item="three cups on the table", verdict="fail until fixed",
                      why="the same speckled ivory glaze and tan rim as our bowl: they read as the bowl's set, which we do not sell (render-agent flagged it too)",
                      fix="code, 0 tokens: plain glaze on the cups (take out the speckle and the tan rim), or a sage glaze (the draft allows cream and sage ceramics)")],
    notes=[
        "the cardigan: at 100% a cardigan (button placket, ribbed cuffs); at frame size it reads as a cream knit throw. This style's throw is not chosen yet ('gauze or smooth knit in milk or sage'), so it can be read as a product. Generic in the brief: the designer's call",
        "the rug: a faded vintage-wash pattern is a third patterned textile beside the floral and the check (the draft allows two per frame); the prompt asked for it. Designer's call",
        "brass (candlesticks, lamps, sconces, the door knob): aged, soft highlights, not mirror-polished or champagne: inside the draft",
        "text, logos, brands: none",
    ],
    final_test="not yet: the clay vase is 'no' (a different vase), the cups are a look-alike of the bowl, the bowl is deep and the runner x1.4; the curtains' tone and the glyph are code",
)

order = ["nordic-A-ed4", "nordic-B-fin", "warm-modern-A-ed4", "boho-A-fin2", "mediterranean-A-ed4", "japandi-A-ed4", "modern-country-A"]
record = dict(
    report="qa/reports/2026-11-07-editorial-fin2-ed4-country.md",
    by="qa-agent", date="2026-11-07",
    scope="product fidelity only (same method as the phase B report): the fin2 code fixes (Nordic A, warm modern, boho), the four ED4 passes (Nordic A, warm modern, mediterranean, japandi) and the new modern-country-A. No lock, grading targets or density",
    inputs="assets/renders/editorial-phase-b-2026-11-06/ (fin2-codefix.json, fin2-before-after/, ed4.json, ed4_regions.json, ed4-sheet.jpg, jobs.json, the frames); briefs/render-editorial-phase-b-2026-11-06.md; data/products cards; docs/design-bible/modern-country-brief-draft.md; supplier crops in the session scratchpad (ed2-crops/, ed-crops/, viewed only)",
    method=dict(
        nothing_else_moved="independent diff of every pair: |after - before| > 2 levels on any channel, components on a 15 px dilation, boxes against the recorded zones (data/diffs.json)",
        traces="crops at 100% and x3-x4, plus a x4 contrast stretch; a trace counts only if it shows at 100%",
        proportions="against card dimensions and known neighbours on the same plane (bowl vs runner vs cups at the same table row; vase vs vase on the sill; cushion vs cushion)"),
    diffs=DIFFS,
    frames={k: frames[k] for k in order},
    summary_counts={k: frames[k]["counts"] for k in order},
    final_test={k: frames[k]["final_test"] for k in order},
    fixes=dict(
        code_0_tokens=[
            "boho: feather the vertical seam at x~400 (y 250-460) over ~40 px; optionally lift the faint ring",
            "mediterranean: clean the ghost arc right of the bowl's rim (wall from the rows above)",
            "mediterranean: tint the bench's generic back cushions to the sand linen the prompt asked for, so the white frayed cushion stands apart",
            "japandi: redo the fill round the narrowed jar (rim wings, the two notches, the base: put back a contact shadow)",
            "warm modern: take one lower ring out of the pendant (card: 5 rings, 2 below the widest), or show it with the note",
            "modern country: plain glaze on the three cups; clone out the glyph on the right floral cushion; lift the curtains toward #EDE7DB",
        ],
        one_targeted_pass=[
            "modern country, the table (one masked crop): the bowl to the rain-hat (as mediterranean ED4) and the runner to 33 cm",
            "modern country, the sill: the clay vase from the card crop (tall neckless ovoid, combed lines, no lug, no pits)",
        ],
        decisions=[
            "boho planter/basket sizes (the prompt asked for the inversion): accept or fix",
            "japandi pendant: the sourcing answer first",
            "modern country: the cardigan and the patterned rug (designer)",
            "the rug pile in Nordic A and warm modern: accept as the direction or an own pass (from phase B)",
        ]),
)

out = os.path.join(ROOT, "qa/reports/2026-11-07-editorial-fin2-ed4-country.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(record, f, ensure_ascii=False, indent=1)
for k in order:
    print(k, frames[k]["counts"])
print("wrote", out)
