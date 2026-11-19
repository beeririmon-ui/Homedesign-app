# Brief: QA on the hall's first products, HT2 and HDx2 (qa-agent, 2026-11-19)

## Why
render-agent added the hall's first four products for sale to the approved still HT2, and carried the wall light to HDx2 in code (`briefs/wm-hall-ht2-products-2026-11-19.md`; FB11). The products are the travertine-walnut wall light A (lit), the walnut pegs, the Khaki waffle throw on the bench, and the cream rope basket under it. The spend was 960. The arrival must not break: these are layers shown at rest only.

EFF1.2: the stills themselves passed QA (`qa/reports/2026-11-18-arrival-stills/`). Check only the new layers and anything they touch.

## Inputs
- `assets/renders/hall/warm-modern/hall-products-2026-11-19/`:
  - the README, with the money, the code fixes, the 5 regions and the two notes for the designer;
  - `ht2-products.png` and `-frame.png`;
  - `hdx2-products.png` and `-frame.png`;
  - `layers/manifest.json` and `hdx2/manifest.json`;
  - `checks.json`, `jobs.json` and `tools/`.
- The approved stills, in `assets/renders/hall/warm-modern/hall-2026-11-18/`.
- The spec: chapters 4, 8.1 and 8.2 of `docs/proposals/wm-house-20-2026-11-19.md`.
- The SKU photos in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`, with `picks/house20-photo-check.json`. Read them there with `python3.12 -I`.

## What to check (0 tokens)
1. **Fidelity, per product:** shape, colour (R5 on lit areas) and size against the card, the SKU photo and the clay. Specifically:
   - the lamp's scale (it was resized from 9.2×31 to 6.5×28);
   - the pegs' colour (they may read reddish against the photo's walnut) and their tilt;
   - the throw's 7.5 cm thickness and its flattened cells;
   - the basket being cream, not grey or pink.
2. **The layers (RND2):**
   - 0 changes outside the layers, against HT2 and HDx2;
   - shadows sit one z below their product;
   - light layers use screen;
   - the black point is within WM-G1.
3. **At ×1–×2:** the five README regions. In HDx2, the side of the lamp block was stretched from 5 to 27 px, so check whether it shows. Check edges, halos and contact shadows.
4. **The designer notes:**
   - 35% of the basket is hidden behind the hanging panel;
   - the lamp's walnut block is 31% more saturated than the bench seat.

   Is either visible or a problem at ×1?
5. **The arrival:** confirm that nothing in the approved stills or clips changed. The products are separate layers only.

## Outputs
- `qa/reports/2026-11-19-hall-products/README.md`: pass or fail per item, with numbers. Low findings go to `status/backlog-low.md`.
- A status line: "עבר QA (מוצרי המבואה ב-HT2 ו-HDx2; לבעלים; לא לאתר לפני רישום 1.3.9)", or the blocking findings, with whether code can fix each.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's files.
- **Another QA run is checking the bedroom MB1.** Don't touch its report.
- Keep scratch files small and delete them when done. The disk is tight.
- Return a short Hebrew summary: the five items, pass or fail with numbers.
