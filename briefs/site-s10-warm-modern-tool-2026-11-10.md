# Brief: S10, the warm-modern house in the room engine with the wheel (frontend-dev, 2026-11-10)

This continues the interface track, `briefs/site-interface-track-2026-11-07.md`. Read it for the working rules: questions don't block, no commits, full checks, evidence. The previous run of S10 stopped for lack of context. It made only one change, the status label in `site/tools/make-story.ts` and `site/e2e/story.spec.ts`. That change is in the tree; check it and keep it.

## The background
- **What the owner approved:** phase 1 of the warm-modern tool pilot, in approval 3 (AP3-WM, 2026-11-07, in `status/decisions.json`).
  - It passed QA in `qa/reports/2026-11-07-pilot-phase1-v3c-verify.md`.
  - The approved files are the v3c display files in `assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07/`: `shell-furniture-v3-graded-v3c.png` and `composite-set-{A,B,C}-v3-graded-v3c.png`.
- **What the site shows today:** the draft at `/story/living-room/warm-modern/tool/` (`site/web/src/story/tool-draft.ts`, `tool_draft` in `data/story/story.json`) uses old, pre-QA files (`shell-graded.png` and the like). It has no product selection.
- **The separate layers are on the way:** render-agent is exporting them now, at 0 tokens, to `layers-v3c/` in that folder: `base.png`, `cushions-set-{A,B,C}.png` and `manifest.json`, with the default set B. The brief is `briefs/render-wm-tool-layers-v3c-2026-11-10.md`. Until they arrive, build against the manifest format, with a fallback to the full composite per set. It's visually equivalent: the swap-diff is 0 outside the products.

## The decision (manager, 2026-11-10): into the room engine, with the wheel
The goal in `CLAUDE.md` is "בוחר וריאציה מגלגל מוצרים ורואה את החדר מתעדכן", and DIR2 gives each style its own house in the tool. So the warm-modern house goes into **the existing room engine** (the one with `VariantWheel`, `/rooms/living-room/`) as a second house, not as a paper picker on a static page.
1. **The engine supports houses:**
   - Every house has its own shell and layer stack, from data.
   - The URL is `?style=warm-modern`, the S3 default. The default house stays Nordic.
   - Don't break anything in the Nordic house: the e2e, the hotspots and the swap-diff report.
2. **The warm-modern house:**
   - **The layers:** base plus the cushions slot.
   - **The cushions slot:** the wheel, with 3 options, sets A/B/C, and the default B per `data/selections/living-room.warm-modern.json`.
   - **Names and prices:** from the cards.
   - **Selling:** a set is sold as a set, with a single unit as an option (SET1). Reuse the S4 logic, including PRE1/MED1, and no price means no add button.
   - **The other slots** in this house have no layers yet. They're shown as part of the base, with no wheel and no dot.
3. **The status label** of the warm-modern house in the engine: "הבית המודרני החם, שלב 1: אושר. עוד לא באתר הציבורי". It stays behind `HD_PUBLIC=0`.
4. **The soft switch between houses:**
   - Move the S3 transition (1.0 s, and 0.3 s with reduced motion) into the engine, and measure it again.
   - The draft route `/story/living-room/warm-modern/tool/` becomes a 301 to the engine with `?style=warm-modern`.
   - Every "עצב בעצמך" button in the warm-modern story points at the engine.
5. **Encoding:** WebP/AVIF at the existing sizes, inside the budgets. Room JS stands at 77.9 of 80 KB. If the house code doesn't fit, split it into a lazy chunk; don't raise the budget.

## Acceptance
- **All the checks:** typecheck, lint, format:check, vitest, e2e, a11y and budget.
- **A swap e2e on the warm-modern house:**
  - changing a set changes nothing outside the cushion area (once `layers-v3c/` exists; until then, mark it skipped with a reason);
  - the wheel reaches all three sets;
  - B is the default.
- **The house-switch e2e:** one box for all the layers, and the timing.
- **Evidence in `qa/reports/2026-11-07-site-track/s10/`:** a README, screens at 400 and 1280 for each of the three sets, and the transition timing.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm.
- If your context runs low, stop at a point where the checks pass, and write a "where I stopped" section in the README.
- Return a short Hebrew summary: what was built, the checks, questions with defaults, and what comes next.
