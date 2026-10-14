# CJ Sourcing requests, round 1 (2026-10-10), decision AC1

> sourcing-support, official CJ API only: `POST /product/sourcing/create` through `scripts/sourcing/cj_source.py` (`source` / `source-batch`), key from the environment, token only inside `scripts/cj.py`. Approval: AC1 (studio rules ד.9, 2026-10-10): up to 20 requests. Record and queue: `sourcing-requests-2026-10-10.json` next to this file. Nothing committed.

## Result
- **5 of 20 created.** The 6th call was refused: code 1600000, "Exceeded the daily source limit". So the API has the **same 5 requests per day** as the website's free tier (it was "not verified" in `docs/suppliers/access-and-pipeline-2026-10.md` 1.1; verified now). The other 15 stay `pending` in the JSON and go out at 5 per day (3 more days) with the `next_batch` command below. Whether the counter resets at 00:00 UTC like the points is not verified.
- Budget today: 550 CJ points: 5 `list` queries for reference images (250) and 6 `sourcing_create` (300, including the refused one). `budget.py` now caps `sourcing_create` at 5 per day, so a refused call no longer costs points.
- Registry: 5 entries `cj-sourcing:<cjSourcingId>` in `data/sources/seen.json` (source `cj-sourcing`, slot, by `sourcing-support`); raw responses in `data/sources/cj-sourcing/<id>.json`.
- Pipeline: `source`, `source-batch` and `source-status` were wired into `cj_source.py` (see `scripts/sourcing/README.md`). A request is sent only with `--approved "<decision id>"`.

## Created
| # | slot | cjSourcingId | reference image (card) | productName sent |
| --- | --- | --- | --- | --- |
| 1 | living-room/rug | 2610101514064490000 | rug-cj-braided-wool-natural | Flatweave wool rug 240 x 300 cm, oat / warm white, pile max 15 mm, rectangular, no long fringe |
| 2 | living-room/floor-lamp | 2610101514084500302 | floor-lamp-cj-black-drum-linen | Floor lamp 145-165 cm, matte black metal stem, base max 26 cm, linen drum shade 35-38 cm dia x 25-35 cm high, E27, EU plug 220-240V, CE |
| 3 | living-room/candle-holders | 2610101514104501300 | candle-holders-cj-travertine-pedestal | Travertine pillar candle holders, set of 2, 5-12 cm high, flat top 9-14 cm or shallow 7.5 cm recess, for 7 cm pillar candles, beige |
| 4 | living-room/pouf | 2610101514124481902 | pouf-cj-cotton-knit-ball-cover (image 2, cream) | Knitted cotton pouf / ottoman, 42-45 cm diameter, 35-36 cm high when filled, warm white or oat chunky knit, with filling or cover only |
| 5 | living-room/curtains (house family: also the dining single panel) | 2610101514144482302 | curtains-cj-japanese-linen-half-shade | Sheer linen curtain panel 140 x 280 cm, oat, 30-60% light transmission, wave or pinch pleat / back tabs, sold per panel |

Every remark ends with "Ship to Israel" and carries the slot spec (materials, colours of the Nordic palette, what is banned). No `productUrl` and no `price` were sent: a CJ URL would point CJ back at the product we already have, and the spec fits in name + remark (200 characters each).

## Pending (queue order in the JSON; 5 per day)
6 living-room/table-runner (35 x 110, oat linen) · 7 living-room/bowl (matte warm-white stoneware, 16-24 cm) · 8 bath/vanity-sconces + wall-sconce (IP44, flat, 10-16 x 18-26, hardwired CE) · 9 dining-room/table-runner (35 x 140) · 10 dining-room/centerpiece-vase (20-28 cm, narrow mouth) · 11 dining-room/candle-holders (charcoal pair) · 12 dining-room/floor-vase (50-65 cm) · 13 dining-room/dining-rug (230 x 220 flatweave) · 14 dining-room/kitchen-sconce (cone/bell, hardwired CE) · 15 dining-room/sink-set (dispenser, brush, tray) · 16 dining-room/utensil-crock · 17 dining-room/cutting-boards (oak pair) · 18 dining-room/canisters (3, oak lids) · 19 dining-room/herb-pots (2, with saucer) · 20 living-room/accent-sconces (travertine pair).

## Deviations from the brief (the binding documents win)
- **rug:** brief said 200 x 300; Bible: 200-240 x 290-340, and the feet rule needs a depth of 235-240 → asked for 240 x 300 (range in the remark).
- **pouf:** brief said 50 cm; Bible 1.3 (plan B): diameter 42-45, height 35-36 → asked for that.
- **bowl:** brief said 25-30 cm; slot and Bible: diameter 16-24, height 5-9 → asked for that.
- **table runner:** brief said 35 x 180; living Bible 30-38 x 100-125, dining 33-38 x 135-145 → two requests (110 and 140), same fabric family.
- **curtains:** living and dining are the same three products by the Bible (dining = one 280 panel), so one request covers both ("sold per panel"). The freed 20th request went to **living-room/accent-sconces** (gap queue #1: travertine pair, 1 candidate with a questionable wood bracket).
- **bath:** one request covers wall-sconce (B1, single) and vanity-sconces (B2, pair): same envelope and the same IP44 / CE rule. Remark: "need 3 per house".

## Reference images
Card images where a card exists (pouf: image 2, the cream variant; sink-set: soap-dispenser image 4 with the black pump; runners: images 2-3; vanity-sconces: image 2, lit). For three slots with no card at all, an image from a CJ `list` hit was used. Those products were **not opened** (no `product` call) and are not cards; they are leads only:
- **cutting-boards:** 2609280610571629100 "Large Cutting Board For Home Kitchen" ($3.51-7.12; reddish wood, handle). Also seen: 2610080901541614500 "Solid Wood Cutting Board, food-grade mineral oil" ($3.48) and 2105195528828334082 acacia paddle board.
- **canisters:** 2609181112041624900 "Three-piece Storage Jar Set With Lids" ($6.25; wooden lids, printed characters). Also seen: 2609191246181603300 "Ceramic Seasoning Jar Suit" ($12.78-22.43).
- **herb-pots:** 2102856040741003266 "White Ceramic Plant Pot With Saucer, 5 inch" ($50.99, probably a US-warehouse listing). Reference only.
- **utensil-crock:** the silver travertine tumbler card image, shape only (the remark says ceramic, not stone).
- The `list` queries ("cutting board", "sealed jar", "flower pot", "planter", "utensil") are cached for 7 days in `data/sources/cj/queries/`. "flower pot" and "utensil" match on single words and are mostly noise; "planter" and "sealed jar" are usable.

## How to poll
```bash
python3 scripts/sourcing/cj_source.py --by sourcing-support source-status \
  2610101514064490000 2610101514084500302 2610101514104501300 2610101514124481902 2610101514144482302
```
`GET /product/sourcing/queryList?sourceIds=...` (up to 100 ids, charged 50 points). `sourceStatus` 3 = succeeded (`cjProductId`, `cjVariantSku`: open the product through the pipeline, `cj_source.py product <pid> --slot ...`, and card it in the normal round), 5 = failed (`failReasonStr`). The website promises an answer within about 24 hours. The status is also cached in `data/sources/cj-sourcing/<id>.json` and noted in the registry entry.

## Next batches
```bash
python3 scripts/sourcing/cj_source.py --by sourcing-support source-batch \
  data/leads/cj/sourcing-requests-2026-10-10.json --approved "AC1 2026-10-10" --count 5
```
Run once a day (2026-10-11, 10-12, 10-13) until `summary.pending` is 0. The batch stops by itself at the daily limit and leaves the rest `pending`; a real failure is recorded under `failures`. `--dry-run` shows what would go out for free.

## Status log
### 2026-10-11 03:50 UTC (daily routine, run 2)
Poll of the first five (50 points): none succeeded yet (no `sourceStatus` 3, no `cjProductId`).

| slot | sourceId | sourceStatus | note |
| --- | --- | --- | --- |
| living-room/rug | 2610101514064490000 | 16 "Pending", failReason 1 | "We contacted many manufacturers for this product. Unfortunately, no exact same one found. And we have similar ones below for your reference." The similar items are not in the API response; they appear only in the CJ web UI (Sourcing list) or via the CJ agent chat. Treat as soft fail. |
| living-room/floor-lamp | 2610101514084500302 | 108 "Pending" | in progress |
| living-room/candle-holders | 2610101514104501300 | 106 "Pending" | in progress |
| living-room/pouf | 2610101514124481902 | 108 "Pending" | in progress |
| living-room/curtains | 2610101514144482302 | 16 "Pending", failReason 1 | same "no exact same one found" text as the rug; soft fail, similar items only in the web UI |

Batch 2 sent (5 requests, 2026-10-11T03:51Z): living-room/table-runner 2610110351004506402, living-room/bowl 2610110351024487100, bath/vanity-sconces 2610110351044487502, dining-room/table-runner 2610110351064487000, dining-room/centerpiece-vase 2610110351084496600. Queue: 10 created, 10 pending. Next poll should include all 10 ids.

### 2026-10-11 09:16 UTC (sourcing-support: request 10 resolved)
2026-10-11 ~07:11Z: 2610110351084496600 succeeded → cjProductId 2604130808271634100 → card already exists: `data/products/dining/centerpiece-vase/centerpiece-vase-cj-sandy-white-bead-band-25.json` (no new card, not rejected)
- CJ's "Sourcing Succeeded" (sourceStatus 116, CJSPU959878784, poll cached 09:14Z) points back at the **same pid we sent as the reference image** (image 1 of that card). `cjVariantSku` is null, so the open question from round 7 (style-number-to-photo map) is still unanswered. This is the circular answer the "Created" section warned about: next time the reference image should not be a CJ listing (use a non-CJ photo or a sketch).
- Pipeline: `cj_source.py product 2604130808271634100 --slot dining-room/centerpiece-vase` → SKIP (registry: card). This pid has no raw cache (carded in round 7 before the cache existed), so a freight call would be a fresh 10-point call for the figures the card already holds from the freight API on 2026-10-09 (inside the 14-day window): CJPacket Eub 12–50 d $56.07, Sensitive $86.08, To Door $90.72, against a 4.15 kg listed weight that looks inflated. Not re-called. 0 CJ points spent.
- Fit vs the slot (h 20–28, d 9–16, narrow mouth) and nordic-dining (preliminary, sourcing-support; `style_scores` stay with master-designer): **7/10**. Pass: matte sandy glaze, stoneware (CJ material field says "Glass", the description says ceramic), 25 × 12 cm with an 8 cm mouth, warm-white neutral (#ECE9E3), no charcoal, not the living default. Held back: carved swirl relief + bead band is busier than a plain Nordic vase; white is close to pure white (check against #F4F1EC); shipping ≈ 7× the $8.23 price; style-to-photo mapping unconfirmed.
- Registry: outcome note added to `cj:2604130808271634100` (status card unchanged) and to `cj-sourcing:2610110351084496600`. The card's notes carry the source line. Request 10 is closed; drop it from the next poll.

### 2026-10-11 09:30 UTC (manager): batch paused for rework
All 20 requests were created with a CJ listing image as `productImage` and no `productUrl`. Result so far: the vase request came back with the very pid we sent (circular), rug and curtains came back "no exact same one found" (CJ looked for the pictured listing, not the spec in the remark). Decision: `summary.batch_paused = true`. The 10 pending requests are reworked with `productUrl` pointing to a non-CJ item (AliExpress shortlist, fit ≥ 7, `data/leads/aliexpress/shortlist-2026-10-10.json`) and a remark that starts with "Source this item or an equivalent; NOT CJ pid <ref>". The daily routine keeps polling the 9 open ids and resumes `source-batch` when the flag is cleared.

### 2026-10-11 (rework)
sourcing-support, after the 09:30 pause. The 10 `pending` requests (n 11–20) were rewritten, and 3 new pending requests (n 21–23) were added for the slots that already came back circular or "no exact same one found". Nothing was sent (the daily routine sends), nothing committed, nothing added to `seen.json` (every item below is already there as `aliexpress:<id>`, "search shortlist, product page not opened"). No AliExpress product page was opened: only the shortlist JSON was used (rules ד.6).

**What changed in every reworked request**
- `productUrl` = the AliExpress item URL from `data/leads/aliexpress/shortlist-2026-10-10.json` (best `fit_guess` for the slot; `< 7` is flagged below).
- `productImage` stays the CJ image, as a style reference only (the API requires an image).
- `remark` starts with `Source the linked AliExpress item or an equivalent. NOT CJ pid <ref pid>, we already have it.` and ends with `Ship to Israel.` The ref pid is the CJ product behind the image (`supplier.product_url` of the ref card, or the `CJ list hit` pid).
- **CJ allows 200 characters per field**, and that prefix with a 19-digit pid is already 104, so the spec text in between was compressed to about 80 characters (dimensions, materials and colours stay in `productName`). The full previous remark is kept as `remark_v1`; a changed name keeps `productName_v1`.
- Slots with no external reference (dining-rug, canisters): `productUrl` stays null, and the prefix reads `Source to this spec (no external reference). NOT CJ pid <ref>, we already have it.` ("linked item" would be misleading with no link).
- New fields per request: `ae_item_id`, `ae_fit_guess`, `ae_price_usd`, `ae_title`, `not_cj_pid`, `reworked_at`, `rework_note`; the 3 new requests also carry `supersedes` (the old n / cjSourcingId / status).
- `summary`: `batch_paused` false, `pending` 13, `planned` 23, `rework_at` 2026-10-11 (`created` 9; the resolved vase request stays `resolved`).

| # | slot | AliExpress item_id | fit_guess | NOT CJ pid | remark summary |
| --- | --- | --- | --- | --- | --- |
| 11 | dining-room/candle-holders | 3256811847480845 | 7 | 2412060248371626300 | pair, matte black iron stand for pillar candles ($2.43): matte black/charcoal, 7 cm pillar, max 12 cm high; no glass/shine |
| 12 | dining-room/floor-vase | 3256813144317414 | 7 | 2411131023531607200 | tall white minimalist floor vase ($37.75, no sales yet; alt 3256808800994217, 105 sold, probably under 50 cm): matte/unglazed stoneware, charcoal OK; no gloss, glass, rattan |
| 13 | dining-room/dining-rug | — | — | 2408230550421602300 | **no external reference** (the shortlist has only living-room rugs): flat weave, light tone, tone-on-tone; no shag, pattern, saturated colour |
| 14 | dining-room/kitchen-sconce | 3256812137993644 | **8** | 2606170257551623500 | beige linen cone on black bracket ($37.45) = Bible variant 2: hardwired, no visible cable, no replica; also a matte ceramic cone version. Name now says "linen or matte ceramic shade" |
| 15 | dining-room/sink-set | 3256812066933865 | 6 (<7) | 2412110118331626300 | ceramic dispenser + steel tray ($5.61), no brush: add a light-wood dish brush and a matte tray; no visible plastic, no logo; one set. Name: "dispenser (as linked)" |
| 16 | dining-room/utensil-crock | 3256811648868911 | 6 (<7) | 2604200352011636600 | French-style ceramic utensil holder ($25.04; tone and size not in title): matte stoneware, not stone (photo is shape only); plain, no text or handles |
| 17 | dining-room/cutting-boards | 3256808220072680 | 5 (<7) | 2609280610571629100 | board with handle, 352 sold ($8.90; wood species not in title): solid oak/ash, matte oil, light tone, not dark as the photo; no bamboo/epoxy/logo. Name: "Oak or ash ... with handle or rounded rectangle" |
| 18 | dining-room/canisters | — | — | 2609181112041624900 | **no external reference**: closed jars, matte glaze, oak/ash lids, 3 glaze tones; no text, glass, glossy bamboo |
| 19 | dining-room/herb-pots | 3256807989828860 | 5 (<7) | 2102856040741003266 | round ceramic planter with bamboo tray ($1.09, 27 sold; size/tone not in title): matte glaze, saucer, drainage hole; no orange terracotta, gloss, plastic. Name: "saucer or tray" |
| 20 | living-room/accent-sconces | 3256807415537790 | **8** | 2609291256041602700 | travertine sconce, hardwired, E27, 333 sold ($49.15): real travertine, up/down wash, no visible cable, no wood bracket; set of 2; CE |
| 21 (new, replaces 1: 2610101514064490000 "no exact same one") | living-room/rug | 3256812098237494 | 5 (<7) | 2408230550421602300 | woven sisal, minimalist ($128.33; size not in title; alt 3256812175255972 handwoven cotton with tassels): wool/jute/cotton/sisal flatweave, light tone; no medallion, shag, viscose. Name: 240 x 300, "wool, jute-wool, cotton or sisal" |
| 22 (new, replaces 5: 2610101514144482302 "no exact same one") | living-room/curtains | 3256808664091154 | 7 | 2411080726491625400 | cotton-linen texture sheer, custom size, 700+ sold ($5.35; same family as 3256811998576912): linen/cotton-linen slub, 140 x 280, oat; no blackout, satin, print, grommets. Name: "Sheer cotton-linen ... custom size" |
| 23 (new, replaces 10: 2610110351084496600 circular) | dining-room/centerpiece-vase | 3256804234725093 | 7 | 2604130808271634100 | Nordic matte ceramic vase for pampas, 19 sold, free shipping ($22.23; alt 2255800578472233 white matte "centerpiece"): **a different model than pid 2604130808271634100: smooth matte stoneware, no bead band or relief, narrow mouth.** Name: "smooth body", 20-28 cm |

Link with fit ≥ 7: 7 slots (candle-holders 7, floor-vase 7, kitchen-sconce 8, accent-sconces 8, curtains 7, centerpiece-vase 7, and rug/curtains family). Below 7, best available anyway: sink-set 6, utensil-crock 6, cutting-boards 5, herb-pots 5, living rug 5. No link: dining-rug, canisters.

**Dry run** (`python3 scripts/sourcing/cj_source.py --dry-run --by sourcing-support source-batch data/leads/cj/sourcing-requests-2026-10-10.json --approved "AC1 2026-10-10" --count 5`): `pending` 13, would send n 11–15 (candle-holders, floor-vase, dining-rug, kitchen-sconce, sink-set) with the new `productUrl` and `remark`, all fields ≤ 200 chars, nothing sent, 0 points. Budget: `sourcing_create` already 5 calls today (the 03:51 batch), so the routine's first real batch of the reworked queue is 2026-10-12; 3 days at 5 per day for 13. Two notes on the pipeline: `--dry-run` is a global flag and goes **before** `source-batch` (after it, argparse rejects it); and `source-batch --dry-run` now prints the exact bodies it would send (slot, productName, productImage, productUrl, price, remark) and runs the 200-char check, instead of slot names only (`scripts/sourcing/cj_source.py`, small change in `do_source_batch`).

**Poll list** stays the 9 open ids (n 1–9); n 10 is closed. When n 21–23 are created, the old ids 2610101514064490000 and 2610101514144482302 can be dropped from the poll.

## 2026-10-12 (שגרה יומית)

- **סטטוס:** 3 בקשות נסגרו.
  - ראנר פינת האוכל: CJ ענו עם מוצר שכבר בכרטיס (2512200838021632400), סומן "circular".
  - שטיח הסלון: Sourcing Failed, ‏failReason 8, "We contacted many manufacturers, unfortunately, we were unable to find it".
  - וילונות הסלון: אותה תשובה.
  - 6 עדיין Pending: מנורת רגל, פמוטים, פוף, ראנר הסלון, קערה ומנורות המראה.
- **נשלחו 5 חדשות:** פמוטים לנר עמוד בפחם, אגרטל רצפה, שטיח אוכל, מנורת קיר במטבח, סט כיור. נותרו 8 בתור.

## 2026-10-13 (שגרה יומית)

- **סטטוס:** 8 בקשות נסגרו.
  - מנורות המראה באמבטיה: CJ מצאו מוצר (1674979039716581376), אבל זו אותה מנורה מחורצת משרף שכבר יש לנו, ויקרה יותר ($16.45 במקום $7.30). היא נפסלה, ולא נכתב לה כרטיס, כי:
    - גובהה 16.5 ס"מ, מתחת למינימום של 18;
    - הגוף משרף ולא מאופל או קרמיקה;
    - יש בה נורות G9 חשופות;
    - לא מוצהרים לה IP ולא CE.
    הצעה לבקשה חדשה: LED מובנה, זכוכית מאופלת או קרמיקה, IP44 בדף המפרט, וגובה 18 ס"מ לפחות.
  - שלוש תשובות שכבר יש להן כרטיס, ולכן סומנו "circular": הקערה בסלון (2505301100271623200), אגרטל הרצפה בפינת האוכל (2411131023531607200) וסט הכיור (2412110118331626300).
  - נכשלו:
    - מנורת רגל: failReason 18, "Product size is too large".
    - פמוטים בסלון: failReason 100, "unable to open the URL ... or find the images".
    - פוף, ראנר בסלון ושטיח לפינת האוכל: failReason 8, "unable to find it".
  - 2 עדיין Pending: פמוטים לפינת האוכל ומנורת קיר במטבח.
- **נשלחו 5 חדשות:** כלי לכלי בישול, קרשי חיתוך, צנצנות אחסון, עציצי תבלינים ומנורות קיר מטרוורטין לסלון. נותרו 3 בתור.

## 2026-10-14 (שגרה יומית)

- **סטטוס:** 5 בקשות נסגרו.
  - כלי לכלי בישול ומנורות הטרוורטין: CJ החזירו מוצרים שכבר יש להם כרטיס (circular).
  - קרשי חיתוך ועציצי תבלינים: CJ החזירו בדיוק את המוצר שהבקשה ביקשה לא להחזיר. אין מוצר חדש.
  - צנצנות: failReason 8, "unable to find it".
  - 2 עדיין Pending: פמוטים לפינת האוכל ומנורת קיר במטבח.
- **נשלחו 3 אחרונות:** שטיח בסלון 240×300, וילון שקוף 140×280 ואגרטל מרכזי חלק. התור ריק. כשכל הסטטוסים יהיו סופיים, השגרה נסגרת.
