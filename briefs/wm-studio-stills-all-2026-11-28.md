# Brief: the list and the art direction for a studio still of every product (master-designer, 2026-11-28)

## The owner's words (FB29, `docs/studio-rules.md`)
Every product picture outside the room view (the product strip, the wheel, the product page) should look like a new photograph of the product:
- a throw folded;
- a vase whole, on a soft background, not black;
- never a crop of the room render, and never cut by something in front of it.

The FB20 stills in `assets/renders/wheel-studio/warm-modern/` (`sheet.jpg`) are the look.

## The task: `docs/proposals/wm-studio-stills-all-2026-11-28.md`
1. **The full list:** every product the tour shows in the 7 warm-modern rooms, room by room, by card id. The defaults come from each room's manifest; the room manifests are listed in `briefs/wm-wheels-plan-2026-11-28.md`.
   - Mark the ones that already have a still (FB20).
   - Mark the ones that will get one in wheel round 1, so they aren't counted twice (`docs/proposals/wm-wheels-plan-2026-11-28.md`, section 5.1).
   - Count what's left.
2. **Staging, one line per product:** folded, standing or hung; the angle; any prop allowed, or none.
   - Sets are shown as the set.
   - Lamps are shown lit or unlit; pick one rule for the house.
   - Large items (sofa covers, rugs, curtains) get a staging that still reads in a small circle.
3. **One house spec** for every still: the background tone, the light, the shadow, the fill of the frame, the framing for the circle and the tile, and no halo or feathered rim.
4. **The cost:** about 320 per still (6,440 for 20 in FB20). Give the total and a cap, split into batches by the route (living → kitchen → bath → bedroom → boy → girl → work).
5. **Flags:** products where a still is risky for faithfulness (unclear SKU photos, a set whose parts aren't all known). Say what to check first.

## Fixed rules
- 0 tokens. A proposal only: don't edit binding docs or `data/`.
- Use the `interior-design-rules` skill.
- **Your summary:** Hebrew, at most 8 lines, with the count, the total cost and cap, and the batches.
