# Brief: photo check of 13 existing cards (general agent, 2026-11-19)

## Why
master-designer's plan for 20 products per room (`docs/proposals/wm-house-20-2026-11-19.md`) relies on existing cards whose SKU photos haven't been judged yet. They are listed in 7.2, items 1–4. Item 5, the bench photos, is not needed: the bench is plan B.

## The task (0 tokens)
- **Fetch the images:** for each item, the image URLs in its card under `data/products/`. Use plain HTTPS GETs of the exact URLs, as in the earlier picks round. Save them only under `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`, and add them to `picks/manifest.json`.
- **Build one sheet:** `picks/house20-photo-check.jpg`, a tile per item, with the label, the card path, the SKU and the price.
- **Measure each item,** on the product itself, not the background or props, using the same method as the earlier checks in `picks/manifest.json` (rough Lab medians). Report:
  - L*, C* and h;
  - the shape and finish against the spec line it serves (chapter 3, 4 or 5 of the document, and 7.1's colour ranges);
  - any mismatch, such as the wrong colour variant photographed, a prop that might be mistaken for the product, an AI-looking scene, or a tiny file.
- **Give a verdict per item:** passes, fails or unclear, with one line why.

## Outputs
- The sheet, plus `picks/house20-photo-check.json` with the numbers and verdicts, both in the scratchpad.
- No repo files.

## Fixed rules
- No contact with anyone, no sign-ups, no scraping beyond the card's own image URLs.
- Supplier images never go into the repo. Run Python that reads them with `python3.12 -I`.
- No commits, no keys, no var2.
- Return a short Hebrew summary: a verdict per item, with the numbers.
