# ריפו רזה וזרימת ענפים ל-`main`: הצעה

> **general-purpose, ‏2026-11-28. הצעה בלבד, 0 טוקנים.** הבריף: `briefs/repo-size-branches-2026-11-28.md` (FB30, FB31). קריאה בלבד: לא נערך שום קובץ מלבד זה, ולא הורצה פקודת git שמשנה משהו.
>
> **איך נמדד:**
> - העץ במעקב נמדד ב-`git ls-tree -r -l` ונבדק מול `git ls-files` + `stat` (אותה תוצאה). הגודל הדחוס של כל קובץ נמדד ב-`git cat-file --batch-check='%(objectsize:disk)'`.
> - המדידה נעשתה על הקומיט `fc8e1bb0`. העץ של `f1b14aa9` (הראש הנוכחי) זהה בגודל ובמספר הקבצים.
> - **מה האתר קורא** נמצא בשלושה מקורות:
>   - מעקב סטטי אחרי הקונפיגים שהסקריפטים של `npm run prepare:data` קוראים: `site/tools/tour/*.json`, `frames.json`, `route.json`, `arrival.json`, `site/tools/house/`, `site/tools/test-page/`, `site/tools/temp/`, `data/story/story.json`, `assets/manifest.json`, המניפסט של `wheel-studio` ו-`source-record.json` של צילומי הסטודיו. משם נמשכו המניפסטים שהם מפנים אליהם, ותיקיות שכלי קורא במלואן נלקחו שלמות.
>   - שמות קבצים שכתובים בקוד ובבדיקות עצמם (`site/**/*.ts`, `studio/*.py`).
>   - מה שדף הניהול קורא (`studio/build.py`).
> - **הבדיקה מול המציאות:**
>   - המעקב מכסה את כל 39 הקבצים ב-`living-room.pin.json` ואת כל 68 הקבצים ב-`living-room-phase2.pin.json`.
>   - כללי ה-sparse שבפרק 5 נבדקו ב-`git sparse-checkout check-rules` של git עצמו.
>   - הרשימה שבנספח א נבנית בפקודות git בלבד, ולא נכנס אליה אף קובץ שהבנייה צריכה.
> - **מגבלה:** זה ניתוח סטטי. השער האמיתי הוא ה-CI על checkout נקי (פרק 5): קובץ חסר עוצר את הבנייה בשמו. כך כבר נמצאו 10 קבצים שרק הבדיקות קוראות (`e2e/mock8.spec.ts`), והם נוספו ל"נשאר".

## 0. בשתי דקות
- **היום:** ‏**11.93GB במעקב, ב-42,106 קבצים.**
  - `assets/` הוא 10.71GB מזה. ‏PNG לבד הוא 9.34GB.
  - ה-`.git` המקומי שוקל 11GB (pack של 9.88GiB), ובו רק 70 הקומיטים מאז 2026-11-26 (השיבוט רדוד).
  - ב-GitHub יש גם את ההיסטוריה מ-2026-09-28 ועד אז, ולכן הריפו שם גדול יותר. המספר המדויק: `gh api repos/<owner>/<repo> --jq .size` (ב-KB).
- **ה-CI כמו שהוא היום לא יעבור:**
  - **דיסק:** checkout רגיל מוריד את כל הקבצים של הראש, כ-10.4GB דחוס, ופורש 11.9GB. זה כ-22GB, ולמכונה של GitHub יש 14GB.
  - **כלים:** גם עם דיסק, `prepare:data` ייעצר. שערי החדרים רצים ב-`python3.12` עם numpy, ‏OpenCV ו-Pillow, וההליכות מקודדות ב-ffmpeg. אף אחד מהם לא מותקן על `ubuntu-24.04` של GitHub.
  - **כנראה הוא עוד לא רץ אף פעם:** ב-`main` יש קובץ אחד, ועוד לא נפתח PR.
- **נשאר בגיט: ‏4.77GB** (39,657 קבצים, כ-3.9GB דחוס):
  - מה שהאתר והבדיקות קוראים;
  - מה שדף הניהול קורא;
  - הפריימים הסופיים;
  - מה שהמסמכים המחייבים מצטטים;
  - ‏`data/`, ‏QA והקוד.
- **יוצא מהמעקב: ‏7.15GB** (2,443 קבצים):
  - טייקים;
  - תיקיות עבודה;
  - npy;
  - גרסאות ישנות;
  - קליי.

  הקבצים נשארים על הדיסק כאן ובהיסטוריה, תחת תגית שמגינה עליהם. **שום דבר לא נמחק.**
- **היסטוריה:** בלי שכתוב ובלי force-push. ה-PR הראשון נכנס ב-**Squash**, ולכן ב-`main` יש רק העץ הרזה (כ-3.9GB). ההיסטוריה המלאה נשמרת בתגית `archive/pre-lean-2026-11-28`.
- **LFS:** לא עכשיו. ה-CI והסשנים מורידים את הסופיים בכל ריצה, כך שהמכסה החינמית (10GiB תעבורה בחודש) נגמרת מהר, ובגיט רגיל אין חיוב.
- **ה-CI אחרי השינוי:**
  - checkout חלקי של מה שהבנייה קוראת: הורדה של 2.5GB, או 4.2GB לפני ההוצאה מהמעקב;
  - Python ו-ffmpeg מותקנים בריצה;
  - מטמון לתמונות הספקים;
  - Lighthouse רץ רק על `main`.
- **ענפים:**
  - ענף לכל סבב מ-`main`;
  - רק המנהל מבצע קומיטים, עם נתיבים מפורשים;
  - PR כשהסבב מאושר והבדיקות ירוקות, ומיזוג ב-Squash.
- **מה הבעלים מפסיד:**
  - טייקים וביניים עתידיים לא נשמרים בריפו. מה ששווה לשמור נכנס לארכיון Release, בחינם;
  - Lighthouse כבר לא חוסם PR;
  - ההיסטוריה קומיט-קומיט נשארת בתגית ולא ב-`main`.
- **שתי שאלות לבעלים** בפרק 8.

## 1. היום: מה תופס את המקום

| תיקייה | גודל | קבצים |
| --- | ---: | ---: |
| `assets/` | 10.71GB | 18,318 |
| `data/` | 0.63GB | 18,061 |
| `qa/` | 0.48GB | 4,555 |
| `studio/` | 0.05GB | 116 |
| `site/` | 0.05GB | 596 |
| `docs/`, `status/`, `briefs/`, `scripts/`, `.claude/` ושורש | 0.01GB | 454 |

- **בתוך `assets/`:**
  - `renders/living-room` 2.95GB (מתוכם `phase2-2026-11-10` לבד 1.62GB);
  - `blockout/house` 1.25GB;
  - `renders/poses` 1.10GB;
  - `video/transitions` 1.04GB.
- **לפי סוג:**
  - PNG ‏9.34GB (4,524);
  - mp4 ‏0.65GB (73);
  - JPG ‏0.61GB;
  - JSON ‏0.54GB (19,564);
  - npy ‏0.22GB (15 קבצים של 25MB);
  - WebP ‏0.21GB;
  - AVIF ‏0.20GB.
- **הקובץ הגדול ביותר:** `assets/video/transitions/warm-modern/route-fb21/leg3/k3c2.earlyblend.mp4`, ‏55MB. GitHub מזהיר מ-50MiB וחוסם מ-100MiB.
- **הקצב:** ב-2026-11-26 עד 28 נוספו 0.96GB של תוכן חדש.
  - 0.57GB מזה לא היה נכנס לפי הכללים כאן. רובו, 0.50GB, טייקים של kling.
  - 0.39GB היה נכנס: פריימים סופיים ושכבות.

## 2. מה חייב להישאר בגיט

| סוג | גודל | קבצים | הערה |
| --- | ---: | ---: | --- |
| קוד, מסמכים וקונפיג (`site/`, `docs/`, `status/`, `studio/`, `scripts/`, `briefs/`, `.claude/`, `.github/`) | 0.11GB | 1,166 | כולל 0.08GB צילומי מסך ב-`studio/screens` וב-`site/screens` |
| `data/`: כרטיסים, מחירים, עמדות, מטמוני ספקים | 0.63GB | 18,061 | ‏0.13GB דחוס. הבנייה קוראת את `data/sources/cj` ואת `data/sources/aliexpress` (קווי משלוח) |
| נכסים שהאתר והבדיקות קוראים | 1.42GB | 7,278 | שכבות, צללים, אורות, פלטות, פריימי אמת ומפות עומק של 10 הפריימים בסיור; פריימי ה-WebP של חמש רגלי המסלול ושל ההגעה; ‏`wheel-studio`; צילומי הסטודיו; הבית של שלב 1; פריימי הסיפור ודף הבדיקה; קוד השערים. **הליבה**, לפי ה-pins והשערים, היא כ-0.83GB. השאר הם מקורות שהמניפסטים והרשומות מפנים אליהם |
| קבצים שרק הקוד או הבדיקות נוקבים בשמם | 0.06GB | 10 | `*-defaults-fb15.png`, ‏`*-defaults-fb16-finish.png` ו-`plate.png` של `e2e/mock8.spec.ts` |
| מה שרק דף הניהול קורא | 0.62GB | 226 | `studio/build.py`: כל רינדורי הסלון הנורדי (חוץ מ-`raw/` ו-`step-*`), ‏`framing/round2` וגיליונות ההשוואה |
| עותקי AVIF בתיקיות `final/` | 0.20GB | 6,105 | חלק מהתוצר הסופי (`formats: avif, webp` במניפסט). הבנייה מקודדת היום מה-WebP |
| מה שהמסמכים המחייבים והלוח מצטטים | 0.28GB | 69 | פריימי המבואה HDX, ‏HT ו-D0O, הדלת D0, ‏`all-round2.jpg` ועוד, מ-`docs/**`, `status/**`, ‏`CLAUDE.md` ו-`.claude/**` |
| רשומות בתוך `assets/` (json, ‏md, ‏py, פרומפטים) | 0.02GB | 1,819 | המקור של כל רינדור |
| QA: טקסט | 0.05GB | 2,415 | |
| QA: תמונות | 0.43GB | 2,051 | הראיות של הפסיקות הקיימות. חדשות נכנסות רק בכוונה (פרק 3) |
| **סך הכול** | **3.81GB** | **39,200** | ‏2.96GB דחוס |

- **מה הכללים שבנספח א משאירים בפועל: ‏4.77GB** (39,657 קבצים, ‏3.90GB דחוס).
  - **למה יותר מ-3.81:** הם שומרים את קובצי השורש של תיקיות החדרים שלמים. זה עוד 1.29GB של גרסאות קודמות לצד הסופיים.
  - **ומה הם מוציאים בכל זאת:** 84 מקורות גולמיים ותמונות קלט של ערימות שכבות מאושרות (0.32GB, למשל `fb13-2026-11-25/raw`, ‏`dining/.../raw`). הרשומות מפנות אליהם, אבל הבנייה לא קוראת אותם. הם נשארים בתגית.
  - **הבחירה:** כללים פשוטים שאפשר לשחזר בפקודות git, על פני רשימה מדויקת שדורשת כלי. דילול השורש של כל תיקייה נעשה בהמשך, תיקייה-תיקייה (פרק 7, צעד 8).

## 3. מה מפסיק להיות במעקב

### 3.1 הרשימה (נספח א בונה אותה בפקודות git)

| סוג | גודל | קבצים |
| --- | ---: | ---: |
| תיקיות עבודה בתוך התיקיות שנשארות: `raw/`, ‏`inputs/`, ‏`work-*/`, ‏`crops-*/`, ‏`step*/`, ‏`*before-after*/` | 2.31GB | 821 |
| גרסאות נורדיות ישנות (v7–v9) מחוץ לסלון, ו-`poses/nordic` v7/v8 | 2.13GB | 505 |
| קליי ומסגור (`assets/blockout`), חוץ מ-round2, גיליונות ההשוואה ומפות העומק `wm-*/*-depth.png` | 1.33GB | 639 |
| וידאו: טייקים וקידודים (mp4). הבנייה מקודדת מהפריימים הסופיים | 0.64GB | 63 |
| רינדורים אחרים שאיש לא קורא: גרסאות קודמות, בדיקות, editorial | 0.41GB | 181 |
| נתוני עבודה: npy, ‏npz, ‏exr, ‏blend | 0.28GB | 71 |
| צילומי מסך ב-`assets/qa/` | 0.05GB | 163 |
| **סך הכול** | **7.15GB** | **2,443** |

- **איך מוציאים:** ‏`git rm --cached` מוציא קבצים מהמעקב בלבד. הם נשארים על הדיסק של המכונה הזו, וכלל `.gitignore` (3.2) משאיר את `git status` נקי.
- **איפה הם:** בהיסטוריה, תחת התגית `archive/pre-lean-2026-11-28`.
- **החזרה של קובץ:** ‏`git restore --source=archive/pre-lean-2026-11-28 -- <path>`.
- **נקודות לבדיקה של master-designer לפני ההוצאה:**
  - `assets/renders/corridor/warm-modern/route-2026-11-27/` (59MB): המסדרון עדיין בעבודה. אם הוא לא נסגר עד ה-PR, משאירים אותו.
  - `assets/blockout/house/framing/wm-*/` (קליי של כל חדר): הרינדורים נועלים עליהם. הם נוצרים בקוד ב-0 טוקנים, והם בתגית.
  - `assets/renders/poses/nordic/` (1.09GB): אם תוכנית הבית הנורדי של FB23 משתמשת בהם שוב, משאירים אותם.

### 3.2 כללי `.gitignore` (טלאי, לא הוחל)
- **המדיניות:** מדיה תחת `assets/` ו-`qa/` לא נכנסת למעקב כברירת מחדל.
- **סופי נכנס בכוונה,** ב-`git add -f`, ונרשם ב-README או במניפסט של התיקייה שלו. סופי הוא מה שהאתר או דף הניהול קוראים, פריים שהבעלים אישר, או גיליון שפסיקת QA מצטטת.
- **קבצים שכבר במעקב לא מושפעים:** שינויים בהם נכנסים כרגיל.
- **נבדק ב-`git check-ignore`:**
  - שכבה חדשה, פריים סופי חדש וגיליון QA חדש נחסמים;
  - `manifest.json`, ‏README, ‏`site/**`, ‏`studio/**` ו-`data/**` לא.

```diff
--- a/.gitignore
+++ b/.gitignore
@@ -10,3 +10,30 @@
 assets/renders/transitions/test-*/**/interp60/
 assets/renders/transitions/test-*/**/*-registered.png
 assets/renders/transitions/test-*/selftest-*/*.png
+# Repo-lean (docs/proposals/repo-lean-branches-2026-11-28.md): work files stay in the scratchpad; only finals are tracked.
+# Numeric work data is never tracked
+*.npy
+*.npz
+*.exr
+*.blend
+*.blend1
+*.pkl
+# Media under assets/ and qa/ is not tracked by default. A final (what the site build or the admin page reads, a frame
+# the owner approved, a sheet a QA verdict cites) goes in on purpose with `git add -f <file>` and is named in its
+# folder's README or manifest. Files already tracked stay tracked, and their changes are committed as usual.
+assets/**/*.png
+assets/**/*.jpg
+assets/**/*.jpeg
+assets/**/*.webp
+assets/**/*.avif
+assets/**/*.gif
+assets/**/*.tif
+assets/**/*.tiff
+assets/**/*.mp4
+assets/**/*.mov
+assets/**/*.webm
+assets/**/*.log
+qa/**/*.png
+qa/**/*.jpg
+qa/**/*.jpeg
+qa/**/*.webp
```

- **מלכודת שנמנעה:** אין כלל `work/`. ‏`work` הוא גם שם של חדר: `assets/renders/work/` ו-`wheel-studio/warm-modern/work/`.
- **החלופה המינימלית,** אם הבעלים לא רוצה ברירת מחדל חוסמת: רק שש השורות של נתוני העבודה ו-`assets/**/*.mp4`. היא חוסמת את הסוגים שתופסים היום 0.9GB מתוך ה-7.15GB (ובשני הימים האחרונים את רוב מה שלא היה צריך להיכנס: טייקים של kling), אבל לא גרסאות קודמות ותיקיות עבודה, שהן רוב ה-7.15GB.

### 3.3 איפה הקבצים האלה חיים מעכשיו
- **ביניים וטייקים רגילים:** ב-scratchpad של הסוכן, כמו שכבר נקבע ("קובצי עבודה של סוכנים נשמרים ב-scratchpad"). ה-scratchpad לא שורד ניקוי או מכונה חדשה.
- **טייק או חלופה ששווה לשמור** (בתשלום, ואולי הבעלים יבחר בו אחר כך): לארכיון Release ב-GitHub.
  - Release אחד לסבב, `takes-<date>-<topic>`, עם tar עד 2GB לקובץ (`split -b 1900m` מעל זה).
  - שורה ב-`assets/archive/index.json` לכל קובץ: נתיב, ‏sha256 ושם הנכס ב-Release.
  - לפי GitHub, אין מגבלה על הגודל הכולל של Release או על התעבורה. כל קובץ צריך להיות קטן ממגבלת הקובץ של LFS בתוכנית, ‏2GB ב-Free וב-Pro.
  - העלאה ב-`gh release create` ‏/ `gh release upload`, ו-`gh` כבר מוגדר בסשנים.
- **Artifacts של Actions:** לא. תקופת השמירה שלהם מוגבלת, והם לא נועדו לארכיון.
- **var2:** שומר את התוצרים שלו, והמזהים רשומים ב-`assets/prompts/`. אבל אין התחייבות לזמן שמירה, אז לא סומכים עליו.

### 3.4 מה הבעלים מפסיד
- **הקבצים הקיימים:** כלום. הכול בהיסטוריה ובתגית, וגם על הדיסק כאן.
- **מעכשיו:**
  - טייק או ביניים שלא נכנסו לארכיון לא יחזרו. אם צריך אותם, מרנדרים מחדש בקרדיט.
  - בתצוגת הקבצים של GitHub, גרסאות ישנות נראות רק בתגית.
- **סשן חדש בענן** לא יקבל את הקבצים שהוצאו. כלי שמחפש קובץ כזה ייעצר בשמו, ומחזירים אותו בפקודה אחת.

## 4. היסטוריה

### 4.1 בלי שכתוב
**לא מוצע** `git filter-repo` או force-push לענף המשותף. אם מישהו יציע זאת, אלה הסיכונים:
- כל ה-SHA משתנים.
  - כל עותק, סשן וענף של סוכן נשבר וצריך שיבוט מחדש.
  - PR פתוח נשבר.
  - קומיטים שמוזכרים במסמכים וברשומות (למשל "recheck after c4b811c0" ב-`assets/manifest.json`, וביומן הלוח) מצביעים לשום מקום.
- force-push לענף שסוכנים עובדים עליו במקביל עלול למחוק עבודה שלא נמשכה.
- GitHub ממשיך להחזיק את האובייקטים הישנים בהפניות `refs/pull/*` ובמטמון שלו, עד בקשת תמיכה. החיסכון בצד שלו לא מובטח.
- אין דרך חזרה, אם לא שמרו עותק מלא לפני כן.

### 4.2 כמה הריפו ישקול
| מצב | `main` (דחוס) | הערה |
| --- | ---: | --- |
| PR ראשון שמעביר את כל ההיסטוריה ("Create a merge commit" או "Rebase and merge") | ‏10.6GB לפחות, ועוד ההיסטוריה שלפני 2026-11-26 | כל שיבוט של `main` מוריד את כולה, לתמיד |
| **Squash, אחרי ההוצאה מהמעקב (מוצע)** | **כ-3.9GB** (עץ 4.77GB) | ההיסטוריה המלאה בתגית ובענף הישן ב-GitHub |
| Squash, בלי ההוצאה מהמעקב | כ-10.4GB | |
| הגידול לסבב, לפי הכללים | כ-0.2–0.5GB | לפי היומיים האחרונים: כ-40% מהקצב של היום |

- **שיבוט רזה של `main`** הוא שיבוט עם `--depth` (שמושך ענף אחד), או `git clone --single-branch --branch main --no-tags`. בסשן ענן: `source_revision: main`.
- **הריפו ב-GitHub עצמו** יישאר מעל 10GB, בגלל הענף הישן, התגית והפניות ה-PR. GitHub ממליץ על פחות מ-1GB, ו"מאוד ממליץ" על פחות מ-5GB. זו המלצה ולא חסימה, ואין עליה חיוב.

### 4.3 Git LFS לסופיים גדולים: לא עכשיו
- **מה GitHub נותן** (מהתיעוד ומדף התמחור):
  - ‏Free ו-Pro: ‏10GiB אחסון ו-10GiB תעבורה בחודש;
  - ‏Team: ‏250GiB;
  - מעל המכסה: תשלום. בדף התמחור: 5 דולר לחודש לכל 50GB אחסון ו-50GB תעבורה;
  - קובץ LFS: עד 2GB ב-Free וב-Pro.
- **למה לא:**
  - כל ריצת CI וכל סשן חדש מורידים את הסופיים שהם פורשים. ב-CI זה כ-2.3GB לריצה (רשימת ה-sparse, אחרי ההוצאה), וסשן חדש מוריד כ-3.7GB. ארבע ריצות בחודש כבר עוברות את ה-10GiB.
  - צריך `git-lfs` בכל סשן. כאן הוא מותקן (3.4.1), אבל זה עוד צעד שאפשר לשכוח.
  - גיט רגיל ב-GitHub לא עולה כסף.
- **מתי לחזור לשאלה:**
  - כש-pack של `main` עובר כ-5GB;
  - או כשסופי בודד עובר 50MB באופן קבוע.

  עד אז, וידאו סופי גדול הולך ל-Release (3.3).

## 5. CI: בדיקת PR רזה ואמינה

### 5.1 מה מתוקן
| בעיה | התיקון |
| --- | --- |
| **checkout מלא, כ-22GB על 14GB** | checkout חלקי (sparse + `blob:none`, ש-`actions/checkout` מוסיף לבד כשיש `sparse-checkout`; נבדק בקוד המקור). רק מה שהבנייה והבדיקות קוראות: 5.05GB עץ והורדה של 4.18GB היום, 3.24GB והורדה של 2.50GB אחרי ההוצאה |
| **אין numpy, ‏OpenCV, ‏Pillow ו-ffmpeg** | `setup-python` 3.12 ו-pip בגרסאות של המכונה כאן: numpy 2.5.5, ‏opencv-python-headless 5.1.0.95, ‏pillow 13.0.0. ‏ffmpeg מ-apt |
| **תמונות הספקים יורדות מהרשת בכל ריצה** | `actions/cache` על `site/.cache/supplier-images` |
| **אין טריגר ידני** | `workflow_dispatch` |
| **מסנן נתיבים חלקי** | נוספו `briefs/**` (`s22` סורק אותם), ‏`docs/ops/**` (`s16`), ‏`status/decisions.json`, ‏`qa/reports/ged-register-*` ונכסי הסיור (`assets/renders/**`, ‏`assets/video/transitions/**`, ‏`assets/blockout/house/framing/**`). PR של מסמכים בלבד, כמו זה, לא מריץ CI |
| **Lighthouse על כל PR** (האיטי ביותר, והרועש ביותר על מכונה משותפת) | רק ב-push ל-`main` ובהרצה ידנית |

- **מה רץ על PR:** ‏`prepare:data`, ‏typecheck, ‏lint, ‏format, ‏vitest, בדיקת הקונפיג, ‏build עם התקציב, הזכויות וההבטחות, ‏Artifact preview, ‏e2e ו-a11y.
  - ה-Artifact נשאר על PR כי ככה הבעלים רואה את האתר, והבדיקה דטרמיניסטית.
  - e2e לא תלוי ב-`dist-artifact`.
- **מה רץ על `main` ובהרצה ידנית:** כל זה, ועוד Lighthouse.
- **הערכת זמן:** 20–30 דקות לריצה, ונמדוד בריצה הראשונה. ה-timeout עולה מ-30 ל-40.
  - ב-Free יש 2,000 דקות בחודש לריפו פרטי. בערך שתי ריצות לסבב (PR ו-`main`), כך שיש מרווח גדול.
- **הטלאי שומר על שתי הבדיקות שקוראות את הקובץ:**
  - `s16` דורש את השורה `npm run check:config -w @hd/api`;
  - `s17` אוסר `npx` בלי `--no-install`.

  הטלאי נבדק ב-`git apply --check` ונקרא כ-YAML תקין.
- **אם בדיקה סטטוס-חובה תוגדר ב-branch protection:** PR שהמסנן מדלג עליו ייחסם. לכן לא מגדירים את `site-ci` כחובה, או שמסירים את מסנן הנתיבים מ-`pull_request`.
- **מצב ה-sparse:** non-cone עובד ב-git של היום, אבל git מסמן אותו כפחות מועדף. אחרי ההוצאה מהמעקב אפשר לעבור ל-cone עם אותן תיקיות, בלי שורות `!`.
- **גרסאות:** ‏`actions/checkout@v4` נשאר (הגרסה האחרונה היא v7). העלאת גרסה היא החלטה נפרדת.

### 5.2 הטלאי (לא הוחל)
```diff
--- a/.github/workflows/site-ci.yml
+++ b/.github/workflows/site-ci.yml
@@ -1,12 +1,40 @@
 # Site CI: quality gates only. No deploy (deploys need the Cloudflare account; see docs/architecture.md, "סביבות").
+# Lean (docs/proposals/repo-lean-branches-2026-11-28.md): a sparse, partial checkout of what the steps read; Lighthouse
+# (the slowest step, and the noisiest on a shared runner) runs on main and by hand, not on every PR.
 name: site-ci
 
 on:
   pull_request:
-    paths: ['site/**', 'data/**', 'docs/house-plan.json', 'assets/manifest.json', '.github/workflows/site-ci.yml']
+    branches: [main]
+    paths:
+      - 'site/**'
+      - 'data/**'
+      - 'briefs/**'
+      - 'docs/house-plan.json'
+      - 'docs/ops/**'
+      - 'status/decisions.json'
+      - 'qa/reports/ged-register-*'
+      - 'assets/manifest.json'
+      - 'assets/renders/**'
+      - 'assets/video/transitions/**'
+      - 'assets/blockout/house/framing/**'
+      - '.github/workflows/site-ci.yml'
   push:
     branches: [main]
-    paths: ['site/**', 'data/**', 'docs/house-plan.json', 'assets/manifest.json', '.github/workflows/site-ci.yml']
+    paths:
+      - 'site/**'
+      - 'data/**'
+      - 'briefs/**'
+      - 'docs/house-plan.json'
+      - 'docs/ops/**'
+      - 'status/decisions.json'
+      - 'qa/reports/ged-register-*'
+      - 'assets/manifest.json'
+      - 'assets/renders/**'
+      - 'assets/video/transitions/**'
+      - 'assets/blockout/house/framing/**'
+      - '.github/workflows/site-ci.yml'
+  workflow_dispatch:
 
 permissions:
   contents: read
@@ -22,14 +50,68 @@
 jobs:
   checks:
     runs-on: ubuntu-24.04
-    timeout-minutes: 30
+    timeout-minutes: 40
     steps:
+      # Only what the build and the tests read (a missing file fails the build by name: add its folder here).
+      # A sparse checkout also clones without blobs (filter blob:none): only the files below are downloaded.
       - uses: actions/checkout@v4
+        with:
+          sparse-checkout-cone-mode: false
+          sparse-checkout: |
+            /site/
+            /data/
+            /.github/
+            /briefs/
+            /docs/house-plan.json
+            /docs/ops/
+            /status/decisions.json
+            /qa/reports/ged-register-*
+            /qa/reports/2026-11-02-v7-g1/data/
+            /assets/manifest.json
+            /assets/prompts/
+            /assets/renders/tools/
+            /assets/renders/wheel-studio/
+            /assets/renders/outside/
+            /assets/renders/products/
+            /assets/renders/living-room/warm-modern/
+            /assets/renders/*/warm-modern/stage1-*/
+            /assets/renders/bath/warm-modern/b1-*/
+            /assets/renders/master/warm-modern/mb1-*/
+            /assets/renders/hall/warm-modern/hall-products-2026-11-19/
+            /assets/renders/living-room/nordic/v7/m0-v7-r2-graded-v3.png
+            /assets/renders/living-room/nordic/v9/m0-1-2-shell-seedream-fix.png
+            /assets/renders/living-room/nordic/styled-preview-r2/styled-preview.png
+            /assets/renders/hall/nordic/v7/h0-v7-r2-graded-v3.png
+            /assets/renders/kitchen-dining/nordic/v7/d1-v7-graded-v3.png
+            /assets/renders/editorial-phase-b-2026-11-06/*.png
+            /assets/renders/house-nordic-*/refs/
+            /assets/renders/transitions/test-2026-11-02/p-d/frames/manifest.json
+            /assets/blockout/house/framing/wm-*/*-depth.png
+            /assets/video/transitions/warm-modern/**/final/
+            !*.npy
+            !*.mp4
+            !*.exr
+            !*.blend
       - uses: actions/setup-node@v4
         with:
           node-version: 22.12.0
           cache: npm
           cache-dependency-path: site/package-lock.json
+      # the room gates (tools/tour/gate_*.py, python3.12) and the walks' encoder (make-route, make-arrival: ffmpeg) are
+      # not on the runner image; the versions are the studio machine's
+      - uses: actions/setup-python@v5
+        with:
+          python-version: '3.12'
+      - name: Python modules of the room gates
+        run: python3.12 -m pip install --disable-pip-version-check numpy==2.5.5 opencv-python-headless==5.1.0.95 pillow==13.0.0
+      - name: ffmpeg
+        run: sudo apt-get update -q && sudo apt-get install -y -q --no-install-recommends ffmpeg
+      # the build downloads each supplier picture once; the cache keeps them between runs (fewer downloads, fewer flaky hosts)
+      - uses: actions/cache@v4
+        with:
+          path: site/.cache/supplier-images
+          key: supplier-images-${{ hashFiles('data/products/**/*.json') }}
+          restore-keys: supplier-images-
       - run: npm ci
       # S14, QA ת32: the generated data (.generated: the catalogs, the scene, the house, the supplier images' index) is
       # what the typecheck reads (@generated imports); on a clean checkout it does not exist until this step makes it
@@ -66,7 +148,8 @@
         run: npm run e2e
       - name: Accessibility (axe, zero violations, light and dark)
         run: npm run a11y
-      - name: Lighthouse mobile (a11y 100, performance >= 90)
+      - name: Lighthouse mobile (a11y 100, performance >= 90) (main and by hand only)
+        if: github.event_name != 'pull_request'
         run: |
           npm run preview > preview.log 2>&1 &
           for i in $(seq 1 120); do curl -sf http://127.0.0.1:8788/api/health > /dev/null && break; sleep 1; done
```

- **כשמוסיפים חדר, רגל או תיקיית סופיים חדשה לסיור,** מוסיפים שורה לרשימת ה-sparse. אם שוכחים, ה-CI נעצר בשם הקובץ החסר, וזה תיקון של שורה אחת.

## 6. זרימת הענפים

### 6.1 ענף לכל סבב
- **הענף:** בין שתי נקודות אישור של הבעלים, נפתח ענף אחד מ-`main`, למשל `claude/round-2026-11-29-wheels-1`.
- **בסוף הסבב:**
  - הבעלים מאשר, וההחלטה נרשמת ב-`docs/studio-rules.md` (FBxx);
  - נפתח PR ל-`main`, שבגוף שלו האישור, דוחות ה-QA והשינוי בגודל;
  - ה-CI ירוק;
  - **מיזוג ב-"Squash and merge".** כל סבב הוא קומיט אחד ב-`main`, ו-`main` הוא רצף נקודות האישור.
- **הרווח מה-Squash:** גרסאות ביניים שנכנסו לענף במהלך הסבב לא נכנסות להיסטוריה של `main`. הן נשארות בהפניות ה-PR ב-GitHub.
- **אחרי המיזוג:**
  - `git fetch origin main && git switch -c claude/round-<date>-<topic> origin/main`;
  - העץ זהה, ולכן המעבר מיידי, ושינויים שעוד לא נכנסו לקומיט עוברים איתו;
  - מוחקים את ענף הסבב שמוזג.
- **בין פתיחת ה-PR למיזוג אין קומיטים חדשים.** אחרת הם נשארים בענף הישן, ומעבירים אותם ב-`git cherry-pick`.
  - **לא ממזגים את `origin/main` לענף ישן אחרי Squash.** הבסיס המשותף ישן, ויוצאות התנגשויות add/add על כל קובץ שהשתנה.

### 6.2 סוכנים במקביל בתוך ענף סבב אחד
**עץ עבודה אחד, בלי worktree לכל סוכן.** כל worktree הוא עוד checkout מלא: 4.8GB אחרי ההוצאה, 11.9GB היום.
- **כל סוכן כותב רק לתיקיות שהבריף שלו נוקב בהן.** קובצי העבודה שלו נשמרים ב-scratchpad, בתת-תיקייה משלו.
- **רק המנהל מריץ פקודות git שכותבות** (add, ‏commit, ‏push):
  - אחרי כל מסירה של סוכן, עם נתיבים מפורשים: `git add -- <paths>`, ואז `git commit -m "…" -- <paths>`. כך עבודה חצי-גמורה של סוכן אחר לא נכנסת.
  - אף פעם לא `git add -A` ולא `commit -a`.
  - סופי נכנס ב-`git add -f`.
  - כך גם אין התנגשות על `.git/index.lock`.
- **push אחרי כל קומיט** (`git push origin HEAD`): העותק ב-GitHub הוא העמיד, והמכונה לא.
- **בנייה אחת בכל פעם:** `site/.generated` ו-`site/web/public/media` משותפים.
  - `flock <scratchpad>/site-build.lock npm run build`, וכך גם `prepare:data`, ‏`e2e` ו-`tour`.
- **הלוח, החוקים וה-digest נכתבים רק בידי המנהל.** הסוכנים מדווחים במסירה.
- **עד 2 סוכנים כבדים במקביל** (EFF1).

### 6.3 בסוף כל סבב, לפני ה-PR
1. `git status --short --ignored -- assets qa | grep '^!!'`: האם יש סופי שעוד לא נכנס? אם כן, `git add -f`.
2. מה הסבב מוסיף: `git diff --name-only --diff-filter=AM origin/main...HEAD -- assets qa | xargs -r stat -c '%s %n' | sort -n | tail -20`. קובץ מעל 50MB הולך ל-Release.
3. `git push`, ‏PR, ‏CI ירוק, אישור, Squash.

### 6.4 ה-PR הראשון: מהענף הנוכחי ל-`main`
- **הנחת הבריף:** "PR יעבור fast-forward". ב-GitHub אין כפתור fast-forward:
  - "Create a merge commit" מכניס את כל ההיסטוריה ל-`main`;
  - "Rebase and merge" יוצר קומיטים חדשים עם אותו תוכן כבד.
- **לכן Squash.** מה שהוא עולה:
  - ב-`main` אין היסטוריה קומיט-קומיט. היא בתגית ובענף הישן;
  - הענף הנוכחי לא ממשיך אחרי המיזוג (6.1);
  - ייתכן ש-GitHub לא יצליח למזג PR של 39 אלף קבצים בממשק (תוכנית חלופית בצעד 6 בפרק 7).
- **הסדר:** בפרק 7.

## 7. הצעדים הראשונים (אחרי אישור הבעלים)
1. **רושמים את ההחלטה** ב-`docs/studio-rules.md` ובתקציר. מעדכנים את `CLAUDE.md` ואת `.claude/agents/render-agent.md`, ‏`motion-agent.md` ו-`qa-agent.md` בשורה אחת: "סופי נכנס ב-`git add -f`; קובצי עבודה ב-scratchpad". השינוי ב-`CLAUDE.md` טעון אישור, וזו שאלה 1.
2. **תגית שמגינה על כל ההיסטוריה,** על הראש הנוכחי:
   `git tag -a archive/pre-lean-2026-11-28 -m "Full history before the lean main (repo-lean proposal)" && git push origin archive/pre-lean-2026-11-28`
   - בודקים: `git ls-remote --tags origin archive/pre-lean-2026-11-28`.
3. **קומיט: ‏`.gitignore` וה-CI,** משני הטלאים שבפרקים 3.2 ו-5.2, ב-`git apply`.
4. **קומיט: ההוצאה מהמעקב.**
   - כשאין סוכן באמצע כתיבה, ואחרי ש-master-designer עבר על 3.1.
   - `bash <script> <scratchpad>/lean` לפי נספח א, ואז `git --literal-pathspecs rm -r --cached --quiet --pathspec-from-file=<scratchpad>/lean/untrack.txt`.
   - קומיט: "Untrack non-final assets (kept on disk; history in archive/pre-lean-2026-11-28)". אחריו `git status --short` צריך להיות נקי.
   - **בדיקה אופציונלית לפני ה-PR:** שיבוט חלקי ל-scratchpad (`git clone --filter=blob:none --no-checkout --depth 1 --branch <branch> …`, ואז `git sparse-checkout set --no-cone --stdin` עם רשימת 5.2, ואז `git checkout`), ובו `npm ci && npm run prepare:data && npm test`. הוא מוריד 2.5GB ותופס 3.2GB. יש כאן 36GB פנויים.
5. **כשהסבב הנוכחי מאושר** (צילומי הסטודיו, גלגלים סבב 1, ‏MOCK12; בלי "WIP" בראש): push, ‏PR ל-`main`, וריצת ה-CI הראשונה. אם משהו חסר, מתקנים ומריצים שוב.
6. **Squash and merge.**
   - **אם הממשק נכשל:** יוצרים את קומיט ה-Squash בלי לגעת בעץ העבודה, `git commit-tree HEAD^{tree} -p origin/main -m "Studio state at <date>"`, דוחפים אותו לענף חדש (`git push origin <sha>:refs/heads/claude/lean-main`), ופותחים ממנו PR.
   - ה-push קטן: כל הקבצים כבר ב-GitHub.
7. **מעבר לענף הסבב הבא מ-`main`** (6.1). הענף הישן הופך לקריאה בלבד, ונמחק מ-GitHub רק אחרי שהתגית נבדקה. סשנים חדשים נפתחים מ-`main`.
8. **בהמשך, לא חוסם:** דילול השורש של תיקיות החדרים (1.29GB של גרסאות קודמות). render-agent עובר תיקייה אחרי תיקייה בסוף כל חדר, ומשאיר מה שהמניפסט משתמש בו ומה שה-README מסמן כסופי.
   - **ל-`status/backlog-low.md`:**
     - דף הניהול קורא 0.62GB של רינדורים נורדיים ישנים. אפשר שיקרא רק את המאושרים;
     - `data/sources/aliexpress/queries` ו-`data/leads/aliexpress/scale-2026-10` (0.30GB, ‏0.06GB דחוס) לא נקראים בבנייה.

## 8. שאלות לבעלים
1. **מאשרים את ההוצאה מהמעקב?** 7.15GB של טייקים, ביניים וגרסאות ישנות יוצאים מהמעקב. הם נשארים בהיסטוריה תחת תגית ועל הדיסק. מעכשיו מדיה נכנסת רק בכוונה, וה-CI הרזה נכנס. **ברירת מחדל: כן.**
2. **ה-PR הראשון ב-Squash,** כך ש-`main` רזה (כ-3.9GB) וההיסטוריה המלאה נשמרת בתגית, ולא העברה של כל ההיסטוריה (10GB ומעלה) ל-`main`? **ברירת מחדל: Squash.**

## נספח א: בניית רשימת ההוצאה (פקודות git לקריאה בלבד)
- **איך מריצים:** משורש הריפו, עם תיקיית פלט ב-scratchpad.
- **מה יוצא:** כאן הסקריפט נתן 2,443 קבצים, 7.15GB.
- **הכלל:**
  - כל מדיה תחת `assets/` שנמצאת מחוץ לתיקיות שהבנייה, הבדיקות ודף הניהול קוראות;
  - וידאו ונתוני עבודה בכל מקום, חוץ מ-`final/`;
  - תיקיות עבודה בתוך התיקיות שנשארות.
- **מה לא נכנס לרשימה:** מה שהמסמכים מצטטים, וארבעה קבצים שהבנייה קוראת מתוך תיקיות עבודה.

```bash
#!/usr/bin/env bash
# Builds the list of tracked files to untrack (read-only: git ls-files and grep). Usage: untrack-list.sh OUTDIR
set -euo pipefail
out=${1:?outdir}
MEDIA='\.(png|jpe?g|webp|avif|gif|tiff?|mp4|mov|webm|npy|npz|exr|blend|log)$'
# what the binding docs and the board cite stays (not this proposal: it names files as examples)
grep -rhoE --exclude=repo-lean-branches-2026-11-28.md 'assets/[A-Za-z0-9_./-]+\.(png|jpe?g|webp|avif|mp4)' docs status CLAUDE.md .claude \
  | sort -u > "$out/cited.txt"
# files the build reads inside work folders (the phase 2 rug pass, the studio pilot's throw)
cat > "$out/exceptions.txt" <<'X'
assets/renders/living-room/warm-modern/phase2-2026-11-10/inputs/fb12s1-input.png
assets/renders/living-room/warm-modern/phase2-2026-11-10/raw/fb12s1-rug-nano.jpg
assets/renders/living-room/warm-modern/phase2-2026-11-10/raw/fb12s1-seedream.png
assets/renders/products/img1-pilot-2026-11-12/raw/p1-throw-raw.jpg
X
KEEP=(
  ':(exclude,glob)assets/manifest.json' ':(exclude,glob)assets/prompts/**' ':(exclude,glob)assets/brand/**'
  ':(exclude,glob)assets/renders/tools/**' ':(exclude,glob)assets/renders/wheel-studio/**' ':(exclude,glob)assets/renders/outside/**'
  ':(exclude,glob)assets/renders/products/**' ':(exclude,glob)assets/renders/living-room/warm-modern/**'
  ':(exclude,glob)assets/renders/*/warm-modern/stage1-*/**' ':(exclude,glob)assets/renders/bath/warm-modern/b1-*/**'
  ':(exclude,glob)assets/renders/master/warm-modern/mb1-*/**' ':(exclude,glob)assets/renders/hall/warm-modern/hall-products-2026-11-19/**'
  ':(exclude,glob)assets/renders/living-room/nordic/**' ':(exclude,glob)assets/renders/editorial-phase-b-2026-11-06/*.png'
  ':(exclude,glob)assets/renders/house-nordic-*/refs/**' ':(exclude)assets/renders/hall/nordic/v7/h0-v7-r2-graded-v3.png'
  ':(exclude)assets/renders/kitchen-dining/nordic/v7/d1-v7-graded-v3.png'
  ':(exclude)assets/renders/transitions/test-2026-11-02/p-d/frames/manifest.json'
  ':(exclude,glob)assets/blockout/house/framing/wm-*/*-depth.png' ':(exclude,glob)assets/blockout/house/framing/round2/**'
  ':(exclude,glob)assets/blockout/house/framing/*-compare.jpg' ':(exclude,glob)assets/video/**/final/**'
)
{
  # 1. outside the folders the build, the tests and the admin page read
  git ls-files -- ':(glob)assets/**' "${KEEP[@]}" | grep -E "$MEDIA" || true
  # 2. work data and video, anywhere but a final folder
  git ls-files -- ':(glob)assets/**/*.mp4' ':(glob)assets/**/*.mov' ':(glob)assets/**/*.npy' ':(glob)assets/**/*.npz' \
    ':(glob)assets/**/*.exr' ':(glob)assets/**/*.blend' ':(glob)assets/**/*.log' ':(exclude,glob)assets/video/**/final/**'
  # 3. work subfolders inside the kept folders (not the work ROOM: assets/renders/work/, wheel-studio/*/work/)
  git ls-files -- ':(glob)assets/renders/**/raw/**' ':(glob)assets/renders/**/inputs/**' ':(glob)assets/renders/**/concepts/**' \
    ':(glob)assets/renders/**/crops-*/**' ':(glob)assets/renders/**/work-*/**' ':(glob)assets/renders/**/step*/**' \
    ':(glob)assets/renders/**/*before-after*/**' ':(glob)assets/renders/living-room/warm-modern/phase2-2026-11-10/work/**' \
    ':(exclude,glob)assets/renders/**/work-fb12s*/**' ':(exclude,glob)assets/renders/wheel-studio/**' \
    ':(exclude,glob)assets/renders/living-room/nordic/**' | grep -E "$MEDIA" || true
} | sort -u | grep -vxF -f "$out/cited.txt" | grep -vxF -f "$out/exceptions.txt" > "$out/untrack.txt"
wc -l < "$out/untrack.txt"
```

## נספח ב: ההוצאה לפי תיקייה (לבדיקה של master-designer)

| תיקייה | גודל | קבצים |
| --- | ---: | ---: |
| `assets/renders/living-room` (בעיקר `phase2-2026-11-10/work-*`, ‏`crops-*` ו-npy; ‏`pilot-phase1/raw`; ‏`fb13/raw` ו-`concepts`) | 1.20GB | 435 |
| `assets/blockout/house` (סבבי המסגור 3–5, ‏`warm-modern-r*`, ‏`wm-door/entrance/hall`, קליי `wm-*`) | 1.19GB | 561 |
| `assets/renders/poses` (נורדי v7/v8) | 1.09GB | 266 |
| `assets/video/transitions` (טייקים וקידודים של `route-fb21`, ‏`arrival-*`, ‏`clip*`) | 0.65GB | 87 |
| `assets/renders/master` (‏`editorial-2026-11-07`, נורדי v7, ‏`raw/` ו-`inputs/`) | 0.51GB | 195 |
| `assets/renders/bath` (נורדי v7, ‏`raw/` ו-`inputs/`) | 0.45GB | 108 |
| `assets/renders/hall` (‏`hall-2026-11-17` ו-`11-18`, ‏`door-*`, נורדי; חוץ מהפריימים המצוטטים) | 0.29GB | 82 |
| `assets/renders/boy`, ‏`girl`, ‏`dining`, ‏`work` (‏`raw/` ו-`inputs/`, נורדי) | 0.91GB | 201 |
| `assets/blockout/living-room` | 0.18GB | 88 |
| `assets/renders/kitchen-dining` (נורדי) | 0.18GB | 42 |
| `assets/renders/editorial-phase-b-2026-11-06` (`raw/` ו-before-after; חוץ מ-7 המצוטטים) | 0.14GB | 88 |
| `assets/renders/corridor` (נורדי, ‏`route-2026-11-27`) | 0.11GB | 36 |
| שאר התיקיות (‏`products/*/crops-100`, ‏`bases`, ‏`assets/qa`, ‏`test-2026-09-29`, ‏`animatic` ועוד) | 0.25GB | 254 |
| **סך הכול** | **7.15GB** | **2,443** |
