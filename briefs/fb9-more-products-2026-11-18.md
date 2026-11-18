# Brief: FB9, more products in the bedroom and the bathroom (master-designer, 2026-11-18)

## Why
The owner saw MB0 and B2 for approval 3 and did not approve them as they are. FB9, now in `docs/studio-rules.md` and the digest:

> "יש לי שאלה, המצעים והציפיות של הכריות והטרו בלנקט הם גם חלק מהמוצרים שלנו, נכון? וגם הייתי מוסיף איזה תמונה או מדף שיהיה מקום להכיל עוד קצת מהמוצרים, ואולי גם אופוף או איזה מחזיק עיתונים או משהו. חסר פה מוצרים, זה נראה ריק... צריך להיות פה לפחות אמרנו 7-10 מוצרים בכל סצנה, והם נראים קטנים, הם לא לוקחים את כל ההצגה. אז כאילו בואי ננסה או למצוא עוד מוצרים, לשים עוד תמונה או איזה מדפון עם עוד כמה דברים, שיהיה עוד מוצרים."

The manager reads it this way:
1. Every tour scene must look full of products, with **at least 7–10 products that read clearly**. The studio minimum (ג.2) is 14 in a "full" room (the bedroom) and 11 in a "lean" room (the bathroom), counted per V7Q6.
2. The products must **take the stage**: large and clear in the frame, not small dots.
3. The owner names a picture, a small shelf with a few items, and a pouf or a magazine holder.
4. The warm-modern "few objects" doesn't override this in the tour.
5. The approved stage-one base stays (the plate, and the defaults that passed QA). New products are added as new layers on it.

## What to write (0 tokens), one designer per room
A dated section "FB9: עוד מוצרים" in your room's render document:
- **The bedroom:** `docs/proposals/wm-master-bedroom-render-2026-11-17.md`.
- **The bathroom:** `docs/proposals/wm-bath-render-2026-11-17.md`.

Cover:
1. **The count now,** per V7Q6, in the current frame (MB0 or B2), product by product, and the target.
2. **The additions,** enough to reach the target. For each new product slot give:
   - the slot (from `data/slots/<room>.json`, or a new slot proposed for the 1.3.9 registration);
   - its exact place in the plan and in the frame (u, v);
   - its size;
   - why it makes the products read bigger or more present.
   For the bedroom, consider:
   - a large picture above the bed (the picture slot, a gap you left open);
   - a small wall shelf or ledge with 3–4 items;
   - a pouf or a magazine holder;
   - a rug that shows on both sides of the bed;
   - a basket;
   - a plant.
   For the bathroom, consider:
   - the towel ladder with towels;
   - the stool;
   - a basket on the vanity's open shelf;
   - a small shelf or a picture.
   Respect the house language and the rejection list. Nothing may hide the hero products.
3. **The products:** score the existing cards first, including the pools (`data/products/pouf/`, `magazine-holder/`, `framed-art/`, `rug/`, `basket/`, `planter/`, and the room's own folders). Give a default per new slot, and list the gaps for sourcing with a spec. Use only products whose SKU photo you can judge. The picks sheets and the photos are in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/`; ask for photos you need through the manager.
4. **"Taking the stage":** besides adding products, say whether anything in the light or the reveal (the line of light that brings the products, B), or in the framing, should change so the products read larger. Any camera change is a 1.3.9 registration item. Mark it as a proposal, and keep the current frame as the baseline.
5. **How to render it** (for render-agent): new layers on the approved base, as mask edits per product or grouped, with an estimated cost at list prices (nano 400 per edit, seedream 650).

## Inputs
- The room's render document (all chapters, especially the slot picks and the latest rulings).
- The QA reports: `qa/reports/2026-11-18-master-mb0/` or `qa/reports/2026-11-18-bath-b2/`. Their counts are in the JSON.
- The frames:
  - `assets/renders/master/warm-modern/stage1-2026-11-17/mb0-defaults-frame.png`;
  - `assets/renders/bath/warm-modern/stage1-2026-11-17/b2-defaults-frame.png`.
- `data/slots/master.json` or `bath.json`, the cards, and `docs/design-bible/warm-modern.md`.
- The digest: FB5, FB6, FB9, ג.2, V7Q6.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's document.
- Write in stages.
- Return a short Hebrew summary: the count now and the target, the added slots with their defaults, the gaps for sourcing, the "take the stage" proposal, and the estimated render cost.
