# כרטיסי הילדים אחרי רישום 1.3.9a, ו-CJ-L2 (general-purpose, ‏2026-11-25)

**הבריף:** `briefs/cards-kids-after-registration-2026-11-25.md`.
**הקלט:**
- פרקים 6–7 של `docs/proposals/wm-registration-1-3-9-kids-2026-11-25.md`;
- `data/slots/kids.json` ‏1.1.0 והסכמה;
- המוסכמות: `briefs/cards-sku-sync-2026-11-19.md` ו-`data/leads/cards-after-reg-1-3-9-2026-11-24.md`;
- ה-manifest של שני חדרי הילדים (`assets/renders/boy|girl/warm-modern/stage1-2026-11-24/manifest.json`);
- ל-CJ-L2: ‏`status/backlog-low.md`, ה-manifest של הרחצה, העבודה והמטבח, ו-`site/tools/tour/*.json`.

**נגעתי רק ב-`data/products/` ובקובץ הזה.** בלי git, בלי רשת ובלי מפתחות.
- כל עותק נבנה בטקסט מהקובץ של המקור. השתנו רק `id`, ‏`room`, ‏`slot`, ‏`rooms`, ‏`placement` ו-`notes`, ולכן `diff` מול המקור מראה רק אותם.
- כל קובץ נבדק ב-`json.loads` מול הערכים המכוונים.
- שם הקובץ זהה ל-id, כי `make-tour-room.ts` מוצא כרטיס לפי שם הקובץ.

**הערה:** המנהל שמר את תיקון ה-placement ב-commit ‏`88a7f58d` ("WIP checkpoint") בזמן העבודה. התיקייה `data/products/living-room/coffee-table/` שהופיעה בזמן הזה לא שלי (ליקוט FB12).

## 1. הבדיקות
| בדיקה | לפני | אחרי |
| --- | --- | --- |
| `python3 scripts/sourcing/options.py validate` | ‏503 כרטיסים עם options, ‏0 לא תקינים, ‏6 אזהרות | ‏**513** (10 עותקים עם options; לתומכי הספרים אין options), ‏**0 לא תקינים**, אותן 6 אזהרות (כרטיסי זוג וסט, קיימות מקודם) |
| ‏vitest המלא (`npx --no-install vitest run` מ-`site/`) | ‏554/555. אדום אחד: `shared.test.ts`, ‏"every product card outside the shared pool parses", חמש שורות `placement` של `kids/under-desk-bin` | ‏**555/555, הכול ירוק** (49/49 קבצים) |
| ‏`json.loads` על כל קובץ שנגעתי בו | — | ‏16/16 תקינים |

## 2. כרטיס-כרטיס (16)
| # | כרטיס | הנתיב (תחת `data/products/`) | מה נעשה | למה |
| --- | --- | --- | --- | --- |
| 1 | `under-desk-bin-aliexpress-enjelwang-arrival-grey-storage-540482` | `kids/under-desk-bin/…540482.json` | ‏`placement`: ‏null ← `floor`. שום דבר אחר | יומן הרישום פרק 6 |
| 2 | `under-desk-bin-aliexpress-felt-basket-laundry-storage-765413` | `kids/under-desk-bin/…765413.json` | ‏`placement`: ‏null ← `floor` | יומן הרישום פרק 6 |
| 3 | `under-desk-bin-aliexpress-felt-storage-basket-foldable-743334` | `kids/under-desk-bin/…743334.json` | ‏`placement`: ‏null ← `floor` | יומן הרישום פרק 6 |
| 4 | `under-desk-bin-aliexpress-minimalist-saddle-leather-storage-966693` | `kids/under-desk-bin/…966693.json` | ‏`placement`: ‏null ← `floor` | יומן הרישום פרק 6 |
| 5 | `under-desk-bin-aliexpress-portable-felt-storage-basket-993764` | `kids/under-desk-bin/…993764.json` | ‏`placement`: ‏null ← `floor` | יומן הרישום פרק 6 |
| 6 | `pen-cup-cj-walnut-beech-square-pen-cup-8x11` | `kids/pen-cup/` | עותק של `desk-organizer-cj-walnut-beech-square-pen-cup-8x11` (`work/desk-organizer`), עם `mirror_of`. ‏`placement` ‏surface. ‏`rooms` ‏kids-boy + kids-girl. ‏`default_sku` ו-`in_room` ‏`CJYD204195901AZ` (אגוז, הילד), כמו במקור. ‏`room_variants: warm-modern.kids-boy=CJYD204195901AZ; warm-modern.kids-girl=CJYD204195902BY` (בוק, אותו מחיר). השורה הזו מחליפה את שורת ה-kids-girl של המקור | יומן פרק 7; ‏manifest: ילד ‏`…-black-walnut`, ילדה ‏`…-beech` |
| 7 | `bookends-cj-black-walnut-l-bookend-pair-kids` | `kids/bookends/` | עותק של `bookends-cj-black-walnut-l-bookend-pair` (`work/bookends`), עם `mirror_of`. ‏`placement` ‏surface. ‏`rooms` ‏kids-boy + kids-girl. למקור אין options, ולכן אין `in_room` לסמן. ‏`supplier.sku` ‏`CJJT153259701AZ` הוא המק"ט המרונדר בשני החדרים, ולכן אין `room_variants`. ‏`price.cost` ‏6.72 לזוג, כמו במקור | יומן פרק 7; ‏manifest: אותו מק"ט בשני החדרים |
| 8 | `pillowcase-cj-pure-linen-envelope-pair-48x74` | `kids/pillowcase/` | עותק של `pillowcases-cj-pure-linen-envelope-pair-48x74` (`master/pillowcases`), עם `mirror_of`. ‏`placement` ‏surface. ‏`rooms` ‏kids-boy. ‏`default_sku` ו-`in_room` ‏`CJYD223749801AZ` (rain-and-dew hemp), כמו במקור. ‏`room_variants: warm-modern.kids-boy=CJYD223749801AZ` | יומן פרק 7; ‏manifest של הילד |
| 9 | `pillowcase-cj-washed-linen-double-ruffle-48x74` | `kids/pillowcase/` | עותק של `pillowcases-cj-washed-linen-double-ruffle-48x74` (`master/pillowcases`), עם `mirror_of`. ‏`placement` ‏surface. ‏`rooms` ‏kids-girl. ‏`default_sku` ו-`in_room` ‏`CJJT165654102BY` (primary color), כמו במקור. ‏`room_variants: warm-modern.kids-girl=CJJT165654102BY` | יומן פרק 7; ‏manifest של הילדה |
| 10 | `pendant-cj-silk-pumpkin-lantern-30` | `kids/pendant/` | עותק של `ceiling-lights-cj-silk-pumpkin-lantern-30` (`corridor/ceiling-lights`), עם `mirror_of`. ‏`placement` ‏ceiling. ‏`rooms` ‏kids-boy + kids-girl. ‏`default_sku` ו-`in_room` ‏`CJYD243199105EV` (‏30, אור חם), כמו במקור. זה המק"ט בשני החדרים, ולכן אין `room_variants` | יומן פרק 7; ‏manifest: אותו מק"ט בשני החדרים |
| 11 | `toy-basket-cj-jute-rope-cylinder` | `kids/toy-basket/` | עותק של `basket-cj-jute-rope-cylinder` (‏`living-room/basket`, התיקייה `basket/`), עם `mirror_of`. ‏`placement` ‏floor. ‏`rooms` ‏kids-boy. ‏`default_sku` ו-`in_room` ‏`CJYD186026903CX` (‏Large), כמו במקור. ‏`room_variants: warm-modern.kids-boy=CJYD186026903CX` | יומן פרק 7; ‏manifest של הילד |
| 12 | `toy-basket-cj-cotton-rope-white` | `kids/toy-basket/` | עותק של `basket-cj-cotton-rope-white` (‏`living-room/basket`, התיקייה `basket/`), עם `mirror_of`. ‏`placement` ‏floor. ‏`rooms` ‏kids-girl. ‏`default_sku` ו-`in_room` ‏`CJJT167870901AZ` (‏White L), כמו במקור. ‏`room_variants: warm-modern.kids-girl=CJJT167870901AZ` | יומן פרק 7; ‏manifest של הילדה (‏GB1b) |
| 13 | `cushions-cj-corduroy-patchwork-kids` | `kids/cushions/` | עותק של `cushions-cj-corduroy-patchwork` (‏`living-room/cushions`, התיקייה `cushions/`), עם `mirror_of`. ‏`placement` ‏surface (על המיטה. במקור sofa). ‏`rooms` ‏kids-boy. ‏`default_sku` ו-`in_room` ‏`CJZT189401911KP` (‏Reindeer Brown), כמו במקור. ‏`room_variants: warm-modern.kids-boy=CJZT189401911KP` | יומן פרק 7; ‏manifest של הילד. של הילדה כבר ב-kids (`cushions-cj-dusty-pink-corduroy-patchwork-45`) |
| 14 | `vanity-tray-cj-travertine-organic-tray-24` | `bath/vanity-tray/` | ‏CJ-L2. עותק של `pool-cj-travertine-organic-tray-24` (`pool/tray`), עם `mirror_of`. ‏`room` ‏bath. ‏`placement` ‏surface. ‏`rooms` ‏bath. ‏`default_sku` ו-`in_room` ‏`CJYD238979001AZ` (‏Beige Hole), כמו במקור | ‏`rendered_default` ב-`data/slots/bath.json`; ה-manifest של הרחצה (‏stage1-2026-11-17), שם המק"ט הזה; ‏`site/tools/tour/bath.warm-modern.json` |
| 15 | `desk-tray-cj-travertine-organic-tray-24` | `work/desk-tray/` | ‏CJ-L2. עותק של אותו כרטיס מאגר, עם `mirror_of`. ‏`room` ‏work. ‏`placement` ‏surface. ‏`rooms` ‏work. ‏`default_sku` ו-`in_room` ‏`CJYD238979001AZ` | ‏`rendered_default` ב-`data/slots/work.json`; ה-manifest של העבודה (‏stage1-2026-11-20); ‏`site/tools/tour/work.warm-modern.json` |
| 16 | `floor-vase-cj-wabi-sabi-floor-vase-white` | `dining/floor-vase/` | ‏CJ-L2. עותק של `pool-cj-wabi-sabi-floor-vase-white` (`pool/vase`), עם `mirror_of`. ‏`room` ‏dining-room. ‏`placement` ‏floor. ‏`rooms` ‏dining-room. ‏`default_sku` ו-`in_room` ‏`CJYD219411603CX` (‏White), כמו במקור | ‏`rendered_default` ב-`data/slots/dining-room.json`; ה-manifest של המטבח (‏D1 ו-D2); ‏`site/tools/tour/dining*.warm-modern.json` |

**הבדיקה של כל השכבות:** עברתי על כל 29 השכבות בשני ה-manifest של הילדים (15 של הילד ו-14 של הילדה). רק שמונה כרטיסים יושבים מחוץ ל-`data/products/kids/`, ולכולם יש עכשיו עותק (שורות 6–13). כל השאר כבר ב-kids:
- ‏roman-blind, ‏bookshelf, ‏framed-prints, ‏toy-cars, ‏bedding ו-soft-toy;
- ‏bedspread, כולל V2 ו-V3 של הגלגל;
- הכריות של הילדה.

## 3. הבטיחות (‏AP2-NEW): מה המקור מצהיר
לא המצאתי אף תו. שדה `safety` הועתק כמו שהוא במקור, וכשאין שדה כזה, גם בעותק אין. שורת `safety (AP2-NEW, kids)` נכתבה ב-notes.

| עותק | התקן הרלוונטי | מה המקור מצהיר |
| --- | --- | --- |
| ‏pen-cup | ‏EN 71 | ‏**לא מוצהר.** ב-`safety.source` כתוב "no certificates stated; non-electrical". זה לא צעצוע |
| ‏bookends | ‏EN 71 | ‏**לא מוצהר.** אותו `safety.source`. זה לא צעצוע |
| ‏pillowcase, ילד | ‏OEKO-TEX | ‏**לא מוצהר.** אין שדה `safety` ואין תעודה ב-notes. העמדה מבקשת OEKO-TEX, ‏"preferred" |
| ‏pillowcase, ילדה | ‏OEKO-TEX | ‏**לא מוצהר.** ב-`safety.source` כתוב "no certificates stated" |
| ‏pendant | ‏CE | ‏**לא מוצהר.** ב-notes כתוב "CE not stated - must be confirmed", ו-"Voltage: <= 36V" של המודעה סותר את רשת ה-220–240V. לפי ה-sale_note של העמדה (ד.7, ‏QA K-I7): לא נמכר לחדר ילדים עד CE |
| ‏toy-basket, שניהם | ‏EN 71 ו-OEKO-TEX | ‏**לא מוצהר.** אין שדה `safety` ואין תקן ב-notes. זה סל אחסון, והכדורים בו מילוי |
| ‏cushions, ילד | ‏OEKO-TEX | ‏**לא מוצהר.** אין שדה `safety`, וב-notes כתוב שגם הרכב הסיבים לא מוצהר |

## 4. ההחלטות שלי בביצוע
1. **בציפיות ובסלים, שני כרטיסים בעמדה, לא כרטיס אחד עם `room_variants`.**
   - הילד והילדה רונדרו עם שני מוצרים שונים. גם יומן פרק 7 אומר "שני כרטיסים" לכל אחת מהעמדות האלה.
   - כרטיס אחד לא יכול להחזיק מק"טים של שני מוצרים.
   - לכן כל עותק מסומן `in_room` על המק"ט של החדר שלו, עם `rooms` של החדר הזה ושורת `room_variants` של החדר הזה בלבד.
2. **ב-`rooms` כתבתי kids-boy / kids-girl, לא kids.** כך כתוב בתיאור השדה `room` בסכמה ("צד הכרטיס נשאר ב-rooms של הכרטיס: kids-boy / kids-girl").
3. **placement לעמדות שלא בטבלה של פרק 6** לקחתי מ-`data/slots/kids.json`: ‏pendant ‏ceiling, ‏toy-basket ‏floor, ו-cushions ‏surface. בכריות המקור הוא sofa.
4. **ה-id של כל עותק:** מחליפים את קידומת העמדה, כמו ב-11-24.
   - כשהעמדה בילדים נקראת כמו העמדה של המקור (bookends, ‏cushions), הוספתי `-kids`. כך עשו ב-11-24 עם `magazine-holder-…-master`.
   - בדקתי שאף id לא קיים כבר ושאין שם קובץ כפול.
5. **ה-notes:**
   - הועתקו מהמקור במלואם, כי `packs.ts` קורא מהם את כמות המכירה.
   - הוצאתי את שורת `room_variants` של המקור. רק לכלי העפרונות הייתה כזו (kids-girl).
   - הוספתי שורה מתוארכת, שורת בטיחות (בילדים), שורת `room_variants` כשצריך, ושורת `mirror_of`.
   - השורות שהוספתי נבדקו מול כל הביטויים של `packs.ts` (‏QTY_PER_PIECE, ‏QTY_WHOLE_SET, ‏TIMES_COST), ואף ביטוי לא נתפס. כך כמות המכירה של עותק נקראת מה-notes בדיוק כמו של המקור, עם ה-`set_of` של העמדה בילדים.
6. **ב-CJ-L2 יצאו שלושה עותקים, לא שניים.**
   - המגש מרונדר בשני חדרים: הרחצה (‏vanity-tray) והעבודה (‏desk-tray, "a marked repeat" ב-work.json). לפי הכלל "כרטיס אחד לעמדה" יש עותק לכל עמדה.
   - האגרטל מרונדר רק ב-`dining-room/floor-vase` (‏D1 ו-D2).
   - כרטיסי המאגר נשארו בלי שינוי.

## 5. פתוח, להכרעת המנהל
1. **שלושת עותקי CJ-L2 עוד לא יתומחרו באתר. זה קוד של frontend-dev, ולא נגעתי בו.**
   - ‏`mirrorOf` ב-`site/tools/build-catalog.ts` עובר למקור רק אם המקור נטען כרטיס תקין (`cards.some(…)`).
   - כרטיסי המאגר לא תקינים לסכמה (בלי `room`, ו-`slot: null`). הם ב-`invalid_cards` של הקטלוג.
   - לכן העותקים לא יקבלו את הכלכלה של המקור, שקיימת תחת ה-id של המאגר (‏`retail_ils` 169 ו-379 ב-`data/economics/products.json`, וגם `freight-cj.json`). כשחדרי הרחצה, העבודה והמטבח ייבנו, העותקים יוסתרו ("no price" או "no shipping line").
   - האפשרויות:
     - (א) ש-`mirrorOf` יחפש בכל ה-id הגולמיים;
     - (ב) שורות כלכלה תחת ה-id של העותקים.
   - עותקי הילדים לא בבעיה הזו, כי המקורות שלהם תקינים.
2. **`data/slots/kids.json` עדיין מצביע על המקורות.** הכוונה ל-`rendered_default` ול-`card` ("a shared card") בשש העמדות, וכך גם ב-bath, ‏work ו-dining-room. עדכון ה-slots הוא שינוי מסמך.
3. **שורות הילדים במקורות נשארו כמו שהן,** כי הבריף לא ביקש לגעת בהם. אם רוצים לנקות, אלה השורות:
   - בכלי העפרונות של העבודה: `room_variants: warm-modern.kids-girl=…`, והשורה מ-2026-11-19 שמסבירה שה-`in_room` הוא של הילד;
   - בכריות הקורדרוי: ה-`in_room` על Reindeer Brown "kids-boy";
   - בציפיות הפשתן: `"kids"` ב-`rooms`.
4. **אף אחד משמונת המקורות לא מצהיר תקן ילדים** (פרק 3). התלויה חסומה למכירה בילדים עד CE. מותר לשאול את הספקים על CE ו-EN 71 (ג.3), אבל שליחה רק באישור הבעלים.
5. **נמוך (ל-`backlog-low`):** בעמדת `cushions` הראשית ב-kids.json כתוב `set_of` 3 (הנורדי, 2+1). במודרני החם הזוג הוא 2 (`by_style`), אבל הקטלוג קורא את הראשית. זה לא קשור לכרטיס.
