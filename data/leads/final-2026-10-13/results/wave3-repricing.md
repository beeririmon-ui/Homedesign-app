# תמחור מחדש לפי שווי בישראל: 62 המנורות והצעצועים של wave 3 (2026-10-14)

> מקור: `wave3-aliexpress.json` → `loss_at_slot_price` (62 שורות, 46 מוצרים עם CE מוצהר, fit 7–8). נתונים מלאים, כולל השוואות עם קישורים: `wave3-repricing.json`.
> שיטה (ה.10): מחיר לפי שווי הפריט בישראל, כ-10–25% מתחת להשוואה הטיפוסית לאותו סוג וגודל, עם תשומת לב למשלוח (₪29 מתחת ל-₪299, חינם מ-₪299). השוואות מ-`il-lighting.json` / `il-decor.json` ומדפים ציבוריים: Nord Light, קמחי, דיל תאורה, ŪBJECT, לדמרקט, Fine Lab, KUALA, הגלריה המקסיקנית, הדודאים, פנטזיה מרוקאית, קארמה, Maileg ישראל, כלנית סריגים, עדינות, צ'ופי (איקאה כרצפה).
> כלכלה בנוסחת הסטודיו: fx 3.3; נטו = מחיר/1.18; תרומה = נטו − נחיתה − (0.02·מחיר + 1.2) − 0.08·נטו; מרווח = תרומה/נטו. הכרטיסים נכתבו offline (`ds.py card --offline`) מה-product.get השמור, בלי שום קריאה ל-API.

## בשורה אחת

- **30 כרטיסים חדשים:** 14 ב-40% ומעלה, 16 מתחת לרף (0–40%, לסמן בסטודיו לפי ה.11).
- **32 שורות עדיין מפסידות** גם בשווי בישראל: אין כרטיס. כמעט כולן מנורות גדולות שהמשלוח שלהן לבד ($94–718) גבוה מהמחיר הישראלי.

## שינויי מחיר לפי עמדה (מחיר העמדה → שווי בישראל)

| עמדה | מחיר עמדה | שווי בישראל | כרטיסים (40%+ / מתחת) | מפסידים |
| --- | --- | --- | --- | --- |
| bath/vanity-sconces | ₪79 | ₪659 | 0 / 2 | 0 |
| bath/wall-sconce | ₪119 | ₪349 | 0 / 2 | 0 |
| dining-room/dining-pendant | ₪229/₪349 | ₪399/₪439 | 0 / 0 | 2 |
| dining-room/kitchen-sconce | ₪119 | ₪229/₪299/₪499 | 10 / 4 | 0 |
| hall/wall-sconce | ₪149 | ₪299 | 0 / 1 | 0 |
| kids/pendant | ₪119 | ₪199 | 0 / 1 | 3 |
| living-room/floor-lamp | ₪229/₪399 | ₪399/₪699/₪949 | 0 / 2 | 3 |
| living-room/pendant | ₪299/₪399 | ₪379/₪399/₪439/₪469 | 0 / 1 | 5 |
| master/bedside-sconces | ₪349 | ₪499 | 1 / 0 | 0 |
| master/pendant | ₪299 | ₪379/₪399/₪439 | 0 / 0 | 4 |
| bath/ceiling-light | ₪149 | ₪369/₪629 | 0 / 0 | 8 |
| corridor/ceiling-lights | ₪249/₪359 | ₪799/₪1199 | 0 / 0 | 2 |
| hall/ceiling-light | ₪199 | ₪399/₪599 | 0 / 0 | 2 |
| kids/doll | ₪49/₪129 | ₪119/₪139 | 1 / 1 | 0 |
| kids/soft-toy | ₪49 | ₪109 | 1 / 0 | 0 |
| kids/toy-cars | ₪129 | ₪149/₪159 | 1 / 1 | 0 |
| master/floor-lamp | ₪349 | ₪399/₪949 | 0 / 1 | 3 |

## מה קיבל כרטיס

| עמדה | מוצר | מחיר | נחיתה | מרווח | כרטיס |
| --- | --- | --- | --- | --- | --- |
| bath/vanity-sconces | גליל טרוורטין על בסיס אגוז (332886) | ₪79 → ₪659 | ₪380.8 | 21.2% ⚑ | `vanity-sconces-aliexpress-walnut-color-yellow-travertine-332886` |
| bath/vanity-sconces | קובייה מטרוורטין IP65 (037853) | ₪79 → ₪659 | ₪454.4 | 8.1% ⚑ | `vanity-sconces-aliexpress-wabi-sabi-yellow-marble-037853` |
| bath/wall-sconce | קובייה מטרוורטין IP65 (037853) | ₪119 → ₪349 | ₪230.5 | 11.3% ⚑ | `wall-sconce-aliexpress-wabi-sabi-yellow-marble-037853` |
| bath/wall-sconce | קובייה מטרוורטין IP65 (430468) | ₪119 → ₪349 | ₪231.8 | 10.9% ⚑ | `wall-sconce-aliexpress-wabi-sabi-natural-stone-430468` |
| dining-room/kitchen-sconce | כדור במבוק על זרוע עץ, תקע EU (632341) | ₪119 → ₪299 | ₪92.4 | 52.7% | `kitchen-sconce-aliexpress-bamboo-lantern-wall-lamp-632341` |
| dining-room/kitchen-sconce | גליל ראטן על זרוע פליז (778712) | ₪119 → ₪299 | ₪104 | 48.1% | `kitchen-sconce-aliexpress-natural-woven-bohemian-rattan-778712` |
| dining-room/kitchen-sconce | כדור במבוק Plug-in על זרוע עץ (159685) | ₪119 → ₪299 | ₪110.7 | 45.5% | `kitchen-sconce-aliexpress-plug-wall-sconce-handcrafted-159685` |
| dining-room/kitchen-sconce | חבל מדורג (856204) | ₪119 → ₪299 | ₪111.4 | 45.2% | `kitchen-sconce-aliexpress-boho-farmhouse-wall-sconces-856204` |
| dining-room/kitchen-sconce | פנס במבוק על זרוע עץ, Plug-in EU (313733) | ₪119 → ₪299 | ₪113.5 | 44.4% | `kitchen-sconce-aliexpress-bamboo-wall-lamp-plug-313733` |
| dining-room/kitchen-sconce | גליל חבל מדורג (215962) | ₪119 → ₪299 | ₪116.2 | 43.3% | `kitchen-sconce-aliexpress-popular-modern-wall-lamps-215962` |
| dining-room/kitchen-sconce | חבל מדורג (143381) | ₪119 → ₪299 | ₪117.1 | 43% | `kitchen-sconce-aliexpress-rattan-wall-lamp-retro-143381` |
| dining-room/kitchen-sconce | חבל מדורג (968057) | ₪119 → ₪499 | ₪199.9 | 42.1% | `kitchen-sconce-aliexpress-joyinled-boho-style-sconce-968057` |
| dining-room/kitchen-sconce | חבל מדורג (425458) | ₪119 → ₪299 | ₪123.5 | 40.4% | `kitchen-sconce-aliexpress-joyinled-hemp-rope-wall-425458` |
| dining-room/kitchen-sconce | חבל מדורג (473459) | ₪119 → ₪299 | ₪124.3 | 40.1% | `kitchen-sconce-aliexpress-joyinled-hemp-rope-wall-473459` |
| dining-room/kitchen-sconce | חצי-גליל חבל קנבוס (747191) | ₪119 → ₪299 | ₪125.1 | 39.8% ⚑ | `kitchen-sconce-aliexpress-vintage-design-hand-woven-747191` |
| dining-room/kitchen-sconce | חבל מדורג (009589) | ₪119 → ₪299 | ₪125.6 | 39.6% ⚑ | `kitchen-sconce-aliexpress-led-vintage-bamboo-sconce-009589` |
| dining-room/kitchen-sconce | חבל מדורג (568607) | ₪119 → ₪299 | ₪128.8 | 38.3% ⚑ | `kitchen-sconce-aliexpress-joyinled-e27-rustic-rattan-568607` |
| dining-room/kitchen-sconce | גליל חבל על זרוע עץ (632957) | ₪119 → ₪229 | ₪100.6 | 37.2% ⚑ | `kitchen-sconce-aliexpress-rustic-wooden-wall-sconce-632957` |
| hall/wall-sconce | חצי-גליל חבל קנבוס (747191) | ₪149 → ₪299 | ₪125.1 | 39.8% ⚑ | `wall-sconce-aliexpress-vintage-design-hand-woven-747191` |
| kids/doll | בובה סרוגה (עבודת יד) (999497) | ₪49 → ₪119 | ₪43.7 | 45.1% | `doll-aliexpress-handmade-crochet-bunny-baby-999497` |
| kids/doll | בובת וולדורף בשיבולת שועל/תכלת, פנים בד (512465) | ₪129 → ₪139 | ₪98.4 | 5.1% ⚑ | `doll-aliexpress-cotton-filled-waldorf-doll-512465` |
| kids/pendant | כיפת ראטן 25 (115646) | ₪119 → ₪199 | ₪129.4 | 12.2% ⚑ | `pendant-aliexpress-joyinled-dia-25-modern-115646` |
| kids/soft-toy | דובי מתולתל בצבע קרמל, 30 (548628) | ₪49 → ₪109 | ₪42.7 | 42.1% | `soft-toy-aliexpress-30cm-lovely-curly-teddy-548628` |
| kids/toy-cars | סט 4 מכוניות בוק טבעי ומפת כביש (147494) | ₪129 → ₪149 | ₪52.3 | 47.3% | `toy-cars-aliexpress-children-s-montessori-traffic-147494` |
| kids/toy-cars | כלי עבודה ומשטרה מבוק עם פרטי אגוז (138166) | ₪129 → ₪159 | ₪115 | 3.4% ⚑ | `toy-cars-aliexpress-wooden-toys-beech-wood-138166` |
| living-room/floor-lamp | פנס בד עמודי על חצובת עץ (217361) | ₪229 → ₪699 | ₪455.1 | 12.6% ⚑ | `floor-lamp-aliexpress-wabi-sabi-japan-floor-217361` |
| living-room/floor-lamp | עמוד עץ מלא כהה, אהיל קפלים לבן ובסיס פליז (518387) | ₪229 → ₪949 | ₪683.2 | 4.5% ⚑ | `floor-lamp-aliexpress-chinese-solid-wood-floor-518387` |
| living-room/pendant | תוף פשתן תלת-שכבתי 40, אור חם (979993) | ₪299 → ₪439 | ₪295.1 | 10% ⚑ | `pendant-aliexpress-wabi-sabi-cloth-pendant-979993` |
| master/bedside-sconces | חבל מדורג (968057) | ₪349 → ₪499 | ₪199.9 | 42.1% | `bedside-sconces-aliexpress-joyinled-boho-style-sconce-968057` |
| master/floor-lamp | עמוד עץ מלא כהה, אהיל קפלים לבן ובסיס פליז (518387) | ₪349 → ₪949 | ₪683.2 | 4.5% ⚑ | `floor-lamp-aliexpress-chinese-solid-wood-floor-518387-master` |

⚑ = מתחת לרף 40% (ה.11). כל הכרטיסים: `status: candidate`, ‏`safety.certificates` עם CE (ו-IP65 בקוביות הטרוורטין) כ-"seller attribute" עם קישור לרישום, `safety.ce: true`. צבעים, משקל ויזואלי ומידות מולאו מתמונות הרישום כהערכה, לבדיקה ב-QA. כל הכרטיסים עוברים את `product-card.schema.json` 1.1.

## מה עדיין מפסיד (בלי כרטיס)

| עמדה | מוצר | שווי בישראל | נחיתה | תרומה |
| --- | --- | --- | --- | --- |
| bath/ceiling-light | טבעת טרוורטין 38 (140025) | ₪629 | ₪864.6 | ₪-388 |
| bath/ceiling-light | זכוכית אופל דונאט 32 (528573) | ₪369 | ₪467.1 | ₪-188 |
| bath/ceiling-light | זכוכית אופל דונאט 32 (122011) | ₪369 | ₪417.6 | ₪-138.5 |
| bath/ceiling-light | טבעת טרוורטין 38 (428551) | ₪629 | ₪598.1 | ₪-121.5 |
| bath/ceiling-light | זכוכית אופל דונאט 32 עם כפתור פליז, אור חם (658332) | ₪369 | ₪380.3 | ₪-101.2 |
| bath/ceiling-light | זכוכית אופל 'אפרסמון' 32 לבן חלבי (056368) | ₪369 | ₪292.8 | ₪-13.7 |
| bath/ceiling-light | זכוכית אופל מדורגת 32 לבן חלבי (324716) | ₪369 | ₪288.4 | ₪-9.3 |
| bath/ceiling-light | זכוכית אופל שמנת 32 (003157) | ₪369 | ₪281.6 | ₪-2.5 |
| corridor/ceiling-lights | תוף זכוכית מצולעת עם פליז 35 (870714) | ₪799 | ₪2250.7 | ₪-1644.9 |
| corridor/ceiling-lights | פנס משי דלעת 40 לבן (682371) | ₪1199 | ₪1775.9 | ₪-866.3 |
| dining-room/dining-pendant | תוף קפלים שמנת 40 (771102) | ₪439 | ₪1115.7 | ₪-783.4 |
| dining-room/dining-pendant | כיפת ראטן חומה 45 (173413) | ₪399 | ₪497.4 | ₪-195.5 |
| hall/ceiling-light | תוף זכוכית מצולעת עם פליז 35 (870714) | ₪399 | ₪1131.5 | ₪-829.6 |
| hall/ceiling-light | פנס משי דלעת 40 לבן (682371) | ₪599 | ₪894.1 | ₪-440.3 |
| kids/pendant | קונוס ראטן 20 (985114) | ₪199 | ₪1073.7 | ₪-923.7 |
| kids/pendant | פעמון חבל עם פרנזים (924801) | ₪199 | ₪564.7 | ₪-414.7 |
| kids/pendant | תוף חבל קלוע 32 (747013) | ₪199 | ₪520.9 | ₪-370.9 |
| living-room/floor-lamp | תוף בד לבן על עמוד חרוזי עץ כהה, 155 (433696) | ₪399 | ₪2842.3 | ₪-2540.4 |
| living-room/floor-lamp | אהיל קפלים לבן, מוט עץ כהה ובסיס פליז (773948) | ₪399 | ₪557.4 | ₪-255.5 |
| living-room/floor-lamp | קפלים לבן, עמוד עץ כהה ובסיס פליז (875443) | ₪399 | ₪533.7 | ₪-231.8 |
| living-room/pendant | תוף קפלים שמנת 40 (771102) | ₪439 | ₪994.4 | ₪-662.1 |
| living-room/pendant | פעמון חבל עם פרנזים (924801) | ₪379 | ₪582.5 | ₪-295.8 |
| living-room/pendant | ראטן וואבי (138088) | ₪399 | ₪500 | ₪-198.1 |
| living-room/pendant | כיפת ראטן חומה 45 (173413) | ₪399 | ₪497.4 | ₪-195.5 |
| living-room/pendant | פנס פשתן סגור 40, ‏3000K (449821) | ₪469 | ₪428.5 | ₪-73.4 |
| master/floor-lamp | תוף בד לבן על עמוד חרוזי עץ כהה, 155 (433696) | ₪399 | ₪2842.3 | ₪-2540.4 |
| master/floor-lamp | אהיל קפלים לבן, מוט עץ כהה ובסיס פליז (773948) | ₪399 | ₪557.4 | ₪-255.5 |
| master/floor-lamp | קפלים לבן, עמוד עץ כהה ובסיס פליז (875443) | ₪399 | ₪533.7 | ₪-231.8 |
| master/pendant | תוף קפלים שמנת 40 (771102) | ₪439 | ₪994.4 | ₪-662.1 |
| master/pendant | פעמון חבל עם פרנזים (924801) | ₪379 | ₪582.5 | ₪-295.8 |
| master/pendant | ראטן וואבי (138088) | ₪399 | ₪500 | ₪-198.1 |
| master/pendant | כיפת ראטן חומה 45 (173413) | ₪399 | ₪497.4 | ₪-195.5 |

הסיבות: משלוח של $94–266 לתלויות ותקרות גדולות (תוף קפלים, פנס משי, זכוכית מצולעת, פעמון חבל, קונוס ראטן), $718 למנורת העמידה עם חרוזים, ומחיר מוצר גבוה בטרוורטין 38. צמודות הזכוכית לאמבטיה (32 ס"מ) שוות בישראל כ-₪407 (קארמה ₪351–432), ולכן ב-₪369 כולן מפסידות; הקרובה ביותר (003157) הייתה מגיעה ל-+1.6% רק ב-₪379 ועם China Post החינמי (14–51 ימים).

## תיקונים בעלות הנחיתה (מסומנים בכרטיס וב-JSON)

- **master/bedside-sconces 968057:** ה-SKU הוא כבר זוג (2pcs), ולכן נחיתה ₪199.9 ולא ₪393.3 (ברשימה נספרו שני זוגות). ‏₪499 לזוג → 42.1%.
- **kids/toy-cars 147494:** '1set car' הוא סט של 4 מכוניות, ולכן נחיתה ₪52.3 ולא ₪143.8 (נספרו 3 סטים). ‏₪149 → 47.3%. לוודא בדף המוצר, לפני המכירה הראשונה, שהסט כולל 4 מכוניות ומפת כביש.
- **kids/pendant 115646:** SKU לבן בלי נורה במקום שחור (אין גוון טבעי); משלוח $1.99 כמו בשני ה-SKU האחים השמורים. נחיתה ₪129.4.
- **floor-lamp 773948 / 875443:** ה-SKU ברשימה הוא מנורת שולחן. גם ה-SKU של מנורת העמידה במשלוח הזול ביותר שראינו (₪557 / ₪534) מפסיד מול שווי ₪399, ולכן לא נכתב כרטיס ולא נוחש משלוח.
- **bath/ceiling-light 056368, 428551, 003157:** נבדקו גם אפשרויות China Post הזולות השמורות (15–52 ימים); עדיין מפסידות.

## צריך את הבעלים

1. **16 כרטיסים מתחת לרף 40%:** לאשר כחריג ה.11 או לוותר. הדקים ביותר: בובת וולדורף ₪139 (5.1%, תרומה ₪6), מכוניות בוק ×3 ₪159 (3.4%, ₪4.6), מנורת עמידה מעץ מלא ₪949 (4.5%), זוג קוביות טרוורטין ₪659 (8.1%). אלה כמעט איזון, וכל החזרה מוחקת אותם.
2. **המחיר בסטודיו:** מחירי העמדה בחבילות לא שונו (מסמכים מחייבים). המחירים כאן הם מחיר מוצע לפי ה.10, והמשתמש מאשר או עורך אותם בבק אופיס.
3. **הדובי המתולתל (548628)** נראה כמו Jellycat Bartholomew: סיכון של חיקוי מותג. לא להציג אותו כ-Jellycat ולא להשוות אליו בדף המוצר.
4. **זוג במטבח:** 968057 נמכר רק כזוג; בעמדת המטבח (מנורה אחת) הוא מתומחר ₪499 לזוג.
5. **תקינה:** CE (ו-IP65) הם הצהרת מוכר בלבד. קובץ התעודה נדרש לפני המכירה הראשונה (S2B), ובצעצועים לא הוצהר EN71, רק CE.
6. **אמבטיה, תאורת תקרה:** כל 8 המועמדים מפסידים. אם רוצים את 003157, זה ₪379 ומשלוח של 14–51 ימים בשביל ₪5 תרומה.
