#!/usr/bin/env python3
"""Priority queue of slots that are short of candidates (doc 2.4).

Inputs: data/slots/*.json, data/products/**/*.json (cards), style scores on the cards (if present),
style tags on the slots (if present), and data/sources/seen.json (recent attempts).

    priority = (target - candidates) x room_weight x style_match - recent_attempts_penalty

  candidates   own non-rejected cards for <room>/<slot> (+0.5 for each card in a shared pool the slot's
               "shared" field points to under data/products/). A card whose style_scores[<style>].score
               is below --min-score does not count.
  room_weight  living-room 3, dining-room 2, every other room 1.
  style_match  1, or 0 when the slot declares style tags ("styles"/"style_tags") that exclude --style.
  penalty      0.25 for every registry entry for this slot examined in the last 14 days with no card
               (max 3): a slot that keeps failing on one source drops, it does not disappear.
Slots that already reach the target are left out.

Usage:
  python3 scripts/sourcing/gaps.py [--style nordic] [--room living-room] [--target 6] [--json] [--write]
  --write saves the queue to data/sources/queue.json (regenerated every run).
"""
import argparse, datetime as dt, glob, json, os, re, signal, sys

sys.path.insert(0, os.path.dirname(__file__))
import registry  # noqa: E402

REPO = registry.REPO
ROOM_WEIGHT = {"living-room": 3, "dining-room": 2}
FOLDER_ROOM = {"bath": "bath", "corridor": "corridor", "dining": "dining-room", "entrance": "hall",
               "kids": "kids", "master": "master", "work": "work", "pool": None}
SHARED_DIR = re.compile(r"data/products/([a-z0-9/_-]+?)/?(?=[\s,(;]|$)")


def load_cards():
    cards = []
    for f in glob.glob(os.path.join(REPO, "data/products/**/*.json"), recursive=True):
        c = json.load(open(f))
        relp = os.path.relpath(f, REPO)
        top = relp.split(os.sep)[2]
        room = FOLDER_ROOM.get(top, "living-room")
        cards.append({"path": relp, "dir": os.path.dirname(relp), "room": room, "slot": c.get("slot"),
                      "status": c.get("status"), "style_scores": c.get("style_scores") or {}, "id": c.get("id")})
    return cards


def counts(card, style, min_score):
    if card["status"] == "rejected":
        return False
    sc = (card["style_scores"].get(style) or {}).get("score") if style else None
    return sc is None or sc >= min_score


def build(style="nordic", target=6, min_score=6.0, room=None, days=14):
    cards = load_cards()
    reg = registry.load()
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    attempts = {}
    for e in reg["items"].values():
        if e.get("slot") and e["status"] != "card" and e.get("opened") and (e.get("last_seen") or "") >= since:
            attempts[e["slot"]] = attempts.get(e["slot"], 0) + 1
    queue = []
    for f in sorted(glob.glob(os.path.join(REPO, "data/slots/*.json"))):
        d = json.load(open(f))
        rname = d.get("room") or os.path.basename(f)[:-5]
        if room and rname != room:
            continue
        for s in d.get("slots", []):
            sid = s["id"]
            own = [c for c in cards if c["room"] == rname and c["slot"] == sid and counts(c, style, min_score)]
            own_paths = {c["path"] for c in own}
            pool = []
            for m in SHARED_DIR.finditer(s.get("shared") or ""):
                pdir = "data/products/" + m.group(1).strip("/")
                pool += [c for c in cards if (c["dir"] == pdir or c["dir"].startswith(pdir + "/"))
                         and c["path"] not in own_paths and counts(c, style, min_score)]
            pool = list({c["path"]: c for c in pool}.values())
            cand = len(own) + 0.5 * len(pool)
            if cand >= target:
                continue
            tags = s.get("styles") or s.get("style_tags")
            style_match = 0 if (tags and style and style not in tags) else 1
            if not style_match:
                continue
            key = "%s/%s" % (rname, sid)
            n_att = attempts.get(key, 0)
            penalty = min(3.0, 0.25 * n_att)
            w = ROOM_WEIGHT.get(rname, 1)
            prio = (target - cand) * w * style_match - penalty
            queue.append({"slot": key, "name_he": s.get("name_he"), "priority": round(prio, 2),
                          "candidates": cand, "own": len(own), "pool": len(pool), "room_weight": w,
                          "recent_attempts": n_att, "set_of": s.get("set_of"),
                          "envelope_cm": s.get("envelope_cm"), "shared": s.get("shared")})
    queue.sort(key=lambda q: (-q["priority"], q["candidates"], q["slot"]))
    return queue


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--style", default="nordic"); ap.add_argument("--target", type=int, default=6)
    ap.add_argument("--min-score", type=float, default=6.0); ap.add_argument("--room")
    ap.add_argument("--json", action="store_true"); ap.add_argument("--write", action="store_true")
    ap.add_argument("--top", type=int, default=0, help="print only the first N")
    a = ap.parse_args()
    q = build(a.style, a.target, a.min_score, a.room)
    if a.write:
        p = os.path.join(REPO, "data", "sources", "queue.json")
        with open(p, "w") as f:
            json.dump({"generated": registry.now(), "style": a.style, "target": a.target, "queue": q},
                      f, ensure_ascii=False, indent=1)
            f.write("\n")
    shown = q[: a.top] if a.top else q
    if a.json:
        json.dump(shown, sys.stdout, ensure_ascii=False, indent=1); print()
        return
    print("# gap queue (%s, target %d) - %d slots short" % (a.style, a.target, len(q)))
    print("%4s  %-6s %-34s %5s %4s %4s %4s  %s" % ("#", "prio", "slot", "cand", "own", "pool", "att", "name"))
    for i, r in enumerate(shown, 1):
        print("%4d  %-6s %-34s %5s %4d %4d %4d  %s" % (i, r["priority"], r["slot"], r["candidates"], r["own"],
                                                       r["pool"], r["recent_attempts"], r["name_he"] or ""))


if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
