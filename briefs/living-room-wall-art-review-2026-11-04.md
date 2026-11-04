# Brief: the living-room hero wall, Nordic (master-designer, 2026-11-04)

**The owner (2026-11-04):** "אבל אספנו מלא מוצרים לקיר של הסלון לא?" When told that only one card (the geometric triptych, Nordic 8) passes for the Nordic hero wall and its card is incomplete (RND2), the owner chose: **"קודם שהמעצב יבדוק עוד תמונות"** — before the triptych goes back into the frame, review the other art we collected.

## Context
- The wall above the sofa in M0 is the room's focal point and the required charcoal carrier (`data/selections/living-room.nordic.ranking.md` §framed-art and its line 158; Bible `docs/design-bible/nordic.md`, framed-art and charcoal rules).
- The slot `framed-art` in `data/slots/living-room.json` 1.6, at the new camera M0 1.2 (house plan 1.2.3): read its envelope and frame box. Your spec in the ranking (line 137): a 70×100 portrait pair, a 50×70 triptych or a single 100×150; soft abstract, line drawing or misty landscape, with a charcoal element; light oak or matte black frame.
- RND2 (answered): the triptych `framed-art-aliexpress-minimal-geometric-triptych-prints` as the default "after the card is completed and the rights cleared". Its card lacks a consumer price, a verified shipping line and rights; the store has one review.

## The cards to review (all of them, not only the living-room folder)
- `data/products/framed-art/` (7): the triptych (Nordic 8 in its notes), the CJ Morandi triptych (6.5), and five AliExpress DS drafts collected for other styles (boho palm arch pair, boho terracotta-sage trio, **japandi bare branch 70×100 pair, no Nordic score**, japandi wall-art set 5.5, Mediterranean wabi-sabi poster 4.5).
- `data/products/wall-decor/` (9).
- Art in the other rooms that could carry this wall in a larger size or as a set: `master/framed-art/` (black ink abstract wide-mat pair 50, no score), `corridor/gallery-art/` (7, incl. black ink abstract wide-mat set of 3, no score), `entrance/framed-art/` (line scribble white mat 50, 6.5), `dining/framed-art/` (swinging line black frame mat 8.0 at 35×45; taupe block 7.5), `work/framed-art/` (misty landscape, beige reed hills, vintage sketch, no Nordic scores), `kids/framed-prints/`.
- Look at the images (each card's `images.urls`; download and view them), not only the notes.

## The task
1. **Score every unscored or under-reviewed card for the Nordic living-room hero wall** with the interior-design-rules rubric, against the Bible and your own spec: subject, palette (the charcoal element), frame, mat, size or the size the supplier also sells (check `options`), and whether it reads as "magazine" at the new camera's scale.
2. **A ranked shortlist of up to 5** for this wall, each with: the card, the size and variant to use, the score and why, what the card is missing before sale (price, shipping, rights, stock), and whether it can be rendered for the test now.
3. **Your recommendation for the test frame:** one choice, plus whether the triptych stays the default for sale (RND2) or something else replaces it. If the best option needs a card that doesn't exist yet, write the sourcing spec instead (sizes, search terms, sources); sourcing waits for API keys.
4. **The second wall slot** (`wall-decor`): one line on whether any card now passes for the test.

## Output
`docs/rooms/living-room-wall-art-2026-11-04.md` (Hebrew): the scored table of every card you looked at, the shortlist, the recommendation, and the question for the owner (a new decision id `RND3`) with options and your recommendation.

## Fixed rules
- New file only; no edits to cards, slots, the Bible or any binding document. No renders, no var2, no commits.
- Return a short summary in Hebrew: the top 3 with scores, your recommendation for the test, and the RND3 question.
