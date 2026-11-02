# בדיקת המוצרים לפני ההדמיות הנורדיות · 2026-11-02

> product-readiness agent · שלב 1 של `briefs/nordic-house-render-2026-10-24.md` סעיף 8: "בדקי שהמוצרים עדכניים ושמישים לפני". בדקתי כל כרטיס שבכותרות `#` של 11 הפרומפטים ב-`assets/prompts/recipe-v5.nordic/` ובתוכנית `docs/rooms-render-plan-2026-10-25.md`. לא שיניתי כרטיס, מחיר, עמדה, פרומפט או מסמך מחייב, לא פניתי לספק ולא גירדתי דפי מוצר.
> **הנתונים המלאים:** `docs/render-products-check-2026-11-02.json` (כל בדיקה לכל כרטיס, כל שורה לכל פריים, ההחלפות ובדיקותיהן). **תור החיות:** `data/leads/final-2026-10-13/round5/liveness-queue-2026-11-02.json`.

## 0. בשורה אחת
- **101 הופעות של 81 כרטיסים** ב-11 הפריימים: CJ ‏65, ‏AliExpress ‏34, ‏Zendrop ‏2 (כרטיסים: 51, ‏28, ‏2). ועוד 5 שטיחים ישראליים כממלאי מקום ב-7 הופעות, רשומים ולא נבדקו.
- **פסק לפי הופעה:** שמיש 30, שמיש עם הערה 57, **להחליף 14** (13 כרטיסים שונים).
- **לפי כרטיס:** שמיש 22, שמיש עם הערה 45, להחליף 12, ושניים שונים בין פריימים (כרית הבוקלה: שמישה ב-M0, עם הערה ב-MB0; הסרוגה: להחליף ב-K-boy, עם הערה ב-K-girl).
- **ההחלפות:** 7 עמדות מקבלות מועמד אחר (מנורות הטרוורטין, פנס פינת האוכל, מעמד הנייר, הדובי, שתי שמיכות הילדים, העציץ ב-W0), השטיח של M0 מקבל ממלא מקום ישראלי, ו-6 עמדות נשארות ריקות במפורש (הרפיה ומנורת הרגל ב-M0, מעמד המטריות, הווילון הרומאי בשני חדרי הילדים, תומכי הספרים).
- **חיות הספק:** שני מוצרי Zendrop חיים ובמלאי היום (דרך ה-MCP). 79 כרטיסי CJ ו-AliExpress לא נבדקו (אין מפתח CJ בסשן, AliExpress בסשן אחר): כל "שמיש" שלהם מותנה בתור.

## 1. איך בדקתי
| # | בדיקה | המקור | מה נחשב כישלון |
| --- | --- | --- | --- |
| 1 | כרטיס קיים, עובר סכמה, לא rejected | `data/products/**`, ‏`product-card.schema.json` 1.1 (מאמת stdlib מלא, כולל minItems ו-propertyNames, room+slot מול קובץ העמדות, ו-`options` עם `scripts/sourcing/options.py`) | rejected או חסר. שגיאות סכמה נרשמות ולא מתוקנות |
| 2 | נורדי 7 ומעלה | `style_scores.nordic`, ‏`round5/designer-audit*.json`, ‏AU3. קיבלתי גם את ההצלבה של המעצב מ-14.10 (`results/basket-*.json`, ‏`round5-designer-cards.json`), מסומן "לא בכרטיס" | ציון מעצב מתחת ל-7. ציון צוות בלבד = "לא מאומת", הערה |
| 3 | בתוך מעטפת העמדה | `data/slots/<room>.json` של החדר שבפריים | יותר מ-10% מחוץ, בלי החלטת מעצב רשומה. עד 10% גבולי; 10–12% "בקצה", מסומן |
| 4 | מחיר ו-no-loss | `products.json`, ‏`no_loss.py --check` ו-`--json` | express-only, ‏cannot-compute, ‏PRE1 או עמדה מוחרגת. בלי מחיר לצרכן = הערה (מחיר הרצפה ידוע) |
| 5 | תמונת רפרנס | הרפרנס בכותרת הפרומפט, או `images[0]` | HTTP שאינו 200 |
| 6 | חיות הספק | Zendrop דרך MCP; ‏CJ ו-AliExpress לתור | מוצר או SKU שלא קיימים |

**הפסק:** שמיש = כל הבדיקות עוברות. שמיש עם הערה = עובר, עם פער שלא עוצר הדמיה (אין מחיר עדיין, שגיאות סכמה, מידה גבולית או חסרה, ציון לא מאומת במעצב, SKU להחליף, מלאי נמוך במטמון). להחליף = המוצר לא יכול להיות בפריים הזה.

**הרצת no_loss:** ‏`python3 -I scripts/economics/no_loss.py --check` נכשל בסביבה הזו לפני החישוב: ‏`python3` הוא 3.11, ו-Pillow של המערכת בנוי ל-3.12. הרצתי `python3.12 -I` באותו סקריפט: יציאה 0, אפס כשלי אינווריאנט, אף מוצר לא מפסיד במחירו הנוכחי (464 מוצרים). התוצאה לכל כרטיס מ-`--json`, לקובץ בתיקיית ה-scratchpad.

## 2. סיכום לפי בדיקה (81 כרטיסים)
1. **כרטיס וסכמה:** כל 81 קיימים, כולם candidate, אף אחד לא rejected. **8 לא עוברים את הסכמה** (כולם AliExpress: ‏`colors` ו-`visual_weight` ריקים; ב-589009 גם `placement: "sill"`; בסרוגה ובמכוניות `certificates[0].url` ריק): `wall-decor-aliexpress-natural-raffia-woven-bohemian-763597`, `vase-aliexpress-vintage-distressed-clay-vase-589009`, `console-vessel-aliexpress-ceramic-wabi-sabi-vase-906575`, `roman-blind-aliexpress-modern-beige-color-flat-868827`, `soft-toy-aliexpress-handmade-crochet-bunny-baby-999497`, `toy-cars-aliexpress-baby-wooden-toys-beech-975232`, `curtains-aliexpress-cotton-linen-curtain-look-902882`, `planter-aliexpress-nordic-style-natural-seagrass-839727`.
2. **התאמה:** **3 מתחת ל-7 במעצב** (`umbrella-stand-cj-solid-wood-umbrella-bucket-hex-19x49`, `bedding-cj-stripe-cotton-single-set-light-brown`, `planter-aliexpress-nordic-style-natural-seagrass-839727`). **3 בציון צוות בלבד** (`framed-art-aliexpress-minimal-geometric-triptych-prints`, `floor-lamp-aliexpress-wabi-sabi-japan-floor-217361`, `shelf-boxes-cj-felt-storage-bin-30x24-pair`). ב-14 הציון של המעצב קיים בהצלבה ולא בכרטיס. ‏AU3 לא חל על אף עמדה כאן.
3. **מעטפת:** 8 הופעות מחוץ למעטפת ביותר מ-10%: M0 accent-sconces, M0 wall-decor, M0 floor-lamp, D1 dining-pendant, K-boy soft-toy, K-girl bedding, W0 planter, W0 bookends. ועוד ה-SKU שבכרטיס של וילון W0 (W100), שיש לו תחליף באותו ליסטינג. גבוליות (עד 10%) ובקצה (10–12%, מנורות המקלחת): בטבלאות.
4. **מחיר:** 52 עוברים. **25 בלי מחיר לצרכן** (לכולם חוץ מאחד יש מחיר רצפה מ-no_loss.py; לעציץ 839727 אין שורה בכלל). **2 באקספרס בלבד** (`rug-cj-braided-wool-natural`, ‏`roman-blind-aliexpress-modern-beige-color-flat-868827`), **2 cannot-compute** (`paper-towel-holder-cj-beech-upright-31`: ל-CJ אין משלוח לישראל; `bedding-cj-stripe-cotton-single-set-light-brown`: אין משלוח ואין הערכה). אף כרטיס לא PRE1, ואף עמדה בפריימים לא מוחרגת (AU2); ‏R6Q2 ו-NL2 פתוחות.
5. **תמונה:** 89 כתובות (הרפרנסים בכותרות, התמונה הראשונה בכרטיסים בלי רפרנס, ותמונות ה-SKU של ההחלפות): כולן 200 עם סוג תמונה, ב-HEAD אחד לכתובת, ברווח של 2 שניות.
6. **חיות:** ‏Zendrop ‏2784524 (סל הבטן, וגם העציץ המוצע ל-W0) ו-2814530 (הצנצנות): במלאי, המחירים כמו בכרטיס. ‏79 כרטיסים בתור.

## 3. לפי פריים
עמדה | כרטיס | פסק | למה | החלפה. ‏"מעטפת" לפי קובץ העמדות של החדר בפריים.

### M0, סלון (`m0-v6.txt`)
| עמדה | כרטיס | ספק | פסק | למה | החלפה |
| --- | --- | --- | --- | --- | --- |
| framed-art (גיבור) | `framed-art-aliexpress-minimal-geometric-triptych-prints`<br>12000039454944614 (colour 1, 50x70) | AE | שמיש עם הערה | מעטפת (אין מספרים): ב-living-room.json אין מעטפת במספרים; 3 × 50×70 עם 6 ס"מ ביניהן = 162, בתוך ה-165 שהערת AU5 מניחה; אין ציון מעצב (8 של הצוות בלבד); RND2 פתוחה; מידע: לחנות ביקורת אחת (דירוג 1.0): איכות ההדפסה לא ידועה; מחיר ₪199 מעל ההשוואה הגבוהה ₪175 (above-market); אין שורה ב-products.json, המחיר מקובץ הליקוט |  |
| accent-sconces | `accent-sconces-cj-travertine-block-updown-8x16` | CJ | **להחליף** | מעטפת (מחוץ): רוחב 8 מול 10–14 בנורדי (‎−20%); בליטה 8 וגובה 16 בתוך המעטפת; מחוץ למעטפת ביותר מ-10%; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪169 | **`wall-sconce-cj-travertine-cube-updown-12`**, ‏type-a indoor (LED9W, 12×12×12). אותו ליסטינג של CJ ‏(2509290740271629700), קוביית טרוורטין 12×12×12 בתוך 10–14 × 12–18, בליטה 12; המעצב 7.0 כמועמד ל-accent-sconces (ציון הכרטיס). אין מחיר לצרכן (רצפה ₪189 ליחידה); וריאנט type-b מפסיד באתר ב-₪149. תמונה 200. חיות לא נבדקה. חלופה שנייה: accent-sconces-cj-ribbed-travertine-half-cylinder-wood-bracket (‏7.5, ‏₪599 לזוג), אבל מידות Type B לא מוצהרות |
| wall-decor | `wall-decor-aliexpress-natural-raffia-woven-bohemian-763597` | AE | **להחליף** | מעטפת (מחוץ): ה-SKU היחיד בגודל 30 ס"מ מול פריט בודד 35–45 (‎−14%); מחוץ למעטפת; זמני ונוטה לבוהו (התוכנית); הכרטיס לא עובר את הסכמה (3 שגיאות) | **להשאיר ריק.** אין עוד כרטיס לעמדה בנורדי 7 ומעלה (המקרמה 6.5, השאר עד 6.5). או: המעצב מרחיב את המעטפת ל-30 לפי AU5 ומדווח למשתמש |
| pendant | `pendant-cj-silk-ribbed-pumpkin-40` | CJ | שמיש עם הערה | מעטפת (אין מספרים): אין מעטפת במספרים ב-living-room.json; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪289; מידע: 2 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| curtains | `curtains-aliexpress-linen-blend-s-fold-180502` | AE | שמיש עם הערה | מעטפת (אין מספרים): אין מעטפת במספרים ב-living-room.json (בחדרים האחרים נפילה 278–282 מול 270); אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪89; מידע: 23 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| vase | `vase-aliexpress-vintage-distressed-clay-vase-589009`<br>L | AE | שמיש עם הערה | מעטפת (בתוך): גוף 31 בתוך 25–35; VL1 פתוחה; הכרטיס לא עובר את הסכמה (4 שגיאות) |  |
| wall-sconce | `wall-sconce-cj-black-swing-arm-fabric` | CJ | שמיש עם הערה | מעטפת (אין מספרים): ב-living-room.json רק מיקום הפלטה, בלי מידות; מידע: גוון האהיל שנשלח לא אומת; מידות לא מוצהרות; ₪519 above-market, תרומה ₪1.09 בלבד |  |
| floor-lamp | `floor-lamp-aliexpress-wabi-sabi-japan-floor-217361` | AE | **להחליף** | מעטפת (מחוץ): פנס עמודי צר על חצובה, אהיל כנראה צר מ-35 (בנורדי 35–38); AU5 התיר את הצורה הזו בג'אפנדי בלבד; אין מידות בכרטיס; אין ציון מעצב (8 של הצוות); הצורה לא מותרת בנורדי עד תשובה לשאלה 2 בתוכנית | **להשאיר ריק.** אין מנורת רגל נורדית בהתאמה 7 ומעלה (התוף השחור 6.5, השאר בלי ציון נורדי או נדחו). אם המשתמש מתיר את הפנס העמודי בנורדי (שאלה 2), 217361 חוזרת עם הערה |
| basket | `basket-zendrop-seagrass-belly-38x34`<br>1775329665785880587 (38×34) | Zendrop | שמיש עם הערה | מעטפת (אין מספרים): אין מעטפת במספרים ב-living-room.json; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪59; מידע: 4 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| rug | `rug-cj-braided-wool-natural`<br>CJJT211801818RI (230×330 Square; בכרטיס 200×300) | CJ | **להחליף** | מעטפת (אין מספרים): אין מעטפת במספרים ב-living-room.json; express-only: הקו היחיד DHL ‏$491, מפסיד ב-₪1,299 (שווה-הפסד באקספרס ₪3,299); NL2 פתוחה, לא למכירה; מידע: 17 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד | **rugs-il-picks-2026-10-20 H01 NYOKO (טולמנ'ס)** (ממלא מקום). ברירת המחדל של המעצב ל-living-room/rug בנורדי ב-20.10 (‏8.5, ‏240×340 בהזמנה או 250×350 מהקטלוג), לפי כלל 3 בתוכנית: STAND-IN, לא למכירה (AU1). NYOKO כבר ממלא מקום ב-W0, ושני החדרים לא נראים יחד. אם NL2 נענית PRE1, השטיח הקלוע יכול להישאר בפריים כ'המלאי אינו זמין כעת' |
| cushions | `cushions-cj-boucle-teddy`<br>CJZT228600103CX (White 50×50) | CJ | שמיש | מעטפת (אין מספרים): אין מעטפת במספרים ב-living-room.json |  |
| cushions | `cushions-cj-knitted-chenille-bean-green` | CJ | שמיש | מעטפת (אין מספרים): אין מעטפת במספרים ב-living-room.json |  |
| cushions | `cushions-cj-linen-look-charcoal`<br>CJZT113551671SH (Dark Grey 30×50) | CJ | שמיש עם הערה | מעטפת (אין מספרים): אין מעטפת במספרים ב-living-room.json; אין רפרנס בכותרת (בכוונה); התמונה הראשונה בכרטיס תקינה; מידע: הפרומפט מבקש 30×50; ה-SKU בחדר בכרטיס 50×50 (קיים SKU ‏Dark Grey 30×50: ‏CJZT113551671SH) |  |
| cushions | `sofa-cover-cj-cotton-muslin-fringe` | CJ | שמיש | מעטפת (אין מספרים): השמיכה של סט הכריות; אין מעטפת במספרים |  |
| table-runner | `table-runner-cj-linen-look-sage-fringe` | CJ | שמיש | מעטפת (אין מספרים): מיקום בלבד, בלי מידות |  |
| candle-holders | `candle-holders-cj-travertine-pedestal` | CJ | שמיש | מעטפת (אין מספרים): מיקום בלבד, בלי מידות |  |
| bowl | `bowl-cj-glutinous-white-belly-bowl-21` | CJ | שמיש | מעטפת (בתוך): 21.2×6.4 בתוך קוטר 16–24, גובה 5–9 |  |

### D1, פינת האוכל (`d1.txt`)
| עמדה | כרטיס | ספק | פסק | למה | החלפה |
| --- | --- | --- | --- | --- | --- |
| dining-pendant (גיבור) | `dining-pendant-cj-black-ring-cloth-lantern-50`<br>CJTH164234902BY (50) | CJ | **להחליף** | מעטפת (מחוץ): גובה 36 מול עד 30 (+20%); כבל 120 מול 130 לפחות (‎−7.7%); קוטר 50 בתוך 45–55; מחוץ למעטפת בגובה; וריאנט מפסיד באתר (SITE1); מידע: 1 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד | **`pendant-cj-silk-pumpkin-lantern`**, ‏CJYD243199107GT (Diameter 50cm / Warm Light). המעצב 7 ל-dining-room/dining-pendant ‏(basket-living); קוטר 50 בתוך 45–55; ₪299 ב-SKU של 40, ול-SKU של 50 צריך מחיר (אף וריאנט לא מפסיד באתר); גובה לא בכרטיס, לבדוק מול 30. תמונת ה-SKU 200. שימו לב: ב-M0 תלויית המשי המצולעת, ו-T-LD עובר מאחת לשנייה; המעצב מחליט. חלופה: להשאיר את הפנס השחור אם המעצב מרחיב את h_max לפי AU5 |
| table-runner | `table-runner-aliexpress-french-linen-stonewash-40x140`<br>12000044133070175 (linen 40×140) | AE | שמיש | מעטפת (אושר במעצב): רוחב 40 מול 33–38 (+5%); המעצב אישר בביקורת (envelope_ok) על שולחן 85 |  |
| centerpiece-vase | `vase-cj-textured-white-stoneware`<br>CJJT312391802BY (Medium) | CJ | שמיש עם הערה | מעטפת (גבולי): Medium ‏26.5×17.5: גובה בתוך 20–28, קוטר 17.5 מול 9–16 (+9%) |  |
| candle-holders | `candle-holders-aliexpress-matte-black-iron-pillar-set2` | AE | שמיש עם הערה | מעטפת (בתוך): צלחות 10.5×3 עם נרות 7×15 ו-7×10: בתוך holder 1–12, נמוך עד 22, גבוה 16–27; מידע: מלאי במטמון: 5 |  |
| curtains | `curtains-aliexpress-linen-blend-s-fold-180502` | AE | שמיש עם הערה | מעטפת (גבולי): פאנל 132 בתוך 130–150; נפילה 270 מול 278–282 (‎−3%); אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪89; מידע: 23 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| bench-pad | `bench-pad-aliexpress-linen-look-flat-cushion-130x35x3`<br>12000051878164389 (1 off white) | AE | שמיש עם הערה | מעטפת (גבולי): אורך 130 מול 135–140 (‎−4%); רוחב ועובי בתוך המעטפת |  |
| framed-art | `framed-art-cj-taupe-block-black-line-30x40` | CJ | שמיש | מעטפת (בתוך): 30×40×2 בתוך המעטפת |  |
| condiment-set | `condiment-set-cj-rubberwood-mill-pair-6in` | CJ | שמיש עם הערה | מעטפת (בתוך): מטחנות 15.2 בתוך 15–20; העמדה סט של 3 עם בקבוק שמן, הכרטיס זוג; הסט חסר את הבקבוק |  |
| bowl | `bowl-cj-glutinous-white-belly-bowl-21` | CJ | שמיש | מעטפת (בתוך): 21.2×6.4 בתוך 20–26 × 5–11 (AU5 בקובץ העמדות; בנספח הנורדי 7–11, שאלה 3) |  |
| tableware-set | `tableware-set-cj-grey-sand-matte-plate` | CJ | שמיש עם הערה | מעטפת (בתוך): צלחת 28 בתוך 23–28; צלחות בלבד, בלי צלחת צד וקערה לערימה; הסט חסר צלחת צד וקערה |  |
| mug-set | `mug-set-cj-sandy-stoneware-mug-glazed-rim-set3` | CJ | שמיש עם הערה | מעטפת (גבולי): גובה 9 בתוך 9–11; קוטר 9.8 מול 8–9 (+9%); אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪59; מידע: הציון מהצלבת המעצב, לא בכרטיס |  |
| dining-rug | ממלא מקום H03 | ישראלי | ממלא מקום | שטיח ישראלי כממלא מקום, לא למכירה (AU1): רשום, לא נבדק | |
| kitchen-runner | ממלא מקום H07 | ישראלי | ממלא מקום | שטיח ישראלי כממלא מקום, לא למכירה (AU1): רשום, לא נבדק | |

### D2, חזית המטבח (`d2.txt`)
| עמדה | כרטיס | ספק | פסק | למה | החלפה |
| --- | --- | --- | --- | --- | --- |
| bench-pad | `bench-pad-aliexpress-linen-look-flat-cushion-130x35x3` | AE | שמיש עם הערה | מעטפת (גבולי): אורך 130 מול 135–140 (‎−4%) |  |
| framed-art | `framed-art-cj-taupe-block-black-line-30x40` | CJ | שמיש | מעטפת (בתוך): 30×40×2 בתוך המעטפת |  |
| condiment-set | `condiment-set-cj-rubberwood-mill-pair-6in` | CJ | שמיש עם הערה | מעטפת (בתוך): מטחנות 15.2 בתוך 15–20; זוג מתוך סט של 3; הסט חסר את הבקבוק |  |
| bowl | `bowl-cj-glutinous-white-belly-bowl-21` | CJ | שמיש | מעטפת (בתוך): בתוך 20–26 × 5–11 |  |
| paper-towel-holder | `paper-towel-holder-cj-beech-upright-31` | CJ | **להחליף** | מעטפת (בתוך): 13×31 בתוך גובה 30–34, בסיס עד 15; cannot-compute: ל-CJ אין משלוח לישראל במוצר הזה (no-route) | **`paper-towel-holder-aliexpress-solid-wood-slotted-paper-towel-stand`**, ‏12000060575834322 (Style A, הטבעי). המעצב 7.5 בנורדי (designer-audit-5d, keep), נספר רק הטבעי, כלומר Style A ולא ה-Style B (אגוז) שבכרטיס; 13×31 בתוך המעטפת; ₪69, לא מפסיד, אף וריאנט לא מפסיד באתר; תמונת ה-SKU 200 (המעצב סימן שתמונות הליסטינג הן הדמיית AI: לחתוך את תמונת ה-SKU). חיות לא נבדקה |
| tableware-set | `tableware-set-cj-grey-sand-matte-plate` | CJ | שמיש עם הערה | מעטפת (בתוך): צלחת 28 בתוך 23–28; צלחות בלבד; הסט חסר צלחת צד וקערה |  |
| mug-set | `mug-set-cj-sandy-stoneware-mug-glazed-rim-set3` | CJ | שמיש עם הערה | מעטפת (גבולי): קוטר 9.8 מול 8–9 (+9%); אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪59; מידע: הציון מהצלבת המעצב, לא בכרטיס |  |
| canisters | `canisters-zendrop-matte-ceramic-bamboo-lid-sml`<br>S+M+L White (…057, …059, …061) | Zendrop | שמיש עם הערה | מעטפת (חסר): קוטר כ-11 בתוך 8–15; הגבהים לא מפורסמים; מידע: גבהים לא מפורסמים (גם לא ב-Zendrop היום); הכותרת ב-d2.txt והתוכנית קוראות לו zendrop-2814530 (שם הקובץ), לא מזהה הכרטיס |  |
| tea-towel | `tea-towel-cj-waffle-cotton-beige-45x65-pair` | CJ | שמיש עם הערה | מעטפת (בתוך): 45×65 מקופלת לחצי = 22.5×32.5 בתוך 22–26 × 32–38; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪39; מידע: 4 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| dining-rug | ממלא מקום H03 | ישראלי | ממלא מקום | שטיח ישראלי כממלא מקום, לא למכירה (AU1): רשום, לא נבדק | |
| kitchen-runner | ממלא מקום H07 | ישראלי | ממלא מקום | שטיח ישראלי כממלא מקום, לא למכירה (AU1): רשום, לא נבדק | |

### H0, הכניסה (`h0-B.txt`)
| עמדה | כרטיס | ספק | פסק | למה | החלפה |
| --- | --- | --- | --- | --- | --- |
| framed-art (גיבור) | `framed-art-cj-swinging-line-black-frame-mat-35x45`<br>CJJT222223002BY (A 45×55; ה-SKU בחדר בכרטיס 35×45) | CJ | שמיש עם הערה | מעטפת (גבולי): רוחב 45 מול 50–60 (‎−10%); גובה 55 בתוך 50–60; ל-SKU של 45×55 אין הצעת משלוח משלו; התרומה ב-35×45 היא ₪1.04 בלבד |  |
| console-vessel | `console-vessel-aliexpress-ceramic-wabi-sabi-vase-906575`<br>12000050733388958 (01) | AE | שמיש עם הערה | מעטפת (גבולי): גובה 26.5 בתוך 25–35; קוטר 17.5 מול 10–16 (+9%); הכרטיס לא עובר את הסכמה (3 שגיאות); מידע: הציון מהצלבת המעצב, לא בכרטיס; מלאי במטמון: 2 (2026-10-12): הראשון בתור לבדיקת חיות; אין שורה ב-products.json; המחיר ₪489 מהכרטיס |  |
| key-tray | `key-tray-aliexpress-oval-metal-tray-693779`<br>black S | AE | שמיש עם הערה | מעטפת (גבולי): 22.2 מול 16–22 (+1%), עומק 9.5 מול 10–14 (‎−5%), שפה 1.5 מול 2–4 (חצי ס"מ); אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪49 |  |
| wall-hooks | `wall-hooks-aliexpress-pine-oval-pegs-4pcs`<br>4pcs | AE | שמיש עם הערה | מעטפת (חסר): 4 יתדות בתוך 3–5, בליטה כ-3 מתוך עד 8; מידות לא מפורסמות; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪29; מידע: מידות לא מפורסמות (יתד כ-3×10, בליטה כ-3); מלאי במטמון: 11; 2 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| wall-sconce | `wall-sconce-cj-white-fabric-cube-15-hall` | CJ | שמיש עם הערה | מעטפת (בתוך): 15×12×15 בתוך 10–24 × 15–30, בליטה עד 20; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪149; מידע: 1 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| bench-cushion | `bench-cushion-aliexpress-linen-look-flat-cushion-110x35x3` | AE | שמיש | מעטפת (בתוך): 110×35×3 בתוך המעטפת |  |
| bench-throw | `bench-throw-cj-cotton-waffle-blanket-150x200`<br>White | CJ | שמיש עם הערה | מעטפת (בתוך): מקופלת לכ-33×33 בתוך 30–34 × 30–36; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪129; מידע: הציון מהצלבת המעצב, לא בכרטיס; גובה הקיפול (5–8) לא נבדק |  |
| basket | `basket-cj-two-tone-rope-jute-white-30` | CJ | שמיש עם הערה | מעטפת (בתוך): 30×30 בתוך 28–34 × 26–30; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪59; מידע: 2 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| umbrella-stand | `umbrella-stand-cj-solid-wood-umbrella-bucket-hex-19x49`<br>Light Color (hex-light) | CJ | **להחליף** | מעטפת (גבולי): 19×49 מול 20–24 × 45–50 (‎−5%); ציון המעצב בנורדי 6.5 (lower-fit), מתחת ל-7; הכותרת כותבת 7 | **להשאיר ריק.** הכרטיס היחיד בעמדה hall/umbrella-stand. להוציא את צורת-המקום והמטרייה מה-clay |

### C0, המסדרון (`c0.txt`)
| עמדה | כרטיס | ספק | פסק | למה | החלפה |
| --- | --- | --- | --- | --- | --- |
| gallery-art (גיבור) | `gallery-art-cj-black-ink-abstract-wide-mat-40-set3` | CJ | שמיש | מעטפת (בתוך): 3 × 40×40 בתוך 40 × 40–50 (corridor.json 1.0.2) |  |
| ceiling-lights | `ceiling-lights-aliexpress-flat-oval-paper-lantern-shade-40-pair` | AE | שמיש | מעטפת (אושר במעצב): קוטר 40 בתוך 30–40; בליטה 22 ועוד הערכה מול 12–20, המעצב אישר על כבל קצר (5d, envelope_ok) |  |
| ceiling-light (hall, בנוף בלבד) | `ceiling-light-aliexpress-flat-oval-paper-lantern-shade-40` | AE | שמיש | מעטפת (בתוך): 40×22 בתוך 35–45 × 18–25 (hall/ceiling-light); מידע: בנוף בלבד, לא נספר |  |

### MB0, חדר ההורים (`mb0.txt`)
| עמדה | כרטיס | ספק | פסק | למה | החלפה |
| --- | --- | --- | --- | --- | --- |
| framed-art (גיבור) | `framed-art-cj-black-ink-abstract-wide-mat-50-pair` | CJ | שמיש | מעטפת (אושר במעצב): 110×50: גובה 50 מול 55–65 (‎−9%), המעצב אישר (5d); מידע: פלקסי: לבקש בלי זיגוג, לרנדר מט |  |
| bedside-sconces (גיבור) | `bedside-sconces-cj-linen-wave-flush` | CJ | שמיש | מעטפת (בתוך): 24×20 בתוך 12–24 × 15–26 (AU5) |  |
| curtains | `curtains-aliexpress-linen-blend-s-fold-180502` | AE | שמיש עם הערה | מעטפת (גבולי): נפילה 270 מול 278–282 (‎−3%); אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪89; מידע: 23 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| sill-vase | `sill-vase-cj-cream-fluted-column-25` | CJ | שמיש | מעטפת (בתוך): 8.5×24.7 בתוך 8–14 × 22–30 |  |
| planter | `planter-cj-seagrass-belly` | CJ | שמיש עם הערה | מעטפת (גבולי): 35×37 מול 36–42 × 38–45 (‎−3%); מידע: 8 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| nightstand-vase | `nightstand-vase-aliexpress-handmade-wabi-sabi-vase-665862` | AE | שמיש עם הערה | מעטפת (בתוך): 11×24.5 בתוך 9–14 × 22–28; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪149 |  |
| trinket-dish | `trinket-dish-cj-reactive-glaze-oval-dish-9`<br>speckled charcoal | CJ | שמיש עם הערה | מעטפת (בתוך): 9.5×3 בתוך 8–12 × 2–4; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪39; מידע: הציון מהצלבת המעצב, לא בכרטיס |  |
| candle-holders | `candle-holders-cj-travertine-pedestal` | CJ | שמיש | מעטפת (בתוך): 7×11 בתוך holder 1–12 |  |
| pillowcases | `pillowcases-cj-pure-linen-envelope-pair-48x74` | CJ | שמיש עם הערה | מעטפת (גבולי): 74 מול 65–70 (+6%) |  |
| bedding | `bedding-cj-washed-linen-natural-set`<br>CJCS278387611KP (Natural Linen 1.8M) | CJ | שמיש עם הערה | מעטפת (חסר): מידת השמיכה בסט 1.8 לא מוצהרת (כנראה 220×240 מול 200–220); מידע: מידת השמיכה בכל סט לא מוצהרת |  |
| cushions | `cushions-cj-boucle-teddy`<br>CJZT228600102BY (White 30×50) | CJ | שמיש עם הערה | מעטפת (גבולי): 30×50 מול 33–40 × 55–65 (‎−9% בשני הצירים) |  |
| throw | `throw-cj-cotton-linen-light-gray-200x230` | CJ | שמיש עם הערה | מעטפת (גבולי): 200×230 מקופלת: רוחב 200 מול 180–185 (+8%), עומק כ-38 בתוך 35–45 |  |

### K-boy, חדר הילד (`k-boy.txt`)
| עמדה | כרטיס | ספק | פסק | למה | החלפה |
| --- | --- | --- | --- | --- | --- |
| roman-blind | `roman-blind-aliexpress-modern-beige-color-flat-868827` | AE | **להחליף** | מעטפת (בתוך): מידה בהזמנה: 134–138 אפשרי; express-only: המשלוח היחיד FedEx IP (חינם); NL2 פתוחה, לא למכירה; אין מחיר לצרכן; הכרטיס לא עובר את הסכמה (3 שגיאות); מידע: הציון מהצלבת המעצב, לא בכרטיס | **להשאיר ריק.** שני הרומאיים הנורדיים האחרים ב-7 גם הם באקספרס בלבד: 221993 מסומן ב-no_loss, ול-488628 המשלוח היחיד במטמון הוא FedEx IP (no_loss.py קורא קודם את שורת המשלוח בכרטיס ולא מסמן אותו). חלון בלי וילון; אם NL2 נענית PRE1, 868827 יכול להישאר בפריים |
| bookshelf | `bookshelf-cj-natural-wood-ledge-pair-42-x2` | CJ | שמיש | מעטפת (בתוך): 41.9 × 10.2: שניים בשורה בתוך 40–50, עומק בתוך 8–12; מידע: הציון מהצלבת המעצב, לא בכרטיס |  |
| bedding | `bedding-cj-stripe-cotton-single-set-light-brown`<br>Dark Grey | CJ | **להחליף** | מעטפת (בתוך): 150×200 בתוך 140×200; ציון המעצב 6.5 בחדר הילדים (הכותרת כותבת 7); cannot-compute: אין משלוח ואין הערכה | **`bedding-cj-washed-linen-natural-set`**, ‏1.2M (צבע לבחירת המעצב: White או Dark German Gray לקו הפחם). המעצב 8 ל-kids/bedding ‏(basket-dining-master-kids); סטים למיטה של 1.2; מידת השמיכה בסט לא מוצהרת; הפס הדק של ה-Bible לילד הולך לאיבוד. אותו סט ב-MB0 (Natural 1.8) ובהצעה ל-K-girl, אז צבע שונה בכל חדר. המחיר במטמון ל-1.2 ‏($99.08 flat, ‏$51.83 fitted) לא מתיישב עם ה-1.8 ‏($48.68): לאמת בהרצת ה-API; ₪799 הוא מחיר ה-1.8, ל-1.2 צריך מחיר. תמונת ה-SKU 200 |
| bedspread | `bedspread-cj-muslin-blanket-beige-150x200`<br>Beige | CJ | שמיש | מעטפת (בתוך): 150×200 מקופלת ל-55–60 × 95–100 |  |
| cushions | `cushions-cj-corduroy-windmill-patchwork-pink-40`<br>Milky White + Dark Gray | CJ | שמיש עם הערה | מעטפת (בתוך): 40×40 בתוך 35–40; הכרית הקטנה 30×30 לא קיימת בליסטינג; 2 מתוך סט של 3; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪39 |  |
| soft-toy | `soft-toy-aliexpress-handmade-crochet-bunny-baby-999497`<br>teddy (bear-12cm / bow bear-13.5cm) | AE | **להחליף** | מעטפת (מחוץ): ה-SKU היחיד של דובי 12 ס"מ (ו-13.5) מול 25–35 (‎−52%); הארנבות 25 ס"מ; אין דובי בגודל העמדה בליסטינג; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪69; הכרטיס לא עובר את הסכמה (4 שגיאות); מידע: המעצב: לוודא שה-SKU בחדר באמת ארנבת; 2 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד | **`soft-toy-aliexpress-stuffed-bunny-cloth-dress-063285`**, ‏12000050510684712 (bear: דובי פשתן שמנת עם מטפחת). המעצב 7.5 בנורדי (designer-audit, keep); 35 ס"מ בתוך 25–35; ₪119, לא מפסיד; מלאי במטמון 285; תמונת ה-SKU 200. EN71 לא מוצהר (שער הבטיחות), ובכרטיס חסר בלוק safety. אותו ליסטינג כמו הבובה של K-girl ‏(SKU boy), בחדר אחר. חיות לא נבדקה |
| toy-basket | `basket-cj-jute-rope-cylinder` | CJ | שמיש עם הערה | מעטפת (גבולי): 35×39 מול 32–36 (+8% בגובה); מידע: 4 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| toy-cars | `toy-cars-aliexpress-baby-wooden-toys-beech-975232`<br>PMZ102004-1P (beech) | AE | שמיש עם הערה | מעטפת (אושר במעצב): 8.9 מול 10–13 (‎−11%), המעצב אישר בביקורת 5d; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪29; הכרטיס לא עובר את הסכמה (4 שגיאות) |  |
| rug | ממלא מקום H06 | ישראלי | ממלא מקום | שטיח ישראלי כממלא מקום, לא למכירה (AU1): רשום, לא נבדק | |

### K-girl, חדר הילדה (`k-girl.txt`)
| עמדה | כרטיס | ספק | פסק | למה | החלפה |
| --- | --- | --- | --- | --- | --- |
| roman-blind | `roman-blind-aliexpress-modern-beige-color-flat-868827` | AE | **להחליף** | מעטפת (בתוך): מידה בהזמנה; express-only (FedEx IP); NL2 פתוחה; אין מחיר לצרכן; הכרטיס לא עובר את הסכמה (3 שגיאות); מידע: הציון מהצלבת המעצב, לא בכרטיס | **להשאיר ריק.** כמו ב-K-boy: אין רומאי נורדי ב-7 שלא באקספרס בלבד |
| framed-prints | `framed-prints-cj-charcoal-flower-silhouette-set3-30x40-boy` | CJ | שמיש עם הערה | מעטפת (בתוך): 30×40 בדיוק; 2 מתוך סט של 3; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪99; מידע: הציון מהצלבת המעצב, לא בכרטיס |  |
| bookshelf | `bookshelf-cj-natural-wood-ledge-pair-42-x2` | CJ | שמיש | מעטפת (בתוך): שניים בשורה בתוך 40–50; מידע: הציון מהצלבת המעצב, לא בכרטיס |  |
| bedding | `bedding-cj-muslin-cotton-duvet-dune`<br>CJCS281437509IR (229×173 Dune) | CJ | **להחליף** | מעטפת (מחוץ): המידה הקטנה בליסטינג 173×229 מול 140×200 (+24% / +15%); אין מידת יחיד; מחוץ למעטפת | **`bedding-cj-washed-linen-natural-set`**, ‏1.2M (Milk Apricot או Natural Linen). כמו ב-K-boy: המעצב 8 ל-kids/bedding; מידת השמיכה בסט 1.2 לא מוצהרת; מחיר ה-1.2 במטמון לאמת. צבע שונה מ-MB0 ומ-K-boy |
| bedspread | `bedspread-cj-muslin-blanket-beige-150x200`<br>Beige | CJ | שמיש | מעטפת (בתוך): מקופלת בתוך המעטפת |  |
| cushions | `cushions-cj-corduroy-windmill-patchwork-pink-40`<br>Milky White + Light Elegant Pink | CJ | שמיש עם הערה | מעטפת (בתוך): 40×40 בתוך 35–40; אין 30×30; 2 מתוך סט של 3; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪39 |  |
| soft-toy | `soft-toy-aliexpress-handmade-crochet-bunny-baby-999497`<br>bunny 25cm (שמנת) | AE | שמיש עם הערה | מעטפת (בתוך): 25 בתוך 25–35; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪69; הכרטיס לא עובר את הסכמה (4 שגיאות); מידע: המעצב: לוודא שה-SKU בחדר באמת ארנבת; 2 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| doll | `doll-aliexpress-linen-bunny-doll-063285`<br>12000046795670252 (boy) | AE | שמיש עם הערה | מעטפת (גבולי): 35 בעמידה, בישיבה כ-25 בתוך 22–28 (לא נמדד); שתי ארנבות בפריים (סימון המעצב); מידע: מלאי במטמון ל-SKU boy: 12; המעצב: שמות הווריאציות לא תואמים לתמונות |  |
| toy-basket | `basket-cj-jute-rope-cylinder` | CJ | שמיש עם הערה | מעטפת (גבולי): גובה 39 מול 32–36 (+8%); מידע: 4 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| rug | ממלא מקום H05 | ישראלי | ממלא מקום | שטיח ישראלי כממלא מקום, לא למכירה (AU1): רשום, לא נבדק | |

### B1, המקלחת (`b1.txt`)
| עמדה | כרטיס | ספק | פסק | למה | החלפה |
| --- | --- | --- | --- | --- | --- |
| shower-curtain (גיבור) | `shower-curtain-aliexpress-linen-blend-slub-panel-200x270` | AE | שמיש | מעטפת (אושר במעצב): 200 בתוך 180–240; נפילה 270 מול 200–265 (+2%), המעצב אישר (envelope_ok); מידע: הבטנה: בד לבן מט, לא PEVA מבריק (המעצב) |  |
| wall-sconce (יחידה אחת מכרטיס vanity-sconces) | `vanity-sconces-cj-fluted-resin-updown-white` | CJ | שמיש עם הערה | מעטפת (בקצה): גובה 16 מול 18–24 (‎−11%, בקצה הטווח של כ-10%); רוחב 13 ובליטה 7.5 בתוך המעטפת; הכרטיס מתומחר כזוג (₪259); בעמדה מנורה אחת: צריך מחיר ליחידה |  |
| bath-mat | `bath-mat-cj-tufted-cotton-frame-beige-40x60` | CJ | שמיש | מעטפת (בתוך): 40×60 בתוך 40–50 × 55–70 |  |
| toilet-paper-stand | `toilet-paper-stand-aliexpress-floor-standing-black-763442`<br>1727H | AE | שמיש עם הערה | מעטפת (חסר): אין מידות בכרטיס (התוכנית: כ-65 מול 60–72); אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪69; מידע: מלאי במטמון: 3; לא אומת שה-SKU בלי מחזיק מברשת; מידות לא בכרטיס |  |
| reed-diffuser | `reed-diffuser-cj-travertine-look-bamboo-lid-milktea`<br>Milk Tea | CJ | שמיש עם הערה | מעטפת (חסר): הערכה מהקרטון 7–8 × 11–12, בתוך 6–8 × 10–14; מידע: מידות מוערכות מהקרטון (7–8 × 11–12) |  |
| candle | `candle-cj-ribbed-matte-ceramic-candle-cup-9`<br>white | CJ | שמיש עם הערה | מעטפת (בתוך): 9×9.8 בתוך 8–10; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪39; מידע: הציון מהצלבת המעצב, לא בכרטיס |  |
| shower-dispensers | `shower-dispensers-cj-sand-ribbed-ceramic-pump-bottle` | CJ | שמיש עם הערה | מעטפת (בתוך): 7.5×16.5 בתוך 6–8 × 15–20; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪49; מידע: הציון מהצלבת המעצב, לא בכרטיס |  |

### B2, הכיור (`b2.txt`)
| עמדה | כרטיס | ספק | פסק | למה | החלפה |
| --- | --- | --- | --- | --- | --- |
| vanity-sconces (גיבור) | `vanity-sconces-cj-fluted-resin-updown-white` | CJ | שמיש עם הערה | מעטפת (בקצה): גובה 16 מול 18–26 (‎−11%, בקצה הטווח); רוחב ובליטה בתוך המעטפת |  |
| shower-curtain | `shower-curtain-aliexpress-linen-blend-slub-panel-200x270` | AE | שמיש | מעטפת (אושר במעצב): נפילה 270 מול 200–265 (+2%), המעצב אישר |  |
| shower-dispensers | `shower-dispensers-cj-sand-ribbed-ceramic-pump-bottle` | CJ | שמיש עם הערה | מעטפת (בתוך): בתוך המעטפת; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪49; מידע: הציון מהצלבת המעצב, לא בכרטיס |  |
| soap-dispenser | `soap-dispenser-cj-sand-ribbed-ceramic-pump-bottle` | CJ | שמיש עם הערה | מעטפת (בתוך): 7.5×16.5 בתוך 6–8 × 16–19; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪49; מידע: הציון מהצלבת המעצב, לא בכרטיס |  |
| toothbrush-cup | `toothbrush-cup-cj-silver-travertine-cup` | CJ | שמיש | מעטפת (בתוך): 8×11 בתוך 7–8 × 9–11 |  |
| vanity-vase | `vanity-vase-aliexpress-sand-oat-bud-vase-g-series`<br>G3 | AE | שמיש | מעטפת (בתוך): 7.6×12.8 בתוך 7–9 × 11–14; מידע: 29 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד |  |
| storage-basket | `storage-basket-cj-cotton-rope-basket-43x33x19`<br>cream | CJ | שמיש עם הערה | מעטפת (גבולי): גובה 19 מול 20–23 (‎−5%); מידע: הציון מהצלבת המעצב, לא בכרטיס |  |
| towel-ring | `towel-ring-aliexpress-minimalist-oval-towel-ring-663845`<br>ellipse-black | AE | שמיש עם הערה | מעטפת (חסר): אין מידות בכרטיס; קוטר 16–18 לא אומת; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪49; מידע: אין הצעת משלוח ל-SKU השחור; קוטר 16–18 לא אומת |  |
| hand-towel | `hand-towel-aliexpress-pure-linen-towel-38x55`<br>12000059652334993 (linen 1pc) | AE | שמיש עם הערה | מעטפת (בתוך): 38×55 בתוך 30–40 × 50–60; מידע: ה-SKU בחדר בכרטיס הוא caramel; הפרומפט מבקש linen (מלאי במטמון 5; זוג linen: 95) |  |

### W0, חדר העבודה (`w0.txt`)
| עמדה | כרטיס | ספק | פסק | למה | החלפה |
| --- | --- | --- | --- | --- | --- |
| curtains | `curtains-aliexpress-cotton-linen-curtain-look-902882`<br>12000059241454226 (S Folds, W132×H264) | AE | שמיש עם הערה | מעטפת (גבולי): ה-SKU בחדר בכרטיס W100×H275: פאנל 100 מול 130–150 (‎−23%), מחוץ למעטפת. באותו ליסטינג W132×H264: פאנל בתוך המעטפת, נפילה 264 מול 278–282 (‎−5%); לרנדר את ה-SKU של W132×H264, לא את W100 שבכרטיס (אף וריאנט לא מפסיד באתר); הכרטיס לא עובר את הסכמה (3 שגיאות) |  |
| basket | `basket-cj-jute-cotton-rope-cylinder-30-work`<br>cream cotton | CJ | שמיש עם הערה | מעטפת (בתוך): 30×30 בתוך 28–32; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪79; מידע: הציון מהצלבת המעצב, לא בכרטיס |  |
| waste-basket | `waste-basket-aliexpress-washable-kraft-paper-bin-25x40`<br>grey | AE | שמיש | מעטפת (בתוך): 25 × 30 (שרוול מקופל) בתוך 19–26 × 28–32 |  |
| planter | `planter-aliexpress-nordic-style-natural-seagrass-839727` | AE | **להחליף** | מעטפת (מחוץ): המעצב: הכלי הגדול כ-21 מול 34–38 (reject); ציון המעצב 6.5, reject; אין בכלל שורה בבדיקת ה-no-loss (אין מחיר); הכרטיס לא עובר את הסכמה (3 שגיאות) | **`planter-zendrop-seagrass-belly-38x34`**, ‏1775329665785880587 (Three belly 38×34). המעצב 7 ל-work/planter (keep); 38×34 מול 34–38 × 36–42 (גובה ‎−6%, גבולי); ₪89, לא מפסיד; Zendrop חי היום ובמלאי (אותו מוצר ואותו SKU כמו סל M0); תמונה 200. סיב אחד בחדר לצד סל החבל |
| shelf-boxes | `shelf-boxes-cj-felt-storage-bin-30x24-pair`<br>Light Grey S | CJ | שמיש עם הערה | מעטפת (גבולי): 30×24.5×15 מול 28–32 × 20–24 × 12–18 (+2% בעומק); אין ציון מעצב (7 של הצוות) |  |
| bookends | `bookends-aliexpress-beech-wooden-bookends-219885` | AE | **להחליף** | מעטפת (מחוץ): עומק 8 מול 12–16 (‎−33%); גובה 13 מול 14–18 (‎−7%); מחוץ למעטפת בעומק; אין מחיר לצרכן; המחיר הנמוך שלא מפסיד לפי no_loss.py: ₪49; מידע: 2 וריאנטים מפסידים באתר (SITE1); המק"ט שבחדר לא מפסיד | **להשאיר ריק.** אין חלופה בתוך המעטפת: הבמבוק 897382 (‏7) בעומק 7.5, וקשת הבוק עם הפלדה (12×10.5×17) רק בציון צוות ועומק ‎−12%. או: המעצב מרחיב את העומק לפי AU5 (מ-W0 העומק כמעט לא נראה) |
| desk-organizer | `desk-organizer-cj-cave-stone-pen-cup-8x11`<br>white speckled | CJ | שמיש | מעטפת (בתוך): 8×11 בתוך 7–10 × 10–14; מידע: הציון מהצלבת המעצב, לא בכרטיס |  |
| rug | ממלא מקום H01 | ישראלי | ממלא מקום | שטיח ישראלי כממלא מקום, לא למכירה (AU1): רשום, לא נבדק | |

## 4. ההחלפות לפי פריים
| פריים | עמדה | יוצא | נכנס | מצב הבדיקות של הנכנס |
| --- | --- | --- | --- | --- |
| M0 | accent-sconces | `accent-sconces-cj-travertine-block-updown-8x16` | `wall-sconce-cj-travertine-cube-updown-12`, ‏type-a indoor (LED9W, 12×12×12) | סכמה עוברת; מחיר אין (רצפה ₪189), no-price; תמונה 200; חיות בתור |
| M0 | wall-decor | `wall-decor-aliexpress-natural-raffia-woven-bohemian-763597` | ריק במפורש | — |
| M0 | floor-lamp | `floor-lamp-aliexpress-wabi-sabi-japan-floor-217361` | ריק במפורש | — |
| M0 | rug | `rug-cj-braided-wool-natural` | rugs-il-picks-2026-10-20 H01 NYOKO (טולמנ'ס) | ממלא מקום, לא למכירה, לא נבדק |
| D1 | dining-pendant | `dining-pendant-cj-black-ring-cloth-lantern-50` | `pendant-cj-silk-pumpkin-lantern`, ‏CJYD243199107GT (Diameter 50cm / Warm Light) | סכמה עוברת; מחיר ₪299 ל-SKU שבחדר של הכרטיס, ok; תמונה 200/200; חיות בתור |
| D2 | paper-towel-holder | `paper-towel-holder-cj-beech-upright-31` | `paper-towel-holder-aliexpress-solid-wood-slotted-paper-towel-stand`, ‏12000060575834322 (Style A, הטבעי) | סכמה עוברת; מחיר ₪69 ל-SKU שבחדר של הכרטיס, ok; תמונה 200; חיות בתור |
| H0 | umbrella-stand | `umbrella-stand-cj-solid-wood-umbrella-bucket-hex-19x49` | ריק במפורש | — |
| K-boy | roman-blind | `roman-blind-aliexpress-modern-beige-color-flat-868827` | ריק במפורש | — |
| K-boy | bedding | `bedding-cj-stripe-cotton-single-set-light-brown` | `bedding-cj-washed-linen-natural-set`, ‏1.2M (צבע לבחירת המעצב: White או Dark German Gray לקו הפחם) | סכמה עוברת; מחיר ₪799 ל-SKU שבחדר של הכרטיס, ok; תמונה 200; חיות בתור |
| K-boy | soft-toy | `soft-toy-aliexpress-handmade-crochet-bunny-baby-999497` | `soft-toy-aliexpress-stuffed-bunny-cloth-dress-063285`, ‏12000050510684712 (bear: דובי פשתן שמנת עם מטפחת) | סכמה לא עוברת (3); מחיר ₪119 ל-SKU שבחדר של הכרטיס, ok; תמונה 200; חיות בתור |
| K-girl | roman-blind | `roman-blind-aliexpress-modern-beige-color-flat-868827` | ריק במפורש | — |
| K-girl | bedding | `bedding-cj-muslin-cotton-duvet-dune` | `bedding-cj-washed-linen-natural-set`, ‏1.2M (Milk Apricot או Natural Linen) | סכמה עוברת; מחיר ₪799 ל-SKU שבחדר של הכרטיס, ok; תמונה 200; חיות בתור |
| W0 | planter | `planter-aliexpress-nordic-style-natural-seagrass-839727` | `planter-zendrop-seagrass-belly-38x34`, ‏1775329665785880587 (Three belly 38×34) | סכמה עוברת; מחיר ₪89 ל-SKU שבחדר של הכרטיס, ok; תמונה 200; חיות חי (Zendrop) |
| W0 | bookends | `bookends-aliexpress-beech-wooden-bookends-219885` | ריק במפורש | — |

**ל-render-agent:** בעמדה שמתרוקנת, צורת-המקום וגם האור שלה יוצאים מה-clay (סעיף 2.3 בתוכנית). בעמדה שמקבלת מוצר אחר, צורת-המקום לפי המידות של הכרטיס החדש.

## 5. מה צריך את המשתמש
- **NL2:** פתוחה. שני מוצרים באקספרס בלבד יוצאים מהפריימים, השטיח הקלוע של M0 (DHL ‏$491, מפסיד ב-₪1,299) והווילון הרומאי של חדרי הילדים (FedEx בלבד). אם התשובה היא PRE1 ('המלאי אינו זמין כעת'), שניהם יכולים להישאר בהדמיה עם התווית. בלי תשובה: NYOKO כממלא מקום ב-M0, וחלון בלי וילון בחדרי הילדים
- **RND2:** פתוחה. הגיבור של M0 הוא הטריפטיך. אין לו ציון מעצב (8 של צוות AliExpress), הוא above-market ‏(₪199 מול ₪175), לחנות ביקורת אחת, וזכויות התמונה לא ברורות. הוא נשאר בפריים כמועמד; צריך את 'כן' שלך ואת ציון המעצב
- **plan-Q2:** שאלה 2 בתוכנית (פנס עמודי כמנורת רגל בנורדי) עדיין פתוחה. בלי היתר, מנורת הרגל יוצאת מ-M0, ונשארות שלוש טיפולוגיות דולקות במקום ארבע
- **plan-Q8 / AU5:** מוצרים מחוץ למעטפת ביותר מ-10%, שהוחלפו או רוקנו: מנורות הטרוורטין ב-M0 (רוחב ‎−20%), הרפיה ב-M0 (‎−14%), פנס פינת האוכל (גובה +20%), שמיכת Dune (+24%), תומכי הספרים (עומק ‎−33%), הדובי (12 מול 25). לפי AU5 המעצב יכול להרחיב מעטפת כשהמוצר עובד בפריים, ומדווח לך. מנורות המקלחת (16 מול 18, ‎−11%) נשארו כגבוליות עד שאלה 8
- **prices:** 25 כרטיסים בפריימים בלי מחיר לצרכן (מחיר הרצפה שלא מפסיד ידוע לכולם חוץ מאחד). לא חוסם הדמיה, חוסם מכירה
- **liveness:** 79 כרטיסי CJ ו-AliExpress לא נבדקו לחיות (אין מפתח CJ בסשן; AliExpress בסשן אחר). התור מוכן, ובראשו מלאי נמוך במטמון: הכד בכניסה (2), מעמד הנייר (3), צלחות הברזל (5), מגבת הפשתן linen ‏1pc ‏(5), היתדות (11), הבובה boy ‏(12). כל "שמיש" של CJ ו-AliExpress מותנה בהרצה הזו
- **hero-gaps:** אחרי הבדיקה: לגיבור של D1 יש מועמד חלופי (פנס משי 50); בכניסה מעמד המטריות יוצא (לא גיבור). חדרי הילדים בלי וילון רומאי, W0 בלי תומכי ספרים
- **stand-in-images:** תמונות חמשת השטיחים הישראליים לא נמצאות: הנתיבים ב-rugs-il-picks-2026-10-20.json מצביעים לתיקיית scratchpad שכבר לא קיימת. render-agent מוריד מחדש מדף הספק לפני הרינדור (מ2 בתוכנית)

## 6. הערות למעצב (לתיקון הפרומפטים בשלב 2)
- הפרומפטים v7 (‏`<frame>-v7.txt`, נכתבו במקביל ב-2026-11-02) משאירים את מוצרי v6 עד הבדיקה הזו. ההחלפות כאן נכנסות שורה ורפרנס; החלפה ב-M0 (מנורות הטרוורטין, הרפיה, מנורת הרגל, השטיח) משנה גם את הנוף בשורה j של h0-v7 ובשורה c של c0-v7 (מ2 ב-render-wow-pass).
- הכותרות של h0-B, ‏k-boy ו-w0 נושאות ציון צוות במקום ציון המעצב: מעמד המטריות 7 (המעצב 6.5), מצעי הפסים 7 (המעצב 6.5), העציץ 839727 ‏7 (המעצב 6.5, reject).
- h0-B: הכד 906575 מסומן 'team fit, not designer-audited', אבל בהצלבה של 14.10 ‏(basket-bath-hall-work) המעצב נתן לו 8 ב-hall/console-vessel.
- d2 והתוכנית קוראים לצנצנות zendrop-2814530 (שם הקובץ). מזהה הכרטיס: canisters-zendrop-matte-ceramic-bamboo-lid-sml.
- k-boy: 'teddy SKU in cream' לא קיים בגודל: הדובי בליסטינג 999497 הוא 12 ס"מ. ההצעה: ה-bear של 063285.
- k-girl: לשמיכת Dune אין מידת יחיד (הקטנה 173×229).
- w0: ה-SKU בחדר של 902882 הוא W100, צר מהפאנל; באותו ליסטינג W132×H264.
- m0: כרית הפחם 30×50 קיימת כ-SKU נפרד (CJZT113551671SH); ה-SKU בחדר בכרטיס 50×50.
- b2: מגבת הידיים, ה-SKU בחדר בכרטיס caramel; לבקש עדכון ל-linen אם זה הצבע הנבחר (מלאי 1pc במטמון: 5).
- B1: מנורת הקיר היא יחידה אחת מכרטיס שמתומחר כזוג.

## 7. מה לא נבדק ולמה
- **חיות CJ ו-AliExpress (79 כרטיסים, ועוד 4 מההחלפות):** בסשן הזה אין `CJ_API_KEY`, ו-AliExpress רץ בסשן נפרד. לא גירדתי דפים ולא השתמשתי ב-scraper. התור: `data/leads/final-2026-10-13/round5/liveness-queue-2026-11-02.json` (מזהה כרטיס, ספק, מזהה מוצר, ה-SKU שבחדר וה-SKU שבפרומפט, עדיפות לפי מלאי נמוך במטמון).
- **נאמנות חזותית:** בדקתי שהתמונות זמינות, לא הסתכלתי עליהן. השיפוט על התמונה נשאר של המעצב ושל QA.
- **השטיחים הישראליים:** רשומים בלבד (סעיף 8).

## 8. ממלאי המקום (רשומים, לא נבדקו)
| בחירה | שטיח | פריימים | עמדה | הערה |
| --- | --- | --- | --- | --- |
| H03 | ASKO אוף-וויט (טולמנ'ס) | D1, D2 | dining-room/dining-rug | מידה מותאמת 230×220 |
| H07 | ראנר מדינה 60×280 (דאר מרקש) | D1, D2 | dining-room/kitchen-runner | פלומה |
| H06 | YUKI 140×200 (נורטלי) | K-boy | kids/rug | התמונה קטנה |
| H05 | LUMI 140×200 (נורטלי) | K-girl | kids/rug | התמונה קטנה |
| H01 | NYOKO 170×240 (טולמנ'ס) | W0 | work/rug | work/rug היא עמדה מתה של AU2 (excluded-slots.json); ממלא המקום הוא בחירת המעצב. מוצע גם ל-M0 במקום השטיח הקלוע |

