# CJ round 5 (2026-10-06): magazine-holder, new envelope (Bible 1.4.2)

Spec: `data/leads/cj/search-specs-2026-10-04.md` section 4. W 26–32 (33–34 only if D ≤20), D 18–22, H 36–48 (prefer 40–45), floor-standing, open or low front, charcoal element required, oak/ash, matte black metal, charcoal felt or leather. No rattan, sea grass, straw, chrome, gold, plastic, acrylic or gloss.

**Result: 0 new cards. No CJ product fits the envelope.** Under the hard filter (exact dimensions published, product really in the envelope), no card was written. Near-misses do not get a card. The table below ranks the closest ones.

Budget used: 9 `search` calls (listV2), 25 `list` calls, 18 `product` calls, 0 `freight` calls. Freight was not checked because no item made the shortlist. Two 429 errors came back and were retried.

## Re-check of existing cards and round-4 near-misses (exact dimensions, new envelope)
| Item | W × D × H (cm) | Verdict |
| --- | --- | --- |
| magazine-holder-cj-arch-iron-cane (1590955645040340992) | 35 × 16.5 × 45 | **Fail.** W35 is over 34, D16.5 is under 18, and the sling has a cane look (rattan is forbidden) |
| magazine-holder-cj-gunmetal-leather-strap (1781890308909830144) | 35 × 19 × 27.5 | **Fail.** W35 and H27.5 are out, and the black chrome has a sheen |
| magazine-holder-cj-felt-snap-bucket (2503220827461603400) | 30 × 30 × 42 | **Fail.** D30. The spec also excludes the bucket |
| magazine-holder-cj-felt-log-basket (2602110556411615100) | 45 × 32 × 40 | **Fail.** The spec excludes it |
| 1990467549195329537 black steel rack | 35 × 15 × 45 | **Fail.** W and D are out, and it has no IL shipping from CN |
| 1990443846197223425 wood X rack | 29.5 × 29.5 × 26.5 | **Fail.** D and H are out |
| 1592868324936003584 leather sling | 40 × 30 × 50 | **Fail.** Size is out, and the frame is gold |
| 1522192177538019328 felt basket | 28 × 28 × 18 | **Fail.** H18 |
| 2078307991622148097 felt tote | 39 × 20 × 26 (+17 handles) | **Fail.** W is out |

## Ranked near-misses from this round (no card)
| # | CJ pid | Product | $ | listedNum | W × D × H | Charcoal | SPEC CHECK |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1385563700525666304 | Black perforated metal sling rack ("Removable Storage Rack For Portable Magazines"), black or white | 7.31 | 7 | **not published** (package 33.5 × 30.5 × 33) | yes (black frame and black perforated sheet) | Best typology: open U-sling, matte black, magazines visible. Dimensions are unknown, and from the photos it looks about 30 cm high, so it likely fails H ≥36. Before any card, ask CJ for the exact W/D/H |
| 2 | 2608300209161600400 | Walnut-veneer X magazine rack with brass studs | 25.56 | 0 | 32 × 23 × 34 | no | Fail: D23 > 22 and H34 < 36. No charcoal, walnut instead of oak, brass dots |
| 3 | 2607090700331624400 | Black steel U log rack with a curved sheet base | 9.45 | 0 | 44 × 37 × 38 (diagram) | yes | Fail: W44 and D37. Right look (black U-frame, open front) at the wrong size |
| 4 | 2504160751161611200 | Felt basket, dark grey or black, cognac handles | 1.65 | 6 | 37 × 32 × 27 | yes | Fail: W, D and H are all out. It is a 12-bottle wine caddy with dividers |
| 5 | 1604115936796225536 | Black solid-wood side table with a magazine slot | 53.13 | 26 | 33 × 47 × 40 | yes | Fail: it is a side table (D47). It also looks like a known designer table (replica risk) |

## Rejected on sight
- 2508090107511626200: wire "Curve"-style rack, 47 × 36 × 35. It is a copy of a known designer rack (replica), it is too wide, and it comes in silver, gold, red or black.
- 2509210258321621600: tall tiered rack, 30 × 12 × 70.
- 1549277345528426496: tabletop wood ornament, 27 × 23 × 1.5 sheet.
- 2105781238020227073 and 2105782034606637058: desktop size (13" and 11" long).
- 1519570625164226560: rose-gold wire basket.
- 2505160603251612900: gold, 10 cm deep.
- 2096675638481813506: ornate scroll log bin, 42 × 40 × 36.
- 1516677323976880128, 1480422536985579520, 1555388782080438272, 1745641678905544704, 1762809382422716416 and 2410300529461619700: acrylic.
- 1489780042518106112: stainless steel, 40 × 45.
- 1392426429546893312, 1519611453999951872 and 1394889942294990848: rattan.
- 2409040753081613900: straw.
- 1541352103275409408: wall-hung, walnut and brass.
- 2097284097530175490 (37 × 20 × 55), 2003424583516532737 and 2003348306863738881: side tables.
- 1990695808486920194 (133 high) and the brochure display stands: far too large.
- 2609170457011614500: kids' bookshelf, 79 × 33.

## Search-tool findings (for the next round)
- `search` (listV2) is useless for this category. "magazine rack floor wood", "magazine holder felt", "newspaper rack metal wood", "iron wire magazine rack", "wooden magazine rack", "leather magazine basket" and "felt storage basket with leather handles" all return car mats, phone holders, curling irons or leather jackets.
- `list` treats several words as OR and returns newest-first noise. Only single rare words work. I scanned every result for "magazine" (144), "newspaper" (122), "magazines" (12) and "newspapers" (6), plus page 1 of "firewood" (175), "trapezoidal", "wrought" and "vinyl".
- `list --category` does filter (for "felt": 1064 results without a category, 316 with Home Office Storage). The Home Office Storage id is `87CF251F-8D11-4DE0-A154-9694D9858EB3`. It is not yet in `docs/suppliers/cj-categories.md`. Most CJ magazine racks sit there. Single words inside it ("felt", "leather", "floor") return mostly unrelated newest items.

## Conclusion and recommendation
CJ's own catalogue has no floor-standing magazine holder with a charcoal element in 26–34 × 18–22 × 36–48. Paths forward (they need a decision from the art director or the user):
1. **CJ Sourcing request.** Ask CJ to source a specific product to spec. The AliExpress leads in `data/leads/living-room/magazine-holder.json` give the typology, for example "nordic iron trapezoidal floor rack" 1005002561280098, "iron wire basket books newspapers" 1005003283696416 and "plated wire faux leather standing" 1005005698589090. CJ quotes the price and the dimensions, and then the product can be carded. AliExpress itself cannot be read directly (reCAPTCHA, see `docs/project-summary.md`).
2. **Ask CJ for the dimensions of 1385563700525666304** (black perforated sling, $7.31). If its height is ≥36, it is the strongest Nordic candidate, with the right typology.
3. If neither works, master-designer reconsiders the envelope (for example H ≥34 or D ≤23).
