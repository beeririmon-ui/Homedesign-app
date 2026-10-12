# AliExpress בקנה מידה: סיכום (2026-10-11)

ליקוט בהיקף גדול דרך ה-API הרשמי של AliExpress (סשן עזר, בקשת המשתמש 2026-10-11: "מאות, לא עשרה"). השיטה: `scripts/ae/scale.py` (סינון רחב → בדיקה מלאה של מחיר SKU ומשלוח לישראל → מבט בתמונה → כרטיס). כל העמדות בכל 8 החדרים (132, בלי 16 הרהיטים הקבועים), לכל ששת הסגנונות, שני סבבים (בסבב 2 שאילתות מתוקנות לעמדות שקיבלו תוצאות שגויות).

## במספרים

| | |
| --- | --- |
| תוצאות חיפוש (ייחודיות) | 40,053, של 13,682 מוצרים שונים |
| מוצרים שנבדקו לעומק (מחיר SKU + משלוח לישראל) | 5,086 |
| מוצרים שנבדקו בעין (גיליונות תמונות) | 2,103 |
| רשומות מוצר×סגנון | 8,594 |
| כרטיסי טיוטה חדשים | 19 |
| קריאות API (2026-10-11: 8,411; 2026-10-12: 2,112) | 10,523 |

**מכסה שנצפתה:** אין מכסה יומית מוחזרת. מגבלת קצב: עם 3 תהליכים במקביל (כ-1.8 קריאות בשנייה) AliExpress החזיר `ApiCallLimit` ("this ban will last 1 seconds"); עם 2 במקביל זה קרה לעיתים רחוקות. כל עצירה נרשמה, וההרצה המשיכה מהנקודה שבה עצרה. התקרה העצמית הועלתה ל-12,000 ביום לריצה הזו (`scripts/sourcing/budget.py`).

עצירות שנרשמו:
```
bath STOP detail at 2026-10-11 17:11:07 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
bath STOP detail at 2026-10-12 04:10:16 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
bath STOP detail at 2026-10-12 04:13:05 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
dining-room STOP detail at 2026-10-12 04:19:14 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
dining-room STOP detail at 2026-10-12 04:22:13 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
dining-room STOP detail at 2026-10-12 04:27:06 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
kids STOP detail at 2026-10-11 16:50:12 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
kids STOP detail at 2026-10-12 04:21:06 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
kids STOP detail at 2026-10-12 04:23:04 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
kids STOP detail at 2026-10-12 04:27:10 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
kids STOP detail at 2026-10-12 04:29:04 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
living-room STOP detail at 2026-10-12 04:09:06 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
living-room STOP detail at 2026-10-12 04:12:04 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
living-room STOP detail at 2026-10-12 04:16:06 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
master STOP all at 2026-10-11 12:03:10 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
master STOP detail at 2026-10-12 04:32:55 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
master STOP detail at 2026-10-12 04:40:05 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
master STOP detail at 2026-10-12 04:42:05 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
master STOP detail at 2026-10-12 04:44:09 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
work STOP detail at 2026-10-11 12:29:17 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
work STOP detail at 2026-10-12 04:48:09 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
work STOP detail at 2026-10-12 04:50:06 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
```

בסבב 3 הוגדרו רצועות מחיר משוערות (מסומנות estimated) לעציצים, סלים וקופסאות בגודל רצפה ולקערות הגשה, כי קטגוריות השוק (עציץ ₪19–29, סל ₪49–69) מתאימות לפריטים קטנים.

**כלכלה:** נחיתה = (מחיר ה-SKU שמתאים לחדר + המשלוח הזול עד 45 יום) × 3.3. מחיר לצרכן = הקצה העליון של רצועת השוק בישראל (`data/economics/market-prices.json`; ה.10). רווח לפי `pricing.ts` (מע"מ 18%, סליקה 2% + 1.2, החזרות 8%), לפני CAC. כרטיס נכתב רק עם fit 8+ אחרי מבט בתמונה, SKU שמידתו אומתה מול העמדה, עלות לא גבוהה מהכרטיס הקיים, ורווח 40%+ (VR1; פחות מזה רק כשאין חלופה בעמדה ובסגנון, ומסומן).

## סבב 3 (2026-10-12)

ל-65 העמדות שנשארו בלי מוצר שמיש אחרי שני סבבים: שאילתות בלי מילת סגנון (חומר וסוג מוצר), ממוינות לפי הזמנות, 2 עמודים לכל שאילתה, ו-12 הממצאים הטובים בכל עמדה נבדקו לעומק ובעין. **אף מוצר לא הגיע ל-fit 8.** כ-75–85% מהתוצאות היו סוג מוצר שגוי (רשתות ניקוז, סלי כביסה, קערות לחיות, תבניות נרות, חלקי אופניים), והשאר קטנים מדי או בלי עמידות למים. רק 3 עמדות יצאו מרשימת הריקות. מסקנה: בעמדות האלה החיפוש הטקסטואלי של AliExpress לא מוצא מוצר מעוצב, וצריך ספק אחר (CJ, Zendrop, ספק ישראלי) או חיפוש לפי תמונה (`ds.py image-search`) מתמונת הייחוס של המעצב.


## סבב 3 של המנהל (2026-10-12)

הרצה של `data/leads/next-sourcing/round-3-2026-10-11.json` (רשימה מאוחדת מהרכבת המעצב לשמונת החדרים) דרך `scripts/ae/ad_round3.py`: שכבה 1 ← 2 ← 3, רזרבה רק לעמדה שלא מלאה, deferred לא רץ. hide-seen, מכסת שאילתות לעמדה (6/4/2), עצירה ב-3 מועמדים שעוברים את תקרת הנחיתה ל-40% ואת המעטפת. כל שאילתה נוספה ל-`searched-index.json`.

- **351 שאילתות**, 100 עמדות, 1397 מוצרים חדשים נבדקו לעומק (SKU במידת העמדה + משלוח לישראל), 42 עמדות הגיעו ל-3 מועמדים בתוך התקרה. כולם נבדקו בעין לכל ששת הסגנונות (`review/ad3-<room>.json`).
- **תוצאות לפי חדר:** `data/leads/next-sourcing/round-3-results/<room>.json` ו-`.md`.

| חדר | עמדות | מועמדים | עוברים מחיר+מידה |
| --- | --- | --- | --- |
| living-room | 15 | 191 | 23 |
| dining-room | 12 | 181 | 15 |
| hall | 12 | 173 | 27 |
| master | 17 | 242 | 24 |
| work | 12 | 158 | 26 |
| kids | 16 | 184 | 30 |
| bath | 12 | 225 | 15 |
| corridor | 4 | 43 | 4 |

- **fit נורדי 8+ (אחרי מבט):** 4.
  - living-room/accent-sconces: [Yellow Travertine Stone Wall Mounted Lamp for Shop Restauran](https://www.aliexpress.com/item/1005009515905096.html), נחיתה ₪468.4 (2 יח'), מעל התקרה, רווח -3%
  - living-room/accent-sconces: [Travertine Stone Wall Light for Living Room Bedroom Stairs C](https://www.aliexpress.com/item/1005009658358794.html), נחיתה ₪621.0 (2 יח'), מעל התקרה, רווח -33%
  - master/rug: [Handmade Woven Wool Carpet for Living Room Luxury Vintage So](https://www.aliexpress.com/item/1005008478888136.html), נחיתה ₪3804.7, מעל התקרה, רווח -256%
  - bath/towel-ring: [Bathroom Stainless Steel Towel Ring Stylish Design Hanging H](https://www.aliexpress.com/item/1005007135312287.html), נחיתה ₪31.2, מעל התקרה, רווח 34%
- **כרטיסי טיוטה:** 0. התנאי (נורדי 8+ וגם בתוך התקרה) לא התקיים לאף מוצר. מנורת הטרוורטין עברה בתחילה, אבל העמדה נמכרת כזוג וזוג נוחת ב-₪468, מעל האיזון. הכרטיס בוטל, והחישוב מכפיל עכשיו לפי qty.
- **קרובים, להחלטת המנהל:** טבעת מגבת שחורה 16 ס"מ (נורדי 8, נחיתה ₪31 מול תקרה ₪27.8, רווח 34%); מנורות תקרה משי-דלעת למסדרון (ג'פנדי 8, נורדי 7.5); שטיח צמר ארוג 200×300 (נורדי 8, אבל ₪3,805 משלוח כולל).
- **הערה:** בשלב החיפוש כלל העצירה (3 עוברים) לא הכפיל לפי qty, כך שעמדות זוג אולי נעצרו מוקדם.
- **בדיקות משלוח (סעיף 4):** 60 פריטים מ-`ae-freight-requests.json`: 35 עם משלוח לישראל, 9 בלי משלוח, 16 שגיאה. ב-`data/leads/profit-fix-2026-10-11/ae-freight-results.json` (הזול, והזול עד 20 יום).
- **כרטיסים עם "needs freight check" (5):** נבדק המשלוח ל-SKU שבכרטיס. **לא נשלחים לישראל:** וילון `curtains-aliexpress-natural-linen-s-fold-613202` (DELIVERY_NOT_AVAILABLE, גם ליחידה וגם לזוג) וראנר `table-runner-aliexpress-solid-color-textured-runner-525144` (DELIVERY_SERVICE_EXCEPTION): צריך SKU אחר או מוצר אחר. נשלחים: אגרטלון 529337 ($6.41, 18–28 יום; $7.99 עד 18 יום), טבעת מגבת 663845 ($4.00, 8–19), מגש 693779 ($1.99, 6–15). ב-`ae-freight-results.json` תחת `cards`.
- **עמדות שעדיין בלי מועמד שמיש:** בובה, עגלת בובות, כיסא ילד, סקייטבורד, סולם מגבות, שרפרף מקלחת, תאורת תקרה לאמבטיה (אין IP44 שמתאים), עציצים גדולים, קנקן לילה, תמונות ממוסגרות לשינה, מחזיק עיתונים.

## סבב 4 של המנהל: מודרני חם (2026-10-12)

`data/leads/next-sourcing/round-4-styles-2026-10-12.json`, רק `warm-modern:high` (30) ו-`warm-modern:medium` (50), דרך `scripts/ae/ad_round3.py --style warm-modern --tiers ... --res-dir data/leads/next-sourcing/round-4-results --tag ad4wm`.

- **מתוך 80 השאילתות, רק 4 מסומנות AliExpress.** 64 מסומנות לספקים ישראליים, 8 ל-CJ ו-4 למלאי מקומי. הן לא הורצו כאן: סשן זה מחובר רק ל-AliExpress, והתוכנית שייכה אותן במכוון לספקים אחרים, כי AliExpress לא מחזיק את המוצרים האלה במידה הנכונה. **צריך להריץ אותן בסשן המתאים.**
- 4 השאילתות של AliExpress (וילונות לסלון, הווריאציה הכהה בטאופ): 18 מועמדים חדשים, כולם נבדקו בעין לששת הסגנונות. **אף אחד לא עובר** את תקרת הזוג (₪145.6 לזוג, 140×280). הקרובים: פשתן כבד בבז' בקפלי צביטה 102×274 (מודרני חם 7, צר), וכותנה-פשתן בתה-חלב 200×260 (7, קצר ועם עיניות). **0 כרטיסים.**
- כלל העצירה מחשב עכשיו את מחיר הזוג כבר בשלב החיפוש (qty מהמעטפת).
- תוצאות: `data/leads/next-sourcing/round-4-results/warm-modern.json` ו-`.md`.

## כרטיסי הטיוטה

| חדר | עמדה | כרטיס | סגנון, fit | נחיתה ₪ | רווח |
| --- | --- | --- | --- | --- | --- |
| corridor | gallery-art | `gallery-art-aliexpress-antique-botanical-posters-prints-710412` | כפרי מודרני 8 | 28 | 74% |
| corridor | gallery-art | `gallery-art-aliexpress-japanese-wabi-sabi-tree-176323` | ג'פנדי 8 | 25 | 76% |
| corridor | gallery-art | `gallery-art-aliexpress-simple-nordic-posters-picasso-983896` | נורדי 8 | 25 | 75% |
| hall | framed-art | `framed-art-aliexpress-japanese-wabi-sabi-tree-176323` | ג'פנדי 8 | 32 | 72% |
| living-room | curtains | `curtains-aliexpress-beige-linen-sheer-curtains-554205` | מודרני חם 8 | 87 | 31% (חריג VR1) |
| living-room | framed-art | `framed-art-aliexpress-japandi-wall-art-set-969661` | ג'פנדי 8 | 38 | 69% |
| living-room | framed-art | `framed-art-aliexpress-mediterranean-wabi-sabi-poster-802890` | ים תיכוני 8 | 29 | 73% |
| living-room | vase | `vase-aliexpress-vintage-distressed-clay-vase-589009` | ג'פנדי 8.5 | 105 | 48% |
| living-room | wall-decor | `wall-decor-aliexpress-japandi-wall-art-set-969661` | ג'פנדי 8 | 29 | 69% |
| master | curtains | `curtains-aliexpress-linen-blend-beige-curtains-122000` | מודרני חם 8 | 78 | 37% (חריג VR1) |
| work | curtains | `curtains-aliexpress-1pc-japanese-folk-wabi-212463` | ג'פנדי 8 | 111 | 16% (חריג VR1) |
| work | curtains | `curtains-aliexpress-beige-linen-sheer-curtains-554205-work` | מודרני חם 8 | 87 | 31% (חריג VR1) |
| work | curtains | `curtains-aliexpress-cotton-linen-curtain-look-902882-work` | נורדי 8 | 64 | 47% |
| work | curtains | `curtains-aliexpress-natural-linen-curtains-84-784378` | כפרי מודרני 8 | 84 | 33% (חריג VR1) |
| work | framed-art | `framed-art-aliexpress-frameless-minimalist-wall-art-631735` | מודרני חם 8.5 | 26 | 75% |
| work | framed-art | `framed-art-aliexpress-japanese-wabi-sabi-tree-176323-work` | ג'פנדי 8.5 | 25 | 76% |
| work | framed-art | `framed-art-aliexpress-mediterranean-wabi-sabi-poster-802890-work` | ים תיכוני 8 | 22 | 77% |
| work | framed-art | `framed-art-aliexpress-modern-minimalist-neutral-gallery-802995` | מודרני חם 8 | 39 | 68% |
| work | wall-sconce | `wall-sconce-aliexpress-rattan-bamboo-wall-lamp-671943` | בוהו 8 | 66 | 23% (חריג VR1) |

כל הכרטיסים הם DRAFT: צבעים (HEX), מידות מוצר ומשקל ויזואלי ריקים, ו-sourcing-agent משלים אותם. הדפסים שנמכרים בלי מסגרת מסומנים בסיבה. ה-fit הוא ציון סינון בעין, לא ציון המעצב.

## איפה AliExpress זול מהכרטיס הקיים (CJ / Zendrop / ישראלי)

fit 7+ במבט, מידה מאומתת, נחיתה זולה מהכרטיס הקיים באותה עמדה.

| חדר/עמדה | AliExpress | נחיתה ₪ | הכרטיס הקיים | נחיתה ₪ |
| --- | --- | --- | --- | --- |
| bath/bath-mat | [Waffle Bath Mat Rug Super Absorbent Non Slip Boho ](https://www.aliexpress.com/item/1005011772248198.html) (כפרי מודרני 7) | 37 | bath-mat-aliexpress-waffle-bath-mat-248198 (AliExpress) | 37 |
| corridor/ceiling-lights | [Bamboo Ceiling Lamp Indoor Ceiling Light E27 Home ](https://www.aliexpress.com/item/1005010079227644.html) (בוהו 7) | 94 | ceiling-lights-cj-silk-pumpkin-lantern-30 (CJ Dropshipping) | 153 |
| corridor/gallery-art | [Japanese Wabi Sabi Tree Abstract Canvas Print Post](https://www.aliexpress.com/item/1005012443176323.html) (ג'פנדי 8) | 25 | gallery-art-cj-black-botanical-cutout-set3 (CJ Dropshipping) | 83 |
| dining-room/candle-holders | [Vintage Metal Taper Candle Holder with Handle Tray](https://www.aliexpress.com/item/1005012396864609.html) (כפרי מודרני 7) | 21 | candle-holders-aliexpress-matte-black-iron-pillar-set2 (AliExpress) | 41 |
| dining-room/framed-art | [Rustic Kitchen Still Life Poster Vintage Bread Art](https://www.aliexpress.com/item/1005011780297081.html) (כפרי מודרני 7) | 19 | framed-art-aliexpress-retro-farmhouse-chicken-botanical-333603 (AliExpress) | 97 |
| dining-room/paper-towel-holder | [1PC Bamboo Paper Towel Holder Kitchen Dining Room ](https://www.aliexpress.com/item/1005009904316063.html) (ג'פנדי 7) | 23 | paper-towel-holder-aliexpress-1pc-bamboo-paper-towel-316063 (AliExpress) | 23 |
| hall/ceiling-light | [Boho Rattan Woven Ceiling Light Semi Flush Mount C](https://www.aliexpress.com/item/1005012561051994.html) (בוהו 7) | 74 | ceiling-light-cj-waxwood-dome-ash-40 (CJ Dropshipping) | 197 |
| hall/framed-art | [Frameless Minimalist Wall Art Set in Brown and Bei](https://www.aliexpress.com/item/1005010493631735.html) (מודרני חם 7) | 26 | framed-art-cj-line-scribble-white-mat-50 (CJ Dropshipping) | 166 |
| hall/wall-sconce | [Rattan Bamboo Wall Lamp Sconce Fixture Vintage Boh](https://www.aliexpress.com/item/1005010168671943.html) (בוהו 7) | 66 | wall-sconce-cj-white-fabric-cube-15-hall (CJ Dropshipping) | 109 |
| kids/bookshelf | [2Pcs Bookshelf,Natural Wood Floating Wall Bookshel](https://www.aliexpress.com/item/1005008149230106.html) (נורדי 7) | 72 | bookshelf-aliexpress-natural-wood-floating-bookshelf-230106 (AliExpress) | 72 |
| kids/framed-prints | [Japandi Wall Art Set of 2 Sage Green Landscape Pos](https://www.aliexpress.com/item/1005012553969661.html) (ג'פנדי 7) | 21 | framed-prints-cj-flower-cutout-set-30x40 (CJ Dropshipping) | 69 |
| kids/pendant | [Rustic Woven Pendant Light Kitchen Island Boho Han](https://www.aliexpress.com/item/1005009394200914.html) (כפרי מודרני 7) | 84 | pendant-cj-fabric-dome-ash-cap-25 (CJ Dropshipping) | 144 |
| living-room/basket | [Seaweed Wicker Basket Rattan Hanging Flowerpot  Di](https://www.aliexpress.com/item/1005001597545859.html) (ים תיכוני 7) | 45 | basket-zendrop-seagrass-belly-foldable-38 (Zendrop) | 60 |
| living-room/curtains | [Beige Linen Sheer Curtains for Living Room Modern ](https://www.aliexpress.com/item/1005004556554205.html) (מודרני חם 8) | 87 | curtains-cj-japanese-linen-half-shade (CJ Dropshipping) | 143 |
| living-room/framed-art | [Vintage Countryside Wall Art Print Retro Rustic Sp](https://www.aliexpress.com/item/1005006849743763.html) (כפרי מודרני 7.5) | 27 | framed-art-cj-morandi-triptych-sage (CJ Dropshipping) | 484 |
| living-room/vase | [Vintage Distressed Clay Vase, Wabi-Sabi Rustic Cer](https://www.aliexpress.com/item/1005012472589009.html) (ג'פנדי 8.5) | 105 | vase-aliexpress-vintage-distressed-clay-vase-589009 (AliExpress) | 105 |
| living-room/wall-decor | [Japandi Wall Art Set of 2 Sage Green Landscape Pos](https://www.aliexpress.com/item/1005012553969661.html) (ג'פנדי 8) | 29 | wall-decor-aliexpress-natural-raffia-woven-bohemian-763597 (AliExpress) | 46 |
| master/bedside-sconces | [Boho Farmhouse Wall Sconces Natural Twine Hand Kni](https://www.aliexpress.com/item/1005009708965037.html) (כפרי מודרני 7) | 88 | bedside-sconces-cj-white-fabric-cube-15 (CJ Dropshipping) | 109 |
| master/curtains | [Natural Linen Voile Curtain 132CM Drop Net Curtain](https://www.aliexpress.com/item/1005008289564712.html) (ים תיכוני 7.5) | 62 | curtains-aliexpress-natural-linen-s-fold-613202 (AliExpress) | 100 |
| work/bookends | [（Summer6）Nature Bamboo Desktop Organizer Bookends ](https://www.aliexpress.com/item/1005010478897382.html) (ג'פנדי 7) | 20 | bookends-aliexpress-bamboo-bookends-897382 (AliExpress) | 20 |
| work/pendant | [Rustic Woven Pendant Light Kitchen Island Boho Han](https://www.aliexpress.com/item/1005009394200914.html) (כפרי מודרני 7.5) | 84 | pendant-cj-fluted-ceramic-wood-cap-short-lantern (CJ Dropshipping) | 115 |
| work/wall-sconce | [Rattan Bamboo Wall Lamp Sconce Fixture Vintage Boh](https://www.aliexpress.com/item/1005010168671943.html) (בוהו 8) | 66 | wall-sconce-cj-black-swan-arm-white-fabric-cone (CJ Dropshipping) | 85 |

## עמדות בלי שום מוצר שמיש מ-AliExpress

אין אף פריט עם fit 7+ במבט בשום סגנון (הסיבה העיקרית בטבלת החדר).

living-room/planter, living-room/bowl, living-room/candle-holders, living-room/pouf, dining-room/bench-pad, dining-room/sink-set, dining-room/utensil-crock, dining-room/cutting-boards, dining-room/condiment-set, dining-room/bowl, dining-room/tableware-set, dining-room/mug-set, dining-room/tea-towel, dining-room/step-stool, hall/console-vessel, hall/storage-boxes, hall/bench-cushion, hall/basket, hall/planter, hall/umbrella-stand, hall/runner-rug, master/floor-lamp, master/trinket-dish, master/bedside-carafe, master/throw, master/basket, master/pendant, work/waste-basket, work/magazine-holder, work/shelf-boxes, kids/roman-blind, kids/wall-sconce, kids/rug, kids/toy-cars, kids/doll, kids/bedding, kids/bedspread, kids/soft-toy, kids/toy-basket, kids/skateboard, kids/doll-pram, kids/desk-chair, bath/shower-dispensers, bath/shower-stool, bath/shower-curtain, bath/floor-planter, bath/towel-ladder, bath/storage-basket, bath/toilet-paper-stand, bath/bin, bath/toilet-brush, bath/ledge-planter, bath/reed-diffuser, bath/candle, bath/soap-dispenser, bath/toothbrush-cup, bath/towel-ring, bath/hand-towel, bath/ceiling-light, corridor/runner-rug, corridor/picture-lights, corridor/gallery-stool

## 30 הרווחיים ביותר (fit 7.5+ במבט, מידה מאומתת)

| # | חדר/עמדה | מוצר | סגנון, fit | נחיתה ₪ | מחיר ₪ | רווח ₪ | % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | dining-room/framed-art | [Bread and Flour Print Country Kitchen Still L](https://www.aliexpress.com/item/1005009177367781.html) | כפרי מודרני 7.5 | 20 | 219 | 145 | 78% |
| 2 | dining-room/framed-art | [Vintage Autumn Farmhouse Dried Herbs Still Li](https://www.aliexpress.com/item/1005009869352182.html) | כפרי מודרני 7.5 | 20 | 219 | 145 | 78% |
| 3 | dining-room/framed-art | [Japandi Wall Art Set of 2 Sage Green Landscap](https://www.aliexpress.com/item/1005012553969661.html) | ג'פנדי 7.5 | 21 | 219 | 144 | 78% |
| 4 | dining-room/framed-art | [Japanese Wabi Sabi Tree Abstract Canvas Print](https://www.aliexpress.com/item/1005012443176323.html) | ג'פנדי 7.5 | 22 | 219 | 144 | 77% |
| 5 | work/framed-art | [Mediterranean Wabi-Sabi Poster Natural Landsc](https://www.aliexpress.com/item/1005011888802890.html) | ים תיכוני 8 | 22 | 219 | 143 | 77% |
| 6 | dining-room/framed-art | [2pcs Mediterranean Landscape Canvas Prints Po](https://www.aliexpress.com/item/1005009401711430.html) | ים תיכוני 7.5 | 23 | 219 | 143 | 77% |
| 7 | work/framed-art | [Scandinavian Minimalist Aesthetic Wall Art Ne](https://www.aliexpress.com/item/1005011956338629.html) | נורדי 7.5 | 24 | 219 | 141 | 76% |
| 8 | corridor/gallery-art | [Simple Nordic Posters Picasso Boho Black Abst](https://www.aliexpress.com/item/1005006634983896.html) | נורדי 8 | 25 | 219 | 140 | 75% |
| 9 | work/framed-art | [Frameless Minimalist Wall Art Set in Brown an](https://www.aliexpress.com/item/1005010493631735.html) | מודרני חם 8.5 | 26 | 219 | 139 | 75% |
| 10 | living-room/framed-art | [Vintage Countryside Wall Art Print Retro Rust](https://www.aliexpress.com/item/1005006849743763.html) | כפרי מודרני 7.5 | 27 | 219 | 138 | 74% |
| 11 | corridor/gallery-art | [Antique Botanical Posters and Prints Rustic F](https://www.aliexpress.com/item/4000153710412.html) | כפרי מודרני 8 | 28 | 219 | 137 | 74% |
| 12 | work/framed-art | [Modern Minimalist Boho Lines Abstract Canvas ](https://www.aliexpress.com/item/1005008404475724.html) | מודרני חם 7.5 | 37 | 219 | 128 | 69% |
| 13 | work/framed-art | [Modern Minimalist Neutral Gallery Wall Art Bl](https://www.aliexpress.com/item/1005006744802995.html) | מודרני חם 8 | 39 | 219 | 126 | 68% |
| 14 | living-room/vase | [Vintage Distressed Clay Vase, Wabi-Sabi Rusti](https://www.aliexpress.com/item/1005012472589009.html) | ג'פנדי 8.5 | 105 | 299 | 121 | 48% |
| 15 | master/curtains | [Natural Linen Voile Curtain 132CM Drop Net Cu](https://www.aliexpress.com/item/1005008289564712.html) | ים תיכוני 7.5 | 62 | 179 | 73 | 48% |
| 16 | living-room/curtains | [Cotton Linen Curtain Look Yarn Tulle S Fold S](https://www.aliexpress.com/item/1005012745902882.html) | נורדי 7.5 | 64 | 179 | 71 | 47% |
| 17 | master/curtains | [Linen Blend Beige Curtains 96 Inches Long for](https://www.aliexpress.com/item/1005008884122000.html) | מודרני חם 8 | 78 | 179 | 56 | 37% |
| 18 | work/pendant | [Rustic Woven Pendant Light Kitchen Island Boh](https://www.aliexpress.com/item/1005009394200914.html) | כפרי מודרני 7.5 | 84 | 179 | 51 | 34% |
| 19 | living-room/curtains | [Natural Linen Curtains 84 Inch Length for Liv](https://www.aliexpress.com/item/1005006755784378.html) | כפרי מודרני 8 | 84 | 179 | 51 | 33% |
| 20 | work/bookends | [Nature Wooden Bookends Desktop Bookshelf Desk](https://www.aliexpress.com/item/1005012292219885.html) | נורדי 7.5 | 23 | 99 | 51 | 60% |
| 21 | living-room/curtains | [Beige Linen Sheer Curtains for Living Room Mo](https://www.aliexpress.com/item/1005004556554205.html) | מודרני חם 8 | 87 | 179 | 47 | 31% |
| 22 | living-room/cushions | [Boho Throw Pillow Cover for Sofa Living Room ](https://www.aliexpress.com/item/1005009261623058.html) | בוהו 7.5 | 30 | 99 | 44 | 53% |
| 23 | work/desk-organizer | [Stationery Storage Wood Vine Rattan Pen Holde](https://www.aliexpress.com/item/1005013248832816.html) | כפרי מודרני 7.5 | 20 | 59 | 24 | 48% |
| 24 | work/curtains | [1pc japanese folk wabi-sabi style crumpled li](https://www.aliexpress.com/item/1005006791212463.html) | ג'פנדי 8 | 111 | 179 | 24 | 16% |
| 25 | work/wall-sconce | [Rattan Bamboo Wall Lamp Sconce Fixture Vintag](https://www.aliexpress.com/item/1005010168671943.html) | בוהו 8 | 66 | 119 | 23 | 23% |
| 26 | dining-room/dining-rug | [Wabi-sabi Style Carpets for Living Room White](https://www.aliexpress.com/item/1005006306177264.html) | ג'פנדי 7.5 | 591 | 799 | 15 | 2% |
| 27 | dining-room/kitchen-runner | [VIKAMA 2PC Modern Minimalist Wabi Sabi Kitche](https://www.aliexpress.com/item/1005012628590923.html) | ג'פנדי 7.5 | 92 | 129 | 5 | 5% |
| 28 | master/bedside-sconces | [Boho Farmhouse Wall Sconces Natural Twine Han](https://www.aliexpress.com/item/1005009708965037.html) | בוהו 7.5 | 88 | 119 | 2 | 2% |

## קבצים

- `<room>.json` / `<room>.md`: כל הרשומות לחדר (גם ב-`../deep-2026-10/<room>.json` למסך "השוואת ספקים" בסטודיו).
- `screen/<room>.jsonl`: כל שורות החיפוש. `detail/<room>.json`: הבדיקה המלאה. `review/<room>.json`: ציוני המבט. `review/sheets/`: גיליונות התמונות.

