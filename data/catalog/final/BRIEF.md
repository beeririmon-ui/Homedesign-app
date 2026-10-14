# Finishing: the final catalog per style (2026-10-13)

The owner (2026-10-13):
- "ושנסיים את הליקוט הזה נעשה פינישים לכל הליקוט ונתחיל להקים את האתר".
- "בתוך הסלוטים גם צבעים, גם צבעים שונים ... צריך שיהיה כל האופציות הנוספות".
- "צריכים כבר להתקדם ולפתוח את האתר".

You are the master designer for **one style**. Your job is to write that style's **final catalog**: for every slot in the house, the options the site will sell.

The site is being built now, in parallel, and will read your file.

## Input
- **Style rules:**
  - Nordic: `docs/design-bible/nordic.md` and `nordic-dining.md`.
  - The other styles: `docs/design-bible/<style>-brief-draft.md`.
  - `.claude/skills/interior-design-rules/` (use the skill).
  - `docs/studio-rules.md`: all of it. The key sections are:
    - ג.3: colour and print are variations;
    - ה.10–14: price by Israeli value, no loss, prefer 40%, design before profit, masterpiece and price tiers;
    - ז.
  - `docs/strategy/masterpiece-and-price-tiers-2026-10-12.md` and `data/strategy/masterpieces-2026-10-12.json`. Decision MP is still open, so mark masterpiece picks `"pending": "MP"`.
- **What you already have:**
  - Nordic: `data/compositions/<room>-nordic-2026-10-11.json`.
  - The others: `data/catalog/<style>-2026-10-12.json`.
- **Everything sourced since:**
  - `data/leads/final-2026-10-13/results/*.json`. These are candidates with `style_fit_guess` and `card_id` (CJ, Zendrop, AliExpress) and Israeli-shop products (`il-*`).
  - Cards whose `notes` start with "final-round 2026-10-13" or "profit-fix", and AliExpress cards from the cloud session (`data/products/**`).
  - `data/leads/aliexpress/catalog-2026-10/matches.md`.
- **The whole basket:** every card in `data/products/**`, about 300 of them. A card from any slot or style that fits your style and the slot is a pick, and a strong one (shared supplier). Many cards were only ever scored for Nordic. Look at their images, not only their titles: local thumbnails are in `studio/dist/img/p/<card id>.webp`, which you can Read as images. Images of AliExpress records without a card are in `studio/dist/img/a/`.
- **Colour and print options:** each card's `options.axes` and `options.skus`, which give an image per SKU. One product in 2–3 colours that suit your style counts as 2–3 picks. Each pick carries its own `sku_id`.
- **Slots:** `data/slots/<room>.json`, with envelope, set_of and electrical.
  - Skip `kind: fixed-product` (furniture follows plan B).
  - Nordic `on-hold` slots: list them as on-hold.
- **Economics:** `data/economics/products.json`. It holds `retail_ils`, margin and flag for priced cards; new cards have no price yet.
  - Formula: net = price/1.18; contribution = net − landed − (0.02·price + 1.2) − 0.08·net.
  - landed = (cost·qty + shipping)·3.3. Shipping for qty q is unit + (q−1)·max(0, unit−3.72) USD.

## What to decide, per slot
1. **Up to 3 picks:**
   - Design first: score each candidate 1–10 for your style; a pick needs ≥ 7.
   - Never a loss at the price you set.
   - Prefer ≥ 40%; lower is allowed only when no equally beautiful option reaches it (ה.11).
   - Respect the envelope; ±5 cm is "check in frame".
   - For lights: CE and 220–240V (IP44 in the bath).
   - For kids' items: EN71 / ת"י 562. A product without a declared standard can be a pick only with `"needs": "standard"`.
2. **Tiers (ה.14):**
   - Where the 3 picks differ in price, mark them `entry`, `middle` and `premium`. The **default is the middle**.
   - Where they don't differ, mark them all `middle` and pick the most beautiful as the default.
3. **Price per pick** (`price_ils`):
   - Keep the card's `retail_ils` if it is set.
   - Otherwise set the Israeli-value price: the slot price, or Israeli comps for a different item class, about 10–25% below comparable shops. Give the comps in `price_basis_he`.
   - Give `margin_pct`.
4. **Israeli-shop products** can be picks with `"source": "il"`. They are not sellable until a trade price is agreed, so they never become the default while a sellable pick exists.
5. **Status:** `full` (3 picks), `partial` (1–2) or `empty`. Write a one-line `note_he` for anything not full.
6. **The whole room:** check palette, materials, visual weight, lighting layers and texture rhythm across the defaults, as the Bible asks. Swap defaults for harmony if needed.

## Output (write only these; do not edit cards, slots, binding docs or products.json; no commits)
- `data/catalog/final/<style>.json`:
  ```json
  {"style": "...", "date": "2026-10-13", "rooms": {"<room>": {"slots": {"<slot id>": {
     "status": "full|partial|empty|on-hold", "masterpiece": false,
     "picks": [{"card_id": "...", "sku_id": "<options sku id or null>", "label_he": "short name incl. colour",
       "style_score": 0, "price_ils": 0, "price_basis_he": "...", "margin_pct": 0, "tier": "entry|middle|premium",
       "default": true, "source": "dropship|il", "needs": null, "pending": null}],
     "note_he": "..."}}, "room_check_he": "..."}},
   "summary": {"slots": 0, "full": 0, "partial": 0, "empty": 0, "on_hold": 0, "new_prices": 0}}
  ```
- `docs/catalog/final/<style>.md`, in Hebrew:
  - a table per room: slot → default, then the other picks, with price and margin;
  - the whole-house look;
  - the empty slots and what would fill them;
  - prices you set that the owner should see.
- You can't run a parser, so check the brackets and quotes carefully. The art director validates with Python.
