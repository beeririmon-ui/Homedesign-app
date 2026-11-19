# Brief: sourcing for the new rooms, 20 products each (sourcing-agent, 2026-11-19)

## Why
The owner wants at least 20 products for sale in every tour room (FB11, FB10, in the digest). master-designer designed four new warm-modern rooms, and each document lists the gaps that no existing card covers:
- **The kitchen and dining:** chapter 5 of `docs/proposals/wm-kitchen-dining-render-2026-11-19.md`, 12 lines.
- **The work room:** chapter 5 of `docs/proposals/wm-work-render-2026-11-19.md`, 8 lines. The first three replace temporary repeats.
- **The boy's and girl's rooms:** sections א.5 and ב.5 of `docs/proposals/wm-kids-rooms-render-2026-11-19.md`. Some lines are shared between the two rooms.

Another sourcing run is covering the existing rooms in parallel (`briefs/sourcing-house20-existing-2026-11-19.md`). Don't duplicate its lines: the stool, the pouf, the planter and the rug lines there serve other rooms. If a card you find suits one of its lines too, say so.

## The task
- **How many:** 6–10 candidates per line, in each document's priority order. Israeli stores and brand sites first for furniture, textiles, rugs, lighting and tableware. Then the official sources in `data/sources/seen.json`.
- **The style:** `docs/design-bible/warm-modern.md` and its rejection list. Use the colour and material ranges in each line, and section 7.1 of `docs/proposals/wm-house-20-2026-11-19.md` as the shared summary.
- **The kids' rooms, safety:**
  - prefer products with a stated EN 71 (toys), OEKO-TEX (textiles) or CE (lighting);
  - any blind must be cordless (EN 13120);
  - record on each card what is stated, or "not stated".
- **Art:** needs stated image rights (PR1) and a full-resolution flat file. Mark `unclear` otherwise.
- **The AE and CJ API keys** are not in this environment, and you have no shell. Say per line what you couldn't reach. Don't work around it.

## Cards
- **One card per candidate,** per `data/product-card.schema.json`, in `data/products/<room>/<slot>/` (rooms: dining, work, kids) or in the pool folder.
- **Each card includes:**
  - price;
  - shipping to Israel;
  - dimensions;
  - materials and finish;
  - photo URLs;
  - link;
  - image rights;
  - safety marks where relevant;
  - a `style_scores.warm-modern` estimate with a one-line reason.
- Mark what you couldn't verify.
- **Slots:** use the slot names the documents give, including new slots proposed for 1.3.9. The manager knows that a site test flags unregistered slots.

## Outputs
- The cards.
- **A ranking file:** `data/leads/new-rooms-2026-11-19.md`, with the best three per line, by room and line.

## Fixed rules
- Official sources only. No scraping AliExpress or BigBuy, no scraper services, no CAPTCHA bypass, no user-agent spoofing, no sign-ups. **No contact with any supplier, store or maker.** Fox Home and Israeli makers are listed only; the owner approves any contact.
- Never write a key, token, phone number or business id into any file.
- Supplier images only in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/sourcing-new-rooms/`.
- New files only. No edits to binding documents or slots. No commits.
- Return a short Hebrew summary covering:
  - the cards per line;
  - the strongest three per line;
  - what you couldn't reach, and why;
  - the Israeli stores found.
