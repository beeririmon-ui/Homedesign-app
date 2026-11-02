# Brief: measurable quality gates, and an audit of the process (qa-agent, 2026-11-02)

**The owner (2026-11-02):** "נוודא שהתהליך עומד בכל הסטנדרטים , שיצא האתר הכי מדהים ומרהיב ומעוצב ובשפת מגזין עיצוב הרמה הכי גבוהה שאפשר, שהממשק והמעברים יהיו וואוו ברמות הכי גבוהות שיש"

Recorded in studio rules א.6: every deliverable is checked against written, measurable quality gates.

## The task
1. Write the quality gates for every type of deliverable.
2. Audit the current work against them: what passed, what is missing, and what blocks.

This is report mode: you write new files and change nothing else.

## Read first
- `CLAUDE.md` (the gates and "נכס שלא עבר QA לא נכנס לאתר"), `docs/studio-rules.md` (א, ג, ו, ז), `docs/ops/agent-playbook.md`.
- `docs/skeleton-spec.md` (layers, cameras, animations, performance targets) and `docs/design-bible/nordic.md` (light, grading and motion, the forbidden list, the interface).
- `docs/house-plan.md` and `docs/house-plan.json` (cameras, transitions, play times).
- `briefs/nordic-house-render-2026-10-24.md`: §6 (swap methods), §7, §8, §8.1, §9.
- `docs/render-recipe-nordic-2026-10-24.md`, `docs/render-recipe-verdict-2026-10-24.md`, `docs/render-wow-pass-2026-11-02.md`.
- `docs/transitions-plan-2026-11-02.md`, `docs/transitions-render-plan-2026-11-02.md`, `assets/renders/transitions/README.md`.
- `docs/focus-mode-spec-2026-11-02.md` (§5 is the integration checklist for you).
- `assets/qa/` (the earlier QA reports, and how they measured).
- The site: `site/README.md` (the test scripts), and `site/screens/`.

## Output 1: `docs/ops/quality-gates-2026-11-02.md` (Hebrew), plus `docs/ops/quality-gates-2026-11-02.json`
For each deliverable type, write the gate:
- **Criteria**, with thresholds.
- **The method and tool:** the existing scripts first:
  - `site/tools/transitions/pan_reproject.py check`, the lock and registration checks;
  - the swap-diff measurement from §6;
  - `scripts/economics/no_loss.py --check`;
  - the site's `npm test`, `e2e`, `a11y`, `lighthouse` and `budget`.
- **Who checks:** qa-agent, master-designer, or the owner.
- **The evidence file** each check leaves.

The deliverable types:
1. A room frame or still (fidelity to the product, the clay lock, light and exposure against the Bible's targets, the forbidden list, density, window balance).
2. A product layer and a variant swap (alpha-bounded difference outside the product, the contact shadow, edges and stems; ו.5).
3. A code pan, a video transition and a frame sequence:
   - speed continuity at the joins;
   - flicker and warping;
   - objects that change between frames;
   - landing exact to the pixel on the shown frame (ו.6);
   - 60 fps on screen;
   - the phone crop path (§8.1).
4. The focus-mode loop (§9 and the spec §5).
5. A site page or component in the magazine language (א.6). Leave the visual criteria as a placeholder: master-designer is writing the art direction now (`docs/site-art-direction-2026-11-02.md`), and its checklist slots in here.
6. Performance: first load, room load, transition weight, fps on a mid-range phone (skeleton spec targets).
7. Accessibility (ו.3: WCAG AA and ת"י 5568).
8. Commerce truth:
   - the price never loses money (ה.13);
   - the shown product matches the sold product;
   - the stock is live.

**Every threshold cites its source** (a document and section). Where no binding number exists, propose one and mark it "הצעה".

## Output 2: the audit, a section in the same document
1. **What was delivered since 2026-10-24:** recipe v5 and v6, the phase B drafts, the transitions test (`assets/renders/transitions/test-2026-11-02/`), the focus-mode spec, and the current site screens.
   For each one:
   - the gate it passed, with evidence;
   - what is missing;
   - whether it may go into the site.

   The v7 frames and the round-4 clays are still being rendered. List them as "in progress", and only state which gates they will need.
2. **The site's own checks:** run `npm run typecheck`, `npm test` and `npm run lint` inside `site/`, only if `site/node_modules` already exists. Don't install anything. Report the results with the failing lines.
3. **Gaps in the process,** ranked by risk. For each gap:
   - what goes wrong if it stays;
   - the fix;
   - the owner agent.

   Include gates that have no tool yet, and places where an agent reported a check without leaving evidence.

## Acceptance
- The JSON passes `python3 -m json.tool`. Each gate has `id`, `deliverable`, `criteria[]` (with `threshold`, `source`, `method`), `checker` and `evidence`.
- No claim without a file or a measurement behind it.

## Fixed rules
- New files only. Don't edit any existing file. No commits.
- No var2 calls. Don't install packages, and don't use the network.
- The render-agent's in-progress folders are read-only, and only if needed: `assets/renders/*/nordic/v7/`, `assets/renders/house-nordic-v7-2026-11-02/`, `assets/blockout/house/framing/round4/`.
- Return a short summary in Hebrew: the top 5 gaps and the site check results.
