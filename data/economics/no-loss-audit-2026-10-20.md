# אין מוצר מפסיד: ביקורת אחרי ההחלה (2026-10-20)

הכלל (ה.13, תיקון 2026-10-20): "בא נוודא שאין דבר כזה מוצר מפסיד בשום צורה! יכול להיות יקר ללקוח אבל אין מפסיד!". הוחל לפי מדיניות המנהל (BRIEF-no-loss-2026-10-20.md, Apply), אחרי דוח מצב הדיווח (no-loss-report-2026-10-20.md).

יומן השינויים: `data/economics/no-loss-changes-2026-10-20.json`. הסקריפט: `python3 -I scripts/economics/no_loss.py --apply`, ואז `--check` ו-`--audit --tests F`.

## המדיניות

1. מחיר הכותרת = max(הנוכחי, המחיר שלא מפסיד במק"ט שבחדר, ביחידות המכירה, בשיטת ברירת המחדל), מעוגל ל-9
2. מחירי וריאנטים שהאתר גוזר (skuRetail) אינם סיבה להעלאה; התיקון באתר: מחיר נגזר לא יורד מתחת למחיר שלא מפסיד של הוריאנט (SITE1)
3. price-qty-mismatch: מחיר ליחידה כשהעמדה מוכרת יותר יחידות = מחיר × יחידות; נבדק ידנית
4. אקספרס-בלבד: בלי העלאה, דגל express-only, לא למכירה עד NL2
5. הכרית של המשתמש: לא משתנה (NL1)
6. אי אפשר לחשב: דגל ורשימה
7. דגלים: ok (40%+), below-floor (0–40%), above-market (מעל ההשוואה הגבוהה, עם היחס); יחס מעל 2 ל-NL2

## בקצרה

- נבדקו 464 מוצרים. לפי סטטוס אחרי ההחלה: ok 318, express-only 6, cannot-compute 10, no-price 130.
- **הועלו 89 מחירים** (products.json 91), ועוד 2 שורות נכתבו מחדש ליחידות המכירה. מ-₪19–₪598 ל-₪39–₪3,529; פי 1.04 עד פי 10.11, חציון פי 1.51.
- **יקר מהשוק: 19** (המחיר מעל ההשוואה הגבוהה); **3 ביחס מעל 2 → NL2**; היחס הגבוה פי 5.42.
- **אקספרס בלבד: 6**, בלי העלאה, דגל express-only, לא למכירה עד NL2. אי אפשר לחשב: 10. הכרית של המשתמש: לא שונתה (NL1).
- **SITE1:** ב-120 מוצרים מחיר וריאנט או יחידה בודדת שהאתר גוזר עדיין מפסיד במחיר הכותרת; התיקון באתר (רצפה למחיר הנגזר), הרשימה למטה.
- **עדיין מפסיד (כותרת או קריאת הסטודיו):** אין.
- **מעל ₪247** ($75 × 3.3, תקרת הפטור ממע"מ): שורות products.json 35 → 48 (מתוך 181); כל המוצרים עם מחיר 95 → 108 (מתוך 324).

## בדיקות

- no_loss --check (the repo, after the apply, 2026-10-23): 0 invariant failures, 0 products lose at their current price (exit 0)
- studio build (python3 studio/build.py, regular, with image fetching, 2026-10-23): exit 0; product images: downloaded 14, from cache 475, failed 0; boards 48, cards 293 (0 placeholders); economics: retail prices 324, shipping from CJ 152, Zendrop 7, AliExpress 13, card SKU 207, manual 14, no route 2, sell quantities 17. Not published
- site vitest (npx vitest run, after the apply): 62 passed, 2 failed, both pre-existing (they fail the same way on the tree before the apply): (1) 'every product card outside the shared pool parses' — 70 cards fail the derived schema; (2) 'sellQtyDefault agrees with studio/build.py on the real cards' — the site's port gives qty 1 where the Studio infers 2 from the record's landed cost (first mismatch: accent-sconces-aliexpress-fluted-white-ceramic-tulip-wall-sconce-on); SITE1
- studio smoke tests (7, on the applied data, 2026-10-23): 6 of 7 pass: boards 91 ok, compare 209 ok, compose 309 ok, decisions 17 ok, office 125 ok, products 153 ok (0 failed checks each); smoke_db_contract --db <studio-db export>: 23 ok, 1 fail unrelated to this change — 'every repo decision is in the db (116 repo, 111 db; missing NL2, NL3, RUG2, RUG3, RUG4)': decisions added to status/decisions.json after the db export; its 23 other checks (synced product edits, read-only, old shape) pass

## מה הועלה

התרחיש = המק"ט שבחדר ביחידות המכירה, בשיטת ברירת המחדל. "כל התרחישים" = המחיר שלא מפסיד גם בוריאנטים וביחידה בודדת כפי שהאתר מתמחר אותם (לא הוחל; SITE1).

| מוצר | מקור | היה | עכשיו | פי | שיטה; יח' | נחיתה | תרומה היום | נקודת איזון | מרווח עכשיו | כל התרחישים | השוואה גבוהה | יחס | דגל |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `floor-lamp-cj-cream-arc-pleated-152` | products.json | ₪349 | ₪3,529 | 10.11 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 | ₪2,673.10 | ₪-2,409.18 | ₪3,520.38 | 0.2% | ₪3,529 | ₪651 | 5.42 | above-market |
| `tableware-set-cj-grey-sand-matte-plate` | products.json | ₪19 | ₪109 | 5.74 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪77.58 | ₪-64.35 | ₪103.71 | 4.4% | ₪109 | ₪50 | 2.18 | above-market |
| `centerpiece-vase-cj-sandy-white-bead-band-25` | products.json | ₪59 | ₪289 | 4.90 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪212.19 | ₪-168.57 | ₪280.90 | 2.5% | ₪299 | ₪295 | 0.98 | below-floor |
| `mug-set-cj-oat-speckled-round-mug-wood-saucer` | products.json | ₪19 | ₪89 | 4.68 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪60.39 | ₪-47.16 | ₪81.08 | 8.0% | ₪89 | ₪60 | 1.48 | above-market |
| `wall-sconce-cj-black-swing-arm-wood-shade` | products.json | ₪119 | ₪429 | 3.60 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 | ₪321.95 | ₪-232.75 | ₪425.38 | 0.8% | ₪429 | ₪195 | 2.2 | above-market |
| `wall-sconce-cj-black-swing-arm-fabric` | products.json | ₪149 | ₪519 | 3.48 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 | ₪391.97 | ₪-279.98 | ₪517.57 | 0.2% | ₪519 | ₪293 | 1.77 | above-market |
| `mug-set-cj-cream-matte-breakfast-cup` | products.json | ₪39 | ₪129 | 3.31 | הסטודיו (cj): CJPacket Eub 12-50; 3 | ₪92.20 | ₪-63.78 | ₪122.95 | 4.2% | ₪149 | ₪90 | 1.43 | above-market |
| `bath-mat-cj-solid-wood-slatted-61x45` | products.json | ₪129 | ₪419 | 3.25 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 | ₪312.01 | ₪-215.22 | ₪412.31 | 1.4% | ₪419 | ₪399 | 1.05 | above-market |
| `candle-holders-aliexpress-cutelife-black-ceramic-candelabra` | products.json | ₪39 | ₪119 | 3.05 | מטמון AliExpress 3256811647185429 sku 12000056728690425 ×1: AliExpress Selection Standard 6-15; 1 | ₪87.85 | ₪-59.42 | ₪117.22 | 1.3% | ₪139 | ₪125 | 0.95 | below-floor |
| `tableware-set-cj-speckled-oat-stoneware-bowl-13` | products.json | ₪29 | ₪79 | 2.72 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪58.64 | ₪-37.81 | ₪78.77 | 0.3% | ₪99 | ₪80 | 0.99 | below-floor |
| `floor-vase-aliexpress-capiron-zen-ceramic` | products.json | ₪49 | ₪129 | 2.63 | מטמון AliExpress 3256808800994217 sku 12000047471652183 ×1: AliExpress standard shipping 8-18; 1 | ₪91.18 | ₪-55.16 | ₪121.61 | 5.1% | ₪129 | ₪295 | 0.44 | below-floor |
| `toothbrush-cup-cj-travertine-look-cup-milktea` | products.json | ₪19 | ₪49 | 2.58 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪34.15 | ₪-20.92 | ₪46.54 | 4.5% | ₪59 | ₪114 | 0.43 | below-floor |
| `bench-pad-cj-tufted-long-cushion-khaki-120` | products.json | ₪59 | ₪139 | 2.36 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪101.74 | ₪-58.12 | ₪135.51 | 2.3% | ₪149 | ₪135 | 1.03 | above-market |
| `floor-lamp-cj-pleated-walnut-stem-158` | products.json | ₪349 | ₪769 | 2.20 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 | ₪580.44 | ₪-316.52 | ₪765.65 | 0.4% | ₪829 | ₪651 | 1.18 | above-market |
| `nightstand-tray-cj-travertine-look-rect-milktea` | products.json | ₪59 | ₪129 | 2.19 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪94.61 | ₪-50.99 | ₪126.12 | 2.0% | ₪149 | ₪347 | 0.37 | below-floor |
| `tea-towel-zendrop-cotton-linen-washed-60x45` | products.json | ₪19 | ₪39 | 2.05 | הסטודיו (zendrop): Zendrop regular 14; 1 | ₪28.05 | ₪-14.82 | ₪38.50 | 1.1% | ₪39 | ₪49 | 0.8 | below-floor |
| `bath-mat-cj-tufted-cotton-frame-beige-40x60` | products.json | ₪39 | ₪79 | 2.03 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪52.77 | ₪-24.34 | ₪71.04 | 9.0% | ₪79 | ₪165 | 0.48 | below-floor |
| `shower-curtain-cj-linen-look-khaki-grommet` | products.json | ₪39 | ₪79 | 2.03 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪56.59 | ₪-28.17 | ₪76.08 | 3.3% | ₪99 | ₪129 | 0.61 | below-floor |
| `bowl-cj-glutinous-white-belly-bowl-21` | products.json | ₪39 | ₪79 | 2.03 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪53.06 | ₪-24.64 | ₪71.43 | 8.6% | ₪79 | ₪120 | 0.66 | below-floor |
| `pool-cj-linen-look-tassel-curtain` | products.json | ₪59 | ₪119 | 2.02 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪84.41 | ₪-40.79 | ₪112.70 | 4.7% | ₪139 | ₪198 | 0.6 | below-floor |
| `pool-cj-terracotta-amphora-floor-51` | products.json | ₪479 | ₪959 | 2.00 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪725.97 | ₪-363.29 | ₪957.23 | 0.2% | ₪959 | ₪1,055 | 0.91 | below-floor |
| `toothbrush-cup-cj-silver-travertine-cup` | products.json | ₪79 | ₪149 | 1.89 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪104.44 | ₪-45.63 | ₪139.07 | 6.0% | ₪149 | ₪347 | 0.43 | below-floor |
| `pool-cj-carbonized-wood-pedestal-candlestick` | products.json | ₪69 | ₪129 | 1.87 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪90.95 | ₪-39.73 | ₪121.30 | 5.3% | ₪129 | ₪185 | 0.7 | below-floor |
| `centerpiece-vase-aliexpress-modern-minimalist-white-ceramic` | products.json | ₪59 | ₪109 | 1.85 | קובץ התמחור:  (הערכה); 1 | ₪77.32 | ₪-33.70 | ₪103.36 | 4.6% | ₪119 | ₪295 | 0.37 | below-floor |
| `pouf-cj-cotton-knit-ball-cover` | products.json | ₪99 | ₪179 | 1.81 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪127.38 | ₪-53.37 | ₪169.26 | 4.9% | ₪179 | ₪450 | 0.4 | below-floor |
| `magazine-holder-cj-gunmetal-leather-strap` | products.json | ₪149 | ₪269 | 1.80 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪200.14 | ₪-88.16 | ₪265.05 | 1.3% | ₪269 | ₪229 | 1.17 | above-market |
| `table-lamp-cj-pleated-shade-wood-column` | products.json | ₪149 | ₪269 | 1.80 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 | ₪197.90 | ₪-85.91 | ₪262.09 | 2.3% | ₪269 | ₪295 | 0.91 | below-floor |
| `centerpiece-vase-aliexpress-nordic-matte-ceramic-vase` | products.json | ₪89 | ₪159 | 1.79 | קובץ התמחור:  (הערכה); 1 | ₪116.19 | ₪-49.78 | ₪154.53 | 2.5% | ₪199 | ₪295 | 0.54 | below-floor |
| `framed-art-cj-line-scribble-white-mat-50` | products.json | ₪129 | ₪229 | 1.77 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪165.73 | ₪-68.93 | ₪219.74 | 3.6% | ₪239 | ₪225 | 1.02 | above-market |
| `reed-diffuser-cj-travertine-look-bamboo-lid-milktea` | products.json | ₪39 | ₪69 | 1.77 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪49.73 | ₪-21.30 | ₪67.04 | 2.5% | ₪69 | ₪144 | 0.48 | below-floor |
| `soap-dispenser-cj-matte-ceramic-cream-black-pump` | products.json | ₪39 | ₪69 | 1.77 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪47.45 | ₪-19.03 | ₪64.05 | 6.4% | ₪69 | ₪120 | 0.57 | below-floor |
| `open-shelf-ceramics-cj-morandi-matte-bottle-set` | products.json | ₪79 | ₪139 | 1.76 | הסטודיו (cj): CJPacket Eub 12-50; 2 | ₪97.94 | ₪-39.13 | ₪130.51 | 5.5% | ₪139 | ₪270 | 0.51 | below-floor |
| `pool-cj-cotton-linen-box-camel-40x30` | products.json | ₪29 | ₪49 | 1.69 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪29.93 | ₪-9.10 | ₪40.98 | 14.7% | ₪49 | ₪70 | 0.7 | below-floor |
| `pendant-cj-fabric-dome-ash-cap-25` | products.json | ₪119 | ₪199 | 1.67 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪144.11 | ₪-54.91 | ₪191.28 | 3.5% | ₪199 | ₪195 | 1.02 | above-market |
| `ceiling-light-cj-opal-glass-drum-flush-32` | products.json | ₪149 | ₪249 | 1.67 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪186.38 | ₪-74.39 | ₪246.93 | 0.7% | ₪249 | ₪300 | 0.83 | below-floor |
| `framed-art-cj-taupe-block-black-line-30x40` | products.json | ₪109 | ₪179 | 1.64 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪132.49 | ₪-50.89 | ₪175.99 | 1.5% | ₪179 | ₪200 | 0.9 | below-floor |
| `soap-dispenser-cj-travertine-look-lotion-milktea` | products.json | ₪49 | ₪79 | 1.61 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪55.47 | ₪-19.45 | ₪74.60 | 5.0% | ₪89 | ₪180 | 0.44 | below-floor |
| `sofa-cover-cj-bubble-stretch-slipcover` | products.json | ₪149 | ₪239 | 1.60 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪179.88 | ₪-67.89 | ₪238.37 | 0.2% | ₪279 | ₪600 | 0.4 | below-floor |
| `dining-pendant-cj-black-ring-cloth-lantern-50` | products.json | ₪229 | ₪359 | 1.57 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪268.49 | ₪-95.73 | ₪355.01 | 1.0% | ₪409 | ₪420 | 0.85 | below-floor |
| `framed-art-cj-swinging-line-black-frame-mat-35x45` | products.json | ₪129 | ₪199 | 1.54 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪148.93 | ₪-52.13 | ₪197.63 | 0.6% | ₪199 | ₪225 | 0.88 | below-floor |
| `framed-prints-cj-charcoal-line-black-frame-35x45` | products.json | ₪129 | ₪199 | 1.54 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪148.93 | ₪-52.13 | ₪197.63 | 0.6% | ₪199 | ₪225 | 0.88 | below-floor |
| `candle-holders-aliexpress-matte-black-iron-pillar-set2` | products.json | ₪39 | ₪59 | 1.51 | מטמון AliExpress 3256811847480845 sku 12000057351444960 ×1: AliExpress Selection Standard 6-15; 1 | ₪41.09 | ₪-12.66 | ₪55.66 | 5.1% | ₪59 | ₪89 | 0.66 | below-floor |
| `wall-hooks-cj-raw-wood-cylinder-peg-set-of-4` | products.json | ₪39 | ₪59 | 1.51 | הסטודיו (cj): CJPacket Eub 12-50 (הוצע ל-4 יח'; נלקח ליחידת מכירה, כמו בסטודיו); 1 | ₪37.19 | ₪-8.76 | ₪50.54 | 12.9% | ₪59 | ₪125 | 0.47 | below-floor |
| `bowl-cj-reactive-white-rimmed-plate-21` | products.json | ₪59 | ₪89 | 1.51 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪65.64 | ₪-22.02 | ₪87.98 | 1.0% | ₪99 | ₪139 | 0.64 | below-floor |
| `picture-lights-cj-black-tube-rechargeable` | products.json | ₪59 | ₪89 | 1.51 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 | ₪60.03 | ₪-16.41 | ₪80.60 | 8.5% | ₪89 | ₪125 | 0.71 | below-floor |
| `condiment-set-zendrop-wood-mills-black-white-21` | products.json | ₪59 | ₪89 | 1.51 | הסטודיו (zendrop): Zendrop regular 14; 1 | ₪65.47 | ₪-21.85 | ₪87.77 | 1.2% | ₪99 | ₪140 | 0.64 | below-floor |
| `wall-sconce-cj-black-swan-arm-white-fabric-cone` | products.json | ₪79 | ₪119 | 1.51 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪84.94 | ₪-26.13 | ₪113.40 | 4.2% | ₪129 | ₪150 | 0.79 | below-floor |
| `table-lamp-cj-white-teardrop-fabric-cone-25x45` | products.json | ₪99 | ₪149 | 1.50 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 | ₪105.34 | ₪-31.33 | ₪140.24 | 5.3% | ₪149 | ₪190 | 0.78 | below-floor |
| `bedding-cj-washed-polyester-set-milk-tea` | products.json | ₪99 | ₪149 | 1.50 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪111.97 | ₪-37.96 | ₪148.97 | 0.0% | ₪159 | ₪210 | 0.71 | below-floor |
| `pendant-cj-pleated-pumpkin-lantern-40` | products.json | ₪299 | ₪449 | 1.50 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪332.97 | ₪-107.03 | ₪439.89 | 1.8% | ₪469 | ₪450 | 1.0 | below-floor |
| `wall-sconce-cj-travertine-dome-15-pull` | products.json | ₪299 | ₪449 | 1.50 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 | ₪332.81 | ₪-106.87 | ₪439.68 | 1.9% | ₪449 | ₪520 | 0.86 | below-floor |
| `basket-cj-cotton-rope-white` | products.json | ₪89 | ₪129 | 1.45 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪90.09 | ₪-23.68 | ₪120.17 | 6.1% | ₪129 | ₪190 | 0.68 | below-floor |
| `framed-art-aliexpress-retro-farmhouse-chicken-botanical-333603` | products.json | ₪89 | ₪129 | 1.45 | הסטודיו (aliexpress): AliExpress Selection Standard 6-15; 1 | ₪96.76 | ₪-30.35 | ₪128.95 | 0.0% | ₪229 | ₪200 | 0.65 | below-floor |
| `pool-cj-travertine-organic-tray-24` | products.json | ₪119 | ₪169 | 1.42 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪120.85 | ₪-31.65 | ₪160.66 | 4.4% | ₪169 | ₪347 | 0.49 | below-floor |
| `ceiling-lights-cj-silk-cocoon-flush-40` | products.json | ₪219 | ₪309 | 1.41 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪233.51 | ₪-68.34 | ₪308.96 | 0.0% | ₪309 | ₪420 | 0.74 | below-floor |
| `wall-sconce-cj-white-fabric-cube-15` | products.json | ₪198 (₪99 ליח') | ₪279 | 1.41 | הסטודיו (cj): CJPacket Eub 12-50; 2 | ₪205.99 | ₪-56.77 | ₪272.73 | 2.0% | ₪299 | ₪299 | 0.93 | below-floor |
| `bath-towels-cj-cotton-waffle-white` | products.json | ₪49 | ₪69 | 1.41 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪46.13 | ₪-10.11 | ₪62.31 | 8.7% | ₪89 | ₪199 | 0.35 | below-floor |
| `vanity-sconces-cj-ip65-mini-updown-white` | products.json | ₪49 | ₪69 | 1.41 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪49.40 | ₪-13.38 | ₪66.61 | 3.1% | ₪69 | ₪220 | 0.31 | below-floor |
| `condiment-set-cj-rubberwood-mill-pair-6in` | products.json | ₪49 | ₪69 | 1.41 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪47.72 | ₪-11.69 | ₪64.39 | 6.0% | ₪69 | ₪130 | 0.53 | below-floor |
| `wall-sconce-cj-wavy-linen-flush-25` | products.json | ₪149 | ₪209 | 1.40 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪151.80 | ₪-39.81 | ₪201.41 | 3.3% | ₪209 | ₪299 | 0.7 | below-floor |
| `vase-cj-french-matte-white-35` | products.json | ₪229 | ₪319 | 1.39 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪238.79 | ₪-66.03 | ₪315.91 | 0.9% | ₪319 | ₪589 | 0.54 | below-floor |
| `magazine-holder-cj-arch-iron-cane` | products.json | ₪129 | ₪179 | 1.39 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪131.34 | ₪-34.54 | ₪174.47 | 2.3% | ₪179 | ₪229 | 0.78 | below-floor |
| `basket-cj-jute-rope-cylinder` | products.json | ₪79 | ₪109 | 1.38 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪80.12 | ₪-21.31 | ₪107.05 | 1.6% | ₪119 | ₪179 | 0.61 | below-floor |
| `ceiling-light-cj-waxwood-dome-ash-40` | products.json | ₪199 | ₪269 | 1.35 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪197.24 | ₪-47.27 | ₪261.22 | 2.6% | ₪279 | ₪420 | 0.64 | below-floor |
| `wall-decor-zendrop-macrame-diamond-dowel-small` | products.json | ₪59 | ₪79 | 1.34 | הסטודיו (zendrop): Zendrop regular 14; 1 | ₪55.31 | ₪-11.69 | ₪74.39 | 5.2% | ₪79 | ₪249 | 0.32 | below-floor |
| `cushions-cj-dusty-pink-corduroy-patchwork-45` | products.json | ₪59 | ₪79 | 1.34 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪52.37 | ₪-8.75 | ₪70.52 | 9.6% | ₪79 | ₪199 | 0.4 | below-floor |
| `pendant-cj-tiered-fabric-drum` | products.json | ₪329 | ₪429 | 1.30 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪323.66 | ₪-74.94 | ₪427.64 | 0.3% | ₪429 | ₪460 | 0.93 | below-floor |
| `framed-art-aliexpress-japanese-wabi-sabi-tree-176323` | products.json | ₪39 | ₪49 | 1.26 | הסטודיו (aliexpress): AliExpress (card option) 6-15; 1 | ₪32.34 | ₪-3.91 | ₪44.15 | 8.9% | ₪69 | ₪95 | 0.52 | below-floor |
| `canisters-zendrop-matte-ceramic-bamboo-lid-sml` | products.json | ₪89 | ₪109 | 1.23 | הסטודיו (zendrop): Zendrop regular 14; 1 | ₪78.01 | ₪-11.60 | ₪104.27 | 3.9% | ₪109 | ₪180 | 0.61 | below-floor |
| `sill-vase-cj-cream-fluted-column-25` | products.json | ₪49 | ₪59 | 1.20 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪38.87 | ₪-2.85 | ₪52.75 | 9.5% | ₪59 | ₪295 | 0.2 | below-floor |
| `wall-sconce-cj-black-folding-arm-woodgrain-cone-18` | products.json | ₪99 | ₪119 | 1.20 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪88.84 | ₪-14.83 | ₪118.52 | 0.4% | ₪139 | ₪195 | 0.61 | below-floor |
| `vase-cj-white-textured-jar` | products.json | ₪149 | ₪179 | 1.20 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪131.47 | ₪-19.48 | ₪174.65 | 2.2% | ₪179 | ₪269 | 0.67 | below-floor |
| `table-lamp-cj-white-textured-ceramic-linen-drum` | products.json | ₪199 | ₪239 | 1.20 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪173.02 | ₪-23.05 | ₪229.34 | 3.6% | ₪239 | ₪295 | 0.81 | below-floor |
| `ceiling-lights-cj-pleated-fabric-saucer-flush-50` | products.json | ₪499 | ₪569 | 1.14 | הסטודיו (cj): CJPacket Eub 12-50; 2 | ₪425.63 | ₪-47.76 | ₪561.87 | 1.1% | ₪569 | ₪900 | 0.63 | below-floor |
| `sofa-cover-cj-polar-fleece-jacquard-slipcover` | products.json | ₪149 | ₪169 | 1.13 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪122.33 | ₪-10.34 | ₪162.61 | 3.4% | ₪219 | ₪600 | 0.28 | below-floor |
| `vanity-sconces-cj-fluted-resin-updown-white` | products.json | ₪229 | ₪259 | 1.13 | הסטודיו (cj): CJPacket Sensitive 22-27; 2 | ₪191.47 | ₪-18.70 | ₪253.62 | 1.9% | ₪259 | ₪440 | 0.59 | below-floor |
| `skateboard-cj-blank-maple-43` | products.json | ₪79 | ₪89 | 1.13 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪64.45 | ₪-5.64 | ₪86.42 | 2.6% | ₪89 | ₪149 | 0.6 | below-floor |
| `bedside-sconces-cj-linen-half-drum-black-trim` | products.json | ₪349 | ₪389 | 1.11 | הסטודיו (cj): CJPacket Eub 12-50; 2 | ₪291.32 | ₪-27.40 | ₪385.07 | 0.9% | ₪389 | ₪598 | 0.65 | below-floor |
| `basket-cj-seagrass-belly` | products.json | ₪89 | ₪99 | 1.11 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪68.47 | ₪-2.07 | ₪91.72 | 6.6% | ₪119 | ₪190 | 0.52 | below-floor |
| `planter-cj-seagrass-belly` | products.json | ₪89 | ₪99 | 1.11 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪68.47 | ₪-2.07 | ₪91.72 | 6.6% | ₪119 | ₪190 | 0.52 | below-floor |
| `wall-hooks-cj-light-wood-rail-5-brass-pegs-58` | products.json | ₪89 | ₪99 | 1.11 | הסטודיו (cj): CJPacket Liquid Line 9-23; 1 | ₪72.07 | ₪-5.66 | ₪96.45 | 2.3% | ₪119 | ₪175 | 0.57 | below-floor |
| `vase-cj-charcoal-carved` | products.json | ₪199 | ₪219 | 1.10 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪158.10 | ₪-8.13 | ₪209.70 | 3.8% | ₪219 | ₪479 | 0.46 | below-floor |
| `vase-cj-faceted-cream` | products.json | ₪199 | ₪219 | 1.10 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪164.01 | ₪-14.04 | ₪217.48 | 0.6% | ₪259 | ₪479 | 0.46 | below-floor |
| `curtains-aliexpress-cotton-linen-texture-translucent-091154` | products.json | ₪299 | ₪329 | 1.10 | הערות הכרטיס (הערכה); 2 | ₪241.39 | ₪-15.46 | ₪319.35 | 2.6% | ₪499 | ₪489 | 0.67 | below-floor |
| `pool-cj-wabi-sabi-floor-vase-white` | products.json | ₪349 | ₪379 | 1.09 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪283.54 | ₪-19.61 | ₪374.82 | 1.0% | ₪379 | ₪835 | 0.45 | below-floor |
| `accent-sconces-aliexpress-indoor-stone-wall-lamp` | products.json | ₪598 (₪299 ליח') | ₪649 | 1.08 | מטמון AliExpress 3256807415537790 sku 12000043242375290 ×1: AliExpress standard shipping 22-32; 2 | ₪484.90 | ₪-31.82 | ₪639.89 | 1.3% | ₪649 | ₪520 | 1.25 | above-market |
| `sofa-cover-cj-waffle-jacquard-stretch-slipcover` | products.json | ₪149 | ₪159 | 1.07 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪118.24 | ₪-6.25 | ₪157.23 | 1.0% | ₪189 | ₪600 | 0.27 | below-floor |
| `vase-cj-matte-moon-jar-white` | products.json | ₪149 | ₪159 | 1.07 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪118.93 | ₪-6.94 | ₪158.14 | 0.5% | ₪179 | ₪269 | 0.59 | below-floor |
| `pendant-cj-fluted-ceramic-wood-cap-short-lantern` | products.json | ₪149 | ₪159 | 1.07 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪114.87 | ₪-2.88 | ₪152.80 | 3.5% | ₪159 | ₪315 | 0.5 | below-floor |
| `centerpiece-vase-aliexpress-nordic-morandi-matte-ceramic` | products.json | ₪199 | ₪209 | 1.05 | קובץ התמחור:  (הערכה); 1 | ₪152.46 | ₪-2.49 | ₪202.27 | 2.9% | ₪219 | ₪400 | 0.52 | below-floor |
| `vase-cj-white-plum-hand-thrown` | products.json | ₪229 | ₪239 | 1.04 | הסטודיו (cj): CJPacket Eub 12-50; 1 | ₪176.95 | ₪-4.18 | ₪234.51 | 1.7% | ₪239 | ₪479 | 0.5 | below-floor |

## price-qty-mismatch: בדיקה ידנית (2 שורות)

- `accent-sconces-aliexpress-indoor-stone-wall-lamp`: המחיר ₪299 הוא ליחידה (price_for_qty 1) והסטודיו מוכר 2 יח' (העמדה זוג): מחיר המכירה ₪299 × 2 = ₪598. נחיתה ל-2 יח' (מטמון AliExpress 3256807415537790 sku 12000043242375290 ×1: AliExpress standard shipping 22-32, משלוח $43.06 בחבילה משולבת) ₪484.9; נטו ₪506.78, עמלות ₪13.16, שמורה ₪40.54 → תרומה ₪-31.82 (-6.3%): מפסיד. נקודת האיזון ל-2 יח' ₪639.89; נכתב ₪649 ל-2 יח' (price_for_qty 2, sell_qty 2).
- `wall-sconce-cj-white-fabric-cube-15`: המחיר ₪99 הוא ליחידה (price_for_qty 1) והסטודיו מוכר 2 יח' (העמדה זוג): מחיר המכירה ₪99 × 2 = ₪198. נחיתה ל-2 יח' (הסטודיו (cj): CJPacket Eub 12-50, משלוח $22.4 בחבילה משולבת) ₪205.99; נטו ₪167.80, עמלות ₪5.16, שמורה ₪13.42 → תרומה ₪-56.77 (-33.8%): מפסיד. נקודת האיזון ל-2 יח' ₪272.73; נכתב ₪279 ל-2 יח' (price_for_qty 2, sell_qty 2).

## יקר מהשוק

19 מוצרים שמחירם מעל ההשוואה הישראלית הגבוהה (דגל `above-market`; הסטודיו מעביר רק ok/below-floor/loss, SITE1). **3 ביחס מעל 2 מסומנים ל-NL2.**

| מוצר | מחיר | היה | השוואה גבוהה | יחס | NL2 | שיטה; יח' |
| --- | --- | --- | --- | --- | --- | --- |
| `floor-lamp-cj-cream-arc-pleated-152` | ₪3,529 | ₪349 | ₪651 | פי 5.42 | **כן** | הסטודיו (cj): CJPacket Sensitive 22-27; 1 |
| `wall-sconce-cj-black-swing-arm-wood-shade` | ₪429 | ₪119 | ₪195 | פי 2.2 | **כן** | הסטודיו (cj): CJPacket Sensitive 22-27; 1 |
| `tableware-set-cj-grey-sand-matte-plate` | ₪109 | ₪19 | ₪50 | פי 2.18 | **כן** | הסטודיו (cj): CJPacket Eub 12-50; 1 |
| `candle-holders-aliexpress-black-lava-stone-candle-holders` | ₪289 | לא הועלה | ₪155 | פי 1.86 |  | הסטודיו (card): המק"ט שבחדר 8-15; 1 |
| `wall-sconce-cj-black-swing-arm-fabric` | ₪519 | ₪149 | ₪293 | פי 1.77 |  | הסטודיו (cj): CJPacket Sensitive 22-27; 1 |
| `mug-set-cj-oat-speckled-round-mug-wood-saucer` | ₪89 | ₪19 | ₪60 | פי 1.48 |  | הסטודיו (cj): CJPacket Eub 12-50; 1 |
| `mug-set-cj-cream-matte-breakfast-cup` | ₪129 | ₪39 | ₪90 | פי 1.43 |  | הסטודיו (cj): CJPacket Eub 12-50; 3 |
| `bedside-sconces-aliexpress-joyinled-boho-style-sconce-968057` | ₪499 | לא הועלה | ₪349 | פי 1.43 |  | הסטודיו (card): המק"ט שבחדר 6-15; 1 |
| `kitchen-sconce-aliexpress-joyinled-boho-style-sconce-968057` | ₪499 | לא הועלה | ₪349 | פי 1.43 |  | הסטודיו (card): המק"ט שבחדר 6-15; 1 |
| `bookshelf-cj-natural-wood-ledge-pair-42-x2` | ₪219 | לא הועלה | ₪158 | פי 1.39 |  | מטמון CJ vid 2410141005261605600 ×1: CJPacket Eub 12-50; 2 |
| `accent-sconces-aliexpress-indoor-stone-wall-lamp` | ₪649 | ₪299 | ₪520 | פי 1.25 |  | מטמון AliExpress 3256807415537790 sku 12000043242375290 ×1: AliExpress standard shipping 22-32; 2 |
| `floor-lamp-cj-pleated-walnut-stem-158` | ₪769 | ₪349 | ₪651 | פי 1.18 |  | הסטודיו (cj): CJPacket Sensitive 22-27; 1 |
| `magazine-holder-cj-gunmetal-leather-strap` | ₪269 | ₪149 | ₪229 | פי 1.17 |  | הסטודיו (cj): CJPacket Eub 12-50; 1 |
| `framed-art-aliexpress-minimal-geometric-triptych-prints` | ₪199 | לא הועלה | ₪175 | פי 1.14 |  | הסטודיו (leads): מהליקוט 6-13 (ל-3 יח'); 3 |
| `waste-basket-aliexpress-water-hyacinth-bin-19x28-pair-057684` | ₪159 | לא הועלה | ₪149.90 | פי 1.06 |  | הסטודיו (leads): מהליקוט 8-15; 1 |
| `bath-mat-cj-solid-wood-slatted-61x45` | ₪419 | ₪129 | ₪399 | פי 1.05 |  | הסטודיו (cj): CJPacket Sensitive 22-27; 1 |
| `bench-pad-cj-tufted-long-cushion-khaki-120` | ₪139 | ₪59 | ₪135 | פי 1.03 |  | הסטודיו (cj): CJPacket Eub 12-50; 1 |
| `framed-art-cj-line-scribble-white-mat-50` | ₪229 | ₪129 | ₪225 | פי 1.02 |  | הסטודיו (cj): CJPacket Eub 12-50; 1 |
| `pendant-cj-fabric-dome-ash-cap-25` | ₪199 | ₪119 | ₪195 | פי 1.02 |  | הסטודיו (cj): CJPacket Eub 12-50; 1 |

## אקספרס בלבד (לא למכירה עד NL2)

| מוצר | מחיר | השיטה היחידה | משלוח | מפסיד היום | לא מפסיד באקספרס | השוואה גבוהה | יחס |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `framed-art-cj-morandi-triptych-sage` | ₪379 | הסטודיו (cj): CJPacket To Door 11-18 | $130.82 | כן | ₪639 | ₪980 | 0.65 |
| `rug-cj-braided-wool-natural` | ₪1,299 | הסטודיו (cj): DHL Official 3-7 | $491.08 | כן | ₪3,299 | ₪2,700 | 1.22 |
| `bedding-cj-cotton-linen-duvet-beige` | ₪479 | הסטודיו (cj): CJPacket To Door 11-18 | $107.99 | כן | ₪1,029 | ₪1,080 | 0.95 |
| `pendant-cj-wabi-pleated-fabric-lantern-50` | ₪299 | הסטודיו (cj): CJPacket To Door 11-18 | $340.29 | כן | ₪1,739 | ₪420 | 4.14 |
| `roman-blind-aliexpress-customized-flat-sheer-roman-221993` | — | מטמון AliExpress 1005008958221993 sku 12000047368507416 ×1: DHL 18-30 (חינם) | $0 | אין מחיר | ₪189 | — | — |
| `roman-blind-aliexpress-modern-beige-color-flat-868827` | — | מטמון AliExpress 1005012057868827 sku 12000057392721266 ×1: Fedex IP 19-35 (חינם) | $0 | אין מחיר | ₪189 | — | — |

## מחיר שהמשתמש קבע (NL1, לא שונה)

- `cushions-aliexpress-fashion-modern-wabi-sabi-464203` ב-₪69 (Studio db product_edits/cushions-aliexpress-fashion-modern-wabi-sabi-464203.json (synced 2026-10-13)). במק"ט שבחדר (הסטודיו (aliexpress): AliExpress Selection Standard 6-15): תרומה ₪1.29, מרווח 2.2%: לא מפסיד; המחיר שלא מפסיד במק"ט שבחדר ₪69. מפסיד רק בוריאנט שהאתר גוזר: color=1pcs-caramel, size=30x50 ב-₪49 (תרומה ₪-7.47, רצפה ₪59); color=1pcs-caramel, size=40x40 ב-₪59 (תרומה ₪-2.75, רצפה ₪69); color=1pcs-dark-gray, size=30x50 ב-₪49 (תרומה ₪-7.27, רצפה ₪59); color=1pcs-dark-gray, size=40x40 ב-₪59 (תרומה ₪-2.75, רצפה ₪69); color=1pcs-beige, size=30x50 ב-₪49 (תרומה ₪-8.56, רצפה ₪69); color=1pcs-beige, size=40x40 ב-₪59 (תרומה ₪-2.08, רצפה ₪69); color=1pcs-lime, size=30x50 ב-₪49 (תרומה ₪-8.23, רצפה ₪69); color=1pcs-lime, size=40x40 ב-₪59 (תרומה ₪-2.75, רצפה ₪69); color=1pcs-lime, size=45x45 ב-₪69 (תרומה ₪-0.53, רצפה ₪79); color=1pcs-white, size=30x50 ב-₪49 (תרומה ₪-8.56, רצפה ₪69); color=1pcs-white, size=40x40 ב-₪59 (תרומה ₪-1.75, רצפה ₪69). בכל התרחישים: ₪89. לפי המדיניות זה תיקון SITE1, לא העלאה.

## אי אפשר לחשב

- `dining-chairs-furniture-express-maya` (products.json, studio-price): עלות במטבע ILS, לא בדולר, מחיר ₪399 (דגל cannot-compute)
- `paper-towel-holder-cj-beech-upright-31` (products.json, studio-price): הספק לא שולח לישראל, מחיר ₪39 (דגל cannot-compute)
- `bath-towels-cj-diamond-peshtemal-cotton-90x180` (coverage): אין משלוח ואין הערכה (דגל cannot-compute)
- `bath-towels-cj-honeycomb-waffle-cotton-70x140` (coverage): אין משלוח ואין הערכה (דגל cannot-compute)
- `bath-towels-cj-striped-peshtemal-cotton-90x180` (coverage): אין משלוח ואין הערכה (דגל cannot-compute)
- `bedding-cj-stripe-cotton-single-set-light-brown` (coverage): אין משלוח ואין הערכה (דגל cannot-compute)
- `pendant-cj-silk-pumpkin-lantern-40-master` (coverage): אין משלוח ואין הערכה (דגל cannot-compute)
- `pillowcases-cj-washed-linen-double-ruffle-48x74` (coverage): אין משלוח ואין הערכה (דגל cannot-compute)
- `tea-towel-cj-herringbone-fringe-cotton-38x60` (coverage): אין משלוח ואין הערכה (דגל cannot-compute)
- `trinket-dish-cj-organic-ceramic-tray-black` (coverage): אין משלוח ואין הערכה (דגל cannot-compute)

## SITE1: רצפה למחיר וריאנט שהאתר גוזר

- מחיר וריאנט שהאתר גוזר (options.ts skuRetail: P + המומלץ של האפשרות − המומלץ של המק"ט שבחדר) לא יורד מתחת למחיר שלא מפסיד של הוריאנט עצמו (נקודת האיזון של הנחיתה שלו, מעוגלת ל-9); אותו דבר להערכת היחידה הבודדת (packs.ts unitPriceEstimateIls).
- 67 השורות שבדוח הדיווח נקבעו מוריאנט: `basket-cj-cotton-rope-white`, `basket-cj-jute-rope-cylinder`, `basket-cj-seagrass-belly`, `bath-towels-cj-cotton-waffle-white`, `bedding-aliexpress-boho-3d-tufted-cut-500672`, `bedding-cj-washed-polyester-set-milk-tea`, `bench-cushion-aliexpress-double-piping-cushion-110x35x5`, `bench-cushion-aliexpress-linen-look-box-cushion-110x35x5`, `bench-pad-aliexpress-double-piping-cushion-130x35x5`, `bench-pad-aliexpress-linen-look-box-cushion-130x35x5`, `bench-pad-cj-tufted-long-cushion-khaki-120`, `bowl-aliexpress-kiln-corrugated-raw-rim-bowl-23`, `bowl-aliexpress-pearl-rim-ingot-bowl-23`, `bowl-cj-reactive-white-rimmed-plate-21`, `candle-holders-aliexpress-cutelife-black-ceramic-candelabra`, `ceiling-light-cj-waxwood-dome-ash-40`, `centerpiece-vase-aliexpress-modern-minimalist-white-ceramic`, `centerpiece-vase-aliexpress-nordic-matte-ceramic-vase`, `centerpiece-vase-aliexpress-nordic-morandi-matte-ceramic`, `centerpiece-vase-cj-sandy-white-bead-band-25`, `condiment-set-zendrop-wood-mills-black-white-21`, `curtains-aliexpress-cotton-linen-texture-translucent`, `curtains-aliexpress-cotton-linen-texture-translucent-091154`, `cushions-aliexpress-fashion-modern-wabi-sabi-464203`, `cushions-aliexpress-textured-boucle-throw-pillow`, `dining-pendant-cj-black-ring-cloth-lantern-50`, `floor-lamp-aliexpress-pleated-walnut-37x158-062736`, `floor-lamp-aliexpress-pleated-walnut-37x158-062736-master`, `floor-lamp-cj-pleated-walnut-stem-158`, `framed-art-aliexpress-japanese-wabi-sabi-tree-176323`, `framed-art-aliexpress-retro-farmhouse-chicken-botanical-333603`, `framed-art-cj-line-scribble-white-mat-50`, `magazine-holder-cj-felt-snap-bucket`, `nightstand-tray-aliexpress-acacia-rect-tray-30x20`, `nightstand-tray-cj-travertine-look-rect-milktea`, `open-shelf-ceramics-cj-patina-clay-pitcher-and-jar`, `paper-towel-holder-aliexpress-slotted-wood-round-base-31`, `pendant-cj-fluted-ceramic-wood-cap-short-lantern`, `pendant-cj-pleated-pumpkin-lantern-40`, `picture-lights-cj-black-tube-rechargeable`, `planter-cj-cement-ribbed-belly`, `planter-cj-seagrass-belly`, `pool-cj-linen-look-tassel-curtain`, `shower-curtain-cj-linen-look-khaki-grommet`, `sill-vase-cj-cream-fluted-column-25`, `soap-dispenser-cj-travertine-look-lotion-milktea`, `sofa-cover-cj-bubble-stretch-slipcover`, `sofa-cover-cj-polar-fleece-jacquard-slipcover`, `sofa-cover-cj-waffle-jacquard-stretch-slipcover`, `sofa-cover-cj-washed-hemp-throw`, `table-lamp-cj-white-teardrop-fabric-cone-25x45`, `table-runner-aliexpress-open-weave-linen-runner`, `tableware-set-cj-grey-sand-matte-plate`, `throw-cj-cotton-waffle-ruffle-khaki-150x200`, `toilet-brush-aliexpress-striped-ceramic-holder-165620`, `toothbrush-cup-cj-travertine-look-cup-milktea`, `vanity-sconces-cj-fluted-resin-updown-white`, `vanity-vase-aliexpress-sand-oat-bud-vase-g-series`, `vase-cj-charcoal-carved`, `vase-cj-faceted-cream`, `vase-cj-matte-moon-jar-white`, `wall-hooks-cj-light-wood-rail-5-brass-pegs-58`, `wall-hooks-cj-raw-wood-cylinder-peg-set-of-4`, `wall-sconce-cj-black-folding-arm-woodgrain-cone-18`, `wall-sconce-cj-black-swan-arm-white-fabric-cone`, `wall-sconce-cj-travertine-dome-15-pull`, `wall-sconce-cj-white-fabric-cube-15`.
- אחרי ההחלה, ב-120 מוצרים מחיר נגזר עדיין מפסיד (הרשימה המלאה ב-JSON, `site1_variant_floor.rows`); הגרוע בכל מוצר:

| מוצר | מחיר הכותרת | וריאנט | מחיר באתר | נחיתה | תרומה | רצפה (לא מפסיד) |
| --- | --- | --- | --- | --- | --- | --- |
| `rug-cj-braided-wool-natural` | ₪1,299 | size=150x200, other=around-tassel-style (variant) | ₪249 | ₪2,062.01 | ₪-1,874.05 | ₪2,719 |
| `pendant-cj-wabi-pleated-fabric-lantern-50` | ₪299 | size=80 (variant) | ₪329 | ₪1,324.36 | ₪-1,075.63 | ₪1,749 |
| `bedding-cj-cotton-linen-duvet-beige` | ₪479 | size=150x200, other=white (variant) | ₪249 | ₪682.04 | ₪-494.09 | ₪909 |
| `framed-art-cj-morandi-triptych-sage` | ₪379 | style=a, size=40x60 (variant) | ₪339 | ₪468.93 | ₪-212.60 | ₪619 |
| `floor-lamp-aliexpress-pleated-walnut-37x158-062736` | ₪949 | size=b-d39.5cm-h51cm, other=warm-light (variant) | ₪299 | ₪361.55 | ₪-135.61 | ₪479 |
| `floor-lamp-aliexpress-pleated-walnut-37x158-062736-master` | ₪949 | size=b-d39.5cm-h51cm, other=warm-light (variant) | ₪299 | ₪361.55 | ₪-135.61 | ₪479 |
| `curtains-aliexpress-cotton-linen-texture-translucent-091154` | ₪329 | set=1pc, width=100, length=200, style=pull_pleated, color=tulle (variant) | ₪9 | ₪109.20 | ₪-103.56 | ₪149 |
| `curtains-aliexpress-cotton-linen-texture-translucent` | ₪299 | set=1pc, width=100, length=200, style=rod_pocket, color=yarn (variant) | ₪19 | ₪85.96 | ₪-72.73 | ₪119 |
| `curtains-aliexpress-natural-linen-s-fold-613202` | — | color=white-color, style=2.-s-folded-tape, size=100x130 (variant) | ₪89 | ₪120.81 | ₪-54.40 | ₪169 |
| `pendant-cj-silk-ribbed-pumpkin-40` | — | size=30, other=warm-light (variant) | ₪139 | ₪152.92 | ₪-48.53 | ₪209 |
| `rug-cj-cream-embossed-arc-plush-200x300` | — | size=100x160 (variant) | ₪199 | ₪195.43 | ₪-45.45 | ₪259 |
| `planter-cj-cement-ribbed-belly` | ₪229 | color=grey, size=small (variant) | ₪59 | ₪86.56 | ₪-42.94 | ₪119 |
| `floor-lamp-cj-pleated-walnut-stem-158` | ₪769 | other=3-colortable-lamp (variant) | ₪649 | ₪531.17 | ₪-39.35 | ₪709 |
| `dining-pendant-cj-black-ring-cloth-lantern-50` | ₪359 | size=40 (variant) | ₪249 | ₪223.94 | ₪-35.98 | ₪299 |
| `sofa-cover-cj-polar-fleece-jacquard-slipcover` | ₪169 | color=dark-gray, other=pillowcase (variant) | ₪69 | ₪82.43 | ₪-31.22 | ₪119 |
| `bedding-cj-washed-linen-duvet-grey-220x240` | — | size=150x200 (variant) | ₪159 | ₪150.64 | ₪-31.06 | ₪209 |
| `bowl-aliexpress-kiln-corrugated-raw-rim-bowl-23` | ₪119 | color=brown-kiln-spoon (variant) | ₪9 | ₪36.17 | ₪-30.53 | ₪59 |
| `vase-cj-faceted-cream` | ₪219 | size=small (variant) | ₪129 | ₪126.26 | ₪-29.46 | ₪169 |
| `centerpiece-vase-aliexpress-nordic-matte-ceramic-vase` | ₪159 | size=s (variant) | ₪79 | ₪85.24 | ₪-26.43 | ₪119 |
| `soap-dispenser-aliexpress-beige-travertine-bathroom-accessorie-528496` | — | color=soap-dish-b (variant) | ₪119 | ₪114.48 | ₪-25.28 | ₪159 |
| `framed-art-aliexpress-retro-farmhouse-chicken-botanical-333603` | ₪129 | size=21x30-black-framed (variant) | ₪59 | ₪68.67 | ₪-25.05 | ₪99 |
| `curtains-aliexpress-beige-linen-sheer-curtains-554205` | — | style=metal-grommet-top, size=100x130 (variant) | ₪49 | ₪61.05 | ₪-25.03 | ₪89 |
| `curtains-aliexpress-beige-linen-sheer-curtains-554205-work` | — | style=metal-grommet-top, size=100x130 (variant) | ₪49 | ₪61.05 | ₪-25.03 | ₪89 |
| `sofa-cover-cj-bubble-stretch-slipcover` | ₪239 | color=cream-white, other=single (variant) | ₪179 | ₪157.97 | ₪-23.19 | ₪219 |
| `curtains-aliexpress-linen-blend-s-fold-180502` | — | style=pull-pleated-tape, size=100x130 (variant) | ₪19 | ₪36.07 | ₪-22.84 | ₪59 |
| `throw-cj-cotton-gauze-fringe-200x230-linen` | — | size=125x150 (variant) | ₪109 | ₪104.44 | ₪-22.84 | ₪149 |
| `sofa-cover-cj-washed-hemp-throw` | ₪229 | size=100x150, other=mustard-yellow (variant) | ₪139 | ₪125.93 | ₪-21.54 | ₪169 |
| `bench-pad-aliexpress-double-piping-cushion-130x35x5` | ₪289 | color=sg-6-light-gray, size=60x30x5 (variant) | ₪109 | ₪102.96 | ₪-21.36 | ₪139 |
| `sofa-cover-cj-waffle-jacquard-stretch-slipcover` | ₪159 | style=s-single, other=grass-green (variant) | ₪99 | ₪93.59 | ₪-19.58 | ₪129 |
| `bench-pad-aliexpress-linen-look-box-cushion-130x35x5` | ₪269 | color=color-10-rice-gray, size=35x35x5 (variant) | ₪89 | ₪84.22 | ₪-17.81 | ₪119 |
| `pendant-cj-pleated-pumpkin-lantern-40` | ₪449 | size=28 (variant) | ₪389 | ₪309.44 | ₪-15.13 | ₪409 |
| `bench-cushion-aliexpress-double-piping-cushion-110x35x5` | ₪259 | color=sg-6-light-gray, size=60x30x5 (variant) | ₪119 | ₪102.96 | ₪-13.76 | ₪139 |
| `throw-cj-waffle-blanket-200x230-beige` | — | size=100x150, other=dark-green (variant) | ₪89 | ₪80.09 | ₪-13.68 | ₪109 |
| `bedspread-cj-waffle-gauze-fringe-150x200` | — | color=linen-brown, size=80x130 (variant) | ₪59 | ₪56.79 | ₪-13.17 | ₪79 |
| `basket-aliexpress-seaweed-wicker-basket-rattan-977022` | — | color=16cm (variant) | ₪9 | ₪18.48 | ₪-12.84 | ₪29 |
| `vase-cj-black-matte-stoneware-jar-30` | — | style=style6 (variant) | ₪89 | ₪79.17 | ₪-12.76 | ₪109 |
| `gallery-art-aliexpress-antique-botanical-posters-prints-710412` | — | color=ph6531, size=21x30-a4-no-frame (variant) | ₪9 | ₪18.18 | ₪-12.55 | ₪29 |
| `nightstand-tray-cj-black-walnut-rect-tray` | — | color=brown (variant) | ₪29 | ₪33.36 | ₪-12.53 | ₪49 |
| `wall-sconce-cj-white-fabric-cube-15` | ₪279 | color=white, style=warm-white, size=12x12 (variant) | ₪229 | ₪185.20 | ₪-12.43 | ₪249 |
| `bedside-sconces-cj-white-fabric-cube-15` | — | color=white, style=warm-white, size=12x12 (variant) | ₪229 | ₪185.20 | ₪-12.43 | ₪249 |
| `basket-cj-seagrass-belly` | ₪99 | color=original, other=a (variant) | ₪49 | ₪47.49 | ₪-11.46 | ₪69 |
| `planter-cj-seagrass-belly` | ₪99 | color=original, other=a (variant) | ₪49 | ₪47.49 | ₪-11.46 | ₪69 |
| `bedding-aliexpress-boho-3d-tufted-cut-500672` | ₪349 | size=eu-single-size-2-pcs (variant) | ₪169 | ₪138.30 | ₪-11.12 | ₪189 |
| `vanity-vase-aliexpress-sand-oat-bud-vase-g-series` | ₪69 | color=b1a (variant) | ₪29 | ₪31.84 | ₪-11.01 | ₪49 |
| `framed-art-aliexpress-japanese-wabi-sabi-tree-176323` | ₪49 | size=20x30 (variant) | ₪9 | ₪16.43 | ₪-10.80 | ₪29 |
| `framed-art-aliexpress-japandi-wall-art-set-969661` | — | size=20x30-no-frame (variant) | ₪9 | ₪16.40 | ₪-10.76 | ₪29 |
| `vase-cj-matte-moon-jar-white` | ₪159 | style=styled (variant) | ₪129 | ₪107.45 | ₪-10.65 | ₪149 |
| `tableware-set-cj-speckled-oat-stoneware-bowl-13` | ₪79 | set=1pc (variant) | ₪49 | ₪46.63 | ₪-10.61 | ₪69 |
| `cutting-boards-aliexpress-2pcs-1pc-wooden-cutting-280363` | — | color=m (variant) | ₪49 | ₪46.63 | ₪-10.61 | ₪69 |
| `centerpiece-vase-cj-matte-frosted-tapered-28` | — | style=rope-1 (variant) | ₪79 | ₪69.37 | ₪-10.55 | ₪99 |
| `vase-cj-matte-frosted-tapered-28` | — | style=rope-1 (variant) | ₪79 | ₪69.37 | ₪-10.55 | ₪99 |
| `bath-towels-cj-cotton-waffle-white` | ₪69 | color=white, other=35x35cm (variant) | ₪29 | ₪31.25 | ₪-10.42 | ₪49 |
| `basket-cj-water-hyacinth-tub` | — | size=small (variant) | ₪159 | ₪129.89 | ₪-10.30 | ₪179 |
| `bench-cushion-aliexpress-linen-look-box-cushion-110x35x5` | ₪249 | color=color-10-rice-gray, size=35x35x5 (variant) | ₪99 | ₪84.22 | ₪-10.21 | ₪119 |
| `wall-sconce-cj-travertine-cube-updown-12` | — | style=type-b, other=indoor (variant) | ₪149 | ₪122 | ₪-10.01 | ₪169 |
| `basket-aliexpress-seaweed-wicker-basket-rattan-442162` | — | color=16cm-xs (variant) | ₪19 | ₪23.23 | ₪-10 | ₪39 |
| `nightstand-tray-cj-travertine-look-rect-milktea` | ₪129 | color=milk-tea-color, other=soap-dish (variant) | ₪89 | ₪76.39 | ₪-9.99 | ₪109 |
| `wall-hooks-cj-light-wood-rail-5-brass-pegs-58` | ₪99 | other=blackwalnut-2hooks (variant) | ₪69 | ₪60.75 | ₪-9.54 | ₪89 |
| `wall-sconce-cj-white-fabric-cube-15-hall` | — | color=white, style=warm-white, size=12x12 (variant) | ₪119 | ₪98.74 | ₪-9.54 | ₪139 |
| `desk-tray-cj-black-walnut-tray-25x16` | — | size=20x13x1.5 (variant) | ₪39 | ₪37.95 | ₪-9.52 | ₪59 |
| `framed-art-aliexpress-frameless-minimalist-wall-art-631735` | — | color=tl2356-2, size=20x30-no-frame (variant) | ₪9 | ₪14.65 | ₪-9.02 | ₪29 |
| `throw-cj-cotton-waffle-ruffle-khaki-150x200` | ₪149 | color=grey, size=100x150 (variant) | ₪99 | ₪82.90 | ₪-8.89 | ₪119 |
| `framed-art-aliexpress-modern-minimalist-neutral-gallery-802995` | — | color=03, size=20x25-no-frame (variant) | ₪19 | ₪21.85 | ₪-8.61 | ₪39 |
| `open-shelf-ceramics-cj-patina-clay-pitcher-and-jar` | ₪229 | other=sy-c03d137 (variant) | ₪159 | ₪128.17 | ₪-8.59 | ₪179 |
| `cushions-aliexpress-fashion-modern-wabi-sabi-464203` | ₪69 | color=1pcs-beige, size=30x50 (variant) | ₪49 | ₪44.58 | ₪-8.56 | ₪69 |
| `sofa-cover-cj-chunky-knit-tassel` | — | size=110x150, other=beige (variant) | ₪129 | ₪104.94 | ₪-8.14 | ₪149 |
| `shower-curtain-cj-linen-look-khaki-grommet` | ₪79 | color=linen-gray-large-hole, size=100x180-single-curtain (variant) | ₪49 | ₪44.12 | ₪-8.10 | ₪69 |
| `wall-sconce-cj-black-folding-arm-woodgrain-cone-18` | ₪119 | color=the-pattern-of-walnut, other=white-light (variant) | ₪99 | ₪81.77 | ₪-7.77 | ₪119 |
| `cushions-aliexpress-textured-boucle-throw-pillow` | ₪59 | size=30x50, color=beige (variant) | ₪39 | ₪36.07 | ₪-7.64 | ₪59 |
| `candle-holders-aliexpress-cutelife-black-ceramic-candelabra` | ₪119 | color=white, set=1pc (variant) | ₪99 | ₪81.64 | ₪-7.64 | ₪119 |
| `pool-cj-linen-look-tassel-curtain` | ₪119 | style=width-150-height-160cm, other=diamond-plaid-stitching (variant) | ₪89 | ₪74.02 | ₪-7.61 | ₪109 |
| `wall-hooks-aliexpress-pine-oval-pegs-4pcs` | — | set=1pc (variant) | ₪9 | ₪13.07 | ₪-7.43 | ₪19 |
| `curtains-cj-linen-yarn-sheer-tab` | — | color=gray, other=double-pack-5272 (variant) | ₪99 | ₪80.92 | ₪-6.91 | ₪109 |
| `nightstand-tray-aliexpress-acacia-rect-tray-30x20` | ₪99 | size=20 (variant) | ₪39 | ₪35.14 | ₪-6.72 | ₪49 |
| `basket-zendrop-seagrass-belly-38x34` | — | size=d22-h20 (variant) | ₪39 | ₪34.68 | ₪-6.26 | ₪49 |
| `bedding-cj-cotton-linen-gauze-cover-natural-220x240` | — | color=natural-polka-dot, other=150x200cm-cover (variant) | ₪219 | ₪171.24 | ₪-6.07 | ₪229 |
| `bowl-aliexpress-pearl-rim-ingot-bowl-23` | ₪129 | color=dessert-bowl-small (variant) | ₪69 | ₪57.29 | ₪-6.07 | ₪79 |
| `framed-art-aliexpress-mediterranean-wabi-sabi-poster-802890` | — | color=05, size=30x40-no-frame (variant) | ₪19 | ₪19.07 | ₪-5.84 | ₪29 |
| `basket-cj-jute-rope-cylinder` | ₪109 | other=small (variant) | ₪89 | ₪72.07 | ₪-5.66 | ₪99 |
| `centerpiece-vase-aliexpress-nordic-morandi-matte-ceramic` | ₪209 | set=3pc, style=e (variant) | ₪179 | ₪140.38 | ₪-5.60 | ₪189 |
| `basket-cj-jute-cotton-rope-cylinder-30-hall` | — | color=cotton-white, size=d30-h30 (variant) | ₪69 | ₪56.73 | ₪-5.51 | ₪79 |
| `paper-towel-holder-aliexpress-slotted-wood-round-base-31` | ₪89 | style=style-1 (variant) | ₪49 | ₪41.45 | ₪-5.42 | ₪59 |
| `ceiling-light-cj-waxwood-dome-ash-40` | ₪269 | color=white-light, size=small (variant) | ₪239 | ₪185.76 | ₪-5.40 | ₪249 |
| `table-runner-aliexpress-open-weave-linen-runner` | ₪99 | color=tea-green, size=20x60 (variant) | ₪59 | ₪48.54 | ₪-4.92 | ₪69 |
| `soap-dispenser-cj-travertine-look-lotion-milktea` | ₪79 | color=milk-tea-color, other=soap-dish (variant) | ₪59 | ₪48.51 | ₪-4.89 | ₪69 |
| `framed-art-cj-line-scribble-white-mat-50` | ₪229 | style=a, size=30x30 (variant) | ₪189 | ₪146.59 | ₪-4.21 | ₪199 |
| `centerpiece-vase-aliexpress-modern-minimalist-white-ceramic` | ₪109 | size=small (variant) | ₪79 | ₪62.83 | ₪-4.02 | ₪89 |
| `toothbrush-cup-cj-travertine-look-cup-milktea` | ₪49 | color=milk-tea-color, other=soap-dish (variant) | ₪39 | ₪31.84 | ₪-3.42 | ₪49 |
| `key-tray-cj-black-walnut-tray-20x13` | — | size=13x13x1.5 (variant) | ₪39 | ₪31.84 | ₪-3.42 | ₪49 |
| `bedspread-cj-muslin-grid-gauze-sage-160x220` | — | color=white, size=140x160-full (variant) | ₪79 | ₪62.20 | ₪-3.39 | ₪89 |
| `cushions-cj-chenille-check-milky-white` | — | color=small-plaid-blue, size=45x45-pillowcase (variant) | ₪39 | ₪31.81 | ₪-3.39 | ₪49 |
| `bedding-cj-washed-polyester-set-milk-tea` | ₪149 | color=gemstone-green, size=200x230-quilt-cover (variant) | ₪149 | ₪115.27 | ₪-3.28 | ₪159 |
| `gallery-art-aliexpress-japanese-wabi-sabi-tree-176323` | — | size=20x30 (variant) | ₪19 | ₪16.43 | ₪-3.20 | ₪29 |
| `condiment-set-zendrop-wood-mills-black-white-21` | ₪89 | set=black (variant) | ₪69 | ₪54.19 | ₪-2.97 | ₪79 |
| `bowl-cj-matte-black-bowl-20` | — | other=2style (variant) | ₪39 | ₪31.38 | ₪-2.96 | ₪49 |
| `mug-set-cj-cream-matte-breakfast-cup` | ₪129 | המק"ט שבחדר (single) | ₪49 | ₪38.94 | ₪-2.92 | ₪59 |
| `nightstand-tray-cj-ebony-rounded-rect-25x18` | — | other=rectangular-20x13cm (variant) | ₪39 | ₪31.22 | ₪-2.79 | ₪49 |
| `bookends-aliexpress-beech-wooden-bookends-219885` | — | המק"ט שבחדר (single) | ₪29 | ₪23.33 | ₪-2.50 | ₪39 |
| `bench-pad-cj-tufted-long-cushion-khaki-120` | ₪139 | color=black, size=130x50x8 (variant) | ₪129 | ₪99.13 | ₪-2.34 | ₪139 |
| `centerpiece-vase-cj-sandy-white-bead-band-25` | ₪289 | other=2345-white (variant) | ₪259 | ₪197.87 | ₪-2.32 | ₪269 |
| `candle-holders-cj-ceramic-chamberstick-beige-pair` | — | המק"ט שבחדר (single) | ₪69 | ₪53.46 | ₪-2.24 | ₪79 |
| `toilet-brush-aliexpress-striped-ceramic-holder-165620` | ₪119 | color=elephant-white (variant) | ₪79 | ₪61.05 | ₪-2.24 | ₪89 |
| `bowl-cj-vietnam-rattan-fruit-plate-25` | — | size=23 (variant) | ₪39 | ₪30.66 | ₪-2.23 | ₪49 |
| `table-runner-cj-pure-white-woven` | — | size=30x50, other=middle-rhombus (variant) | ₪29 | ₪23.03 | ₪-2.20 | ₪39 |
| `desk-tray-cj-acacia-organic-tray-30x20` | — | size=16x13x2 (variant) | ₪49 | ₪37.98 | ₪-1.96 | ₪59 |
| `table-runner-aliexpress-solid-color-textured-runner-525144` | — | size=33x91 (variant) | ₪29 | ₪22.64 | ₪-1.81 | ₪39 |
| `candle-holders-cj-ceramic-pedestal-tray` | — | המק"ט שבחדר (single) | ₪59 | ₪45.34 | ₪-1.72 | ₪69 |
| `bowl-cj-reactive-white-rimmed-plate-21` | ₪89 | set=1pc, other=7.7-inches (variant) | ₪79 | ₪60.16 | ₪-1.35 | ₪89 |
| `wall-hooks-cj-walnut-block-peg-set-of-4` | — | color=beech (variant) | ₪29 | ₪22.18 | ₪-1.35 | ₪39 |
| `bath-towels-cj-waffle-cotton-milky-white-70x140` | — | המק"ט שבחדר (single) | ₪49 | ₪37.26 | ₪-1.23 | ₪59 |
| `tea-towel-cj-waffle-cotton-beige-45x65-pair` | — | color=dark-gray, size=35x35 (variant) | ₪29 | ₪22.04 | ₪-1.21 | ₪39 |
| `mug-set-cj-speckled-stoneware-mug-raw-rim-set3` | — | color=black-white-dots, set=mug (variant) | ₪49 | ₪37.16 | ₪-1.13 | ₪59 |
| `toilet-paper-stand-aliexpress-stainless-steel-toilet-paper-254527` | — | color=silver (variant) | ₪69 | ₪52.07 | ₪-0.86 | ₪79 |
| `wall-sconce-cj-black-swan-arm-white-fabric-cone` | ₪119 | color=black, style=single-head, other=no-bulb-included (variant) | ₪109 | ₪82.20 | ₪-0.60 | ₪119 |
| `basket-aliexpress-plant-basket-handles-wicker-464380` | — | size=s (variant) | ₪39 | ₪28.97 | ₪-0.55 | ₪49 |
| `mug-set-aliexpress-oat-matte-cup-acacia-saucer-573382` | ₪229 | המק"ט שבחדר (single) | ₪79 | ₪59.23 | ₪-0.42 | ₪89 |
| `candle-holders-cj-black-iron-ball-foot-plate-11` | — | המק"ט שבחדר (single) | ₪29 | ₪21.19 | ₪-0.36 | ₪39 |
| `magazine-holder-cj-felt-snap-bucket` | ₪59 | color=black-without-lining, size=30x42-medium (variant) | ₪49 | ₪36.20 | ₪-0.18 | ₪59 |
| `soft-toy-aliexpress-handmade-crochet-bunny-baby-999497` | — | color=zebra-12cm (variant) | ₪49 | ₪36.20 | ₪-0.18 | ₪59 |
| `basket-cj-two-tone-rope-jute-white-30` | — | color=natural-white, size=20x20 (variant) | ₪49 | ₪36.13 | ₪-0.11 | ₪59 |

## כמות המכירה

| מוצר | יח' בסטודיו | יח' בדוח | מחיר | בסיס | אם יחידה אחת | סימון |
| --- | --- | --- | --- | --- | --- | --- |
| `accent-sconces-aliexpress-fluted-white-ceramic-tulip-wall-sconce-on` | 2 | 2 | ₪999 | the row's price for the sale | ₪299 | qty-inferred-from-landed |
| `accent-sconces-aliexpress-scalloped-white-ceramic-flower-wall-sconce-on` | 2 | 2 | ₪649 | the row's price for the sale | ₪209 | qty-inferred-from-landed |
| `cutting-boards-cj-black-walnut-paddle-pair-39-34` | 2 | 2 | ₪279 | the row's price for the sale | ₪149 | qty-inferred-from-landed |
| `framed-art-aliexpress-japandi-bare-branch-70x100-776445` | 2 | 2 | ₪349 | the row's price for the sale | ₪89 | qty-inferred-from-landed |
| `framed-art-aliexpress-minimal-geometric-triptych-prints` | 3 | 3 | ₪199 | the row's price for the sale | ₪59 | qty-inferred-from-landed |
| `framed-prints-aliexpress-watercolour-bunny-nursery-prints` | 2 | 2 | ₪119 | the row's price for the sale | ₪29 | qty-inferred-from-landed |
| `framed-prints-aliexpress-watercolour-sun-and-rainbow-nursery-prints` | 2 | 2 | ₪119 | the row's price for the sale | ₪39 | qty-inferred-from-landed |
| `kitchen-sconce-aliexpress-rustic-wooden-wall-sconce-632957` | 1 | 1 | ₪229 | the row's price for the sale | יחידה אחת | unit-override |
| `shelf-boxes-aliexpress-seagrass-lidded-box-32x22-pair` | 2 | 2 | ₪219 | the row's price for the sale | ₪89 | qty-inferred-from-landed |
| `shelf-boxes-cj-felt-storage-bin-30x24-pair` | 2 | 2 | ₪63 | the row's price for the sale | ₪49 | qty-inferred-from-landed |
| `shelf-boxes-cj-lined-straw-basket-28x21x17-pair` | 2 | 2 | ₪149 | the row's price for the sale | ₪79 | qty-inferred-from-landed |
| `toy-cars-aliexpress-wooden-toys-beech-wood-138166` | 3 | 3 | ₪159 | the row's price for the sale | ₪59 | qty-inferred-from-landed |
| `vanity-sconces-aliexpress-wabi-sabi-yellow-marble-037853` | 2 | 2 | ₪659 | the row's price for the sale | ₪309 | qty-inferred-from-landed |
| `shelf-boxes-cj-two-tone-fabric-bin-27x20x12-pair` | 2 | 2 | ₪63 | the row's price for the sale | ₪49 | qty-inferred-from-landed |

- תיקון כמות בכרטיס: `kitchen-sconce-aliexpress-rustic-wooden-wall-sconce-632957` sell_qty None → 1 (המנהל (2026-10-20): מנורת מטבח אחת, לא 4. הסטודיו הסיק 4 יח' מעלות הנחיתה ברשומה (₪100.6 = יחידה אחת + משלוח)).

## קלטים מוערכים וסימונים

- `qty-freight-estimated`: 30 מוצרים
- `freight-from-cache-only`: 26 מוצרים
- `options-with-sale-cost`: 17 מוצרים
- `qty-inferred-from-landed`: 13 מוצרים
- `freight-estimated`: 8 מוצרים
- `freight-missing`: 8 מוצרים
- `freight-from-other-sku`: 6 מוצרים
- `express-only`: 6 מוצרים
- `sale-cost-from-leads`: 6 מוצרים
- `options-are-set-parts`: 4 מוצרים
- `cost-not-usd`: 1 מוצרים
- `no-route`: 1 מוצרים
- `freight-quote-other-qty`: 1 מוצרים
- `unit-override`: 1 מוצרים

## מועמדים שנדחו רק בגלל הפסד

51 מועמדים (סבבים 5 ו-6, התאמה 7+) נדחו רק בגלל ההפסד; הרשימה המלאה בדוח הדיווח (no-loss-report-2026-10-20.md). אם ייספרו: nordic +1 (65.3→66.3%), warm-modern +3 (65.3→67.7%), japandi +2 (61.3→62.9%), mediterranean +5 (60.5→64.5%), modern-country +4 (57.3→60.5%), boho +5 (58.9→62.9%); סה"כ 442 → 462 עמדות (61.3→64.1%). להחלטת המשתמש.

## מה עוד צריך

- NL2: המוצרים ביחס מעל 2, ומוצרי האקספרס-בלבד (העלאה, או "המלאי אינו זמין כעת" לפי PRE1).
- SITE1: רצפה למחיר וריאנט נגזר וליחידה בודדת; הסטודיו מציג רק ok/below-floor/loss (above-market, express-only ו-cannot-compute לא מוצגים כתווית); האתר לא קורא את flag (מוצר שמסומן לא למכירה נמכר באתר).
- ממשיכים לחפש חלופה זולה יותר באותו מראה למוצרים שהועלו הרבה (ה.13).
