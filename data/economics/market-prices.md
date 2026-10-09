# מחירי שוק ותמחור מומלץ לפי קטגוריה

עודכן: 2026-10-09 · מחקר רשת ושליפה מקטלוגי רשתות. קובץ נתונים: `market-prices.json`. שער חישוב: **₪3.7 לדולר (לעדכן!)** — ברירת המחדל של הסטודיו. הדולר נסחר ב-2026 סביב ₪3.0 (ראו `fulfillment-research.md`), ולכן כל המרווחים כאן שמרניים. עמודת "בשער 3.0" מראה את ההבדל.

**סימון:** **לא אומת** = לא הצלחתי לפתוח מקור ישיר ועדכני. מחיר = מחיר מלא לפני מבצע, כולל מע"מ.

## שורה תחתונה

1. **מה שמרוויח מ-CJ: טקסטיל קל ושטוח.** ציפות לכריות (מרווח חציוני 56% ב-₪99), ראנרים (58% ב-₪129), כיסויי ספה נמתחים (47% ב-₪349), ציפה לשמיכה, מגבות, וקישוט קיר קל. כאן אפשר למכור **מתחת לחציון השוק** ועדיין לעבור את יעד ה-35%.
2. **מה שלא מרוויח: כל מה שכבד, שביר או חשמלי.** אגרטלים, קערות, ספלים, פמוטים, מנורות (שולחן, רצפה, קיר, תלייה), עציצים ושטיח הצמר. המשלוח מ-CJ לבד (בדרך כלל $20–90) גבוה ממחיר המדף של המתחרים. בשער 3.7 אין מחיר תחרותי שמגיע ל-35%. אלה מועמדים למלאי מקומי (ראו `fulfillment-research.md`), או למכירה כמוצר פרימיום מעל החציון, רק כשהמוצר באמת ברמה של Zara Home.
3. **נקודות מחיר:** השוק הישראלי מתמחר כמעט תמיד בסיומת 9 (Fox Home 93%, Home Style 91%). IKEA היא החריגה, עם סיומת 5 (₪95, ₪145, ₪195). ממליץ על מספרים שלמים שמסתיימים ב-9 (₪99, ₪149, ₪199, ₪249), בלי אגורות. זה נראה פרימיום יותר מ-₪99.90 ועדיין נהנה מאפקט הספרה השמאלית.
4. **משלוח חינם מ-₪299, ₪29 מתחת לסף.** זה בטווח של השוק (₪199–349), כ-30–40% מעל סל ממוצע משוער של כ-₪210 (1.4 פריטים), ומעודד צירוף פריט שני. ציפה לכרית לבד ב-₪99 משאירה כ-₪6 אחרי CAC; בסל של 3 פריטים התרומה אחרי CAC היא ₪160–200.
5. **סלים ("שופ דה לוק")** הם הכלי הכי חזק כאן, כי הם מפזרים את ה-CAC ואת עמלת החבילה הקבועה של CJ ($3.72 לחבילה שנחסכת). דוגמה בסעיף 2.3: כיסוי ספה + 2 ציפות ב-10% הנחה = 49% מרווח.
6. **מחיר "לפני" (compare-at): לא בהשקה.** לפי חוק הגנת הצרכן, "מחיר לפני" חייב להיות מחיר שבאמת נגבה לפני המבצע. לאתר חדש אין מחיר כזה. מציגים מחיר אחד, כולל מע"מ.
7. **שיעור המרה צפוי לעיצוב הבית: 1.3–1.9%** (ממוצע כלל המסחר המקוון כ-1.8–3%). כל הנתונים ממקורות של ספקים, לא ממחקר מבוקר.

## שיטה ומקורות

| רשת | פלח | איך נאסף | פריטים מסווגים | אומת? |
| --- | --- | --- | --- | --- |
| IKEA ישראל | נורדי, עממי-ביניים | API החיפוש של ikea.com/il, 46 שאילתות | 30 קטגוריות | כן |
| Fox Home | ביניים | קטלוג Shopify מלא (`products.json`), 1,400 מוצרים | 24 קטגוריות | כן |
| Home Center | עממי | קטלוג Shopify מלא, כ-22,000 מוצרים | 32 קטגוריות | כן |
| Home Style | ביניים (טקסטיל) | קטלוג Shopify מלא, 636 מוצרים | 13 קטגוריות | כן |
| Terminal X (Home) | ביניים-גבוה, מותגים (Fox Home, Laura Ashley, MYKEL, Decorado, Red Carpet) | חיפוש באתר, נתוני המוצרים שבדף; 24 תוצאות ראשונות לכל שאילתה | 27 קטגוריות | כן |
| Naaman | ביניים (כלי שולחן) | חיפוש באתר (Magento) | 4 קטגוריות | כן |
| ACE | עממי (DIY) | חיפוש באתר (Magento) | 18 קטגוריות | כן |
| Zara Home ישראל | פרימיום | האתר חוסם גישה אוטומטית (Akamai). המחירים לקוחים מתקצירי מנוע החיפוש של דפי המוצר ב-zarahome.com/il | 7 קטגוריות | **חלקית** (תקציר חיפוש, לא נפתח ישירות) |
| H&M Home ישראל, Golf&Co, Kitan, Story | — | האתרים חוסמים גישה (403 / הפניה לדף חסימה). Story מוכרת בעיקר אופנה. בחיפוש לא נמצאו מחירים | — | **לא אומת** |
| JYSK ישראל | — | האתר לא עלה | — | **לא אומת** |

- **סיווג:** לפי מילות מפתח בעברית בשם ובסוג המוצר, עם רשימת החרגות (למשל: אגרטל בלי זכוכית ומתכת, כי המוצרים שלנו קרמיים; שטיח בלי שטיחי אמבטיה וכניסה). מידת שטיח ואגרטל נלקחה מהשם או מהווריאנט. כל וריאנט מידה נספר בנפרד.
- **low / median / high:** low = אחוזון 10 של כל השוק. **median = חציון השוק הבינוני והנורדי** (IKEA, Fox Home, Home Style, Terminal X, Naaman, Zara Home), כי זה המיצוב שלנו. אם יש בו פחות מ-8 פריטים, החציון הוא של כל השוק. high = אחוזון 90 של כל השוק.
- **מבצעים:** בזמן הבדיקה חלק גדול מ-Fox Home היה ב-30% הנחה, ו-ACE הציגה מחיר ללא מע"מ. בכל המקרים נלקח המחיר המלא.
- **מגבלות:** סט מצעים משווה בעיקר לזוגי (Home Style דומיננטית). פוף בשוק הוא הדום מרופד, ולנו יש כיסוי סרוג. בכיסוי לספה יש רק 12 פריטים (ביטחון נמוך). בקישוט לחדר ילדים יש בעיקר מדבקות קיר. בקטגוריות האלה המספר הוא הערכה גסה.

## 1. מחירי שוק לפי קטגוריה (₪, כולל מע"מ)

| קטגוריה | פריטים | נמוך (P10) | **חציון** | גבוה (P90) | חציון לפי רשת | ביטחון |
| --- | --- | --- | --- | --- | --- | --- |
| ציפה לכרית נוי (`cushion-cover`) | 144 | ₪21 | **₪100** | ₪180 | Home Center ₪25, IKEA ₪34, Terminal X ₪70, Fox Home ₪130, Home Style ₪190, Zara Home ₪199 | גבוה |
| שמיכת סלון / פלייד (`throw`) | 36 | ₪49 | **₪120** | ₪200 | IKEA ₪79, Fox Home ₪120, Zara Home ₪399 | גבוה |
| כיסוי לספה (`sofa-cover`) | 12 | ₪83 | **₪372** | ₪804 | Home Center ₪110, Home Style ₪499, IKEA ₪710 | נמוך |
| וילונות בד, זוג (`curtains`) | 38 | ₪84 | **₪185** | ₪395 | IKEA ₪185 | בינוני |
| שטיח קטן (עד 1.5 מ"ר, למשל 60x90–80x150) (`rug-small`) | 116 | ₪49 | **₪129** | ₪302 | Home Center ₪65, IKEA ₪125, Home Style ₪129, Zara Home ₪329, Fox Home ₪350, Terminal X ₪420 | גבוה |
| שטיח בינוני (1.5–3.2 מ"ר, למשל 120x170–160x200) (`rug-medium`) | 60 | ₪195 | **₪345** | ₪562 | IKEA ₪225, Home Center ₪250, ACE ₪334, Terminal X ₪450, Home Style ₪469 | גבוה |
| שטיח גדול (מעל 3.2 מ"ר, למשל 160x230 ומעלה) (`rug-large`) | 66 | ₪459 | **₪895** | ₪1,612 | Home Style ₪569, Home Center ₪680, ACE ₪884, Fox Home ₪900, IKEA ₪945, Terminal X ₪2,190 | גבוה |
| אגרטל קטן (עד 25 ס"מ) (`vase-small`) | 65 | ₪19 | **₪42** | ₪95 | Home Center ₪30, IKEA ₪39, ACE ₪70, Zara Home ₪269 | גבוה |
| אגרטל גדול (מעל 25 ס"מ) (`vase-large`) | 30 | ₪78 | **₪327** | ₪655 | IKEA ₪79, ACE ₪80, Terminal X ₪366, Zara Home ₪419 | גבוה |
| קערה קרמית / קערת הגשה (`ceramic-bowl`) | 161 | ₪8 | **₪49** | ₪130 | Home Center ₪15, IKEA ₪15, ACE ₪32, Naaman ₪50, Fox Home ₪60, Terminal X ₪100 | גבוה |
| פמוט / מעמד לנר (`candle-holder`) | 85 | ₪22 | **₪89** | ₪219 | Home Center ₪25, IKEA ₪35, ACE ₪80, Naaman ₪90, Fox Home ₪95, Terminal X ₪186 | גבוה |
| מנורת שולחן (`table-lamp`) | 76 | ₪50 | **₪192** | ₪282 | Home Center ₪50, ACE ₪100, IKEA ₪125, Terminal X ₪210, Fox Home ₪225 | גבוה |
| מנורה עומדת (`floor-lamp`) | 32 | ₪98 | **₪225** | ₪450 | ACE ₪200, IKEA ₪225 | בינוני |
| מנורת קיר (`wall-sconce`) | 52 | ₪60 | **₪125** | ₪299 | IKEA ₪110, ACE ₪150, Terminal X ₪150, Home Center ₪195 | גבוה |
| מנורת תלייה (`pendant`) | 158 | ₪20 | **₪195** | ₪295 | Home Center ₪80, Terminal X ₪159, IKEA ₪195, Fox Home ₪230 | גבוה |
| תמונה ממוסגרת / הדפס (`framed-print`) | 139 | ₪30 | **₪225** | ₪610 | ACE ₪50, Home Center ₪55, IKEA ₪145, Fox Home ₪200, Terminal X ₪438 | גבוה |
| קישוט קיר / מקרמה / מראה דקורטיבית (`wall-decor`) | 67 | ₪29 | **₪175** | ₪515 | Terminal X ₪99, IKEA ₪175, Home Center ₪474 | גבוה |
| סלסלה קלועה (`basket`) | 209 | ₪25 | **₪69** | ₪300 | IKEA ₪59, Home Center ₪60, Fox Home ₪66, Terminal X ₪230, ACE ₪262 | גבוה |
| פוף / הדום (`pouf`) | 81 | ₪262 | **₪495** | ₪850 | ACE ₪354, Home Center ₪449, IKEA ₪495, Terminal X ₪690 | גבוה |
| ראנר לשולחן (`table-runner`) | 53 | ₪16 | **₪130** | ₪140 | Home Center ₪30, IKEA ₪39, Fox Home ₪130, Terminal X ₪255 | גבוה |
| סט מצעים (ציפה + ציפיות, זוגי) (`bedding-set`) | 399 | ₪125 | **₪489** | ₪869 | Home Center ₪120, ACE ₪142, IKEA ₪145, Home Style ₪499, Fox Home ₪520, Terminal X ₪564 | גבוה |
| ציפה לשמיכה (`duvet-cover`) | 121 | ₪120 | **₪370** | ₪480 | Home Center ₪120, Home Style ₪259, Terminal X ₪370, Fox Home ₪380, Zara Home ₪529 | גבוה |
| מגבת רחצה (גוף) (`towels`) | 163 | ₪40 | **₪129** | ₪180 | Home Center ₪30, IKEA ₪55, Home Style ₪129, Fox Home ₪140, Terminal X ₪150, Zara Home ₪180 | גבוה |
| אביזרי אמבטיה (דיספנסר / כוס) (`bath-accessories`) | 109 | ₪19 | **₪60** | ₪153 | Home Center ₪22, IKEA ₪29, ACE ₪33, Fox Home ₪60, Terminal X ₪154 | גבוה |
| צנצנות / אחסוניות מטבח (`kitchen-canisters`) | 147 | ₪15 | **₪50** | ₪100 | Home Center ₪20, IKEA ₪24, ACE ₪26, Fox Home ₪50, Naaman ₪50, Terminal X ₪159 | גבוה |
| מלחייה / פלפלייה / מטחנות (`salt-pepper`) | 50 | ₪13 | **₪60** | ₪130 | ACE ₪20, Home Center ₪20, IKEA ₪34, Naaman ₪70, Terminal X ₪89, Fox Home ₪90 | גבוה |
| קישוט לחדר ילדים (`kids-decor`) | 10 | ₪19 | **₪90** | ₪118 | IKEA ₪19, Home Center ₪90, Home Style ₪369 | נמוך |
| צעצוע (עץ / רך) (`toys`) | 97 | ₪17 | **₪49** | ₪151 | IKEA ₪49, ACE ₪65, Home Center ₪109, Terminal X ₪159 | גבוה |
| ***קטגוריות נוספות מהקטלוג שלנו*** | | | | | | |
| שטיח אמבטיה (`bath-mat`) | 63 | ₪25 | **₪100** | ₪116 | Home Center ₪55, Home Style ₪89, Fox Home ₪100, Terminal X ₪139 | גבוה |
| וילון מקלחת/אמבטיה (`shower-curtain`) | 49 | ₪35 | **₪90** | ₪129 | IKEA ₪44, Home Center ₪60, Fox Home ₪90, Home Style ₪129 | גבוה |
| ספל / מאג (`mug`) | 117 | ₪7 | **₪20** | ₪30 | Home Center ₪15, Fox Home ₪18, IKEA ₪49 | גבוה |
| מגש דקורטיבי (`tray`) | 88 | ₪7 | **₪130** | ₪399 | Home Center ₪37, Fox Home ₪130, Terminal X ₪347 | גבוה |
| עציץ / כיסוי לעציץ (`planter`) | 114 | ₪15 | **₪35** | ₪160 | Home Center ₪35, Fox Home ₪55, Terminal X ₪312 | נמוך |
| גוף תאורה צמוד תקרה (`ceiling-light`) | 91 | ₪80 | **₪180** | ₪450 | Home Center ₪180, ACE ₪235 | נמוך |
| ציפיות לכרית שינה (זוג) (`pillowcases`) | 129 | ₪59 | **₪95** | ₪145 | Home Center ₪30, Fox Home ₪80, Terminal X ₪90, IKEA ₪95, Home Style ₪99 | גבוה |
| כרית ישיבה / לספסל (`seat-cushion`) | 37 | ₪30 | **₪70** | ₪108 | Home Center ₪40, Home Style ₪69, Fox Home ₪70, Terminal X ₪70 | גבוה |

### דוגמאות ומקורות (נבדק 2026-10-09)

לכל קטגוריה: הפריט הקרוב לחציון של כל רשת, ועוד הזול והיקר ביותר. במבצע מופיע גם מחיר המבצע.

**ציפה לכרית נוי**
- IKEA: [SANELA כיסוי לכרית](https://www.ikea.com/il/he/p/sanela-cushion-cover-light-blue-80635998/) (‎50x50 ס"מ‏) — ₪29
- Fox Home: [כרית נוי מרובעת עם דוגמה פרחונית Flow](https://www.foxhome.co.il/products/0335215800) — ₪130, במבצע ₪91
- Home Center: [ציפית לכרית נוי 46*46 הדפס זברה כותנה](https://www.homecenter.co.il/products/5151418794) — ₪25
- Home Style: [כרית נוי, דגם בוהו - כרית נוי](https://www.homestyle.co.il/products/568751772974256-999) (30/50 סמ כרית נוי) — ₪190, במבצע ₪95
- Zara Home: [ציפית מבד פשתן כבד 50x50](https://www.zarahome.com/il/%D7%A6%D7%99%D7%A4%D7%99%D7%AA-%D7%9E%D7%91%D7%93-%D7%A4%D7%A9%D7%AA%D7%9F-%D7%9B%D7%91%D7%93-l46350008) — ₪199 — **לא אומת ישירות** (תקציר חיפוש)
- Terminal X: [ציפית טטרה לכרית נוי / 45x45 (TERMINAL X HOME )](https://www.terminalx.com/catalogsearch/result?q=%D7%9B%D7%A8%D7%99%D7%AA+%D7%A0%D7%95%D7%99) (OS OS OS OS) — ₪70
- Home Center: [ציפה לכרית 46/46 דגם מוזס](https://www.homecenter.co.il/products/5151417935) — ₪10
- Zara Home: [ציפית מפשתן שטוף 40x60](https://www.zarahome.com/il/%D7%A6%D7%99%D7%A4%D7%99%D7%AA-%D7%9E%D7%A4%D7%A9%D7%AA%D7%9F-%D7%A9%D7%98%D7%95%D7%A3-l46392008) — ₪329 — **לא אומת ישירות** (תקציר חיפוש)

**שמיכת סלון / פלייד**
- IKEA: [LAPPKATTFOT שמיכת טלוויזיה](https://www.ikea.com/il/he/p/lappkattfot-throw-brown-black-70598661/) (‎130x170 ס"מ‏) — ₪79
- Fox Home: [שמיכת פליז עם עיטורי מיקי מאוס Star Mickey](https://www.foxhome.co.il/products/0333749900) — ₪120
- Zara Home: [שמיכה ג׳קארד פרחונית 140x190](https://www.zarahome.com/il/%D7%A9%D7%9E%D7%99%D7%9B%D7%94-%D7%92%D7%A7%D7%90%D7%A8%D7%93-%D7%A4%D7%A8%D7%97%D7%95%D7%A0%D7%99%D7%AA-l41386004) — ₪399 — **לא אומת ישירות** (תקציר חיפוש)
- IKEA: [VITMOSSA שמיכת טלוויזיה](https://www.ikea.com/il/he/p/vitmossa-throw-grey-90304889/) (‎120x160 ס"מ‏) — ₪12
- Zara Home: [שמיכה בעיצוב גאומטרי פשתן-כותנה 140x190](https://www.zarahome.com/il/%D7%A9%D7%9E%D7%99%D7%9B%D7%94-%D7%91%D7%A2%D7%99%D7%A6%D7%95%D7%91-%D7%92%D7%90%D7%95%D7%9E%D7%98%D7%A8%D7%99-l49132004) — ₪479 — **לא אומת ישירות** (תקציר חיפוש)

**כיסוי לספה**
- Home Center: [כיסוי לספה דו מושבית בצבע אפור 113*190 ס"מ](https://www.homecenter.co.il/products/5151616429) — ₪110, במבצע ₪70
- IKEA: [SÖDERHAMN ריפוד לספה תלת-מושבית נפתחת](https://www.ikea.com/il/he/p/soederhamn-cover-for-3-seat-sofa-bed-section-kelinge-dark-blue-70630369/) — ₪595
- Home Style: [סט כיסוי סלון 3 חלקים דו צדדי - אפור](https://www.homestyle.co.il/products/1535-104) (O.S כיסוי סלון) — ₪499, במבצע ₪250
- Home Center: [כיסוי לספת יחיד בצבע אפור 57*190 ס"מ](https://www.homecenter.co.il/products/5151616428) — ₪80, במבצע ₪50
- IKEA: [EKTORP ריפוד לספה תלת-מושבית עם שזלונג](https://www.ikea.com/il/he/p/ektorp-cover-f-3-seat-sofa-w-chaise-longue-mangbyn-brown-multicolour-90635554/) — ₪995

**וילונות בד, זוג**
- IKEA: [MAISTANGG וילון/2 כנפיים](https://www.ikea.com/il/he/p/maistangg-curtains-1-pair-off-white-dark-grey-striped-with-heading-tape-30641096/) (‎145x300 ס"מ‏) — ₪175
- IKEA: [MATILDA וילון שקוף/2 כנפיים](https://www.ikea.com/il/he/p/matilda-sheer-curtains-1-pair-pale-pink-with-rod-pocket-90626597/) (‎60x120 ס"מ‏) — ₪35
- IKEA: [DYTÅG וילון/2 כנפיים](https://www.ikea.com/il/he/p/dytag-curtains-1-pair-beige-with-heading-tape-80607820/) (‎145x300 ס"מ‏) — ₪395

**שטיח קטן (עד 1.5 מ"ר, למשל 60x90–80x150)**
- Home Style: [שטיחון, דגם שייני - בז'](https://www.homestyle.co.il/products/3254-128) (70/130 סמ שטיח רצפה) — ₪129, במבצע ₪64
- IKEA: [LOKALTÅG שטיח, סיבים קצרים](https://www.ikea.com/il/he/p/lokaltag-rug-low-pile-beige-grey-60623232/) (‎80x150 ס"מ‏) — ₪125
- Home Center: [שטיח שניל 60/120 Stripe](https://www.homecenter.co.il/products/1765974626157) — ₪70
- Terminal X: [שטיח סיירה קרם-חום SIERRA (RED CARPET)](https://www.terminalx.com/catalogsearch/result?q=%D7%A9%D7%98%D7%99%D7%97) (150X80 160X230 170X120 140x90 200X290 34) — ₪390
- Fox Home: [שטיח עבודת יד לסלון עם דוגמה מובלטת בגוון טבעי Connie](https://www.foxhome.co.il/products/0335700300) (‏ס"מ‎ 150X90) — ₪350, במבצע ₪245
- Zara Home: [שטיח פסים כותנה 60x120](https://www.zarahome.com/il/%D7%A9%D7%98%D7%99%D7%97-%D7%A4%D7%A1%D7%99%D7%9D-l47277029) — ₪329, במבצע ₪160 — **לא אומת ישירות** (תקציר חיפוש)
- IKEA: [TIPHEDE שטיח באריגה שטוחה](https://www.ikea.com/il/he/p/tiphede-rug-flatwoven-natural-black-40592825/) (‎50x80 ס"מ‏) — ₪15
- Home Center: [שטיח לוטוס  9999/11 במידה 2.90*1.90](https://www.homecenter.co.il/products/1761046317190) — ₪670

**שטיח בינוני (1.5–3.2 מ"ר, למשל 120x170–160x200)**
- Home Center: [שטיח רצפה 200*150  סמ אוסקה קשתות בז'](https://www.homecenter.co.il/products/1787574230772) — ₪250
- IKEA: [LEN שטיח, סיבים קצרים](https://www.ikea.com/il/he/p/len-rug-low-pile-beige-dot-pattern-40625109/) (‎133x160 ס"מ‏) — ₪225
- ACE: [שטיח בייבי מנדלה 5248-00 מידה 120/170 ס"מ](https://www.ace.co.il/4490055) — ₪250
- Terminal X: [שטיח טרנדס 02 צבעוני (RED CARPET)](https://www.terminalx.com/catalogsearch/result?q=%D7%A9%D7%98%D7%99%D7%97) (170X120 190X140 160X230 120X80) — ₪450, במבצע ₪225
- Home Style: [שטיח רצפה כביס, סקיי](https://www.homestyle.co.il/products/2170-999) (150/200 סמ שטיח רצפה) — ₪469, במבצע ₪234
- IKEA: [TIPHEDE שטיח באריגה שטוחה](https://www.ikea.com/il/he/p/tiphede-rug-flatwoven-natural-black-40456757/) (‎120x180 ס"מ‏) — ₪79
- Terminal X: [שטיח קילים סקנדינבי 30 שחור/לבן (RED CARPET)](https://www.terminalx.com/catalogsearch/result?q=%D7%95%D7%99%D7%9C%D7%95%D7%9F) (170X120 190X140 160X230 200X290 340X240 ) — ₪750, במבצע ₪225

**שטיח גדול (מעל 3.2 מ"ר, למשל 160x230 ומעלה)**
- IKEA: [LOHALS שטיח באריגה שטוחה](https://www.ikea.com/il/he/p/lohals-rug-flatwoven-natural-40614262/) (‎240x350 ס"מ‏) — ₪995
- Home Center: [שטיח היילנד  1819/89 290*195](https://www.homecenter.co.il/products/1705315018985) — ₪680
- ACE: [שטיח דיאנה שאגי קטיפה ורוד 160/230](https://www.ace.co.il/4488481) — ₪1,049
- Home Style: [שטיח רצפה כביס, סקיי](https://www.homestyle.co.il/products/2170-999) (160/230 סמ שטיח רצפה) — ₪569, במבצע ₪284
- Fox Home: [שטיח עבודת יד לסלון עם דוגמה מובלטת בגוון טבעי Connie](https://www.foxhome.co.il/products/0335700300) (‏ס"מ‎ 240X160) — ₪900, במבצע ₪630
- Terminal X: [שטיח ניקי NIKI (RED CARPET)](https://www.terminalx.com/catalogsearch/result?q=%D7%A9%D7%98%D7%99%D7%97) (300X200) — ₪2,190, במבצע ₪1,971
- Home Center: [שטיח היילנד  0821/90 170*115](https://www.homecenter.co.il/products/1705302148593) — ₪240
- Home Center: [שטיח ניו הרמס 7777/66 3.30*2.40](https://www.homecenter.co.il/products/1661250941977) — ₪3,670, במבצע ₪1,650

**אגרטל קטן (עד 25 ס"מ)**
- IKEA: [PÅSKÖTRÄD אגרטל](https://www.ikea.com/il/he/p/paskoetraed-vase-glass-light-brown-10610538/) (20 ס"מ) — ₪39
- ACE: [אגרטל טארה בז 20 סמ](https://www.ace.co.il/9908806) — ₪70, במבצע ₪28
- Home Center: [אגרטל הנרי 15 ס"מ לבן](https://www.homecenter.co.il/products/1691063440587) — ₪30, במבצע ₪20
- Zara Home: [אגרטל מקרמיקה עם טקסטורה 16 ס"מ](https://www.zarahome.com/il/%D7%90%D7%92%D7%A8%D7%98%D7%9C-%D7%9E%D7%A7%D7%A8%D7%9E%D7%99%D7%A7%D7%94-%D7%A2%D7%9D-%D7%98%D7%A7%D7%A1%D7%98%D7%95%D7%A8%D7%94-l47100046) — ₪269, במבצע ₪150 — **לא אומת ישירות** (תקציר חיפוש)
- IKEA: [VILJESTARK אגרטל](https://www.ikea.com/il/he/p/viljestark-vase-clear-glass-00338577/) (17 ס"מ) — ₪7

**אגרטל גדול (מעל 25 ס"מ)**
- ACE: [אגרטל ציפורים לבן 30 סמ](https://www.ace.co.il/9908821) — ₪80, במבצע ₪32
- Terminal X: [אגרטל MASA (DECORADO)](https://www.terminalx.com/catalogsearch/result?q=%D7%90%D7%92%D7%A8%D7%98%D7%9C) (52CM 52CM) — ₪366
- IKEA: [KONSTFULL אגרטל](https://www.ikea.com/il/he/p/konstfull-vase-clear-glass-patterned-20511953/) (26 ס"מ) — ₪79
- Zara Home: [אגרטל קרמיקה אסימטרי 38.5 ס"מ](https://www.zarahome.com/il/%D7%90%D7%92%D7%A8%D7%98%D7%9C-%D7%A7%D7%A8%D7%9E%D7%99%D7%A7%D7%94-l47122046) — ₪479 — **לא אומת ישירות** (תקציר חיפוש)
- IKEA: [BERGKÖRSBÄR אגרטל](https://www.ikea.com/il/he/p/bergkoersbaer-vase-glass-green-30611042/) (28 ס"מ) — ₪49
- Terminal X: [אגרטל קורל XL (MYKEL)](https://www.terminalx.com/catalogsearch/result?q=%D7%90%D7%92%D7%A8%D7%98%D7%9C) (60CM) — ₪1,055

**קערה קרמית / קערת הגשה**
- Home Center: [קערה 15 סמ פורצלן FABIO](https://www.homecenter.co.il/products/1765114176878) — ₪15
- Fox Home: [קערת הגשה ממלמין בגוון ירוק מרווה Crystal](https://www.foxhome.co.il/products/0332462105) — ₪60, במבצע ₪42
- IKEA: [IKEA 365+ קערה](https://www.ikea.com/il/he/p/ikea-365-bowl-rounded-sides-white-20278351/) (16 ס"מ) — ₪15
- Naaman: [קערה SUNNY](https://www.naamanp.co.il/2612_998) — ₪50, במבצע ₪20
- Terminal X: [קערה 26 MINTY (FOX HOME)](https://www.terminalx.com/catalogsearch/result?q=%D7%A7%D7%A2%D7%A8%D7%94) — ₪100, במבצע ₪40
- ACE: [קערה + מכסה 9 ליטר](https://www.ace.co.il/9908565) — ₪26, במבצע ₪22
- Home Center: [קערת קונוס גאומטרי WIN - בינוני](https://www.homecenter.co.il/products/1756730854648) — ₪3
- Terminal X: [קערת קורל (MYKEL)](https://www.terminalx.com/catalogsearch/result?q=%D7%A7%D7%A2%D7%A8%D7%94) (36CM) — ₪835

**פמוט / מעמד לנר**
- IKEA: [KUNGSTÄRNA פמוט](https://www.ikea.com/il/he/p/kungstaerna-candlestick-clear-glass-gold-colour-70623745/) (19 ס"מ) — ₪35
- Terminal X: [פמוט OCRA (DECORADO)](https://www.terminalx.com/catalogsearch/result?q=%D7%A4%D7%9E%D7%95%D7%98) — ₪185
- Fox Home: [פמוט מתכת 22 ס"מ בגוון זהב Terra](https://www.foxhome.co.il/products/0332329901) — ₪100, במבצע ₪70
- Home Center: [פמוט סטון דגם נטורל 11*16](https://www.homecenter.co.il/products/1755168206137) — ₪25
- ACE: [פמוט אורך 48 סמ מתכת זהב Crush](https://www.ace.co.il/9909984) — ₪80, במבצע ₪68
- Naaman: [פמוט כסף Silver light](https://www.naamanp.co.il/11310164) — ₪90, במבצע ₪18
- IKEA: [FINSMAK פמוט](https://www.ikea.com/il/he/p/finsmak-candlestick-clear-glass-80630774/) (4 ס"מ) — ₪5
- Terminal X: [זוג פמוטים ROXANA קריסטל בוהמיה 31 ס״מ (Bohemia)](https://www.terminalx.com/catalogsearch/result?q=%D7%A4%D7%9E%D7%95%D7%98) — ₪674

**מנורת שולחן**
- IKEA: [ÅRSTID מנורת שולחן](https://www.ikea.com/il/he/p/arstid-table-lamp-brass-white-30321373/) — ₪125
- Home Center: [מנורת שולחן עם בסיס E-27 ורוד(לרכישה באתר בלבד)](https://www.homecenter.co.il/products/7272000195) — ₪50
- Fox Home: [מנורת שולחן עם בסיס קרמי ואהיל בד בהיר Lian](https://www.foxhome.co.il/products/0336582400) — ₪200, במבצע ₪140
- Terminal X: [מנורה BISTRO WAVES לבן (STYLISTIC)](https://www.terminalx.com/catalogsearch/result?q=%D7%9E%D7%A0%D7%95%D7%A8%D7%AA+%D7%A9%D7%95%D7%9C%D7%97%D7%9F) — ₪230
- ACE: [מנורת שולחן 8237 צבע אדום](https://www.ace.co.il/7614826) — ₪100
- IKEA: [BARLAST מנורת שולחן](https://www.ikea.com/il/he/p/barlast-table-lamp-black-white-00504557/) (31 ס"מ) — ₪19
- IKEA: [STOCKHOLM 2025 מנורת שולחן](https://www.ikea.com/il/he/p/stockholm-2025-table-lamp-white-textile-brass-plated-90585926/) (65 ס"מ) — ₪345

**מנורה עומדת**
- IKEA: [IKEA PS 2026 מנורה עומדת, תאורה עילית](https://www.ikea.com/il/he/p/ikea-ps-2026-floor-uplighter-yellow-80608532/) (182 ס"מ) — ₪225
- ACE: [מנורת עמידה 1393 ורוד](https://www.ace.co.il/7403018) — ₪200
- IKEA: [BARLAST מנורה עומדת](https://www.ikea.com/il/he/p/barlast-floor-lamp-black-white-10430368/) (150 ס"מ) — ₪49
- IKEA: [STOCKHOLM 2025 מנורה עומדת](https://www.ikea.com/il/he/p/stockholm-2025-floor-lamp-white-textile-brass-plated-50585914/) (159 ס"מ) — ₪495

**מנורת קיר**
- Home Center: [מנורת קיר CARDO 180 UP AND DOWN 2X4W גוון צהוב שחור](https://www.homecenter.co.il/products/1755092006749) — ₪220, במבצע ₪176
- IKEA: [ÅRSTID מנורת קיר](https://www.ikea.com/il/he/p/arstid-wall-lamp-brass-white-50321386/) — ₪95
- ACE: [מנורת קיר דגם וינטג' מייפל](https://www.ace.co.il/7639881) — ₪150
- Terminal X: [מנורה WAVES S לבן (STYLISTIC)](https://www.terminalx.com/catalogsearch/result?q=%D7%9E%D7%A0%D7%95%D7%A8%D7%AA+%D7%A9%D7%95%D7%9C%D7%97%D7%9F) — ₪150
- Home Center: [זרוע צמוד קיר למסך בגודל 13 עד 43 אינץ](https://www.homecenter.co.il/products/1745228643743) — ₪40, במבצע ₪30
- Home Center: [קולט אדים צמוד קיר זכוכית שחור MIDEA 60V71-B](https://www.homecenter.co.il/products/1704897792280) — ₪1,090

**מנורת תלייה**
- Home Center: [קולב נירוסטה 4 כפול ניקל](https://www.homecenter.co.il/products/8080709208) — ₪80
- IKEA: [BÄCKNATE אהיל מנורת תלייה](https://www.ikea.com/il/he/p/baecknate-pendant-lamp-shade-white-60578791/) (50 ס"מ) — ₪195
- Fox Home: [לוח תלייה לקיר מחורץ ממתכת בגוון שחור Libby](https://www.foxhome.co.il/products/298920200) — ₪230, במבצע ₪60
- Terminal X: [צעצועים לתלייה לאוניברסיטה  ארנב ורוד, גזר, כוכב JABADABADO (MEKUPELET)](https://www.terminalx.com/catalogsearch/result?q=%D7%A6%D7%A2%D7%A6%D7%95%D7%A2) — ₪159
- Home Center: [קולב בודד 840 מושחר עתיק](https://www.homecenter.co.il/products/8081214280) — ₪11
- IKEA: [STOCKHOLM 2025 מנורת תלייה](https://www.ikea.com/il/he/p/stockholm-2025-pendant-lamp-glass-brass-plated-90585950/) (54 ס"מ) — ₪745

**תמונה ממוסגרת / הדפס**
- Home Center: [מפצל HDMI ל 3](https://www.homecenter.co.il/products/7071300993) — ₪55, במבצע ₪30
- Terminal X: [תמונת קנבס - CAN-RYK052 (EFRAT ILAN)](https://www.terminalx.com/catalogsearch/result?q=%D7%AA%D7%9E%D7%95%D7%A0%D7%94) (15040 80X35) — ₪450
- IKEA: [BLODFLÄDER תמונה ממוסגרת](https://www.ikea.com/il/he/p/blodflaeder-picture-two-birds-00601921/) (‎40x50 ס"מ‏) — ₪145
- Fox Home: [תמונת קיר דקורטיבית בעיצוב בוטני Leaf](https://www.foxhome.co.il/products/0332680300) — ₪200, במבצע ₪150
- ACE: [תמונה קנבס מודפסת Marny](https://www.ace.co.il/9909969) — ₪50, במבצע ₪42
- Home Center: [מארז תבריג RF לכבלים נקבה נקבה](https://www.homecenter.co.il/products/7069905105) — ₪13
- Terminal X: [תמונת קנבס - CAN-PRH059 (EFRAT ILAN)](https://www.terminalx.com/catalogsearch/result?q=%D7%AA%D7%9E%D7%95%D7%A0%D7%94) (150X100) — ₪1,000

**קישוט קיר / מקרמה / מראה דקורטיבית**
- IKEA: [LINDBYN מראה](https://www.ikea.com/il/he/p/lindbyn-mirror-black-70590448/) (50 ס"מ) — ₪175
- Home Center: [מראה עגולה PlatinumBlack בצבע שחור במידות 50X50](https://www.homecenter.co.il/products/1782655223898) — ₪360, במבצע ₪252
- Terminal X: [קישוט קיר חמסה לאהוב (MYKEL)](https://www.terminalx.com/catalogsearch/result?q=%D7%A7%D7%99%D7%A9%D7%95%D7%98+%D7%A7%D7%99%D7%A8) — ₪99
- IKEA: [LÖNSÅS מראה](https://www.ikea.com/il/he/p/loensas-mirror-50471026/) (‎21x30 ס"מ‏) — ₪10
- Home Center: [מראה עץ מלא 110X186X7.5 WOOP WHITE NVENGER](https://www.homecenter.co.il/products/1777298407252) — ₪1,800, במבצע ₪1,080

**סלסלה קלועה**
- Home Center: [סל קש עגול דגם חבלים S](https://www.homecenter.co.il/products/2020485409) — ₪60
- IKEA: [FLÅDIS סלסילה](https://www.ikea.com/il/he/p/fladis-basket-seagrass-60322173/) (25 ס"מ) — ₪59
- Fox Home: [סלסלת קש מלבנית בגוון טבעי Maui](https://www.foxhome.co.il/products/0334540300) — ₪70, במבצע ₪49
- Terminal X: [סנסיווריה ירוקה L בסלסלת לאגוס (PLANT IT)](https://www.terminalx.com/catalogsearch/result?q=%D7%A1%D7%9C%D7%A1%D7%9C%D7%94) (L) — ₪230
- ACE: [ספסל אחסון קורדרוי דגם TOMAS אבן](https://www.ace.co.il/4495103) — ₪262
- Home Center: [סלסלת אטבים עם ידית קשיחה](https://www.homecenter.co.il/products/6766612011) — ₪10
- IKEA: [METOD / MAXIMERA ארון תחתון לכיריים/מגירה/2 סלסילות](https://www.ikea.com/il/he/p/metod-maximera-base-cab-f-hob-drawer-2-wire-bskts-white-voxtorp-dark-grey-s99463770/) (‎60x60 ס"מ‏) — ₪1,285

**פוף / הדום**
- Home Center: [סט פוף Shelly והדום Dotcom Quilt צבע אפור](https://www.homecenter.co.il/products/1745870435849) — ₪449
- IKEA: [LILLESÄTER הדום](https://www.ikea.com/il/he/p/lillesaeter-pouffe-axvall-off-white-40619066/) — ₪495
- ACE: [הדום ישיבה באורך 85 ס"מ עשוי במבוק דגם J42](https://www.ace.co.il/4501526) — ₪321
- Terminal X: [הדום לאונרדו 01 לבן 60*60*45 LEONARDO 01 (RED CARPET)](https://www.terminalx.com/catalogsearch/result?q=%D7%94%D7%93%D7%95%D7%9D) (60X60) — ₪690, במבצע ₪207
- Home Center: [ציר כפוף (זוג במארז)](https://www.homecenter.co.il/products/8081213907) — ₪20
- Terminal X: [הדום BUKALA FABRIC CREAM (LIFE STYLE)](https://www.terminalx.com/catalogsearch/result?q=%D7%94%D7%93%D7%95%D7%9D) — ₪1,360

**ראנר לשולחן**
- Home Center: [סט 4 פלייסמטים 30*45 סמ כסוף SHINY](https://www.homecenter.co.il/products/1724577659280) — ₪30
- Fox Home: [ראנר שולחן בעיצוב גאומטרי בגווני ירוק ושמנת Terra](https://www.foxhome.co.il/products/0333929996) — ₪130, במבצע ₪91
- IKEA: [VÅRARV מפת ראנר](https://www.ikea.com/il/he/p/vararv-table-runner-dark-grey-natural-20545854/) (‎35x150 ס"מ‏) — ₪39
- Terminal X: [ראנר לימונים כותנה (RANGOLI HOME DESIGN)](https://www.terminalx.com/catalogsearch/result?q=%D7%A8%D7%90%D7%A0%D7%A8) (180X40 280X40) — ₪215
- Home Center: [פלייסמט 33*48 נקודות גארדן](https://www.homecenter.co.il/products/5150614563) — ₪10
- Terminal X: [ראנר הורטנזיה כחולה כותנה (RANGOLI HOME DESIGN)](https://www.terminalx.com/catalogsearch/result?q=%D7%A8%D7%90%D7%A0%D7%A8) (280X40) — ₪295

**סט מצעים (ציפה + ציפיות, זוגי)**
- Home Style: [סט מצעי פרקל כותנה EXCLUSIVE - ענבל](https://www.homestyle.co.il/products/3073-999) (120/200 סמ מיטה וחצי) — ₪499, במבצע ₪250
- IKEA: [ÄNGSLILJA ציפה ו-2 ציפיות](https://www.ikea.com/il/he/p/aengslilja-duvet-cover-and-2-pillowcases-dark-blue-60636611/) (‎200x220/50x70 ס"מ‏) — ₪145
- Home Center: [סט מיטה וחצי 120/200 סמ נטלי](https://www.homecenter.co.il/products/1787648348425) — ₪120
- Fox Home: [סט מצעי סאטן בדוגמת פרחים בשילוב עלים בגוונים טבעיים Yulia](https://www.foxhome.co.il/products/0331729900) (‏ס"מ‎ 90X200) — ₪440, במבצע ₪308
- ACE: [סט מצעים למיטה וחצי דגם בוב חיוך גדול](https://www.ace.co.il/4475434) — ₪143
- Terminal X: [סט מצעים 100% כותנה סאטן (REPLAY)](https://www.terminalx.com/catalogsearch/result?q=%D7%9E%D7%A6%D7%A2%D7%99%D7%9D) (90X200 120X200 160X200 180X200 90X200 12) — ₪539, במבצע ₪270
- Home Style: [סט מצעי סאטן כותנה, קריסטין - כחול](https://www.homestyle.co.il/products/3005-107) (2X50/70 סמ זוג ציפיות) — ₪29
- Home Style: [סט מצעי סאטן, כותנה מצרית, ונוס - אבן](https://www.homestyle.co.il/products/3259-219) (220/200 סמ מיטה זוגי מיוחד) — ₪1,799, במבצע ₪900

**ציפה לשמיכה**
- Fox Home: [ציפת פרקל לבנה עם עיטורי תחרה עדינים Orchid](https://www.foxhome.co.il/products/0331910100) (‏ס"מ‎ 150X200) — ₪380, במבצע ₪266
- Home Style: [ציפה כותנה חלקה - ורוד Mix&Match](https://www.homestyle.co.il/products/1530-116) (220/200 סמ ציפה) — ₪259, במבצע ₪119
- Home Center: [ציפה זוגית 220/200 ס"מ גרסי 100% כותנה פיסטוק MOON](https://www.homecenter.co.il/products/1707832882588) — ₪120
- Terminal X: [ציפה 002X051 CARLY (FOX HOME)](https://www.terminalx.com/catalogsearch/result?q=%D7%A6%D7%99%D7%A4%D7%94+%D7%9C%D7%9B%D7%A8%D7%99%D7%AA) (150X200) — ₪370, במבצע ₪148
- Zara Home: [ציפה מפשתן מנוגד 150x220 (יחיד)](https://www.zarahome.com/il/%D7%A6%D7%99%D7%A4%D7%94-%D7%9E%D7%A4%D7%A9%D7%AA%D7%9F-%D7%9E%D7%A0%D7%95%D7%92%D7%93-l44126088) — ₪399 — **לא אומת ישירות** (תקציר חיפוש)
- Home Center: [ציפה לשמיכה 200*150 גרסי סגול](https://www.homecenter.co.il/products/5150216537) — ₪50
- Zara Home: [ציפה מפשתן מנוגד 150/160 (זוגי)](https://www.zarahome.com/il/%D7%A6%D7%99%D7%A4%D7%94-%D7%9E%D7%A4%D7%A9%D7%AA%D7%9F-%D7%9E%D7%A0%D7%95%D7%92%D7%93-l44126088) — ₪659 — **לא אומת ישירות** (תקציר חיפוש)

**מגבת רחצה (גוף)**
- Home Style: [מגבת ג'אקרד, דגם לוסיל - אפור כהה](https://www.homestyle.co.il/products/3241-105) (70/130 סמ מגבת גוף) — ₪129, במבצע ₪64
- Fox Home: [מגבת רחצה Diva](https://www.foxhome.co.il/products/0243452105) — ₪140, במבצע ₪98
- Home Center: [מגבת גוף ענקית 70X150 ס"מ 100% כותנה אפור כהה](https://www.homecenter.co.il/products/1667395395260) — ₪30
- IKEA: [BROKGINST מגבת רחצה](https://www.ikea.com/il/he/p/brokginst-bath-towel-white-00614443/) (‎70x140 ס"מ‏) — ₪55
- Terminal X: [מגבת גוף מגבת כותנה 550  REPLAY (REPLAY)](https://www.terminalx.com/catalogsearch/result?q=%D7%9E%D7%92%D7%91%D7%AA) (140x90 130x70 140x90 130x70 140x90 130x7) — ₪150, במבצע ₪60
- Zara Home: [מגבת רחצה מכותנה עם פסים](https://www.zarahome.com/il/%D7%9E%D7%92%D7%91%D7%AA-%D7%A8%D7%97%D7%A6%D7%94-%D7%9E%D7%9B%D7%95%D7%AA%D7%A0%D7%94-%D7%A2%D7%9D-%D7%A4%D7%A1%D7%99%D7%9D-l41515013) — ₪180 — **לא אומת ישירות** (תקציר חיפוש)
- IKEA: [LUDDVIAL מגבת רחצה](https://www.ikea.com/il/he/p/luddvial-bath-towel-white-10579868/) (‎55x120 ס"מ‏) — ₪10
- Home Style: [מגבת רחצה פרימיום, דגם הדסון  - קרם](https://www.homestyle.co.il/products/3036-219) (90/140 סמ מגבת ענק) — ₪225, במבצע ₪112

**אביזרי אמבטיה (דיספנסר / כוס)**
- Fox Home: [דיספנסר לסבון בגוון אפור Icon](https://www.foxhome.co.il/products/0336875800) — ₪60, במבצע ₪42
- Home Center: [מעמד לסבון מוצק דגם מיורקה](https://www.homecenter.co.il/products/6763211194) — ₪20
- ACE: [דיספנסר ויקי- שחור](https://www.ace.co.il/3100165) — ₪33
- Terminal X: [סט דיספנסר לסבון נוזלי וצנצנת Lyon - שחור (ESSENTIALS.)](https://www.terminalx.com/catalogsearch/result?q=%D7%93%D7%99%D7%A1%D7%A4%D7%A0%D7%A1%D7%A8) — ₪148
- IKEA: [SILVTJÄRN מעמד למברשות שיניים](https://www.ikea.com/il/he/p/silvtjaern-toothbrush-holder-30501915/) — ₪29
- Home Center: [סבונייה אליס - שמנת](https://www.homecenter.co.il/products/6763110801) — ₪5
- Terminal X: [מארז דיספנסר, כוס ומגש שיש L - לבן (STUDIO MARMO)](https://www.terminalx.com/catalogsearch/result?q=%D7%93%D7%99%D7%A1%D7%A4%D7%A0%D7%A1%D7%A8) — ₪373

**צנצנות / אחסוניות מטבח**
- Home Center: [צנצנת זכוכית 1000 מל ACACIA](https://www.homecenter.co.il/products/1752065285438) — ₪20
- Fox Home: [אחסונית לתה ממתכת עם ידית מעץ Simple](https://www.foxhome.co.il/products/0325339401) — ₪50, במבצע ₪35
- IKEA: [BRUGDHAJ צנצנת עם מכסה](https://www.ikea.com/il/he/p/brugdhaj-jar-with-lid-beige-10596170/) (0.3 ל') — ₪25
- Naaman: [צנצנת זכוכית מכסה עץ - 1.9 ליטר](https://www.naamanp.co.il/41324819) — ₪50, במבצע ₪20
- ACE: [צנצנת זכוכית 1 ליטר מכסה עץ השיטה Arche](https://www.ace.co.il/9909790) — ₪26, במבצע ₪22
- Terminal X: [צנצנת שיש Sofia ג' 10 סמ - לבן (STUDIO MARMO)](https://www.terminalx.com/catalogsearch/result?q=%D7%A6%D7%A0%D7%A6%D7%A0%D7%AA) — ₪159
- Home Center: [צנצנת מלח/פלפל זכוכית+ידית ומכסה מתכת צבעוני](https://www.homecenter.co.il/products/2020244026) — ₪6
- Terminal X: [זוג צנצנות שיש Sofia S/L - לבן (STUDIO MARMO)](https://www.terminalx.com/catalogsearch/result?q=%D7%A6%D7%A0%D7%A6%D7%A0%D7%AA) — ₪318

**מלחייה / פלפלייה / מטחנות**
- Home Center: [זוג מגבות מטבח 40/70 סמ מלח ופלפל](https://www.homecenter.co.il/products/1713703224926) — ₪20
- Terminal X: [שמפו משקם ללא מלחים 400 מ"ל Silica (SILICA)](https://www.terminalx.com/catalogsearch/result?q=%D7%9E%D7%9C%D7%97) (400ML) — ₪89, במבצע ₪76
- IKEA: [AFTONHAJ סט מלחיה/פלפליה, 2 חלקים](https://www.ikea.com/il/he/p/aftonhaj-salt-pepper-shaker-set-of-2-stainless-steel-beech-walnut-40623742/) (8.5 ס"מ) — ₪39
- Fox Home: [סט מלח פלפל מזכוכית Homey Cooking](https://www.foxhome.co.il/products/0293579998) — ₪90, במבצע ₪27
- Naaman: [מלחייה נירוסטה](https://www.naamanp.co.il/11308208) — ₪70, במבצע ₪42
- ACE: [מלחייה זכוכית 125 מל](https://www.ace.co.il/9907440) — ₪19
- Home Center: [צנצנת מלח/פלפל זכוכית+ידית ומכסה מתכת צבעוני](https://www.homecenter.co.il/products/2020244026) — ₪6
- Terminal X: [זוג מלחיות פתוחות שיש וכפיות זהב על מגש עץ כהה 20/10 גובה 8 ס״מ (NOVELL COLLECTION)](https://www.terminalx.com/catalogsearch/result?q=%D7%9E%D7%9C%D7%97) — ₪500

**קישוט לחדר ילדים**
- Home Center: [מדבקת  קיר צורות  לחדרי ילדים](https://www.homecenter.co.il/products/5840901223) — ₪90
- IKEA: [ALPTALL סט מדבקות קישוט, 3 יח'](https://www.ikea.com/il/he/p/alptall-decoration-stickers-set-of-3-multicolour-himalayan-animals-and-plants-20625186/) — ₪19
- Home Style: [שטיח רצפה כביס לילדים - סטיץ תמונות](https://www.homestyle.co.il/products/3131-999) (110/160 סמ שטיח רצפה) — ₪369, במבצע ₪184

**צעצוע (עץ / רך)**
- IKEA: [ALPTALL צעצוע רך](https://www.ikea.com/il/he/p/alptall-soft-toy-pallass-cat-grey-40620625/) (31 ס"מ) — ₪49
- Home Center: [משטח פעילות לילדים דגם איילים](https://www.homecenter.co.il/products/1774278019709) — ₪119
- ACE: [סט מגדל טבעות 6 חלקים + צעצוע משיכה מעודד הליכה מתגלגל מעץ מלא - שועל ורוד](https://www.ace.co.il/4449918) — ₪64
- Terminal X: [צעצועים לתלייה לאוניברסיטה  ארנב ורוד, גזר, כוכב JABADABADO (MEKUPELET)](https://www.terminalx.com/catalogsearch/result?q=%D7%A6%D7%A2%D7%A6%D7%95%D7%A2) — ₪159
- IKEA: [FABLER BJÖRN צעצוע רך](https://www.ikea.com/il/he/p/fabler-bjoern-soft-toy-beige-00141401/) (21 ס"מ) — ₪9
- ACE: [ארגונית צעצועים 4KIDS קרם](https://www.ace.co.il/4477774) — ₪618

**שטיח אמבטיה**
- Fox Home: [שטיח אמבטיה מכותנה בצורת פרח Alina](https://www.foxhome.co.il/products/0335999401) — ₪100, במבצע ₪70
- Home Center: [שטיח אמבטיה נגד החלקה פי.וי.סי אובלי לבן ריבועים](https://www.homecenter.co.il/products/1712061181042) — ₪60, במבצע ₪30
- Home Style: [Benetton Essential Bath Mat - פטרול](https://www.homestyle.co.il/products/2029-227) (50/80 סמ מגבת רצפה) — ₪89, במבצע ₪53
- Terminal X: [Laura Ashley -שטיח אמבטיה 100% כותנה - אפור (LAURA ASHLEY)](https://www.terminalx.com/catalogsearch/result?q=%D7%A9%D7%98%D7%99%D7%97) (70X30) — ₪139, במבצע ₪56
- Home Center: [AB5826 שטיח אמבטיה אובלי BASIC 33.5*61 (24)](https://www.homecenter.co.il/products/1769421529085) — ₪10
- Fox Home: [שטיח אמבט בגוון בז׳ Lucia](https://www.foxhome.co.il/products/0164836000) — ₪200, במבצע ₪60

**וילון מקלחת/אמבטיה**
- Home Center: [וילון אמבט 180*200 צבעי ים](https://www.homecenter.co.il/products/1726399952981) — ₪60, במבצע ₪30
- Home Style: [וילון אמבטיה ג'אקרד - כחול](https://www.homestyle.co.il/products/2063-107) (180/180 סמ וילון אמבט) — ₪129, במבצע ₪64
- IKEA: [LUDDHAGTORN וילון למקלחת](https://www.ikea.com/il/he/p/luddhagtorn-shower-curtain-light-beige-00649664/) (‎180x200 ס"מ‏) — ₪29
- Fox Home: [וילון אמבטיה בדוגמת  לבבות בצבעי שחור, אפור ואדום Hearts](https://www.foxhome.co.il/products/0168359900) — ₪90, במבצע ₪63
- IKEA: [HASSJÖN טבעת לוילון מקלחת](https://www.ikea.com/il/he/p/hassjoen-shower-curtain-ring-white-00466008/) — ₪7

**ספל / מאג**
- Home Center: [שישיית כוסות שופ 200 מל חלקות](https://www.homecenter.co.il/products/1766496748265) — ₪15
- Fox Home: [מאג מקרמיקה לשתייה חמה 350 מ"ל Mika](https://www.foxhome.co.il/products/0334376361) — ₪20, במבצע ₪14
- IKEA: [DUKTIG סט צעצועים, ספל וצלוחית/8 חל'](https://www.ikea.com/il/he/p/duktig-8-piece-cup-saucer-playset-mixed-colours-10490244/) — ₪49
- Home Center: [מאג אספרסו גיגון 65 מל](https://www.homecenter.co.il/products/1716208559790) — ₪4
- Home Center: [כיסוי אקספלור לגריל ביסטרו](https://www.homecenter.co.il/products/1112080095) — ₪100

**מגש דקורטיבי**
- Home Center: [מגש אקרילי 31/13/4 סמ ANNA](https://www.homecenter.co.il/products/1741874579385) — ₪40
- Fox Home: [מגש הגשה ממתכת בגוון ורוד Romy](https://www.foxhome.co.il/products/0336223939) — ₪130, במבצע ₪91
- Terminal X: [מארז דיספנסר, כוס ומגש שיש S - לבן (STUDIO MARMO)](https://www.terminalx.com/catalogsearch/result?q=%D7%93%D7%99%D7%A1%D7%A4%D7%A0%D7%A1%D7%A8) — ₪347
- Home Center: [מגש אובלי עמוק קטן WIN](https://www.homecenter.co.il/products/1756730854650) — ₪3
- Home Center: [פוף הדום מרובע 68*68 מבד חוץ עם מגש לבחירה צבע שמנת בחירת מגש שיש אוניקס](https://www.homecenter.co.il/products/1745870435955) — ₪399

**עציץ / כיסוי לעציץ**
- Home Center: [עציץ נשפכים דגם הולנד](https://www.homecenter.co.il/products/1755161967867) — ₪35
- Fox Home: [עציץ נוי דקורטיבי צבעוני Troy](https://www.foxhome.co.il/products/0336419900) — ₪60, במבצע ₪42
- Terminal X: [קלתאה אינסיגניס M בעציץ קופנהגן לבן וזמיה קוקוס M סלסלת לאגוס (PLANT IT)](https://www.terminalx.com/catalogsearch/result?q=%D7%A1%D7%9C%D7%A1%D7%9C%D7%94) (M) — ₪312
- Home Center: [תחתית לאדנית מרובעת](https://www.homecenter.co.il/products/1011408434) — ₪8
- Home Center: [זוג בתי עציץ צבע אבן MoonRiver 59X59X50 39X39X33](https://www.homecenter.co.il/products/1780322422360) — ₪1,600, במבצע ₪1,360

**גוף תאורה צמוד תקרה**
- Home Center: [צמוד תקרה צבע עץ קוטר 50 ס"מ ORA CCT 50W](https://www.homecenter.co.il/products/1752753358946) — ₪180, במבצע ₪126
- ACE: [צמוד תקרה דגם יאכטה אור חם](https://www.ace.co.il/7667563) — ₪300
- Home Center: [גוף תאורה צמוד תקרה IP40 20 W ATLAS קוטר 25 ס"מ CCT לבן](https://www.homecenter.co.il/products/1780226712569) — ₪60, במבצע ₪48
- Home Center: [גוף תאורה צמוד תקרה לבן JULIA 120W 100CM 3CCT](https://www.homecenter.co.il/products/1741178273653) — ₪850, במבצע ₪680

**ציפיות לכרית שינה (זוג)**
- IKEA: [STRANDLUMMER ציפה וציפית](https://www.ikea.com/il/he/p/strandlummer-duvet-cover-and-pillowcase-multicolour-floral-pattern-10599017/) (‎150x200/50x70 ס"מ‏) — ₪95
- Fox Home: [ציפית סאטן בהדפס פרחוני עשיר Tamarin](https://www.foxhome.co.il/products/0331529900) — ₪80, במבצע ₪56
- Home Style: [קולקציית MIX & MATCH של Benetton - זוג ציפיות - לבן](https://www.homestyle.co.il/products/3185-101) (2X50/70 סמ זוג ציפיות) — ₪99, במבצע ₪59
- Terminal X: [AURA 50*70 ציפית (FOX HOME)](https://www.terminalx.com/catalogsearch/result?q=%D7%A6%D7%99%D7%A4%D7%94+%D7%9C%D7%9B%D7%A8%D7%99%D7%AA) — ₪90, במבצע ₪63
- Home Center: [זוג ציפיות 50/70 ס"מ גרסי 100% כותנה אפור כהה MOON](https://www.homecenter.co.il/products/1707832882590) — ₪30
- Home Center: [ציפית לכרית רביצה 80*80 100% כותנה](https://www.homecenter.co.il/products/5150216689) — ₪20
- Terminal X: [ציפית 220X200 Royal (FOX HOME)](https://www.terminalx.com/catalogsearch/result?q=%D7%A6%D7%99%D7%A4%D7%94+%D7%9C%D7%9B%D7%A8%D7%99%D7%AA) — ₪560, במבצע ₪392

**כרית ישיבה / לספסל**
- Home Center: [כרית מושב 40/40 סמ חלקה גל קפה](https://www.homecenter.co.il/products/1771400261427) — ₪40
- Fox Home: [כרית מושב מרובעת River](https://www.foxhome.co.il/products/0335322400) — ₪70, במבצע ₪49
- Home Style: [כרית מושב, דגם קשת - קפה](https://www.homestyle.co.il/products/2209-217) (40/40 סמ כרית מושב) — ₪69, במבצע ₪34
- Terminal X: [כרית מושב 40R MARRY (FOX HOME)](https://www.terminalx.com/catalogsearch/result?q=%D7%9B%D7%A8%D7%99%D7%AA+%D7%A0%D7%95%D7%99) (OS OS) — ₪70, במבצע ₪28
- Home Style: [כרית מושב מודפסת, דגם טום - חרדל](https://www.homestyle.co.il/products/1666-214) (40/40 סמ כרית מושב) — ₪19
- Fox Home: [כרית מושב ארוכה ומרופדת בגוון בז' River](https://www.foxhome.co.il/products/0335336000) — ₪130, במבצע ₪91

> קישורי Terminal X מובילים לדף החיפוש באתר. המחיר נלקח מנתוני המוצר שבאותו דף.

## 2. תמחור שממיר: מה אומרות הראיות

### 2.1 נקודות מחיר פסיכולוגיות

| ממצא | מקור |
| --- | --- |
| **אפקט הספרה השמאלית:** מחיר שמסתיים ב-9 נתפס כזול משמעותית רק כשהספרה השמאלית יורדת (₪149 מול ₪150 כן; ₪147 מול ₪148 לא) | Thomas & Morwitz, *Penny Wise and Pound Foolish*, Journal of Consumer Research, 2005 (מצוטט דרך [kolenda.io](https://kolenda.io/tactics/charm-prices) ו-[Entrepreneur](https://entm.ag/29UcdRF)); מטא-אנליזה Troll et al., 2023, Journal of Consumer Psychology. **לא קראתי את המאמרים עצמם** |
| ניסוי שדה מפורסם: שמלה מכרה 21 יחידות ב-$39, לעומת 16 ב-$34 ו-17 ב-$44 | [WARC](https://cdn.warc.com/newsandopinion/opinion/nine-thats-a-magic-number/2050). מדגם קטן; המקור המקורי לא אותר. **המחשה בלבד** |
| טענות כמו "עלייה של 8–24% בהמרה" | בלוגים בלי מקור ([monetizely](https://www.getmonetizely.com/articles/why-does-99-work-better-than-100-the-psychology-behind-charm-pricing-in-saas)). **לא אומת, לא להסתמך** |
| **השוק הישראלי (מדידה שלנו, 2026-10-09):** Fox Home: 93% מהמחירים בסיומת 9 (בעיקר X9.90). Home Style: 91% (מספרים שלמים: ₪99, ₪139, ₪199, ₪499). Home Center: 62%. IKEA: 62% בסיומת 5 (₪95, ₪145, ₪195) ו-31% בסיומת 9 | ניתוח הקטלוגים שבסעיף 1 |
| **הספים שבהם השוק מתקבץ** (פריטי ביניים מסווגים): עד ₪99 — 846 פריטים; ₪100–149 — 300; ₪150–199 — 199; ₪200–249 — 93; ₪250–299 — 108; ₪300–399 — 119 | שם |

**המלצה:** ספים: **₪99 / ₪149 / ₪199 / ₪249 / ₪299 / ₪349**. מחיר שלם בסיומת 9, בלי אגורות. לא לקבוע מחיר ₪5–10 מעל סף (₪155, ₪205): עדיף לרדת לסף או לעלות לסף הבא עם ערך מוסף (סט של 2, מידה גדולה).

### 2.2 סף למשלוח חינם

| ממצא | מקור |
| --- | --- |
| נורמה בישראל: משלוח ₪15–30, חינם מעל ₪199–349 (Terminal X ו-Fox Home ₪249, Golf ₪349, H&M ו-Zara ₪199) | `fulfillment-research.md` §3.1 (נבדק 2026-10-09) |
| כלל אצבע: סף 15–30% מעל הסל הממוצע. מקורו בממוצעי פלטפורמות ולא במחקר מבוקר | [Branvas](https://branvas.com/blogs/news/free-shipping-threshold-by-category); [GrowthSuite](https://www.growthsuite.net/blog/free-shipping-thresholds-increase-aov) |
| ניסוי A/B יחיד שנמצא: העלאת הסף הביאה כ-6% עלייה בסל הממוצע וכ-12% בהכנסה למבקר, בלי פגיעה בהמרה | [Intelligems](https://www.intelligems.io/resources/customer-stories/boost-aov-by-upping-your-free-shipping-threshold) (חקר מקרה של ספק) |
| סף חציוני ברשתות בארה"ב: $64; בקטגוריית בית: כ-$45 | ParcelLab, דרך [Branvas](https://branvas.com/blogs/news/free-shipping-threshold-by-category). **לא אומת במקור** |

**המלצה:** **משלוח חינם מ-₪299. מתחת לסף: ₪29** (המחירים כבר כוללים את עלות CJ, ולכן דמי המשלוח הם תוספת רווח, לא כיסוי עלות. החישוב בסעיף 3 לא כולל אותם, ולכן הוא שמרני). ₪299 הוא שני פריטי ליבה (כיסוי ספה; או ציפה + ראנר + קישוט). אחרי חודש לבדוק את התפלגות הסלים ולהריץ A/B מול ₪249.

### 2.3 סלים ו"שופ דה לוק"

| ממצא | מקור |
| --- | --- |
| ווידג'טים של "נקנים יחד" מעלים את מספר הפריטים בהזמנה ב-5–30% | [Personyze](https://www.personyze.com/?p=36284) (טענת ספק) |
| מספרים כמו "55% עלייה בסל" או "עד 35% (Forrester)" חוזרים בבלוגים בלי מתודולוגיה | [Fastlane](https://ecommercefastlane.com/how-shopify-bundles-drive-aov-increases/); [Digital Commerce 360, 08.09.2026](https://www.digitalcommerce360.com/2026/09/08/product-bundling-how-online-retailers-grow-order-values-without-growing-acquisition-costs/). **לא אומת** |
| CJ: כל חבילה שנחסכת בהזמנה משולבת חוסכת **$3.72** (עמלה קבועה לחבילה). חיסכון של 19–24% בקו הזול. מנורה בסל מעבירה את כל ההזמנה לקו Sensitive | `freight-cj.md`, בדיקת סלים |

**דוגמה מחושבת** (שער 3.7, משלוח משולב = סכום המשלוחים פחות $3.72 לכל חבילה שנחסכת):

| סל | מחיר מלא | הנחת סל | מחיר | עלות נחיתה | מרווח | תרומה אחרי CAC ₪40 |
| --- | --- | --- | --- | --- | --- | --- |
| כיסוי ספה וופל + 2 ציפות (`sofa-cover-cj-waffle-jacquard-stretch-slipcover`, `cushions-cj-linen-look-ivory`, `cushions-cj-knitted-chenille-bean-green`) | ₪547 | 10% | ₪492 | ₪182 | 49% | ₪163 |
| אותו סל + ראנר (`table-runner-cj-linen-look-sage-fringe`) | ₪676 | 10% | ₪608 | ₪209 | 52% | ₪227 |
| לעומת: ציפה אחת לבד ב-₪99 | ₪99 | — | ₪99 | ₪28 | 58% | **₪6** |

**המלצה:** בכל חדר סל "הלוק המלא" של 3–5 פריטים, ב-10% הנחה (לא יותר מ-15%). הסל בנוי מפריטי טקסטיל רווחיים, ואפשר להוסיף לו פריט אחד "לא כדאי" (אגרטל, פמוט) כפריט עוגן ויזואלי, כי הרווח של שאר הסל מממן אותו. לא לשים מנורה בסל עם טקסטיל, כי היא מעבירה את כל ההזמנה לקו יקר.

### 2.4 מחיר "לפני" (compare-at) לפי הדין בישראל

| כלל | מקור |
| --- | --- |
| במכירה מיוחדת (מבצע) העוסק חייב לציין אילו מוצרים כלולים, את **המחיר שהיה בתוקף לפני המבצע**, ואת המחיר אחרי ההנחה או שיעורה, ואת תנאי המבצע | חוק הגנת הצרכן, הוראות "מכירה מיוחדת"; [ice](https://www.ice.co.il/consumerism/news/article/873142); [וואלה](https://finance.walla.co.il/item/1125492) |
| לא מספיק לציין מחיר רגיל ואחוז הנחה. **חובה להציג את המחיר אחרי ההנחה** לכל מוצר (פסק דין נגד ניו-פארם והמשביר) | [כלכליסט](https://www.calcalist.co.il/articles/0,7340,L-3762515,00.html) |
| "מחיר לפני" שלא נגבה בפועל = **הטעיה**. היו הרשעות פליליות על שילוט מבצע בלי הנחה אמיתית | [ice](https://www.ice.co.il/consumerism/news/article/873142) |
| המחיר המוצג לצרכן חייב להיות **המחיר הכולל, כולל מע"מ**, בשקלים. הרשות אוכפת גם באתרים (סעיפים 17ב, 17ד) | [ice](https://www.ice.co.il/finance/news/article/1039938); [ice](https://www.ice.co.il/law/news/article/867381) |
| החוק לא קובע כמה זמן מבצע יכול להימשך, או מהו "המחיר הקודם". הצעות חוק (מבצע רק 30 יום אחרי עלייה למדף, ועד 45 יום בשנה) **לא נמצא שאושרו** | [כלכליסט](https://www.calcalist.co.il/articles/0,7340,L-3740118,00.html); [הצעת חוק בכנסת](https://fs.knesset.gov.il/25/law/25_lst_2110750.pdf). **לא אומת** אם יש תיקון בתוקף |
| הנחיית הממונה מ-2013, שלפיה אחרי 35 יום מחיר המבצע הופך למחיר הרגיל | הוזכרה בתוצאת חיפוש בלבד. **לא אומת** |

**המלצה (לא ייעוץ משפטי, לאשר מול עו"ד):**
- בהשקה: **מחיר אחד, בלי "מחיר לפני"**. לאתר חדש אין מחיר שנגבה בפועל.
- מבצע עתידי: "מחיר לפני" רק אם המוצר נמכר באתר באותו מחיר לפחות 30 יום רצופים לפני המבצע (כלל זהיר, שתואם את הצעות החוק ואת ההנחיה האירופית). להציג את מחיר המבצע עצמו ואת תנאיו ותאריכיו, ולא להחזיק מבצע יותר מכ-35–45 יום.
- לא להשתמש ב"מחיר מחירון" או ב"שווי" שאינו מחיר אמיתי שלנו (למשל המחיר של Zara Home).
- המחיר בכל מקום באתר כולל מע"מ.

### 2.5 שיעור המרה צפוי

| מקור | עיצוב הבית / ריהוט | כלל המסחר המקוון |
| --- | --- | --- |
| [Firework 2026](https://firework.com/blog/home-decor-ecommerce-statistics-2026-market-size-trends-and-what-drives-conversion) | 1.4% (השני הנמוך ביותר, אחרי מוצרי יוקרה) | — |
| [Skailama 2026](https://skailama.com/blog/ecommerce-conversion-rate-by-industry) | 1.0–1.4%, טיפוסי 1.3% | 1.81–2.9% |
| [OptiMonk 2026](https://www.optimonk.com/industry-conversion-rate-benchmarks) | 1.24–1.9% | חנויות Shopify 2.5–3%; העשירון העליון 3.5–5% |
| [ATTN Agency 2026](https://www.attnagency.com/blog/ecommerce-conversion-rate-benchmarks-2026) | אקססוריז 2.8%, ריהוט 1.6% (חריג) | — |

**לתכנון:** 1.3–1.9%. אקססוריז זולים (מתחת ל-₪150) ממירים יותר מרהיטים. כל המקורות הם בלוגים של ספקים, לא נתונים מבוקרים. אתר עם זמן אספקה של 12–50 יום כנראה ימיר בחלק התחתון של הטווח, עד שיהיה מלאי מקומי או קו מהיר.

## 3. רצועת מחיר מומלצת וכדאיות

**איך חושב:** עלות נחיתה = (עלות CJ + משלוח זול מ-`freight-cj.json`) × 3.7. מרווח = (הכנסה נטו − עלות נחיתה − סליקה 2% + ₪1.2 − שמורת החזרות 5%) ÷ הכנסה נטו; הכנסה נטו = מחיר ÷ 1.18. אותה נוסחה כמו בסטודיו (`econCalc`). בלי CAC; CAC מופיע בנפרד. ליחידה אחת.

- **רצועה:** מ-75% מהחציון ועד החציון, מעוגל מטה לנקודת מחיר בסיומת 9. מוצר שעובר 35% מתחילת הרצועה מקבל את כולה; אחרת הרצועה שלו מתחילה במחיר שנותן 35%.
- **פסק דין:** כדאי = מרווח ≥35% במחיר העליון של הרצועה. רק בסל = פחות מ-35% לבד, אבל לפחות 25% בסל של 3 (חיסכון $2.48 משלוח לפריט) ורווח חיובי אחרי CAC ÷ 3. לא כדאי מ-CJ = אחרת.
- **פרימיום מעל החציון:** מוסבר רק כשהמוצר באמת ברמה גבוהה (פשתן אמיתי, טרוורטין). התקרה היא אחוזון 75 של השוק הבינוני (עמודה P75).

| קטגוריה | חציון שוק | **רצועה מומלצת** | P75 (תקרת פרימיום) | עלות נחיתה שלנו (חציון) | מחיר ל-35% (חציון) | מרווח במחיר העליון (חציון) | פסק דין | מוצרים: כדאי / סל / לא |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ציפה לכרית נוי | ₪100 | **₪69–₪99** | ₪140 | ₪30 | ₪63 | 56% | כדאי | 10 / 2 / 0 |
| שמיכת סלון / פלייד | ₪120 | **₪89–₪119** | ₪195 | ₪103 | ₪214 | -11% | לא כדאי מ-CJ | 0 / 0 / 6 |
| כיסוי לספה | ₪372 | **₪279–₪349** | ₪601 | ₪133 | ₪274 | 47% | כדאי | 4 / 1 / 0 |
| וילונות בד, זוג | ₪185 | **₪129–₪179** | ₪345 | ₪127 | ₪263 | 8% | לא כדאי מ-CJ | 0 / 1 / 1 |
| שטיח קטן (עד 1.5 מ"ר, למשל 60x90–80x150) | ₪129 | **₪89–₪129** | ₪178 | — | — | — | אין מוצר בקטלוג | — |
| שטיח בינוני (1.5–3.2 מ"ר, למשל 120x170–160x200) | ₪345 | **₪249–₪329** | ₪469 | — | — | — | אין מוצר בקטלוג | — |
| שטיח גדול (מעל 3.2 מ"ר, למשל 160x230 ומעלה) | ₪895 | **₪649–₪799** | ₪1,250 | ₪2,807 | ₪5,749 | -322% | לא כדאי מ-CJ | 0 / 0 / 1 |
| אגרטל קטן (עד 25 ס"מ) | ₪42 | **₪29–₪39** | ₪69 | ₪78 | ₪162 | -147% | לא כדאי מ-CJ | 0 / 0 / 4 |
| אגרטל גדול (מעל 25 ס"מ) | ₪327 | **₪229–₪299** | ₪476 | ₪184 | ₪379 | 20% | לא כדאי מ-CJ | 1 / 3 / 5 |
| קערה קרמית / קערת הגשה | ₪49 | **₪29–₪49** | ₪90 | ₪66 | ₪137 | -69% | לא כדאי מ-CJ | 0 / 0 / 5 |
| פמוט / מעמד לנר | ₪89 | **₪59–₪89** | ₪129 | ₪93 | ₪193 | -32% | לא כדאי מ-CJ | 0 / 0 / 2 |
| מנורת שולחן | ₪192 | **₪139–₪179** | ₪230 | ₪194 | ₪400 | -36% | לא כדאי מ-CJ | 0 / 0 / 3 |
| מנורה עומדת | ₪225 | **₪149–₪219** | ₪295 | ₪174 | ₪359 | -2% | לא כדאי מ-CJ | 0 / 0 / 3 |
| מנורת קיר | ₪125 | **₪89–₪119** | ₪150 | ₪162 | ₪334 | -69% | לא כדאי מ-CJ | 2 / 1 / 15 |
| מנורת תלייה | ₪195 | **₪139–₪179** | ₪245 | ₪221 | ₪455 | -54% | לא כדאי מ-CJ | 0 / 0 / 9 |
| תמונה ממוסגרת / הדפס | ₪225 | **₪149–₪219** | ₪450 | ₪149 | ₪307 | 12% | לא כדאי מ-CJ | 2 / 0 / 5 |
| קישוט קיר / מקרמה / מראה דקורטיבית | ₪175 | **₪129–₪169** | ₪345 | ₪79 | ₪165 | 36% | כדאי | 2 / 2 / 0 |
| סלסלה קלועה | ₪69 | **₪49–₪69** | ₪95 | ₪77 | ₪160 | -41% | לא כדאי מ-CJ | 0 / 3 / 6 |
| פוף / הדום | ₪495 | **₪349–₪449** | ₪822 | ₪143 | ₪295 | 55% | כדאי | 1 / 0 / 0 |
| ראנר לשולחן | ₪130 | **₪89–₪129** | ₪155 | ₪37 | ₪79 | 58% | כדאי | 3 / 0 / 0 |
| סט מצעים (ציפה + ציפיות, זוגי) | ₪489 | **₪349–₪449** | ₪699 | ₪290 | ₪596 | 16% | לא כדאי מ-CJ | 2 / 1 / 3 |
| ציפה לשמיכה | ₪370 | **₪269–₪349** | ₪440 | ₪117 | ₪241 | 53% | כדאי | 1 / 0 / 0 |
| מגבת רחצה (גוף) | ₪129 | **₪89–₪129** | ₪157 | ₪56 | ₪116 | 40% | כדאי | 2 / 0 / 0 |
| אביזרי אמבטיה (דיספנסר / כוס) | ₪60 | **₪39–₪59** | ₪117 | ₪59 | ₪123 | -27% | לא כדאי מ-CJ | 0 / 0 / 5 |
| צנצנות / אחסוניות מטבח | ₪50 | **₪29–₪49** | ₪80 | — | — | — | אין מוצר בקטלוג | — |
| מלחייה / פלפלייה / מטחנות | ₪60 | **₪39–₪59** | ₪110 | ₪79 | ₪165 | -68% | לא כדאי מ-CJ | 0 / 0 / 1 |
| קישוט לחדר ילדים | ₪90 | **₪59–₪89** | ₪90 | ₪72 | ₪150 | -5% | לא כדאי מ-CJ | 0 / 0 / 1 |
| צעצוע (עץ / רך) | ₪49 | **₪29–₪49** | ₪95 | ₪33 | ₪70 | 10% | רק בסל | 0 / 1 / 0 |
| ***נוספות*** | | | | | | | | |
| שטיח אמבטיה | ₪100 | **₪69–₪99** | ₪100 | ₪204 | ₪422 | -153% | לא כדאי מ-CJ | 0 / 1 / 1 |
| וילון מקלחת/אמבטיה | ₪90 | **₪59–₪89** | ₪129 | ₪64 | ₪132 | 7% | לא כדאי מ-CJ | 0 / 0 / 1 |
| ספל / מאג | ₪20 | **₪19–₪19** | ₪25 | ₪56 | ₪116 | -261% | לא כדאי מ-CJ | 0 / 0 / 2 |
| מגש דקורטיבי | ₪130 | **₪89–₪129** | ₪150 | ₪120 | ₪248 | -18% | לא כדאי מ-CJ | 0 / 0 / 2 |
| עציץ / כיסוי לעציץ | ₪35 | **₪19–₪29** | ₪59 | ₪127 | ₪262 | -428% | לא כדאי מ-CJ | 0 / 0 / 2 |
| גוף תאורה צמוד תקרה | ₪180 | **₪129–₪179** | ₪300 | ₪246 | ₪505 | -70% | לא כדאי מ-CJ | 0 / 0 / 3 |
| ציפיות לכרית שינה (זוג) | ₪95 | **₪69–₪89** | ₪125 | ₪85 | ₪177 | -22% | לא כדאי מ-CJ | 0 / 0 / 2 |
| כרית ישיבה / לספסל | ₪70 | **₪49–₪69** | ₪70 | ₪114 | ₪236 | -104% | לא כדאי מ-CJ | 0 / 0 / 1 |

**מה עולה מהטבלה:**
- **כדאי (לפי חציון הקטגוריה):** ציפות לכריות, כיסוי לספה, ראנר, ציפה לשמיכה, מגבות, קישוט קיר. כאן אפשר לתמחר בחציון השוק או מתחתיו.
- **פוף:** יוצא "כדאי", אבל ההשוואה היא להדומים מרופדים (₪262–850), ואצלנו זה כיסוי סרוג בלבד. רק אם מוכרים אותו עם מילוי. ככיסוי לבד, המחיר צריך להיות נמוך בהרבה, ולכן המספר הזה לא אמין.
- **מוצרים בודדים כדאיים בקטגוריה שאינה כדאית:** סטים של מצעים לילדים (`bedding-cj-washed-polyester-set-milk-tea`, `bedding-cj-cream-ruffle-rosebud-set`), תמונות (`framed-prints-cj-flower-cutout-set-30x40`, `gallery-art-cj-black-botanical-cutout-set3`), אגרטל גדול אחד (`vase-cj-textured-white-stoneware`), ושתי מנורות אמבטיה קטנות (`vanity-sconces-cj-flat-halo-disc-white`, `vanity-sconces-cj-ip65-mini-updown-white`). ראו טבלת המוצרים.
- **שמיכות (throw):** לא כדאי מ-CJ. השוק זול (IKEA ₪49–145, Fox ₪90–200), והמשלוח של שמיכת כותנה כבד. חציון עלות הנחיתה שלנו ₪103, מול חציון שוק ₪120.
- **תאורה, קרמיקה וכלי שולחן:** לא כדאי. כדי להגיע ל-35% צריך מחיר של פי 2–3 מהחציון (מנורת שולחן: ₪400 מול ₪192; קערה: ₪137 מול ₪49).
- **שטיחים:** אין בקטלוג שטיח קטן או בינוני. שטיח הצמר הקלוע נוחת ב-₪2,807, וזה לא כדאי בשום מחיר.
- **בשער 3.0** (השער האמיתי ב-2026) המרווחים עולים ב-6–27 נקודות אחוז (חציון 14). 11 מוצרים "רק בסל" הופכים לכדאיים, ביניהם 3 אגרטלים. אף מוצר "לא כדאי" לא הופך לכדאי, ותאורה וקרמיקה נשארות לא כדאיות. השדה `margin_at_band_fx3` ב-JSON.

### 15 המוצרים עם המרווח הגבוה ביותר במחיר תחרותי

מדורג לפי המרווח במחיר העליון של הרצועה (≤ חציון השוק).

| מוצר | קטגוריה | רצועה | עלות נחיתה | מרווח במחיר העליון | בשער 3.0 | מחיר ל-35% | פסק דין | הערות |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `cushions-cj-chenille-wide-wale-green` | ציפה לכרית נוי | ₪69–₪99 | ₪26 | **60%** | 66% | ₪56 | כדאי | benchmark-mostly-filled-cushions |
| `bedding-cj-washed-polyester-set-milk-tea` | סט מצעים (ציפה + ציפיות, זוגי) | ₪349–₪449 | ₪126 | **59%** | 66% | ₪259 | כדאי | benchmark-mostly-double-size |
| `cushions-cj-washed-cotton-frayed` | ציפה לכרית נוי | ₪69–₪99 | ₪28 | **58%** | 65% | ₪59 | כדאי | benchmark-mostly-filled-cushions |
| `pool-cj-woven-cotton-runner-fringe` | ראנר לשולחן | ₪89–₪129 | ₪37 | **58%** | 64% | ₪78 | כדאי |  |
| `cushions-cj-knitted-chenille-bean-green` | ציפה לכרית נוי | ₪69–₪99 | ₪28 | **58%** | 64% | ₪60 | כדאי | benchmark-mostly-filled-cushions |
| `sofa-cover-cj-knit-thick-slipcover` | כיסוי לספה | ₪279–₪349 | ₪103 | **58%** | 64% | ₪212 | כדאי |  |
| `table-runner-cj-linen-look-triangle-end` | ראנר לשולחן | ₪89–₪129 | ₪37 | **58%** | 64% | ₪79 | כדאי |  |
| `cushions-cj-wide-stripe-corduroy-light-green` | ציפה לכרית נוי | ₪69–₪99 | ₪28 | **57%** | 64% | ₪61 | כדאי | benchmark-mostly-filled-cushions |
| `cushions-cj-wide-wale-corduroy` | ציפה לכרית נוי | ₪69–₪99 | ₪28 | **57%** | 64% | ₪61 | כדאי | benchmark-mostly-filled-cushions |
| `cushions-cj-corduroy-patchwork` | ציפה לכרית נוי | ₪69–₪99 | ₪29 | **57%** | 64% | ₪61 | כדאי | benchmark-mostly-filled-cushions |
| `pouf-cj-cotton-knit-ball-cover` | פוף / הדום | ₪349–₪449 | ₪143 | **55%** | 62% | ₪295 | כדאי | benchmark-is-upholstered-ottoman |
| `cushions-cj-linen-look-charcoal` | ציפה לכרית נוי | ₪69–₪99 | ₪31 | **55%** | 62% | ₪65 | כדאי | benchmark-mostly-filled-cushions |
| `table-runner-cj-linen-look-sage-fringe` | ראנר לשולחן | ₪89–₪129 | ₪41 | **54%** | 61% | ₪86 | כדאי |  |
| `sofa-cover-cj-linen-feel-chenille-slipcover` | כיסוי לספה | ₪279–₪349 | ₪115 | **53%** | 61% | ₪238 | כדאי |  |
| `bedding-cj-muslin-cotton-duvet-dune` | ציפה לשמיכה | ₪269–₪349 | ₪117 | **53%** | 60% | ₪241 | כדאי |  |

### 15 המוצרים עם המרווח הנמוך ביותר

במחיר תחרותי כל אחד מאלה מפסיד כסף בכל מכירה. "מחיר ל-35%" מראה כמה היה צריך לגבות.

| מוצר | קטגוריה | רצועה | עלות נחיתה | מרווח במחיר העליון | בשער 3.0 | מחיר ל-35% | פסק דין | הערות |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `planter-cj-cement-ribbed-belly` | עציץ / כיסוי לעציץ | ₪29–₪29 | ₪177 | **-631%** | -495% | ₪364 | לא כדאי מ-CJ |  |
| `wall-sconce-cj-black-swing-arm-fabric` | מנורת קיר | ₪119–₪119 | ₪440 | **-344%** | -262% | ₪902 | לא כדאי מ-CJ |  |
| `mug-set-cj-oat-speckled-round-mug-wood-saucer` | ספל / מאג | ₪19–₪19 | ₪68 | **-335%** | -256% | ₪141 | לא כדאי מ-CJ |  |
| `bath-mat-cj-solid-wood-slatted-61x45` | שטיח אמבטיה | ₪99–₪99 | ₪350 | **-326%** | -247% | ₪719 | לא כדאי מ-CJ |  |
| `rug-cj-braided-wool-natural` | שטיח גדול (מעל 3.2 מ"ר, למשל 160x230 ומעלה) | ₪799–₪799 | ₪2,807 | **-322%** | -244% | ₪5,749 | לא כדאי מ-CJ |  |
| `vase-cj-matte-moon-jar-white` | אגרטל קטן (עד 25 ס"מ) | ₪39–₪39 | ₪133 | **-314%** | -238% | ₪275 | לא כדאי מ-CJ |  |
| `magazine-holder-cj-gunmetal-leather-strap` | סלסלה קלועה | ₪69–₪69 | ₪224 | **-293%** | -221% | ₪462 | לא כדאי מ-CJ |  |
| `wall-sconce-cj-travertine-dome-15-pull` | מנורת קיר | ₪119–₪119 | ₪373 | **-279%** | -209% | ₪766 | לא כדאי מ-CJ |  |
| `wall-sconce-cj-black-swing-arm-wood-shade` | מנורת קיר | ₪119–₪119 | ₪361 | **-266%** | -199% | ₪741 | לא כדאי מ-CJ |  |
| `pool-cj-terracotta-amphora-floor-51` | אגרטל גדול (מעל 25 ס"מ) | ₪299–₪299 | ₪814 | **-229%** | -168% | ₪1,669 | לא כדאי מ-CJ |  |
| `planter-cj-seagrass-belly` | עציץ / כיסוי לעציץ | ₪29–₪29 | ₪77 | **-225%** | -166% | ₪160 | לא כדאי מ-CJ |  |
| `framed-art-cj-morandi-triptych-sage` | תמונה ממוסגרת / הדפס | ₪219–₪219 | ₪542 | **-200%** | -145% | ₪1,113 | לא כדאי מ-CJ |  |
| `mug-set-cj-cream-matte-breakfast-cup` | ספל / מאג | ₪19–₪19 | ₪44 | **-186%** | -135% | ₪92 | לא כדאי מ-CJ |  |
| `wall-sconce-cj-travertine-disc-25` | מנורת קיר | ₪119–₪119 | ₪273 | **-180%** | -128% | ₪562 | לא כדאי מ-CJ |  |
| `centerpiece-vase-cj-sandy-white-bead-band-25` | אגרטל קטן (עד 25 ס"מ) | ₪39–₪39 | ₪86 | **-171%** | -122% | ₪178 | לא כדאי מ-CJ | shipping-estimated |

**סה"כ 135 מוצרים שלא נדחו:** 30 כדאי, 16 רק בסל, 89 לא כדאי מ-CJ. הפירוט המלא לכל מוצר ב-`market-prices.json` (`products`).

**דגלים:** `shipping-estimated` = אין למוצר נתון ב-`freight-cj.json`, ולכן הוצב חציון המשלוח של הקטגוריה. `viable-as-premium-up-to-P75` = לא עובר 35% במחיר החציון, אבל עובר אותו במחיר שעדיין מתחת לאחוזון 75 של השוק, כלומר אפשרי רק כמוצר פרימיום.

## הערות ומגבלות

- **השער:** 3.7 לפי ברירת המחדל של הסטודיו. **צריך לעדכן**, השער ב-2026 קרוב ל-3.0.
- **כמות:** הכל ליחידה אחת לפי עלות הכרטיס. מוצרים שנמכרים כזוג או כסט (מנורות קיר ליד המיטה, פמוטי טרוורטין, ספלים) יקבלו בסטודיו `sell_qty` אחר, ואז גם המחיר והמרווח ישתנו.
- **התאמת מידות:** סטים של מצעים לילדים (יחיד) הושוו לשוק שרובו זוגי. ציפית לכרית מושווית לכריות נוי מלאות, כי זה מה שרוב הרשתות מוכרות (ציפה לבד זולה יותר).
- **דמי משלוח מהלקוח** (₪29 מתחת לסף) לא נכללו, וגם לא הכנסה ממע"מ על משלוח. בפועל המרווח על הזמנה קטנה טוב יותר ממה שמוצג.
- **לא אומת:** Zara Home (תקצירי חיפוש בלבד), H&M Home, Golf&Co, Kitan, Story, JYSK. הנחיית 35 הימים. מצב הצעות החוק על מבצעים.
