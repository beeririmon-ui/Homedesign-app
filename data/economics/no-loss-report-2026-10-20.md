# אין מוצר מפסיד: דוח (מצב דיווח, 2026-10-20)

הכלל (ה.13, תיקון 2026-10-20): "בא נוודא שאין דבר כזה מוצר מפסיד בשום צורה! יכול להיות יקר ללקוח אבל אין מפסיד!". לכל מוצר שהסטודיו או האתר יכולים למכור חושבה התרומה בתרחיש הגרוע ביותר לפי הכללים המתוקנים, ומוצע מחיר = max(הנוכחי, המחיר שלא מפסיד). **שום דבר לא שונה**: לא products.json, לא הכרטיסים, לא הסטודיו ולא האתר. המנהל קורא, ובריף קצר שני מחיל.

הסקריפט: `python3 -I scripts/economics/no_loss.py --report --db <ייצוא db של הסטודיו>` (הדוח הזה; הקובץ המלא: `no-loss-report-2026-10-20.json`), `--check` (אינווריאנטים; יוצא ב-1 כל עוד יש מוצר שמפסיד במחירו הנוכחי), `--apply` (לבריף ההחלה; לא הורץ).

## הכללים המתוקנים

1. שיטת משלוח: רק שיטת ברירת המחדל, הזולה לישראל, עם מעקב כשהספק מציע (בדרך כלל CJ Eub או השיטה של AliExpress בכרטיס). לא To Door, DHL או אקספרס כשיש זולה יותר; אקספרס-בלבד נרשם בנפרד
2. כמות: החבילה המשולבת של הסטודיו, משלוח ל-q = יחידה + (q−1) × max(0, יחידה − $3.72)
3. kitchen-sconce-aliexpress-rustic-wooden-wall-sconce-632957: יחידה אחת
4. וריאנטים, צבעים וגדלים נשארים בתרחיש הגרוע; משלוח מוערך בתרחיש הגרוע שלו
5. מחיר מוצע = max(הנוכחי, המחיר שלא מפסיד), מעוגל למעלה לסיומת 9. לא יורד. הכרית של המשתמש (₪69) מדווחת ולא משתנה

## בקצרה

- נבדקו 464 מוצרים: כל שורה ב-products.json, כל כרטיס שסקריפט הכיסוי סופר, וכל כרטיס שיש לו מחיר בסטודיו. לפי סטטוס: raise 113, ok 204, owner-set-loses 1, express-only 6, cannot-compute 10, no-price 130.
- **הועלות מוצעות: 113** (מתוך 324 מוצרים עם מחיר שאפשר לחשב). מ-₪19–₪949 ל-₪39–₪3,529; פי 1.04 עד פי 10.11, חציון פי 1.5.
- מה קבע את ההעלאה: sale 46, variant 66, single 1 (sale = המכירה במק"ט שבחדר; variant = אפשרות ספק במחיר שהאתר נותן לה; single = יחידה אחת מסט במחיר ההערכה של האתר). ב-22 מהן המחיר הנוכחי לא מפסיד במק"ט שבחדר, וההעלאה באה רק מהאפשרויות או מהיחידה הבודדת כפי שהאתר מתמחר אותן.
- **יקר מהשוק: 28** (המחיר שלא מפסיד מעל ההשוואה הגבוהה); היחס הגבוה פי 5.42.
- **אקספרס בלבד: 6** (לספק אין שיטה רגילה למוצר); רשומים בנפרד, בלי העלאה מוצעת.
- מחיר של המשתמש שמפסיד: 1 (הכרית, NL1). אי אפשר לחשב: 10. כרטיסים שנספרים בכיסוי בלי מחיר בכלל: 130.
- בדיקת הנוסחה: ב-166 מתוך 169 שורות products.json המרווח של צוות התמחור שווה לקריאת הסטודיו של הדוח (עד נקודה); שונה ב-3: `cushions-aliexpress-fashion-modern-wabi-sabi-464203`, `framed-art-aliexpress-japanese-wabi-sabi-tree-176323`, `wall-sconce-cj-white-fabric-cube-15` (מחיר, מק"ט או כמות אחרים; `row-margin-differs`).
- **מעל ₪247** ($75 × 3.3: תקרת הפטור ממע"מ ביבוא אישי (docs/tax/README.md)): שורות products.json 35 → 53 (מתוך 181); כל המוצרים עם מחיר 95 → 113 (מתוך 324). 'אחרי' = המחירים המוצעים; מחיר המשתמש ומוצרי אקספרס-בלבד נשארים במחירם הנוכחי.

## הנוסחה, ואיפה המחיר חי

- תרומה = נטו − נחיתה − (2% מהמחיר + ₪1.2) − 8% מהנטו; נטו = מחיר ÷ 1.18; נחיתה = (עלות ליחידה × כמות + משלוח לכמות) × 3.3. לפני CAC. דמי המשלוח שהלקוח משלם לא נספרים, כמו בסטודיו. סיומת המחיר: שקל שלם שנגמר ב-9.
- הגדרות: usd_ils 3.3, vat_pct 18, card_pct 2, card_fixed_ils 1.2, returns_pct 8, cac_ils 100, packaging_ils 0, target_margin_pct 40, items_per_order 1.4 (data/economics/settings.json + ברירות המחדל של הסטודיו).
- ייצוא ה-db של הסטודיו שנקרא: `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/studio-db` (עריכות מחיר של המשתמש).

| מקור המחיר | מוצרים | מי קורא אותו |
| --- | --- | --- |
| owner | 1 | עריכה בסטודיו (db product_edits), מסונכרנת ל-products.json עם retail_src studio. לא משתנה |
| products.json | 180 | data/economics/products.json products.<id>.retail_ils: הסטודיו והאתר קוראים אותו |
| card | 41 | כרטיס המוצר price.suggested_retail או price.retail_ils: הסטודיו בלבד |
| leads | 102 | price_ils ברשומת הסבב האחרון (data/leads/final-2026-10-13/results/*.json): הסטודיו בלבד, דרך room_boards.Context; בהחלה המחיר החדש נרשם בכרטיס (price.retail_ils), שהסטודיו קורא לפני הרשומה |
| none | 140 | אין מחיר: כרטיס שנספר בכיסוי בלי מחיר בשום מקום |

- data/economics/pricing/*-2026-10-11.json: המקור שממנו נבנה products.json; אף אחד לא קורא אותו היום (היסטוריה)

### הסטודיו מול האתר

| נושא | הסטודיו | האתר | זהה |
| --- | --- | --- | --- |
| נוסחת התרומה | studio/src/index.html econCalc: נטו = P/1.18; עמלה = 2%·P + ₪1.2; שמורה = 8% מהנטו; אריזה 0; תרומה = נטו − נחיתה − עמלה − שמורה | site/shared/src/pricing.ts unitEconomics: אותה נוסחה, באגורות (עיגול בכל שלב, הפרש של אגורות) | כן |
| הגדרות | data/economics/settings.json + ברירות המחדל של ECON_META (שער 3.3, מע"מ 18%, 2% + ₪1.2, החזרות 8%, יעד 40%) | site/shared/src/schema/economics.ts DEFAULT_SETTINGS + resolveSettings: אותם ערכים | כן |
| משלוח לכמות | shipForQty: יחידה + (q − 1) × max(0, יחידה − $3.72); הצעה שנמדדה לכל המכירה (quoted_qty = q) נלקחת כמו שהיא. **זה הכלל של הדוח (תיקון 2)** | cogsAgorot = (עלות + משלוח ליחידה) × q: ליניארי, בלי חיסכון החבילה (שמרני יותר); build-catalog.ts | לא |
| שיטת המשלוח | ידני (products.json) ← freight-cj / freight-zendrop / freight-aliexpress (cheapest) ← המק"ט בכרטיס ← רשומת הסבב האחרון | ידני ← freight-cj.json cheapest ← ברירת מחדל $17 (resolveShippingUsd): למוצרי AliExpress ו-Zendrop בלי משלוח ידני האתר מחשב $17 | לא |
| מקור המחיר | עריכה בסטודיו (db) ← products.json retail_ils ← מחיר בכרטיס (price.retail_ils / suggested_retail) ← price_ils ברשומת הסבב | products.json retail_ils בלבד; בלי שורה: מחיר מומלץ ב-40% (זמני), ובבנייה קפדנית (--strict-prices) לא מוצג | לא |
| אפשרויות הספק (וריאנטים) | רק המק"ט שבחדר | options.ts skuRetail: sku_retail_ils של הסטודיו, אחרת P + (המומלץ של האפשרות − המומלץ של המק"ט שבחדר); בבנייה קפדנית אפשרות בלי sku_retail_ils לא נמכרת | לא |
| יחידה אחת מסט (P1) | לא מוצג | packs.ts unitPriceEstimateIls: ceil(P/N × 1.15) מעוגל מטה ל-9, או unit_retail_ils | לא |

מסקנה: נוסחת התרומה וההגדרות זהות בסטודיו ובאתר; הקלטים שונים (משלוח לכמות, מקור המשלוח, מקור המחיר, האפשרויות והיחידה הבודדת). הדוח הולך לפי הסטודיו במשלוח לכמות (תיקון 2) ולפי האתר במחיר האפשרויות והיחידה הבודדת (זה מה שנמכר שם).

## ההעלאות המוצעות

"מק"ט בלבד" = המחיר שלא מפסיד כשבודקים רק את המכירה במק"ט שבחדר (בלי אפשרויות ויחידה בודדת): כשהוא שווה למחיר הנוכחי, ההעלאה באה מתמחור האפשרויות באתר (skuRetail) או מהיחידה הבודדת. "מרווח" = המרווח במחיר המוצע במכירה הרגילה (מק"ט שבחדר, שיטת ברירת המחדל). הדגל: ok ≥40%, below-floor 0–40%, above-market = המחיר שלא מפסיד מעל ההשוואה הגבוהה.

| מוצר | מקור | נוכחי | מוצע | פי | התרחיש הגרוע (שיטה; כמות; וריאנט) | תרומה היום | נקודת איזון | מק"ט בלבד | מרווח | השוואה גבוהה | פי מההשוואה | דגל |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `floor-lamp-cj-cream-arc-pleated-152` | products.json | ₪349 | ₪3,529 | 10.11 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; המק"ט שבחדר | ₪-2,409.18 | ₪3,520.38 | ₪3,529 | 0.2% | ₪651 | 5.42 | above-market |
| `tableware-set-cj-grey-sand-matte-plate` | products.json | ₪19 | ₪109 | 5.74 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; size=10inch (נמכר ב-₪9) | ₪-66.57 | ₪106.63 | ₪109 | 4.4% | ₪50 | 2.18 | above-market |
| `centerpiece-vase-cj-sandy-white-bead-band-25` | products.json | ₪59 | ₪299 | 5.07 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; other=2345-white (נמכר ב-₪29) | ₪-177.04 | ₪292.05 | ₪289 | 5.4% | ₪295 | 1.01 | above-market |
| `mug-set-cj-oat-speckled-round-mug-wood-saucer` | products.json | ₪19 | ₪89 | 4.68 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-47.16 | ₪81.08 | ₪89 | 8.0% | ₪60 | 1.48 | above-market |
| `mug-set-cj-cream-matte-breakfast-cup` | products.json | ₪39 | ₪149 | 3.82 | הסטודיו (cj): CJPacket Eub 12-50; 3 יח'; המק"ט שבחדר | ₪-63.78 | ₪147 | ₪129 | 15.7% | ₪90 | 1.66 | above-market |
| `wall-sconce-cj-black-swing-arm-wood-shade` | products.json | ₪119 | ₪429 | 3.60 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; המק"ט שבחדר | ₪-232.75 | ₪425.38 | ₪429 | 0.8% | ₪195 | 2.2 | above-market |
| `candle-holders-aliexpress-cutelife-black-ceramic-candelabra` | products.json | ₪39 | ₪139 | 3.56 | מטמון AliExpress 3256811647185429 sku 12000056728690425 ×1: AliExpress Selection Standard 6-15; 1 יח'; color=white, set=1pc (נמכר ב-₪19) | ₪-68.41 | ₪129.05 | ₪119 | 14.0% | ₪125 | 1.11 | above-market |
| `wall-sconce-cj-black-swing-arm-fabric` | products.json | ₪149 | ₪519 | 3.48 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; המק"ט שבחדר | ₪-279.98 | ₪517.57 | ₪519 | 0.2% | ₪293 | 1.77 | above-market |
| `tableware-set-cj-speckled-oat-stoneware-bowl-13` | products.json | ₪29 | ₪99 | 3.41 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-37.81 | ₪92.96 | ₪79 | 18.3% | ₪80 | 1.24 | above-market |
| `bath-mat-cj-solid-wood-slatted-61x45` | products.json | ₪129 | ₪419 | 3.25 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; המק"ט שבחדר | ₪-215.22 | ₪412.31 | ₪419 | 1.4% | ₪399 | 1.05 | above-market |
| `toothbrush-cup-cj-travertine-look-cup-milktea` | products.json | ₪19 | ₪59 | 3.10 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=milk-tea-color, other=soap-dish (נמכר ב-₪9) | ₪-26.21 | ₪53.50 | ₪49 | 18.9% | ₪114 | 0.52 | below-floor |
| `wall-sconce-cj-white-fabric-cube-15` | products.json | ₪99 | ₪299 | 3.02 | הסטודיו (cj): CJPacket Eub 12-50; 2 יח'; color=white, style=warm-white, size=12x12 (נמכר ב-₪49) | ₪-149.17 | ₪295.37 | ₪279 | 7.9% | ₪299 | 1.0 | below-floor |
| `floor-vase-aliexpress-capiron-zen-ceramic` | products.json | ₪49 | ₪129 | 2.63 | מטמון AliExpress 3256808800994217 sku 12000047471652183 ×1: AliExpress standard shipping 8-18; 1 יח'; המק"ט שבחדר | ₪-55.16 | ₪121.61 | ₪129 | 5.1% | ₪295 | 0.44 | below-floor |
| `framed-art-aliexpress-retro-farmhouse-chicken-botanical-333603` | products.json | ₪89 | ₪229 | 2.57 | הסטודיו (aliexpress): AliExpress Selection Standard 6-15; 1 יח'; size=21x30-black-framed (נמכר ב-₪19) | ₪-55.44 | ₪220.78 | ₪129 | 39.2% | ₪200 | 1.15 | above-market |
| `shower-curtain-cj-linen-look-khaki-grommet` | products.json | ₪39 | ₪99 | 2.54 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=linen-gray-large-hole, size=100x180-single-curtain (נמכר ב-₪9) | ₪-38.48 | ₪89.66 | ₪79 | 20.8% | ₪129 | 0.77 | below-floor |
| `bench-pad-cj-tufted-long-cushion-khaki-120` | products.json | ₪59 | ₪149 | 2.52 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=black, size=130x50x8 (נמכר ב-₪49) | ₪-63.11 | ₪142.07 | ₪139 | 8.1% | ₪135 | 1.1 | above-market |
| `nightstand-tray-cj-travertine-look-rect-milktea` | products.json | ₪59 | ₪149 | 2.52 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=milk-tea-color, other=soap-dish (נמכר ב-₪19) | ₪-63.16 | ₪142.14 | ₪129 | 13.8% | ₪347 | 0.43 | below-floor |
| `floor-lamp-cj-pleated-walnut-stem-158` | products.json | ₪349 | ₪829 | 2.38 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; other=3-colortable-lamp (נמכר ב-₪229) | ₪-358.41 | ₪820.80 | ₪769 | 6.8% | ₪651 | 1.27 | above-market |
| `pool-cj-linen-look-tassel-curtain` | products.json | ₪59 | ₪139 | 2.36 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; style=width-150-height-160cm, other=diamond-plaid-stitching (נמכר ב-₪29) | ₪-53.19 | ₪129.02 | ₪119 | 17.0% | ₪198 | 0.7 | below-floor |
| `centerpiece-vase-aliexpress-nordic-matte-ceramic-vase` | products.json | ₪89 | ₪199 | 2.24 | קובץ התמחור:  (הערכה); 1 יח'; size=s (נמכר ב-₪9) | ₪-79.60 | ₪193.79 | ₪159 | 20.0% | ₪295 | 0.67 | below-floor |
| `accent-sconces-aliexpress-indoor-stone-wall-lamp` | products.json | ₪299 | ₪649 | 2.17 | מטמון AliExpress 3256807415537790 sku 12000043242375290 ×1: AliExpress standard shipping 22-32; 2 יח'; המק"ט שבחדר | ₪-258.96 | ₪639.89 | ₪649 | 1.3% | ₪520 | 1.25 | above-market |
| `tea-towel-zendrop-cotton-linen-washed-60x45` | products.json | ₪19 | ₪39 | 2.05 | הסטודיו (zendrop): Zendrop regular 14; 1 יח'; המק"ט שבחדר | ₪-14.82 | ₪38.50 | ₪39 | 1.1% | ₪49 | 0.8 | below-floor |
| `bath-mat-cj-tufted-cotton-frame-beige-40x60` | products.json | ₪39 | ₪79 | 2.03 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-24.34 | ₪71.04 | ₪79 | 9.0% | ₪165 | 0.48 | below-floor |
| `bowl-cj-glutinous-white-belly-bowl-21` | products.json | ₪39 | ₪79 | 2.03 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-24.64 | ₪71.43 | ₪79 | 8.6% | ₪120 | 0.66 | below-floor |
| `centerpiece-vase-aliexpress-modern-minimalist-white-ceramic` | products.json | ₪59 | ₪119 | 2.02 | קובץ התמחור:  (הערכה); 1 יח'; size=small (נמכר ב-₪29) | ₪-42 | ₪114.29 | ₪109 | 11.8% | ₪295 | 0.4 | below-floor |
| `pool-cj-terracotta-amphora-floor-51` | products.json | ₪479 | ₪959 | 2.00 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-363.29 | ₪957.23 | ₪959 | 0.2% | ₪1,055 | 0.91 | below-floor |
| `toothbrush-cup-cj-silver-travertine-cup` | products.json | ₪79 | ₪149 | 1.89 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-45.63 | ₪139.07 | ₪149 | 6.0% | ₪347 | 0.43 | below-floor |
| `sofa-cover-cj-bubble-stretch-slipcover` | products.json | ₪149 | ₪279 | 1.87 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=cream-white, other=single (נמכר ב-₪89) | ₪-91.56 | ₪269.53 | ₪239 | 13.1% | ₪600 | 0.47 | below-floor |
| `pool-cj-carbonized-wood-pedestal-candlestick` | products.json | ₪69 | ₪129 | 1.87 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-39.73 | ₪121.30 | ₪129 | 5.3% | ₪185 | 0.7 | below-floor |
| `framed-art-cj-line-scribble-white-mat-50` | products.json | ₪129 | ₪239 | 1.85 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; style=a, size=30x30 (נמכר ב-₪89) | ₪-80.18 | ₪234.54 | ₪229 | 7.2% | ₪225 | 1.06 | above-market |
| `bath-towels-cj-cotton-waffle-white` | products.json | ₪49 | ₪89 | 1.82 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=white, other=35x35cm (נמכר ב-₪9) | ₪-25.61 | ₪82.72 | ₪69 | 26.9% | ₪199 | 0.45 | below-floor |
| `soap-dispenser-cj-travertine-look-lotion-milktea` | products.json | ₪49 | ₪89 | 1.82 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=milk-tea-color, other=soap-dish (נמכר ב-₪29) | ₪-27.68 | ₪85.44 | ₪79 | 14.5% | ₪180 | 0.49 | below-floor |
| `pouf-cj-cotton-knit-ball-cover` | products.json | ₪99 | ₪179 | 1.81 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-53.37 | ₪169.26 | ₪179 | 4.9% | ₪450 | 0.4 | below-floor |
| `magazine-holder-cj-gunmetal-leather-strap` | products.json | ₪149 | ₪269 | 1.80 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-88.16 | ₪265.05 | ₪269 | 1.3% | ₪229 | 1.17 | above-market |
| `table-lamp-cj-pleated-shade-wood-column` | products.json | ₪149 | ₪269 | 1.80 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; המק"ט שבחדר | ₪-85.91 | ₪262.09 | ₪269 | 2.3% | ₪295 | 0.91 | below-floor |
| `dining-pendant-cj-black-ring-cloth-lantern-50` | products.json | ₪229 | ₪409 | 1.79 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; size=40 (נמכר ב-₪119) | ₪-134.74 | ₪406.37 | ₪359 | 11.8% | ₪420 | 0.97 | below-floor |
| `reed-diffuser-cj-travertine-look-bamboo-lid-milktea` | products.json | ₪39 | ₪69 | 1.77 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-21.30 | ₪67.04 | ₪69 | 2.5% | ₪144 | 0.48 | below-floor |
| `soap-dispenser-cj-matte-ceramic-cream-black-pump` | products.json | ₪39 | ₪69 | 1.77 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-19.03 | ₪64.05 | ₪69 | 6.4% | ₪120 | 0.57 | below-floor |
| `framed-art-aliexpress-japanese-wabi-sabi-tree-176323` | products.json | ₪39 | ₪69 | 1.77 | הסטודיו (aliexpress): AliExpress (card option) 6-15; 1 יח'; size=30x40 (נמכר ב-₪9) | ₪-16.11 | ₪63.21 | ₪49 | 32.3% | ₪95 | 0.73 | below-floor |
| `open-shelf-ceramics-cj-morandi-matte-bottle-set` | products.json | ₪79 | ₪139 | 1.76 | הסטודיו (cj): CJPacket Eub 12-50; 2 יח'; המק"ט שבחדר | ₪-39.13 | ₪135.65 | ₪139 | 5.5% | ₪270 | 0.51 | below-floor |
| `pool-cj-cotton-linen-box-camel-40x30` | products.json | ₪29 | ₪49 | 1.69 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-9.10 | ₪40.98 | ₪49 | 14.7% | ₪70 | 0.7 | below-floor |
| `bowl-cj-reactive-white-rimmed-plate-21` | products.json | ₪59 | ₪99 | 1.68 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; set=1pc, other=7.7-inches (נמכר ב-₪49) | ₪-24.14 | ₪90.77 | ₪89 | 10.0% | ₪139 | 0.71 | below-floor |
| `condiment-set-zendrop-wood-mills-black-white-21` | products.json | ₪59 | ₪99 | 1.68 | הסטודיו (zendrop): Zendrop regular 14; 1 יח'; set=black (נמכר ב-₪39) | ₪-25.76 | ₪92.91 | ₪89 | 10.2% | ₪140 | 0.71 | below-floor |
| `pendant-cj-fabric-dome-ash-cap-25` | products.json | ₪119 | ₪199 | 1.67 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-54.91 | ₪191.28 | ₪199 | 3.5% | ₪195 | 1.02 | above-market |
| `ceiling-light-cj-opal-glass-drum-flush-32` | products.json | ₪149 | ₪249 | 1.67 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-74.39 | ₪246.93 | ₪249 | 0.7% | ₪300 | 0.83 | below-floor |
| `curtains-aliexpress-cotton-linen-texture-translucent-091154` | products.json | ₪299 | ₪499 | 1.67 | הערות הכרטיס (הערכה); 2 יח'; set=1pc, width=100, length=250, style=pull_pleated, color=tulle (נמכר ב-₪9) | ₪-115.57 | ₪498.93 | ₪329 | 32.3% | ₪489 | 1.02 | above-market |
| `framed-art-cj-taupe-block-black-line-30x40` | products.json | ₪109 | ₪179 | 1.64 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-50.89 | ₪175.99 | ₪179 | 1.5% | ₪200 | 0.9 | below-floor |
| `wall-sconce-cj-black-swan-arm-white-fabric-cone` | products.json | ₪79 | ₪129 | 1.63 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=black, style=single-head, other=no-bulb-included (נמכר ב-₪69) | ₪-30.99 | ₪119.79 | ₪119 | 10.8% | ₪150 | 0.86 | below-floor |
| `bedding-cj-washed-polyester-set-milk-tea` | products.json | ₪99 | ₪159 | 1.61 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=gemstone-green, size=200x230-quilt-cover (נמכר ב-₪99) | ₪-41.26 | ₪153.32 | ₪149 | 5.7% | ₪210 | 0.76 | below-floor |
| `pendant-cj-pleated-pumpkin-lantern-40` | products.json | ₪299 | ₪469 | 1.57 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; size=28 (נמכר ב-₪239) | ₪-129.08 | ₪468.92 | ₪449 | 5.6% | ₪450 | 1.04 | above-market |
| `framed-art-cj-swinging-line-black-frame-mat-35x45` | products.json | ₪129 | ₪199 | 1.54 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-52.13 | ₪197.63 | ₪199 | 0.6% | ₪225 | 0.88 | below-floor |
| `framed-prints-cj-charcoal-line-black-frame-35x45` | products.json | ₪129 | ₪199 | 1.54 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-52.13 | ₪197.63 | ₪199 | 0.6% | ₪225 | 0.88 | below-floor |
| `candle-holders-aliexpress-matte-black-iron-pillar-set2` | products.json | ₪39 | ₪59 | 1.51 | מטמון AliExpress 3256811847480845 sku 12000057351444960 ×1: AliExpress Selection Standard 6-15; 1 יח'; המק"ט שבחדר | ₪-12.66 | ₪55.66 | ₪59 | 5.1% | ₪89 | 0.66 | below-floor |
| `wall-hooks-cj-raw-wood-cylinder-peg-set-of-4` | products.json | ₪39 | ₪59 | 1.51 | הסטודיו (cj): CJPacket Eub 12-50 (הוצע ל-4 יח'; נלקח ליחידת מכירה, כמו בסטודיו); 1 יח'; color=black-short (נמכר ב-₪39) | ₪-10.88 | ₪53.32 | ₪59 | 12.9% | ₪125 | 0.47 | below-floor |
| `picture-lights-cj-black-tube-rechargeable` | products.json | ₪59 | ₪89 | 1.51 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; other=touch-switch (נמכר ב-₪59) | ₪-17.23 | ₪81.68 | ₪89 | 8.5% | ₪125 | 0.71 | below-floor |
| `basket-cj-jute-rope-cylinder` | products.json | ₪79 | ₪119 | 1.51 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; other=small (נמכר ב-₪59) | ₪-28.45 | ₪116.45 | ₪109 | 9.0% | ₪179 | 0.66 | below-floor |
| `table-lamp-cj-white-teardrop-fabric-cone-25x45` | products.json | ₪99 | ₪149 | 1.50 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; size=16x34-black-small (נמכר ב-₪89) | ₪-33.71 | ₪143.38 | ₪149 | 5.3% | ₪190 | 0.78 | below-floor |
| `wall-sconce-cj-travertine-dome-15-pull` | products.json | ₪299 | ₪449 | 1.50 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; style=15cm-without-pull-switch, other=light-source-not-included (נמכר ב-₪289) | ₪-112.25 | ₪446.77 | ₪449 | 1.9% | ₪520 | 0.86 | below-floor |
| `sofa-cover-cj-polar-fleece-jacquard-slipcover` | products.json | ₪149 | ₪219 | 1.47 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=dark-gray, other=pillowcase (נמכר ב-₪49) | ₪-46.41 | ₪210.09 | ₪169 | 23.1% | ₪600 | 0.36 | below-floor |
| `basket-cj-cotton-rope-white` | products.json | ₪89 | ₪129 | 1.45 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=white, other=s (נמכר ב-₪69) | ₪-30.16 | ₪128.70 | ₪129 | 6.1% | ₪190 | 0.68 | below-floor |
| `curtains-aliexpress-cotton-linen-texture-translucent` | products.json | ₪299 | ₪429 | 1.44 | הערות הכרטיס (הערכה); 2 יח'; set=1pc, width=100, length=200, style=rod_pocket, color=yarn (נמכר ב-₪19) | ₪-72.73 | ₪428 | ₪299 | 33.2% | ₪489 | 0.88 | below-floor |
| `pool-cj-travertine-organic-tray-24` | products.json | ₪119 | ₪169 | 1.42 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-31.65 | ₪160.66 | ₪169 | 4.4% | ₪347 | 0.49 | below-floor |
| `bowl-aliexpress-kiln-corrugated-raw-rim-bowl-23` | leads | ₪119 | ₪169 | 1.42 | הסטודיו (leads): מהליקוט 6-15; 1 יח'; color=brown-kiln-spoon (נמכר ב-₪9) | ₪-30.53 | ₪161.11 | ₪119 | 32.8% | ₪139 | 1.22 | above-market |
| `ceiling-lights-cj-silk-cocoon-flush-40` | products.json | ₪219 | ₪309 | 1.41 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-68.34 | ₪308.96 | ₪309 | 0.0% | ₪420 | 0.74 | below-floor |
| `vanity-sconces-cj-ip65-mini-updown-white` | products.json | ₪49 | ₪69 | 1.41 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-13.38 | ₪66.61 | ₪69 | 3.1% | ₪220 | 0.31 | below-floor |
| `condiment-set-cj-rubberwood-mill-pair-6in` | products.json | ₪49 | ₪69 | 1.41 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-11.69 | ₪64.39 | ₪69 | 6.0% | ₪130 | 0.53 | below-floor |
| `wall-sconce-cj-black-folding-arm-woodgrain-cone-18` | products.json | ₪99 | ₪139 | 1.40 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=the-pattern-of-walnut, other=white-light (נמכר ב-₪79) | ₪-22.96 | ₪129.23 | ₪119 | 13.2% | ₪195 | 0.71 | below-floor |
| `wall-sconce-cj-wavy-linen-flush-25` | products.json | ₪149 | ₪209 | 1.40 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-39.81 | ₪201.41 | ₪209 | 3.3% | ₪299 | 0.7 | below-floor |
| `ceiling-light-cj-waxwood-dome-ash-40` | products.json | ₪199 | ₪279 | 1.40 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=white-light, size=small (נמכר ב-₪169) | ₪-58.57 | ₪276.11 | ₪269 | 5.7% | ₪420 | 0.66 | below-floor |
| `vase-cj-french-matte-white-35` | products.json | ₪229 | ₪319 | 1.39 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-66.03 | ₪315.91 | ₪319 | 0.9% | ₪589 | 0.54 | below-floor |
| `magazine-holder-cj-arch-iron-cane` | products.json | ₪129 | ₪179 | 1.39 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-34.54 | ₪174.47 | ₪179 | 2.3% | ₪229 | 0.78 | below-floor |
| `cushions-aliexpress-textured-boucle-throw-pillow` | products.json | ₪59 | ₪79 | 1.34 | מטמון AliExpress 3256806985105007 sku 12000059524978165 ×1: AliExpress Selection Standard 6-15; 1 יח'; size=30x50, color=beige (נמכר ב-₪39) | ₪-7.64 | ₪69.06 | ₪59 | 23.0% | ₪239 | 0.33 | below-floor |
| `wall-decor-zendrop-macrame-diamond-dowel-small` | products.json | ₪59 | ₪79 | 1.34 | הסטודיו (zendrop): Zendrop regular 14; 1 יח'; המק"ט שבחדר | ₪-11.69 | ₪74.39 | ₪79 | 5.2% | ₪249 | 0.32 | below-floor |
| `cushions-cj-dusty-pink-corduroy-patchwork-45` | products.json | ₪59 | ₪79 | 1.34 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-8.75 | ₪70.52 | ₪79 | 9.6% | ₪199 | 0.4 | below-floor |
| `basket-cj-seagrass-belly` | products.json | ₪89 | ₪119 | 1.34 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=original, other=a (נמכר ב-₪39) | ₪-19.06 | ₪114.09 | ₪99 | 20.6% | ₪190 | 0.63 | below-floor |
| `planter-cj-seagrass-belly` | products.json | ₪89 | ₪119 | 1.34 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=original, other=a (נמכר ב-₪39) | ₪-19.06 | ₪114.09 | ₪99 | 20.6% | ₪190 | 0.63 | below-floor |
| `wall-hooks-cj-light-wood-rail-5-brass-pegs-58` | products.json | ₪89 | ₪119 | 1.34 | הסטודיו (cj): CJPacket Liquid Line 9-23; 1 יח'; other=blackwalnut-2hooks (נמכר ב-₪59) | ₪-17.13 | ₪111.55 | ₪99 | 17.0% | ₪175 | 0.68 | below-floor |
| `pendant-cj-tiered-fabric-drum` | products.json | ₪329 | ₪429 | 1.30 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-74.94 | ₪427.64 | ₪429 | 0.3% | ₪460 | 0.93 | below-floor |
| `vase-cj-faceted-cream` | products.json | ₪199 | ₪259 | 1.30 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; size=small (נמכר ב-₪109) | ₪-44.65 | ₪257.78 | ₪219 | 14.4% | ₪479 | 0.54 | below-floor |
| `vanity-vase-aliexpress-sand-oat-bud-vase-g-series` | leads | ₪69 | ₪89 | 1.29 | הסטודיו (leads): מהליקוט 6-15; 1 יח'; color=b1a (נמכר ב-₪29) | ₪-11.01 | ₪83.50 | ₪69 | 26.4% | ₪79 | 1.13 | above-market |
| `sofa-cover-cj-waffle-jacquard-stretch-slipcover` | products.json | ₪149 | ₪189 | 1.27 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; style=s-single, other=grass-green (נמכר ב-₪89) | ₪-27.18 | ₪184.78 | ₪159 | 15.1% | ₪600 | 0.32 | below-floor |
| `planter-cj-cement-ribbed-belly` | products.json | ₪229 | ₪289 | 1.26 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=grey, size=small (נמכר ב-₪59) | ₪-42.94 | ₪285.52 | ₪229 | 24.8% | ₪360 | 0.8 | below-floor |
| `canisters-zendrop-matte-ceramic-bamboo-lid-sml` | products.json | ₪89 | ₪109 | 1.23 | הסטודיו (zendrop): Zendrop regular 14; 1 יח'; המק"ט שבחדר | ₪-11.60 | ₪104.27 | ₪109 | 3.9% | ₪180 | 0.61 | below-floor |
| `sill-vase-cj-cream-fluted-column-25` | products.json | ₪49 | ₪59 | 1.20 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; other=evening-snow-arrives (נמכר ב-₪39) | ₪-6.45 | ₪57.50 | ₪59 | 9.5% | ₪295 | 0.2 | below-floor |
| `vase-cj-matte-moon-jar-white` | products.json | ₪149 | ₪179 | 1.20 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; style=styled (נמכר ב-₪119) | ₪-18.25 | ₪173.02 | ₪159 | 10.4% | ₪269 | 0.67 | below-floor |
| `vase-cj-white-textured-jar` | products.json | ₪149 | ₪179 | 1.20 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-19.48 | ₪174.65 | ₪179 | 2.2% | ₪269 | 0.67 | below-floor |
| `table-lamp-cj-white-textured-ceramic-linen-drum` | products.json | ₪199 | ₪239 | 1.20 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-23.05 | ₪229.34 | ₪239 | 3.6% | ₪295 | 0.81 | below-floor |
| `floor-lamp-aliexpress-pleated-walnut-37x158-062736` | leads | ₪949 | ₪1,129 | 1.19 | הסטודיו (card): המק"ט שבחדר 15-26; 1 יח'; size=b-d39.5cm-h51cm, other=warm-light (נמכר ב-₪299) | ₪-135.61 | ₪1,127.51 | ₪949 | 23.2% | ₪1,395 | 0.81 | below-floor |
| `floor-lamp-aliexpress-pleated-walnut-37x158-062736-master` | leads | ₪949 | ₪1,129 | 1.19 | הסטודיו (card): המק"ט שבחדר 15-26; 1 יח'; size=b-d39.5cm-h51cm, other=warm-light (נמכר ב-₪299) | ₪-135.61 | ₪1,127.51 | ₪949 | 23.2% | ₪1,395 | 0.81 | below-floor |
| `magazine-holder-cj-felt-snap-bucket` | products.json | ₪59 | ₪69 | 1.17 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=black-without-lining, size=30x42-medium (נמכר ב-₪49) | ₪-0.18 | ₪59.23 | ₪59 | 25.2% | ₪130 | 0.53 | below-floor |
| `ceiling-lights-cj-pleated-fabric-saucer-flush-50` | products.json | ₪499 | ₪569 | 1.14 | הסטודיו (cj): CJPacket Eub 12-50; 2 יח'; המק"ט שבחדר | ₪-47.76 | ₪561.87 | ₪569 | 1.1% | ₪900 | 0.63 | below-floor |
| `throw-cj-cotton-waffle-ruffle-khaki-150x200` | products.json | ₪149 | ₪169 | 1.13 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=grey, size=100x150 (נמכר ב-₪99) | ₪-8.89 | ₪160.70 | ₪149 | 16.5% | ₪399 | 0.42 | below-floor |
| `sofa-cover-cj-washed-hemp-throw` | products.json | ₪229 | ₪259 | 1.13 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; size=100x150, other=mustard-yellow (נמכר ב-₪139) | ₪-21.54 | ₪257.35 | ₪229 | 14.3% | ₪479 | 0.54 | below-floor |
| `vanity-sconces-cj-fluted-resin-updown-white` | products.json | ₪229 | ₪259 | 1.13 | הסטודיו (cj): CJPacket Sensitive 22-27; 2 יח'; color=white, other=tricolor-light-source (נמכר ב-₪219) | ₪-20.82 | ₪256.41 | ₪259 | 1.9% | ₪440 | 0.59 | below-floor |
| `skateboard-cj-blank-maple-43` | products.json | ₪79 | ₪89 | 1.13 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-5.64 | ₪86.42 | ₪89 | 2.6% | ₪149 | 0.6 | below-floor |
| `bedside-sconces-cj-linen-half-drum-black-trim` | products.json | ₪349 | ₪389 | 1.11 | הסטודיו (cj): CJPacket Eub 12-50; 2 יח'; המק"ט שבחדר | ₪-27.40 | ₪385.07 | ₪389 | 0.9% | ₪598 | 0.65 | below-floor |
| `bench-pad-aliexpress-linen-look-box-cushion-130x35x5` | leads | ₪269 | ₪299 | 1.11 | הסטודיו (card): המק"ט שבחדר 18-29; 1 יח'; color=color-10-rice-gray, size=35x35x5 (נמכר ב-₪89) | ₪-17.81 | ₪292.44 | ₪269 | 26.0% | ₪290 | 1.03 | above-market |
| `paper-towel-holder-aliexpress-slotted-wood-round-base-31` | card | ₪89 | ₪99 | 1.11 | הסטודיו (leads): מהליקוט 6-15; 1 יח'; style=style-1 (נמכר ב-₪49) | ₪-5.42 | ₪96.14 | ₪89 | 18.6% | — | — | below-floor |
| `bench-pad-aliexpress-double-piping-cushion-130x35x5` | leads | ₪289 | ₪319 | 1.10 | הסטודיו (leads): מהליקוט 18-29; 1 יח'; color=sg-6-light-gray, size=60x30x5 (נמכר ב-₪109) | ₪-21.36 | ₪317.11 | ₪289 | 23.6% | ₪290 | 1.1 | above-market |
| `vase-cj-charcoal-carved` | products.json | ₪199 | ₪219 | 1.10 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; style=style-a (נמכר ב-₪169) | ₪-14.52 | ₪218.11 | ₪219 | 3.8% | ₪479 | 0.46 | below-floor |
| `centerpiece-vase-aliexpress-nordic-morandi-matte-ceramic` | products.json | ₪199 | ₪219 | 1.10 | קובץ התמחור:  (הערכה); 1 יח'; set=3pc, style=e (נמכר ב-₪169) | ₪-13.20 | ₪216.38 | ₪209 | 6.8% | ₪400 | 0.55 | below-floor |
| `nightstand-tray-aliexpress-acacia-rect-tray-30x20` | card | ₪99 | ₪109 | 1.10 | הסטודיו (leads): מהליקוט 6-15; 1 יח'; size=20 (נמכר ב-₪39) | ₪-6.72 | ₪107.84 | ₪99 | 23.2% | — | — | below-floor |
| `table-runner-aliexpress-open-weave-linen-runner` | leads | ₪99 | ₪109 | 1.10 | הסטודיו (card): המק"ט שבחדר 20-27; 1 יח'; color=tea-green, size=20x60 (נמכר ב-₪59) | ₪-4.92 | ₪105.48 | ₪99 | 20.2% | ₪129.90 | 0.84 | below-floor |
| `open-shelf-ceramics-cj-patina-clay-pitcher-and-jar` | products.json | ₪229 | ₪249 | 1.09 | ידני (data/economics/products.json shipping_cost_usd); 1 יח'; other=sy-c03d137 (נמכר ב-₪159) | ₪-8.59 | ₪240.30 | ₪229 | 14.8% | ₪240 | 1.04 | above-market |
| `pool-cj-wabi-sabi-floor-vase-white` | products.json | ₪349 | ₪379 | 1.09 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-19.61 | ₪374.82 | ₪379 | 1.0% | ₪835 | 0.45 | below-floor |
| `toilet-brush-aliexpress-striped-ceramic-holder-165620` | card | ₪119 | ₪129 | 1.08 | הסטודיו (card): המק"ט שבחדר 8-18; 1 יח'; color=elephant-white (נמכר ב-₪79) | ₪-2.24 | ₪121.94 | ₪119 | 20.7% | — | — | below-floor |
| `bench-cushion-aliexpress-linen-look-box-cushion-110x35x5` | leads | ₪249 | ₪269 | 1.08 | הסטודיו (leads): מהליקוט 18-29; 1 יח'; color=color-10-rice-gray, size=35x35x5 (נמכר ב-₪99) | ₪-10.21 | ₪262.44 | ₪249 | 24.1% | ₪290 | 0.93 | below-floor |
| `bowl-aliexpress-pearl-rim-ingot-bowl-23` | leads | ₪129 | ₪139 | 1.08 | הסטודיו (leads): מהליקוט 6-15; 1 יח'; color=dessert-bowl-small (נמכר ב-₪69) | ₪-6.07 | ₪136.99 | ₪129 | 17.1% | ₪139 | 1.0 | below-floor |
| `bench-cushion-aliexpress-double-piping-cushion-110x35x5` | leads | ₪259 | ₪279 | 1.08 | הסטודיו (leads): מהליקוט 18-29; 1 יח'; color=sg-6-light-gray, size=60x30x5 (נמכר ב-₪119) | ₪-13.76 | ₪277.11 | ₪259 | 22.1% | ₪290 | 0.96 | below-floor |
| `pendant-cj-fluted-ceramic-wood-cap-short-lantern` | products.json | ₪149 | ₪159 | 1.07 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; style=short-lantern-style, other=without-customs-source (נמכר ב-₪139) | ₪-5.53 | ₪156.28 | ₪159 | 3.5% | ₪315 | 0.5 | below-floor |
| `bedding-aliexpress-boho-3d-tufted-cut-500672` | products.json | ₪349 | ₪369 | 1.06 | הסטודיו (aliexpress): AliExpress (card option) 9-23; 1 יח'; size=eu-single-size-2-pcs (נמכר ב-₪169) | ₪-11.12 | ₪363.64 | ₪349 | 20.7% | ₪425 | 0.87 | below-floor |
| `vase-cj-white-plum-hand-thrown` | products.json | ₪229 | ₪239 | 1.04 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר | ₪-4.18 | ₪234.51 | ₪239 | 1.7% | ₪479 | 0.5 | below-floor |
| `mug-set-aliexpress-oat-matte-cup-acacia-saucer-573382` | card | ₪229 | ₪239 | 1.04 | מטמון AliExpress 1005010036573382 sku 12000050905930710 ×1: AliExpress Selection Standard 6-13; 1 יח'; המק"ט שבחדר (נמכר ב-₪79) | ₪-0.42 | ₪229.57 | ₪229 | 7.8% | ₪237 | 1.01 | above-market |

## יקר מהשוק

28 מוצרים: המחיר שלא מפסיד מעל ההשוואה הישראלית הגבוהה. מסומנים `above-market` (הסטודיו עוד לא מציג תווית כזו).

| מוצר | נוכחי | מוצע | השוואה גבוהה | יחס | התרחיש הגרוע |
| --- | --- | --- | --- | --- | --- |
| `floor-lamp-cj-cream-arc-pleated-152` | ₪349 | ₪3,529 | ₪651 | פי 5.42 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; המק"ט שבחדר |
| `wall-sconce-cj-black-swing-arm-wood-shade` | ₪119 | ₪429 | ₪195 | פי 2.2 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; המק"ט שבחדר |
| `tableware-set-cj-grey-sand-matte-plate` | ₪19 | ₪109 | ₪50 | פי 2.18 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; size=10inch (נמכר ב-₪9) |
| `candle-holders-aliexpress-black-lava-stone-candle-holders` | ₪289 | ₪289 | ₪155 | פי 1.86 | הסטודיו (card): המק"ט שבחדר 8-15; 1 יח'; המק"ט שבחדר |
| `wall-sconce-cj-black-swing-arm-fabric` | ₪149 | ₪519 | ₪293 | פי 1.77 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; המק"ט שבחדר |
| `mug-set-cj-cream-matte-breakfast-cup` | ₪39 | ₪149 | ₪90 | פי 1.66 | הסטודיו (cj): CJPacket Eub 12-50; 3 יח'; המק"ט שבחדר |
| `mug-set-cj-oat-speckled-round-mug-wood-saucer` | ₪19 | ₪89 | ₪60 | פי 1.48 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר |
| `bookshelf-cj-natural-wood-ledge-pair-42-x2` | ₪219 | ₪219 | ₪158 | פי 1.39 | מטמון CJ vid 2410141005261605600 ×1: CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר (נמכר ב-₪119) |
| `floor-lamp-cj-pleated-walnut-stem-158` | ₪349 | ₪829 | ₪651 | פי 1.27 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; other=3-colortable-lamp (נמכר ב-₪229) |
| `accent-sconces-aliexpress-indoor-stone-wall-lamp` | ₪299 | ₪649 | ₪520 | פי 1.25 | מטמון AliExpress 3256807415537790 sku 12000043242375290 ×1: AliExpress standard shipping 22-32; 2 יח'; המק"ט שבחדר |
| `tableware-set-cj-speckled-oat-stoneware-bowl-13` | ₪29 | ₪99 | ₪80 | פי 1.24 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר |
| `bowl-aliexpress-kiln-corrugated-raw-rim-bowl-23` | ₪119 | ₪169 | ₪139 | פי 1.22 | הסטודיו (leads): מהליקוט 6-15; 1 יח'; color=brown-kiln-spoon (נמכר ב-₪9) |
| `magazine-holder-cj-gunmetal-leather-strap` | ₪149 | ₪269 | ₪229 | פי 1.17 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר |
| `framed-art-aliexpress-retro-farmhouse-chicken-botanical-333603` | ₪89 | ₪229 | ₪200 | פי 1.15 | הסטודיו (aliexpress): AliExpress Selection Standard 6-15; 1 יח'; size=21x30-black-framed (נמכר ב-₪19) |
| `framed-art-aliexpress-minimal-geometric-triptych-prints` | ₪199 | ₪199 | ₪175 | פי 1.14 | הסטודיו (leads): מהליקוט 6-13 (ל-3 יח'); 1 יח'; color=2, size=20x30-unframed (נמכר ב-₪39) |
| `vanity-vase-aliexpress-sand-oat-bud-vase-g-series` | ₪69 | ₪89 | ₪79 | פי 1.13 | הסטודיו (leads): מהליקוט 6-15; 1 יח'; color=b1a (נמכר ב-₪29) |
| `candle-holders-aliexpress-cutelife-black-ceramic-candelabra` | ₪39 | ₪139 | ₪125 | פי 1.11 | מטמון AliExpress 3256811647185429 sku 12000056728690425 ×1: AliExpress Selection Standard 6-15; 1 יח'; color=white, set=1pc (נמכר ב-₪19) |
| `bench-pad-cj-tufted-long-cushion-khaki-120` | ₪59 | ₪149 | ₪135 | פי 1.1 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; color=black, size=130x50x8 (נמכר ב-₪49) |
| `bench-pad-aliexpress-double-piping-cushion-130x35x5` | ₪289 | ₪319 | ₪290 | פי 1.1 | הסטודיו (leads): מהליקוט 18-29; 1 יח'; color=sg-6-light-gray, size=60x30x5 (נמכר ב-₪109) |
| `framed-art-cj-line-scribble-white-mat-50` | ₪129 | ₪239 | ₪225 | פי 1.06 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; style=a, size=30x30 (נמכר ב-₪89) |
| `bath-mat-cj-solid-wood-slatted-61x45` | ₪129 | ₪419 | ₪399 | פי 1.05 | הסטודיו (cj): CJPacket Sensitive 22-27; 1 יח'; המק"ט שבחדר |
| `pendant-cj-pleated-pumpkin-lantern-40` | ₪299 | ₪469 | ₪450 | פי 1.04 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; size=28 (נמכר ב-₪239) |
| `open-shelf-ceramics-cj-patina-clay-pitcher-and-jar` | ₪229 | ₪249 | ₪240 | פי 1.04 | ידני (data/economics/products.json shipping_cost_usd); 1 יח'; other=sy-c03d137 (נמכר ב-₪159) |
| `bench-pad-aliexpress-linen-look-box-cushion-130x35x5` | ₪269 | ₪299 | ₪290 | פי 1.03 | הסטודיו (card): המק"ט שבחדר 18-29; 1 יח'; color=color-10-rice-gray, size=35x35x5 (נמכר ב-₪89) |
| `curtains-aliexpress-cotton-linen-texture-translucent-091154` | ₪299 | ₪499 | ₪489 | פי 1.02 | הערות הכרטיס (הערכה); 2 יח'; set=1pc, width=100, length=250, style=pull_pleated, color=tulle (נמכר ב-₪9) |
| `pendant-cj-fabric-dome-ash-cap-25` | ₪119 | ₪199 | ₪195 | פי 1.02 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; המק"ט שבחדר |
| `centerpiece-vase-cj-sandy-white-bead-band-25` | ₪59 | ₪299 | ₪295 | פי 1.01 | הסטודיו (cj): CJPacket Eub 12-50; 1 יח'; other=2345-white (נמכר ב-₪29) |
| `mug-set-aliexpress-oat-matte-cup-acacia-saucer-573382` | ₪229 | ₪239 | ₪237 | פי 1.01 | מטמון AliExpress 1005010036573382 sku 12000050905930710 ×1: AliExpress Selection Standard 6-13; 1 יח'; המק"ט שבחדר (נמכר ב-₪79) |

## אקספרס בלבד

לספק אין שיטה רגילה למוצר: המשלוח היחיד הוא To Door, DHL או FedEx. לא מוצעת העלאה; המחיר שלא מפסיד כאן הוא במשלוח האקספרס היחיד, להחלטת המנהל (להציע עם משלוח בנפרד, לסמן "המלאי אינו זמין כעת", או לחפש רישום אחר).

| מוצר | נוכחי | השיטה היחידה | משלוח למכירה | מפסיד היום | מחיר שלא מפסיד באקספרס | השוואה גבוהה | יחס |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `framed-art-cj-morandi-triptych-sage` | ₪379 | הסטודיו (cj): CJPacket To Door 11-18 | $130.82 | כן | ₪659 | ₪980 | 0.67 |
| `rug-cj-braided-wool-natural` | ₪1,299 | הסטודיו (cj): DHL Official 3-7 | $491.08 | כן | ₪4,099 | ₪2,700 | 1.52 |
| `bedding-cj-cotton-linen-duvet-beige` | ₪479 | הסטודיו (cj): CJPacket To Door 11-18 | $107.99 | כן | ₪1,139 | ₪1,080 | 1.05 |
| `pendant-cj-wabi-pleated-fabric-lantern-50` | ₪299 | הסטודיו (cj): CJPacket To Door 11-18 | $340.29 | כן | ₪1,739 | ₪420 | 4.14 |
| `roman-blind-aliexpress-customized-flat-sheer-roman-221993` | — | מטמון AliExpress 1005008958221993 sku 12000047368507416 ×1: DHL 18-30 (חינם) | $0 | אין מחיר | ₪189 | — | — |
| `roman-blind-aliexpress-modern-beige-color-flat-868827` | — | מטמון AliExpress 1005012057868827 sku 12000057392721266 ×1: Fedex IP 19-35 (חינם) | $0 | אין מחיר | ₪189 | — | — |

## מחיר שהמשתמש קבע ומפסיד (לא שונה; NL1)

- `cushions-aliexpress-fashion-modern-wabi-sabi-464203` ב-₪69 (Studio db product_edits/cushions-aliexpress-fashion-modern-wabi-sabi-464203.json (synced 2026-10-13)). התרחיש הגרוע: הסטודיו (aliexpress): AliExpress Selection Standard 6-15; 1 יח'; color=1pcs-beige, size=30x50 (נמכר ב-₪49), תרומה ₪-8.56. **המחיר שלא מפסיד: ₪89** (נקודת איזון ₪80.27); במק"ט שבחדר בלבד: ₪69. אם יועלה: דגל below-floor, פי 0.37 מההשוואה הגבוהה (₪239). להחלטת המשתמש.

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

כרטיסים שנספרים בכיסוי ואין להם מחיר בשום מקום (130): המחיר שלא מפסיד לכל אחד ב-JSON (`no_price`), כרצפה למחיר התחלה. לא נכתב מחיר.

## מוצרים מעל ₪247

- $75 × 3.3: תקרת הפטור ממע"מ ביבוא אישי (docs/tax/README.md). מעל הסף הלקוח עלול לשלם מע"מ ועמלת שחרור בדלת (VAT1 פתוחה).
- שורות products.json: **35 לפני → 53 אחרי** (מתוך 181).
- כל המוצרים עם מחיר (324): **95 לפני → 113 אחרי**.
- חוצים את הסף בגלל ההעלאה (18): `bath-mat-cj-solid-wood-slatted-61x45`, `ceiling-light-cj-opal-glass-drum-flush-32`, `ceiling-light-cj-waxwood-dome-ash-40`, `ceiling-lights-cj-silk-cocoon-flush-40`, `centerpiece-vase-cj-sandy-white-bead-band-25`, `dining-pendant-cj-black-ring-cloth-lantern-50`, `magazine-holder-cj-gunmetal-leather-strap`, `open-shelf-ceramics-cj-patina-clay-pitcher-and-jar`, `planter-cj-cement-ribbed-belly`, `sofa-cover-cj-bubble-stretch-slipcover`, `sofa-cover-cj-washed-hemp-throw`, `table-lamp-cj-pleated-shade-wood-column`, `vanity-sconces-cj-fluted-resin-updown-white`, `vase-cj-faceted-cream`, `vase-cj-french-matte-white-35`, `wall-sconce-cj-black-swing-arm-fabric`, `wall-sconce-cj-black-swing-arm-wood-shade`, `wall-sconce-cj-white-fabric-cube-15`.
- 'אחרי' = המחירים המוצעים; מחיר המשתמש ומוצרי אקספרס-בלבד נשארים במחירם הנוכחי.

## כמות המכירה: בדיקות

במוצרים האלה הסטודיו קרא את מספר היחידות במכירה מעלות הנחיתה שברשומה (studio/build.py lead_qty), לא משדה כמות, או שהמחיר בקובץ התמחור הוא לכמות אחרת מזו שהסטודיו מוכר (`price-qty-mismatch`). המחיר נבדק לפי הכמות שהסטודיו מוכר, חוץ ממנורת המטבח (תיקון 3: יחידה אחת). העמודה האחרונה: המחיר שלא מפסיד אילו המכירה הייתה יחידה אחת.

| מוצר | יח' בסטודיו | יח' בדוח | נוכחי | מוצע | אם יחידה אחת | סימון |
| --- | --- | --- | --- | --- | --- | --- |
| `accent-sconces-aliexpress-indoor-stone-wall-lamp` | 2 | 2 | ₪299 | ₪649 | — | price-qty-mismatch |
| `wall-sconce-cj-white-fabric-cube-15` | 2 | 2 | ₪99 | ₪299 | — | price-qty-mismatch |
| `accent-sconces-aliexpress-fluted-white-ceramic-tulip-wall-sconce-on` | 2 | 2 | ₪999 | ₪999 | ₪299 | qty-inferred-from-landed |
| `accent-sconces-aliexpress-scalloped-white-ceramic-flower-wall-sconce-on` | 2 | 2 | ₪649 | ₪649 | ₪209 | qty-inferred-from-landed |
| `cutting-boards-cj-black-walnut-paddle-pair-39-34` | 2 | 2 | ₪279 | ₪279 | ₪169 | qty-inferred-from-landed |
| `framed-art-aliexpress-japandi-bare-branch-70x100-776445` | 2 | 2 | ₪349 | ₪349 | ₪129 | qty-inferred-from-landed |
| `framed-art-aliexpress-minimal-geometric-triptych-prints` | 3 | 3 | ₪199 | ₪199 | ₪69 | qty-inferred-from-landed |
| `framed-prints-aliexpress-watercolour-bunny-nursery-prints` | 2 | 2 | ₪119 | ₪119 | ₪49 | qty-inferred-from-landed |
| `framed-prints-aliexpress-watercolour-sun-and-rainbow-nursery-prints` | 2 | 2 | ₪119 | ₪119 | ₪49 | qty-inferred-from-landed |
| `kitchen-sconce-aliexpress-rustic-wooden-wall-sconce-632957` | 4 | 1 | ₪229 | ₪229 | יחידה אחת בדוח | qty-inferred-from-landed, unit-override |
| `shelf-boxes-aliexpress-seagrass-lidded-box-32x22-pair` | 2 | 2 | ₪219 | ₪219 | ₪99 | qty-inferred-from-landed |
| `shelf-boxes-cj-felt-storage-bin-30x24-pair` | 2 | 2 | ₪63 | ₪63 | ₪49 | qty-inferred-from-landed |
| `shelf-boxes-cj-lined-straw-basket-28x21x17-pair` | 2 | 2 | ₪149 | ₪149 | ₪79 | qty-inferred-from-landed |
| `toy-cars-aliexpress-wooden-toys-beech-wood-138166` | 3 | 3 | ₪159 | ₪159 | ₪59 | qty-inferred-from-landed |
| `vanity-sconces-aliexpress-wabi-sabi-yellow-marble-037853` | 2 | 2 | ₪659 | ₪659 | ₪309 | qty-inferred-from-landed |
| `shelf-boxes-cj-two-tone-fabric-bin-27x20x12-pair` | 2 | 2 | ₪63 | ₪63 | ₪49 | qty-inferred-from-landed |

## קלטים מוערכים וסימונים

- `qty-freight-estimated`: 30 מוצרים
- `freight-from-cache-only`: 26 מוצרים
- `options-with-sale-cost`: 17 מוצרים
- `qty-inferred-from-landed`: 14 מוצרים
- `freight-estimated`: 8 מוצרים
- `freight-missing`: 8 מוצרים
- `freight-from-other-sku`: 6 מוצרים
- `express-only`: 6 מוצרים
- `sale-cost-from-leads`: 6 מוצרים
- `options-are-set-parts`: 4 מוצרים
- `row-margin-differs`: 3 מוצרים
- `price-qty-mismatch`: 2 מוצרים
- `cost-not-usd`: 1 מוצרים
- `no-route`: 1 מוצרים
- `freight-quote-other-qty`: 1 מוצרים
- `unit-override`: 1 מוצרים

freight-estimated = אין הצעת משלוח, נלקחה ההערכה הגבוהה; qty-freight-estimated = משלוח לכמה יחידות לפי נוסחת החבילה המשולבת; freight-from-other-sku = המשלוח נמדד על מק"ט אחר; freight-from-cache-only = לסטודיו אין משלוח, נלקח ממטמון הספק; freight-quote-other-qty = ההצעה לכמות אחרת, תורגמה ליחידה; qty-inferred-from-landed = הכמות הוסקה מעלות הנחיתה; unit-override = כמות שהמנהל קבע; price-qty-mismatch = המחיר בקובץ לכמות אחרת מהמכירה; sale-cost-from-leads = עלות המכירה מהרשומה (בהחלה צריך שורה ב-products.json עם sale_cost_usd); options-are-set-parts = האפשרויות הן חלקי הסט, לא וריאנטים; express-only = רק אקספרס; no-route = הספק לא שולח לישראל; cost-not-usd = העלות לא בדולר.

## מועמדים שנדחו רק בגלל הפסד (סבבים 5 ו-6, התאמה 7+)

נקראו 105 מועמדים בלי כרטיס שהרשומה שלהם מפסידה; **51 נדחו רק בגלל ההפסד**. כל מועמד בלי כרטיס בהתאמה 7+ שהרשומה שלו מפסידה נקרא ידנית: 'in' רק כשההפסד הוא סיבת הדחייה היחידה. המשלוח: שיטת ברירת המחדל מהמטמון של הספק (המק"ט שברשומה, אחרת הגרוע מבין המק"טים), בחבילה משולבת לכמות; בלי מטמון, המשלוח שברשומה. הרווח בכיסוי מחושב בכלל של final_round_coverage.py (פונקציות הסקריפט, בלי לכתוב קובץ), כאילו לכל מועמד יש כרטיס באפשרות אחת (צבע אחד) בסגנונות שבהם ההתאמה 7+. דיווח בלבד: לא שונה אף קובץ תוצאות ולא סקריפט הכיסוי. להחלטת המשתמש.

| עמדה | מוצר | סגנונות 7+ | יח' | משלוח (שיטה) | נחיתה | נקודת איזון | מחיר שלא מפסיד | השוואה גבוהה | יחס | הערה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bath/bath-towels | AliExpress 1005012773111382 | nordic 7, warm-modern 7, japandi 8, mediterranean 7, modern-country 7 | 1 | $2.5 (AliExpress Selection Standard 6-13) | ₪147.15 | ₪195.28 | ₪199 | ₪279.80 | 0.71 | זוג; נדחה כי המחיר שלא מפסיד מעל ההשוואה (בדיוק מה שהכלל החדש מתיר) |
| bath/ledge-planter | AliExpress 1005005532674549 | japandi 8, boho 7 | 1 | $1.99 (AliExpress Selection Standard 6-13) | ₪139.52 | ₪185.24 | ₪189 | ₪90 | 2.1 | מעטפת גבולית (גובה 10, לבדוק בפריים) |
| bath/toilet-brush | AliExpress 1005009105041173 | mediterranean 7, boho 7 | 1 | $11.53 (AliExpress standard shipping 8-15) | ₪134 | ₪177.97 | ₪179 | ₪120 | 1.49 | מעטפת גבולית (11×40) |
| bath/toilet-brush | AliExpress 1005009768828838 | mediterranean 7, boho 7 | 1 | $14.87 (AliExpress standard shipping 22-29) | ₪129.60 | ₪172.18 | ₪179 | ₪120 | 1.49 | מעטפת גבולית; משלוח 22–29 יום |
| bath/toilet-brush | AliExpress 1005012951198712 | mediterranean 7, boho 7 | 1 | $0 (AliExpress standard shipping 8-15) | ₪222.39 | ₪294.33 | ₪299 | ₪90 | 3.32 | מעטפת גבולית |
| bath/toothbrush-cup | AliExpress 1005012763561649 | modern-country 8 | 1 | $1.99 (AliExpress Selection Standard 6-11) | ₪51.28 | ₪69.08 | ₪79 | ₪59.90 | 1.32 |  |
| corridor/ceiling-lights | AliExpress 1005008258911244 | modern-country 7 | 2 | $58.94 (China Post Air Parcel 15-52; ברשומה $31.33) | ₪642.91 | ₪847.90 | ₪849 | ₪864 | 0.98 | זוג; 2 × ₪432 |
| corridor/ceiling-lights | AliExpress 1005012943662628 | japandi 7 | 1 | $103.38 (China Post Air Parcel 10-40) | ₪925.85 | ₪1,220.35 | ₪1,229 | ₪1,164 | 1.06 | זוג; 2 × ₪582 |
| corridor/ceiling-lights | AliExpress 1005009553503527 | warm-modern 7 | 1 | $0 (AliExpress standard shipping 7-15) | ₪1,313.80 | ₪1,731.04 | ₪1,739 | ₪1,164 | 1.49 | זוג; 2 × ₪582; מעטפת גבולית |
| corridor/ceiling-lights | AliExpress 1005010338870714 | modern-country 7.5 | 1 | $266.42 (AliExpress standard shipping 7-18) | ₪2,250.70 | ₪2,964.35 | ₪2,969 | ₪749 | 3.96 | משלוח $266, 15 ק"ג |
| corridor/gallery-stool | AliExpress 1005007997798374 | warm-modern 8, japandi 8, boho 7 | 1 | $0 (China Post Air Parcel 5-35) | ₪837.84 | ₪1,104.49 | ₪1,109 | ₪990 | 1.12 | מעטפת גבולית (32) |
| corridor/gallery-stool | AliExpress 1005013193019065 | nordic 7, japandi 7, mediterranean 7, boho 7 | 1 | $135.51 (AliExpress standard shipping 8-15) | ₪788 | ₪1,038.88 | ₪1,039 | ₪450 | 2.31 | מעטפת גבולית (32, לבדוק בפריים) |
| corridor/gallery-stool | AliExpress 1005012957725537 | modern-country 7, boho 7 | 1 | $0 (הרשומה (ship_usd למכירה)) | ₪930.60 | ₪1,226.60 | ₪1,229 | ₪530 | 2.32 | מעטפת גבולית |
| corridor/gallery-stool | AliExpress 1005009998944410 | modern-country 7, boho 7 | 1 | $85 (הרשומה (ship_usd למכירה)) | ₪377.40 | ₪498.38 | ₪499 | ₪150 | 3.33 | משלוח מוערך (~$85 ל-4 ק"ג), אין הצעה במטמון |
| corridor/gallery-stool | AliExpress 1005010196581566 | mediterranean 7 | 1 | $248.42 (China Post Air Parcel 6-41; ברשומה $0) | ₪2,008.09 | ₪2,644.98 | ₪2,649 | ₪530 | 5.0 | מעטפת גבולית; גזע עץ כבד |
| corridor/picture-lights | AliExpress 1005008195905528 | nordic 7 | 3 | $16.05 (AliExpress standard shipping 12-23; ברשומה $7.83) | ₪769.13 | ₪1,014.04 | ₪1,019 | ₪599.70 | 1.7 | שלישייה; מעטפת גבולית |
| dining-room/bowl | CJ 1392716043398549504 | mediterranean 7.5, modern-country 7, boho 7.5 | 1 | $21.67 (CJPacket Eub 12-50) | ₪103.60 | ₪137.96 | ₪139 | ₪184 | 0.76 |  |
| dining-room/bowl | AliExpress 1005006118879427 | boho 7 | 1 | $9.08 (AliExpress standard shipping 7-15) | ₪55.24 | ₪74.30 | ₪79 | ₪60 | 1.32 |  |
| dining-room/bowl | AliExpress 1005010778409131 | boho 8 | 1 | $1.99 (AliExpress Selection Standard 6-13) | ₪82.47 | ₪110.14 | ₪119 | ₪60 | 1.98 |  |
| dining-room/canisters | CJ 1475674474018902016 | japandi 7.5 | 3 | $99.09 (CJPacket Eub 12-50; ברשומה $57.45, מק"ט אחר במטמון) | ₪410.01 | ₪541.31 | ₪549 | ₪210 | 2.61 | סט של 3 |
| dining-room/dining-pendant | AliExpress 1005010594359379 | boho 7 | 1 | $28.17 (China Post Air Parcel 12-49) | ₪514.30 | ₪678.59 | ₪679 | ₪490 | 1.39 |  |
| dining-room/dining-pendant | AliExpress 1005004131706427 | japandi 7, mediterranean 8, boho 7 | 1 | $0 (AliExpress standard shipping 8-15) | ₪731.35 | ₪964.31 | ₪969 | ₪640 | 1.51 |  |
| dining-room/dining-pendant | AliExpress 1005008672138088 | mediterranean 7, boho 7 | 1 | $111.23 (AliExpress standard shipping 7-18; ברשומה $111.2) | ₪565.10 | ₪745.46 | ₪749 | ₪490 | 1.53 | משלוח $111 |
| dining-room/herb-pots | AliExpress 1005009049409120 | mediterranean 7 | 1 | $1.99 (AliExpress Selection Standard 6-13) | ₪151.07 | ₪200.44 | ₪209 | ₪79.60 | 2.63 | 4 עציצים; ההשוואה 4 × ₪19.90 |
| dining-room/mug-set | AliExpress 1005010196442767 | modern-country 7 | 1 | $48.75 (AliExpress standard shipping 7-15) | ₪234.30 | ₪310.01 | ₪319 | — | — | 3 ספלים; משלוח $18.73 ליחידה; אין השוואה ברשומה |
| dining-room/tableware-set | Zendrop 2624310 | japandi 7, mediterranean 7, modern-country 7.5 | 6 | $49.92 (הרשומה (ship_usd למכירה)) | ₪415 | ₪547.88 | ₪549 | ₪485 | 1.13 | סט 6; בתמונה סימן מים של מותג אחר |
| hall/planter | AliExpress 1005008561559475 | boho 7 | 1 | $281.54 (China Post Air Parcel 5-35) | ₪1,173.45 | ₪1,546.28 | ₪1,549 | ₪349 | 4.44 | מעטפת גבולית; לא נבדקו השוואות (משלוח $281) |
| hall/storage-boxes | CJ 1705144683208388608 | modern-country 7 | 1 | $55.43 (CJPacket Eub 12-50) | ₪223.20 | ₪295.39 | ₪299 | ₪398 | 0.75 | זוג; מעטפת גבולית |
| hall/storage-boxes | AliExpress 1005008480586450 | boho 7 | 1 | $6.38 (AliExpress standard shipping 8-19) | ₪132.90 | ₪176.53 | ₪179 | ₪196 | 0.91 | זוג; בתור חיפוש-תמונה למוכר זול |
| hall/storage-boxes | AliExpress 1005012923580024 | boho 8 | 1 | $3.5 (AliExpress Selection Standard 6-13) | ₪291.30 | ₪385.04 | ₪389 | ₪200 | 1.95 | מעטפת גבולית (L, לבדוק בפריים); זוג |
| kids/bookshelf | AliExpress 1005007471139220 | modern-country 7 | 2 | $11.5 (AliExpress Standard for Special Goods 8-14) | ₪275.50 | ₪364.24 | ₪369 | ₪278 | 1.33 | זוג מדפים 50 |
| living-room/floor-lamp | AliExpress 1005009785153450 | nordic 7 | 1 | $266.42 (AliExpress standard shipping 17-25) | ₪1,288.35 | ₪1,697.53 | ₪1,699 | ₪1,000 | 1.7 | מעטפת גבולית; משלוח $266 |
| living-room/floor-lamp | AliExpress 1005009386433696 | warm-modern 7 | 1 | $718.35 (Seller's Shipping Method 69-69) | ₪2,842.30 | ₪3,743.12 | ₪3,749 | ₪949 | 3.95 | משלוח $718; אין השוואה ברשומה (מחיר השווי ₪949) |
| living-room/framed-art | CJ 1643938313063108608 | nordic 7 | 1 | $397.06 (DHL Official 3-7; אקספרס; ברשומה $121.48) | ₪2,327.31 | ₪3,065.20 | ₪3,069 | ₪979 | 3.13 | שלישייה; To Door ‏$121 ליחידה |
| living-room/magazine-holder | CJ 2608300209161600400 | warm-modern 7.5 | 1 | $23.27 (CJPacket Eub 12-50) | ₪161.14 | ₪213.70 | ₪219 | ₪229 | 0.96 | מעטפת גבולית |
| living-room/pendant | AliExpress 1005008672138088 | mediterranean 7, boho 7 | 1 | $111.23 (AliExpress standard shipping 7-18; ברשומה $111.2) | ₪565.10 | ₪745.46 | ₪749 | ₪449 | 1.67 | משלוח $111 |
| living-room/pendant | AliExpress 1005013224966509 | mediterranean 7 | 1 | $266.42 (AliExpress standard shipping 21-29) | ₪1,079.80 | ₪1,423 | ₪1,429 | ₪582 | 2.46 | לבוהו המידה לא מתאימה; ים-תיכוני בלבד |
| living-room/sofa-cover | AliExpress 1005012935062690 | boho 7 | 1 | $0 (AliExpress standard shipping 8-18) | ₪192.70 | ₪255.25 | ₪259 | ₪150 | 1.73 |  |
| living-room/wall-decor | AliExpress 1005012947811160 | modern-country 7 | 1 | $1.99 (AliExpress Selection Standard 6-13) | ₪75.37 | ₪100.79 | ₪109 | ₪99 | 1.1 | בלי חישוק פליז |
| master/floor-lamp | AliExpress 1005012507637187 | warm-modern 8, modern-country 7 | 1 | $0 (China Post Air Parcel 14-51) | ₪742 | ₪978.33 | ₪979 | ₪949 | 1.03 | מעטפת גבולית; 12 ק"ג |
| master/floor-lamp | AliExpress 1005009551034916 | warm-modern 8 | 1 | $93.99 (AliExpress standard shipping 22-33) | ₪809.80 | ₪1,067.58 | ₪1,069 | ₪949 | 1.13 | מעטפת גבולית |
| master/floor-lamp | AliExpress 1005009386433696 | warm-modern 7 | 1 | $718.35 (Seller's Shipping Method 69-69) | ₪2,842.30 | ₪3,743.12 | ₪3,749 | ₪949 | 3.95 | משלוח $718 |
| master/nightstand-tray | AliExpress 1005007695543234 | warm-modern 7, japandi 7, mediterranean 7 | 1 | $0 (AliExpress standard shipping 8-15) | ₪62.53 | ₪83.89 | ₪89 | ₪89 | 1.0 | מעטפת גבולית (20) |
| master/nightstand-tray | CJ 1393439287588032512 | nordic 7.5, warm-modern 7 | 1 | $20.64 (CJPacket Eub 12-50) | ₪117.68 | ₪156.49 | ₪159 | ₪139 | 1.14 |  |
| master/pendant | AliExpress 1005008743252990 | warm-modern 7, japandi 7, modern-country 7 | 1 | $0 (China Post Air Parcel 17-47) | ₪455.20 | ₪600.79 | ₪609 | ₪652 | 0.93 | מעטפת גבולית |
| master/pendant | AliExpress 1005008672138088 | mediterranean 7, boho 7 | 1 | $111.23 (AliExpress standard shipping 7-18; ברשומה $111.2) | ₪565.10 | ₪745.46 | ₪749 | ₪449 | 1.67 | משלוח $111 |
| master/pendant | AliExpress 1005006435771102 | modern-country 7.5 | 1 | $180.21 (AliExpress standard shipping 22-33) | ₪994.40 | ₪1,310.58 | ₪1,319 | ₪499 | 2.64 | משלוח $180, 10 ק"ג |
| work/magazine-holder | CJ 2608300209161600400 | warm-modern 7.5 | 1 | $23.27 (CJPacket Eub 12-50) | ₪161.14 | ₪213.70 | ₪219 | ₪229 | 0.96 | מעטפת גבולית |
| work/shelf-boxes | AliExpress 1005006768278100 | boho 7 | 1 | $1.99 (AliExpress Selection Standard 6-13) | ₪151.17 | ₪200.58 | ₪209 | ₪198 | 1.06 | זוג; מעטפת גבולית |
| work/shelf-boxes | CJ 2110994015976243202 | japandi 7 | 1 | $49.12 (CJPacket Eub 12-50) | ₪332.10 | ₪438.75 | ₪439 | ₪360 | 1.22 | זוג; 2 × ₪180 |
| work/shelf-boxes | AliExpress 1005009831522799 | boho 7 | 1 | $0 (AliExpress standard shipping 7-15) | ₪200.57 | ₪265.61 | ₪269 | ₪180 | 1.49 | זוג; מעטפת גבולית |

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

## מה בריף ההחלה יעשה (לא בוצע)

- products.json: retail_ils של כל שורה שמועלית (הישן נשמר ב-retail_before_no_loss_ils, retail_src initial-no-loss-<תאריך>), ועדכון flag/flags/no_loss.
- כרטיס עם מחיר משלו (price.suggested_retail / price.retail_ils): השדה בכרטיס; מחיר מרשומת הסבב: price.retail_ils בכרטיס (הרשומה לא משתנה); רשומה שעלות המכירה שלה אינה N × הכרטיס: שורה חדשה ב-products.json עם sale_cost_usd.
- הכרית של המשתמש: לפי NL1. אקספרס-בלבד: לפי החלטת המנהל.
- אחר כך: build הסטודיו, 7 בדיקות העשן, ספירת המוצרים מעל ₪247 שוב.
