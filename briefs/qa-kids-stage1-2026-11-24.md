# Brief: QA on the warm-modern boy's and girl's rooms, stage one (qa-agent, 2026-11-24)

## Why
The owner approved the kids' rooms (AP2-NEW). render-agent then rendered stage one of both rooms:

| Room | Frames | Spend | Products (manager count / V7Q6) |
| --- | --- | --- | --- |
| Boy | `K-boy-defaults`, with the throw in V1–V3 | 2,650 | 13 / 11 |
| Girl | `K-girl-defaults`, with the throw in V1–V3 | 1,200 | 12 / 9 |

The total spend was 3,850, against a cap of 9,700.

The girl's plate was derived in code from the boy's (ב.6). There was one extra send, GB1b, for the basket. These are new rooms, so this is a full stage-one QA.

## Inputs
- **The renders:** `assets/renders/boy/warm-modern/stage1-2026-11-24/` and `assets/renders/girl/warm-modern/stage1-2026-11-24/`. Each has:
  - a README, with the money, the count, the code fixes and the QA regions;
  - `K-<room>-defaults.png` and `-frame.png`, and `K-<room>-V2/V3.png` and `-frame.png`;
  - `plate.png` and `plate-compose.json`;
  - `layers/`, `shadows/`, `light/` and `manifest.json`;
  - `checks.json`, `jobs.json`, `qa-sheet.jpg` and `tools/`.
- **The clay:** `assets/blockout/house/framing/wm-kids-2026-11-24/`, with `selfcheck.json`.
- **The spec:**
  - `docs/proposals/wm-kids-rooms-render-2026-11-19.md`. Chapter ד overrides א–ג. The rejection lists are א.7 and ב.7, the sample slot is ד.4, the count is ד.5 and safety is ד.7.
  - The kids chapter in `docs/design-bible/warm-modern.md` (1.1), including the olive band exception #A8A88E for the boy, and #E8D5CC for the girl.
- **The products:** the cards in `data/products/` (kids). The SKU comes from `room_variants` "warm-modern.kids-boy" or "warm-modern.kids-girl", or from the card's default.
  - The SKU photos are in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`, with `picks/new-rooms-photo-check.json` and `picks/ae-round-photo-check.json`.
  - Read them only with `python3.12 -I`.

## What to check (0 tokens)
1. **Fidelity, per product:**
   - shape, colour (R5 on lit areas) and size against the card, the SKU photo and the clay;
   - most attention to the items rescaled or recut in code: the silk pumpkin lamp at 30 cm, the throws with their fringes cut to 2.75 cm, and the girl's basket (GB1b) against its 40×45 cylinder with two long loop handles;
   - also the cars (2 of 3 drawn), the teddy (moved about 100 px from the clay box), the bunny's ears, and the prints A, B and C (pasted in code);
   - V1–V3 of the throw in both rooms: does each match its SKU photo, and does each read as a variant?
2. **The rejection lists and the Bible:**
   - **The bands:** #A8A88E for the boy and #E8D5CC for the girl. render-agent reports dE00 0.14–0.21 per wall.
   - **The girl's plaster above the band:** HSL H 31.5, against the rule of 32–40. render-agent says this is a bounce from the pink, not paint. Accept or not?
   - **Safety (ד.7):** the Roman blind 868827 is in the frame, but its sale is blocked (no EN 13120). It must show **no cord and no chain**. Check it in both rooms. No toy is sold without EN 71, so flag any product dot this would affect.
3. **The layers (RND2):**
   - rebuild per each `manifest.json`;
   - 0 pixels outside alpha, shadow and light, in the defaults, V2 and V3;
   - V2 and V3 change only inside the throw layer;
   - shadows sit one z below their product, and light layers use screen;
   - the black point is within WM-G1 (reported boy 11.58, girl 12.35).
4. **At ×1–×2, per region:** first the regions in both READMEs, then the whole frame. Also check what the manager saw in the girl's frame at ×1:
   - **(a)** A strong white bloom on the pink band to the right of the bed pillows, at about x 770–1250 and y 400–760 in 1920×1080. In the frame the band reads as washed out to white there, unlike the boy's even band. Is it plausible light from the window and lamp, or a plate defect?
   - **(b)** A grey-green vertical strip on the window-wall pier, left of the bed, at about x 385–440 and y 390–560. This could be a remnant of the boy's olive band left by the code derivation.
   - **(c)** A greenish vertical line behind the desk's left leg, at about x 1295–1320 and y 650–930. Same suspicion.

   Then the whole frame: does each room read as the same house as the living room, the bedroom, the work room and the kitchen, at magazine level (FB5) and lived-in (FB6)? And as "the parents' house at a child's scale"?
5. **The count:** each product once per room, plus V7Q6, against ד.5. List which products are missing to reach 20 in each room (the gaps in ד.6).

## Outputs
- `qa/reports/2026-11-24-kids-stage1/README.md`: pass or fail per item and per room, with numbers. Low findings go to `status/backlog-low.md` as K-L1 and on.
- **A status line per room:** either "עבר QA (חדר הילד/הילדה שלב 1; לבעלים לאישור 3; לא לאתר לפני רישום 1.3.9)", or the blocking findings, saying for each whether code can fix it.

## Fixed rules
- 0 tokens, no var2, no commits, no keys.
- Don't edit a binding document, `data/`, or another agent's files.
- Never run `git stash`, `git checkout` or `git reset`.
- Keep scratch files small and delete them when done. The disk is tight (about 2.4 GB free).
- **Return a short Hebrew summary:** the five items per room, pass or fail with numbers, and your judgment on (a)–(c).
