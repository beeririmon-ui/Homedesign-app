# Brief: FB12 stage 1, the Olia coffee table as a product layer in M0 (render-agent, 2026-11-25)

## The decision
FB12-T was answered on 2026-11-25 (`docs/studio-rules.md`, after EFF2): "רנדרי שולחן שיהיה בר החלפה, שולחן שיתאים לסלון..סטיילי אבל לא כבד".
- **Render** IDANA Olia in natural oak, 120×65×38. The card is `data/products/living-room/coffee-table/coffee-table-idana-javorina-olia-natural.json`.
- **"בר החלפה":** the table is its own product layer, never baked into the plate, so other tables can be swapped in later.
- **Budget for the whole stage:** expected about 1,100, **cap 2,650**. Ask the manager before going over.

## The task
Follow `docs/proposals/wm-fb12-2026-11-25.md`, א.6 "שלב 1", א.7 and א.10 (the fit: position (0.30, 1.72), angle 0).
1. **The tone, first, at 0 tokens.**
   - Use the real-unit photos linked in the card. Download them to the scratchpad only, and read them with `python3.12 -I`.
   - Estimate the natural finish's L\* and hue against א.3 (L\* 56–66).
   - If it falls far outside, stop and report before spending anything.
2. **The table:** one edit on the clean plate with the rug (`layers/base-fb12s0.png` + `rug-…-fb12s0.png`), without the bowl and candlesticks.
   - **Model:** seedream 2K (650), or nano 4K (450) if enough. One retry in reserve.
   - **Clay:** at the real dimensions.
   - **Output:** a `coffee-table` layer at z 57, plus its contact shadow at z 56, using the frozen recipe.
   - **Fidelity:**
     - dimensions ±5;
     - a top 3–4 cm thick, with a hand-worked edge and visible grain;
     - two slab legs at the ends, open between them;
     - at least 60% air under the top.
3. **Stage-0 leftovers** (the rug braid seam right of centre, and the throw's edge at the old table's corner): if they still show at ×2 after the table is in, fix them in the same round, with one nano 4K edit (450). If the table covers them, skip it.
4. **The bowl and candlesticks, in code (0):**
   - The candlesticks move 18 cm left. The bowl moves to (0.46, 1.85).
   - Re-seat them on the oak at 38 cm, and re-cut their contact shadows with the same recipe.
   - Un-hide them in the defaults. This closes WM-T3.
5. **Rebuild** the defaults A, B and C, and the 1920 frames. Write a manifest (new name, as in stage 0).

## Acceptance (script, plus your own eye at ×2)
- RND2: 0 outside the table, its shadow, the moved items and the stage-0 regions.
- WM-G1 holds.
- At ×2: no halo, and the grain and edge read as real wood, not CG-smooth.
- The table reads light, not heavy, against the sofa. That is the owner's whole point.

## Outputs
- the layers, defaults and frames, and a `qa-sheet-fb12-stage1.jpg` (×2 table, ×1 room in sets A, B and C);
- the README, checks and `assets/manifest.json` (re-read before writing);
- one line for motion-agent: the final landing plate and sha.

## Fixed rules
- **var2:** never ask for codes or tokens. If var2 asks for re-auth, stop and report.
- **Supplier photos:** they stay in the scratchpad, and are used as references only. No supplier pixels in a layer.
- **Don't touch:** `data/`, `docs/`, `site/`, other rooms, or the arrival masters.
- **Git:** never `git stash`, `checkout`, `reset` or `commit`.
- **Disk:** it's tight; delete scratch.
- **The report (EFF2):** a Hebrew summary of at most 15 lines. Say what was done, the spend, the measures, and the regions for QA.
