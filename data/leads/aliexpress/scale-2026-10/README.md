# AliExpress בקנה מידה: סיכום (2026-10-11)

ליקוט בהיקף גדול דרך ה-API הרשמי של AliExpress (סשן עזר, בקשת המשתמש 2026-10-11: "מאות, לא עשרה"). השיטה: `scripts/ae/scale.py` (סינון רחב → בדיקה מלאה של מחיר SKU ומשלוח לישראל → מבט בתמונה → כרטיס). כל העמדות בכל 8 החדרים (132, בלי 16 הרהיטים הקבועים), לכל ששת הסגנונות, שני סבבים (בסבב 2 שאילתות מתוקנות לעמדות שקיבלו תוצאות שגויות).

## במספרים

| | |
| --- | --- |
| שורות סינון (תוצאות חיפוש) | 87,792 |
| מוצרים שנבדקו לעומק (מחיר SKU + משלוח לישראל) | 6,644 |
| מוצרים שנבדקו בעין (גיליונות תמונות) | 3,110 |
| רשומות מוצר×סגנון | 11,522 |
| כרטיסי טיוטה חדשים | 16 |
| קריאות API היום (כל הסשן) | 8,262 |

**מכסה שנצפתה:** אין מכסה יומית מוחזרת. מגבלת קצב: עם 3 תהליכים במקביל (כ-1.8 קריאות בשנייה) AliExpress החזיר `ApiCallLimit` ("this ban will last 1 seconds"); עם 2 במקביל זה קרה לעיתים רחוקות. כל עצירה נרשמה, וההרצה המשיכה מהנקודה שבה עצרה. התקרה העצמית הועלתה ל-12,000 ביום לריצה הזו (`scripts/sourcing/budget.py`).

עצירות שנרשמו:
```
ad3 STOP search at 2026-10-12 08:06:48 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
ad3 STOP search at 2026-10-12 08:13:33 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
ad3 STOP search at 2026-10-12 08:26:36 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
ad3 STOP search at 2026-10-12 08:53:45 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
ad3 STOP search at 2026-10-12 09:00:44 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
ad3 STOP search at 2026-10-12 09:02:37 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
ad3 STOP search at 2026-10-12 09:13:21 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
bath STOP detail at 2026-10-11 17:11:07 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
bath STOP detail at 2026-10-12 04:10:16 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
bath STOP detail at 2026-10-12 04:13:05 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
bath STOP detail at 2026-10-12 07:29:56 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
dining-room STOP detail at 2026-10-12 04:19:14 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
dining-room STOP detail at 2026-10-12 04:22:13 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
dining-room STOP detail at 2026-10-12 04:27:06 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
dining-room STOP detail at 2026-10-12 07:49:16 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
kids STOP detail at 2026-10-11 16:50:12 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
kids STOP detail at 2026-10-12 04:21:06 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
kids STOP detail at 2026-10-12 04:23:04 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
kids STOP detail at 2026-10-12 04:27:10 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
kids STOP detail at 2026-10-12 04:29:04 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
kids STOP detail at 2026-10-12 07:30:02 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
kids STOP detail at 2026-10-12 07:33:02 UTC: flow control: ApiCallLimit | Api access frequency exceeds the limit. this ban will last 1 seconds
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

**כלכלה:** נחיתה = (מחיר ה-SKU שמתאים לחדר + המשלוח הזול עד 45 יום) × 3.3. מחיר לצרכן = הקצה העליון של רצועת השוק בישראל (`data/economics/market-prices.json`; ה.10). רווח לפי `pricing.ts` (מע"מ 18%, סליקה 2% + 1.2, החזרות 8%), לפני CAC. כרטיס נכתב רק עם fit 8+ אחרי מבט בתמונה, SKU שמידתו אומתה מול העמדה, עלות לא גבוהה מהכרטיס הקיים, ורווח 40%+ (VR1; פחות מזה רק כשאין חלופה בעמדה ובסגנון, ומסומן).

## סבב 6 ובדיקת השיטה (2026-10-13)

המשתמש ביקש לבדוק אם השיטה לא טובה. שני ממצאים:
1. **הסינון העדיף זול:** `score_row` דירג לפי מחיר מול רצועת השוק (רמת איקאה), ומוצרים מהסוג הנכון נפלו לפני שמישהו ראה אותם. כלי לכלי עץ: 36 מ-36 נפלו על מחיר. מברשת אסלה: 53 מ-57. מעמד מטריות: 32 מ-49. הבדיקה בעין קיבלה את הזול. **תוקן ב-`scripts/ae/round6.py`:** דירוג לפי איכות (שם המוצר, הזמנות, דירוג), בלי העדפת מחיר, עם תקרה רופפת (עד פי 3 ממחיר העמדה). 15 הטובים לכל עמדה נבדקים לעומק ובעין. המחיר נשפט רק אחרי הבדיקה בעין.
2. **מגבלת ה-API:** סולם מגבות מעץ ב-₪50 עם משלוח חינם (צילום מסך של המשתמש מהאפליקציה) **לא חוזר מ-`aliexpress.ds.text.search` גם עם הכותרת המדויקת** (1 מ-19 תוצאות הוא סולם בכלל), וחיפוש לפי תמונה מצילום המסך מחזיר מוטות מגבת. כלומר, אינדקס החיפוש של ה-DS API הוא תת-קבוצה של הקטלוג באפליקציה. מוצר עם מזהה ידוע נבדק במלואו ב-`product.get`. **פתרון:** API השותפים הרשמי של AliExpress (`aliexpress.affiliate.product.query`, חיפוש על כל הקטלוג; צריך אפליקציית Affiliates ומפתחות `AE_AFF_*` בהגדרות הסביבה), או קישורים מהמשתמש לבדיקה לפי מזהה.
3. **חיפוש לפי תמונה מתמונה נקייה של מוצר מוצא את המוצר עצמו.** שלושה סולמות מצילומי המסך של המשתמש נמצאו בדיוק, עם אותה כותרת: סולם פלדה שחור 1005013278303013, סולם במבוק עם סל 1005012956782008, במבוק 3 מוטות 1005012919677018. חיפוש טקסט עם הכותרות המדויקות לא מצא אף אחד מהם. מכאן שהשיטה הנכונה היא חיפוש לפי תמונה מתמונות ייחוס טובות: כרטיסים עם ציון 8+, ותמונות מהמשתמש. תמונות של פריטי AliExpress בינוניים מביאות עוד מאותו הדבר.
   - **סולם מגבות (מפרט: אלון/טיק מט, 30–45×130–135, תקרה ₪82.5, איזון ₪150, מחיר ₪199):** הפלדה השחורה בנחיתה ₪107 (25% ב-₪199; 40% ב-₪259; לא החומר שבמפרט הנורדי). סולמות הבמבוק בנחיתה ₪280–340 בגלל משלוח ₪215+. הסולם המולבן שהמשתמש שלח (1005004859945504 או דומה לו) הוא סולם קיר קטן למגבת יד, ₪90 בנחיתה, ולא סולם 130 ס"מ.

## כרטיסי הטיוטה

| חדר | עמדה | כרטיס | סגנון, fit | נחיתה ₪ | רווח |
| --- | --- | --- | --- | --- | --- |
| corridor | gallery-art | `gallery-art-aliexpress-antique-botanical-posters-prints-710412` | כפרי מודרני 8 | 28 | 74% |
| corridor | gallery-art | `gallery-art-aliexpress-japanese-wabi-sabi-tree-176323` | ג'פנדי 8 | 25 | 76% |
| corridor | gallery-art | `gallery-art-aliexpress-simple-nordic-posters-picasso-983896` | נורדי 8 | 25 | 75% |
| hall | console-vessel | `console-vessel-aliexpress-ceramic-wabi-sabi-vase-906575` | נורדי 8, ג'פנדי 8 | 203 | 9% (חריג VR1) |
| hall | framed-art | `framed-art-aliexpress-japanese-wabi-sabi-tree-176323` | ג'פנדי 8 | 32 | 72% |
| kids | toy-cars | `toy-cars-aliexpress-let-s-make-wooden-192455` | נורדי 8, ג'פנדי 8 | 19 | 41% |
| living-room | framed-art | `framed-art-aliexpress-japandi-wall-art-set-969661` | ג'פנדי 8 | 38 | 69% |
| living-room | framed-art | `framed-art-aliexpress-mediterranean-wabi-sabi-poster-802890` | ים תיכוני 8 | 29 | 73% |
| living-room | vase | `vase-aliexpress-vintage-distressed-clay-vase-589009` | ג'פנדי 8.5 | 105 | 48% |
| living-room | wall-decor | `wall-decor-aliexpress-japandi-wall-art-set-969661` | ג'פנדי 8 | 29 | 69% |
| work | curtains | `curtains-aliexpress-cotton-linen-curtain-look-902882-work` | נורדי 8 | 128 | 5% (חריג VR1) |
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
| bath/bath-towels | [140x70cm Large Bath Towels Soft Bathroom Washcloth](https://www.aliexpress.com/item/1005006701175783.html) (מודרני חם 7) | 21 | bath-towels-cj-waffle-cotton-milky-white-70x140 (CJ Dropshipping) | 37 |
| bath/vanity-vase | [White Ceramic Mini Vase Minimalist Tabletop Bud Va](https://www.aliexpress.com/item/1005012840529337.html) (נורדי 7) | 27 | vanity-vase-aliexpress-white-ceramic-mini-vase-529337 (AliExpress) | 27 |
| corridor/ceiling-lights | [Bamboo Ceiling Lamp Indoor Ceiling Light E27 Home ](https://www.aliexpress.com/item/1005010079227644.html) (בוהו 7) | 94 | ceiling-lights-cj-silk-pumpkin-lantern-30 (CJ Dropshipping) | 153 |
| corridor/gallery-art | [Japanese Wabi Sabi Tree Abstract Canvas Print Post](https://www.aliexpress.com/item/1005012443176323.html) (ג'פנדי 8) | 25 | gallery-art-cj-black-botanical-cutout-set3 (CJ Dropshipping) | 83 |
| dining-room/candle-holders | [Vintage Metal Taper Candle Holder with Handle Tray](https://www.aliexpress.com/item/1005012396864609.html) (כפרי מודרני 7) | 21 | candle-holders-aliexpress-matte-black-iron-pillar-set2 (AliExpress) | 41 |
| dining-room/condiment-set | [1PC-Solid wood pepper grinder household kitchen ma](https://www.aliexpress.com/item/1005012731736880.html) (נורדי 7.5) | 29 | condiment-set-cj-rubberwood-mill-pair-6in (CJ Dropshipping) | 48 |
| dining-room/framed-art | [Rustic Kitchen Still Life Poster Vintage Bread Art](https://www.aliexpress.com/item/1005011780297081.html) (כפרי מודרני 7) | 19 | framed-art-aliexpress-retro-farmhouse-chicken-botanical-333603 (AliExpress) | 97 |
| dining-room/paper-towel-holder | [1PC Bamboo Paper Towel Holder Kitchen Dining Room ](https://www.aliexpress.com/item/1005009904316063.html) (ג'פנדי 7) | 23 | paper-towel-holder-aliexpress-1pc-bamboo-paper-towel-316063 (AliExpress) | 23 |
| dining-room/tableware-set | [Retro Style Ceramic Matte Marble Pattern Western D](https://www.aliexpress.com/item/1005009834992952.html) (מודרני חם 7) | 27 | tableware-set-cj-speckled-oat-stoneware-bowl-13 (CJ Dropshipping) | 59 |
| dining-room/tea-towel | [Zen Ramie Linen Tea Towel Multipurpose Cloth Kung ](https://www.aliexpress.com/item/1005011827798432.html) (ג'פנדי 7) | 17 | tea-towel-cj-waffle-cotton-beige-45x65-pair (CJ Dropshipping) | 27 |
| hall/ceiling-light | [Nordic LED Ceiling Light with Wood Base Modern Rou](https://www.aliexpress.com/item/1005011997278771.html) (נורדי 7) | 64 | ceiling-light-cj-waxwood-dome-ash-40 (CJ Dropshipping) | 197 |
| hall/framed-art | [Frameless Minimalist Wall Art Set in Brown and Bei](https://www.aliexpress.com/item/1005010493631735.html) (מודרני חם 7) | 26 | framed-art-cj-line-scribble-white-mat-50 (CJ Dropshipping) | 166 |
| hall/table-lamp | [Wabi-Sabi LED Table Lamp Interior Lighting Fixture](https://www.aliexpress.com/item/1005007582176500.html) (ג'פנדי 7) | 73 | table-lamp-cj-white-teardrop-fabric-cone-25x45 (CJ Dropshipping) | 105 |
| hall/wall-hooks | [Wall Mount Wooden Coat Rack with Shelf Multi-Purpo](https://www.aliexpress.com/item/1005012513892313.html) (מודרני חם 7) | 28 | wall-hooks-aliexpress-pine-oval-pegs-4pcs (AliExpress) | 30 |
| hall/wall-sconce | [Rattan Bamboo Wall Lamp Sconce Fixture Vintage Boh](https://www.aliexpress.com/item/1005010168671943.html) (בוהו 7) | 66 | wall-sconce-cj-white-fabric-cube-15-hall (CJ Dropshipping) | 109 |
| kids/bedding | [1pc Solid Color Duvet Cover 100% Washed Cotton Qui](https://www.aliexpress.com/item/1005007425893717.html) (נורדי 7) | 75 | bedding-cj-muslin-cotton-duvet-dune (CJ Dropshipping) | 104 |
| kids/bedspread | [6 Layers Baby Bath Towel Kids Swaddle Wrap Bedding](https://www.aliexpress.com/item/1005006994285109.html) (נורדי 7) | 42 | bedspread-cj-muslin-blanket-beige-150x200 (CJ Dropshipping) | 80 |
| kids/bookshelf | [2Pcs Bookshelf,Natural Wood Floating Wall Bookshel](https://www.aliexpress.com/item/1005008149230106.html) (נורדי 7) | 72 | bookshelf-aliexpress-natural-wood-floating-bookshelf-230106 (AliExpress) | 72 |
| kids/cushions | [New Wildflower Pillow Cover Farmhouse Style 45 x 4](https://www.aliexpress.com/item/1005011530710046.html) (כפרי מודרני 7) | 21 | cushions-cj-corduroy-windmill-patchwork-pink-40 (CJ Dropshipping) | 25 |
| kids/framed-prints | [Japandi Wall Art Set of 2 Sage Green Landscape Pos](https://www.aliexpress.com/item/1005012553969661.html) (ג'פנדי 7) | 21 | framed-prints-cj-flower-cutout-set-30x40 (CJ Dropshipping) | 69 |
| kids/pendant | [Rustic Woven Pendant Light Kitchen Island Boho Han](https://www.aliexpress.com/item/1005009394200914.html) (כפרי מודרני 7) | 84 | pendant-cj-fabric-dome-ash-cap-25 (CJ Dropshipping) | 144 |
| kids/toy-cars | [Let's Make Wooden Baby Toys 0 12 Month 1PC Toys Fo](https://www.aliexpress.com/item/4001204192455.html) (נורדי 8) | 19 | toy-cars-cj-beech-peg-bus (CJ Dropshipping) | 30 |
| kids/wall-sconce | [Nordic Simple Single Rocker Arm Hotel Room Studio ](https://www.aliexpress.com/item/1005008568485604.html) (נורדי 7) | 84 | wall-sconce-cj-black-folding-arm-woodgrain-cone-18 (CJ Dropshipping) | 89 |
| living-room/accent-sconces | [Boho Farmhouse Wall Sconces Natural Twine Hand Kni](https://www.aliexpress.com/item/1005009708965037.html) (בוהו 7) | 88 | accent-sconces-cj-travertine-block-updown-8x16 (CJ Dropshipping) | 122 |
| living-room/basket | [Seaweed Wicker Basket Rattan Hanging Flowerpot  Di](https://www.aliexpress.com/item/1005001597545859.html) (ים תיכוני 7) | 45 | basket-zendrop-seagrass-belly-foldable-38 (Zendrop) | 60 |
| living-room/framed-art | [Vintage Countryside Wall Art Print Retro Rustic Sp](https://www.aliexpress.com/item/1005006849743763.html) (כפרי מודרני 7.5) | 27 | framed-art-cj-morandi-triptych-sage (CJ Dropshipping) | 484 |
| living-room/planter | [Seagrass Wicker Woven Storage Basket Planting Flow](https://www.aliexpress.com/item/1005003094192174.html) (בוהו 7) | 24 | planter-zendrop-seagrass-belly-basket-45 (Zendrop) | 47 |
| living-room/vase | [Vintage Distressed Clay Vase, Wabi-Sabi Rustic Cer](https://www.aliexpress.com/item/1005012472589009.html) (ג'פנדי 8.5) | 105 | vase-aliexpress-vintage-distressed-clay-vase-589009 (AliExpress) | 105 |
| living-room/wall-decor | [Japandi Wall Art Set of 2 Sage Green Landscape Pos](https://www.aliexpress.com/item/1005012553969661.html) (ג'פנדי 8) | 29 | wall-decor-aliexpress-natural-raffia-woven-bohemian-763597 (AliExpress) | 46 |
| master/bedside-sconces | [Boho Farmhouse Wall Sconces Natural Twine Hand Kni](https://www.aliexpress.com/item/1005009708965037.html) (כפרי מודרני 7) | 88 | bedside-sconces-cj-white-fabric-cube-15 (CJ Dropshipping) | 109 |
| work/bookends | [（Summer6）Nature Bamboo Desktop Organizer Bookends ](https://www.aliexpress.com/item/1005010478897382.html) (ג'פנדי 7) | 20 | bookends-aliexpress-bamboo-bookends-897382 (AliExpress) | 20 |
| work/pendant | [Rustic Woven Pendant Light Kitchen Island Boho Han](https://www.aliexpress.com/item/1005009394200914.html) (כפרי מודרני 7.5) | 84 | pendant-cj-fluted-ceramic-wood-cap-short-lantern (CJ Dropshipping) | 115 |
| work/wall-sconce | [Rattan Bamboo Wall Lamp Sconce Fixture Vintage Boh](https://www.aliexpress.com/item/1005010168671943.html) (בוהו 8) | 66 | wall-sconce-cj-black-swan-arm-white-fabric-cone (CJ Dropshipping) | 85 |

## עמדות בלי שום מוצר שמיש מ-AliExpress

אין אף פריט עם fit 7+ במבט בשום סגנון (הסיבה העיקרית בטבלת החדר).

living-room/bowl, dining-room/bench-pad, dining-room/utensil-crock, dining-room/cutting-boards, hall/planter, hall/umbrella-stand, hall/runner-rug, master/basket, work/waste-basket, kids/roman-blind, kids/doll, kids/soft-toy, kids/toy-basket, kids/skateboard, kids/doll-pram, kids/desk-chair, bath/shower-stool, bath/floor-planter, bath/towel-ladder, bath/toilet-paper-stand, bath/bin, bath/toilet-brush, bath/ledge-planter, bath/candle, bath/towel-ring, corridor/runner-rug, corridor/picture-lights, corridor/gallery-stool

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
| 15 | work/desk-lamp | [Nordic Desk Lamp USB Powered Bedside Table La](https://www.aliexpress.com/item/1005008734758186.html) | נורדי 7.5 | 67 | 179 | 68 | 45% |
| 16 | hall/key-tray | [Wabi Sabi Style Acacia Wood Decorative Servin](https://www.aliexpress.com/item/1005012509590290.html) | ג'פנדי 8 | 33 | 129 | 64 | 59% |
| 17 | work/desk-lamp | [Wabi-Sabi LED Table Lamp Interior Lighting Fi](https://www.aliexpress.com/item/1005007582176500.html) | ג'פנדי 7.5 | 73 | 179 | 62 | 40% |
| 18 | work/pendant | [Rustic Woven Pendant Light Kitchen Island Boh](https://www.aliexpress.com/item/1005009394200914.html) | כפרי מודרני 7.5 | 84 | 179 | 51 | 34% |
| 19 | work/bookends | [Nature Wooden Bookends Desktop Bookshelf Desk](https://www.aliexpress.com/item/1005012292219885.html) | נורדי 7.5 | 23 | 99 | 51 | 60% |
| 20 | living-room/cushions | [Boho Throw Pillow Cover for Sofa Living Room ](https://www.aliexpress.com/item/1005009261623058.html) | בוהו 7.5 | 30 | 99 | 44 | 53% |
| 21 | work/desk-organizer | [Stationery Storage Wood Vine Rattan Pen Holde](https://www.aliexpress.com/item/1005013248832816.html) | כפרי מודרני 7.5 | 20 | 59 | 24 | 48% |
| 22 | work/wall-sconce | [Rattan Bamboo Wall Lamp Sconce Fixture Vintag](https://www.aliexpress.com/item/1005010168671943.html) | בוהו 8 | 66 | 119 | 23 | 23% |
| 23 | hall/console-vessel | [Ceramic Wabi Sabi Vase Hotel Home decor Flowe](https://www.aliexpress.com/item/1005009973906575.html) | נורדי 8 | 203 | 299 | 23 | 9% |
| 24 | hall/console-vessel | [French Country Faux Terracotta Metal Vase, Vi](https://www.aliexpress.com/item/1005012450327532.html) | כפרי מודרני 7.5 | 205 | 299 | 21 | 8% |
| 25 | dining-room/floor-vase | [Wabi Sabi Ceramic Vase Handmade Retro Pottery](https://www.aliexpress.com/item/1005008837526491.html) | ג'פנדי 7.5 | 208 | 299 | 18 | 7% |
| 26 | kids/toy-cars | [Let's Make Wooden Baby Toys 0 12 Month 1PC To](https://www.aliexpress.com/item/4001204192455.html) | נורדי 8 | 19 | 49 | 17 | 41% |
| 27 | kids/toy-cars | [1PC Baby Toy Beech Wood Blocks Cartoon Car Ed](https://www.aliexpress.com/item/1005001519152942.html) | נורדי 8 | 20 | 49 | 16 | 40% |
| 28 | kids/toy-cars | [4pc Wooden Baby Car Toys Beech Wooden Blocks ](https://www.aliexpress.com/item/1005012601754833.html) | נורדי 8 | 20 | 49 | 16 | 39% |
| 29 | dining-room/dining-rug | [Wabi-sabi Style Carpets for Living Room White](https://www.aliexpress.com/item/1005006306177264.html) | ג'פנדי 7.5 | 591 | 799 | 15 | 2% |
| 30 | dining-room/condiment-set | [1PC-Solid wood pepper grinder household kitch](https://www.aliexpress.com/item/1005012731736880.html) | נורדי 7.5 | 29 | 59 | 15 | 29% |

## סבבים 6–7 ופידי הקטלוג (2026-10-13): בדיקת השיטה

**מה לא עבד:**
- **מיון לפי מחיר:** סבבים 1–5 מיינו את תוצאות החיפוש לפי מחיר מול הרצועה של השוק (רמת איקאה), ולכן מוצרים מהסוג הנכון נפלו לפני הבדיקה בעין.
- **חיפוש הטקסט:** חיפוש הטקסט של ה-DS API חלקי וחלש ברלוונטיות. סולמות המגבת ששלח המשתמש לא הוחזרו אפילו לפי השם המדויק.

**סבב 6 (round6.py):**
- דירוג לפי איכות בלבד: שם המוצר, הזמנות ודירוג; המחיר רק כתקרה רופפת.
- 3 עמודים לכל שאילתה, 15 המובילים לכל עמדה נבדקו לעומק, ו-354 מוצרים נבדקו בעין בכל 6 הסגנונות.

**סבב 7 (snowball.py):** חיפוש לפי תמונה מהמוצרים שקיבלו בביקורת fit 5 ומעלה, 316 מוצרים חדשים, 105 נבדקו בעין.

**פידי הקטלוג הרשמיים (feeds.py, aliexpress.ds.recommend.feed.get):**
- 5 פידים נקראו. כל פיד חושף בפועל כ-5,000 מוצרים ייחודיים בלבד, ומעבר לזה הדפים חוזרים על עצמם (ה-total המוצהר, למשל 94,652, לא אמיתי). פידי ZA ריקים לישראל.
- סך הכול 19,565 מוצרים ייחודיים, בעיקר רבי-מכר כלליים, עם תפוקה נמוכה לעמדות הנישה (data/leads/aliexpress/catalog-2026-10/matches.md).

**מוצרים שהמשתמש שלח בצילום מסך:** נמצאו בדיוק בחיפוש לפי תמונה (user-refs/2026-10-13-towel.md).

**תוצאה:**
- עמדות בלי אף מוצר בציון 7 ומעלה: ירד מ-28 ל-11.
- כרטיסים חדשים: סל לחדר השינה (464380) וטבעת מגבת (827023).
- מוצרים בציון 8 שנפסלו רק על מחיר, מול רצועת שוק נמוכה מדי (הצעת מחיר למשתמש, "לא אושר"):

| מוצר | נחיתה | מחיר ל-40% |
| --- | --- | --- |
| בובת ולדורף 1005010719659177 | ₪72.5 | ₪179 |
| בובת ולדורף 1005008884671015 | ₪96.6 | ₪239 |
| ארנבת בד 35 ס"מ 1005008817063285 | ₪40.5 | ₪109 |

**עמדות שנשארו בלי ציון 7 ב-AliExpress:**
- כלי לכלי מטבח: רק העתקים של Le Creuset.
- עציץ, מעמד מטריות ושטיח ראנר למבואה. במעמד המטריות יש ליד אם בוחרים מק"ט שחור.
- סקייטבורד: רק קרשים בלי גלגלים.
- כיסא ילד.
- סולם מגבות: הוצעו מחמם מגבות וקולב חרוזים כחלופה, ושינוי העמדה דורש אישור.
- עציץ אדן ונר לאמבטיה.
- שטיח ראנר ומנורות תמונה למסדרון.

**המסקנה לשיטה:**
- חיפוש לפי תמונה מתמונת מוצר נכונה הוא הכלי החזק.
- הצעד הבא הוא תמונות ייחוס טובות לכל עמדה חסרה (צילום מסך מהאפליקציה, או מוצר מספק ישראלי), ומהן חיפוש לפי תמונה.

## קבצים

- `<room>.json` / `<room>.md`: כל הרשומות לחדר (גם ב-`../deep-2026-10/<room>.json` למסך "השוואת ספקים" בסטודיו).
- `screen/<room>.jsonl`: כל שורות החיפוש. `detail/<room>.json`: הבדיקה המלאה. `review/<room>.json`: ציוני המבט. `review/sheets/`: גיליונות התמונות.

