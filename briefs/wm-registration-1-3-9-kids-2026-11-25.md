# Brief: register the kids' rooms, 1.3.9 addendum (master-designer, 2026-11-25)

## Why
The owner answered AP3-KIDS with "Approved" on 2026-11-25 (`docs/studio-rules.md`). That approves:
- the boy's room and the girl's room, warm-modern, stage one;
- their registration in the binding documents, as for the other approved rooms in 1.3.9 (AP3-KW, your log in `docs/proposals/wm-registration-1-3-9-2026-11-24.md`).

The owner also asked for faster progress. Keep this tight.

## Scope
- **Register:** the cameras, `style_shells.warm-modern.kids-boy` / `kids-girl` (or the house's existing naming for the kids room and its `girl_offset_y`), the fixed, not-sold furniture (the walnut bed, desk and chair), and the product slots of both rooms, including the wheel (the folded throw, V1–V3, in both).
- **Slots from the approved product list:** also register the slots that are in the approved product list (AP2-NEW, ch. ד of the kids proposal) but not rendered yet. Each has a planned position in the proposal. Mark them as not yet rendered.
  - `desk-bin` (gap ג16). The cards sit in `data/products/kids/under-desk-bin/`, so choose one name and say which. Sourcing will move the cards if needed.
  - `floor-cushion` (ג6 / ג15).
  - `night-light` (ג7).
  - Any other ד.6 gap with a planned position.
- **The truth is the rendered, QA-passed frames.** Where the render moved something from the proposal, register the rendered position.

## Inputs
- The renders:
  - `assets/renders/boy/warm-modern/stage1-2026-11-24/`;
  - `assets/renders/girl/warm-modern/stage1-2026-11-24/`.

  Each has a README, `manifest.json`, `checks.json` and `plate-compose.json`.
- The clay: `assets/blockout/house/framing/wm-kids-2026-11-24/`, including `selfcheck.json`.
- The QA report: `qa/reports/2026-11-24-kids-stage1/README.md`. Both rooms passed, after re-check 2.
- The proposal: `docs/proposals/wm-kids-rooms-render-2026-11-19.md`. Chapter ד overrides א–ג. ג.3 is the registration proposal.
- The binding documents you edit:
  - `docs/house-plan.md` and `docs/house-plan.json` (now 1.3.9);
  - `data/slots/kids.json` (1.0.4).
- Your 1.3.9 log, for the form and the conventions (`styles` on warm-modern-only slots, placement values).
- The vitest failures still open, all kids:
  - `kids/under-desk-bin` ×5: "not a slot", and "placement" missing;
  - `kids/floor-cushion` ×1;
  - `kids/night-light` ×1.

## Outputs
1. **The house plan.** Update `docs/house-plan.md` and `docs/house-plan.json` with an addendum to 1.3.9: one history line that names AP3-KIDS (2026-11-25) and what it took in. Call it 1.3.9a if the files' convention prefers a new number.
2. **The slots.** Bump the version of `data/slots/kids.json`, with an `update_…` note in the file's style. Give every slot its z, frame membership, placement and `styles`.
3. **A short log** at `docs/proposals/wm-registration-1-3-9-kids-2026-11-25.md`, covering:
   - what was registered, and from where;
   - what wasn't, and why;
   - the slot name for the bin;
   - the placement value for each new slot, which sourcing needs;
   - any cards with no approved slot.

## Acceptance
- **JSON:** every touched file parses. The manager runs `json.load` and vitest after you.
- **vitest:** after your edits, plus sourcing's placement fix for the 5 bin drafts, it should be fully green.
- **The other rooms and styles** are unchanged.

## Fixed rules
- 0 tokens and no var2.
- Edit only `docs/house-plan.*`, `data/slots/kids.json` and the new log. Don't touch `data/products/`, the Bible, the studio rules, the render folders or `site/`.
- Return a short Hebrew summary: what was registered, what wasn't, and the list for the manager.
