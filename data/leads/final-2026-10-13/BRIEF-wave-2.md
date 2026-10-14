# The final round, wave 2: storage, ceramics and textiles (2026-10-14)

This is an addendum to `BRIEF-cj-zendrop.md`. Read that first: tools, economics, card rules, output shape and limits all still apply.

The owner's target (2026-10-14) is 90% of slots in all six styles with **3 options each**. Colours and prints count (rule ג.3).
- Coverage now: 41% (`data/leads/final-2026-10-13/coverage.json`).
- What is missing: `coverage.json` → `remaining.<style>`, with `category` per gap.

## Your scope
Work by **category**, across all rooms; your task names the categories. One search serves every room and style that needs the same kind of item: magazine holders in the living room and the work room, storage boxes in the hall and the work room, bins in the bath and the work room, and so on.

Not in this wave:
- Lighting: no Chinese supplier declares CE. That waits for an owner decision.
- Kids' toys: no EN71 declared. That waits for an owner decision.
- Large rugs: Israeli shops already cover them.
- Furniture.

## What is different from wave 1
1. **Listings in several colours first.** A listing that comes in 3+ colours or finishes, where 2–3 of them suit the styles, can fill a slot for several styles at once.
   - In the results, give `variants_fit: {style: n}`, how many of its colours fit each style, and `fitting_skus`.
   - Make sure the card's `options` lists every colour with its image. Check with `python3 -I scripts/sourcing/cj_source.py options <pid> --sku <variantSku>` and `backfill-options`.
2. **Price by Israeli value, per item (rule ה.10).** Many sets lost money in wave 1 only because the slot price is low. In Israel a set of 4 mugs, a 3-piece canister set or a large rope basket costs more.
   - For each candidate, find 2–3 Israeli comps (public shop pages, with URLs) and set the price about 10–25% below the typical comparable.
   - Judge loss and margin at that price, not at the slot price. Put the comps in the card's `notes` and in the results (`price_basis_he`).
   - If even the Israeli value can't carry the shipping, it loses. Say so.
3. **New queries only.** Check `data/leads/next-sourcing/searched-index.json` (`cj_queries`, `zendrop_queries`, `aliexpress_queries_by_slot`). Try different angles:
   - other materials (seagrass, water hyacinth, paper cord, felt, enamel, stoneware, wood);
   - other words (organizer, caddy, tidy, bin, pot, jar set, crock, bundle);
   - sets and bundles.
4. **Card cap:** up to 2 new cards per style gap and up to 8 per slot, as before. Prefer one listing that serves several styles and rooms.

## Output
- Cards per `BRIEF-cj-zendrop.md`, with notes starting "final-round wave-2 2026-10-14:".
- `data/leads/final-2026-10-13/results/wave2-<group>.json` (same shape; slots keyed "<room>/<slot>"; candidates with `style_fit_guess`, `variants_fit`, `card_id`, economics at the Israeli-value price, and `price_basis_he`).
- A short Hebrew `wave2-<group>.md`.
- CJ: `--max-points 6000 --max-calls 400`, with run-id `final-w2-<group>`.

Return a short Hebrew summary:
- the style gaps filled;
- the cards written;
- the best multi-colour finds;
- the prices you re-derived;
- CJ points used.
