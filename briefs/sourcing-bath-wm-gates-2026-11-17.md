# Brief: the warm-modern bath, the checks before render, and the picks into data (sourcing-agent, 2026-11-17)

## Why
The owner approved rendering the warm-modern bathroom (HOUSE, HOUSE1, 2026-11-17). master-designer picked the products: `docs/proposals/wm-bath-render-2026-11-17.md`, with the picks in 4.1, the full ranking in 4.2, the sample slot in 5, the gaps in 6, and the notes for the manager in 11. Two gates stand before render-agent may send, because without the real dimensions there is no faithful render.

## The work (0 tokens)
1. **The gates (first, and report them as soon as they're done):**
   - **The travertine sconce** `…037853` (the cards `data/products/bath/vanity-sconces/vanity-sconces-aliexpress-wabi-sabi-yellow-marble-037853.json` and `wall-sconce/...-037853.json`): the backplate and shade dimensions, the projection from the wall, the IP rating and the SKU. Do the same for the backup `…430468`.
   - **The floor planter** `data/products/planter/planter-cj-cement-ribbed-belly`, SKU Beige-Medium: diameter and height, and whether the SKU exists. The designer needs the belly up to 31 and the height 26–36.
   - **The hand towel** `hand-towel-aliexpress-pure-linen-towel-38x55`: confirm the three SKUs (caramel `12000059652536005`, linen `12000059652334993`, black `12000059652334999`) exist, with their colour names and the size.
   - Official sources only. AliExpress through the official API (the AE DS keys from the environment); CJ through `CJ_API_KEY`. If a key is missing, say so. A listing's text visible through a normal fetch is fine where your rules allow it. No scraping.
   - Update each card with what you verified, and mark what you couldn't.
2. **The picks into data:** mirror the designer's tables 4.1 and 4.2:
   - Write `data/selections/bath.warm-modern.json` in the same format as `data/selections/living-room.warm-modern.json`. The status line is "proposed; part of owner approval 3 with the B2 render".
   - Add `style_scores.warm-modern` (score and one-line reason) to each bath card that the designer scored.
   - **Don't** change card statuses (selected/rejected) until the owner approves. **Don't** change `data/slots/bath.json`. The ledge Z change is for the 1.3.9 registration.
3. **The gaps (chapter 6):** only if time allows after 1–2, start the towel ladder (with its towels) and the stool. They are the most visible gaps in the frame. 6–10 candidates each, as usual. Otherwise list them as next.

## Fixed rules
- Official sources only. No scraping of AliExpress or BigBuy, no scraper services, no CAPTCHA bypass, no user-agent spoofing, no sign-ups, no contact with any supplier.
- Never write a key, token, phone number or business id into any file. Supplier images go only in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/sourcing-bath/`.
- No commits. No edits to binding documents or slots.
- Return a short Hebrew summary: the gates (the sconce dimensions and IP, the planter, the towel SKUs: pass or fail with numbers), what was written into data, and the gaps' status.
