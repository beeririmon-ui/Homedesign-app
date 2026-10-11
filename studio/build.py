#!/usr/bin/env python3
"""Build "the Studio" (internal back-office) into studio/dist/.

Reads the repo's source-of-truth files (read-only) and writes:
  dist/data.json        everything the page shows, computed from the repo
                        (data/, docs/, assets/ and status/: board.md, decisions.json, blockers.json)
  dist/img/p/<id>.webp  first image of each product, 360px long side, q72
  dist/img/f/<n>.webp   frames and renders, 1280px long side, q78
  dist/index.html       the page (copied from studio/src/index.html)

Product images are downloaded once and cached in studio/.cache/, so a second
build does not hit the network. Frame conversions are cached there too.

Usage: python3 studio/build.py [--offline] [--economics-dir DIR] [--deep-dir DIR] [--dist DIR]
                               [--furniture-dir DIR] [--suppliers-dir DIR]
  --offline        never download; products without a cached image get a placeholder.
  --economics-dir  read the economics files from another folder (testing).
  --deep-dir       read the deep AliExpress pass from another folder (testing; default data/leads/aliexpress/deep-2026-10).
  --dist           write the build to another folder (testing; default studio/dist).
  --furniture-dir  read the furniture leads from another folder (testing; default data/leads/furniture-il).
  --suppliers-dir  read candidates-furniture-*.json from another folder (testing; default data/suppliers).

Only the Python standard library and Pillow are used.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import io
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "studio"
DIST = STUDIO / "dist"
CACHE = STUDIO / ".cache"
PAGE_SRC = STUDIO / "src" / "index.html"

LIMIT_BYTES = 60 * 1024 * 1024  # a version holds up to 256MB; each publish sends only new files
LIMIT_FILES = 480  # a version holds up to 511 files; each publish sends at most 255, so publish new files only
P_SIZE, P_Q = 360, 72
F_SIZE, F_Q = 1280, 78
CA_BUNDLE = Path("/root/.ccr/ca-bundle.crt")
UA = "Mozilla/5.0 (X11; Linux x86_64) studio-build/1.0"

# Product folders that hold one room's slots: data/products/<dir>/<slot>/<card>.json.
# Cards directly under data/products/<slot>/ are the living room (the first room).
ROOM_DIRS = {
    "bath": "bath",
    "corridor": "corridor",
    "dining": "dining-room",
    "dining-room": "dining-room",
    "entrance": "hall",
    "hall": "hall",
    "kids": "kids",
    "master": "master",
    "work": "work",
    "living-room": "living-room",
}
POOL_DIR = "pool"
LEADS_DIR = "leads"  # data/products/leads/<slug>.json: new leads written by studio/apply_edits.py

# Extra links (alternative suppliers, reviews...) live in a delimited block at the end of
# a card's notes, because the card schema has no links field. apply_edits.py writes it;
# build.py reads it back out so the page shows notes and links separately.
LINKS_OPEN, LINKS_CLOSE = "[studio-links]", "[/studio-links]"
LINKS_RE = re.compile(r"\s*\[studio-links\]\n(.*?)\n?\[/studio-links\]\s*", re.S)


def split_links(notes):
    """Return (notes without the links block, [{label, url}])."""
    if not notes:
        return notes, []
    m = LINKS_RE.search(notes)
    if not m:
        return notes, []
    links = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        m2 = re.match(r"^(.*?)\s*\|\s*(\S+)$", line)
        label, url = (m2.group(1), m2.group(2)) if m2 else ("", line)
        links.append({"label": label.strip(), "url": url.strip()})
    clean = (notes[:m.start()] + ("\n\n" if notes[:m.start()].strip() and notes[m.end():].strip() else "") + notes[m.end():]).strip()
    return (clean or None), links


def join_links(notes, links):
    """Inverse of split_links: notes text plus a links block (omitted when there are no links)."""
    text = (notes or "").strip()
    rows = [l for l in (links or []) if (l.get("url") or "").strip()]
    if not rows:
        return text or None
    block = "\n".join([LINKS_OPEN] + [f"{(l.get('label') or '').strip()} | {l['url'].strip()}".strip() for l in rows] + [LINKS_CLOSE])
    return (text + "\n\n" + block) if text else block

# Product "rooms" tags -> slot-file room ids (only used for pool cards that no slot points to).
ROOM_TAGS = {
    "living-room": "living-room",
    "dining": "dining-room",
    "kitchen-dining": "dining-room",
    "hallway": "hall",
    "bath": "bath",
    "work": "work",
    "master": "master",
    "bedroom": "master",
    "corridor": "corridor",
    "kids": "kids",
    "kids-boy": "kids",
    "kids-girl": "kids",
}

# Words that tie a decision's text to a room (Hebrew prefixes such as ב/ל/ה attach,
# so these are substring matches).
ROOM_WORDS = {
    "living-room": ["סלון", "M0"],
    "dining-room": ["מטבח", "פינת אוכל", "פינת האוכל"],
    "hall": ["כניסה", "H0"],
    "corridor": ["מסדרון", "C0"],
    "work": ["חדר עבודה", "חדר העבודה", "W0"],
    "master": ["הורים", "MB0"],
    "bath": ["מקלחת", "B1", "B2"],
    "kids": ["ילד", "K-boy", "K-girl"],
}
FRAME_TOKEN_ROOM = {"D1": "dining-room", "D2": "dining-room"}


def log(msg: str) -> None:
    print(msg, flush=True)


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def read_json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20)
        return out.stdout.rstrip() if out.returncode == 0 else ""
    except Exception:
        return ""


def git_date(p: Path) -> str | None:
    d = git("log", "-1", "--format=%cs", "--", rel(p)).strip()
    return d or None


def first_date(text: str) -> str | None:
    m = re.search(r"(20\d\d-\d\d-\d\d)", text)
    return m.group(1) if m else None


# --------------------------------------------------------------------------- rooms and slots

def load_rooms(plan: dict) -> tuple[list[str], dict]:
    rooms: dict[str, dict] = {}
    order: list[str] = []
    transit = plan.get("slots_1_1", {})
    for r in plan.get("rooms", []):
        sf = r.get("slots_file") or ""
        m = re.search(r"data/slots/([\w-]+)\.json", sf)
        if not m:
            continue
        rid = m.group(1)
        if rid not in rooms:
            rooms[rid] = {"id": rid, "house_rooms": [], "name_parts": [], "frames": [], "transit_only": []}
            order.append(rid)
        room = rooms[rid]
        room["house_rooms"].append(r["id"])
        room["name_parts"].append(r.get("name_he") or r["id"])
        for fr in r.get("frames", []):
            if fr not in room["frames"]:
                room["frames"].append(fr)
        for s in (transit.get(r["id"]) or {}).get("transit_only", []):
            if s not in room["transit_only"]:
                room["transit_only"].append(s)
    # any slots file the plan does not list still gets a room
    for f in sorted((ROOT / "data" / "slots").glob("*.json")):
        rid = f.stem
        if rid not in rooms:
            rooms[rid] = {"id": rid, "house_rooms": [], "name_parts": [rid], "frames": [], "transit_only": []}
            order.append(rid)
    for room in rooms.values():
        room["name_he"] = " + ".join(room.pop("name_parts"))
    return order, rooms


def load_slots(order: list[str], rooms: dict) -> dict:
    """Return {room_id: [slot rows]} and fill room meta from the slots file."""
    out = {}
    for rid in order:
        p = ROOT / "data" / "slots" / f"{rid}.json"
        if not p.exists():
            out[rid] = []
            continue
        d = read_json(p)
        room = rooms[rid]
        room["slots_file"] = rel(p)
        room["slots_version"] = d.get("version")
        room["variants_required"] = d.get("variants_required")
        if not room["frames"]:
            v = d.get("views") or d.get("view")
            room["frames"] = v if isinstance(v, list) else ([v] if v else [])
        rows = []
        for s in d.get("slots", []):
            frames = s.get("frames") or list(room["frames"])
            rows.append({
                "key": f"{rid}/{s['id']}",
                "id": s["id"],
                "room": rid,
                "name_he": s.get("name_he"),
                "category": s.get("category"),
                "placement": s.get("placement"),
                "placement_detail": s.get("placement_detail"),
                "position": s.get("position"),
                "frames": frames,
                "seen_in": s.get("seen_in") or [],
                "transit_only": s["id"] in room["transit_only"],
                "variants_required": s.get("variants", d.get("variants_required")),
                "z": s.get("z"),
                "set_of": s.get("set_of"),
                "has_light_layer": bool(s.get("has_light_layer")),
                "shared": s.get("shared"),
                "for_rooms": s.get("rooms"),
                "electrical": s.get("electrical"),
                "safety": s.get("safety"),
            })
        out[rid] = rows
    return out


# --------------------------------------------------------------------------- products

STD_PATTERNS = {
    "CE": re.compile(r"(?<![A-Za-z])CE(?![A-Za-z])"),
    "IP44": re.compile(r"(?<![A-Za-z])IP\s?(?:44|X4|[4-6][4-8])(?![0-9])"),
    "EN71": re.compile(r"EN\s?71|ת\"י\s?562"),
}
NEG = re.compile(r"not\s+(?:verified|mentioned|stated|shown|confirmed)|NOT\b|missing|unknown|UNKNOWN|unverified|"
                 r"FAIL|none\b|None\b|must be|must provide|needs? to be|אין|בלי|ללא|לא מאומת|לא צוין", re.I)
NEG_BEFORE = re.compile(r"(?:\bno|without|✗|אין|בלי|ללא|\bnot)\b[^;.\n]{0,10}$", re.I)
POS_AFTER = re.compile(r"^\W{0,3}(?:\(?stated\)?|PASS|מוצהר|certified)", re.I)
POS_BEFORE = re.compile(r"(?:certifications?\s*:|PASS\s*\()[^;.]{0,30}$", re.I)


def detect_standards(notes: str) -> dict:
    """Classify CE / IP44 / EN71 from free-text notes. Default is 'unknown'.

    'stated'     at least one mention with an explicit positive cue (stated / PASS /
                 certifications:) and no negative wording right after it
    'unverified' mentioned only next to negative wording (not verified, missing, no ...)
    'unknown'    not mentioned, or mentioned only as a requirement
    """
    res = {}
    text = notes or ""
    for std, pat in STD_PATTERNS.items():
        state = "unknown"
        snippets = []
        for m in pat.finditer(text):
            before = text[max(0, m.start() - 40):m.start()]
            after = text[m.end():m.end() + 60]
            near_after = re.split(r"[;.]\s", after, maxsplit=1)[0][:45]
            snippet = (text[max(0, m.start() - 50):m.end() + 60]).replace("\n", " ").strip()
            neg = bool(NEG.search(near_after)) or bool(NEG_BEFORE.search(before))
            pos = (bool(POS_AFTER.search(after)) or bool(POS_BEFORE.search(before))) and not NEG.search(near_after[:25])
            if pos and not (neg and not POS_AFTER.search(after)):
                kind = "stated"
            elif neg:
                kind = "unverified"
            else:
                kind = "mention"
            snippets.append({"kind": kind, "text": snippet, "match": m.group(0)})
            if kind == "stated":
                state = "stated"
            elif kind == "unverified" and state == "unknown":
                state = "unverified"
        res[std] = {"state": state, "snippets": snippets[:6]}
    return res


def pid_of(url: str) -> str | None:
    m = re.search(r"-p-([^./?#]+)\.html", url or "")
    return m.group(1) if m else None


def load_products(room_ids=None) -> list[dict]:
    base = ROOT / "data" / "products"
    products = []
    for p in sorted(base.rglob("*.json")):
        try:
            card = read_json(p)
        except Exception as e:  # keep going, report it
            log(f"  ! cannot read {rel(p)}: {e}")
            continue
        parts = p.relative_to(base).parts
        room = None
        slot = card.get("slot")
        pool = False
        lead = parts[0] == LEADS_DIR
        if lead:
            for t in card.get("rooms") or []:
                room = t if t in (room_ids or ()) else ROOM_TAGS.get(t)
                if room:
                    break
        elif len(parts) == 2:
            room = "living-room"
            slot = slot or parts[0]
        elif parts[0] == POOL_DIR:
            pool = True
        else:
            room = ROOM_DIRS.get(parts[0])
            slot = slot or (parts[1] if len(parts) > 2 else None)
        sup = card.get("supplier") or {}
        card["_path"] = rel(p)
        card["_dir"] = "/".join(p.relative_to(ROOT).parts[:-1]) + "/"
        card["_room"] = room
        card["_slot_key"] = f"{room}/{slot}" if (room and slot) else None
        card["_pool"] = pool
        card["_pid"] = pid_of(sup.get("product_url", ""))
        card["_standards"] = detect_standards(card.get("notes") or "")
        card["notes"], card["_links"] = split_links(card.get("notes"))
        card["_lead"] = lead
        products.append(card)
    return products


def mark_duplicates(products: list[dict]) -> int:
    parent = {p["id"]: p["id"] for p in products}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    seen: dict[str, str] = {}
    for p in products:
        keys = []
        sku = ((p.get("supplier") or {}).get("sku") or "").strip()
        if sku:
            keys.append("sku:" + sku)
        if p["_pid"]:
            keys.append("pid:" + p["_pid"])
        for k in keys:
            if k in seen:
                parent[find(p["id"])] = find(seen[k])
            else:
                seen[k] = p["id"]
    groups: dict[str, list[str]] = {}
    for p in products:
        groups.setdefault(find(p["id"]), []).append(p["id"])
    n = 0
    for p in products:
        g = groups[find(p["id"])]
        p["_dups"] = [x for x in g if x != p["id"]]
        if p["_dups"]:
            n += 1
    return n


def attach_candidates(slots: dict, products: list[dict]) -> None:
    by_key: dict[str, list[dict]] = {}
    for p in products:
        if p["_slot_key"]:
            by_key.setdefault(p["_slot_key"], []).append(p)
    by_id = {p["id"]: p for p in products}
    for rid, rows in slots.items():
        for s in rows:
            direct = by_key.get(s["key"], [])
            direct_ids = {p["id"] for p in direct}
            shared_ids: list[str] = []
            text = s.get("shared") or ""
            for m in re.finditer(r"data/products/([\w./-]+?)/?(?=[\s,;)]|$)", text):
                prefix = "data/products/" + m.group(1).rstrip("/") + "/"
                for p in products:
                    if p["_dir"].startswith(prefix) and p["id"] not in direct_ids and p["id"] not in shared_ids:
                        shared_ids.append(p["id"])
            for m in re.finditer(r"data/slots/([\w-]+)\.json\s+([\w-]+)", text):
                for p in by_key.get(f"{m.group(1)}/{m.group(2)}", []):
                    if p["id"] not in direct_ids and p["id"] not in shared_ids:
                        shared_ids.append(p["id"])
            s["direct"] = [p["id"] for p in direct]
            s["shared_ids"] = shared_ids
            live = lambda ids: [i for i in ids if by_id[i].get("status") != "rejected"]
            s["n_direct"] = len(live(s["direct"]))
            s["n_shared"] = len(live(shared_ids))
            s["n_candidates"] = s["n_direct"] + s["n_shared"]
            s["n_rejected"] = len([i for i in s["direct"] + shared_ids if by_id[i].get("status") == "rejected"])
            s["n_selected"] = len([i for i in s["direct"] + shared_ids if by_id[i].get("status") == "selected"])
            for i in shared_ids:
                by_id[i].setdefault("_shared_in", []).append(s["key"])
    for p in products:
        rooms_in = []
        if p["_room"]:
            rooms_in.append(p["_room"])
        for k in p.get("_shared_in", []):
            r = k.split("/")[0]
            if r not in rooms_in:
                rooms_in.append(r)
        if not rooms_in and p["_pool"]:
            for t in p.get("rooms") or []:
                r = ROOM_TAGS.get(t)
                if r and r not in rooms_in:
                    rooms_in.append(r)
        p["_in_rooms"] = rooms_in
        p.setdefault("_shared_in", [])


# --------------------------------------------------------------------------- sell quantity

# The slot may need a set (data/slots: set_of). Card cost is sometimes per piece, sometimes per set.
QTY_PER_PIECE = [
    re.compile(r"price\s+(?:is\s+)?per\s+(?:lamp|light|unit|piece|pc|item|cup|mug|plate|bowl|cover|cushion|frame|print)", re.I),
    re.compile(r"(?:pair|set)\s*=\s*\d+\s*x\s*\$", re.I),
    re.compile(r"set of \d+\s*=\s*\d+\s*units", re.I),
    re.compile(r"=\s*order\s+qty\s*\d", re.I),
    re.compile(r"sell\s+\d+\s+units", re.I),
    re.compile(r"sell as a set of [\d\sor]+=\s*qty", re.I),
    re.compile(r"sold\s+(?:as\s+1\s*pc|singly|individually|per\s+piece)", re.I),
    re.compile(r"(?:מחיר|cost)[^.;\n]{0,25}ליחידה"),
    re.compile(r"ליחידה[^.;\n]{0,15}(?:מחיר|cost)"),
]
QTY_WHOLE_SET_NOTES = [
    re.compile(r"price\s+(?:is\s+)?for\s+(?:\d+|two|three|four|the\s+(?:set|pair))\b", re.I),
    re.compile(r"המחיר\s+(?:הוא\s+)?ל(?:סט|זוג)"),
]
QTY_WHOLE_SET_NAME = [
    re.compile(r"\bset of \d\b", re.I),
    re.compile(r"\bpair\b", re.I),
    re.compile(r"\b(?:two|three|four|five|six)-piece\b|\b\d+\s*-?\s*(?:pcs|pieces)\s*/\s*set", re.I),
]
QTY_COUNT = re.compile(r"set of (\d+)\s*=\s*\d+\s*units|כסט של (\d+) יחידות", re.I)
# How many pieces the card's cost covers, read from the room SKU (options.default_sku): the supplier's labels of its
# option values ("1 PC W100cmxH275cm", "1PC (price is per piece)", "2PC W225cm", "4 pcs", "set of 2", "pair").
# This is the strongest evidence: a SKU that is already a pair or a set is never multiplied by the slot's set size.
SKU_PIECES = [
    (re.compile(r"(?<![\d.])(\d{1,2})\s*-?\s*(?:pcs?|pieces?|panels?)\b(?!\s*(?:/|per)\s*(?:colou?r))", re.I), None),
    (re.compile(r"\bset\s*of\s*(\d{1,2})\b", re.I), None),
    (re.compile(r"\bpairs?\b|זוג"), 2),
    (re.compile(r"\bper\s+piece\b|\bsingle\b|פאנל אחד|יחידה אחת"), 1),
]


def sku_pieces(p: dict) -> tuple[int | None, str | None]:
    """(pieces the room SKU's price covers, the label that says so), or (None, None) when the card has no options or
    the SKU labels do not say. When labels disagree the largest count wins (the safe side: never sell a pair twice)."""
    o = p.get("options") if isinstance(p.get("options"), dict) else None
    if not o:
        return None, None
    sku = next((x for x in o.get("skus") or [] if isinstance(x, dict) and x.get("id") == o.get("default_sku")), None)
    if not sku:
        return None, None
    labels = []
    for a in o.get("axes") or []:
        if not isinstance(a, dict):
            continue
        vid = (sku.get("values") or {}).get(a.get("id"))
        v = next((x for x in a.get("values") or [] if isinstance(x, dict) and x.get("id") == vid), None)
        if v:
            labels += [str(v.get(k)) for k in ("label_src", "label_he") if v.get(k)]
    for k in ("label", "name", "label_src"):
        if isinstance(sku.get(k), str):
            labels.append(sku[k])
    found = []
    for lab in labels:
        for rx, n in SKU_PIECES:
            m = rx.search(lab)
            if m:
                k = n if n else int(m.group(1))
                if k >= 1:
                    found.append((k, lab))
                break
    if not found:
        return None, None
    return max(found, key=lambda x: x[0])


def sell_qty_default(p: dict, slot_by_key: dict) -> dict:
    """Default units per sale (units of the card's cost). A room SKU whose own label says it is already a pair or a set
    (sku_pieces > 1) is never multiplied: qty 1 (not sure when the slot's set is bigger). A one-piece label only confirms
    the per-piece reading and never raises the quantity by itself; then, as before, the slot's set_of counts only when the
    card says its cost is per piece, and when that is unclear the default is 1 and sure=False (a 'not sure' chip)."""
    def set_of(k):
        v = (slot_by_key.get(k) or {}).get("set_of")
        return int(v) if isnum(v) and v > 1 else None
    home = set_of(p.get("_slot_key")) if p.get("_slot_key") else None
    shared = [(set_of(k), k) for k in p.get("_shared_in") or [] if set_of(k)]
    name, notes = p.get("name") or "", p.get("notes") or ""
    pcs, pcs_label = sku_pieces(p)
    if pcs is not None and pcs > 1:
        m = QTY_COUNT.search(name) or QTY_COUNT.search(notes)
        if home:
            need, why = home, f"העמדה דורשת סט של {home}"
        elif m:
            need = int(next(g for g in m.groups() if g))
            why = f"ההערות אומרות שהמוצר נמכר כסט של {need}"
        elif shared:
            need, k = max(shared)
            why = f"העמדה המשותפת {k} דורשת סט של {need}"
        else:
            need, why = None, None
        if not need or pcs >= need:
            return {"qty": 1, "sure": True, "set_of": need, "sku_pieces": pcs,
                    "reason": f"{why}, והמק\"ט שבחדר כבר כולל {pcs} יח' ({pcs_label})" if need else None}
        # the SKU is already a pair or a set, smaller than the slot's: never multiply a set by guess
        return {"qty": 1, "sure": False, "set_of": need, "sku_pieces": pcs,
                "reason": f"{why}, והמק\"ט שבחדר הוא כבר סט של {pcs} ({pcs_label}). לא ברור אם צריך עוד סט"}
    out = _sell_qty_notes(name, notes, home, shared)
    if pcs == 1:
        out["sku_pieces"] = 1
        if out["qty"] > 1 and out.get("reason"):
            out["reason"] += f"; המק\"ט שבחדר הוא יחידה אחת ({pcs_label})"
        elif not out["sure"] and out.get("set_of"):
            # the price is per piece; what is open is whether the set is N of this same product (not raised by guess)
            out["reason"] = (f"העמדה דורשת סט של {out['set_of']}, והמק\"ט שבחדר הוא יחידה אחת ({pcs_label}). "
                             f"לא ברור אם הסט הוא {out['set_of']} מאותו מוצר")
    return out


def _sell_qty_notes(name: str, notes: str, home, shared) -> dict:
    """The notes rule (before 2026-10-11): the slot's set_of only when the card says its cost is per piece."""
    pp = any(r.search(name) or r.search(notes) for r in QTY_PER_PIECE)
    ws_strong = any(r.search(notes) for r in QTY_WHOLE_SET_NOTES)
    ws = ws_strong or any(r.search(name) for r in QTY_WHOLE_SET_NAME)
    if home:
        if pp and not ws_strong:
            return {"qty": home, "sure": True, "set_of": home, "reason": f"העמדה דורשת סט של {home}, וההערות אומרות שהעלות ליחידה"}
        if ws and not pp:
            return {"qty": 1, "sure": True, "set_of": home, "reason": f"העמדה דורשת סט של {home}, והעלות בכרטיס כבר לסט או לזוג"}
        return {"qty": 1, "sure": False, "set_of": home,
                "reason": f"העמדה דורשת סט של {home}, ולא ברור מהכרטיס אם העלות ליחידה או לסט"}
    if pp:
        m = QTY_COUNT.search(name) or QTY_COUNT.search(notes)
        if m:
            n = int(next(g for g in m.groups() if g))
            why = f"ההערות אומרות שהעלות ליחידה ושהמוצר נמכר כסט של {n}"
        elif shared:
            n, k = max(shared)
            why = f"ההערות אומרות שהעלות ליחידה, והעמדה המשותפת {k} דורשת סט של {n}"
        else:
            n, why = None, None
        if n and n > 1:
            return {"qty": n, "sure": True, "set_of": n, "reason": why}
    return {"qty": 1, "sure": True, "set_of": None, "reason": None}


# --------------------------------------------------------------------------- images

_ssl_ctx = None


def ssl_ctx():
    global _ssl_ctx
    if _ssl_ctx is None:
        _ssl_ctx = ssl.create_default_context(cafile=str(CA_BUNDLE)) if CA_BUNDLE.exists() else ssl.create_default_context()
    return _ssl_ctx


def fetch_cached(url: str, offline: bool) -> tuple[bytes | None, str, bool]:
    """Return (bytes, error, from_cache)."""
    h = hashlib.sha1(url.encode()).hexdigest()[:20]
    cdir = CACHE / "p"
    cdir.mkdir(parents=True, exist_ok=True)
    cp = cdir / f"{h}.bin"
    if cp.exists() and cp.stat().st_size > 0:
        return cp.read_bytes(), "", True
    if offline:
        return None, "offline build, not in cache", False
    last = ""
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*;q=0.8"})
            with urllib.request.urlopen(req, context=ssl_ctx(), timeout=25) as r:
                b = r.read()
            Image.open(io.BytesIO(b)).verify()
            tmp = cp.with_suffix(".tmp")
            tmp.write_bytes(b)
            tmp.replace(cp)
            return b, "", False
        except Exception as e:
            last = f"{type(e).__name__}: {e}"[:160]
            time.sleep(0.6 * (attempt + 1))
    return None, last, False


def to_webp(img: Image.Image, size: int, quality: int, out: Path) -> tuple[int, int]:
    if img.mode in ("P", "LA"):
        img = img.convert("RGBA")
    elif img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    img.thumbnail((size, size), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "WEBP", quality=quality, method=6)
    return img.size


def placeholder(hex_color: str, out: Path) -> tuple[int, int]:
    try:
        c = tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    except Exception:
        c = (217, 214, 208)
    img = Image.new("RGB", (P_SIZE, P_SIZE), (238, 236, 232))
    d = ImageDraw.Draw(img)
    d.rectangle([60, 60, P_SIZE - 60, P_SIZE - 60], fill=c)
    for x in range(-P_SIZE, P_SIZE, 18):  # hatching marks it as "no photo"
        d.line([(x, P_SIZE), (x + P_SIZE, 0)], fill=(220, 217, 211), width=2)
    d.rectangle([60, 60, P_SIZE - 60, P_SIZE - 60], fill=c)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "WEBP", quality=P_Q, method=6)
    return img.size


def build_product_images(products: list[dict], offline: bool) -> dict:
    stats = {"downloaded": 0, "cached": 0, "failed": 0, "fallback": 0}

    def work(p):
        urls = (p.get("images") or {}).get("urls") or []
        out = DIST / "img" / "p" / f"{p['id']}.webp"
        errors = []
        for i, url in enumerate(urls[:3]):
            b, err, cached = fetch_cached(url, offline)
            if b is None:
                errors.append(f"#{i + 1}: {err}")
                continue
            try:
                w, h = to_webp(Image.open(io.BytesIO(b)), P_SIZE, P_Q, out)
            except Exception as e:
                errors.append(f"#{i + 1}: {type(e).__name__}: {e}"[:160])
                continue
            note = None
            if i > 0:
                note = f"התמונה הראשונה לא נטענה ({errors[0]}); מוצגת תמונה {i + 1}."
            return p["id"], {"src": f"img/p/{p['id']}.webp", "w": w, "h": h, "ok": True, "index": i,
                             "cached": cached, "note": note}
        w, h = placeholder((p.get("colors") or {}).get("dominant_hex", ""), out)
        why = "; ".join(errors) if errors else "אין כתובות תמונה בכרטיס"
        return p["id"], {"src": f"img/p/{p['id']}.webp", "w": w, "h": h, "ok": False, "index": None,
                         "cached": False, "note": f"ההורדה נכשלה, מוצג מקום שמור בצבע הדומיננטי. {why}"}

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for pid, r in ex.map(work, products):
            results[pid] = r
            if not r["ok"]:
                stats["failed"] += 1
            elif r["cached"]:
                stats["cached"] += 1
            else:
                stats["downloaded"] += 1
            if r["ok"] and r["index"]:
                stats["fallback"] += 1
    for p in products:
        p["_img"] = results[p["id"]]
    return stats


def readme_captions(d: Path) -> dict:
    """Parse '| `file` | description |' rows from a folder README."""
    caps = {}
    r = d / "README.md"
    if not r.exists():
        return caps
    for line in r.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*$", line)
        if m:
            text = re.sub(r"\*\*|`", "", m.group(2)).replace("‏", "").strip()
            caps[m.group(1)] = text
    return caps


def collect_frames(plan: dict, order: list[str], rooms: dict) -> list[dict]:
    house_to_room = {}
    for rid in order:
        for h in rooms[rid]["house_rooms"]:
            house_to_room[h] = rid
    cams = {c["id"]: c for c in plan.get("cameras", [])}
    frame_room = {}
    for rid in order:
        for fr in rooms[rid]["frames"]:
            frame_room[fr] = rid

    items = []
    # round 2, approved
    r2 = ROOT / "assets/blockout/house/framing/round2"
    for p in sorted(r2.glob("*.png")):
        stem = p.stem
        base = re.sub(r"-lit$", "", stem)
        frame = base if base in cams else None
        if not frame:
            tok = re.compile(r"(?<![\w-])" + re.escape(base) + r"(?![\w-])")
            for cid, c in cams.items():
                if tok.search(c.get("status", "") or ""):
                    frame = cid
                    break
        room = frame_room.get(frame) or house_to_room.get(cams.get(frame, {}).get("room"))
        if not room:
            log(f"  ! round2 {p.name}: no room found, skipped")
            continue
        items.append({"name": f"r2-{stem}", "path": p, "room": room, "frame": frame, "kind": "round2",
                      "label": "סבב 2 (מאושר)", "caption": f"{frame} · clay סבב 2, נבחר ואושר" + (" · מצב מואר" if stem.endswith("-lit") else ""),
                      "order": 0})
    # round 1 compare sheets
    r1 = ROOT / "assets/blockout/house/framing"
    for p in sorted(r1.glob("*-compare.jpg")):
        house = p.stem[: -len("-compare")]
        room = house_to_room.get(house)
        if not room:
            log(f"  ! round1 {p.name}: no room found, skipped")
            continue
        items.append({"name": f"r1-{p.stem}", "path": p, "room": room, "frame": None, "kind": "compare",
                      "label": "סבב 1 (השוואה)", "caption": f"סבב 1: השוואת חלופות המסגור ({house})", "order": 5})
    # living-room renders
    rd = ROOT / "assets/renders/living-room/nordic"
    manifest = {}
    mp = ROOT / "assets/manifest.json"
    if mp.exists():
        try:
            for a in read_json(mp).get("assets", []):
                manifest[a.get("path")] = a
        except Exception:
            pass
    renders = []
    for p in rd.rglob("*"):
        if p.suffix.lower() not in (".png", ".jpg", ".jpeg") or "/raw/" in p.as_posix() or p.name.startswith("step-"):
            continue
        renders.append(p)
    renders.sort(key=lambda p: (0 if p.name == "m0-pilot-b-graded.png" else 1, -p.stat().st_mtime))
    caps_cache = {}
    for i, p in enumerate(renders):
        caps = caps_cache.setdefault(p.parent, readme_captions(p.parent))
        folder = p.parent.relative_to(rd).as_posix()
        cap = caps.get(p.name) or p.name
        m = manifest.get(rel(p)) or {}
        is_sheet = "compare" in p.name or "before-after" in p.name
        items.append({"name": "rd-" + re.sub(r"[^\w-]+", "-", f"{folder}-{p.stem}"), "path": p, "room": "living-room",
                      "frame": "M0", "kind": "compare" if is_sheet else "render",
                      "label": "רינדור", "caption": f"{folder}/{p.name}: {cap}", "status": m.get("status"),
                      "order": 1 + i / 100})
    return items


def build_frame_images(items: list[dict]) -> int:
    cdir = CACHE / "f"
    cdir.mkdir(parents=True, exist_ok=True)
    hits = 0

    def work(it):
        p: Path = it["path"]
        st = p.stat()
        key = hashlib.sha1(f"{rel(p)}|{st.st_size}|{int(st.st_mtime)}|{F_SIZE}|{F_Q}".encode()).hexdigest()[:16]
        cp = cdir / f"{it['name']}-{key}.webp"
        out = DIST / "img" / "f" / f"{it['name']}.webp"
        out.parent.mkdir(parents=True, exist_ok=True)
        if cp.exists():
            shutil.copyfile(cp, out)
            with Image.open(out) as im:
                return it, im.size, True
        with Image.open(p) as im:
            im.load()
            size = to_webp(im.copy(), F_SIZE, F_Q, cp)
        shutil.copyfile(cp, out)
        return it, size, False

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for it, size, hit in ex.map(work, items):
            it["w"], it["h"] = size
            it["src"] = f"img/f/{it['name']}.webp"
            hits += hit
    return hits


# --------------------------------------------------------------------------- board, decisions, reports

def parse_board(p: Path) -> dict:
    stages, roadmap, logs = [], [], []
    section = None
    cur = None
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            m = re.match(r"שלב\s+(\d+)\s*[—–-]\s*(.+)", title)
            if m:
                cur = {"n": int(m.group(1)), "title": m.group(2).strip(), "items": []}
                stages.append(cur)
                section = "stage"
            elif title.startswith("יומן"):
                section, cur = "log", None
            elif title.startswith("מפת דרכים"):
                section, cur = "roadmap", None
            else:
                section, cur = None, None
            continue
        m = re.match(r"^- \[( |x|X|~)\]\s+(.+)$", line)
        if m and section in ("stage", "roadmap"):
            raw = m.group(2).strip()
            state = {"x": "done", "X": "done", "~": "partial", " ": "todo"}[m.group(1)]
            gate = bool(re.search(r"\*\*(אישור|בחירת) משתמש", raw))
            item = {"state": state, "text": re.sub(r"\*\*", "", raw), "gate": gate}
            if section == "stage":
                cur["items"].append(item)
            else:
                roadmap.append(item)
            continue
        if section == "log":
            m = re.match(r"^- (\d{4}-\d{2}-\d{2})\s+·\s+(.+?)\s+·\s+(.+)$", line)
            if m:
                parts = [s.strip() for s in m.group(3).split(" · ")]
                logs.append({"date": m.group(1), "who": m.group(2).strip(), "who_key": who_key(m.group(2)),
                             "text": m.group(3).strip(), "parts": parts})
            elif line.startswith("- ") and logs:
                pass
    for s in stages:
        n = len(s["items"])
        done = sum(1 for i in s["items"] if i["state"] == "done")
        part = sum(1 for i in s["items"] if i["state"] == "partial")
        s.update({"total": n, "done": done, "partial": part})
    return {"stages": stages, "roadmap": roadmap, "log": logs}


def who_key(who: str) -> str:
    w = who.strip()
    if w.startswith("המשתמש"):
        return "user"
    if w.startswith("המנהל"):
        return "manager"
    for k in ("master-designer", "motion-agent", "render-agent", "qa-agent", "frontend-dev", "astra"):
        if w.startswith(k):
            return k
    if w.startswith("sourcing"):
        return "sourcing-agent"
    return "other"


def infer_decision_rooms(d: dict, room_ids: list[str]) -> list[str]:
    if isinstance(d.get("rooms"), list):
        return [r for r in d["rooms"] if r in room_ids]
    text = " ".join(str(d.get(k) or "") for k in ("title", "question", "context", "blocks", "source"))
    for o in d.get("options") or []:
        text += " " + str(o.get("label") or "") + " " + str(o.get("desc") or "")
    found = []
    for rid in room_ids:
        if re.search(r"data/slots/" + re.escape(rid) + r"\.json|(?:,\s*)" + re.escape(rid) + r"\.json", text):
            found.append(rid)
    for rid, words in ROOM_WORDS.items():
        if rid in room_ids and rid not in found and any(w in text for w in words):
            found.append(rid)
    for tok, rid in FRAME_TOKEN_ROOM.items():
        if re.search(r"(?<![\w-])" + tok + r"(?![\w-])", text) and rid not in found:
            found.append(rid)
    return [r for r in room_ids if r in found]


def load_decisions(room_ids: list[str]) -> dict:
    p = ROOT / "status" / "decisions.json"
    if not p.exists():
        return {"items": [], "note": None, "updated": None, "source": None}
    d = read_json(p)
    items = []
    for i, it in enumerate(d.get("decisions", [])):
        it = dict(it)
        it["_order"] = i
        it["_rooms"] = infer_decision_rooms(it, room_ids)
        items.append(it)
    return {"items": items, "note": d.get("note"), "updated": d.get("updated"), "version": d.get("version"),
            "source": rel(p)}


def load_blockers() -> dict:
    """status/blockers.json: actions that are stuck or need the user (the 'waiting for you' screen).

    Each item: id, kind (user_action | decision | waiting | blocked | resolved), priority 1-3, title,
    stuck, needs, who, since, links, decisions, status (open | done). The file order is kept in _order;
    the page sorts by priority and since. 'done' marks made in the page live in the page db (settings/blockers)."""
    p = ROOT / "status" / "blockers.json"
    if not p.exists():
        return {"items": [], "note": None, "updated": None, "version": None, "source": None}
    d = read_json(p)
    items = []
    for i, it in enumerate(d.get("items") or []):
        if not isinstance(it, dict) or not it.get("id"):
            continue
        it = dict(it)
        it["_order"] = i
        it["links"] = [l for l in (it.get("links") or []) if isinstance(l, str)]
        it["decisions"] = [x for x in (it.get("decisions") or []) if isinstance(x, str)]
        items.append(it)
    return {"items": items, "note": d.get("note"), "updated": d.get("updated"), "version": d.get("version"),
            "source": rel(p)}


def load_reports(globs: list[str], kind: str) -> list[dict]:
    out = []
    seen = set()
    for g in globs:
        for p in sorted(ROOT.glob(g)):
            if p in seen or not p.is_file():
                continue
            seen.add(p)
            md = p.read_text(encoding="utf-8")
            title = next((l[2:].strip() for l in md.splitlines() if l.startswith("# ")), p.stem)
            date = first_date(p.name) or first_date(md[:600]) or git_date(p)
            out.append({"id": re.sub(r"[^\w-]+", "-", rel(p)).strip("-"), "kind": kind, "path": rel(p),
                        "title": title, "date": date, "bytes": len(md.encode()), "md": md})
    out.sort(key=lambda r: (r["date"] or ""), reverse=True)
    return out


# --------------------------------------------------------------------------- economics

def isnum(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _max_days(key: str, o: dict):
    for k in ("days_max", "max_days"):
        if isnum(o.get(k)):
            return o[k]
    d = o.get("days")
    if isnum(d):
        return d
    if isinstance(d, str):
        nums = [int(x) for x in re.findall(r"\d+", d)]
        if nums:
            return max(nums)
    if key == "fastest_under_20d":
        return 20
    return None


def pick_freight(entry: dict):
    """The cheapest CJ option that arrives within 20 days. Returns (usd, option_key, option), or None when
    no option is known to arrive within 20 days (no silent fallback to the slow line: the page then shows
    'no fast shipping' for the under-20-days method)."""
    if not isinstance(entry, dict):
        return None
    cu = entry.get("cheapest_under_20d")
    if isinstance(cu, dict) and isnum(cu.get("usd")):
        return cu["usd"], "cheapest_under_20d", cu
    opts = []
    for key in ("cheapest", "fastest_under_20d"):
        o = entry.get(key)
        if isinstance(o, dict) and isnum(o.get("usd")):
            opts.append((key, o))
    for o in entry.get("options") or []:
        if isinstance(o, dict) and isnum(o.get("usd")):
            opts.append(("option", o))
    if not opts:
        return None
    under = [(k, o) for k, o in opts if (_max_days(k, o) is not None and _max_days(k, o) <= 20)]
    if not under:
        return None
    k, o = min(under, key=lambda x: x[1]["usd"])
    return o["usd"], k, o


# Freight files, one per supplier, all in the freight-cj.json format (products[id]: options, cheapest,
# cheapest_under_20d, fastest_under_20d, checked_at, status, error; optional qty = pieces the quote covers, note).
FREIGHT_FILES = (("freight-cj.json", "cj"), ("freight-zendrop.json", "zendrop"), ("freight-aliexpress.json", "aliexpress"))
SITE_ECON_TS = ROOT / "site" / "shared" / "src" / "schema" / "economics.ts"
STOREFRONT_KEYS = ("shipping_fee_economy_ils", "free_shipping_threshold_ils")


def storefront_settings(settings_file: dict | None) -> dict:
    """Customer-facing shipping (what the customer pays on top of the price): data/economics/settings.json `storefront`
    first, else DEFAULT_SETTINGS in site/shared/src/schema/economics.ts (the site's own defaults), else 29 / 299."""
    out = {"shipping_fee_economy_ils": 29, "free_shipping_threshold_ils": 299, "src": "ברירת מחדל"}
    if SITE_ECON_TS.exists():
        t = SITE_ECON_TS.read_text(encoding="utf-8")
        m = re.search(r"DEFAULT_SETTINGS[^=]*=\s*\{(.*?)\};", t, re.S)
        if m:
            for k in STOREFRONT_KEYS:
                v = re.search(rf"\b{k}\s*:\s*(\d+(?:\.\d+)?|null)", m.group(1))
                if v:
                    out[k] = None if v.group(1) == "null" else float(v.group(1)) if "." in v.group(1) else int(v.group(1))
            out["src"] = rel(SITE_ECON_TS)
    sf = (settings_file or {}).get("storefront") if isinstance(settings_file, dict) else None
    if isinstance(sf, dict) and any(k in sf for k in STOREFRONT_KEYS):
        for k in STOREFRONT_KEYS:
            if k in sf and (isnum(sf[k]) or (k == "free_shipping_threshold_ils" and sf[k] is None)):
                out[k] = sf[k]
        out["src"] = "data/economics/settings.json"
    return out


def card_sku_shipping(p: dict):
    """Shipping to Israel of the room SKU written in the card (options.skus[].shipping_il, USD), as a freight entry.
    Only the structured field: amounts in the notes are not used here (they are often estimates for another SKU)."""
    o = p.get("options") if isinstance(p.get("options"), dict) else {}
    sku = next((x for x in o.get("skus") or [] if isinstance(x, dict) and x.get("id") == o.get("default_sku")), None)
    si = (sku or {}).get("shipping_il") or {}
    if not (isnum(si.get("amount")) and str(si.get("currency") or "").upper() == "USD"):
        return None
    d = days_pair(si.get("days"))
    opt = {"usd": float(si["amount"]), "name": si.get("method") or si.get("name") or "המק\"ט שבחדר", "days": f"{d[0]}-{d[1]}" if d else None}
    return {"options": [opt], "cheapest": opt, "cheapest_under_20d": opt if d and d[1] <= 20 else None, "status": "ok"}


def _clean_il_value(v):
    """il_value from the pricing team: {low, typical, high, comps:[{retailer, title, price, url}]}; only https links."""
    if not isinstance(v, dict):
        return None
    out = {k: v[k] for k in ("low", "typical", "high") if isnum(v.get(k))}
    comps = []
    for c in v.get("comps") or []:
        if not isinstance(c, dict):
            continue
        url = c.get("url") if isinstance(c.get("url"), str) and c["url"].startswith("https://") else None
        comps.append({"retailer": str(c.get("retailer") or "")[:80], "title": str(c.get("title") or "")[:200],
                      "price": c.get("price") if isnum(c.get("price")) else None, "url": url,
                      "size": str(c.get("size"))[:80] if c.get("size") else None,
                      "list_price": c.get("list_price") if isnum(c.get("list_price")) else None,
                      "note": str(c.get("note"))[:160] if c.get("note") else None})
    out["comps"] = comps[:12]
    for k in ("note", "basis", "date"):
        if isinstance(v.get(k), str):
            out[k] = v[k][:400]
    return out if (len(out) > 1 or comps) else None


def load_economics(eco_dir: Path, products: list[dict]) -> dict:
    out = {"dir": rel(eco_dir) if eco_dir.is_relative_to(ROOT) else str(eco_dir), "settings": None, "budget": None,
           "products": {}, "freight": None, "freight_files": [], "bundles": None, "files": [], "storefront": None}
    settings_file = None
    if eco_dir.exists():
        sp = eco_dir / "settings.json"
        if sp.exists():
            settings_file = read_json(sp)
            out["settings"] = settings_file.get("economics")
            out["budget"] = settings_file.get("budget")
            out["files"].append(sp.name)
    out["storefront"] = storefront_settings(settings_file)
    if not eco_dir.exists():
        return out
    bp = eco_dir / "budget.json"
    if out["budget"] is None and bp.exists():
        out["budget"] = read_json(bp)
        out["files"].append(bp.name)
    manual, pricing_meta = {}, None
    pp = eco_dir / "products.json"
    if pp.exists():
        d = read_json(pp)
        manual = d.get("products", d) if isinstance(d, dict) else {}
        if not isinstance(manual, dict):
            manual = {}
        out["files"].append(pp.name)
        pricing_meta = {"file": rel(pp) if pp.is_relative_to(ROOT) else pp.name,
                        "updated": first_date(str(d.get("updated") or "")) if isinstance(d, dict) else None}
    out["pricing"] = pricing_meta
    freights = {}  # source key -> (products dict, file date)
    for fname, src in FREIGHT_FILES:
        fp = eco_dir / fname
        if not fp.exists():
            continue
        try:
            d = read_json(fp)
            fprods = d.get("products") or {}
            fdate = None
            for k in ("updated", "generated_at", "generated", "date", "checked_at", "as_of", "created"):
                if d.get(k):
                    fdate = first_date(str(d[k]))
                    if fdate:
                        break
            fdate = fdate or git_date(fp) or dt.date.fromtimestamp(fp.stat().st_mtime).isoformat()
            freights[src] = (fprods, fdate)
            meta = {"file": fp.name, "src": src, "date": fdate, "products": len(fprods), "source": d.get("source")}
            out["freight_files"].append(meta)
            if src == "cj":
                out["freight"] = {k: meta[k] for k in ("file", "date", "products")}
            out["files"].append(fp.name)
        except Exception as e:
            log(f"  ! cannot read {fp.name}: {e}")
    bp2 = eco_dir / "freight-bundles.json"
    if bp2.exists():
        try:
            d = read_json(bp2)
            rows = []
            for bid, bd in (d.get("bundles") or {}).items():
                if not isinstance(bd, dict):
                    continue
                comb = bd.get("combined") or {}
                rows.append({"id": bid, "label": bd.get("label"), "items": len(bd.get("items") or []),
                             "sum_single_cheapest": bd.get("sum_single_cheapest"), "sum_single_under20": bd.get("sum_single_cheapest_under_20d"),
                             "combined_cheapest": (comb.get("cheapest") or {}).get("usd"), "combined_under20": (comb.get("cheapest_under_20d") or {}).get("usd"),
                             "saving_pct_cheapest": bd.get("saving_pct_cheapest"), "saving_pct_under20": bd.get("saving_pct_under_20d"),
                             "ship_share_single_pct": bd.get("ship_share_landed_single_pct"), "ship_share_combined_pct": bd.get("ship_share_landed_combined_pct"),
                             "status": bd.get("status")})

            def avg_factor(key):
                vals = [r[key] for r in rows if isnum(r.get(key))]
                return round(1 - sum(vals) / len(vals) / 100, 2) if vals else None

            out["bundles"] = {"file": bp2.name, "date": next((first_date(str(d[k])) for k in ("updated", "date", "generated_at") if d.get(k)), None),
                              "rows": rows, "findings": [f for f in (d.get("findings") or []) if isinstance(f, str)],
                              "suggested_factor": {"cheapest": avg_factor("saving_pct_cheapest"), "under20": avg_factor("saving_pct_under20")}}
            out["files"].append(bp2.name)
        except Exception as e:
            log(f"  ! cannot read {bp2.name}: {e}")
    n_fr = {"cj": 0, "zendrop": 0, "aliexpress": 0, "card": 0}
    n_manual = n_no_fast = n_qty = n_no_route = 0

    def opt(o):
        if not isinstance(o, dict) or not isnum(o.get("usd")):
            return None
        days = o.get("days") or (f"{o.get('days_min')}-{o.get('days_max')}" if o.get("days_min") is not None else None)
        return {"usd": o["usd"], "name": o.get("name") or o.get("logistic") or o.get("method"), "days": days}

    for p in products:
        pid = p["id"]
        m = manual.get(pid) or {}
        if not isinstance(m, dict):
            m = {}
        e = {}
        if isnum(m.get("shipping_cost_usd")):
            e["manual"] = {"shipping_cost_usd": m["shipping_cost_usd"], "date": first_date(str(m.get("updated_at") or ""))}
            n_manual += 1
        sup = p.get("supplier") or {}
        skey = supplier_key(sup.get("name"), sup.get("product_url"), (p.get("price") or {}).get("currency"))
        e["sup"] = skey
        # the supplier's own freight file first, then any file that has the product, then the card's room SKU
        order = [skey] + [s for _, s in FREIGHT_FILES if s != skey]
        src, fe, fdate = None, None, None
        for s in order:
            if s in freights and isinstance(freights[s][0].get(pid), dict):
                src, fe, fdate = s, freights[s][0][pid], freights[s][1]
                break
        if fe is None:
            cs = card_sku_shipping(p)
            if cs:
                src, fe, fdate = "card", cs, None
        if fe is not None:
            under = pick_freight(fe)
            fr = {"src": src, "cheapest": opt(fe.get("cheapest")), "under20": opt(under[2]) if under else None,
                  "date": first_date(str(fe.get("checked_at") or fe.get("date") or "")) or fdate, "status": fe.get("status")}
            if fr["cheapest"] is None:  # no explicit cheapest: the cheapest of all options
                allo = [opt(o) for o in (fe.get("options") or [])] + [fr["under20"], opt(fe.get("fastest_under_20d"))]
                allo = [o for o in allo if o]
                fr["cheapest"] = min(allo, key=lambda o: o["usd"]) if allo else None
            if fe.get("status") == "no_route" or (fr["cheapest"] is None and fr["under20"] is None):
                fr["status"] = "no_route"  # the supplier returned no shipping method to Israel
                n_no_route += 1
            elif under is None:
                n_no_fast += 1
            if isnum(fe.get("qty")) and fe["qty"] > 1:
                fr["quoted_qty"] = int(fe["qty"])
            if isinstance(fe.get("note"), str) and fe["note"].strip():
                fr["note"] = fe["note"].strip()[:300]
            if fr["cheapest"] or fr["under20"]:
                n_fr[src] += 1
            e["freight"] = fr
        for k in ("retail_ils", "compare_at_ils", "customer_total_ils"):
            if isnum(m.get(k)):
                e[k] = m[k]
        for k in ("retail_src", "price_note", "sale_contains", "action_he"):
            if isinstance(m.get(k), str) and m[k].strip():
                e[k] = m[k].strip()[:400]
        # the units the pricing team priced (checked against the studio's sell quantity on the page)
        if isnum(m.get("price_for_qty")) and float(m["price_for_qty"]).is_integer() and m["price_for_qty"] >= 1:
            e["price_for_qty"] = int(m["price_for_qty"])
        # VR1 (2026-10-11): the pricing team's verdict at its price (ok / below-floor / loss) and whether the slot has
        # another product above the 40% floor; the page shows "חריג: אין חלופה בעמדה" or "מתחת לרף 40%"
        if m.get("flag") in ("ok", "below-floor", "loss"):
            e["price_flag"] = m["flag"]
        if isinstance(m.get("slot_alternative_ok"), bool):
            e["slot_alternative_ok"] = m["slot_alternative_ok"]
        if m.get("addon_only") is True:
            e["addon_only"] = True  # sold only as an add-on to an order (the page shows "רק כתוספת לסל")
        iv = _clean_il_value(m.get("il_value"))
        if iv:
            e["il_value"] = iv
        q = m.get("sell_qty")
        if isnum(q) and float(q).is_integer() and q >= 1:
            e["sell_qty"] = int(q)
            n_qty += 1
        out["products"][pid] = e
    out["counts"] = {"shipping_cj": n_fr["cj"], "shipping_zendrop": n_fr["zendrop"], "shipping_aliexpress": n_fr["aliexpress"],
                     "shipping_card": n_fr["card"], "shipping_manual": n_manual, "no_fast_shipping": n_no_fast,
                     "no_route": n_no_route, "sell_qty": n_qty,
                     "initial_prices": sum(1 for v in out["products"].values() if "retail_ils" in v and str(v.get("retail_src") or "").startswith("initial")),
                     "retail": sum(1 for v in out["products"].values() if "retail_ils" in v)}
    return out



# --------------------------------------------------------------------------- market, styles, suppliers

FLAG_HE = {
    "shipping-estimated": "משלוח מוערך (חציון הקטגוריה)",
    "viable-as-premium-up-to-P75": "כדאי גם כפרימיום, עד האחוזון ה-75",
    "benchmark-mostly-filled-cushions": "ההשוואה בעיקר לכריות ממולאות",
    "benchmark-mostly-double-size": "ההשוואה בעיקר למידה זוגית",
    "benchmark-is-upholstered-ottoman": "ההשוואה לפוף מרופד",
}
# Decisions in status/decisions.json that an access option or a supplier belongs to.
# S4 is taken from directory.json recommended_first_contacts; the rest are named in the decision texts.
ACCESS_DECISIONS = {
    "cj-api-sourcing": "AC1", "aliexpress-ds-api": "AC2", "aliexpress-affiliate-api": "AC2",
    "google-vision-web": "AC3", "dsers-mcp": "AC4", "china-agents": "S6", "1688-agents": "S6",
}
SUPPLIER_DECISIONS = {
    "china-purchasing-agent": "S6", "supplyia": "S6", "leeline-sourcing": "S6", "onestop-wh": "S6",
    "amourlinen": "S7", "magiclinen": "S7",
}


MARKET_PAIR = re.compile(r"(?:^|[\s,(])זוג(?:$|[\s,)])")


def load_market(eco_dir: Path) -> dict | None:
    """data/economics/market-prices.json -> {categories, products, assumptions} (only what the page shows)."""
    mp = eco_dir / "market-prices.json"
    if not mp.exists():
        mp = ROOT / "data" / "economics" / "market-prices.json"
    if not mp.exists():
        return None
    d = read_json(mp)
    cats = {}
    for k, c in (d.get("categories") or {}).items():
        cats[k] = {f: c.get(f) for f in ("label_he", "low", "median", "high", "p75", "band", "n", "confidence", "verdict", "price_for_35pct_median")}
        # pieces in one market price: "וילונות בד, זוג" / "ציפיות (זוג)" are priced per pair, so a sale of 2 single panels
        # is one market unit (not two). An explicit "pieces" in the file wins. "זוגי" (double size) is not a pair.
        pc = c.get("pieces")
        cats[k]["pieces"] = int(pc) if isnum(pc) and pc >= 1 else (2 if MARKET_PAIR.search(c.get("label_he") or "") else 1)
        cats[k]["sources"] = [{f: s.get(f) for f in ("retailer", "title", "size", "price", "sale_price", "url", "date")}
                              for s in (c.get("sources") or []) if isinstance(s, dict)]
    prods = {}
    for pid, e in (d.get("products") or {}).items():
        q = {f: e.get(f) for f in ("category", "suggested_band", "verdict", "margin_at_band", "margin_at_band_min",
                                   "margin_at_band_fx3", "margin_in_bundle", "landed_ils", "price_for_35pct")}
        q["flags"] = [{"id": f, "he": FLAG_HE.get(f, f)} for f in (e.get("flags") or [])]
        prods[pid] = q
    a = d.get("assumptions") or {}
    return {"file": rel(mp), "updated": d.get("updated"), "categories": cats, "products": prods,
            "assumptions": {k: a.get(k) for k in ("fx_usd_ils", "target_margin", "cac_ils", "returns_reserve", "verdict", "band", "qty")}}


def load_styles() -> dict | None:
    sp = ROOT / "data" / "strategy" / "israel-styles.json"
    if not sp.exists():
        return None
    d = read_json(sp)
    styles = [{f: s.get(f) for f in ("id", "name_he", "name_en", "rank", "launch_order", "demand_score", "trend", "tier")}
              for s in d.get("styles") or []]
    styles.sort(key=lambda s: (s.get("rank") or 99))
    return {"file": rel(sp), "doc": d.get("doc"), "date": d.get("date"), "status": d.get("status"),
            "recommended_launch_order": d.get("recommended_launch_order") or [],
            "current_plan_order": d.get("current_plan_order") or [], "styles": styles}


def load_suppliers(decision_ids: set) -> dict | None:
    dp = ROOT / "data" / "suppliers" / "directory.json"
    ap = ROOT / "data" / "suppliers" / "access-options.json"
    if not dp.exists() and not ap.exists():
        return None
    out = {"directory": None, "access": None}
    if dp.exists():
        d = read_json(dp)
        first = {r["id"]: r for r in d.get("recommended_first_contacts") or [] if isinstance(r, dict) and r.get("id")}
        rows = []
        for s in d.get("suppliers") or []:
            q = {f: s.get(f) for f in ("id", "name", "website", "section", "type", "country", "categories", "model", "moq",
                                       "price_level", "shipping_to_israel", "lead_time", "standards", "integration",
                                       "status", "unverified", "sample_links", "price_note")}
            fit = s.get("nordic_fit") or {}
            q["fit"] = fit.get("score") if isinstance(fit, dict) else fit
            q["fit_why"] = fit.get("rationale") if isinstance(fit, dict) else None
            c = s.get("contact") or {}
            q["contact"] = {k: v for k, v in c.items() if isinstance(v, str)} if isinstance(c, dict) else {}
            dec = SUPPLIER_DECISIONS.get(s.get("id")) or ("S4" if s.get("id") in first else None)
            q["decision"] = dec if dec in decision_ids else None
            if s.get("id") in first:
                q["first_rank"] = first[s["id"]].get("rank")
                q["first_why"] = first[s["id"]].get("why")
            q["next_wave"] = s.get("id") in (d.get("next_wave") or [])
            rows.append(q)
        out["directory"] = {"file": rel(dp), "updated": d.get("updated"), "scope": d.get("scope"),
                            "fields": d.get("fields"), "suppliers": rows}
    if ap.exists():
        a = read_json(ap)
        opts = []
        for o in a.get("options") or []:
            q = {f: o.get(f) for f in ("id", "name", "type", "priority", "unlocks", "user_steps", "requirements", "cost",
                                       "approval_days", "depends_on", "sources", "verified", "env_vars", "checked")}
            dec = ACCESS_DECISIONS.get(o.get("id"))
            q["decision"] = dec if dec in decision_ids else None
            opts.append(q)
        opts.sort(key=lambda o: (o.get("priority") if isinstance(o.get("priority"), (int, float)) else 999, o.get("id") or ""))
        out["access"] = {"file": rel(ap), "updated": a.get("updated"), "note": a.get("note"), "options": opts}
    return out


# --------------------------------------------------------------------------- supplier comparison

# The deep AliExpress pass (studio-rules ז.00, 2026-10-11) writes one file per room here. Records:
# {room, slot, style, item_id, title, sku, price_usd, ship_usd, ship_days, landed_ils, retail_band_ils,
#  margin_ils, margin_pct, fit, reason, compared_to: {card_id, landed_ils}, verdict: best|alternative|reject}
DEEP_DIR = ROOT / "data" / "leads" / "aliexpress" / "deep-2026-10"
AE_FIRST_CALL = ROOT / "data" / "leads" / "aliexpress" / "api-first-call-2026-10-11.md"
AE_SHORTLIST = ROOT / "data" / "leads" / "aliexpress" / "shortlist-2026-10-10.json"
SEEN = ROOT / "data" / "sources" / "seen.json"

# The six styles, in the order of studio-rules ד.8. Hebrew names come from data/strategy/israel-styles.json.
STYLE_ORDER = ["nordic", "warm-modern", "japandi", "mediterranean", "modern-country", "boho"]
STYLE_FALLBACK_HE = {"nordic": "נורדי", "warm-modern": "מודרני חם", "japandi": "ג'פנדי", "mediterranean": "ים תיכוני",
                     "modern-country": "כפרי מודרני", "boho": "בוהו"}
STYLE_ALIASES = {
    "nordic": "nordic", "scandinavian": "nordic", "scandi": "nordic", "נורדי": "nordic", "סקנדינבי": "nordic",
    "warm-modern": "warm-modern", "modern-warm": "warm-modern", "warmmodern": "warm-modern", "מודרני-חם": "warm-modern",
    "japandi": "japandi", "ג'פנדי": "japandi", "ג'אפנדי": "japandi",
    "mediterranean": "mediterranean", "med": "mediterranean", "ים-תיכוני": "mediterranean",
    "modern-country": "modern-country", "country": "modern-country", "modern-farmhouse": "modern-country",
    "rustic-modern": "modern-country", "כפרי-מודרני": "modern-country", "כפרי": "modern-country",
    "boho": "boho", "bohemian": "boho", "בוהו": "boho",
}
ROOM_ALIASES = dict(ROOM_DIRS, **ROOM_TAGS, **{"living": "living-room", "kitchen": "dining-room", "bathroom": "bath",
                                               "office": "work", "entry": "hall", "bedroom-master": "master"})
DEEP_VERDICTS = {"best", "alternative", "reject"}
SUP_HE = {"aliexpress": "AliExpress", "cj": "CJ", "zendrop": "Zendrop", "il": "ספק ישראלי", "other": "אחר"}
# Shipping to Israel written in a card (the card schema has no shipping-cost field): first the default SKU's
# options.skus[].shipping_il, then the notes: "Shipping to IL: cheapest 23.39 USD AliExpress standard shipping, 22-32 days",
# "SHIPPING to IL: only one option returned: AliExpress Selection Standard 1.99 USD, 6-15 days", "Shipping to IL: regular
# $14.24, 14 days" (Zendrop). The first amount after the label is the cheapest option in every format seen.
SHIP_HEAD = re.compile(r"shipping to IL\s*:", re.I)
SHIP_AMOUNT = re.compile(r"\$\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*USD")
SHIP_DAYS = re.compile(r"(\d+)(?:\s*[-–]\s*(\d+))?\s*days", re.I)
AE_ITEM = re.compile(r"aliexpress\.[a-z.]+/item/(\d+)\.html", re.I)


def to_num(v):
    if isnum(v):
        return float(v)
    if isinstance(v, str):
        m = re.search(r"-?\d+(?:\.\d+)?", v.replace(",", ""))
        return float(m.group(0)) if m else None
    return None


def days_pair(v):
    """'6-15', 14, [6, 15], {min, max} -> [6, 15]; None when there is no number."""
    if isinstance(v, dict):
        v = [v.get(k) for k in ("min", "days_min", "max", "days_max")]
    if isnum(v):
        return [int(v), int(v)]
    if isinstance(v, (list, tuple)):
        ns = [int(x) for x in v if isnum(x)]
    elif isinstance(v, str):
        ns = [int(x) for x in re.findall(r"\d+", v)]
    else:
        return None
    return [min(ns), max(ns)] if ns else None


def band_pair(v):
    """retail band in ILS: [lo, hi], {low, high}, a number or '129-149' -> [lo, hi]."""
    if isinstance(v, dict):
        v = [v.get(k) for k in ("low", "min", "lo", "high", "max", "hi")]
    if isnum(v):
        return [float(v), float(v)]
    if isinstance(v, (list, tuple)):
        ns = [float(x) for x in v if isnum(x)]
    elif isinstance(v, str):
        ns = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", v.replace(",", ""))]
    else:
        return None
    return [min(ns), max(ns)] if ns else None


def style_key(v):
    if not isinstance(v, str) or not v.strip():
        return None
    k = re.sub(r"[\s_]+", "-", v.strip().lower())
    return STYLE_ALIASES.get(k) or (k if k in STYLE_ORDER else None)


def room_key(v, room_ids):
    if not isinstance(v, str):
        return None
    k = v.strip().lower()
    return k if k in room_ids else ROOM_ALIASES.get(k)


def supplier_key(name, url, currency) -> str:
    n = (name or "").lower()
    host = ""
    m = re.match(r"https?://([^/]+)", url or "")
    if m:
        host = m.group(1).lower()
    if re.search(r"\bcj\b|cjdropshipping", n) or "cjdropshipping" in host:
        return "cj"
    if "zendrop" in n or "zendrop" in host:
        return "zendrop"
    if "aliexpress" in n or "aliexpress" in host:
        return "aliexpress"
    if str(currency or "").upper() == "ILS" or host.endswith(".co.il") or re.search(r"[֐-׿]", name or ""):
        return "il"
    return "other"


def ae_canon(item_id, aliases) -> str | None:
    """Canonical AliExpress item id (.us 3256... ids; .com 1005... ids and SKUs map through seen.json aliases)."""
    if item_id is None:
        return None
    s = re.sub(r"\D", "", str(item_id))
    if not s:
        return None
    seen = set()
    key = "aliexpress:" + s
    while key in aliases and key not in seen:
        seen.add(key)
        key = aliases[key]
    return key.split(":", 1)[1] if key.startswith("aliexpress:") else s


def strip_md(t: str) -> str:
    return re.sub(r"\*\*|`", "", t or "").strip()


def frac(v):
    """margin percent as a fraction: 0.31 or 31 or '31%' -> 0.31."""
    x = to_num(v)
    if x is None:
        return None
    return x / 100 if abs(x) > 1.5 else x


def card_ship(p: dict) -> dict | None:
    """Shipping to Israel in USD written in the card, for cards without CJ freight (AliExpress, Zendrop)."""
    o = p.get("options") if isinstance(p.get("options"), dict) else {}
    sku = next((x for x in o.get("skus") or [] if isinstance(x, dict) and x.get("id") == o.get("default_sku")), None)
    si = (sku or {}).get("shipping_il") or {}
    if isnum(si.get("amount")) and str(si.get("currency") or "").upper() == "USD":
        return {"usd": float(si["amount"]), "days": days_pair(si.get("days")), "src": "options"}
    notes = p.get("notes") or ""
    m = SHIP_HEAD.search(notes)
    if not m:
        return None
    seg = notes[m.end():m.end() + 160]
    a = SHIP_AMOUNT.search(seg)
    if not a:
        return None
    d = SHIP_DAYS.search(seg[a.end():a.end() + 90])
    days = [int(x) for x in d.groups() if x] if d else []
    return {"usd": float(a.group(1) or a.group(2)), "days": [min(days), max(days)] if days else None, "src": "notes"}


def load_deep(deep_dir: Path, room_ids: set, slot_keys: set, aliases: dict) -> dict:
    """All records of the deep AliExpress pass, normalized. Bad records are reported, not dropped silently."""
    out = {"dir": rel(deep_dir) if deep_dir.is_relative_to(ROOT) else str(deep_dir), "present": False,
           "files": [], "records": [], "unmatched": [], "warnings": []}
    if not deep_dir.exists():
        return out
    for f in sorted(deep_dir.glob("*.json")):
        try:
            d = read_json(f)
        except Exception as e:
            out["warnings"].append(f"{f.name}: {type(e).__name__}: {e}"[:200])
            continue
        if isinstance(d, list):
            recs, meta = d, {}
        elif isinstance(d, dict):
            recs = next((d[k] for k in ("records", "items", "candidates", "results", "rows") if isinstance(d.get(k), list)), [])
            meta = d
        else:
            recs, meta = [], {}
        n_ok = 0
        for i, r in enumerate(recs):
            if not isinstance(r, dict):
                continue
            room = room_key(r.get("room") or meta.get("room") or f.stem, room_ids)
            slot = str(r.get("slot") or "").strip()
            style = style_key(r.get("style"))
            item = ae_canon(r.get("item_id") or (AE_ITEM.search(str(r.get("url") or "")) or [None, None])[1], aliases)
            where = f"{f.name} #{i + 1}"
            problem = None
            if not item:
                problem = "אין item_id"
            elif not room:
                problem = f"חדר לא מוכר: {r.get('room') or meta.get('room') or f.stem}"
            elif f"{room}/{slot}" not in slot_keys:
                problem = f"עמדה לא קיימת: {room}/{slot}"
            elif not style:
                problem = f"סגנון לא מוכר: {r.get('style')}"
            if problem:
                out["unmatched"].append({"where": where, "why": problem, "title": str(r.get("title") or "")[:120],
                                         "item_id": str(r.get("item_id") or "")})
                continue
            verdict = str(r.get("verdict") or "").strip().lower()
            ct = r.get("compared_to") if isinstance(r.get("compared_to"), dict) else {}
            url = r.get("url") if isinstance(r.get("url"), str) and r["url"].startswith("https://") else f"https://www.aliexpress.com/item/{item}.html"
            out["records"].append({
                "room": room, "slot": slot, "key": f"{room}/{slot}", "style": style, "item": item, "url": url,
                "title": str(r.get("title") or "").strip() or f"AliExpress {item}", "sku": r.get("sku"),
                "price_usd": to_num(r.get("price_usd")), "ship_usd": to_num(r.get("ship_usd")),
                "ship_days": days_pair(r.get("ship_days")), "band": band_pair(r.get("retail_band_ils")),
                "landed_ils": to_num(r.get("landed_ils")), "margin_ils": to_num(r.get("margin_ils")),
                "margin_pct": frac(r.get("margin_pct")), "fit": to_num(r.get("fit")),
                "reason": str(r.get("reason") or "").strip() or None,
                "verdict": verdict if verdict in DEEP_VERDICTS else None,
                "compared_to": {"card_id": ct.get("card_id"), "landed_ils": to_num(ct.get("landed_ils"))} if ct.get("card_id") else None,
                "file": f.name,
            })
            n_ok += 1
        st = f.stat()
        out["files"].append({"file": f.name, "records": len(recs), "ok": n_ok,
                             "date": first_date(str(meta.get("updated") or meta.get("date") or ""))
                             or (git_date(f) if f.is_relative_to(ROOT) else None)
                             or dt.date.fromtimestamp(st.st_mtime).isoformat()})
    out["present"] = bool(out["files"])
    return out


def load_ae_first_call(path: Path, aliases: dict) -> list[dict]:
    """The table of data/leads/aliexpress/api-first-call-2026-10-11.md:
    | item_id | room/slot | SKU | price USD | shipping (USD, days) | card | why |"""
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(\d{10,})\s*\|(.*)\|\s*$", line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) < 6:
            continue
        where, sku, price, ship, card, why = cells[:6]
        room, _, slot = where.partition("/")
        price_t, ship_t = strip_md(price), strip_md(ship)
        no_ship = "אין משלוח" in ship_t
        ship_usd, days = None, None
        if not no_ship and "לא נבדק" not in ship_t:
            a, _, b = ship_t.partition(",")
            ship_usd, days = to_num(a), days_pair(b)
        rows.append({"item": ae_canon(m.group(1), aliases), "room": room.strip(), "slot": slot.strip(),
                     "sku": None if sku in ("—", "-", "") else strip_md(sku),
                     "price_usd": None if "placeholder" in price_t.lower() else to_num(price_t),
                     "price_from": price_t.split("(")[0].strip().endswith("+"),
                     "ship_usd": ship_usd, "ship_days": days, "no_ship": no_ship,
                     "carded": card.strip().startswith("כן"), "why": strip_md(why)})
    return rows


def build_comparison(slots: dict, products: list[dict], slot_by_key: dict, room_ids: list[str], deep_dir: Path) -> dict:
    """data.json 'comparison': room -> slot -> candidates, from the product cards (all suppliers), the deep AliExpress
    pass and the first AliExpress API call. Only facts here; the page computes landed cost and margin with the same
    econCalc as the profit screen, so the numbers agree and follow the studio's settings."""
    aliases = {}
    if SEEN.exists():
        try:
            aliases = read_json(SEEN).get("aliases") or {}
        except Exception as e:
            log(f"  ! cannot read {rel(SEEN)}: {e}")
    titles = {}
    if AE_SHORTLIST.exists():
        try:
            for it in read_json(AE_SHORTLIST):
                if isinstance(it, dict) and it.get("item_id"):
                    titles[ae_canon(it["item_id"], aliases)] = it.get("title")
        except Exception as e:
            log(f"  ! cannot read {rel(AE_SHORTLIST)}: {e}")
    slot_keys = set(slot_by_key)
    by_id = {p["id"]: p for p in products}

    # styles: the six, names from israel-styles.json
    names = {}
    sp = ROOT / "data" / "strategy" / "israel-styles.json"
    if sp.exists():
        try:
            for s in read_json(sp).get("styles") or []:
                if s.get("id") in STYLE_ORDER and s.get("name_he"):
                    names[s["id"]] = s["name_he"].split(" / ")[0].strip()
        except Exception:
            pass
    styles = [{"id": k, "name_he": names.get(k) or STYLE_FALLBACK_HE[k]} for k in STYLE_ORDER]

    deep = load_deep(deep_dir, set(room_ids), slot_keys, aliases)
    api = load_ae_first_call(AE_FIRST_CALL, aliases)
    api_by_item = {r["item"]: r for r in api}

    def card_cand(p, shared):
        sup = p.get("supplier") or {}
        price = p.get("price") or {}
        c = {"k": "card", "id": p["id"], "sup": supplier_key(sup.get("name"), sup.get("product_url"), price.get("currency"))}
        if shared:
            c["shared"] = True
        ship = card_ship(p)
        if ship:
            c["ship"] = ship
        mi = AE_ITEM.search(sup.get("product_url") or "")
        if mi:
            c["ae"] = ae_canon(mi.group(1), aliases)
            a = api_by_item.get(c["ae"])
            if a and a.get("why"):
                c["note"] = a["why"]
        return c

    rooms_out: dict[str, dict] = {}
    n_cards = n_deep = n_api = 0
    used_api = set()
    by_sup: dict[str, int] = {}
    for rid in room_ids:
        rslots = {}
        for s in slots.get(rid) or []:
            cands = []
            ae_index = {}
            best_set = set()  # deep candidates whose shown price already comes from a 'best' record
            for pid in s.get("direct") or []:
                cands.append(card_cand(by_id[pid], False))
            for pid in s.get("shared_ids") or []:
                cands.append(card_cand(by_id[pid], True))
            for c in cands:
                if c.get("ae"):
                    ae_index[c["ae"]] = c
            # deep AliExpress records: one candidate per item, one entry per style
            for r in (x for x in deep["records"] if x["key"] == s["key"]):
                c = ae_index.get(r["item"])
                if c is None:
                    q = sell_qty_default({"name": r["title"], "notes": r["reason"] or "", "_slot_key": s["key"], "_shared_in": []}, slot_by_key)
                    c = {"k": "deep", "id": "ae:" + r["item"], "sup": "aliexpress", "item": r["item"], "title": r["title"],
                         "url": r["url"], "sku": r["sku"], "price_usd": r["price_usd"], "ship_usd": r["ship_usd"],
                         "ship_days": r["ship_days"], "band": r["band"], "qty": q, "styles": {}}
                    a = api_by_item.get(r["item"])
                    if a and a.get("why"):
                        c["note"] = a["why"]
                    cands.append(c)
                    ae_index[r["item"]] = c
                    n_deep += 1
                entry = {k: r[k] for k in ("fit", "verdict", "reason", "landed_ils", "margin_ils", "margin_pct",
                                           "compared_to", "sku", "price_usd", "ship_usd", "ship_days", "band", "file")}
                (c.setdefault("deep", {}) if c["k"] == "card" else c["styles"])[r["style"]] = entry
                # the first record the pass itself picked as best (styles in file order) sets the price shown for "all styles"
                if c["k"] == "deep" and r["verdict"] == "best" and c["id"] not in best_set:
                    best_set.add(c["id"])
                    for k in ("sku", "price_usd", "ship_usd", "ship_days", "band"):
                        if r[k] is not None:
                            c[k] = r[k]
            # first API call: items that did not become a card (no shipping to Israel, 76 days, no price...)
            for a in api:
                if a["carded"] or a["item"] in ae_index or f"{room_key(a['room'], set(room_ids))}/{a['slot']}" != s["key"]:
                    continue
                cands.append({"k": "api", "id": "ae:" + a["item"], "sup": "aliexpress", "item": a["item"],
                              "title": titles.get(a["item"]) or f"AliExpress {a['item']}",
                              "url": f"https://www.aliexpress.com/item/{a['item']}.html", "sku": a["sku"],
                              "price_usd": a["price_usd"], "price_from": a["price_from"], "ship_usd": a["ship_usd"],
                              "ship_days": a["ship_days"], "no_ship": a["no_ship"], "rejected": True, "note": a["why"]})
                used_api.add(a["item"])
                n_api += 1
            for c in cands:
                by_sup[c["sup"]] = by_sup.get(c["sup"], 0) + 1
                n_cards += c["k"] == "card"
            rslots[s["id"]] = cands
        rooms_out[rid] = rslots
    n_slots = sum(1 for r in rooms_out.values() for v in r.values() if v)
    log(f"  comparison: {n_slots} slots with candidates · cards {n_cards} · deep AliExpress {len(deep['records'])} records"
        f" in {len(deep['files'])} files -> {n_deep} new candidates · first API call {n_api} · unmatched {len(deep['unmatched'])}"
        + ("" if deep["present"] else f" (no {deep['dir']} yet)"))
    for w in deep["warnings"]:
        log(f"  ! deep file {w}")
    return {
        "styles": styles,
        "suppliers": SUP_HE,
        "fit_min": 7,
        "rooms": rooms_out,
        "sources": {
            "deep": {k: deep[k] for k in ("dir", "present", "files", "warnings")} | {"records": len(deep["records"]),
                                                                                   "unmatched": deep["unmatched"][:60],
                                                                                   "n_unmatched": len(deep["unmatched"])},
            "api": {"file": rel(AE_FIRST_CALL) if AE_FIRST_CALL.exists() else None, "rows": len(api),
                    "carded": sum(1 for a in api if a["carded"]), "shown": len(used_api)},
            "by_supplier": by_sup,
        },
    }


# --------------------------------------------------------------------------- furniture (the "ריהוט" screen)

# Furniture leads from Israeli suppliers (studio-rules ג, "מדור ריהוט וספקים ישראליים", 2026-10-11). Records:
# {supplier_id, supplier_name, supplier_new, website, room, slot, tier, model_name, url, price_ils, price_type,
#  dimensions_cm, materials, options: {colors: [{label_he, hex}], fabrics, sizes, finishes}, lead_time,
#  delivery_assembly, photo_type, image_urls, styles, fit_by_style, wow_gate: {applies, passed, failed_checks, note},
#  standard?, verdict, reason}
FURN_DIR = ROOT / "data" / "leads" / "furniture-il"
FURN_EXPRESS = ROOT / "data" / "leads" / "furniture-express" / "models-2026-10-11.json"
WOW_REVIEW = ROOT / "docs" / "proposals" / "furniture-wow-review-2026-10-11.md"
SUPPLIERS_DIR = ROOT / "data" / "suppliers"
OUTREACH_README = ROOT / "docs" / "suppliers" / "outreach" / "README.md"
# Tiers of the 16 fixed-product slots, docs/proposals/furniture-wow-review-2026-10-11.md §2 (a record's own tier wins)
TIER_BY_SLOT = {
    "living-room/sofa": "A", "living-room/armchair": "A", "master/bed": "A", "dining-room/dining-table": "A",
    "living-room/coffee-table": "B", "dining-room/dining-chairs": "B", "dining-room/dining-bench": "B", "bath/vanity": "B",
    "work/desk": "B", "work/chair": "B", "kids/bed": "B",
    "master/nightstands": "C", "hall/console": "C", "hall/bench": "C", "work/shelf": "C", "kids/desk": "C",
}
TIER_FALLBACK = {"A": {"he": "גיבור (וואו חובה)", "need": "עוברים את שער הוואו המלא"},
                 "B": {"he": "משנית בולטת", "need": "צורה פשוטה מספיקה, אבל הביצוע והחומר חייבים להחזיק תקריב: שערים 1, 3 ו-4"},
                 "C": {"he": "משנית", "need": "רהיט נקי ופשוט שמתאים לפלטה: שערים 1 ו-3"}}
GATE_SHORT = {1: "צילום אמיתי", 2: "פרופורציות", 3: "חומרים", 4: "ביצוע", 5: "פרט חתימה", 6: "מבחן השער"}
FURN_WORDS = re.compile(r"ריהוט|רהיט|ספ[הות]|כורס|מיט|שולח|קונסול|שיד|ספסל|ארון|כיסא|כסא|furniture|sofa|bed|table|chair", re.I)


def tier_key(v):
    s = str(v or "").strip().upper()
    return {"A": "A", "B": "B", "C": "C", "1": "A", "2": "B", "3": "C", "א": "A", "ב": "B", "ג": "C"}.get(s[:1]) if s else None


def verdict_class(v) -> str:
    t = str(v or "").strip().lower()
    if not t or re.search(r"pending|ממתין|לבדיקה|לא נבדק", t):
        return "pending"
    if re.search(r"reject|להוריד|נדחה|נפסל|drop", t):
        return "reject"
    if re.search(r"condition|בתנאי|רק בהתאמה|לשמור רק|maybe|אולי", t):
        return "conditional"
    if re.search(r"keep|shortlist|best|pass|approve|candidate|לשמור|מומלץ|מועמד|עבר|מתאים", t):
        return "ok"
    return "pending"


def photo_key(v, *texts) -> str:
    t = str(v or "").strip().lower()
    if t in ("real", "photo", "render", "mixed", "none", "unknown"):
        return "real" if t == "photo" else t
    t = " ".join([t] + [str(x or "") for x in texts])
    # "the photo looks like a render" is a render: any mention of a render wins over the word "photo"
    if re.search(r"render|הדמי", t, re.I):
        return "render"
    return "real" if re.search(r"\breal\b|\bphoto\b|אמיתי|אולם|סטודיו|מהסדנה|צילום טלפון", t, re.I) else "unknown"


def price_type_key(v) -> str:
    t = str(v or "").strip().lower()
    if re.search(r"dealer|wholesale|trade|סוחר|סיטונ", t):
        return "dealer"
    if re.search(r"consumer|retail|list|צרכן|באתר", t):
        return "consumer"
    return "unknown"


def str_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [x.strip() for x in re.split(r"[;,،]\s*", v) if x.strip()]
    out = []
    for x in v if isinstance(v, list) else [v]:
        if isinstance(x, dict):
            x = x.get("label_he") or x.get("label") or x.get("name") or ""
        if str(x).strip():
            out.append(str(x).strip())
    return out


def norm_options(o) -> dict:
    if isinstance(o, str):
        return {"colors": [], "fabrics": [], "sizes": [], "finishes": [], "text": o.strip() or None}
    o = o if isinstance(o, dict) else {}
    colors = []
    for c in o.get("colors") or []:
        if isinstance(c, dict):
            hx = c.get("hex") if isinstance(c.get("hex"), str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", c.get("hex") or "") else None
            lab = str(c.get("label_he") or c.get("label") or c.get("name") or hx or "").strip()
            if lab or hx:
                colors.append({"label_he": lab or hx, "hex": hx})
        elif isinstance(c, str) and c.strip():
            colors.append({"label_he": c.strip(), "hex": c.strip() if re.fullmatch(r"#[0-9A-Fa-f]{6}", c.strip()) else None})
    return {"colors": colors, "fabrics": str_list(o.get("fabrics")), "sizes": str_list(o.get("sizes")),
            "finishes": str_list(o.get("finishes")), "text": str(o.get("text") or o.get("note") or "").strip() or None}


def norm_fits(fits, styles) -> tuple[dict, list]:
    out = {}
    for k, v in (fits or {}).items() if isinstance(fits, dict) else []:
        sk = style_key(k)
        x = to_num(v.get("score") if isinstance(v, dict) else v)
        if sk and x is not None:
            out[sk] = x
    st = [s for s in (style_key(x) for x in (styles or []) if isinstance(x, str)) if s]
    return out, list(dict.fromkeys(st))


def name_token_re(tok: str):
    return re.compile(r"(?<![\w֐-׿])" + re.escape(tok) + r"(?![\w֐-׿])")


def load_wow_review(path: Path) -> dict:
    """§1 verdict table (furniture-express), §2 tier labels and the wow gate checks."""
    out = {"file": rel(path) if path.exists() else None, "verdicts": [], "tiers": dict(TIER_FALLBACK), "gate": []}
    if not path.exists():
        return out
    sec = None
    gate = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            sec = (re.match(r"##\s*(\d+)\.", line) or [None, None])[1]
            gate = False
            continue
        if sec == "1":
            m = re.match(r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", line)
            if m:
                name = strip_md(m.group(2))
                out["verdicts"].append({"n": int(m.group(1)), "token": name.split(" (")[0].strip(),
                                        "where": (re.search(r"\((.+)\)", name) or [None, ""])[1],
                                        "verdict": strip_md(m.group(3)), "why": strip_md(m.group(4))})
        elif sec == "2":
            m = re.match(r"^\|\s*\*\*([אבג])\.\s*(.+?)\*\*\s*(\(.*?\))?\s*\|.*?\|\s*(.+?)\s*\|\s*$", line)
            if m:
                k = tier_key(m.group(1))
                out["tiers"][k] = {"he": m.group(2).strip(), "where": (m.group(3) or "").strip("() ") or None, "need": strip_md(m.group(4))}
            if line.startswith("**שער הוואו"):
                gate = True
                continue
            if gate:
                m = re.match(r"^(\d+)\.\s+(.+)$", line)
                if m:
                    out["gate"].append({"n": int(m.group(1)), "short": GATE_SHORT.get(int(m.group(1)), m.group(1)), "text": strip_md(m.group(2))})
                elif line.strip() and out["gate"]:
                    gate = False
    return out


def coop_state(sup: dict, readme_rows: dict, board_log: list[dict]) -> dict:
    """The cooperation request (בקשת שת"פ) to one supplier: none / draft / sent / replied, with the evidence.
    Order: an explicit coop_request / outreach object in the supplier record; the directory status and outreach_log;
    the outreach README tables; the board log ("נשלח"/"נשלחו" with the supplier's name)."""
    for k in ("coop_request", "outreach"):
        o = sup.get(k)
        if isinstance(o, dict) and o.get("state") in ("none", "draft", "sent", "replied"):
            tone = o.get("tone") if o.get("tone") in ("positive", "negative", "bounced") else None
            return {"state": o["state"], "tone": tone, "date": first_date(str(o.get("date") or "")), "note": o.get("note"), "src": k}
    status = sup.get("status") or ""
    logs = [x for x in sup.get("outreach_log") or [] if isinstance(x, str)]
    if status in ("replied_positive", "declined", "not_relevant") or any(re.search(r"ענו|התקשרו|השיבו|replied", x) for x in logs):
        hit = next((x for x in reversed(logs) if re.search(r"ענו|התקשרו|השיבו|replied", x)), logs[-1] if logs else "")
        tone = "positive" if status == "replied_positive" else "negative" if status in ("declined", "not_relevant") else None
        return {"state": "replied", "tone": tone, "date": first_date(hit), "note": hit, "src": "directory.json"}
    if status == "email_bounced" or any(re.search(r"נשלח|sent|550|לא קיים", x) for x in logs):
        hit = next((x for x in reversed(logs)), "")
        return {"state": "sent", "tone": "bounced" if status == "email_bounced" else None, "date": first_date(hit), "note": hit, "src": "directory.json"}
    names = sup.get("_aliases") or []
    row = next((readme_rows[a] for a in names if a in readme_rows), None)
    if row and re.search(r"נשלח", row):
        return {"state": "sent", "date": first_date(row), "note": row, "src": rel(OUTREACH_README)}
    for e in reversed(board_log):
        t = e.get("text") or ""
        if re.search(r"נשלח", t) and any(name_token_re(a).search(t) for a in names):
            return {"state": "sent", "date": e.get("date"), "note": t[:220], "src": "status/board.md"}
    if (row and "טיוטה" in row) or any("טיוטה" in x for x in logs):
        return {"state": "draft", "date": first_date(row or ""), "note": row if row and "טיוטה" in row else next(x for x in logs if "טיוטה" in x),
                "src": rel(OUTREACH_README) if row and "טיוטה" in row else "directory.json"}
    return {"state": "none", "date": None, "note": row, "src": rel(OUTREACH_README) if row else None}


def supplier_aliases(name: str, sid: str) -> list[str]:
    """Short names the outreach files and the board use: 'רהיטי יראון' -> יראון, 'דיבאני סנטר (...)' -> דיבאני סנטר, דיבאני."""
    out = []
    base = re.sub(r'בע"מ|בע״מ', "", re.split(r"\s*[(/:]", name or "")[0]).strip(" ,.-")
    if base:
        out.append(base)
        words = base.split()
        generic = {"רהיטי", "ריהוט", "קבוצת", "יצרני", "תאורה", "חברת"}
        if len(words) > 1 and words[0] in generic and len(" ".join(words[1:])) >= 3:
            out.append(" ".join(words[1:]))
        if len(words) > 1 and words[0] not in generic and len(words[0]) >= 4:
            out.append(words[0])
    for m in re.finditer(r"\(([^)]+)\)", name or ""):
        t = m.group(1).strip()
        if 3 <= len(t) <= 30 and not re.search(r"\d|בע\"מ|;|,", t):
            out.append(t)
    return list(dict.fromkeys(a for a in out if len(a) >= 3))


def readme_outreach_rows(path: Path) -> dict:
    """supplier short name -> the status cell (main table) or the state cell (Gmail round table) of the outreach README."""
    rows = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(cells) >= 7 and re.fullmatch(r"\d+", cells[0]):
            for a in supplier_aliases(strip_md(cells[1]), ""):
                rows.setdefault(a, strip_md(cells[5]))
        elif len(cells) == 3 and cells[0] not in ("ספק", "---") and not set(cells[0]) <= set("- "):
            for a in supplier_aliases(strip_md(cells[0]), ""):
                rows[a] = strip_md(cells[2])  # the Gmail round is newer than the main table
    return rows


def read_records(path: Path):
    d = read_json(path)
    if isinstance(d, list):
        return d, {}
    if isinstance(d, dict):
        return next((d[k] for k in ("records", "models", "items", "candidates", "results", "suppliers") if isinstance(d.get(k), list)), []), d
    return [], {}


def load_furniture(order: list[str], products: list[dict], directory: dict | None, board_log: list[dict],
                   furn_dir: Path, sup_dir: Path) -> dict:
    room_ids = set(order)
    # the 16 fixed-product slots, in house order
    slots = []
    for rid in order:
        p = ROOT / "data" / "slots" / f"{rid}.json"
        if not p.exists():
            continue
        for s in read_json(p).get("slots") or []:
            if s.get("kind") == "fixed-product":
                key = f"{rid}/{s['id']}"
                slots.append({"key": key, "room": rid, "id": s["id"], "name_he": s.get("name_he"), "tier": TIER_BY_SLOT.get(key),
                              "as_shown": s.get("as_shown"), "frames": s.get("frames") or [], "sales_note": s.get("sales_note")})
    slot_keys = {s["key"] for s in slots}
    review = load_wow_review(WOW_REVIEW)
    dir_sups = {s["id"]: s for s in (directory or {}).get("suppliers") or [] if isinstance(s, dict) and s.get("id")}
    cards_by_url = {}
    for p in products:
        u = ((p.get("supplier") or {}).get("product_url") or "").strip()
        if u and p.get("_slot_key") in slot_keys:
            cards_by_url[u.rstrip("/").lower()] = p

    models, unmatched, warnings, files = [], [], [], []

    def add(rec: dict, src: str, where: str):
        room = room_key(rec.get("room"), room_ids)
        slot = str(rec.get("slot") or "").strip()
        key = f"{room}/{slot}"
        if not rec.get("model_name"):
            return
        if key not in slot_keys:
            unmatched.append({"where": where, "why": f"עמדת ריהוט לא קיימת: {rec.get('room')}/{slot}", "title": str(rec.get("model_name"))[:120]})
            return
        fits, styles = norm_fits(rec.get("fit_by_style"), rec.get("styles"))
        url = rec.get("url") if isinstance(rec.get("url"), str) and rec["url"].startswith("https://") else None
        card = cards_by_url.get((url or "").rstrip("/").lower())
        wg = rec.get("wow_gate") if isinstance(rec.get("wow_gate"), dict) else None
        tier = tier_key(rec.get("tier")) or TIER_BY_SLOT.get(key)
        imgs = [u for u in rec.get("image_urls") or [] if isinstance(u, str) and u.startswith("https://")]
        m = {
            "id": re.sub(r"[^\w-]+", "-", f"{rec.get('supplier_id') or 'x'}-{key}-{rec.get('sku') or rec.get('model_name')}")[:120],
            "src": src, "supplier_id": rec.get("supplier_id"), "supplier_name": rec.get("supplier_name"),
            "supplier_new": bool(rec.get("supplier_new")), "website": rec.get("website"),
            "room": room, "slot": slot, "key": key, "tier": tier, "model_name": str(rec["model_name"]).strip(), "url": url,
            "sku": rec.get("sku"), "price_ils": to_num(rec.get("price_ils")), "price_original_ils": to_num(rec.get("price_original_ils")),
            "price_type": price_type_key(rec.get("price_type")), "price_type_raw": rec.get("price_type"),
            "dimensions": rec.get("dimensions_cm") if rec.get("dimensions_cm") is not None else rec.get("dimensions"),
            "materials": rec.get("materials"), "options": norm_options(rec.get("options")),
            "lead_time": rec.get("lead_time"), "delivery_assembly": rec.get("delivery_assembly") or rec.get("delivery_notes"),
            "photo_type": "none" if rec.get("image_urls") == [] and not rec.get("photo_type") else photo_key(rec.get("photo_type"), rec.get("image_note"), rec.get("reason") if src == "furniture-express" else None),
            "image_note": rec.get("image_note"),
            "image_urls": imgs[:4], "n_images": len(imgs), "styles": styles, "fits": fits,
            "wow_gate": {"applies": bool(wg.get("applies", tier == "A")), "passed": wg.get("passed") if isinstance(wg.get("passed"), bool) else None,
                         "failed_checks": [x for x in (wg.get("failed_checks") or []) if isinstance(x, (int, str))],
                         "note": wg.get("note")} if wg else {"applies": tier == "A", "passed": None, "failed_checks": [], "note": None},
            "standard": rec.get("standard"), "verdict": rec.get("verdict"), "verdict_class": verdict_class(rec.get("verdict")),
            "reason": rec.get("reason"), "sourcing_reason": rec.get("sourcing_reason"),
            "card_id": card["id"] if card else None, "card_status": card.get("status") if card else None,
        }
        models.append(m)

    # 1. the new Israeli supplier leads
    if furn_dir.exists():
        for f in sorted(furn_dir.glob("*.json")):
            try:
                recs, meta = read_records(f)
            except Exception as e:
                warnings.append(f"{f.name}: {type(e).__name__}: {e}"[:200])
                continue
            for i, r in enumerate(recs):
                if isinstance(r, dict):
                    r = dict(r)
                    for k in ("supplier_id", "supplier_name", "website", "supplier_new"):
                        if r.get(k) is None and meta.get(k) is not None:
                            r[k] = meta[k]
                    add(r, "furniture-il", f"{f.name} #{i + 1}")
            files.append({"file": f.name, "records": len(recs),
                          "date": first_date(str(meta.get("updated") or meta.get("date") or "")) or (git_date(f) if f.is_relative_to(ROOT) else None)
                          or dt.date.fromtimestamp(f.stat().st_mtime).isoformat()})
    # 2. furniture-express models with the designer's verdicts (§1 of the wow review; the cards' status wins)
    if FURN_EXPRESS.exists():
        fx = dir_sups.get("furniture-express") or {}
        for i, r in enumerate(read_json(FURN_EXPRESS)):
            if not isinstance(r, dict) or not r.get("model_name"):
                continue
            v = next((x for x in review["verdicts"] if name_token_re(x["token"]).search(str(r["model_name"]))), None)
            r = dict(r, supplier_id="furniture-express", supplier_name=re.sub(r'\s*בע"מ', "", fx.get("name") or "ריהוט אקספרס"),
                     website=fx.get("website"), supplier_new=False, price_type="consumer",
                     verdict=(v or {}).get("verdict"), reason=(v or {}).get("why"), sourcing_reason=r.get("reason"))
            before = len(models)
            add(r, "furniture-express", f"{FURN_EXPRESS.name} #{i + 1}")
            if len(models) > before:
                m = models[-1]
                m["review_n"] = v["n"] if v else None
                if m["card_status"] == "rejected":
                    m["verdict_class"] = "reject"
                if m["wow_gate"]["applies"] and m["verdict_class"] == "reject":
                    m["wow_gate"].update(passed=False, note="נדחה בביקורת הוואו של המעצב (2026-10-11)")
    # dedupe: the same url from two sources keeps the furniture-il record
    seen, uniq = set(), []
    for m in models:
        k = (m["key"], (m["url"] or m["id"]).lower())
        if k in seen:
            continue
        seen.add(k)
        uniq.append(m)
    models = uniq

    # suppliers: furniture suppliers in the directory, new candidates files, and anyone the leads name
    cand_files, cands = [], []
    if sup_dir.exists():
        for f in sorted(sup_dir.glob("candidates-furniture-*.json")):
            try:
                recs, meta = read_records(f)
            except Exception as e:
                warnings.append(f"{f.name}: {type(e).__name__}: {e}"[:200])
                continue
            cand_files.append({"file": f.name, "records": len(recs)})
            cands += [dict(r, _file=f.name) for r in recs if isinstance(r, dict) and r.get("id")]
    by_sup: dict[str, list] = {}
    for m in models:
        by_sup.setdefault(m["supplier_id"] or m["supplier_name"] or "?", []).append(m)
    sups = {}
    for sid, s in dir_sups.items():
        if s.get("section") == "furniture_il" or (s.get("section") == "general_il" and FURN_WORDS.search(" ".join(s.get("categories") or []))) or sid in by_sup:
            sups[sid] = dict(s, _new=False)
    for c in cands:
        if c["id"] in sups:
            sups[c["id"]].update({k: v for k, v in c.items() if v not in (None, "", []) and k not in ("id",)})
        else:
            sups[c["id"]] = dict(c, _new=True)
    for sid, ms in by_sup.items():
        if sid not in sups:
            m0 = ms[0]
            sups[sid] = {"id": sid, "name": m0["supplier_name"] or sid, "website": m0["website"], "_new": bool(m0["supplier_new"])}
    readme_rows = readme_outreach_rows(OUTREACH_README)
    sup_out = []
    for sid, s in sups.items():
        s["_aliases"] = supplier_aliases(s.get("name") or "", sid)
        ms = by_sup.get(sid, [])
        fit = s.get("nordic_fit")
        c = s.get("contact") if isinstance(s.get("contact"), dict) else {}
        sup_out.append({
            "id": sid, "name": s.get("name") or sid, "website": s.get("website"), "new": bool(s.get("_new")),
            "section": s.get("section"), "type": s.get("type"), "location": s.get("location") or s.get("country"),
            "categories": [x for x in s.get("categories") or [] if isinstance(x, str)],
            "styles": [x for x in (style_key(y) for y in s.get("styles") or [] if isinstance(y, str)) if x],
            "price_level": s.get("price_level"), "fit": fit.get("score") if isinstance(fit, dict) else fit,
            "status": s.get("status"), "why": s.get("why"), "b2b_signals": s.get("b2b_signals"),
            "contact": {k: v for k, v in c.items() if isinstance(v, str)} if c else ({"text": s["contact"]} if isinstance(s.get("contact"), str) else {}),
            "log": [x for x in s.get("outreach_log") or [] if isinstance(x, str)][-4:],
            "coop": coop_state(s, readme_rows, board_log), "file": s.get("_file"),
            "n_models": len(ms), "n_ok": sum(1 for m in ms if m["verdict_class"] in ("ok", "conditional")),
        })
    order_state = {"replied": 0, "sent": 1, "draft": 2, "none": 3}
    sup_out.sort(key=lambda x: (-x["n_models"], order_state.get(x["coop"]["state"], 9), -(x["fit"] if isnum(x["fit"]) else -1), x["name"]))
    log(f"  furniture: {len(slots)} slots · {len(models)} models ({sum(1 for m in models if m['src'] == 'furniture-il')} from {len(files)} furniture-il files,"
        f" {sum(1 for m in models if m['src'] == 'furniture-express')} furniture-express) · {len(sup_out)} suppliers ({len(cands)} from candidates files)"
        f" · unmatched {len(unmatched)}" + ("" if furn_dir.exists() else f" (no {rel(furn_dir) if furn_dir.is_relative_to(ROOT) else furn_dir} yet)"))
    for w in warnings:
        log(f"  ! furniture file {w}")
    return {"slots": slots, "models": models, "suppliers": sup_out, "tiers": review["tiers"], "gate": review["gate"],
            "sources": {"furniture_il": {"dir": rel(furn_dir) if furn_dir.is_relative_to(ROOT) else str(furn_dir), "present": bool(files), "files": files},
                        "express": rel(FURN_EXPRESS) if FURN_EXPRESS.exists() else None, "review": review["file"],
                        "candidates": cand_files, "unmatched": unmatched[:60], "n_unmatched": len(unmatched), "warnings": warnings}}


# --------------------------------------------------------------------------- main

def main() -> int:
    global DIST
    offline = "--offline" in sys.argv
    eco_dir = ROOT / "data" / "economics"
    if "--economics-dir" in sys.argv:  # for testing with sample files outside the repo data
        eco_dir = Path(sys.argv[sys.argv.index("--economics-dir") + 1]).resolve()
    deep_dir = DEEP_DIR
    if "--deep-dir" in sys.argv:  # for testing the comparison screen with a fixture (studio/tests/fixtures/)
        deep_dir = Path(sys.argv[sys.argv.index("--deep-dir") + 1]).resolve()
    furn_dir, sup_dir = FURN_DIR, SUPPLIERS_DIR
    if "--furniture-dir" in sys.argv:  # testing: furniture leads from another folder (studio/tests/fixtures/furniture-il)
        furn_dir = Path(sys.argv[sys.argv.index("--furniture-dir") + 1]).resolve()
    if "--suppliers-dir" in sys.argv:  # testing: candidates-furniture-*.json from another folder
        sup_dir = Path(sys.argv[sys.argv.index("--suppliers-dir") + 1]).resolve()
    if "--dist" in sys.argv:  # build somewhere else (the smoke test builds the fixture into its own folder)
        DIST = Path(sys.argv[sys.argv.index("--dist") + 1]).resolve()
    t0 = time.time()
    log(f"Studio build · repo {ROOT}")
    plan = read_json(ROOT / "docs" / "house-plan.json")
    order, rooms = load_rooms(plan)
    slots = load_slots(order, rooms)
    products = load_products(set(order))
    n_dup = mark_duplicates(products)
    attach_candidates(slots, products)
    slot_by_key = {s["key"]: s for rows in slots.values() for s in rows}
    for p in products:
        p["_sell_qty"] = sell_qty_default(p, slot_by_key)
    n_qty = sum(1 for p in products if p["_sell_qty"]["qty"] > 1)
    n_unsure = sum(1 for p in products if not p["_sell_qty"]["sure"])
    log(f"  rooms {len(order)} · slots {sum(len(v) for v in slots.values())} · products {len(products)} · duplicate cards {n_dup}")
    log(f"  sell quantity: {n_qty} cards sold as a set by default · {n_unsure} not sure (default 1)")

    # fresh dist (studio/dist is generated output)
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "img" / "p").mkdir(parents=True)
    (DIST / "img" / "f").mkdir(parents=True)

    pstats = build_product_images(products, offline)
    log(f"  product images: downloaded {pstats['downloaded']} · from cache {pstats['cached']} · failed {pstats['failed']} · used a later image {pstats['fallback']}")

    frames = collect_frames(plan, order, rooms)
    hits = build_frame_images(frames)
    log(f"  frame images: {len(frames)} ({hits} from cache)")

    economics = load_economics(eco_dir, products)
    if economics["files"]:
        c = economics.get("counts", {})
        log(f"  economics: {', '.join(economics['files'])} · shipping from CJ {c.get('shipping_cj', 0)}, Zendrop {c.get('shipping_zendrop', 0)},"
            f" AliExpress {c.get('shipping_aliexpress', 0)}, card SKU {c.get('shipping_card', 0)}, manual {c.get('shipping_manual', 0)}"
            f" · no route to Israel {c.get('no_route', 0)} · no option within 20 days {c.get('no_fast_shipping', 0)}"
            f" · retail prices {c.get('retail', 0)} ({c.get('initial_prices', 0)} initial) · sell quantities {c.get('sell_qty', 0)}")
    else:
        log(f"  economics: no files in {economics['dir']} (the page shows its defaults)")

    board = parse_board(ROOT / "status" / "board.md")
    decisions = load_decisions(order)
    blockers = load_blockers()
    market = load_market(eco_dir)
    styles = load_styles()
    dec_ids = {d.get("id") for d in decisions.get("items") or [] if isinstance(d, dict)}
    suppliers = load_suppliers(dec_ids)
    if blockers["items"]:
        n_open = sum(1 for b in blockers["items"] if b.get("status") != "done")
        log(f"  blockers: {len(blockers['items'])} items in {blockers['source']} · {n_open} open")
    if market:
        log(f"  market: {len(market['categories'])} categories · {len(market['products'])} products with a verdict")
    if suppliers:
        log(f"  suppliers: {len((suppliers.get('directory') or {}).get('suppliers') or [])} in the directory · {len((suppliers.get('access') or {}).get('options') or [])} access options")
    comparison = build_comparison(slots, products, slot_by_key, order, deep_dir)
    dir_raw = read_json(SUPPLIERS_DIR / "directory.json") if (SUPPLIERS_DIR / "directory.json").exists() else None
    furniture = load_furniture(order, products, dir_raw, board["log"], furn_dir, sup_dir)
    qa = load_reports(["assets/qa/*.md", "qa/reports/*.md"], "qa")
    leads = load_reports(["data/leads/**/*.md"], "lead")

    # room summaries (all computed from the data above)
    cams = {c["id"]: c for c in plan.get("cameras", [])}
    frames_meta = plan.get("frames_1_1", {})
    room_list = []
    for rid in order:
        r = rooms[rid]
        rows = slots[rid]
        imgs = sorted([f for f in frames if f["room"] == rid], key=lambda f: (f["order"], f["name"]))
        room_list.append({
            "id": rid,
            "name_he": r["name_he"],
            "house_rooms": r["house_rooms"],
            "frames": [{"id": fr, "role": (cams.get(fr) or {}).get("role") or (cams.get(fr) or {}).get("status"),
                        "hero": (cams.get(fr) or {}).get("hero"),
                        "kind": (frames_meta.get(fr) or {}).get("kind"),
                        "min": (frames_meta.get(fr) or {}).get("min"),
                        "counted": (frames_meta.get(fr) or {}).get("counted")} for fr in r["frames"]],
            "slots_file": r.get("slots_file"),
            "slots_version": r.get("slots_version"),
            "variants_required": r.get("variants_required"),
            "n_slots": len(rows),
            "n_covered3": sum(1 for s in rows if s["n_candidates"] >= 3),
            "n_selected_slots": sum(1 for s in rows if s["n_selected"] > 0),
            "transit_only": r["transit_only"],
            "images": [{k: f.get(k) for k in ("src", "w", "h", "kind", "label", "caption", "frame", "status")} for f in imgs],
            "slots": rows,
        })

    status_counts: dict[str, int] = {}
    for p in products:
        status_counts[p.get("status") or "unknown"] = status_counts.get(p.get("status") or "unknown", 0) + 1

    out_products = []
    for p in products:
        q = {k: v for k, v in p.items() if not k.startswith("_")}
        q.update({
            "path": p["_path"], "room": p["_room"], "slot_key": p["_slot_key"], "pool": p["_pool"],
            "pid": p["_pid"], "dups": p["_dups"], "shared_in": p["_shared_in"], "in_rooms": p["_in_rooms"],
            "standards": p["_standards"], "img": p["_img"], "links": p["_links"], "lead": p["_lead"],
            "sell_qty_default": p["_sell_qty"],
        })
        # supplier options (studio rules ג, 2026-10-11): the products screen shows how many; the SKU list stays in the card
        opts = q.pop("options", None)
        if isinstance(opts, dict):
            q["options_n"] = len(opts.get("skus") or [])
            q["options_axes"] = [a.get("name_he") for a in opts.get("axes") or [] if isinstance(a, dict)]
        out_products.append(q)

    commit = git("rev-parse", "--short", "HEAD").strip() or None
    dirty = [l for l in git("status", "--porcelain").splitlines() if l and not l[3:].startswith(("studio/", ".gitignore"))]
    data = {
        "build": {
            "commit": commit,
            "branch": git("rev-parse", "--abbrev-ref", "HEAD").strip() or None,
            "dirty": [l[3:] for l in dirty],
            "built_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "product_images": pstats,
        },
        "counts": {
            "products": len(products),
            "by_status": status_counts,
            "duplicates": n_dup,
            "images_failed": pstats["failed"],
            "rooms": len(order),
            "slots": sum(len(v) for v in slots.values()),
            "frames": sum(len(r["frames"]) for r in room_list),
        },
        "rooms": room_list,
        "products": out_products,
        "stages": board["stages"],
        "roadmap": board["roadmap"],
        "log": board["log"],
        "decisions": decisions,
        "blockers": blockers,
        "economics": economics,
        "market": market,
        "styles": styles,
        "suppliers": suppliers,
        "comparison": comparison,
        "furniture": furniture,
        "reports": qa,
        "leads": leads,
    }
    (DIST / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    if not PAGE_SRC.exists():
        log(f"  ! missing page source {rel(PAGE_SRC)}")
        return 1
    shutil.copyfile(PAGE_SRC, DIST / "index.html")

    files = [p for p in DIST.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    log(f"  dist: {len(files)} files · {total / 1024 / 1024:.2f} MB (limits {LIMIT_FILES} files, {LIMIT_BYTES / 1024 / 1024:.0f} MB)")
    log(f"  data.json {(DIST / 'data.json').stat().st_size / 1024:.0f} KB · commit {commit}{' (uncommitted changes)' if dirty else ''}")
    log(f"done in {time.time() - t0:.1f}s")
    if total > LIMIT_BYTES or len(files) > LIMIT_FILES:
        log("  ! dist is over the limit")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
