# Brief: Israeli stores, the swap tables plus the living-room and entrance gaps (sourcing-agent, 2026-11-25)

## Why
- **FB12-T, 2026-11-25:** the owner asked for a coffee table that's swappable: "סטיילי אבל לא כבד". Olia is being rendered now. The wheel needs 2 more tables that pass the spec.
- **FB11:** at least 20 products in every tour room. The living room and entrance have blocking gaps.
- **CJ is still blocked** (API access disabled), and AliExpress waits for the owner's login. So this round is **Israeli stores**, which is also the owner's partner model (furniture, rug and lighting stores in Israel).

## The lines, in this order (4–6 candidates each, real-unit photos only)
1. **Coffee tables for the swap wheel.**
   - The spec is `docs/proposals/wm-fb12-2026-11-25.md` א.3, and its rejection list in ג.1.
   - Light and crafted, an open base, L\* 56–66 wood (or travertine or stone with honest texture), length 120–140.
   - Already carded, don't repeat them: Olia, Tintin, Upsula, Boomerang.
   - At least 2 must differ from Olia in form, for example a round or oval top, travertine, or a different base. A real choice, not three of the same.
2. **The living room**, blocking lines in `docs/proposals/wm-house-20-2026-11-19.md` 7.3:
   - `pouf`;
   - `wall-decor`;
   - `armchair-cushion`.
3. **The entrance**, the same table:
   - `framed-art`: rights stated, or `unclear`;
   - `door-mat`;
   - `exterior-wall-light`: **CE / IP44 required**, or "not stated";
   - `runner-rug`, in the corridor.

Read the line specs in 7.3 and the warm-modern Bible (`docs/design-bible/`) before searching.

## For each candidate
- **A card** per `data/product-card.schema.json`, in `data/products/<room>/<slot>/`. Pool cards are fine if a slot isn't registered.
- **The basics:** URL, model, price, stock or lead time, shipping, dimensions, materials and finish.
- **At least 2 photos of a real unit,** as URLs. No downloads into the repo.
- **Safety marks** where they apply. Record what the page states, or "not stated".
- **A `style_scores.warm-modern` estimate,** with a one-line reason.
- **Anything unverified,** marked as such.

## Outputs
- the cards;
- `data/leads/israel-gaps-2026-11-25.md`, one short table per line: the candidates, and the best 3 with reasons.

## Fixed rules
- **Sources:** official public store pages only. No AliExpress or BigBuy scraping, no scraper services, no CAPTCHA bypass, no user-agent spoofing, no sign-ups.
- **No contact** with any store, maker or artist.
- **Nothing private:** never write a key, token, phone number or business id into a file.
- **Don't edit** binding documents or `data/slots/`. No commits.
- **The report (EFF2):** a Hebrew summary of at most 15 lines: per line, the count and the top pick with its price; plus what you couldn't reach.
