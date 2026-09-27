# Home Design Studio — מערכת הסוכנים

סביבת העבודה של הפרויקט ב-Claude Code. השיחה הראשית היא המנהל (לפי `CLAUDE.md`), ושישה סוכנים מתמחים נמצאים ב-`.claude/agents/`.

## מה יש כאן
```
CLAUDE.md                         המנהל: שלבים, נקודות אישור, איך מפעילים סוכנים
.claude/agents/                   sourcing-agent, master-designer, render-agent,
                                  motion-agent, frontend-dev, qa-agent
.claude/skills/interior-design-rules/   חוקי העיצוב ומחוון הדירוג של המעצב
.mcp.json                         חיבור ל-var2
docs/skeleton-spec.md             מפרט השלד
docs/design-bible/nordic.md       Design Bible נורדי (טיוטה)
data/product-card.schema.json     מבנה כרטיס מוצר
data/slots/living-room.json       עמדות המוצר וסדר השכבות בסלון
status/board.md                   לוח הסטטוס
data/products, data/selections, briefs, assets, qa/reports, site   תוצרי הסוכנים
```

## הקמה מהטלפון
1. צור ריפו חדש ופרטי ב-GitHub.
2. העלה אליו רק את הקובץ `BOOTSTRAP.md`.
3. באפליקציית Claude, פתח את Claude Code ובחר את הריפו.
4. כתוב: "בצע את ההוראות ב-BOOTSTRAP.md". Claude Code ייצור את כל הקבצים.

## הקמה מהמחשב
פרוס את קובץ ה-zip לתוך ריפו, בצע commit ו-push, ופתח את התיקייה ב-Claude Code.

## var2
`.mcp.json` מגדיר את var2. בפעם הראשונה ייתכן שתתבקש לאשר את השרת ולהתחבר לחשבון var2. var2 נדרש רק משלב הרינדור, כך ששלבים 0–1 עובדים גם בלעדיו.

## איך מתחילים
כתוב ל-Claude Code: "התחל שלב 0". המנהל יפעיל את המעצב, ישלים את ה-Design Bible הנורדי ויחזור אליך לאישור.
