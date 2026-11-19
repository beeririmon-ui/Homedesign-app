# Brief: the warm-modern boy's and girl's rooms, with 20 products each (master-designer, 2026-11-19)

## Why
The owner (FB11, in the digest):

> "בואי נמשיך לכל החדרים, ננסה להגיע ל20 מוצרים בחדר ולא 11, וכשהכל יהיה מוכן נייצר מעברונים"

Every tour room of the warm-modern house gets at least 20 products for sale. More is better (FB10), and they must "take the stage" (FB9). The two kids' rooms (stations 6–7, K-boy and K-girl, each 13.4 m²) are not designed in this style yet. This brief designs both, up to approval 2. The transition clips wait until every room is ready.

## Inputs
- **The house plan:** `docs/house-plan.md` and `docs/house-plan.json`, with the rooms, openings and cameras.
- **The route:** chapters 1, 4 and 11 of `docs/proposals/wm-tour-route-2026-11-17.md`.
- **The style:** `docs/design-bible/warm-modern.md`. Kids' rooms in the same house: warm, calm and natural, not cartoonish, and still the same house language.
- **The slots:** `data/slots/kids.json` (19 slots).
- **The cards:** `data/products/kids/` and the pools in `data/products/`.
- **The method:** the bedroom and bath render documents (`docs/proposals/wm-master-bedroom-render-2026-11-17.md`, `wm-bath-render-2026-11-17.md`).
- **The rules:** `docs/studio-rules-digest.md`, especially FB5–FB11, ג.2, V7Q6, plan B (beds and desks fixed, not sold) and PR1.
- `.claude/skills/interior-design-rules/`.
- **Child safety:** no small loose parts within reach in the styling, and no cords hanging near the bed. Flag any product whose card lacks a safety note.

## Write
`docs/proposals/wm-kids-rooms-render-2026-11-19.md`, with a chapter per room. The two rooms are siblings: they share the shell and differ in palette and objects.

Each room covers:
1. **The architecture and language:** a proposed Bible chapter for approval.
2. **The frames:** a hero frame, and a second frame if 20 needs it, with the camera from the plan. Every new camera is a 1.3.9 item.
3. **The products, 20 or more for sale,** per slot:
   - the frame;
   - the place (plan and u,v);
   - the size;
   - the default card and two alternatives;
   - the sample slot for approval 3, with 3 variants.

   Use existing cards first, and only cards whose SKU photo you can judge. The photos are in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/`. Ask the manager for others. Count the way the manager counts: each product once per room, in the frame where it's biggest. Also give the V7Q6 count.
4. **The gaps for sourcing:** one line per gap, with the spec and 6–10 candidates wanted. Israeli stores first.
5. **The render plan,** at list prices: seedream-5-pro 2K 650, nano 400 per edit.
6. **The rejection list.**
7. **The approval-2 list** for the owner.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's documents.
- Fidelity before beauty, and IKEA only as a marked alternative.
- **Write in stages:** the boy's room first.
- Return a short Hebrew summary per room: the frames, the count, the gaps, the cost, and the approval-2 list.
