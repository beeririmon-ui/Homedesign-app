# Brief: the hall bench and the hall console, warm-modern (sourcing-agent, 2026-11-17)

## Why
The owner approved the new tour route (ROUTE1, 2026-11-17). The entrance hall is now a station. Facing the door there's a walnut bench on the stone wall, and next to the opening to the living room a walnut console. Both are product slots that are sold (R5Q4). Under F3 (`data/slots/hall.json`, "sales_note"), each is sold as one product with no variants: the render stays as designed, and we sell **a matching model, preferably from an Israeli supplier**. They are about to be rendered, and there are no cards for them yet. TOUR2 adds the business angle: furniture like this is exactly what we show Israeli furniture stores as future partners.

## The two slots (warm-modern; the spec is master-designer's, `docs/proposals/wm-tour-route-2026-11-17.md` §2.2)
- **bench:** solid walnut or walnut veneer in a matte oil finish (about #6B4A33). Seat height about 45, depth about 40, **length about 80 (70–100 acceptable)**. A slab top about 5 thick, two full slab end panels about 5 thick, and open between them. Softly rounded corners. No cushion, no back, no metal legs, no drawers.
- **console:** walnut, matte oil, **about 80 × 35, height about 80** (width 70–100, depth 30–40, height 75–85). A slab top about 5 thick with rounded front corners, on two elliptical drum or pedestal bases set in from the ends (the language of the coffee table). Nothing on it. A slab or pedestal base is better than four thin legs. No glass, no metal frame, no drawers.
- Note `data/slots/hall.json` still describes them in oak at the H0 sizes (bench 120). The warm-modern spec above is the current one (registration pending, 1.3.9). Score against it, and say if a strong candidate only exists in oak.

## The task (6–10 candidates per slot)
1. **Israeli stores first** (F3, TOUR2): Israeli furniture stores, makers and importers that sell online with a clear price, dimensions and material. Record them as candidate partners too (`data/suppliers/` or your usual place for Israeli store leads).
2. **Then the usual sources,** per your agent rules: CJ through the API if `CJ_API_KEY` is set, and the official sources you use (`data/sources/seen.json`). Heavy furniture shipped from abroad is expected to be weak on shipping to Israel. Say so with numbers rather than dropping it silently.
3. **A card per candidate** per `data/product-card.schema.json`, in `data/products/entrance/bench/` and `data/products/entrance/console/`. Each card has the price, shipping to Israel (cost and days), dimensions, materials and finish, the link, image rights (`unclear` unless stated), standards if shown, and the no-loss price from `scripts/economics/no_loss.py` where the data allows. Mark anything you couldn't verify.
4. **A short ranking file:** `data/leads/hall-bench-console-2026-11-17.md`. Per slot, the best three against the spec: how close the form is (slab ends and a slab top; drum bases), the size, the walnut tone, the price and the availability in Israel. master-designer picks; you rank.

## Fixed rules
- Official sources only: no scraping of AliExpress or BigBuy, no scraper services, no CAPTCHA bypass, no user-agent spoofing, no sign-ups. **No contact with any supplier or store** (no forms, no emails, no chat).
- Never write a key, token, phone number or business id into any file. Supplier images are not saved in the repo. If you download any, they go in the scratchpad: `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/sourcing-hall/`.
- New files only. No edits to binding documents or slots. No commits.
- Return a short summary in Hebrew: the candidates per slot, the best three with why, the Israeli stores found, and what you couldn't verify.
