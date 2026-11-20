# Brief: photo sheets for the AliExpress round candidates (general agent, 2026-11-20)

## Why
A separate sourcing session ran the first AliExpress round with the owner's keys (`data/leads/ae-round-2026-11-20.md`). It wrote 58 draft cards across 14 gap lines: the hall key tray, exterior wall light, table lamp and corridor stool; the living-room armchair cushion; the bath ledge planter; the kids' roman blind and under-desk bin; the kitchen pendant variant, grinders, boards and bench pad; and the work wall sconce and shelf object. The designers pick defaults only from SKU photos they can judge, so the photos need checking first.

## The task (0 tokens)
- **Which items:** every card the ranking file names, grouped by its line. Start with the blocking lines (22, 24, 27, 15, 18, and ג0) and the top three of each other line. Find the cards with `grep -rl "aliexpress" data/products --include=*.json` filtered to the files added in the AE commits (`git log --name-only --format= 7862ce30^..5144580b -- data/products`).
- **Fetch the images:** the cards' own image URLs, with plain HTTPS GETs of the exact URLs only. Save them under `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`, and add a section `ae_round_2026_11_20` to `picks/manifest.json` (leave the other sections alone).
- **Build a sheet per room group** in `picks/`:
  - `ae-hall-corridor.jpg`;
  - `ae-living-bath.jpg`;
  - `ae-kitchen.jpg`;
  - `ae-work.jpg`;
  - `ae-kids.jpg`.

  Give each a tile per card with the line number, the short Hebrew label, the card path, the SKU, the price and the shipping.
- **Measure each** on the product itself (rough Lab medians, the method of the earlier checks). Then check its shape and size against the line's spec, and look for any mismatch: the wrong colour photographed, an AI-looking scene, someone else's brand on the box, or a design copy. For lighting, note any visible CE mark or plug. For kids' items, note any safety mark.
- **Give a verdict per card:** passes, fails or unclear, with one line why. Mark the best passing card per line.

## Outputs
- The five sheets, plus `picks/ae-round-photo-check.json` with the numbers and verdicts, all in the scratchpad.
- No repo files.

## Fixed rules
- No contact with anyone, no sign-ups, and no scraping beyond the cards' own image URLs.
- Supplier images never go into the repo. Run Python that reads them with `python3.12 -I`.
- No commits, no keys, no var2.
- Never run `git stash`, `checkout` or `reset`.
- **The disk is tight** (about 2.7GB). Download at a reasonable size, and delete temp files.
- Return a short Hebrew summary per line: how many pass, the best one, and the failures in one line each.
