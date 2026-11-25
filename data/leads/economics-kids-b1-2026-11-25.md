# כלכלה לחדרי הילדים ול-B1 (M6-L2), 2026-11-25

הבריף: `briefs/economics-kids-b1-2026-11-25.md`. רק נתונים שכבר בריפו: `price.cost` בכרטיס, ה-SKU שב-`options`, משלוח מהמטמון של הספק (אותו מק"ט או מק"ט אח באותו ליסטינג ובאותו משקל), והמחיר שהרשומות בריפו כבר נותנות. בלי רשת ובלי מפתחות.

## 1. מה היה חסר
המקור: `npx --no-install tsx tools/build-catalog.ts --rooms=living-room --products=tools/tour/rooms.products.json --out=<שם> --lenient` (כמו `npm run tour`), שדה `hidden`, על הכרטיסים של `site/tools/tour/boy|girl|bath-b1.warm-modern.json`.

| כרטיס | חדר | למה הוסתר | מה יש בריפו |
| --- | --- | --- | --- |
| `framed-prints-cj-charcoal-flower-silhouette-set3-30x40-boy` | ילד | אין מחיר | עלות $12.74; משלוח $8.14 ב-`shipping_il` של המק"ט שבחדר; ₪229 ב-profit-fix ‏2026-10-11 (`rest-decor.json`), אותו מחיר כמו Type A בחדר הילדה |
| `bookends-cj-black-walnut-l-bookend-pair-kids` (עותק של `bookends-cj-black-walnut-l-bookend-pair`) | ילד, ילדה | אין מחיר | עלות $6.72 לזוג; הצעת CJ לזוג $8.77 (מטמון, אותו vid); ₪79 ברשומה (`cj-zendrop-hall-work.json`) |
| `bedding-cj-stripe-cotton-single-set-light-brown` | ילד | אין משלוח ואין מחיר | עלות $16.42; הצעה $25.42 למק"ט אח (Dark Grey XS, אותו משקל 1,720 ג'); ₪199 ברשומה (`cj-zendrop-kids.json`), השוואות Fox Home ו-Terminal X בהערות הכרטיס |
| `bedspread-cj-waffle-gauze-fringe-150x200` (השמיכה) | ילד, ילדה | אין מחיר | עלות $13.93; משלוח $10.91 ב-`shipping_il`; ₪199 ברשומה (`cj-zendrop-kids.json`) |
| `pendant-cj-silk-pumpkin-lantern-30` (עותק של `ceiling-lights-cj-silk-pumpkin-lantern-30`), מוחזק בטיחותית | ילד, ילדה | אין מחיר | עלות $24.88; משלוח $21.62 ב-`shipping_il`; ₪219 ליחידה ב-profit-fix (`rest-lighting.json`) |
| `pillowcase-cj-washed-linen-double-ruffle-48x74` (עותק של `pillowcases-cj-washed-linen-double-ruffle-48x74`) | ילדה | אין משלוח ואין מחיר | עלות $8.61 ליחידה, זוג; הצעה $4.73 למק"ט אח (White, אותו משקל 80 ג'); ₪149 לזוג ברשומה (`cj-zendrop-master-corridor.json`) |
| `shower-dispensers-cj-sand-ribbed-ceramic-pump-bottle` | B1 | אין מחיר | עלות $2.35, סט של 3; משלוח $7.88 ליחידה, $16.21 ל-3 (מטמון); ₪149 לסט ברשומה (`cj-zendrop-bath.json`), השוואות בהערות |
| `ledge-planter-aliexpress-retro-ceramic-flower-vase-228781` | B1 | אין משלוח | עלות $20.64 (…577); אין הצעה למק"ט שבחדר; ראו סעיף 3 |
| `candle-cj-ribbed-matte-ceramic-candle-cup-9` | B1 | אין מחיר | עלות $1.36; משלוח $7.00 ב-`shipping_il`; ₪69 ברשומה (`cj-zendrop-bath.json`) |
| `window-sill-vase-cj-black-matte-stoneware-jar-30` (עותק של `vase-cj-black-matte-stoneware-jar-30`) | B1 | אין מחיר | עלות $13.34; משלוח $16.97 ב-`shipping_il`; ₪199 ב-profit-fix (`decor.json`) |
| `toilet-brush-cj-fluted-ceramic-holder-black-handle` | B1 | אין מחיר | עלות $5.03; משלוח $13.56 ב-`shipping_il`; ₪89 ברשומה (`cj-zendrop-bath.json`) |

מוסתרים מסיבה אחרת (כרטיס טיוטה, לפני התמחור), לא נגעתי: הווילון הרומאי 868827, המכוניות 754833, והארנבת 063285 (בחדר הילד, ה"דובי" הוא ה-SKU ‏bear של אותו כרטיס).

## 2. מה מולא: שורה לכל מוצר
כל השורות ב-`data/economics/products.json`, ‏`retail_src` ‏`initial-2026-11-25` (מחיר התחלתי, לא אושר, ה.9), עם `retail_sku`. שדות הרווחיות וה-`no_loss` נכתבו ב-`refresh_rows` של `no_loss.py`, כמו בהחלה של 2026-10-20. המרווח הוא לפני CAC.

- **הדפסי הילד** (`framed-prints-cj-charcoal-flower-silhouette-set3-30x40-boy`): ₪229 לסט של 3, מ-profit-fix 2026-10-11. משלוח $8.14 מהכרטיס. נחיתה ₪68.9, מרווח 53.5% (ok). לא-מפסיד ₪99. ‏`il_value` הועתק מכרטיס הילדה, אותו ליסטינג.
- **תומכי הספרים** (השורה `bookends-cj-black-walnut-l-bookend-pair`, העותק בילד ובילדה קורא אותה): ₪79 לזוג, מהרשומה. ‏`sell_qty` 1, ‏`sale_cost_usd` 6.72, משלוח $8.77 (הצעת CJ לזוג). המוסכמה של 2026-10-18: הסטודיו מכר קודם 2 × $6.72. נחיתה ₪51.1, מרווח 11.5% (below-floor). לא-מפסיד ₪69. אין השוואות.
- **מצעי הילד** (`bedding-cj-stripe-cotton-single-set-light-brown`): ₪199, מחיר העמדה ברשומה. משלוח $25.42 ממק"ט אח, מסומן `freight_from_sibling` בשורה החדשה ב-`freight-cj.json`. נחיתה ₪138.1, מרווח 7.1% (below-floor). לא-מפסיד ₪189. לפי הרשומה, ב-₪229 (השווי בישראל לסט של 3 חלקים) המרווח 17.9%; ההחלטה למשתמש.
- **השמיכה** (`bedspread-cj-waffle-gauze-fringe-150x200`, ילד וילדה): ₪199 מהרשומה. משלוח $10.91 מהכרטיס. נחיתה ₪82.0, מרווח 40.3% (ok). לא-מפסיד ₪119 למק"ט שבחדר, ₪139 בכל התרחישים. אין השוואות.
- **המנורה התלויה** (השורה `ceiling-lights-cj-silk-pumpkin-lantern-30`, העותק בילד ובילדה קורא אותה): ₪219 ליחידה, מ-profit-fix. משלוח $21.62 מהכרטיס. נחיתה ₪153.4, מרווח 6.3% (below-floor). לא-מפסיד ₪209. בחדרי הילדים היא נשארת חסומה (אין CE, `sale: blocked` ב-`kids.json` ובקובצי הסיור). לא נגעתי בכרטיס, בהערות או בבטיחות.
- **הציפיות עם הסלסול** (השורה `pillowcases-cj-washed-linen-double-ruffle-48x74`, העותק בילדה קורא אותה): ₪149 לזוג מהרשומה, ‏`sell_qty` 2. המשלוח $4.73 ליחידה ממק"ט אח, מסומן `freight_from_sibling` ב-`freight-cj.json`; לזוג $5.74 בנוסחת החבילה. נחיתה ₪75.8, מרווח 28.7% (below-floor). לא-מפסיד ₪109. אין השוואות.
- **סט המתקנים** (`shower-dispensers-cj-sand-ribbed-ceramic-pump-bottle`): ₪149 לסט של 3 מהרשומה, ‏`sell_qty` 3. משלוח $16.21 (הצעת CJ ל-3). נחיתה ₪76.8, מרווח 27.9% (below-floor). לא-מפסיד ₪109. ההשוואה הגבוהה ₪180 (Fox Home ‏3 × ₪60).
- **הנר** (`candle-cj-ribbed-matte-ceramic-candle-cup-9`): ₪69 מהרשומה. משלוח $7.00 מהכרטיס. נחיתה ₪27.6, מרווח 40.4% (ok). לא-מפסיד ₪39. ‏`il_value` מקטגוריית הפמוטים ב-`market-prices.json`, כמו ברשומה.
- **הכד על אדן החלון** (השורה `vase-cj-black-matte-stoneware-jar-30`, העותק ב-B1 קורא אותה): ₪199, מ-profit-fix. משלוח $16.97 מהכרטיס. נחיתה ₪100.0, מרווח 29.6% (below-floor). לא-מפסיד ₪139 למק"ט שבחדר, ₪159 בכל התרחישים. אין השוואות.
- **מברשת האסלה** (`toilet-brush-cj-fluted-ceramic-holder-black-handle`): ₪89 מהרשומה. משלוח $13.56 מהכרטיס. נחיתה ₪61.3, מרווח 6.7% (below-floor). המחיר שווה בדיוק למחיר הלא-מפסיד (₪89; נקודת האיזון ₪82.3).

## 3. מה לא מולא ולמה
- **העציץ על המדף ב-B1** (`ledge-planter-aliexpress-retro-ceramic-flower-vase-228781`): **נשאר בלי שורה.**
  - המק"ט שבחדר הוא …577, ‏"Large brown round", ‏$20.64. אין לו הצעת משלוח לישראל במטמון.
  - ההצעה היחידה במטמון היא למק"ט האח …584, ‏"101-a small elegant black flat type", ‏$11.46: ‏A.Studio Standard ‏$0, ‏13–22 יום.
  - …584 הוא מידה אחרת (קטן ושטוח, מול גדול ועגול), ובמחיר כמעט חצי. ל-AliExpress יש משקל אריזה אחד לכל הליסטינג (0.334 ק"ג, ‏19×17×16), בלי משקל לכל מק"ט. לכן אי אפשר לקבוע שהם באותה מחלקת משקל.
  - ל-…583 התקבל `DELIVERY_RATE_LIMIT_FOR_SINGLE_PRODUCT`, כלומר בלי תשובה.
  - **מחכה לטוקן AE חדש:** קריאת freight אחת ל-…577.
- **שלוש הטיוטות** (הווילון, המכוניות, הארנבת/הדובי): לא מוסתרות בגלל כלכלה, ולא מולאו.
  - הווילון: רק FedEx IP, כלומר רק אקספרס (NL2).
  - המכוניות: יש משלוח בכרטיס ואין מחיר.
  - הארנבת: יש לה כבר ₪119 מהליקוט ומשלוח מהכרטיס.

## 4. השפעות לוואי
- ארבע מהשורות הן של כרטיס המקור שהעותק קורא (`mirror_of`), ולכן המקור מתומחר גם בחדר שלו:
  - תומכי הספרים: work;
  - הציפיות: master;
  - המנורה: corridor;
  - הכד: living-room.
- **בחנות, בעמדת האגרטל של הסלון הנורדי, משתנה האגרטל השני.** הכד השחור (ציון נורדי 8.0) נכנס במקום הבקבוק הלבן `vase-cj-white-plum-hand-thrown` (7.5), כי הבנייה בוחרת את 3 המתומחרים בעלי הציון הגבוה. בסלון של הסיור (מודרני חם) אין שינוי.
- **חוסר במשלוח של שאר המידות:** מידות המצעים S/M/L (‏1.82–2.02 ק"ג) והמנורה ב-40/50 ס"מ כבדות יותר ואין להן הצעה. האתר מתמחר אותן על משלוח המק"ט שבחדר. `--check-derived` לא מצא הפסד, אבל המשלוח שלהן לא נמדד.

## 5. בדיקות
- **`python3 -E -P scripts/economics/no_loss.py --check`:** אף אחד מ-10 המוצרים לא מפסיד, וכולם `ok` במחיר שנקבע. הקוד יוצא ב-1 בגלל מוצר אחד שמפסיד מקודם ולא נגעתי בו: `sofa-cover-cj-cotton-muslin-fringe` (₪129 מול ₪139).
  - הספירות: ok ‏321 → 331, ‏no-price ‏128 → 120, ‏cannot-compute ‏14 → 12.
  - הדגל `-I` לא עובד כאן, כי Pillow מותקן רק ב-user site. ‏`-E -P` שומר על אותו בידוד, חוץ מ-user site.
- **`--check-derived`:** אפס תרחישים מפסידים.
- **`--check-site` על קטלוג הסיור החדש:** הפסד אחד בלבד, אותה ספה.
- **הבנייה של קטלוג הסיור:** כל 10 המוצרים (12 עמדות) מקבלים מחיר. העציץ נשאר "no shipping line".
- **`python3 -I scripts/sourcing/options.py validate`:** ‏513 כרטיסים, 0 לא תקינים.
- **`npx --no-install vitest run` (מ-`site/`):** ‏51 קבצים, ‏571/571.
- **JSON:** ‏`products.json` ו-`freight-cj.json` נטענים, ושאר השורות בהם לא השתנו (בדיקת round-trip).
