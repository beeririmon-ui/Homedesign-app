# Brief: the first CJ round, pricing and gaps to 20 per room (a new session with `CJ_API_KEY`, 2026-11-25)

## Why
The owner saved `CJ_API_KEY` in this environment on 2026-11-25. Environment variables load only at session start, so this round runs in a new session.

The owner's directive FB11 is at least 20 products for sale in every tour room. Transition clips come last. Today:

| Room | Products | Target |
| --- | --- | --- |
| Living room | 16 | 20 |
| Entrance (hall and corridor) | 4 | 14–16 |
| Master bedroom | 22 | 20 (met) |
| Bath | 19 | 20 |
| Kitchen | 23 | 20 (met) |
| Work room | 18 | 20 |
| Boy | 13 | 20 |
| Girl | 12 | 20 |

MOCK5, the site, also shows many products as "עוד לא במכירה", because they have no price or shipping to Israel. The AliExpress round (2026-11-20) passed only 9 of 58. CJ is expected to fill most of the gaps.

## Read first
- `CLAUDE.md`, `docs/studio-rules-digest.md` and `status/board.md` (the tail);
- `scripts/sourcing/README.md`: the "once" pipeline, the registry, the budget and the cache;
- `data/product-card.schema.json` and `briefs/cards-sku-sync-2026-11-19.md`, for the card conventions:
  - `in_room` on `default_sku`;
  - `room_variants: <style>.<room>=<sku>; …` in `notes`;
  - card-level `supplier.sku` and `price.cost` from `options.skus`;
  - `mirror_of` copies are explained in `data/leads/cards-after-reg-1-3-9-2026-11-24.md`;
- `docs/design-bible/warm-modern.md`: the style, and its rejection list.

## Part A: prices for what is already in the rooms (first)
1. List every card that is a rendered default in an approved room and has no price or no shipping to Israel. The approved rooms are the living room, entrance, master, bath, dining and work.
   - The catalog marks these as "עוד לא במכירה". Build it with `npm run tour` in `site/`, or read `site/tools/build-catalog.ts` to see how a price is resolved.
   - `mirror_of` copies take the original's economics, so price the original.
2. For each CJ card on that list:
   - get the freight to IL with `cj_source.py freight` (the cache and registry rules apply);
   - write it where the pipeline expects it (`data/economics/freight-cj.json` and the card);
   - follow the existing no-loss pricing (`data/economics/BRIEF-no-loss-2026-10-20.md`, `settings.json`, `products.json`).
3. Cards from other suppliers (AE, IKEA, Fox Home and others) stay as they are. List them with the reason they have no price.

## Part B: gap lines, in this order
Give 6–10 CJ candidates per line, each one a card under `data/products/<room>/<slot>/` per the schema. Each card needs:
- price and shipping to IL;
- dimensions, materials and finish;
- photo URLs, the link, and image rights for art;
- safety marks, where they apply;
- a `style_scores.warm-modern` estimate with a one-line reason;
- a mark on anything you couldn't verify.

1. **Blocking lines** in `docs/proposals/wm-house-20-2026-11-19.md`, section 7.3, marked "כן":
   - the living room: `pouf` (16), `wall-decor` (17), `armchair-cushion` (18);
   - the entrance: `framed-art` (20), `door-mat` (23), `exterior-wall-light` (24, **CE required**), `runner-rug` in the corridor (25);
   - the rest of the blocking rows in that table.
2. **The kids' rooms:** `docs/proposals/wm-kids-rooms-render-2026-11-19.md`, section ד.6. Seven lines for the boy, eight for the girl. Safety rules:
   - toys sold only with EN 71;
   - textiles: OEKO-TEX preferred;
   - lighting only with CE;
   - **a cordless Roman blind (EN 13120)** is the most valuable find. Today's blind can't be sold.

   Record what each card states, or "not stated".
3. **The rest:**
   - the bath: `shower-stool` (8), `wall-art` (9);
   - the master bedroom: `sill-plant` (2), `pouf` (3);
   - the work room: the remaining lines in `docs/proposals/wm-work-render-2026-11-19.md`, chapter 5;
   - the kitchen: the remaining lines in `docs/proposals/wm-kitchen-dining-render-2026-11-19.md`, chapter 5 (the runner, the rug, the caramel bench pad, grinders, boards);
   - the remaining non-blocking rows of 7.3.

Slot names: use the ones the documents give. Some aren't registered in `data/slots` yet. A site test flags them, and the manager knows. Don't edit `data/slots`.

## Part C: a photo check of the new cards
Follow the standard in `briefs/photo-check-ae-round-2026-11-20.md`:
- check the SKU photo against the spec (shape, size, colour, material, logo, whether the photo shows the real product);
- give pass, unclear or fail, with the reason, and the best per line.

Keep supplier images only in this session's scratchpad, and read them with `python3 -I`. **Never commit a supplier image.** Commit only the verdict JSON: `data/leads/cj-round-2026-11-25-photo-check.json`.

## Outputs (commit and push)
- **The cards and the economics updates.**
- **`data/leads/cj-round-2026-11-25.md`**, covering:
  - Part A: priced, and not priced with the reason;
  - Part B: per line, the cards and the best three;
  - Part C: per line, what passed;
  - the CJ budget used;
  - what you couldn't reach.
- **Checks:** `python3 scripts/sourcing/options.py validate` is clean, and the vitest in `site/shared/test/shared.test.ts` has no new failure besides unregistered slots (list those).

## Committing
- Commit to branch `claude/agent-system-brand-launch-ax87dv`.
- Use the identity from `git log -1` (`git -c user.name=… -c user.email=…`).
- End each message with the two attribution lines this session gives you.
- Push with `timeout 300 bash scripts/git/sync.sh`. It merges, because the manager's session pushes to the same branch.
- **Before every commit, run the secret scan from the board**, the `grep -lE 'sk-proj-|…'` line. Exit 123 means clean.
- Check new `data/` files for phone-number patterns. AE and CJ ids are false positives.

## Fixed rules
- **Keys:** they come only from the environment. Never print, read or write `~/.cache/cj/token.json`. Never write a key, token, phone number or business id into a file.
- **Official sources only:**
  - the CJ API through `scripts/sourcing/cj_source.py`;
  - no scraping of AliExpress or BigBuy;
  - no scraper services, CAPTCHA bypass or user-agent spoofing;
  - no sign-ups.
- **No contact with any supplier, store or maker.** Israeli makers are listed only; the owner approves any contact.
- **The budget:** stop at 80% of the daily CJ quota and at the run cap (README rule 3). Free accounts are limited to 1 request per second.
- **Don't touch:** binding documents, `data/slots/`, render folders, `site/` code or `assets/`.
- **Git:** never `git stash`, `git checkout`, `git reset` or `git rebase`. Never `npx` without `--no-install`.
- **The disk is a fixed allowance.** Keep scratch small.
- **When done,** the last commit's message starts with "CJ round 2026-11-25 done:" and a one-line count.
