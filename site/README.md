# site/: החנות (אפשרות ג')

האתר: Preact, ‏Vite ומנוע WebGL2. השרת: Cloudflare Worker (Hono) עם D1 ו-Queues.
הארכיטקטורה המלאה, ההחלטות הפתוחות והסביבות מתוארות ב-[`docs/architecture.md`](../docs/architecture.md).

## דרישות

- Node 22.12 ומעלה.
- כל השאר מקומי: לא צריך חשבון ולא צריך מפתח.

## הרצה מקומית

```bash
cd site
npm install
npm run dev        # בונה קטלוג ומדיה זמנית, מאפס D1 מקומי, ומריץ את Vite ‏(http://127.0.0.1:5180) ואת ה-Worker ‏(8787)
```

- בפעם הראשונה נוצר `api/.dev.vars` עם סוד מקומי אקראי ל-mock. הקובץ ב-gitignore.
- התשלום מדומה (`/mock-pay/...`), וגם הספק מדומה.

## סקריפטים

| פקודה                             | מה עושה                                                                                         |
| --------------------------------- | ----------------------------------------------------------------------------------------------- |
| `npm run dev`                     | פיתוח: ‏Vite ו-wrangler dev עם D1 מקומי                                                         |
| `npm run build`                   | קטלוג ← מדיה זמנית ← build של האתר ו-prerender ← dry-run של ה-Worker ← בדיקת תקציב (`budget`)   |
| `npm run preview`                 | הבנייה המקומית "כמו בפרודקשן": Worker אחד מגיש את `web/dist` ואת ה-API ‏(http://127.0.0.1:8788) |
| `npm run typecheck`               | ‏tsc בכל ה-workspaces ובדיקה שהסכמה שנוצרה מעודכנת                                              |
| `npm run lint`                    | ESLint עם typescript-eslint ו-jsx-a11y (strict)                                                 |
| `npm run format` / `format:check` | Prettier                                                                                        |
| `npm test`                        | Vitest: תמחור, סכמות, routes של ה-API מול SQLite, webhook חתום, תור ו-Access JWT                |
| `npm run e2e`                     | Playwright: זרימת קנייה מלאה, מקלדת וגרירה בגלגל, SEO, תקציב 3MB, preload                       |
| `npm run a11y`                    | axe בכל סוגי העמודים, בבהיר ובכהה, עם אפס הפרות                                                 |
| `npm run lighthouse`              | Lighthouse במובייל (צריך `npm run preview` רץ). הדוחות נשמרים ב-`.lighthouse/`                  |
| `npm run budget`                  | תקציב JS, ‏CSS וטעינה ראשונה של החדר                                                            |
| `npm run catalog:strict`          | קטלוג בכלל של פרודקשן: מוצר בלי `retail_ils` לא מוצג                                            |
| `npm run preview:artifact`        | בונה את `dist-artifact/` (ה-API מדומה בדפדפן) ובודק את חוזה ה-Artifact                          |
| `npm run screens:artifact`        | פותח את `dist-artifact` ב-Chromium ברוחב 1280 וברוחב 400, ושומר צילומים ב-`screens/`            |

**Playwright:**

- משתמש ב-Chromium שב-`/opt/pw-browsers/chromium`. בסביבה הזו לא מריצים `playwright install`.
- במחשב אחר מגדירים `PW_CHROMIUM=<נתיב>`.
- ה-e2e מריץ `npm run preview` בעצמו, אחרי `npm run build`.

## מה נמצא איפה

- `shared/`: סכמות zod, תמחור (`pricing.ts`, אותה נוסחה כמו בסטודיו), חתימת webhook.
- `api/`:
  - `src/routes/`: ‏public, ‏payments ו-admin.
  - `src/lib/`: ‏payments ו-suppliers (ממשקים, כרגע mock), ‏fulfillment (צרכן התור) ו-access.
  - `migrations/`: הסכמה של D1.
  - `scripts/seed.ts`: מהקטלוג אל SQL.
- `web/`:
  - `src/engine/`: מנוע השכבות. הסדר לפי z מ-`data/slots`. הצל ב-multiply והאור ב-screen. מצלמה, זום עם פרלקסה, cross-fade של 0.3 שניות לווריאציה ושל שנייה לסגנון, ורצף פריימים.
  - `src/components/`: החדר, הגלגל והמעברים.
  - `src/pages/`: העמודים.
- `tools/`:
  - `build-catalog.ts`: מהריפו אל הקטלוג.
  - `make-temp-assets.ts`: תמונות זמניות בשמות הסופיים.
  - בדיקות תקציב ו-Artifact.
- `e2e/`: בדיקות Playwright.

## תמונות זמניות

- `npm run assets:temp` מייצר מדיה ב-`web/public/media/` (gitignored) מתוך מקורות שמוגדרים ב-`tools/temp/living-room.nordic.json` וב-`assets/manifest.json`.
- הנתיבים כבר סופיים. כשיהיו נכסים סופיים שעברו QA, מחליפים קבצים ולא קוד.

## Artifact (תצוגה מקדימה לפרסום)

```bash
npm run preview:artifact     # dist-artifact/: index.html ותיקיית media/ (WebP), ובדיקת מגבלות
npm run screens:artifact     # צילומים ב-screens/artifact-{1280,400}-*.png
```

- אין doctype, ‏html, ‏head או body.
- הסדר: `<title>`, אחריו `<style>`, ואחריו Google Fonts. ה-JS inline.
- הניווט בזיכרון, בלי hash.
- העגלה וההזמנות נשמרות ב-localStorage, עם try/catch.
