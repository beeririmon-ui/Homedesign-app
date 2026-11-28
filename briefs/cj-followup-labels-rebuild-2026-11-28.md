# Brief: after the CJ pricing, Hebrew labels, the losing sofa cover, and a rebuilt preview (general-purpose, 2026-11-28)

## Why
The CJ round (`data/leads/economics-cj-2026-11-28.md`) priced 18 of 21 tour products. What's left:
1. **Two products are priced and pass no-loss but aren't in yet:** the curtain and the cube sconce (`wall-sconce-cj-travertine-cube-updown-12`; for the curtain id, see the log). With a price they enter the shop catalog, and vitest fails on rule ת12: about 80 of their option labels are in Latin letters. Their numbers are ready in the log.
2. **`sofa-cover-cj-cotton-muslin-fringe` loses money:** it's ₪129 against a no-loss floor of ₪139. That was the case before this round. The no-loss rule (`data/economics/BRIEF-no-loss-2026-10-20.md`) says no price may lose.
3. **The tour catalog wasn't rebuilt,** so the preview doesn't show the new prices yet.

## The task
1. **Hebrew labels** for every Latin option label of those two products, in `data/catalog/option-labels-he.json`.
   - Follow the file's existing conventions exactly: colour names, sizes with "ס\"מ", sets, the light colour as "גוון אור".
   - Translate faithfully; never invent a property.
   - Then add their economics lines from the log to `data/economics/products.json` (and to `freight-cj.json` if it needs them), exactly as the log gives them.
2. **The sofa cover:** set its price to the lowest price that passes the no-loss check, rounded by the project's convention (₪139 or the next allowed price point). Note it in the log.
3. **Rebuild:**
   - From `site/`: `npm run tour`, then rebuild `site/dist-artifact/` the way MOCK11 did (see `site/README.md`).
   - Run `check-artifact`.
   - Write the publish batches to `site/.generated/artifact-batches.json` as before.
   - List which files changed against the current `dist-artifact`: index.html and any media.

## Acceptance (run these yourself)
- The no-loss check is clean, the sofa cover included (`--check`, `--check-derived` and `--check-site`).
- `python3 scripts/sourcing/options.py validate` is clean.
- From `site/`: `npx --no-install vitest run` is fully green, and so is `npx --no-install playwright test e2e/mock11.spec.ts --trace off`.
- In the rebuilt tour, the 20 newly priced products show a price, not "עוד לא במכירה".

## Outputs
- the labels, the economics and the sofa cover price;
- a short addition at the end of `data/leads/economics-cj-2026-11-28.md`;
- `site/dist-artifact/` rebuilt.

## Fixed rules
- **Touch only:** `data/catalog/option-labels-he.json`, `data/economics/`, the log, and the generated site output. No cards, no site code, no docs.
- No network, no keys.
- Never `git stash`, `checkout`, `reset`, `mv` or `commit`. Never `npx` without `--no-install`. Don't run `playwright install`.
- **Return a short Hebrew summary:**
  - what went in;
  - the sofa cover's new price;
  - the test numbers;
  - the files changed in `dist-artifact`.
