# No product loses money, in any scenario (2026-10-20)

The owner (2026-10-20): "בא נוודא שאין דבר כזה מוצר מפסיד בשום צורה! יכול להיות יקר ללקוח אבל אין מפסיד!"

The rule is `docs/studio-rules.md` ה.13, amended on 2026-10-20. In short:
- **No product loses money.** Every product's price gives a contribution of zero or more, before CAC, in the Studio formula.
- **In every scenario:**
  - every variant, colour and size;
  - every quantity we sell (freight by quantity);
  - every shipping method offered.
  - An estimated freight cost is taken at its worst case.
- **A price set by Israeli value (ה.10) that loses money is raised to the price that doesn't**, even above the highest comp. Such a product is flagged "יקר מהשוק" instead of "מפסיד".
- **No price is lowered** because of this rule.
- **A price the owner set in the Studio is never changed.** If it loses money, it's listed for the owner. Today there is one: `cushions-aliexpress-fashion-modern-wabi-sabi-464203` at ₪69, product_edits in the Studio db.

## Where we are
`data/economics/products.json` has 181 rows:
- 97 flagged `loss`;
- 71 `below-floor`;
- 13 `ok`.

Its note says it was built from `data/economics/pricing/*-2026-10-11.json`, with a fix on 2026-10-18.

The round-5 and round-6 cards in `data/products/**` may hold their own Israeli-value prices with comps. Find the real source of truth for each product's retail price: the pricing files, the card `price`, `products.json`, `studio/build.py` and `site/tools/build-catalog.ts`. Document it.

## The Studio formula
Settings are in `data/economics/settings.json`.
- fx: ₪3.3 per USD.
- VAT: 18%, so net = P / 1.18.
- Card fee: 2% + ₪1.2.
- Returns: 8% of net.
- landed = (unit cost + freight) × fx. For quantity q, freight = unit + (q−1) · max(0, unit − 3.72).
- contribution = net − landed − fees − 0.08 · net.
- margin = contribution / net.

Check the formula against `studio/build.py` and `site/shared/src/schema/economics.ts`. If they differ, report it; don't silently pick one.

## Do
1. **Write `scripts/economics/no_loss.py`:** an importable function and a CLI.
   - For each product, compute the worst-case contribution over all its scenarios, using the card, the variants, the freight data (`data/economics/freight-*.json`, `data/sources/cj`, the AliExpress results) and the settings.
   - Give the break-even price, and the **no-loss price**: the lowest price on the Studio's usual price endings that has a contribution of zero or more in every scenario.
   - Flag every estimated or missing input.
   - Run Python that reads cached data with `-I`.
2. **Audit every product** that the Studio or the site can sell: every products.json row, and every card counted by `scripts/sourcing/final_round_coverage.py`.
3. **Apply.** Where the worst case loses money, raise the retail price to the no-loss price, in the real source of truth.
   - Keep a change log: old price, new price, scenario, reason.
   - Set the flags: `ok` (40% or more), `below-floor` (0–40%), `above-market` (the no-loss price is above the highest comp; show the ratio).
   - **Never** lower a price, and **never** touch a price the owner set in the Studio. List those.
4. **Re-run the checks:**
   - `python3 studio/build.py`, and the 7 tests: `for t in studio/tests/smoke_*.py; do python3 "$t"; done`;
   - `smoke_db_contract.py` takes `--db /tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/studio-db`;
   - the site's unit tests, if they run.
   Report anything that breaks. Don't publish the Studio; the manager does that.
5. **Rejected candidates that only lost money** (`data/leads/final-2026-10-13/results/round*-*.json`): list each one that was rejected **only** for a loss and has fit 7+, with its no-loss price and the ratio to its highest comp. Estimate the coverage gain per style if they were counted. **Don't change the coverage script or any result file.** It's for the owner to decide.

## Output
- `scripts/economics/no_loss.py`.
- The updated price data, and a change log: `data/economics/no-loss-changes-2026-10-20.json`.
- `data/economics/no-loss-audit-2026-10-20.md` (Hebrew) and `.json`:
  - the formula, and where the price truth lives;
  - how many products were raised;
  - the above-market list with ratios;
  - the owner-set prices that lose money;
  - the test results;
  - the rejected candidates that could return, and their coverage gain.

## Rules
- Never print, read or write keys or tokens.
- No contact with suppliers.
- Don't edit binding docs, slots or the coverage script.
- Validate every JSON.
- No commits.
