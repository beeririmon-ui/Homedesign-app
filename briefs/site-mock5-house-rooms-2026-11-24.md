# Brief: MOCK5, every approved room in the tour (frontend-dev, 2026-11-24)

## Why
The owner wants the whole site built and opened gradually (CLAUDE.md). FB11 says: every room first, transition clips last.

The tour today is MOCK4 (2026-11-18): the arrival v2, the living room M0, the bedroom MB0 and the bath B2. Since then:
- the bedroom and the bath got second frames (MB1, B1);
- the kitchen-dining (D1, D2) and the work room (W0) passed QA and owner approval 3 (AP3-KW, 2026-11-24);
- registration 1.3.9 put them all into `docs/house-plan.*` and `data/slots/` (commit 78d94cd6).

The kids' rooms are not approved yet, so they stay out.

## What to build (behind `HD_PUBLIC=0`; the public build has no tour, as today)
1. **New rooms and frames,** from the layers, with the same engine and the same rules as MOCK4:
   - **The rules:** sorted by z, shadows multiply, light is screen. The rested frame must match each folder's defaults PNG to the pixel. Atlas packing for products that don't change.

   | Room | Frames | Folders |
   | --- | --- | --- |
   | The bedroom | MB0 and MB1 | `assets/renders/master/warm-modern/stage1-2026-11-17/` (with FB10 and 13.11) and `mb1-2026-11-19/` |
   | The bath | B2 and B1 | `assets/renders/bath/warm-modern/stage1-2026-11-17/` and `b1-2026-11-19/` |
   | The kitchen-dining | D1 and D2 | `assets/renders/dining/warm-modern/stage1-2026-11-20/`. Its `manifest.json` has a `rebuild` key. D2 is the 10.9 version, at yaw −86 with the niche |
   | The work room | W0 | `assets/renders/work/warm-modern/stage1-2026-11-20/` |

2. **Frames inside a room:** a small "frame" control, for example "קיר המיטה / מרגלי המיטה".
   - Use a short temporary dissolve, as between rooms, and mark it in the code as temporary.
   - Never a zoom-in (rule ו.6).
3. **Room buttons:** the living room, the bedroom, the bath, the kitchen and the work room.
   - The move between rooms stays a temporary dissolve until the T-C\* clips (FB11).
   - The arrival stays as MOCK4.
4. **Product dots** for every product for sale in each frame, from the cards.
   - Registration 1.3.9 added `mirror_of` copies: one card per slot, same supplier/SKU/price, with the line `mirror_of: <id>` in `notes`.
   - `build-catalog.ts` looks up economics by id, so make it take price and shipping from the `mirror_of` original. That keeps those copies from showing as "עוד לא במכירה".
   - Count a product once per room, in the frame where it is biggest, as the counting rule says.
   - Fixed, unsold furniture (beds, nightstands, the vanity, the dining table and chairs, the bench, the desk) gets no dot.
5. **Close-up and wheel** on each room's sample slot:

   | Room | Sample slot | Variants |
   | --- | --- | --- |
   | The bedroom | The throw (as MOCK4) | — |
   | The bath | The hand towel (as MOCK4) | In B1, the bath mat, if its variant layers exist in the folder |
   | The kitchen | The pendant | V1 and V3 (`D1-V3`) |
   | The work room | The art | 08, 01, 02 (`w0-variant-art-01/02`) |

6. **The rights rule:**
   - 776445, above the bed, stays ×1 only, as in MOCK4.
   - For every framed print in the new rooms (the work room's art, the kitchen print 386242 and the bedroom's framed-art-2), check the card's rights field.
   - If rights are unclear or missing, apply the same ×1-only rule, and say which prints it hit.
7. **The catalog and the plan:**
   - Warm-modern cameras are registered only under `style_shells_1_3_1.warm-modern.<room>.cameras` in `docs/house-plan.json`. `make-tour-room.ts` reads `plan.cameras`, so for warm-modern it must read the style shell. Otherwise D2 gets Nordic's −91 instead of −86.
   - Warm-modern-only slots carry `styles`, so filter by it in `build-catalog.ts`. Otherwise they leak into the Nordic catalog.
8. **The owner's count chip,** per room: "X מוצרים למכירה בחדר". Expected counts:
   - the living room: 16;
   - the bedroom: 22;
   - the bath: 18;
   - the kitchen: 23;
   - the work room: 18.

   If your count differs, say why.

## Inputs
- **The previous MOCK:** the MOCK4 brief and its `site/README.md` section, and the code in `site/` (`web/src/tour/*`, `tools/make-tour-room.ts`, `tools/tour/*.json`, `tools/make-arrival.ts`).
- **The binding documents:**
  - `docs/house-plan.json` and `docs/house-plan.md` (1.3.9);
  - `data/slots/*.json`;
  - the log `docs/proposals/wm-registration-1-3-9-2026-11-24.md`, chapter 6;
  - `data/product-card.schema.json`.
- **The card changes:** `data/leads/cards-after-reg-1-3-9-2026-11-24.md`.
- **The QA reports:** the folders under `qa/reports/`:
  - `2026-11-18-master-fb10`, `2026-11-19-master-mb1`;
  - `2026-11-18-bath-fb10`, `2026-11-19-bath-b1`;
  - `2026-11-20-kitchen-dining`, `2026-11-24-kitchen-d2-stage`;
  - `2026-11-20-work-w0`.

## Outputs
- **The build:** `site/dist-artifact/`, rebuilt with `npm run preview:artifact`, with `check-artifact` passing. **Don't publish.**
- **A walkthrough video** for the owner, no more than 12 MB, recorded with Playwright at 1280×720. Save it at `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/mock5/walkthrough.mp4`. It shows:
  - the arrival and its "דלג";
  - each room at rest;
  - a frame switch in the bedroom, the bath and the kitchen;
  - one close-up with the wheel in the kitchen and one in the work room.
- **Screens** at 1280 and 400 for each frame at rest, and for the two new wheels.
- **A short "MOCK5" section** in `site/README.md`: what's new and what's temporary.
- **The checks,** with their numbers: typecheck, lint, vitest, the affected e2e (add a `mock5.spec.ts`), a11y on the tour pages, the budget, and both builds.
  - vitest has 2 known failures, the `kids/*` lines in `shared.test.ts`. They wait for the kids' approval 3. Don't "fix" them in data.
  - Note anything you didn't verify.

## Fixed rules
- 0 tokens, no var2, no commits, no keys.
- Don't edit any binding document or anything in `data/`, and don't edit the render or video masters.
- Supplier images only as FR-I already uses them. The build stays private for the owner.
- **Never run `git stash`, `git checkout` or `git reset`.**
- **Never `npx` without `--no-install`.** Don't run `playwright install`.
- **Another agent is fixing the kids' renders** in `assets/renders/boy|girl/`. Don't touch them.
- **The disk is tight** (about 2.4 GB free). Keep temporary builds and recordings small, and delete what you don't hand over.
- **Return a short Hebrew summary:**
  - what the owner will see, step by step;
  - the counts per room;
  - the sizes;
  - the checks;
  - what's temporary;
  - what's next.
