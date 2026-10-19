# Round 6: channels and methods we haven't tried (2026-10-19)

The owner (2026-10-19): "ובא במקביל נמצא שיטת ליקוט או אתרים שלא בדקנו.. חשוב 80 אחוז".

## Where we are
Coverage (`final_round_coverage.py`, pct_ready: 3 ready options per slot) is **61.2%**.

| Style | Ready | Needed for 80% | Missing |
| --- | --- | --- | --- |
| nordic | 66 | 81 | 15 |
| warm-modern | 81 | 100 | 19 |
| japandi | 76 | 100 | 24 |
| mediterranean | 75 | 100 | 25 |
| modern-country | 71 | 100 | 29 |
| boho | 72 | 100 | 28 |

That is **140 style-slots** in all. The gap by group (`round5/targets.json`):

| Group | Slots | Options still needed | Style-slots at zero |
| --- | --- | --- | --- |
| storage-function | 24 | 241 | 70 |
| lighting | 19 | 181 | 42 |
| textile | 13 | 118 | 32 |
| ceramics-tableware | 18 | 112 | 25 |
| art-decor-toys | 8 | 30 | 6 |

The audit (`round5/sourcing-failure-audit.md`) found the gap is **structural**:
- Wired lamps with CE exist only on AliExpress.
- Heavy and bulky items (furniture, floor planters, rugs) lose money when shipped one by one from China.
- Many style-slots never saw a product with fit 7+.

Better search words alone add about 10. **So this round looks for new sources and new methods, not more of the same.**

## Already tried (don't repeat)
Read `docs/suppliers/directory.md`, `access-and-pipeline-2026-10.md`, `aggregators-2026-10.md`, `deep-research-2026-10.md`, `data/suppliers/access-options.json` and `data/suppliers/directory.json` for the full list. In short:
- CJ (API);
- AliExpress (DS API, in a separate session);
- Zendrop;
- Yakkyofy and the agents in the aggregators doc;
- Syncee and BigBuy (drafts only: Syncee needs a sign-up, BigBuy needs a subscription);
- Bloomingville (draft);
- Etsy masterpieces;
- the Israeli shops, partners and boutique rugs;
- Morocco, Egypt and the Chinese API sources of 2026-10-17;
- 1688 and Alibaba (CAPTCHA).

## Owner rules that hold
- **AU1:** only dropshipping counts. An Israeli shop or partner counts only after a clear trade-price and supply agreement.
- **AU2:** 8 dead slots are excluded.
- **AU3:** 6.5 counts only for the 13 approved items.
- **ה.10, ה.11, ה.13:** Israeli-value pricing with comps; under 40% only with no alternative; no loss.
- **Rugs:** natural fibre only, 80% or more.
- **S5:** no print-on-demand.
- **Lighting:** CE and 220–240V stated, or a shade only.
- **Kids' items:** EN71.
- **PRE1:** heavy items may show "המלאי אינו זמין כעת".

## Track A: new channels (web research)
Output: `data/leads/final-2026-10-13/results/round6-channels.md` (Hebrew) and `round6-channels.json`.

1. Find channels **not in the list above** that can supply our gap groups to Israel, either by dropshipping or in small quantities. Kinds to check, and others you find:
   - Chinese platforms with dropshipping and shipping to Israel: Banggood, DHgate, Tmall/Taobao export programs.
   - EU and US dropship networks that ship to Israel: VidaXL, Spocket, Faire, Ankorstore, Creoate, AppScenic, Wholesale2B and others. **Check Israel shipping first.**
   - Origin countries with a strong craft supply: India (block-print and handloom textiles, brass and cane lighting, dhurries, jute), Vietnam and Indonesia (rattan, seagrass, bamboo, lacquer), Portugal and Greece (ceramics). Look for exporters with small minimums or a dropship program.
   - **Turkey:** first check whether trade with Israel is open in 2026. If it's still closed, say so and skip it.
   - Israeli dropship suppliers or B2B wholesalers that ship to the end customer.
2. For each channel:
   - ships to Israel (yes/no, with the source);
   - the model: dropship, small MOQ, or wholesale only;
   - access: API, feed, CSV or manual; sign-up and fees;
   - **a sample:** search 5 of our open slots on public pages and list up to 3 plausible products per slot, with link, price, shipping to Israel and size;
   - reliability.
3. Rank the channels by **expected style-slots closed per unit of effort**, against `round5/targets.json`.

## Track B: new methods on the channels we have (local tools and CJ)
Output: `data/leads/final-2026-10-13/results/round6-methods.md` (Hebrew) and `round6-methods.json`. You may write candidate cards per the round-5 brief's card rules.

1. **Image-first search:**
   - Find similar products from the images of approved and near-miss items: `scripts/sourcing/google_vision_source.py`, if the key `GOOGLE_VISION_API_KEY` is set in the environment (never print it), and AliExpress image search through a queue for the AliExpress session.
   - Report whether the key is available. If it isn't, say so and continue.
2. **Browse by category instead of keywords:** CJ category IDs (`docs/suppliers/cj-categories.md`) for the gap groups, with `--hide-seen`, within the CJ budget (`scripts/sourcing/budget.py`, soft stop at 40k points a day).
3. **Expand from proven sellers:** other products from the CJ suppliers and AliExpress stores of our approved cards. Use the API if it allows; otherwise send a queue to the AliExpress session (`round5/ae-queue-*.json`, the same shape).
4. **The cache, again, by image or attribute:** within the 45,446 records (`scripts/sourcing/cache_search.py`), anything matching the gap slots by material, form and size that the word search missed.
5. **Per gap slot, the blocking reason:** is it the price, the freight, the size, the style, or no product at all? Do this for the 70 storage and the 42 lighting style-slots at zero. Propose rule changes **only as questions to the owner**, with the gain in style-slots.

## Rules (both tracks)
- **Official APIs and public pages only.** No scraping AliExpress or BigBuy, no scraper APIs, no user-agent tricks. Stop at any login, CAPTCHA or block.
- **No contact, sign-ups or forms.** A channel that needs a sign-up is listed for the owner.
- **Never print, read or write keys or tokens.** Only the scripts touch `~/.cache/`.
- Don't edit existing cards, slots, binding docs, `targets.json` or scripts.
- Validate every JSON you write.
- Run Python that reads cached data with `-I`.
- No commits.
