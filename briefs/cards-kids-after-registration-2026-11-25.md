# Brief: kids' cards after registration 1.3.9a, plus CJ-L2 (general-purpose, 2026-11-25)

## Why
Registration 1.3.9a (commit d942155b; log `docs/proposals/wm-registration-1-3-9-kids-2026-11-25.md`, chapters 6–7) put the warm-modern boy's and girl's rooms into `data/slots/kids.json` 1.1.0.

vitest is down to one red test: 5 cards in `kids/under-desk-bin` with `placement: null`.

The rendered defaults of several kids' slots are cards that live in other rooms' folders. The house rule (manager, 2026-11-24) is **one card per slot, no schema change**: a copy whose `notes` carry `mirror_of: <original id>; keep supplier/sku/price in sync`. Same as `data/leads/cards-after-reg-1-3-9-2026-11-24.md`.

## The task
1. **Placement:** `floor` on the 5 cards in `data/products/kids/under-desk-bin/`. Change nothing else on them.
2. **`mirror_of` copies,** one per kids slot whose rendered default lives elsewhere (log, ch. 7). Create each in `data/products/kids/<slot>/`:
   - `pen-cup` ← `work/desk-organizer` (the rendered one);
   - `bookends` ← `work/bookends`;
   - `pillowcase` ← `master/pillowcases` (the rendered SKU per room; one card with `room_variants` for boy and girl if they differ, otherwise one plain copy);
   - `pendant` ← `corridor/ceiling-lights`;
   - `toy-basket` ← `basket/`. The boy's jute basket and the girl's cotton rope basket (GB1b) are two different products, so make two cards in the slot, each `in_room` for its room via `room_variants`, or whatever the conventions say.
   - the boy's `cushions` ← `cushions/`;
   - any other rendered kids default whose card sits outside `data/products/kids/`. Check every layer in `assets/renders/boy|girl/warm-modern/stage1-2026-11-24/manifest.json` against `data/slots/kids.json`.

   For each copy: its own `id`, `room: "kids"`, the kids `slot` and `placement` per the log's ch. 6, and the same supplier, SKU options and price as the original. Set `in_room` on the SKU that is rendered, with `room_variants: warm-modern.kids-boy=<sku>; warm-modern.kids-girl=<sku>` where the rooms differ.

   **Safety (AP2-NEW):** in `notes`, record what the original states for kids' safety (EN 71 for toys, OEKO-TEX for textiles, CE for lighting). If it's "not stated", say so. Don't invent a mark.
3. **CJ-L2,** from `status/backlog-low.md`: `pool-cj-travertine-organic-tray-24` and `pool-cj-wabi-sabi-floor-vase-white` are pool cards that a rendered room uses.
   - Find which room and slot, from the render manifests or from `site/tools/tour/*.json`.
   - Make a `mirror_of` copy in that room and slot, the same way.
   - Leave the pool originals as they are.

## Inputs
- `docs/proposals/wm-registration-1-3-9-kids-2026-11-25.md`, chapters 6–7;
- `data/slots/kids.json` and `data/product-card.schema.json`;
- `briefs/cards-sku-sync-2026-11-19.md` and `data/leads/cards-after-reg-1-3-9-2026-11-24.md`, for the conventions;
- the kids render manifests named above.

## Outputs
- The cards, under `data/products/`.
- A log, `data/leads/cards-kids-after-reg-2026-11-25.md`: one line per card, with what was done and why.

## Acceptance (run these yourself)
- `python3 scripts/sourcing/options.py validate` is clean.
- From `site/`: `npx --no-install vitest run` is **fully green, 555/555**. If it isn't, say exactly which line fails and why.
- Every JSON file you touched parses.

## Fixed rules
- Touch only `data/products/` and the log. Don't touch `data/slots/`, `docs/`, the schema, the render folders or `site/` code.
- **Never** `git stash`, `git checkout`, `git reset`, `git mv` or `git commit`. The manager commits.
- No network, no keys. Never `npx` without `--no-install`.
- Return a short Hebrew summary: the counts, the copies made, CJ-L2, and the vitest numbers.
