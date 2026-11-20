# מדריך: מפתחות AliExpress ו-CJ לליקוט (2026-11-20)

המפתחות נשמרים רק בהגדרות הסביבה של Claude, ואף פעם לא בצ'אט, בקבצים או בפקודות. הסקריפטים קוראים אותם ממשתני הסביבה ולא מדפיסים אותם.

## א. AliExpress (‏Open Platform, אפליקציית Drop Shipping)
1. נכנסים ל-https://openservice.aliexpress.com ומתחברים עם חשבון ה-AliExpress.
2. **אם כבר יש אפליקציה, מדלגים לשלב 3.** בסביבה "Alìexpress àpi" המפתחות כבר מוגדרים, אז כנראה שיש.
   - **אם אין אפליקציה:** נרשמים כמפתחים (Register / Become a developer). אחר כך App Console > Create App, ובוחרים את הקטגוריה **Drop Shipping** (AliExpress-dropship).
   - **ה-Callback URL:** ‏`https://127.0.0.1/callback`.
3. ב-App Console > App Management > האפליקציה > **Advanced Information** מעתיקים את ה-**App Key** ואת ה-**App Secret**.
4. **מומלץ:** בקונסול לוחצים **Apply Online**, כדי להעביר את האפליקציה מ-Test לייצור. ב-Test הטוקן מחזיק יום אחד, ובייצור 30 יום.

## ב. CJdropshipping
1. נכנסים ל-https://www.cjdropshipping.com ונרשמים או מתחברים. החשבון חינם.
2. בתפריט השמאלי: **Apps** > **Install App**. בחנות, בקטגוריה **Others**, מתקינים את **API**. אם כבר יש וי ירוק, מדלגים.
3. פותחים https://www.cjdropshipping.com/my.html#/authorize/API, ובלשונית **API** לוחצים **Add API**.
4. בחלון: ב-**API Key Name** כותבים שם כלשהו, למשל studio. ב-**Type** בוחרים **API Key** (לא MCP Token), ולוחצים **Confirm**.
5. ברשימה, בשורה שה-Type שלה API Key, לוחצים על אייקון ההעתקה בעמודה **API Key & MCP Token**. המפתח נראה כמו `CJ…@api@…`.
- **תוקף וקצב:** הטוקן תקף 180 יום. בחשבון חינמי מותרת קריאה אחת בשנייה.
- **המקור:** https://developers.cjdropshipping.com/en/api/start/apikey.html

## ג. איפה שמים את המפתחות ב-Claude
1. בשורת הכותרת של הסשן פותחים את תפריט הסביבה ("הקמת אתר לפרוייקט דרופשיפינג לבית") ולוחצים **Edit**.
2. ב-**Environment variables** מוסיפים שלוש שורות, כל אחת בצורה NAME=value:
   - `AE_DS_APP_KEY=`, ואחריו ה-App Key;
   - `AE_DS_APP_SECRET=`, ואחריו ה-App Secret;
   - `CJ_API_KEY=`, ואחריו מפתח ה-CJ.
3. שומרים, וכותבים בצ'אט "שמרתי", בלי המפתחות. משתני סביבה נטענים כשסשן מתחיל. אם המנהל לא רואה אותם, פותחים סשן חדש באותה סביבה וכותבים "נמשיך". כל המצב שמור בלוח הסטטוס.

## ד. ההרשאה של AliExpress (פעם אחת, אחרי שהמפתחות נשמרו)
1. המנהל מריץ `python3 scripts/ae/auth.py url` ושולח קישור.
2. פותחים את הקישור, מתחברים עם **חשבון הקונה** של AliExpress ולוחצים Authorize.
3. הדפדפן עובר לכתובת שמתחילה ב-`https://127.0.0.1/callback?code=`. **הדף לא ייטען, וזה בסדר.**
4. מעתיקים את כל הכתובת ומדביקים בצ'אט (חוק ח.3). זה קוד חד-פעמי לכמה דקות, לא מפתח. המנהל מחליף אותו מיד בטוקן, שנשמר מחוץ לריפו.

## אם מפתח הודבק בטעות בצ'אט
מוחקים אותו באתר ויוצרים חדש: ב-CJ מוחקים את השורה ויוצרים API חדש, וב-AliExpress מחדשים את ה-App Secret בקונסול.
