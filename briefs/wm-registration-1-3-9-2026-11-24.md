# Brief: register the approved warm-modern rooms in the house plan and the slot files, 1.3.9 (master-designer, 2026-11-24)

## Why
On 2026-11-24 the owner answered AP3-KW with "Approved", which the manager reads as the recommended option (`docs/studio-rules.md`, AP3-KW). That answer:
- approves the kitchen-dining and the work room (approval 3);
- authorises registering, in the binding documents, the cameras, product slots and fixed furniture of every room the owner has approved. This is also the answer to REG1.

Until now, each render proposal wrote its own registration items as proposals and edited no binding document:
- 1.3.7 for the bedroom;
- 1.3.8 for the entrance;
- 1.3.9 for the rest.

Because they are not registered:
- the site can't wire these rooms in;
- vitest is red: 47 cards name a room + slot that isn't in `data/slots`.

## Scope
**Register (approved):** the warm-modern frames, cameras, `style_shells` and slots of:
- **the living room:** M0, with the FB9/FB10 additions in `wm-house-20` that passed QA;
- **the entrance, "הכניסה" (ENT20):** the hall and the corridor, with the frames the owner saw and the products that passed QA (HT2 / HE / HC as the proposals name them);
- **the master bedroom:** MB0 and MB1, including 13.11 and the MB1 forward check;
- **the bath:** B2 and B1;
- **the kitchen-dining:** D1, and D2 at yaw −86 with the walnut niche (10.9.7);
- **the work room:** W0, chapter 1.6.

**Don't register yet:**
- **The kids' rooms.** Their approval 3 is still open (QA fixes running), so they wait for it.
- **The tour route's transitions** (T-HC, T-C*, the U1 H0 note in `wm-tour-route` 11.4). These wait for their pilot. Clips come at the end (FB11).
- **The magazine frames.** They are not bound (1.3, DIR2).
- Anything a proposal marks as pending an owner answer that the owner never gave.

**If you're unsure** whether the owner approved an item, don't register it. List it for the manager, with the reason.

## Inputs
- **The binding documents, which you edit:**
  - `docs/house-plan.md` and `docs/house-plan.json` (now 1.3.6);
  - `data/slots/living-room.json`, `hall.json`, `corridor.json`, `master.json`, `bath.json`, `dining-room.json` and `work.json`.

  Follow each file's existing structure and its `version` history line. Keep `by_style` per style. Nordic and the other styles must not change.
- **The proposals, with their registration chapters:**
  - `docs/proposals/wm-master-bedroom-render-2026-11-17.md` (1.3.7 items, and 13.11);
  - `docs/proposals/wm-mb1-forward-check-2026-11-19.md`;
  - `docs/proposals/wm-entrance-hall-architecture-2026-11-13.md` (1.3.8);
  - `docs/proposals/wm-entrance-magazine-2026-11-15.md`;
  - `docs/proposals/wm-front-door-2026-11-14.md` (chapter 7);
  - `docs/proposals/wm-bath-render-2026-11-17.md`;
  - `docs/proposals/wm-house-20-2026-11-19.md`, chapters 0–8;
  - `docs/proposals/wm-kitchen-dining-render-2026-11-19.md`, 1.7 and 10.9.7;
  - `docs/proposals/wm-work-render-2026-11-19.md`, 1.6.
- **What actually got rendered and passed QA:** this is the truth to register. Where a render moved something from the proposal, register the rendered position.
  - Each render folder's README, `manifest.json` and `checks.json`:
    - `assets/renders/master/warm-modern/stage1-2026-11-17/` and `mb1-2026-11-19/`;
    - `assets/renders/bath/warm-modern/stage1-2026-11-17/` and `b1-2026-11-19/`;
    - `assets/renders/hall/warm-modern/hall-products-2026-11-19/`;
    - `assets/renders/dining/warm-modern/stage1-2026-11-20/`;
    - `assets/renders/work/warm-modern/stage1-2026-11-20/`.
  - The QA reports in `qa/reports/` for those folders.
- **The owner's rulings:** `docs/studio-rules-digest.md` (FB9–FB11, HOUSE2, AP2-NEW, AP3-KW, ENT20, V7Q6 / F10 counting).
- **The vitest failures:** `briefs/reg-1-3-9-vitest-fails-2026-11-24.txt`. Each line is "card path: room/slot is not a slot", or "card path: placement".
  - The "not a slot" lines in the six approved rooms are yours. Register the slot if it is in an approved frame or in the room's approved product list.
  - If a card's slot isn't in any approved design (an old candidate pool, for example), don't invent a slot. List those cards for the manager, who will have sourcing move or archive them.
  - The "placement" lines are card fixes, which sourcing does. Don't edit `data/products/`. But if your registration decides a slot's placement, say which value it is (the schema enum is floor, wall, window, sill, surface, sofa, ceiling), so sourcing can match it.
  - The `kids/*` lines wait for the kids' approval 3.

## Outputs
1. **The house plan:** `docs/house-plan.md` and `docs/house-plan.json` at 1.3.9.
   - One history line names what this version takes in: 1.3.7, 1.3.8 and the 1.3.9 items, with the owner's decision AP3-KW (2026-11-24).
   - For each room: the shell (`style_shells.warm-modern.<room>`), the cameras with exact numbers (position, yaw, focal, u0/v0, tilt), the fixed, not-sold furniture, and the counting note (F10, ENT20).
2. **The slot files:** each touched `data/slots/<room>.json` gets its version bumped, with an `update_…` note in the file's own style.
   - Every slot in the approved frames, with its z, frame membership and placement.
   - The sample-slot wheel, per AP3 and the render folders:
     - the kitchen: the pendant, V1 and V3;
     - the work room: the art;
     - the master bedroom: the throw;
     - the bath: the hand towel.
3. **A short registration log:** `docs/proposals/wm-registration-1-3-9-2026-11-24.md`. It covers:
   - what was registered, per room, with source chapter and render folder;
   - what was not registered and why;
   - cards whose slot doesn't exist in any approved design;
   - each new slot's placement value, for the sourcing fix.

## Acceptance
- **JSON:** all touched JSON files parse. The manager runs `python3 -c json.load` and vitest after you.
- **vitest:** after your edits plus the sourcing placement fix, vitest should be green except the `kids/*` lines and any cards you list as "no approved slot".
- **Consistency:** no camera or slot number differs from the rendered, QA-passed frame without a written reason.
- **Unchanged:** Nordic and the other styles' entries. Diff them mentally before you finish.

## Fixed rules
- 0 tokens and no var2.
- You may edit only `docs/house-plan.*`, `data/slots/*.json` and the new log. Don't touch `data/products/`, the Bible, the studio rules, or any render folder.
- No git commands, which you don't have anyway. No keys.
- Return a short Hebrew summary:
  - per room, what was registered;
  - what wasn't, and why;
  - the list for the manager.
