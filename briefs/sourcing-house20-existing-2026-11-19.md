# Brief: sourcing for 20 products in the existing rooms (sourcing-agent, 2026-11-19)

## Why
The owner wants at least 20 products for sale in every tour room (FB11, FB10, in the digest). master-designer merged every gap for the existing rooms into one list: chapter 7 of `docs/proposals/wm-house-20-2026-11-19.md`. The rooms are the bedroom, the bathroom, the living room, the entrance hall and the corridor. The manager's rulings are in 6.6א.

## The task
- **The lines:** the 28 lines in 7.3, under the rules in 7.1.
- **The order:** the 11 blocking lines first (8, 11, 16, 17, 18, 20, 22, 23, 24, 25, 26, 27), then 1–7, 9, 10, 12 and 21. The backups (13, 14, 15, 19, 28) are last, and only if time allows.
- **How many:** 6–10 candidates per line. Israeli stores and brand sites first for furniture, textiles, rugs and lighting. Then the official sources in `data/sources/seen.json`.
- **Matching the drawing:** lines 23 and 24 must match what D0 already shows (the coir mat, the bronze cylinder wall light). Read the spec closely.
- **Art:** lines 6, 9, 20 and 26 need stated image rights (PR1) and a full-resolution flat file. Mark `unclear` otherwise.
- **The AE and CJ API keys** are not in this environment, and you have no shell. Say per line what you couldn't reach. Don't work around it.

## Cards
- **One card per candidate,** per `data/product-card.schema.json`, in `data/products/<room>/<slot>/` (rooms: master, bath, living-room or the pool, entrance, corridor) or in the pool folder.
- **Each card includes:**
  - price;
  - shipping to Israel;
  - dimensions;
  - materials and finish;
  - photo URLs;
  - link;
  - image rights;
  - a `style_scores.warm-modern` estimate with a one-line reason.
- Mark what you couldn't verify.
- **Slots:** use the slot names the document gives. Some are new slots proposed for the 1.3.9 registration (for example `armchair-cushion`, `window-vessel`, `door-mat`, `exterior-wall-light` and `wall-art`). Put them under the room folder with that slot name anyway. The manager knows that a site test flags unregistered slots until 1.3.9 is approved.

## Outputs
- The cards.
- **A ranking file:** `data/leads/house20-existing-2026-11-19.md`, with the best three per line and why, by line number.

## Fixed rules
- Official sources only. No scraping AliExpress or BigBuy, no scraper services, no CAPTCHA bypass, no user-agent spoofing, no sign-ups. **No contact with any supplier, store or maker.** Fox Home and Israeli makers are listed only; the owner approves any contact.
- Never write a key, token, phone number or business id into any file.
- Supplier images only in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/sourcing-house20/`.
- New files only. No edits to binding documents or slots. No commits.
- Return a short Hebrew summary covering:
  - the cards per line;
  - the strongest three for each blocking line;
  - what you couldn't reach, and why;
  - the Israeli stores found.
