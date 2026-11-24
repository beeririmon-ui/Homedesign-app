# Brief: product cards after registration 1.3.9 (general-purpose, 2026-11-24)

## Why
Registration 1.3.9 (commit 78d94cd6) put the approved warm-modern rooms into `docs/house-plan.*` and `data/slots/`. vitest still has 2 red tests in `site/shared/test/shared.test.ts`:
- cards whose room + slot isn't a slot;
- AE draft cards with a missing `placement`.

The log in `docs/proposals/wm-registration-1-3-9-2026-11-24.md`, chapters 4–6, says what each card needs.

The manager's rulings:
1. **No schema change.** Where a new slot's rendered default is a card that lives in another slot (log 6.3), create **one card per slot**: a copy with its own `id`, `room`, `slot` and `placement`, and the same supplier, SKU and price. Each copy's `notes` gets this line: `mirror_of: <original id>; keep supplier/sku/price in sync`. This follows the rule that repeats across rooms are temporarily allowed, and each counts in its own room.
2. **The 17 cards with no approved slot** (log ch. 4):
   - **Hiba** (`master/nightstand-objects`) moves to `work/desk-candle`, because it is that slot's rendered default.
   - **Lenni and Dora** (`master/table-lamp`) move to `work/desk-lamp`, if that slot exists in `data/slots/work.json` (it does) and no card with the same id is already there.
   - **Every other card** moves to the shared pool: `data/products/pool/<category>/`, with `room` and `slot` cleared the way existing pool cards do it (`room: null`, `slot: null`, `rooms: [...]`). Its `notes` gets the line `intended_slot: <room>/<slot> (not registered; returns when the slot is registered)`.
3. **`placement`, per log ch. 5:**
   - `hall/exterior-wall-light` gets `wall`;
   - `work/shelf-object` gets `surface`;
   - the armchair cushion 911182 goes to the pool (rule 2), and gets `sofa` as its placement.

   Leave `kids/*` alone. Kids wait for their approval 3.
4. **KD-L7**, in `status/backlog-low.md`: sync the kitchen cards to 10.9 (render folder `assets/renders/dining/warm-modern/stage1-2026-11-20/`, README and `manifest.json`):
   - the print 05: `…944` (40×50), not `…935` (30×40);
   - the tea towel: the set of 2, `…006`, not 1pc;
   - board F: `in_room` true on its default SKU.

   Use the house's card conventions:
   - `in_room` on `default_sku`;
   - other room variants in a `room_variants: <style>.<room>=<sku>; …` notes line;
   - card-level `supplier.sku` and `price.cost` synced from `options.skus`.

## Inputs
- `docs/proposals/wm-registration-1-3-9-2026-11-24.md`, chapters 4–6;
- `data/slots/*.json` and `data/product-card.schema.json`;
- `briefs/cards-sku-sync-2026-11-19.md`, for the card conventions;
- the cards in `data/products/`, and `data/products/pool/` for the pool format;
- the kitchen render folder above, for KD-L7.

## Outputs
- the card files edited, moved or created under `data/products/`;
- a short log, `data/leads/cards-after-reg-1-3-9-2026-11-24.md`: one line per card, with what was done and why.

## Acceptance (run these yourself)
- `python3 scripts/sourcing/options.py validate` is clean.
- From `site/`: `npx --no-install vitest run shared/test/shared.test.ts`. The only lines allowed to fail are the `kids/*` ones (7 "not a slot" and 5 "placement"). Report the before and after counts.
- From `site/`: the full `npx --no-install vitest run` has no new failure.
- Every JSON file you touched parses.

## Fixed rules
- Only `data/products/` and the new log. Don't touch `data/slots/`, `docs/`, the schema, the render folders or the site code.
- **Never** run `git stash`, `git checkout`, `git reset`, `git mv` or `git commit`. Use plain `mv` and file writes. The manager commits.
- **Another agent is fixing the kids' renders** in `assets/renders/boy|girl/`. Don't touch those folders.
- No network, no keys, no var2, no supplier contact.
- Never `npx` without `--no-install`.
- Return a short Hebrew summary: the counts, what moved, the copies created, the KD-L7 changes, and the vitest numbers.
