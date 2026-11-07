# Brief: master bedroom, two story base frames (render-agent, 2026-11-07)

**Status: FINAL (2026-11-07).** MB-Q1 and MB-Q2 were decided by the manager. The brief runs as soon as MB1 is answered.

**Owner decision needed first:** MB1 (render spend). Run only after MB1 is answered.
**Cap:** 1,300 for the two base frames.
**Rules:**
- Test only: no site, no layers.
- No clay lock, no fixed camera, no grading to targets.
- No commit.
- Supplier images: crop them in the session scratchpad, upload with `var2_upload_asset`, never save them in the repo.

**Sources:**
- concept and products: `docs/master-bedroom-comparison-2026-11-07.md` §2–§3;
- the line: `docs/design-line-across-rooms-2026-11-07.md`;
- the method: `docs/render-recipe-story-v1-2026-11-07.md` §1–§6.

## Model and cost
| Frame | Model | Why | Tokens |
| --- | --- | --- | --- |
| Nordic master, wide | gpt-image-2-5 sunburst, 2K, 16:9 | The recipe's model for wide frames. It was the most faithful wide model in ED1, and built Nordic A, the approved frame | 600 |
| Warm-modern master, wide | gpt-image-2-5 sunburst, 2K, 16:9 | The same model built warm-modern ed5 (approved), so the comparison stays like-for-like | 600 |
| **Total** | | | **1,200** (cap 1,300) |

**Not part of this brief:**
- **Fidelity passes** (seedream-5-pro on masked crops, about 650 each) come after QA, per the recipe §3, and need the manager's approval.
- **Second frames and close-ups** come later.

## References (per frame: 1 products board + up to 5 single crops)
- **Crop source:** each crop comes from the card's `images.urls[0]` (or the named option), the product alone, no text and no people.
- **Fixed furniture:** the board also carries a plain description of it (generic, not sold in the story).

| Frame | Products board (all starring products) | 5 single references (shape-critical) |
| --- | --- | --- |
| Nordic | `bedding-cj-washed-linen-natural-set`, ‏`pillowcases-cj-pure-linen-envelope-pair-48x74` (natural), ‏`cushions-cj-boucle-teddy` (30×50, warm white), ‏`throw-cj-cotton-linen-light-gray-200x230`, ‏`nightstand-vase-aliexpress-handmade-wabi-sabi-vase-665862`, ‏`candle-holders-cj-travertine-pedestal`, ‏`bedside-sconces-cj-linen-wave-flush`, ‏`curtains-aliexpress-linen-blend-s-fold-180502`, ‏`vase-aliexpress-vintage-distressed-clay-vase-589009`, ‏`planter-zendrop-seagrass-belly-38x34`, ‏`basket-cj-jute-rope-cylinder` (11) | sconce (wave-flush), candle holders, nightstand vase, bedding, basket |
| Warm modern | `bedding-cj-washed-linen-natural-set` (Natural Linen), ‏`pillowcases-cj-pure-linen-envelope-pair-48x74` (Caramel), ‏`cushions-cj-boucle-teddy` (Milk Tea 30×50), ‏`sofa-cover-cj-cotton-muslin-fringe` (Pecan), ‏`wall-sconce-cj-travertine-cone-walnut`, ‏`candle-holders-cj-travertine-pedestal`, ‏`nightstand-vase-aliexpress-handmade-wabi-sabi-vase-665862` (Color D, the sand/taupe bottle 24.5×11; 2026-11-07: was "Color E" by mistake, E is a dark-red onion vase 16×20, card default_sku fixed), ‏`floor-lamp-cj-pleated-walnut-stem-158`, ‏`planter-cj-cement-ribbed-belly` (Beige, Large), ‏`curtains-aliexpress-beige-linen-sheer-curtains-554205`, ‏`sill-vase-cj-cream-fluted-column-25`, ‏`basket-cj-jute-rope-cylinder` (12) | travertine cone sconce, floor lamp (reuse the ED1 crop in the earlier `jobs.json`), candle holders, nightstand bottle, pillowcase (Caramel) |

**MB-Q1, final (manager, 2026-11-07): only products I could check by eye go in.**
- **What I checked:** the site's supplier-image cache (`site/.generated/supplier-images.json`, ‏`site/.cache/supplier-images/`) and the repo hold only the living-room products. None of the four sourcing-guess products is there.

| Product | Status | Consequence |
| --- | --- | --- |
| `framed-art-cj-black-ink-abstract-wide-mat-50-pair` (Nordic) | not cached | **Out.** The wall above the bed carries no art: the panelling, the sconces and the window light make the wall |
| `nightstand-tray-cj-black-walnut-rect-tray` (warm modern) | not cached | **Out.** The candle holders stand on the nightstand itself |
| `trinket-dish-cj-travertine-rough-edge-10x10` | not cached | **Out** (was not in the prompt) |
| `rug-cj-cream-embossed-arc-plush-200x300` | not cached | **Out** (was not in the prompt) |
| `floor-lamp-aliexpress-pleated-walnut-37x158-062736-master` (warm modern) | not cached; its 8.5 is from card data | **Out.** It is replaced by `floor-lamp-cj-pleated-walnut-stem-158` (warm modern 9.0, catalog), which was rendered faithfully in warm-modern ed5, and whose crop is already uploaded |

- **In:** every other product in the table carries a designer score that was given from its photos: on the card, in the Nordic assembly of 2026-10-11, or in the warm-modern catalog of 2026-10-12. Six of them were also already rendered faithfully in the living-room frames: the candle holders, the bouclé cushion, the muslin throw, the jute basket, the seagrass planter and the floor lamp. None of them was scored from card data alone.
- **Counts:** 11 products in the Nordic frame, 12 in the warm-modern frame. Both are inside the 10–14 rule.

**MB-Q2, final (manager, 2026-11-07):** a generic Nordic armchair by the window, with no dot. Its material and colour differ from the living-room armchair (that one is a light-oak frame with mist-grey bouclé).

## What the model decides, and what we fix
**The model decides:**
- the exact architecture within the concept;
- the light detail;
- the crop;
- the life traces (book, cup, robe, sandals).

**We fix:**
- the concept;
- lens and height (approximate);
- every product, with its count and shape.

## The prompts (English, as sent)
**The fidelity block, appended to both prompts:**
> Every listed product must match its reference exactly: shape, proportions, colour, material, pattern and number of pieces. Cushions are as stated (30 × 50 lumbar). Do not add any other baskets, bowls, vases, throws, cushions, lamps, rugs, trays, pictures or wall decorations beyond those listed. Generic props must differ clearly in material and colour from every listed product. No people, no readable text, no logos, no mirrors, no clear glass, no copied designer pieces.

### Nordic master: "Sunday morning, late February, 08:30"
> Editorial interior photograph for a high-end design magazine. The master bedroom of an old Scandinavian apartment: a tall white-painted double casement window with a deep 30 cm reveal, white-painted vertical board panelling to 1.10 m with a thin oak cap rail, warm mineral-white walls above, a plain cornice, a panelled door ajar to a dressing room, wide white-oiled oak floorboards.
> Light: a clear late-February morning, 08:30; low sun from the window on the left lays the diagonal stripes of the window frame across the rumpled linen bedding and one pillow; the far side of the room in soft shade; melting snow and birches outside. Lamps are off, except one bedside wall light left on faintly.
> Camera: 35 mm at 0.95 m, a three-quarter view from the foot corner of the bed toward the headboard wall, not symmetrical; foreground: the folded end of the grey throw on the bed, out of focus; aperture f/4, the bedside table and pillows sharp.
> Products, as in the references:
> - washed natural linen bedding, rumpled, the duvet folded back on one side;
> - exactly two natural linen envelope pillowcases;
> - one warm-white bouclé lumbar cushion 30 × 50;
> - the light-grey cotton-linen throw pushed to the foot of the bed;
> - on the bedside table, the taupe wabi-sabi bottle vase with one dry stem, and the pair of travertine pedestal candle holders with pillar candles;
> - the pair of cream ribbed linen wall lights, one on each side of the bed;
> - no picture above the bed: the panelling, the wall lights and the morning light make that wall;
> - natural linen S-fold curtains;
> - the cream clay vase with eucalyptus on the deep window sill;
> - in the corner, exactly one seagrass belly basket planter with a small olive tree and exactly one jute rope cylinder basket.
>
> Generic life, not products: a ceramic tea cup in a colour unlike the vase, a book lying open face-down, reading glasses, a linen robe over a generic lounge chair by the window, in a dark-stained ash frame with an undyed natural linen seat (not bouclé, not light oak, not mist grey).
> The bed and the bedside tables are simple light-oak pieces.

### Warm-modern master: "August siesta, 18:30"
> Editorial interior photograph for a high-end design magazine. The master bedroom of an architect's apartment: slim dark-bronze steel-framed glazing on the left, half veiled by a sheer beige linen curtain; a bone limewash plaster wall behind the bed with a rounded pill-shaped niche above the headboard; softly rounded wall corners; a 1 cm shadow gap at the ceiling; wide smoked-oak floorboards.
> Light: 18:30 in August; low amber sun from the west, filtered through the sheer curtain, falls as one soft slice across the plaster wall and a travertine wall light; the room in warm shade; the travertine lights have just been switched on.
> Camera: 50 mm at 0.85 m, almost frontal to the bed but shifted to the left so the composition is not symmetrical; foreground: the corner of the bed with the caramel muslin throw, out of focus; aperture f/4.
> Products, as in the references:
> - washed natural linen bedding, softly rumpled;
> - exactly two caramel linen envelope pillowcases;
> - one milk-tea bouclé lumbar cushion 30 × 50;
> - the pecan cotton muslin throw with short fringe folded across the foot of the bed;
> - the pair of travertine cone wall lights on walnut plates, one each side;
> - on the walnut bedside table, the pair of travertine pedestal candle holders and the tall sand-toned wabi-sabi bottle with an olive sprig, with no tray;
> - in the corner, the floor lamp with a walnut stem, brass details and a cream pleated cone shade (as in the reference), lit, and the warm-grey ribbed concrete planter with an olive tree;
> - on the window ledge, the cream fluted column vase;
> - one natural jute rope cylinder basket by the bed.
>
> Generic life, not products: an open architecture book, a stoneware cup in a colour unlike the products, leather sandals on the floor.
> The bed and bedside tables are simple walnut pieces with rounded edges.

## After the run (0 tokens unless approved)
1. QA: fidelity table and imitation check per frame (G-ED).
2. Code fixes: scale (sconces and lamps usually come out too big), ring and pleat counts, glaze of generic props.
3. Targeted passes, only with the manager's approval (about 650 each).
4. QA round 2, then the designer's eye verdict (G-ED.10 and .13), then the owner.
5. Present the result next to MB0 v7 and the approved living-room frames of the same style.

## Output
- `assets/renders/master/editorial-2026-11-07/nordic-MB-A.png`
- `assets/renders/master/editorial-2026-11-07/warm-modern-MB-A.png`
- `jobs.json`: placeholder ids, tokens, reference URLs.
- `sheet.jpg`: the two frames, next to MB0 v7 and to living-room Nordic A and warm modern ed5.
