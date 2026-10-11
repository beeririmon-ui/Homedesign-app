"""Shortlist up to 8 per slot x style (transparent heuristic), download main images, contact sheets.

python3 -I shortlist.py <room> [--no-img]
"""
import json, os, re, sys, subprocess, collections

WORK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WORK)
SCR = os.path.dirname(WORK)
IMG = os.path.join(SCR, "scale-images")
SHEETS = os.path.join(SCR, "sheets")
import prep  # noqa

TOP = 8
MIN_MARGIN = 0.20
PLASTIC = re.compile(r"plastic|pvc|acrylic|polypropylene|\bpp\b|polyethylene|\bpe\b|abs\b", re.I)
RESIN = re.compile(r"resin|polyresin", re.I)
RUGNOT = r"\bround\b|circle|circular|door\s*mat|doormat|\bbath\b|runner|half\s*round|irregular|shaped|kids|children|cartoon|puzzle"
LAMPNOT = r"cord\s*(kit|set)|shade\s*only|lampshade\s*only|bulb\s*only|\bbulbs?\b(?!.*(lamp|light))"
# slot-specific must / not (title), on top of the screen's noun check: obvious non-products out before anyone looks
MUST = {"floor-lamp": r"floor\s*(lamp|light)|standing\s*(lamp|light)|stand\s*light",
        "sofa-cover": r"sofa\s*(slip)?cover|slipcover|couch\s*cover|sofa\s*(protector|towel|blanket|throw|covers)|cover\s*for\s*sofa",
        "magazine-holder": r"magazine\s*(rack|holder|basket|stand|storage|organizer)|newspaper|book\s*rack",
        "table-runner": r"runner", "curtains": r"curtain|drape", "accent-sconces": r"wall\s*(lamp|light|sconce)|sconce",
        "bedside-sconces": r"wall\s*(lamp|light|sconce)|sconce", "kitchen-sconce": r"wall\s*(lamp|light|sconce)|sconce",
        "wall-sconce": r"wall\s*(lamp|light|sconce)|sconce", "pillowcases": r"pillow\s*case|pillowcase|pillow\s*cover|sham",
        "bedding": r"duvet|bedding|quilt\s*cover|bed\s*set|sheet\s*set|comforter\s*cover", "throw": r"throw|blanket",
        "candle-holders": r"candle", "paper-towel-holder": r"paper\s*towel|towel\s*holder|roll\s*holder|kitchen\s*roll",
        "tea-towel": r"tea\s*towel|kitchen\s*towel|dish\s*(towel|cloth)|hand\s*towel|towel",
        "bench-pad": r"bench|long\s*cushion|seat\s*cushion|seat\s*pad|chair\s*pad|cushion", "step-stool": r"stool|step",
        "framed-art": r"frame|framed|wall\s*art|painting|poster|print|canvas"}
NOT = {"curtains": r"tie\s*-?backs?|\bhooks?\b|holder|\brods?\b(?!\s*pocket)|\brings?\b|\bclips?\b|buckle|valance|shower|door\s*curtain|noren|partition|cafe|fabric\s*for|sewing|diy",
       "rug": RUGNOT, "dining-rug": RUGNOT,
       "floor-lamp": r"lamp\s*shade|lampshade|shade\s*for|table\s*lamp|desk\s*lamp",
       "magazine-holder": r"\bgun|pistol|holster|tactical|9mm|glock|ammo|airsoft|rifle|pouch|magnetic|scissor|\bmag\b|clip|acrylic|wall\s*mounted\s*file",
       "sofa-cover": r"pillow\s*case|pillowcase|cushion\s*cover|seat\s*cushion|floor\s*cushion|chair\s*(cover|pad)|stool|ottoman",
       "cushions": r"seat\s*cushion|chair\s*pad|floor\s*cushion|insert\s*only|horror|anime|movie|car\b|sofa\s*cover|pet\b|dog\b|cat\b",
       "candle-holders": r"mold|mould|silicone|glass|lantern|hurricane|tea\s*light|tealight|\bjar\b|\bwax\b|candle\s*making|led\s*candle|flameless|scented|incense|warmer",
       "pendant": LAMPNOT, "dining-pendant": LAMPNOT,
       "wall-decor": r"plant\s*hanger|sticker|decal|clock|mirror|hooks?\b|shelf|neon|\bled\b|flag|tapestry\s*cloth",
       "accent-sconces": r"\bplug|usb|rechargeable|battery|solar|candle|touch|magnetic",
       "bedside-sconces": r"rechargeable|battery|solar|candle|touch|magnetic",
       "vase": r"artificial|fake|flowers?\s*included|dried\s*flower|bud\s*vase|mini\b|small\b|glass|acrylic",
       "floor-vase": r"artificial|fake|flowers?\s*included|dried|mini\b|small\b|tabletop|table\s*vase|bud",
       "table-runner": r"place\s*mat|placemat|table\s*cloth|tablecloth|coaster|bed\s*runner|bed\s*scarf|floor|rug",
       "basket": r"cosmetic|desk|\btray|hanging|bike|picnic|fruit|bread|mini\b|small\b|tissue|plant|flower|pet\b|dog\b|cat\b",
       "framed-art": r"un-?framed|no\s*frame|frameless|diamond\s*painting|cross\s*stitch|paint\s*by\s*number|sticker|decal|tapestry|photo\s*frame|picture\s*frame(?!d)",
       "pillowcases": r"cushion|throw\s*pillow|decorative|sofa|lumbar",
       "bedding": r"pillow\s*case\s*only|fitted\s*sheet\s*only|kids|children|cartoon|crib|baby",
       "throw": r"sofa\s*cover|electric|heated|kids|baby",
       "cushions@master": r"seat\s*cushion|chair\s*pad|floor\s*cushion|insert\s*only|car\b|pet\b",
       "nightstand-tray": r"serving\s*tray\s*with\s*handles|ottoman|rolling|bed\s*tray|laptop|breakfast|lap\s*desk|bamboo\s*bath",
       "trinket-dish": r"soap\s*dish|ashtray|resin\s*mold|silicone|mould|mold",
       "paper-towel-holder": r"toilet|wall\s*mounted|under\s*cabinet|adhesive|suction",
       "tableware-set": r"disposable|paper\s*plate|plastic|melamine|kids|baby|cutlery|chopsticks|spoon|fork|knife",
       "sink-set": r"toilet|bathroom\s*set|shower|toothbrush",
       "tea-towel": r"microfiber|bath\s*towel|beach|hair|face\s*towel|cartoon"}


def score(r, style):
    """-> (score, why) or (None, reason it is out)."""
    key = "%s/%s" % (r["room"], r["slot"])
    if r["drop"]:
        return None, r["drop"]
    t = r["title"] or ""
    slot = r["slot"]
    if slot in MUST and not re.search(MUST[slot], t, re.I):
        return None, "not the product (title)"
    nt = NOT.get("%s@%s" % (slot, r["room"])) or NOT.get(slot)
    if nt and re.search(nt, t, re.I):
        return None, "not the product (title: %s)" % re.search(nt, t, re.I).group(0)
    bad = prep.bad_words(r["title"], key, style)
    if bad:
        return None, "banned words: " + ", ".join(bad)
    mats = " ".join(str(m) for m in r.get("materials") or [])
    m0 = str((r.get("materials") or [""])[0])
    if PLASTIC.search(m0):  # the main material (a PVC anti-slip backing on a rug is not a plastic product)
        return None, "material: " + mats[:60]
    if r["margin_pct"] < MIN_MARGIN:
        return None, "margin %d%% < %d%% at the top of the band" % (round(r["margin_pct"] * 100), MIN_MARGIN * 100)
    sc = (r["screen"].get(style) or {}).get("score")
    if sc is None:
        sc = max([v.get("score", 0) for v in r["screen"].values()] or [0]) - 10
    s = sc + 30 * min(r["margin_pct"], 0.6)
    why = ["screen %.0f" % sc, "margin %d%%" % round(r["margin_pct"] * 100)]
    s += {"fit": 10, "near": 0, "unknown": -3, "n/a": 0}.get(r.get("size"), 0)
    why.append("size " + str(r.get("size")))
    if RESIN.search(mats):
        s -= 15; why.append("resin")
    try:
        dmax = int(str(r.get("ship_days") or "").split("-")[-1])
    except ValueError:
        dmax = None
    if dmax and dmax > 30:
        s -= 5; why.append("ship %s d" % r["ship_days"])
    if r["ship_basis"].startswith("estimated"):
        s -= 2; why.append("ship est.")
    return round(s, 1), "; ".join(why)


def run(room, img=True):
    rs = json.load(open(os.path.join(WORK, "prep-%s.json" % room)))
    slots = [k.split("/")[1] for k in prep.SLOTS if k.startswith(room + "/")]
    out = {"room": room, "slots": {}, "excluded": collections.Counter()}
    for slot in slots:
        cand = [r for r in rs if r["slot"] == slot]
        per = {}
        for style in prep.STYLE_ORDER:
            ranked = []
            for r in cand:
                if style not in r["styles"]:
                    continue
                s, why = score(r, style)
                if s is None:
                    out["excluded"][why.split(":")[0].split(" (")[0][:30]] += 1
                    continue
                ranked.append((s, r["item_id"], why))
            ranked.sort(key=lambda x: -x[0])
            per[style] = [{"item_id": i, "score": s, "why": w} for s, i, w in ranked[:TOP]]
        items = []
        for style in prep.STYLE_ORDER:
            for x in per[style]:
                if x["item_id"] not in items:
                    items.append(x["item_id"])
        out["slots"][slot] = {"per_style": per, "items": items}
    out["excluded"] = dict(out["excluded"])
    json.dump(out, open(os.path.join(WORK, "short-%s.json" % room), "w"), ensure_ascii=False, indent=1)
    n = sum(len(v["items"]) for v in out["slots"].values())
    print("%s: %d unique shortlisted items, %d slot x style picks" % (room, n, sum(len(p) for v in out["slots"].values() for p in v["per_style"].values())))
    if img:
        os.makedirs(IMG, exist_ok=True)
        byid = {r["item_id"]: r for r in rs}
        miss = 0
        for v in out["slots"].values():
            for iid in v["items"]:
                fp = os.path.join(IMG, iid + ".jpg")
                if os.path.exists(fp) and os.path.getsize(fp) > 1000:
                    continue
                url = byid[iid]["image"]
                ok = False
                for u in (url + "_480x480.jpg", url):
                    rc = subprocess.run(["curl", "-sS", "-L", "--max-time", "30", "-A", "Mozilla/5.0", "-o", fp, u]).returncode
                    if rc == 0 and os.path.exists(fp) and os.path.getsize(fp) > 1000:
                        ok = True
                        break
                miss += not ok
        print("images missing: %d" % miss)
    return out


if __name__ == "__main__":
    run(sys.argv[1], "--no-img" not in sys.argv)
