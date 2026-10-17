# Round 5d: the audit's fixes (2026-10-17)

The audit (`round5/sourcing-failure-audit.md` and `.json`) found three things we can fix now, without the owner's decisions:
- **F4: search method.** Searching "<style> <product>" brings back mostly products we've already seen. On AliExpress only 28% of results were new. Most searches stopped at page 1. Both CJ and AliExpress match each word on its own, so long queries add noise.
- **F5: registry.** 605 items were marked rejected for "no shipping to Israel" because **one SKU** failed (DELIVERY_SERVICE_EXCEPTION). In all 6 rejected items with fit 7+, another SKU did ship, and the data is already in the cache.
- **A missing card:** the rattan cup `aliexpress:1005013248832816` for boho, at a 48% margin, never got a card.

The coverage count now applies the audit's fix:
- each supplier listing counts once per slot;
- colours stored in other axes count;
- the Nordic on-hold slots are reported.

Coverage is **55.8%**.

## The method (binding for this round)
Read `BRIEF-round5-massive.md` in full. Its card rules, economics, honest fit, no-loss rule and output shape all hold. The new rules for this round:
- **Queries:** never a style word. Use 1–4 words the seller would use, for example "storage tank", "floor mat", "steak plate" or "desktop storage basket". Use pages 1–3, sorted by orders.
- **The cache comes first.** `python3 -I scripts/sourcing/cache_search.py` now also reads the CJ search lists: 45,446 records, including about 12,000 CJ listings that were never opened.
- **Search by function.** Search for what the product does and is made of, not for what the style is called. The style is judged from the photo.

## Do, in this order
1. **The missing card:** write the card for `aliexpress:1005013248832816`, using `ds.py card --offline` from the cache. Check the slot and the economics in the audit JSON.
2. **F5, the registry:**
   - List the registry entries rejected for no IL shipping where another SKU of the same item has cached IL freight. Start with the ones that had fit 7+ in a style that still needs the slot.
   - For each, judge the shipping SKU: colour, size, fit.
   - If it passes, write the card with that SKU, offline from the cache, and mark it `card` in the registry.
   - Mark the rest with the correct reason. The reason is the SKU, not the product.
3. **F4, the leads:**
   - Start with the `query_tests` rows where `new_plausible` > 0, and the cache finds (591) in the audit JSON.
   - Then run `corrected_queries` for the 93 open slots, highest `styles_open` first, on the cache and on CJ: `python3 scripts/sourcing/cj_source.py --by round5d --run-id round5d --max-points 6000 --max-calls 300 --hide-seen search "..."`.
   - There is no AliExpress API here. Listings that are only listed (no details in the cache) go to `round5/ae-queue-5d.json`.
4. Work slot by slot, open slots first. Re-run `final_round_coverage.py` and `round5_targets.py` at the start and every few slots.

## Output (no commits)
- **Cards**, as in the round-5 brief, with notes starting "round5d 2026-10-17:".
- `results/round5d-audit-fixes.json` and `.md`, in the same shape. Write as you go.
- `round5/ae-queue-5d.json`.

## Rules
- Never touch keys or tokens.
- Never contact suppliers.
- Don't edit existing cards, slots, binding docs or scripts.
- Validate the JSON.
- Run Python that reads cached data with `-I`.
