# The final sourcing round: CJ and Zendrop, by room (2026-10-13)

The owner (2026-10-13): "ליקוט לכל סגנונות העיצוב, לכל חדרי הבית, ליקוט מקיף ביותר, עבודה רצינית ... ואז פינישים ונתחיל להקים את האתר".

This is the last sourcing round before the site. Its aim is to fill every slot, in every style, with up to 3 good, non-losing options.

Each team owns a group of rooms and searches **once per slot, for all six styles together**: Nordic, warm modern, japandi, mediterranean, modern country and boho. One search often finds options for several styles. That is the point: no slot is searched twice.

## Input
- **Gap packs**, one per style: `data/leads/final-2026-10-13/<style>.json`. Take only the gaps in your rooms. Each gap gives:
  - the slot spec (envelope, set_of, electrical, safety);
  - `have` and `need`;
  - the existing picks, so you don't bring the same product;
  - the designer's style spec and queries (where they exist);
  - the price ceiling: slot price, landed cost for break-even, and landed cost for 40%;
  - `already_searched_aliexpress` for that slot.
  - Each pack also has `already_searched_cj_global`, the CJ queries that already ran.
- **Style rules:**
  - Nordic: `docs/design-bible/nordic.md` and `docs/design-bible/nordic-dining.md`.
  - The other five: `docs/design-bible/<style>-brief-draft.md` (drafts, but the best guide we have).
  - Also `.claude/skills/interior-design-rules/`.
- **Binding rules:** `docs/studio-rules.md`. Read ה.10–14 and ז.
  - Price is the Israeli value.
  - Never a product that loses money.
  - Prefer a 40% margin.
  - Design comes before profit.
  - Lighting needs CE and 220–240V.
  - Kids' items need EN71 / ת"י 562.
  - No replicas of designer pieces.
- **Slot files:** `data/slots/<room>.json`.

## Tools
- **CJ API**, from this machine.
  - Read `scripts/sourcing/README.md` first.
  - Search: `python3 scripts/sourcing/cj_source.py --by sourcing-support --run-id final-<group> --max-points 7000 --hide-seen search "<keywords>"` (50 points). Product: `product <pid>` (10). Freight: `freight <vid> --to IL` (10).
  - The daily budget is shared, with a cap of 7,000 points for your team.
  - Pace your calls: CJ returns 429 if you go too fast.
- **Zendrop**, through the MCP tools: `mcp__Zendrop_mcp__get_catalog_products`, `mcp__Zendrop_mcp__get_catalog_product`, `mcp__Zendrop_mcp__get_catalog_shipping_estimate` with country "il". Load them with ToolSearch (`select:mcp__Zendrop_mcp__get_catalog_products,mcp__Zendrop_mcp__get_catalog_product,mcp__Zendrop_mcp__get_catalog_shipping_estimate`). Read-only: never import, order or change anything in the Zendrop account. If the tools are missing, say so and continue with CJ.
- **No AliExpress here.** The cloud session covers it.

## How to work, per slot
1. Read the gaps for this slot across all six packs. Note which styles need it and what each style wants (material, colour, shape).
2. Write 2–5 English queries that together cover the styles' looks. Skip any query already run, or a near-duplicate of one (`already_searched_*`).
   - Run each on CJ with `--hide-seen`, and the best 1–3 on Zendrop.
3. For each promising hit, check:
   - the product page: variants, real dimensions, materials, photos;
   - freight to IL: the cheapest option, plus the cheapest within 20 days;
   - the economics at the slot price.
   - Use the Studio formula: fx 3.3, VAT 18%, card fee 2% + ₪1.2, returns 8% of net.
     - Shipping for qty q: unit + (q−1)·max(0, unit−3.72) USD.
     - landed = (cost·q + shipping)·3.3.
     - net = price/1.18.
     - contribution = net − landed − (0.02·price + 1.2) − 0.08·net.
     - margin = contribution/net.
   - If the hit is a clearly different item class than the slot price assumes, re-derive the price from Israeli comps (give the URLs).
4. Give each candidate a **fit guess (1–10) for each of the six styles**. The designers will score for real later.
5. **Write a product card** when all of these hold:
   - fit guess ≥ 7 for at least one style that has a gap here;
   - no loss at the slot price;
   - the envelope fits. Within about 5 cm counts as "borderline, check in frame"; also check the supplier's other sizes.
   - CE for lighting, as stated by the supplier.
   - Write the card per `data/product-card.schema.json` (schema 1.1: `room` is required).
   - Put it in the same folder as the existing cards for that slot (look there first), and follow their style.
   - Set `status: "candidate"`.
   - Fill in the real supplier URL, cost, shipping days, dimensions, materials, images and `safety`.
   - Add a `notes` line starting with "final-round 2026-10-13:" that gives the economics and the style fit guesses.
   - Do NOT set `style_scores`.
   - Cap: up to 2 new cards per style that needs this slot, and no more than 8 per slot. Prefer one product that serves several styles over several that serve one.
6. Record what you rejected and why. A rejected product is still useful: it is not opened again (the registry handles that through the script).

## Output (write only these; no commits)
- **Cards**, as above.
- `data/leads/final-2026-10-13/results/cj-zendrop-<group>.json`:
  ```json
  {"group": "...", "rooms": [...], "cj_points_used": 0, "zendrop_calls": 0,
   "slots": {"<room>/<slot>": {"queries_cj": [...], "queries_zendrop": [...],
     "candidates": [{"source": "CJ|Zendrop", "id": "pid", "url": "...", "title": "...", "image": "...", "sku_or_vid": "...",
       "cost_usd": 0, "ship_usd": 0, "ship_days": "...", "landed_ils": 0, "slot_price_ils": 0, "margin_pct": 0,
       "dims_cm": "...", "fits_envelope": "yes|borderline|no", "style_fit_guess": {"nordic": 0, "warm-modern": 0, "japandi": 0, "mediterranean": 0, "modern-country": 0, "boho": 0},
       "card_id": "<id or null>", "why_he": "..."}],
     "verdict_he": "..."}}}
  ```
- `data/leads/final-2026-10-13/results/cj-zendrop-<group>.md`, a short Hebrew summary:
  - per room: how many style gaps you can now fill, and which cards;
  - the slots where nothing was found, and what you suggest;
  - CJ points used.

## Rules
- Never read, print or write API keys or tokens (`~/.cache/*`, env vars). The scripts handle auth.
- Never contact a supplier, sign up, order or import.
- Do not edit:
  - existing cards;
  - binding docs (`docs/`, `data/slots/`);
  - `data/leads/next-sourcing/searched-index.json` (the art director merges your queries);
  - the Studio or the site.
- Validate every JSON you write with Python (`python3 -m json.tool`).
- Work in priority order (high, then medium, then low). If you run out of budget, stop cleanly and say where you stopped.
