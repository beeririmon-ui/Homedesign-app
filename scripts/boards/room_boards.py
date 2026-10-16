"""Product boards: one image per room and style, summarising the products chosen so far (2026-10-16).

Sources, in order of authority:
  1. Nordic: data/compositions/<room>-nordic-2026-10-11.json (default + variations).
     Other styles: data/catalog/<style>-2026-10-12.json (designer picks).          -> "chosen"
  2. The final sourcing round: data/leads/final-2026-10-13/results/*.json, cards with a style fit >= 7
     for that style, to fill slots that are still short of 3.                       -> "candidate"
Furniture (kind: fixed-product) is left out: it follows plan B (Israeli suppliers).

  python3 scripts/boards/room_boards.py <out_dir>        # writes <style>-<room>.html and .jpg
"""
import glob, html, json, os, subprocess, sys, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
STYLES = ["nordic", "warm-modern", "japandi", "mediterranean", "modern-country", "boho"]
ST_HE = {"nordic": "נורדי", "warm-modern": "מודרני חם", "japandi": "ג'פנדי", "mediterranean": "ים-תיכוני",
         "modern-country": "כפרי מודרני", "boho": "בוהו"}
ROOMS = ["living-room", "dining-room", "master", "kids", "work", "hall", "corridor", "bath"]
ROOM_HE = {"living-room": "סלון", "dining-room": "מטבח ופינת אוכל", "master": "חדר שינה", "kids": "חדר ילדים",
           "work": "חדר עבודה", "hall": "כניסה", "corridor": "מסדרון", "bath": "חדר רחצה"}


def cards():
    out = {}
    for f in glob.glob("data/products/**/*.json", recursive=True):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        cid = d.get("id") or os.path.basename(f)[:-5]
        urls = (d.get("images") or {}).get("urls") if isinstance(d.get("images"), dict) else d.get("images")
        price = None
        econ = d.get("price") or {}
        if isinstance(econ, dict):
            price = econ.get("retail_ils") or econ.get("suggested_retail")
        out[cid] = {"name": d.get("name") or cid, "urls": urls or [], "price": price}
        out.setdefault(os.path.basename(f)[:-5], out[cid])
    return out


def slots(room):
    d = json.load(open(f"data/slots/{room}.json"))
    return [s for s in d["slots"] if s.get("kind") != "fixed-product"]


def chosen(style, room):
    """slot id -> list of (card_id, price, role)"""
    out = {}
    if style == "nordic":
        p = f"data/compositions/{room}-nordic-2026-10-11.json"
        if not os.path.exists(p):
            return out
        for sid, s in json.load(open(p))["slots"].items():
            lst = []
            if s.get("default") and s["default"].get("card_id"):
                lst.append((s["default"]["card_id"], s["default"].get("price_ils"), "default"))
            for v in s.get("variations") or []:
                if v.get("card_id"):
                    lst.append((v["card_id"], v.get("price_ils"), "variation"))
            out[sid] = {"picks": lst, "status": s.get("status")}
    else:
        p = f"data/catalog/{style}-2026-10-12.json"
        r = (json.load(open(p)).get("rooms") or {}).get(room) or {}
        for sid, s in (r.get("slots") or {}).items():
            lst = [(k["card_id"], k.get("price_ils"), "default" if i == 0 else "variation")
                   for i, k in enumerate(s.get("picks") or []) if k.get("card_id")]
            out[sid] = {"picks": lst, "status": s.get("status")}
    return out


def candidates(style, room):
    out = {}
    for f in glob.glob("data/leads/final-2026-10-13/results/*.json"):
        if os.path.basename(f).startswith("il-"):
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        for key, s in (d.get("slots") or {}).items():
            if not key.startswith(room + "/"):
                continue
            sid = key.split("/", 1)[1]
            for c in s.get("candidates") or []:
                fit = (c.get("style_fit_guess") or {}).get(style)
                try:
                    fit = float(fit or 0)
                except (TypeError, ValueError):
                    fit = 0
                if fit >= 7 and c.get("card_id"):
                    out.setdefault(sid, {})
                    out[sid][c["card_id"]] = max(fit, out[sid].get(c["card_id"], 0))
    return {k: sorted(v.items(), key=lambda x: -x[1]) for k, v in out.items()}


def image(cid, cat, cache):
    local = f"studio/dist/img/p/{cid}.webp"
    if os.path.exists(local):
        return os.path.abspath(local)
    urls = (cat.get(cid) or {}).get("urls") or []
    if not urls:
        return None
    url = urls[0]
    path = os.path.join(cache, hashlib.md5(url.encode()).hexdigest()[:16] + ".jpg")
    if not os.path.exists(path):
        subprocess.run(["curl", "-sL", "--max-time", "25", "-o", path, url], check=False)
    return path if os.path.exists(path) and os.path.getsize(path) > 2000 else None


CSS = """body{font-family:'DejaVu Sans',sans-serif;background:#f4f1ec;color:#2b2622;margin:0;padding:30px 34px;width:1532px}
h1{font-size:34px;margin:0}.sub{font-size:16px;color:#6b625a;margin:6px 0 20px}
.g{display:grid;grid-template-columns:repeat(5,1fr);gap:16px}
.t{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);padding-bottom:10px;position:relative}
.t.empty{background:#ebe6df;box-shadow:none;border:2px dashed #cfc6ba}
.im{aspect-ratio:1/1;background:#f0ece6;overflow:hidden}.im img{width:100%;height:100%;object-fit:cover}
.sl{font-size:14px;font-weight:700;padding:8px 10px 0}.nm{font-size:12px;color:#6b625a;padding:2px 10px;height:30px;overflow:hidden}
.pr{font-size:17px;font-weight:700;padding:2px 10px 0}
.alts{display:flex;gap:4px;padding:6px 10px 0}.alts img{width:44px;height:44px;object-fit:cover;border-radius:6px}
.tag{position:absolute;top:8px;right:8px;font-size:11px;border-radius:9px;padding:2px 8px;background:#2b2622;color:#fff}
.tag.c{background:#c9b28f;color:#2b2622}.miss{font-size:15px;color:#8a7f73;padding:40px 10px;text-align:center}
.legend{font-size:13px;color:#6b625a;margin-top:14px}"""


def board(style, room, cat, cache):
    ch, ca = chosen(style, room), candidates(style, room)
    tiles, n_chosen, n_cand, total = [], 0, 0, 0
    for s in slots(room):
        sid = s["id"]
        name = s.get("name_he") or sid
        picks = (ch.get(sid) or {}).get("picks") or []
        status = (ch.get(sid) or {}).get("status")
        role = "chosen"
        if not picks and ca.get(sid):
            picks = [(cid, (cat.get(cid) or {}).get("price"), "candidate") for cid, _ in ca[sid][:3]]
            role = "candidate"
        picks = [p for p in picks if p[0] in cat]
        if not picks:
            note = "בהמתנה" if status == "on-hold" else "חסר"
            tiles.append(f"<div class='t empty'><div class='miss'>{html.escape(name)}<br><b>{note}</b></div></div>")
            continue
        main = picks[0]
        img = image(main[0], cat, cache)
        alts = "".join(f"<img src='file://{a}'>" for a in [image(p[0], cat, cache) for p in picks[1:3]] if a)
        price = main[1]
        if price:
            total += price
        if role == "chosen":
            n_chosen += 1
        else:
            n_cand += 1
        tag = "<span class='tag'>נבחר</span>" if role == "chosen" else "<span class='tag c'>מועמד</span>"
        tiles.append(f"""<div class='t'>{tag}<div class='im'>{f"<img src='file://{img}'>" if img else ''}</div>
<div class='sl'>{html.escape(name)}</div><div class='nm'>{html.escape(cat[main[0]]['name'][:70])}</div>
<div class='pr'>{f"₪{price:,.0f}" if price else ''}</div><div class='alts'>{alts}</div></div>""")
    n = len(tiles)
    doc = f"""<!doctype html><html dir='rtl' lang='he'><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<h1>{ROOM_HE[room]} · {ST_HE[style]}</h1>
<div class='sub'>{n} עמדות: {n_chosen} עם בחירת מעצב, {n_cand} עם מועמד מהליקוט האחרון, {n - n_chosen - n_cand} חסרות. סכום ברירות המחדל: ₪{total:,.0f}</div>
<div class='g'>{''.join(tiles)}</div>
<div class='legend'>"נבחר": בחירת המעצב (ברירת המחדל, ובקטן הווריאציות). "מועמד": מוצר מהליקוט האחרון בהתאמה 7 ומעלה, שעוד לא עבר את המעצב. בלי ריהוט קבוע (ספקים ישראליים).</div>
</body></html>"""
    return doc, n_chosen, n_cand, n


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    cache = os.path.join(out, "_img")
    os.makedirs(cache, exist_ok=True)
    cat = cards()
    summary = []
    for st in STYLES:
        for room in ROOMS:
            doc, a, b, n = board(st, room, cat, cache)
            open(os.path.join(out, f"{st}-{room}.html"), "w").write(doc)
            summary.append((st, room, a, b, n))
    json.dump(summary, open(os.path.join(out, "summary.json"), "w"), ensure_ascii=False)
    for s in summary:
        print(*s)


if __name__ == "__main__":
    main()
