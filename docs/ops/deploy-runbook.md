# העלאה לאוויר: מה צריך ליצור, ובאיזה סדר (S9, 2026-11-10)

> **frontend-dev.** אין כאן סודות, ולעולם לא יהיו בריפו.
> - **הסודות** נכנסים ב-`wrangler secret put <NAME> --env <preview|production>`, או ל-`.dev.vars` מקומי, שלא בריפו.
> - **הקונפיגורציה:** `site/api/wrangler.jsonc` (הסביבות `preview` ו-`production`, עם ערכי מקום).
> - **ה-CI:** `.github/workflows/site-ci.yml`. הוא מריץ את כל הבדיקות: typecheck, ‏lint, ‏format, ‏vitest, בנייה ותקציב, e2e (כולל סריקת שמות הספקים), ‏a11y ו-Lighthouse.
> - **מה חוסם השקה:** `qa/reports/2026-11-10-site-track/launch-checklist.md`.

## 1. מה הבעלים יוצר (פעם אחת)
| מה | איפה | מה מעתיקים לריפו | מה נכנס כסוד |
| --- | --- | --- | --- |
| **חשבון Cloudflare** (W4, תוכנית חינמית) | dash.cloudflare.com | — | — |
| **שני D1:** `homedesign-preview` ו-`homedesign-prod` | Workers ו-D1 | ה-`database_id` במקום `REPLACE_WITH_PREVIEW_D1_ID` ו-`REPLACE_WITH_PRODUCTION_D1_ID` | — |
| **Queues:** `supplier-orders-<env>` ו-DLQ | Workers ו-Queues | השמות, אם שונים מ-wrangler.jsonc | — |
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

**סדר השלמה:** כשהתיעוד נכנס לריפו, משלימים את המתאם, מוסיפים לבדיקת החוזה (`site/api/test/integrations.test.ts`) דוגמה מהתיעוד, ורק אז מדליקים את הדגל (`GROW_DOCS_CONFIRMED=1`, ‏`PAYMENT_PROVIDER=grow`, ‏`INVOICE_PROVIDER=…`, ‏`SUPPLIER_PROVIDER=cj`).

## 3. העלאה, צעד אחר צעד
1. **בדיקות:** `npm ci && npm run test:all` ב-`site/`. ה-CI מריץ את אותו הדבר.
2. **בנייה ציבורית:** `HD_PUBLIC=1 npm run build`. בלי `/test/` ובלי `/story/`, עד שיש פריימים במצב "מאושר לאתר".
3. **D1:** `npx wrangler d1 migrations apply DB --env preview --remote`, ואחר כך `npm run seed:sql -w @hd/api` ו-`npx wrangler d1 execute DB --env preview --remote --file ../.generated/seed.sql`.
4. **סודות:** `wrangler secret put …` לכל סוד בטבלה, ל-`preview` קודם.
5. **העלאה:** `npx wrangler deploy --env preview` מ-`site/api`. אחר כך בדיקה ידנית: קנייה מלאה עם התשלום המדומה, ותשלום sandbox כשהסולק מחובר.
6. **אותו הדבר ל-production:** רק אחרי אישור הבעלים, ורק כשכל החוסמים ברשימת ההשקה סגורים.

## 4. מה מוגן כבר היום
- **בלי נתוני אשראי באתר:** דף תשלום מתארח, ‏SAQ A (לא אומת).
- **התשלום המדומה חסום ב-production:** `mock_payments_disabled_in_production`.
- **Grow ו-CJ מסרבים בקול רם** כשחסר מפתח או תיעוד. אף קריאה לא נשלחת עם בקשה מנוחשת.
- **השרת מתמחר כל שורה:** הוא מסרב לכמות מחוץ ל-1–20 ולמוצר שלא במכירה.
- **סריקה בכל CI:** שום שם ספק או מספר מוצר לא מגיע לדפדפן.
