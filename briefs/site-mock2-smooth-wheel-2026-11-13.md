# Brief: MOCK2, smooth motion and a wheel of products on their own (frontend-dev, 2026-11-13)

## Why
The owner tried MOCK1 (`briefs/site-mock1-wow-tour-2026-11-12.md`, done at `90b3471a`) on his phone. His feedback is rule FB1 in `docs/studio-rules-digest.md`, under EFF1.6. Read it first. In his words:
- "The motion isn't smooth, there are jumps… **first of all I want the interface to work smoothly.**"
- "In the wheel, show the product as if folded, not laid out and cut from the picture… **the products on their own, not a piece of the living room.**"
- "It shouldn't look like a bad Photoshop cut": in the Nordic room, after swapping the throw and the cushion covers, lines stay around the products.

A real living room → bedroom transition and new product renders are separate, paid work, and are not in this sprint.

## 1. Smooth motion. This is the sprint.
MOCK1 could not prove smoothness: the build machine has no GPU, so its frame rates measure the machine. The owner's phone shows jumps. Find the causes by reasoning and instrumentation, and remove them by construction.

**Suspects to check first, in this order:**
1. **Decode and upload inside animations.** No image decode, texture upload, shader compile or program link may happen during an animated frame. Decode off the main thread (`createImageBitmap`), upload every texture and warm every shader an effect needs **before** its first frame. The door waits (with a quiet progress hint) until the room is ready to animate.
2. **Layer sizes on phones.** The tour ships only 2720-wide layers (`media/tour/.../*.2720.webp`), about 25 of them, to a phone. Ship phone-sized encodes (the same encoding gate applies) and pick by viewport and DPR. This also cuts memory, which is a jank source on its own.
3. **Per-frame work.** One `requestAnimationFrame` loop, time-based interpolation, no allocations in the loop, no layout reads or writes per frame. Move what can be a compositor transform or opacity to CSS on its own layer, instead of recompositing the full canvas.
4. **Resolution while moving.** Render at a reduced resolution during motion when the frame time rises, and return to full resolution at rest (the settled frame must stay pixel-exact, as in MOCK1).
5. **DOM overlays.** Labels, rings and the wheel animate with transform and opacity only. No big blurred or filtered areas on phones.
6. **Timers and loading mid-flight.** Nothing lazy-loads during an effect. Effects never start from `setTimeout` chains.

**Instrumentation (kept behind the temporary control):**
- Counters per effect: decodes, texture uploads, shader compiles, layout passes, long frames (> 20 ms and > 34 ms), and the worst frame.
- A one-tap **"copy report"** in the temporary control: device, browser, viewport, DPR, GPU string, and the per-effect table, as plain text the owner can paste into the chat.

**Acceptance for smoothness (provable on this machine):**
- During every effect: 0 decodes, 0 texture uploads, 0 shader compiles, 0 forced layouts. A test fails if any counter is above 0.
- Script time per frame ≤ 4 ms on average and ≤ 8 ms at the worst, with the CPU throttled ×4.
- On the phone profile, composited megapixels per frame while moving ≤ the number you set and justify.
- GPU memory for the room's textures on the phone profile: report it, and say what it was in MOCK1.
- The seams and the settled-frame tests from MOCK1 still pass.
- Say plainly what still can't be proven without a real device. The owner's pasted report closes that.

## 2. The wheel shows the product on its own
Never a crop of the room. For each variant in a wheel (the tour's, and the room tool's), in this order of preference:
1. **Our own studio image,** where one exists and passed QA. Today that is the IMG1 pilot, in `assets/renders/products/img1-pilot-2026-11-12/` (`source-record.json` says which files passed QA: the vase and the throw; the stone sconces did not). Use only files whose record says QA passed.
2. **Otherwise, the product's own layer,** alone: the RGBA layer trimmed to its bounds, on a plain studio card with a soft neutral ground shadow. Nothing of the room around it.
3. **Mark which variants need a real studio shot.** Textiles shown in their in-room pose (throws, cushions, curtains, rugs) are the ones the owner pointed at. Write the list for the manager: slot, variant, card id.
- The card's look (background, shadow, padding, size in the wheel) is a default for master-designer to review. Keep it quiet and consistent across products.
- Supplier photos are not used in the wheel.

## 3. The Nordic room's cut lines
The Nordic living room's layers are the old temporary ones; real layers need rendering, which is a separate decision. In this sprint:
- Find out whether the lines the owner saw are in the files (halo or matte in the temporary layers) or come from the engine (filtering, premultiplied alpha, mip levels, an encode at the wrong size). **If any part is the engine, fix it**, and check the warm-modern layers for the same fault at ×1 and ×2.
- If it is the files only: say so with two crops, and mark the old Nordic tool in the mock-up as "תמונות זמניות" so it isn't judged as final.

## Out of scope
- The door's design, copy and layout; the choice of reveal; the bedroom; a real room-to-room transition.
- Hardening items from `status/backlog-low.md`.

## Acceptance
- **The repo's checks:** `npm run test:all`, check:config, check:rights, check:promises, the encoding gate (including the new phone-sized layers), both builds, the budgets unchanged.
- **New tests:** the zero-counter test per effect; the wheel image source per variant (never a room crop, never a supplier photo); the phone-sized layer selection.
- **A fresh `npm run preview:artifact`,** inside the size limits, for the manager to publish to the same page.
- **Evidence:** `qa/reports/2026-11-07-site-track/mock2/` with a README: the cause found for each kind of jump, the counters before and after, the memory and megapixel numbers, the wheel's image source per variant, the studio-shot list, and the Nordic finding.
- **Working files in the scratchpad (EFF1).**

## Fixed rules
- No commits, no var2, no keys, no network beyond npm. Every `npx` with `--no-install`.
- Don't edit `data/`, the selection, the slots file or any binding doc.
- If your context runs low, stop where the checks are green with the artifact build working, and write "where I stopped".
- Return a short Hebrew summary: what caused the jumps and what you changed, the numbers, what the owner should do on his phone, and your open questions with the default you took.
