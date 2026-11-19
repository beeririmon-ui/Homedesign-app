# Brief: the warm-modern kitchen and dining, and the work room, with 20 products each (master-designer, 2026-11-19)

## Why
The owner (FB11, in the digest):

> "בואי נמשיך לכל החדרים, ננסה להגיע ל20 מוצרים בחדר ולא 11, וכשהכל יהיה מוכן נייצר מעברונים"

Every tour room of the warm-modern house gets at least 20 products for sale. More is better (FB10), and they must "take the stage" (FB9). The kitchen and dining (station 4, D1 then D2, point PD) and the work room (station 10, W0) are not designed in this style yet. This brief designs both, up to approval 2. The transition clips wait until every room is ready.

## Inputs
- **The house plan:** `docs/house-plan.md` and `docs/house-plan.json` (kitchen-dining 28.5 m², work 11.1 m²), with the openings and cameras.
- **The route:** chapters 1, 3 and 11 of `docs/proposals/wm-tour-route-2026-11-17.md`.
- **The style:** `docs/design-bible/warm-modern.md`. The Nordic dining supplement `docs/design-bible/nordic-dining.md` is for structure only, not style.
- **The slots:** `data/slots/dining-room.json` (27 slots) and `data/slots/work.json` (17).
- **The cards:** `data/products/dining/`, `data/products/work/` and the pools in `data/products/`.
- **The same house:** the living room's approved frames and the bedroom and bath render documents (`docs/proposals/wm-master-bedroom-render-2026-11-17.md`, `wm-bath-render-2026-11-17.md`), for method and language.
- **The rules:** `docs/studio-rules-digest.md`, especially FB5–FB11, ג.2, V7Q6, plan B (furniture fixed, not sold) and PR1.
- `.claude/skills/interior-design-rules/`.

## Write, per room (one document each)
- `docs/proposals/wm-kitchen-dining-render-2026-11-19.md`
- `docs/proposals/wm-work-render-2026-11-19.md`

Each document covers:
1. **The room's architecture and language** in the warm-modern house, as a proposed Bible chapter for approval: the materials, the fixed furniture (kitchen units, the dining table and chairs: which are fixed and which are for sale), and the light.
2. **The frames:** a hero frame, and a second frame if 20 needs it. Give each the camera (position, height, lens, yaw) from the plan, what it shows, and the product stage. Every new camera is a 1.3.9 item.
3. **The products, 20 or more for sale,** per slot:
   - the slot;
   - the frame;
   - the place (plan and u,v);
   - the size;
   - the default card and two alternatives where the wheel will use them;
   - the sample slot for approval 3, with 3 variants.

   Use existing cards first. Use only cards whose SKU photo you can judge. The photos and sheets are in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/`. Ask the manager for others.
   - Count the way the manager counts: each product once per room, in the frame where it's biggest. Also give the V7Q6 count.
4. **The gaps for sourcing:** one line per gap, with the spec, the size, the tone and the material, and 6–10 candidates wanted. Israeli stores first for furniture, textiles and tableware.
5. **The render plan**, following the bedroom's: clay, plate, defaults, mask edits, layers, and the sample variants. List prices are seedream-5-pro 2K 650 and nano 400 per edit.
6. **The rejection list** for render-agent and QA.
7. **What the owner approves (approval 2):** a short list for the picks sheet.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's documents.
- Respect:
  - fidelity before beauty;
  - IKEA only as a marked alternative;
  - framed art only with stated rights (PR1);
  - nothing hides a hero product.
- **Write in stages:** kitchen-dining first, then work.
- Return a short Hebrew summary per room: the frames, the product count, the gaps, the cost, and the approval-2 list.
