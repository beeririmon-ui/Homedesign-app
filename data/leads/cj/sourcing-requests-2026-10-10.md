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
