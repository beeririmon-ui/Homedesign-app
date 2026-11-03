# Brief: the five bath slots, and the candidates that come back (sourcing-agent, 2026-11-03)

The owner answered the decisions meeting today (`status/decisions-meeting-2026-11-03.md`; the answers are in `status/decisions.json`, studio rules ב.12, ה.15 and the ז log of 2026-11-03). Two answers are sourcing work.

## The answers
- **V7Q3 = yes (2):** targeted sourcing for five empty bath slots. The owner's remark behind it (2026-11-02): "בשירותים אין מוצרים כמעט".
- **NL3 = up to 2×:** the candidates rejected in rounds 5–6 only because they lost at the slot price come back, when their no-loss price is at most 2× the high Israeli comparison (35 candidates per `data/economics/no-loss-report-2026-10-20.md`).
- **R6Q1 = yes:** five existing 6.5 cards as a third option, after master-designer approves each against its image. Not your task; it is listed so you don't re-source those slots.

## Task 1: the five bath slots (Nordic first, 6–10 candidates per slot)
The specs are master-designer's, in `docs/render-v7-review-2026-11-02.md` §5.2:
- **towel-ladder:** a leaning ladder in oiled oak or teak, width 30–45, height 130–135, 4–5 round rungs. Heavy: PRE1 ("המלאי אינו זמין כעת") allowed. This is the most important addition to the bath.
- **shower-stool:** teak or oiled oak, 28–34 × 42–46, straight legs, water-resistant. PRE1 allowed.
- **bin:** a matte pedal bin, diameter 20–24, height 28–32, matte black or warm matte white, a lid that closes quietly.
- **ledge-planter:** a matte ceramic planter, 11–14 × 11–14, warm white, sand or oat, matte glaze; a humidity-loving plant as filler.
- **floor vessel (ceramic):** a matte ceramic floor vessel for the bath, per the Bible's "כלי מט" (the sea-grass basket is the 6.5 stand-in for the test).
Rules: the slot envelopes in `data/slots/bath.json`, the Bible (`docs/design-bible/nordic.md`, bath chapter), the forbidden list, and your own agent rules (sources, ד.6 search-page rule for AliExpress, `data/sources/seen.json`). A card per candidate per `data/product-card.schema.json`, in `data/products/bath/<slot>/`, with price, shipping to Israel (cost and days), dimensions, materials, link, image rights (`unclear` unless stated), standards if shown, and the no-loss price from `scripts/economics/no_loss.py` where the data allows. Mark anything you could not verify.

## Task 2: NL3, the returns
From `data/economics/no-loss-report-2026-10-20.json` (and the round 5–6 result files it cites), list the candidates rejected only for losing at the slot price whose no-loss price is ≤ 2× the high Israeli comparison. For each: restore the card's status to candidate with the no-loss price and a note "returned 2026-11-03 (NL3)", and leave the ones above 2× as they are. Write the list to `data/leads/returns-2026-11-03.md` (slot, style, product, no-loss price, comparison, ratio). If a card's comparison data is missing, list it as "needs a comparison" instead of restoring it.

## Fixed rules
- Official sources only: no scraping of AliExpress or BigBuy, no scraper services, no CAPTCHA bypass, no user-agent spoofing, no sign-ups, no contact with any supplier. The CJ API needs `CJ_API_KEY` in the environment; if it is missing, say so and use the other sources.
- Never write a key, token, phone number or business id into any file.
- New files, plus the status edits of Task 2 only. No edits to binding documents or slots. No commits.
- Return a short summary in Hebrew: candidates per bath slot with the best three and their scores, the returns count by ratio band, and what you could not verify.
