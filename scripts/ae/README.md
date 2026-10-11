# AliExpress Dropshipping API: ‏`scripts/ae/`

לקוח Python 3 (ספרייה סטנדרטית בלבד) ל-AliExpress Open Platform, אפליקציית **Drop Shipping**, לפי התיעוד הרשמי ו-SDK הרשמי. נכתב 2026-10-10. חלק מצנרת הסורסינג "פעם אחת" (`scripts/sourcing/README.md`): אותו מרשם (`data/sources/seen.json`), אותו תקציב ואותו מטמון כמו ב-CJ.

| קובץ | מה הוא |
| --- | --- |
| `client.py` | הפרוטוקול: חתימה, קריאות מערכת (`/rest/auth/token/*`) ועסקיות (`/sync?method=aliexpress.ds.*`), טוקן, קצב, שגיאות |
| `auth.py` | ההרשאה החד-פעמית עם חשבון הקונה של המשתמש, ומצב הטוקן |
| `ds.py` | ה-CLI לסורסינג: חיפוש, מוצר, משלוח, חיפוש לפי תמונה, תעודות, קטגוריות, כרטיס מוצר |
| `test_sign.py` | בדיקות יחידה לחתימה מול הדוגמה הרשמית: `python3 -I scripts/ae/test_sign.py` |

## 1. הגדרה (פעם אחת)

**מפתחות רק במשתני סביבה.** ‏`AE_DS_APP_KEY` ו-`AE_DS_APP_SECRET` (App Key ו-App Secret מ-App Console > App Management > Advanced Information) נכנסים בהגדרות הסביבה של Claude (תפריט הסביבה בשורת הכותרת > Edit > Network secrets / משתני סביבה), ואז פותחים סשן חדש. לא מדביקים אותם בצ'אט, לא בקבצים ולא בפקודות. הסקריפטים לא מדפיסים אותם לעולם; בלי משתני הסביבה הם מדפיסים "לא מוגדר" ולא קוראים לכלום.

**מצב האפליקציה:** האפליקציה שלנו בסטטוס **Test**, עם קבוצות ההרשאה **System Tool** ו-**AliExpress-dropship**, ו-Callback URL ‏`https://127.0.0.1/callback`. בסטטוס Test הטוקן קצר: ‏access_token ליום אחד ו-refresh_token ליומיים (תיעוד 1590). אחרי שהפיתוח עובד, לוחצים **Apply Online** בקונסול (Quick Start, שלב 5, תיעוד 1391); אחרי האישור הטוקן תקף 30 יום וה-refresh ‏60 יום. עד אז צריך לרענן או להרשות מחדש כל יום-יומיים; `ds.py` מרענן לבד כל עוד ה-refresh_token בתוקף.

## 2. הרשאה ראשונה (חשבון הקונה של המשתמש)

להריץ **בסשן שבו משתני הסביבה קיימים, רצוי בסשן על המחשב של המשתמש (Claude Desktop)**, כך שה-code לא עובר בצ'אט:

```bash
python3 scripts/ae/auth.py url
```
1. פותחים את הכתובת בדפדפן ומתחברים עם **חשבון הקונה** של AliExpress (לא חשבון מוכר), ולוחצים Access Now / Authorize.
2. הדפדפן מופנה אל `https://127.0.0.1/callback?code=...`. **הדף לא ייטען, וזה בסדר.** מעתיקים את הערך של `code` משורת הכתובת (אפשר להעתיק את כל הכתובת).
3. באותו טרמינל, תוך דקות (ה-code חד-פעמי וקצר-חיים):
```bash
python3 scripts/ae/auth.py code <code>
```
הפלט: `stored, expires <תאריך>, account <מוסווה>`. הטוקן נשמר ב-`~/.cache/ae/token.json` (‏chmod 600, מחוץ לריפו) עם access_token, refresh_token, תוקף ומזהה החשבון כפי שחזר. אף פעם לא מדפיסים אותו.

```bash
python3 scripts/ae/auth.py status    # יש טוקן תקף? עד מתי? אפשר לרענן?
python3 scripts/ae/auth.py refresh   # רענון עכשיו (/auth/token/refresh)
python3 scripts/ae/auth.py forget    # מחיקת הטוקן השמור
```
אם סשן הענן צריך את הטוקן: מעתיקים את הקובץ `~/.cache/ae/token.json` לאותו נתיב בסביבה (לא דרך הצ'אט), או מריצים את ההרשאה שם.

## 3. פקודות (`ds.py`)

דגלים גלובליים לפני הפקודה, כמו ב-`cj_source.py`: ‏`--dry-run` (בלי רשת ובלי כתיבה), ‏`--force`, ‏`--by NAME`, ‏`--run-id ID`, ‏`--max-calls N`, ‏`--no-cache`, ‏`--hide-seen`, ‏`--raw`. קודי יציאה: 1 שגיאת API (ההודעה המלאה של AliExpress מודפסת, בלי סודות), 2 לא מוגדר, 3 עצירת תקציב.

| פקודה | שיטה | הערות |
| --- | --- | --- |
| `search "<מילים>" [--ship-to IL] [--currency USD] [--page 1] [--size 20] [--sort orders,desc] [--category ID]` | `aliexpress.ds.text.search` | מיון: `min_price` / `orders` / `comments` עם `asc` או `desc`. כל תוצאה מסומנת `registry` (open / warn / skip). מטמון 7 ימים |
| `product <id> [<id> ...] [--ship-to IL] [--slot room/slot] [--full]` | `aliexpress.ds.product.get` | מדלג על מה שהמרשם אומר לדלג (כמו CJ). כותרת, תמונות, SKU עם מחירים ומלאי, מאפיינים, אריזה ומשקל, חנות, קטגוריה. ה-HTML של התיאור מוסר אלא אם `--full`. מטמון 30 יום. נרשם כ-`seen`, ‏`opened: true` |
| `freight <id> --sku <sku_id> [--country IL] [--qty 1]` | `aliexpress.ds.freight.query` | אפשרויות משלוח: קוד, חברה, עלות, ימים, מעקב, מאיפה נשלח. מטמון 14 יום. ‏`sku_id` מגיע מ-`product` |
| `image-search <קובץ או https-URL> [--type similar\|same] [--ship-to IL]` | `aliexpress.ds.image.searchV2` | התמונה נשלחת ב-base64 (עד 5MB). קיים ל-DS, מחובר |
| `specialinfo <id> [--country IL]` | `aliexpress.ds.product.specialinfo.get` | תעודות (CE ועוד) כפי שהמוכר מצהיר. **לא מורשה לאפליקציה שלנו (2026-10-11): `APPKEY_NOT_ALLOWED`**, ולכן גם `card --certs` נכשל |
| `category [--id ID]` | `aliexpress.ds.category.get` | שם קטגוריה לפי `cateId` מהחיפוש |
| `card <id> --slot <room>/<slot> [--out נתיב] [--sku ID] [--certs] [--no-freight]` | מוצר + משלוח (+ תעודות) | כותב כרטיס לפי `data/product-card.schema.json` ורושם במרשם כ-`card`. ראו 3.1 |
| `card <id> --slot <room>/<slot> --offline [--sku ID] [--ship-usd X --ship-days A-B --ship-company NAME --ship-basis "..."]` | מטמון בלבד | אותו כרטיס (כולל `options`) מתשובת `product.get` השמורה, בלי מפתח, בלי טוקן, בלי תקציב ובלי רשת (כל ניסיון קריאה נחסם). המשלוח: הציטוט השמור ל-SKU, אחרת הערכים שבשורת הפקודה (למשל מרשומת ה-detail של ריצת הסקייל), אחרת בלי משלוח. `--certs` נדחה. נוסף ב-2026-10-11 לשלב 3 של ריצת הסקייל |
| `backfill-options [card.json ...]` | מטמון בלבד | בונה `options` (כל ה-SKU) לכרטיסי AliExpress קיימים מתשובות `product` השמורות ב-`data/sources/aliexpress/<id>.json`. בלי קריאה ובלי תקציב. כרטיס שכבר יש בו options נשאר כמו שהוא (`--force` בונה מחדש רק `source: "api"`) |
| `check <id> [...]` / `mark <id> --status ... --reason "..."` | מרשם בלבד | בלי קריאה |

`scripts/sourcing/aliexpress_source.py` הוא כיסוי דק לאותן פקודות (`image` = ‏`image-search`), כדי שכל המקורות ייראו אותו דבר.

### 3.1 מה `card` ממלא ומה לא
ממלא מה-API בלבד, בלי להמציא: שם, ‏`supplier` (‏AliExpress, ‏`https://www.aliexpress.com/item/<id>.html`, ‏SKU שנבחר, דירוג המוצר), מחיר ה-SKU (הזול במלאי, או `--sku`) בדולר כפי שחזר, משלוח לישראל (הזול: ימים; הזול והמהיר ב-notes), תמונות (`usage_rights: unclear`), חומרים אם מופיעים במאפיינים, ‏`placement` מקובץ העמדות, ואם `--certs`: ‏`safety.certificates`. **לא ממלא** צבעים (HEX), משקל ויזואלי, מידות המוצר (רק האריזה, ב-notes) וטקסטורה: הם `null`, וה-notes פותחים ב-"DRAFT". sourcing-agent משלים אותם מהתמונות לפני QA. המזהה: `<slot>-aliexpress-<מילים מהכותרת>` (אפשר `--id`).

**אפשרויות (2026-10-11, חוקי הסטודיו ג):** `card` כותב גם `options`: כל ה-SKU של המוצר מ-`ae_item_sku_info_dtos` (שם הציר מ-`sku_property_name`, התווית מ-`property_value_definition_name`), מחיר, מלאי ותמונה לכל SKU, ומשלוח לישראל ל-SKU שיש לו הצעה שמורה. ‏`default_sku` הוא ה-SKU שנבחר (‏`--sku`), והוא היחיד עם `in_room: true`. המיפוי והבדיקה: `scripts/sourcing/options.py`.

דוגמת סבב:
```bash
python3 scripts/ae/ds.py --hide-seen search "travertine wall sconce" --sort orders,desc
python3 scripts/ae/ds.py --dry-run product 1005001234567890
python3 scripts/ae/ds.py product 1005001234567890 --slot living-room/accent-sconces
python3 scripts/ae/ds.py freight 1005001234567890 --sku 12000012345678901
python3 scripts/ae/ds.py card 1005001234567890 --slot living-room/accent-sconces --certs
```

## 4. הפרוטוקול, בקצרה (אומת 2026-10-10)
- **כתובות** (תיעוד 1369): עסקיות `https://api-sg.aliexpress.com/sync?method=<api>` ‏(‏`aliexpress.ds.*`), מערכת `https://api-sg.aliexpress.com/rest/auth/token/create` ו-`/rest/auth/token/refresh`. תמיד POST ‏(`application/x-www-form-urlencoded`).
- **חתימה** (תיעוד 1386, דוגמה מלאה ב-1385, ו-SDK הרשמי `IopUtils.signApiRequest`): ממיינים את כל הפרמטרים (מערכת ועסקיים, כולל `method`) לפי שם, משרשרים שם+ערך בלי מפרידים (ערכים ריקים מדולגים), בקריאת מערכת מקדימים את הנתיב (`/auth/token/create`), ‏HMAC-SHA256 עם ה-App Secret, הקס באותיות גדולות. ‏`sign_method=sha256`, ‏`timestamp` במילישניות (עד 7200 שניות מ-UTC).
- **פרמטרי מערכת** שאנחנו שולחים ב-`/sync`: ‏`app_key`, ‏`timestamp`, ‏`sign_method`, ‏`method`, ‏`access_token`, ‏`format=json`, ‏`v=2.0`, ‏`simplify=true`, ‏`partner_id`. **אומת 2026-10-11: `access_token` עובד** (ה-SDK הרשמי קורא לו `session`; `AE_DS_TOKEN_PARAM=session` נשאר כגיבוי).
- **הרשאה** (תיעוד 1364 ו-1590): ‏`https://api-sg.aliexpress.com/oauth/authorize?response_type=code&force_auth=true&redirect_uri=<callback>&client_id=<app_key>`, ואז `code` → ‏`/auth/token/create`. רענון מומלץ 30 דקות לפני הפקיעה; ‏`refresh_expires_in = 0` אומר שאי אפשר לרענן.
- **שגיאות:** שגיאת gateway היא `{type, code, message|msg, sub_code, sub_msg, request_id}` (לפעמים תחת `error_response`); שגיאה עסקית ב-`rsp_code`/`rsp_msg`, ‏`resp_code`, ‏`code`/`msg` או `result.success`. המעטפת `<api>_response` ו-`resp_result` מוסרת אוטומטית. ההודעה מודפסת במלואה (שמות השגיאות נחוצים לדיבוג), בלי שום סוד.
- **קצב:** לפחות 0.5 שניות בין קריאות; ניסיון חוזר עם המתנה רק על HTTP 5xx ושגיאות רשת; על "Api access frequency exceeds the limit" (תיעוד 1790) ניסיון חוזר אחד אחרי 2 שניות. ‏`AE_DS_DEBUG=1` מדפיס רק שמות פרמטרים, לא ערכים.

## 5. מגבלות שנמצאו
- **מכסת קריאות לאפליקציית Test: לא פורסמה.** לפי התיעוד (1361) מדיניות בקרת התעבורה נקבעת לקטגוריית האפליקציה ומוצגת בקונסול (App Console > Auth Management / App Overview). ב-FAQ של `ds.product.get` (תיעוד 1790): ‏QPS כולל 500 לחיבור, ו-1–2% שגיאות ויסות שמומלץ לפתור בהמתנה של 1–2 שניות. עד שיועתק הערך מהקונסול, התקציב שלנו (`scripts/sourcing/budget.py`) מגביל ל-5,000 קריאות ביום (עצירה רכה ב-4,000) ו-150 קריאות לריצה.
- **טוקן ב-Test:** יום אחד (‏refresh יומיים). אחרי Apply Online: ‏30 / 60 יום.
- **ה-code** מההרשאה חד-פעמי וקצר-חיים (התיעוד אומר 3 דקות במקום אחד ו-30 דקות במקום אחר): להחליף מיד.
- **זכויות תמונה:** לא מוגדרות ב-API. נשאר `unclear`.
- **מחירים:** `ds.product.get` מחזיר מחירי SKU למטבע ולמדינה שביקשנו (USD, ‏IL); לפי התיעוד המחיר יכול להיות שונה ממחיר האתר אם יש הנחת דף. אם `estimated_import_charges` ריק, המחיר כולל מסי יבוא משוערים (שינוי 2025-04-27).

## 6. מה לא מומש
- הזמנות (`aliexpress.ds.order.create`, ‏`aliexpress.ds.order.tracking.get`, ‏`aliexpress.ds.order.afterpay`), פידים (`aliexpress.ds.feed.itemids.get`), סיטונאות (`aliexpress.ds.product.wholesale.get`), ‏`aliexpress.logistics.buyer.freight.calculate` (יש לנו `ds.freight.query`), ‏Webhooks, ו-`/auth/token/security/*`.
- אפליקציית ה-Affiliates (מפתחות `AE_AFF_*`): לא נדרשת ולא מחוברת.
- המרת מזהי `.us` (3256…) למזהי `.com` (1005…) לפני הקריאה: ה-API מקבל את שניהם, והמזהים שחוזרים ב-`product_id_converter_result` נרשמים במרשם כ-aliases.
- (ראו סעיף 7: מה שלא היה מאומת אומת ב-2026-10-11.)

## 7. אומת מול ה-API החי (2026-10-11)
פירוט מלא: `data/leads/aliexpress/api-first-call-2026-10-11.md`.
- **הרשאה:** עבדה עם חשבון הקונה. ‏`auth.py code` מקבל את כתובת ה-redirect המלאה. בסטטוס Test: ‏access_token ‏24 שעות, refresh ‏48 שעות.
- **טוקן:** `access_token`. מכסה יומית לא מוחזרת בתגובות.
- **מעטפות עם `simplify=true`:** אין `<method>_response`. ‏`ds.product.get` שטוח (`result`, ‏`rsp_code: 200`, ‏`rsp_msg`, ‏`request_id`); ‏`ds.category.get` בתוך `resp_result` (`resp_code`). ‏`unwrap()` ו-`business_status()` מטפלים בשניהם.
- **`ds.text.search`:** שמות השדות לפי התיעוד. ‏`salePrice` ביואן (`salePriceCurrency: CNY`); המחיר בדולר ב-`targetSalePrice`. ‏`orders`/`evaluateRate` לפעמים ריקים.
- **מזהים:** מזהי `.us` (3256…) מתקבלים ישירות ב-`ds.product.get`; ‏`product_id_converter_result.main_product_id` הוא מזהה ה-.com, ו-`sub_product_id` מחרוזת JSON (`"{\"US\":3256...}"`), שמפורקת ל-aliases.
- **משלוח:** אין אפשרות → שגיאה `DELIVERY_SERVICE_EXCEPTION` (נשמר ככרטיס "אין משלוח"). באפשרות חינמית אין מטבע: הלקוח ממלא את המטבע המבוקש.
- **`card`:** ברירת המחדל היא ה-SKU הזול במלאי, שבטקסטיל הוא בדרך כלל המידה הקטנה ביותר: לבחור `--sku`. ‏`--out` לא קובע את ה-id: להעביר גם `--id`. slug זהה של מוצר אחר לא נדרס (מתווספות 6 ספרות מהמזהה).
