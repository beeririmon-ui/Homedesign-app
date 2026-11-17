# Brief: the warm-modern master bedroom, stage one, MB0 (render-agent, 2026-11-17)

## Why
The owner asked for the warm-modern bedroom and bathroom to be rendered in parallel, so the style has one complete house (HOUSE, 2026-11-17). They approved the budget: "כן כמה קרדיט שיעלה להגיע לתוצאה טובה" (HOUSE1). master-designer wrote the bedroom in `docs/proposals/wm-master-bedroom-render-2026-11-17.md`. **Chapter 12 overrides the earlier chapters** wherever they differ: the bed of the magazine frame, the throw as the sample slot. The bathroom plate is done (`assets/renders/bath/warm-modern/stage1-2026-11-17/plate.png`). Match its house language.

## Your sources
- **The architecture:** chapter 1. **The fixed furniture** (the walnut bed and nightstands, not sold): chapter 2.
- **The picks:** 3.2, with the changes in 12.2. **The sample slot:** chapter 12.3. The throw is in three colours of one muslin card: Pecan `CJYD205807508HS` (the default), Flax brown `CJYD205807538LO` and Clay `CJYD205807510JQ`.
- **The scene brief:** chapter 6 (6.1 the order, 6.2 the camera and canvas, 6.3 the frame, 6.4 the light, 6.5 each product, 6.6 the plate prompt, 6.7 the default scene, 6.8 the filler).
- **The rejection list:** chapter 7. **What QA checks:** chapter 9.
- **The plan:** `docs/house-plan.json`, room "master" and camera MB0; and `data/slots/master.json`. The 1.1 clay of MB0 is in `assets/blockout/house/framing/` (MB-A, MB-B).
- **The house language:** the warm-modern living-room `base.png` and its layers, the hall stills, the bathroom plate, and the bedroom magazine frame fix6 (`assets/renders/master/editorial-2026-11-07/`), for the bed styling only.
- **The bar:** FB5, the warm-modern living-room magazine frame. FB6: lived-in, not a hotel. Product fidelity before beauty.

## The order
1. **The warm-modern clay for MB0, now (0 tokens):** the architecture, the fixed furniture, and the products as boxes at their slot envelopes. Add passes, a lock target and a self-check of the composition numbers in 6.3, as you did for the bathroom.
2. **Price the outputs** with `var2_estimate_cost` (SPEND2): the plate, MB0 with the defaults, and two throw variants as mask edits.
3. **Send the plate now** (the empty room, the fixed furniture and their shadow). It has no products, so it doesn't wait for owner approval 2.
4. **The defaults and the throw variants wait** until the manager relays owner approval 2 (HOUSE2). Then send them in order, and make the product and light layers in masks (RND2), as in the living room.

## Money
- **The working cap for this run is 3,500.** A fix is allowed only for something visible at ×1–×2 or a product mismatch (EFF1). If a good result needs more, stop at 3,500 and report.

## Outputs
- **The clay:** `assets/blockout/house/framing/wm-master-2026-11-17/` (with a README).
- **The renders:** `assets/renders/master/warm-modern/stage1-2026-11-17/`: the plate, then MB0 with the defaults, the variants and the layers, the lock record, `jobs.json`, and a README with the rejection-list result and what QA should look at.
- **The prompts:** `assets/prompts/warm-modern-master-2026-11-17/`.
- Update `assets/manifest.json`. Working files go in the scratchpad (EFF1).

## Fixed rules
- Tokens only for these outputs, inside the cap. Nothing of the bathroom or the clips.
- No commits, no keys, never ask for codes. Don't edit a binding document, `data/`, or another agent's document.
- Return a short Hebrew summary: the clay (and any composition number that doesn't hold), the prices, what was sent, the plate's path, model, tokens and rejection-list result, the total, and what's open.
