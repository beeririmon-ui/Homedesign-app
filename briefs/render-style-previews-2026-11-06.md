# Brief: five style previews of the living room, M0 1.2 (render-agent, 2026-11-06)

**Decision:** STY1 (owner, 2026-11-06; studio rules ז). Five previews, one frame per style.
**This is a test only.** Nothing from this pass goes on the site, into the slot layers or into QA'd assets.

**Composition source:** `docs/style-previews-2026-11-06.md`, sections 1–5 (palette, furniture finish, per-slot card or generic item, hero moves). This brief covers only how to render it.

**Budget:**
- 5 × seedream-5-pro image-to-image, about **650 each**.
- **3,250 at most** in total. There is no reserve: if a style fails the lock, report it and do not re-run without the manager's approval.

**Rules:**
- No other render, no commit.
- Supplier images are **view only**: pass them to the model by URL and never save them into the repo.

## Input (same for all five)
- **Base / reference 1:** the round-5b clay `assets/blockout/house/framing/round5b/M0.png`, with the product proxies at the house plan 1.2.5 points. That is the rebuilt reference 2 of the products pass, with the magazine holder at (−0.54, 2.52), box [0.335, 0.421, 0.848, 1.0].
  - If that rebuild is not done yet, do it first (0 tokens).
  - All 17 in-frame slots need a proxy. Empty slots (japandi wall decor; warm-modern and japandi runner) keep their proxy **off**.
- **Camera:** M0 1.2. C (0.83, 4.64, 1.20), yaw 25, 24 mm, u0 0.47, v0 0.50, canvas 2736×1539.
- **Product references:** at most 5 per pass (the model loses fidelity beyond that). Use the card's `images.urls[0]` in the stated option. All other slots go into the prompt as text.

| Style | The 5 reference images (by card) |
| --- | --- |
| warm modern | `framed-art-aliexpress-frameless-minimalist-wall-art-631735`, `accent-sconces-aliexpress-travertine-cylinder-walnut-choice`, `floor-lamp-cj-pleated-walnut-stem-158`, `cushions-cj-boucle-teddy` (White), `pendant-cj-tiered-fabric-drum` |
| boho | `wall-decor-aliexpress-natural-raffia-woven-bohemian-763597`, `wall-sconce-aliexpress-rattan-bamboo-wall-lamp-671943`, `planter-zendrop-seagrass-belly-basket-45`, `cushions-cj-washed-cotton-frayed` (Rust Orange), `table-runner-aliexpress-boho-macrame-table-runners-263532` |
| japandi | `framed-art-aliexpress-japanese-wabi-sabi-tree-176323`, `vase-cj-black-matte-stoneware-jar-30`, `pendant-cj-pleated-pumpkin-lantern-40`, `accent-sconces-aliexpress-travertine-cylinder-walnut-choice`, `candle-holders-aliexpress-matte-black-iron-pillar-set2` |
| Mediterranean | `framed-art-aliexpress-mediterranean-wabi-sabi-poster-802890`, `magazine-holder-cj-arch-iron-cane`, `vase-aliexpress-vintage-distressed-clay-vase-589009`, `cushions-cj-washed-cotton-frayed` (Earthy Orange), `basket-zendrop-seagrass-belly-38x34` |
| modern country | `cushions-aliexpress-farmhouse-floral-pillow-covers-166217`, `vase-aliexpress-vintage-distressed-clay-vase-589009`, `table-runner-cj-linen-look-sage-fringe` (4 Light Green), `bowl-cj-speckled-ivory-wide-bowl-21`, `basket-zendrop-seagrass-belly-38x34` |

## What changes and what must not
**Changes per style:**
- wall and ceiling colour and texture, plus the window-frame colour (warm modern only: #3A322C);
- furniture fabric and wood finish, at the same geometry;
- all 17 slot items;
- branch and plant fillers.

**Never changes (shell lock):**
- wall, window, ceiling and floor geometry;
- the floor, whitened oak #D6BF9E;
- the window view (winter, no sun, no snow);
- the camera;
- the furniture silhouettes;
- the slot positions and boxes.
- No arched window (Mediterranean), no rounded sofa arms (warm modern), no new furniture.

**Light:**
- Every lamp in frame is on: the pendant, the accent pair and the floor lamp (the floor lamp is lit in all five).
- No visible cast shadow from lamps. Only the window casts shadows.

## Prompt core (one per style; adapt to the model's format)
**Common lead:**
> Restyle this photograph of a living room as a {STYLE} interior. Keep the camera, the walls, the window, the floor, every piece of furniture and every object position exactly as in the reference layout. Change only materials, colours and the small objects listed. Winter afternoon daylight from the left window, soft, no sun. All lamps on, warm 2700 K. Matte materials. No text, no people.

**Per style (append):**
- **Warm modern:**
  > Bone limewash walls #ECE5DA with soft trowel movement; window frame dark bronze. Sofa upholstered in greige bouclé, walnut coffee table, armchair with walnut frame and bone bouclé cushions. Travertine cylinder wall lights on walnut plates glowing up and down beside an abstract triptych in walnut frames with an espresso line. Tonal cushions bone, milk-tea and camel, flax muslin throw on the right arm. Ribbed concrete planter with an olive tree, textured white stoneware vase with a dry olive branch on the sill, natural braided wool rug, jute rope basket, leather-strap magazine holder, black matte bowl and travertine candle holders on the bare walnut table, tiered fabric drum pendant, walnut floor lamp with pleated shade, round greige bouclé pouf. Plaster relief disc on the wall.
- **Boho:**
  > Chalk-cream walls #F0E7D8. Oat linen-look curtains with small tassels puddling on the floor. Earth-tone abstract triptych (arch, sun, organic shape in terracotta, sand and olive) in wood frames; raffia sun on the wall; woven bamboo ball wall lights. Washed hemp throw in raw jute draped over the sofa, rust frayed cotton cushions and an olive lumbar cushion. Seagrass belly basket with a bird-of-paradise plant and a second seagrass belly basket beside it. Flat-woven kilim rug in sand with rust diamonds. Macramé-and-jute runner, mango-wood bowl and aged-brass candle holders on the oak table. Woven rattan dome pendant and a rattan-shade floor lamp with an inner diffuser, glowing without patterned shadows. Natural knit pouf, rattan magazine basket, clay vase with dried pampas.
- **Japandi:**
  > Washi-paper walls #EFE9DF. Sofa in raw linen, armchair frame in smoked walnut with stone linen cushions. Wabi-sabi tree triptych in thin matte black frames; the wall to the left is intentionally bare. Travertine cylinder wall lights on walnut plates. Black matte stoneware jar with one branch on the sill. Pleated paper lantern pendant, a low paper column floor lantern on a dark wooden tripod. Ink clay planter with an olive tree, seagrass belly basket, light-wood folding magazine stand. On the bare oak table only a black matte bowl and two low black iron plates with pillar candles. Cushions: one moss frayed cotton, one ink linen-look, a beige gauze quilt folded in a straight line. Cream tone-on-tone striped low-pile rug, round raw-linen pouf. Restraint and empty space.
- **Mediterranean:**
  > Warm limewash walls #F1EBE0 with visible trowel movement in the raking window light. Sand linen curtains. Triptych of limewashed walls, olive branches, jars and an arch in thin oak frames; the wall to the left is bare. Travertine block wall lights. Clay vase with olive branches on the sill. Sand linen loosely draped over the sofa, cushions in white, terracotta and moss with a muslin throw. Terracotta pot with an olive tree, seagrass belly basket, arched iron magazine holder with cane mesh. Beige linen-look runner, speckled ivory bowl and travertine candle holders on the oak table. Woven cane dome pendant with a linen lining, a thin black floor lamp with a linen drum shade, a sand linen pouf, natural braided wool rug. No blue.
- **Modern country:**
  > Warm milk walls #F3ECDF. Triptych of vintage oil landscapes in thin walnut frames with ivory mats. Small antique-brass wall lights with pleated shades; a woven wicker wall basket. Natural washed linen draped over the sofa with a small ruffled edge, block-print floral cushions in sage and clay rose, a tone-on-tone check cushion; armchair with honey-oak frame and plain natural linen cushions; honey-oak coffee table with a sage linen runner, a speckled ivory bowl and antique-brass chamberstick candle holders with lit taper candles. Clay vase with garden stems on the sill. Terracotta pot with an olive tree, one seagrass belly basket, a wicker magazine basket, a piped linen pouf. Vintage-wash wool rug in cream, sage and faded rose. Pleated fabric pendant with a brass neck, antique-brass floor lamp with a pleated empire shade.

## After each pass (0 tokens, render-agent)
1. **Shell lock:**
   - `lock_v2` against the clay: shift ≤2 px, max edge ≤9.6 px on the wall, window, floor and furniture edges.
   - Floor patch (the free floor between the rug and the window wall): mean ΔE ≤3 against the Nordic frame.
   - Every slot item inside its clay box ±15%; no item outside the 17 slots.
   - **A fail is reported, not re-run.**
2. **Grading v6** (the corrected chain from `docs/render-m0-1-2-review-2026-11-05.md` §4), adapted per style as test values only. Exposure targets are B1–B6, re-based on each wall colour's L.

| Style | White balance | Black point | Saturation | Wall L target (back wall by the corner) |
| --- | --- | --- | --- | --- |
| warm modern | 4600 K (shared) | L 11–14 | −5 to −10% | 88–92 |
| boho | 4400 K (draft proposal) | as Nordic | terracotta/rust up to S 60 | 87–92 |
| japandi | 4600 K | as Nordic | as Nordic | 88–92 |
| Mediterranean | 4400 K (draft proposal) | as Nordic | terracotta up to S 58 | 89–93 |
| modern country | 4400 K (draft proposal) | as Nordic | as Nordic | 89–93 |

   - **Not allowed in any style:** orange-teal, HDR, halos.
   - **Lamps:** shades glow ≥6 L above the wall behind them. The floor-lamp pool lands on the sofa's right end.
3. **Contact sheet:** six frames in a 3×2 grid, each 1368 px wide, labelled under the frame (style name, "TEST, not for site").
   - Top row: Nordic, warm modern, boho.
   - Bottom row: japandi, Mediterranean, modern country.
   - The Nordic frame is the current graded M0 1.2 frame: the products-pass result if it has passed QA, otherwise the graded v5.

## Output
- `assets/renders/living-room/style-previews-2026-11-06/<style>-raw.png` and `<style>-graded.png` for each of: `warm-modern`, `boho`, `japandi`, `mediterranean`, `modern-country`.
- `assets/renders/living-room/style-previews-2026-11-06/contact-sheet.png`.
- `assets/renders/living-room/style-previews-2026-11-06/report.json`, with one entry per style:
  - tokens used;
  - lock_v2 numbers;
  - floor ΔE;
  - the slot boxes that moved more than 15%;
  - the reference URLs used;
  - pass / fail.
- Hand the contact sheet to master-designer for review against `docs/style-previews-2026-11-06.md`. It is then shown to the owner as a direction test only.
