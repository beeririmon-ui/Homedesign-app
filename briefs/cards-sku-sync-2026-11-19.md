# Brief: sync the cards' rendered SKUs (sourcing-agent, 2026-11-19)

## Why
QA and the photo checks found cards whose `in_room` or `default_sku` points to a different variant than the one the designers picked and render-agent rendered (HP-I1 in `qa/reports/2026-11-19-hall-products/README.md`). If they stay that way, the site would sell a different variant from the one shown. This task is data hygiene only.

## The source of truth (the designers' latest chapters)
- `docs/proposals/wm-house-20-2026-11-19.md`, chapter 8 (8.1–8.3).
- `docs/proposals/wm-kitchen-dining-render-2026-11-19.md`, chapter 10.
- `docs/proposals/wm-work-render-2026-11-19.md`, chapter 10.
- `docs/proposals/wm-kids-rooms-render-2026-11-19.md`, chapter ד.
- `qa/reports/2026-11-19-hall-products/README.md` (HP-I1) and `qa/reports/2026-11-19-master-mb1/README.md`, the note on the rug.

## Known items (not the full list; check every SKU the chapters name)
- **The hall wall light 332886-hall:** A (…270), not B (…272).
- **The hall basket:** cream `CJYD195774302BY`, not jute (…305EV).
- **The waffle throw** (hall bench): Khaki (…213MN), not white (…201AZ).
- **The hall console vessel 906575:** colour 02 (`12000050733388959`).
- **The moon jar:** StyleG (black) where the kitchen uses it; StyleC (`CJJT276473903CX`, white) where the work room uses it.
- **The burnt bowl:** Fire Color (`CJJT276748902BY`).
- **The bookends:** walnut arch, SKU 9 (`12000058962195729`).
- **The work rug:** 160×230 (`CJJT211801816PK`).
- **The bedroom rug:** the MB1 rug is 200×300, while the card's `in_room` points to the living room's 230×330. Mark both rooms' sizes.

## The task
- **Which fields:** for each card involved, set the per-SKU `in_room` flags (or the card's equivalent field per `data/product-card.schema.json`) and the default SKU, so they match what each room uses.
- **Shared cards:** where a card is used in several rooms with different variants, mark each and say which room uses which, in `notes`.
- **Nothing else changes:** no prices, scores or images. Add one dated line to each card's `notes`: "2026-11-19: in_room synced to the rendered/picked variant (<room>)".
- **The log:** write the list of changes to `data/leads/sku-sync-2026-11-19.md` as card, field, from, to and source chapter.
- **Uncertainties:** if a chapter is unclear or two chapters disagree, don't guess. List it in the log as open.

## Fixed rules
- Edit only those fields in existing cards, plus the new log file. No web access is needed. No binding documents, no slots, no commits, no keys.
- Return a short Hebrew summary: how many cards changed, and anything left open.
