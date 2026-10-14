# The final round, wave 3: a new method for the blocked slots (2026-10-14)

The owner (2026-10-14): "בואי נמשיך בליקוט ... אולי לשנות שיטת חיפוש ... צריך להתקרב ל-90 אחוז".

- **Coverage now:** 44.7% of slots with 3 options (`coverage.json`), 63% with at least one.
- **What's left:** mostly blocked, not unsearched.

| Blocker | Gaps | The new method in this wave |
| --- | --- | --- |
| Lights with no declared CE | about 94 lighting gaps | **Certification first:** search for and filter on lights whose listing declares CE (and IP44 in the bath) |
| Kids' toys with no declared EN71 | about 30 | **Certification first:** EN71 or CE-toy declared in the listing |
| Big items that lose on shipping | rugs, floor vases, floor lamps, storage | Lighter versions of the same role (washable flatweave and cotton rugs, foldable, fabric, paper-cord); sold per piece or set |
| Made-to-measure textiles | bench cushions, runners, the 255–265 shower curtain, roman blinds | **Custom-size listings** (made to order in any size), runners sold per metre |
| Framed art | about 20 | Prints sold **with** a wood or aluminium frame, in light sizes, or a print plus a separate frame listing |

Everything else from `BRIEF-cj-zendrop.md` and `BRIEF-wave-2.md` still applies:
- new queries only;
- multi-colour first, with `variants_fit`;
- price by Israeli value per item (ה.10, with comps);
- no loss;
- the card rules (schema 1.1);
- no supplier contact.

## Certification first: how
- **AliExpress:**
  - The `aliexpress.ds.product.get` attributes include a "Certification" property (values such as CE, EMC, LVD, RoHS, CCC, EN71, UKCA).
  - First scan **every** cached lighting and toy record (`data/sources/aliexpress/*.json` and the deep or scale files) for CE / EN71 in that property, and list the ones that fit a style and slot.
  - Then run new searches that include the words ("CE wall lamp", "CE certified pendant E27 220V", "EN71 wooden toy car"), and keep only results whose attributes declare it.
  - IP44 or higher in the bath.
  - Record `"standard_declared": "CE (seller attribute)"` in the card's `safety.certificates` and `notes`.
- **CJ:** listings rarely declare it. Read the product description (`product <pid>`) for "CE" / "EN71" / "certificate", and keep only those that state it.
- **The owner's rule (S2B):** a light or toy without a declared standard is not sold. A declared standard (seller attribute) is enough to list it as a candidate. The certificate file is requested before the first sale.

## Output
- Cards per the earlier briefs. Notes start "final-round wave-3 2026-10-14:".
- `data/leads/final-2026-10-13/results/wave3-<group>.json` in the same shape. Add `"standard_declared"` per candidate where relevant.
- A short Hebrew `wave3-<group>.md`.

Return a short Hebrew summary:
- gaps filled, by blocker;
- how many lights and toys with a declared standard were found;
- points and calls used.
