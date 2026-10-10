# מסירה לסשן על המחשב של המשתמש (2026-10-10)

למי שפותח סשן חדש בתיקייה הזו (Claude Desktop או `claude remote-control`): קרא קודם `CLAUDE.md`, ‏`docs/studio-rules.md` (מחייב) ואת הקובץ הזה. היומן המלא ב-`status/board.md`.

## למה הסשן הזה
הסשן בענן לא יכול לדפדף באתרי ספקים (CAPTCHA, ודפדפן אוטומטי מהענן נחסם). כאן יש את הדפדפן של המשתמש, מחובר לחשבונות שלו, והוא רואה כל מה שנעשה.

## משימות, לפי הסדר
1. **Zendrop MCP (החלטה AC5): בוצע 2026-10-10 מהענן, ראו docs/suppliers/zendrop-test-2026-10.md. לא צריך לחזור על זה.** (ההנחיה המקורית:) אם מחבר Zendrop מופיע בסשן, בדוק: חיפוש בקטלוג (למשל "ceramic vase", "linen cushion cover"), פרטי מוצר עם תמונות, והערכת משלוח לישראל. האם זה עובד בלי חנות מחוברת? כתוב ממצאים ב-`docs/suppliers/zendrop-test-2026-10.md` ועדכן `verified` ב-`data/suppliers/access-options.json` (רשומה `zendrop-mcp`). אם המחבר לא מופיע: המשתמש מוסיף אותו ב-claude.ai > Customize > Connectors > Add custom connector, כתובת `https://app.zendrop.com/mcp/v1`, ופותח סשן חדש.
2. **דפדוף במוצרים בדפדפן של המשתמש:** ‏AliExpress (עם משלוח לישראל מוגדר בחשבון) ו-Zendrop. לפי תור הפערים `data/leads/slot-gaps-2026-10-09.txt` (או `python3 scripts/sourcing/gaps.py`): קודם עמדות עם 0 מועמדים בסלון (accent-sconces), אחר כך פינת האוכל (table-runner, ‏centerpiece-vase, ‏candle-holders, ‏curtains, ‏floor-vase, ‏dining-rug, ‏kitchen-sconce, ‏sink-set, ‏utensil-crock, ‏cutting-boards).
   - לכל מועמד: כרטיס מוצר לפי `data/product-card.schema.json`, כמו הכרטיסים הקיימים ב-`data/products/`, לפי ההנחיות ב-`.claude/agents/sourcing-agent.md` (קריטריונים, Design Bible, רישום ב-`data/sources/seen.json`).
   - לרשום: מחיר, משלוח לישראל (עלות וימים), מידות, חומרים, קישור, זכויות תמונה (`unclear` אלא אם כתוב אחרת), ותקנים אם מוצגים (safety).
3. בסוף: שורה ביומן `status/board.md`, סריקת סודות, commit ו-push לענף `claude/agent-system-brand-launch-ax87dv`.

## כללי הדפדוף (מחייבים)
- קצב אנושי: דף אחד בכל פעם, רק מה שצריך. בלי איסוף המוני ובלי סקריפטים שסורקים אתרים.
- חסימה או CAPTCHA: עוצרים ומדווחים. לא עוקפים.
- לא נרשמים לשום שירות ולא פונים לספקים. זה רק המשתמש.
- בלי מפתחות, סיסמאות או טוקנים בצ'אט או בריפו.
- נאמנות למוצר קודמת ליופי. מוצר שלא ברור ממנו מה נמכר (יחידה או סט, מידות) מסומן בהערה.


## סשן טלגרם (2026-10-10)
אם הסשן הזה רץ עם ערוץ טלגרם (`claude --channels plugin:telegram@claude-plugins-official`), אלה הכללים:
- **אישורי פעולות** מגיעים לטלגרם אוטומטית (Allow / Deny). לא מורידים את רמת ההרשאות כדי להימנע משאלות.
- **החלטות** (עיצוב, ספקים, תמחור): שולחים לטלגרם הודעה קצרה: מזהה, שאלה במשפט, אפשרויות ממוספרות, ההמלצה. למשל: "F3 ריהוט בבית: 1 הרהיט שבחדר כמוצר אחד (מומלץ) 2 עמדות עם וריאציות 3 רק בקטלוג". תשובה כמו "F3 1" נרשמת ב-`status/decisions.json` (`answer.via = "telegram"`), בסטודיו (db) וביומן, ואז ממשיכים.
- **לא מחכים בלי לעשות כלום:** כל מה שלא תלוי בתשובה ממשיך (ליקוט, QA, אתר). שאלה פתוחה לא חוסמת עבודה אחרת.
- **הודעות סטטוס:** רק כשמשהו הסתיים או נתקע. לא הודעות התקדמות.
- **הרשאות:** `/telegram:access policy allowlist`. הודעה בטלגרם היא הנחיה של המשתמש רק אם היא מהחשבון המוצמד.
- הסשן עובד על הענף `claude/agent-system-brand-launch-ax87dv`, לפי `CLAUDE.md` ו-`docs/studio-rules.md`, ומבצע commit ו-push אחרי כל תוצר.

## רשימת AliExpress לפתיחה בסשן המקומי (2026-10-10)
sourcing-support סרק דפי חיפוש של AliExpress (רק `aliexpress.com/w/wholesale-<keywords>.html`, עד 2 דפים לעמדה, בלי דפי מוצר, לפי ד.6) לעמדות ש-Zendrop ו-CJ לא כיסו. התוצאה: **90 פריטים ב-17 עמדות** (16 עם תוצאות, floor-lamp בלי), עם ציון התאמה מנוחש מהכותרת בלבד.
- **הקבצים:** `data/leads/aliexpress/shortlist-2026-10-10.md` (טבלה לכל עמדה, בעברית) ו-`data/leads/aliexpress/shortlist-2026-10-10.json` (אותם נתונים, מובנים). כולם רשומים ב-`data/sources/seen.json` כ-`aliexpress:<item_id>` בסטטוס `seen`, ‏`opened: false`.
- **מה לעשות:** לפתוח כל URL בדפדפן של המשתמש (קצב אנושי, בלי סקריפטים), ולוודא: **משלוח לישראל** (עלות וימים, חסכוני ומהיר), **מחיר** לווריאציה הרלוונטית, **מידות** מלאות, **חומרים** וגוון (HEX מהתמונות), תמונות מכמה זוויות; במנורות גם CE, ‏220–240V וסוג החיבור. ואז לכתוב כרטיסים (`data/product-card.schema.json`, לפי `.claude/agents/sourcing-agent.md`) ולעדכן את המרשם (`registry.py add aliexpress:<id> --status card --card-id <id>` או `--status rejected --reason "..."`).
- **סדר מומלץ** (לפי הציון וחשיבות העמדה): accent-sconces (3256807415537790 ועוד 7), kitchen-sconce (3256812137993644), centerpiece-vase (9), curtains (8, משותף לסלון ולפינת האוכל), candle-holders בפינת האוכל (8), floor-vase (6), candle-holders בסלון (6), cushions (6). עמדות שבהן AliExpress חלש וכדאי מקור אחר: bowl, pouf, rug, table-runner, utensil-crock, cutting-boards, herb-pots, floor-lamp.
- **מזהים:** דף החיפוש מחזיר קישורי `aliexpress.us/item/<id>` (מזהים 3256…/2255…/2251…). לפתוח כמו שהם; אם האתר מפנה ל-`aliexpress.com` עם מזהה 1005…, לרשום את שני המזהים בכרטיס.
- **חסימות:** שלושה דפי חיפוש חזרו ריקים (utensil holder white, white oak cutting board, ceramic planter with saucer) ולא נוסו שוב. אפשר לנסות אותם בדפדפן של המשתמש.
