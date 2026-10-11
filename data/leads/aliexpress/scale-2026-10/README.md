# AliExpress בקנה מידה (2026-10): סיכום

שלבים 1–2 (חיפוש ופירוט) רצו מול ה-API בסשן אחר ונעצרו ב-2026-10-11 על מגבלת השימוש (`stop-master.txt`). **שלב 3 (דירוג, השוואה וכרטיסים) רץ אופליין** מאותם נתונים: `detail/<room>.json` והמטמון `data/sources/aliexpress/<id>.json`, בלי אף קריאה ל-AliExpress. שלושה חדרים: סלון, מטבח ופינת אוכל, חדר שינה הורים. כל ששת הסגנונות.

## קבצים

| קובץ | מה יש בו |
| --- | --- |
| `detail/<room>.json` | שלב 2: מוצר, SKU, מחיר, משלוח לישראל (1,457 רשומות) |
| `../deep-2026-10/<room>.json` | שלב 3, לסטודיו (מסך "השוואת ספקים"): רשומה לכל מוצר×סגנון ברשימה הקצרה, עם SKU שמתאים לחדר, נחיתה, רצועה, רווח, fit, נימוק, השוואה לכרטיס הקיים ו-verdict |
| `living-room.md`, `dining-room.md`, `master.md` | לכל עמדה: טבלה עם עמודה לכל סגנון, הבחירה הטובה וההשוואה |
| `review/sheets/` | דפי המגע משלב 2 (שלב 3 הסתכל בתמונות עצמן, בגודל גדול יותר) |

## סיכומים

| חדר | מפורטים | עם מחיר, משלוח ובלי פסילת מידה | ברשימה הקצרה (נבדקו בתמונה) | רשומות מוצר×סגנון | עברו | הכי טוב | כרטיסים חדשים |
| --- | --- | --- | --- | --- | --- | --- | --- |
| סלון | 526 | 354 | 142 | 233 | 65 | 10 | 8 |
| מטבח ופינת אוכל | 499 | 311 | 129 | 254 | 23 | 3 | 3 |
| חדר שינה הורים | 432 | 283 | 125 | 201 | 32 | 1 | 1 |
| **סה"כ** | **1,457** | **948** | **396** | **688** | **120** | **14** | **12** |

"עברו" = fit 7 ומעלה (סף הסטודיו) ורווח 20% ומעלה במחיר העליון של הרצועה. רשימה קצרה: עד 8 לכל עמדה×סגנון, לפי ציון הסינון של שלב 1 ועוד רווח וקנה מידה, אחרי הוצאת מה שלא מתאים (ראו "השיטה").

## איפה AliExpress מנצח את CJ ו-Zendrop

| חדר / עמדה | סגנון | AliExpress | הכרטיס הקיים |
| --- | --- | --- | --- |
| סלון / curtains | נורדי | 1005012745902882, fit 8.0, נחיתה ₪94, רווח 27% | curtains-cj-japanese-linen-half-shade (CJ), fit 7.5, נחיתה ₪143, רווח -5% |
| סלון / table-runner | בוהו | 1005011825244347, fit 8.0, נחיתה ₪31, רווח 60% | table-runner-zendrop-ben-white-linen-look-33x183 (Zendrop), fit 3, נחיתה ₪46, רווח 46% |
| סלון / vase | נורדי | 1005012472589009, fit 8.5, נחיתה ₪105, רווח 48% | vase-cj-textured-white-stoneware (CJ), fit 8.5, נחיתה ₪124, רווח 40% |
| סלון / vase | מודרני חם | 1005012472589009, fit 8.0, נחיתה ₪105, רווח 48% | vase-cj-textured-white-stoneware (CJ), fit 8.5, נחיתה ₪124, רווח 40% |
| סלון / wall-decor | ים תיכוני | 1005006165763597, fit 8.0, נחיתה ₪46, רווח 56% | wall-decor-zendrop-macrame-diamond-dowel-small (Zendrop), fit 5, נחיתה ₪55, רווח 50% |
| סלון / wall-decor | בוהו | 1005006165763597, fit 8.5, נחיתה ₪46, רווח 56% | wall-decor-zendrop-macrame-diamond-dowel-small (Zendrop), fit 9, נחיתה ₪55, רווח 50% |

**ממלא סגנון שאין לו כרטיס עם ציון** (הכרטיסים הקיימים בעמדה לא דורגו לסגנון הזה, או שאין כרטיס בכלל):

- סלון / cushions, ג'פנדי: 1005009053464203 (fit 8.0, נחיתה ₪50, רווח 29%)
- סלון / cushions, כפרי מודרני: 1005012897166217 (fit 8.5, נחיתה ₪42, רווח 38%)
- סלון / vase, ג'פנדי: 1005012472589009 (fit 8.5, נחיתה ₪105, רווח 48%)
- סלון / vase, כפרי מודרני: 1005012472589009 (fit 8.0, נחיתה ₪105, רווח 48%)
- מטבח ופינת אוכל / framed-art, כפרי מודרני: 1005012481333603 (fit 8.0, נחיתה ₪97, רווח 37%)
- מטבח ופינת אוכל / paper-towel-holder, ג'פנדי: 1005009904316063 (fit 8.0, נחיתה ₪23, רווח 57%)
- מטבח ופינת אוכל / table-runner, בוהו: 1005009623263532 (fit 8.0, נחיתה ₪33, רווח 58%)
- חדר שינה הורים / bedding, בוהו: 1005012862500672 (fit 8.5, נחיתה ₪214, רווח 33%)

## עמדות בלי שום מועמד שעבר

בשום סגנון אין מוצר עם fit 7 ומעלה ורווח 20% ומעלה. הסיבה העיקרית בסוגריים.

- **סלון:** framed-art (קנבס בלי מסגרת); wall-sconce (נבדק אחד בתמונה ונדחה; בסינון בעיקר: רווח מתחת ל-20% ברצועה); rug (5 נבדקו בתמונה ונדחו; בסינון בעיקר: רווח מתחת ל-20% ברצועה); floor-lamp (לא המוצר (כותרת)); planter (רווח מתחת ל-20% ברצועה); sofa-cover (10 נבדקו בתמונה ונדחו; בסינון בעיקר: לא המוצר (כותרת)); basket (לא המוצר (כותרת)); magazine-holder (2 נבדקו בתמונה ונדחו; בסינון בעיקר: לא המוצר (כותרת)); bowl (רווח מתחת ל-20% ברצועה); pendant (2 נבדקו בתמונה ונדחו; בסינון בעיקר: רווח מתחת ל-20% ברצועה)
- **מטבח ופינת אוכל:** dining-pendant (2 נבדקו בתמונה ונדחו; בסינון בעיקר: רווח מתחת ל-20% ברצועה); centerpiece-vase (רווח מתחת ל-20% ברצועה); candle-holders (12 נבדקו בתמונה ונדחו; בסינון בעיקר: לא המוצר (כותרת)); floor-vase (21 נבדקו בתמונה ונדחו; בסינון בעיקר: לא המוצר (כותרת)); bench-pad (7 נבדקו בתמונה ונדחו; בסינון בעיקר: אין מידה שמתאימה לחדר); dining-rug (4 נבדקו בתמונה ונדחו; בסינון בעיקר: אין מידה שמתאימה לחדר); open-shelf-ceramics (רווח מתחת ל-20% ברצועה); kitchen-sconce (3 נבדקו בתמונה ונדחו; בסינון בעיקר: רווח מתחת ל-20% ברצועה); sink-set (6 נבדקו בתמונה ונדחו; בסינון בעיקר: חומר או מילה אסורה); utensil-crock (5 נבדקו בתמונה ונדחו; בסינון בעיקר: חומר או מילה אסורה); cutting-boards (7 נבדקו בתמונה ונדחו; בסינון בעיקר: רווח מתחת ל-20% ברצועה); condiment-set (חומר או מילה אסורה); bowl (רווח מתחת ל-20% ברצועה); mug-set (רווח מתחת ל-20% ברצועה); herb-pots (רווח מתחת ל-20% ברצועה); canisters (2 נבדקו בתמונה ונדחו; בסינון בעיקר: רווח מתחת ל-20% ברצועה); tea-towel (14 נבדקו בתמונה ונדחו); kitchen-runner (אין מידה שמתאימה לחדר); step-stool (4 נבדקו בתמונה ונדחו; בסינון בעיקר: רווח מתחת ל-20% ברצועה)
- **חדר שינה הורים:** curtains (אין מידה שמתאימה לחדר); framed-art (קנבס בלי מסגרת); bedside-sconces (2 נבדקו בתמונה ונדחו; בסינון בעיקר: רווח מתחת ל-20% ברצועה); sill-vase (רווח מתחת ל-20% ברצועה); planter (רווח מתחת ל-20% ברצועה); floor-lamp (נבדק אחד בתמונה ונדחה; בסינון בעיקר: רווח מתחת ל-20% ברצועה); nightstand-vase (רווח מתחת ל-20% ברצועה); trinket-dish (11 נבדקו בתמונה ונדחו; בסינון בעיקר: חומר או מילה אסורה); bedside-carafe (2 נבדקו בתמונה ונדחו; בסינון בעיקר: רווח מתחת ל-20% ברצועה); pillowcases (4 נבדקו בתמונה ונדחו; בסינון בעיקר: אין מידה שמתאימה לחדר); throw (נבדק אחד בתמונה ונדחה; בסינון בעיקר: רווח מתחת ל-20% ברצועה); basket (נבדק אחד בתמונה ונדחה; בסינון בעיקר: אין מידה שמתאימה לחדר); pendant (2 נבדקו בתמונה ונדחו; בסינון בעיקר: רווח מתחת ל-20% ברצועה)

## 20 הכי רווחיים (מבין אלה שעברו)

| # | חדר / עמדה | מוצר | סגנון (fit) | $ מוצר+משלוח | נחיתה | רצועה | רווח | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | חדר שינה הורים / rug | [VIKAMA Luxury Minimalist Area Rug Beig](https://www.aliexpress.com/item/1005013204627117.html) | נורדי 7.0, מודרני חם 7.0 | 81.11+1.99 | ₪274 | 649–799 | ₪332 · 49% | חלופה |
| 2 | סלון / pouf | [Modern PU Leather Pouf Ottoman Cover L](https://www.aliexpress.com/item/1005013014674879.html) | מודרני חם 7.0, ים תיכוני 7.0, בוהו 7.5 | 12.91+4.26 | ₪57 | 349–449 | ₪283 · 74% | חלופה |
| 3 | סלון / pouf | [Modern PU Leather Pouf Ottoman Cover U](https://www.aliexpress.com/item/1005012884189502.html) | בוהו 7.0 | 14.55+3.90 | ₪61 | 349–449 | ₪279 · 73% | חלופה |
| 4 | סלון / pouf | [Boho Pattern Ottoman Pouf PU Leather L](https://www.aliexpress.com/item/1005012622343078.html) | ים תיכוני 7.5, בוהו 7.5 | 15.70+4.28 | ₪66 | 349–449 | ₪274 · 72% | חלופה |
| 5 | סלון / pouf | [New PU Leather Fillable Ottoman Pouf E](https://www.aliexpress.com/item/1005013231174631.html) | ים תיכוני 7.0, בוהו 7.0 | 20.37+1.99 | ₪74 | 349–449 | ₪266 · 70% | חלופה |
| 6 | חדר שינה הורים / bedding | [100% Washed Cotton Duvet Cover Set Que](https://www.aliexpress.com/item/1005011886972799.html) | מודרני חם 7.0 | 39.74+1.99 | ₪138 | 349–449 | ₪202 · 53% | חלופה |
| 7 | חדר שינה הורים / bedding | [French Ruffle Cotton Duvet Cover Set K](https://www.aliexpress.com/item/1005010662357058.html) | כפרי מודרני 7.0 | 37.92+4.15 | ₪139 | 349–449 | ₪201 · 53% | חלופה |
| 8 | חדר שינה הורים / bedding | [Bohemian Pleated Wheat Color Fluffy Du](https://www.aliexpress.com/item/1005010466700189.html) | ים תיכוני 7.0, בוהו 7.5 | 43.14+0.00 | ₪142 | 349–449 | ₪198 · 52% | חלופה |
| 9 | חדר שינה הורים / bedding | [Boho Chic Wrinkled Duvet Cover Set Ult](https://www.aliexpress.com/item/1005010093087696.html) | בוהו 7.5 | 45.95+0.00 | ₪152 | 349–449 | ₪188 · 50% | חלופה |
| 10 | חדר שינה הורים / bedding | [Cute Duvet Cover Set with Sheet Pillow](https://www.aliexpress.com/item/1005006190004683.html) | ג'פנדי 7.0, כפרי מודרני 7.5 | 49.44+9.63 | ₪195 | 349–449 | ₪145 · 38% | חלופה |
| 11 | חדר שינה הורים / bedding | [Boho 3D Tufted Cut Flower Quilt Cover ](https://www.aliexpress.com/item/1005012862500672.html) | מודרני חם 7.0, ים תיכוני 7.0, בוהו 8.5 | 65.00+0.00 | ₪214 | 349–449 | ₪125 · 33% | הכי טוב · כרטיס |
| 12 | סלון / vase | [Vintage Distressed Clay Vase, Wabi-Sab](https://www.aliexpress.com/item/1005012472589009.html) | נורדי 8.5, מודרני חם 8.0, ג'פנדי 8.5, ים תיכוני 7.5, כפרי מודרני 8.0 | 4.53+27.25 | ₪105 | 229–299 | ₪121 · 48% | הכי טוב · כרטיס |
| 13 | סלון / vase | [3pcs Bohemian Ceramic Vase Set, Modern](https://www.aliexpress.com/item/1005008455616613.html) | נורדי 7.0, כפרי מודרני 7.0, בוהו 7.0 | 32.92+1.99 | ₪115 | 229–299 | ₪111 · 44% | חלופה |
| 14 | סלון / candle-holders | [New Rustic Wooden Candlesticks Handmad](https://www.aliexpress.com/item/1005010391178645.html) | כפרי מודרני 7.0 | 3.86+1.99 ×2 | ₪32 | 59–89 | ₪95 · 66% | חלופה |
| 15 | סלון / wall-decor | [4 Bohemian Wall Art Set - Wooden Bohem](https://www.aliexpress.com/item/1005009168911590.html) | בוהו 7.0 | 8.01+1.99 | ₪33 | 129–169 | ₪94 · 66% | חלופה |
| 16 | סלון / wall-decor | [Macrame Wall Hanging, Boho Leaves Macr](https://www.aliexpress.com/item/1005011872608079.html) | בוהו 7.0 | 10.93+1.99 | ₪43 | 129–169 | ₪84 · 59% | חלופה |
| 17 | סלון / wall-decor | [Leaf Macrame Wall Hanging Boho Room Ho](https://www.aliexpress.com/item/1005008100137440.html) | בוהו 7.5 | 12.01+1.99 | ₪46 | 129–169 | ₪81 · 56% | חלופה |
| 18 | סלון / wall-decor | [Natural Raffia Woven Bohemian Wall Dec](https://www.aliexpress.com/item/1005006165763597.html) | נורדי 7.5, ים תיכוני 8.0, בוהו 8.5 | 12.85+1.16 | ₪46 | 129–169 | ₪81 · 56% | הכי טוב · כרטיס |
| 19 | סלון / table-runner | [Mediterranean Table Runner Linen Style](https://www.aliexpress.com/item/1005013203386192.html) | ים תיכוני 7.0 | 5.21+1.99 | ₪24 | 89–129 | ₪73 · 67% | חלופה |
| 20 | סלון / table-runner | [Minimalist Solid Color Table Runner, N](https://www.aliexpress.com/item/1005012179525144.html) | נורדי 7.5, מודרני חם 7.0, ג'פנדי 7.5 | 6.42+1.99 | ₪28 | 89–129 | ₪69 · 63% | חלופה |

## הכרטיסים החדשים (DRAFT)

נכתבו ב-`python3 scripts/ae/ds.py card <id> --slot <room/slot> --sku <SKU של החדר> --id <id> --offline`: מהמטמון בלבד, עם `options` מלא (כל ה-SKU של הספק), ונרשמו ב-`data/sources/seen.json` כ-card. הם טיוטה כמו כל כרטיס API: צבעים (HEX), משקל ויזואלי, מידות המוצר וטקסטורה ריקים; ה-style_scores הם ציון סינון שלי ולא של המעצב. master-designer מדרג ו-qa-agent בודק.

| כרטיס | עמדה | SKU בחדר | נחיתה | רווח | משלוח |
| --- | --- | --- | --- | --- | --- |
| `curtains-aliexpress-cotton-linen-curtain-look-902882` | סלון / curtains | Color S Folds Size 1 PC W100cmxH275cm Pr | ₪94 (2 יח') | 27% | הערכה |
| `cushions-aliexpress-fashion-modern-wabi-sabi-464203` | סלון / cushions | Color 1PCS-White Size 50 x 50cm | ₪50 | 29% | הערכה |
| `cushions-aliexpress-farmhouse-floral-pillow-covers-166217` | סלון / cushions | Color 1 Size 45×45cm | ₪42 | 38% | הערכה |
| `table-runner-aliexpress-nordic-table-runner-kitchen-244347` | סלון / table-runner | Color BEIGE Size 30*120cm | ₪31 | 60% | הערכה |
| `table-runner-aliexpress-boho-macrame-table-runners-263532` | סלון / table-runner | Color A-4 Size 30x120cm Style Other | ₪32 | 59% | הערכה |
| `table-runner-aliexpress-boho-table-runner-macrame-072806` | סלון / table-runner | Color Khaki with tassel Size 30x120cm | ₪36 | 56% | הערכה |
| `vase-aliexpress-vintage-distressed-clay-vase-589009` | סלון / vase | Color L | ₪105 | 48% | צוטט |
| `wall-decor-aliexpress-natural-raffia-woven-bohemian-763597` | סלון / wall-decor | Color 2 Size 30cm | ₪46 | 56% | צוטט |
| `framed-art-aliexpress-retro-farmhouse-chicken-botanical-333603` | מטבח ופינת אוכל / framed-art | Color G5241 Size (Inch) 30x40cm Wood Fra | ₪97 | 37% | הערכה |
| `paper-towel-holder-aliexpress-1pc-bamboo-paper-towel-316063` | מטבח ופינת אוכל / paper-towel-holder | Color Single bar Round | ₪23 | 57% | צוטט |
| `table-runner-aliexpress-boho-macrame-table-runners-263532` | מטבח ופינת אוכל / table-runner | Color A-4 Size 30x140cm Style Other | ₪33 | 58% | הערכה |
| `bedding-aliexpress-boho-3d-tufted-cut-500672` | חדר שינה הורים / bedding | Color Khaki Size US Queen size 3 pcs | ₪214 | 33% | צוטט |

## לסשן הבא עם ה-API: משלוח ל-SKU של החדר

בשלב 2 נבחר ברוב המקרים ה-SKU הזול (sku-default ב-1,321 מתוך 1,457), שבטקסטיל, בשטיחים ובתמונות הוא המידה הקטנה. שלב 3 בחר מהמטמון את ה-SKU שמתאים למעטפת של העמדה (השתנה ב-208 מתוך 1,229 רשומות עם מחיר), אבל המשלוח צוטט רק ל-SKU של שלב 2. ההערכה: ב-AliExpress Selection Standard (Choice) המשלוח קבוע, 1.99 דולר לפריט בכל 843 הציטוטים של הריצה, בכל מחיר; בשאר החברות המשלוח הוכפל ביחס המחירים בין ה-SKU (מעל פי 1.5) או במודל החבילה של הסטודיו (מתחת). כדאי לצטט את אלה לפני QA (fit 7.5 ומעלה):

```
python3 scripts/ae/ds.py freight 1005012745902882 --sku 12000059241454224   # living-room/curtains, Color S Folds Size 1 PC W100cmxH275cm Pr
python3 scripts/ae/ds.py freight 1005009053464203 --sku 12000047728467291   # living-room/cushions, Color 1PCS-White Size 50 x 50cm
python3 scripts/ae/ds.py freight 1005012897166217 --sku 12000059675354792   # living-room/cushions, Color 1 Size 45×45cm
python3 scripts/ae/ds.py freight 1005006412064335 --sku 12000037071828314   # living-room/cushions, Color CL006 Size 45x45cm
python3 scripts/ae/ds.py freight 1005009261623058 --sku 12000048519921711   # living-room/cushions, Color Beige-45x45cm
python3 scripts/ae/ds.py freight 1005006856211815 --sku 12000038527813258   # living-room/cushions, Color As Picture Size 45x45cm
python3 scripts/ae/ds.py freight 1005012179525144 --sku 12000057716654671   # living-room/table-runner, Size 40x140cm
python3 scripts/ae/ds.py freight 1005009813736421 --sku 12000050255861419   # living-room/table-runner, Color Dark Brown Size 1PCS-30x120cm
python3 scripts/ae/ds.py freight 1005011825244347 --sku 12000056696249963   # living-room/table-runner, Color BEIGE Size 30*120cm
python3 scripts/ae/ds.py freight 1005009623263532 --sku 12000049664148478   # living-room/table-runner, Color A-4 Size 30x120cm Style Other
python3 scripts/ae/ds.py freight 1005008814072806 --sku 12000046780624550   # living-room/table-runner, Color Khaki with tassel Size 30x120cm
python3 scripts/ae/ds.py freight 1005005344284009 --sku 12000032688263947   # living-room/table-runner, Color Size 1 Size 30*120cm Style Other
python3 scripts/ae/ds.py freight 1005012125608439 --sku 12000057565119394   # dining-room/framed-art, Color G3823 Size (Inch) 30x40cm Wood Fra
python3 scripts/ae/ds.py freight 1005012481333603 --sku 12000058489859911   # dining-room/framed-art, Color G5241 Size (Inch) 30x40cm Wood Fra
python3 scripts/ae/ds.py freight 1005009505269164 --sku 12000049305758185   # dining-room/table-runner, Color white Size 33x140cm
python3 scripts/ae/ds.py freight 1005009623263532 --sku 12000049664148479   # dining-room/table-runner, Color A-4 Size 30x140cm Style Other
python3 scripts/ae/ds.py freight 1005010466700189 --sku 12000052506947829   # master/bedding, Color Ivory Size 200x200cm
```

## השיטה (שלב 3)

1. **SKU של החדר:** מכל רשומה, מתשובת `product.get` השמורה: SKU במלאי, לא "contact us", במידה שבמעטפת של העמדה (`data/slots/<room>.json`, ובסלון ה-Design Bible): הזול מבין המתאימים. אם אין מידה שמתאימה בכלל, המוצר יוצא ("לא פוסלים בגלל אפשרות אחת": מספיק SKU אחד שמתאים). בתאורה: תקע אירופאי או 220V, אור חם. בתמונה ממוסגרת: רק SKU עם מסגרת (רוב ההדפסים ב-AliExpress הם קנבס בלי מסגרת, Frame mode = Unframed).
2. **כלכלה:** כמו בסטודיו: (מחיר × כמות + משלוח לכמות) × 3.3, רווח ב-econCalc במחיר העליון של הרצועה (`data/economics/market-prices.json` דרך `scripts/ae/scale_config.py`). בעמדת זוג (וילונות, זוג מנורות, פמוטים, ציפיות וכו') הכמות היא מספר היחידות, והרצועה נרשמת ליחידה, כך שהסטודיו מחשב אותו מספר (הנימוק כולל "price per piece; set of N = N units").
3. **רשימה קצרה:** בכל עמדה×סגנון, מהמוצרים שנמצאו לסגנון: בלי מוצר שאינו המוצר (מחזיקי מחסניות, אהילים בלי מנורה, נורת USB, תחתיות), בלי מילים אסורות (פלסטיק, מבריק, ניאון, קרטון, LED strip, זהב/קטיפה בנורדי...), בלי חומר עיקרי מפלסטיק, ורווח לפחות 20%. דירוג: ציון החיפוש + 30×רווח + 10 למידה שמתאימה, פחות על משלוח ארוך או מוערך. עד 8.
4. **מבט בתמונה:** כל תמונה ראשית הורדה ונבדקה (בדפי מגע של 12), ונתתי fit 1–10 לכל סגנון שהמוצר נמצא בו (ולפעמים לסגנון נוסף שהוא מתאים לו בבירור), עם נימוק בשורה. בפריטים שנכנסו לכרטיס בדקתי גם את תמונות ה-SKU ובחרתי את הצבע שבתמונה.
5. **השוואה:** מול הכרטיס הקיים בעמדה עם הציון הגבוה לאותו סגנון (בנורדי גם כרטיס בלי ציון, כמו בסטודיו), באותה כמות ובאותו מחיר מכירה. כרטיס בלי משלוח ידוע מקבל 17 דולר, ברירת המחדל של הסטודיו.
6. **כרטיסים:** fit 8 ומעלה ורווח לפחות כמו הכרטיס הקיים (או שאין כרטיס עם ציון לסגנון), עד 3 לעמדה×סגנון.

## לשים לב

- **רצועות נמוכות מדי:** עציץ רצפה (19–29), אגרטל קטן (29–39), ספל (19), קערה (29–49) ומלח ופלפל לא משאירים 20% אף פעם מ-AliExpress. ברצועת "עציץ" יש כנראה עציצים קטנים; לעציץ רצפה של 38 ס"מ היא לא מתאימה.
- **השוואה לכרטיסים בסטודיו:** לכרטיס וילון שנמכר בזוג הסטודיו מכפיל את רצועת השוק (שהיא כבר לזוג) בכמות (2), ולכן מראה בכרטיס רווח גבוה מדי. ברשומות של `deep-2026-10` הרצועה רשומה לפאנל, והמספר נכון.
- **כפילות:** אותו סט מצעים נמכר בשתי חנויות (1005012855035925, ‏1005012862500672); כרטיס רק לחנות עם המלאי הגדול.
- **רישום במרשם:** רק הכרטיסים. מוצרים שנדחו בתמונה לא סומנו rejected במרשם, כי הדחייה היא לעמדה מסוימת והמרשם הוא למוצר.

