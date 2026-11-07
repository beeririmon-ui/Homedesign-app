# Brief: QA on the story prototype `/test/story/` (qa-agent, 2026-11-07)

frontend-dev built the story-first test page, following the owner's DIR1 decision and the brief `briefs/site-story-prototype-2026-11-07.md`. The evidence is in `qa/reports/2026-11-07-site-story-prototype/` (README, evidence.json, screens). The hotspots are in `site/tools/test-page/story-hotspots.json`; they are temporary and placed by eye.

## Check
1. **G-ED.17 and G-ED.18 on Nordic A and B** (`docs/ops/quality-gate-g-ed-2026-11-07.md`).
   - Every dot sits on its product, and every touch box covers the product's visible part.
   - The touch boxes meet the 4:5 phone-crop threshold you proposed: ≥44×24 CSS at 390.
   - No two dots overlap.
   - The coverage holds across the story.
   - frontend-dev reports the wall sconce in Nordic A at 12×24 CSS on the phone, below the threshold. Confirm or refute this, and list any other products below the threshold.
2. **Only "yes" products carry a dot.** Check this against your 2026-11-07 fidelity table. "Partial" products (the rugs, the Nordic B curtain, the warm-modern pendant) appear in the list without a dot.
3. **The frames are marked "טיוטה / בדיקה" and appear only on the test route.** No other page links to them. Check the build output.
4. **Spot-check frontend-dev's numbers:**
   - the first-load weight (168–275 KB);
   - LCP 1.14 s on a throttled phone;
   - contrast ≥ 6.27:1;
   - axe with 0 violations.

   Rebuild and run where you can, with the local Chromium at `/opt/pw-browsers/chromium` (no `playwright install`): `cd site && npm run build && npm run test:story` or the repo's equivalent. Say exactly which commands you ran and their results.
5. **The one e2e failure** (`hotspots.spec` at 1280, the magazine holder in the room engine): confirm the cause, the temporary M0 lines not updated after slots 1.8.

## Output
- `qa/reports/2026-11-07-site-story-prototype-qa.md` (Hebrew) plus `.json`.
- Overlays of the dots and boxes on both frames, under the folder of the same name.
- A verdict: may the page be shown to the owner as a prototype, and what must change before that, if anything.

## Fixed rules
- New files only, no commits, no var2. No network beyond what the local build needs.
- Return a short Hebrew summary.
