"""Hebrew reports for stage 3: data/leads/aliexpress/scale-2026-10/<room>.md and README.md.

python3 -I reports.py
"""
import collections, json, os, re, sys

WORK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WORK)
import prep, shortlist  # noqa

REPO = prep.REPO
OUT = os.path.join(REPO, "data", "leads", "aliexpress", "scale-2026-10")
ROOMS = ["living-room", "dining-room", "master"]
ROOM_HE = {"living-room": "סלון", "dining-room": "מטבח ופינת אוכל", "master": "חדר שינה הורים"}
STYLE_ORDER = prep.STYLE_ORDER
STYLE_HE = {"nordic": "נורדי", "warm-modern": "מודרני חם", "japandi": "ג'פנדי", "mediterranean": "ים תיכוני",
            "modern-country": "כפרי מודרני", "boho": "בוהו"}
SUP_HE = {"cj": "CJ", "zendrop": "Zendrop", "aliexpress": "AliExpress", "il": "ספק ישראלי", "other": "אחר"}
VERDICT_HE = {"best": "הכי טוב", "alternative": "חלופה", "reject": "נדחה"}
# Hebrew notes for the picks that became best or a card (the JSON keeps the English reason)
NOTE_HE = {
    "1005012745902882": "וילון שקוף במראה פשתן בשיבולת שועל, קפלי S (גל), פאנל 100×275; זוג = 2 פאנלים. פוליאסטר, והפאנל צר מ-130–150",
    "1005009053464203": "ציפה בשנייל סלאב בשנהב עם נמש אפור, 50×50 (יש גם קרמל, אפור כהה ו-30×50). מרקם יד, מט",
    "1005012897166217": "ציפות בהדפס בלוק פרחוני במרווה על פשתן שנהב, סט של 2, צבע 1, 45×45. המראה הכפרי-סבתאי",
    "1005011825244347": "ראנר בקליעה פתוחה בשמנת עם פרנזים קשורים, 30×120 בז'",
    "1005009623263532": "ראנר מקרמה: שוליים בשמנת ומרכז קלוע בגוון יוטה, פרנזים; צבע A-4 (30×120 בסלון, 30×140 בפינת האוכל)",
    "1005008814072806": "ראנר מקרמה בשמנת עם פס חאקי ופרנזים, 30×120",
    "1005012472589009": "אגרטל חרס גס בשמנת עם מרקם 'שחוק', מידה L ‏31×15, מט, צללית כד. משלוח 27 דולר (כבד), ועדיין 48%",
    "1005006165763597": "קישוט קיר מרפיה טבעית עם פרנזים ומרכז קלוע, 30 ס\"מ (מתחת למעטפת 35–45). צבע 2; צבע 3 אזל",
    "1005012481333603": "הדפס תרנגול וינטג' על רקע בוטני במרווה, מסגרת עץ 30×40 (יש גם שחורה באותו מחיר)",
    "1005009904316063": "מעמד במבוק פשוט לנייר מטבח, בסיס עגול 11.5, גובה 28.5 (1.5 ס\"מ מתחת ל-30–34)",
    "1005012862500672": "סט ציפה בוהו עם טאפטינג של קשתות ופסים בחאקי-שמנת, US Queen, 3 חלקים (ציפה ו-2 ציפיות)",
}


def slot_names(room):
    return {s["id"]: s.get("name_he") for s in json.load(open(os.path.join(REPO, "data", "slots", room + ".json")))["slots"]
            if s.get("kind") != "fixed-product"}


def item_status(r, room):
    """First reason an item (any style) did not reach the shortlist, for the per-slot diagnostics."""
    if r["drop"]:
        d = r["drop"]
        if d.startswith("no shipping"):
            return "אין משלוח לישראל"
        if d.startswith("no product"):
            return "אין נתוני מוצר"
        if d.startswith("no SKU fits"):
            return "אין מידה שמתאימה לחדר"
        if d.startswith("unframed"):
            return "קנבס בלי מסגרת"
        return "אחר"
    best = None
    for st in r["styles"]:
        s, why = shortlist.score(r, st)
        if s is not None:
            return None
        best = best or why
    w = best or ""
    if w.startswith("not the product"):
        return "לא המוצר (כותרת)"
    if w.startswith("margin"):
        return "רווח מתחת ל-20% ברצועה"
    if w.startswith("material") or w.startswith("banned"):
        return "חומר או מילה אסורה"
    return "אחר"


def money(x):
    return "₪%.0f" % x


def cell(r):
    if not r:
        return "—"
    t = (r["title"] or "")[:42].replace("|", "/")
    m = "%s · %d%%" % (money(r["margin_ils"]), round(r["margin_pct"] * 100))
    q = " ×%d" % r["qty"] if r.get("qty", 1) > 1 else ""
    card = " · כרטיס" if r.get("card_id") else ""
    return "[%s](%s)<br>$%.2f+%.2f%s · נחיתה %s<br>רווח %s · fit %s<br>**%s**%s" % (
        t, r["url"], r["price_usd"], r["ship_usd"], q, money(r["landed_ils"]), m, r["fit"], VERDICT_HE[r["verdict"]], card)


def cmp_cell(r, slot_cards):
    if not r:
        return "—"
    c = r.get("compared_to")
    if not c:
        return "אין כרטיס בעמדה"
    if not c.get("scored_for_style"):
        return "אין כרטיס עם ציון לסגנון (הזול: %s %s)" % (SUP_HE.get(c["supplier"], c["supplier"]), money(c["landed_ils"]))
    return "%s %s, fit %s, רווח %d%% %s" % (SUP_HE.get(c["supplier"], c["supplier"]), money(c["landed_ils"]), c.get("fit"),
                                          round(c["margin_pct"] * 100), "✓ AliExpress רווחי יותר" if r.get("beats_existing") else "✗ הכרטיס רווחי יותר")


def room_md(room, F, P, S):
    names = slot_names(room)
    L = []
    nP = len(P)
    ok = sum(1 for r in P if not r["drop"])
    shortlisted = sum(len(v["items"]) for v in S["slots"].values())
    picks = sum(len(x) for v in S["slots"].values() for x in v["per_style"].values())
    passed = [r for r in F if r["verdict"] != "reject"]
    carded = sorted({r["card_id"] for r in F if r.get("card_id")})
    L += ["# AliExpress בקנה מידה, שלב 3 (דירוג וכרטיסים): %s" % ROOM_HE[room], "",
          "2026-10-11 · sourcing-support · אופליין (בלי קריאות API; רק המטמון של הסשן שנעצר). מקור: `detail/%s.json`. הרשומות לסטודיו: `data/leads/aliexpress/deep-2026-10/%s.json`." % (room, room), "",
          "**במספרים:** %d מוצרים מפורטים, %d עם מחיר, משלוח לישראל ובלי פסילת מידה. ברשימה הקצרה %d מוצרים (%d בחירות עמדה×סגנון), ובכל אחד הסתכלתי בתמונה הראשית. עברו (fit 7 ומעלה ורווח 20%% ומעלה) %d רשומות; %d \"הכי טוב\"; **%d כרטיסים חדשים**." % (
              nP, ok, shortlisted, picks, len(passed), sum(r["verdict"] == "best" for r in F), len(carded)), "",
          "**איך:** עלות נחיתה = (מחיר ה-SKU שמתאים לחדר × כמות + משלוח לישראל) × 3.3. הרווח בנוסחת הסטודיו (econCalc: מע\"מ 18%, סליקה 2%+‏1.20, החזרות 8%), במחיר העליון של רצועת השוק, לפני CAC. "
          "בעמדה של זוג או סט ממוצר יחיד הכמות היא מספר היחידות, כמו בסטודיו. fit לפי מחוון הסטודיו (צבע 30, חומר 25, צורה 25, קנה מידה 20), אחרי מבט בתמונה; זה ציון סינון ולא הציון של המעצב. "
          "\"הכי טוב\" = הראשון בעמדה×סגנון עם fit 8 ומעלה ורווח לפחות כמו הכרטיס הקיים עם הציון הגבוה לאותו סגנון (או שאין כרטיס כזה). כרטיס: עד 3 לעמדה×סגנון באותם תנאים.", ""]
    for slot in [k.split("/")[1] for k in prep.SLOTS if k.startswith(room + "/")]:
        rs = [r for r in F if r["slot"] == slot]
        Ps = [r for r in P if r["slot"] == slot]
        if not Ps:
            continue
        L.append("## %s · %s" % (slot, names.get(slot, "")))
        L.append("")
        why = collections.Counter(item_status(r, room) for r in Ps)
        n_short = len(S["slots"].get(slot, {}).get("items", []))
        why.pop(None, None)
        L.append("מפורטים %d · ברשימה הקצרה %d · %s" % (len(Ps), n_short, " · ".join("%s %d" % (k, v) for k, v in why.most_common())))
        L.append("")
        top = {}
        for st in STYLE_ORDER:
            live = [r for r in rs if r["style"] == st and r["verdict"] != "reject"]
            live.sort(key=lambda r: ({"best": 0, "alternative": 1}[r["verdict"]], -r["fit"], -r["margin_ils"]))
            top[st] = live[0] if live else None
        if any(top.values()):
            L.append("| | " + " | ".join(STYLE_HE[s] for s in STYLE_ORDER) + " |")
            L.append("| --- | " + " | ".join("---" for _ in STYLE_ORDER) + " |")
            L.append("| הבחירה | " + " | ".join(cell(top[s]) for s in STYLE_ORDER) + " |")
            L.append("| SKU | " + " | ".join((top[s]["sku_label"] or "")[:34].replace("|", "/") if top[s] else "—" for s in STYLE_ORDER) + " |")
            L.append("| מול הכרטיס הקיים | " + " | ".join(cmp_cell(top[s], None) for s in STYLE_ORDER) + " |")
            L.append("")
            bests = [(s, top[s]) for s in STYLE_ORDER if top[s] and top[s]["verdict"] == "best"]
            if bests:
                seen = set()
                for s, r in bests:
                    if r["item_id"] in seen:
                        continue
                    seen.add(r["item_id"])
                    sts = ", ".join(STYLE_HE[x] for x, y in bests if y["item_id"] == r["item_id"])
                    L.append("**הכי טוב (%s):** [%s](%s): %s. נחיתה %s, רווח %d%%%s." % (
                        sts, r["item_id"], r["url"], NOTE_HE.get(r["item_id"], (r["title"] or "")[:60]), money(r["landed_ils"]),
                        round(r["margin_pct"] * 100), "; כרטיס `%s`" % r["card_id"] if r.get("card_id") else ""))
                L.append("")
            else:
                L.append("אין \"הכי טוב\": אף מועמד לא הגיע ל-fit 8 עם רווח לפחות כמו הכרטיס הקיים.")
                L.append("")
            extra = [r for r in rs if r.get("card_id") and r["verdict"] == "alternative" and r["fit"] >= 8]
            if extra:
                L.append("כרטיסים נוספים (fit 8, רווחי יותר מהכרטיס הקיים): " + " · ".join(sorted({"`%s`" % r["card_id"] for r in extra})))
                L.append("")
        else:
            L.append("**אין מועמד שעבר.** %s" % slot_why(slot, rs, why))
            L.append("")
    return "\n".join(L) + "\n"


def slot_why(slot, rs, why):
    looked = [r for r in rs]
    if looked and all(r["verdict"] == "reject" for r in looked):
        lowm = [r for r in looked if (r.get("reject_why") or "").startswith("margin")]
        if lowm and len(lowm) == len(looked):
            return "כל מה שנבדק לא מגיע ל-20% רווח ברצועה."
        return "בתמונות: %d נבדקו ונדחו (לא המוצר, קנה מידה, סגנון או רווח)." % len({r["item_id"] for r in looked})
    return "שום מוצר לא עבר את הסינון (%s)." % ", ".join(k for k, _ in why.most_common(3))


def readme(all_F, all_P, all_S, made):
    L = ["# AliExpress בקנה מידה (2026-10): סיכום", "",
         "שלבים 1–2 (חיפוש ופירוט) רצו מול ה-API בסשן אחר ונעצרו ב-2026-10-11 על מגבלת השימוש (`stop-master.txt`). **שלב 3 (דירוג, השוואה וכרטיסים) רץ אופליין** מאותם נתונים: `detail/<room>.json` והמטמון `data/sources/aliexpress/<id>.json`, בלי אף קריאה ל-AliExpress. "
         "שלושה חדרים: סלון, מטבח ופינת אוכל, חדר שינה הורים. כל ששת הסגנונות.", "",
         "## קבצים", "",
         "| קובץ | מה יש בו |", "| --- | --- |",
         "| `detail/<room>.json` | שלב 2: מוצר, SKU, מחיר, משלוח לישראל (1,457 רשומות) |",
         "| `../deep-2026-10/<room>.json` | שלב 3, לסטודיו (מסך \"השוואת ספקים\"): רשומה לכל מוצר×סגנון ברשימה הקצרה, עם SKU שמתאים לחדר, נחיתה, רצועה, רווח, fit, נימוק, השוואה לכרטיס הקיים ו-verdict |",
         "| `living-room.md`, `dining-room.md`, `master.md` | לכל עמדה: טבלה עם עמודה לכל סגנון, הבחירה הטובה וההשוואה |",
         "| `review/sheets/` | דפי המגע משלב 2 (שלב 3 הסתכל בתמונות עצמן, בגודל גדול יותר) |", ""]
    tot = {"detail": 0, "ok": 0, "short": 0, "picks": 0, "records": 0, "passed": 0, "best": 0}
    rows = []
    for room in ROOMS:
        F, P, S = all_F[room], all_P[room], all_S[room]
        d = dict(detail=len(P), ok=sum(1 for r in P if not r["drop"]), short=sum(len(v["items"]) for v in S["slots"].values()),
                 picks=sum(len(x) for v in S["slots"].values() for x in v["per_style"].values()), records=len(F),
                 passed=sum(1 for r in F if r["verdict"] != "reject"), best=sum(1 for r in F if r["verdict"] == "best"),
                 cards=len({r["card_id"] for r in F if r.get("card_id")}))
        rows.append((room, d))
        for k in tot:
            tot[k] += d[k]
    tot["cards"] = sum(d["cards"] for _, d in rows)
    L += ["## סיכומים", "",
          "| חדר | מפורטים | עם מחיר, משלוח ובלי פסילת מידה | ברשימה הקצרה (נבדקו בתמונה) | רשומות מוצר×סגנון | עברו | הכי טוב | כרטיסים חדשים |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for room, d in rows:
        L.append("| %s | %d | %d | %d | %d | %d | %d | %d |" % (ROOM_HE[room], d["detail"], d["ok"], d["short"], d["records"], d["passed"], d["best"], d["cards"]))
    L.append("| **סה\"כ** | **{:,}** | **{:,}** | **{:,}** | **{:,}** | **{:,}** | **{:,}** | **{:,}** |".format(tot["detail"], tot["ok"], tot["short"], tot["records"], tot["passed"], tot["best"], tot["cards"]))
    L += ["", "\"עברו\" = fit 7 ומעלה (סף הסטודיו) ורווח 20% ומעלה במחיר העליון של הרצועה. רשימה קצרה: עד 8 לכל עמדה×סגנון, לפי ציון הסינון של שלב 1 ועוד רווח וקנה מידה, אחרי הוצאת מה שלא מתאים (ראו \"השיטה\").", ""]
    # AliExpress wins
    wins, nocard = [], []
    for room in ROOMS:
        for r in all_F[room]:
            if r["verdict"] != "best":
                continue
            c = r.get("compared_to")
            if c and c.get("scored_for_style") and c["supplier"] in ("cj", "zendrop"):
                wins.append((room, r))
            else:
                nocard.append((room, r))
    L += ["## איפה AliExpress מנצח את CJ ו-Zendrop", "",
          "| חדר / עמדה | סגנון | AliExpress | הכרטיס הקיים |", "| --- | --- | --- | --- |"]
    for room, r in wins:
        c = r["compared_to"]
        L.append("| %s / %s | %s | %s, fit %s, נחיתה %s, רווח %d%% | %s (%s), fit %s, נחיתה %s, רווח %d%% |" % (
            ROOM_HE[room], r["slot"], STYLE_HE[r["style"]], r["item_id"], r["fit"], money(r["landed_ils"]), round(r["margin_pct"] * 100),
            c["card_id"], SUP_HE[c["supplier"]], c.get("fit"), money(c["landed_ils"]), round(c["margin_pct"] * 100)))
    L += ["", "**ממלא סגנון שאין לו כרטיס עם ציון** (הכרטיסים הקיימים בעמדה לא דורגו לסגנון הזה, או שאין כרטיס בכלל):", ""]
    for room, r in nocard:
        L.append("- %s / %s, %s: %s (fit %s, נחיתה %s, רווח %d%%)" % (ROOM_HE[room], r["slot"], STYLE_HE[r["style"]], r["item_id"], r["fit"], money(r["landed_ils"]), round(r["margin_pct"] * 100)))
    L.append("")
    # nothing
    L += ["## עמדות בלי שום מועמד שעבר", "", "בשום סגנון אין מוצר עם fit 7 ומעלה ורווח 20% ומעלה. הסיבה העיקרית בסוגריים.", ""]
    for room in ROOMS:
        F, P = all_F[room], all_P[room]
        names = slot_names(room)
        empty = []
        for slot in [k.split("/")[1] for k in prep.SLOTS if k.startswith(room + "/")]:
            if any(r["slot"] == slot and r["verdict"] != "reject" for r in F):
                continue
            Ps = [r for r in P if r["slot"] == slot]
            why = collections.Counter(item_status(r, room) for r in Ps)
            why.pop(None, None)
            looked = len({r["item_id"] for r in F if r["slot"] == slot})
            main = why.most_common(1)[0][0] if why else None
            if looked:
                main = ("נבדק אחד בתמונה ונדחה" if looked == 1 else "%d נבדקו בתמונה ונדחו" % looked) + ("; בסינון בעיקר: %s" % main if main else "")
            empty.append("%s (%s)" % (slot, main))
        L.append("- **%s:** %s" % (ROOM_HE[room], "; ".join(empty) if empty else "—"))
    L.append("")
    # top 20 by margin
    pool = {}
    dups = {i for (_, i) in __import__("stage3").DUPLICATE_OF}
    for room in ROOMS:
        for r in all_F[room]:
            if r["verdict"] == "reject" or r["item_id"] in dups:
                continue
            k = r["item_id"]  # one row per product (the same product in two rooms counts once)
            if k not in pool or (pool[k]["margin_ils"], pool[k]["fit"]) < (r["margin_ils"], r["fit"]):
                pool[k] = dict(r, _room=room)
    top = sorted(((r["_room"], r["slot"], k), r) for k, r in pool.items())
    top = sorted(top, key=lambda kv: -kv[1]["margin_ils"])[:20]
    L += ["## 20 הכי רווחיים (מבין אלה שעברו)", "", "| # | חדר / עמדה | מוצר | סגנון (fit) | $ מוצר+משלוח | נחיתה | רצועה | רווח | verdict |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for i, ((room, slot, iid), r) in enumerate(top, 1):
        sts = ", ".join("%s %s" % (STYLE_HE[x["style"]], x["fit"]) for x in all_F[room] if x["slot"] == slot and x["item_id"] == iid and x["verdict"] != "reject")
        L.append("| %d | %s / %s | [%s](%s) | %s | %.2f+%.2f%s | %s | %s–%s | %s · %d%% | %s%s |" % (
            i, ROOM_HE[room], slot, (r["title"] or "")[:38].replace("|", "/"), r["url"], sts, r["price_usd"], r["ship_usd"],
            " ×%d" % r["qty"] if r["qty"] > 1 else "", money(r["landed_ils"]), r["retail_band_ils"][0], r["retail_band_ils"][1],
            money(r["margin_ils"]), round(r["margin_pct"] * 100), VERDICT_HE[r["verdict"]], " · כרטיס" if r.get("card_id") else ""))
    L.append("")
    # cards
    L += ["## הכרטיסים החדשים (DRAFT)", "",
          "נכתבו ב-`python3 scripts/ae/ds.py card <id> --slot <room/slot> --sku <SKU של החדר> --id <id> --offline`: מהמטמון בלבד, עם `options` מלא (כל ה-SKU של הספק), ונרשמו ב-`data/sources/seen.json` כ-card. "
          "הם טיוטה כמו כל כרטיס API: צבעים (HEX), משקל ויזואלי, מידות המוצר וטקסטורה ריקים; ה-style_scores הם ציון סינון שלי ולא של המעצב. master-designer מדרג ו-qa-agent בודק.", "",
          "| כרטיס | עמדה | SKU בחדר | נחיתה | רווח | משלוח |", "| --- | --- | --- | --- | --- | --- |"]
    for room in ROOMS:
        seen = set()
        for r in all_F[room]:
            if not r.get("card_id") or r["card_id"] in seen:
                continue
            seen.add(r["card_id"])
            L.append("| `%s` | %s / %s | %s | %s%s | %d%% | %s |" % (r["card_id"], ROOM_HE[room], r["slot"], (r["sku_label"] or "")[:40].replace("|", "/"),
                                                            money(r["landed_ils"]), " (%d יח')" % r["qty"] if r["qty"] > 1 else "", round(r["margin_pct"] * 100),
                                                            "צוטט" if r["ship_basis"].startswith("quoted") else "הערכה"))
    L.append("")
    # freight queue
    q = []
    for room in ROOMS:
        for r in all_F[room]:
            if r["verdict"] in ("best", "alternative") and not r["ship_basis"].startswith("quoted") and r["fit"] >= 7.5:
                q.append((room, r))
    qq = {}
    for room, r in q:
        qq.setdefault((r["item_id"], r["sku"]), (room, r))
    n_default = sum(1 for room in ROOMS for r in all_P[room] if r.get("detail_sku"))
    n_changed = sum(1 for room in ROOMS for r in all_P[room] if r.get("detail_sku") and r.get("sku") != r.get("detail_sku"))
    L += ["## לסשן הבא עם ה-API: משלוח ל-SKU של החדר", "",
          "בשלב 2 נבחר ברוב המקרים ה-SKU הזול (sku-default ב-1,321 מתוך 1,457), שבטקסטיל, בשטיחים ובתמונות הוא המידה הקטנה. שלב 3 בחר מהמטמון את ה-SKU שמתאים למעטפת של העמדה "
          "(השתנה ב-{:,} מתוך {:,} רשומות עם מחיר), אבל המשלוח צוטט רק ל-SKU של שלב 2. "
          "ההערכה: ב-AliExpress Selection Standard (Choice) המשלוח קבוע, 1.99 דולר לפריט בכל 843 הציטוטים של הריצה, בכל מחיר; בשאר החברות המשלוח הוכפל ביחס המחירים בין ה-SKU (מעל פי 1.5) או במודל החבילה של הסטודיו (מתחת). "
          "כדאי לצטט את אלה לפני QA (fit 7.5 ומעלה):".replace("{:,}", "%s") % ("{:,}".format(n_changed), "{:,}".format(n_default)), "", "```"]
    for (iid, sku), (room, r) in qq.items():
        L.append("python3 scripts/ae/ds.py freight %s --sku %s   # %s/%s, %s" % (iid, sku, room, r["slot"], (r["sku_label"] or "")[:40]))
    L += ["```", ""]
    # method
    L += ["## השיטה (שלב 3)", "",
          "1. **SKU של החדר:** מכל רשומה, מתשובת `product.get` השמורה: SKU במלאי, לא \"contact us\", במידה שבמעטפת של העמדה (`data/slots/<room>.json`, ובסלון ה-Design Bible): הזול מבין המתאימים. אם אין מידה שמתאימה בכלל, המוצר יוצא (\"לא פוסלים בגלל אפשרות אחת\": מספיק SKU אחד שמתאים). בתאורה: תקע אירופאי או 220V, אור חם. בתמונה ממוסגרת: רק SKU עם מסגרת (רוב ההדפסים ב-AliExpress הם קנבס בלי מסגרת, Frame mode = Unframed).",
          "2. **כלכלה:** כמו בסטודיו: (מחיר × כמות + משלוח לכמות) × 3.3, רווח ב-econCalc במחיר העליון של הרצועה (`data/economics/market-prices.json` דרך `scripts/ae/scale_config.py`). בעמדת זוג (וילונות, זוג מנורות, פמוטים, ציפיות וכו') הכמות היא מספר היחידות, והרצועה נרשמת ליחידה, כך שהסטודיו מחשב אותו מספר (הנימוק כולל \"price per piece; set of N = N units\").",
          "3. **רשימה קצרה:** בכל עמדה×סגנון, מהמוצרים שנמצאו לסגנון: בלי מוצר שאינו המוצר (מחזיקי מחסניות, אהילים בלי מנורה, נורת USB, תחתיות), בלי מילים אסורות (פלסטיק, מבריק, ניאון, קרטון, LED strip, זהב/קטיפה בנורדי...), בלי חומר עיקרי מפלסטיק, ורווח לפחות 20%. דירוג: ציון החיפוש + 30×רווח + 10 למידה שמתאימה, פחות על משלוח ארוך או מוערך. עד 8.",
          "4. **מבט בתמונה:** כל תמונה ראשית הורדה ונבדקה (בדפי מגע של 12), ונתתי fit 1–10 לכל סגנון שהמוצר נמצא בו (ולפעמים לסגנון נוסף שהוא מתאים לו בבירור), עם נימוק בשורה. בפריטים שנכנסו לכרטיס בדקתי גם את תמונות ה-SKU ובחרתי את הצבע שבתמונה.",
          "5. **השוואה:** מול הכרטיס הקיים בעמדה עם הציון הגבוה לאותו סגנון (בנורדי גם כרטיס בלי ציון, כמו בסטודיו), באותה כמות ובאותו מחיר מכירה. כרטיס בלי משלוח ידוע מקבל 17 דולר, ברירת המחדל של הסטודיו.",
          "6. **כרטיסים:** fit 8 ומעלה ורווח לפחות כמו הכרטיס הקיים (או שאין כרטיס עם ציון לסגנון), עד 3 לעמדה×סגנון.", "",
          "## לשים לב", "",
          "- **רצועות נמוכות מדי:** עציץ רצפה (19–29), אגרטל קטן (29–39), ספל (19), קערה (29–49) ומלח ופלפל לא משאירים 20% אף פעם מ-AliExpress. ברצועת \"עציץ\" יש כנראה עציצים קטנים; לעציץ רצפה של 38 ס\"מ היא לא מתאימה.",
          "- **השוואה לכרטיסים בסטודיו:** לכרטיס וילון שנמכר בזוג הסטודיו מכפיל את רצועת השוק (שהיא כבר לזוג) בכמות (2), ולכן מראה בכרטיס רווח גבוה מדי. ברשומות של `deep-2026-10` הרצועה רשומה לפאנל, והמספר נכון.",
          "- **כפילות:** אותו סט מצעים נמכר בשתי חנויות (1005012855035925, ‏1005012862500672); כרטיס רק לחנות עם המלאי הגדול.",
          "- **רישום במרשם:** רק הכרטיסים. מוצרים שנדחו בתמונה לא סומנו rejected במרשם, כי הדחייה היא לעמדה מסוימת והמרשם הוא למוצר.", ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    F, P, S = {}, {}, {}
    for room in ROOMS:
        F[room] = json.load(open(os.path.join(WORK, "final-%s.json" % room)))
        P[room] = json.load(open(os.path.join(WORK, "prep-%s.json" % room)))
        S[room] = json.load(open(os.path.join(WORK, "short-%s.json" % room)))
        open(os.path.join(OUT, room + ".md"), "w").write(room_md(room, F[room], P[room], S[room]))
    open(os.path.join(OUT, "README.md"), "w").write(readme(F, P, S, None))
    print("ok")
