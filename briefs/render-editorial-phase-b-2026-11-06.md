# Brief: editorial frames, phase B: finish three, add four styles (render-agent, 2026-11-06)

**Decisions (owner, 2026-11-06):**
- On the test: "נראה הרבה יותר מעוצב הפעם".
- **ED2:** first finish the three good frames, then the four other styles, about 4,550 tokens in total.
- **ED3:** the model per style is the designer's choice.

**Inputs:**
- The direction: `docs/creative-review-2026-11-06.md` (§2א, §3, §3.7).
- QA fidelity: `qa/reports/2026-11-06-editorial-test-fidelity.md` (+ `.json`, overlays).
- The test records: `assets/renders/editorial-test-2026-11-06/jobs.json` (reference URLs and placeholder ids) and `sheet.jpg`.

**Rules:**
- **TEST, not for the site** or the layers.
- No clay lock, no fixed camera, no grading to targets.
- No commit.
- Supplier images: crop them in the session scratchpad and upload with `var2_upload_asset`. Never save them in the repo.
- A new reference uses the card's `images.urls[0]` (or the option image named here), cropped to the product, with any text removed.

**Lesson from QA that applies to every prompt below: no invented look-alikes.**
- **List every product with its count** (for example "exactly one jute basket", "exactly one black bowl").
- **Add this line to every prompt:** "Do not add any other baskets, bowls, vases, throws, cushions, lamps or rugs beyond those listed."
- Cushions are described with shape and size ("square 50 × 50").

## Part 1: finishing (3 frames, one targeted pass each)
**Model:** **seedream-5-pro** image-to-image at 2K, about 650 per frame.
- **Why seedream:** it holds geometry, scale and the light of the base, and edits locally.
- The base is the frame itself, image_url = the placeholder below.
- **Prompt format:** "Edit this photograph. Keep the camera, architecture, light, shadows and every object not listed exactly as they are. Change only: …"

**The rug is the same fix in all three frames, and goes inside the same pass** (not its own pass; the budget is one pass per frame):
- **Reference:** `rug-cj-braided-wool-natural`, the crop already uploaded in `jobs.json` ("rug … caption removed").
- **Text:**
  > Replace the rug with the rug in the reference: a flat braided wool rug in cream and oat, made of tight parallel braided cords sewn side by side so it reads as fine tonal stripes running along its length, completely flat and low (about 1 cm), a soft matte surface. No loops, no shag, no diamond or Berber pattern, no fringe, no jute look. Keep its position under the front legs of the sofa and the armchair, and keep the sun and shadow falling across it exactly as before.
- **If the stripe still does not read,** QA marks the rug "partial". No re-run without the manager's approval.

### 1.1 Nordic A: base gpt-image-2-5 (`91902915-c566-4fa1-b224-75d84ae972de`)
**Why this base:**
- It has the fewest failures (QA: 8 faithful, 6 partial, 2 fail against nano's 5 fails).
- It has the stronger editorial qualities: sun stripes across the rug, a door open to the next room, and the armchair as a foreground.
- **Its errors are local.**

**Changes in the pass:**

| What | Do | Reference |
| --- | --- | --- |
| The **empty** seagrass basket in the back-left corner (the one without the olive tree) | **Replace** with exactly one `basket-cj-jute-rope-cylinder`: a straight jute-rope cylinder about 35 Ø × 39 with two rope-loop handles, standing on the floor | the jute crop in `jobs.json` |
| The seagrass belly planter with the olive tree | keep, exactly one | — |
| The charcoal lumbar cushion | **replace** with one **square 50 × 50** charcoal linen-look cushion, same place on the right seat | `cushions-cj-linen-look-charcoal` images.urls[0] (new upload) |
| The sage cushion | same place, size and colour, but the **knitted chenille bubble texture** of the card | `cushions-cj-knitted-chenille-bean-green` images.urls[0] (new upload) |
| The white bowl on the table | the same bowl made **shallower**: wide belly bowl about 21 Ø × 6.4, height/diameter about 0.3 | `bowl-cj-glutinous-white-belly-bowl-21` images.urls[0] (new upload) |
| The rug | the rug fix above | rug crop |

**Size fixes in code, after the pass (0 tokens):**
- **Wall lights:**
  - **Scale:** about 0.38× around their mounting point, to a block of about 8 × 16 against the 50 cm frames (QA measured them at 2.6–3×).
  - **Glow:** shrink it with them.
  - **Wall:** repair it from the adjacent texture and keep the sun patch.
- **Pendant:** scale about 0.7× from the cable anchor, to 40 cm against the 220 sofa (QA: 50–65). Keep the cable reaching the ceiling.
- **Check after both fixes:** the gap between the pendant and the triptych top stays at 0.02 of the frame or more.

### 1.2 Nordic B: base nano-banana-2 (`9287e398-ef4d-411c-8817-78ed3e42f540`)
**Why this base:** the most faithful frame (5 of 7 faithful). The only fail is the rug.

**Changes in the pass:**

| What | Do | Reference |
| --- | --- | --- |
| The taupe fringed throw on the armchair (invented, reads as ours) | **replace** with our throw `sofa-cover-cj-cotton-muslin-fringe`: soft crinkled muslin with a fine waffle grid and short 2–4 cm fringe, in white-ivory, folded once and draped over the right arm | the muslin crop in `jobs.json` |
| The rug | the rug fix above | rug crop |

**Note only (no change):**
- The corn-husk round's rim reads darker and wider than the card's thin honey rim. If the pass allows a third local change: "thin honey water-hyacinth rim".
- Otherwise it goes to QA as "partial, note".

### 1.3 Warm modern A: base gpt-image-2-5 (`64478a7a-25c6-4d69-886f-eb73872f167a`)
**Why this base:**
- QA: 7 faithful against nano's 4.
- The sunset glazing and the wall niche are the strongest frame of the test.

**Changes in the pass:**

| What | Do | Reference |
| --- | --- | --- |
| The second ribbed black bowl on the travertine side table, front left (invented) | **remove**; the side-table top shows travertine only (a cup may stay) | — |
| The pendant | **replace** with the card's shape: a fabric drum of 4–5 stacked rings that widen toward the middle and narrow at top and bottom, warm white, diffuser at the bottom. Not three tiers stepping down | `pendant-cj-tiered-fabric-drum` crop in `jobs.json` |
| The cream vase on the table | **replace** with `vase-cj-textured-white-stoneware`: tall crinkled off-white stoneware, about 16 Ø × 32, the olive branch kept | images.urls[0], Large option (new upload) |
| One of the two white bouclé cushions | change it to **Milk Tea** bouclé, square 50 × 50; the other stays white | `cushions-cj-boucle-teddy` Milk Tea option image (new upload) |
| The rug | the rug fix above (it is the same card, warm-modern 8.5) | rug crop |

- **Note to QA:** the brass of the floor lamp reads polished. A local specular soften in code is allowed (0 tokens). Otherwise mark it "note".
- **Generic, never a "buy" point:** the rounded sofa, the walnut table, the travertine side table.

## Part 2: four styles, one editorial frame each
- **Structure for every style** (as in the test):
  - image_url = a **products board** (the starring crops on a plain background);
  - plus up to **5 single references** for the shape-critical products;
  - 2K, 16:9.
- **The prompt** is §3 of the review turned into a photograph brief, plus the fidelity block with counts.

### Model per style (ED3)
| Style | Model | Why | Tokens |
| --- | --- | --- | --- |
| Boho | **gpt-image-2-5** sunburst | Many textiles and filtered striped light. gpt was the more faithful model in both test styles, and lights richly | 600 |
| Mediterranean | **gpt-image-2-5** sunburst | Hard noon light through shutters and arched architecture. gpt built the strongest architecture in the test (glazing, niche) | 600 |
| Modern country | **gpt-image-2-5** sunburst | Rain light against warm lamp pools, a doorway frame. The lamps are generic, and the starring products are textiles, the cushions above all, where gpt held pattern and texture better | 600 |
| Japandi | **nano-banana-2** | Few products (restraint), blue hour, a low camera. nano drew the most faithful frame of the test (Nordic B, a vignette with few objects), and the lower product count suits its weakness | 400 |

**Starring products and references**

| Style | Products board (all starring) | The 5 single references |
| --- | --- | --- |
| Boho | `cushions-cj-washed-cotton-frayed` Rust Orange ×2, `cushions-cj-sandstone-chenille-flange` (olive), `sofa-cover-cj-washed-hemp-throw` Raw Jute, `table-runner-aliexpress-boho-macrame-table-runners-263532`, `planter-zendrop-seagrass-belly-basket-45`, `basket-cj-seagrass-belly-xl`, `pouf-cj-cotton-knit-ball-cover` (natural), `wall-decor-aliexpress-natural-raffia-woven-bohemian-763597`, `wall-sconce-aliexpress-rattan-bamboo-wall-lamp-671943` | raffia sun, bamboo wall light, macramé runner, frayed rust cushion, knit pouf |
| Mediterranean | `framed-art-aliexpress-mediterranean-wabi-sabi-poster-802890` (three of the six designs: limewash wall, olive, arch), `magazine-holder-cj-arch-iron-cane`, `vase-aliexpress-vintage-distressed-clay-vase-589009`, `cushions-cj-washed-cotton-frayed` White + Earthy Orange + Moss Green 30×50, `sofa-cover-cj-cotton-muslin-fringe`, `bowl-cj-speckled-ivory-wide-bowl-21`, `candle-holders-cj-travertine-pedestal`, `basket-zendrop-seagrass-belly-38x34` | art triptych, arch magazine holder, candle holders, speckled bowl, seagrass basket |
| Modern country | `cushions-aliexpress-farmhouse-floral-pillow-covers-166217` (pair 50×50), `cushions-cj-chenille-check-milky-white`, `vase-aliexpress-vintage-distressed-clay-vase-589009`, `sill-vase-cj-cream-fluted-column-25`, `table-runner-cj-linen-look-sage-fringe` 4 Light Green, `bowl-cj-speckled-ivory-wide-bowl-21`, `curtains-aliexpress-linen-blend-s-fold-180502` | floral cushion, check cushion, fluted column vase, sage runner, clay vase |
| Japandi | `framed-art-aliexpress-japanese-wabi-sabi-tree-176323` (three of the series), `pendant-cj-pleated-pumpkin-lantern-40`, `vase-cj-black-matte-stoneware-jar-30`, `accent-sconces-aliexpress-travertine-cylinder-walnut-choice` (crop in `jobs.json`), `bowl-cj-matte-black-bowl-20`, `candle-holders-aliexpress-matte-black-iron-pillar-set2`, `bedspread-cj-six-layer-gauze-quilt` Beige Khaki, `cushions-aliexpress-fashion-modern-wabi-sabi-464203` | tree triptych, pleated lantern, black jar, iron plates, wabi-sabi cushion |

**Generic filler (in the frame, never a "buy" point):**
- **Boho:** the kilim rug, the earth-tone art, the rattan dome pendant, the mango bowl, the brass candle holders, the plants, the tea tray, the French doors and the painted tiles. The sofa, table and armchair are generic too.
- **Mediterranean:** the terracotta pot with the olive tree, the cane pendant, the jute rug, the built-in plaster bench, the shutters, the figs, the straw hat, the water carafe; the sofa, table and armchair.
- **Modern country:**
  - the art, the pleated pendant and the floor lamp, the brass candle holders, the wicker wall basket, the rug;
  - the terracotta pot, the wicker magazine basket, the pouf;
  - the jug of flowers, the cardigan;
  - the sofa, table and armchair.
- **Japandi:** the paper column floor lantern, the ink planter with the olive tree, the rug, the tea tray and set, the sofa, the table, the armchair and the low step.

### The prompts (English, as sent)
**The fidelity block, appended to all four:**
> Every listed product must match its reference exactly: shape, proportions, colour, material, pattern and number of pieces. Cushions are square 50 × 50 unless stated. Do not add any other baskets, bowls, vases, throws, cushions, lamps, rugs or wall decorations beyond those listed. No people, no readable text, no logos, no mirrors, no copied designer pieces.

**Boho:**
> Editorial interior photograph for a high-end design magazine. A living room in an old stone house by a harbour: thick walls with deep reveals, warm sand clay-plaster walls, exposed timber ceiling beams, a pair of tall wooden French doors standing open to a small balcony full of plants; the floor is faded earth-tone patterned cement tiles, with a flat-woven kilim rug in sand with rust diamonds over it.
> Light: 16:00 sun filtered through a half-rolled reed blind on the doors, throwing soft parallel stripes of light across the rug and the cushions; leaf shadows moving on the plaster.
> Camera: 30 mm, low at 0.85 m, from the corner; a large out-of-focus plant leaf in the foreground at the frame edge; the sofa vignette sharp.
> On a low linen sofa: the washed hemp throw (reference) in raw jute draped over the back and the left seats, two rust frayed cotton cushions and one olive chenille cushion with a flange. On a low wooden table: the macramé-and-jute runner, a mango-wood bowl, aged-brass candle holders, a tea tray with glasses. In the corner: exactly one seagrass belly basket planter with a bird-of-paradise plant and exactly one larger seagrass belly basket beside it. The natural chunky-knit ball pouf on the rug. On the wall: the raffia sun (reference) and two woven bamboo ball wall lights (reference) glowing softly from inside, no patterned shadows. An earth-tone abstract triptych (arch, sun, organic shape in terracotta, sand and olive) in plain wood frames. A woven rattan dome pendant. Layered, collected, edited, not a market.

**Mediterranean:**
> Editorial interior photograph for a high-end design magazine. A whitewashed house in early summer: thick warm limewash walls with gentle hand movement, an arched window with a splayed deep reveal and interior wooden shutters half open, a built-in plaster bench with sand linen cushions along one wall, a timber-beamed ceiling with reed infill, a terracotta tile floor and a flat jute rug.
> Light: 13:00, hard high sun; the shutter throws one sharp blade of light across the limewash and a terracotta pot with an olive tree; the rest of the room in cool shade; outside an overexposed glimpse of olive trees and sea.
> Camera: 26 mm at 1.0 m, shot through an arched doorway whose plaster edge frames the left and top of the picture in soft focus.
> On a linen sofa loosely draped in sand linen: square cushions in white, terracotta and moss green (moss as a 30 × 50 lumbar), the crinkled muslin throw with short fringe. On a thick oak table: the speckled ivory bowl with figs, the pair of travertine pedestal candle holders. On the deep sill: the cream clay vase with olive branches. Beside the bench: the arched iron magazine holder with cane mesh (reference) with folded magazines. Exactly one seagrass belly basket. A woven cane dome pendant with a linen lining. On the wall: the triptych (reference) of limewashed walls, olive and an arch in thin oak frames. A straw hat on the bench. No blue.

**Modern country:**
> Editorial interior photograph for a high-end design magazine. A cottage living room on a rainy morning: low ceiling with honey-oak beams, sage-grey painted wall panelling to 1.1 m with warm milk-white plaster above, a small-paned casement window with a deep sill and raindrops on the glass, wide honey-oak floorboards, a faded vintage-wash wool rug in cream, sage and soft clay rose.
> Light: 10:00, soft blue-grey rain light from the window; every pleated lamp is on and makes warm pools: a pleated fabric pendant with a brass neck, a brass floor lamp with a pleated empire shade, two small brass wall lights with pleated shades.
> Camera: 35 mm at 1.1 m, framed through an open doorway, the thick door casing soft in the foreground.
> On a natural washed-linen draped sofa with a small ruffled edge: the pair of block-print floral cushions (reference) in sage and clay rose and one tone-on-tone check cushion (reference). On a honey-oak coffee table: the sage linen runner with short fringe (reference), the speckled ivory bowl, brass chamberstick candle holders with lit tapers, two cups. On the sill: the cream clay vase with garden stems and the cream fluted column vase. Natural linen curtains. A triptych of vintage oil landscapes in thin walnut frames with ivory mats. A cardigan over the armchair. Exactly one seagrass basket by the sofa.

**Japandi:**
> Editorial interior photograph for a high-end design magazine. A quiet house at blue hour in winter: a long low ribbon window from 0.45 to 1.2 m looking onto a courtyard of stone and moss, warm grey clay-plaster walls, a dark timber slatted ceiling, a dark smoked-wood floor, a low step separating the sitting area.
> Light: 17:15, deep blue dusk outside; inside only low warm glows: the pleated paper lantern pendant (reference) and a slim paper column floor lantern on a dark wooden tripod; corners fall into shadow.
> Camera: 35 mm, low at 0.75 m, generous empty space, composition built on the horizontal of the window.
> On a low raw-linen sofa: the moss frayed cotton cushion, the ink linen-look cushion, the wabi-sabi cushion (reference), the beige-khaki gauze quilt folded in a straight line. On a low oak table: the black matte bowl and exactly two low black iron plates with pillar candles (reference), a small tea set on a tray. On the sill: the black matte stoneware jar (reference) with one branch. On the wall: the wabi-sabi tree triptych (reference) in thin matte black frames, flanked by the pair of travertine cylinder wall lights on walnut plates. An ink clay planter with an olive tree. Restraint: at least two thirds of every surface empty.

## Acceptance (every frame)
1. **The owner's eye:** a sheet of all seven frames (three finished, four new), with the current M0 v6 for comparison.
2. **QA's fidelity table per frame,** in the format of `qa/reports/2026-11-06-editorial-test-fidelity.md`:
   - for every starring product: present / faithful / partial / no;
   - **any invented look-alike is a fail.**
3. **What is not checked:** no clay lock, no box tolerances, no grading to targets. The guardrails are only no HDR, no orange-teal, and clipped highlights at most 1% outside the window.

## Token plan
| Item | Model | Tokens |
| --- | --- | --- |
| Finishing Nordic A, Nordic B, warm modern A | seedream-5-pro ×3 | 1,950 |
| Boho, Mediterranean, modern country | gpt-image-2-5 ×3 | 1,800 |
| Japandi | nano-banana-2 | 400 |
| **Total** | | **4,150** (ED2: about 4,550; 400 left) |

- **The 400 left over:**
  - one nano re-run, or
  - part of a rug-only pass, if QA marks the rug "no" in a finished frame.
- **Either way only with the manager's approval.**
- **Code fixes:** 0 tokens.

## Output
**Folder:** `assets/renders/editorial-phase-b-2026-11-06/`

**Files:**
- **The three finished frames:** `nordic-A-fin.png`, `nordic-B-fin.png`, `warm-modern-A-fin.png`.
- **The four new frames:** `boho-A.png`, `mediterranean-A.png`, `modern-country-A.png`, `japandi-A.png`.
- **`jobs.json`:**
  - placeholder ids and tokens;
  - the reference URLs;
  - the code fixes, with their scale factors.
- **`sheet.jpg`.**

**When done:** hand the sheet to qa-agent (fidelity) and then to master-designer.
