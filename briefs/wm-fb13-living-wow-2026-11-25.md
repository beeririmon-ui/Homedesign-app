# Brief: FB13, a "wow" magazine-level living room with nothing pasted; plus a pasted-look audit of all rooms (master-designer, 2026-11-25)

## The owner's words (FB13, `docs/studio-rules.md`)
> "הכל נראה מודבק ולא חלק מהפריים, משהו ברנדור או בחיבור לא עובד הכי טוב...וגם נראה קצת בנאלי הסלון..לא תמונת מגזין כמו הבקשה המקורית... אז בא נסדר את הסלון שיהיה וואוו ובמקביל נסיים את שאר החדרים"

The goal (CLAUDE.md) asks for a site "ברמה שלא נראתה לפני", where every frame is at the level of the magazine frames (FB5).

## Look at
- **Today's M0:** `assets/renders/living-room/warm-modern/phase2-2026-11-10/default-frame-basket-set-{A,B,C}.png`, the active `layers/manifest-basket.json`, and the README for how it is built. Layers were rendered separately from rounds R3a–R9 and composited on a plate.
- **The magazine frames the owner liked:** `assets/renders/editorial-phase-b-2026-11-06/` and `editorial-test-2026-11-06/`, plus the magazine gate in the site. Find the warm-modern living-room one.
- **The rules:** the Bible (`docs/design-bible/`), the `interior-design-rules` skill, and `docs/house-plan.json` (M0 camera, 1.3.9).
- **The other rooms' current defaults:**
  - kitchen and dining;
  - work;
  - master bedroom;
  - bath B1 and B2;
  - boy and girl (`K-*-defaults*.png`);
  - the entrance.

  Find them under `assets/renders/<room>/warm-modern/`.

## The task
1. **Why it reads "pasted".** Per layer, in plain words: light direction and softness, colour temperature, contact shadows, occlusion, sharpness, grain and noise, perspective, and scale. Rank the worst offenders.
2. **Why it reads "banal" against the magazine frame.** Camera height, lens and angle; light (time of day, sun patches, shadow drama); composition and depth layers; styling density and story; materials. Be concrete.
3. **The proposal for a new M0.** It must stay true to the products sold, keep the wheel (sample-slot) idea working, and keep the swappable table (FB12-T).
   - **The art direction:** camera (may change; the arrival clip is redone at the very end anyway, FB11), light, styling and the hero moment.
   - **The render method that removes "pasted":** for example, one coherent full-scene render of the default set with all products in one light, using SKU references, as the hero frame. Variants are made by in-context edits on that frame, not separate renders. Layers are extracted from the single render, and a unifying finish (grain, grade, light wrap) is done in code. Name what render-agent must do differently from R3a–R9.
   - **The cost** in var2 (seedream 2K 650, nano 2K 400 / 4K 450), with an expected total and a cap.
4. **The audit of the other rooms.** For each room, one line: does it read pasted (none / slight / strong), which products, and the cheapest fix. Note that later rooms used in-context crop edits; say whether that held up.
5. **Owner questions:** at most 2, and only if they truly block. The default is to proceed.

## Output
- `docs/proposals/wm-fb13-living-wow-2026-11-25.md`, tight.
- A Hebrew summary of at most 12 lines: the diagnosis, the direction, the method, the cost, and the other rooms.

## Fixed rules
- 0 tokens. A proposal only; edit no binding document.
- Keep to the Bible's rejection list and to product fidelity: the render shown must be the product sold.
