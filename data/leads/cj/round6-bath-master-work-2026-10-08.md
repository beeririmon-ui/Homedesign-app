# CJ round 6 (2026-10-08): bathroom (B1/B2), master bedroom (MB0), work room (W0)

> sourcing-agent. User request: "חפש מוצרים מתאימים להכל, כמה דוגמאות לכל מוצר".
> Slots: `docs/proposals/house-framing.json` → `round_2.rooms.bath` (21 slots, B1 + B2) and `round_2.lighting_plan_S12`; `docs/house-plan.json` → `slots_first_list.master` / `.work`, plus the S11 additions (master: floor-lamp, nightstand-tray; work: pendant, wall-sconce, bookends, waste-basket). Palette and materials: `docs/design-bible/nordic.md` 1.5 (including the bath exception U6 and the proposed bath lighting exception: no fabric or paper shade, matte ceramic, plaster or etched opal glass, IP44). Electrical: `docs/brand-brief.md`.
> Master and work have no written envelopes yet. The SPEC CHECK lines use the frame geometry (MB-A: bed 180×200, 45 cm nightstands, sconce pair; W-A: 160×60 desk on the east wall, window 1.20 wide).
> 17 new cards, all `status: candidate`, no style_scores, `usage_rights: unclear`. **CE is not verified on any light, and IP44 is not verified on any bath light except the IP65 mini fitting.** Nothing committed by me. (The coordinator's commits already include these cards.)

## API use: I went over my cap (wrapper bug)
- **Intended:** 37 search/list calls (9 `search`, 28 `list`, including 1 `getCategory`) and 45 product/freight calls (28 `product`, 17 `freight`).
- **Real, including accidental retries:** about **57 search/list** and **55 product/freight** successful requests. My scratch wrapper retried any call whose output contained the text "429". CJ image URLs often contain "429" in their UUIDs, so 15 successful calls were each repeated twice more (30 extra requests). There were also about 20 genuine QPS-429 rejections, which were retried after a few seconds.
- The API never returned a daily-quota error. I stopped all API calls once I found the bug. **For future wrappers:** match `HTTP Error 429` in stderr only, never the JSON body.

## Search-tool findings
- `list "<one word>" --category <id>` is the only reliable filter. Useful ids from `getCategory`: Towels `331F43CE-CA1D-45F2-BE2A-8AE62EC10251`, Bedding Sets `496E6FFC-4BC4-4CA6-8225-5BC0D56E8E11`, Bathroom Storage `B62EE40F-7650-4715-A7A5-BA227540593C`, Night Lights `538CB48E-B7A0-46F7-B5A2-BB8183247B23` (holds most table and bedside lamps), Wall Lamps `AC4A8F93-27FF-4531-8394-53E97F02159D`, Floor Mats `2601070550351602500` (tiny), Storage Bags & Cases & Boxes `2502140315331600200`. The tree has no table-lamp, desk-lamp, rug, vase or candle category.
- Words that worked: "shower" in Curtains (41 results), "linen" in Bedding Sets (147), "fabric" in Wall Lamps (15), "linen" in Night Lights (7), "ceramic" in Bathroom Storage (136), "bookends" (42). Older scratch lists were reused at no cost: `list travertine` gave the travertine trays and the bath set.
- `search` (listV2) returns pet ladders for "towel ladder" or "blanket ladder", phone holders for "toilet brush", and seasoning bottles for "reed diffuser". Avoid it for these.
- Volumetric shipping: flush sconces and bulky textiles get "fast" quotes of $70–110. Only Eub is sensible for them.

Legend: ✓ passes the envelope; ~ passes with a flag; ✗ fails a hard point (kept for the record). "Reuse" = an existing card (any room) that can serve the slot.

## Bathroom (B1 + B2, 21 slots)
| Slot | Candidates (card) | Price $ | IL shipping eco / fast | Dims (cm) | Verdict |
| --- | --- | --- | --- | --- | --- |
| **shower-curtain** (hero B1; linen-look, oat, floor-skimming from the ceiling L-track at 2.70; run 1.20 + 1.05) | NEW `bath/shower-curtain/shower-curtain-cj-linen-look-khaki-grommet` | 6.88 | Eub 12–50 d $10.27 / To Door 11–18 d $18.68 | 200 × 240 | ~ right colour and weave (polyester linen-look). ✗ drop: the longest is 240, so it ends ~25 cm above the floor. Silver grommets show at the top of the stack |
| | lead 2602070307171635000 tencel/poly-linen check or stripe, beige/white (opened, no freight) | 8.98–10.08 | — | max 183 × 213 | ✗ drop even shorter; subtle check pattern |
| | leads (not opened): 1719298630785437696 plain "shading" curtain (listedNum 108); 2609080642591606200 laminated linen-look, magnetic (0) | 1.71–6.08 | — | n/v | thumbnails only |
| **vanity-sconces** (B2 pair, flat ≤12, IP44, hardwired; also B1 **wall-sconce**, same family) | NEW `bath/vanity-sconces/vanity-sconces-cj-fluted-resin-updown-white` | 7.30 each | Sensitive 22–27 d $23.57 / To Door $28.20 | 13 × 7.5 × 16 | ~ **best look** (matte white fluted up/down, listedNum 81). IP not stated, 110–220V, CE n/v |
| | NEW `bath/vanity-sconces/vanity-sconces-cj-flat-halo-disc-white` (D15/20/24) | 5.92 | Liquid Line 9–23 d $9.40 / To Door $14.31 | D15, ~3–4 thick | ~ 85–265V, flat halo, listedNum 62. No IP, reads modern rather than ceramic/opal |
| | NEW `bath/vanity-sconces/vanity-sconces-cj-ip65-mini-updown-white` | 3.30 | Eub $11.67 / To Door $20.87 | 4.5 × 5.8 × 9.5 | ✗ scale (too small beside a 100 × 80 mirror). The only IP-rated option (IP65, 86–265V, 3000K). Fallback for B1 |
| **bath-towels** (on the ladder) + **hand-towel** (ring) | NEW `bath/bath-towels/bath-towels-cj-cotton-waffle-white` (70×140; the 35×75 vid is in the card) | 5.47 / 1.65 | Eub $8.51 / To Door $15.90 | 70 × 140 | ~ cotton waffle, listedNum 64. Pure white (cool), no oat. Photos are mostly set diagrams |
| | lead 1770752693439565824 cotton waffle towel (53), colours n/v | 1.16–13.12 | — | n/v | not opened |
| **bath-mat** (zone 40 × 55) | NEW `bath/bath-mat/bath-mat-cj-tufted-cotton-frame-beige-40x60` | 5.97 | Eub $10.02 / To Door $31.50 | 40 × 60 | ✓ cream framed cotton; khaki and lines-beige variants give 3 variations |
| | NEW `bath/bath-mat/bath-mat-cj-solid-wood-slatted-61x45` | 19.70 | Sensitive $74.85 / To Door $79.49 | 61 × 45 × 3 | ✗ too big, too orange, shipping 4× the price. The wood-duckboard idea is right |
| **shower-dispensers** (set of 3, matte ceramic, niche) + **soap-dispenser** (vanity) | NEW `bath/soap-dispenser/soap-dispenser-cj-matte-ceramic-cream-black-pump` (×3 for the niche) | 4.36 | Eub $10.02 / To Door $18.28 | 9.6 × 12.5 | ✓ matte cream with a black pump. White, tan and dark-brown bodies in the same listing. Avoid the rose-gold pump |
| | lead 2604200352011637200 silver travertine lotion bottle 8 × 16 (opened) | 21.39 | — | 8 × 16 | ✗ antique-bronze pump |
| | lead 2605250751341616600 hammered taupe 4-piece ceramic set (opened) | 5.80 | — | n/v | ✗ no dimensions published |
| **toothbrush-cup** | NEW `bath/toothbrush-cup/toothbrush-cup-cj-silver-travertine-cup` | 19.73 | Eub $11.92 / To Door $21.26 | D8 × H11 | ✓ honed silver travertine, sits well on the limestone top. Pricey |
| **vanity-vase** (bud vase, one sprig) | lead 5DA8C827-8C4C-45C0-BCE8-90533B59BA98 matte white Nordic bisque vases A–I (1016) (opened) | 3.90–6.79 | — | n/v | ✗ no dimensions, no shape-to-variant map (also noted by the dining agent) |
| | lead 2602240558451615800 travertine dried-flower vase (7) | 14.76–32.01 | — | n/v | not opened |
| **storage-basket** (vanity open shelf, cabinet 110 × 48) | NEW `pool/basket/pool-cj-cotton-linen-box-camel-40x30` | 1.57 | Eub $7.50 / To Door $16.30 | 40 × 30 × 25 | ~ fits; two-tone (camel + white band) reads utilitarian |
| | reuse `basket/basket-cj-jute-rope-cylinder` (35 × 39), `basket/basket-cj-cotton-rope-white` | 5.17 / 12.86 | see cards | | ~ height vs the shelf opening not yet known |
| **toilet-brush** | lead 2607180701501610400 ceramic holder D10.5 × H12.5, overall 28 (opened, no freight) | 5.47 | — | 10.5 × 28 | ✗ glossy speckled glaze, printed wood-grain band, steel handle |
| **bin** (pedal, matte) | leads: 1952654031088754689 8-piece ABS + bamboo set incl. bin and brush, 5 colours (94, opened); 1702334570311458816 black 5-piece incl. bin (34) | 26.01 / 17.54 | — | n/v | ✗ plastic, chrome pump. Gap |
| **toilet-paper-stand** | leads: 2076505874313023489 black standing holder; 2076505850407976961 steel stand | 25.76 / 28.35 | — | n/v | not opened; US-style listings. Gap |
| **shower-stool** (oak or teak, oiled) | leads: 1991192246121127938 bamboo bench 20" with shelf (14); 2096857199063883777 dark-wood bench (3) | 44.06 / 55.80 | — | ~51 wide | not opened; bamboo/dark wood, likely US warehouse. Gap |
| **towel-ladder** (≤1.35 high) | none | | | | **Gap.** No towel or blanket ladder on CJ |
| **towel-ring** | lead 2609080556041629700 punch-free steel ring/bar (0) | 4.04–4.92 | — | n/v | not opened; finish n/v. Gap |
| **ledge-planter**, **floor-planter** | reuse `planter/planter-cj-cement-ribbed-belly` (floor, 42 × 35.5) | 31.16 | see card | | ~ floor only; nothing small for the ledge. Gap for ledge-planter |
| **reed-diffuser** | none | | | | **Gap** (search returns perfume and seasoning bottles) |
| **candle** (matte vessel) | reuse `candle-holders/candle-holders-cj-travertine-pedestal` (pillar candle as filler) | 9.12 | see card | 7 × 11 | ~ a holder, not a vessel. Gap for a vessel candle |
| optional pendant west of the vanity / flush ceiling light (IP44) | none | | | | not searched further: no IP44 fabric-free pendant seen in Wall/Ceiling lists |

## Master bedroom (MB0, 15 slots)
| Slot | Candidates (card) | Price $ | IL shipping eco / fast | Dims (cm) | Verdict |
| --- | --- | --- | --- | --- | --- |
| **bedding** (hero, bed 180 × 200) | NEW `master/bedding/bedding-cj-washed-linen-natural-set` (1.8 m set) | 48.68 | Eub $43.96 / To Door $71.67 | duvet size n/v (220 × 240 expected) | ✓/~ **best**: washed linen in 11 colours (natural, white, milk-apricot, a sage-like mint = 3 variations). No fibre % stated. Photos look like a western brand's catalogue, so order a sample |
| | NEW `master/bedding/bedding-cj-cotton-linen-duvet-beige` (3-piece) | 128.36 | To Door $107.99 / only DHL | 240 × 220 | ~ cotton-linen blend; expensive, 5 kg |
| | reference: `kids/bedding/bedding-cj-muslin-cotton-duvet-dune` | 14.93 | see card | 173 × 229 | ✗ too small for 180 |
| **pillowcases** | NEW `master/pillowcases/pillowcases-cj-linen-pair-coconut-button` (pair, 100% linen) | 13.23 | Eub $9.15 / To Door $16.89 | 48 × 74 | ✓ natural or white; also included in the washed-linen set |
| | lead 2604030237181610200 ruffled linen pillowcase, sage (0) | 12.87 | — | n/v | not opened |
| **throw** (bed foot) | NEW `master/throw/throw-cj-cotton-waffle-ruffle-khaki-150x200` | 13.55 | Eub $17.84 / To Door $30.58 | 150 × 200 | ~ cotton waffle, listedNum 424; ruffled frill; grey may read as sage |
| | reuse `sofa-cover/sofa-cover-cj-washed-hemp-throw`, `sofa-cover/sofa-cover-cj-cotton-muslin-fringe` | 37.98 / 11.64 | see cards | 150 × 200 | ~ |
| | reuse `kids/bedspread/bedspread-cj-muslin-blanket-beige-150x200`, `kids/bedspread/bedspread-cj-six-layer-gauze-quilt` | 11.61 / 8.46 | see cards | 150 × 200 | ~ |
| **cushions** | reuse the 11 cards in `cushions/` (rooms include bedroom): linen-look ivory/charcoal, washed cotton, sage chenille | 1.2–3.6 | see cards | 45 × 45 | ✓ |
| **bedside-sconces** (pair, oat linen, hardwired) | NEW `master/bedside-sconces/bedside-sconces-cj-linen-wave-flush` | 29.78 each | Eub $11.54 / To Door $82.78 | 24 × 20 | ~ beige linen scallop flush, 220V, CE n/v, depth n/v, listedNum 1 |
| | NEW `master/bedside-sconces/bedside-sconces-cj-linen-half-drum-black-trim` | 30.68 each (pair $61.36) | Eub $15.32 / To Door $39.16 | 25 × 21 | ~ voltage and CE n/v. **Duplicate:** the entrance agent carded the same pid 2512310801421607100 as `entrance/wall-sconce/wall-sconce-cj-wavy-linen-flush-25`. Merge into one pool card |
| | reuse `wall-sconce/wall-sconce-cj-black-swing-arm-fabric` (plug-in EU) | 13.76 | Sensitive $105 / To Door $110 | n/v | ~ shipping 8× the price |
| | lead 2601010327331635600 square fabric cube 12/15/20 (opened) | 16.86–31.18 | — | 20 × 20 × 15 | ✗ listing says "≤36V" |
| **floor-lamp** (reading corner, X ≈1.40) | reuse `floor-lamp/floor-lamp-cj-black-drum-linen` | 9.02 | see card | n/v | ~ plug type not stated |
| | lead 2603160537471605400 linen column floor lamp (opened) | 43.95 | — | ~150 h (box 157) | ✗ only a US-plug variant (220V). Strong Nordic look: ask CJ for an EU plug |
| **pendant** (centre, transit only) | reuse `pendant/pendant-cj-silk-pumpkin-lantern`, `pendant/pendant-cj-pleated-pumpkin-lantern-40`, `pendant/pendant-cj-tiered-fabric-drum` | 29.85–46.10 | see cards | D40–50 | ~ CE n/v on all |
| | reuse `corridor/ceiling-lights/ceiling-lights-cj-pleated-fabric-saucer-flush-50`, `corridor/ceiling-lights/ceiling-lights-cj-silk-cocoon-flush-40` (bridge with the corridor) | 36.15 / 28.83 | see cards | | ~ CE n/v |
| **curtains** (window 1.50 wide, 3.00 ceiling) | reuse `curtains/curtains-cj-japanese-linen-half-shade`, `pool/curtains/pool-cj-linen-look-tassel-curtain` | 16.58 / 9.62 | see cards | 150 × 260 | ~/✗ the 260 drop is probably short (the dining spec needs 278–282) |
| **rug** | reuse `rug/rug-cj-braided-wool-natural` | 267.54 | see card | 200 × 300 | ~ only option |
| | leads: 2105401081122893825 beige washable 5×7 ft; 2105398589498912769 beige distressed 5×7 ft | 68.99 | — | 152 × 213 | not opened; US warehouse. Gap |
| **framed-art** (centred over the bed) | reuse `framed-art/framed-art-cj-morandi-triptych-sage` (50 × 70), `dining/framed-art/framed-art-cj-swinging-line-black-frame-mat-35x45`, `kids/framed-prints/framed-prints-cj-charcoal-line-black-frame-35x45` | 15.75–21.23 | see cards | | ✓ |
| | leads (round 2): 2411130841401628600 B&W winter trees pair (519), 2411231150051604700 B&W line abstract (251) | | | | not opened |
| **nightstand-vase** | reuse `vase/vase-cj-white-plum-hand-thrown` (H33), `vase/vase-cj-coarse-sand-white-tall` (H30), `vase/vase-cj-textured-white-stoneware` | 10–24 | see cards | | ✓ (may be tall for a 45 cm nightstand group) |
| **candle-holders** | reuse `candle-holders/candle-holders-cj-travertine-pedestal`, `pool/candle-holders/pool-cj-carbonized-wood-pedestal-candlestick` | 9.12 / 8.45 | see cards | | ~ |
| **planter** | reuse `planter/planter-cj-cement-ribbed-belly`, `planter/planter-cj-seagrass-belly` | 31.16 / 8.00 | see cards | | ~ |
| **basket** | reuse `basket/basket-cj-jute-rope-cylinder`, `basket/basket-cj-seagrass-belly`, `basket/basket-cj-cotton-rope-white`, NEW `pool/basket/pool-cj-cotton-linen-box-camel-40x30` | 1.57–12.86 | see cards | | ✓ |
| **nightstand-tray** | NEW `pool/tray/pool-cj-travertine-organic-tray-24` | 17.13 | Eub $19.49 / To Door $33.17 | 24 × 17 × 1.8 | ✓ beige travertine pebble tray (bridges to the living-room travertine); "bright light" craft field: confirm it is honed |
| | leads (free, from older lists): 2602131451031607000 grey travertine tray (6); 2601250905591635600 off-white travertine round tray (4); 2609190823201624800 travertine soap dish | 27.36 / 42.45 / 2.57 | — | n/v | not opened |

## Work room (W0, 13 slots)
| Slot | Candidates (card) | Price $ | IL shipping eco / fast | Dims (cm) | Verdict |
| --- | --- | --- | --- | --- | --- |
| **desk-lamp** | reuse `entrance/table-lamp/table-lamp-cj-white-textured-ceramic-linen-drum` (EU plug, 220V) | 15.28 | see card | 32 × 55 | ~ ceramic + linen = the Bible shared lamp family |
| | reuse `entrance/table-lamp/table-lamp-cj-pleated-shade-wood-column` | 19.73 | see card | n/v | ~ |
| | lead 2411250830471615200 turned-wood lamp, EU plug (opened) | 26.20 | — | 23 × 52 | ✗ black opaque shade (Bible: shade warm white or oat only) |
| | lead 2609010242431602800 linen cylinder on a wood base (1) | 1.60–2.76 | — | n/v | not opened; the price suggests USB |
| | rejected on sight: 2609180703541605900 "Italian" balance-arm desk lamp | | | | replica risk |
| **pendant** (over the desk) | reuse `kids/pendant/pendant-cj-fabric-dome-ash-cap-25` (Large 40 vid in that listing) = `entrance/ceiling-light/ceiling-light-cj-waxwood-dome-ash-40` (**same pid 2508280237031614500, carded twice by the other agents**) | 14.10–17.58 | see cards | D25 / D40 | ~ CE n/v |
| | reuse `pendant/pendant-cj-silk-pumpkin-lantern`, `pendant/pendant-cj-pleated-pumpkin-lantern-40` | 29.85 / 46.10 | see cards | D40 | ~ |
| | 1410516049559949312 fabric drum (re-opened by mistake: it is the rejected `pendant/pendant-cj-oak-stem-fabric-drum`) | 14.02 | — | D40 | ✗ listing says "Certification: None" |
| **wall-sconce** (by the window) | reuse `wall-sconce/wall-sconce-cj-black-swing-arm-fabric` (plug-in EU, short cable to a socket is allowed outside kids/bath) | 13.76 | Sensitive $105 / To Door $110 | n/v | ~ shipping |
| | reuse NEW `master/bedside-sconces/...linen-half-drum-black-trim` / `...linen-wave-flush` (hardwired) | ~30 | see above | | ~ |
| | lead 2607310945011637900 black adjustable spot wall lamp (0) | 5.61–8.25 | — | n/v | not opened; reads modern |
| **shelf-boxes** | NEW `pool/basket/pool-cj-cotton-linen-box-camel-40x30` | 1.57 | Eub $7.50 / To Door $16.30 | 40 × 30 × 25 | ~ depends on the shelf depth |
| | leads: 2091644495797080065 linen bins with rope handles, 3-pack (11); 2605140825131625100 cotton-linen box (4) | 40.74 / 1.22 | — | n/v | not opened |
| **desk-tray** | NEW `pool/tray/pool-cj-travertine-organic-tray-24` | 17.13 | see above | 24 × 17 | ✓ |
| | lead 2610071003451617200 solid-wood desk organizer with a charging slot (0) | 2.85 | — | n/v | ✗ dark walnut, gadget look |
| **bookends** (books = filler) | lead 2602280344041635200 stone bookends, 9 styles incl. travertine arch and rough white rock (opened) | 29.85–111.94 | — | 8–23 cm, 2.3–5.7 kg | no card: the style-to-photo map is unclear and the weight makes shipping heavy. Ask CJ which style is the travertine arch |
| | leads: 1569991671146885120 plain black iron bookends (19); 1551864920176865280 black-walnut bookend (31) | 1.70 / 3.36 | — | n/v | not opened |
| **waste-basket** | leads: 2509060609261629100 flip wastebasket (1); 1607283628000686080 foldable bucket (53) | 4.27 / 3.25 | — | n/v | not opened. Gap |
| **magazine-holder** | reuse the 4 `magazine-holder/` cards (round 5: none fits the living envelope; work has no envelope yet) | | see cards | | ~ |
| **planter** | reuse `planter/planter-cj-cement-ribbed-belly` | 31.16 | see card | 42 × 35.5 | ✓ corner by the window |
| **framed-art** | same reuse as master | | | | ✓ |
| **rug** (room 2.95 × 3.75) | none | | | | **Gap** (braided wool 200 × 300 is too big) |
| **curtains** (window 1.20, head 2.70) | reuse the two 150 × 260 curtains | | | | ~ |
| **basket** | same reuse as master | | | | ✓ |

## Coverage (≥3 candidates, cards + reuse)
- **Bath:** 2 of 21 (vanity-sconces and the B1 wall-sconce, the same 3 cards). One card each: shower-curtain, bath-towels/hand-towel, shower-dispensers/soap-dispenser, toothbrush-cup, storage-basket. Two for bath-mat.
- **Master:** 7 of 15 (throw, cushions, bedside-sconces, pendant, framed-art, nightstand-vase, basket). bedding 2, pillowcases 1–2, curtains 2 (drop flag), floor-lamp 1, rug 1, candle-holders 2, planter 2, nightstand-tray 1.
- **Work:** 5 of 13 (pendant, wall-sconce, magazine-holder, framed-art, basket). desk-lamp 2 (reuse), shelf-boxes 1, desk-tray 1, planter 1, curtains 2, rug 0, bookends 0 (leads only), waste-basket 0.

## Gaps and questions for master-designer / the user
1. **Shower curtain drop:** CJ tops out at 240 (the khaki card) or 213. A floor-skimming curtain from the 2.70 ceiling track needs about 255–260. Options: lower the L-track or add a drop rod in the shell, accept a 240 that stops about 20 cm above the floor, or a CJ Sourcing request.
2. **Bath lights:** no CJ listing states IP44 together with a Nordic matte ceramic, plaster or opal look. The best look (fluted resin, listedNum 81) has no IP rating. Ask the supplier, or accept the IP65 fitting at B1 only?
3. **Missing on CJ:** towel ladder, oak or teak shower stool, matte pedal bin, toilet-paper stand, toilet brush, reed diffuser, candle vessel, bud vase with dimensions, Nordic desk lamp, mid-size rug (work 140 × 200 / master 200 × 300), waste-basket, bookends with a clear variant map. These need a CJ Sourcing request or an approved non-CJ dropship source.
4. **Two cross-agent duplicates:** pid 2512310801421607100 (`master/bedside-sconces/...half-drum-black-trim` = `entrance/wall-sconce/...wavy-linen-flush-25`) and pid 2508280237031614500 (`kids/pendant/...fabric-dome-ash-cap-25` = `entrance/ceiling-light/...waxwood-dome-ash-40`). Each should become one pool card listing all rooms.
5. **Washed-linen bedding set** (the master hero): the lifestyle photos look borrowed from a western linen brand. Order a sample before rendering for product fidelity.
6. Linen column floor lamp 2603160537471605400: ask CJ for an EU-plug version. It is the best reading-corner look found.
