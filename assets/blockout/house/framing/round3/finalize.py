#!/usr/bin/env python3
"""Round-3 wrap-up, 0 tokens: paste the summarize.py table into README.md (RESULTS_TABLE), add the notes that only the final run
could give, and build round2-vs-round3.jpg from the selfcheck (the final run used --no-sheet).  python3 finalize.py"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOUSE = os.path.abspath(os.path.join(HERE, "..", ".."))
sc = json.load(open(os.path.join(HERE, "selfcheck.json")))
table = subprocess.run([sys.executable, os.path.join(HERE, "summarize.py")], capture_output=True, text=True).stdout.strip()
h0 = sc["frames"].get("H0", {}).get("light_balance", {})
extra = json.load(open(os.path.join(HERE, "extra", "H0-hallroof-1.35.json"))) if os.path.exists(os.path.join(HERE, "extra", "H0-hallroof-1.35.json")) else {}
notes = f"""
### הערות על הסבב הסופי (3840×2160, 36 דגימות)
- **M0 לא רונדר בסבב 3.** הריצה הראשית (D1 → M0) נעצרה באמצע K-girl בהשהיית הסשן (2026-10-25 ~14:50 UTC) והופעלה מחדש ל-K-girl, B1, B2, W0 בלבד; המנהל הנחה שטיוטת M0 משתמשת ב-`assets/blockout/living-room/m0-clay-4k.png` (כותרת `m0-v6.txt` ביקשה clay עם צורות-מקום). ‏`python3 framing_r3.py --plan framing/round3/plan.json --frames M0 --res 3840 --samples 36 --hall-roof 1.6 --no-sheet` משלים אותו (~17 דקות, 0 טוקנים).
- **מאזן הכניסה (H0):** הסלון דרך הדלת גבוה מקיר הכניסה מעל הקונסולה ב-{h0.get('living_minus_hall_stops')} סטופ (יעד 0.5–0.9; `pass_2_3_stop` {h0.get('pass_2_3_stop')}), ומנקודת ה-QA (0.35, 0.40) ב-{h0.get('qa_point_minus_front_wall_L')} L מעל הקיר שמולה (יעד ≥ 8, עובר). מול הקיר מימין לקונסולה ההפרש הוא ~0.65 סטופ. ניסוי חוזר עם חלון הגג ×1.35 (`extra/H0-hallroof-1.35.png`, ‏{extra.get('light_balance', {}).get('living_minus_hall_stops')} סטופ) הזיז את קיר הכניסה פחות מ-1 L: ב-4K חלון הגג אינו המנוף; הכניסה מוארת בעיקר מגלישת הסלון דרך הפורטל וממנורת הקובייה. בדיקות העשן ב-960px הראו רגישות גדולה בהרבה (×1.6 → 0.72), כנראה הבדל בדגימת הטלאים ברזולוציה נמוכה. לא תוקן; מועמד לסבב הבא: `--living-boost` (להעלות את קיר הסלון לכיוון L 88–90 כמו ב-M0) במקום לכבות את הכניסה.
- **המטבח (D1/D2):** הטיוטות של gpt-image-2-5 ציירו את קו המשטח והמדפים 0.02–0.04 מגובה הפריים מעל קווי ה-clay בשתי דגימות של D2 (ב-D1 נעול). ה-clay עצמו לא השתנה; לבדיקת המעצב אם גובה המצלמה 1.1 במטבח (מול 1.2 בשאר) הוא הסיבה.

### כרטיס הטוקנים של שלב B (var2, gpt-image-2-5 sunburst 2K)
‏10 עבודות × 600 = **6,000 טוקנים** (d1, d2, d2-r2, h0-B, c0, mb0, k-boy, k-girl, m0-v6, m0-v6-r2); תקרה 12,000. היתרה בחשבון ירדה ל-360, ולכן **k-girl-r2, b1, b2 ו-w0 לא נשלחו** (צריך 600 לעבודה; 2,400 להשלמה). ה-clay של B1, B2 ו-W0 מוכן ומועלה ל-var2 (`assets/renders/house-nordic-2026-10-25/jobs.json` → `clay`).
"""
p = os.path.join(HERE, "README.md")
s = open(p, encoding="utf-8").read()
if "RESULTS_TABLE" in s:
    s = s.replace("RESULTS_TABLE", table + "\n" + notes)
    s = s.replace("ראו `selfcheck.json` ואת הטבלה ב-`summarize.py` (מודבקת כאן בסוף הסבב).", "מ-`selfcheck.json` דרך `summarize.py` (הריצה הסופית):")
    open(p, "w", encoding="utf-8").write(s)
    print("README results pasted")
else:
    print("README already finalised")
# round 2 vs round 3 sheet
sys.path.insert(0, HOUSE)
os.chdir(HOUSE)
import framing_r3 as r3  # noqa: E402  (imports bpy; 0 renders)
frames = [f for f in r3.ORDER if f in sc.get("frames", {})]
print("sheet:", r3.sheet(sc, frames), len(frames), "frames")
