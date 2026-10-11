# תמחור התחלתי — סלון (2026-10-11)

קובץ הנתונים: `living-room-2026-10-11.json` (73 מוצרים). כל המחירים בש"ח כולל מע"מ, למכירה אחת (`price_for_qty`).

## שיטה

- **שווי בישראל:** לכל מוצר 3–5 מוצרים דומים (מידה, חומר, מראה) מ-IKEA, Fox Home, Home Style, Terminal X, זארה הום, Nord Light, Dealteora, Carpetshop וחנויות עיצוב. המחיר הטיפוסי הוא רמת הביניים, לא הזול של איקאה. מחירי השוואה הם המחיר שהלקוח משלם היום; מחיר מחוק מופיע בנפרד (`list_price`).
- **מחיר:** הסכום ללקוח (מחיר + ₪29, חינם מ-₪299) נמוך בכ-8–18% מהטיפוסי, עוד לפני דמי המשלוח של הרשתות (₪15–40). במוצר עיצובי או בזוג/סט הוא קרוב יותר לטיפוסי. כל המחירים מסתיימים ב-9. כשמחיר טבעי יצא ממש מתחת ל-₪299 נבחר ₪299, כי כך המשלוח חינם.
- **מרווח (לדיווח בלבד):** שער 3.3, מע"מ 18%, סליקה 2% + ₪1.2, שמורת החזרות 8% מהנטו, CAC ₪71.4 לפריט. משלוח לכמות: יחידה + (q−1)×(יחידה−3.72)$. המחיר לא הועלה כדי להגיע ל-40%.
- **דגלים (VR1):** `ok` ≥ 40%, `below-floor` 0–40%, `loss` תרומה שלילית. `slot_alternative_ok` = true רק אם יש בעמדה חלופה שעוברת 40% **וגם** ציון הנורדי שלה לא נמוך יותר (עיצוב לפני רווחיות). אף מוצר לא מומלץ להוצאה בגלל מרווח.

## שורה תחתונה

- **1 ok, 45 below-floor, 27 loss.** המוצר היחיד שעובר 40% הוא סט ציפיות הפרחים (ציון נורדי 4.0), ולכן **בכל 18 העמדות החריגה מרצפת ה-40% חלה**.
- חציון המחיר: 72% מהטיפוסי בישראל; חציון הסכום ללקוח (עם משלוח) -14% מהטיפוסי. חציון המרווח 11.0%.
- הסיבה היא המשלוח מסין לפי יחידה, לא המחיר: בפריטים קטנים המשלוח גבוה מהמוצר, ובמנורות, באגרטלים, בתמונה ובשטיח הוא כמעט כל העלות.
- **דמי המשלוח ₪29 משנים את התמונה בפריטים זולים:** כשהלקוח משלם משלוח, חציון המרווח במוצרים שמתחת ל-₪299 הוא 30%.
- **סטים במשלוח מאוחד:** סט 4 ציפיות CJ ב-₪196 (4×₪49) במשלוח אחד מגיע לחציון מרווח של 50%, לעומת כ-26% לציפית בודדת. זה הכלי החזק ביותר לטקסטיל.

## טבלה

| מוצר | מחיר | טיפוסי בישראל | סה"כ ללקוח | מול טיפוסי | מרווח | דגל | נורדי |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `accent-sconces-aliexpress-indoor-stone-wall-lamp` | ₪299 | ₪349 | ₪299 | -14% | -8.9% | loss | 8.0 |
| `accent-sconces-cj-ribbed-travertine-half-cylinder-wood-bracket` (זוג) | ₪599 | ₪698 | ₪599 | -14% | 29.9% | below-floor | 7.5 |
| `basket-cj-cotton-rope-white` | ₪89 | ₪139 | ₪118 | -15% | -31.4% | loss | 8.0 |
| `basket-cj-jute-rope-cylinder` | ₪79 | ₪129 | ₪108 | -16% | -31.8% | loss | 8.5 |
| `basket-cj-seagrass-belly` | ₪89 | ₪139 | ₪118 | -15% | -2.7% | loss | 7.5 |
| `basket-cj-seagrass-belly-xl` | ₪89 | ₪139 | ₪118 | -15% | 21.5% | below-floor | 7.0 |
| `basket-zendrop-seagrass-belly-foldable-38` | ₪89 | ₪139 | ₪118 | -15% | 8.9% | below-floor | 7.0 |
| `bowl-cj-reactive-white-rimmed-plate-21` | ₪59 | ₪99 | ₪88 | -11% | -44.0% | loss | 6.0 |
| `bowl-cj-speckled-ivory-wide-bowl-21` | ₪79 | ₪119 | ₪108 | -9% | 11.8% | below-floor | 7.5 |
| `candle-holders-cj-travertine-pedestal` (זוג) | ₪199 | ₪260 | ₪228 | -12% | 7.1% | below-floor | 8.5 |
| `curtains-aliexpress-cotton-linen-curtain-look-902882` (זוג) | ₪179 | ₪249 | ₪208 | -16% | 27.1% | below-floor | 8.0 |
| `curtains-aliexpress-cotton-linen-texture-translucent` (זוג) | ₪299 | ₪349 | ₪299 | -14% | 8.6% | below-floor | 6.5 |
| `curtains-aliexpress-cotton-linen-texture-translucent-091154` (זוג) | ₪299 | ₪349 | ₪299 | -14% | -6.1% | loss | 6.5 |
| `curtains-cj-japanese-linen-half-shade` | ₪229 | ₪299 | ₪258 | -14% | 15.5% | below-floor | 7.5 |
| `cushions-aliexpress-farmhouse-floral-pillow-covers-166217` | ₪129 | ₪178 | ₪158 | -11% | 49.7% | ok | 4.0 |
| `cushions-aliexpress-fashion-modern-wabi-sabi-464203` | ₪59 | ₪99 | ₪88 | -11% | -12.6% | loss | 7.0 |
| `cushions-aliexpress-textured-boucle-throw-pillow` | ₪59 | ₪99 | ₪88 | -11% | 0.4% | below-floor | 7.5 |
| `cushions-cj-boucle-teddy` | ₪59 | ₪99 | ₪88 | -11% | 8.0% | below-floor | 8.5 |
| `cushions-cj-bubble-chenille-bean-green` | ₪49 | ₪89 | ₪78 | -12% | 17.0% | below-floor | 7.0 |
| `cushions-cj-chenille-wide-wale-green` | ₪49 | ₪89 | ₪78 | -12% | 30.6% | below-floor | 6.5 |
| `cushions-cj-corduroy-patchwork` | ₪49 | ₪89 | ₪78 | -12% | 25.1% | below-floor | 7.0 |
| `cushions-cj-knitted-chenille-bean-green` | ₪49 | ₪89 | ₪78 | -12% | 26.5% | below-floor | 8.0 |
| `cushions-cj-linen-look-charcoal` | ₪49 | ₪89 | ₪78 | -12% | 20.9% | below-floor | 7.5 |
| `cushions-cj-linen-look-ivory` | ₪59 | ₪99 | ₪88 | -11% | 0.5% | below-floor | 7.0 |
| `cushions-cj-sandstone-chenille-flange` | ₪49 | ₪89 | ₪78 | -12% | 11.6% | below-floor | 7.0 |
| `cushions-cj-washed-cotton-frayed` | ₪49 | ₪89 | ₪78 | -12% | 27.8% | below-floor | 6.0 |
| `cushions-cj-wide-stripe-corduroy-light-green` | ₪49 | ₪89 | ₪78 | -12% | 25.7% | below-floor | 6.5 |
| `cushions-cj-wide-wale-corduroy` | ₪49 | ₪89 | ₪78 | -12% | 25.6% | below-floor | 7.0 |
| `floor-lamp-cj-black-drum-linen` | ₪229 | ₪299 | ₪258 | -14% | 14.8% | below-floor | 6.5 |
| `framed-art-cj-morandi-triptych-sage` | ₪379 | ₪449 | ₪379 | -16% | -61.3% | loss | 6.5 |
| `magazine-holder-cj-arch-iron-cane` | ₪129 | ₪179 | ₪158 | -12% | -31.6% | loss | 5.5 |
| `magazine-holder-cj-felt-log-basket` | ₪79 | ₪119 | ₪108 | -9% | 28.7% | below-floor | 7.0 |
| `magazine-holder-cj-felt-snap-bucket` | ₪59 | ₪99 | ₪88 | -11% | 14.2% | below-floor | 5.5 |
| `magazine-holder-cj-gunmetal-leather-strap` | ₪149 | ₪199 | ₪178 | -11% | -69.8% | loss | 5.0 |
| `pendant-cj-pleated-pumpkin-lantern-40` | ₪299 | ₪349 | ₪299 | -14% | -42.2% | loss | 8.5 |
| `pendant-cj-silk-pumpkin-lantern` | ₪299 | ₪349 | ₪299 | -14% | 12.3% | below-floor | 7.0 |
| `pendant-cj-tiered-fabric-drum` | ₪329 | ₪399 | ₪329 | -18% | -26.9% | loss | 6.0 |
| `planter-cj-cement-ribbed-belly` | ₪229 | ₪299 | ₪258 | -14% | 7.8% | below-floor | 6.0 |
| `planter-cj-seagrass-belly` | ₪89 | ₪139 | ₪118 | -15% | -2.7% | loss | 7.0 |
| `planter-zendrop-seagrass-belly-basket-45` | ₪99 | ₪149 | ₪128 | -14% | 32.2% | below-floor | 7.0 |
| `pouf-cj-cotton-knit-ball-cover` | ₪99 | ₪149 | ₪128 | -14% | -63.6% | loss | 7.5 |
| `rug-cj-braided-wool-natural` | ₪1,299 | ₪1,590 | ₪1,299 | -18% | -137.9% | loss | 8.0 |
| `sofa-cover-cj-bubble-stretch-slipcover` | ₪149 | ₪199 | ₪178 | -11% | -53.8% | loss | 3.5 |
| `sofa-cover-cj-cotton-muslin-fringe` | ₪129 | ₪179 | ₪158 | -12% | 11.0% | below-floor | 8.0 |
| `sofa-cover-cj-knit-thick-slipcover` | ₪149 | ₪199 | ₪178 | -11% | 16.2% | below-floor | 4.0 |
| `sofa-cover-cj-linen-feel-chenille-slipcover` | ₪179 | ₪249 | ₪208 | -16% | 21.3% | below-floor | 6.0 |
| `sofa-cover-cj-polar-fleece-jacquard-slipcover` | ₪149 | ₪199 | ₪178 | -11% | -8.2% | loss | 2.5 |
| `sofa-cover-cj-waffle-jacquard-stretch-slipcover` | ₪149 | ₪199 | ₪178 | -11% | -4.9% | loss | 3.0 |
| `sofa-cover-cj-washed-hemp-throw` | ₪229 | ₪299 | ₪258 | -14% | 4.4% | below-floor | 7.0 |
| `table-runner-aliexpress-boho-macrame-table-runners-263532` | ₪69 | ₪119 | ₪98 | -18% | 32.4% | below-floor | 3.0 |
| `table-runner-aliexpress-boho-table-runner-macrame-072806` | ₪69 | ₪119 | ₪98 | -18% | 26.0% | below-floor | 3.0 |
| `table-runner-aliexpress-nordic-table-runner-kitchen-244347` | ₪69 | ₪119 | ₪98 | -18% | 35.2% | below-floor | 5.5 |
| `table-runner-cj-linen-look-sage-fringe` | ₪79 | ₪129 | ₪108 | -16% | 33.3% | below-floor | 7.0 |
| `table-runner-cj-linen-look-triangle-end` | ₪79 | ₪129 | ₪108 | -16% | 38.4% | below-floor | 5.5 |
| `table-runner-zendrop-ben-white-linen-look-33x183` | ₪79 | ₪129 | ₪108 | -16% | 18.4% | below-floor | 7.0 |
| `vase-aliexpress-vintage-distressed-clay-vase-589009` | ₪229 | ₪279 | ₪258 | -8% | 35.0% | below-floor | 8.5 |
| `vase-cj-charcoal-carved` | ₪199 | ₪279 | ₪228 | -18% | -4.8% | loss | 6.0 |
| `vase-cj-coarse-sand-white-tall` | ₪229 | ₪279 | ₪258 | -8% | 8.9% | below-floor | 7.5 |
| `vase-cj-faceted-cream` | ₪199 | ₪279 | ₪228 | -18% | -8.3% | loss | 5.5 |
| `vase-cj-french-matte-white-35` | ₪229 | ₪299 | ₪258 | -14% | -34.0% | loss | 7.0 |
| `vase-cj-matte-moon-jar-white` | ₪149 | ₪199 | ₪178 | -11% | -5.5% | loss | 5.5 |
| `vase-cj-textured-white-stoneware` | ₪229 | ₪279 | ₪258 | -8% | 25.2% | below-floor | 8.5 |
| `vase-cj-white-plum-hand-thrown` | ₪229 | ₪279 | ₪258 | -8% | -2.2% | loss | 7.5 |
| `vase-cj-white-textured-jar` | ₪149 | ₪199 | ₪178 | -11% | -15.4% | loss | 6.0 |
| `wall-decor-aliexpress-natural-raffia-woven-bohemian-763597` | ₪89 | ₪139 | ₪118 | -15% | 26.8% | below-floor | 7.0 |
| `wall-decor-cj-macrame-dowel-50x70` | ₪119 | ₪169 | ₪148 | -12% | 27.3% | below-floor | 6.5 |
| `wall-decor-zendrop-macrame-diamond-dowel-small` | ₪59 | ₪99 | ₪88 | -11% | -23.4% | loss | 5.0 |
| `wall-sconce-cj-black-swing-arm-fabric` | ₪149 | ₪199 | ₪178 | -11% | -221.7% | loss | 7.0 |
| `wall-sconce-cj-travertine-cone-walnut` | ₪299 | ₪349 | ₪299 | -14% | 28.4% | below-floor | 6.0 |
| `wall-sconce-cj-travertine-disc-25` | ₪379 | ₪449 | ₪379 | -16% | 13.3% | below-floor | 5.0 |
| `wall-sconce-cj-travertine-dome-15-alt` | ₪299 | ₪349 | ₪299 | -14% | 26.2% | below-floor | 7.0 |
| `wall-sconce-cj-travertine-dome-15-pull` | ₪299 | ₪349 | ₪299 | -14% | -42.2% | loss | 6.5 |
| `wall-sconce-cj-travertine-half-bowl-15` | ₪229 | ₪299 | ₪258 | -14% | 35.2% | below-floor | 6.0 |

## מתחת לרצפה ובהפסד, לפי עמדה

בכל העמדות אין חלופה שעוברת 40% ויפה לפחות כמו המוצר, ולכן **החריגה נדרשת בכולן** (מסומן ⚑). המוצרים נשארים; ההמלצה היא רק איך לשפר את המרווח.

### זוג מנורות טרוורטין (`accent-sconces`) ⚑ חריגה נדרשת

- `accent-sconces-aliexpress-indoor-stone-wall-lamp` — loss, -8.9% (ב-₪299, נורדי 8.0). עלות היחידה $51.94 גבוהה: לחפש את אותו גליל אצל ספק זול יותר או ב-CJ
- `accent-sconces-cj-ribbed-travertine-half-cylinder-wood-bracket` — below-floor, 29.9% (ב-₪599, נורדי 7.5). המשלוח $23.90 ליחידה הוא רוב העלות: לבדוק משלוח מאוחד לזוג או מלאי מקומי

### סל (`basket`) ⚑ חריגה נדרשת

- `basket-cj-jute-rope-cylinder` — loss, -31.8% (ב-₪79, נורדי 8.5). המשלוח $19.11 פי 4 מהמוצר: לבדוק Liquid Line/משלוח מאוחד או ספק אחר לאותו סל
- `basket-cj-cotton-rope-white` — loss, -31.4% (ב-₪89, נורדי 8.0). המשלוח $14.44 ועלות $12.86: למכור בסט עם כריות או לחפש ספק זול יותר
- `basket-cj-seagrass-belly` — loss, -2.7% (ב-₪89, נורדי 7.5). אותו סל זמין זול יותר ב-Zendrop ובווריאנט XL: להעביר לספק הזול
- `basket-cj-seagrass-belly-xl` — below-floor, 21.5% (ב-₪89, נורדי 7.0). לשפר בסט (סל + עציץ באותה שפה) או במשלוח מאוחד
- `basket-zendrop-seagrass-belly-foldable-38` — below-floor, 8.9% (ב-₪89, נורדי 7.0). משלוח Zendrop $13.38: לבדוק את ה-38×34 מכרטיס העציץ, שהמשלוח שלו זול יותר

### קערה (`bowl`) ⚑ חריגה נדרשת

- `bowl-cj-speckled-ivory-wide-bowl-21` — below-floor, 11.8% (ב-₪79, נורדי 7.5). המשלוח $11.92 פי 3.4 מהמוצר: למכור בזוג או בסט שולחן במשלוח מאוחד
- `bowl-cj-reactive-white-rimmed-plate-21` — loss, -44.0% (ב-₪59, נורדי 6.0). משלוח $10.27 על מוצר $9.62: למכור בסט עם הקערה השנייה או בזוג

### פמוטים (`candle-holders`) ⚑ חריגה נדרשת

- `candle-holders-cj-travertine-pedestal` — below-floor, 7.1% (ב-₪199, נורדי 8.5). המשלוח (2 יחידות) $23.60 והאבן כבדה: לבדוק משלוח מאוחד בסט שולחן הקפה

### וילונות (`curtains`) ⚑ חריגה נדרשת

- `curtains-aliexpress-cotton-linen-curtain-look-902882` — below-floor, 27.1% (ב-₪179, נורדי 8.0). עלות $13.19 לפאנל: לבדוק אם יש מחיר לזוג אצל אותו ספק
- `curtains-cj-japanese-linen-half-shade` — below-floor, 15.5% (ב-₪229, נורדי 7.5). המשלוח $26.67 גבוה מהמוצר: לבדוק Liquid Line או מלאי מקומי לווילונות
- `curtains-aliexpress-cotton-linen-texture-translucent-091154` — loss, -6.1% (ב-₪299, נורדי 6.5). אותו בד בדיוק נמכר זול יותר ב-ZJBYZHOUSEHOLD ($29.94): להעביר לספק הזול
- `curtains-aliexpress-cotton-linen-texture-translucent` — below-floor, 8.6% (ב-₪299, נורדי 6.5). עלות $29.94 לפאנל: לבחור רוחב 130–150 (זול יותר וגם תואם לחדר)

### כריות (`cushions`) ⚑ חריגה נדרשת

- `cushions-cj-boucle-teddy` — below-floor, 8.0% (ב-₪59, נורדי 8.5). המשלוח $8.39 גבוה מהמוצר: למכור כסט 4 כריות במשלוח מאוחד
- `cushions-cj-knitted-chenille-bean-green` — below-floor, 26.5% (ב-₪49, נורדי 8.0). למכור כסט 4 כריות במשלוח מאוחד
- `cushions-aliexpress-textured-boucle-throw-pillow` — below-floor, 0.4% (ב-₪59, נורדי 7.5). לא ודאי אם העלות ליחידה: אם זה סט, המרווח טוב; לבדוק מול הספק
- `cushions-cj-linen-look-charcoal` — below-floor, 20.9% (ב-₪49, נורדי 7.5). למכור כסט 4 כריות במשלוח מאוחד
- `cushions-aliexpress-fashion-modern-wabi-sabi-464203` — loss, -12.6% (ב-₪59, נורדי 7.0). לא ודאי אם העלות ליחידה או לסט: אם לסט, המרווח קופץ; לבדוק מול הספק
- `cushions-cj-bubble-chenille-bean-green` — below-floor, 17.0% (ב-₪49, נורדי 7.0). למכור כסט 4 כריות במשלוח מאוחד
- `cushions-cj-corduroy-patchwork` — below-floor, 25.1% (ב-₪49, נורדי 7.0). למכור כסט 4 כריות במשלוח מאוחד
- `cushions-cj-linen-look-ivory` — below-floor, 0.5% (ב-₪59, נורדי 7.0). המילוי מכפיל את המשלוח ($10.78): למכור ציפית בלבד או במשלוח מאוחד
- `cushions-cj-sandstone-chenille-flange` — below-floor, 11.6% (ב-₪49, נורדי 7.0). למכור כסט 4 כריות במשלוח מאוחד
- `cushions-cj-wide-wale-corduroy` — below-floor, 25.6% (ב-₪49, נורדי 7.0). למכור כסט 4 כריות במשלוח מאוחד
- `cushions-cj-chenille-wide-wale-green` — below-floor, 30.6% (ב-₪49, נורדי 6.5). למכור כסט 4 כריות במשלוח מאוחד
- `cushions-cj-wide-stripe-corduroy-light-green` — below-floor, 25.7% (ב-₪49, נורדי 6.5). למכור כסט 4 כריות במשלוח מאוחד
- `cushions-cj-washed-cotton-frayed` — below-floor, 27.8% (ב-₪49, נורדי 6.0). למכור כסט 4 כריות במשלוח מאוחד

### מנורה עומדת (`floor-lamp`) ⚑ חריגה נדרשת

- `floor-lamp-cj-black-drum-linen` — below-floor, 14.8% (ב-₪229, נורדי 6.5). המשלוח $34.62 (חבילה גדולה): לבדוק מלאי מקומי או ספק עם אריזה שטוחה

### תמונה (`framed-art`) ⚑ חריגה נדרשת

- `framed-art-cj-morandi-triptych-sage` — loss, -61.3% (ב-₪379, נורדי 6.5). המשלוח $130.82 פי 8 מהמוצר: הדפסה ומסגור מקומיים, או לשלוח רק את ההדפסים מגולגלים

### מחזיק עיתונים (`magazine-holder`) ⚑ חריגה נדרשת

- `magazine-holder-cj-felt-log-basket` — below-floor, 28.7% (ב-₪79, נורדי 7.0). לשפר במשלוח מאוחד עם פריטי טקסטיל
- `magazine-holder-cj-arch-iron-cane` — loss, -31.6% (ב-₪129, נורדי 5.5). עלות $21.96 ומשלוח $17.84: לחפש ספק אחר לאותו מעמד
- `magazine-holder-cj-felt-snap-bucket` — below-floor, 14.2% (ב-₪59, נורדי 5.5). לשפר במשלוח מאוחד עם פריטי טקסטיל
- `magazine-holder-cj-gunmetal-leather-strap` — loss, -69.8% (ב-₪149, נורדי 5.0). עלות $31.08 ומשלוח $29.57: לחפש ספק אחר לאותו מעמד

### מנורת תלייה (`pendant`) ⚑ חריגה נדרשת

- `pendant-cj-pleated-pumpkin-lantern-40` — loss, -42.2% (ב-₪299, נורדי 8.5). המשלוח $54.80 גבוה מהמוצר: מלאי מקומי או ספק עם אריזה שטוחה
- `pendant-cj-silk-pumpkin-lantern` — below-floor, 12.3% (ב-₪299, נורדי 7.0). לבדוק משלוח מאוחד או מלאי מקומי
- `pendant-cj-tiered-fabric-drum` — loss, -26.9% (ב-₪329, נורדי 6.0). המשלוח $54.80 (קרטון 54 ס"מ): מלאי מקומי או ספק עם אריזה שטוחה

### עציץ (`planter`) ⚑ חריגה נדרשת

- `planter-cj-seagrass-belly` — loss, -2.7% (ב-₪89, נורדי 7.0). אותו סל זמין ב-Zendrop D45 במשלוח זול יותר: להעביר לספק הזול
- `planter-zendrop-seagrass-belly-basket-45` — below-floor, 32.2% (ב-₪99, נורדי 7.0). קרוב לרצפה: למכור בסט עם סל הספה
- `planter-cj-cement-ribbed-belly` — below-floor, 7.8% (ב-₪229, נורדי 6.0). מלט כבד ושביר: עדיף מלאי מקומי או ספק ישראלי לאותו כד

### פוף (`pouf`) ⚑ חריגה נדרשת

- `pouf-cj-cotton-knit-ball-cover` — loss, -63.6% (ב-₪99, נורדי 7.5). כיסוי בלבד ומשלוח $21.88: למכור עם מילוי מקומי, או ספק עם פוף ממולא

### שטיח (`rug`) ⚑ חריגה נדרשת

- `rug-cj-braided-wool-natural` — loss, -137.9% (ב-₪1,299, נורדי 8.0). רק DHL $491 (12 ק"ג): משלוח ימי או מלאי מקומי, או ספק שטיחים ישראלי

### כיסוי ספה / שמיכה (`sofa-cover`) ⚑ חריגה נדרשת

- `sofa-cover-cj-cotton-muslin-fringe` — below-floor, 11.0% (ב-₪129, נורדי 8.0). לשפר בסט ספה (שמיכה + 2 ציפיות) במשלוח מאוחד
- `sofa-cover-cj-washed-hemp-throw` — below-floor, 4.4% (ב-₪229, נורדי 7.0). עלות $37.98: לבדוק ספק אחר לאותה שמיכה או את מידת 100×150
- `sofa-cover-cj-linen-feel-chenille-slipcover` — below-floor, 21.3% (ב-₪179, נורדי 6.0). לשפר בסט ספה עם כריות במשלוח מאוחד
- `sofa-cover-cj-knit-thick-slipcover` — below-floor, 16.2% (ב-₪149, נורדי 4.0). המשלוח $20.75 פי 3 מהמוצר: משלוח מאוחד
- `sofa-cover-cj-bubble-stretch-slipcover` — loss, -53.8% (ב-₪149, נורדי 3.5). עלות $24.05 ומשלוח $30.46: לחפש ספק זול יותר לאותו כיסוי
- `sofa-cover-cj-waffle-jacquard-stretch-slipcover` — loss, -4.9% (ב-₪149, נורדי 3.0). המשלוח $22.89: משלוח מאוחד
- `sofa-cover-cj-polar-fleece-jacquard-slipcover` — loss, -8.2% (ב-₪149, נורדי 2.5). המשלוח $22.20: משלוח מאוחד

### ראנר (`table-runner`) ⚑ חריגה נדרשת

- `table-runner-cj-linen-look-sage-fringe` — below-floor, 33.3% (ב-₪79, נורדי 7.0). לשפר בסט שולחן (ראנר + קערה + פמוטים)
- `table-runner-zendrop-ben-white-linen-look-33x183` — below-floor, 18.4% (ב-₪79, נורדי 7.0). המשלוח $12.42 פי 7 מהמוצר: לעבור לאותו ראנר ב-CJ ($7.32) או לשלב בסט
- `table-runner-aliexpress-nordic-table-runner-kitchen-244347` — below-floor, 35.2% (ב-₪69, נורדי 5.5). קרוב לרצפה: לשפר בסט שולחן
- `table-runner-cj-linen-look-triangle-end` — below-floor, 38.4% (ב-₪79, נורדי 5.5). לשפר בסט שולחן
- `table-runner-aliexpress-boho-macrame-table-runners-263532` — below-floor, 32.4% (ב-₪69, נורדי 3.0). קרוב לרצפה: לשפר בסט שולחן
- `table-runner-aliexpress-boho-table-runner-macrame-072806` — below-floor, 26.0% (ב-₪69, נורדי 3.0). לשפר בסט שולחן

### אגרטל (`vase`) ⚑ חריגה נדרשת

- `vase-aliexpress-vintage-distressed-clay-vase-589009` — below-floor, 35.0% (ב-₪229, נורדי 8.5). המשלוח $27.25 פי 6 מהמוצר: למכור בסט אגרטלים או במשלוח מאוחד
- `vase-cj-textured-white-stoneware` — below-floor, 25.2% (ב-₪229, נורדי 8.5). המשלוח $27.31 פי 2.7 מהמוצר: מלאי מקומי לאגרטלים או סט
- `vase-cj-coarse-sand-white-tall` — below-floor, 8.9% (ב-₪229, נורדי 7.5). המשלוח $30.84 גבוה מהמוצר: מלאי מקומי לאגרטלים
- `vase-cj-white-plum-hand-thrown` — loss, -2.2% (ב-₪229, נורדי 7.5). עלות $24.05 ומשלוח $29.57: מלאי מקומי לאגרטלים
- `vase-cj-french-matte-white-35` — loss, -34.0% (ב-₪229, נורדי 7.0). עלות $42.79 ומשלוח $29.57: לחפש ספק זול יותר
- `vase-cj-charcoal-carved` — loss, -4.8% (ב-₪199, נורדי 6.0). עלות $26.53: לחפש ספק זול יותר לאותו אגרטל
- `vase-cj-white-textured-jar` — loss, -15.4% (ב-₪149, נורדי 6.0). המשלוח $33.24 פי 5 מהמוצר: מלאי מקומי לאגרטלים
- `vase-cj-faceted-cream` — loss, -8.3% (ב-₪199, נורדי 5.5). המשלוח $32.29 גבוה מהמוצר: מלאי מקומי לאגרטלים
- `vase-cj-matte-moon-jar-white` — loss, -5.5% (ב-₪149, נורדי 5.5). המשלוח $20.12: מלאי מקומי לאגרטלים

### קישוט קיר (`wall-decor`) ⚑ חריגה נדרשת

- `wall-decor-aliexpress-natural-raffia-woven-bohemian-763597` — below-floor, 26.8% (ב-₪89, נורדי 7.0). לשפר בסט קיר או במשלוח מאוחד
- `wall-decor-cj-macrame-dowel-50x70` — below-floor, 27.3% (ב-₪119, נורדי 6.5). לשפר במשלוח מאוחד עם טקסטיל
- `wall-decor-zendrop-macrame-diamond-dowel-small` — loss, -23.4% (ב-₪59, נורדי 5.0). המשלוח $14.24 פי 5.7 מהמוצר: לעבור לספק עם משלוח זול או למכור כזוג

### מנורת קיר (`wall-sconce`) ⚑ חריגה נדרשת

- `wall-sconce-cj-black-swing-arm-fabric` — loss, -221.7% (ב-₪149, נורדי 7.0). המשלוח $105 פי 8 מהמוצר: לא כלכלי מהספק הזה, לחפש את אותו דגם במשלוח רגיל
- `wall-sconce-cj-travertine-dome-15-alt` — below-floor, 26.2% (ב-₪299, נורדי 7.0). לבדוק משלוח מאוחד לזוג
- `wall-sconce-cj-travertine-dome-15-pull` — loss, -42.2% (ב-₪299, נורדי 6.5). אותו עיצוב זמין ב-wall-sconce-cj-travertine-dome-15-alt במשלוח $30 במקום $85: להזמין מהספק השני
- `wall-sconce-cj-travertine-cone-walnut` — below-floor, 28.4% (ב-₪299, נורדי 6.0). לבדוק משלוח מאוחד לזוג
- `wall-sconce-cj-travertine-half-bowl-15` — below-floor, 35.2% (ב-₪229, נורדי 6.0). לשפר בזוג במשלוח מאוחד
- `wall-sconce-cj-travertine-disc-25` — below-floor, 13.3% (ב-₪379, נורדי 5.0). עלות $38.14: לבדוק ספק אחר לאותו דיסק

## חמשת המקרים הבעייתיים ביותר

- `rug-cj-braided-wool-natural`: תרומה ₪-1,518 ב-₪1,299 (נחיתה ₪2,503). רק DHL $491 (12 ק"ג): משלוח ימי או מלאי מקומי, או ספק שטיחים ישראלי
- `wall-sconce-cj-black-swing-arm-fabric`: תרומה ₪-280 ב-₪149 (נחיתה ₪392). המשלוח $105 פי 8 מהמוצר: לא כלכלי מהספק הזה, לחפש את אותו דגם במשלוח רגיל
- `framed-art-cj-morandi-triptych-sage`: תרומה ₪-197 ב-₪379 (נחיתה ₪484). המשלוח $130.82 פי 8 מהמוצר: הדפסה ומסגור מקומיים, או לשלוח רק את ההדפסים מגולגלים
- `pendant-cj-pleated-pumpkin-lantern-40`: תרומה ₪-107 ב-₪299 (נחיתה ₪333). המשלוח $54.80 גבוה מהמוצר: מלאי מקומי או ספק עם אריזה שטוחה
- `wall-sconce-cj-travertine-dome-15-pull`: תרומה ₪-107 ב-₪299 (נחיתה ₪333). אותו עיצוב זמין ב-wall-sconce-cj-travertine-dome-15-alt במשלוח $30 במקום $85: להזמין מהספק השני

## הערות

- ארבעה מוצרים בלי משלוח בקלט קיבלו את המשלוח מהערות הכרטיס (`ship_estimated: true`): מנורת האבן מ-AliExpress ($23.39), שני וילונות AliExpress ($1.99) וציפית הבוקלה מ-AliExpress ($1.99).
- בכמה ציפיות AliExpress לא ברור אם העלות ליחידה או לסט (`sure: false`). המחיר הוא ליחידה, ואם העלות היא לסט המרווח עולה מאוד.
- בעמדות התאורה, הטיפוסי מבוסס על Nord Light ו-Dealteora (מנורות טרוורטין ₪294–520). השוק הבינוני (Fox Home, Home Style) כמעט לא מוכר מנורות.
- מחירי זארה הום, חלק מחנויות העיצוב ו-SofaCovers לקוחים מתקצירי חיפוש (`source: search-snippet`), כי האתרים חוסמים גישה ישירה.
