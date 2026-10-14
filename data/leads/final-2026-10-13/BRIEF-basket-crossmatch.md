# The final round: match the existing basket to all styles and slots (2026-10-14)

The owner (2026-10-14):
- "90% זה כולל אופציות נוספות בכל סלוט";
- "קודם כל מחפשים את כל הסלוטים, ואז ... העיצוב".

The target is 90% of slots, in all six styles, with 3 options each. Colours and prints of the same product count as options (studio rule ג.3).

We already hold about 310 product cards (`data/products/**`). Most were judged only for Nordic, and only for the slot they were found for. Many of them, and many of their colour options, fit other styles and other slots: the same vase on the console in the hall, the same curtain family in every room, a throw in the master bedroom and on the hall bench.

Matching what we already have is the cheapest sourcing there is. This is **matching, not design**: no room compositions, no defaults, no tiers, no prices.

## Input
- **Your cards:** the folders listed in your task.
  - Per card: `name`, `slot`, `room`, `dims`/`dimensions`, `materials`, `colors`, `options` (axes and skus, with colour names and hex values), and `notes`.
  - **Look at the image:** `studio/dist/img/p/<card id>.webp`, which you can Read as an image.
- **Economics:** `data/economics/products.json`. Skip a card whose `flag` is `loss` unless the slot you match it to has a clearly higher Israeli price; say so in `why_he`.
- **Slots, all rooms:** `data/slots/<room>.json`, giving envelope, placement, set_of, category and electrical. Skip `kind: fixed-product`.
- **What is still missing:** `data/leads/final-2026-10-13/coverage.json` → `remaining.<style>`, the slots below 3 options per style. Prioritise those.
- **Style rules:**
  - Nordic: `docs/design-bible/nordic.md` and `nordic-dining.md`.
  - The other styles: `docs/design-bible/<style>-brief-draft.md`.
  - `.claude/skills/interior-design-rules/` (the style-fit rubric).
- **Binding:** `docs/studio-rules.md`.
  - ג.3: colours are variations.
  - Lights need CE and 220–240V (IP44 in the bath).
  - Kids' items need EN71 / ת"י 562.
  - No replicas.

## What to do, per card
1. **Fit per style:** give a fit guess (1–10) for each of the six styles: nordic, warm-modern, japandi, mediterranean, modern-country and boho. Be honest; 7 means "a designer would put it in that style's room".
2. **Fitting colours:** for every style where the card fits (≥ 7), count how many of its colour, print or style options fit that style. List them by `sku` id or colour value. A card in sand, white and terracotta might fit Nordic in 2 colours and Mediterranean in 3.
3. **Slots:** list the card under its own slot and under **every other slot, in any room,** where it fits:
   - the role and placement;
   - the envelope, where ±5 cm counts as "borderline";
   - the set size.
   Common cross-room families include vases, bowls and trays; candle holders; baskets; throws, cushions and curtains; framed art; small planters; and bath textiles.
4. Do not change cards, slots or prices.

## Output (write only this; no commits)
`data/leads/final-2026-10-13/results/basket-<group>.json`, in the same shape as the other results files:
```json
{"group": "basket-<group>", "source": "basket", "date": "2026-10-14", "cards_reviewed": 0,
 "slots": {"<room>/<slot>": {"candidates": [
   {"source": "basket", "card_id": "...", "title": "...", "fits_envelope": "yes|borderline",
    "style_fit_guess": {"nordic": 0, "warm-modern": 0, "japandi": 0, "mediterranean": 0, "modern-country": 0, "boho": 0},
    "variants_fit": {"<style>": 0}, "fitting_skus": {"<style>": ["<sku id or colour value>"]},
    "why_he": "short"}],
   "verdict_he": ""}}}
```
- List a candidate under a slot only if at least one style is ≥ 7 there.
- `variants_fit` lists only the styles ≥ 7.
- You can't run a parser, so check brackets, commas and quotes carefully. The art director validates with Python.

Return a short Hebrew summary:
- cards reviewed;
- new style-slot matches, by style;
- the biggest cross-room wins;
- cards that fit nowhere.
