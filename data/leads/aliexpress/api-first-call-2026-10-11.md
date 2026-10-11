# AliExpress DS API: הרשאה ראשונה וקריאות חיות (2026-10-11)

סשן עזר "aliexpress-session". לקוח: `scripts/ae/`. אפליקציה 552442 בסטטוס Test. 34 קריאות API (תקציב לריצה: 150).

## מה עבד
- **הרשאה:** `auth.py url` → המשתמש אישר עם חשבון הקונה → `auth.py code '<redirect URL>'` (מקבל את הכתובת המלאה). הטוקן נשמר ב-`~/.cache/ae/token.json` (מחוץ לריפו). חשבון: buyerApp.
- **שם פרמטר הטוקן:** `access_token` (ברירת המחדל) עובד. לא נדרש `AE_DS_TOKEN_PARAM=session`.
- **תוקף הטוקן (Test):** access_token ‏24 שעות (עד 2026-10-12 10:07 UTC), refresh_token ‏48 שעות (עד 2026-10-13 10:07 UTC). תואם את התיעוד.
- **מכסה יומית:** לא מוחזרת בתגובות (אין כותרת או שדה). נשאר התקציב שלנו ב-`scripts/sourcing/budget.py`.
- **עובדים:** `ds.text.search`, ‏`ds.product.get`, ‏`ds.freight.query`, ‏`ds.category.get`.
- **לא מורשה:** `aliexpress.ds.product.specialinfo.get` (תעודות) מחזיר `APPKEY_NOT_ALLOWED | appkey is not allowed`. כלומר `--certs` לא עובד באפליקציה הזו עד שתתווסף הרשאה בקונסול.

## צורת המעטפות (עם `simplify=true`)
- **אין** עטיפת `<method>_response`.
- `ds.product.get`: שטוח: `{result: {...}, rsp_code: 200, rsp_msg: "Call succeeds", request_id, _trace_id_}`.
- `ds.category.get`: `{resp_result: {result, resp_code: 200, resp_msg}, request_id, _trace_id_}`.
- `ds.text.search`: ‏`total`, ומוצרים עם `itemId`, ‏`title`, ‏`itemMainPic`, ‏`itemUrl`, ‏`orders`, ‏`evaluateRate`, ‏`score`, ‏`cateId`. **מחירים:** `salePrice`/`originalPrice` ביואן (`salePriceCurrency: CNY`); בדולר: `targetSalePrice`/`targetOriginalPrice`. ‏`orders` ו-`evaluateRate` לפעמים ריקים.
- `ds.freight.query`: ‏`result.delivery_options`. באפשרות חינמית אין `shipping_fee_currency` (תוקן בלקוח: המטבע המבוקש). אם אין משלוח: שגיאה `DELIVERY_SERVICE_EXCEPTION`.
- `ds.product.get` → `product_id_converter_result`: ‏`main_product_id` מספר (מזהה ה-.com), ‏`sub_product_id` **מחרוזת JSON** כמו `"{\"US\":3256...}"` (תוקן בלקוח).
- שגיאות מערכת (מהסשן הראשי): שטוח `{type, code, message}`; שגיאה עסקית: `{"error_response": {type, code, msg}}`.

## מזהים
- **מזהי `.us` ‏(3256…) מתקבלים ישירות** בכל 15 המוצרים; ה-API מחזיר את מזהה ה-.com ‏(1005…) ב-`main_product_id`, והוא נרשם כ-alias במרשם.
- מזהה ישן (2255800578472233) עבד גם הוא; ה-main שלו 4000764786985.

## המוצרים (15 עם fit_guess ≥ 7 ב-`shortlist-2026-10-10.json`)
מחיר = ה-SKU שנבחר לכרטיס, בדולר, לפני משלוח. משלוח = האפשרות הזולה לישראל.

| item_id | עמדה | SKU שנבחר | מחיר USD | משלוח ל-IL (USD, ימים) | כרטיס | למה |
| --- | --- | --- | --- | --- | --- | --- |
| 3256806985105007 | living-room/cushions | Beige 45×45 | 11.17 | 1.99, 6–15 | כן | בוקלה מט; כרית בוקלה אחת בסט מותרת. כיסוי בלבד |
| 3256808664091154 | living-room/curtains | Tulle 1PC 200×260, Rod pocket | 41.71 | 1.99, 6–15 | כן | פשתן-לוק שקוף, 232 ביקורות. **גובה מקסימלי 260** (מוט ב-282: הקצה כ-20 ס"מ מעל הרצפה, לבדוק אם יש מידה מותאמת). 100% פוליאסטר |
| 3256811998576912 | living-room/curtains | Yarn 1PC 200×260, Rod pocket | 29.70 | 1.99, 6–15 | כן | אותו בד ואותה כותרת כמו הקודם, חנות אחרת, 4 ביקורות. אותה הערת גובה |
| 3256810570758345 | living-room/curtains | — | 13.50+ | 0, **76 ימים** (Seller's Shipping) | לא | משלוח לישראל רק בשיטת המוכר, 76 יום. נדחה במרשם |
| 3256805238071479 | living-room/curtains | — | 135 (placeholder) | לא נבדק | לא | כל ה-SKU הם "Contact us"/"Custom Size" ב-135: אין מחיר אמיתי. נדחה |
| 3256807415537790 | living-room/accent-sconces | Warm White 3000K, 16 ס"מ | 51.94 (ליחידה; זוג = ×2) | 23.39, 22–32 | כן | אבן (Stone), מחווט, E27, ‏90–260V. מידת 16 ס"מ נכנסת במעטפת 14×18 (23/28/32 לא). **לוודא טרוורטין אמיתי ו-CE**: תעודות לא זמינות ב-API |
| 3256807071050757 | dining-room/centerpiece-vase | — | 15.78 | **אין משלוח** | לא | DELIVERY_SERVICE_EXCEPTION. נדחה |
| 3256809956724885 | dining-room/centerpiece-vase | F | 11.90 | **30.64**, 9–19 | כן | מט מורנדי, 7 גוונים (A–G, הצבעים רק בתמונות). המשלוח יקר פי 2.5 מהמוצר |
| 3256804234725093 | dining-room/centerpiece-vase | S | 17.41 | 8.42, 8–18 | כן | מט, CAPIRON (אותה חנות כמו אגרטל הרצפה). S/L, גובה לבדוק מול 20–28 |
| 2255800578472233 | dining-room/centerpiece-vase | Small | 10.62 | 0.00, 8–18 | כן | לבן מט, S/M/L. גובה לבדוק מול 20–28 |
| 3256811647185429 | dining-room/candle-holders | Black, no candle | 24.63 | 1.99, 6–15 | כן | קרמיקה שחורה (פחם חובה). 0 ביקורות. "Big candle holder": לבדוק גובה מול 1–12 |
| 3256811847480845 | dining-room/candle-holders | (SKU יחיד) | 10.46 | 1.99, 6–15 | כן | זוג ברזל שחור מט לנרות עמוד. מלאי 5, ‏0 ביקורות |
| 3256813144317414 | dining-room/floor-vase | — | 35.02 | לא נבדק | לא | הכותרת "קרמיקה" אבל המאפיין Material = Plastic; מלאי 1. נדחה |
| 3256808800994217 | dining-room/floor-vase | B | 22.02 | 5.61, 8–18 | כן | CAPIRON, קרמיקה, Size L, ‏14 ביקורות. גובה לבדוק מול 50–65 |
| 3256812137993644 | dining-room/kitchen-sconce | Beige | 27.02 | **אין משלוח** | לא | DELIVERY_SERVICE_EXCEPTION. נדחה (אחרת מתאים: פשתן, זרוע שחורה, 220V) |

**סה"כ: 10 כרטיסים** (4 בסלון, 6 בפינת האוכל), 5 נדחו ונרשמו כ-`rejected` ב-`data/sources/seen.json`.

כל הכרטיסים הם **DRAFT**: צבעים (HEX), משקל ויזואלי, מידות המוצר וטקסטורה ריקים (ה-API נותן רק מידות אריזה). sourcing-agent משלים מהתמונות, ואז master-designer מדרג ו-qa-agent בודק.

## תיקונים בלקוח (`scripts/ae/ds.py`)
1. `sub_product_id` הוא מחרוזת JSON: מפורק למזהים; ה-aliases השגויים ב-15 הרשומות נוקו.
2. `card` כבר לא דורס כרטיס של מוצר אחר עם אותו slug (מוכרים ממחזרים כותרות): מוסיף 6 ספרות אחרונות של המזהה.
3. משלוח חינם בלי מטבע: מקבל את המטבע המבוקש.
- `test_sign.py` עובר.

## לשים לב
- ברירת המחדל של `card` היא ה-SKU הזול במלאי. בווילונות זה היה 100×130: תמיד לבחור `--sku` לפי מידה.
- `--out` לא קובע את ה-id של הכרטיס: בפינת האוכל להעביר גם `--id` (שם הקובץ).
- בסטטוס Test צריך לרענן כל יום (`ds.py` עושה זאת לבד) ולהרשות מחדש אחרי יומיים. Apply Online בקונסול נותן 30/60 יום.
