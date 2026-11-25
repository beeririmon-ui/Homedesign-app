# Brief: MOCK6, the kids' rooms in the tour, plus a many-option wheel (frontend-dev, 2026-11-25)

## Why
- **The kids' rooms are approved.** The owner approved them (AP3-KIDS, 2026-11-25), and they are now registered in the binding documents: 1.3.9a, `data/slots/kids.json` 1.1.0, commit d942155b.
- **Their cards are ready.** The `mirror_of` copies are in, and vitest is 555/555 (`data/leads/cards-kids-after-reg-2026-11-25.md`).
- **The bath gained a product.** B1 has a new ledge planter that passed QA, so the bath is at 19.
- **The owner wants faster progress.** For the kids' art he asked for "in the scroll, many options" (FB12). The designer's proposal `docs/proposals/wm-fb12-2026-11-25.md` (ב.4, ב.8) sets 10 art sets per room as a second wheel. The art sets themselves come later, so this MOCK prepares the wheel for many options.

## What to build (behind `HD_PUBLIC=0`)
1. **The boy's and girl's rooms** in the tour, using the same engine and rules as MOCK5.
   - **Sources:** the layers in `assets/renders/boy/warm-modern/stage1-2026-11-24/` and `assets/renders/girl/warm-modern/stage1-2026-11-24/`.
   - **Pixel gate:** 0 pixels different from each `K-<room>-defaults.png`.
   - **Cameras:** from `style_shells_1_3_1.warm-modern.kids` in `docs/house-plan.json`. The girl's room uses `girl_offset_y`.
   - **Room buttons:** add "חדר הילד" and "חדר הילדה", with the temporary dissolve.
2. **Product dots and counts.**
   - **Counts:** boy 13, girl 12.
   - **No dot on fixed pieces:** the walnut bed, desk and chair get no dot.
   - **Safety, per AP2-NEW and QA K-I7:**
     - **The Roman blind (868827):** shown, but "לא במכירה" (EN 13120 is missing).
     - **The pendant in the kids' rooms:** not sold there (no CE). Show a dot with "לא במכירה לחדר ילדים", or no dot. Pick one, and say which.
     - **The teddy bear, bunny and cars:** "עדכנו אותי" until EN 71 exists.
     - **Textiles:** sold as usual. OEKO-TEX is preferred, but not required.
3. **The wheel:**
   - **The throw:** the wheel today, V1–V3 in each room.
   - **Many options:** make the wheel component handle **8–12 options**. Use a scroll-snap carousel with a counter ("3 / 10"), keyboard and swipe, and lazy-load only the patch for the selected option. Test it with a fixture of 10 options. Don't fake real art into the build.
4. **The bath:** include the new B1 ledge-planter layer, and update the bath count to 19.
5. **`mirrorOf` for pool originals (option (a)).** Today `build-catalog.ts` resolves `mirror_of` only to originals that pass the schema. Pool cards have no `room`, so the three CJ-L2 copies stay hidden. Let `mirrorOf` find a pool original too, and take its economics. The three copies:
   - `bath/vanity-tray/vanity-tray-cj-travertine-organic-tray-24`;
   - `work/desk-tray/desk-tray-cj-travertine-organic-tray-24`;
   - `dining/floor-vase/floor-vase-cj-wabi-sabi-floor-vase-white`.
6. **Leave the living room exactly as in MOCK5.** A render-agent is working on a clean M0 plate right now (FB12, the coffee table). Pin the living room to the plate and manifest MOCK5 used, and don't pick up any new living-room file.

## Inputs
- the MOCK5 code and its README section; `site/tools/make-tour-room*.ts`, `site/tools/tour/*`, `site/web/src/tour/*`;
- `docs/house-plan.json` (1.3.9a), `data/slots/kids.json`, `data/slots/bath.json`;
- the QA reports `qa/reports/2026-11-24-kids-stage1/` and `qa/reports/2026-11-25-bath-b1-planter/`;
- `docs/proposals/wm-registration-1-3-9-kids-2026-11-25.md`;
- `docs/proposals/wm-fb12-2026-11-25.md`, ב.4 and ב.8.

## Outputs
- **The artifact:** `site/dist-artifact/`, rebuilt, with `check-artifact` passing (at most 255 files). Don't publish it.
- **A walkthrough video,** no more than 12 MB, at 1280×720: `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/mock6/walkthrough.mp4`. It shows:
  - both kids' rooms at rest;
  - the throw wheel in each;
  - the bath B1 with the planter;
  - the new wheel with the 10-option fixture, if it can be shown honestly as a demo. If not, skip it.
- **Screens** at 1280 and 400 for both kids' rooms and the wheel.
- **A short "MOCK6" section** in `site/README.md`.
- **The checks,** with numbers: typecheck, lint, vitest (should be 555/555 plus your new tests), e2e (add `mock6.spec.ts`; mock5 must still pass), a11y, budget, and both builds.

## Fixed rules
- 0 tokens, no var2, no commits, no keys.
- Don't edit `data/`, binding documents, render folders or masters.
- **Never `git stash`, `git checkout` or `git reset`.** Never `npx` without `--no-install`. Don't run `playwright install`.
- **Don't touch** `assets/renders/living-room/`. render-agent is working there.
- **The disk is tight** (about 1.8 GB). Delete what you don't hand over.
- **Return a short Hebrew summary:**
  - what the owner sees;
  - the counts;
  - the safety handling;
  - the wheel;
  - the sizes and checks;
  - what's next.
