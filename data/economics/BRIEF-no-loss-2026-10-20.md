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

## Correction (2026-10-20, after the first pass)
The first pass raised 162 prices because the scenario definition above was too wide. It was reverted (commit be35e4b0). `scripts/economics/no_loss.py` holds the agent's mid-correction version (commit 32ef3435, not validated). The corrected rules:
1. **Shipping method.** The worst case runs only over the method we actually ship with by default: the cheapest method that ships the product to Israel, tracked where the supplier offers tracking (usually CJ Eub, or the AliExpress method on the card). Never CJ To Door, DHL or any express line when a cheaper method exists. If express is the **only** method, the product is listed separately as "express only".
2. **Quantity.** The Studio's combined-parcel formula: freight for q = unit + (q−1)·max(0, unit−3.72). Not one parcel per unit.
3. **`kitchen-sconce-…-632957`** is one unit, not four.
4. **Variants, colours and sizes** stay in the worst case.
5. **Prices:** new price = max(current price, corrected no-loss price), rounded up to an ending in 9. Never lower. The owner's cushion (₪69) is never changed; its corrected no-loss price is reported (decision NL1).

**This run is report mode only.** Nothing in `data/economics/products.json`, in the cards or in the Studio changes. The manager reads the report, then a second short brief applies it.

### Output of the report run
- `scripts/economics/no_loss.py`: finished and validated (`--check` runs; a `--report` mode writes the files below without touching data).
- `data/economics/no-loss-report-2026-10-20.json`: per product: current price, worst scenario (method, quantity, variant), worst contribution, break-even, proposed price, flag (`ok` / `below-floor` / `above-market` with the ratio to the highest comp / `express-only` / `cannot-compute` with the reason).
- `data/economics/no-loss-report-2026-10-20.md` (Hebrew): the counts, the raises (range and median ratio), the above-market list, the express-only list, the products that cannot be computed, the count of products above ₪247 before and after, and the rejected round-5/6 candidates that failed only on a loss (fit 7+) with their no-loss price, ratio and coverage gain per style.
