"""Product boards: one board per room and style, summarising the products chosen so far (2026-10-16).

Sources, in order of authority:
  1. Nordic: data/compositions/<room>-nordic-2026-10-11.json (default + variations).
     Other styles: data/catalog/<style>-2026-10-12.json (designer picks).          -> "chosen"
  2. The final sourcing round: data/leads/final-2026-10-13/results/*.json, cards with a style fit >= 7
     for that style, to fill slots that are still short of 3.                       -> "candidate"
Furniture (kind: fixed-product) is left out: it follows plan B (Israeli suppliers).

  python3 scripts/boards/room_boards.py <out_dir>        # writes <style>-<room>.html and summary.json
                                                         # (the .jpg boards were screenshots of these pages)

As a module this is the single source of the boards' logic: studio/build.py calls boards() and writes the result into
the Studio's data.json ("לוחות חדרים"). boards() reads the repo only and never touches the network; importing the
module has no side effects (the CLI alone changes the working directory, as it always did).

For every product on a board, boards() also gives its supplier, its margin and its status with the supplier (2026-10-17):
  margin   the pick's own margin_pct (composition / catalog), else data/economics/products.json, else the candidate's
           record in the final round (econ[style].margin_pct, margin_pct per style or plain), else none ("לא תומחר").
  status   on hold (the card's notes), missing standard (lighting without a declared CE, IP44 in the bath; toys without
           EN71), shade only (needs the E27 pendant set), loss / under 40%, a candidate not yet reviewed,
           the outreach state of an Israeli supplier (data/suppliers/directory.json), else ready for dropshipping.
"""
import glob, html, json, math, os, re, subprocess, sys, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STYLES = ["nordic", "warm-modern", "japandi", "mediterranean", "modern-country", "boho"]
ST_HE = {"nordic": "נורדי", "warm-modern": "מודרני חם", "japandi": "ג'פנדי", "mediterranean": "ים-תיכוני",
         "modern-country": "כפרי מודרני", "boho": "בוהו"}
ROOMS = ["living-room", "dining-room", "master", "kids", "work", "hall", "corridor", "bath"]
ROOM_HE = {"living-room": "סלון", "dining-room": "מטבח ופינת אוכל", "master": "חדר שינה", "kids": "חדר ילדים",
           "work": "חדר עבודה", "hall": "כניסה", "corridor": "מסדרון", "bath": "חדר רחצה"}
LEGEND_HE = ('"נבחר": בחירת המעצב (ברירת המחדל, ובקטן הווריאציות). "מועמד": מוצר מהליקוט האחרון בהתאמה 7 ומעלה, '
             'שעוד לא עבר את המעצב. בלי ריהוט קבוע (ספקים ישראליים).')
RESULTS_GLOB = "data/leads/final-2026-10-13/results/*.json"
MARGIN_FLOOR = 40.0   # VR1, studio rules ה.11
MARGIN_AMBER = 25.0   # the coordinator's colour bands: >= 40 green, 25-40 amber, below 25 (or a loss) red
TOY_SLOTS = {"kids/toy-cars", "kids/doll", "kids/soft-toy", "kids/doll-pram", "kids/skateboard"}
TOY_STANDARDS = {"EN71", "SI-562", "EN13613"}
DROPSHIP = {"cj": "CJ", "aliexpress": "AliExpress", "zendrop": "Zendrop"}
ON_HOLD_RX = re.compile(r"(?i)(?<!not )\bon[\s-]hold\b")
SHADE_ONLY_RX = re.compile(r"(?i)\bshade only\b")
COOP_STATE = {"sent": "coop-sent", "replied": "coop-replied", "draft": "coop-none", "none": "coop-none"}
# the status with the supplier: code -> (label, tone, the default explanation); a pick keeps only the code, and a "why"
# when it says more than the default. Tones: good / warn / bad / info / neutral (the page maps them to its colours).
STATUS = {
    "on-hold": ("בהמתנה", "bad", "הכרטיס מסומן בהמתנה בהערות"),
    "no-standard": ("חסר תקן", "bad", "אין תקן מוצהר"),
    "shade-set": ("אהיל + סט תלייה", "info", "אהיל בלי חלקי חשמל: נמכר עם סט תלייה E27 עם תקן (S2B חל על הסט)"),
    "loss": ("מפסיד", "bad", "תרומה שלילית"),
    "below-floor": ("מתחת ל-40%", "warn", "מתחת לרף הרווח של 40% (VR1)"),
    "coop-sent": ("פנייה נשלחה", "info", "בקשת שת\"פ נשלחה לספק הישראלי (data/suppliers/directory.json)"),
    "coop-replied": ("ענו", "good", "הספק הישראלי ענה לבקשת השת\"פ (data/suppliers/directory.json)"),
    "coop-none": ("לא פנינו", "neutral", "עוד לא פנינו לספק הישראלי (data/suppliers/directory.json)"),
    "unreviewed": ("מועמד, לא נבדק", "neutral", "מהליקוט האחרון, עוד לא עבר את המעצב"),
    "ready": ("מוכן לדרופשיפינג", "good", "ספק דרופשיפינג, מתומחר, בלי דגל חוסם"),
}
MARGIN_SRC_HE = {"pick": "בחירת המעצב (הרכבה או קטלוג)", "economics": "קובץ התמחור (data/economics/products.json)",
                 "leads": "הליקוט האחרון (final-2026-10-13)"}


def _p(rel):
    return os.path.join(ROOT, rel)


def _num(v):
    """A finite number or None (NaN would make data.json unreadable in the browser)."""
    if isinstance(v, bool) or v is None:
        return None
    try:
        x = float(v) if isinstance(v, (int, float)) else float(str(v).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _load(rel_or_abs):
    try:
        with open(rel_or_abs if os.path.isabs(rel_or_abs) else _p(rel_or_abs), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def cards():
    out = {}
    for f in glob.glob(_p("data/products/**/*.json"), recursive=True):
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
        sup = d.get("supplier") if isinstance(d.get("supplier"), dict) else {}
        out[cid] = {"id": cid, "name": d.get("name") or cid, "urls": urls or [], "price": price,
                    "supplier": sup, "safety": d.get("safety") if isinstance(d.get("safety"), dict) else {},
                    "notes": d.get("notes") if isinstance(d.get("notes"), str) else "",
                    "currency": econ.get("currency") if isinstance(econ, dict) else None}
        out.setdefault(os.path.basename(f)[:-5], out[cid])
    return out


def slots(room):
    d = json.load(open(_p(f"data/slots/{room}.json")))
    return [s for s in d["slots"] if s.get("kind") != "fixed-product"]


def chosen(style, room):
    """slot id -> {"picks": [(card_id, price, role, extra)], "status"}; extra holds the pick's margin_pct and flag."""
    out = {}

    def extra(k):
        return {"margin_pct": k.get("margin_pct"), "flag": k.get("flag")}
    if style == "nordic":
        p = _p(f"data/compositions/{room}-nordic-2026-10-11.json")
        if not os.path.exists(p):
            return out
        for sid, s in json.load(open(p))["slots"].items():
            lst = []
            if s.get("default") and s["default"].get("card_id"):
                lst.append((s["default"]["card_id"], s["default"].get("price_ils"), "default", extra(s["default"])))
            for v in s.get("variations") or []:
                if v.get("card_id"):
                    lst.append((v["card_id"], v.get("price_ils"), "variation", extra(v)))
            out[sid] = {"picks": lst, "status": s.get("status")}
    else:
        p = _p(f"data/catalog/{style}-2026-10-12.json")
        r = (json.load(open(p)).get("rooms") or {}).get(room) or {}
        for sid, s in (r.get("slots") or {}).items():
            lst = [(k["card_id"], k.get("price_ils"), "default" if i == 0 else "variation", extra(k))
                   for i, k in enumerate(s.get("picks") or []) if k.get("card_id")]
            out[sid] = {"picks": lst, "status": s.get("status")}
    return out


def lead_results():
    """[(file name, data)] of the final round, without the Israeli-shop files (il-*), in the order the CLI always read them."""
    out = []
    for f in glob.glob(_p(RESULTS_GLOB)):
        if os.path.basename(f).startswith("il-"):
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        out.append((os.path.basename(f), d))
    return out


def candidates(style, room, results=None):
    out = {}
    for _, d in (results if results is not None else lead_results()):
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


# --------------------------------------------------------------------------- supplier, margin, status (2026-10-17)

def _style_val(v, style):
    return v.get(style) if isinstance(v, dict) else v


def _record_margin(c, style):
    """(margin %, the price it was computed at) from one final-round candidate record, or None."""
    price = _num(_style_val(c.get("price_ils"), style)) or _num(_style_val(c.get("slot_price_ils"), style))
    e = c.get("econ")
    if isinstance(e, dict) and isinstance(e.get(style), dict):
        m = _num(e[style].get("margin_pct"))
        if m is not None:
            return m, _num(_style_val(c.get("slot_price_ils"), style)) or price
    for k in ("margin_pct", "margin_at_slot_price_pct"):
        m = _num(_style_val(c.get(k), style))
        if m is not None:
            return m, price
    return None


class Context:
    """Everything the boards read once: the cards, the final round, the pricing file and the supplier directory."""

    def __init__(self, cat=None):
        self.cat = cat if cat is not None else cards()
        self.results = lead_results()
        eco = _load("data/economics/products.json") or {}
        self.economics = eco.get("products") if isinstance(eco.get("products"), dict) else {}
        directory = _load("data/suppliers/directory.json") or {}
        self.directory = [s for s in directory.get("suppliers") or [] if isinstance(s, dict)]
        self.slot_cat = {}
        for room in ROOMS:
            try:
                for s in json.load(open(_p(f"data/slots/{room}.json")))["slots"]:
                    self.slot_cat[f"{room}/{s['id']}"] = s.get("category")
            except Exception:
                pass
        # final-round records per (room/slot, card) and per card: the repriced ones (an Israeli-value price) first,
        # then the newest file
        self.records, self.records_any = {}, {}
        for fname, d in self.results:
            date = str(d.get("date") or "")
            for key, s in (d.get("slots") or {}).items():
                for c in (s.get("candidates") or []) if isinstance(s, dict) else []:
                    if isinstance(c, dict) and c.get("card_id"):
                        rec = (0 if c.get("price_ils") in (None, "", {}) else 1, date, fname, c)
                        self.records.setdefault((key, c["card_id"]), []).append(rec)
                        self.records_any.setdefault(c["card_id"], []).append(rec)
        for v in list(self.records.values()) + list(self.records_any.values()):
            v.sort(key=lambda r: (r[0], r[1], r[2]), reverse=True)


def supplier_of(card):
    sup = card.get("supplier") or {}
    name, url = str(sup.get("name") or ""), str(sup.get("product_url") or "")
    n, host = name.lower(), (re.match(r"https?://([^/]+)", url) or [None, ""])[1].lower()
    if re.search(r"\bcj\b|cjdropshipping", n) or "cjdropshipping" in host:
        key = "cj"
    elif "zendrop" in n or "zendrop" in host:
        key = "zendrop"
    elif "aliexpress" in n or "aliexpress" in host:
        key = "aliexpress"
    elif str(card.get("currency") or "").upper() == "ILS" or host.endswith(".co.il") or re.search(r"[֐-׿]", name):
        key = "il"
    else:
        key = "other" if name else None
    return {"key": key, "name": DROPSHIP.get(key) or name or None}


def _coop(ctx, name):
    """The outreach state of an Israeli supplier from data/suppliers/directory.json (coop_request / outreach)."""
    low = (name or "").strip().lower()
    if not low:
        return None
    for s in ctx.directory:
        names = [str(s.get(k) or "").strip().lower() for k in ("name", "id", "name_he", "name_en")]
        if low in names or any(n and (n in low or low in n) for n in names if len(n) >= 3):
            for k in ("coop_request", "outreach"):
                o = s.get(k)
                if isinstance(o, dict) and o.get("state") in COOP_STATE:
                    return o["state"]
            return "none"
    return "none"


def margin_of(ctx, style, room, sid, cid, extra, role):
    """{pct, price, src, flag, tone} or None. Order: the pick, the pricing file, the final round."""
    flag = None
    if role != "candidate" and extra:
        m = _num(extra.get("margin_pct"))
        if m is not None:
            f = str(extra.get("flag") or "")
            flag = "loss" if m < 0 else "ok" if m >= MARGIN_FLOOR else "below-floor"
            return _tone({"pct": m, "price": None, "src": "pick", "flag": flag, "exception": f.startswith("exception") or None})
    e = ctx.economics.get(cid)
    if isinstance(e, dict) and _num(e.get("margin_pct")) is not None:
        m = _num(e["margin_pct"])
        flag = e.get("flag") if e.get("flag") in ("ok", "below-floor", "loss") else None
        return _tone({"pct": m, "price": _num(e.get("retail_ils")), "src": "economics",
                      "flag": flag or ("loss" if m < 0 else "ok" if m >= MARGIN_FLOOR else "below-floor")})
    for rec in ctx.records.get((f"{room}/{sid}", cid), []) + ctx.records_any.get(cid, []):
        got = _record_margin(rec[3], style)
        if got:
            m, price = got
            return _tone({"pct": m, "price": price, "src": "leads", "file": rec[2],
                          "flag": "loss" if m < 0 else "ok" if m >= MARGIN_FLOOR else "below-floor"})
    return None


def _tone(m):
    pct = m["pct"]
    m["pct"] = round(pct, 1)
    m["tone"] = "bad" if (m.get("flag") == "loss" or pct < MARGIN_AMBER) else "good" if pct >= MARGIN_FLOOR else "warn"
    return {k: v for k, v in m.items() if v is not None}


def statuses_of(ctx, room, sid, card, sup, margin, role, price):
    """The product's status with the supplier, most important first: [{code, why?}] (labels in STATUS)."""
    out = []

    def add(code, why=None):
        out.append({"code": code, "why": why} if why and why != STATUS[code][2] else {"code": code})
    notes = card.get("notes") or ""
    safety = card.get("safety") or {}
    key = f"{room}/{sid}"
    if ON_HOLD_RX.search(notes):
        m = ON_HOLD_RX.search(notes)
        add("on-hold", notes[max(0, notes.rfind("|", 0, m.start()) + 1):m.end() + 140].strip()[:240])
    if ctx.slot_cat.get(key) == "lighting":
        if SHADE_ONLY_RX.search(str(safety.get("source") or "")) or SHADE_ONLY_RX.search(notes):
            add("shade-set")
        elif safety.get("ce") is not True:
            add("no-standard", "תאורה בלי CE מוצהר")
        elif room == "bath" and not re.search(r"IP\s*(?:4[4-9]|[5-6]\d)", str(safety.get("ip_rating") or ""), re.I):
            add("no-standard", "תאורה במקלחת בלי IP44 מוצהר")
    if key in TOY_SLOTS and not (set(safety.get("toy_standard") or []) & TOY_STANDARDS):
        add("no-standard", "צעצוע בלי EN71 מוצהר")
    if margin and margin.get("flag") == "loss":
        add("loss")
    elif margin and margin.get("flag") == "below-floor":
        add("below-floor", "חריג שהמעצב אישר: אין בעמדה חלופה שעוברת 40% (ה.11)" if margin.get("exception") else None)
    if sup.get("key") == "il":
        add(COOP_STATE.get(_coop(ctx, sup.get("name")), "coop-none"))
    if role == "candidate":
        add("unreviewed")
    elif not out and sup.get("key") in DROPSHIP and (margin or price):
        add("ready")
    return out


# --------------------------------------------------------------------------- the boards as data

def board_data(style, room, cat=None, ctx=None):
    """One board: the slots in the slot file's order, with status chosen / candidate / missing / on-hold."""
    ctx = ctx or Context(cat)
    cat = ctx.cat
    ch, ca = chosen(style, room), candidates(style, room, ctx.results)
    out, n_chosen, n_cand, n_hold, total = [], 0, 0, 0, 0
    for s in slots(room):
        sid = s["id"]
        name = s.get("name_he") or sid
        picks = (ch.get(sid) or {}).get("picks") or []
        status = (ch.get(sid) or {}).get("status")
        role = "chosen"
        if not picks and ca.get(sid):
            picks = [(cid, (cat.get(cid) or {}).get("price"), "candidate", None) for cid, _ in ca[sid][:3]]
            role = "candidate"
        picks = [p for p in picks if p[0] in cat]
        row = {"id": sid, "name_he": name}
        if not picks:
            row["status"] = "on-hold" if status == "on-hold" else "missing"
            n_hold += row["status"] == "on-hold"
            out.append(row)
            continue
        main = picks[0]
        price = main[1]
        if price:
            total += price
        if role == "chosen":
            n_chosen += 1
        else:
            n_cand += 1
        rows = []
        for p in picks:
            card = cat[p[0]]
            row_p = {"card_id": card["id"], "price": p[1], "role": p[2], "supplier": None, "margin": None, "supplier_status": []}
            try:  # a malformed card or record never stops the boards: the page shows "—" for what is missing
                sup = supplier_of(card)
                margin = margin_of(ctx, style, room, sid, card["id"], p[3] if len(p) > 3 else None, p[2])
                row_p.update({"supplier": sup, "margin": margin,
                              "supplier_status": statuses_of(ctx, room, sid, card, sup, margin, role, p[1])})
            except Exception as e:
                row_p["error"] = f"{type(e).__name__}: {e}"[:160]
            rows.append(row_p)
        row.update({"status": role, "main_role": main[2], "picks": rows})
        out.append(row)
    n = len(out)
    return {"style": style, "room": room, "style_he": ST_HE[style], "room_he": ROOM_HE[room], "slots": out,
            "counts": {"slots": n, "chosen": n_chosen, "candidate": n_cand, "missing": n - n_chosen - n_cand, "on_hold": n_hold},
            "total": total}


def boards(cat=None):
    """All 48 boards (STYLES x ROOMS) as data, with the labels and the legend. Reads the repo only."""
    ctx = Context(cat)
    return {"styles": [{"id": s, "he": ST_HE[s]} for s in STYLES], "rooms": [{"id": r, "he": ROOM_HE[r]} for r in ROOMS],
            "legend_he": LEGEND_HE, "margin_floor": MARGIN_FLOOR, "margin_amber": MARGIN_AMBER,
            "status_labels": {k: {"he": v[0], "tone": v[1], "why": v[2]} for k, v in STATUS.items()},
            "margin_src_he": MARGIN_SRC_HE,
            "boards": [board_data(st, room, ctx=ctx) for st in STYLES for room in ROOMS]}


# --------------------------------------------------------------------------- the CLI: one HTML page per board

def image(cid, cat, cache):
    local = _p(f"studio/dist/img/p/{cid}.webp")
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


def board(style, room, cat, cache, ctx=None):
    b = board_data(style, room, ctx=ctx or Context(cat))
    tiles = []
    for s in b["slots"]:
        name = s["name_he"]
        if s["status"] in ("missing", "on-hold"):
            note = "בהמתנה" if s["status"] == "on-hold" else "חסר"
            tiles.append(f"<div class='t empty'><div class='miss'>{html.escape(name)}<br><b>{note}</b></div></div>")
            continue
        main = s["picks"][0]
        img = image(main["card_id"], cat, cache)
        alts = "".join(f"<img src='file://{a}'>" for a in [image(p["card_id"], cat, cache) for p in s["picks"][1:3]] if a)
        price = main["price"]
        tag = "<span class='tag'>נבחר</span>" if s["status"] == "chosen" else "<span class='tag c'>מועמד</span>"
        tiles.append(f"""<div class='t'>{tag}<div class='im'>{f"<img src='file://{img}'>" if img else ''}</div>
<div class='sl'>{html.escape(name)}</div><div class='nm'>{html.escape(cat[main['card_id']]['name'][:70])}</div>
<div class='pr'>{f"₪{price:,.0f}" if price else ''}</div><div class='alts'>{alts}</div></div>""")
    c = b["counts"]
    n, n_chosen, n_cand, total = c["slots"], c["chosen"], c["candidate"], b["total"]
    doc = f"""<!doctype html><html dir='rtl' lang='he'><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<h1>{ROOM_HE[room]} · {ST_HE[style]}</h1>
<div class='sub'>{n} עמדות: {n_chosen} עם בחירת מעצב, {n_cand} עם מועמד מהליקוט האחרון, {n - n_chosen - n_cand} חסרות. סכום ברירות המחדל: ₪{total:,.0f}</div>
<div class='g'>{''.join(tiles)}</div>
<div class='legend'>{LEGEND_HE}</div>
</body></html>"""
    return doc, n_chosen, n_cand, n


def main():
    os.chdir(ROOT)  # as before: a relative <out_dir> is relative to the repo root
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    cache = os.path.join(out, "_img")
    os.makedirs(cache, exist_ok=True)
    ctx = Context()
    summary = []
    for st in STYLES:
        for room in ROOMS:
            doc, a, b, n = board(st, room, ctx.cat, cache, ctx)
            open(os.path.join(out, f"{st}-{room}.html"), "w").write(doc)
            summary.append((st, room, a, b, n))
    json.dump(summary, open(os.path.join(out, "summary.json"), "w"), ensure_ascii=False)
    for s in summary:
        print(*s)


if __name__ == "__main__":
    main()
