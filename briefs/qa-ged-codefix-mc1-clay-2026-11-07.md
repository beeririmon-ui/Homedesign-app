# Brief: G-ED on the code fixes and MC1, and G1 on the warm-modern clay (qa-agent, 2026-11-07)

render-agent's two rounds are in. Board log 2026-11-07, the codefix3 and codefix4/clay/MC1 lines. Per playbook §5.3, nothing counts until QA has checked it.

## 1. G-ED on the editorial frames
Use your gate (`docs/ops/quality-gate-g-ed-2026-11-07.md`). The new frames are in `assets/renders/editorial-phase-b-2026-11-06/`:

| Frame | New file | Against | Record |
|---|---|---|---|
| Boho | `boho-A-fin4.png` (fin3 + basket ×0.75) | `boho-A-fin2.png` | `codefix3.json`, `codefix4.json` |
| Mediterranean | `mediterranean-A-ed5.png` | `-ed4` | `codefix3.json` |
| Japandi | `japandi-A-ed5.png` | `-ed4` | `codefix3.json` |
| Warm modern | `warm-modern-A-ed5.png` | `-ed4` | `codefix3.json` |
| Modern country | `modern-country-A-mc1.png` (fix1 → fix2 rug → MC1 table and sill) | `modern-country-A.png` | `codefix3.json`, `codefix4.json`, `mc1.json` |

For every pair, check:
- the mask diffs, G-ED.8;
- seams and halos at 100% and ×4, G-ED.9;
- the fidelity table for the changed products, G-ED.1–7. Include:
  - the country cups' imitation set;
  - the clay vase;
  - the bowl, against the "hat" at about 0.24;
  - the runner, against 33 cm;
  - the pendant, at 5 rings.

The open points render-agent reported itself:
- the light fringe tops on the Mediterranean bench cushions;
- the grain under the japandi jar at ×4;
- a tiny flaw where the warm-modern pendant joins ring 4;
- a warm hint on the first country cup at ×4;
- a thin light line at the furniture leg tips on the country rug at ×2;
- **the boho door behind the basket, with square, misaligned plank pieces at ×2–×4.**

Also note that EDR1 failed (`mc1.json`, the "rugs" key). There are no new rug frames. The Nordic A and warm-modern rugs stay "partial".

Give the state per frame (not yet / almost / final test), and what is left, with who fixes it and at what cost.

## 2. G1 on the warm-modern clay (`assets/blockout/house/framing/warm-modern-r1/`)
The inputs are house plan 1.3.1 §0א, slots 1.9 `by_style.warm-modern`, render-agent's `clay-checks-2026-11-07.json`, `clay_checks_wm_r1.py` and the sheet.

Confirm or refute these with your own named-edge tool:
- the projection against the plan numbers;
- the tangencies render-agent found:
  - the planter against the back curtain stack, 9 px in M0;
  - the tree crown proxy r 0.40 reaching through the wall and to 1.4 cm from the glass;
  - the rounded corner along the left frame edge in M0p;
  - the armchair and basket against the magazine holder, 0.0176 and 0.0177;
- the vase-on-bench clearance, 89 px.

Say whether the clay may serve as the reference for the paid shell step. That step still waits on the owner's approval 2 (WMP2).

## Output
- `qa/reports/2026-11-07-ged-codefix-mc1-clay.md` (Hebrew) plus `.json`, with overlays and crops under the folder of the same name.
- Update nothing else.

## Fixed rules
- New files only, no commits, no var2, no network.
- Return a short Hebrew summary: the state per frame with what is left, and the clay verdict with its findings.
