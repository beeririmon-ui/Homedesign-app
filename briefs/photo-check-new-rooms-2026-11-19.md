# Brief: photo sheets for the new rooms (general agent, 2026-11-19)

## Why
master-designer has designed four new warm-modern rooms: the kitchen and dining, the work room, the boy's room and the girl's room. Almost every default was picked from the card alone, marked ◻ or "לפני צילום". Nothing is rendered before its SKU photo is judged, and the owner approves the picks (approval 2) from photo sheets.

## Which items
Each document lists what to check:
- `docs/proposals/wm-kitchen-dining-render-2026-11-19.md`, chapter 9;
- `docs/proposals/wm-work-render-2026-11-19.md`, chapter 9;
- `docs/proposals/wm-kids-rooms-render-2026-11-19.md`, section ג.1.

Include every default and every listed alternative that has a card with image URLs. Skip items already judged in `picks/manifest.json`, and say which were skipped.

## The task (0 tokens)
- **Fetch the photos:** for each item, the image URLs in its card under `data/products/`, with plain HTTPS GETs of the exact URLs.
  - Save them only under `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`.
  - Add them to `picks/manifest.json`.
  - If a card has no image URL, list it as "no photo".
- **Build one sheet per room,** with a tile per item showing the label, the slot, the card path, the SKU and the price:
  - `picks/kitchen-dining-picks.jpg`;
  - `picks/work-picks.jpg`;
  - `picks/boy-picks.jpg`;
  - `picks/girl-picks.jpg`.

  These are the owner's approval-2 sheets as well. Keep them clean, and mark each tile as default, alternative or sample variant.
- **Measure each item** on the product itself, using the method of the earlier checks in `picks/manifest.json` (rough Lab medians). Report:
  - L*, C* and h;
  - shape and finish against the slot's spec in the document and the Bible's colour ranges (`docs/design-bible/warm-modern.md`, and the house-20 document's 7.1 summary);
  - any mismatch, such as the wrong colour photographed, a prop that might be mistaken for the product, an AI-looking scene, or a tiny file.
- **The kids' rooms:** also note any visible safety marking (CE, EN 71, OEKO-TEX), or "none visible".

## Outputs
- The four sheets.
- `picks/new-rooms-photo-check.json`, with the numbers and a verdict per item: passes, fails or unclear, with one line why.
- Both go in the scratchpad. No repo files.

## Fixed rules
- No contact with anyone, no sign-ups, and no scraping beyond the cards' own image URLs.
- Supplier images never go into the repo. Run Python that reads them with `python3.12 -I`.
- No commits, no keys, no var2.
- Return a short Hebrew summary per room: how many passed, failed, were unclear or had no photo, and the failures with one line each.
