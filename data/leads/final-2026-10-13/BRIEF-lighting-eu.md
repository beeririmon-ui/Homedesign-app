# Lighting from Europe: brands that design in Europe and make in Asia (2026-10-14)

The owner (2026-10-14): "ומה עם אירופה? Next? או מישהו אחר שעושה את הפרוסס מסין לאירופה?"

## Background (don't redo this)
- **`docs/suppliers/directory.md`** (2026-10): no European supplier confirmed shipping to Israel.
  - Bloomingville is the only one that declares drop shipment.
  - vidaXL doesn't ship to Israel.
  - BigBuy is unverified; Lucide (BE) is unverified for Israel.
- **`docs/suppliers/lighting-certified-cn-2026-10-14.md`:** Chinese factories gave 0 grade-A and 2 grade-B suppliers, and large lights lose money on shipping volume (box size, not weight).
- **What's new in this round: the "China → Europe" model.**
  - Many European lighting brands design in Europe and manufacture in Asia. As the EU importer, the brand must hold the CE technical file and DoC. Since Dec 2024 (GPSR) every product sold in the EU also needs an EU responsible person.
  - So their documents are real.
  - The questions are whether they reach Israel, at what price, and whether they ship flat.

## Brands to check
Start with these; add others you find:
- **Scandinavian:** Nordlux, Markslöjd, Globen Lighting, PR Home, Halo Design, House Doctor (lighting), Bloomingville (lighting), Hübsch, Watt a Lamp.
- **Flat-pack shades** (the answer to the volume problem): **UMAGE** (formerly VITA Copenhagen), and any similar flat-pack or self-assembly shade brands you find.
- **Others:** Lucide (BE), Light & Living (NL; Israeli importer The Collection, see `docs/suppliers/decor-il-2026-10-12.md`), Leitmotiv / Present Time (NL), Bloomingville Mini (kids).
- Premium brands (Le Klint, Tom Rossau, Nuura and the like) go in a short "masterpiece only" list, not the main table.
- **NEXT (UK):** check in one line whether it has any reseller, wholesale, dropship or affiliate programme, or whether it only sells retail direct to Israel, which would make it a competitor.

## For each brand, find (public pages only)
1. **An Israeli distributor or stockist** (name, URL, contact). If one exists, that is the best route: local stock, the Israeli standard, a trade price. Check the brand's "where to buy" / "dealers" page and Israeli shop search results.
2. **Dropship or reseller programme:** minimum order, ships to Israel (yes / no / unknown), and the B2B portal URL.
3. **Documents:** CE, EPREL registration where relevant, a downloadable DoC or test data (a link per model where available). Grade them as in `BRIEF-certified-lighting-cn.md` (A/B/C).
4. **Flat-pack or compact shipping:** yes/no, with carton dimensions where given.
5. **Models matched to our lighting gaps:**
   - the gaps: `data/leads/final-2026-10-13/coverage.json` → `remaining.<style>`, category containing "light";
   - envelope and electrical needs: `data/slots/<room>.json`;
   - style rules: `docs/design-bible/nordic.md`, `nordic-dining.md`, `docs/design-bible/<style>-brief-draft.md`.
   - Give 2–5 models per brand, with dimensions, EU retail price, Israeli retail price if a stockist sells it, and style fit (1–10, a guess from text and images where possible).
6. **Economics** (studio formula):
   - net = price/1.18; contribution = net − landed − (0.02·price + 1.2) − 0.08·net; fx EUR→ILS 3.9.
   - Give the margin at the Israeli value when buying at about 50% of EU retail (a typical wholesale price), with shipping to Israel where known.
   - Say what's unknown.

## Hard limits
- Public pages at a human pace. Stop at any login wall, CAPTCHA or block, and say so.
- No sign-ups, forms, messages or emails.
- No product cards. Don't edit binding docs, slots or cards.

## Output
1. `docs/suppliers/lighting-eu-2026-10-14.md`, a short Hebrew report:
   - a ranked table, ranked first by an Israeli distributor or Israel shipping, then flat-pack, then style fit;
   - the routes in order: an Israeli distributor; the brand's own dropship; ordering small stock;
   - the questions to ask;
   - a one-line verdict on NEXT.
2. `data/leads/final-2026-10-13/lighting-eu-2026-10-14.json`: the same content as valid JSON, with brands, models, distributors and grades. Put it in this folder, not in `results/`.

## Acceptance
- At least 8 brands checked, each with a URL for every claim.
- For each brand: whether an Israeli distributor exists (yes / no / not found), and Israel shipping (yes / no / unknown).
- At least 3 brands with models fit ≥ 7 for a style that needs that slot.

Return a short Hebrew summary:
- which brands have an Israeli distributor;
- which ship flat;
- the best 3 routes;
- the NEXT verdict.
