# Brief: a creative review, out of the box (master-designer, 2026-11-06)

**The owner (2026-11-06), verbatim:** "טוב, משהו בזה לא עובד. היו דברים שעשיתי בעבר והיו נראים הרבה הרבה יותר וואו. כנראה שנכנסנו יותר מדי לתבנית ואיבדנו קצת מהקסם ומהיכולות של ה-AI. הייתי רוצה רגע שנצא מהקופסה ונחשוב איך אנחנו יכולים להרים את זה ממש, אולי משהו בסלון הזה לא נראה 100%. אני אשמח שנעשה איזשהו ריוויו ונראה איך אנחנו בכל כל סגנון יכול לראות קצת שונה, החלונות, משהו אחיד מדי, משהו אחיד מדי ונראה קצת פרגמטי. אני אשמח שנמצא את הדרך להקפיץ את זה באמת לרמת מגזין. זה נראה כאילו צילמנו למישהו את החדר והצענו לו כל מיני אופציות."

This is not a request for another fix. It is a request to step back and rethink the visual approach. You are the creative director for this review; everything is open, including our own rules, as long as you say which rule you would change and why.

## Look first (with Read, at full size)
- **Now:** `assets/renders/living-room/nordic/v9/m0-1-2-products-frame-fix-v6.png` (the current Nordic living room), `assets/renders/living-room/style-previews-2026-11-06/contact-sheet.png` (the five styles), `assets/renders/house-nordic-sheet-v7-2026-11-02.jpg` (the whole house, v7).
- **Earlier:** `assets/renders/living-room/nordic/styled-preview/styled-preview.png` and `step-*.png`, `assets/renders/living-room/nordic/styled-preview-r2/compare.jpg`, `assets/renders/house-nordic-sheet-2026-10-25.jpg`, `assets/renders/test-2026-09-29/`, the old gpt M0 (`assets/renders/house-nordic-v7-2026-11-02/refs/m0-v7-r2-graded-ref.jpg`), and the raw seedream and gpt renders in `assets/renders/living-room/nordic/v8/` and `v9/raw/`. Which of all our frames has the most "wow", and why?
- Our rules that shape every frame: `docs/design-bible/nordic.md` (camera 24 mm, light, grading, density), `docs/house-plan.md` (one house, fixed cameras, the clay lock), `docs/skeleton-spec.md` (the same house dressed in several styles; layers and swaps), the recipe v8 (`docs/render-recipe-nordic-v8-2026-11-03.md`), the quality gates G1 (`docs/ops/quality-gates-2026-11-02.md`), studio rules א.1 and א.6 (magazine level), and the style drafts `docs/design-bible/*-brief-draft.md`.

## The manager's hypotheses (test them, don't take them)
1. **We optimised for lockability, not for beauty.** The clay lock to the pixel, ±15% product boxes, fixed 24 mm at eye height, grading to numbers: every rule removes a decision the model is good at (light, atmosphere, composition, depth, styling).
2. **"A photo of someone's room with options":** one wide frontal wall, even daylight, every product visible and spaced out, nothing in the foreground, nothing out of focus, no human trace, no time of day. That is a real-estate or catalogue shot, not an editorial one.
3. **One shell for all styles:** the same windows, walls, floor, ceiling and proportions make the styles read as "the same room with different props". A magazine story for a Mediterranean home has arched openings, limewash and deep reveals; a modern-country one beams and panelling; a warm-modern one steel-framed glazing and plaster.
4. **Fidelity is still the rule** (CLAUDE.md: "נאמנות למוצר קודמת ליופי"), but it belongs to the products, not to the walls. Perhaps two kinds of frames: an **editorial hero frame** per room and style (free light, camera, architecture, styling, the AI at full strength; the real products shown faithfully) and the **shop frame** (locked, swappable layers).

## The task
Write `docs/creative-review-2026-11-06.md` (Hebrew) with:
1. **The diagnosis:** what exactly makes our frames read as pragmatic and uniform, with evidence from the images (name the frame and what you see). What the earlier "wow" frames had that we lost.
2. **The new direction:** your proposal for how the site's visuals should work so they reach magazine level, and how product fidelity and the swap mechanism (ו.5) survive it. Two tiers, or another idea; be concrete about what the customer sees first.
3. **Per style (Nordic, warm modern, boho, modern country, japandi, Mediterranean):** a creative concept for the living room: architecture and windows (shape, frames, reveals), surfaces (walls, ceiling, floor), light (time of day, season, weather, direction, practical lamps), camera and composition (height, lens, angle, foreground layer, depth of field), styling with life (what is open, used, draped), the one hero moment, and how it differs visibly from the other five. Describe qualities only; never copy a specific existing design or brand (Bible: forbidden).
4. **A small test plan** to prove the direction before anything else is spent: e.g. one editorial frame per style, which model and why (from what we learned: seedream holds geometry and scale, gpt-image-2-5 lights richly but enlarges furniture, nano-banana and flux options), how the products enter (references, which ones), what we let the model decide, the acceptance (the owner's eye plus a product-fidelity check, not a pixel lock), and the cost in var2 tokens (≈650 per frame at 2K).
5. **What it changes** in the binding documents (Bible, skeleton spec, house plan, recipe, gates), each as a question for the owner with your recommendation and the proposed text.
6. **Three questions to the owner** that would most sharpen the direction (for example, examples of the earlier work he means).

## Fixed rules
New files only; no edits to binding documents; no renders, no var2, no commits. Return a short Hebrew summary: the diagnosis in 3–5 lines, the new direction in 3–5 lines, one line per style, the test plan with its cost, and the owner questions.
