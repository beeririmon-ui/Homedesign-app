# Brief: three tasks for the living room (master-designer, 2026-11-06)

**The owner (2026-11-06):** "ואולי צריך מדף עם קצת אביזרים? אשמח להדמיות מסגנונות אחרים, הכפרי, בוהו, מודרני חם ועוד". Decision STY1 (answered): five style previews, one frame each, test only. Recorded in `docs/studio-rules.md` (ז, 2026-11-06) and `status/decisions.json`.

## Task 1 (first, it blocks a paid pass): the magazine holder hides the basket
render-agent built reference 2 for the products pass (`assets/renders/living-room/nordic/v9/m0-products-pass-ref2-clay.png` + `.json`) and stopped before paying: at house plan 1.2.4 the holder's box [0.345, 0.411, 0.774, 1.0] covers the lower 38% of the basket's box [0.350, 0.401, 0.686, 0.822]; the sides nearly coincide, so the basket reads as standing on the holder. Rotating the holder doesn't help; there is no room right of it up to the table. Decide within your authority (M0S2 approved moving both): move the basket or the holder, or accept the overlap explicitly as layers. Update house plan 1.2.5 and slots 1.8 with dated notes, and correct the products-pass brief (`briefs/render-m0-products-pass-2026-11-05.md`): boxes in uv only (its px column used u×2736, wrong for the canvas), and the pouf at filled height 36 starts at v 0.956, not 0.915.

## Task 2: a shelf with accessories (proposal for the owner)
Where could a shelf (wall shelf, low console or ledge) carry a styled group of 3–5 accessories in M0 1.2 without crowding the hero wall, the window or the sofa? Check the clay and the projection, the Bible's living-room layout and density (S11), and the products we already have for shelves and small accessories (search all of `data/products/` for cards with Nordic ≥ 7: books, bookends, small vases, candles, boxes, trays, small plants). Give one or two placements with the shelf type and size, the 3–5 accessories (card ids, scores), what it adds to the frame, and what it costs (a new slot means a change to the slots file and the Bible; one more product pass, or the same pass if it is not run yet). End with the owner question `SHF1` and your recommendation.

## Task 3: five style previews of the same living room (STY1)
For each of **warm modern, boho, modern country, japandi, Mediterranean**: one M0 1.2 frame, same camera, same clay (round 5b), same shell (walls, window, floor), restyled. Read each style's draft (`docs/design-bible/*-brief-draft.md`) and `docs/proposals/style-pools.md`. For each style write a compact composition brief that render-agent can turn into one seedream-5-pro pass:
- the palette and materials in a few lines (wall colour may change only if the draft says so; the floor stays as the style pools say);
- per living-room slot that is in frame at M0 1.2: the card with the best score in that style (≥ 7 where one exists; say where you fall back to a lower score or to "generic, not a product"), with its card id and reference image;
- the furniture: keep the Nordic sofa, table and armchair unless the style draft requires otherwise, and say which;
- what makes it read as that style at first glance (2–3 hero moves);
- an honest note where the catalog is too thin (japandi 3 cards, Mediterranean 4, modern country 7 at ≥ 7), so the preview will lean on generic styling.
Output: `docs/style-previews-2026-11-06.md` (one section per style) and a short render brief `briefs/render-style-previews-2026-11-06.md` for render-agent: one seedream-5-pro image-to-image pass per style on the round-5b clay with M0 1.2's camera, ~650 each, ≤ 3,250 total, the same shell-lock check, grading v6 adapted per style, a contact sheet of the five plus the Nordic frame. Test only, not for the site.

## Fixed rules
Binding documents only where Task 1 says. New files otherwise. No renders, no commits. Return a short Hebrew summary: the Task 1 decision with the new boxes, the shelf proposal and SHF1, and one line per style with its hero moves and catalog strength.
