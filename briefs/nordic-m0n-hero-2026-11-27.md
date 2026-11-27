# Brief: the Nordic living room M0-N, in the look of the approved magazine frame (render-agent, 2026-11-27)

## The decision
- **The owner rejected the two M0-N concepts** (FB24, `docs/studio-rules.md`): "הסלון לא נראה טוב, היו תמונות הרבה יותר מרשימות של הנורדי החם".
- **The look to reach** is the approved Nordic magazine frame, `assets/renders/editorial-phase-b-2026-11-06/nordic-A-fin2.png`:
  - golden afternoon sun through tall double casements;
  - a white panelled door;
  - a window seat;
  - birches in snow outside;
  - lamps lit;
  - soft, real and calm.
- **The budget:** stage A was approved at 6,700, with 750 spent on the concepts. **This run's cap is 3,950.**

## The task: the M0-W method, applied to M0-N
1. **Start from the facts.**
   - Your M0-N clay (`assets/renders/living-room/nordic/fb23-2026-11-26/`) gives the geometry and camera.
   - Bring the clay's room and window design closer to the magazine frame: tall double casements, the panelled door and the window seat, inside what `docs/house-plan.json` allows. Say what you changed.
   - **The sun and the hour come from the magazine frame,** not the February 14:00 plan.
2. **P-N, the empty-room plate** in that light (seedream 2K, 650). The main reference is `nordic-A-fin2.png` for the look; the clay is for geometry.
3. **H-N, the hero frame** with every Nordic default product in one light (seedream 2K, 650, up to 9 SKU references).
   - **The products:** the Nordic living-room defaults in `data/slots/living-room.json`, cross-checked with the designer's approval-2 list in `docs/proposals/nordic-house-plan-2026-11-26.md`, chapter 7.
   - **Where they differ,** use the slot file's rendered defaults.
   - **For a slot with no product,** leave it empty or use filler, and say which. Don't invent products.
   - No text on magazines. Candles follow the Bible.
4. **Gate, your own check before any further spend:**
   - it reads at least as well as the magazine frame (light, depth, calm);
   - every product is true to its SKU (the rug is the real rug, no shaggy substitute; the real floor lamp);
   - the pendant is whole;
   - it reads as one photograph.

   If it fails after one retry, stop and report with the frame.
5. **Group edits** (nano 2K, 400 each) only where needed. Then the layers, by the plate split (as M0-W), and the shared finish (`assets/renders/tools/finish/`).
6. **Outputs:**
   - `plate-PN.png`, `hero-HN.png`, the layers with a manifest, and `default-frame-m0n.png` at 1920×1080;
   - `qa-sheet-m0n.jpg`, with the magazine frame next to the new tour frame;
   - a README.

## Fixed rules
- **Spend:** cap 3,950. Stop and report before going over.
- **var2:** never ask for codes. If re-auth is needed, stop and report.
- **Scope:** don't touch `data/`, `docs/`, `site/`, or warm-modern folders.
- **Git:** never `git stash`, `checkout`, `reset` or `commit`.
- **Disk:** it's tight, about 600 MB. Delete scratch as you go.
- **Your report:** a Hebrew summary of at most 8 lines.
