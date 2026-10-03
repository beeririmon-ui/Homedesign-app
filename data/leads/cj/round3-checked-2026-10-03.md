# CJ round 3 (2026-10-03): framed-art, floor-lamp, table-runner, candle-holders — what was checked
Budget used: ~51 search/list calls (one 429 retry), 35 product, 2 freight. Quota was NOT exhausted.

## Search-tool findings (save calls next time)
- `search` (listV2) only indexes a small subset: every "floor lamp" phrasing returns the same ~12 lamps; every runner phrasing returns the same 3 runners; candle phrasings return the same ~8 items. More rephrasings are wasted calls.
- `list "<words>"` ORs the words (multi-word = useless, sorted newest first). A single rare word works as a real name filter: "travertine" = 41, "triptych" = 31, "candleholder" = 7, "candlesticks" = 11, "hemstitch" = 1, "japandi" = 0, "Morandi" = 301, "candlestick" = 526 (pages 1-5 scanned), "runner" = 419 (pages 1-3 scanned).

## Cards written
- framed-art/framed-art-cj-morandi-triptych-sage.json (pid 2502230640411602800, 50x70 x3, black frame; weak: mockup-only images, sage may be too dark, To Door $130.82)
- pool/candle-holders/pool-cj-carbonized-wood-pedestal-candlestick.json (pid 2412060248371626300, warm-modern/japandi; 22 cm too tall for the Nordic slot)

## Rejected (do not re-check)
framed-art:
- 2090688333793595394 set of 2 21x29in (53x74) plaster texture — pair too narrow (114 < 145)
- 2090687523563114497 set of 2 24x36in — gold-foil boho arches, pair 130 wide; $105
- 2411231150051604700 B&W lines — max 45x55
- 2411120156531607200 B&W line — square, max 50x50
- 2505180906311624200 hand-drawn B&W — max 40x60
- 2511220828321604600 Morandi plant set of 3 — max 40x60
- 0FEA5300-A900-4E9C-ADB2-050EB011DCB3 — Van Gogh reproductions
- 1390510171146555392 triptych 50x70/70x100 — teal + gold ribbons
- 1404601859657830400 aluminium frame 50x70 — teal/gold-foil, glossy
- 1400627733377191936 100x150 single — gold x-ray flower on black
- 1603208319190183936, 2412030222161606800, 2411130841401628600, 7E023897-…, 1652611329217277952 — canvas core / poster only, no frame
floor-lamp:
- 2089189830207655938 tripod + linen drum 155 cm — E26 (US), reddish walnut legs
- 2507240232361627000 — glass globe stacked-ball lamp
- 2601300352451626900, 2508011015391606700 — arc/hook lamps, rattan, 110V
- 1786009278642393088 — plastic torchiere uplighter, US
- (round 2) 1990709163020832770 121 cm, 1990513445764902914 135 cm — too short
table-runner:
- 2406081338021602100 polyester voile 90x180+; 1434760666610274304 hollow/lace tassel; 2605130123011602100 polyester printed 35x180+; 2606150914241628900 chenille tassel; 2608181039461606700 jacquard
candle-holders:
- 1601765055845117952 bark log tealight; 1600751473074384896 bark taper/tealight
- 2508301115231624200 ceramic candle jars (enclose the candle)
- 2411250620171602600, 2502100656061623100, 2504130925371609200, 1750875799516876800 — taper-only (2.2-2.5 cm)
- 2407180604431613600 — Stoff Nagel copy, taper, chrome/gold
- 2412060248371626300 — carbonized wood, 22-32 cm tall (to pool)
