# Brief: adopting the new direction in the binding documents (master-designer, 2026-11-07)

**The owner (2026-11-07), four answers.** All four are recorded in `status/decisions.json` and in studio rules ז under "הכיוון החדש מאומץ":
- **DIR1, story first:** the site opens on a full story frame per room and style. Touching a product opens "קנה את המראה". From there the customer enters the "עצב בעצמך" tool: the variant wheel and the walk through the house.
- **DIR2, each style is a different house, everywhere:** every style has its own architecture (windows, frames, ceiling, floor) in the story frames **and in the tool**. So CR3 and CR3b apply now, not after phase B. This replaces studio rule ב.1. I added a note there: the room program (rooms, paths, slots) stays the shared base unless you propose otherwise and the owner approves.
- **CR: CR1–CR9 of your `docs/creative-review-2026-11-06.md` §5 are adopted, all of them.** I already updated studio rules ו.5 (CR2) and ג.5 (CR7), plus the goal in `CLAUDE.md`. qa-agent writes the G-ED gate (CR9) in parallel, from your §4 acceptance and CR5's guardrails.
- **MC1:** two targeted passes in modern country (the table, the sill). render-agent runs them after its code fixes. Not your task.

QA's latest report, `qa/reports/2026-11-07-editorial-fin2-ed4-country.md`, finds Nordic A (ed4) and B ready as "final test" frames. Warm modern is almost ready. Boho, Mediterranean, japandi and modern country are not ready yet.

## Task 1: write CR1, CR3/CR3b, CR4, CR5, CR6 and CR8 into the documents
Use your proposed texts from §5. Each document gets a version bump and a dated changelog line citing the decision (CR, DIR1, DIR2, 2026-11-07). The documents:
- **`docs/skeleton-spec.md` (CR1 + DIR1 + DIR2):**
  - the three layers and the site flow (story → product card / "קנה את המראה" → the tool);
  - which assets each layer needs;
  - replace "אותו בית, סגנונות מתחלפים" (line 21) with the per-style architecture rule.
- **`docs/house-plan.md` + `.json` (CR3, CR3b):** say exactly what the house plan still binds. My suggestion: the room program, the openings' positions, the paths and the slots, for the tool. Then say what each style may change: window shape and frames, reveals, ceiling, floor, wall finish, maybe arches. Say where the per-style architecture lives: a section per style in the style's Bible, or one file per style; your call. Do the same for `docs/proposals/style-pools.md` principle 2. **If a style's concept needs moving an opening, a camera or a slot in the tool, don't decide it.** List it as an owner question with your recommendation.
- **`docs/design-bible/nordic.md` → 1.9 (CR4, CR5, CR6):** story-frame camera, light story and grading guardrails, story-frame density. All of this applies to story frames only; the tool's rules stay as they are and are labelled "the tool". Fold in what we learned in the editorial test, phase B and ED4. Two things in particular:
  - **the "imitation set" rule:** an unsold item glazed like our product fails (the country cups);
  - **products the model reshapes:** these get a targeted pass or a code fix before QA.
- **New recipe `docs/render-recipe-story-v1-2026-11-07.md` (CR8):**
  - the model per style (ED3: your choice per style; say which and why from the results);
  - the prompt structure, and the references (how many, which crops);
  - the fidelity route: seedream-5-pro on crops with object masks, composited back in code; code fixes for scale and ring counts; nothing changed outside the masks;
  - light post-processing only;
  - the cost per frame, and the order of work: base frame → QA → code fixes → targeted passes → QA → owner.
- **The tool's shells per style (CR3b, DIR2):** a short plan. What a per-style shell in the tool costs (clay, shell renders per camera), and in which order (living room first, Nordic as is). Mark the costs as estimates. This becomes the next owner question about spend; nothing is approved yet.

## Task 2: QA's open design items (`qa/reports/2026-11-07-...` §5, "החלטות")
For each item, decide within your authority. Choose one of: accept it as the direction (with a note), a code fix (0 tokens, render-agent), or a targeted pass (state the cost; that becomes an owner question). The items:
- modern country: the cardigan, and the patterned rug;
- boho: the planter and basket sizes are inverted (the prompt asked for it);
- the rug pile in Nordic A (pile, not a flat weave) and the thick rug in warm modern;
- japandi: the paper pendant. It must not read as a copy of a specific known design (Bible forbidden list). Also, its shape vs the card (egg vs a 40×25 pumpkin) waits on sourcing; say what you would do meanwhile.

## Fixed rules
- Edit only the binding documents named in Task 1, and add the new files.
- No renders, no var2, no commits.
- Do not touch studio rules or `CLAUDE.md`; I keep those.
- Return a short Hebrew summary:
  - per document, the version and the gist of the change;
  - the per-style architecture rule in two lines;
  - the tool-shell plan with its cost estimate;
  - per Task 2 item, your decision;
  - any owner questions, each with a recommendation.
