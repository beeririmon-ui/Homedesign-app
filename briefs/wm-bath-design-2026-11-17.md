# Brief: the warm-modern bathroom, ready to render (master-designer, 2026-11-17)

## Why
The owner (2026-11-17): "בבקשה בואי נתחיל לרנדר גם חדר שינה וחדר מקלחת כדי שתהיה דוגמא שלמה של בית לסגנון שהתחלנו, אפשר לרנדר במקביל, גם אני רוצה להתקדם עם הפרוייקט." The warm-modern house gets its bathroom and master bedroom next to the living room and the hall, as one complete example of the style. The bedroom runs in parallel (a separate brief).

The studio process applies (CLAUDE.md, stages 1–2). For each room, render first the shell, the fixed fittings and their shadow, the products in their default option, and **one sample slot with 3 variants**. That goes to QA and you, then to owner approval 3. Only then come the other layers.

## What exists
- **The plan:** `docs/house-plan.json`, room "bath" (X 3.25–6.25, Y 9.95–13.59, h 2.7, route "lean"). The cameras are B1, the arrival, and B2, a pan of −35 from it, both from point CB. Also the openings, and the corridor transition T-CBath, which chapter 11.2 of `docs/proposals/wm-tour-route-2026-11-17.md` turns into a forward walk.
- **The slots and cards:** `data/slots/bath.json` (23 slots) and the cards in `data/products/bath/` (68). The Nordic bath is rendered (`assets/renders/bath/nordic/`), and the Nordic Bible has a bath chapter. The warm-modern bath has no architecture yet.
- **The rules:** the warm-modern Bible `docs/design-bible/warm-modern.md`, and your living-room and bedroom work as the house language (`docs/proposals/wm-master-bedroom-architecture-2026-11-13.md`). It is the same plaster, floor family, walnut and bronze.
- **The bar:** FB5, every tour frame at the level of the warm-modern living-room magazine frame (`site/web/public/media/story/living-room/warm-modern/A/1280.webp`). FB6: a home people live in, not a resort. Product fidelity comes before beauty.

## What to write (0 tokens)
A new document, `docs/proposals/wm-bath-render-2026-11-17.md`, short and concrete, that render-agent can build the clay and the prompts from:
1. **The warm-modern bath architecture**, in the same fields as the bedroom (11-13): walls, floor, wet zone, ceiling, window, openings, fixed fittings (the vanity, the WC, the shower) and the light. Mark each change to the house plan for the 1.3.9 registration. Don't edit the plan.
2. **The frames:** B1 and B2 as they are, or a change if warm-modern needs one. Say which frame is the room's hero, and whether the bath at first stage needs both.
3. **The product picks per slot:** score the existing cards against the warm-modern Bible with the `interior-design-rules` skill rubric. Pick the default product, say which slots stay empty for now (FB6), choose **the sample slot** with 3 variants (towels or the bath mat are natural choices, but you decide), and list the gaps for sourcing with a spec for each.
4. **The scene brief** for the hero frame (and the second, if needed): what it shows, the hero, the light, the styling, and a rejection list.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's document.
- Write the document in stages (the headings first, then each section), so nothing is lost if the run stops.
- Return a short Hebrew summary: the architecture in a few lines, the frames, the picks per slot (default and gaps), the sample slot and its 3 variants, and anything that needs the owner.
