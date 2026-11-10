# Brief: the warm-modern living-room tool, phase 2 (render-agent, 2026-11-10)

**The owner (2026-11-10):**
- **PH2-WM, approved up to 9,740** with the reserve. Answer: "Yes, stage 2 too (Recommended)".
- **SPEND2:** "את יכולה לנצל עוד מהקרדיט של var2 במידת הצורך".

These are recorded in `status/decisions.json` and in studio rules ז.

**The plan is binding:** master-designer's `docs/proposals/warm-modern-tool-phase2-2026-11-07.md` §2–§3. Read it whole. This brief covers **steps 0–3 and the checkpoint**. Steps 4–9 come in a follow-up brief only after the checkpoint passes. Steps 10–11, the depth map and the pans, are motion-agent's.

## The base you build on (phase 1, approved and QA'd)
- **The shell, furniture and cushions in v3c:** `assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07/`, especially `layers-v3c/` with its manifest, the method and the verification scripts.
- **QA:**
  - `qa/reports/2026-11-07-pilot-phase1-v3c-verify.md`;
  - `qa/reports/2026-11-10-wm-tool-layers-v3c.md`. Read its finding 1 (per-layer downscaling) and its note on cutting from composites, not grading layers separately.
- **The clay:**
  - `assets/blockout/house/framing/warm-modern-r4/`, house plan 1.3.5;
  - slots `data/slots/living-room.json` 1.9.3 `by_style.warm-modern`.
- **The selection, the source of truth:** `data/selections/living-room.warm-modern.json`. If the proposal and the selection differ, the selection wins; note the difference.

## Product rules decided after the proposal (2026-11-10)
These are in `briefs/site-s11-qa-fixes-2026-11-10.md`, addendum 1.
- **The floor lamp with the walnut pole:** render the **regular floor-lamp variant only**. The smart variants and the table variant are not sold.
- **CJ's travertine lamp and the black bowl:** render only an **identified** variant (see `data/catalog/option-labels-he.json` and `docs/proposals/names-labels-he-2026-11-10.md`). If the default's variant isn't identified, say so and use an identified one.
- **Lamps without CE:** rendered, but not sold (proposal §4).
- **The default cushion set is B** (CAM1). The full default scene is shell + furniture + set B + the defaults of steps 1–3.

## The steps in this brief
| # | Step | Model | ≈ tokens |
|---|---|---|---|
| 0 | clay r4 checks per slot (F3), and place-holders for the defaults only | Blender / code | 0 |
| 1 | The rug under the fixed furniture, with the contact shadow redone | seedream-5-pro i2i 2K | 650 |
| 2 | Defaults, the window/floor group: curtains, vase, planter, basket, magazine-holder, floor-lamp | seedream-5-pro i2i 2K | 650 |
| 3 | Defaults, the wall/table group: framed-art, accent-sconces, pendant, bowl, candle-holders | seedream-5-pro i2i 2K | 650 |
| | **This brief's total** | | **1,950** |

- **The fidelity cards:** card crops as references, uploaded to var2 only and never committed.
- **Before each job:** run `var2_estimate_cost`, and stop if it differs by more than 10% from the table.
- **Cheaper model for a targeted retake:** grok-imagine-image-2 segment-map (free) plus segment-edit (about 250) is allowed, if it preserves the other pixels.
- **The reserve:** up to 1,300 for retakes, **only with my approval**. Report and wait.

## Acceptance (for the checkpoint)
- **Every product is its own layer,** extracted with a mask and cut from the graded composite. Lit products are rendered off; their light layer is made in code, as in the Nordic house.
- **Swap-diff per layer:** 0 px outside the product and its shadow (rule ו.5).
- **The v3c display grade on everything:** one grade, black point L 11–14 (WM-G1). No layer graded separately.
- **The shell lock against clay r4** holds: lock_v2 / edges v3 on the named lines.
- **Fidelity to each card:** shape, colour and proportions (G1). Flag anything "partial" honestly.
- **The output:** `assets/renders/living-room/warm-modern/phase2-2026-11-10/`. It holds:
  - the raw files;
  - the jobs with prices (`jobs.json`);
  - the layers plus `layers/manifest.json`, in the same format as `layers-v3c`, with a verification script;
  - one sheet showing the full default scene, plus each step.

## Fixed rules
- If var2 asks for authentication, stop and report. Never ask for codes or tokens.
- New files only. Don't change approved phase-1 files. No commits.
- Return a short Hebrew summary: tokens per job and total, the lock and swap-diff numbers, fidelity per product, and your honest read.
