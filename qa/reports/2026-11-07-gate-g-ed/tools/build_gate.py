"""qa-agent, 2026-11-07: writes docs/ops/quality-gate-g-ed-2026-11-07.json (the G-ED gate for story frames).
The Hebrew document docs/ops/quality-gate-g-ed-2026-11-07.md carries the same ids, thresholds and mapping.
Reads (read only) the guardrail measurements in ../data/. Usage: python3.12 -I build_gate.py
"""
import json
import os

ROOT = "/home/user/homedesign-app"
HERE = os.path.join(ROOT, "qa/reports/2026-11-07-gate-g-ed")
RAW = json.load(open(os.path.join(HERE, "data/guardrails-raw.json")))
FIN = json.load(open(os.path.join(HERE, "data/guardrails-finished.json")))


def c(id_, name, measures, method, tool, threshold, source, binding):
    return dict(id=id_, name=name, measures=measures, method=method, tool=tool, threshold=threshold, source=source, binding=binding)


criteria = [
    c("G-ED.1", "טבלת כיסוי: אילו מוצרים בפריים",
      "כל מוצר נראה בפריים, עם מזהה הכרטיס; מוצרי הכוכב של הסגנון (creative review §3.7 והבריף של הפריים); אילו מוצרים יקבלו נקודת \"קנה את המראה\"; הרהיטים הקבועים הם מוצרים אם מוכרים אותם",
      "מעבר על הפריים ב-100% באריחים, מול לוח המוצרים ורשימת הכוכבים בבריף. כל פריט שנראה כמו מוצר שאנחנו מוכרים נרשם, גם אם הוא גנרי",
      "חיתוכים ב-100% (qa/reports/<date>-<scope>/overlays/); טבלה ב-JSON (frames.<id>.rows)",
      "כל מוצר נראה מזוהה בכרטיס או מסומן \"גנרי\"; כל מוצר כוכב של הפריים נוכח, או שהבריף קבע במפורש שהוא בפריים אחר",
      "CR9 (מאומץ 2026-11-07); docs/creative-review-2026-11-06.md §2, §3.7; CLAUDE.md", "מחייב"),
    c("G-ED.2", "נאמנות: צללית ומספר חלקים",
      "צללית, ומספר החלקים שאפשר לספור: טבעות, קומות, רגליים, ידיות, פריטים בסט, גדילים, שורות מוטיב",
      "החיתוך מהפריים ליד חיתוך תמונת הספק של המק\"ט בחדר, באותו גודל. ספירה ידנית בהגדלה ×3–×4",
      "חיתוך ×3–×4 (NEAREST); חיתוכי הספק (מבחר המוצרים, לא נשמרים בריפו)",
      "אותה צללית. ספירה זהה בטבעות, קומות, רגליים, ידיות ופריטים בסט. הצעה: גדילים ופרנזים ±1 לכל 10, כשהספירה בתמונת הספק ברורה",
      "CLAUDE.md (\"נאמנות למוצר קודמת ליופי\"); CR9; creative review §2 (\"צללית\"); בריף ED2 (\"number of pieces\")", "מעורב"),
    c("G-ED.3", "נאמנות: צבע, חומר ודוגמה תחת אור הסצנה",
      "משפחת הגוון ביחס לשכן ניטרלי באותו אור; החומר והגימור (מט, סאטן, מבריק; פליז מוברש מול מלוטש); הדוגמה: המוטיב, הצבעים וגודל החזרה",
      "Lab ממוצע בתוך המוצר מול משטח ניטרלי סמוך באותו אור (קיר, ספה), מול אותו יחס בין hex הכרטיס לשכן. דוגמה: ספירת חזרות לרוחב מול מידת המוצר",
      "סקריפט Lab קצר (כמו בדוחות 2026-11-07); חיתוך ×2",
      "אותה משפחת גוון וגימור; הצעה: הפרש L* מהשכן הניטרלי בתוך ±10 מהיחס שבכרטיס; חזרת הדוגמה ±15%. פריט שאור הסצנה שרף אותו (G-ED.12) לא עובר כאן",
      "CLAUDE.md; CR9; creative review §2 (\"צבע תחת אור הסצנה, חומר\")", "מעורב"),
    c("G-ED.4", "נאמנות: פרופורציה וקנה מידה",
      "גובה/רוחב (או גובה/קוטר) מול מידות הכרטיס; גודל מול שכנים באותו מישור ובאותו עומק שיש להם מידה ידועה",
      "מדידה בפיקסלים על החיתוך. שכנים: מוצר אחר עם מידה בכרטיס באותה שורת עומק (קערה, ראנר וכוסות על אותו שולחן; אגרטל ואגרטל על אותו אדן; כרית מול כרית)",
      "רשת מדידה על החיתוך (mc-table-grid.jpg לדוגמה); הסקריפט של הדוח",
      "±15% ביחס ובגודל. כשאין שכן עם מידה או שאין מידה בכרטיס: נרשם \"לא מדיד\", וזה לא \"עבר\"",
      "creative review §2 (\"ופרופורציה מול שכנים ומול המידות בכרטיס (±15%)\"), מאומץ ב-CR", "מחייב"),
    c("G-ED.5", "פסק לכל מוצר, וכלל המעבר של הפריים",
      "טבלה: כרטיס | נוכח | נאמן (כן / חלקית / לא) | למה | התיקון (קוד 0 טוקנים / מעבר ממוקד / מעבר משלו / החלטה)",
      "סיכום G-ED.2–G-ED.4 לכל מוצר",
      "JSON: frames.<id>.rows ו-counts",
      "הפריים עובר רק אם כל מוצר כוכב וכל מוצר עם נקודת \"קנה\" הוא \"כן\". \"לא\" אף פעם. \"חלקית\" מותר רק כחריג בשם, שהבעלים אישר בכתב (status/decisions.json), עם ההערה שתוצג",
      "CLAUDE.md; CR9; הבריף (2026-11-07). החריג הכתוב: הצעה", "מעורב"),
    c("G-ED.6", "אין מוצר נמכר מומצא",
      "פריט שנראה כמו מוצר שלנו ואינו הוא: כפיל של מוצר (קערה שנייה, סל שני), או פריט גנרי מקטגוריה שאנחנו מוכרים בסגנון שאי אפשר להבדיל ממוצר שלנו. ספירות \"exactly one\" מהבריף",
      "מעבר על כל הפריטים הגנריים בפריים מול מוצרי הסגנון בקטלוג. ספירה לכל קטגוריה",
      "חיתוכים ב-100%",
      "0 פריטים כאלה. ספירות הבריף מתקיימות",
      "בריף ED2 (\"any invented look-alike is a fail\"); CLAUDE.md; חוקי הסטודיו ג (\"החדר מציג אפשרות אחת שקיימת אצל הספק\")", "מחייב"),
    c("G-ED.7", "כלל \"הסט המדומה\"",
      "פריט שלא נמכר ונקרא כחלק מסט של מוצר שלנו: אותו זיגוג, דוגמה, אריג או חומר, ועוד הפרט המזהה (נימור, שפה, גדיל), ליד המוצר",
      "לכל מוצר: הפריטים הגנריים שלידו, וההשוואה של גימור ופרט מזהה. בדוגמה: שלוש הכוסות בכפרי, באותו שנהב מנומר עם שפה שזופה כמו הקערה",
      "חיתוך ×2–×3 של המוצר עם השכנים שלו",
      "0. התיקון: גימור אחר לפריט הגנרי (זיגוג חלק או צבע אחר), בקוד ב-0 טוקנים כשאפשר",
      "הבריף (2026-11-07); CLAUDE.md (נאמנות). הניסוח: הצעה", "מעורב"),
    c("G-ED.8", "מסכות: שום דבר מחוץ להן לא זז",
      "אחרי מעבר ממוקד או תיקון בקוד: כל פיקסל ששינה ערך, מול האזורים שנרשמו (crop_box, אזורים, קופסאות)",
      "הפרש עצמאי לכל זוג לפני/אחרי: |אחרי − לפני| > 2 רמות בערוץ כלשהו; רכיבים מחוברים על הרחבה של 15 פיקסלים; התיבה של כל רכיב מול האזורים",
      "qa/reports/2026-11-07-editorial-fin2-ed4-country/tools/diffs.py (data/diffs.json, overlays/diff-*.jpg)",
      "0 רכיבים מחוץ לאזורים. פיקסל בודד עד 5 רמות נרשם כ\"זניח\". תיקון בלי קובץ אזורים (כמו fin2-codefix.json, ed4.json): \"חסר ראיה\"",
      "חוקי הסטודיו ז (2026-10-24, \"אפס הפרש מחוץ למסכה\"); המספרים: הצעה", "מעורב"),
    c("G-ED.9", "תפרים, הילות, רוחות ומילוי שטוח",
      "בתוך המסכה ובשוליה: תפר (קפיצה ישרה), הילה, \"רוח\" של הצורה הישנה, מילוי בלי גרעין, צל מגע שנעלם",
      "חיתוך ב-100%, הגדלה ×3–×4 (NEAREST), ומתיחת ניגודיות ×4 (אחוזונים 1–60) של כל אזור ששונה",
      "overlays/<pair>-before-after.jpg, <pair>-stretch.jpg, וחיתוכי רשת",
      "שום דבר לא נראה ב-100%. מה שנראה רק במתיחה נרשם כהערה. דוגמאות מ-2026-11-07: כנפי השפה סביב הכד בג'אפנדי, הד השפה בים התיכוני, התפר בבוהו",
      "חוקי הסטודיו ז (2026-10-24: הכתמים שהמשתמש ראה); G2.3 (רצועת הילה)", "מעורב"),
    c("G-ED.10", "מעקה: בלי מראה HDR",
      "הילות זוהר סביב קצוות בניגוד גבוה, ניגוד מקומי \"פריך\", צללים מורמים ושמיים או חלון \"מצוירים\", זהוב-על-הכול",
      "עין, בגודל מלא וב-100%, של qa-agent ושל master-designer, עם פסק כתוב",
      "אין כלי מספרי. פסק עין בקובץ (מי, מתי, על איזה קובץ, מה ראה)",
      "שניהם כותבים \"אין מראה HDR\"",
      "CR5 (מאומץ 2026-11-07)", "מחייב"),
    c("G-ED.11", "מעקה: בלי כתום-טיל",
      "פיצול גוונים גלובלי: צללים לכחול-טורקיז וגווני עור/עץ לכתום, שלא מגיע ממקורות האור בסצנה",
      "עין, ועזר מספרי: a*, b* של 10% הכהים ו-10% הבהירים. דגל כשהצללים b* < −4 והבהירים b* > +15. חפץ ניטרלי באותו אור צריך להיקרא ניטרלי",
      "qa/reports/2026-11-07-gate-g-ed/tools/guardrails.py (split_flag)",
      "אין פיצול גלובלי. פיצול חם-קר מותר רק כשסיפור האור כולל שני מקורות (שעה כחולה ופנסים, גשם ומנורות)",
      "CR5", "מחייב"),
    c("G-ED.12", "מעקה: הבהקים שרופים עד 1%, חוץ מהחלון",
      "החלק של הפריים שבו ערוץ כלשהו ≥254, בלי קופסאות החלון",
      "על הפלט הגולמי של המודל, לפני כל ברך. ברך רכה מורידה פיקסלים שרופים מתחת ל-254 ולא מחזירה להם פרט. גם על הפריים הגמור, כבקרה",
      "guardrails.py --window x0,y0,x1,y1 על raw/ ועל הגמור (clipped_254_pct, clipped_top_components_px_box)",
      "עד 1.0% מחוץ לחלון. גוף תאורה שהוא מוצר לא יכול להיות שרוף עד שהחומר שלו לא נקרא (ראו G-ED.3)",
      "CR5 (\"הבהקים שרופים עד 1% מהפריים חוץ מהחלון\"); המדידה על הגולמי ו-254: הצעה", "מעורב"),
    c("G-ED.13", "מעקה: סיפור האור נקרא",
      "השעה, מזג האוויר ו\"רגע הגיבור\" של הסגנון (creative review §3.1–§3.6)",
      "עין של master-designer מול הקונספט, עם פסק כתוב",
      "פסק עין בקובץ",
      "master-designer כותב שסיפור האור של הסגנון נקרא, ואיפה רגע הגיבור",
      "CR5 (\"לכל סגנון יש סיפור אור\")", "מחייב"),
    c("G-ED.14", "בלי טקסט קריא",
      "אותיות ומספרים: מגזינים, ספרים, תוויות, שלטים, אריזות, שעונים",
      "סריקה ב-100% של כל משטח מודפס",
      "חיתוכים ב-100%",
      "0 טקסט קריא. ספרים ומגזינים מותרים כמילוי, בלי טקסט קריא (CR7)",
      "CR7; חוקי הסטודיו (\"בלי טקסט קריא\" לא משתנה)", "מחייב"),
    c("G-ED.15", "בלי מותגים ובלי העתקי עיצוב",
      "לוגו, סימן מסחרי, ופריט מעוצב מוכר (למשל Akari, ‏Moragas), במוצרים ובפריטים הגנריים",
      "עין מול רשימות ההעתקים בטיוטות הסגנון וב-Bible; ספק עובר ל-master-designer",
      "חיתוכים ב-100%",
      "0. ספק נרשם עם פסק של master-designer",
      "CLAUDE.md וחוקי הסטודיו (\"בלי העתקת עיצובים ומותגים\" לא משתנה); הטיוטות לכל סגנון", "מחייב"),
    c("G-ED.16", "רשימת \"אסור\" של הסגנון",
      "חומרים, גימורים וצבעים אסורים (למשל לבן קר, זהב מלוטש ו\"שמפניה\" בכפרי, שחור כמשטח גדול)",
      "מעבר על המוצרים ועל הפריטים הגנריים מול סעיף \"אסור\" של ה-Bible (נורדי) או של טיוטת הסגנון",
      "חיתוכים; Lab לגוונים כשצריך",
      "0 על המוצרים שלנו. בפריטים גנריים: 0, או חריג כתוב של master-designer",
      "docs/design-bible/nordic.md \"אסור\" (מחייב); docs/design-bible/*-brief-draft.md (טיוטות: הצעה עד שהמעצב מעדכן את המסמכים לפי CR)", "מעורב"),
    c("G-ED.17", "נקודת \"קנה\": אפשר לגעת במוצר בטלפון",
      "לכל מוצר שיקבל נקודה: החלק הנראה והלא מוסתר שלו, החדות שלו, והמרחק מנקודות אחרות, בהצגה בטלפון",
      "תצוגת ייחוס (הצעה): טלפון 390×844 CSS לאורך, הפריים ממלא את הגובה (cover). קנה המידה: 844 / גובה הפריים בפיקסלים, ‏0.55 CSS לפיקסל בפריים של 1536. נוסחה לכל הצגה אחרת: פיקסלים בפריים = יעד ב-CSS × פיקסלי הפריים / פיקסלי CSS המוצגים",
      "תיבות המוצרים בפריים (מפת הנקודות של frontend-dev או תיבות של qa-agent); אחרי הבנייה: G5.3 על צילום מסך",
      "הצעה: החלק הנראה ≥44 CSS בצד הארוך ו-≥24 CSS בצד הקצר (WCAG 2.5.8), כלומר ≥80 ו-≥44 פיקסלים בפריים של 1536; המוצר חד מספיק לזיהוי (לא חזית מטושטשת); יעדי 44×44 CSS של שתי נקודות לא חופפים (מרכזים ≥80 פיקסלים זה מזה), אחרת מקבצים לנקודה אחת (G5.3); הנקודה בתוך החלק שנראה בחיתוך הטלפון או בדרך ה-pan. מוצר שלא עומד בזה לא מקבל נקודה בפריים הזה, ומופיע בפריים השני או בתקריב (G-ED.18)",
      "DIR1 (\"נגיעה במוצר פותחת 'קנה את המראה'\"); G5.3 ו-G7.7 (44, הצעה); WCAG 2.5.8 (24). הספים: הצעה", "מעורב"),
    c("G-ED.18", "כיסוי בסיפור כולו (ברמת הסגנון)",
      "כל מוצר בחדר מופיע לפחות פעם אחת שלם, חד, ובגודל של לפחות 1.5% מהפריים: בפריים הרחב, בפריים השני או בתקריב",
      "טבלת \"מוצר × פריים\" על כל פריימי הסיפור של החדר בסגנון",
      "JSON: story.<style>.coverage",
      "כל מוצר עם נקודה עומד בזה פעם אחת לפחות. רץ על הסט, לא על פריים בודד, לפני שהסיפור של הסגנון עולה לאתר",
      "creative review §2א.5 (\"הכלל המוצע\"). הצעה", "הצעה"),
]

states = [
    dict(id="not_yet", label="עוד לא",
         entry="לפחות אחד: מוצר כוכב או מוצר עם נקודה ב\"לא\"; פריט מומצא או סט מדומה (G-ED.6, G-ED.7); \"חלקית\" שצריך מעבר או החלטה; עקב שנראה ב-100% שאינו תיקון קוד קטן; כשל במעקה (G-ED.10–G-ED.13); טקסט, מותג או \"אסור\" על מוצר",
         shown_to_owner=False, on_site=False),
    dict(id="almost", label="כמעט",
         entry="כל מה שפתוח הוא תיקון קוד ב-0 טוקנים (בשם ובמקום) או הערה שהבעלים יכול לקבל. אין \"לא\", אין חיקוי, אין כשל במעקה, אין טקסט",
         shown_to_owner=False, on_site=False),
    dict(id="final_test", label="מבחן סופי",
         entry="G-ED.1–G-ED.16 עוברים. \"חלקית\" רק כהערה כתובה שהבעלים רואה (כיוון שלא נפתר במעבר אחד, למשל ערימת השטיח). master-designer הסתכל וכתב פסק. המנהל מציג לבעלים",
         shown_to_owner=True, on_site=False),
    dict(id="approved_for_site", label="מאושר לאתר",
         entry="כל G-ED עובר, כולל G-ED.17, ו-G-ED.18 ברמת הסגנון. כל \"חלקית\" שנשאר הוא חריג בשם שהבעלים אישר ב-status/decisions.json. יש אישור מפורש של הבעלים לפריים הזה ב-status/decisions.json, ודוח QA שכתוב בו \"עבר\". בלי QA שום נכס לא נכנס לאתר (CLAUDE.md)",
         shown_to_owner=True, on_site=True),
]

process = [
    dict(step=1, what="פריים בסיס: מודל לפי הסגנון, טקסט ו-5 ייחוסים (מתכון \"סיפור v1\", CR8). jobs.json עם הייחוסים, הפרומפט, המודל והטוקנים", who="render-agent; המודל: master-designer", checks=[]),
    dict(step=2, what="QA סבב 1 על הפריים כולו", who="qa-agent מודד; master-designer שופט את העין", checks=["G-ED.1–G-ED.7", "G-ED.10–G-ED.16"], out="qa/reports/<date>-<scope>.md ו-.json, עם רשימת תיקונים לפי סוג"),
    dict(step=3, what="תיקוני קוד ב-0 טוקנים, כל אחד עם קובץ אזורים (קופסאות, איך, פיקסלים בפנים ובחוץ)", who="render-agent", checks=[]),
    dict(step=4, what="מעברים ממוקדים על חיתוך עם מסכה (crop_box, אזורים, ecc, הגברים), רק בטוקנים שהמנהל או הבעלים אישרו (כמו ED4, ‏MC1)", who="render-agent", checks=[]),
    dict(step=5, what="QA סבב 2: כל זוג לפני/אחרי, ונאמנות מחדש של המוצרים ששונו. אם מעבר שינה יותר מ-10% מהפריים, השער כולו מחדש (הצעה)", who="qa-agent", checks=["G-ED.8", "G-ED.9", "G-ED.2–G-ED.7 למוצרים ששונו", "G-ED.12 על הגולמי החדש"]),
    dict(step=6, what="ביקורת עיצוב ופסק עין כתוב", who="master-designer", checks=["G-ED.10", "G-ED.13", "G-ED.15 (ספק)", "G-ED.16 (חריגים)"]),
    dict(step=7, what="\"מבחן סופי\": המנהל מציג לבעלים רק פריימים במצב הזה, עם ההערות", who="המנהל → הבעלים", checks=[]),
    dict(step=8, what="לפני האתר: מפת נקודות, ואז G-ED.17; G-ED.18 על סט הסגנון", who="frontend-dev (המפה); qa-agent (הבדיקה)", checks=["G-ED.17", "G-ED.18"]),
    dict(step=9, what="אישור מפורש של הבעלים ב-status/decisions.json → \"מאושר לאתר\"; אחרי הבנייה G5.3 על צילום מסך, ושערי האתר (G5–G7)", who="הבעלים; frontend-dev; qa-agent", checks=["G5.3", "G6", "G7"]),
]

raw_by = {r["file"].split("/")[-1]: r for r in RAW}
fin_by = {r["file"].split("/")[-1]: r for r in FIN}


def g(raw_name, fin_name):
    r, f = raw_by[raw_name], fin_by[fin_name]
    return dict(raw=raw_name, raw_clipped_254_pct=r["clipped_254_pct"], raw_top_clipped_boxes=r["clipped_top_components_px_box"],
                finished_clipped_254_pct=f["clipped_254_pct"], split_flag=f["split_flag"])


mapping = [
    dict(frame="nordic-A-ed4", file="assets/renders/editorial-phase-b-2026-11-06/nordic-A-ed4.png", state="final_test",
         counts=dict(yes=13, partly=1, no=0), guardrails=g("nordic-A-fin-seedream.png", "nordic-A-ed4.png"),
         line="מבחן סופי (הוצג 2026-11-07). לאתר חסרים: השטיח \"חלקית\" (לתקן או חריג בכתב), G-ED.17, ואישור הבעלים"),
    dict(frame="nordic-B-fin", file="assets/renders/editorial-phase-b-2026-11-06/nordic-B-fin.png", state="final_test",
         counts=dict(yes=7, partly=1, no=0), guardrails=g("nordic-B-fin-seedream.png", "nordic-B-fin.png"),
         line="מבחן סופי (הוצג 2026-11-07). לאתר חסרים: הווילון \"חלקית\" רק כי הקפל מחוץ לפריים (חריג בכתב), G-ED.17, ואישור הבעלים"),
    dict(frame="warm-modern-A-ed4", file="assets/renders/editorial-phase-b-2026-11-06/warm-modern-A-ed4.png", state="almost",
         counts=dict(yes=9, partly=2, no=0), guardrails=g("warm-modern-A-fin-seedream.png", "warm-modern-A-ed4.png"),
         line="כמעט: בתלויה 6 טבעות ובכרטיס 5 (G-ED.2, קוד ב-0 טוקנים); השטיח העבה \"חלקית\" כמו בנורדי A"),
    dict(frame="boho-A-fin2", file="assets/renders/editorial-phase-b-2026-11-06/boho-A-fin2.png", state="not_yet",
         counts=dict(yes=7, partly=2, no=0), guardrails=g("boho-A-gpt-image-2-5.png", "boho-A-fin2.png"),
         line="עוד לא: התפר ב-x≈400 (G-ED.9, קוד); העציץ והסל בגדלים הפוכים (G-ED.4, החלטה); המראה הזהוב הקרוב ל-HDR (G-ED.10)"),
    dict(frame="mediterranean-A-ed4", file="assets/renders/editorial-phase-b-2026-11-06/mediterranean-A-ed4.png", state="not_yet",
         counts=dict(yes=9, partly=1, no=0), guardrails=g("mediterranean-A-gpt-image-2-5.png", "mediterranean-A-ed4.png"),
         line="עוד לא: כרית הפרנזים הלבנה לא נבדלת מכריות הספסל (G-ED.6); הד השפה ליד הקערה (G-ED.9, קוד)"),
    dict(frame="japandi-A-ed4", file="assets/renders/editorial-phase-b-2026-11-06/japandi-A-ed4.png", state="not_yet",
         counts=dict(yes=7, partly=3, no=0), guardrails=g("japandi-A-nano-banana-2.png", "japandi-A-ed4.png"),
         line="עוד לא: עקבות הקוד סביב הכד (G-ED.9); בגולמי 2.09% שרוף, רובו התלויה עצמה (G-ED.12; הברך לא נחשבת); התלויה מחכה ל-sourcing (G-ED.2); מנורות הקיר וכרית הוואבי-סאבי \"חלקית\""),
    dict(frame="modern-country-A", file="assets/renders/editorial-phase-b-2026-11-06/modern-country-A.png", state="not_yet",
         counts=dict(yes=3, partly=3, no=1), guardrails=g("modern-country-A-gpt-image-2-5.png", "modern-country-A.png"),
         line="עוד לא: אגרטל החימר \"לא\" (G-ED.2, ‏G-ED.4); הכוסות סט מדומה (G-ED.7); הקערה עמוקה והראנר פי 1.4 (G-ED.4; ‏MC1 אושר); גוון הווילונות והסימן על הכרית (קוד)"),
]

record = dict(
    id="quality-gate-g-ed-2026-11-07",
    title="שער G-ED: פריימי סיפור",
    version="1.0", date="2026-11-07", author="qa-agent",
    mode="קבצים חדשים בלבד. לא שונה שום קובץ קיים, אין commit, אין var2, אין רשת.",
    brief="briefs/qa-gate-g-ed-2026-11-07.md",
    rules="CR9 ו-CR5, CR7 (docs/creative-review-2026-11-06.md §5), מאומצים 2026-11-07 (status/decisions.json: CR; חוקי הסטודיו ז, \"הכיוון החדש מאומץ\"); DIR1; CLAUDE.md (נאמנות למוצר קודמת ליופי; נכס שלא עבר QA לא נכנס לאתר)",
    companion_md="docs/ops/quality-gate-g-ed-2026-11-07.md",
    scope="שכבה 1 (פריימי סיפור: הפריים הרחב והפריים השני של כל חדר וסגנון). G1 נשאר לכלי \"עצב בעצמך\" (שכבה 3). תקריבי שכבה 2: G-ED.1–G-ED.16 על אותו מוצר, ועוד G4.16 (מסגור התקריב)",
    read=["briefs/qa-gate-g-ed-2026-11-07.md", "docs/creative-review-2026-11-06.md (§2, §2א, §3, §3.7, §5)", "docs/studio-rules.md (ז: ED1–ED4, הכיוון החדש מאומץ, MC1)",
          "status/decisions.json (DIR1, CR)", "docs/ops/quality-gates-2026-11-02.md ו-.json (המבנה; G1, G2.3, G5.3, G7.7)",
          "qa/reports/2026-11-06-editorial-test-fidelity.md", "qa/reports/2026-11-06-editorial-phase-b-fidelity.md", "qa/reports/2026-11-07-editorial-fin2-ed4-country.md",
          "assets/renders/editorial-phase-b-2026-11-06/jobs.json (finishing: clipped_pct_before, px_at_255_after)", "docs/design-bible/nordic.md, docs/design-bible/modern-country-brief-draft.md"],
    source_policy=dict(
        binding="מחייב = CLAUDE.md, חוקי הסטודיו, ושינויי CR שהבעלים אימץ ב-2026-11-07 בנוסח של docs/creative-review-2026-11-06.md",
        proposal="הצעה = כל סף שאין לו מספר במקור מחייב. נכנס לשער באישור המנהל; שינוי במסמך מחייב באישור הבעלים",
        mixed="העיקרון מחייב והמספר הצעה; החלק המספרי מסומן \"הצעה:\""),
    verdicts={"עבר": "הבדיקה נמדדה, יש קובץ ראיה, והתוצאה בתוך הסף", "נכשל": "נמדד מחוץ לסף", "חסר ראיה": "נטען שנבדק ואין קובץ; נחשב \"לא עבר\"", "לא נבדק": "אף אחד לא מדד"},
    common_rules=[
        "פריים עובר מצב רק אם לכל בדיקה של המצב יש מדידה או פסק בקובץ. \"חסר ראיה\" הוא \"לא עבר\".",
        "הראיה: qa/reports/<date>-<scope>.md ו-.json, ולצידם תיקייה עם overlays/, tools/, data/.",
        "בדיקה עצמית של render-agent (למשל \"OK\" ב-product_notes_render_agent, או px_at_255_after) היא מידע, לא QA.",
        "פסק עין (\"נאמן\", \"אין HDR\", \"סיפור האור נקרא\") נרשם: מי, מתי, על איזה קובץ ומה ראה.",
        "כל תיקון (קוד או מעבר) נבדק שוב לפני שהפריים עולה מצב.",
    ],
    gate=dict(
        id="G-ED",
        deliverable="פריים סיפור (שכבה 1) לחדר בסגנון: הפריים הרחב והפריים השני",
        when="אחרי פריים הבסיס, אחרי כל סבב תיקונים, ולפני שהפריים מוצג לבעלים או נכנס לאתר",
        checker=dict(measures="qa-agent", judges="master-designer (G-ED.10, G-ED.13, ספק ב-G-ED.15, חריגים ב-G-ED.16)", approves="הבעלים: \"מבחן סופי\" ו\"מאושר לאתר\", וכל חריג \"חלקית\""),
        evidence=dict(report="qa/reports/<date>-<scope>.md ו-.json",
                      files=["overlays/ (חיתוכים ב-100%, ×3–×4, מתיחה ×4, מפות הפרש)", "data/diffs.json (diffs.py)", "data/guardrails-raw.json ו-guardrails-finished.json (guardrails.py)",
                             "הרשומות של render-agent: jobs.json, קובצי האזורים של כל תיקון (fin2-codefix.json, ed4.json)"]),
        criteria=criteria,
        counts=dict(total=len(criteria), binding=sum(1 for x in criteria if x["binding"] == "מחייב"),
                    mixed=sum(1 for x in criteria if x["binding"] == "מעורב"), proposal=sum(1 for x in criteria if x["binding"] == "הצעה"))),
    states=states,
    process=process,
    mapping=dict(date="2026-11-07", basis="qa/reports/2026-11-07-editorial-fin2-ed4-country.md; G-ED.12 נמדד היום (guardrails.py); G-ED.17 ו-G-ED.18 לא הורצו על אף פריים",
                 frames=mapping),
    measurements=dict(
        tool="qa/reports/2026-11-07-gate-g-ed/tools/guardrails.py",
        raw=RAW, finished=FIN,
        reading="בגמור 0% שרוף בכל השבעה, כי הברך של render-agent (0.90 → 0.985) מורידה הכול מתחת ל-254. בגולמי: ג'אפנדי 2.09% (רובו פנס הנייר שהוא מוצר, [148,304,596,859]), ושאר הששה 0.07–0.39%. דגל הפיצול כבוי בכולם."),
    open_items=[
        dict(id="Q-ED1", what="G-ED.12 על הגולמי מול הגמר של render-agent: px_at_255_after = 0 נרשם כעמידה במעקה, אבל הברך לא מחזירה פרט", gate_uses="הגולמי", owner="המנהל; render-agent"),
        dict(id="Q-ED2", what="תצוגת הייחוס בטלפון ל-G-ED.17 עוד לא נקבעה (DIR1 חדש, האתר לא נבנה)", gate_uses="390×844 לאורך, cover בגובה; הנוסחה לכל הצגה אחרת", owner="frontend-dev ו-master-designer → הבעלים"),
        dict(id="Q-ED3", what="רשימות \"אסור\" של חמשת הסגנונות הן טיוטות", gate_uses="הטיוטות כהצעה עד שהמעצב מעדכן את המסמכים לפי CR", owner="master-designer"),
        dict(id="Q-ED4", what="חריגי \"חלקית\" לערימת השטיח (נורדי A, מודרני חם) ולקפל הווילון (נורדי B)", gate_uses="נדרש חריג בשם ב-decisions.json לפני \"מאושר לאתר\"", owner="המנהל → הבעלים"),
        dict(id="Q-ED5", what="צורת התלויה בג'אפנדי (ביצה מול דלעת 40×25 בכרטיס)", gate_uses="G-ED.2 לא יעבור עד תשובה", owner="sourcing-agent"),
    ],
    changelog=["1.0 (2026-11-07): השער, 18 בדיקות, ארבעה מצבים, הסדר, והמיפוי של שבעת הפריימים."],
)

out = os.path.join(ROOT, "docs/ops/quality-gate-g-ed-2026-11-07.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(record, f, ensure_ascii=False, indent=1)
print("criteria", record["gate"]["counts"])
for m in mapping:
    print(m["frame"], m["state"], m["guardrails"]["raw_clipped_254_pct"])
print("wrote", out)
