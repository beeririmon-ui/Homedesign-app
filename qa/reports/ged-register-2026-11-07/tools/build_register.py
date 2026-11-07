"""qa-agent 2026-11-07: builds the single G-ED register qa/reports/ged-register-2026-11-07.json (version 1) from QA's own records:
the base rows of qa/reports/2026-11-07-editorial-fin2-ed4-country.json, the changes of 2026-11-07-ged-codefix-mc1-clay.json and
2026-11-07-ged-codefix5-clay-r3.json, this round's fix4 check (data/fix4.json), and master-designer's eye verdicts
(docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md §5-§7). Option ids come from data/story/story.json where a point names one,
else from the card's option axes by label, else the label as text. Usage: python3.12 -I build_register.py
"""
import glob
import json
import os
import re

REPO = "/home/user/homedesign-app"
R = "assets/renders/editorial-phase-b-2026-11-06/"
BASE = json.load(open(os.path.join(REPO, "qa/reports/2026-11-07-editorial-fin2-ed4-country.json")))["frames"]
STORY = json.load(open(os.path.join(REPO, "data/story/story.json")))
FIX4 = json.load(open(os.path.join(REPO, "qa/reports/ged-register-2026-11-07/data/fix4.json")))

CARDS = {}
for p in glob.glob(os.path.join(REPO, "data/products/**/*.json"), recursive=True):
    try:
        c = json.load(open(p))
    except Exception:
        continue
    if isinstance(c, dict) and c.get("id"):
        CARDS.setdefault(c["id"], c)

STORY_OPT = {}
for pair in STORY["pairs"].values():
    for f in pair.get("frames", []):
        for pt in f.get("points", []) or []:
            STORY_OPT.setdefault((f.get("qa_key"), pt["product"], pt.get("name_he")), pt.get("option"))


def option_for(card_id, label):
    """the card's option value ids whose label matches the label (case-insensitive substring), else the label text"""
    if not label:
        return None
    c = CARDS.get(card_id)
    if c and isinstance(c.get("options"), dict):
        out = {}
        for ax in c["options"].get("axes", []):
            for v in ax.get("values", []):
                names = [str(v.get("label_src", "")), str(v.get("label_he", "")), str(v.get("id", ""))]
                if any(label.lower() in n.lower() or (n and n.lower() in label.lower() and len(n) > 3) for n in names):
                    out[ax["id"]] = v["id"]
                    break
        if out:
            return out
    return label


def row(card_id, verdict, note, option=None, present=True, label=None, dot=None):
    dot = dot or ("yes" if verdict == "yes" else "no")
    return dict(card_id=card_id, option=option, verdict=verdict, note=note, dot=dot,
                card=card_id + (f" ({label})" if label else ""), present=present, faithful=verdict, why=note)


def from_base(key, overrides=None, splits=None):
    out, fixed = [], []
    for r in BASE[key]["rows"]:
        text = r["card"]
        if text.startswith("fixed furniture"):
            fixed.append(dict(what=text, verdict=r["faithful"], note="no card: no dot"))
            continue
        card_id = text.split(" ")[0]
        m = re.search(r"\(([^)]*)\)", text)
        label = m.group(1) if m else None
        if splits and text in splits:
            out += splits[text]
            continue
        v, note = r["faithful"], r.get("why") or ""
        if overrides and text in overrides:
            v, note, *rest = overrides[text]
            dot = rest[0] if rest else None
        else:
            dot = None
        lab = None if label in ("pair", "x2", "3 of 6", "3 of the series") else label
        opt = option_for(card_id, lab) if lab else None
        out.append(row(card_id, v, note, opt, label=label, dot=dot))
    return out, fixed


RUG = ("partly", "pile, not the card's flat braid; accepted as the direction with a note (designer); EDR1 failed (mc1.json, rugs)", "closeup_only")
frames = {}

rows, fixed = from_base("nordic-A-ed4", {"rug-cj-braided-wool-natural": RUG})
frames["nordic-A-ed4"] = dict(file=R + "nordic-A-ed4.png", state="final_test", state_source="qa/reports/2026-11-07-editorial-fin2-ed4-country.md (shown to the owner 2026-11-07)",
                              designer_eye="shown as final test before the gate; no open eye item", rows=rows, fixed_furniture=fixed)

rows, fixed = from_base("nordic-B-fin", {"curtains-aliexpress-linen-blend-s-fold-180502": ("partly", "reasonable; the S-fold heading is outside the frame", "closeup_only")})
frames["nordic-B-fin"] = dict(file=R + "nordic-B-fin.png", state="final_test", state_source="qa/reports/2026-11-07-editorial-fin2-ed4-country.md",
                              designer_eye="as nordic-A", rows=rows, fixed_furniture=fixed)

wm_split = {
    "cushions-cj-boucle-teddy (White, Milk tea)": [
        row("cushions-cj-boucle-teddy", "yes", "white boucle, two in the frame", None, label="White"),
        row("cushions-cj-boucle-teddy", "yes", "light milk-tea boucle", STORY_OPT.get(("warm-modern-A-ed5", "cushions-cj-boucle-teddy", "ציפית כרית בוקלה, תה חלב")) or option_for("cushions-cj-boucle-teddy", "Milk tea"), label="Milk tea")],
}
rows, fixed = from_base("warm-modern-A-ed4", {"pendant-cj-tiered-fabric-drum": ("yes", "ed5: 5 rings, the widest third, 2 below it, as the card"), "rug-cj-braided-wool-natural": RUG}, wm_split)
for r_ in rows:
    if r_["card_id"] == "cushions-cj-knitted-chenille-bean-green":
        r_["option"] = STORY_OPT.get(("warm-modern-A-ed5", "cushions-cj-knitted-chenille-bean-green", "ציפית כרית שניל סרוגה, קאמל")) or r_["option"]
    if r_["card_id"] == "sofa-cover-cj-cotton-muslin-fringe":
        r_["option"] = STORY_OPT.get(("warm-modern-A-ed5", "sofa-cover-cj-cotton-muslin-fringe", "שמיכת מוסלין כותנה עם פרנזים, חום פשתן")) or r_["option"]
frames["warm-modern-A-ed5"] = dict(file=R + "warm-modern-A-ed5.png", state="final_test",
                                   state_source="QA: qa/reports/2026-11-07-ged-codefix-mc1-clay.md; eye: master-designer, G-ED.10 and G-ED.13 pass (the ed5 verdict)",
                                   designer_eye={"G-ED.10": "pass", "G-ED.13": "pass"}, rows=rows, fixed_furniture=fixed)

rows, fixed = from_base("boho-A-fin2", {
    "planter-zendrop-seagrass-belly-basket-45": ("yes", "fin4: the larger of the two, as the cards; two handles"),
    "basket-cj-seagrass-belly-xl": ("yes", "fin4 x0.75 (inside +-15% of the cards' ratio); fin5: two handles")})
frames["boho-A-fin6"] = dict(file=R + "boho-A-fin6.png", state="final_test",
                             state_source="QA: qa/reports/2026-11-07-ged-codefix5-clay-r3.md; eye: docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md §5, §7",
                             designer_eye={"G-ED.10": "pass", "G-ED.13": "pass", "G-ED.16": "the clear-glass kettle and glass: written exception for this frame only (§7), no dot"},
                             rows=rows, fixed_furniture=fixed)

rows, fixed = from_base("mediterranean-A-ed4", {
    "cushions-cj-washed-cotton-frayed (White)": ("yes", "ed6: the three bench back cushions are this card's White 50 x 50 (x3, CJZT218451503CX): hue, fringe and size as ours")})
for r_ in rows:
    if r_["card"] == "cushions-cj-washed-cotton-frayed (White)":
        r_["card"] = "cushions-cj-washed-cotton-frayed (White x3, bench back)"
frames["mediterranean-A-ed6"] = dict(file=R + "mediterranean-A-ed6.png", state="not_yet",
                                     state_source="QA: qa/reports/2026-11-07-ged-codefix5-clay-r3.md (all rows yes); eye: §6, G-ED.13 fails (reads as golden hour, not 13:00)",
                                     designer_eye={"G-ED.10": "pass", "G-ED.13": "fail", "G-ED.16": "pass"},
                                     open=["the regional shade grade ed7 (render-agent, 0 tokens): QA G-ED.8-G-ED.12, then the designer's G-ED.13 again"], rows=rows, fixed_furniture=fixed)

rows, fixed = from_base("japandi-A-ed4", {"vase-cj-black-matte-stoneware-jar-30": ("yes", "ed5: H/W 2.05, clean")})
frames["japandi-A-ed5"] = dict(file=R + "japandi-A-ed5.png", state="not_yet",
                               state_source="qa/reports/2026-11-07-ged-codefix-mc1-clay.md; the designer holds it until sourcing (docs/proposals/tool-shells-and-qa-items-2026-11-07.md)",
                               open=["the pendant (sourcing, then a pass; JP1)", "the tripod column lantern (reads as a copy, G-ED.15)", "G-ED.12: raw 2.09 % clipped, mostly the pendant"],
                               rows=rows, fixed_furniture=fixed)

mc_over = {
    "vase-aliexpress-vintage-distressed-clay-vase-589009": ("yes", "fix3: H/W 2.05 (line >= 1.85), neckless, grooves; note: widest at the middle"),
    "table-runner-cj-linen-look-sage-fringe (4 Light Green)": ("yes", "mc1: ~33 cm (1.49 x the bowl, cards 1.55)"),
    "bowl-cj-speckled-ivory-wide-bowl-21": ("yes", "fix3: H/D 0.272 (render-agent) / ~0.24 (QA), line <= 0.28, card 0.244"),
    "cushions-aliexpress-farmhouse-floral-pillow-covers-166217 (pair)": ("yes", "exactly two, square, the card's block print; the glyph on the right cushion was removed in fix1"),
}
rows, fixed = from_base("modern-country-A", mc_over, {
    "curtains-aliexpress-linen-blend-s-fold-180502 (pair)": [row("curtains-aliexpress-linen-blend-s-fold-180502", "yes",
        "fix1: the card's tone; the gathered heading is the listing's 'Pull Pleated Tape' option, so the dot names it",
        STORY_OPT.get(("modern-country-A-mc1", "curtains-aliexpress-linen-blend-s-fold-180502", "זוג וילונות שקופים במראה פשתן, סרט קפלים")) or {"style": "pull-pleated-tape"}, label="pair, Pull Pleated Tape")]})
frames["modern-country-A-fix4"] = dict(file=R + "modern-country-A-fix4.png", state="almost",
                                       state_source="QA: this round (fix3 -> fix4, codefix6) on qa/reports/2026-11-07-ged-codefix5-clay-r3.md; eye: no master-designer G-ED.10 / G-ED.13 verdict yet",
                                       designer_eye={"G-ED.10": "pending", "G-ED.13": "pending"},
                                       fix4_check=dict(g_ed_8="three components only, at the sofa spot [1190,1095,1216,1121], the strip left of the vase [1879,622,1916,706] and the mullion [1981,535,2018,706]",
                                                       sofa_spot="gone: darkest pixel 111 -> 168 against the sofa's median 198 (its grain); clean at x5",
                                                       vase_left_line="still a faint light line along the old outline (max |dx| 24 at y 610, as in fix3): clear at x2-x3, faint at 100%: a note",
                                                       mullion="no longer flat (longest flat run 2 px)", data="qa/reports/ged-register-2026-11-07/data/fix4.json"),
                                       open=["master-designer's G-ED.10 / G-ED.13"], rows=rows, fixed_furniture=fixed)

register = dict(
    id="ged-register", version=1, date="2026-11-07", by="qa-agent", supersedes=None,
    schema=dict(
        frames="frames.<key>: key = the frame file's name without .png (the qa_key)",
        state="one of not_yet | almost | final_test | approved_for_site (docs/ops/quality-gate-g-ed-2026-11-07.md §3); master-designer's eye verdicts are folded in: a pending eye verdict keeps a frame at 'almost' at most, a failed one makes it 'not_yet'",
        rows="frames.<key>.rows: one row per product (and per option when the frame shows two options of one card). card_id = the card's id; option = an object of the card's option value ids (from data/story/story.json or the card's axes), a label as text when no id matched, or null for the card's default; verdict = yes | partly | no ('partly' is 'partial'); note = why; dot = yes | no | closeup_only (G-ED.5 and recipe §6: a dot only on 'yes', or on 'partly' through a faithful close-up)",
        compat="every row also carries the fields site/tools/lib/qa-frames.ts reads today: card (card_id plus the label), present, faithful (= verdict), why (= note)",
        fixed_furniture="frames.<key>.fixed_furniture: the board furniture without a card (no dot); kept out of rows",
        superseded_by="older frame keys that the site may still name, mapped to the frame that replaces them",
        pending_qa="frames that landed after this version and are not checked yet"),
    versioning="a new dated file per QA round, never an edit: qa/reports/ged-register-<date>.json, and qa/reports/ged-register-<date>-r<N>.json for a second round the same day; each has version (+1) and supersedes (the previous file). The site reads the file with the highest version",
    frames=frames,
    superseded_by={"modern-country-A-mc1": "modern-country-A-fix4", "modern-country-A-fix3": "modern-country-A-fix4", "boho-A-fin4": "boho-A-fin6", "boho-A-fin5": "boho-A-fin6",
                   "mediterranean-A-ed5": "mediterranean-A-ed6", "warm-modern-A-ed4": "warm-modern-A-ed5", "japandi-A-ed4": "japandi-A-ed5", "nordic-A-fin2": "nordic-A-ed4"},
    pending_qa=[dict(file=R + "mediterranean-A-ed7.png", record=R + "grade-med.json", note="the regional shade grade; QA G-ED.8-G-ED.12 next, then the designer's G-ED.13")],
)
out = os.path.join(REPO, "qa/reports/ged-register-2026-11-07.json")
json.dump(register, open(out, "w"), ensure_ascii=False, indent=1)
for k, f in frames.items():
    c = {v: sum(1 for r_ in f["rows"] if r_["verdict"] == v) for v in ("yes", "partly", "no")}
    print(k, f["state"], len(f["rows"]), c, [(r_["card_id"], r_["option"]) for r_ in f["rows"] if r_["option"]])
