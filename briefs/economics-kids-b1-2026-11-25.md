# Brief: economics for the kids' rooms and the B1 planter (general-purpose, 2026-11-25)

## Why
In MOCK6 (commit dd3fb7b7), several products in the boy's and girl's rooms show "עוד לא במכירה" because they have no line in `data/economics`. Among them:
- the boy's prints;
- the bookends;
- the bedding;
- the throw.

The B1 ledge planter in the bath has no shipping line either. This is backlog M6-L2 in `status/backlog-low.md`.

## The task
1. **Find the products with missing economics.**
   - **The rooms:** the products the tour shows in the boy's room, the girl's room and bath B1. See `site/tools/tour/boy.warm-modern.json`, `girl.warm-modern.json`, `bath-b1.warm-modern.json` and `rooms.products.json`.
   - **The check:** list those that `site/tools/build-catalog.ts` prices as missing.
   - **The output:** a table of card id, why it's missing, and the data on hand.
2. **Fill them, following the existing conventions exactly.**
   - **Where:** `data/economics/products.json`, the freight files (`freight-aliexpress.json`, `freight-cj.json`, `freight-bundles.json`) and `settings.json`.
   - **How:** read `data/economics/BRIEF-no-loss-2026-10-20.md`, and how earlier rooms were priced (`scripts/economics/no_loss.py`, `no-loss-report-2026-10-20.md`).
   - **Use only data already in the repo:**
     - card `price.cost`;
     - the SKU options;
     - cached freight for the same or a sibling SKU, the same seller and the same weight class.
   - **Mark any freight you take from a sibling as such,** as earlier rounds did.
3. **No guessing.** If a product has no usable freight in the repo, leave it out and list it.
   - It waits for the CJ API to be reactivated, or a new AE token.
   - Don't invent a freight number.
4. **Respect the no-loss rule.** Every price you set passes `scripts/economics/no_loss.py`, or the project's equivalent check.
5. **Safety-held products** (the Roman blind 868827, the kids' pendant, the teddy bear, the bunny and the cars): economics may be filled, but the site keeps them held. Don't change their notes or safety status.

## Acceptance (run these yourself)
- The no-loss check passes on every product you touched.
- `python3 scripts/sourcing/options.py validate` is clean.
- From `site/`: `npx --no-install vitest run` stays fully green (571/571 at MOCK6).
- The catalog build lists a price for each product you filled.
- Every JSON you touched parses.

## Outputs
- the economics changes;
- a log, `data/leads/economics-kids-b1-2026-11-25.md`: one line per product, saying what was filled, from what source, the price and the margin, or why it was left out.

## Fixed rules
- Touch only `data/economics/` and the log. Not the cards, slots, `site/` code, `docs/` or renders.
- No network, no keys.
- Never `git stash`, `checkout`, `reset`, `mv` or `commit`. Never `npx` without `--no-install`.
- The disk is tight. Don't leave builds behind.
- Return a short Hebrew summary:
  - how many products were filled per room;
  - which are still missing and why;
  - the vitest numbers.
