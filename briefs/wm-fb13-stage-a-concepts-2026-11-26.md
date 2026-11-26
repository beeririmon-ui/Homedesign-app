# Brief: FB13 stage A, step 1: two concepts of the new living room M0-W (render-agent, 2026-11-26)

## The decision
The owner asked for a luxury design-magazine level living room, and to move forward without loops (FB13, FB14 in `docs/studio-rules.md`). Stage A is approved: expected 5,250, cap 6,500 for the whole stage. **This run is step 1 only: the two concepts, about 500.**

## Read
- `docs/proposals/wm-fb13-living-wow-2026-11-25.md`, sections 3.1–3.3.
- Your prep: `assets/renders/living-room/warm-modern/fb13-2026-11-25/` (clay, light maps, `camera-m0w-proposal.json`, README).

## The two concepts (flux-2 1K, about 250 each; one retry in reserve)
Both use the M0-W camera and clay, the rounded-arm sofa, the styling of 3.1, and **all four lamps on**.
- **A, "today's rules":** the light of today, with no direct sun, and the exposure 0.5 stop lower so the lamps carry the picture. It matches the front door's day (DL1).
- **B, "the last winter sun" (the designer's pick):** low winter sun through the glazing, a warm patch across the rug and sofa, and the olive's leaf shadow on the plaster. It needs the flipped compass you found; accept that for the concept.

## Must hold in both
- **The coffee table is Olia:** light natural oak, a thin top with two slab legs, open underneath. **Never the old dark walnut table on drum legs.** The owner was upset to see the old table again. Use the Olia layer or frame from `phase2-2026-11-10` as a reference.
- **The pendant is whole in the frame.** Use v0 0.555, as your clay found.
- **Products look like our SKUs** as far as a concept can: the rug, set B cushions and the Pecan throw, the travertine sconces, the floor lamp, the framed trio. Use the current frames as references. No invented hero objects, and nothing from the Bible's rejection list.
- **It must read as one photograph:** one light, real contact shadows, depth. No pasted look.

## Outputs
- `assets/renders/living-room/warm-modern/fb13-2026-11-25/concepts/concept-A.png` and `concept-B.png`, with the prompts and job json next to them.
- `concepts-sheet.jpg`: A and B side by side, labelled, at most 2400 px wide.
- Three lines in the README: what each concept shows, and what you'd fix in the hero render.

## Fixed rules
- **Spend:** at most 750 in this run (two concepts, plus one retry). Stop after the concepts.
- **var2:** never ask for codes. If var2 asks for re-auth, stop and report.
- **Scope:** don't touch `data/`, `docs/`, `site/` or other rooms.
- **Git:** never `git stash`, `checkout`, `reset` or `commit`.
- **Disk:** it's tight, about 1.4 GB; delete scratch.
- **Your report:** a Hebrew summary of at most 8 lines: the spend, what each concept shows, and your honest view of which is stronger and why.
