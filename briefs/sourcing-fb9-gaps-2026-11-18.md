# Brief: the FB9 gaps, bedroom and bathroom, warm-modern (sourcing-agent, 2026-11-18)

## Why
The owner wants fuller rooms, with at least 7–10 products that read clearly (FB9, in the digest). Both designers added product slots:
- **The bedroom:** chapter 13 of `docs/proposals/wm-master-bedroom-render-2026-11-17.md`.
- **The bathroom:** chapter 12 of `docs/proposals/wm-bath-render-2026-11-17.md`.
Most new slots have a card already. These don't, and the specs are in those chapters (13.3 and 12.3).

## The gaps (6–10 candidates each, Israeli suppliers first where it's furniture)
- **The bedroom:**
  1. A walnut wall shelf or ledge, about 180 × 24 × 4 cm, matte oil, with hidden brackets. It will carry two framed prints and two vases. Israeli makers and stores first.
  2. A tall floor planter, D 34–40 × H 50–65 cm, in espresso or warm charcoal, matte, so it stands above the magazine holder.
  3. A ceramic carafe or pitcher for the nightstand (the existing gap 3, as specified in the doc).
- **The bathroom:**
  4. A small stool for under the shower niche: a drum in walnut-toned wood, or stone, water-resistant, about 28–34 × 42–46.
  5. A lidded jar for the vanity's open shelf: matte ceramic or travertine-look.
  6. A small framed print, up to 23 × 32, in a warm-minimal palette, with clear image rights. Prefer prints whose seller states rights (PR1).

## The task
- **Cards:** one per candidate, per `data/product-card.schema.json`, in the room's folder (`data/products/master/<slot>/`, `data/products/bath/<slot>/`), or the pool folder for planters and art. Each card needs:
  - price;
  - shipping to Israel (cost and days);
  - dimensions;
  - materials and finish;
  - link;
  - image rights (`unclear` unless stated);
  - the no-loss price where the data allows.
  - Mark what you couldn't verify.
- **A ranking file:** `data/leads/fb9-gaps-2026-11-18.md`, with the best three per gap against the spec.
- The AE and CJ API keys are not set in this environment. Use the official sources available to you, and say what you couldn't check.

## Fixed rules
- **Official sources only:** no scraping AliExpress or BigBuy, no scraper services, no CAPTCHA bypass, no user-agent spoofing, no sign-ups. **No contact with any supplier or store.**
- **Never write** a key, token, phone number or business id into any file.
- **Supplier images** only in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/sourcing-fb9/`.
- **New files only.** No edits to binding documents or slots. No commits.
- **Return** a short Hebrew summary: candidates per gap, the best three with why, and what you couldn't verify.
