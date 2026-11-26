# Brief: FB13 stage A, steps 2–6: the M0-W plate, the hero frame and the layers, direction B (render-agent, 2026-11-26)

## The decision
Stage A is approved (FB13-A, FB14 in `docs/studio-rules.md`). The concepts are done: `assets/renders/living-room/warm-modern/fb13-2026-11-25/concepts/`. **Direction B, "the last winter sun", goes ahead:** it's the designer's pick, and yours. The owner has the sheet and may still redirect; if the manager messages you, follow that.

## The task: `docs/proposals/wm-fb13-living-wow-2026-11-25.md`, section 3.2, steps 2–6
1. **P-W,** the empty-room plate in the hero light (seedream 2K, 650).
2. **H-W,** the hero frame with every default product in one light (seedream 2K, 650, up to 9 SKU references).
3. **Gate, your own check of H-W before any further spend.** If it fails after one retry, stop and report with the frame.
   - **The table:** it is Olia. Never the old walnut table.
   - **The products, true to our SKUs:**
     - the rug is our braided wool rug; the concept drew a woven rug with a border, which is wrong;
     - the set B cushions, including the long lumbar one;
     - the Pecan throw;
     - the travertine sconces, the floor lamp and the pendant;
     - the vase and the newspaper holder.
   - **The light:**
     - all four lamps read as lit, the sconces too; they barely did in concept B;
     - plaster in shade at L 70–78; the concept was about a stop too dark;
     - plaster in sun at L 92–95;
     - black point at L 9–11.
   - **The room:**
     - the sofa has soft rounded arms, with no pillow-arm seams;
     - the plaster is smoother than in the concept;
     - no invented niche, socket or object.
   - **The pendant:** whole, with a clear margin.
   - **One photograph:** real contact shadows, bounce and depth.
4. **The three group edits on H-W** (nano 2K, 400 each): the table group, the window group, and the left floor group. Do only the ones needed.
5. **"H-W without the table group"** (nano 2K, 400), so the table stays a swappable layer (FB12-T).
6. **The prints** in code. Then **extract the layers** from the hero (split by the plate, multiply and screen) and apply the shared finish (`assets/renders/tools/finish/`). No refit of any product after rendering.
7. **Rebuild** the default frame from the layers, and run the pasted test and RND2-style checks on it.

**Not in this run:** step 7 of the proposal (the cushion sets A and C).

## Outputs, in `assets/renders/living-room/warm-modern/fb13-2026-11-25/`
- `plate-PW.png`, `hero-HW.png`, the layers and a manifest, and `default-frame-m0w.png` at 1920×1080.
- `qa-sheet-m0w.jpg`: the hero at ×1; ×2 crops of the table, the sofa and the sconces; and the old M0 beside the new one.
- The README, checks, and `assets/manifest.json` (re-read before writing).

## Fixed rules
- **Spend cap for this run: 3,950.** Stage A has used 750 of 6,500. Stop and report before going over.
- **var2:** never ask for codes. If var2 asks for re-auth, stop and report.
- **Supplier photos** are references only, in the scratchpad.
- **Scope:** don't touch `data/`, `docs/`, `site/`, other rooms, or the old `phase2-2026-11-10` files.
- **Git:** never `git stash`, `checkout`, `reset` or `commit`.
- **Disk:** it's tight, about 1.4 GB; delete scratch as you go.
- **Your report:** a Hebrew summary of at most 10 lines: the spend, what passed the gate, what's still off, and the regions for QA.
