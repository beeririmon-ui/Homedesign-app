# Brief: the warm-modern master bedroom, ready to render (master-designer, 2026-11-17)

## Why
The owner (2026-11-17): "בבקשה בואי נתחיל לרנדר גם חדר שינה וחדר מקלחת כדי שתהיה דוגמא שלמה של בית לסגנון שהתחלנו, אפשר לרנדר במקביל, גם אני רוצה להתקדם עם הפרוייקט." The warm-modern house gets its master bedroom and bathroom next to the living room and the hall, as one complete example of the style. The bath runs in parallel (a separate brief).

The studio process applies (CLAUDE.md, stages 1–2). For each room, render first the shell, the fixed furniture and their shadow, the products in their default option, and **one sample slot with 3 variants**. That goes to QA and you, then to owner approval 3. Only then come the other layers.

## What exists
- `docs/proposals/wm-master-bedroom-architecture-2026-11-13.md` (yours): the warm-modern architecture and the MB0 plate. It is the same house as the living room: lime plaster #ECE5DA, smoked oak floor #8B6F55, walnut-lined openings with no architrave, a 0.20 rounded corner, no G-M4 wainscot, a shadow gap at the ceiling, and ARC2 light.
- `docs/proposals/wm-tour-route-2026-11-17.md`, chapter 11 (FB8): the visitor arrives forward-only (MBf, around the foot of the bed), and MB0 is unchanged.
- `docs/house-plan.json` (room "master", camera MB0, openings), `data/slots/master.json` (20 slots), the cards in `data/products/master/` (55), and the Bible `docs/design-bible/warm-modern.md`.
- The bar: FB5, every tour frame at the level of the warm-modern living-room magazine frame (`site/web/public/media/story/living-room/warm-modern/A/1280.webp`). FB6: a home people live in, not a resort. Product fidelity comes before beauty.
- The style reference: the bedroom magazine frame fix6 (`assets/renders/master/editorial-2026-11-07/`), as a reference for the style only.

## What to write (0 tokens)
A new document, `docs/proposals/wm-master-bedroom-render-2026-11-17.md`, short and concrete, that render-agent can build the clay and the prompts from:
1. **The architecture, final:** your 11-13 proposal, updated for anything since (FB8, the hall decisions). Mark each change to the house plan for the 1.3.9 registration. Don't edit the plan.
2. **The fixed furniture** (the bed, the nightstands) in warm-modern: material, colour and form, with exact dimensions.
3. **The product picks per slot:** for each slot in `data/slots/master.json`, score the existing cards against the warm-modern Bible with the `interior-design-rules` skill rubric. Pick the default product, and say which slots stay empty for now (FB6: lived-in, not crowded). Choose **the sample slot** with 3 variants (the bedding or the throw is a natural choice, but you decide). List the gaps for sourcing, with the spec for each.
4. **The scene brief for MB0:** what the frame shows, the hero, the light, what's on and off, styling details, and a rejection list (as you did for the hall stills).
5. **MBf** (the forward arrival frame in chapter 11), if it's needed for the room itself and not only for the clip. Say so.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's document.
- Write the document in stages (the headings first, then each section), so nothing is lost if the run stops.
- Return a short Hebrew summary: the architecture decisions, the picks per slot (default and gaps), the sample slot and its 3 variants, and anything that needs the owner.
