# Brief: MOCK1, the wow-tour mock-up (frontend-dev, 2026-11-12)

## Why
The owner's new direction (rules TOUR1, TOUR2, MOCK1 and his answers, in `docs/studio-rules-digest.md` under EFF1.6): the site is a high-tech virtual tour that opens at the front door, and everything in it has to be "wow". Before any credit is spent on real door frames and room-to-room transitions, he wants **a mock-up that runs in the site**, "to see that we really speak the same language". He will judge it by eye, on his phone and on a desktop.

This is the first sprint that is about what the visitor sees. It replaces the hardening track, which is paused (EFF1.1).

## The design source
`docs/proposals/wow-tour-experience-2026-11-12.md` (master-designer). Read all of it; it is the spec for this sprint: the storyboard, the three reveal concepts (A "burst", B "depth scan", C "dim highlight"), the wheel swap, the style change, the temporary door screen, and the motion language (durations, easing).
- Where it deviates from `docs/skeleton-spec.md` (a 0.45 s variant swap, a ~3 s first style change), build it as the designer wrote. The skeleton is updated after the owner approves the mock-up.
- The designer's "empty house on the way" idea (products hidden while moving between rooms) is the owner's call. Build what the mock-up needs and leave it switchable.

## Scope: what the mock-up shows, in this order
1. **The door (temporary, in code).** The designed door screen from the brief: a portal with the real empty living room inside it, and a button to the living room. It grows until it fills the screen and you are in the room. Mark it "זמני" discreetly.
2. **The warm-modern living room with its final product layers.**
   - Wire the phase 2 layers into the engine: 12 default products and 10 variants, each with its shadow, from `assets/renders/living-room/warm-modern/phase2-2026-11-10/` (`layers/manifest-r9.json`; QA passed R9, `qa/reports/2026-11-12-wm-phase2-r9.md`).
   - Today the site builds only the cushion sets for this house. The bowl stays at its current temporary point. Bowl 3 and the iron candle holders stay out.
   - Pendant 2 is in the wheel as it is (R9); its known banding is parked.
3. **The reveal: "what is for sale here".** All three concepts, switchable without a reload (a small temporary control, and `?fx=a|b|c`). After any reveal settles, the frame is exactly the true composite: no effect may leave a product's colour or shape changed.
4. **The product close-up and the wheel.** A press on a product moves in on its area, and the wheel swaps variants in the room with the designer's recommended swap effect (the "scan wipe"). Offer the brief's alternatives behind the same temporary control if they are cheap; otherwise the recommended one only.
5. **The style change, warm-modern ↔ Nordic,** in the living room: the designer's two concepts (the first-time "strip and dress", and the repeat "material wave"). The Nordic room's layers are the temporary ones it has today; that is known and accepted for the mock-up.
6. **Last, and only if it lines up: moving to another room.** A short separate segment approximated in code from the existing Nordic stills (the brief's chapter 8 says which), clearly marked "זמני". If the stills don't line up well enough to show rhythm and direction honestly, don't ship the segment: say so, with one screenshot of why.

## How the owner will see it
- **The claude.ai artifact preview:** make `npm run preview:artifact` produce the mock-up (the door is its first screen), inside the artifact page contract your `finalize-artifact.ts` already enforces. The manager publishes `site/dist-artifact/`. Keep it comfortably inside the size limits (16 MB for the page, 15 MB per media file) and say what you left out to get there.
- **Screen captures:** record the flow with Playwright at a phone size and at 1280: one capture per reveal concept (door → room → reveal), one of the close-up and wheel swap, and one of the style change. Save them as mp4 if ffmpeg is available, otherwise webm, in the evidence folder. These go straight to the owner, so capture at real speed and don't crop.

## Quality bar
- **Smoothness is the point.** Measure the frame rate of every animation on a mid-range phone profile (CPU throttled ×4) and on desktop. Report dropped frames per animation. Anything that stutters is a failure of this sprint, not a detail.
- **No jump at any seam:** the door into the room, the reveal's last frame against the settled composite, the close-up in and out, the swap, the style change. Check each seam by pixel difference at its first and last frame.
- **`prefers-reduced-motion`:** every effect has a calm fallback (a short fade).
- **The budgets stay:** first load ≤ 3 MB on the phone, room JS ≤ 80 KB (the goal is ≤ 74). Lazy-load effect code that isn't needed for first paint. If the phase 2 layers break the phone budget, propose the encoding and loading order; don't raise the budget.
- **Everything stays behind `HD_PUBLIC=0`.** The public build is unchanged.
- **Accessibility:** the door button, the room buttons, the wheel and the temporary effect switch all work from the keyboard.

## Acceptance
- **The repo's checks:** `npm run test:all`, check:config, check:rights, check:promises, the encoding gate on the new layers (this closes QA's F7), and both builds.
- **New tests:**
  - the settled frame after each reveal equals the plain composite (pixel-exact, or within the engine's existing tolerance);
  - each seam listed above;
  - the phase 2 layers load and swap;
  - the reduced-motion fallbacks.
- **Evidence:** in `qa/reports/2026-11-07-site-track/mock1/`:
  - a README with the frame-rate table, the seam checks, the weights, what is temporary, and what you left out;
  - the captures.
- **Working files stay in the scratchpad (EFF1).** Only the code, the evidence and the captures go into the repo.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm. Every `npx` with `--no-install`.
- Don't edit `data/`, the selection, the slots file or any binding doc. Don't copy a supplier image anywhere.
- New copy: only the few words the door and controls need. Take defaults, keep them short, and list them for master-designer.
- If your context runs low, stop where the checks are green, with the artifact build working for whatever part is done, and write a "where I stopped" section.
- Return a short Hebrew summary covering:
  - what the owner will see, step by step;
  - the frame rates;
  - what is temporary;
  - your open questions with the default you took for each.
