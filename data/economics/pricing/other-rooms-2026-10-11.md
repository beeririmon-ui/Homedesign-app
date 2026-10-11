# תמחור ראשוני: שאר החדרים (2026-10-11)

קובץ הנתונים: `other-rooms-2026-10-11.json`. 93 מוצרים: מטבח ופינת אוכל, חדר שינה, אמבטיה, ילדים, כניסה, מסדרון, חדר עבודה והמאגר המשותף. המחירים הם הצעה ראשונית, וכולם ממתינים לאישור המשתמש.

## שיטה

1. **ערך ישראלי:** לכל מוצר 2–5 מוצרים דומים ברשתות ישראליות (IKEA, Fox Home, Home Style, Terminal X, Cotton Club, LEDmarket, נעמן, ACE, Home Center, ו-Zara Home ו-H&M לפי תקציר חיפוש). "טיפוסי" הוא המחיר שהלקוח משלם היום ברמת הביניים, לא הבסיס של IKEA. Home Style מוכרת כמעט הכול ב-50% ממחיר מחוק קבוע, ו-Fox Home ב-30% הנחה על 91% מהקטלוג, ולכן נספר המחיר בפועל (המחוק נשמר ב-list_price).
2. **מחיר:** הסה"כ ללקוח (מחיר + ₪29 משלוח, חינם מ-₪299) כ-10–15% מתחת לטיפוסי; קרוב יותר לטיפוסי בסטים ובפריטים עיצוביים, ולעולם לא מעליו. נקודות מחיר שמסתיימות ב-9. במחירים סביב ₪280 נבחר ₪299 (משלוח חינם).
3. **רווחיות לדיווח בלבד:** שער 3.3, מע"מ 18%, סליקה 2% + ₪1.2, שמורת החזרות 8% מהנטו, CAC ‏₪71.4 לפריט. המחיר לא הועלה כדי לתקן מרווח.
4. **דגלים (VR1):** ok = מרווח 40% ומעלה; below-floor = 0–40%; loss = תרומה שלילית. "חלופה בעמדה" = מוצר אחר באותה עמדה (או shared_in) שמגיע ל-40% **ובציון נורדי לא נמוך יותר**. כשאין חלופה כזו, החריג (מרווח נמוך כדי למלא עמדה) יכול לחול.

## שורה תחתונה

- **דגלים:** ok ‏5, below-floor ‏18, loss ‏70.
- **מחיר מול טיפוסי:** חציון המחיר הוא 69% מהטיפוסי, וחציון הסה"כ ללקוח (כולל משלוח) -11% מול הטיפוסי.
- **הסיבה להפסדים היא המשלוח, לא המחיר:** במנורות, אגרטלים, תמונות ממוסגרות ופריטי אמבטיה קטנים, משלוח CJ לבד ($10–90) קרוב למחיר המדף הישראלי או גבוה ממנו. הטקסטיל (מצעים, שמיכות מוסלין, ציפיות פשתן) והסטים של תמונות הם מה שמרוויח.
- **פריטים קטנים (טיפוסי עד ₪89):** עם ₪29 משלוח הם לא יכולים להיות זולים מהשוק לבד; הם מסומנים addon_only (תוספת לסל, חינם מ-₪299, או חלק מסט). בשניים מהם (צלחת בודדת, מגבת מטבח) גם ₪19 לבד גבוה מהטיפוסי, והם יימכרו רק בסט או בסל.
- **כיסא מאיה:** המחיר הוא המחיר הציבורי של ריהוט אקספרס (₪399); הרווחיות תלויה בתנאי השותפות (מחיר סוחר עדיין לא התקבל).

## טבלת מחירים

| מוצר | חדר | מחיר | טיפוסי בישראל | סה"כ ללקוח | מרווח | דגל |
| --- | --- | --- | --- | --- | --- | --- |
| `bath-mat-cj-solid-wood-slatted-61x45` | אמבטיה | ₪129 | ₪179 | ₪158 (-12%) | -197% | loss |
| `bath-mat-cj-tufted-cotton-frame-beige-40x60` | אמבטיה | ₪39 | ₪79 | ₪68 (-14%) | -74% | loss |
| `bath-towels-cj-cotton-waffle-white` | אמבטיה | ₪49 | ₪89 | ₪78 (-12%) | -24% | loss |
| `ceiling-light-cj-opal-glass-drum-flush-32` | אמבטיה | ₪149 | ₪199 | ₪178 (-11%) | -59% | loss |
| `reed-diffuser-cj-travertine-look-bamboo-lid-milktea` | אמבטיה | ₪39 | ₪79 | ₪68 (-14%) | -64% | loss |
| `shower-curtain-cj-linen-look-khaki-grommet` | אמבטיה | ₪39 | ₪69 | ₪68 (-1%) | -85% | loss |
| `soap-dispenser-cj-matte-ceramic-cream-black-pump` | אמבטיה | ₪39 | ₪69 | ₪68 (-1%) | -58% | loss |
| `soap-dispenser-cj-travertine-look-lotion-milktea` | אמבטיה | ₪49 | ₪79 | ₪78 (-1%) | -47% | loss |
| `toothbrush-cup-cj-silver-travertine-cup` | אמבטיה | ₪79 | ₪119 | ₪108 (-9%) | -68% | loss |
| `toothbrush-cup-cj-travertine-look-cup-milktea` | אמבטיה | ₪19 | ₪49 | ₪48 (-2%) | -130% | loss |
| `vanity-sconces-cj-flat-halo-disc-white` | אמבטיה | ₪79 | ₪129 | ₪108 (-16%) | 12% | below-floor |
| `vanity-sconces-cj-fluted-resin-updown-white` | אמבטיה | ₪229 | ₪279 | ₪258 (-8%) | -10% | loss |
| `vanity-sconces-cj-ip65-mini-updown-white` | אמבטיה | ₪49 | ₪89 | ₪78 (-12%) | -32% | loss |
| `ceiling-lights-cj-pleated-fabric-saucer-flush-50` | מסדרון | ₪499 | ₪538 | ₪499 (-7%) | -11% | loss |
| `ceiling-lights-cj-silk-cocoon-flush-40` | מסדרון | ₪219 | ₪269 | ₪248 (-8%) | -37% | loss |
| `gallery-art-cj-black-botanical-cutout-set3` | מסדרון | ₪349 | ₪399 | ₪349 (-13%) | 61% | ok |
| `picture-lights-cj-black-tube-rechargeable` | מסדרון | ₪59 | ₪99 | ₪88 (-11%) | -33% | loss |
| `bench-pad-cj-tufted-long-cushion-khaki-120` | מטבח ופינת אוכל | ₪59 | ₪99 | ₪88 (-11%) | -116% | loss |
| `bowl-cj-glutinous-white-belly-bowl-21` | מטבח ופינת אוכל | ₪39 | ₪69 | ₪68 (-1%) | -74% | loss |
| `candle-holders-aliexpress-cutelife-black-ceramic-candelabra` | מטבח ופינת אוכל | ₪39 | ₪69 | ₪68 (-1%) | -180% | loss |
| `candle-holders-aliexpress-matte-black-iron-pillar-set2` | מטבח ופינת אוכל | ₪39 | ₪69 | ₪68 (-1%) | -38% | loss |
| `canisters-zendrop-matte-ceramic-bamboo-lid-sml` | מטבח ופינת אוכל | ₪89 | ₪129 | ₪118 (-9%) | -15% | loss |
| `centerpiece-vase-aliexpress-modern-minimalist-white-ceramic` | מטבח ופינת אוכל | ₪59 | ₪99 | ₪88 (-11%) | -67% | loss |
| `centerpiece-vase-aliexpress-nordic-matte-ceramic-vase` | מטבח ופינת אוכל | ₪89 | ₪129 | ₪118 (-9%) | -66% | loss |
| `centerpiece-vase-aliexpress-nordic-morandi-matte-ceramic` | מטבח ופינת אוכל | ₪199 | ₪249 | ₪228 (-8%) | -2% | loss |
| `centerpiece-vase-cj-sandy-white-bead-band-25` | מטבח ופינת אוכל | ₪59 | ₪99 | ₪88 (-11%) | -337% | loss |
| `condiment-set-cj-rubberwood-mill-pair-6in` | מטבח ופינת אוכל | ₪49 | ₪89 | ₪78 (-12%) | -28% | loss |
| `condiment-set-zendrop-wood-mills-black-white-21` | מטבח ופינת אוכל | ₪59 | ₪99 | ₪88 (-11%) | -44% | loss |
| `dining-chairs-furniture-express-maya` | מטבח ופינת אוכל | ₪399 | ₪449 | ₪399 (-11%) | -49% | loss |
| `dining-pendant-cj-black-ring-cloth-lantern-50` | מטבח ופינת אוכל | ₪229 | ₪279 | ₪258 (-8%) | -49% | loss |
| `floor-vase-aliexpress-capiron-zen-ceramic` | מטבח ופינת אוכל | ₪49 | ₪89 | ₪78 (-12%) | -133% | loss |
| `framed-art-aliexpress-retro-farmhouse-chicken-botanical-333603` | מטבח ופינת אוכל | ₪89 | ₪139 | ₪118 (-15%) | -40% | loss |
| `framed-art-cj-swinging-line-black-frame-mat-35x45` | מטבח ופינת אוכל | ₪129 | ₪179 | ₪158 (-12%) | -48% | loss |
| `framed-art-cj-taupe-block-black-line-30x40` | מטבח ופינת אוכל | ₪109 | ₪159 | ₪138 (-13%) | -55% | loss |
| `mug-set-cj-cream-matte-breakfast-cup` | מטבח ופינת אוכל | ₪39 | ₪69 | ₪68 (-1%) | -193% | loss |
| `mug-set-cj-oat-speckled-round-mug-wood-saucer` | מטבח ופינת אוכל | ₪19 | ₪49 | ₪48 (-2%) | -293% | loss |
| `open-shelf-ceramics-cj-morandi-matte-bottle-set` | מטבח ופינת אוכל | ₪79 | ₪119 | ₪108 (-9%) | -58% | loss |
| `paper-towel-holder-aliexpress-1pc-bamboo-paper-towel-316063` | מטבח ופינת אוכל | ₪39 | ₪69 | ₪68 (-1%) | 16% | below-floor |
| `paper-towel-holder-cj-beech-upright-31` | מטבח ופינת אוכל | ₪39 | ₪69 | ₪68 (-1%) | -90% | loss |
| `table-runner-aliexpress-boho-macrame-table-runners-263532` | מטבח ופינת אוכל | ₪69 | ₪109 | ₪98 (-10%) | 30% | below-floor |
| `tableware-set-cj-grey-sand-matte-plate` | מטבח ופינת אוכל | ₪19 | ₪39 | ₪48 (+23%) | -400% | loss |
| `tableware-set-cj-speckled-oat-stoneware-bowl-13` | מטבח ופינת אוכל | ₪29 | ₪59 | ₪58 (-2%) | -154% | loss |
| `tea-towel-zendrop-cotton-linen-washed-60x45` | מטבח ופינת אוכל | ₪19 | ₪29 | ₪48 (+66%) | -92% | loss |
| `ceiling-light-cj-waxwood-dome-ash-40` | כניסה | ₪199 | ₪249 | ₪228 (-8%) | -28% | loss |
| `framed-art-cj-line-scribble-white-mat-50` | כניסה | ₪129 | ₪179 | ₪158 (-12%) | -63% | loss |
| `table-lamp-cj-pleated-shade-wood-column` | כניסה | ₪149 | ₪199 | ₪178 (-11%) | -68% | loss |
| `table-lamp-cj-white-teardrop-fabric-cone-25x45` | כניסה | ₪99 | ₪149 | ₪128 (-14%) | -37% | loss |
| `table-lamp-cj-white-textured-ceramic-linen-drum` | כניסה | ₪199 | ₪249 | ₪228 (-8%) | -14% | loss |
| `wall-hooks-cj-light-wood-rail-5-brass-pegs-58` | כניסה | ₪89 | ₪129 | ₪118 (-9%) | -8% | loss |
| `wall-hooks-cj-raw-wood-cylinder-peg-set-of-4` | כניסה | ₪39 | ₪79 | ₪68 (-14%) | -26% | loss |
| `wall-sconce-cj-wavy-linen-flush-25` | כניסה | ₪149 | ₪199 | ₪178 (-11%) | -32% | loss |
| `bedding-cj-cream-ruffle-rosebud-set` | ילדים | ₪299 | ₪349 | ₪299 (-14%) | 26% | below-floor |
| `bedding-cj-muslin-cotton-duvet-dune` | ילדים | ₪179 | ₪229 | ₪208 (-9%) | 20% | below-floor |
| `bedding-cj-washed-polyester-set-milk-tea` | ילדים | ₪99 | ₪149 | ₪128 (-14%) | -45% | loss |
| `bedspread-cj-muslin-blanket-beige-150x200` | ילדים | ₪199 | ₪259 | ₪228 (-12%) | 41% | ok |
| `bedspread-cj-six-layer-gauze-quilt` | ילדים | ₪199 | ₪259 | ₪228 (-12%) | 47% | ok |
| `cushions-cj-dusty-pink-corduroy-patchwork-45` | ילדים | ₪59 | ₪99 | ₪88 (-11%) | -18% | loss |
| `framed-prints-cj-charcoal-line-black-frame-35x45` | ילדים | ₪129 | ₪179 | ₪158 (-12%) | -48% | loss |
| `framed-prints-cj-flower-cutout-set-30x40` | ילדים | ₪229 | ₪299 | ₪258 (-14%) | 54% | ok |
| `pendant-cj-fabric-dome-ash-cap-25` | ילדים | ₪119 | ₪169 | ₪148 (-12%) | -54% | loss |
| `skateboard-cj-blank-maple-43` | ילדים | ₪79 | ₪119 | ₪108 (-9%) | -8% | loss |
| `toy-cars-cj-beech-peg-bus` | ילדים | ₪129 | ₪177 | ₪158 (-11%) | 30% | below-floor |
| `wall-sconce-cj-black-folding-arm-woodgrain-cone-18` | ילדים | ₪99 | ₪149 | ₪128 (-14%) | -18% | loss |
| `wall-sconce-cj-black-swing-arm-wood-shade` | ילדים | ₪119 | ₪169 | ₪148 (-12%) | -231% | loss |
| `bedding-aliexpress-boho-3d-tufted-cut-500672` | חדר שינה | ₪349 | ₪399 | ₪349 (-13%) | 17% | below-floor |
| `bedding-cj-cotton-linen-duvet-beige` | חדר שינה | ₪479 | ₪549 | ₪479 (-13%) | -103% | loss |
| `bedding-cj-plain-linen-flat-sheet-raw-jute-260x280` | חדר שינה | ₪469 | ₪549 | ₪469 (-15%) | 32% | below-floor |
| `bedding-cj-washed-cotton-khaki-set-220x240` | חדר שינה | ₪349 | ₪399 | ₪349 (-13%) | 21% | below-floor |
| `bedding-cj-washed-linen-natural-set` | חדר שינה | ₪799 | ₪899 | ₪799 (-11%) | 44% | ok |
| `bedside-sconces-cj-linen-half-drum-black-trim` | חדר שינה | ₪349 | ₪399 | ₪349 (-13%) | -9% | loss |
| `bedside-sconces-cj-linen-wave-flush` | חדר שינה | ₪349 | ₪399 | ₪349 (-13%) | 1% | below-floor |
| `floor-lamp-cj-cream-arc-pleated-152` | חדר שינה | ₪349 | ₪399 | ₪349 (-13%) | -779% | loss |
| `floor-lamp-cj-pleated-walnut-stem-158` | חדר שינה | ₪349 | ₪399 | ₪349 (-13%) | -107% | loss |
| `nightstand-tray-cj-travertine-look-rect-milktea` | חדר שינה | ₪59 | ₪99 | ₪88 (-11%) | -102% | loss |
| `pendant-cj-light-wood-slat-drum-43` | חדר שינה | ₪299 | ₪349 | ₪299 (-14%) | 15% | below-floor |
| `pendant-cj-wabi-pleated-fabric-lantern-50` | חדר שינה | ₪299 | ₪329 | ₪299 (-9%) | -430% | loss |
| `pillowcases-cj-linen-pair-coconut-button` | חדר שינה | ₪129 | ₪179 | ₪158 (-12%) | 21% | below-floor |
| `pillowcases-cj-pure-linen-envelope-pair-48x74` | חדר שינה | ₪129 | ₪179 | ₪158 (-12%) | 21% | below-floor |
| `sill-vase-cj-cream-fluted-column-25` | חדר שינה | ₪49 | ₪89 | ₪78 (-12%) | -7% | loss |
| `throw-cj-cotton-linen-light-gray-200x230` | חדר שינה | ₪229 | ₪299 | ₪258 (-14%) | 13% | below-floor |
| `throw-cj-cotton-waffle-ruffle-khaki-150x200` | חדר שינה | ₪149 | ₪199 | ₪178 (-11%) | 7% | below-floor |
| `pool-cj-cotton-linen-box-camel-40x30` | מאגר | ₪29 | ₪59 | ₪58 (-2%) | -37% | loss |
| `pool-cj-carbonized-wood-pedestal-candlestick` | מאגר | ₪69 | ₪109 | ₪98 (-10%) | -68% | loss |
| `pool-cj-linen-look-tassel-curtain` | מאגר | ₪59 | ₪99 | ₪88 (-11%) | -82% | loss |
| `pool-cj-woven-cotton-runner-fringe` | מאגר | ₪69 | ₪109 | ₪98 (-10%) | 32% | below-floor |
| `pool-cj-travertine-organic-tray-24` | מאגר | ₪119 | ₪159 | ₪148 (-7%) | -31% | loss |
| `pool-cj-terracotta-amphora-floor-51` | מאגר | ₪479 | ₪549 | ₪479 (-13%) | -90% | loss |
| `pool-cj-wabi-sabi-floor-vase-white` | מאגר | ₪349 | ₪399 | ₪349 (-13%) | -7% | loss |
| `pool-cj-wood-sunburst-mirror-43` | מאגר | ₪119 | ₪169 | ₪148 (-12%) | 7% | below-floor |
| `framed-art-aliexpress-japanese-wabi-sabi-tree-176323` | חדר עבודה | ₪39 | ₪69 | ₪68 (-1%) | 11% | below-floor |
| `pendant-cj-fluted-ceramic-wood-cap-short-lantern` | חדר עבודה | ₪149 | ₪199 | ₪178 (-11%) | -2% | loss |
| `wall-sconce-cj-black-swan-arm-white-fabric-cone` | חדר עבודה | ₪79 | ₪129 | ₪108 (-16%) | -39% | loss |
| `wall-sconce-cj-white-fabric-cube-15` | חדר עבודה | ₪99 | ₪149 | ₪128 (-14%) | -42% | loss |

## below-floor לפי עמדה

✱ = אין בעמדה חלופה שמגיעה ל-40% בציון עיצוב שווה או גבוה, ולכן **החריג נדרש** כדי למלא אותה.

- **(מאגר, בלי עמדה)**
  - `pool-cj-woven-cotton-runner-fringe`: ₪69, מרווח 32%, ציון נורדי 6.0. פריט מאגר. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
  - `pool-cj-wood-sunburst-mirror-43`: ₪119, מרווח 7%, ציון נורדי —. פריט מאגר. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
- **bath/vanity-sconces** ✱
  - `vanity-sconces-cj-flat-halo-disc-white`: ₪79, מרווח 12%, ציון נורדי —. אין חלופה. פעולה: לזוג (2 יח') ₪199 (כ-36%); עדיין צריך אישור IP44 לפני חדר רחצה.
- **dining-room/paper-towel-holder** ✱
  - `paper-towel-holder-aliexpress-1pc-bamboo-paper-towel-316063`: ₪39, מרווח 16%, ציון נורדי 7.0. אין חלופה. פעולה: פריט תוספת לסל.
- **dining-room/table-runner** ✱
  - `table-runner-aliexpress-boho-macrame-table-runners-263532`: ₪69, מרווח 30%, ציון נורדי 3.0. אין חלופה. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
- **kids/bedding** ✱
  - `bedding-cj-cream-ruffle-rosebud-set`: ₪299, מרווח 26%, ציון נורדי —. אין חלופה. פעולה: לבקש מהספק את סט ה-1.2 מ' המתאים למיטת יחיד.
  - `bedding-cj-muslin-cotton-duvet-dune`: ₪179, מרווח 20%, ציון נורדי —. אין חלופה. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
- **kids/toy-cars** ✱
  - `toy-cars-cj-beech-peg-bus`: ₪129, מרווח 30%, ציון נורדי —. אין חלופה. פעולה: שלושה אוטובוסים זהים הם סט מוזר: לשקול סט של כלי רכב שונים מאותו ספק, או אוטובוס בודד כפריט תוספת; צריך תקן EN71.
- **master/bedding**
  - `bedding-aliexpress-boho-3d-tufted-cut-500672`: ₪349, מרווח 17%, ציון נורדי —. יש חלופה: `bedding-cj-washed-linen-natural-set`. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
  - `bedding-cj-plain-linen-flat-sheet-raw-jute-260x280`: ₪469, מרווח 32%, ציון נורדי —. יש חלופה: `bedding-cj-washed-linen-natural-set`. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
  - `bedding-cj-washed-cotton-khaki-set-220x240`: ₪349, מרווח 21%, ציון נורדי —. יש חלופה: `bedding-cj-washed-linen-natural-set`. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
- **master/bedside-sconces** ✱
  - `bedside-sconces-cj-linen-wave-flush`: ₪349, מרווח 1%, ציון נורדי —. אין חלופה. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
- **master/pendant** ✱
  - `pendant-cj-light-wood-slat-drum-43`: ₪299, מרווח 15%, ציון נורדי —. אין חלופה. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
- **master/pillowcases** ✱
  - `pillowcases-cj-linen-pair-coconut-button`: ₪129, מרווח 21%, ציון נורדי —. אין חלופה. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
  - `pillowcases-cj-pure-linen-envelope-pair-48x74`: ₪129, מרווח 21%, ציון נורדי —. אין חלופה. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
- **master/throw** ✱
  - `throw-cj-cotton-linen-light-gray-200x230`: ₪229, מרווח 13%, ציון נורדי —. אין חלופה. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
  - `throw-cj-cotton-waffle-ruffle-khaki-150x200`: ₪149, מרווח 7%, ציון נורדי —. אין חלופה. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.
- **work/framed-art** ✱
  - `framed-art-aliexpress-japanese-wabi-sabi-tree-176323`: ₪39, מרווח 11%, ציון נורדי —. אין חלופה. פעולה: לשמור; לשפר רווח במכירה בסל או בסט.

## loss: פעולה מוצעת

אף מוצר לא מומלץ להוצאה בגלל רווח (הנחיית המשתמש: עיצוב קודם). הפעולות משפרות רווח בלי להחליף את המוצר: סל, משלוח זול יותר, אותו מוצר מספק אחר או מלאי בישראל.

| מוצר | חדר | מחיר | תרומה | חלופה בעמדה | פעולה |
| --- | --- | --- | --- | --- | --- |
| `floor-lamp-cj-cream-arc-pleated-152` | חדר שינה | ₪349 | ₪-2304 | אין ✱ | המשלוח היחיד הוא DHL ‏$766: לא משתלם מהספק הזה: לחפש את אותו דגם אצל ספק עם משלוח רגיל, או מלאי בישראל. |
| `pendant-cj-wabi-pleated-fabric-lantern-50` | חדר שינה | ₪299 | ₪-1089 | אין ✱ | משלוח To Door ‏$340 (6 ק"ג): לא משתלם מהספק הזה: לחפש את אותו פנס אצל ספק עם משלוח רגיל, או מלאי בישראל. |
| `bedding-cj-cotton-linen-duvet-beige` | חדר שינה | ₪479 | ₪-417 | יש | עלות $128 ומשלוח $108 (5 ק"ג): לא משתלם מהספק הזה: לחפש את אותו סט אצל ספק עם משלוח רגיל. |
| `pool-cj-terracotta-amphora-floor-51` | מאגר | ₪479 | ₪-363 | אין ✱ | עלות $183: לחפש את אותה אמפורה אצל ספק זול יותר (יעד עלות ~$60). |
| `floor-lamp-cj-pleated-walnut-stem-158` | חדר שינה | ₪349 | ₪-317 | אין ✱ | משלוח Sensitive ‏$145: רק עם מלאי בישראל (מנורה נמכרת היטב, 58 מכירות). |
| `wall-sconce-cj-black-swing-arm-wood-shade` | ילדים | ₪119 | ₪-233 | אין ✱ | משלוח Sensitive ‏$86.8: לא משתלם מהספק הזה: לבקש קו Eub או לחפש את אותו דגם אצל ספק אחר. |
| `bath-mat-cj-solid-wood-slatted-61x45` | אמבטיה | ₪129 | ₪-215 | אין ✱ | משלוח Sensitive בלבד ($75) הורג את המוצר: לחפש ספק עם קו Eub או גרסה קלה וקטנה יותר. |
| `centerpiece-vase-cj-sandy-white-bead-band-25` | מטבח ופינת אוכל | ₪59 | ₪-169 | אין ✱ | משלוח $56 (משקל 4.15 ק"ג שגוי כנראה): לבקש מ-CJ לתקן משקל או ספק אחר. |
| `dining-chairs-furniture-express-maya` | מטבח ופינת אוכל | ₪399 | ₪-166 | אין ✱ | תלוי בתנאי השותפות: ב-₪399 הכיסא מגיע ל-40% רק אם העלות כולל משלוח היא עד ~₪165. |
| `dining-pendant-cj-black-ring-cloth-lantern-50` | מטבח ופינת אוכל | ₪229 | ₪-96 | אין ✱ | עלות $51.8: לבדוק את ה-40 ס"מ ($38.3) או ספק אחר. |
| `table-lamp-cj-pleated-shade-wood-column` | כניסה | ₪149 | ₪-86 | אין ✱ | משלוח Sensitive ‏$40: לבדוק קו זול או מלאי בישראל. |
| `ceiling-light-cj-opal-glass-drum-flush-32` | אמבטיה | ₪149 | ₪-74 | אין ✱ | משלוח $35 על גוף של $21: לחפש ספק עם משלוח זול או מלאי בישראל; IP44 עדיין לא אושר. |
| `framed-art-cj-line-scribble-white-mat-50` | כניסה | ₪129 | ₪-69 | אין ✱ | משלוח $35.6: לבדוק את ה-40x40 או מסגרת קלה. |
| `ceiling-lights-cj-silk-cocoon-flush-40` | מסדרון | ₪219 | ₪-68 | אין ✱ | לזוג ₪449; המשלוח (~$42) נאמד לפי הכרטיס ולא צוטט, לצטט לפני בחירה. |
| `tableware-set-cj-grey-sand-matte-plate` | מטבח ופינת אוכל | ₪19 | ₪-64 | אין ✱ | צלחת בודדת לא נמכרת לבד: סט 4–6 בלבד (משלוח $15.6 לצלחת). |
| `mug-set-cj-cream-matte-breakfast-cup` | מטבח ופינת אוכל | ₪39 | ₪-64 | אין ✱ | משלוח $8.4 לכל כוס: לחפש ספק עם כוסות קלות יותר או למכור רק בסל. |
| `candle-holders-aliexpress-cutelife-black-ceramic-candelabra` | מטבח ופינת אוכל | ₪39 | ₪-59 | אין ✱ | העלות ($24.6) גבוהה מאוד לפריט הזה; ספק אחר לאותו מראה. |
| `bench-pad-cj-tufted-long-cushion-khaki-120` | מטבח ופינת אוכל | ₪59 | ₪-58 | אין ✱ | משלוח $24.5 על פריט של $6: רק בסל, או ספק עם כרית שטוחה וקלה יותר. |
| `floor-vase-aliexpress-capiron-zen-ceramic` | מטבח ופינת אוכל | ₪49 | ₪-55 | אין ✱ | עלות $22 לאגרטל קטן: ספק אחר. |
| `pendant-cj-fabric-dome-ash-cap-25` | ילדים | ₪119 | ₪-55 | אין ✱ | משלוח $29.6 על מנורה של $14: רק עם מלאי בישראל או ספק עם משלוח זול. |
| `framed-art-cj-swinging-line-black-frame-mat-35x45` | מטבח ופינת אוכל | ₪129 | ₪-52 | אין ✱ | משלוח $24 על מסגרת 1.6 ק"ג: לבדוק משלוח בלי זכוכית/פרספקס או מלאי בישראל. |
| `framed-prints-cj-charcoal-line-black-frame-35x45` | ילדים | ₪129 | ₪-52 | יש | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `nightstand-tray-cj-travertine-look-rect-milktea` | חדר שינה | ₪59 | ₪-51 | אין ✱ | משלוח $20 על 1.3 ק"ג: למכור בסט הטרוורטין. |
| `framed-art-cj-taupe-block-black-line-30x40` | מטבח ופינת אוכל | ₪109 | ₪-51 | אין ✱ | משלוח $29 (2 ק"ג): לבדוק משקל אמיתי. |
| `centerpiece-vase-aliexpress-nordic-matte-ceramic-vase` | מטבח ופינת אוכל | ₪89 | ₪-50 | אין ✱ | עלות $26.8 גבוהה: לחפש את אותה צורה אצל ספק אחר. |
| `ceiling-lights-cj-pleated-fabric-saucer-flush-50` | מסדרון | ₪499 | ₪-48 | אין ✱ | עלות $36 + משלוח $30 ליחידה: לבדוק הנחת כמות או ספק שני; אולי מלאי בישראל. |
| `ceiling-light-cj-waxwood-dome-ash-40` | כניסה | ₪199 | ₪-47 | אין ✱ | משלוח $42: לבדוק ספק עם משלוח זול או את ה-25 ס"מ. |
| `mug-set-cj-oat-speckled-round-mug-wood-saucer` | מטבח ופינת אוכל | ₪19 | ₪-47 | אין ✱ | פריט תוספת; גם כסט של 3 (₪99) המשלוח גבוה מדי: לבקש ציטוט לשלושה יחד או ספל קל יותר. |
| `toothbrush-cup-cj-silver-travertine-cup` | אמבטיה | ₪79 | ₪-46 | אין ✱ | העלות ($19.7) גבוהה לכוס: למכור בסט עם הדיספנסר והמגש מאותו ספק. |
| `pool-cj-linen-look-tassel-curtain` | מאגר | ₪59 | ₪-41 | מאגר | לזוג ₪119; משלוח $16 לכנף. |
| `wall-sconce-cj-wavy-linen-flush-25` | כניסה | ₪149 | ₪-40 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `pool-cj-carbonized-wood-pedestal-candlestick` | מאגר | ₪69 | ₪-40 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `open-shelf-ceramics-cj-morandi-matte-bottle-set` | מטבח ופינת אוכל | ₪79 | ₪-39 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `bedding-cj-washed-polyester-set-milk-tea` | ילדים | ₪99 | ₪-38 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `tableware-set-cj-speckled-oat-stoneware-bowl-13` | מטבח ופינת אוכל | ₪29 | ₪-38 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `wall-sconce-cj-white-fabric-cube-15` | חדר עבודה | ₪99 | ₪-35 | אין ✱ | "≤36V" בשדה הספק: לאמת 220V/E27 לפני מכירה. |
| `centerpiece-vase-aliexpress-modern-minimalist-white-ceramic` | מטבח ופינת אוכל | ₪59 | ₪-34 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `pool-cj-travertine-organic-tray-24` | מאגר | ₪119 | ₪-32 | מאגר | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `table-lamp-cj-white-teardrop-fabric-cone-25x45` | כניסה | ₪99 | ₪-31 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `framed-art-aliexpress-retro-farmhouse-chicken-botanical-333603` | מטבח ופינת אוכל | ₪89 | ₪-30 | אין ✱ | עלות $27.3 גבוהה; לבדוק את המידה בלי מסגרת וספק אחר. |
| `paper-towel-holder-cj-beech-upright-31` | מטבח ופינת אוכל | ₪39 | ₪-30 | אין ✱ | אין ל-CJ מסלול לישראל (מחסן בחו"ל): לבקש מ-CJ מסלול או ספק אחר לאותו מוצר. |
| `shower-curtain-cj-linen-look-khaki-grommet` | אמבטיה | ₪39 | ₪-28 | אין ✱ | זול בלבד בסל; לבדוק משלוח לשני וילונות יחד. |
| `bedside-sconces-cj-linen-half-drum-black-trim` | חדר שינה | ₪349 | ₪-27 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `wall-sconce-cj-black-swan-arm-white-fabric-cone` | חדר עבודה | ₪79 | ₪-26 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `bowl-cj-glutinous-white-belly-bowl-21` | מטבח ופינת אוכל | ₪39 | ₪-25 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `bath-mat-cj-tufted-cotton-frame-beige-40x60` | אמבטיה | ₪39 | ₪-24 | אין ✱ | להציע גם את 50x80 ($8.96) או למכור בסט אמבטיה (שטיח + מגבות). |
| `table-lamp-cj-white-textured-ceramic-linen-drum` | כניסה | ₪199 | ₪-23 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `condiment-set-zendrop-wood-mills-black-white-21` | מטבח ופינת אוכל | ₪59 | ₪-22 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `reed-diffuser-cj-travertine-look-bamboo-lid-milktea` | אמבטיה | ₪39 | ₪-21 | אין ✱ | למכור כסט אמבטיה במראה טרוורטין (מפיץ + דיספנסר + כוס + מגש; וריאנט סט מלא $35) או להוסיף נוזל ריח מקומי. |
| `toothbrush-cup-cj-travertine-look-cup-milktea` | אמבטיה | ₪19 | ₪-21 | אין ✱ | פריט תוספת בלבד, בסט הטרוורטין. |
| `pool-cj-wabi-sabi-floor-vase-white` | מאגר | ₪349 | ₪-20 | אין ✱ | משלוח $60: לבדוק משלוח זול או מלאי בישראל. |
| `soap-dispenser-cj-travertine-look-lotion-milktea` | אמבטיה | ₪49 | ₪-19 | אין ✱ | למכור בסט הטרוורטין (מגש + דיספנסר + כוס + מפיץ). |
| `soap-dispenser-cj-matte-ceramic-cream-black-pump` | אמבטיה | ₪39 | ₪-19 | אין ✱ | פריט תוספת: למכור בסט אמבטיה (2–3 בקבוקים לנישה) כדי לחלק את המשלוח. |
| `vanity-sconces-cj-fluted-resin-updown-white` | אמבטיה | ₪229 | ₪-19 | אין ✱ | משלוח Sensitive ‏$23.6 ליחידה: לחפש קו Eub או ספק אחר לאותו דגם. |
| `picture-lights-cj-black-tube-rechargeable` | מסדרון | ₪59 | ₪-16 | אין ✱ | לסט של 3 ₪199; גוף פלסטיק, לבדוק איכות בתקריב. |
| `wall-sconce-cj-black-folding-arm-woodgrain-cone-18` | ילדים | ₪99 | ₪-15 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `tea-towel-zendrop-cotton-linen-washed-60x45` | מטבח ופינת אוכל | ₪19 | ₪-15 | אין ✱ | פריט תוספת לסל בלבד; גם כסט של 3 (₪59) המשלוח ליחידה ($3–7) גבוה מדי, לבדוק ספק עם משלוח מאוחד. |
| `vanity-sconces-cj-ip65-mini-updown-white` | אמבטיה | ₪49 | ₪-13 | אין ✱ | לזוג ₪129; מנורה טכנית, מתאימה בעיקר לחדר הרחצה. |
| `candle-holders-aliexpress-matte-black-iron-pillar-set2` | מטבח ופינת אוכל | ₪39 | ₪-13 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `condiment-set-cj-rubberwood-mill-pair-6in` | מטבח ופינת אוכל | ₪49 | ₪-12 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `canisters-zendrop-matte-ceramic-bamboo-lid-sml` | מטבח ופינת אוכל | ₪89 | ₪-12 | אין ✱ | המשלוח צוטט כנראה על הצנצנת הקטנה; לבדוק משלוח לסט (2.2 ק"ג). |
| `bath-towels-cj-cotton-waffle-white` | אמבטיה | ₪49 | ₪-10 | אין ✱ | למכור כסט (Set A של CJ: 2 מגבות + מגבת פנים, $11.74) ב-₪129, כך המשלוח מתחלק. |
| `pool-cj-cotton-linen-box-camel-40x30` | מאגר | ₪29 | ₪-9 | מאגר | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `wall-hooks-cj-raw-wood-cylinder-peg-set-of-4` | כניסה | ₪39 | ₪-9 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `cushions-cj-dusty-pink-corduroy-patchwork-45` | ילדים | ₪59 | ₪-9 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `wall-hooks-cj-light-wood-rail-5-brass-pegs-58` | כניסה | ₪89 | ₪-6 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `skateboard-cj-blank-maple-43` | ילדים | ₪79 | ₪-6 | אין ✱ | משלוח $17.6 על לוח של $1.9; גלגלים אדומים צריכים אישור לפני מכירה. |
| `pendant-cj-fluted-ceramic-wood-cap-short-lantern` | חדר עבודה | ₪149 | ₪-3 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `sill-vase-cj-cream-fluted-column-25` | חדר שינה | ₪49 | ₪-3 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |
| `centerpiece-vase-aliexpress-nordic-morandi-matte-ceramic` | מטבח ופינת אוכל | ₪199 | ₪-2 | אין ✱ | מכירה בסל או בסט כדי לחלק את המשלוח. |

## הערות

- **משלוח מוערך** (לא היה בשדה המשלוח): `candle-holders-aliexpress-cutelife-black-ceramic-candelabra`, `candle-holders-aliexpress-matte-black-iron-pillar-set2`, `centerpiece-vase-aliexpress-modern-minimalist-white-ceramic`, `centerpiece-vase-aliexpress-nordic-matte-ceramic-vase`, `centerpiece-vase-aliexpress-nordic-morandi-matte-ceramic`, `dining-chairs-furniture-express-maya`, `floor-vase-aliexpress-capiron-zen-ceramic`, `paper-towel-holder-cj-beech-upright-31`. הבסיס לכל אחד ב-`ship_basis`.
- `paper-towel-holder-cj-beech-upright-31`: ל-CJ אין מסלול לישראל; תומחר ומסומן loss.
- `skateboard-cj-blank-maple-43`: לא נמצא מקביל ישראלי (Terminal X, IKEA, חיפוש רשת); הערך הוערך לפי קישוט ילדים בשוק ומחירים בחו"ל.
- מחירי Zara Home, H&M וחלק מחנויות העיצוב לקוחים מתקציר חיפוש ולא נפתחו ישירות (מסומן בשדה note של ההשוואה).
- `il_value` של סט או זוג הוא לכל הסט; השוואות שמסומנות "(ליחידה)" הן מחיר של פריט בודד.
