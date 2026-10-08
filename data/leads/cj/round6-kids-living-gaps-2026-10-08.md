# CJ round 6 (2026-10-08): kids K2 (boy/girl) + living-room gaps

Agent (c) of three parallel sourcing agents. User request: "חפש מוצרים מתאימים להכל, כמה דוגמאות לכל מוצר".
Slots: `docs/proposals/house-framing.json` → `round_2.rooms.kids` (15 per room) and living-room gaps (sofa-cover, magazine-holder, wall-decor, framed-art, accent-sconces, pendant with CE).
New cards: `data/products/kids/<slot>/` (12 cards). Reused existing cards are referenced, not copied. No card was overwritten. Nothing committed.

**API used:** 45/45 search+list, 34/45 product+freight (11 product/freight calls left unused for the other agents). No quota or 429 errors.
Prices are CJ cost in USD. "IL ship" = cheapest / reasonable fast option, with days. "CE n/v" = CE not stated in the listing (not verified).

## Kids K2 (boy and girl)

| Slot | Candidate (card) | $ | IL ship (eco / fast) | Size (cm) | Verdict |
| --- | --- | --- | --- | --- | --- |
| **pendant** (d ≤28, shade h ≤25, hardwired) | kids/pendant/pendant-cj-fabric-dome-ash-cap-25 (2508280237031614500, vid …615200) | 14.10 | 29.57 Eub 12–50 d / 89.46 Sensitive 22–27 d | Ø25 × 23, h20 | **Best fit by size.** 220V, CE n/v. Open bottom (bulb may show), walnut-tone cap and brown hem binding |
| | reuse: pendant/pendant-cj-pleated-pumpkin-lantern-40 → vid 2601130233171625100 ("28cm" egg) | 38.97 | 42.19 Eub / 133.39 To Door 11–18 d | Ø28, h n/v (egg, likely >25) | Shade and bridge are right (closed pleated lantern). 111–240V, CE n/v. Height probably fails |
| | reuse: pendant/pendant-cj-silk-pumpkin-lantern → vid 2507161004081614500 (30 cm) | 24.88 | 21.62 Eub / 32.66 Liquid Line 9–23 d | Ø30, flat | +2 cm over Ø28. CE n/v. Small bottom opening |
| **wall-sconce** (swing arm 30–45, hardwired, no cable) | kids/wall-sconce/wall-sconce-cj-black-swing-arm-wood-shade (2412090835251617400) | 10.78 | 86.78 Sensitive 22–27 d / 91.42 To Door (no Eub) | arm 23, shade Ø18 (A) / Ø20 (B) | **Partial.** Only hardwired swing arm found. Fails: shade is wood/iron (not fabric), bulb visible, arm 23 < 30, CE n/v, freight 8× the price |
| | reuse: wall-sconce/wall-sconce-cj-black-swing-arm-fabric (2412050322241626300) | 13.76 | 105.02 / 109.66 | n/v | Right look (fabric shade, folding arm), but plug-in → fails the kids hardwired rule |
| | reuse: wall-sconce/wall-sconce-cj-black-swan-arm-pleated-linen (rejected for living) | 27.78 | 19.49 Eub / 60.03 To Door | proj 26, h17 | Hardwired, linen shade. Fails: projection 26, bronze sheen |
| **bedding** | kids/bedding/bedding-cj-muslin-cotton-duvet-dune (2604010316331613400) | 14.93 | 16.59 Eub / 24.35 Liquid Line | 173 × 229 (cover only) | Cotton muslin, warm cream. Calm default. Only 3 rendered-looking photos |
| | kids/bedding/bedding-cj-washed-polyester-set-milk-tea (2503020244061618700) | 9.78 | 24.15 Eub / 36.82 Liquid Line | duvet 150 × 200 + sheet + 2 pillowcases | Oat-sand. Polyester despite the "washed cotton" title. Good consistent studio photos |
| | kids/bedding/bedding-cj-cream-ruffle-rosebud-set (2504170314541614200) — girl | 16.35 | 31.85 Eub / 47.98 Sensitive | "1.5 m" set; duvet size n/v | Cream with scalloped ruffle and rosebuds = the "a bit girly" brief. Lace and embroidery are busier than Nordic. Likely oversized for a single bed |
| **bedspread** (quilt folded over the foot third) | kids/bedspread/bedspread-cj-six-layer-gauze-quilt (2603130535281638600) | 8.46 | 12.80 Eub / 18.12 Liquid Line | 150 × 200 | **Strong.** 6-layer cotton gauze. Matcha (boy, borderline sage H55), Khaki (oat), White. Excellent photos |
| | kids/bedspread/bedspread-cj-muslin-blanket-beige-150x200 (2504160702281620100) | 11.61 | 12.68 Eub / 17.91 Liquid Line | 150 × 200 | 100% cotton gauze, oat. listedNum 37. Pink is salmon (out) |
| **cushions** boy (sage + neutrals) | reuse: cushions/cushions-cj-wide-wale-corduroy, -corduroy-patchwork, -bubble-chenille-bean-green, -washed-cotton-frayed (silt green), -linen-look-ivory, -boucle-teddy | 1.72–3.61 | 6.78–14.79 | 45/50 | Covered by existing sage and warm-white cards |
| **cushions** girl (dusty rose ≤2 slots + neutrals) | kids/cushions/cushions-cj-dusty-pink-corduroy-patchwork-45 (1642811981793071104) | 11.08 | 4.79 Eub / 10.04 To Door | 45 × 45 | Dusty rose (~H8 S23 L63, hue a touch pink). Sister of the sage patchwork card. Pair with ivory and boucle for 2+1. The washed-cotton listing (2411060912291619600) has no dusty rose (Apricot is caramel, Rose Red is hot pink) |
| **framed-prints** (pair 30×40) | kids/framed-prints/framed-prints-cj-charcoal-line-black-frame-35x45 (2411231150051604700) — boy | 21.23 | 23.90 Eub / 36.40 Liquid Line | 35 × 45 | Charcoal brush line, wide warm-white mat, black solid-wood frame. listedNum 254. Abstract, not a kid motif. 5 cm over the format. Copy check needed |
| | kids/framed-prints/framed-prints-cj-flower-cutout-set-30x40 (2511220828321604600) — girl | 12.74 (set of 3) | 8.14 Eub / 31.09 Liquid Line | 30 × 40 | Exact format, soft flower shapes. Ochre/terracotta push saturation. Wood-look PS frame |
| **toy-basket** (Ø35 h35) | reuse: basket/basket-cj-jute-rope-cylinder | 5.17 | 19.11 Eub / 32.30 Sensitive | 35 × 39 | Good (rope cylinder) |
| | reuse: basket/basket-cj-seagrass-belly | 8.00 | 12.75 Eub (fast $158) | 35 × 37 | Good. Seagrass is allowed in the basket slot (no other fibre item in the kids room) |
| | reuse: basket/basket-cj-cotton-rope-white | 12.86 | 14.44 Eub / 20.59 Sensitive | 40 × 45 | A bit big. Kids-style photos |
| **toy-cars** (set of 3 wooden) | kids/toy-cars/toy-cars-cj-beech-peg-bus (2510210529201638800) | 3.07 | 5.87 Eub / 6.70 Liquid Line | 14 × 2.6 × 7.5 | Natural beech bus with peg people. One vehicle, not 3. **No CE/EN71 stated**; pegs are small parts |
| **skateboard** | kids/skateboard/skateboard-cj-blank-maple-43 (2507110232191607000) | 1.93 | 17.60 Eub / 28.01 Liquid Line | 43 × 13 | Plain maple deck. **Red wheels** (slot wants charcoal/oat). Mini size. No safety mark |
| **roman-blind** | — | | | | **Gap.** CJ has none ("roman" in Curtains = 1 embroidered rod screen; "lifting" = 0; listV2 returns sandals) |
| **rug** 140×200 | — | | | | **Gap.** F0443A4D… "Scandinavian linen cotton rug" is only 60×90 and printed. Floor Mats category returns bath mats. MAVAL rugs are a US brand from a US warehouse |
| **bookshelf** (2 ledges, 80 cm) | — | | | | **Gap.** Near-misses: 2102505023551066113 (2 × 40 cm wavy pine ledges, $50.99, Canadian third-party seller, IL freight not checked); 1758026415229898752 (white ledge with animal cut-outs) |
| **desk-chair** | — | | | | **Gap.** The Furniture category is EU-warehouse beds. Nothing child-scale in wood |
| **desk-organizer** | — | | | | **Gap.** "pencil" in Home Office Storage = pencil cases only |
| **soft-toy** (bear / bunny) | — | | | | **Gap.** listV2 returns pet toys. "teddy" = clothing |
| **doll** | — | | | | **Gap.** All Waldorf dolls rejected: their photos carry individual makers' branding (e.g. "Zhenya Elizarova", "Stepina … with love"), so they are copies of artisan/Etsy dolls |
| **doll-pram** | — | | | | **Gap.** "pram" = baby and pet strollers only |

## Living-room gaps (no new card in any of the six)

| Slot | What was checked | Result |
| --- | --- | --- |
| sofa-cover (linen/cotton, non-stretch, 220×92×78, track arms) | `list slipcover` (98, newest since 10-04) | Only sofa towels or elastic covers. Closest new item: 2605170628371631900 (cream chenille, per-cushion pieces, "one pull, one hook" elastic). Same type as the existing best card (sofa-cover-cj-linen-feel-chenille-slipcover). **Gap stands** |
| magazine-holder | Not re-searched. Round 5 scanned every "magazine/newspaper" listing (2026-10-06) | **Gap stands.** Recommendation from round 5: a CJ Sourcing request, or ask CJ for the dimensions of 1385563700525666304 |
| wall-decor ≤45×45 (ceramic/plaster/wood relief, round oak mirror) | `list plaster` (550, medical and aroma items), `list relief` (2437, noise), `list oak` (furniture) | **Gap.** Only the boho sunburst mirror already in the pool (pool-cj-wood-sunburst-mirror-43). Note: the Bible's wall-decor rule still forbids mirrors and requires natural fibre or wood. A ceramic, plaster or mirror item needs a Bible change |
| framed-art with charcoal (pair 70×100, triptych 50×70, single 100×150) | `list framed` in Decor Paintings (113 = US print-on-demand 8×8 metal prints) | **Gap.** The black-frame charcoal print above (45×55 max) is too small for the 145–165 envelope. Existing card: framed-art-cj-morandi-triptych-sage |
| accent-sconces (travertine, hardwired, CE + 220–240V) | `list travertine` (42, unchanged), `list cave` in Wall Lamps (12) | **Gap: no CE on any listing.** New near-miss 2508280308441627100: 10 cm travertine disc (4 cm thick) on a 23 cm wood bar, 220V, built-in LED 9W, pull chain, $14.18, projection ~17. Fails H 12–18 and depth 7–12, and the wood bar is the main body. Not carded. Other new items have glass globes or wooden brackets |
| pendant with CE stated | Fabric pendants in Ceiling Lights / Chandeliers (`list fabric`) + 3 product checks | **Gap: no listing states CE.** 2508280237031614500 Large (40 × 34 × h28, 220V, $17.58, vid …615000) fits the living-room size, but CE n/v, it has an open bottom and a walnut-tone cap. 2409290953571606200 (petal shape, no voltage), 2608271035431607800 (iron frame, no voltage, 2.5–4.5 kg) and 2511241223061607100 (silk capsule, 110–240V, h40) all fail |

## Rejected on sight (do not re-check)
- Replicas: 2411260709231626700, 2411250548011615200 (Nelson Bubble look-alikes); 2606230304521623300 (Serge Mouille look-alike); 2507291338191625400 ("Bauhaus" long arm).
- Brass or glass sconces: 2509171004441605700, 2412050521431624500, 2412050400521608000, 2412041003391612900.
- Bedding: 1961693457541279746 / 1961691019199426561 (Serta, a US brand); 2104…/2103… "bedspread" sets (US patterned quilts, Zen Weave brand).
- Prints: 2411130841401628600 (B&W winter trees, canvas core only, frameless).

## Search-tool findings (for the next round)
- listV2 `search` is useless for toys, rugs, shelves, blinds, chairs and dolls: it matches loosely and returns pets, clothes and car parts.
- `list` with one rare word is the only reliable tool. Words that worked: "muslin" (29, good textiles), "waldorf" (12), "kilim" (2), "ledge" (12), "beech" (388, found the toy bus), "skateboard" (396, one blank deck), "cave" in Wall Lamps.
- Category filters are narrow and mis-assigned. Toys sit in "Home Office Storage" and furniture in "Bedding Sets". Floor Mats + "cotton" = 5 bath mats.
- Kids items (toys, child furniture, roman blinds, kids' rugs) are effectively missing from the CJ API catalogue. The remaining kids gaps need a decision from master-designer or the user: a CJ Sourcing request, or an approved non-CJ dropship source (AliExpress is blocked by reCAPTCHA for agents).

## Open questions for master-designer / user
1. Kids lighting: no CE on any CJ pendant or sconce. Ask the suppliers for CE certificates, or accept "CE on request" as a pre-order step?
2. Kids wall-sconce: accept a wood or metal shade (the closest hardwired swing arm), or keep the fabric shade and allow a plug-in in the kids room (the brief says hardwired)?
3. Toys (toy-cars, doll): no listing states EN71/CE. Selling toys requires test reports from the supplier.
4. Girl bedding: is the romantic ruffle-and-rosebud set acceptable, or plain cream muslin + the dusty-rose cushion only?
