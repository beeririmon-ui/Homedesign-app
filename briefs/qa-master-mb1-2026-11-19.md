# Brief: QA on the bedroom's second frame, MB1 (qa-agent, 2026-11-19)

## Why
render-agent rendered MB1, the bedroom's second frame. The camera is at (1.60, 21.20), yaw 33.7, 24 mm, Z 1.05, tilt 0. The owner approved this frame (AP3-HOUSE2, FB11). The spend was 3,450 in 8 sends. The room now counts 22 products for sale, and 8 of them are biggest in MB1. This is a new frame, so this is a full stage-one QA for it, as in the MB0 rounds.

## Inputs
- **The render:** `assets/renders/master/warm-modern/mb1-2026-11-19/`:
  - the README, with the money, the count, what was done in code, what wasn't fixed, and the 10 QA regions;
  - `mb1-defaults.png` and `-frame.png`;
  - `mb1-qa-sheet.jpg`;
  - `layers/`, `shadows/`, `light/`, and `layers/manifest.json`;
  - `mb1-checks.json` and `jobs.json`;
  - `tools/run_all.sh`.
- **The spec:**
  - `briefs/wm-master-mb1-render-2026-11-19.md`;
  - chapters 13 and 13.11 of `docs/proposals/wm-master-bedroom-render-2026-11-17.md`;
  - chapters 1 and 8 of `docs/proposals/wm-house-20-2026-11-19.md`;
  - `docs/proposals/wm-mb1-forward-check-2026-11-19.md`.
- **MB0, for reference:** `assets/renders/master/warm-modern/stage1-2026-11-17/`, and its QA reports `qa/reports/2026-11-18-master-mb0/` and `2026-11-18-master-fb10/`.
- **The products:** the cards, and the SKU photos in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`. Read them there with `python3.12 -I`.

## What to check (0 tokens)
1. **Fidelity, per product,** against the card, the SKU photo and its look in MB0: shape, colour (R5 on lit areas) and size.
   - Pay most attention to the 8 products biggest in MB1: the rug, the waffle throw on the bench, the basket, the planter, the floor lamp, the magazine holder, the carafe and the candle holders.
   - render-agent reports ΔE00 against MB0 of 4–7.6 on the bedding, the pillowcases, the Pecan throw, the carafe and the candle holders, mostly in brightness from the new angle. Judge whether a visitor would read them as the same products.
2. **The rejection list and the manager's rulings.** The manager saw these at ×1; check them:
   - **The Pecan throw's fringes are visible** on the near right end, which falls about 50 cm, against about 10 in MB0. In MB0 the fringes are hidden by styling. Is this a rejection-list item (fringes over 3 cm), and can code fix it (hide or shorten the drop)?
   - **The bench (plan B, fixed, not sold):** the spec is a 5 cm seat on two solid end panels, *open between them*, in matte walnut, the same family as the hall bench. At ×1 it may read as a closed box or chest with a front panel. Check against the spec.
   - **Art A** has no close-up and no zoom.
   - **The magazine covers** are blank, per 13.11.
3. **The layers (RND2):**
   - recompositing with `run_all.sh` reproduces the output;
   - 0 pixels outside the masks;
   - shadows sit one z below their product;
   - light layers use screen;
   - the carafe pixel-yield step on the bedding layers is sound;
   - the black point is within WM-G1 (12.09 reported).
4. **At ×1–×2, as a frame:** the 10 regions in the README. Check edges, halos, the GrabCut cutouts and the contact shadows, including the soft shadow on the bedding beside the waffle roll. Does it read as the same room as MB0 and the same house, at the magazine level (FB5), and lived-in (FB6)?
5. **The count:** each product once per room, in the frame where it's biggest, plus V7Q6. Confirm 22 for sale, with 19 passing V7Q6.

## Outputs
- `qa/reports/2026-11-19-master-mb1/README.md`: pass or fail per item, with numbers. Evidence images only when needed; scripts in the scratchpad.
- Low findings go to `status/backlog-low.md`.
- A status line: "עבר QA (MB1 שלב 1; לבעלים; לא לאתר לפני רישום 1.3.9)", or the blocking findings, with whether code can fix each. A model fix is a question for the manager.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's files.
- **Another render-agent is working on the hall.** Don't touch its files.
- Keep scratch files small and delete them when done. The disk is tight.
- Return a short Hebrew summary: the five items, pass or fail with numbers, and whether MB1 passed.
