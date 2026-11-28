# Brief: a wheel plan for the warm-modern house (master-designer, 2026-11-28)

## Why
The owner (2026-11-28): "ממש מעט מהמוצרים יש להם גלגל מוצרים, זה בגלל שאין עוד מוצרים או שלא רונדרו עדיין?"

**Today:** the 7 tour rooms have about 111 product slots in their manifests, and only 11 of them have a wheel:
- living room: cushions;
- dining: framed art, condiment set, sink set, pendant, tea towel;
- bath: hand towel;
- bedroom: throw;
- boy: bedspread;
- girl: bedspread;
- work: framed art.

That is mostly the stage-2 "one sample slot per room" rule plus budget, not a lack of cards: `data/products/` holds about 650 cards over about 127 slot types.

## The task: one plan, `docs/proposals/wm-wheels-plan-2026-11-28.md`
For each room (living M0-W, dining D1, bath B1, bedroom MB0, boy, girl, work):
1. **Choose the 3–5 slots that most deserve a wheel next.** Rank them by:
   - how much of the frame the product fills and how much it changes the room (FB20: "how much the product fills the space");
   - at least 3 options that pass the style rubric of `interior-design-rules`;
   - true to the product, and sold by a supplier we can reach. CJ is blocked and AE needs the owner's login: mark each option with its supplier.
2. **For each chosen slot:** list the 3–8 options (card ids, with the default first), and one line on why they work together in the room.
3. **The gaps:** slots that deserve a wheel but have fewer than 3 good options. Say what sourcing should look for.
4. **Cost,** by the warm-modern actuals:
   - an in-room option is a nano 2K in-context edit, 400;
   - a studio still is about 320 (6,440 for 20).
   - Give the cost per room and in total for your proposed first round. Also give a cheaper "top wheel per room" round.
5. **Order:** which rooms first. The living room and the bedroom are the ones the visitor meets on the route first.

## Inputs
- the room manifests:
  - `assets/renders/living-room/warm-modern/fb13-2026-11-25/layers/manifest-wheel-pecan.json`
  - `assets/renders/dining/warm-modern/stage1-2026-11-20/manifest-fb16.json`
  - `assets/renders/bath/warm-modern/stage1-2026-11-17/layers/manifest-fb16.json`
  - `assets/renders/master/warm-modern/stage1-2026-11-17/layers/manifest-fb16.json`
  - `assets/renders/boy/warm-modern/stage1-2026-11-24/manifest-fb16.json`
  - `assets/renders/girl/warm-modern/stage1-2026-11-24/manifest-g1-fb16.json`
  - `assets/renders/work/warm-modern/stage1-2026-11-20/layers/manifest-fb16.json`
- the display frames next to them, to judge what fills the frame;
- `data/products/**` (the cards and `style_scores`), `data/slots/*.json`, and `data/catalog/sale-exclusions.json`;
- the studio stills, `assets/renders/wheel-studio/warm-modern/manifest.json`;
- `docs/studio-rules-digest.md`; the Bible is `docs/design-bible/` (for warm-modern, use the warm-modern sections and the catalog).

## Fixed rules
- 0 tokens. A proposal only: don't edit binding documents or `data/`.
- Use the `interior-design-rules` skill.
- Work economically: read the digest, not the full rules.
- **Your summary:** Hebrew, at most 10 lines, with the wheels per room, the total cost of round 1, the cheaper round, and the gaps.
