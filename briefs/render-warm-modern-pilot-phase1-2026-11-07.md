# Brief: warm-modern living-room tool pilot, phase 1 (render-agent, 2026-11-07)

**The owner (2026-11-07):**
- TS1: the pilot, now. 8,400 is approved and the cap is 10,000.
- WMB1: Bible 1.0 and house plan 1.3.x are approved.
- WMP2: the products are approved as they are.

These are recorded in `status/decisions.json` and in studio rules ז under "המודרני החם, אישורים 1 ו-2". Per `CLAUDE.md` stage 2, this phase covers only:
1. the room shell;
2. the fixed furniture and its shadow;
3. one slot with 3 variants.

Then qa-agent and master-designer check, and then **owner approval 3**. Poses and pans come only after that.

**Update 2026-11-07 (QA, `qa/reports/2026-11-07-ged-codefix5-clay-r3.md`):** clay **r3** (`assets/blockout/house/framing/warm-modern-r3/`) may serve as the reference for this phase: the shell, the fixed furniture and the cushions. The magazine holder (WMC9, r4) is outside this phase. **The shell lock leaves out the back-wall floor line** until the 3 cm edge, probably a shadow gap at the skirting, is confirmed in the house plan. Every other named line is in.

## The steps
The plan is master-designer's `docs/proposals/warm-modern-living-room-slots-2026-11-07.md` §2, rows 2–4. Run `var2_estimate_cost` before each step, and stop if it differs from 650 by more than 10%.

| # | Step | Model | ≈ tokens |
|---|---|---|---|
| 2 | Room shell on the clay r3 at M0 1.2: walls, glazing, bench, ceiling band and gap, floor. The shell-lock check is lock_v2 / edges v3 on the shell's named lines, per M0S1. | seedream-5-pro i2i 2K, `aspect_ratio: auto` | 650 |
| 3 | Fixed furniture (sofa, coffee table, armchair) in the style's finish per Bible 1.0, composited on the shell, with a shadow layer made in code | seedream-5-pro i2i 2K | 650 |
| 4 | The **cushions** slot: sets A, B and C from `data/selections/living-room.warm-modern.json`, the throw included. One pass each on shell plus furniture, extracted with a mask as a swappable layer. | seedream-5-pro ×3 | 1,950 |
| | **Phase 1 total** | | **3,250** |
| | Reserve: one shell retake and one furniture retake, only with my approval | | up to 1,300 |

## Acceptance
- **The shell** passes the lock against clay r3 (all named lines except the back-wall floor line). The windows, bench, ceiling band and floor follow Bible 1.0's tool chapter, and the light is the tool's fixed light (ARC2), with the black point L 11–14 in grading (WM-G1).
- **The furniture** keeps the footprints. The armchair has the Nordic geometry in walnut and bone bouclé (WM-F1).
- **The three cushion sets** are faithful to their cards. The layers swap with no change outside the product: per studio rule ו.5, the swap-diff check is what applies in the tool.
- Keep the raw files, the job records with prices, and a sheet: clay r3 | shell | shell + furniture | the three cushion variants.

## Fixed rules
- If var2 requires authentication, stop and report. Never ask for codes or tokens.
- New files only, no commits. This is a test and not for the site until QA and approval 3.
- Return a short Hebrew summary: tokens per job and total, the lock numbers, and your honest read.
