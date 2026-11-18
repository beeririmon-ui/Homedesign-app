# Brief: sourcing round FB10, the warm-modern bedroom and bathroom (sourcing-agent, 2026-11-18)

## Why
The owner set a new target: **at least 20 products per room, and more is better** (FB10, in the digest). It replaces 14/11 and FB9's 7–10. Today the bedroom has about 13 and the bathroom about 10, counting the FB9 additions. Both designers are re-picking from every existing card. This round adds new candidates where the existing cards don't reach.

## Current state
- **Cards:** `data/products/master/` (57 cards, 18 slots), `data/products/bath/` (70 cards, 21 slots), and the pools in `data/products/` (`basket`, `vase`, `planter`, `framed-art`, `wall-decor`, `cushions`, `pouf`, `rug`, `bowl`, `candle-holders`, `table-runner`, `accent-sconces`, `wall-sconce` and others).
- **Picks and gaps:**
  - the bedroom in chapters 12–13 of `docs/proposals/wm-master-bedroom-render-2026-11-17.md`;
  - the bathroom in chapters 0א and 12 of `docs/proposals/wm-bath-render-2026-11-17.md`;
  - the FB9 gap leads in `data/leads/fb9-gaps-2026-11-18.md`.
- **The style:** `docs/design-bible/warm-modern.md`. It uses walnut #6B4A33, travertine and limestone, lime plaster #ECE5DA, caramel, oat and cream, espresso as an accent, bronze-espresso metal, and matte, natural, handmade finishes. No pure white, no pure black (accents only), no gloss, no chrome.

## What to find (6–10 candidates per line, in this order)
**The bedroom:**
1. A walnut wall shelf or ledge, about 180 × 24.
2. Framed art for above the bed, in warm tones (espresso, caramel, oat; not pure black), 50×70 or larger, a pair or a single large piece. The seller must state the image rights (PR1).
3. A tall floor planter, espresso or warm charcoal, H 50–65.
4. A ceramic carafe with a cup for the nightstand.
5. Decorative books, or a book stack in neutral linen covers.
6. A small table lamp: a travertine or ceramic base with a linen shade.
7. A jute or wool rug in oat or cream, about 200×300.
8. A pouf or a small bench: bouclé, leather in caramel, or walnut.
9. A small mirror or wall object in walnut or bronze.
10. More nightstand objects: a small dish, a jewellery box, a scented candle in a ceramic vessel.

**The bathroom:**
11. A shower stool: a drum in walnut-toned wood or stone, about 30 × 45.
12. A lidded jar for the vanity shelf, in ceramic or travertine-look.
13. A small framed print, up to 23×32, with rights stated.
14. Folded hand or bath towels in coffee or taupe (h 30–60°, L* 40–58), or warm oat.
15. A cream or oat rope or seagrass basket for the open shelf, under about 43 cm.
16. A robe and a wall hook (bronze-espresso).
17. A small plant in a matte pot for the vanity.
18. A scented candle or diffuser in a ceramic vessel.
19. A bath mat in oat or cream (cotton or waffle).

## How
- **Israeli stores and brand sites first,** with clear photos, dimensions and prices. Then the official sources you use (`data/sources/seen.json`).
- **The AE and CJ API keys are not set in this environment.** If you can't reach a source because of that, say so per line. Don't work around it.
- **A card per candidate** per `data/product-card.schema.json`, in `data/products/master/<slot>/` or `data/products/bath/<slot>/`, or in the pool folder. Each card has the price, shipping to Israel, dimensions, materials and finish, the photo URLs, the link, image rights (`unclear` unless stated), and a `style_scores.warm-modern` estimate with a one-line reason. Mark what you couldn't verify.
- **A ranking file:** `data/leads/fb10-round-2026-11-18.md`, with the best three per line.

## Fixed rules
- Official sources only. No scraping AliExpress or BigBuy, no scraper services, no CAPTCHA bypass, no user-agent spoofing, no sign-ups. **No contact with any supplier or store.**
- Never write a key, token, phone number or business id into any file.
- Supplier images only in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/sourcing-fb10/`.
- New files only. No edits to binding documents or slots. No commits.
- Return a short Hebrew summary: the cards per line, the strongest three per line, what you couldn't reach (and why), and the Israeli stores found.
