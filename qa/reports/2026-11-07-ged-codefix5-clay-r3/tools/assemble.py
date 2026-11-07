"""qa-agent 2026-11-07: the machine record of qa/reports/2026-11-07-ged-codefix5-clay-r3.md. Reads data/*.json. Usage: python3.12 -I assemble.py"""
import json
import os

REPO = "/home/user/homedesign-app"
HERE = os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix5-clay-r3")
D = json.load(open(os.path.join(HERE, "data/diffs.json")))
G = json.load(open(os.path.join(HERE, "data/guardrails-boho.json")))
C = json.load(open(os.path.join(HERE, "data/clay-wm-r3.json")))
R = "assets/renders/editorial-phase-b-2026-11-06/"


def chk(i, v, n):
    return dict(check=i, verdict=v, note=n)


frames = {
    "modern-country-A-fix3": dict(
        file=R + "modern-country-A-fix3.png", against=R + "modern-country-A-mc1.png", record=R + "codefix5.json", state="almost",
        counts=dict(rows=7, yes=7, partly=0, no=0),
        checks=[
            chk("G-ED.8", "pass", "three components: the left seam band with the bowl [1021,1079,1266,1536], the vase [1876,533,2032,773], the right seam band [1570,1195,1634,1536]"),
            chk("G-ED.9 seams", "pass", "the steps at x 1120 / 1626 fell from 11-15 levels to <= 2.5 (one 4.3 on the table's front edge row); |dx| at the edge columns 3.8 / 3.1 against 2.4 typical; nothing at 100%"),
            chk("G-ED.4 bowl", "pass", "rim 219 px; render-agent's measure (base point to the rim plane) 0.272; QA's, base plane centre to rim plane centre, ~0.24 (card 0.244); the designer's line <= 0.28. Thin tan rim, sparse speckle, ~21-22 cm"),
            chk("G-ED.4 clay vase", "pass", "H/W 2.05 (106 x 218 px), the line >= 1.85, card ~2.1; neckless, grooves, no lug or pits. Note: widest at the middle, the card at the shoulder"),
            chk("G-ED.9 bowl fill", "fail (small)", "a dark-and-bright fleck on the sofa where the old rim was: L 111-126 against 180-230 with a 235-241 edge, ~4 x 6 px at (1199-1203, 1103-1110); visible at 100%"),
            chk("G-ED.9 vase fill", "note / small", "left of the vase a faint light line following the old outline (x ~1887-1895, y ~600-660, a 16-24 level step against 5-9): clear at x2, faint at 100%. Right of it the rebuilt mullion is a flat fill (L 209, no grain) and the light step by the shoulder shows at x4"),
        ],
        left=[dict(what="clone out the fleck on the sofa by the bowl's right rim", who="render-agent", cost="0"),
              dict(what="blend the left strip's edge beside the vase (the old outline line); optional: grain on the mullion strip", who="render-agent", cost="0")],
        story_points="the bowl and vase points in data/story/story.json (frame mc1) still fall on the products in fix3 (by coordinates; G-ED.17 not run)"),
    "boho-A-fin6": dict(
        file=R + "boho-A-fin6.png", against=R + "boho-A-fin4.png", record=[R + "codefix5.json", R + "grade-boho.json"], state="final_test_pending_designer",
        counts=dict(rows=9, yes=9, partly=0, no=0),
        checks=[
            chk("G-ED.8", "pass", "fin4 -> fin5: one component [2108,748,2293,1084] (door, handle, wall strip), no drift elsewhere; fin5 -> fin6 is the grade (global by design)"),
            chk("G-ED.9 door", "pass", "the door is rebuilt along its planks: jamb, stile, panel edge and sun stripes continuous, no blocks at 100% or x3"),
            chk("G-ED.2 basket", "pass", "two handles; the planter keeps its two"),
            chk("G-ED.9 grade", "pass", "no halo at the plaster mask's edges: a* of the plaster in the gaps between the frames and above them 4.5-5.8 like the open wall (5.0); leaves and sconces clean"),
            chk("G-ED.11", "pass", "no split (shadows b* 14.9, highlights b* 10.6); deepest shadow L* p1 11.0 (p0.5 9.4)"),
            chk("G-ED.12", "pass", "raw 0.153 % clipped; fin6 0.000 % (near clip >= 250: 1.15 %); fin5 had 0.001 %"),
            chk("G-ED.10 / G-ED.13", "open", "master-designer's eye, in parallel. QA's read: the plaster now off-white (a* 14 -> 5, b* 31 -> 20), the golden cast gone from the walls; the sun stripes and the lamp glows stay"),
            chk("G-ED.16", "open (from phase B)", "the clear-glass teapot and glasses: a generic prop under the boho draft's list; needs the designer's written exception"),
        ],
        left=[dict(what="written G-ED.10 / G-ED.13 verdict on fin6, and the teapot exception", who="master-designer", cost="0")]),
    "mediterranean-A-ed6": dict(
        file=R + "mediterranean-A-ed6.png", against=R + "mediterranean-A-ed5.png", record=R + "med-cushions.json", state="final_test_pending_designer",
        counts=dict(rows=11, yes=11, partly=0, no=0),
        checks=[
            chk("G-ED.8", "pass", "inside the two cushion boxes only"),
            chk("G-ED.3", "pass", "the two bench cushions now read as our White: lit Lab (70.3, 4.0, 11.8) and (73.9, 4.0, 12.0) against ours (70.8, 3.9, 11.8); cushion minus wall L +4.8 / +4.4 against ours +4.9; the fringe is the body's tone now (no light tops)"),
            chk("G-ED.2 / G-ED.4", "pass", "frayed self-fringe of the same listing; ~48-54 cm against the 50 x 50 terracotta in front (inside +-15%)"),
            chk("G-ED.6", "pass", "no longer a look-alike: the three back cushions are cushions-cj-washed-cotton-frayed White 50 x 50 x3 (designer, docs/proposals/med-bench-cushions-2026-11-07.md)"),
            chk("G-ED.9", "pass", "the Lab shift keeps the crinkle; the pale spot on the left cushion is the base frame's"),
            chk("G-ED.10 / G-ED.13", "open", "master-designer's written eye"),
        ],
        left=[dict(what="written G-ED.10 / G-ED.13", who="master-designer", cost="0"),
              dict(what="before the site: the White SKU's stock (B22), the bench-back-cushions slot, and hotspots for the three", who="sourcing-agent, master-designer, frontend-dev", cost="0")]),
}
unchanged = {"nordic-A-ed4": "final_test", "nordic-B-fin": "final_test", "warm-modern-A-ed5": "final_test_pending_designer (G-ED.10 / G-ED.13)",
             "japandi-A-ed5": "not_yet (pendant via sourcing and JP1, the tripod lantern, raw 2.09 % clipped)"}

clay = dict(
    folder="assets/blockout/house/framing/warm-modern-r3/", plan="house plan 1.3.3 section 0א (WMC1-WMC8)", measurements=C,
    projection="QA's own projection equals render-agent's r3 uv on five named endpoints (the track's start differs only in the chosen start point)",
    named_edges="8 of 9 named lines within 0 to -0.5 px at 1920 (r1: up to 4 px); the back-wall floor line -8 px as in r1: the strongest edge sits ~3 cm above Z 0, probably a skirting shadow gap the plan does not list",
    verdicts={
        "WMC6 (bench from Y 1.00)": "solved: pot to bench 90 px = 0.0234 of the width (>= 0.02); M0p bench corner u -0.0447, outside",
        "WMC7 (stack Y 2.65-2.95)": "solved: the armchair covers the stack over u 0.0229-0.0635 = 0.041, a clear overlap (>= 0.03); the sconce plate 0.22 m from the stack. The stack is cut by the frame edge on all 2,160 rows; in the 3 % overscan canvas it ends 28 px (0.0073) short of the canvas edge (the selfcheck's 0.0069): matters only if a pan shows the overscan (motion-agent)",
        "WMC8 (magazine holder at 35 x 19 x 27.5)": "not solved: 69 px = 0.018 from the armchair (< 0.02); basket 0.059 and table 0.035 clear. Waits for WMC9 / r4. The slots 1.9.1 box (top v 0.861) is the 40 cm proxy's; at the real size the top is v 0.927",
        "accepted 1.3.3": "arc start 1.9 px from the pot (documented exception, not measured as a line); basket top over the pot rim 1.30 % (above the 1 % line)",
        "vase on the bench": "89 px from the armchair, clear",
        "M0p corner (WMC3)": "arc tangent u -0.0108, outside",
    },
    reference_phase1=dict(
        verdict="yes, for pilot phase 1 (shell, fixed furniture and shadow, the cushions slot)",
        why="every shell line within 0.5 px of the plan except the floor line (explained); WMC6, WMC7 and the accepted tangents hold; the one open item, the holder (WMC8 -> WMC9), is a product slot outside phase 1",
        conditions=["r4's 2 cm holder shift must change only the holder proxy: QA re-runs the named-edge check on r4 (expected: no shell change), then gives the holder its verdict",
                    "the shell lock leaves the back-wall floor line out until the ~3 cm edge is confirmed in the plan",
                    "the pilot brief still names 'clay r2': the manager points it at r3 (or r4)"]),
)

record = dict(report="qa/reports/2026-11-07-ged-codefix5-clay-r3.md", by="qa-agent", date="2026-11-07",
              brief="the coordinator's message of 2026-11-07 (codefix5, grade-boho, med-cushions, clay r3)", gate="docs/ops/quality-gate-g-ed-2026-11-07.md",
              frames=frames, unchanged=unchanged, diffs=D, guardrails_boho=G, clay_r3=clay,
              tool_note="the story hotspots moved to data/story/story.json (pairs -> frames -> points); the G-ED doc's Q-ED2 still names site/tools/test-page/story-hotspots.json (now gone)")
json.dump(record, open(os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix5-clay-r3.json"), "w"), ensure_ascii=False, indent=1)
print({k: (v["state"], v["counts"]) for k, v in frames.items()})
