# Audit: why the sourcing fails (2026-10-17)

The owner (2026-10-17): "תעשה בדיקה מקיפה, אולי בחיפושים התפספס משהו שלא מצאנו את העמדות, אולי חוק סטודיו קטן? אולי מילות חיפוש לא נכונות? נותן למודל החזק לבדוק כשלים בליקוט".

## The situation
- The goal is 80% of slots in every style with 3 ready options.
- Coverage is stuck at **56.8%**, measured by `scripts/sourcing/final_round_coverage.py` with the designer's audit applied.
- Rounds 5, 5b and 5c (CJ, Zendrop, the local cache and AliExpress) added a lot of work for small gains. The last rounds found almost nothing.

This is not another sourcing round. It is a root-cause audit: **find what makes us miss**, and measure each cause.

## Check all six
1. **The measurement itself (bugs first).** Is `final_round_coverage.py` missing options that exist? Check:
   - **Cards the count can't see.** Cards in `data/products/**` that are not in any results file (`results/*.json`) and not in the packs' `existing_picks`, so they never count. Examples: older rounds, wave-4 shades, cross-room cards.
   - **Slot keys that don't match.** Keys in results files that don't match the eligible slot ids, for example `dining/...` against `dining-room/...`, or `entrance/...` against `hall/...`.
   - **Variant axes the count misses.** `card_variants()` only counts axes named color, style, pattern or print. Check how many cards use other names (`colour`, `Color`, `finish`, `material`, a Chinese label) and lose their variants.
   - **Stale packs.** Coverage relies on the 2026-10-13 packs (`<style>.json`, `have` and `existing_picks`). Check whether they are stale against `data/compositions/` and `data/catalog/`.
   - **Cards that exist but weren't credited.** Cards with `style_scores` from the designer that would count, but aren't credited.
2. **The rules: which rules, small ones included, block the most?**
   - Go through the rejection reasons (`data/sources/seen.json`, `rejected` with a reason) and the results files (`why_he`, `fits_envelope`, the margins, `decision`).
   - Classify every rejection of a product that had fit ≥ 7 by the rule that stopped it. For example:
     - envelope by a few cm;
     - natural fibre;
     - CE or IP44;
     - EN71;
     - no loss at the old slot price;
     - a colour banned by the Bible (oat or mist grey on the sofa, polished gold, chrome, and so on);
     - polyester or "plastic look";
     - one look across several listings;
     - set_of or pairs;
     - the card cap.
   - For each rule, count how many style-slots it alone keeps below 3, the ones that would close if it were eased.
   - Point to rules that are stricter than they need to be, with the exact text and its place in `docs/studio-rules.md`, `docs/design-bible/*` or `data/slots/*`.
3. **The search words.** For the slots still open (`round5/targets.json`):
   - Look at what actually ran:
     - `searched-index.json`;
     - `queries_*` in the results;
     - `data/sources/aliexpress/queries/` and `data/sources/cj/queries/`, which hold the real query text and the result counts.
   - Find the patterns:
     - queries that are too long or too specific (the AliExpress search is weak on long sentences);
     - English words that sellers don't use;
     - CJ matching single words, so style words return noise;
     - slots where the product's real name is different (trade or category names);
     - slots searched only in one source.
   - **Test it.** Pick 8–12 slots that are open in 2 or more styles. For each, run 3–5 new, short, seller-style queries on the local cache (`python3 -I scripts/sourcing/cache_search.py`, free) and on CJ (`python3 scripts/sourcing/cj_source.py --by audit --run-id audit --max-points 2500 --max-calls 120 --hide-seen search "..."`). See whether better words find candidates that fit. Don't write cards: list the finds.
4. **The designer's thresholds.** List the near misses: fit 6–6.9 in a style that is still open, with the reason they fell short. A small spec change could make some of them count.
5. **Slots that may not be worth searching.** Some slots are open in all six styles and nothing was ever found for them. Show them with their numbers, and what is special about each: size, a standard, a very specific spec.
6. **Coverage that is in the house but not counted.** Israeli shops (`il-*`, counted in pct_any only), the partner studios, and the boutique rugs. How many points would they add?

## Inputs (read-only)
- **Measurement:** `scripts/sourcing/final_round_coverage.py`, `scripts/sourcing/round5_targets.py`, `coverage.json`, `round5/targets.json`, `round5/designer-audit*.json`.
- **Results and packs:** `data/leads/final-2026-10-13/results/*.json` and `*.md`, `data/leads/final-2026-10-13/<style>.json`, and the briefs `BRIEF-*.md` in the same folder.
- **Products, registry and searches:** `data/products/**`, `data/sources/seen.json`, `data/leads/next-sourcing/searched-index.json`.
- **Binding docs:** `docs/studio-rules.md`, `docs/design-bible/*`, `data/slots/*`, `data/compositions/*`, `data/catalog/*`.

## Output
- `data/leads/final-2026-10-13/round5/sourcing-failure-audit.md`, in Hebrew, short and clear:
  1. **The summary:** 5–8 findings, ranked by how many style-slots each would close, with the estimate.
  2. Per finding:
     - what's wrong;
     - the proof (files, numbers, examples with ids);
     - the fix;
     - who decides: a bug the art director fixes, or a rule the owner decides.
  3. **The search words:** what was wrong, which queries worked in the test, and a list of corrected queries per open slot.
  4. **Near misses** and **slots not worth searching**.
- `data/leads/final-2026-10-13/round5/sourcing-failure-audit.json`, the same in machine form:
  - `findings[]`, each with `id`, `type` (bug | rule | search | threshold | slot), `style_slots_gain_est`, `evidence` and `fix`;
  - `query_tests[]`;
  - `near_misses[]`;
  - `dead_slots[]`.
- If you find a bug in the count, you may write a **proposed** fix as a patch file, `round5/coverage-fix.patch`. Don't change the script. Show the before and after numbers by running a copy of the script from the scratchpad: `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/audit/`.

## Rules
- Don't edit cards, results files, slots, binding docs or the scripts. Write only the outputs above and scratch files.
- Never touch keys or tokens. Never contact suppliers. No commits.
- CJ: up to 2,500 points and 120 calls. The cache is free. There is no AliExpress API here.
- Run Python that reads cached data with `-I`, and validate the JSON you write.
- **Give numbers, not impressions:** every claim backed by a count or an example id.
