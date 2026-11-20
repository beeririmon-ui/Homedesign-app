# Brief: QA on the warm-modern kitchen and dining, D1 and D2, stage one (qa-agent, 2026-11-20)

## Why
The owner approved the kitchen and dining (AP2-NEW). render-agent rendered stage one: two frames, D1 and D2, from the same point; 21 products for sale (12 in D1, 9 in D2); and the sample slot, the pendant, in 3 variants (V2 done in code). The spend was 5,300, exactly the plan. It was rebuilt after a container restart, and render-agent found and fixed two code bugs left by the earlier session: the WM-G1 toe was never applied, and the projection between frames overwrote layers. This is a new room, so this is a full stage-one QA.

## Inputs
- **The render folder:** `assets/renders/dining/warm-modern/stage1-2026-11-20/`:
  - the README, with the money, the count, the code fixes, the decisions for review and the 10 QA regions;
  - `D1-defaults.png` and `-frame.png`, and `D2-defaults.png` and `-frame.png`;
  - `D1-V2-frame.png` and `D1-V3-frame.png`;
  - `qa-sheet.jpg`;
  - `layers/`, `shadows/`, `light/` and `manifest.json` (its `rebuild` key gives the rebuild order);
  - `checks.json`, `jobs.json` and `tools/`.
- **The clay:** `assets/blockout/house/framing/wm-dining-2026-11-20/`.
- **The spec:**
  - `docs/proposals/wm-kitchen-dining-render-2026-11-19.md`, where chapter 10 overrides the rest; the rejection list is in chapter 7, and what QA checks is in 6.5;
  - the kitchen chapter in `docs/design-bible/warm-modern.md` (1.1).
- **The products:** the cards; `room_variants` "warm-modern.kitchen-dining" or the card's default gives the SKU. The SKU photos are in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`, with `picks/new-rooms-photo-check.json`. Read them with `python3.12 -I`.

## What to check (0 tokens)
1. **Fidelity, per product:** shape, colour (R5 on lit areas) and size against the card, the SKU photo and the clay. Pay most attention to:
   - the items rescaled in code (the tray, the dispenser, the grinders, the oil, the board, the paper stand, the jars, the olive);
   - the runner's caramel;
   - the pendant V1, with its 30 cm rod and hanging line;
   - V2, which is V1's body with a white cord: is that a faithful rendering of its SKU, and does it read as a variant at all?
   - V3.
2. **The rejection list and the Bible.** Also check the curtain: it's about 55 cm wide against the 20 cm stack of KD-5, and partly over the glass.
3. **The layers (RND2):**
   - rebuild per `manifest.json` → `rebuild`;
   - 0 pixels outside alpha, shadow and light;
   - the 82 and 69 px of ≤3/255 light rounding in the variants: accept or not;
   - shadows sit one z below their product;
   - light layers use screen;
   - the black point is within WM-G1 (11.38–11.49);
   - D1 and D2 read as one room (ΔE00 0.88–2.96).
4. **At ×1–×2, per region:** the 10 regions in the README. Then the whole frame. Does it read as the same house as the living room, the bedroom and the work room, at the magazine level (FB5), and lived-in (FB6)?
   **And FB9, products that "take the stage":** the manager's eye says D2 reads sparse, with large blank tall-cabinet fronts and small products. Measure and say whether a visitor would read D2 as empty, and what would fix it. The options are a tighter crop (a camera change, which is a 1.3.9 item and needs the designer), the KD-z zoom frame, or more or larger products.
5. **The count:** each product once per room, plus V7Q6. render-agent counts 21 of 21, with 10 by V7Q6 in D1 and 5 in D2.

## Outputs
- `qa/reports/2026-11-20-kitchen-dining/README.md`: pass or fail per item, with numbers. Low findings go to `status/backlog-low.md`.
- A status line: "עבר QA (המטבח ופינת האוכל שלב 1; לבעלים לאישור 3; לא לאתר לפני רישום 1.3.9)", or the blocking findings, with whether code can fix each. The D2 "takes the stage" judgment is a separate line for the manager.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's files.
- **Another render-agent is fixing the work room.** Don't touch its folders.
- Never run `git stash`, `git checkout` or `git reset`.
- Keep scratch files small and delete them when done. The disk is tight.
- Return a short Hebrew summary: the five items, pass or fail with numbers, plus the D2 judgment.
