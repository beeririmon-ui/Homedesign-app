# אין מוצר מפסיד: ביקורת ותיקון מחירים (2026-10-20)

הכלל (ה.13, תיקון 2026-10-20): "בא נוודא שאין דבר כזה מוצר מפסיד בשום צורה! יכול להיות יקר ללקוח אבל אין מפסיד!". לכל מוצר שהסטודיו או האתר יכולים למכור חושבה התרומה בתרחיש הגרוע ביותר, ומחיר שמפסיד הועלה למחיר הנמוך שלא מפסיד, גם מעל ההשוואה הישראלית הגבוהה. שום מחיר לא ירד, ומחיר שהמשתמש קבע בסטודיו לא שונה.

הסקריפט: `python3 -I scripts/economics/no_loss.py` (ביקורת), `--apply` (תיקון), `--report` (הדוח הזה), `--check` (יוצא ב-1 אם נשאר מוצר מפסיד).

## בקצרה

- נבדקו 464 מוצרים: כל שורה ב-products.json, כל כרטיס שסקריפט הכיסוי סופר, וכל כרטיס שיש לו מחיר בסטודיו.
- הועלו 162 מחירים (products.json 143, leads 13, card 6). מ-₪19–₪1,299 ל-₪39–₪4,099; פי 1.02 עד פי 9.71 (חציון פי 1.94).
- 67 מוצרים יקרים מהשוק עכשיו (מעל ההשוואה הגבוהה), היחס הגבוה פי 5.41.
- 38 מהמחירים הועלו רק בגלל המשלוח המהיר: במשלוח חסכוני בלבד המחיר הקודם לא הפסיד.
- מוצרים שעדיין מפסידים (לא של המשתמש): 0. מחיר של המשתמש שמפסיד: 1. אי אפשר לחשב: 10. כרטיסים שנספרים בכיסוי בלי מחיר בכלל: 132.

## הנוסחה, ואיפה המחיר חי

- תרומה = נטו − נחיתה − (2% מהמחיר + ₪1.2) − 8% מהנטו; נטו = מחיר ÷ 1.18; נחיתה = (עלות ליחידה × כמות + משלוח לכמות) × 3.3. לפני CAC. דמי המשלוח שהלקוח משלם (₪29, מהיר ₪59) לא נספרים, כמו בסטודיו.
- סיומת המחיר: שקל שלם שנגמר ב-9 (19, 29 … 149, 159), כמו המחירים בקובץ התמחור ו-charmRoundUpIls של האתר.

| מקור המחיר | לפני | אחרי | מי קורא אותו |
| --- | --- | --- | --- |
| products.json | 180 | 181 | data/economics/products.json products.<id>.retail_ils: הסטודיו והאתר |
| owner | 1 | 1 | עריכה בסטודיו (db product_edits), מסונכרנת ל-products.json עם retail_src studio |
| card | 41 | 53 | כרטיס המוצר price.suggested_retail או price.retail_ils: הסטודיו בלבד |
| leads | 102 | 89 | price_ils ברשומת הסבב האחרון (data/leads/final-2026-10-13/results/*.json): הסטודיו בלבד, דרך room_boards.Context; מחיר חדש נרשם בכרטיס (price.retail_ils), שהסטודיו קורא לפני הרשומה, והרשומה לא משתנה |
| none | 140 | 140 | אין מחיר: כרטיס שנספר בכיסוי או שאין לו משלוח |

- data/economics/pricing/*-2026-10-11.json: המקור שממנו נבנה products.json; אף אחד לא קורא אותו היום (היסטוריה)

### הסטודיו מול האתר

| נושא | הסטודיו | האתר | זהה |
| --- | --- | --- | --- |
| נוסחת התרומה | studio/src/index.html econCalc: נטו = P/1.18; עמלה = 2%·P + ₪1.2; שמורה = 8% מהנטו; אריזה 0; תרומה = נטו − נחיתה − עמלה − שמורה | site/shared/src/pricing.ts unitEconomics: אותה נוסחה, באגורות (עיגול בכל שלב, הפרש של אגורות) | כן |
| הגדרות | data/economics/settings.json + ברירות המחדל של ECON_META (שער 3.3, מע"מ 18%, 2% + ₪1.2, החזרות 8%, יעד 40%) | site/shared/src/schema/economics.ts DEFAULT_SETTINGS + resolveSettings: אותם ערכים | כן |
| משלוח לכמות | יחידה + (q − 1) × max(0, יחידה − $3.72) (הערכה); הצעה שנמדדה לכל המכירה (quoted_qty = q) נלקחת כמו שהיא | cogs = (עלות + משלוח) × q: ליניארי, בלי חיסכון החבילה; הצעה לכל המכירה (משלוח הליקוט, sale_shipping) נכפלת ב-q | לא |
| מקור המשלוח | ידני (products.json) ← freight-cj / freight-zendrop / freight-aliexpress ← המק"ט בכרטיס ← רשומת הסבב האחרון | ידני ← freight-cj.json בלבד ← ברירת מחדל $17: למוצרי AliExpress ו-Zendrop בלי משלוח ידני האתר מחשב $17 | לא |
| מקור המחיר | עריכה בסטודיו (db) ← products.json retail_ils ← מחיר בכרטיס (price.retail_ils / suggested_retail) ← price_ils ברשומת הסבב | products.json retail_ils בלבד; בלי שורה: מחיר מומלץ ב-40% (זמני), ובבנייה קפדנית לא מוצג. מחירי הכרטיס והסבב לא מגיעים לאתר | לא |
| אפשרויות הספק (וריאנטים) | רק המק"ט שבחדר | options.ts skuRetail: P + (המומלץ של האפשרות − המומלץ של המק"ט שבחדר). אפשרות זולה יורדת במחיר פי ~2.4 מהירידה בעלות, ומפסידה ~0.8 מהפרש העלות; בבנייה קפדנית אפשרות בלי sku_retail_ils לא נמכרת | לא |
| יחידה אחת מסט (P1) | לא מוצג | packs.ts unitPriceEstimateIls: ceil(P/N × 1.15) מעוגל מטה ל-9, או unit_retail_ils | לא |
| דמי משלוח ללקוח | לא נספרים כהכנסה | ₪29 (חינם מ-₪299), מהיר ₪59; לא נספרים בתרומה | כן |

מסקנה: נוסחת התרומה וההגדרות זהות; הקלטים שונים: משלוח לכמות, מקור המשלוח, מקור המחיר, האפשרויות והיחידה הבודדת (ראו compare). לא נבחרה אחת מהן בשקט: הביקורת לוקחת את הגרוע מבין השתיים בכל נקודה (משלוח לכמות כחבילה לכל יחידה, מחיר האפשרות והיחידה הבודדת כמו באתר, משלוח מכל המקורות של הסטודיו).

## התרחישים

- המכירה (sell_qty) במשלוח חסכוני ובמשלוח מהיר (עד 20 יום) כשהסטודיו מציע אותו
- יחידה אחת מסט (P1), במחיר היחידה של האתר
- כל אפשרות ספק במלאי, במחיר שהאתר נותן לה, ויחידה אחת ממנה
- כמה מכירות בסל: לא גרוע יותר (משלוח לכמה יחידות ≤ סכום החלקים)
- משלוח: ההצעה הגרועה מכל המקורות לכל שיטה; משלוח לכמה יחידות שהוא הערכה = חבילה לכל יחידה; בלי הצעה בכלל = ההערכה הגבוהה, מסומן

## מה הועלה

"חסכוני בלבד" = המחיר שהיה מספיק אילו המשלוח המהיר לא היה מוצע במוצר (לא הוחל; להחלטת המשתמש).

| מוצר | מקור | היה | עכשיו | חסכוני בלבד | התרחיש הגרוע | השוואה גבוהה | פי מההשוואה |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `floor-lamp-cj-cream-arc-pleated-152` | products.json | ₪349 | ₪3,389 | ₪3,389 | המכירה (1 יח'), משלוח חסכוני | ₪651 | 5.21 |
| `basket-cj-seagrass-belly` | products.json | ₪89 | ₪749 | ₪119 | אפשרות color=original, other=a, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪190 | 3.94 |
| `planter-cj-seagrass-belly` | products.json | ₪89 | ₪749 | ₪119 | אפשרות color=original, other=a, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪190 | 3.94 |
| `tableware-set-cj-grey-sand-matte-plate` | products.json | ₪19 | ₪159 | ₪109 | אפשרות size=10inch, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪50 | 3.18 |
| `centerpiece-vase-cj-sandy-white-bead-band-25` | products.json | ₪59 | ₪449 | ₪299 | אפשרות other=2345-white, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪295 | 1.52 |
| `pendant-cj-tiered-fabric-drum` | products.json | ₪329 | ₪2,489 | ₪429 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪460 | 5.41 |
| `dining-pendant-cj-black-ring-cloth-lantern-50` | products.json | ₪229 | ₪1,559 | ₪409 | אפשרות size=40, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪420 | 3.71 |
| `mug-set-cj-oat-speckled-round-mug-wood-saucer` | products.json | ₪19 | ₪119 | ₪89 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪60 | 1.98 |
| `mug-set-cj-cream-matte-breakfast-cup` | products.json | ₪39 | ₪239 | ₪149 | המכירה (3 יח'), משלוח מהיר (עד 20 יום) | ₪90 | 2.66 |
| `planter-cj-cement-ribbed-belly` | products.json | ₪229 | ₪1,389 | ₪289 | אפשרות color=grey, size=small, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪360 | 3.86 |
| `pendant-cj-wabi-pleated-fabric-lantern-50` | products.json | ₪299 | ₪1,739 | ₪1,739 | המכירה (1 יח'), משלוח חסכוני | ₪420 | 4.14 |
| `table-lamp-cj-white-textured-ceramic-linen-drum` | products.json | ₪199 | ₪1,129 | ₪239 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪295 | 3.83 |
| `ceiling-light-cj-waxwood-dome-ash-40` | products.json | ₪199 | ₪1,099 | ₪279 | אפשרות color=white-light, size=small, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪420 | 2.62 |
| `tableware-set-cj-speckled-oat-stoneware-bowl-13` | products.json | ₪29 | ₪159 | ₪99 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪80 | 1.99 |
| `open-shelf-ceramics-cj-morandi-matte-bottle-set` | products.json | ₪79 | ₪429 | ₪149 | המכירה (2 יח'), משלוח מהיר (עד 20 יום) | ₪270 | 1.59 |
| `wall-sconce-cj-white-fabric-cube-15` | products.json | ₪99 | ₪529 | ₪319 | אפשרות color=white, style=warm-white, size=12x12, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪299 | 1.77 |
| `ceiling-lights-cj-pleated-fabric-saucer-flush-50` | products.json | ₪499 | ₪2,339 | ₪579 | המכירה (2 יח'), משלוח מהיר (עד 20 יום) | ₪900 | 2.6 |
| `toothbrush-cup-cj-travertine-look-cup-milktea` | products.json | ₪19 | ₪89 | ₪59 | אפשרות color=milk-tea-color, other=soap-dish, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪114 | 0.78 |
| `pool-cj-terracotta-amphora-floor-51` | products.json | ₪479 | ₪2,129 | ₪959 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪1,055 | 2.02 |
| `bath-mat-cj-tufted-cotton-frame-beige-40x60` | products.json | ₪39 | ₪169 | ₪79 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪165 | 1.02 |
| `ceiling-lights-cj-silk-cocoon-flush-40` | products.json | ₪219 | ₪899 | ₪309 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪420 | 2.14 |
| `bowl-cj-glutinous-white-belly-bowl-21` | products.json | ₪39 | ₪159 | ₪79 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪120 | 1.32 |
| `pendant-cj-fabric-dome-ash-cap-25` | products.json | ₪119 | ₪479 | ₪199 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪195 | 2.46 |
| `ceiling-light-cj-opal-glass-drum-flush-32` | products.json | ₪149 | ₪599 | ₪249 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪300 | 2.0 |
| `wall-sconce-cj-black-swan-arm-white-fabric-cone` | products.json | ₪79 | ₪309 | ₪129 | אפשרות color=black, style=single-head, other=no-bulb-included, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪150 | 2.06 |
| `wall-sconce-cj-black-swing-arm-wood-shade` | products.json | ₪119 | ₪449 | ₪429 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪195 | 2.3 |
| `pool-cj-wood-sunburst-mirror-43` | products.json | ₪119 | ₪449 | ₪119 | אפשרות other=xh-22-235-diameter-30cm, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪220 | 2.04 |
| `bench-pad-cj-tufted-long-cushion-khaki-120` | products.json | ₪59 | ₪219 | ₪149 | אפשרות color=black, size=130x50x8, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪135 | 1.62 |
| `vase-cj-white-plum-hand-thrown` | products.json | ₪229 | ₪849 | ₪239 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪479 | 1.77 |
| `wall-sconce-cj-black-swing-arm-fabric` | products.json | ₪149 | ₪539 | ₪519 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪293 | 1.84 |
| `pendant-cj-light-wood-slat-drum-43` | products.json | ₪299 | ₪1,069 | ₪299 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪895 | 1.19 |
| `candle-holders-aliexpress-cutelife-black-ceramic-candelabra` | products.json | ₪39 | ₪139 | ₪139 | אפשרות color=white, set=1pc, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪125 | 1.11 |
| `nightstand-tray-cj-travertine-look-rect-milktea` | products.json | ₪59 | ₪209 | ₪149 | אפשרות color=milk-tea-color, other=soap-dish, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪347 | 0.6 |
| `bath-mat-cj-solid-wood-slatted-61x45` | products.json | ₪129 | ₪439 | ₪419 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪399 | 1.1 |
| `shower-curtain-cj-linen-look-khaki-grommet` | products.json | ₪39 | ₪129 | ₪99 | אפשרות color=linen-gray-large-hole, size=100x180-single-curtain, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪129 | 1.0 |
| `pool-cj-linen-look-tassel-curtain` | products.json | ₪59 | ₪189 | ₪139 | אפשרות style=width-150-height-160cm, other=diamond-plaid-stitching, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪198 | 0.95 |
| `rug-cj-braided-wool-natural` | products.json | ₪1,299 | ₪4,099 | ₪4,099 | אפשרות size=150x200, other=around-tassel-style, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪2,700 | 1.52 |
| `vase-cj-matte-moon-jar-white` | products.json | ₪149 | ₪469 | ₪179 | אפשרות style=styled, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪269 | 1.74 |
| `pool-cj-cotton-linen-box-camel-40x30` | products.json | ₪29 | ₪89 | ₪49 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪70 | 1.27 |
| `pendant-cj-pleated-pumpkin-lantern-40` | products.json | ₪299 | ₪909 | ₪469 | אפשרות size=28, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪450 | 2.02 |
| `magazine-holder-cj-gunmetal-leather-strap` | products.json | ₪149 | ₪439 | ₪269 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪229 | 1.92 |
| `wall-sconce-cj-black-folding-arm-woodgrain-cone-18` | products.json | ₪99 | ₪289 | ₪139 | אפשרות color=the-pattern-of-walnut, other=white-light, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪195 | 1.48 |
| `bowl-cj-reactive-white-rimmed-plate-21` | products.json | ₪59 | ₪169 | ₪99 | אפשרות set=1pc, other=7.7-inches, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪139 | 1.22 |
| `bedside-sconces-cj-linen-wave-flush` | products.json | ₪349 | ₪989 | ₪369 | המכירה (2 יח'), משלוח מהיר (עד 20 יום) | ₪598 | 1.65 |
| `vase-cj-charcoal-carved` | products.json | ₪199 | ₪559 | ₪219 | אפשרות style=style-a, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪479 | 1.17 |
| `reed-diffuser-cj-travertine-look-bamboo-lid-milktea` | products.json | ₪39 | ₪109 | ₪69 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪144 | 0.76 |
| `soap-dispenser-cj-matte-ceramic-cream-black-pump` | products.json | ₪39 | ₪109 | ₪69 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪120 | 0.91 |
| `pool-cj-carbonized-wood-pedestal-candlestick` | products.json | ₪69 | ₪189 | ₪129 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪185 | 1.02 |
| `pendant-cj-fluted-ceramic-wood-cap-short-lantern` | products.json | ₪149 | ₪399 | ₪159 | אפשרות style=short-lantern-style, other=without-customs-source, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪315 | 1.27 |
| `soap-dispenser-cj-travertine-look-lotion-milktea` | products.json | ₪49 | ₪129 | ₪89 | אפשרות color=milk-tea-color, other=soap-dish, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪180 | 0.72 |
| `floor-vase-aliexpress-capiron-zen-ceramic` | products.json | ₪49 | ₪129 | ₪129 | המכירה (1 יח'), משלוח חסכוני | ₪295 | 0.44 |
| `sill-vase-cj-cream-fluted-column-25` | products.json | ₪49 | ₪129 | ₪59 | אפשרות other=evening-snow-arrives, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪295 | 0.44 |
| `framed-art-cj-line-scribble-white-mat-50` | products.json | ₪129 | ₪339 | ₪239 | אפשרות style=a, size=30x30, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪225 | 1.51 |
| `framed-art-aliexpress-retro-farmhouse-chicken-botanical-333603` | products.json | ₪89 | ₪229 | ₪229 | אפשרות size=21x30-black-framed, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪200 | 1.15 |
| `vase-cj-french-matte-white-35` | products.json | ₪229 | ₪589 | ₪319 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪589 | 1.0 |
| `basket-cj-jute-rope-cylinder` | products.json | ₪79 | ₪199 | ₪119 | אפשרות other=small, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪179 | 1.11 |
| `framed-art-cj-taupe-block-black-line-30x40` | products.json | ₪109 | ₪269 | ₪179 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪200 | 1.34 |
| `floor-lamp-cj-pleated-walnut-stem-158` | products.json | ₪349 | ₪849 | ₪829 | אפשרות other=3-colortable-lamp, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪651 | 1.3 |
| `bath-towels-cj-cotton-waffle-white` | products.json | ₪49 | ₪119 | ₪89 | אפשרות color=white, other=35x35cm, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪199 | 0.6 |
| `pouf-cj-cotton-knit-ball-cover` | products.json | ₪99 | ₪239 | ₪179 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪450 | 0.53 |
| `sofa-cover-cj-bubble-stretch-slipcover` | products.json | ₪149 | ₪359 | ₪279 | אפשרות color=cream-white, other=single, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪600 | 0.6 |
| `toothbrush-cup-cj-silver-travertine-cup` | products.json | ₪79 | ₪189 | ₪149 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪347 | 0.54 |
| `bedding-cj-cotton-linen-duvet-beige` | products.json | ₪479 | ₪1,139 | ₪1,139 | אפשרות size=150x200, other=white, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪1,080 | 1.05 |
| `kitchen-sconce-aliexpress-rustic-wooden-wall-sconce-632957` | leads | ₪229 | ₪539 | ₪539 | המכירה (4 יח'), משלוח חסכוני | ₪1,080 | 0.5 |
| `bedding-cj-washed-polyester-set-milk-tea` | products.json | ₪99 | ₪229 | ₪159 | אפשרות color=gemstone-green, size=200x230-quilt-cover, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪210 | 1.09 |
| `wall-hooks-cj-raw-wood-cylinder-peg-set-of-4` | products.json | ₪39 | ₪89 | ₪59 | אפשרות color=black-short, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪125 | 0.71 |
| `centerpiece-vase-aliexpress-nordic-matte-ceramic-vase` | products.json | ₪89 | ₪199 | ₪199 | אפשרות size=s, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪295 | 0.67 |
| `pool-cj-wabi-sabi-floor-vase-white` | products.json | ₪349 | ₪779 | ₪379 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪835 | 0.93 |
| `vanity-sconces-cj-ip65-mini-updown-white` | products.json | ₪49 | ₪109 | ₪69 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪220 | 0.5 |
| `condiment-set-cj-rubberwood-mill-pair-6in` | products.json | ₪49 | ₪109 | ₪69 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪130 | 0.84 |
| `accent-sconces-aliexpress-indoor-stone-wall-lamp` | products.json | ₪299 | ₪659 | ₪659 | המכירה (2 יח'), משלוח חסכוני | ₪520 | 1.27 |
| `bowl-cj-speckled-ivory-wide-bowl-21` | products.json | ₪79 | ₪169 | ₪79 | אפשרות other=small-white, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪199 | 0.85 |
| `vase-cj-faceted-cream` | products.json | ₪199 | ₪419 | ₪259 | אפשרות size=small, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪479 | 0.87 |
| `framed-art-cj-swinging-line-black-frame-mat-35x45` | products.json | ₪129 | ₪269 | ₪199 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪225 | 1.2 |
| `framed-prints-cj-charcoal-line-black-frame-35x45` | products.json | ₪129 | ₪269 | ₪199 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪225 | 1.2 |
| `wall-sconce-cj-wavy-linen-flush-25` | products.json | ₪149 | ₪309 | ₪209 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪299 | 1.03 |
| `tea-towel-zendrop-cotton-linen-washed-60x45` | products.json | ₪19 | ₪39 | ₪39 | המכירה (1 יח'), משלוח חסכוני | ₪49 | 0.8 |
| `centerpiece-vase-aliexpress-modern-minimalist-white-ceramic` | products.json | ₪59 | ₪119 | ₪119 | אפשרות size=small, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪295 | 0.4 |
| `skateboard-cj-blank-maple-43` | products.json | ₪79 | ₪159 | ₪89 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪149 | 1.07 |
| `basket-cj-cotton-rope-white` | products.json | ₪89 | ₪179 | ₪129 | אפשרות color=white, other=s, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪190 | 0.94 |
| `table-lamp-cj-pleated-shade-wood-column` | products.json | ₪149 | ₪289 | ₪269 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪295 | 0.98 |
| `pool-cj-travertine-organic-tray-24` | products.json | ₪119 | ₪229 | ₪169 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪347 | 0.66 |
| `vase-cj-coarse-sand-white-tall` | products.json | ₪229 | ₪439 | ₪229 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪479 | 0.92 |
| `magazine-holder-cj-felt-log-basket` | products.json | ₪79 | ₪149 | ₪79 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪130 | 1.15 |
| `sofa-cover-cj-polar-fleece-jacquard-slipcover` | products.json | ₪149 | ₪279 | ₪219 | אפשרות color=dark-gray, other=pillowcase, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪600 | 0.47 |
| `magazine-holder-cj-arch-iron-cane` | products.json | ₪129 | ₪239 | ₪179 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪229 | 1.04 |
| `picture-lights-cj-black-tube-rechargeable` | products.json | ₪59 | ₪109 | ₪89 | אפשרות other=touch-switch, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪125 | 0.87 |
| `vase-cj-white-textured-jar` | products.json | ₪149 | ₪269 | ₪179 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪269 | 1.0 |
| `framed-art-aliexpress-japanese-wabi-sabi-tree-176323` | products.json | ₪39 | ₪69 | ₪69 | אפשרות size=30x40, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪95 | 0.73 |
| `bedside-sconces-cj-linen-half-drum-black-trim` | products.json | ₪349 | ₪609 | ₪409 | המכירה (2 יח'), משלוח מהיר (עד 20 יום) | ₪598 | 1.02 |
| `framed-art-cj-morandi-triptych-sage` | products.json | ₪379 | ₪659 | ₪659 | אפשרות style=a, size=40x60, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪980 | 0.67 |
| `sofa-cover-cj-waffle-jacquard-stretch-slipcover` | products.json | ₪149 | ₪259 | ₪189 | אפשרות style=s-single, other=grass-green, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪600 | 0.43 |
| `table-lamp-cj-white-teardrop-fabric-cone-25x45` | products.json | ₪99 | ₪169 | ₪149 | אפשרות size=16x34-black-small, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪190 | 0.89 |
| `curtains-aliexpress-cotton-linen-texture-translucent-091154` | products.json | ₪299 | ₪509 | ₪509 | אפשרות set=1pc, width=100, length=250, style=pull_pleated, color=tulle, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪489 | 1.04 |
| `vase-cj-textured-white-stoneware` | products.json | ₪229 | ₪389 | ₪229 | אפשרות size=small, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪479 | 0.81 |
| `cushions-cj-boucle-teddy` | products.json | ₪59 | ₪99 | ₪59 | אפשרות color=white, size=30x50, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪239 | 0.41 |
| `cushions-cj-linen-look-ivory` | products.json | ₪59 | ₪99 | ₪59 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪289 | 0.34 |
| `magazine-holder-cj-felt-snap-bucket` | products.json | ₪59 | ₪99 | ₪69 | אפשרות color=black-without-lining, size=30x42-medium, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪130 | 0.76 |
| `condiment-set-zendrop-wood-mills-black-white-21` | products.json | ₪59 | ₪99 | ₪99 | אפשרות set=black, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪140 | 0.71 |
| `cushions-cj-dusty-pink-corduroy-patchwork-45` | products.json | ₪59 | ₪99 | ₪79 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪199 | 0.5 |
| `cushions-cj-bubble-chenille-bean-green` | products.json | ₪49 | ₪79 | ₪49 | אפשרות color=beige, size=40x40, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪199 | 0.4 |
| `wall-sconce-cj-travertine-dome-15-pull` | products.json | ₪299 | ₪469 | ₪449 | אפשרות style=15cm-without-pull-switch, other=light-source-not-included, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪520 | 0.9 |
| `toy-cars-cj-beech-peg-bus` | products.json | ₪129 | ₪199 | ₪129 | המכירה (3 יח'), משלוח מהיר (עד 20 יום) | ₪507 | 0.39 |
| `candle-holders-aliexpress-matte-black-iron-pillar-set2` | products.json | ₪39 | ₪59 | ₪59 | המכירה (1 יח'), משלוח חסכוני | ₪89 | 0.66 |
| `candle-holders-cj-travertine-pedestal` | products.json | ₪199 | ₪299 | ₪209 | המכירה (2 יח'), משלוח מהיר (עד 20 יום) | ₪300 | 1.0 |
| `throw-cj-cotton-waffle-ruffle-khaki-150x200` | products.json | ₪149 | ₪219 | ₪169 | אפשרות color=grey, size=100x150, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪399 | 0.55 |
| `curtains-aliexpress-cotton-linen-texture-translucent` | products.json | ₪299 | ₪439 | ₪439 | אפשרות set=1pc, width=100, length=200, style=rod_pocket, color=yarn, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪489 | 0.9 |
| `bowl-aliexpress-kiln-corrugated-raw-rim-bowl-23` | leads | ₪119 | ₪169 | ₪169 | אפשרות color=brown-kiln-spoon, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪139 | 1.22 |
| `shelf-boxes-cj-two-tone-fabric-bin-27x20x12-pair` | card | ₪63 | ₪89 | ₪89 | יחידה אחת, אפשרות color=grey, size=l, משלוח חסכוני | ₪70 | 1.27 |
| `cushions-cj-corduroy-patchwork` | products.json | ₪49 | ₪69 | ₪49 | אפשרות color=light-blue, size=45x45, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪199 | 0.35 |
| `cushions-cj-knitted-chenille-bean-green` | products.json | ₪49 | ₪69 | ₪49 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪199 | 0.35 |
| `cushions-cj-linen-look-charcoal` | products.json | ₪49 | ₪69 | ₪49 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪199 | 0.35 |
| `cushions-cj-sandstone-chenille-flange` | products.json | ₪49 | ₪69 | ₪49 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪199 | 0.35 |
| `cushions-cj-washed-cotton-frayed` | products.json | ₪49 | ₪69 | ₪49 | אפשרות size=30x50, other=white, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪199 | 0.35 |
| `cushions-cj-wide-stripe-corduroy-light-green` | products.json | ₪49 | ₪69 | ₪49 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪199 | 0.35 |
| `cushions-cj-wide-wale-corduroy` | products.json | ₪49 | ₪69 | ₪49 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪199 | 0.35 |
| `vanity-sconces-cj-fluted-resin-updown-white` | products.json | ₪229 | ₪319 | ₪279 | אפשרות color=white, other=tricolor-light-source, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪440 | 0.72 |
| `sofa-cover-cj-cotton-muslin-fringe` | products.json | ₪129 | ₪179 | ₪129 | אפשרות size=130x170, other=white, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪399 | 0.45 |
| `cushions-aliexpress-textured-boucle-throw-pillow` | products.json | ₪59 | ₪79 | ₪79 | אפשרות size=30x50, color=beige, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪239 | 0.33 |
| `wall-decor-zendrop-macrame-diamond-dowel-small` | products.json | ₪59 | ₪79 | ₪79 | המכירה (1 יח'), משלוח חסכוני | ₪249 | 0.32 |
| `basket-cj-seagrass-belly-xl` | products.json | ₪89 | ₪119 | ₪89 | אפשרות color=wood-color, other=s, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪190 | 0.63 |
| `wall-hooks-cj-light-wood-rail-5-brass-pegs-58` | products.json | ₪89 | ₪119 | ₪119 | אפשרות other=blackwalnut-2hooks, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪175 | 0.68 |
| `sofa-cover-cj-knit-thick-slipcover` | products.json | ₪149 | ₪199 | ₪149 | אפשרות color=pine-and-cypress-green, other=90-to-140cm, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪600 | 0.33 |
| `curtains-cj-japanese-linen-half-shade` | products.json | ₪229 | ₪299 | ₪229 | אפשרות color=light-beige, size=100x200-4hook, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪489 | 0.61 |
| `sofa-cover-cj-washed-hemp-throw` | products.json | ₪229 | ₪299 | ₪259 | אפשרות size=100x150, other=mustard-yellow, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪479 | 0.62 |
| `throw-cj-cotton-linen-light-gray-200x230` | products.json | ₪229 | ₪299 | ₪229 | אפשרות color=light-gray, size=150x200, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪479 | 0.62 |
| `pool-cj-woven-cotton-runner-fringe` | products.json | ₪69 | ₪89 | ₪69 | אפשרות size=33x140-170g, other=1-waffle, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪150 | 0.59 |
| `vanity-vase-aliexpress-sand-oat-bud-vase-g-series` | leads | ₪69 | ₪89 | ₪89 | אפשרות color=b1a, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪79 | 1.13 |
| `floor-lamp-cj-black-drum-linen` | products.json | ₪229 | ₪289 | ₪229 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪450 | 0.64 |
| `shelf-boxes-cj-felt-storage-bin-30x24-pair` | card | ₪63 | ₪79 | ₪79 | יחידה אחת, אפשרות color=dark-grey, size=l, משלוח חסכוני | ₪70 | 1.13 |
| `vanity-sconces-cj-flat-halo-disc-white` | products.json | ₪79 | ₪99 | ₪79 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪220 | 0.45 |
| `pendant-cj-silk-pumpkin-lantern` | products.json | ₪299 | ₪369 | ₪299 | אפשרות size=30, other=warm-light, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪450 | 0.82 |
| `pillowcases-cj-pure-linen-envelope-pair-48x74` | products.json | ₪129 | ₪159 | ₪129 | אפשרות other=one-rain-dew-hemp, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪299 | 0.53 |
| `canisters-zendrop-matte-ceramic-bamboo-lid-sml` | products.json | ₪89 | ₪109 | ₪109 | המכירה (1 יח'), משלוח חסכוני | ₪180 | 0.61 |
| `open-shelf-ceramics-cj-patina-clay-pitcher-and-jar` | products.json | ₪229 | ₪279 | ₪249 | אפשרות other=sy-c03d137, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪240 | 1.16 |
| `cushions-cj-chenille-wide-wale-green` | products.json | ₪49 | ₪59 | ₪49 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪199 | 0.3 |
| `floor-lamp-aliexpress-pleated-walnut-37x158-062736` | leads | ₪949 | ₪1,129 | ₪1,129 | אפשרות size=b-d39.5cm-h51cm, other=warm-light, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪1,395 | 0.81 |
| `floor-lamp-aliexpress-pleated-walnut-37x158-062736-master` | leads | ₪949 | ₪1,129 | ₪1,129 | אפשרות size=b-d39.5cm-h51cm, other=warm-light, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪1,395 | 0.81 |
| `sofa-cover-cj-linen-feel-chenille-slipcover` | products.json | ₪179 | ₪209 | ₪179 | אפשרות color=beige, style=single-seat, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪600 | 0.35 |
| `wall-sconce-cj-travertine-disc-25` | products.json | ₪379 | ₪429 | ₪379 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪600 | 0.71 |
| `table-runner-cj-linen-look-sage-fringe` | products.json | ₪79 | ₪89 | ₪79 | אפשרות color=1-beige, size=33x153, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪215 | 0.41 |
| `toy-cars-aliexpress-wooden-toys-beech-wood-138166` | leads | ₪159 | ₪179 | ₪179 | המכירה (3 יח'), משלוח חסכוני | ₪199 | 0.9 |
| `paper-towel-holder-aliexpress-slotted-wood-round-base-31` | card | ₪89 | ₪99 | ₪99 | אפשרות style=style-1, משלוח חסכוני (מחיר האפשרות לפי האתר) | — | — |
| `bedding-cj-muslin-cotton-duvet-dune` | products.json | ₪179 | ₪199 | ₪179 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪266 | 0.75 |
| `bench-pad-aliexpress-linen-look-box-cushion-130x35x5` | leads | ₪269 | ₪299 | ₪299 | אפשרות color=color-10-rice-gray, size=35x35x5, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪290 | 1.03 |
| `bench-pad-aliexpress-double-piping-cushion-130x35x5` | leads | ₪289 | ₪319 | ₪319 | אפשרות color=sg-6-light-gray, size=60x30x5, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪290 | 1.1 |
| `nightstand-tray-aliexpress-acacia-rect-tray-30x20` | card | ₪99 | ₪109 | ₪109 | אפשרות size=20, משלוח חסכוני (מחיר האפשרות לפי האתר) | — | — |
| `table-runner-aliexpress-open-weave-linen-runner` | leads | ₪99 | ₪109 | ₪109 | אפשרות color=tea-green, size=20x60, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪129.90 | 0.84 |
| `centerpiece-vase-aliexpress-nordic-morandi-matte-ceramic` | products.json | ₪199 | ₪219 | ₪219 | אפשרות set=3pc, style=e, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪400 | 0.55 |
| `accent-sconces-cj-ribbed-travertine-half-cylinder-wood-bracket` | products.json | ₪599 | ₪659 | ₪599 | אפשרות other=wall-lamp, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪1,040 | 0.63 |
| `wall-decor-cj-macrame-dowel-50x70` | products.json | ₪119 | ₪129 | ₪119 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪329 | 0.39 |
| `toilet-brush-aliexpress-striped-ceramic-holder-165620` | card | ₪119 | ₪129 | ₪129 | אפשרות color=elephant-white, משלוח חסכוני (מחיר האפשרות לפי האתר) | — | — |
| `bench-cushion-aliexpress-linen-look-box-cushion-110x35x5` | leads | ₪249 | ₪269 | ₪269 | אפשרות color=color-10-rice-gray, size=35x35x5, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪290 | 0.93 |
| `pillowcases-cj-linen-pair-coconut-button` | products.json | ₪129 | ₪139 | ₪129 | המכירה (1 יח'), משלוח מהיר (עד 20 יום) | ₪299 | 0.46 |
| `bowl-aliexpress-pearl-rim-ingot-bowl-23` | leads | ₪129 | ₪139 | ₪139 | אפשרות color=dessert-bowl-small, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪139 | 1.0 |
| `bench-cushion-aliexpress-double-piping-cushion-110x35x5` | leads | ₪259 | ₪279 | ₪279 | אפשרות color=sg-6-light-gray, size=60x30x5, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪290 | 0.96 |
| `tableware-set-cj-swirl-coarse-pottery-set-23` | leads | ₪429 | ₪459 | ₪459 | המכירה (6 יח'), משלוח חסכוני | ₪485 | 0.95 |
| `bedding-aliexpress-boho-3d-tufted-cut-500672` | products.json | ₪349 | ₪369 | ₪369 | אפשרות size=eu-single-size-2-pcs, משלוח חסכוני (מחיר האפשרות לפי האתר) | ₪425 | 0.87 |
| `bedding-cj-washed-cotton-khaki-set-220x240` | products.json | ₪349 | ₪369 | ₪349 | אפשרות color=khaki, size=200x230, other=1.5-1.8m-flat-sheet-set, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪435 | 0.85 |
| `mug-set-aliexpress-oat-matte-cup-acacia-saucer-573382` | card | ₪229 | ₪239 | ₪239 | יחידה אחת מהסט, משלוח חסכוני (מחיר היחידה: ההערכה של האתר) | ₪237 | 1.01 |
| `bedding-cj-cream-ruffle-rosebud-set` | products.json | ₪299 | ₪309 | ₪299 | אפשרות color=rose-fairy-light-pink, other=2.0m-flat-sheet-four-pieces, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪420 | 0.74 |
| `bedding-cj-plain-linen-flat-sheet-raw-jute-260x280` | products.json | ₪469 | ₪479 | ₪469 | אפשרות style=bed-sheet-120x220cm, other=cameo-red, משלוח מהיר (מחיר האפשרות לפי האתר) | ₪940 | 0.51 |

התרחיש שקבע את המחיר: sale/economy 11, variant/fast 62, sale/fast 58, variant/economy 28, single/economy 1, variant-single/economy 2.

## יקר מהשוק

67 מוצרים. מסומנים `above-market` ב-`flags` וב-`no_loss` של השורה (הסטודיו עוד לא מציג תווית כזו: build.py מעביר רק ok, below-floor ו-loss).

| מוצר | מחיר חדש | השוואה גבוהה | יחס |
| --- | --- | --- | --- |
| `pendant-cj-tiered-fabric-drum` | ₪2,489 | ₪460 | פי 5.41 |
| `floor-lamp-cj-cream-arc-pleated-152` | ₪3,389 | ₪651 | פי 5.21 |
| `pendant-cj-wabi-pleated-fabric-lantern-50` | ₪1,739 | ₪420 | פי 4.14 |
| `basket-cj-seagrass-belly` | ₪749 | ₪190 | פי 3.94 |
| `planter-cj-seagrass-belly` | ₪749 | ₪190 | פי 3.94 |
| `planter-cj-cement-ribbed-belly` | ₪1,389 | ₪360 | פי 3.86 |
| `table-lamp-cj-white-textured-ceramic-linen-drum` | ₪1,129 | ₪295 | פי 3.83 |
| `dining-pendant-cj-black-ring-cloth-lantern-50` | ₪1,559 | ₪420 | פי 3.71 |
| `tableware-set-cj-grey-sand-matte-plate` | ₪159 | ₪50 | פי 3.18 |
| `mug-set-cj-cream-matte-breakfast-cup` | ₪239 | ₪90 | פי 2.66 |
| `ceiling-light-cj-waxwood-dome-ash-40` | ₪1,099 | ₪420 | פי 2.62 |
| `ceiling-lights-cj-pleated-fabric-saucer-flush-50` | ₪2,339 | ₪900 | פי 2.6 |
| `pendant-cj-fabric-dome-ash-cap-25` | ₪479 | ₪195 | פי 2.46 |
| `wall-sconce-cj-black-swing-arm-wood-shade` | ₪449 | ₪195 | פי 2.3 |
| `ceiling-lights-cj-silk-cocoon-flush-40` | ₪899 | ₪420 | פי 2.14 |
| `wall-sconce-cj-black-swan-arm-white-fabric-cone` | ₪309 | ₪150 | פי 2.06 |
| `pool-cj-wood-sunburst-mirror-43` | ₪449 | ₪220 | פי 2.04 |
| `pendant-cj-pleated-pumpkin-lantern-40` | ₪909 | ₪450 | פי 2.02 |
| `pool-cj-terracotta-amphora-floor-51` | ₪2,129 | ₪1,055 | פי 2.02 |
| `ceiling-light-cj-opal-glass-drum-flush-32` | ₪599 | ₪300 | פי 2.0 |
| `tableware-set-cj-speckled-oat-stoneware-bowl-13` | ₪159 | ₪80 | פי 1.99 |
| `mug-set-cj-oat-speckled-round-mug-wood-saucer` | ₪119 | ₪60 | פי 1.98 |
| `magazine-holder-cj-gunmetal-leather-strap` | ₪439 | ₪229 | פי 1.92 |
| `wall-sconce-cj-black-swing-arm-fabric` | ₪539 | ₪293 | פי 1.84 |
| `vase-cj-white-plum-hand-thrown` | ₪849 | ₪479 | פי 1.77 |
| `wall-sconce-cj-white-fabric-cube-15` | ₪529 | ₪299 | פי 1.77 |
| `vase-cj-matte-moon-jar-white` | ₪469 | ₪269 | פי 1.74 |
| `bedside-sconces-cj-linen-wave-flush` | ₪989 | ₪598 | פי 1.65 |
| `bench-pad-cj-tufted-long-cushion-khaki-120` | ₪219 | ₪135 | פי 1.62 |
| `open-shelf-ceramics-cj-morandi-matte-bottle-set` | ₪429 | ₪270 | פי 1.59 |
| `rug-cj-braided-wool-natural` | ₪4,099 | ₪2,700 | פי 1.52 |
| `centerpiece-vase-cj-sandy-white-bead-band-25` | ₪449 | ₪295 | פי 1.52 |
| `framed-art-cj-line-scribble-white-mat-50` | ₪339 | ₪225 | פי 1.51 |
| `wall-sconce-cj-black-folding-arm-woodgrain-cone-18` | ₪289 | ₪195 | פי 1.48 |
| `framed-art-cj-taupe-block-black-line-30x40` | ₪269 | ₪200 | פי 1.34 |
| `bowl-cj-glutinous-white-belly-bowl-21` | ₪159 | ₪120 | פי 1.32 |
| `floor-lamp-cj-pleated-walnut-stem-158` | ₪849 | ₪651 | פי 1.3 |
| `accent-sconces-aliexpress-indoor-stone-wall-lamp` | ₪659 | ₪520 | פי 1.27 |
| `pool-cj-cotton-linen-box-camel-40x30` | ₪89 | ₪70 | פי 1.27 |
| `pendant-cj-fluted-ceramic-wood-cap-short-lantern` | ₪399 | ₪315 | פי 1.27 |
| `shelf-boxes-cj-two-tone-fabric-bin-27x20x12-pair` | ₪89 | ₪70 | פי 1.27 |
| `bowl-cj-reactive-white-rimmed-plate-21` | ₪169 | ₪139 | פי 1.22 |
| `bowl-aliexpress-kiln-corrugated-raw-rim-bowl-23` | ₪169 | ₪139 | פי 1.22 |
| `framed-art-cj-swinging-line-black-frame-mat-35x45` | ₪269 | ₪225 | פי 1.2 |
| `framed-prints-cj-charcoal-line-black-frame-35x45` | ₪269 | ₪225 | פי 1.2 |
| `pendant-cj-light-wood-slat-drum-43` | ₪1,069 | ₪895 | פי 1.19 |
| `vase-cj-charcoal-carved` | ₪559 | ₪479 | פי 1.17 |
| `open-shelf-ceramics-cj-patina-clay-pitcher-and-jar` | ₪279 | ₪240 | פי 1.16 |
| `magazine-holder-cj-felt-log-basket` | ₪149 | ₪130 | פי 1.15 |
| `framed-art-aliexpress-retro-farmhouse-chicken-botanical-333603` | ₪229 | ₪200 | פי 1.15 |
| `shelf-boxes-cj-felt-storage-bin-30x24-pair` | ₪79 | ₪70 | פי 1.13 |
| `vanity-vase-aliexpress-sand-oat-bud-vase-g-series` | ₪89 | ₪79 | פי 1.13 |
| `basket-cj-jute-rope-cylinder` | ₪199 | ₪179 | פי 1.11 |
| `candle-holders-aliexpress-cutelife-black-ceramic-candelabra` | ₪139 | ₪125 | פי 1.11 |
| `bath-mat-cj-solid-wood-slatted-61x45` | ₪439 | ₪399 | פי 1.1 |
| `bench-pad-aliexpress-double-piping-cushion-130x35x5` | ₪319 | ₪290 | פי 1.1 |
| `bedding-cj-washed-polyester-set-milk-tea` | ₪229 | ₪210 | פי 1.09 |
| `skateboard-cj-blank-maple-43` | ₪159 | ₪149 | פי 1.07 |
| `bedding-cj-cotton-linen-duvet-beige` | ₪1,139 | ₪1,080 | פי 1.05 |
| `curtains-aliexpress-cotton-linen-texture-translucent-091154` | ₪509 | ₪489 | פי 1.04 |
| `magazine-holder-cj-arch-iron-cane` | ₪239 | ₪229 | פי 1.04 |
| `wall-sconce-cj-wavy-linen-flush-25` | ₪309 | ₪299 | פי 1.03 |
| `bench-pad-aliexpress-linen-look-box-cushion-130x35x5` | ₪299 | ₪290 | פי 1.03 |
| `bath-mat-cj-tufted-cotton-frame-beige-40x60` | ₪169 | ₪165 | פי 1.02 |
| `bedside-sconces-cj-linen-half-drum-black-trim` | ₪609 | ₪598 | פי 1.02 |
| `pool-cj-carbonized-wood-pedestal-candlestick` | ₪189 | ₪185 | פי 1.02 |
| `mug-set-aliexpress-oat-matte-cup-acacia-saucer-573382` | ₪239 | ₪237 | פי 1.01 |

## מחיר שהמשתמש קבע ומפסיד (לא שונה)

- `cushions-aliexpress-fashion-modern-wabi-sabi-464203` ב-₪69 (Studio db product_edits/cushions-aliexpress-fashion-modern-wabi-sabi-464203.json (synced 2026-10-13)). במק"ט שבחדר התרומה ₪1.29 (מרווח 2.2%), אבל בתרחיש הגרוע (אפשרות color=1pcs-beige, size=30x50, משלוח חסכוני (מחיר האפשרות לפי האתר)) ₪-8.56. המחיר שלא מפסיד באף תרחיש: ₪89 (נקודת איזון ₪80.27). להחלטת המשתמש.

## לבדוק: כמות המכירה

במוצרים האלה הסטודיו קרא את מספר היחידות במכירה מעלות הנחיתה שברשומה (studio/build.py lead_qty), לא משדה כמות. המחיר הועלה לפי הכמות שהסטודיו מוכר. ברשימה רק מוצרים שבהם המחיר הקודם לא היה מפסיד אילו המכירה הייתה יחידה אחת (העמודה האחרונה: המחיר הנמוך שלא מפסיד ליחידה אחת).

| מוצר | יח' בסטודיו | היה | עכשיו | אם יחידה אחת |
| --- | --- | --- | --- | --- |
| `kitchen-sconce-aliexpress-rustic-wooden-wall-sconce-632957` | 4 | ₪229 | ₪539 | ₪139 |
| `toy-cars-aliexpress-wooden-toys-beech-wood-138166` | 3 | ₪159 | ₪179 | ₪59 |

`kitchen-sconce-aliexpress-rustic-wooden-wall-sconce-632957`: עלות הנחיתה ברשומה (₪100.6) היא בדיוק יחידה אחת ועוד משלוח ($8.01 + $22.49 במטמון AliExpress, × 3.3), והעמדה היא מנורה אחת: כנראה הסטודיו טועה ב-4 יח'. מומלץ לקבוע כמות 1 ולהחזיר את המחיר ל-₪229 בהחלטת המשתמש. `toy-cars-aliexpress-wooden-toys-beech-wood-138166`: הנחיתה ברשומה (₪115) מתאימה ל-3 יח' ב-$1.99, אבל הנימוק אומר "פריט בודד (יש SKU סט)": לבדוק מה נמכר.

## קלטים מוערכים

- `no-fast-method`: 74 מוצרים
- `qty-freight-estimated`: 24 מוצרים
- `freight-from-cache-only`: 11 מוצרים
- `freight-from-other-sku`: 6 מוצרים
- `freight-estimated`: 6 מוצרים

freight-estimated = אין הצעת משלוח, נלקחה ההערכה הגבוהה; qty-freight-estimated = משלוח לכמה יחידות לפי חבילה לכל יחידה; freight-from-other-sku = המשלוח נמדד על מק"ט אחר; freight-from-cache-only = לסטודיו אין משלוח, נלקח ממטמון הספק; no-fast-method = אין לספק משלוח עד 20 יום בנתוני הסטודיו (אם יוצע מהיר במוצר כזה, הוא לא נבדק).

## אי אפשר לחשב

- `dining-chairs-furniture-express-maya` (products.json, studio-price): עלות במטבע ILS, לא בדולר, מחיר ₪399
- `paper-towel-holder-cj-beech-upright-31` (products.json, studio-price): הספק לא שולח לישראל, מחיר ₪39
- `bath-towels-cj-diamond-peshtemal-cotton-90x180` (coverage): אין משלוח ואין הערכה
- `bath-towels-cj-honeycomb-waffle-cotton-70x140` (coverage): אין משלוח ואין הערכה
- `bath-towels-cj-striped-peshtemal-cotton-90x180` (coverage): אין משלוח ואין הערכה
- `bedding-cj-stripe-cotton-single-set-light-brown` (coverage): אין משלוח ואין הערכה
- `pendant-cj-silk-pumpkin-lantern-40-master` (coverage): אין משלוח ואין הערכה
- `pillowcases-cj-washed-linen-double-ruffle-48x74` (coverage): אין משלוח ואין הערכה
- `tea-towel-cj-herringbone-fringe-cotton-38x60` (coverage): אין משלוח ואין הערכה
- `trinket-dish-cj-organic-ceramic-tray-black` (coverage): אין משלוח ואין הערכה

כרטיסים שנספרים בכיסוי ואין להם מחיר בכלל (132): המחיר שלא מפסיד לכל אחד ב-JSON (`counted_without_price`), כמחיר התחלה מוצע. לא נכתב מחיר.

## בדיקות

- בניית הסטודיו: python3 -I studio/build.py --offline: עברה (489 כרטיסים, 324 מחירים, 58 קבצים, 19.7MB). הורצה offline כדי לא לפנות לשרתי הספקים: 14 תמונות מוצר שאינן במטמון יצאו כמקום שמור. לפני פרסום להריץ בנייה רגילה. הסטודיו לא פורסם.
- smoke_boards: עבר (0 כשלים)
- smoke_compare: עבר (0 כשלים)
- smoke_compose: עבר (0 כשלים)
- smoke_decisions: עבר (0 כשלים)
- smoke_office: עבר (0 כשלים)
- smoke_products: עבר (0 כשלים)
- smoke_db_contract --db scratchpad/studio-db: נכשל בבדיקה אחת שאינה קשורה למחירים: ההחלטות R6Q1–R6Q4 ו-VAT1 נמצאות ב-status/decisions.json ולא ב-db המיוצא (ייצוא מ-2026-10-17, ישן מההחלטות). כל שאר הבדיקות עברו, כולל עריכת המוצר המסונכרנת
- בדיקות היחידה של האתר (vitest): 62 עברו, 2 נכשלו. אותם 2 נכשלים גם ב-HEAD נקי (worktree): 78 כרטיסים לא עוברים את הסכמה (בעיית נתונים קיימת), ו-sellQtyDefault של האתר לא מסיק כמות מעלות הנחיתה כמו studio/build.py (הבדיקה רצה רק כש-studio/dist/data.json קיים). לא נגרמו מהשינוי
- בניית הקטלוג של האתר (tsx tools/build-catalog.ts): עברה: 42 מוצרים בסלון (6 במחיר זמני), 11 מהם במשלוח ברירת מחדל $17; 78 כרטיסים לא תקינים דולגו (קיים). הקבצים ב-site/.generated נבנו מחדש
- python3 -I scripts/economics/no_loss.py --check: יצא ב-0: אין מוצר מפסיד, חוץ ממחיר המשתמש

## מועמדים שנדחו רק בגלל הפסד (סבבים 5 ו-6, התאמה 7+)

נקראו 105 מועמדים בלי כרטיס שהרשומה שלהם מפסידה; 51 נדחו רק בגלל ההפסד. כל מועמד בלי כרטיס בהתאמה 7+ שהרשומה שלו מפסידה נקרא ידנית: 'in' רק כשההפסד הוא סיבת הדחייה היחידה. הרווח בכיסוי מחושב בכלל של final_round_coverage.py (פונקציות הסקריפט, בלי לכתוב קובץ), כאילו לכל מועמד יש כרטיס באפשרות אחת (צבע אחד) בסגנונות שבהם ההתאמה 7+. המחיר שלא מפסיד כאן הוא במשלוח שברשומה בלבד. דיווח בלבד: לא שונה אף קובץ תוצאות ולא סקריפט הכיסוי.

| עמדה | מוצר | סגנונות 7+ | נחיתה | מחיר שלא מפסיד | השוואה גבוהה | יחס | הערה |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bath/bath-towels | AliExpress 1005012773111382 | nordic 7, warm-modern 7, japandi 8, mediterranean 7, modern-country 7 | ₪147.15 | ₪199 | ₪279.80 | 0.71 | זוג; נדחה כי המחיר שלא מפסיד מעל ההשוואה (בדיוק מה שהכלל החדש מתיר) |
| bath/ledge-planter | AliExpress 1005005532674549 | japandi 8, boho 7 | ₪139.52 | ₪189 | ₪90 | 2.1 | מעטפת גבולית (גובה 10, לבדוק בפריים) |
| bath/toilet-brush | AliExpress 1005009105041173 | mediterranean 7, boho 7 | ₪134 | ₪179 | ₪120 | 1.49 | מעטפת גבולית (11×40) |
| bath/toilet-brush | AliExpress 1005009768828838 | mediterranean 7, boho 7 | ₪129.60 | ₪179 | ₪120 | 1.49 | מעטפת גבולית; משלוח 22–29 יום |
| bath/toilet-brush | AliExpress 1005012951198712 | mediterranean 7, boho 7 | ₪222.39 | ₪299 | ₪90 | 3.32 | מעטפת גבולית |
| bath/toothbrush-cup | AliExpress 1005012763561649 | modern-country 8 | ₪51.28 | ₪79 | ₪59.90 | 1.32 |  |
| corridor/ceiling-lights | AliExpress 1005008258911244 | modern-country 7 | ₪551.80 | ₪729 | ₪864 | 0.84 | זוג; 2 × ₪432 |
| corridor/ceiling-lights | AliExpress 1005012943662628 | japandi 7 | ₪925.85 | ₪1,229 | ₪1,164 | 1.06 | זוג; 2 × ₪582 |
| corridor/ceiling-lights | AliExpress 1005009553503527 | warm-modern 7 | ₪1,313.80 | ₪1,739 | ₪1,164 | 1.49 | זוג; 2 × ₪582; מעטפת גבולית |
| corridor/ceiling-lights | AliExpress 1005010338870714 | modern-country 7.5 | ₪2,250.70 | ₪2,969 | ₪749 | 3.96 | משלוח $266, 15 ק"ג |
| corridor/gallery-stool | AliExpress 1005007997798374 | warm-modern 8, japandi 8, boho 7 | ₪837.84 | ₪1,109 | ₪990 | 1.12 | מעטפת גבולית (32) |
| corridor/gallery-stool | AliExpress 1005013193019065 | nordic 7, japandi 7, mediterranean 7, boho 7 | ₪788 | ₪1,039 | ₪450 | 2.31 | מעטפת גבולית (32, לבדוק בפריים) |
| corridor/gallery-stool | AliExpress 1005012957725537 | modern-country 7, boho 7 | ₪930.60 | ₪1,229 | ₪530 | 2.32 | מעטפת גבולית |
| corridor/gallery-stool | AliExpress 1005010196581566 | mediterranean 7 | ₪1,188.30 | ₪1,569 | ₪530 | 2.96 | מעטפת גבולית; גזע עץ כבד |
| corridor/gallery-stool | AliExpress 1005009998944410 | modern-country 7, boho 7 | ₪377.40 | ₪499 | ₪150 | 3.33 | משלוח מוערך (~$85 ל-4 ק"ג), אין הצעה במטמון |
| corridor/picture-lights | AliExpress 1005008195905528 | nordic 7 | ₪742 | ₪979 | ₪599.70 | 1.63 | שלישייה; מעטפת גבולית |
| dining-room/bowl | CJ 1392716043398549504 | mediterranean 7.5, modern-country 7, boho 7.5 | ₪103.60 | ₪139 | ₪184 | 0.76 |  |
| dining-room/bowl | AliExpress 1005006118879427 | boho 7 | ₪55.24 | ₪79 | ₪60 | 1.32 |  |
| dining-room/bowl | AliExpress 1005010778409131 | boho 8 | ₪82.47 | ₪119 | ₪60 | 1.98 |  |
| dining-room/canisters | CJ 1475674474018902016 | japandi 7.5 | ₪272.60 | ₪369 | ₪210 | 1.76 | סט של 3 |
| dining-room/dining-pendant | AliExpress 1005010594359379 | boho 7 | ₪514.30 | ₪679 | ₪490 | 1.39 |  |
| dining-room/dining-pendant | AliExpress 1005004131706427 | japandi 7, mediterranean 8, boho 7 | ₪731.35 | ₪969 | ₪640 | 1.51 |  |
| dining-room/dining-pendant | AliExpress 1005008672138088 | mediterranean 7, boho 7 | ₪565 | ₪749 | ₪490 | 1.53 | משלוח $111 |
| dining-room/herb-pots | AliExpress 1005009049409120 | mediterranean 7 | ₪151.07 | ₪209 | ₪79.60 | 2.63 | 4 עציצים; ההשוואה 4 × ₪19.90 |
| dining-room/mug-set | AliExpress 1005010196442767 | modern-country 7 | ₪234.30 | ₪319 | — | — | 3 ספלים; משלוח $18.73 ליחידה; אין השוואה ברשומה |
| dining-room/tableware-set | Zendrop 2624310 | japandi 7, mediterranean 7, modern-country 7.5 | ₪415 | ₪549 | ₪485 | 1.13 | סט 6; בתמונה סימן מים של מותג אחר |
| hall/planter | AliExpress 1005008561559475 | boho 7 | ₪1,173.45 | ₪1,549 | ₪349 | 4.44 | מעטפת גבולית; לא נבדקו השוואות (משלוח $281) |
| hall/storage-boxes | CJ 1705144683208388608 | modern-country 7 | ₪223.20 | ₪299 | ₪398 | 0.75 | זוג; מעטפת גבולית |
| hall/storage-boxes | AliExpress 1005008480586450 | boho 7 | ₪132.90 | ₪179 | ₪196 | 0.91 | זוג; בתור חיפוש-תמונה למוכר זול |
| hall/storage-boxes | AliExpress 1005012923580024 | boho 8 | ₪291.30 | ₪389 | ₪200 | 1.95 | מעטפת גבולית (L, לבדוק בפריים); זוג |
| kids/bookshelf | AliExpress 1005007471139220 | modern-country 7 | ₪275.50 | ₪369 | ₪278 | 1.33 | זוג מדפים 50 |
| living-room/floor-lamp | AliExpress 1005009785153450 | nordic 7 | ₪1,288.35 | ₪1,699 | ₪1,000 | 1.7 | מעטפת גבולית; משלוח $266 |
| living-room/floor-lamp | AliExpress 1005009386433696 | warm-modern 7 | ₪2,842.30 | ₪3,749 | ₪949 | 3.95 | משלוח $718; אין השוואה ברשומה (מחיר השווי ₪949) |
| living-room/framed-art | CJ 1643938313063108608 | nordic 7 | ₪1,417.90 | ₪1,869 | ₪979 | 1.91 | שלישייה; To Door ‏$121 ליחידה |
| living-room/magazine-holder | CJ 2608300209161600400 | warm-modern 7.5 | ₪161.14 | ₪219 | ₪229 | 0.96 | מעטפת גבולית |
| living-room/pendant | AliExpress 1005008672138088 | mediterranean 7, boho 7 | ₪565 | ₪749 | ₪449 | 1.67 | משלוח $111 |
| living-room/pendant | AliExpress 1005013224966509 | mediterranean 7 | ₪1,079.80 | ₪1,429 | ₪582 | 2.46 | לבוהו המידה לא מתאימה; ים-תיכוני בלבד |
| living-room/sofa-cover | AliExpress 1005012935062690 | boho 7 | ₪192.70 | ₪259 | ₪150 | 1.73 |  |
| living-room/wall-decor | AliExpress 1005012947811160 | modern-country 7 | ₪75.37 | ₪109 | ₪99 | 1.1 | בלי חישוק פליז |
| master/floor-lamp | AliExpress 1005012507637187 | warm-modern 8, modern-country 7 | ₪742 | ₪979 | ₪949 | 1.03 | מעטפת גבולית; 12 ק"ג |
| master/floor-lamp | AliExpress 1005009551034916 | warm-modern 8 | ₪809.80 | ₪1,069 | ₪949 | 1.13 | מעטפת גבולית |
| master/floor-lamp | AliExpress 1005009386433696 | warm-modern 7 | ₪2,842.30 | ₪3,749 | ₪949 | 3.95 | משלוח $718 |
| master/nightstand-tray | AliExpress 1005007695543234 | warm-modern 7, japandi 7, mediterranean 7 | ₪62.53 | ₪89 | ₪89 | 1.0 | מעטפת גבולית (20) |
| master/nightstand-tray | CJ 1393439287588032512 | nordic 7.5, warm-modern 7 | ₪117.68 | ₪159 | ₪139 | 1.14 |  |
| master/pendant | AliExpress 1005008743252990 | warm-modern 7, japandi 7, modern-country 7 | ₪455.20 | ₪609 | ₪652 | 0.93 | מעטפת גבולית |
| master/pendant | AliExpress 1005008672138088 | mediterranean 7, boho 7 | ₪565 | ₪749 | ₪449 | 1.67 | משלוח $111 |
| master/pendant | AliExpress 1005006435771102 | modern-country 7.5 | ₪994.40 | ₪1,319 | ₪499 | 2.64 | משלוח $180, 10 ק"ג |
| work/magazine-holder | CJ 2608300209161600400 | warm-modern 7.5 | ₪161.14 | ₪219 | ₪229 | 0.96 | מעטפת גבולית |
| work/shelf-boxes | AliExpress 1005006768278100 | boho 7 | ₪151.17 | ₪209 | ₪198 | 1.06 | זוג; מעטפת גבולית |
| work/shelf-boxes | CJ 2110994015976243202 | japandi 7 | ₪332.10 | ₪439 | ₪360 | 1.22 | זוג; 2 × ₪180 |
| work/shelf-boxes | AliExpress 1005009831522799 | boho 7 | ₪200.57 | ₪269 | ₪180 | 1.49 | זוג; מעטפת גבולית |

### הרווח בכיסוי אם ייספרו

| סגנון | עמדות | 3 אפשרויות היום | אם ייספרו | נוספו |
| --- | --- | --- | --- | --- |
| nordic | 101 | 66 (65.3%) | 67 (66.3%) | +1 (+1.0 נק') |
| warm-modern | 124 | 81 (65.3%) | 84 (67.7%) | +3 (+2.4 נק') |
| japandi | 124 | 76 (61.3%) | 78 (62.9%) | +2 (+1.6 נק') |
| mediterranean | 124 | 75 (60.5%) | 80 (64.5%) | +5 (+4.0 נק') |
| modern-country | 124 | 71 (57.3%) | 75 (60.5%) | +4 (+3.2 נק') |
| boho | 124 | 73 (58.9%) | 78 (62.9%) | +5 (+4.0 נק') |
| **סה"כ** | 721 | 442 (61.3%) | 462 (64.1%) | +20 |

שאר המועמדים שנקראו נדחו גם מסיבה אחרת (מעטפת, CE או IP44, קליעה פתוחה, מלאי, כפילות); הסיבה לכל אחד ב-JSON (`rejected_candidates.reviewed`).

## מה עוד צריך

- המשתמש: לאשר או לשנות את המחירים שהועלו, ובמיוחד את היקרים מהשוק. אפשרות: לגבות משלוח מהיר בנפרד במוצרים כבדים, או לא להציע אותו בהם, ואז המחיר לפי החסכוני מספיק (`no_loss_economy_only_ils` לכל מוצר).
- frontend-dev: מחיר האפשרויות באתר (skuRetail) מוריד אפשרות זולה יותר ממה שהעלות יורדת, והאתר מחשב משלוח $17 למוצרי AliExpress ו-Zendrop; תווית "יקר מהשוק" בסטודיו (build.py מעביר היום רק ok, below-floor ו-loss).
- לוחות החדרים (scripts/boards/room_boards.py) קוראים את המרווח של כרטיסי הסבב מהרשומה, לא מהמחיר החדש בכרטיס.
- ממשיכים לחפש חלופה זולה יותר באותו מראה למוצרים שהועלו הרבה (ה.13).
