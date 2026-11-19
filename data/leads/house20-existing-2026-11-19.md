# House20, existing rooms: sourcing ranking (sourcing-agent, 2026-11-19)

Brief: `briefs/sourcing-house20-existing-2026-11-19.md`. Lines: chapter 7 of `docs/proposals/wm-house-20-2026-11-19.md`. Cards are in `data/products/<room>/<slot>/` with `status: candidate`.

## Bottom line
- **16 new cards on 5 of the 28 lines** (23, 24, 25, 16, 18). The target was 6-10 per line; only line 23 reached 7. **Not reached on 23 lines**, mostly for lack of time and reach, not because the market is empty (see per line).
- **What this run could do:** web search and single-page reads only. No shell, so no downloads, no `scripts/sourcing/*`, no `seen.json` check or update (new files only), no `gaps.py`. AE and CJ API keys not set: **no AliExpress or CJ search was run for any line.**
- **What worked:** IKEA Israel product pages (ikea.com/il/he/p/...) and Fox Home (foxhome.co.il, including its search pages) are readable. **Home Center, Zara Home Israel, Wolf and Badger: 403 or unreadable. Kave Home: 429.** Search engine results for Israeli stores were thin and mostly Home Center listings that could not be opened.
- **IKEA is alternative-only (rules 7.1).** Almost every priced card is IKEA or Fox Home: no Israeli maker with a serial, priced, photographed item was reached.
- **Cards store no keys, phone numbers or business ids. Supplier images were not downloaded** (no shell); the scratchpad folder `sourcing-house20/` was not created. Photo URLs are in the cards. Image rights are `unclear` throughout.
- **Not registered in `data/sources/seen.json`.** Items opened this run, to register with `build_seen.py`: IKEA Israel 80047635, 40399045, 00612279, 50210128, 00385314, 10517682, 50515105, 60561875, 89508868 (read, no card); IKEA Ireland 80428461; Fox Home 0315316361, 159440100, 0333790300; amoslighting ORT3275; pooky portreath.

## Per line (blocking first)

### Blocking lines
**23, entrance `door-mat` (D0 coir mat, about 60x90, plain natural): 7 cards.**
1. `door-mat-ikea-aebelnaes-coir-60x90`: the exact size (60x90, 99.5% coir, 15 EUR), but read on the Ireland page. The Israel listing was not found: **availability and ILS price unverified.**
2. `door-mat-ikea-triabo-coir-40x70` (49 ILS, Israel page read, plain natural, closest in proportion among verified-in-Israel).
3. `door-mat-ikea-sindal-coir-50x80` (45 ILS, Israel page read, largest verified in Israel, 12 mm).
- Others: TRAMPA 40x60 (45), KONTANTER 40x60 (49, "natural style", surface unverified), two Home Center listing-level cards (WELCOME lettering, PVC backing; Kedem 8 arches 45x75, 29.90), both without photos.
- No Israeli store with a 60x90 coir mat was found. Strongest route: confirm the IKEA 60x90 in the browser or find an Israeli 60x90.

**24, entrance `exterior-wall-light` (D0 bronze-espresso cylinder, up and down, about D7 x H18, IP44+, wired): 4 cards.**
1. `exterior-wall-light-amos-dar-ortega-brass-up-down-ip65`: solid brass, aged brass, D 8.5 x W7 x H 21, IP65, up and down, 121 GBP. **Closest to the drawing.** UK shop: Israel shipping and CE unverified.
2. `exterior-wall-light-pooky-portreath-up-down-bronze-ip65`: bronze solid brass, IP65, 110 GBP; size and photo (thumbnail only) unverified.
3. `exterior-wall-light-homecenter` not carded (price only from a snippet for LOTUS-S black 69.90; no bronze, no up/down). `exterior-wall-light-ikea-allarp-outdoor-wall-lamp-23`: aluminium colour, IP44, 195 ILS, search-summary level. Weak.
- Leads without a card (no price read): Boscolighting CYL cylinder up/down IP65 (archipro), Home Center PARIS up/down IP65 black and ORI DOWN grey, no bronze among Israeli listings. No Israeli lighting shop with a bronze cylinder was found.

**25, corridor `runner-rug` (60-70 x 680-700, flatweave wool or wool-jute, L* 65-78): 2 cards, both fail the spec.**
1. `runner-rug-ikea-tidtabell-wool-beige-80x200` (100% wool, 395 ILS; 80 wide, 200 long, pattern unverified).
2. `runner-rug-ikea-lohals-jute-80x250` (100% jute, 295 ILS; 80 x 250).
- No 7 m runner exists off the shelf. The realistic route is a made-to-measure Israeli maker (a search found Rugs and Co, custom wool rugs, 30 days, 50% deposit; no price, **listed only, no contact**). Kiliim, KUFUF, Pama, Tamnoon not reached.

**16, living-room `pouf` (D45-48 x H35-37, bouclé or leather): 1 card.**
1. `pouf-ikea-sandared-beige-45`: D 45 x H 33, beige woven fabric, 245 ILS. Not bouclé. Hard line: Home Center poufs are corduroy or velvet at 85 cm, a 68 cm outdoor round (399) or a rabbit. No Israeli bouclé or leather round pouf at this size found.

**18, living-room `armchair-cushion` (30x50, cognac leather or caramel linen): 2 cards, both off-spec.**
1. `armchair-cushion-ikea-dytag-linen-50x50` (100% linen, red-brown, 55 ILS; square).
2. `armchair-cushion-foxhome-ruby-camel-40x80` (camel polyester, 44.97 ILS; 40x80).
- Lead only: Kave Home Katny brown leather 30x50 (429, unread; foreign).

**8 (shower-stool), 17 (wall-decor), 20 (entrance framed-art), 22 (key-tray), 26 (gallery-art), 27 (gallery-stool): 0 new cards.**
- **8:** existing FB10 cards in `data/products/bath/shower-stool/` (IKEA SKOGSTA acacia 28x45, STORADDAM bench) remain the best; new this run: Waxman TOD (solid oak stool, "contact us", no price, not wet-rated) listed only. IKEA IL SKOGSTA page not reached (category index returned).
- **17:** nothing found (no relief disc in plaster or walnut plate). Search returned only Home Center mirrors and clocks.
- **20 and 26 (art, PR1):** no card with stated rights and a flat full-resolution file. Existing cards in `entrance/framed-art/` and `corridor/gallery-art/` are AliExpress or CJ sets with `unclear` rights. Rights-clean route not carded: museum open-access CC0 (Met, Art Institute of Chicago, Cleveland, Rijksmuseum) with public-domain abstractions (Klee, Kandinsky, Taeuber-Arp); each object page must be checked for the Open Access label before use, and style fit to oat/espresso minimal is unverified. Israeli artists and print platforms: not reached.
- **22:** nothing matching (travertine or honed limestone tray 18-22 x 10-14, not walnut). IKEA OMBONAD (walnut veneer 42 cm, 145 ILS) is the wrong material and size; Fox Home trays are wood, melamine or metal. Foreign travertine trays (Wolf and Badger Raya, 403) not read. Existing cards: CJ oval solid wood, AE acacia and metal oval.
- **27:** nothing new. Existing cane-seat card was rejected by the spec. IKEA SKOGSTA could serve as a stand-in (same item as line 8), not carded for this slot.

### Non-blocking lines (1-7, 9, 10, 12, 21) and backups (11, 13, 14, 15, 19, 28)
**Not searched in this run** (time spent on the blocking lines): 1 bench (see `data/leads/hall-bench-console-2026-11-17.md` for Tomik, Pony Style, MESA), 2, 3 (SANDARED serves line 3 too, same card), 4, 5, 6, 7, 9, 10, 11 (IKEA BRUGDHAJ already carded, line is blocking only if IKEA is out), 12, 13, 14, 15, 19, 21 (console: same leads file), 28. No card, no reach attempted on AE, CJ or Israeli stores for these.

## Israeli stores found this run
| Store | Reach | What |
| --- | --- | --- |
| IKEA Israel | product pages readable, category pages partly | door mats, poufs, runners, cushion covers, trays; alternative-only |
| Fox Home | pages and search readable | cushions, trays, bath mats; nothing on style for the blocking lines; partner potential, no contact |
| Home Center | search snippets only, pages unreadable | coir mats (19.90, 29.90), IP65 wall lights (grey, black), poufs |
| Waxman (TRUE design Tod) | page readable | solid oak stool, price on request |
| Rugs and Co | snippet only | made-to-measure wool rugs, 30 days; not contacted |
Zara Home Israel, Shilav, ACE, Pama, Tamnoon, Kiliim, KUFUF, Safsalina: not reached or 403.

## What was not reached, per kind
- **AE and CJ:** keys not set, no shell: every line. Heavy furniture and runner rugs are weak there anyway (rules ד.2).
- **Image downloads, colours from photos:** no shell. HEX values are estimates from colour names, not measurements.
- **Wholesale or partner prices:** none exist without contact; no-loss prices not computed.
