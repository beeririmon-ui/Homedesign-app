# The final sourcing round: Israeli shops, by category (2026-10-13)

The owner (2026-10-13): "ליקוט לכל סגנונות העיצוב, לכל חדרי הבית, ליקוט מקיף ביותר ... ואז פינישים ונתחיל להקים את האתר".

This is the last sourcing round before the site. Dropshipping from China does not work for the heavy and hero items: rugs, large lighting, framed art, large ceramics, some textiles. Shipping kills the margin, or the look isn't available.

Your job is to map the Israeli shops and importers that sell what the gaps need, with public prices, across all six styles: Nordic, warm modern, japandi, mediterranean, modern country and boho. We don't contact anyone now. Under studio rule ז, supplier outreach waits for a working site. This list is what we take to them then.

## Input
- **Gap packs:** `data/leads/final-2026-10-13/<style>.json`, one per style.
  - Take the gaps in your category: the slot's `category` field, and the slot names.
  - First the gaps where `designer_source_type` is `israeli` or `local-stock`, then the hero and heavy items, then the rest of your category.
  - Each gap gives the spec, the envelope, the slot price and the existing picks.
- **Style rules:**
  - Nordic: `docs/design-bible/nordic.md` and `nordic-dining.md`.
  - The other five: `docs/design-bible/<style>-brief-draft.md`.
  - Also `.claude/skills/interior-design-rules/`.
- **Binding rules:** `docs/studio-rules.md` (ה.10–14, ז).
- **Already researched.** Don't repeat these shops; add new products from them only if the gap needs it:
  - `data/suppliers/candidates-decor-il-2026-10-12.json`;
  - `data/suppliers/masterpiece-makers-2026-10-12.json`;
  - `data/suppliers/etsy-masterpieces-2026-10-12.json`;
  - the furniture files in `data/suppliers/`;
  - `docs/suppliers/*.md`.

## What to find, per gap
- The Israeli online shops, importers or wholesalers that sell a fitting product, with a public price in ₪.
  - Examples: home-decor chains, design shops, rug importers, lighting shops, ceramics studios, textile brands.
- Per product, record:
  - the shop, the product URL and an image URL;
  - the price in ₪, and whether it includes VAT;
  - dimensions, material, colours or sizes available;
  - stock or lead time if stated;
  - a fit guess (1–10) for each of the six styles;
  - the slot or slots it fits.
- **Per shop, record:**
  - whether it shows any public sign of B2B, wholesale, trade or designer pricing, dropshipping, or a marketplace or affiliate programme. Quote the page.
  - delivery terms;
  - city.
- **Margin note:** at the shop's retail price we earn nothing. Note how deep a trade discount would need to be for 40% at the slot price, using the Studio formula. net = price/1.18; contribution = net − cost − (0.02·price + 1.2) − 0.08·net; for 40%, cost ≤ 0.52·net − 0.02·price − 1.2.
- Aim for 3 options per style gap where Israel has them. Prefer shops that cover many gaps: one supplier relationship for 20 slots beats 20 relationships.

## Output (write only these; no product cards; no commits)
- `data/leads/final-2026-10-13/results/il-<group>.json`:
  ```json
  {"group": "...", "shops": [{"id", "name", "url", "city", "b2b_signals": [{"text", "url"}], "delivery_he", "covers_slots": [...]}],
   "slots": {"<room>/<slot>": {"styles_needing": [...],
     "products": [{"shop_id", "title", "url", "image", "price_ils", "vat_included", "dims_cm", "material",
       "style_fit_guess": {"nordic": 0, "warm-modern": 0, "japandi": 0, "mediterranean": 0, "modern-country": 0, "boho": 0},
       "trade_discount_needed_pct": 0, "why_he": "..."}],
     "verdict_he": "..."}}}
  ```
- `data/leads/final-2026-10-13/results/il-<group>.md`, a short Hebrew summary:
  - the top shops, ranked by how many gaps they cover;
  - per room and style, what Israel can fill;
  - what Israel can't fill either.

## Rules
- Public web pages only.
  - No logins, no forms, no CAPTCHA or block bypassing.
  - No scraping of marketplaces that forbid it.
  - No scraper APIs, no user-agent tricks.
  - A page that blocks you: note it and move on.
- Never contact anyone, sign up, or send a form.
- Do not edit cards, binding docs, `searched-index.json`, the Studio or the site.
- Validate your JSON with Python if you can. If you can't run Python, check the brackets and quotes carefully; the art director validates.
