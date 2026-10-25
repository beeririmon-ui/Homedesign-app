# The Nordic house in renders: a wow recipe, all 8 rooms, and the transitions (2026-10-24)

The owner (2026-10-24): "בואי נתחיל לייצר את ההדמיות לשאר החדרים בנורדי, כדי שנוכל להתחיל לעצב את הזרימה של האתר. הדוגמא שעשינו לא נראית וואוו ואני רוצה שהמעברים בין חדר לחדר יהיו מדוייקים, אז נעשה את כל החדרים בנורדי ונתחיל לעבוד על המעברונים שיהיו וואוו".

Recorded in `docs/studio-rules.md` ז (2026-10-24). The binding sources, unchanged: `docs/house-plan.md` + `.json` 1.1 (cameras, frames, transitions, rail, build order), `docs/design-bible/nordic.md` 1.7.2 (quality bar א.1, light, "גריידינג ותנועה"), `docs/design-bible/nordic-dining.md`, `docs/skeleton-spec.md`, `docs/rooms/*-nordic-2026-10-11.md` (per-room composition), `data/slots/*.json`, `docs/var2-models.md`.

## 1. What is wrong with what we have
Two living-room assets exist and both miss the bar (`docs/studio-rules.md` א.1: "מגזין עיצוב ברמה הכי גבוהה", every frame "וואו"):
- `assets/renders/living-room/nordic/m0/pilot-v4.1/m0-pilot-b-graded.png`: the shell plus three fixed pieces. Flat frontal daylight, no modelling of the walls, an over-exposed window, no depth, no life. Shot at 10:30 / 5000K while the Bible asks for 15:00 winter / 4600K (Bible changelog 1.4: "נדרש גריידינג חדש או פיילוט M0 חדש"; never done).
- `assets/renders/living-room/nordic/styled-preview-r2/styled-preview.png`: a catalogue mock-up. Generic prints, a stock olive tree, a knitted pouf, even light everywhere, no shadows, no focal point, the sofa and armchair look like mass-market defaults.

Neither has: directional light with real shadow shapes, the back-wall falloff the Bible specifies (L 92–95 → 82–86), material depth (oak grain, linen weave, plaster), layered styling with a hero, a photographer's framing, or the grade (raised black point, soft roll-off, desaturated 10–15%).

## 2. The program, in three phases with two owner gates
**Phase A: the wow recipe (now).** Living room M0 and the hall H0 (the site's opening frame, U1), as image-to-image from the binding clay (`assets/blockout/house/framing/round2/*.png` and `assets/blockout/living-room/m0-clay-4k.png`), so the geometry, camera and lens stay exact. Three recipes, drafts at 1K or 2K, then the owner picks. **Gate 1: the owner picks a recipe** (studio rule א.5).

**Phase B: the master frames of all 8 rooms**, in the house-plan build order: kitchen-dining (D1, D2), hall (H0), corridor (C0), master (MB0), boy (K-boy), girl (K-girl), bath (B1, B2), work (W0), plus the living M0 redone with the recipe. Each frame: shell + fixed furniture + the room's default products in one image (`docs/rooms/<room>-nordic-2026-10-11.md`; where a slot has no default, the filler rule applies). Layers and variants come after the flow is designed, not now. 2K drafts for approval, 4K masters after approval. **Gate 2: the owner approves the 8 rooms** (approval 3 in CLAUDE.md).

**Phase C: the transitions**, exactly as `house-plan.json` → `transitions` (10) and `rail` define them: first frame and last frame from the approved masters, kling-3 pro or ltx-2.3, the pan/dolly segments, play times per `transition_playback_U10`, speeds and easing per the Bible. "Precise" means the path, the heading and the jamb clearance in the plan, checked by QA against the clay. Two attempts per transition at most without the manager.

## 3. Phase A: what each agent does
### master-designer: `docs/render-recipe-nordic-2026-10-24.md` + prompts
1. **The critique**: 8–12 lines on why the two assets fail, against the Bible's light, grading and composition rules. Specific, not general.
2. **The recipe**: light (15:00 winter sun, 4600K, the window as the key, the falloff, the lamps "lit" per the Bible's lighting hierarchy), lens and camera (24 mm, 120 cm, level, per house-plan), materials (the Bible's palette and textures, with the words that make models render them: oiled white oak plank grain, slubbed linen, lime-plaster matte, travertine), styling density (magazine 2, S11), the hero of each frame (house-plan `hero`), the grade (the Bible's table), and what to forbid (bloom, HDR, generic décor, stock plants, text).
3. **Three prompt variants for M0** and one for H0, each ≤ 3,900 characters, each starting with the clay-lock paragraph (keep every wall, opening, camera, lens, furniture exactly as the clay). Write them as files in `assets/prompts/recipe-v5.nordic/`: `m0-A.txt`, `m0-B.txt`, `m0-C.txt`, `h0-A.txt`. The variants differ in **model and emphasis**, not in layout:
   - A: photoreal, fine materials (flux-2 at 2K);
   - B: long literal prompt, premium control (gpt-image-2-5, quality sunburst, 2K);
   - C: the 4K path (nano-banana-2, 2K draft).
4. **The 7 other rooms**: for each, confirm that `docs/rooms/<room>-nordic-2026-10-11.md` + the Bible give enough to write the master-frame prompt (fixed furniture, defaults, filler, hero). List what's missing per room in one table. Don't write those prompts yet.
Rules: don't edit binding docs; propose Bible changes as questions.

### render-agent, in two steps
**Step 1 (now, in parallel with the designer): preparation, no renders.**
- Report the var2 balance and the per-job costs for flux-2 2K, gpt-image-2-5 2K sunburst, nano-banana-2 2K/4K, kling-3 pro and ltx-2.3 (`var2_list_models`, `var2_estimate_cost`). Never print keys.
- Check that every master frame has a clay: list the 16 cameras of `house-plan.json` against `assets/blockout/house/framing/round2/` and `assets/blockout/living-room/`. Name the frames with no clay (D1/D2/B1/B2 and the hall H0 vs H-B-lit, etc.).
- Set up `assets/renders/<room>/nordic/recipe-v5/` and the prompt-record template (`assets/prompts/m0.nordic/m0-pilot-a.json` is the shape).
- Write `assets/renders/README-recipe-v5.md` with the plan for step 2 and the cost of Phase A.
**Step 2 (after the designer's prompts exist): the drafts.**
- M0 × 3 recipes and H0 × 1, image-to-image from the clay, 2K (A, B) and 2K (C). One attempt each; a second only if the first broke the clay lock. Record every job as a prompt record. Apply the Bible grade in post (`grade.py` exists in pilot-v4.1) and keep both raw and graded.
- Build `assets/renders/living-room/nordic/recipe-v5/compare.jpg`: the 3 M0 drafts, the old pilot and the old styled preview, labelled, plus H0.
- Report cost used.
QA (qa-agent) then measures the clay lock (edges, furniture positions) and the grade values against the Bible table; the manager shows the owner the sheet.

## 4. Phase B and C: sizing (for the owner's budget decision, after Gate 1)
`house-plan.json` → `credits_estimate` (1.1, mixed route): about 415,000 var2 tokens for the house without the living room, plus about 59,000 for the transitions, ±15%. Those figures assume full slot variants; **the master frames alone** (one 2K draft + one 4K master per frame, 11 frames, with one retake) are roughly 11 × (≈480 + ≈420) × 1.5 ≈ 15,000 tokens. The transitions at kling-3 pro: 10 × 2 attempts × ~4 s × 324 ≈ 26,000. The render-agent refines this in step 1.

## 5. Rules
- No 4K and no series before the owner has seen the Phase A sheet (א.5).
- The clay is the layout: nothing moves. A draft that moves a wall, an opening or a fixed piece is rejected, not fixed in words.
- Products in frame are the room's real defaults; fillers only per the filler rule. No invented décor.
- Never print keys or tokens. Only the scripts and the MCP touch var2.
- Prompt records for every job; raw and graded files kept; no commits.

## 6. Phase D: the product-swap method (added 2026-10-24)
The owner (2026-10-24): "גם החלפת המוצרים עושה מעין כתמים על התמונה ולא נראה מושלם, אז או שנמצא שיטה אחרת או שנעשה חיתוך מדוייק לכל מוצר מתחלף".

Today's swap (a variant layer composited over the room) leaves blotches: a halo or a grade step around the product, a shadow that doesn't match, texture that changes outside the product (`assets/qa/swap-diff/*.diff.png`). The site needs combinations (any cushion with any sofa cover with any rug), so whole-frame renders per variant can't replace layers; the layers must be **pixel-exact outside the product**.

**A method test on one frame and two slots** (the recipe winner's M0, or the old styled preview until it exists; slots: `vase` on the sill and `cushions` on the sofa, one variant each), three methods, same prompt, same grade:
1. **Region edit:** `grok-imagine-image-2` segment-map (free) → segment-edit of the product's segments only; every other pixel untouched by design. Check its resolution ceiling (1K/2K) and whether the edit can be lifted to the 4K master by a mask.
2. **Diff cutout:** a full-frame image-to-image render of the variant under the clay lock → a mask from the diff against the base (threshold + morphology) intersected with a segmentation of the product → alpha matting with a 2–4 px feather → composite; the shadow comes with the mask because the diff includes it.
3. **Reference cutout:** the product rendered in isolation (studio, remove-background) and placed by the slot's geometry, with a separately rendered contact shadow. The current approach, as the control.

**Measure, per method (qa-agent, the `swap-diff` tooling):** residual difference outside the product mask (mean and max ΔE, must be ~0), halo width at the edge in px, shadow continuity, grade match (L/S of the wall next to the product before and after), and the look in the Studio compare at zoom. **Deliver:** a sheet with the three results and the numbers, and a recommendation. The owner decides the method (decision RND2) before the series of layers. Cost: about 6 jobs at 1K–2K, under 3,000 tokens.

## 7. Phase B, started 2026-10-25: the master frames of the other rooms
The owner (2026-10-25): "מה עם שאר החדרים?". Gate 1 is taken as **recipe B (gpt-image-2-5, quality sunburst)**, the recommendation of the designer and the manager, unless the owner says otherwise. No 4K and no series beyond the 2K drafts until the owner approves the room sheet (Gate 2).

**Frames (house-plan 1.1, build order):** D1, D2, H0 (retake), C0, MB0, K-boy, K-girl, B1, B2, W0, and M0 v6 with the verdict's five prompt changes. 11 jobs at 2K (600 each), one retake each at most: **cap 12,000 tokens** for this batch.

**Products in frame.** For each slot of the frame: the locked default; else the best catalogue candidate for nordic with fit ≥ 7 (a real card in `data/products/`, named by id in the prompt file's `#` header, flagged "candidate, not locked"); else explicitly empty, and fillers only per the filler rule. Hero slots get a candidate whenever one exists: an empty hero pulls other objects into its place (the M0 lesson). Every small product is described with its size relative to the furniture next to it, and a close-up reference of the product is attached where the card has a usable image.

**Clay first (0 tokens).** The round-2 clays predate the 1.1.x frame fixes and carry placeholders for empty slots. Before the drafts, the render-agent rebuilds each frame's clay at 3840×2160 from `assets/blockout/house/` (`build_house.py`, `framing_r2.py`): the 1.1.x camera values from `house-plan.json`, placeholders **only** for the slots that will hold a product in the draft (per the designer's per-frame list), the S12 lamps lit, neutral albedo, and the hall 2/3 stop darker than the living room seen through the opening (verdict §3). The living room seen from H0 and C0 is the M0 clay.

**Prompts.** The designer writes `assets/prompts/recipe-v5.nordic/<frame>.txt` per frame (≤ 3,900 characters, the clay-lock paragraph first, recipe B with the verdict's five changes, the room's Bible annex and `docs/rooms/<room>-nordic-2026-10-11.md`), plus `m0-v6.txt`, and a per-frame placeholder list for the clay in `docs/rooms-render-plan-2026-10-25.md`.

**QA, per draft:** clay lock (edges and furniture within 0.5% of the frame), each product within ±15% of its slot box, the Bible's light targets as amended if BIB1 passes, no invented objects. A draft that fails the lock or invents objects gets its one retake; otherwise it goes on the sheet as is, with the finding.

**Deliver:** `assets/renders/<room>/nordic/recipe-v5/<frame>.png` and `-graded.png`, prompt records, measurements, and one sheet `assets/renders/house-nordic-sheet-2026-10-25.jpg` with all 11 frames in the house-plan order, labelled, for the owner.
