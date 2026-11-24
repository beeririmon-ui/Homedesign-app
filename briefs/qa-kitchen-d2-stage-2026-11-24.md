# Brief: QA on the changes in the kitchen's D2, "take the stage" (10.9) (qa-agent, 2026-11-24)

## Why
The kitchen's stage one passed QA on 2026-11-20, apart from the D2 FB9 judgment: "D2 reads sparse".

The designer wrote 10.9. render-agent then:
- rebuilt D2 at yaw −86, in code from the two approved plates;
- added a walnut niche, the print 05 in a 40×50 frame, the moon jar, a vessel with branches, a pair of walnut boards and a second towel;
- graded the floor and the plaster in both frames (KD-L4);
- removed V2 from the wheel, which is now V1 and V3.

The manager's rulings, after the first report:
- the branch vessel stays visible at D1's right edge, for physical consistency between the frames;
- the print is fixed in code to show whole at 4:5;
- the branches get no further edit;
- board F's corner is fixed in code.

**Spend:** 2,000 (cap 3,450). **The room:** 23 products.

**This is a changed-only QA (EFF1).** Don't re-check what passed on 2026-11-20 and hasn't changed.

## Inputs
- **The render folder:** `assets/renders/dining/warm-modern/stage1-2026-11-20/`:
  - the README, with chapter 10.9, the regions and the rulings;
  - `checks.json`, `d2stage.json`, `jobs.json` and `qa-sheet.jpg`;
  - `D1-defaults.png`, `D2-defaults.png`, `D1-V3.png` and their `-frame.png`s;
  - `plate-D1.png` and `plate-D2.png`;
  - `layers/`, `shadows/`, `light/` and `manifest.json` (its `rebuild` key);
  - `tools/kd_d2stage.py` and `tools/kd_print.py`.
- **The clay for −86:** `assets/blockout/house/framing/wm-dining-2026-11-24/`.
- **The spec:**
  - `docs/proposals/wm-kitchen-dining-render-2026-11-19.md`, chapter 10.9, which overrides earlier chapters;
  - the kitchen chapter in `docs/design-bible/warm-modern.md` (1.1).
- **The previous QA:** `qa/reports/2026-11-20-kitchen-dining/`, to know what already passed.
- **The products:** each new product's card in `data/products/`, with its SKU via `room_variants` "warm-modern.kitchen-dining" or the default.
  - SKU photos: `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`, with `picks/new-rooms-photo-check.json` and `picks/ae-round-photo-check.json`.
  - Read them only with `python3.12 -I`.

## What to check (0 tokens, only what changed)
1. **Fidelity of the new or changed products:**
   - the print 05 in its frame: 40×50, 4:5, whole, with the float margin;
   - the moon jar;
   - the branch vessel;
   - the walnut board pair, including board F's corner and board B at ×0.78;
   - the second towel;
   - the niche's plates, bowls and jars.

   For each: shape, colour (R5 on lit areas) and size against the card, the SKU photo and the clay. Does the item that's sold match what's drawn?
2. **The new geometry:**
   - **D2 at −86:**
     - the seam at x 304–364 (floor 1.85, bench 1.85, plaster 0.23 ΔE00);
     - the camera against the clay;
     - is anything bent, doubled or warped?
   - **The niche:** its walnut against stage one's niche (0.38 ΔE00), its light, and whether it reads as built-in.
3. **The layers (RND2):**
   - rebuild per `manifest.json` → `rebuild`;
   - 0 pixels outside alpha, shadow and light in D1-defaults, D2-defaults and D1-V3;
   - shadows one z below their product;
   - light layers on screen;
   - the black point within WM-G1 (reported 11.27–11.49);
   - D1 and D2 still read as one room after the grade.
4. **At ×1–×2, per region:** the 9 regions in the README or `qa-sheet.jpg`. Your old check 4 changes: the branch vessel at D1's right edge is a deliberate projection from D2. Judge only whether it reads well there; it isn't a "new object". Then look at the whole frame:
   - Does D2 now "take the stage" (FB9)? The coverage is 7.8% against a target of about 8, with two products over 1%.
   - Would a visitor still read D2 as empty?
   - Is it the same house as the living room, the bedroom and the work room, at magazine level (FB5), and lived-in (FB6)?
5. **The count:** 23 in the room (11 in D1, 12 in D2), each product once per room, plus V7Q6 (D1 12, D2 9). Confirm the wheel is V1 and V3 only, and that `D1-V2` is gone from the manifest.

## Outputs
- **The report:** `qa/reports/2026-11-24-kitchen-d2-stage/README.md`, with pass or fail per item and numbers. Low findings go to `status/backlog-low.md` as KD-L5 and on.
- **A status line:** "עבר QA (המטבח ופינת האוכל שלב 1 כולל 10.9; לבעלים לאישור 3; לא לאתר לפני רישום 1.3.9)", or the blocking findings, saying for each whether code can fix it.

## Fixed rules
- 0 tokens, no var2, no commits, no keys.
- Don't edit a binding document, `data/`, or another agent's files.
- **A render-agent is working on the kids' rooms** (`assets/renders/boy/`, `assets/renders/girl/`, `assets/blockout/house/framing/wm-kids-2026-11-24/`). Don't touch them, or their entries in `assets/manifest.json`.
- Never run `git stash`, `git checkout` or `git reset`.
- Keep scratch files small and delete them when done. The disk is tight (about 2.4 GB free).
- **Return a short Hebrew summary:** the five items, pass or fail with numbers, and the FB9 judgment.
