# Brief: a studio still for every warm-modern product (render-agent, 2026-11-28)

## The decision
- **FB29:** every product picture outside the room is a new studio photograph.
- **FB31:** the owner approved `docs/proposals/wm-studio-stills-all-2026-11-28.md`. That's 72 stills, expected 23,040, **cap 28,800**.
- **Not approved:** the 5 frozen products (the Roman blind, the three toys, the kids' pendant).

## The task
Follow the proposal exactly:
- the list, room by room, with what already has a still or gets one in wheel round 1, so nothing is made twice;
- the staging per product;
- the house spec: background, light, shadow, fill, and framing for the circle and the tile;
- batches by the route: living → kitchen → bath → bedroom → boy → girl → work.

Another render-agent is doing wheel round 1 in parallel (`briefs/wm-wheels-round1-2026-11-28.md`). Don't touch its slots. Its studio stills are in the same folder and manifest, so before each batch, re-read the manifest and skip any product that already has a still.

1. **Before spending on a product, check faithfulness** from the SKU photos and the card. The photos are in `site/.cache/supplier-images/` or the card URLs; keep them in your scratch folder and read them with `python3.12 -I`.
   - Sets are shown as the set, so check what's in each one: the bedding, the niche set, the carafe, the cutting board, the diffuser and the girl's prints.
   - Check whether the sconces are sold one or a pair.
   - An unclear product is skipped and listed, not guessed.
2. **Render** in the FB20 look (`assets/renders/wheel-studio/warm-modern/`, the same light, angle and fill).
   - No halo or light rim, and no glow spill on the background.
   - Lamps are lit, with the light kept inside the lamp.
   - The product is whole, and textiles are folded.
3. **Write each still** to `assets/renders/wheel-studio/warm-modern/<room>/<slot>/<card id>.png` and `.webp`, and add it to that folder's `manifest.json` with the same schema. The site picks them up from there; `site/.generated/studio-missing.json` lists what it still lacks.
4. **After the living-room batch:** stop and report with a contact sheet. The owner sees it before you go on.

## The gate
Your own eye at ×1 and ×2 against the SKU: true to the product, no halo, whole, and the same look across the house.

## Outputs
- the stills and the manifest entries;
- a contact sheet per batch, in your scratch folder;
- the spend in `assets/prompts/wm-stills-2026-11-28/jobs.json`.

## Fixed rules
- **Spend:** cap 28,800. Stop and report before going over.
- **var2:** never ask for codes. If re-auth is needed, stop and report.
- **Supplier pixels:** never in a still or a committed file.
- **Scope:** don't touch `data/`, `docs/` or `site/`.
- **Git:** never `git stash`, `checkout`, `reset` or `commit`.
- **Your report, after each batch:** at most 4 lines, with the spend, your eye check and the sheet path.
