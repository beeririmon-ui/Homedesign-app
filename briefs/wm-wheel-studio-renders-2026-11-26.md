# Brief: studio images for every product wheel (render-agent, 2026-11-26)

## The decision
The owner approved this on 2026-11-26 (FB20, FB20-S, `docs/studio-rules.md`): **expected about 5,250, cap 7,000.**

The principle: in the wheel the product appears **as it is sold**, for example a folded throw or a cushion standing, on a uniform studio backdrop. In the room it appears in use.

## The wheels (warm-modern)
Find each wheel's options in `data/slots/<room>.json` (`sample_slot`) and the cards:
- **living room:** the cushion sets B, A and C, each a set (cushions plus throw) as one composed studio still;
- **bath:** the hand towel;
- **dining:** the dining pendant;
- **kids:** the bedspread or throw, boy and girl;
- **master:** the throw;
- **work:** the framed art.

About 21 variants. List the exact set first, and stop to report if it's far from 21.

## The studio standard (one look for all)
- **Backdrop:** a warm off-white seamless backdrop, L\* about 92, b\* 6–8, matching the house hour. Soft key light from upper left, with a gentle contact shadow.
- **View:** the same three-quarter view from about 30° above, the product centred, filling about 70% of a square.
- **Fidelity:** true to the SKU (shape, colour, texture, proportions), from the card's SKU images as references. The supplier photos stay in the scratchpad, and no supplier pixels go into the output. Textiles are folded neatly, lamps are lit, and framed art is upright and front-facing.
- **Model and size:** flux-2 1K (about 250), square 1024×1024. Use nano 2K only where 1K can't hold the texture, with a reason.
- **Output:** per variant, `assets/renders/wheel-studio/warm-modern/<room>/<slot>/<variant-id>.png`, plus a 512-px webp, and a `manifest.json` that maps the variant id to the card and SKU.
- **The sheet:** `assets/renders/wheel-studio/warm-modern/sheet.jpg`, all variants in one grid, labelled.

## Checks
- Per image: an ΔE00 check of the main colour against the SKU reference, plus your eye at ×1.
- Re-roll anything off. One retry per image, within the cap.

## Fixed rules
- **Spend:** cap 7,000. Stop and report before going over.
- **var2:** never ask for codes. If re-auth is needed, stop and report.
- **Don't touch:** `data/`, `docs/`, `site/`, or room render folders. Other agents are working in the living room and on the site.
- **Git:** never `git stash`, `checkout`, `reset` or `commit`.
- **Disk:** it's tight; delete scratch.
- **Work economically.**
- **Your report:** a Hebrew summary of at most 8 lines.
