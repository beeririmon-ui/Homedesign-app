# הצעה: הכלי בסלון המודרני החם, שלב 2 · 2026-11-07

> master-designer.
> **הבסיס:** אישור 3 (AP3-WM, הבעלים, 2026-11-07). שלב 1 סופי: מעטפת v3c, הרהיטים הקבועים, ושלושה סטי כריות כשכבות. ברירת המחדל בכלי היא סט B (CAM1).
> **הקלט:**
> - הבחירה המאושרת: `data/selections/living-room.warm-modern.json`;
> - העמדות: `data/slots/living-room.json` 1.9.3 (‏`by_style.warm-modern`);
> - תוכנית הבית 1.3.5, פרק 0א;
> - תוכנית הפיילוט: `docs/proposals/warm-modern-living-room-slots-2026-11-07.md` §2.
>
> **מחירי היחידה** (כמו בפיילוט, ‏render-agent מאשר ב-`var2_estimate_cost` לפני כל שלב, ועוצר בסטייה מעל 10%):
> - seedream-5-pro i2i 2K: ‏650 למעבר;
> - kling-3 pro, ‏5 שניות: ‏1,620 לסרטון;
> - clay, מפת עומק, שכבות צל ואור, חילוץ במסכה ו-swap-diff: ‏0, בקוד.
>
> **הצעה בלבד.** שום הוצאה לפני תשובת הבעלים.

## 1. מה נשאר בפריים M0
**12 עמדות עם מוצרים, 25 וריאציות.** הכריות כבר בשלב 1.

| עמדה | הווריאציות (הראשונה היא ברירת המחדל) | כמה יש | חסר עד 3 |
| --- | --- | --- | --- |
| curtains | `curtains-aliexpress-beige-linen-sheer-curtains-554205`; ‏`curtains-aliexpress-linen-blend-s-fold-180502`; ‏`curtains-cj-japanese-linen-half-shade` | 3 | — (חסר רק ציר צבע כהה, טאופ-פטריה) |
| framed-art | `framed-art-aliexpress-frameless-minimalist-wall-art-631735`; ‏`framed-art-aliexpress-modern-minimalist-neutral-gallery-802995` | 2 | 1 |
| accent-sconces | `accent-sconces-aliexpress-travertine-cylinder-walnut-choice`; ‏`accent-sconces-cj-travertine-block-updown-8x16`; ‏`accent-sconces-cj-ribbed-travertine-half-cylinder-wood-bracket` | 3 | — (שער החשמל CE פתוח בשלושתן) |
| vase | `vase-cj-textured-white-stoneware`; ‏`vase-cj-charcoal-carved`; ‏`vase-cj-white-plum-hand-thrown` | 3 | — |
| rug | `rug-cj-braided-wool-natural` | 1 | 2 (ספק ישראלי, IL1) |
| floor-lamp | `floor-lamp-cj-pleated-walnut-stem-158` | 1 | 2 (WM-FL1: מחכה ל-NL3) |
| planter | `planter-cj-cement-ribbed-belly` | 1 | 2 (מלאי מקומי, LK1) |
| basket | `basket-cj-jute-rope-cylinder` | 1 | 2 |
| magazine-holder | `magazine-holder-cj-gunmetal-leather-strap` (WMC9, ‏(‎−0.47, 2.57)); ‏`magazine-holder-cj-felt-log-basket` | 2 | 1 |
| bowl | `bowl-cj-matte-black-bowl-20`; ‏`bowl-cj-glutinous-white-belly-bowl-21`; ‏`bowl-cj-speckled-ivory-wide-bowl-21` | 3 | — |
| candle-holders | `candle-holders-cj-travertine-pedestal`; ‏`candle-holders-cj-ceramic-pedestal-tray`; ‏`candle-holders-aliexpress-matte-black-iron-pillar-set2` | 3 | — |
| pendant | `pendant-cj-tiered-fabric-drum`; ‏`pendant-cj-pleated-pumpkin-lantern-40` | 2 | 1 (CE פתוח) |

- **ריקות בכוונה (TR3), בלי רינדור:** wall-decor, ‏sofa-cover, ‏table-runner, ‏pouf.
- **מחוץ ל-M0:** wall-sconce נראית רק במעבר.

## 2. איך מרנדרים בזול בלי לאבד נאמנות: מעברים מקובצים
- **הכלל:** במעבר אחד מרנדרים כמה עמדות שלא נוגעות זו בזו ב-M0, ואז מחלצים כל מוצר במסכה לשכבה משלו. כל שכבה עוברת swap-diff (כלל ו.5): אסור שפיקסל מחוץ למוצר ולצל שלו ישתנה.
- **מוצרים שמאירים** (מנורות קיר, תלויה ומנורת רגל) מרונדרים כבויים כמוצר. שכבת האור של כל אחד נבנית בקוד, כמו בנורדי.
- **השטיח מקבל מעבר משלו,** כי הוא מתחת לשכבת הרהיטים הקבועים, וצל המגע של הרהיטים עליו מחושב מחדש.
- **שתי קבוצות שלא נוגעות זו בזו:**
  - **קבוצת החלון והרצפה:** וילון, אגרטל על הספסל, עציץ, סל, מחזיק עיתונים, מנורת רגל.
  - **קבוצת הקיר והשולחן:** הדפסים, מנורות קיר, תלויה, קערה, פמוטים.
  - הסל חופף את העציץ בכוונה, ולכן שניהם תמיד באותו מעבר.
  - הקערה והפמוטים קרובים זה לזה על השולחן, אבל לא חופפים, ויכולים לחלוק מעבר.

## 3. סדר העבודה והעלות
| # | שלב | מה במעבר | סוכן | מודל | טוקנים |
| --- | --- | --- | --- | --- | --- |
| 0 | **clay r4:** ‏WMC9 (מחזיק העיתונים ב-2.57) ו-WMC10 (שיפולים 15, קו הרצפה ב-Z ‏0). צורות-מקום רק לברירות המחדל. בדיקות F3 לכל עמדה | — | render-agent | Blender | 0 |
| 1 | **השטיח** מתחת לרהיטים, וצל המגע מחדש | rug | render-agent | seedream ×1 | 650 |
| 2 | **ברירות המחדל, קבוצת החלון והרצפה** | curtains, vase, planter, basket, magazine-holder, floor-lamp (6) | render-agent | seedream ×1 | 650 |
| 3 | **ברירות המחדל, קבוצת הקיר והשולחן** | framed-art, accent-sconces, pendant, bowl, candle-holders (5) | render-agent | seedream ×1 | 650 |
| — | **נקודת בדיקה:** הסצנה המלאה של ברירות המחדל (עם סט B). QA ‏(G1, נאמנות, swap-diff) ועין של המעצב. אם נכשל, עוצרים לפני שלבים 4–7 | — | qa-agent, ‏master-designer | — | 0 |
| 4 | **וריאציה 2, החלון והרצפה** | curtains 2, vase 2, magazine-holder 2 | render-agent | seedream ×1 | 650 |
| 5 | **וריאציה 2, הקיר והשולחן** | framed-art 2, sconces 2, pendant 2, bowl 2, candle-holders 2 | render-agent | seedream ×1 | 650 |
| 6 | **וריאציה 3, החלון** | curtains 3, vase 3 | render-agent | seedream ×1 | 650 |
| 7 | **וריאציה 3, הקיר והשולחן** | sconces 3, bowl 3, candle-holders 3 | render-agent | seedream ×1 | 650 |
| 8 | **שכבות צל ואור** לכל מוצר, וחילוץ, ו-swap-diff | — | render-agent | קוד | 0 |
| 9 | **שתי פוזות, M0p ו-M0x:** מעטפת v3c, רהיטים קבועים וברירות המחדל, עם נעילת מעטפת מול ה-clay של כל פוזה | — | render-agent | seedream ×2 | 1,300 |
| 10 | **מפת עומק** ל-M0, ‏M0p ו-M0x | — | motion-agent | קוד | 0 |
| 11 | **שני הפאנים בחדר:** P0 (מ-M0 ל-M0p) ו-P1 (מ-M0p ל-M0x), מהפריים הראשון והאחרון | — | motion-agent | kling-3 pro, ‏5 שניות ×2 | 3,240 |
| | **סך הכול לשלבים** | | | | **8,440** |
| | **רזרבה:** שני תיקונים (מעבר אחד לכל היותר לכל קבוצה), רק באישור המנהל | | render-agent | seedream ×2 | 1,300 |
| | **סך הכול עם הרזרבה** | | | | **9,740** |

- **בפוזות** הכלי מציג את ברירות המחדל בלבד. בחירת וריאציות קורית ב-M0, כמו בנורדי.
  - **אם הבעלים רוצה וריאציות גם בפוזות:** כל וריאציה עולה בכל פוזה. זה בערך פי שלושה משלבים 4–7 לכל פוזה, כ-5,200 נוספים לשתיהן. **ההמלצה: לא.**
- **מחוץ לתוכנית:**
  - **המעבר בפריים הסיפור** של CAM1, שמחליף את כרית ה-21 Camel בקורדרוי קאמל, כ-650. זה בשכבת הסיפור ולא בכלי, ורשום אצל render-agent.
  - **מעברי הבית T-E0 ו-T-LD:** דורשים מעטפת מודרנית-חמה לכניסה ולפינת האוכל (שאלה WM-T1), כ-7,140 לפי ההערכה בפיילוט.

## 4. מה מחכה ל-sourcing
- **עמדות עם פחות מ-3 וריאציות:** 7 עמדות, 11 וריאציות חסרות.
  - framed-art: ‏1;
  - rug: ‏2;
  - floor-lamp: ‏2;
  - planter: ‏2;
  - basket: ‏2;
  - magazine-holder: ‏1;
  - pendant: ‏1.
- **מה עושים איתן עכשיו:** מרנדרים את מה שיש, כי ברירות המחדל נדרשות לסצנה השלמה. הן לא נחסמות.
- **מתי מוסיפים:** כל וריאציה חסרה נכנסת כשנמצא מוצר ועובר דירוג.
  - **המחיר:** כ-650 למעבר מקובץ של עד 5 עמדות שלא נוגעות זו בזו.
  - **ל-11 החסרות:** בערך 3–4 מעברים, כ-1,950–2,600, בהצעה נפרדת.
- **מה חוסם את ה-sourcing:**
  - B22 (בלי מפתחות);
  - IL1 ו-LK1 (ספקים מקומיים);
  - WM-FL1 (מנורת הרגל מחכה ל-NL3);
  - CE (מנורות הקיר והתלויה).
- **CE חוסם רק מכירה, לא רינדור:** מרנדרים את מנורות הקיר ואת התלויה, אבל הן לא עולות לחנות בלי אישור CE.

## 5. השאלה לבעלים
- **שלב 2:** 8,440, ועם רזרבה 9,740.
  - **מה כלול:** שאר העמדות בכל הווריאציות שיש, שתי הפוזות ושני הפאנים.
  - **הסדר:** קודם ברירות המחדל, ואחריהן נקודת בדיקה.
- **ההמלצה: לאשר.**
- **render-agent מאשר** את ההערכות לפני כל שלב.
