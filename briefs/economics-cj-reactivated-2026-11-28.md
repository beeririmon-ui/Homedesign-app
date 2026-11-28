# Brief: prices and freight for the tour's CJ products, now that the CJ API works again (general-purpose, 2026-11-28)

## Why
The owner reactivated CJ API access (2026-11-28; it had returned code 1600014, "API access disabled"). In the warm-modern tour, about 21 CJ products show "עוד לא במכירה" because they have no price or no freight line. The list is `hidden` in `site/.generated/catalog.tour-rooms.full.json`: the ids containing `-cj-` whose reason starts with "no price" or "no shipping line".

## The task
1. **Make the list:** id, slot, room and reason, from that `hidden` list. Rebuild the catalog first if needed, the way `site/tools/build-catalog.ts` is normally run.
2. **For each CJ product, use the official API through `scripts/cj.py` only.** The commands are `product <pid>` and `freight <vid> --to IL --qty <n>`.
   - **Check the card against CJ:**
     - the card's SKU/variant still exists;
     - it's in stock;
     - the cost matches the card's `price.cost`.

     If the cost changed, note it, and use the API's current cost for the economics.
   - **Freight:** use the default line by the project's convention.
3. **Fill the economics, following the existing conventions exactly.**
   - Write to `data/economics/products.json` and `freight-cj.json`.
   - Read `data/economics/BRIEF-no-loss-2026-10-20.md`, `scripts/economics/no_loss.py` and the last round's log, `data/leads/economics-kids-b1-2026-11-25.md`.
   - Every price must pass the no-loss check.
4. **No guessing.** A product with no variant, no stock or no freight to IL is left out and listed, with the reason.
5. **Safety-held products** may get economics, but their safety status and notes stay as they are.

## Be gentle with the CJ API
The access was disabled once:
- at most 1 request every 1.5 s;
- at most 150 requests in total;
- cache every answer you get in your scratch folder.

Stop at the first error that isn't a normal "not found", and report its code and message.

## Acceptance (run these yourself)
- The no-loss check passes on every product you touched.
- `python3 scripts/sourcing/options.py validate` is clean.
- From `site/`: `npx --no-install vitest run` stays fully green.
- The catalog build lists a price for each product you filled.
- Every JSON you touched parses.

## Outputs
- the economics changes;
- a log, `data/leads/economics-cj-2026-11-28.md`: one line per product, with what was filled, the source, the price and margin, or why it was left out.

## Fixed rules
- **Touch only:** `data/economics/` and the log. If a card's cost or stock changed, list it in the log and don't edit the card.
- **The CJ API only through `scripts/cj.py`:**
  - Never print, copy or write the key or the token. The token lives in `~/.cache/cj/token.json`.
  - Never call `source` or `source-status`: no sourcing requests, no contact with suppliers.
- Never `git stash`, `checkout`, `reset`, `mv` or `commit`. Never `npx` without `--no-install`.
- **Return a short Hebrew summary:**
  - how many products were filled per room;
  - which are still missing, and why;
  - cost changes;
  - the vitest numbers.
