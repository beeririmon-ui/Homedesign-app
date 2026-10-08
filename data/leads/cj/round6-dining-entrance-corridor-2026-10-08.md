# CJ round 6 (2026-10-08): kitchen + dining (D1/D2), entrance (H0), corridor (C0)

> sourcing-agent. User request: "חפש מוצרים מתאימים להכל, כמה דוגמאות לכל מוצר".
> Slots from: `docs/proposals/house-framing.json` round_2 (kitchen-dining D1 8 + D2 15, `lighting_plan_S12`), `docs/proposals/house-framing.md` 8.4-8.5, `docs/house-plan.json` slots_first_list (hall, corridor), `data/slots/dining-room.json`, `data/leads/cj/search-specs-dining-2026-10-06.md`. Palette/materials: `docs/design-bible/nordic.md` 1.5 + `nordic-dining.md`. Electrical: `docs/brand-brief.md`.
> Hall and corridor slots have no written envelopes yet. The SPEC CHECK lines use envelopes derived from the plan geometry: console X 2.55-3.35, bench wall Y 6.35-7.98, corridor 1.40 wide with a 2.70 dropped ceiling, and a gallery of 3 prints 40 wide with the top at 1.70 or lower. master-designer should confirm them.
> All new cards have `status: candidate` (one is `rejected`), no style_scores, and `usage_rights: unclear`. **CE is not verified on any light.** Nothing is committed.

## API use (shared daily quota)
- **search/list: 43 of 45** (14 `search`, 29 `list`, including 1 `getCategory` and 2 calls that ended in a QPS 429 error).
- **product/freight: 43 of 45** (29 `product`, 14 `freight`).
- 2 + 2 calls remain. No quota error was hit. QPS-429 errors came back several times because three agents ran in parallel, and they were retried after a few seconds.

## Search-tool findings (to save calls next time)
- `list "<one word>" --category <id>` works as AND (word in the name, inside the category). This is the only reliable filter.
- `getCategory` (1 call) returns the tree. New useful ids: Dinnerware `0F4CFA22-8B97-4016-94A6-18066B9BD05C`, Drinkware `CF330457-0E5B-4FAF-9BAE-7D2C247BD8DE`, Cooking Tools `E448A723-43DC-4BD8-A9AD-2FB9699338B4`, Kitchen Storage `56845C3D-4D9E-4729-B5D4-6D7DE310C031`, Storage Bottles & Jars `C1394E10-1EDF-4107-AA93-F142B44C3136`, Bathroom Storage `B62EE40F-7650-4715-A7A5-BA227540593C`, Towels `331F43CE-CA1D-45F2-BE2A-8AE62EC10251`, Night Lights `538CB48E-B7A0-46F7-B5A2-BB8183247B23` (table lamps live here and under Pendant Lights).
- The `list` `remark` field holds only description images, not text. Dimensions need a `product` call.
- Thumbnails (`productImage` / `bigImage`) download freely from the CDN. A contact sheet before each `product` call saved many calls.
- Weak on CJ, with nothing Nordic in name-filtered results: rugs and runners (the Floor Mats category is tiny; the rest is printed/boho or US-warehouse "MAVAL" rugs), oak cutting boards, wall hooks, trays, canisters, soap dispensers, herb pots, salt/pepper sets, paper-towel holders, tea towels, charcoal candle holders and floor vases.
- **Bulky lamps:** only CJPacket Eub (12-50 d, about $30-55) is reasonable. Every "fast" line costs $200-300 (volumetric weight). This repeats the pattern of the earlier pendant cards.

## Kitchen + dining (D1 / D2)
Legend: ✓ passes the envelope; ~ passes with a flag; ✗ fails a hard point (kept for the record).

| Slot | Candidates (card) | Price | IL shipping eco / fast | Dims (cm) | Verdict |
| --- | --- | --- | --- | --- | --- |
| **dining-pendant** (D45-55, H25-35, cable ≥130, hidden bulb) | NEW `dining/dining-pendant/dining-pendant-cj-black-ring-cloth-lantern-50` | $51.79 | Eub $29.57 / none under $290 | D50 H36, wire 120 | ~ best new: closed cloth lantern, listedNum 50, 111-240V; H +1, wire 120 < 130, CE ? |
| | existing `pendant/pendant-cj-silk-pumpkin-lantern` (50 cm vid 2507161004081617900) | $38.97 | Eub $35.51 / none under $337 | D50 | ~ "≤36V" text, open bottom ring |
| | existing `pendant/pendant-cj-tiered-fabric-drum` | $43.28 | Eub $54.80 / none | D50 | ~ open bottom, 4-tier silhouette |
| table-runner (33-38 × 135-145) | existing `pool/table-runner/pool-cj-woven-cotton-runner-fringe`, **33×140 vid 2506020359111606100** | $2.72 | (183 vid) Eub $6.74 / To Door $13.11 | 33×140 | ~ only runner of the right length; fringe length not stated (≤5 required) |
| centerpiece-vase (H20-28, D9-16, narrow mouth) | existing `vase/vase-cj-white-textured-jar` (Medium) | $6.60 | Eub $33.24 / To Door $54.80 | D16 H28, mouth 10 | ~ fits at the limits; the relief texture read as boho in the living ranking |
| candle-holders (charcoal pair, holder 1-12) | existing `pool/candle-holders/pool-cj-carbonized-wood-pedestal-candlestick` | $8.45 | Sensitive $27.94 / To Door $32.57 | 11×11×22 | ✗ holder 22 tall (limit 12) |
| curtains (single panel 130-150 × 278-282) | existing `curtains/curtains-cj-japanese-linen-half-shade` | $16.58 | Eub $26.67 / ... | 150×260 | ✗ only a 260 drop on the listing |
| floor-vase (H50-65, D25-32) | existing `pool/vase/pool-cj-wabi-sabi-floor-vase-white` | $26.20 | Eub $59.72 / ... | D28 H45 | ✗ too short |
| bench-pad (bench 140 × 35) | NEW `dining/bench-pad/bench-pad-cj-tufted-long-cushion-khaki-120` | $6.30 | not quoted | 120×50×8 | ✗ depth 50, 8 thick, tufted polyester (record only) |
| dining-rug | none | | | | gap |
| **framed-art** (30×40 / 35×45, charcoal) | NEW `dining/framed-art/framed-art-cj-swinging-line-black-frame-mat-35x45` | $21.23 | Eub $23.90 / To Door $40.12 | 35×45 | ✓ black frame + cream mat, listedNum 254; plexiglass glare to check |
| | NEW `dining/framed-art/framed-art-cj-taupe-block-black-line-30x40` | $10.95 | Eub $29.20 / To Door $48.44 | 30×40 | ~ canvas, no glass; no mat |
| open-shelf-ceramics (jug 18-26 + low 10-15) | NEW `dining/open-shelf-ceramics/open-shelf-ceramics-cj-morandi-matte-bottle-set` (M grey) | $6.85 | Eub $9.85 / To Door $42.09 | D10 H15.5 | ~ low item only; listing says "glass ceramic" (confirm not glass); no jug |
| tableware-set (2×26-28, 2×19-22, 2×14-16 bowls) | NEW `dining/tableware-set/tableware-set-cj-grey-sand-matte-plate` (11 in) | $7.93 | Eub $15.58 / To Door $27.02 | D28 | ~ dinner plate only, no side plate or bowl in the line |
| | NEW `dining/tableware-set/tableware-set-cj-speckled-oat-stoneware-bowl-13` (2 pcs) | $7.37 | Eub $10.40 / To Door $23.60 | D13.6 H6 | ~ bowls only, 0.4 under 14 |
| mug-set | NEW `dining/mug-set/mug-set-cj-cream-matte-breakfast-cup` | $3.41 | Eub $8.39 / To Door $15.70 | D12.6 H6.3 | ✓ cream matte, wide low cup |
| | NEW `dining/mug-set/mug-set-cj-oat-speckled-round-mug-wood-saucer` | $8.28 | not quoted (~same class) | 9.8×7.5 | ~ dark walnut saucer |
| **bowl** (D20-26, H7-11) | NEW `dining/bowl/bowl-cj-glutinous-white-belly-bowl-21` | $6.68 | Eub $9.40 / To Door $27.41 | D21.2 H6.4 | ~ best so far: real photos; H 0.6 short |
| | existing `bowl/bowl-cj-speckled-ivory-wide-bowl-21` / `bowl-cj-reactive-white-rimmed-plate-21` | $3.50 / $9.62 | $11.92 / $31.68 ; $10.27 / $26.95 | H5.2 / H4.4 | ✗ too shallow |
| **kitchen-sconce** (hardwired, CE, 220-240V) | existing `wall-sconce/wall-sconce-cj-linen-cone-black` | $66.00 | Eub $43.45 / To Door $70.88 | 15×20×25.8 | ✓ for this slot (it failed only the living reading-lamp envelope); hardwired |
| | existing `wall-sconce/wall-sconce-cj-black-swan-arm-pleated-linen` | $27.78 | Eub $19.49 / To Door $60.03 | 18×26×17 | ~ swan arm, black-bronze sheen |
| | NEW `entrance/wall-sconce/wall-sconce-cj-wavy-linen-flush-25` | $30.68 | Eub $15.32 / To Door $39.16 | 25×21 | ~ flush linen, wavy French edge |
| | (other rooms) `kids/wall-sconce/wall-sconce-cj-black-swing-arm-wood-shade`, `master/bedside-sconces/bedside-sconces-cj-linen-wave-flush` | $10.78 / $29.78 | see cards | | options carded by the parallel agents |
| herb-pots, sink-set, utensil-crock, cutting-boards, condiment-set, paper-towel-holder, canisters, tea-towel, kitchen-runner | none | | | | gaps (see below) |
| under-shelf LED | none (shell per round_2) | | | | no card needed. Lead only: F91CA00A-6403-435D-8E5A-5555B4D78FFA LED cabinet light, listedNum 384 |

**Leads not opened (pid, price, listedNum; thumbnails only):**
- mug: 2609031002121616200 cream stoneware mug with a wood handle ($2.30, 1).
- open-shelf: 5DA8C827-8C4C-45C0-BCE8-90533B59BA98 matte white Nordic bisque vases, 9 shapes A-I, including a small two-ear amphora ($3.90-6.79, 1016). Opened, but no dimensions and no shape-to-variant map, so no card.
- utensil-crock: 2606261004131613300 wooden utensil container ($4.56, 8; acacia-brown).
- cutting-boards: 2609080217501628300 acacia board ($6.60, 3; acacia is outside the oak range).
- tea-towel: 1783073830336995328 (3-pack cotton, 31) and 1785616307094827008 (cotton plaid, 44); colours look teal/blue.

## Entrance (H0)
| Slot | Candidates (card) | Price | IL shipping eco / fast | Dims (cm) | Verdict |
| --- | --- | --- | --- | --- | --- |
| **table-lamp** (console 80 wide, EU plug, CE, fabric shade) | NEW `entrance/table-lamp/table-lamp-cj-white-textured-ceramic-linen-drum` | $15.28 | Eub $37.15 / none under $239 | H55 shade D32 | ~ right materials; images look AI-rendered, listedNum 0 |
| | NEW `entrance/table-lamp/table-lamp-cj-pleated-shade-wood-column` | $19.73 | not quoted | not stated | ✗ palette: reddish-walnut column (warm-modern pool) |
| **wall-sconce** above the bench | NEW `entrance/wall-sconce/wall-sconce-cj-wavy-linen-flush-25` | $30.68 | Eub $15.32 / To Door $39.16 | 25×21 | ~ (see kitchen) |
| | existing `wall-sconce-cj-linen-cone-black`, `wall-sconce-cj-black-swan-arm-pleated-linen`; `master/.../bedside-sconces-cj-linen-wave-flush` | | | | same family; bridge rule = linen |
| **ceiling-light** (hall centre pendant) | NEW `entrance/ceiling-light/ceiling-light-cj-waxwood-dome-ash-40` | $17.58 | Eub $42.19 / none under $226 | 40×34×26 | ~ walnut-brown cap and trim |
| | existing `pendant/pendant-cj-pleated-pumpkin-lantern-40` | $46.10 | Eub $54.80 / none | D40 H25 | ✓ closed pleated lantern (8.5 in the living ranking) |
| | NEW dining lantern card, **40 cm vid 1604681294414360576** | $38.29 | not quoted | D40 H30 | ✓ same line as the dining pendant (bridge) |
| | existing `pendant/pendant-cj-silk-pumpkin-lantern` (40) | $29.85 | Sensitive $43.81 / To Door $48.44 | D40 | ~ |
| bench-cushion | NEW bench-pad card (long cushion 100/120/150 × 50 × 8) | $5.31-7.46 | not quoted | | ✗ weak (tufted polyester) |
| key-tray, runner-rug, wall-hooks (oak) | none | | | | gaps |
| mirror | not listed (house-plan 6.3: "no mirror") | | | | not searched |

Not assigned to me but available in the pool for the hall: basket (`basket/*` with `hallway`), planter, and console-vessel (`vase/vase-cj-white-textured-jar` Tall 36 / `pool/vase/pool-cj-wabi-sabi-floor-vase-white`).

## Corridor (C0)
| Slot | Candidates (card) | Price | IL shipping eco / fast | Dims (cm) | Verdict |
| --- | --- | --- | --- | --- | --- |
| **ceiling-lights** (2 semi-flush, 2.70 ceiling) | NEW `corridor/ceiling-lights/ceiling-lights-cj-pleated-fabric-saucer-flush-50` | $36.15 each | Eub $30.20 / none under $227 | D50 H21 | ~ voltage and CE not stated; listedNum 4 |
| | NEW `corridor/ceiling-lights/ceiling-lights-cj-silk-cocoon-flush-40` | $28.83 each | not quoted | D40 H15 | ~ "silk" is a sprayed polymer cocoon (plastic? copy-risk family) |
| gallery-art (3 prints, 40 wide, top ≤1.70) | NEW `corridor/gallery-art/gallery-art-cj-black-botanical-cutout-set3` (Type B) | $14.53 / set | not quoted | 3 × 40×60 | ~ 5 cm over the top line; PS wood-look frame |
| | NEW dining `framed-art-cj-swinging-line-...` Types A+B+C | 3 × $21.23 | Eub $23.90 each | 3 × 35×45 | ~ 35 wide; B and C are dark blocks |
| picture-lights (×3) | NEW `corridor/picture-lights/picture-lights-cj-black-tube-rechargeable` | $5.72 | not quoted | bar ~30 | ~ plastic body, no 2700K, battery (no cable) |
| | NEW `corridor/picture-lights/picture-lights-cj-black-battery-bar-40` | $51.86 | **no IL shipping** | 40 | ✗ rejected |
| runner-rug (long, flat) | none | | | | gap |

## Rejected after a `product` call (no card; do not re-check)
- 2411260709231626700: fabric "lantern" line (Ball/UFO/Saucer/Cigar 30-60). Nelson Bubble/Saucer look-alikes (copy rule). Many 220V sizes.
- 2606101042451600000: pleated cone on an angled black stem. Reads as a known design (Pleat Box type), H40 > 35, open bottom, 9.6 kg.
- 2411120547411604200: French scalloped embroidered table lamp. US plug only, brass, embroidery.
- 2610080619101631900: linen column table lamp. CN/US plug only.
- F0443A4D-DEEB-440D-A010-FEF21147C452: "Scandinavian" cotton-linen rug. Only 60×90, every variant printed, with tassels.
- 2411050950161619400: linen-cotton tea towel. Blue plaid only.
- 2606010921211616500: ceramic foam dispenser. Squirrel/owl figurative.
- 2607010514221630100: coarse-pottery tea canister. Rustic glazes, printed fabric lids.

## Slot coverage summary
- **Kitchen + dining (23 slots + shell LED): 2 slots have ≥3 candidates**: dining-pendant (3) and kitchen-sconce (3, plus 2 from other rooms). bowl has 3 cards, but only the new one is close (H 6.4). 1-2 candidates: framed-art (2), mug-set (2), tableware-set (2 partial lines, no full set), table-runner (1, 33×140), centerpiece-vase (1), open-shelf-ceramics (1 partial), bench-pad (1 weak). **0 usable**: candle-holders (charcoal), curtains (no 280 drop), floor-vase, dining-rug, herb-pots, sink-set, utensil-crock, cutting-boards, condiment-set, paper-towel-holder, canisters, tea-towel, kitchen-runner.
- **Entrance (8 assigned): 2 slots have ≥3 candidates**: wall-sconce and ceiling-light. table-lamp has 2 (1 good). Gaps: key-tray, runner-rug, bench-cushion (weak only), wall-hooks.
- **Corridor (4): 0 slots have ≥3 candidates.** ceiling-lights 2, gallery-art 2, picture-lights 1. Gap: runner-rug.

## Gaps and next steps (need a decision)
1. **CJ cannot supply the small kitchen accessories, rugs or oak wood items.** Name-filtered searches return bonsai pots, glass jars, bamboo boards and printed rugs. Options: (a) a **CJ Sourcing request** with photos and dimensions for: oak cutting boards (2 sizes), oak-lid stoneware canisters ×3, stoneware utensil crock, stoneware herb pots ×2, matte ceramic soap pump with a dish brush and tray, salt/pepper grinders + ceramic oil cruet, oak paper-towel stand, linen tea towel (oat/stripe), flat-weave cotton runners (60×240-280, 70×200, 70×450) and a dining rug (160×230 / 200×290); (b) the AliExpress route, once it can be read (reCAPTCHA so far); (c) master-designer drops the weakest D2 slots (density rule: the smallest slot on the busiest surface goes first).
2. **Curtains:** the house curtain family is sold only in a 260 drop. The dining panel needs 278-282: ask the supplier for a custom length, or choose another product for the family.
3. **Candle-holders (charcoal) and floor-vase:** still no CJ match after 3 rounds.
4. **Lights:** CE is not stated on any listing. Before ranking, ask the suppliers for certificates for the shortlisted vids (dining lantern 50/40, pleated saucer, wavy linen sconce, linen-cone sconce, ceramic table lamp).
5. **Duplicates across rooms:** the parallel agents carded the same listings for kids/master in the same session (waxwood dome, wavy linen sconce, swinging-line art, cut-out set). Each card notes the other path. These are the same product used in several rooms, with different variants.
