# Brief: MOCK4, the house tour with the new arrival, the bedroom and the bathroom (frontend-dev, 2026-11-18)

## Why
The owner asked: "תראי לי את האתר שהגענו עד כה". The latest site preview is MOCK3 (`83ae7bb8`, 2026-11-13, published privately for the owner). It shows a temporary door, the warm-modern living room with the R9 layers, three reveals, the close-up and wheel, and the style change. Since then, three new pieces have passed QA, all of them temporary and for the owner only:
- **The arrival v2:** from the door through the hall to the living room, one flowing walk, always facing forward (FB7, FB8).
- **The bedroom MB0:** stage one plus FB10, with 19 products for sale.
- **The bathroom B2:** stage one plus FB10.

The owner should see one tour with all of it. The run costs 0 tokens.

## What to build (behind `HD_PUBLIC=0`; the public build has no tour, as today)
1. **The arrival:**
   - Replace MOCK3's temporary door-to-living-room move with the arrival v2: `assets/video/transitions/warm-modern/arrival-v2/`. Read its README, `segments.json`, `camera.json` and `manifest.preview.json`.
   - Use the `.clean` masters, and draw the labels in HTML at the rest on HC, from the anchors in the README (ARR-M1). The bath is at 0.3944–0.4114, the bedroom is centred at 0.496, and the laundry has no label. If that is too heavy, the `.ui` version is the fallback; say which you used.
   - Per FB8 (route ch. 11.1), the first arrival has labels and "דלג", and no buttons.
   - **Encode for the web:**
     - desktop: no more than 8 MB, 60 fps if it fits, otherwise say what you chose;
     - phone: no more than 3 MB;
     - each file under 15 MB, the artifact's limit.

     The masters in the repo stay untouched.
   - It lands on M0 with reveal B, exactly as today.
2. **Two new rooms in the tour,** the bedroom and the bathroom, warm-modern, built from the layers:
   - **The folders:** `assets/renders/master/warm-modern/stage1-2026-11-17/` and `assets/renders/bath/warm-modern/stage1-2026-11-17/`. Each has `layers/`, `shadows/`, `light/`, `layers/manifest.json` and the compose JSONs.
   - **The engine:** the same as the living room. Shadows multiply, light is screen, and z comes from `data/slots/master.json` and `bath.json` or the manifests. The rested frame must match the defaults PNG to the pixel, as in MOCK1.
   - **A product dot** for each product for sale, from the cards in `data/products/master/`, `data/products/bath/` and the pools the manifests name.
   - **The close-up and wheel** on each room's sample slot:
     - the bedroom: the throw in 3 variants (`mb0-variant-throw-flax/clay`);
     - the bath: the hand towel (`b2-variant-linen/khaki`).

     The fixed items (the bed, the nightstands, the vanity, the wall shelf) get no dot.
   - **The rights rule:** the large framed art 776445 above the bed has unclear rights. It is ×1 only: a dot and a product page are fine, but no close-up or zoom of it.
3. **Room buttons** after the arrival: living room, bedroom and bathroom.
   - There are no clips between these rooms yet. Use a short temporary fade, not a zoom-in, which rule ו.6 forbids. Mark it in the code as temporary, to be replaced by the T-C* clips.
   - Keep the mini-map or labels from route ch. 5 only if they are cheap. Otherwise list them as next.
4. **The count:** in each room, a small temporary line or chip for the owner: "X מוצרים למכירה בחדר".

## Inputs
- **The route:** `docs/proposals/wm-tour-route-2026-11-17.md`, chapters 5 and 11 (11.1 and 11.2).
- **MOCK1–3:** `briefs/site-mock1-wow-tour-2026-11-12.md`, `site-mock2-smooth-wheel-2026-11-13.md` and `site-mock3-whole-frame-2026-11-13.md`, and the code in `site/`.
- **The QA reports:**
  - `qa/reports/2026-11-18-arrival-v2/`;
  - `qa/reports/2026-11-18-master-mb0/` and `2026-11-18-master-fb10/`;
  - `qa/reports/2026-11-18-bath-b2/` and `2026-11-18-bath-fb10/`.
- `docs/skeleton-spec.md` for the layers, and `data/product-card.schema.json`.

## Outputs
- **The artifact:** `site/dist-artifact/`, rebuilt with `npm run preview:artifact`, with `check-artifact` passing. The manager publishes it to the owner's existing private page. **Don't publish it yourself.**
- **Screens:** at 1280 and 400 (`npm run screens:artifact`, or your own), covering the arrival's rest on HC, each room at rest, the bedroom close-up with the wheel, and the bath close-up.
- **A short section** in `site/README.md` or the MOCK notes: what is new, and what is temporary.
- **The checks:** typecheck, lint, vitest, the affected e2e tests, a11y on the tour pages, the budget, and both builds, with the numbers. Note anything not verified (for example, a real phone's fps).

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or the render and video masters.
- Supplier images only as FR-I already does: product pages, copied next to the page. The artifact stays private for the owner, and isn't shared with stores.
- Never `npx` without `--no-install`. Don't run `playwright install`.
- Return a short Hebrew summary covering:
  - what the owner will see, step by step;
  - the file sizes;
  - the checks;
  - what is temporary;
  - what is next.
