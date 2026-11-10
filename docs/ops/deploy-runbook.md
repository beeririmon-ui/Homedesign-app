# העלאה לאוויר: מה צריך ליצור, ובאיזה סדר (S9, 2026-11-10; תוקן ב-S12, ת24)

> **frontend-dev.** אין כאן סודות, ולעולם לא יהיו בריפו.
> - **הסודות** נכנסים ב-`wrangler secret put <NAME> --env <preview|production>`, או ל-`.dev.vars` מקומי, שלא בריפו.
> - **הקונפיגורציה:** `site/api/wrangler.jsonc` (הסביבות `preview` ו-`production`, עם ערכי מקום).
> - **ה-CI:** `.github/workflows/site-ci.yml`. הוא מריץ את כל הבדיקות: typecheck, ‏lint, ‏format, ‏vitest, בנייה ותקציב (כולל בדיקת הקונפיגורציה, ‏`check-config`), ‏e2e (כולל סריקת שמות הספקים וסף הקידוד), ‏a11y ו-Lighthouse.
>   - **סוד ה-webhook ב-e2e:** ה-CI מייצר סוד זמני לכל ריצה (`openssl rand -hex 24` אל `site/api/.dev.vars`). בלעדיו ארבע בדיקות התשלום המדומה מחזירות 503.
> - **כתובות חיצוניות בקוד:** ה-API של CJ (`developers.cjdropshipping.com/api2.0/v1`, כמו ב-`scripts/cj.py`), ומפתחות החתימה של Cloudflare Access ‏(`https://<ACCESS_TEAM_DOMAIN>/cdn-cgi/access/certs`, ב-`site/api/src/lib/access.ts`, לאימות ה-JWT של ה-admin).
> - **מה חוסם השקה:** `qa/reports/2026-11-10-site-track/launch-checklist.md`.

## 1. מה הבעלים יוצר (פעם אחת)
| מה | איפה | מה מעתיקים לריפו | מה נכנס כסוד |
| --- | --- | --- | --- |
| **חשבון Cloudflare** (W4, תוכנית חינמית) | dash.cloudflare.com | — | — |
| **שני D1:** `homedesign-preview` ו-`homedesign` (של production) | Workers ו-D1 | ה-`database_id` במקום `REPLACE_WITH_PREVIEW_D1_ID` ו-`REPLACE_WITH_PRODUCTION_D1_ID` | — |
| **Queues:** ‏`supplier-orders-preview` ו-`supplier-orders-preview-dlq`; ב-production ‏`supplier-orders` ו-`supplier-orders-dlq` | Workers ו-Queues | השמות, אם שונים מ-wrangler.jsonc | — |
| **Rate limiting:** ‏`namespace_id` לכל סביבה | Workers | ‏`namespace_id` אמיתיים | — |
| **Access** (ה-admin) | Zero Trust | ‏`ACCESS_TEAM_DOMAIN`, ‏`ACCESS_AUD` (vars) | — |
| **דומיין ‎.co.il** (W3, אחרי שם המותג) | רשם, ואז Cloudflare DNS | ‏`ORIGIN` ב-`web/src/head.ts`, ו-`routes` ב-wrangler | — |
| **Webhook של התשלום** | אצל הסולק | — | `PAYMENT_WEBHOOK_SECRET` (או מה שהסולק נותן) |
| **Grow** (W1) | חשבון סוחר | — | `GROW_USER_ID`, ‏`GROW_PAGE_CODE`, ‏`GROW_API_KEY` |
| **חשבוניות** (W2: המודול של Grow, או Morning) | אצל השירות | — | `INVOICE_API_KEY` |
| **CJ** | חשבון CJ, ‏API key | — | `CJ_API_KEY` |

## 2. התיעוד שחסר בריפו (אף נקודת קצה לא נוחשה)
- **Grow** (`site/api/src/lib/payments/grow.ts`):
  - יצירת תהליך תשלום: URL ל-sandbox ול-production, אימות, והשדות לסכום, לתיאור, ללקוח, לכתובות החזרה וה-notify ולמזהה שלנו. בתשובה: כתובת הדף והמזהה.
  - התראה משרת לשרת: הפורמט, השדות, ואיך היא מאומתת (חתימה, סוד משותף, או קריאה חוזרת לאישור). דרושה דוגמה לבדיקת החוזה.
  - זיכוי דרך API, אם קיים.
- **חשבונית** (`site/api/src/lib/invoices`): הקריאה להפקת חשבונית מס/קבלה, השדות (פריטים, מע"מ כלול, משלוח, לקוח), ומזהה שמונע כפילות.
- **CJ** (`site/api/src/lib/suppliers`). מה ידוע: הטוקן מ-`scripts/cj.py`. מה חסר:
  - קריאת יצירת ההזמנה ושדותיה: מספר ההזמנה שלנו, כתובת בישראל, ‏vid וכמות, ושם הלוגיסטיקה לחסכוני ולמהיר;
  - התשובה (מזהה ההזמנה אצל CJ);
  - שלב התשלום (יתרה או ידני);
  - הזמנת sandbox.

**סדר השלמה:** כשהתיעוד נכנס לריפו, משלימים את המתאם, מוסיפים לבדיקת החוזה (`site/api/test/integrations.test.ts`) דוגמה מהתיעוד, ורק אז מדליקים את הדגל (`GROW_DOCS_CONFIRMED=1`, ‏`PAYMENT_PROVIDER=grow`, ‏`INVOICE_PROVIDER=…`).
- **`SUPPLIER_PROVIDER=cj` כבר נמצא ב-production, וזה בכוונה.** זה הערך הבטוח: בלי התיעוד, ‏CJ מסרב ליצור הזמנה לפני כל בקשה (`cj_order_api_docs_needed`), וכל הזמנה ששולמה מגיעה אחרי הניסיון החמישי ל-`supplier_error`, ולא ל"נשלחה". עד שהמתאם גמור, ההזמנות לספק נעשות ביד.

## על מה production אסור שירוץ (S12, ת17)
- **ספקים מרשימה סגורה, בהתאמה מדויקת** (`site/api/src/lib/config.ts`): תשלום `grow`; חשבוניות `grow` או `morning`; ספק `cj`. ‏`mock` מותר רק כש-`ENVIRONMENT` הוא `development`, ‏`preview`, ‏`preview-local` או `test`. כל ערך אחר של `ENVIRONMENT`, כולל ערך חסר, נחשב production.
- **ערך חסר, `mock` ב-production או שגיאת כתיב (`CJ`, ‏`Grow`):** שום ספק לא רץ. הג'וב נכשל בקול רם (ביומן של ה-Worker), נשלח לניסיון חוזר ובסוף ל-DLQ. ההזמנה נשארת במצבה האמיתי, ואף פעם לא "נשלחה לספק" או "חויבה בחשבונית".
- **`UNDECIDED`** הוא ערך המקום היחיד שמותר ב-wrangler.jsonc (התשלום והחשבוניות ב-production היום). הוא נכשל סגור בזמן ריצה: הקופה מחזירה 503, וג'וב החשבונית ממתין בתור.
- **בדיקת deploy:** ‏`npm run check:config -w @hd/api`, וגם בתוך `npm run build`. היא נכשלת על כל ערך שאינו ספק מהרשימה, ועל `mock` ב-production.
- **חשבונית אחת להזמנה (ת16):** הג'וב תופס את ההזמנה בטבלת `invoices` לפני הקריאה לספק, ומעביר את מספר ההזמנה כמפתח אידמפוטנטיות. תפיסה בלי תוצאה נפתרת בשאלה לספק, ואף פעם לא בהפקה חוזרת. כשהספק לא מאפשר לשאול: מצב `unresolved` ושורת `invoice.unresolved` ב-audit_log, לבדיקה של אדם.
- **רק הזמנה ששולמה (ת18):** ‏`paid_at` קיים, והסטטוס מתוך רשימה סגורה. הזמנה שבוטלה או זוכתה לפני ששולמה לא מקבלת חשבונית.
- **webhook רק מהספק המוגדר (ת20):** `/api/webhooks/payment/<x>` עונה רק כש-`x` הוא `PAYMENT_PROVIDER`. אחרת 404.

## 3. העלאה, צעד אחר צעד
1. **בדיקות:** `npm ci && npm run test:all` ב-`site/`. ה-CI מריץ את אותן בדיקות, ובנוסף Lighthouse ובניית ה-Artifact. מקומית, ‏e2e צריך `site/api/.dev.vars` עם `PAYMENT_WEBHOOK_SECRET` (כל מחרוזת אקראית).
2. **בנייה ציבורית:** `HD_PUBLIC=1 npm run build`. בלי `/test/` ובלי `/story/`, עד שיש פריימים במצב "מאושר לאתר".
3. **D1:** `npx wrangler d1 migrations apply DB --env preview --remote`, ואחר כך `npm run seed:sql -w @hd/api` ו-`npx wrangler d1 execute DB --env preview --remote --file ../.generated/seed.sql`. ה-seed עושה upsert, ולכן אפשר להריץ אותו שוב.
4. **סודות:** `wrangler secret put …` לכל סוד בטבלה, ל-`preview` קודם.
5. **העלאה:** `npx wrangler deploy --env preview` מ-`site/api`. אחר כך בדיקה ידנית: קנייה מלאה עם התשלום המדומה, ותשלום sandbox כשהסולק מחובר.
6. **אותו הדבר ל-production:** רק אחרי אישור הבעלים, ורק כשכל החוסמים ברשימת ההשקה סגורים.

## 4. מה מוגן כבר היום
- **בלי נתוני אשראי באתר:** דף תשלום מתארח, ‏SAQ A (לא אומת).
- **התשלום המדומה חסום ב-production:** `mock_payments_disabled_in_production`. מ-S12 גם החשבונית והספק המדומים (ראו "על מה production אסור שירוץ").
- **Grow ו-CJ מסרבים בקול רם** כשחסר מפתח או תיעוד. אף קריאה לא נשלחת עם בקשה מנוחשת.
- **השרת מתמחר כל שורה:** הוא מסרב לכמות מחוץ ל-1–20 ולמוצר שלא במכירה.
- **סריקה בכל CI:** שום שם ספק או מספר מוצר לא מגיע לדפדפן.
