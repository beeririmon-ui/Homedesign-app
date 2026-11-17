# Brief: the arrival, Phase B, the rest (motion-agent, 2026-11-17)

## Why
Clip 2 (HDx → M0, take 1 + code repair r2) passed QA in round 2 (`qa/reports/2026-11-17-clip2/README.md`). CLIP2-R is closed as not needed, and the pilot cap stays 13,900. Spent 9,946; left 3,954; planned: clip 1a 1,296 and the bedroom 2,596, so the reserve is about 62. The four hall stills passed QA (`assets/renders/hall/warm-modern/hall-2026-11-17/`). Now the rest of S1, so the owner can see the whole arrival raw: D0 → the door opens in code → clip 1a to HT → clip 1b to HD → the 65° turn in code → clip 2 → reveal B.

**var2 is not authorized right now** (the owner has to reconnect it in claude.ai's connector settings). So do the 0-token parts first. Clip 1a is the last step and goes out only if var2 answers.

## The work, in order
1. **The door opens in code** (plan §6, `turn_door.py`), on D0 → D0o, the leaf from `d0-lock.json`. Use the frames and the duration in your timeline.
2. **Clip 1b in code** (plan §10.7, job `clip1b-code`): HT projected forward through the clay depth to HD, with the wall of HD. This is the manager's decision: 1b goes in code, and the model job (972) is only a fallback, which the manager would decide on after QA. Handle the 0.8% strip along the walnut edge (§10.7). The walk test on the result (route clip1b). The ends must be identical to HT and HD.
3. **The turn in code** (`turn_door.py turn`, HD → HDx, the joints gate, §10.5). p90 ≤ 2 px both ways, or exit 3 and stop.
4. **HT-L2 (backlog):** confirm whether 1a, 1b or the turn reads HT's right margin (from x 2643 on the canvas). If it does, say where. It becomes a medium finding for render-agent, so don't patch it yourself.
5. **The partial arrival:** assemble everything except 1a (`export_arrival.py`, desktop and phone previews), with 1a replaced by a clearly marked placeholder (a hold on D0o and a cut to HT, or a plain dissolve labelled "1a missing"). Name the files so nobody mistakes them for final.
6. **Clip 1a (D0o + leaf → HT, 4 s, kling-3-omni 1080p).** Go, with a cap of **1,296, one take, no retake**.
   - **Before sending:** reread `clip1a-d0o--ht.txt` with the lesson of clip 2 in mind. Remove any sentence asking the model to show something that neither end frame shows (clip 2's [DINING] paragraph caused the column and the glass). Write in the prompt file and `jobs.json` what you changed and why.
   - **The send:** `var2_estimate_cost` first (SPEND2). If var2 is not authorized or the price is above 1,296, don't send. Stop and report. Never ask for codes or tokens.
   - **If it renders:** the walk test (route clip1a, id 50 excluded 1.0–1.8 m, the herbs leaving at 2.15–2.40 m, checks 5 and 6), the bank with the end locks, exposure (the drop of about 0.6 in clip 1a is intended), and your own `repair_right_wall.py check`-style border check if you repair anything in code. Then the full raw arrival, desktop and phone, the same as in step 5 but with 1a.
   - **If 1a has a local defect:** a code repair (0 tokens) is allowed, as in clip 2. A second take is not: stop and report.

## Outputs
- `assets/video/transitions/warm-modern/` per clip (`clip1a-d0o--ht/`, `clip1b-ht--hd/` as code, `turn-hd--hdx/`, and `arrival-s1/` for the assembled previews), each with a short README: what was checked, the numbers, what's left, the frame ranges for QA to look at.
- Update `assets/prompts/transitions.warm-modern/jobs.json` (dated) and a short dated section in your proposal document.
- Working files go in the scratchpad. The disk allowance is limited: keep banks only while you need them, and say what you deleted.

## Fixed rules
- Tokens only for clip 1a, inside the 1,296 cap, one take. Nothing for the bedroom.
- No commits, no keys. Don't edit a binding document, `data/`, or another agent's document or stills.
- Return a short Hebrew summary: per part what was made and its checks, 1a sent or not (and the tokens), the preview paths, what QA should look at (frame ranges), and anything that needs the manager.
