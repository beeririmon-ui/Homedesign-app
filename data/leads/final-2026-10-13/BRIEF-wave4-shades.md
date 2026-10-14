# Wave 4: shades only, with no electrical parts (2026-10-14)

The owner (2026-10-14): "חפש עוד ספקים? או אהילים ללא בית נורה כמו המרוקאיות מנחושת/פליז".

## Why this solves two problems
1. **Certification.** A shade with no socket, wiring or driver isn't an electrical product. The electrical-standard rule (S2B: CE, 220–240V; Israeli ת"י 20) applies to the **suspension set**, not to the shade.
   - We sell the shade, and pair it with a suspension set (E27 socket, cord, canopy) that carries a standard. That set comes from a source with real documents.
   - The product page says: "shade only, mounts on a standard E27 pendant set, LED bulb up to X W".
2. **Shipping.** Shades-only listings are lighter, and many fold, nest or ship flat: paper, fabric, pleated, rattan nesting sets, split bamboo. That changes the economics of the large pendants that lost money in wave 3 because of $94–718 express shipping.

## Scope: the slots
- **Pendant and ceiling slots, where a shade on a pendant or ceiling set is the product.** The style gaps are in `coverage.json` → `remaining.<style>`:
  - `dining-room/dining-pendant` (mediterranean, modern-country, boho);
  - `living-room/pendant` (mediterranean, modern-country, boho);
  - `master/pendant` (mediterranean, modern-country, boho);
  - `work/pendant` (nordic, mediterranean, modern-country, boho);
  - `kids/pendant` (modern-country);
  - `hall/ceiling-light` and `corridor/ceiling-lights` (nordic, modern-country), only with a shade that mounts on a ceiling set.
- **Envelope, placement and electrical needs:** `data/slots/<room>.json`.
- **Not in scope:**
  - the bath (IP44 needs a sealed fitting);
  - wall sconces;
  - floor and table lamps, which need a wired base.
- Also look for shades that would beat existing picks in the other styles. Don't overwrite anything; just list them.

## What to look for
- **Boho and mediterranean:**
  - pierced brass or copper Moroccan shades;
  - rattan, wicker, seagrass, palm and raffia shades;
  - pleated or gathered linen.
- **Modern country:**
  - pleated fabric shades (cream, sage, small floral);
  - gathered linen.
- **Nordic and japandi** (Nordic forbids brass, glass and opaque metal; see `docs/design-bible/nordic.md` lighting):
  - paper lanterns and pleated paper;
  - linen drums, wood-veneer slats;
  - natural rattan in light tones.
- **Search words:** "lampshade only", "shade without fitting", "pendant shade no socket", "replacement lampshade", "rattan lampshade", "Moroccan brass lampshade", "pleated fabric lampshade", "paper lantern shade", "collapsible", "flat pack".
- **The suspension set:** find 1–3 sources of an E27 pendant set (socket, 1–1.5 m cord, canopy) with a real standard. Prefer a public Israeli shop that sells sets marked ת"י 20, or a set whose listing has a CE DoC or test report. Neutral colours (white, black, natural cotton cord). Record price and URL. This becomes the paired add-on.

## Sources and tools
- **Read `BRIEF-cj-zendrop.md` first.** Tools, economics, card rules and limits all apply.
- **CJ:**
  - `python3 -I scripts/sourcing/cj_source.py --by sourcing-support --run-id final-w4-shades --max-points 15000 --max-calls 300 --hide-seen search "<keywords>"`, then `product <pid>` and `freight <vid> --to IL`.
  - New queries only; check `data/leads/next-sourcing/searched-index.json`.
- **AliExpress:** **offline only**. The account is near its weekly API limit, which resets 2026-10-20.
  - Scan the cached records in `data/sources/aliexpress/*.json` (and the deep and scale files) for shade-only listings.
  - Write cards with `python3 -I scripts/ae/ds.py card <id> --slot <room>/<slot> --offline`.
  - No new AliExpress API calls.
- **Israeli shops (public pages only):** Moroccan Fantasy, Fine Lab Home (the "wild palm" shade), and others you find. These are `il` products and need a trade price, so list them; no cards.
- **Registry:** use `data/sources/seen.json` (hide-seen). Don't re-open known products.

## Card rules for shades
- Follow schema 1.1 (`data/product-card.schema.json`); `room` is required.
- `category`: "lighting".
- In `safety` and `notes`:
  - "shade only, no electrical parts. Sold with a certified E27 pendant set (S2B applies to the set). LED bulb max <W>";
  - the shade material's heat note.
- In `notes`: "final-round wave-4 shades 2026-10-14:" plus the economics.
- The price is the shade plus the paired set, at the Israeli value (ה.10). Give comps from Israeli shops (shade-only and complete pendants). No loss; prefer 40%.
- **Card cap:** up to 2 new cards per style gap, and up to 8 per slot. Prefer listings in several colours and sizes.

## Output
- **Cards** (as above).
- **`data/leads/final-2026-10-13/results/wave4-shades.json`**, in the standard results shape:
  - slots keyed "<room>/<slot>";
  - candidates with `source`, `id`, `card_id`, `style_fit_guess` (6 styles), `variants_fit`, economics and `price_basis_he`;
  - plus `"shade_only": true` and `"needs": "pendant-set"`.
  - Put the suspension-set sources under a top-level `"pendant_sets"` list.
- **`data/leads/final-2026-10-13/results/wave4-shades.md`:** a short Hebrew summary.
- **After writing:**
  - run `python3 scripts/sourcing/final_round_coverage.py --merge-index`;
  - run `python3 -c "import json;json.load(open('data/leads/final-2026-10-13/results/wave4-shades.json'))"` to validate;
  - report the new coverage numbers.
- **Do not** commit, push, edit binding docs or slots, or contact anyone.

Return a short Hebrew summary:
- the gaps filled, by style;
- the cards written;
- the best pendant-set source;
- whether shades fix the shipping loss for the large pendants;
- CJ points used;
- coverage before and after.
