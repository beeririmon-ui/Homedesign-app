# Brief: 20 products in each existing room of the warm-modern house (master-designer, 2026-11-19)

## Why
The owner (FB11, in the digest):

> "בואי נמשיך לכל החדרים, ננסה להגיע ל20 מוצרים בחדר ולא 11, וכשהכל יהיה מוכן נייצר מעברונים"

- **The target:** at least 20 products for sale in every tour room. More is better (FB10). They must "take the stage" (FB9).
- **The approvals:** AP3-HOUSE2 is read as yes for the bedroom and the bathroom, including a second frame in each (MB1, B1).
- **The transition clips** between rooms wait until every room is ready.

This brief covers the rooms that already exist in this style. Two other designer runs, in parallel, cover the kitchen and dining with the work room, and the two kids' rooms.

## The rooms in this brief
1. **The living room (M0).** It has 16 products for sale today; the tour's count chip reads 16, with the cushion set as 4. Reach 20 or more: what to add in M0, and whether a second frame is needed. The selections are in `data/selections/living-room.warm-modern.json` and `data/slots/living-room.json`. Keep the approved R9 base.
2. **The entrance hall** (the junction, the stills HT2, HDx2, HC and HC130, and the door D0). Today its stills show the bench and the console with almost no products for sale.
   - **Slots:** `data/slots/hall.json` has 16 slots, and cards exist in `data/products/entrance/`.
   - **The route:** chapters 2, 11 and 12 of `docs/proposals/wm-tour-route-2026-11-17.md`, and `docs/proposals/wm-entrance-magazine-2026-11-15.md`.
   - **To decide:** which frame is the hall's product frame (HDx2, HT2, or a new one), and how it reaches 20.
   - **The arrival:** it passed QA and must not break. The products are added to the rest still, and the clips are re-cut later with the other transitions (FB11).
3. **The corridor (C0, "the light gallery"):** `data/slots/corridor.json` has 5 slots, and cards are in `data/products/corridor/`. Say honestly whether 20 makes sense in a 10.8 m² corridor. If not, propose the best full version and say why. The owner decides.
4. **The bedroom:** MB0 has 19, and MB1 is the second frame (chapter 13 of `docs/proposals/wm-master-bedroom-render-2026-11-17.md`).
   - Confirm the MB1 product list and the count.
   - **The bench:** the Ears 02 bench has no image URLs, so pick a bench whose SKU photo you can judge.
   - Name any gaps.
5. **The bathroom:** B2 has about 12, and B1 is the second frame (chapters 0א and 12 of `docs/proposals/wm-bath-render-2026-11-17.md`). Reach 20 across B1 and B2, and list the gaps: the stool, the small print, the plant, the jar, the vase, the mat and others.

## For each room, write
- **The count now:**
  - each product counts once per room, in the frame or close-up where it's biggest;
  - also say how many pass V7Q6 visibility.
- **The additions to reach 20 or more,** per slot:
  - the slot (existing, or a new one for the 1.3.9 registration);
  - the frame;
  - the place (plan and u,v);
  - the size;
  - the default card.

  Use existing cards first: the room's folder and the pools in `data/products/`. Use only cards whose SKU photo you can judge. The photos and sheets are in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/`. Ask the manager for others.
- **A second frame, if needed:** the camera, what it shows, and why. Every new camera is a 1.3.9 item.
- **The gaps for sourcing:** one line per gap, with the spec, the size, the tone and the material, and 6–10 candidates wanted. Israeli stores first for furniture and textiles.
- **The render plan,** at list prices (seedream-5-pro 2K 650, nano 400 per edit). Mark what can be done in code.
- **The order:** which room first. Suggestion: the bedroom MB1 and the bath B1 (closest to done), then the living room, then the hall, then the corridor.

## The output
- **The new document** `docs/proposals/wm-house-20-2026-11-19.md`:
  - a summary table first: room, count now, target, frames, gaps, cost;
  - then a chapter per room;
  - a final chapter, "for sourcing", that merges every gap line from all rooms.
- **Write in stages.** The context is large.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's documents.
- Respect:
  - `docs/design-bible/warm-modern.md` and its rejection lists;
  - fidelity before beauty;
  - IKEA only as a marked alternative;
  - framed art only with stated image rights (PR1);
  - nothing hides a hero product.
- Return a short Hebrew summary: the table, the gap count, the total estimated cost, and the order.
