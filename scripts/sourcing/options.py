#!/usr/bin/env python3
"""Supplier options on product cards (studio rules ג, 2026-10-11, "כל האפשרויות של הספק בדף המוצר").

The `options` object of data/product-card.schema.json lists every SKU the supplier sells for a product, on the axes
the product page lets the customer choose from (size, length, width, color, pattern, finish, style, set, other).
The room shows only `default_sku` (in_room); the card's top-level price and supplier.sku stay those of default_sku.

Shared by the card writers and their no-API backfills:
  scripts/ae/ds.py             card (writes options) · backfill-options (from data/sources/aliexpress/<id>.json)
  scripts/sourcing/cj_source.py options · backfill-options (from data/sources/cj/<pid>.json)

  from_variants(rows, default_sku)   rows of {id, props: [(name_src, label_src, image)], price, currency, stock, image,
                                     shipping_il} -> (options, None) or (None, reason)
  validate(options, card=None)       -> (errors, warnings); errors mirror the JSON schema plus the cross-field rules
  write_options(path, options)       splices the "options" member into the card text (the rest of the file is kept
                                     byte for byte); never replaces options whose source is "manual"

CLI (no network):
  python3 -I scripts/sourcing/options.py validate [card.json ...]   every card under data/products when no path
  python3 -I scripts/sourcing/options.py summary                     cards with options, by supplier
"""
import json, os, re, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PRODUCTS = os.path.join(REPO, "data", "products")

AXES = ("size", "length", "width", "color", "pattern", "finish", "style", "set", "other")
AXIS_HE = {"size": "מידה", "length": "אורך", "width": "רוחב", "color": "צבע", "pattern": "דוגמה", "finish": "גימור",
           "style": "דגם", "set": "כמות", "other": "אפשרות"}
# order on the product page: the look first (colour, pattern...), then the fit (size...), then quantity
AXIS_ORDER = ("color", "pattern", "finish", "style", "size", "length", "width", "set", "other")
VALUE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
CUR = re.compile(r"^[A-Z]{3}$")
DAYS = re.compile(r"^[0-9]+(-[0-9]+)?$")

# Values a seller lists that are not a product one can order as is (custom work, "message us").
BOGUS = re.compile(r"contact\s*us|custom(?:ized|ised)?\s*(?:size|made|order)?$|^custom|please\s+(?:contact|leave|message)|message\s+us|"
                   r"leave\s+(?:a\s+)?(?:message|note)|remark|link\s+for|price\s+difference|extra\s+fee|shipping\s+fee", re.I)
SHIPS_FROM = re.compile(r"ships?\s*from|shipping\s*from|send\s*from|origin|发货地", re.I)
# Fixed to the room's SKU, never a customer choice: the origin, and the plug type (the room's is the one checked for IL).
PLUG_NAME = re.compile(r"plug|electrical\s*outlet|socket\s*type|规格插头", re.I)
PLUG_VALUE = re.compile(r"^(?:us|eu|uk|au|il|jp|cn|kr|br|in|ch|it|za)(?:\s*plug)?$|\bplug\b", re.I)

# ----------------------------------------------------------------------------- labels

COLORS = {
    "white": ("לבן", "#F4F2EE"), "off white": ("לבן שבור", "#EEE9DF"), "off-white": ("לבן שבור", "#EEE9DF"),
    "milk white": ("לבן חלבי", "#F1ECE2"), "cream": ("קרם", "#EFE6D2"), "cream white": ("לבן קרם", "#F0E9DA"),
    "ivory": ("שנהב", "#F2EBDD"), "beige": ("בז'", "#D9CBB3"), "khaki": ("חאקי", "#BFAE8A"), "camel": ("קאמל", "#B8915F"),
    "sand": ("חול", "#D6C3A3"), "oatmeal": ("שיבולת שועל", "#D8CCB6"), "linen": ("פשתן", "#D9CDB8"), "natural": ("טבעי", "#CDB58F"),
    "apricot": ("משמש", "#E8C2A0"), "taupe": ("טאופ", "#9C8C7C"), "milk tea": ("תה חלב", "#C9AE8F"), "coffee": ("קפה", "#6F4E37"),
    "brown": ("חום", "#7A5A40"), "chocolate": ("שוקולד", "#5A3D2B"), "tan": ("חום בהיר", "#C1A07A"), "caramel": ("קרמל", "#B07A44"),
    "walnut": ("אגוז", "#6B4A32"), "oak": ("אלון", "#B98E5E"), "wood": ("עץ", "#A57C52"), "wood color": ("בגוון עץ", "#A57C52"),
    "black": ("שחור", "#1E1E1E"), "grey": ("אפור", "#9A9A96"), "gray": ("אפור", "#9A9A96"), "charcoal": ("פחם", "#3E3E3C"),
    "silver": ("כסף", "#C0C0C0"), "gold": ("זהב", "#C9A54A"), "brass": ("פליז", "#B5944B"), "copper": ("נחושת", "#B87333"),
    "green": ("ירוק", "#5E7D5A"), "sage": ("מרווה", "#A3AE92"), "sage green": ("ירוק מרווה", "#A3AE92"), "olive": ("זית", "#7A7A4A"),
    "army green": ("ירוק צבאי", "#5B5E3A"), "grey green": ("ירוק-אפור", "#8C978A"), "gray green": ("ירוק-אפור", "#8C978A"),
    "mint": ("מנטה", "#B8D8C4"), "emerald": ("אזמרגד", "#2E7D5B"), "teal": ("טורקיז כהה", "#2F6F73"),
    "blue": ("כחול", "#4A6A94"), "navy": ("כחול נייבי", "#24324F"), "navy blue": ("כחול נייבי", "#24324F"),
    "sky blue": ("תכלת", "#9CC3DE"), "haze blue": ("כחול אפרפר", "#8DA0B3"),
    "pink": ("ורוד", "#E3B7BC"), "rose": ("ורוד עתיק", "#C9989C"), "red": ("אדום", "#B23A32"), "brick red": ("אדום לבנים", "#9C4A35"),
    "rust red": ("אדום חלודה", "#9E4A2F"), "orange rust red": ("כתום חלודה", "#B5532F"),
    "wine": ("יין", "#6E2A35"), "wine red": ("אדום יין", "#6E2A35"), "burgundy": ("בורדו", "#6D2232"), "orange": ("כתום", "#D9822B"),
    "rust": ("חלודה", "#A4532D"), "terracotta": ("טרקוטה", "#B5653F"), "yellow": ("צהוב", "#E3C34F"), "mustard": ("חרדל", "#C49A2C"),
    "purple": ("סגול", "#6E4F86"), "lavender": ("לבנדר", "#B7A6CC"), "coral": ("אלמוג", "#E07C66"),
    "transparent": ("שקוף", "#E8ECEE"), "clear": ("שקוף", "#E8ECEE"), "multicolor": ("צבעוני", None), "multi": ("צבעוני", None),
}
SHADES = {"light": ("בהיר", 0.35), "dark": ("כהה", -0.35), "deep": ("עמוק", -0.25), "pale": ("חיוור", 0.45)}
WORDS = {  # words around a colour or a size; a phrase is translated only when every word is known, else kept as is
    "tulle": "טול", "linen": "פשתן", "cotton": "כותנה", "velvet": "קטיפה", "boucle": "בוקלה", "yarn": "חוט", "sheer": "שקוף",
    "no candle": "בלי נר", "with candle": "עם נר", "linen like curtain": "וילון במראה פשתן", "set": "סט", "matte": "מט",
    "glossy": "מבריק", "glaze": "מזוגג", "ceramic": "קרמיקה", "metal": "מתכת", "pillowcase": "ציפית", "pillow case": "ציפית",
    "pillow": "כרית", "cushion": "כרית", "pillow core": "מילוי", "with core": "עם מילוי", "without core": "בלי מילוי",
    "pillow core and pillowcase": "כרית עם מילוי", "cover only": "ציפית בלבד", "single": "יחיד", "double": "זוגי",
    "curtain": "וילון", "single curtain": "וילון אחד", "panel": "יריעה", "pair": "זוג", "a pair": "זוג", "1 pair": "זוג",
    "bed sheet": "סדין", "flat sheet": "סדין שטוח", "fitted sheet": "סדין עם גומי", "quilt cover": "ציפה לשמיכה",
    "duvet cover": "ציפה לשמיכה", "frameless": "בלי מסגרת", "frameless painting": "בלי מסגרת", "with frame": "עם מסגרת",
    "black frame": "מסגרת שחורה", "white frame": "מסגרת לבנה", "wood frame": "מסגרת עץ", "tall": "גבוה", "short": "נמוך",
    "low": "נמוך", "high": "גבוה", "round": "עגול", "square": "מרובע", "tassel": "פרנזים", "with tassel": "עם פרנזים",
    "warm light": "אור חם", "white light": "אור לבן", "neutral light": "אור ניטרלי", "tricolor light": "אור בשלושה גוונים",
    "three colors": "אור בשלושה גוונים", "tri color": "אור בשלושה גוונים", "no light source": "בלי נורה",
    "light source not included": "בלי נורה", "with pull switch": "עם מתג משיכה", "without pull switch": "בלי מתג משיכה",
    "remote control": "שלט רחוק", "bottle": "בקבוק", "medium bottle": "בקבוק בינוני", "tall bottle": "בקבוק גבוה",
    "low bottle": "בקבוק נמוך", "tall style": "דגם גבוה", "short style": "דגם נמוך", "default": "רגיל", "original": "מקורי",
    "seat": "מושב", "1 seat": "מושב אחד", "single seat": "מושב אחד", "double seat": "שני מושבים", "three seat": "שלושה מושבים",
    "four seat": "ארבעה מושבים", "five seat": "חמישה מושבים",
}
HEADINGS = [  # curtain heading ("Processing")
    (r"hidden\s*back\s*tab", "לולאות נסתרות"), (r"grommet.*ring|ring", "טבעות"), (r"white\s*grommet", "טבעות לבנות"),
    (r"grommet|eyelet", "טבעות מתכת"), (r"multi\s*fu?nc?tion\s*tape", "סרט רב-שימושי"), (r"pleat|tape", "סרט קפלים"),
    (r"rod\s*pocket", "מנהרה למוט"), (r"s\s*fold|wave", "קפלי S"), (r"velcro", "סקוטש"), (r"hook", "ווים"), (r"tab\s*top", "לולאות"),
]
SIZE_WORDS = {"small": "קטן", "medium": "בינוני", "middle": "בינוני", "large": "גדול", "big": "גדול", "mini": "מיני",
              "extra large": "גדול מאוד", "x-large": "גדול מאוד", "xl": "XL", "l": "L", "m": "M", "s": "S", "xs": "XS", "xxl": "XXL"}
KELVIN = re.compile(r"\b\d{4}\s*k\b|warm\s*(?:white|light)|cold\s*(?:white|light)|cool\s*(?:white|light)|neutral\s*(?:white|light)|"
                    r"natural\s*light|white\s*light|daylight|tri-?colou?r", re.I)
NUM = r"(\d+(?:\.\d+)?)"
CM = r"\s*(?:cm|厘米)?"
DIMS = re.compile(NUM + CM + r"\s*[x×*]\s*[a-z]?\s*" + NUM + CM + r"(?:\s*[x×*]\s*[a-z]?\s*" + NUM + CM + r")?", re.I)
WH = re.compile(r"\bw\s*" + NUM + r"\s*cm\s*[x×*]?\s*(?:[hl])\s*" + NUM + r"\s*cm", re.I)
PCS = re.compile(r"^\s*(\d+)\s*(?:pc|pcs|piece|pieces|panel|panels)\b", re.I)
ONE_LEN = re.compile(r"^\s*(diameter\s*|dia\.?\s*|d\s*|h\s*|height\s*|length\s*)?" + NUM + r"\s*(cm|mm|m|inches|inch|in|\")\s*$", re.I)
LETTER = re.compile(r"^(?:[a-z]|(?:style|type|model|no\.?|design)\s*[a-z0-9]+|[a-z]\d{0,2})$", re.I)
SET = re.compile(r"^\s*(?:(\d+)\s*(?:pc|pcs|piece|pieces|set|sets)|set\s*of\s*(\d+)|(\d+)\s*-?\s*piece\s*set)\s*$", re.I)


def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def slug(s):
    s = clean(s).lower().replace("×", "x").replace("*", "x")
    s = re.sub(r"[^a-z0-9.]+", "-", s).strip("-.")
    return s[:60].strip("-.") or "v"


def fmt_num(x):
    f = float(x)
    return str(int(f)) if f == int(f) else ("%g" % f)


def shade_hex(hex_, k):
    if not hex_:
        return None
    rgb = [int(hex_[i:i + 2], 16) for i in (1, 3, 5)]
    rgb = [round(c + (255 - c) * k) if k > 0 else round(c * (1 + k)) for c in rgb]
    return "#%02X%02X%02X" % tuple(max(0, min(255, c)) for c in rgb)


def color_of(label):
    """'Light Camel' -> ('קאמל בהיר', hex); 'Beige Tulle' -> ("בז' (טול)", hex); unknown -> (None, None)."""
    low = clean(label).lower().replace("_", " ")
    if low in COLORS:
        return COLORS[low]
    if low in WORDS:
        return WORDS[low], None
    toks = re.split(r"[\s/,+&-]+", low)
    for n in (3, 2, 1):  # the longest colour phrase anywhere in the label
        for i in range(len(toks) - n + 1):
            phrase = " ".join(toks[i:i + n])
            if phrase not in COLORS:
                continue
            he, hx = COLORS[phrase]
            shade = SHADES.get(toks[i - 1]) if i > 0 else None
            if shade:
                he, hx = "%s %s" % (he, shade[0]), shade_hex(hx, shade[1])
            rest = " ".join(t for j, t in enumerate(toks) if not (i <= j < i + n) and not (shade and j == i - 1))
            if rest:
                he = "%s (%s)" % (he, words_he(rest))
            return he, hx
    return None, None


def words_he(s):
    """Hebrew for a short phrase when every word is known (WORDS, COLORS), else the phrase as the supplier wrote it."""
    s = clean(s)
    low = s.lower()
    if not low:
        return ""
    if low in WORDS:
        return WORDS[low]
    if low in COLORS:
        return COLORS[low][0]
    toks = [x for x in re.split(r"[\s/,+&]+", low) if x]
    if toks and all(x in WORDS or x in COLORS for x in toks):
        return " ".join(WORDS.get(x) or COLORS[x][0] for x in toks)
    return s


def size_of(label):
    """-> (id, label_he, sort_key) for a size-like label, else None. Other words stay: 'Single Curtain 100x180' ->
    '100×180 ס"מ (וילון אחד)'."""
    lab = clean(label)
    low = lab.lower()
    pcs = PCS.match(lab)
    n = int(pcs.group(1)) if pcs else 1
    m = WH.search(lab)
    dims, span = ((m.group(1), m.group(2)), m.span()) if m else (None, None)
    if not dims:
        d = DIMS.search(lab)
        if d and not KELVIN.search(lab):
            dims, span = tuple(x for x in d.groups() if x), d.span()
    if dims:
        rest = lab[:span[0]] + " " + lab[span[1]:]
        if pcs:
            rest = rest.replace(pcs.group(0).strip(), " ", 1)
        rest = clean(re.sub(r"(?i)\b(?:size|cm|mm|w|h|l|d)\b|[-–(),:]", " ", rest))
        txt = "×".join(fmt_num(x) for x in dims)
        vid = "x".join(fmt_num(x) for x in dims)
        he = '%s ס"מ' % txt
        if n > 1:
            vid, he = "%dpc-%s" % (n, vid), "%d יח', %s" % (n, he)
        if rest:
            vid, he = "%s-%s" % (vid, slug(rest)), "%s (%s)" % (he, words_he(rest))
        return vid, he, (n, [float(x) for x in dims], rest.lower())
    m = ONE_LEN.match(lab)
    if m:
        unit = m.group(3).lower()
        unit = "inch" if unit.startswith("inch") else unit
        unit_he = {"cm": 'ס"מ', "mm": 'מ"מ', "m": "מ'", "inch": "אינץ'", "in": "אינץ'", '"': "אינץ'"}[unit]
        what = {"diameter": "קוטר ", "dia": "קוטר ", "dia.": "קוטר ", "d": "קוטר ", "height": "גובה ", "h": "גובה ", "length": "אורך "}.get(clean(m.group(1)).lower(), "")
        return "%s%s" % (fmt_num(m.group(2)), "" if unit == "cm" else unit.replace('"', "in")), "%s%s %s" % (what, fmt_num(m.group(2)), unit_he), (1, [float(m.group(2))], "")
    if low in SIZE_WORDS:
        order = ["xs", "s", "mini", "small", "m", "medium", "middle", "l", "large", "big", "xl", "x-large", "extra large", "xxl"]
        return slug(low), SIZE_WORDS[low], (1, [float(order.index(low)) if low in order else 50.0], "")
    return None


def is_size(labels):
    return bool(labels) and all(size_of(l) for l in labels)


def is_kelvin(labels):
    return bool(labels) and all(KELVIN.search(l) for l in labels)


def is_letter(labels):
    return bool(labels) and all(LETTER.match(clean(l)) and not size_of(l) for l in labels)


def is_set(labels):
    return bool(labels) and all(SET.match(l) for l in labels)


def is_heading(labels):
    return bool(labels) and all(any(re.search(p, l, re.I) for p, _ in HEADINGS) for l in labels)


def is_color(labels):
    return bool(labels) and all(color_of(l)[0] for l in labels)


def classify(name, labels):
    """(axis id, name_he) for one supplier property. The values win over the seller's name ("Color: Large/Small" is a size)."""
    n = clean(name).lower()
    if is_kelvin(labels) or re.search(r"colou?r\s*temperature|light\s*colou?r|light\s*source", n):
        return "other", "גוון אור"
    if is_heading(labels) or re.search(r"processing|heading|header|curtain\s*(?:top|type)", n):
        return "style", "סוג תלייה"
    if is_set(labels) or re.search(r"quantity|number\s*of|pcs|package|^set$|bundle", n):
        return "set", "כמות"
    if is_size(labels):
        if re.search(r"length", n):
            return "length", AXIS_HE["length"]
        if re.search(r"width", n):
            return "width", AXIS_HE["width"]
        return "size", AXIS_HE["size"]
    if is_letter(labels):
        return "style", "דגם"
    if re.search(r"colou?r", n):
        return "color", AXIS_HE["color"]
    if re.search(r"pattern|print", n):
        return "pattern", AXIS_HE["pattern"]
    if re.search(r"material|finish|surface", n):
        return "finish", "חומר" if "material" in n else AXIS_HE["finish"]
    if re.search(r"style|type|model|design|shape", n):
        return "style", AXIS_HE["style"]
    if re.search(r"size|dimension|specification|spec", n):
        return "size", AXIS_HE["size"]
    if re.search(r"length", n):
        return "length", AXIS_HE["length"]
    if re.search(r"width", n):
        return "width", AXIS_HE["width"]
    if is_color(labels):
        return "color", AXIS_HE["color"]
    return "other", AXIS_HE["other"]


def value_of(axis, label):
    """-> dict(id, label_he, label_src[, hex]) and a sort key."""
    lab = clean(label)
    v = {"id": slug(lab), "label_he": lab, "label_src": lab}
    key = None
    if axis in ("size", "length", "width"):
        s = size_of(lab)
        if s:
            v["id"], v["label_he"], key = s
    elif axis == "color":
        he, hx = color_of(lab)
        if he:
            v["id"] = slug(lab)
            v["label_he"] = he
        if hx:
            v["hex"] = hx
    elif axis == "set":
        m = SET.match(lab)
        k = int(next((g for g in m.groups() if g), 1)) if m else None
        if k:
            v["id"], v["label_he"], key = ("%dpc" % k), ("יחידה אחת" if k == 1 else "%d יחידות" % k), (k, [], "")
    elif axis == "style":
        for pat, he in HEADINGS:
            if re.search(pat, lab, re.I):
                v["label_he"] = he
                break
        else:
            if re.match(r"^[a-z]$|^[a-z]\d{0,2}$", lab, re.I):
                v["label_he"] = "דגם %s" % lab.upper()
                key = (0, [float(ord(lab[0].upper()))] + [float(x) for x in re.findall(r"\d+", lab)], "")
    if axis in ("style", "other", "finish", "pattern", "set") and v["label_he"] == lab:
        v["label_he"] = words_he(lab)
    if axis == "other" and KELVIN.search(lab) and v["label_he"] == lab:
        k = re.search(r"(\d{4})\s*k", lab, re.I)
        low = lab.lower()
        tone = "חם" if "warm" in low else "קר" if ("cold" in low or "cool" in low) else "ניטרלי" if ("neutral" in low or "natural" in low) else None
        if "light" in low and not k:
            v["label_he"] = "אור %s" % (tone or "לבן")
        else:
            v["label_he"] = "לבן%s%s" % (" " + tone if tone else "", " %sK" % k.group(1) if k else "")
    if not VALUE_ID.match(v["id"]):
        v["id"] = "v-" + slug(lab)
    if v["label_he"] == v["label_src"]:
        del v["label_src"]  # nothing to keep apart
    return v, key


# ----------------------------------------------------------------------------- build

def from_variants(rows, default_sku, source="api"):
    """rows: [{id, props: [(name_src, label_src, image)], price, currency, stock, image, shipping_il}] -> (options, None)
    or (None, reason). Drops custom-order values and other ship-from origins, merges single-value axes away."""
    default_sku = str(default_sku or "")
    rows = [r for r in rows if r.get("id") and isinstance(r.get("price"), (int, float))]
    if len(rows) < 2:
        return None, "single SKU"
    if default_sku not in {str(r["id"]) for r in rows}:
        return None, "default SKU %s is not in the supplier's SKU list" % (default_sku or "(none)")
    dropped = []
    keep = []
    for r in rows:
        bad = [l for _, l, _ in r["props"] if BOGUS.search(clean(l))]
        if bad and str(r["id"]) != default_sku:
            dropped.append(str(r["id"]))
            continue
        keep.append(r)
    rows = keep
    # ship-from is not the customer's choice: keep the origin of the SKU in the room
    dflt = next(r for r in rows if str(r["id"]) == default_sku)
    every = {}
    for r in rows:
        for n, l, _ in r["props"]:
            every.setdefault(clean(n), set()).add(clean(l))
    fixed = lambda n: SHIPS_FROM.search(n) or PLUG_NAME.search(n) or (every.get(n) and all(PLUG_VALUE.search(v) for v in every[n]))
    origin = {clean(n): clean(l) for n, l, _ in dflt["props"] if fixed(clean(n))}
    if origin:
        rows = [r for r in rows if all(clean(l) == origin[clean(n)] for n, l, _ in r["props"] if clean(n) in origin)]
    names = []
    labels = {}
    for r in rows:
        for n, l, _ in r["props"]:
            n = clean(n)
            if n in origin:
                continue
            if n not in labels:
                names.append(n)
                labels[n] = []
            if clean(l) not in labels[n]:
                labels[n].append(clean(l))
    names = [n for n in names if len(labels[n]) > 1]  # one value everywhere = no choice to make
    if not names:
        return None, "no choice left (every property has one value)"
    axes, used = [], set()
    for n in names:
        aid, name_he = classify(n, labels[n])
        if aid in used:
            aid = next((a for a in ("style", "pattern", "finish", "other") if a not in used), None)
            if aid is None:
                return None, "more properties than axis ids"
            name_he = AXIS_HE[aid] if (not clean(n) or clean(n).startswith("#")) else clean(n)
        used.add(aid)
        vals, ids, keyed = [], {}, []
        for lab in labels[n]:
            v, key = value_of(aid, lab)
            base, i = v["id"], 2
            while v["id"] in ids.values():
                v["id"] = "%s-%d" % (base, i)
                i += 1
            ids[lab] = v["id"]
            vals.append(v)
            keyed.append(key)
        if all(k is not None for k in keyed):  # sizes and quantities in numeric order
            vals = [v for _, v in sorted(zip(keyed, vals), key=lambda kv: kv[0])]
        axes.append({"src": n, "id": aid, "name_he": name_he, "values": vals, "ids": ids})
    axes.sort(key=lambda a: AXIS_ORDER.index(a["id"]))
    skus, by_combo = [], {}
    for r in rows:
        got = {clean(n): clean(l) for n, l, _ in r["props"]}
        values = {a["id"]: a["ids"][got[a["src"]]] for a in axes if a["src"] in got}
        if len(values) != len(axes):
            dropped.append(str(r["id"]))
            continue
        sku = {"id": str(r["id"]), "values": values, "price": {"amount": round(float(r["price"]), 2), "currency": r.get("currency") or "USD"}}
        if r.get("shipping_il"):
            sku["shipping_il"] = r["shipping_il"]
        if r.get("stock") is not None:
            try:
                sku["stock"] = max(0, int(float(r["stock"])))
            except (TypeError, ValueError):
                pass
        if r.get("image") and str(r["image"]).startswith("https://"):
            sku["image"] = r["image"]
        sku["in_room"] = sku["id"] == default_sku
        combo = tuple(values[a["id"]] for a in axes)
        prev = by_combo.get(combo)
        if prev is not None:  # the seller listed the same combination twice: keep the room's, else in stock and cheaper
            other = skus[prev]
            better = sku["in_room"] or (not other["in_room"] and ((sku.get("stock") or 0) > 0, -sku["price"]["amount"]) > ((other.get("stock") or 0) > 0, -other["price"]["amount"]))
            dropped.append(other["id"] if better else sku["id"])
            if better:
                skus[prev] = sku
            continue
        by_combo[combo] = len(skus)
        skus.append(sku)
    if len(skus) < 2:
        return None, "single SKU after filtering"
    # every value that survived must be used by a SKU
    for a in axes:
        used_ids = {s["values"][a["id"]] for s in skus}
        a["values"] = [v for v in a["values"] if v["id"] in used_ids]
    order = {a["id"]: {v["id"]: i for i, v in enumerate(a["values"])} for a in axes}
    skus.sort(key=lambda s: [order[a["id"]][s["values"][a["id"]]] for a in axes])
    opts = {"axes": [{"id": a["id"], "name_he": a["name_he"], "values": a["values"]} for a in axes],
            "skus": skus, "default_sku": default_sku, "source": source}
    return opts, ("dropped %d SKUs (custom order, other origin or duplicate): %s" % (len(dropped), ", ".join(dropped[:6])) if dropped else None)


def shipping_from_quotes(quotes):
    """[{fee|usd, currency, days_min, days_max | days}] -> the cheapest as {amount, currency, days} or None."""
    best = None
    for q in quotes or []:
        fee = q.get("fee", q.get("usd"))
        if not isinstance(fee, (int, float)):
            continue
        if best is None or fee < best[0]:
            days = q.get("days")
            if days is None and q.get("days_min") is not None:
                days = "%s-%s" % (q.get("days_min"), q.get("days_max")) if q.get("days_max") not in (None, q.get("days_min")) else str(q.get("days_min"))
            days = str(days) if days is not None else None
            best = (fee, {"amount": round(float(fee), 2), "currency": q.get("currency") or "USD", "days": days if days and DAYS.match(days) else None})
    return best[1] if best else None


# ----------------------------------------------------------------------------- validate

def _type_ok(v, t):
    return {"string": isinstance(v, str), "number": isinstance(v, (int, float)) and not isinstance(v, bool),
            "integer": isinstance(v, int) and not isinstance(v, bool), "boolean": isinstance(v, bool),
            "object": isinstance(v, dict), "array": isinstance(v, list), "null": v is None}[t]


def validate(o, card=None):
    """-> (errors, warnings). Errors: what data/product-card.schema.json rejects, plus the rules a schema cannot say
    (each SKU names one value per axis, values exist, combinations and ids are unique, default_sku is a SKU)."""
    E, W = [], []
    if not isinstance(o, dict):
        return ["options: not an object"], W

    def extra(obj, allowed, where):
        for k in obj:
            if k not in allowed:
                E.append("%s: unknown key %r" % (where, k))

    def money(m, where, days=False):
        if not isinstance(m, dict):
            E.append("%s: not an object" % where)
            return
        extra(m, ("amount", "currency", "days") if days else ("amount", "currency"), where)
        if not _type_ok(m.get("amount"), "number") or m["amount"] < 0:
            E.append("%s.amount: a number >= 0" % where)
        if not (isinstance(m.get("currency"), str) and CUR.match(m["currency"])):
            E.append("%s.currency: ISO code like USD" % where)
        if days and m.get("days") is not None and not (isinstance(m["days"], str) and DAYS.match(m["days"])):
            E.append("%s.days: like 6-15" % where)

    extra(o, ("axes", "skus", "default_sku", "source"), "options")
    for k in ("axes", "skus", "default_sku", "source"):
        if k not in o:
            E.append("options.%s: missing" % k)
    if o.get("source") not in ("api", "manual"):
        E.append("options.source: api or manual")
    axes = o.get("axes") if isinstance(o.get("axes"), list) else []
    if not axes:
        E.append("options.axes: at least one axis")
    vals = {}
    for i, a in enumerate(axes):
        w = "options.axes[%d]" % i
        if not isinstance(a, dict):
            E.append("%s: not an object" % w)
            continue
        extra(a, ("id", "name_he", "values"), w)
        if a.get("id") not in AXES:
            E.append("%s.id: one of %s, got %r" % (w, ", ".join(AXES), a.get("id")))
        elif a["id"] in vals:
            E.append("%s.id: %r twice" % (w, a["id"]))
        if not (isinstance(a.get("name_he"), str) and a["name_he"].strip()):
            E.append("%s.name_he: missing" % w)
        ids = []
        for j, v in enumerate(a.get("values") if isinstance(a.get("values"), list) else []):
            wv = "%s.values[%d]" % (w, j)
            if not isinstance(v, dict):
                E.append("%s: not an object" % wv)
                continue
            extra(v, ("id", "label_he", "label_src", "hex"), wv)
            if not (isinstance(v.get("id"), str) and VALUE_ID.match(v["id"])):
                E.append("%s.id: lowercase like 200x260 or beige, got %r" % (wv, v.get("id")))
            elif v["id"] in ids:
                E.append("%s.id: %r twice in the axis" % (wv, v["id"]))
            ids.append(v.get("id"))
            if not (isinstance(v.get("label_he"), str) and v["label_he"].strip()):
                E.append("%s.label_he: missing" % wv)
            if "label_src" in v and not isinstance(v["label_src"], str):
                E.append("%s.label_src: a string" % wv)
            if "hex" in v and not (isinstance(v["hex"], str) and HEX.match(v["hex"])):
                E.append("%s.hex: #RRGGBB" % wv)
        if not ids:
            E.append("%s.values: at least one value" % w)
        if isinstance(a.get("id"), str):
            vals[a["id"]] = set(ids)
    skus = o.get("skus") if isinstance(o.get("skus"), list) else []
    if not skus:
        E.append("options.skus: at least one SKU")
    seen_ids, seen_combo, used = set(), {}, {k: set() for k in vals}
    for i, s in enumerate(skus):
        w = "options.skus[%d]" % i
        if not isinstance(s, dict):
            E.append("%s: not an object" % w)
            continue
        extra(s, ("id", "values", "price", "shipping_il", "stock", "image", "in_room"), w)
        sid = s.get("id")
        if not (isinstance(sid, str) and sid):
            E.append("%s.id: missing" % w)
        elif sid in seen_ids:
            E.append("%s.id: %r twice" % (w, sid))
        seen_ids.add(sid)
        sv = s.get("values")
        if not isinstance(sv, dict):
            E.append("%s.values: not an object" % w)
            sv = {}
        for k, v in sv.items():
            if k not in AXES:
                E.append("%s.values: unknown axis %r" % (w, k))
            elif k not in vals:
                E.append("%s.values.%s: no such axis in axes" % (w, k))
            elif v not in vals[k]:
                E.append("%s.values.%s: %r is not a value of the axis" % (w, k, v))
            else:
                used[k].add(v)
        for k in vals:
            if k not in sv:
                E.append("%s.values: missing a value for %r" % (w, k))
        combo = tuple(sorted(sv.items()))
        if combo in seen_combo:
            E.append("%s: same values as %s" % (w, seen_combo[combo]))
        seen_combo[combo] = sid
        money(s.get("price"), w + ".price")
        if "shipping_il" in s:
            money(s["shipping_il"], w + ".shipping_il", days=True)
        if "stock" in s and s["stock"] is not None and not (_type_ok(s["stock"], "integer") and s["stock"] >= 0):
            E.append("%s.stock: an integer >= 0 or null" % w)
        if "image" in s and s["image"] is not None and not (isinstance(s["image"], str) and s["image"].startswith("https://")):
            E.append("%s.image: an https url or null" % w)
        if "in_room" in s and not isinstance(s["in_room"], bool):
            E.append("%s.in_room: true or false" % w)
        if s.get("in_room") is True and sid != o.get("default_sku"):
            E.append("%s.in_room: only default_sku is in the room" % w)
    for k, ids in vals.items():
        for v in ids - used.get(k, set()):
            W.append("options.axes.%s: value %r has no SKU" % (k, v))
    d = o.get("default_sku")
    if not (isinstance(d, str) and d):
        E.append("options.default_sku: missing")
    elif d not in seen_ids:
        E.append("options.default_sku: %r is not one of the SKUs" % d)
    if card is not None and isinstance(d, str):
        sup = (card.get("supplier") or {}).get("sku")
        if sup is not None and str(sup) != d:
            W.append("options.default_sku %r differs from supplier.sku %r" % (d, sup))
        price = card.get("price") or {}
        ds = next((s for s in skus if isinstance(s, dict) and s.get("id") == d), None)
        if ds and isinstance(ds.get("price"), dict):
            if price.get("currency") and ds["price"].get("currency") != price.get("currency"):
                W.append("default SKU currency %s differs from the card's %s" % (ds["price"].get("currency"), price.get("currency")))
            elif isinstance(price.get("cost"), (int, float)) and isinstance(ds["price"].get("amount"), (int, float)) and \
                    abs(ds["price"]["amount"] - price["cost"]) > max(0.01, 0.005 * price["cost"]):
                W.append("default SKU price %.2f differs from the card's price.cost %.2f" % (ds["price"]["amount"], price["cost"]))
    return E, W


# ----------------------------------------------------------------------------- write

def _members(text):
    """Top-level members of a JSON object text: [(key, key_start, value_start, value_end)]."""
    dec = json.JSONDecoder()
    ws = re.compile(r"\s*")
    pos = ws.match(text, 0).end()
    if text[pos] != "{":
        raise ValueError("not a JSON object")
    pos = ws.match(text, pos + 1).end()
    out = []
    while text[pos] != "}":
        kstart = pos
        key, pos = dec.raw_decode(text, pos)
        pos = ws.match(text, pos).end()
        if text[pos] != ":":
            raise ValueError("expected ':' at %d" % pos)
        vstart = ws.match(text, pos + 1).end()
        _, vend = dec.raw_decode(text, vstart)
        out.append((key, kstart, vstart, vend))
        pos = ws.match(text, vend).end()
        if text[pos] == ",":
            pos = ws.match(text, pos + 1).end()
    return out


def _flat(o):
    return json.dumps(o, ensure_ascii=False, separators=(", ", ": "))


def render(o, indent="  "):
    """The options value as card text: one axis value and one SKU per line, so a diff shows what changed."""
    i1, i2, i3, i4 = indent * 2, indent * 3, indent * 4, indent * 5
    axes = []
    for a in o["axes"]:
        head = {k: a[k] for k in a if k != "values"}
        vals = (",\n").join(i4 + _flat(v) for v in a["values"])
        axes.append("%s%s, \"values\": [\n%s\n%s]}" % (i3, _flat(head)[:-1], vals, i3))
    skus = (",\n").join(i3 + _flat(s) for s in o["skus"])
    rest = [k for k in o if k not in ("axes", "skus")]
    tail = "".join(",\n%s%s: %s" % (i2, json.dumps(k), json.dumps(o[k], ensure_ascii=False)) for k in rest)
    return "{\n%s\"axes\": [\n%s\n%s],\n%s\"skus\": [\n%s\n%s]%s\n%s}" % (i2, ",\n".join(axes), i2, i2, skus, i2, tail, i1)


def write_options(path, options, force=False, dry_run=False):
    """Puts `options` into the card at `path`, changing nothing else in the file. -> 'written' | 'unchanged' |
    'kept-manual' (an existing source "manual" object is never replaced unless force)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    card = json.loads(text)
    cur = card.get("options")
    if isinstance(cur, dict) and cur.get("source") == "manual" and not force:
        return "kept-manual"
    if cur == options:
        return "unchanged"
    members = _members(text)
    first = members[0][1]
    indent = text[text.rfind("\n", 0, first) + 1:first]
    value = render(options, indent)
    hit = next((m for m in members if m[0] == "options"), None)
    if hit:
        new = text[:hit[2]] + value + text[hit[3]:]
    else:
        status = next((m for m in members if m[0] == "status"), None)
        if status:
            line = text.rfind("\n", 0, status[1]) + 1
            new = text[:line] + "%s\"options\": %s,\n" % (indent, value) + text[line:]
        else:
            last = members[-1]
            new = text[:last[3]] + ",\n%s\"options\": %s" % (indent, value) + text[last[3]:]
    after = json.loads(new)
    if after.get("options") != options or {k: v for k, v in after.items() if k != "options"} != {k: v for k, v in card.items() if k != "options"}:
        raise RuntimeError("%s: splice check failed, nothing written" % path)
    if not dry_run:
        tmp = path + ".tmp-options"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(new)
        os.replace(tmp, path)
    return "written"


def card_paths():
    for root, _, files in os.walk(PRODUCTS):
        for n in sorted(files):
            if n.endswith(".json"):
                yield os.path.join(root, n)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv.pop(0) if argv else "summary"
    if cmd == "validate":
        paths = argv or list(card_paths())
        bad = 0
        n = 0
        for p in paths:
            with open(p, encoding="utf-8") as f:
                card = json.load(f)
            if "options" not in card:
                continue
            n += 1
            errs, warns = validate(card["options"], card)
            rel = os.path.relpath(p, REPO)
            for e in errs:
                print("ERROR %s: %s" % (rel, e))
            for w in warns:
                print("warn  %s: %s" % (rel, w))
            bad += bool(errs)
        print("%d cards with options, %d invalid" % (n, bad))
        return 1 if bad else 0
    if cmd == "summary":
        by = {}
        for p in card_paths():
            with open(p, encoding="utf-8") as f:
                card = json.load(f)
            sup = (card.get("supplier") or {}).get("name") or "?"
            o = card.get("options")
            row = by.setdefault(sup, {"cards": 0, "with_options": 0, "skus": 0, "manual": 0})
            row["cards"] += 1
            if isinstance(o, dict):
                row["with_options"] += 1
                row["skus"] += len(o.get("skus") or [])
                row["manual"] += o.get("source") == "manual"
        for sup, r in sorted(by.items(), key=lambda kv: -kv[1]["cards"]):
            print("%-20s %3d cards · %3d with options (%d manual) · %4d SKUs" % (sup, r["cards"], r["with_options"], r["manual"], r["skus"]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
