# Chinese lighting suppliers that provide certification (2026-10-14)

The owner (2026-10-14): "או למצוא ספק סיני שכן נותן תקינה למנורות". The full entry is in studio rule ז, `docs/studio-rules.md`.

## Why
- **Lighting is the biggest blocked category:** 77 style-slot gaps (`coverage.json` → `remaining`, category lighting).
- **What wave 3 found:**
  - AliExpress has lights whose seller *declares* CE: 262 in our cache (`ae-certified-cache-2026-10-14.json`).
  - A declaration isn't a document. Before the first sale we need the CE Declaration of Conformity plus a test report for that model (EN 60598-1 and the relevant part 2, LVD + EMC).
  - Israel's ת"י 20 is based on IEC 60598.
  - The large lights (floor lamps, pendants 40–55 cm) lose money even at the Israeli value, because AliExpress express shipping for one big box is $94–718. See `results/wave3-repricing.md`.
- **What we need:** a supplier that has the documents *and* can send single units to Israel at a sane shipping cost. Flat-pack and collapsible shades ship light; nesting rattan and fabric drums also work.

## Where to look (public pages only)
- **B2B platforms that show certificates per supplier or product:**
  - Alibaba.com: Verified or Assessed suppliers; the "Certifications" tab with the lab named (TÜV, SGS, Intertek, BV, CQC, UL).
  - Made-in-China.com: audited suppliers.
  - Global Sources.
  - For each, check whether the supplier does single units / dropshipping / "Ready to Ship", and whether it ships to Israel.
- **Chinese lighting makers with their own export web stores:** e.g. Zhongshan/Guzhen factories, design-lamp brands. They sell retail worldwide and publish CE/RoHS documents or test reports.
- **Dropship and sourcing platforms that say they hold compliance documents:** CJ's own sourcing, Zendrop, HyperSKU, Sourcinbox, Wiio, and others you find. Check each one's lighting compliance policy, and whether it ships to Israel.
- **AliExpress brand stores:** only through WebSearch result snippets and the brand's own site. **Do not fetch AliExpress pages** (studio rule ד.6: AliExpress only via the official API).

## What fits
- **Slots:** read the lighting gaps in `coverage.json` → `remaining.<style>`, plus `data/slots/<room>.json` for the envelope, placement and electrical needs of each gap. The biggest gaps are:
  - living and master floor lamps;
  - living wall sconce, kids wall sconce, work wall sconce;
  - hall table lamp, work desk lamp;
  - corridor picture lights;
  - bath ceiling light (IP44+);
  - pendants for mediterranean, modern-country and boho: rattan, woven, linen, pleated fabric 45–55.
- **Styles:** `docs/design-bible/nordic.md`, `nordic-dining.md` and `docs/design-bible/<style>-brief-draft.md`.
  - Nordic forbids chrome, brass, glass, multi-arm and industrial.
  - Warm modern loves travertine, linen and wood.
- **Electrical:** 220–240V, an E27/E14/GU10 socket or LED, and a plug where the slot needs one (Israel type H, or the EU type with an adapter, as noted in the existing cards). IP44+ in the bath.
- **Economics** (studio formula; see `BRIEF-cj-zendrop.md`):
  - fx 3.3, VAT 18%;
  - net = price/1.18;
  - contribution = net − landed − (0.02·price + 1.2) − 0.08·net;
  - landed = (unit cost + shipping to Israel)·3.3.
  - Price by Israeli value, from the comps in `results/wave3-repricing.json` and `il-lighting.json`. No loss; prefer 40%.

## Hard limits
- Read public pages at a human pace. Stop at any login wall, CAPTCHA or block, and say so.
- None of the following:
  - sign-up, contact forms, chat or messages to any supplier;
  - scraping APIs; user-agent tricks;
  - fetching AliExpress pages.
- No product cards. These are **leads**: we don't have API data, and nothing is sellable until the documents are in hand.
- Don't edit binding docs, slots, cards or `products.json`.

## Grading the certificate evidence (be strict)
- **A:** a test report or certificate for that model, or a named model family, from an accredited lab (lab name and report number visible), plus a DoC.
- **B:** a supplier-level certificate page from an accredited lab covering lighting products, without model numbers.
- **C:** "CE" claimed in text or as a logo only.
- **Red flags:** a "CE certificate" from a non-accredited "certification company"; an EMC-only report for a mains lamp; a report for a different product; dates or numbers that don't match.

## Output
1. `data/leads/final-2026-10-13/results/certified-lighting-cn.json`. Use this shape, so the coverage script ignores it (no `card_id`):
   ```json
   {"group": "certified-lighting-cn", "date": "2026-10-14",
    "suppliers": [{"name": "", "platform": "", "url": "", "type": "factory|trading|brand-store|platform",
      "evidence_grade": "A|B|C", "evidence": "what is shown, lab, report no., URL", "red_flags": "",
      "single_units": "yes|no|unknown", "dropship": "yes|no|unknown", "ships_to_israel": "yes|no|unknown",
      "shipping_note": "flat-pack? cost to IL if shown", "moq": "",
      "products": [{"title": "", "url": "", "slot": "<room>/<slot>", "style_fit_guess": {"nordic": 0, "warm-modern": 0, "japandi": 0, "mediterranean": 0, "modern-country": 0, "boho": 0},
        "dims_cm": "", "price_usd": 0, "ship_usd_il": null, "israeli_value_ils": 0, "margin_pct_est": null, "notes": ""}],
      "public_contact": "public email/page only", "question_draft_en": "short, per this supplier"}],
    "summary_he": ""}
   ```
2. `docs/suppliers/lighting-certified-cn-2026-10-14.md`, a short Hebrew report:
   - the best 5–10 suppliers, ranked: evidence grade first, then single-unit shipping to Israel, then style fit;
   - which lighting gaps each could fill;
   - what to ask each one;
   - what remains unsolved.

## Acceptance
- At least 5 suppliers at grade A or B. If fewer exist, say so honestly; don't pad with C.
- For each A/B supplier: at least 2 products matched to real gaps, with style fit ≥ 7 in at least one style that needs that slot.
- Every claim has a URL.
- Valid JSON (the art director checks it with Python).

Return a short Hebrew summary:
- how many suppliers at each grade;
- the 3 best, and which gaps they unlock;
- whether any of them solves the big-light shipping problem.
