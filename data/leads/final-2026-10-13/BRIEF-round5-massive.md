# Round 5: the massive sourcing round to 80% in every style (2026-10-17)

The owner (2026-10-17), recorded in `docs/studio-rules.md` ז:

> "בואי נעשה ליקוט מאסיבי לנסות לסיים את ה-80 אחוז בכל האופציות... אולי מילות חיפוש אחרות, אולי הגבלות מחיר שעצרו אותנו"

## The goal
**80% of the slots in every style with 3 ready options.** This is the `pct_ready` measure in `scripts/sourcing/final_round_coverage.py`. Colours and prints of one card count, up to 3 per card.

| Style | Slots | Covered now | Goal | Still needed |
| --- | --- | --- | --- | --- |
| nordic | 109 | 66 | 88 | 22 |
| warm-modern | 132 | 76 | 106 | 30 |
| japandi | 132 | 66 | 106 | 40 |
| mediterranean | 132 | 62 | 106 | 44 |
| modern-country | 132 | 52 | 106 | 54 |
| boho | 132 | 55 | 106 | 51 |

A slot only counts once it reaches 3 options.
- **Partial slots first:** closing a slot that already has 1–2 options is the cheapest win. Then slots that several styles need at once.
- **The weakest styles weigh most:** modern country, boho, mediterranean and japandi.

## What stopped us before (the analysis)
- **Price, the biggest one:** 141 candidates with fit 7+ were dropped as "loss at the slot price". The slot price was often the old, low card price, not the Israeli value (rule ה.10).
- **Size:** 64 were dropped because they were slightly outside the envelope.
- **Words:** most queries were literal English product names. Chinese sellers list with other words, for example "pastoral" for country, "coarse pottery", "ins style", "French retro", "cream style", "wabi sabi".
- **Unused cache:** about 9,000 products are already opened and cached (AliExpress and CJ, many with freight to IL), plus about 21,000 search listings. Most were checked for one slot only.

## Your input
- **Your targets:** `data/leads/final-2026-10-13/round5/targets.json`. Take only the targets whose `group` is yours. Each target gives:
  - the styles that need it, with `have_ready` and `need`;
  - the slot spec;
  - per style: the designer's spec, queries, price ceiling and existing picks;
  - `already_searched_aliexpress`;
  - **`unused_candidates`**: products already found, with their blocker.
- **The gap packs:** `data/leads/final-2026-10-13/<style>.json`, for `already_searched_cj_global`.
- **Searched index:** `data/leads/next-sourcing/searched-index.json`, the CJ and Zendrop queries that already ran. Don't repeat one or a near-duplicate.
- **Style rules:**
  - Nordic: `docs/design-bible/nordic.md` and `docs/design-bible/nordic-dining.md`.
  - The other styles: `docs/design-bible/<style>-brief-draft.md`.
  - Also `.claude/skills/interior-design-rules/`.
- **Binding rules:** `docs/studio-rules.md`. Read ג.0–ג.3, ד (standards), ה.10–ה.14, and ז, including the new 2026-10-17 entry.
- **Slots:** `data/slots/<room>.json`.
- **Card schema:** `data/product-card.schema.json`. Look at existing cards in the same folder first and follow them.
- **Pipeline rules:** `scripts/sourcing/README.md`, for the registry, budget and cache.

## Work in this order, per target

### Step 1. Rescue the unused candidates (no API)
For each item in `unused_candidates`:
- **`loss_at_slot_price`, `unpriced` or `below_40`:**
  - Price it by **the Israeli value** (ה.10). Use 2–3 comparable products in Israeli shops (public pages, give the URLs). Set the price about 10–25% below the typical comp.
  - A product can be priced above the old slot price when the market supports it. A premium lamp is not a ₪99 lamp.
  - Re-run the economics at that price. Take freight from the cache (`cache_search.py --id`) or from CJ.
  - If it no longer loses money, it can get a card.
  - **Truly heavy or bulky losers** (floor lamps or big rugs at −100%) are real losses: drop them fast, don't spend time on them.
- **`envelope`:**
  - First look for another size of the same product, from the same supplier or another.
  - Up to about 10% outside the envelope may still get a card, marked `"fits_envelope": "borderline"`, with the size in `why_he` ("גבולי, לבדוק בפריים"). The designer decides later.
  - More than that is a no.

### Step 2. Mine the local cache (no API)
`python3 -I scripts/sourcing/cache_search.py` searches every product and listing we already fetched:
- Run it with `--help`.
- Words are AND. Use `--any` for OR, `--not` to exclude, and `--opened` for products with full details.
- Look for items that fit your slots in other styles, or fit other slots. A basket opened for the hall may be right for the bath in boho.
- **Registry status:**
  - `rejected` with a reason about another slot or style does **not** block it here. Read the reason.
  - A rejection for the product itself (quality, replica, plastic, no CE) does block it.
- **Opened AliExpress products** have SKUs, package size and cached IL freight. Check the photos, the title and the SKU list in the cache file (`data/sources/aliexpress/<id>.json`).
- **Listed-only items** (`kind: listed`) have no details or freight.
  - **There is no AliExpress API in this session**, so don't try to open them.
  - Put the best ones (fit 8+ and clearly in a gap) in your AliExpress queue file (see Output), for the AliExpress session.

### Step 3. New searches, with new words (CJ and Zendrop)
For each target that is still short, write **new** English queries. Not the queries in the index, not near-duplicates. Mix these approaches:
- **Seller style words:**
  - "ins style", "nordic ins", "japanese style", "wabi sabi", "french retro", "french country";
  - "american country", "pastoral", "idyllic", "rural retro", "farmhouse", "cottagecore", "provence";
  - "mediterranean", "greek", "santorini", "moroccan", "bohemian", "ethnic", "tribal";
  - "cream style", "quiet luxury", "mid-century", "vintage distressed".
- **Material plus form:**
  - Fibres and wood: seagrass, water hyacinth, rattan, cane, abaca, jute, raffia, paper rope, cotton rope, bamboo, teak, acacia, mango wood, olive wood, walnut, beech.
  - Stone and clay: travertine, marble, terrazzo, sandstone, coarse pottery, stoneware, terracotta, unglazed, reactive glaze, speckled, crackle.
  - Fabric: linen, washed cotton, muslin, gauze, waffle, seersucker, gingham, ticking stripe, toile, chenille, boucle, slub, macrame, tufted, punch needle.
- **Trade names:** peshtemal, fouta, hammam towel, dhurrie, chindi, kilim, kantha, boucherouite, lumbar pillow, lantern, pleated, scalloped, fluted, ribbed.
- **The literal Chinese-English listing phrases:** "home decoration ornaments", "desktop ornament", "handmade storage basket", "high-end", "retro distressed", "light luxury".
- **Sizes:** in cm and in inches.
- **Category browsing:** on CJ use `/product/list` by category, for slots whose products have varied names. Category ids are in `docs/suppliers/cj-categories.md`.
- **Near misses:** search for the same item in another size or colour, or from another listing with cheaper freight.

Run each query on CJ with `--hide-seen`, and the best 1–3 on Zendrop. Open only promising hits.

### Step 4. Economics, fit and the card
- **Economics:** use the Studio formula.
  - fx 3.3, VAT 18%, card fee 2% + ₪1.2, returns 8% of net.
  - Shipping for qty q: unit + (q−1)·max(0, unit−3.72) USD.
  - landed = (cost·q + shipping)·3.3.
  - net = price/1.18.
  - contribution = net − landed − (0.02·price + 1.2) − 0.08·net.
  - margin = contribution/net.
  - The price is the Israeli value, with comps.
- **Fit guess:** 1–10 for each of the six styles, **honestly**.
  - The master-designer audits a sample of this round.
  - An inflated fit is reverted, and it costs us more than a missing option.
  - `variants_fit`: how many of the product's colours fit each style.
- **Write a card when all of these hold:**
  - fit ≥ 7 in a style that still needs this slot;
  - **no loss** at the Israeli-value price (ה.13);
  - the envelope fits, or is borderline as above;
  - lighting has CE and 220–240V as stated by the supplier, **or** it is a shade-only product (ז, 2026-10-14) for pendant or ceiling slots, sold with an E27 suspension set;
  - kids' and toy items have EN71 / ת"י 562 as stated;
  - it is not a replica of a designer piece.
  - Below 40% margin is allowed when there is no alternative (ה.11); say so in `notes`.
- **The card itself:**
  - Write it per the schema, in the same folder as the existing cards for that slot, with `status: "candidate"`.
  - Fill in the real supplier URL, cost, shipping days, dimensions, materials, images, `safety` and `options` (all the supplier's SKUs; see `scripts/sourcing/options.py`).
  - Add a `notes` line starting "round5 2026-10-17:" with the economics, the comps and the fit guesses.
  - Do NOT set `style_scores`.
- **Cap:** only as many cards as the styles still need in that slot (3 − have_ready, per style). No more than 10 new cards per slot. One product that serves several styles beats several that serve one.
- **Registry:** mark every opened product: `card` with the card id, or `rejected` with a short reason (see the README).

## Tools and budget
- **CJ:** `python3 scripts/sourcing/cj_source.py --by round5-<group> --run-id round5-<group> --max-points 6000 --max-calls 400 --hide-seen search "<keywords>"`.
  - Costs: search 50, product 10, freight 10.
  - **Your team's cap is 6,000 points and 400 calls.** The daily budget is shared by 6 teams.
  - Use the same `--by`, `--run-id`, `--max-points` and `--max-calls` flags on every `product` and `freight` call too.
  - Pace your calls: CJ returns 429 if you go too fast.
- **Zendrop:**
  - Load the tools with ToolSearch: `select:mcp__Zendrop_mcp__get_catalog_products,mcp__Zendrop_mcp__get_catalog_product,mcp__Zendrop_mcp__get_catalog_shipping_estimate`.
  - Country "il". Up to about 150 calls.
  - Read-only: never import, order or change anything in the account. If the tools are missing, continue without them.
- **Cache:** `python3 -I scripts/sourcing/cache_search.py`, free.
- **Web:** WebSearch and WebFetch for Israeli comps only. Use public pages at a human pace, and stop at any login or CAPTCHA.

## Output (write only these; no commits)
- **Cards**, as above.
- `data/leads/final-2026-10-13/results/round5-<group>.json`, in the same shape as `results/cj-zendrop-*.json`:
  ```json
  {"group": "...", "date": "2026-10-17", "cj_points_used": 0, "zendrop_calls": 0,
   "slots": {"<room>/<slot>": {"queries_cj": [], "queries_zendrop": [], "queries_cache": [],
     "candidates": [{"source": "CJ|Zendrop|AliExpress", "found_by": "rescue|cache|search", "id": "", "url": "", "title": "", "image": "",
       "sku_or_vid": "", "cost_usd": 0, "ship_usd": 0, "ship_days": "", "landed_ils": 0, "price_ils": 0, "price_basis_he": "", "comps": [],
       "margin_pct": 0, "dims_cm": "", "fits_envelope": "yes|borderline|no",
       "style_fit_guess": {"nordic": 0, "warm-modern": 0, "japandi": 0, "mediterranean": 0, "modern-country": 0, "boho": 0},
       "variants_fit": {"<style>": 0}, "card_id": "<id or null>", "why_he": ""}],
     "verdict_he": ""}}}
  ```
  - Every candidate you judged goes in, including the rescued ones: a rescued product that gets a card is listed here again with its `card_id`.
  - **Write this file as you go**, after each slot, so nothing is lost if you stop.
- `data/leads/final-2026-10-13/round5/ae-queue-<group>.json`: AliExpress listings worth opening in the AliExpress session.
  ```json
  {"items": [{"id": "", "url": "", "title": "", "slot": "", "styles": [], "why_he": ""}]}
  ```
- `data/leads/final-2026-10-13/results/round5-<group>.md`, a short Hebrew summary:
  - per style, how many slots in your group now reach 3 options;
  - how many came from rescue, cache and search;
  - which new words worked;
  - where nothing was found, and what you suggest;
  - CJ points and Zendrop calls used.

## Rules
- Never read, print or write API keys or tokens (`~/.cache/cj`, `~/.cache/ae`, env vars). The scripts handle auth.
- Never contact a supplier, sign up, order or import.
- Do not edit:
  - existing cards;
  - binding docs (`docs/`, `data/slots/`);
  - `searched-index.json`;
  - `targets.json`;
  - the Studio or the site.
- Validate every JSON you write (`python3 -m json.tool`).
- Run Python that reads downloaded or cached data with `-I`.
- **Stopping:**
  - If you hit your budget, stop cleanly and say where you stopped.
  - If CJ returns exit code 3 (budget stop), don't work around it.
- Return a short Hebrew summary:
  - cards written;
  - style slots closed;
  - what was rescued;
  - the new words that worked;
  - what's blocked.
