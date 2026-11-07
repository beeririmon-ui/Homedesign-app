# Brief: the design line across the house, tested on the master bedroom (master-designer, 2026-11-07)

**The owner (2026-11-07):** "וגם עבדנו על הסלון מלא איך קו העיצוב משפיע על שאר החדרים?? בא נבדוק השוואה של חדר שינה מאסטר". Under studio rule ז, "זרימה בלי עצירות", don't wait on anything. The render spend for the comparison is queued for the owner as MB1. This brief prepares everything that is free, so the frames can run as soon as MB1 is answered.

## The inputs
- **The new line:** `docs/creative-review-2026-11-06.md` §2–§3, the story concepts per style. Also `docs/design-bible/nordic.md` 1.9.1 (story chapter), `docs/design-bible/warm-modern.md` 1.0, the recipe `docs/render-recipe-story-v1-2026-11-07.md`, and the G-ED gate.
- **The approved living-room frames:** Nordic A/B and warm modern ed5, in `assets/renders/editorial-phase-b-2026-11-06/`.
- **The master bedroom as it is today ("before"):**
  - the frame `assets/renders/master/nordic/v7/mb0-v7-r2-graded-v5.png`, from the old locked pipeline;
  - the room assembly `docs/rooms/master-nordic-2026-10-11.md`;
  - house plan 1.3.3, the master room;
  - the products in `data/products/master/` (80 cards across 17 slots).

## Task 1: the design line across the house, `docs/design-line-across-rooms-2026-11-07.md`
DIR2 says each style is its own house. So one story per style has to run through all of its rooms. Cover:
- **What carries from room to room** within a style: the architecture vocabulary (windows, frames, ceilings, floors, walls), the palette and materials, the light story, the camera language, the styling, the density rule.
- **What changes per room:** each room's hero moment, its time of day and its mood.
- Light for each room, consistent with BIB2 (living > hall > corridor) or a replacement for it in the story layer.
- One short paragraph per room per style is enough for now. Go deeper only for the master bedroom.

## Task 2: the master bedroom, concept and comparison
1. **The diagnosis of MB0 v7:** what makes it read "pragmatic" by the same criteria as your §1 diagnosis of the living room. Name what you see in the frame.
2. **A story concept for the master bedroom, Nordic and warm modern:** architecture, surfaces, light (time of day), camera, styling with life, the hero moment, and how it links visibly to the same style's living room.
3. **The starring products per style:** card ids from `data/products/master/`, with scores, and the gaps.
   - Use the rejected re-check where it helps.
   - The density is 10–14 products in 3–4 islands.
   - Where a card is missing, give a generic, non-product item with a note, never an invented product.
4. **A ready-to-run render brief,** `briefs/render-master-editorial-2026-11-07.md`. Per recipe story v1, one wide frame per style (Nordic, warm modern):
   - your choice of model per style, with the price per frame;
   - the full English prompts;
   - the reference list (card crops), and what we let the model decide.

   Base frames only in this first comparison; fidelity passes come after QA, per the recipe. **The cap is 1,300 for the two base frames.** If your model choice costs more, say so; that is the owner's call in MB1.

## Fixed rules
- New files only. No edits to binding documents in this brief; if the design line needs one, list it as a question with a recommendation.
- No renders, no var2, no commits.

Return a short Hebrew summary:
- the design line in 5 lines;
- the MB0 v7 diagnosis in 3 lines;
- one line per style for the master concept;
- the starring products and gaps;
- the render brief and its cost;
- questions, each with a recommendation.
