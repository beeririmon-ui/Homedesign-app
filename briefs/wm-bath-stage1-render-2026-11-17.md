# Brief: the warm-modern bathroom, stage one, B2 (render-agent, 2026-11-17)

## Why
The owner asked for the warm-modern bedroom and bathroom to be rendered in parallel, so the style has one complete house (HOUSE, 2026-11-17). They approved the budget: "כן כמה קרדיט שיעלה להגיע לתוצאה טובה" (HOUSE1). master-designer wrote the bathroom: `docs/proposals/wm-bath-render-2026-11-17.md`. The hero frame is **B2** (the vanity wall). Stage one is B2 only; B1 comes after owner approval 3.

## Your sources
- **The architecture:** chapter 1 (and 2 for what changes against the plan; render the warm-modern version, the registration comes later).
- **The scene brief:** chapter 7 (7.1 the three outputs in order, 7.2 the camera and canvas, 7.3 the composition, 7.4 the layers, 7.5–7.10).
- **The rejection list:** chapter 8. **What QA checks:** chapter 9.
- **The picks:** 4.1. **The sample slot:** chapter 5 (the hand towel, three SKUs).
- **The plan:** `docs/house-plan.json` (room "bath", camera B2 from CB), and `data/slots/bath.json`. The 1.1 clay of B2 is in `assets/blockout/house/framing/round2/`.
- **The house language:** the warm-modern living room (`assets/renders/living-room/warm-modern/phase2-2026-11-10/layers/base.png` and its layers) and the approved door stone (`assets/renders/hall/warm-modern/door-2026-11-16/d0.png`).
- **The bar:** FB5, the warm-modern living-room magazine frame. FB6: lived-in, not a resort. Product fidelity before beauty.

## The order
1. **The warm-modern clay for B2, now (0 tokens):** the architecture of chapter 1 on the plan geometry, the fixed vanity, and the products as boxes at their slot envelopes. Add passes and a lock target as you did for the hall. Check every composition number in 7.3 on the clay, and say if one doesn't hold.
2. **Price the three outputs** with `var2_estimate_cost` (SPEND2), as you would write each job.
3. **Send only when both of these are true:**
   - (a) var2 is connected. It needs re-authorising now. If it isn't connected, stop after step 2 and report. Never ask for codes or tokens.
   - (b) The manager has relayed the gates from sourcing-agent: the travertine sconce dimensions (or the switch to the backup `…430468`), and the floor planter Medium. Without (b), the empty plate (output 1) may go, because it has no products. The defaults wait.
4. **Then, in order:** the empty plate → B2 with the defaults → the two towel variants (mask edits). Then the product and light layers in masks (RND2), as in the living room.

## Money
- **Estimate:** about 1,850–2,250 for the three outputs (the designer, by the price list). A fix is allowed only for something visible at ×1–×2 or a product mismatch (EFF1).
- **The working cap for this run is 3,500.** If a good result needs more, stop at 3,500 and report what is left and why. The owner approved more, but the manager reports it.

## Outputs
- **The clay:** `assets/blockout/house/framing/wm-bath-2026-11-17/` (with a README).
- **The renders:** `assets/renders/bath/warm-modern/stage1-2026-11-17/`: the plate, B2 with the defaults, the variants, the layers, the lock record against the clay, `jobs.json`, and a short README with the rejection-list result and the frame ranges for QA.
- **The prompts:** `assets/prompts/warm-modern-bath-2026-11-17/` (the sent text, next to the designer's text if you had to shorten it).
- Update `assets/manifest.json`. Working files go in the scratchpad (EFF1).

## Fixed rules
- Tokens only for these outputs, inside the cap. Nothing of the bedroom or the clips.
- No commits, no keys. Don't edit a binding document, `data/`, or another agent's document.
- Return a short Hebrew summary: the clay (and any composition number that doesn't hold), the prices, what was sent (or why not), per output the path, model and tokens and the rejection-list result, the total, and what's open.
