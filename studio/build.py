#!/usr/bin/env python3
"""Build "the Studio" (internal back-office) into studio/dist/.

Reads the repo's source-of-truth files (read-only) and writes:
  dist/data.json        what the overview and most screens need, computed from the repo
                        (data/, docs/, assets/ and status/: board.md, decisions.json, blockers.json); under 4 MB
  dist/data-<name>.json the heavy parts the page loads when their screen opens (CHUNKS: the comparison's rooms, the
                        sourcing results, furniture, boards, lead reports); data.json "chunks" lists them
  dist/img/s/<room>-<n>-<hash>.webp  the product pictures, packed 36 to a sheet (6 x 6 cells of 320px, q74):
                        one file per card did not fit the artifact's file limit (QA 2026-10-17, B1)
  dist/img/f/<n>.webp   frames and renders, 1280px long side, q78
  dist/index.html       the page (copied from studio/src/index.html)
At the end it prints the published paths (studio/published-files.json) that this build no longer produces: the
publish removes them, so the version stays under 511 files. Duplicate card ids are reported loudly.

The room boards ("לוחות חדרים", data.json "boards") come from scripts/boards/room_boards.py, the single source of their
logic; every card on a board gets its dist/img/p/<id>.webp from the same product-image pipeline and cache.

Product images are downloaded once and cached in studio/.cache/, so a second
build does not hit the network. Frame conversions are cached there too.

Usage: python3 studio/build.py [--offline] [--economics-dir DIR] [--deep-dir DIR] [--dist DIR]
                               [--furniture-dir DIR] [--suppliers-dir DIR]
                               [--compositions-dir DIR] [--sourcing-dir DIR] [--round-results-dir DIR]
  --offline        never download; products without a cached image get a placeholder.
  --economics-dir  read the economics files from another folder (testing).
  --deep-dir       read the deep AliExpress pass from another folder (testing; default data/leads/aliexpress/deep-2026-10).
  --dist           write the build to another folder (testing; default studio/dist).
  --furniture-dir  read the furniture leads from another folder (testing; default data/leads/furniture-il).
  --suppliers-dir  read candidates-furniture-*.json from another folder (testing; default data/suppliers).
  --compositions-dir   read the room compositions from another folder (testing; default data/compositions).
  --sourcing-dir       read round-N-*.json and searched-index.json from another folder (testing; default
                       data/leads/next-sourcing).
  --round-results-dir  read the round's results from another folder (default <sourcing-dir>/round-N-results).

Only the Python standard library and Pillow are used.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.parse
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
# Since card schema 1.1 (2026-10-13, Q2) a card names its room itself (`room`); the folder is the fallback.
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
    # any slots file the plan does not list still gets a room, when it has slots: data/slots/filler-replacements.json
    # (a list of `items`, no room in the plan) showed as a ninth room with 0 frames and 0 slots (QA 2026-10-17, L3)
    for f in sorted((ROOT / "data" / "slots").glob("*.json")):
        rid = f.stem
        if rid in rooms:
            continue
        try:
            sl = read_json(f).get("slots")
        except Exception as e:
            log(f"  ! {rel(f)}: {type(e).__name__}: {e}"[:200])
            sl = None
        if not sl:
            log(f"  slots file without slots, not a room: {rel(f)}")
            continue
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
                # the slot's envelope as data/slots has it now (QA 2026-10-17, L6: the sourcing screen showed only the
                # round-3 envelopes of 12.10), and its alternative form (hall/storage-boxes: one long basket, set_of 1)
                "envelope": envelope_lines(s.get("envelope_cm")) or None,
                "alternative_form": alt_forms(s.get("alternative_form")) or None,
            })
        out[rid] = rows
    return out


def alt_forms(v) -> list[dict]:
    """A slot's alternative_form (one object or a list) as the page and sell_qty_default() read it."""
    out = []
    for a in (v if isinstance(v, list) else [v] if isinstance(v, dict) else []):
        if not isinstance(a, dict):
            continue
        so = a.get("set_of")
        out.append({"id": str(a.get("id") or "") or None, "name_he": a.get("name_he") if isinstance(a.get("name_he"), str) else None,
                    "set_of": int(so) if isnum(so) and float(so).is_integer() and so >= 1 else None,
                    "envelope": envelope_lines(a.get("envelope_cm")) or None,
                    "envelope_cm": a.get("envelope_cm") if isinstance(a.get("envelope_cm"), dict) else None,
                    "note": a.get("note") if isinstance(a.get("note"), str) else None})
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


def card_index(base: Path) -> tuple[dict, dict]:
    """(card id -> path, card id -> [paths] for ids that more than one file claims), for data/products/**.
    A card is found by its own `id`; the file name is only the fallback (a card without an id, or an old reference by
    file name: zendrop-2883892.json holds basket-zendrop-seagrass-belly-foldable-38). The first file wins a duplicate."""
    index, dups, stems = {}, {}, {}
    for p in sorted(base.rglob("*.json")):
        try:
            cid = json.loads(p.read_text(encoding="utf-8")).get("id")
        except Exception:
            cid = None
        cid = cid if isinstance(cid, str) and cid.strip() else p.stem
        if cid in index:
            dups.setdefault(cid, [index[cid]]).append(p)
        else:
            index[cid] = p
        stems.setdefault(p.stem, p)
    for stem, p in stems.items():
        index.setdefault(stem, p)
    return index, dups


def load_products(room_ids=None) -> list[dict]:
    base = ROOT / "data" / "products"
    products = []
    for p in sorted(base.rglob("*.json")):
        try:
            card = read_json(p)
        except Exception as e:  # keep going, report it
            log(f"  ! cannot read {rel(p)}: {e}")
            continue
        if not isinstance(card, dict):
            log(f"  ! {rel(p)}: not a card (a JSON object)")
            continue
        if not (isinstance(card.get("id"), str) and card["id"].strip()):
            card["id"] = p.stem
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
        # Card schema 1.1 (Q2): the card's own `room` decides; the folder above is the fallback for older cards.
        own = card.get("room")
        if isinstance(own, str) and own in (room_ids or set(ROOM_DIRS.values())):
            if room and room != own and not lead:
                log(f"  ! {rel(p)}: room '{own}' but its folder says '{room}' (the card's room is used)")
            room = own
        elif own is not None:
            log(f"  ! {rel(p)}: unknown room {own!r} (the folder's room is used)")
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


def schema_check(products: list[dict]) -> dict:
    """QA 2026-10-17, L1: the cards that do not follow data/product-card.schema.json, by the validator a Studio edit goes
    through (studio/apply_edits.py validate). Read-only: the cards are the sourcing agent's to fix; the Studio shows the
    errors (the overview counts them by kind, the product drawer lists them). Sets p["_schema"]."""
    out = {"schema": "data/product-card.schema.json", "checked": 0, "failing": 0, "by_kind": {}, "error": None}
    try:
        spec = importlib.util.spec_from_file_location("studio_apply_edits", STUDIO / "apply_edits.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        schema = read_json(ROOT / out["schema"])
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"[:200]
        for p in products:
            p["_schema"] = None
        return out
    kinds: dict[str, int] = {}
    for p in products:
        p["_schema"] = None
        try:
            errs = m.validate(read_json(ROOT / p["_path"]), schema)
        except Exception as e:
            errs = [f"$: {type(e).__name__}"]
        out["checked"] += 1
        if not errs:
            continue
        out["failing"] += 1
        p["_schema"] = errs[:6]
        for k in {re.sub(r"\[\d+\]", "[]", x) for x in errs}:
            kinds[k] = kinds.get(k, 0) + 1
    out["by_kind"] = dict(sorted(kinds.items(), key=lambda kv: -kv[1]))
    return out


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
# "2 x $1.48", "(2 x 1.48 + 8.26)", "3 x 9.98 USD", "2 × $20.01 =": the notes price a sale of N units of the card's cost
# (QA 2026-10-17, M5: pair and set cards were sold as one unit). Only a money reading counts, never "15 x 15 x 30 cm".
TIMES_COST = re.compile(r"(?<![\d.,])([2-9])\s*[x×]\s*(\$\s*)?(\d+(?:\.\d+)?)(\s*(?:USD|\+|=))?")


def notes_times_cost(p: dict) -> tuple[int, str] | None:
    """(N, the words) when the card's notes price the sale as N x the card's own cost, else None."""
    cost = (p.get("price") or {}).get("cost")
    if not isnum(cost) or cost <= 0:
        return None
    for m in TIMES_COST.finditer(p.get("notes") or ""):
        if not (m.group(2) or m.group(4)):
            continue
        if abs(float(m.group(3)) - cost) <= 0.011:
            return int(m.group(1)), m.group(0).strip()
    return None


LEAD_FX = 3.3  # the final round priced at the conservative rate of FR-C (2026-10-10)


def lead_qty(p: dict) -> tuple[int, str] | None:
    """(units in the sale, where it says so) from the card's final-round record, when more than one: its qty_in_sale /
    qty, else what its landed cost implies (landed = (units x the card's cost + shipping) x 3.3: the wave-3 repricing
    priced "the pair" or "the set of 3" without a qty field)."""
    lr = p.get("_lead_rec") or {}
    c = lr.get("rec") or {}
    for k in ("qty_in_sale", "qty"):
        q = c.get(k)
        if isnum(q) and float(q).is_integer() and q > 1:
            return int(q), lr.get("file") or ""
    cost = (p.get("price") or {}).get("cost")
    if any(isnum(c.get(k)) for k in ("qty_in_sale", "qty")) or not (isnum(c.get("landed_ils")) and isnum(cost) and cost > 0):
        return None
    if isnum(c.get("ship_usd")):
        ship = c["ship_usd"]
    else:
        cs = card_sku_shipping(p)
        ship = ((cs or {}).get("cheapest") or {}).get("usd") or 0
    q = (c["landed_ils"] / LEAD_FX - ship) / cost
    n = round(q)
    if 2 <= n <= 12 and abs(q - n) <= 0.05 * n:
        return n, f"{lr.get('file') or ''}, לפי עלות הנחיתה ₪{c['landed_ils']:g}"
    return None
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
    own = p.get("sell_qty")
    if isnum(own) and float(own).is_integer() and own >= 1:
        return {"qty": int(own), "sure": True, "set_of": home, "reason": f"הכרטיס קובע {int(own)} יח' למכירה (sell_qty)"}
    # the slot's alternative form (data/slots alternative_form, QA 2026-10-17 L6): hall/storage-boxes is a pair, or one
    # long basket (set_of 1). A card of that form is one sale of its own set, never 2 x a long basket.
    alt = alt_form_of(p, slot_by_key.get(p.get("_slot_key")) or {}) if p.get("_slot_key") else None
    if alt:
        n = alt["set_of"] or 1
        return {"qty": n, "sure": True, "set_of": n, "alt_form": alt["id"],
                "reason": f"הצורה החלופית של העמדה ({alt['name_he'] or alt['id']}): {n} יח' במכירה" + (f", {alt['why']}" if alt.get("why") else "")}
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
    if out["qty"] == 1:
        # the card says the cost is per unit and prices the sale as N units: the round's record, then the notes
        lq, tc = lead_qty(p), notes_times_cost(p)
        if lq:
            out = {"qty": lq[0], "sure": True, "set_of": home or lq[0],
                   "reason": f"הליקוט האחרון מתמחר {lq[0]} יח' במכירה ({lq[1]}), והעלות בכרטיס ליחידה"}
        elif tc:
            out = {"qty": tc[0], "sure": True, "set_of": home or tc[0],
                   "reason": f"ההערות מחשבות את המכירה כ-{tc[0]} × העלות שבכרטיס (\"{tc[1][:40]}\")"}
    if pcs == 1:
        out["sku_pieces"] = 1
        if out["qty"] > 1 and out.get("reason"):
            out["reason"] += f"; המק\"ט שבחדר הוא יחידה אחת ({pcs_label})"
        elif not out["sure"] and out.get("set_of"):
            # the price is per piece; what is open is whether the set is N of this same product (not raised by guess)
            out["reason"] = (f"העמדה דורשת סט של {out['set_of']}, והמק\"ט שבחדר הוא יחידה אחת ({pcs_label}). "
                             f"לא ברור אם הסט הוא {out['set_of']} מאותו מוצר")
    return out


ALT_TOL_CM = 3


def alt_form_of(p: dict, slot: dict) -> dict | None:
    """The slot's alternative form this card is (data/slots alternative_form), or None. A card is that form when its
    name or notes name it (its id, "long basket" for "long-basket", its Hebrew name), or when its width falls in the
    form's own width range (within ALT_TOL_CM): a 60 cm basket in hall/storage-boxes, whose pair is 26-34 cm each."""
    forms = slot.get("alternative_form") or []
    if not forms:
        return None
    text = f"{p.get('name') or ''}\n{p.get('notes') or ''}".lower()
    dims = p.get("dimensions_cm") if isinstance(p.get("dimensions_cm"), dict) else {}
    width = dims.get("width") if isnum(dims.get("width")) else None
    for a in forms:
        words = [w for w in (a.get("id"), (a.get("id") or "").replace("-", " "), a.get("name_he")) if w]
        hit = next((w for w in words if w.lower() in text), None)
        if hit:
            return dict(a, why=f"הכרטיס מציין \"{hit}\"")
        rng = (a.get("envelope_cm") or {}).get("w")
        if width is not None and isinstance(rng, list) and len(rng) == 2 and all(isnum(x) for x in rng) \
                and min(rng) - ALT_TOL_CM <= width <= max(rng) + ALT_TOL_CM:
            return dict(a, why=f"רוחב {width:g} ס\"מ בטווח של הצורה החלופית ({min(rng):g}–{max(rng):g})")
    return None


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


def ascii_url(url: str) -> str:
    """An IRI as a URI urllib can send: Hebrew letters in the path (rihut-express.co.il/.../כסא-צייסר-1200x1200.jpg)
    made every download fail with UnicodeEncodeError (QA 2026-10-17, L7). Existing %XX escapes are kept; a non-ASCII
    host goes through IDNA. The cache key stays the URL as the card writes it."""
    if url.isascii():
        return url
    u = urllib.parse.urlsplit(url)
    host = u.netloc
    if u.hostname and not u.hostname.isascii():
        host = host.replace(u.hostname, u.hostname.encode("idna").decode("ascii"))
    q = lambda s, safe: urllib.parse.quote(s, safe=safe)
    return urllib.parse.urlunsplit((u.scheme, host, q(u.path, "/%:@!$&'()*+,;=~"), q(u.query, "=&%:@!$'()*+,;/?~"),
                                    q(u.fragment, "%:@!$&'()*+,;=/?~")))


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
            req = urllib.request.Request(ascii_url(url), headers={"User-Agent": UA, "Accept": "image/*,*/*;q=0.8"})
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


def build_product_images(products: list[dict], offline: bool) -> dict:
    """Pick each product's picture: the first of its first 3 image URLs that is in the cache or downloads (into
    studio/.cache/p/). Nothing is written to dist here: pack_product_sheets() draws every picture into a sheet."""
    stats = {"downloaded": 0, "cached": 0, "failed": 0, "fallback": 0}

    def work(p):
        urls = (p.get("images") or {}).get("urls") or []
        errors = []
        for i, url in enumerate(urls[:3]):
            if not isinstance(url, str):
                continue
            b, err, cached = fetch_cached(url, offline)
            if b is None:
                errors.append(f"#{i + 1}: {err}")
                continue
            note = None
            if i > 0:
                note = f"התמונה הראשונה לא נטענה ({errors[0]}); מוצגת תמונה {i + 1}."
            return p["id"], {"ok": True, "index": i, "cached": cached, "note": note,
                             "_src": str(CACHE / "p" / (hashlib.sha1(url.encode()).hexdigest()[:20] + ".bin"))}
        why = "; ".join(errors) if errors else "אין כתובות תמונה בכרטיס"
        return p["id"], {"ok": False, "index": None, "cached": False,
                         "note": f"ההורדה נכשלה, מוצג מקום שמור בצבע הדומיננטי. {why}",
                         "_ph": str((p.get("colors") or {}).get("dominant_hex") or "")}

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


# Product pictures are packed into sheets (2026-10-17, QA B1: one file per card hit the artifact's file limit, and the
# house will have thousands of products). A sheet is a grid of square cells, each picture contained in its cell on white
# (every product box in the page is a white square). Sheets are per room, the cards in slot order, so a room's screens
# load a few sheets; the name carries a hash of what is drawn, so a changed sheet is a new file (never a stale cache)
# and an unchanged one keeps its name between builds (the publish sends only new names).
SHEET_CELL, SHEET_COLS, SHEET_ROWS, SHEET_Q = 320, 6, 6, 74
SHEET_PAD = 4  # white margin inside a cell: no bleed from the next cell when the browser scales the sheet


def _cell_image(info: dict) -> tuple[Image.Image | None, str | None]:
    """(the picture fitted to a cell, error) from the cached bytes, or (None, error)."""
    try:
        im = Image.open(info["_src"])
        im.draft("RGB", (SHEET_CELL * 2, SHEET_CELL * 2))
        if im.mode in ("P", "LA", "RGBA", "PA"):
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
            bg.alpha_composite(im)
            im = bg.convert("RGB")
        elif im.mode != "RGB":
            im = im.convert("RGB")
        box = SHEET_CELL - 2 * SHEET_PAD
        im.thumbnail((box, box), Image.LANCZOS)
        return im, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"[:160]


def _cell_placeholder(hex_color: str) -> Image.Image:
    try:
        c = tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    except Exception:
        c = (217, 214, 208)
    n = SHEET_CELL
    img = Image.new("RGB", (n, n), (238, 236, 232))
    d = ImageDraw.Draw(img)
    for x in range(-n, n, 16):  # hatching marks it as "no photo"
        d.line([(x, n), (x + n, 0)], fill=(220, 217, 211), width=2)
    m = n // 6
    d.rectangle([m, m, n - m, n - m], fill=c)
    return img


def sheet_group(p: dict) -> str:
    return "leads" if p.get("_lead") else (p.get("_room") or ("pool" if p.get("_pool") else "other"))


def pack_product_sheets(products: list[dict]) -> dict:
    """Draw every product's picture into dist/img/s/<group>-<n>-<hash>.webp and point p["_img"] at its cell:
    {sheet, cell: [col, row], grid: [cols, rows]}. Sheets are cached in studio/.cache/s/ by what they hold."""
    out_dir = DIST / "img" / "s"
    out_dir.mkdir(parents=True, exist_ok=True)
    cdir = CACHE / "s"
    cdir.mkdir(parents=True, exist_ok=True)
    groups: dict[str, list[dict]] = {}
    for p in products:
        groups.setdefault(sheet_group(p), []).append(p)
    per = SHEET_COLS * SHEET_ROWS
    stats = {"sheets": 0, "cells": 0, "from_cache": 0, "bytes": 0, "decode_failed": 0}
    jobs = []
    for g in sorted(groups):
        rows = sorted(groups[g], key=lambda p: (p.get("_slot_key") or "~", p["id"]))
        for n in range(0, len(rows), per):
            jobs.append((g, n // per, rows[n:n + per]))

    def key_of(cells):
        parts = [f"{SHEET_CELL}|{SHEET_COLS}|{SHEET_PAD}|{SHEET_Q}"]
        for p in cells:
            im = p["_img"]
            parts.append(f"{p['id']}:{Path(im['_src']).name if im.get('_src') else 'ph' + im.get('_ph', '')}")
        return hashlib.sha1("\n".join(parts).encode()).hexdigest()

    def work(job):
        g, i, cells = job
        h = key_of(cells)
        rows_n = (len(cells) + SHEET_COLS - 1) // SHEET_COLS
        cols_n = SHEET_COLS if rows_n > 1 else len(cells)
        name = f"{g}-{i + 1}-{h[:10]}.webp"
        cached, meta = cdir / f"{h}.webp", cdir / f"{h}.json"
        failed = {}
        if cached.exists() and meta.exists():
            try:
                failed = json.loads(meta.read_text(encoding="utf-8")).get("failed") or {}
                shutil.copyfile(cached, out_dir / name)
                return g, i, cells, name, cols_n, rows_n, failed, True
            except Exception:
                failed = {}
        sheet = Image.new("RGB", (cols_n * SHEET_CELL, rows_n * SHEET_CELL), (255, 255, 255))
        for k, p in enumerate(cells):
            x0, y0 = (k % SHEET_COLS) * SHEET_CELL, (k // SHEET_COLS) * SHEET_CELL
            im, err = (_cell_image(p["_img"]) if p["_img"].get("_src") else (None, None))
            if im is None:
                if err:
                    failed[p["id"]] = err
                ph = _cell_placeholder(p["_img"].get("_ph") or (p.get("colors") or {}).get("dominant_hex") or "")
                sheet.paste(ph, (x0, y0))
            else:
                sheet.paste(im, (x0 + (SHEET_CELL - im.width) // 2, y0 + (SHEET_CELL - im.height) // 2))
        tmp = cached.with_suffix(".tmp")
        sheet.save(tmp, "WEBP", quality=SHEET_Q, method=6)
        tmp.replace(cached)
        meta.write_text(json.dumps({"failed": failed, "ids": [p["id"] for p in cells]}), encoding="utf-8")
        shutil.copyfile(cached, out_dir / name)
        return g, i, cells, name, cols_n, rows_n, failed, False

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for g, i, cells, name, cols_n, rows_n, failed, hit in ex.map(work, jobs):
            stats["sheets"] += 1
            stats["cells"] += len(cells)
            stats["from_cache"] += hit
            stats["bytes"] += (out_dir / name).stat().st_size
            for k, p in enumerate(cells):
                im = p["_img"]
                if p["id"] in failed and im.get("ok"):
                    stats["decode_failed"] += 1
                    im.update({"ok": False, "note": f"התמונה לא נפתחה ({failed[p['id']]}), מוצג מקום שמור."})
                im.update({"sheet": f"img/s/{name}", "cell": [k % SHEET_COLS, k // SHEET_COLS], "grid": [cols_n, rows_n]})
    for p in products:
        for k in ("_src", "_ph"):
            p["_img"].pop(k, None)
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
    # "כניסה לבית" / "לכניסה לסל" is admission, not the entrance hall (QA 2026-10-17, L8: VR1 showed "חלל כניסה")
    text = re.sub(r"ל?כניסה\s+ל(?:בית|סל)", " ", text)
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
    bare = [it.get("id") for it in items if isinstance(it.get("answer"), str)]
    if bare:  # the page shows them (it normalizes the shape), but the repo should store {option, note, at, via}
        log(f"  ! status/decisions.json: {len(bare)} answers are a bare string, not {{option, note, at, via}}: {', '.join(map(str, bare[:8]))}")
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


# --------------------------------------------------------------------------- the office (agents)

AGENTS_JSON = ROOT / "status" / "agents.json"
OFFICE_STATES = ("working", "idle", "blocked", "planned")
# board log authors ("who") and words in the text that name each agent; the default is the agent id itself
OFFICE_ALIASES = {
    "user": {"who": ("המשתמש",)},
    "art-director": {"who": ("המנהל",)},
    "sourcing-agent": {"who": ("sourcing",), "text": ("sourcing-agent",)},
    "pricing-living": {"who": ("pricing (סלון)",)},
    "pricing-rest": {"who": ("pricing (שאר",)},
    "profit-fix": {"who": ("profit-fix",), "text": ("profit-fix",)},
    "explorer": {"who": ("explorer", "general-purpose")},
    "aliexpress-scale": {"who": ("aliexpress",), "text": ("aliexpress-scale",)},
    "cj-daily": {"who": ("שגרה יומית CJ", "שגרה CJ", "cj-daily"), "text": ("שגרת CJ", "cj-daily")},
    "supplier-replies": {"who": ("supplier-replies",), "text": ("supplier-replies",)},
}
# lines of the instructions that state a limit: "לא ...", "אסור", "אף פעם", "רק ..." (and the English equivalents)
LIMIT_RX = re.compile(r"(?:^|[\s(\"'״„*])(?:לא|אסור|אף\s+פעם|רק)(?=[\s:,.])|\b(?:never|do not|don't|must not|only)\b", re.I)
# never publish anything that looks like a secret, even if a file ever contained one
SECRET_RX = [re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{8,}"), re.compile(r"\b[0-9a-fA-F]{24,}\b"),
             re.compile(r"[\w.+-]+@api\b", re.I), re.compile(r"API@CJ\w*"), re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
             re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-./+]{12,}")]


def redact(text: str) -> tuple[str, int]:
    n = 0
    for rx in SECRET_RX:
        text, k = rx.subn("[הוסתר]", text)
        n += k
    return text, n


def parse_instructions(path: Path) -> dict:
    """An agent file (.claude/agents/<id>.md: --- name, description, tools, model, skills --- body) or CLAUDE.md (no
    frontmatter). tools None = the file names none (the agent inherits the session's tools)."""
    raw = path.read_text(encoding="utf-8")
    fm, body = {}, raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end > 0:
            for line in raw[3:end].splitlines():
                m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
                if m:
                    fm[m.group(1).lower()] = m.group(2).strip()
            body = raw[end + 4:].lstrip("\n")
    body, n_red = redact(body)
    for k in list(fm):
        fm[k], k_red = redact(fm[k])
        n_red += k_red
    split = lambda v: [x.strip() for x in re.split(r"[,\s]+", v or "") if x.strip()] or None
    limits, seen, in_code = [], set(), False
    for line in body.splitlines():
        t = line.strip()
        if t.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not t or t.startswith(("#", "|")):
            continue
        t = re.sub(r"^(?:>\s*|[-*+]\s+|\d+[.)]\s+)+", "", t)
        t = re.sub(r"\*\*|`", "", t).strip()
        for sent in re.split(r"(?<=[.!?])\s+(?=\S)", t):
            sent = sent.strip()
            if len(sent) < 6 or not LIMIT_RX.search(sent):
                continue
            key = sent[:80]
            if key in seen:
                continue
            seen.add(key)
            limits.append(sent if len(sent) <= 260 else sent[:257].rstrip() + "…")
    return {"src": rel(path), "name": fm.get("name"), "description": fm.get("description"), "tools": split(fm.get("tools")),
            "model": fm.get("model"), "skills": split(fm.get("skills")), "body": body, "limits": limits[:16],
            "n_limits": len(limits), "redacted": n_red, "lines": body.count("\n") + 1}


def office_mentions(aid: str, logs: list[dict]) -> list[dict]:
    """Board log lines that name the agent: as the author (who) or in the text."""
    al = OFFICE_ALIASES.get(aid, {})
    who = al.get("who", (aid,))
    words = al.get("text", (aid,) if re.search(r"[a-z]-[a-z]", aid) else ())
    out = []
    for e in logs:
        w = e.get("who") or ""
        if any(w.startswith(x) for x in who) or any(x in (e.get("text") or "") for x in words):
            out.append(e)
    return out


def load_office(logs: list[dict]) -> dict | None:
    """status/agents.json + every agent's instructions + its lines in the board log -> data.json "office"."""
    if not AGENTS_JSON.exists():
        return None
    d = read_json(AGENTS_JSON)
    states = d.get("states") or {}
    wings = [w for w in d.get("wings") or [] if isinstance(w, dict) and w.get("id")]
    wing_ids = {w["id"] for w in wings}
    agents, warn, n_red = [], [], 0
    for a in d.get("agents") or []:
        if not isinstance(a, dict) or not a.get("id"):
            continue
        q = {k: v for k, v in a.items() if k != "instructions_src"}
        if q.get("state") not in OFFICE_STATES:
            warn.append(f"{a['id']}: state {q.get('state')!r} -> idle")
            q["state"] = "planned" if q.get("kind") == "planned" else "idle"
        if q.get("wing") not in wing_ids:
            warn.append(f"{a['id']}: wing {q.get('wing')!r} not in wings")
        q["limits_he"] = [x for x in (a.get("limits_he") or []) if isinstance(x, str)]
        src = a.get("instructions_src")
        q["instructions"] = None
        if src:
            sp = (ROOT / src).resolve()
            if sp.is_relative_to(ROOT) and sp.exists():
                q["instructions"] = parse_instructions(sp)
                n_red += q["instructions"]["redacted"]
            else:
                warn.append(f"{a['id']}: instructions {src} not found")
        hits = office_mentions(a["id"], logs)
        last = sorted(hits, key=lambda e: e.get("date") or "")[-5:][::-1]
        q["board"] = {"count": len(hits), "last": [{"date": e.get("date"), "who": e.get("who"), "text": redact(e.get("text") or "")[0][:400]} for e in last]}
        agents.append(q)
    ids = {a["id"] for a in agents}
    flows = []
    for f in d.get("flows") or []:
        if isinstance(f, dict) and f.get("from") in ids and f.get("to") in ids:
            flows.append({"from": f["from"], "to": f["to"], "label_he": f.get("label_he") or ""})
        else:
            warn.append(f"flow {f!r}: unknown agent")
    return {"file": rel(AGENTS_JSON), "updated": d.get("updated"), "note": d.get("note"), "states": states, "wings": wings,
            "agents": agents, "flows": flows, "warnings": warn, "redacted": n_red}


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


_BOARDS_MODULES: dict = {}


def boards_module():
    """scripts/boards/room_boards.py (BOARDS_SRC) as a module, loaded once per path."""
    key = str(BOARDS_SRC)
    if key not in _BOARDS_MODULES:
        spec = importlib.util.spec_from_file_location("room_boards", BOARDS_SRC)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _BOARDS_MODULES[key] = m
    return _BOARDS_MODULES[key]


_FINAL_CTX: dict = {}


def final_round_context():
    """room_boards.Context(cat={}) once per build: the final round's records, the designer's audits and the pricing file,
    read the way the boards read them. None (said loudly) when it cannot be built."""
    if "ctx" not in _FINAL_CTX:
        try:
            _FINAL_CTX["ctx"] = boards_module().Context(cat={})
        except Exception as e:
            log(f"  ! final-round records: {rel(BOARDS_SRC)}: {type(e).__name__}: {e}")
            _FINAL_CTX["ctx"] = None
    return _FINAL_CTX["ctx"]


def lead_records() -> dict:
    """card id -> {rec, file, date}: the card's final-round record with a plain price (the repriced one first, then the
    newest), the same records the boards read their margin from (room_boards.Context.records_any)."""
    ctx = final_round_context()
    if ctx is None:
        return {}
    out = {}
    for cid, recs in ctx.records_any.items():
        for _flag, date, fname, c in recs:
            if isnum(c.get("price_ils")) and c["price_ils"] > 0:
                out[cid] = {"rec": c, "file": fname, "date": date}
                break
    return out


def _fits(v) -> dict:
    """{style: score} with numeric scores only (0 stays: "does not count for this style")."""
    out = {}
    for k, x in (v.items() if isinstance(v, dict) else []):
        if k in STYLE_ORDER and isnum(x) and not isinstance(x, bool):
            out[k] = round(float(x), 2) if not float(x).is_integer() else int(x)
    return out


def audit_files(entries) -> dict:
    """id(entry) -> the audit file it came from (relative to the final-round folder). audits() keeps the entries only;
    the same files are read again, in its order, and matched by content."""
    try:
        d = ROOT / boards_module().coverage_module().D
    except Exception:
        d = ROOT / "data" / "leads" / "final-2026-10-13"
    by_text = {}
    for f in sorted(d.glob("round*/designer-audit*.json")):
        try:
            for c in read_json(f).get("cards") or []:
                by_text[json.dumps(c, sort_keys=True, ensure_ascii=False)] = str(f.relative_to(d))
        except Exception:
            continue
    return {id(e): by_text.get(json.dumps(e, sort_keys=True, ensure_ascii=False)) for e in entries}


def attach_fit_sources(products: list[dict]) -> dict:
    """QA 2026-10-17, M6: what the products and compare screens know about a card's fit, per slot.
      _audit  {slot key or "*": the designer's entry}: the master-designer's audits (round*/designer-audit*.json), read
              through room_boards.load_audits() -> scripts/sourcing/final_round_coverage.py audits(), the single source
              of that logic (an entry with "slots" applies only there, "*" everywhere, later files override earlier
              ones); the page picks an entry the way audit_for() does: the slot's own entry, then "*".
              verdict "reject" = rejected for that slot (the card stays in the basket); "lower-fit" = a lower score.
      _guess  {slot key: the team's style_fit_guess}: the final round's records for that slot, newest first per style.
    The designer's fit replaces the team's guess wherever the designer scored a style."""
    ctx = final_round_context()
    stats = {"audit_entries": 0, "cards_audited": 0, "rejected": 0, "lowered": 0, "kept": 0, "cards_guess": 0, "error": None}
    for p in products:
        p["_audit"], p["_guess"] = {}, {}
    if ctx is None:
        stats["error"] = "no final-round context"
        return stats
    stats["error"] = getattr(ctx, "audit_error", None)
    by_id = {p["id"]: p for p in products}
    audit = getattr(ctx, "audit", None) or {}
    files = audit_files(list(audit.values()))
    for (cid, slot), a in audit.items():
        p = by_id.get(cid)
        if p is None or not isinstance(a, dict):
            continue
        v = str(a.get("verdict") or "") or None
        p["_audit"][slot] = {k: x for k, x in {
            "v": v, "fit": _fits(a.get("fit")), "vf": _fits(a.get("variants_fit")),
            "note": a.get("note_he") if isinstance(a.get("note_he"), str) else None,
            "flags": [str(x) for x in a.get("flags") or [] if isinstance(x, (str, int, float))][:8],
            "seen": a.get("image_seen") if isinstance(a.get("image_seen"), bool) else None,
            "env_ok": a.get("envelope_ok") if isinstance(a.get("envelope_ok"), bool) else None,
            "team": a.get("team") if isinstance(a.get("team"), str) else None,
            "file": files.get(id(a)),
        }.items() if x not in (None, {}, [])}
        stats["audit_entries"] += 1
        stats["rejected"] += v == "reject"
        stats["lowered"] += v == "lower-fit"
        stats["kept"] += v == "keep"
    for (slot, cid), recs in (getattr(ctx, "records", None) or {}).items():
        p = by_id.get(cid)
        if p is None:
            continue
        fit, src = {}, None
        for _flag, date, fname, c in sorted(recs, key=lambda r: (r[1], r[2]), reverse=True):
            g = _fits(c.get("style_fit_guess"))
            for k, x in g.items():
                if k not in fit:
                    fit[k] = x
                    src = src or {"file": fname, "date": date or None}
        if fit:
            p["_guess"][slot] = dict(src or {}, fit=fit)
    stats["cards_audited"] = sum(1 for p in products if p["_audit"])
    stats["cards_guess"] = sum(1 for p in products if p["_guess"])
    return stats


# premium pricing (ה.10, 2026-10-17): the designer judged the product premium, so the price may go up to the typical
# Israeli price; the owner approves it ("תמחור פרימיום, לאישור")
PREMIUM_RX = re.compile(r"premium\s+pricing\s*\(\s*(?:ה|h)\.\s*10|תמחור\s+פרימיום", re.I)


def card_economics(p: dict) -> dict:
    """A card without a row in data/economics/products.json (QA 2026-10-17, M4: the round-5 cards showed "חסר מחיר"):
    its starting price from the card itself (price.retail_ils, price.suggested_retail), else from its final-round record
    (price_ils at the Israeli value, the record the boards show), with the record's comparisons, its verdict against the
    40% floor (ה.11) and whether it is priced as premium (ה.10). Marked "initial-...": a starting price, not approved."""
    out = {}
    pr = p.get("price") or {}
    lr = p.get("_lead_rec") or {}
    rec = lr.get("rec") or {}
    for k, src in (("retail_ils", "initial-card"), ("suggested_retail", "initial-card")):
        if isnum(pr.get(k)) and pr[k] > 0 and str(pr.get("currency") or "USD").upper() in ("USD", "ILS"):
            out.update({"retail_ils": pr[k], "retail_src": src})
            break
    if "retail_ils" not in out and isnum(rec.get("price_ils")) and rec["price_ils"] > 0:
        out.update({"retail_ils": rec["price_ils"], "retail_src": f"initial-leads ({lr.get('file')})"})
    if not out:
        return {}
    if isinstance(rec.get("price_basis_he"), str) and rec["price_basis_he"].strip():
        out["price_note"] = rec["price_basis_he"].strip()[:400]
    comps = []
    for c in rec.get("comps") or []:
        url = c if isinstance(c, str) else (c.get("url") if isinstance(c, dict) else None)
        if isinstance(url, str) and url.startswith("https://"):
            comps.append({"retailer": re.sub(r"^www\.", "", urllib.parse.urlparse(url).hostname or ""), "title": "",
                          "price": c.get("price") if isinstance(c, dict) and isnum(c.get("price")) else None, "url": url})
    if comps:
        iv = _clean_il_value({"comps": comps, "note": "ההשוואות מהליקוט האחרון (" + str(lr.get("file") or "") + ")"})
        if iv:
            out["il_value"] = iv
    m = rec.get("margin_pct")
    if isnum(m) and out["retail_ils"] == rec.get("price_ils"):
        out["lead_margin_pct"] = m
        out["price_flag"] = "loss" if m < 0 else "below-floor" if m < 40 else "ok"
        if isnum(rec.get("landed_ils")):
            out["lead_landed_ils"] = rec["landed_ils"]
    # a sale that is not N units of the card's cost (a mixed stack of plates, a pitcher with its jar): the record's cost
    # of the whole sale, so the margin is the record's and not "6 x the big plate"
    cost, rc, q = pr.get("cost"), rec.get("cost_usd"), (p.get("_sell_qty") or {}).get("qty") or 1
    if isnum(rc) and rc > 0 and isnum(cost) and cost > 0 and out["retail_ils"] == rec.get("price_ils"):
        per_unit = abs(rc - cost) <= max(0.011, 0.03 * cost)
        whole = abs(rc - cost * q) <= max(0.02, 0.03 * rc)
        if not per_unit and not whole:
            out["sale_cost_usd"] = rc
    out["from_card"] = True
    return out


def lead_freight(p: dict) -> dict | None:
    """Shipping to Israel from the card's final-round record (ship_usd for the units of the sale), as a freight entry;
    only when no freight file and no room SKU has it."""
    lr = p.get("_lead_rec") or {}
    c = lr.get("rec") or {}
    if not isnum(c.get("ship_usd")) or c["ship_usd"] < 0:
        return None
    d = days_pair(c.get("ship_days"))
    # the record's shipping is for the sale it priced: its qty, else the units the Studio sells (the same sale)
    q = next((int(c[k]) for k in ("qty_in_sale", "qty") if isnum(c.get(k)) and float(c[k]).is_integer() and c[k] >= 1),
             (p.get("_sell_qty") or {}).get("qty") or 1)
    opt = {"usd": float(c["ship_usd"]), "name": "מהליקוט", "days": f"{d[0]}-{d[1]}" if d else None}
    return {"options": [opt], "cheapest": opt, "cheapest_under_20d": opt if d and d[1] <= 20 else None, "status": "ok",
            "qty": q, "checked_at": lr.get("date"), "note": f"משלוח מהרשומה בליקוט האחרון ({lr.get('file')}), ל-{q} יח'"}


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
        # the pricing team edits this file while the Studio builds (2026-10-18): a read that does not parse is tried
        # again, then the committed version is used (room_boards.load_json_stable, the boards read the same version)
        try:
            d, note = boards_module().load_json_stable(str(pp))
        except Exception as e:
            d, note = None, f"{rel(pp) if pp.is_relative_to(ROOT) else pp.name}: {type(e).__name__}: {e}"[:200]
        if note:
            log(f"  ! pricing: {note}")
        manual = d.get("products", d) if isinstance(d, dict) else {}
        if not isinstance(manual, dict):
            manual = {}
        if d is not None:
            out["files"].append(pp.name)
        pricing_meta = {"file": rel(pp) if pp.is_relative_to(ROOT) else pp.name,
                        "updated": first_date(str(d.get("updated") or "")) if isinstance(d, dict) else None,
                        "note": note, "rows": len(manual)}
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
    n_fr = {"cj": 0, "zendrop": 0, "aliexpress": 0, "card": 0, "leads": 0}
    n_from_card = 0
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
        if fe is None and pid not in manual:
            lf = lead_freight(p)
            if lf:
                src, fe, fdate = "leads", lf, lf.get("checked_at")
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
        if pid not in manual:
            ce = card_economics(p)
            if ce:
                e.update(ce)
                n_from_card += 1
        if m.get("premium") is True or PREMIUM_RX.search(p.get("notes") or "") or PREMIUM_RX.search(str(e.get("price_note") or "")):
            e["premium"] = True
        out["products"][pid] = e
    out["counts"] = {"shipping_cj": n_fr["cj"], "shipping_zendrop": n_fr["zendrop"], "shipping_aliexpress": n_fr["aliexpress"],
                     "shipping_card": n_fr["card"], "shipping_leads": n_fr["leads"], "from_card": n_from_card,
                     "shipping_manual": n_manual, "no_fast_shipping": n_no_fast,
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

# --------------------------------------------------------------------------- room boards (לוחות חדרים)

BOARDS_SRC = ROOT / "scripts" / "boards" / "room_boards.py"
BOARD_TEXT_KEYS = {"why", "name_he", "he", "legend_he", "style_he", "room_he", "error", "file"}
SLUG_RX = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,160}$")


def load_slot_ids() -> dict:
    """room -> the slots of data/slots/<room>.json (only ids are needed), for checking the ids on the boards."""
    out = {}
    for f in sorted((ROOT / "data" / "slots").glob("*.json")):
        try:
            out[f.stem] = [s for s in read_json(f).get("slots") or [] if isinstance(s, dict) and isinstance(s.get("id"), str)]
        except Exception:
            continue
    return out


def load_boards(products: list[dict], offline: bool) -> dict:
    """The room boards (2026-10-17): one board per style and room, exactly as scripts/boards/room_boards.py computes them
    (that module is the single source of the logic; its CLI renders the same data as images). Every card on a board must
    have its picture: the product-image pipeline gives every card one (a cell in a sheet, pack_product_sheets()), and any
    card that is still without one goes through the same pipeline here. Nothing secret may reach data.json: the boards
    pass the same redact() check as the office."""
    try:
        data = boards_module().boards()
    except Exception as e:  # the rest of the Studio is still built; the screen says why it is empty
        log(f"  ! boards: {rel(BOARDS_SRC)} failed: {type(e).__name__}: {e}")
        return {"present": False, "error": f"{type(e).__name__}: {e}"[:300], "src": rel(BOARDS_SRC), "boards": []}
    if (data.get("audit") or {}).get("error"):
        log(f"  ! boards: the designer audits did not load: {data['audit']['error']}")
    by_id = {p["id"]: p for p in products}
    ids = sorted({pk["card_id"] for b in data["boards"] for s in b["slots"] for pk in s.get("picks") or []})
    todo = [by_id[i] for i in ids if i in by_id and not by_id[i].get("_img")]
    if todo:
        build_product_images(todo, offline)
    not_cards = [i for i in ids if i not in by_id]
    placeholders = [i for i in ids if i in by_id and not (by_id[i].get("_img") or {}).get("ok")]
    with_file = [i for i in ids if i in by_id and by_id[i].get("_img")]
    # secrets: the free text (labels, the reasons quoted from a card's notes) goes through redact(); ids are not free
    # text (a card file's id, a slot of data/slots/): they must be known slugs. redact() is not run on the ids, because
    # its "sk-..." pattern also matches inside "desk-organizer" and would break the links.
    n_red = 0

    def scrub(o):
        nonlocal n_red
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and k in BOARD_TEXT_KEYS:
                    o[k], n = redact(v)
                    n_red += n
                elif isinstance(v, (dict, list)):
                    scrub(v)
        elif isinstance(o, list):
            for v in o:
                scrub(v)
    scrub(data)
    slot_ids = {s["id"] for rows in load_slot_ids().values() for s in rows}
    bad_ids = sorted({x for b in data["boards"] for s in b["slots"] for x in [s["id"]] + [pk["card_id"] for pk in s.get("picks") or []]
                      if not SLUG_RX.match(x) or (x not in by_id and x not in slot_ids)})
    if bad_ids:
        log(f"  ! boards: ids that are neither a card nor a slot, or not a plain slug: {', '.join(bad_ids[:6])}")
    if n_red:
        log(f"  ! boards: {n_red} secret-looking strings redacted in the free text")
    data.update({"present": True, "src": rel(BOARDS_SRC), "redacted": n_red, "bad_ids": bad_ids,
                 "images": {"cards": len(ids), "with_file": len(with_file), "placeholders": placeholders, "not_cards": not_cards,
                            "built_now": [p["id"] for p in todo]}})
    return data


# --------------------------------------------------------------------------- compositions and the next sourcing round

# The designer's room compositions (master-designer, 2026-10-11): data/compositions/<room>-<style>-<date>.json, one per
# room and style, with a human-readable twin in docs/rooms/. Every designer run wrote a slightly different shape (slots as
# a dict or a list, counts or status_counts, default as a card, an AliExpress record, a set or a furniture model, per-room
# sub-slots in the kids rooms...), so everything here is read defensively: an odd field is skipped, never fatal.
COMPOSITIONS_DIR = ROOT / "data" / "compositions"
ROOMS_DOC_DIR = ROOT / "docs" / "rooms"
NEXT_SOURCING_DIR = ROOT / "data" / "leads" / "next-sourcing"
SCALE_DIR = ROOT / "data" / "leads" / "aliexpress" / "scale-2026-10"
AE_SOURCES = ROOT / "data" / "sources" / "aliexpress"
COMP_STATUSES = ("ready-to-lock", "partial", "empty", "on-hold")
COMP_STATUS_ALIASES = {"ready-to-lock": "ready-to-lock", "ready": "ready-to-lock", "ready-for-lock": "ready-to-lock",
                       "lockable": "ready-to-lock", "partial": "partial", "empty": "empty", "on-hold": "on-hold",
                       "hold": "on-hold", "onhold": "on-hold", "blocked": "on-hold", "waiting": "on-hold"}
SUBROOM_HE = {"boy": "חדר הילד", "girl": "חדר הילדה", "both_rooms": "שני החדרים"}
WHOLE_SUB_HE = {"without_conditional_lights": "בלי המנורות המותנות", "without_conditional_sconce": "בלי מנורת הקיר המותנית",
                "boy": "חדר הילד", "girl": "חדר הילדה", "both_rooms": "שני החדרים"}
# text fields of a whole-look block, in the order the page shows them
WHOLE_TEXT_HE = {"basis_he": "בסיס", "scope_he": "היקף", "note_he": "הערה", "notes_he": "הערות", "missing_he": "מה חסר",
                 "clean_today_he": "נקי היום", "addon_only_he": "רק כתוספת לסל", "bundles_he": "חבילות", "bundle_hint_he": "חבילה",
                 "furniture_he": "ריהוט", "repeats_across_rooms_he": "חוזר בין חדרים", "full_look_estimate_note_he": "המראה המלא",
                 "items_he": "פריטים"}
# extra designer fields of a slot, shown under "more" in the page
SLOT_MORE_HE = (("conditions_he", "תנאים"), ("lock_conditions_he", "תנאי נעילה"), ("lock_decision", "החלטת נעילה"),
                ("structure_issue", "בעיית מבנה"), ("out_he", "לא נכנסו"), ("rejected_he", "נפסלו"),
                ("kept_aside", "נשארו בצד"), ("leads", "לידים"), ("rejected_records", "רשומות AliExpress שנפסלו"),
                ("fillers", "מילוי"), ("reassigned_he", "הועבר מעמדה אחרת"), ("family", "משפחה"))
REF_NOTE_KEYS = ("note_he", "desc_he", "condition_he", "conditional_he", "conditions_he", "incomplete_he", "price_note_he",
                 "margin_note_he", "score_note", "landed_note")
REF_OPTION_KEYS = ("option_he", "sku_he", "by_room_option_he", "sku_note")
TOKEN_RX = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)(?![A-Za-z0-9])")
AE_ID_RX = re.compile(r"(?<!\d)(\d{11,17})(?!\d)")
RESULT_LIST_KEYS = ("records", "results", "items", "candidates", "found", "rows", "products")
TIER_HE = {"tier1": "שכבה 1 · עדיפות גבוהה", "tier2": "שכבה 2 · בינונית", "tier3": "שכבה 3 · נמוכה",
           "spare": "רזרבה (רק אם העמדה לא מלאה)", "deferred": "נדחה: עמדות בהמתנה להחלטה"}
TIER_ORDER = ("tier1", "tier2", "tier3", "spare", "deferred")


def as_text_list(v) -> list[str]:
    """A designer field (string, list of strings, list of dicts) as a list of short display lines."""
    out = []
    if v is None or v is False:
        return out
    if isinstance(v, (str, int, float)):
        t = str(v).strip()
        return [t] if t else []
    if isinstance(v, dict):
        parts = []
        for k in ("card_id", "ae_item_id", "item_id", "id", "slot", "model"):
            if v.get(k):
                parts.append(("AE " if k in ("ae_item_id", "item_id") else "") + str(v[k]))
                break
        if isnum(v.get("score")):
            parts.append(f"ציון {v['score']}")
        if isnum(v.get("price_ils")) or isnum(v.get("price_ils_from")):
            parts.append(f"₪{v.get('price_ils') if isnum(v.get('price_ils')) else 'מ-' + str(v['price_ils_from'])}")
        for k in ("why_he", "note_he", "he", "note", "reason", "why", "text"):
            if isinstance(v.get(k), str) and v[k].strip():
                parts.append(v[k].strip())
                break
        return [" · ".join(parts)] if parts else []
    if isinstance(v, list):
        for x in v:
            out.extend(as_text_list(x))
    return out


def comp_status(v) -> str | None:
    if not isinstance(v, str) or not v.strip():
        return None
    k = re.sub(r"[\s_]+", "-", v.strip().lower())
    return COMP_STATUS_ALIASES.get(k, k)


def decision_ids(texts, dec_ids: set) -> list[str]:
    found = []
    for t in texts:
        for m in TOKEN_RX.finditer(str(t or "")):
            tok = m.group(1)
            for c in [tok] + (tok.split("-") if "-" in tok else []):
                if c in dec_ids and c not in found:
                    found.append(c)
    return found


def first_num(d: dict, *keys):
    for k in keys:
        x = to_num(d.get(k)) if not isinstance(d.get(k), bool) else None
        if x is not None:
            return x
    return None


class CompCtx:
    """What the composition and sourcing readers share: cards by id, cards by AliExpress item, AliExpress records."""

    def __init__(self, products: list[dict], dec_ids: set, room_ids: list[str], slot_by_key: dict):
        self.by_id = {p["id"]: p for p in products}
        self.dec_ids = dec_ids
        self.room_ids = room_ids
        self.slot_by_key = slot_by_key
        self.aliases = {}
        if SEEN.exists():
            try:
                self.aliases = read_json(SEEN).get("aliases") or {}
            except Exception as e:
                log(f"  ! cannot read {rel(SEEN)}: {e}")
        self.ae_cards: dict[str, list[dict]] = {}
        for p in products:
            m = AE_ITEM.search(((p.get("supplier") or {}).get("product_url") or ""))
            if m:
                self.ae_cards.setdefault(ae_canon(m.group(1), self.aliases), []).append(p)
        self.ae: dict[str, dict] = {}  # item -> {title, url, img_url, img}
        self.wanted: set[str] = set()

    def card_id(self, cid) -> str | None:
        if not isinstance(cid, str) or not cid.strip():
            return None
        c = cid.strip()
        if c in self.by_id:
            return c
        m = re.match(r"[\w.-]+", c)  # "ceiling-lights-...-30 ×2", "vase-... (Medium)"
        return m.group(0) if m and m.group(0) in self.by_id else None

    def card_for_ae(self, item: str, slot_key: str | None) -> str | None:
        cs = self.ae_cards.get(item) or []
        live = [p for p in cs if p.get("status") != "rejected"] or cs
        same = [p for p in live if p.get("_slot_key") == slot_key]
        p = (same or live or [None])[0]
        return p["id"] if p else None

    def want_ae(self, item: str) -> None:
        if item:
            self.wanted.add(item)


def norm_ref(x, ctx: CompCtx, slot_key: str | None, role: str | None = None) -> dict | None:
    """One product in a composition (default, variation, set item, whole-look item) in one shape for the page."""
    if not isinstance(x, dict):
        if isinstance(x, str) and x.strip():
            x = {"ae_item_id": x} if AE_ID_RX.fullmatch(re.sub(r"^ae:", "", x.strip())) else {"card_id": x}
        else:
            return None
    r: dict = {}
    raw_id = x.get("card_id") or (x.get("id") if isinstance(x.get("id"), str) and not str(x.get("id")).startswith("ae:") else None)
    ae_raw = x.get("ae_item_id") or x.get("item_id") or (str(x["id"])[3:] if isinstance(x.get("id"), str) and str(x["id"]).startswith("ae:") else None)
    if isinstance(x.get("items"), list) and x["items"]:
        r["k"] = "set"
        r["items"] = [i for i in (norm_ref(it, ctx, slot_key, it.get("role") if isinstance(it, dict) else None) for it in x["items"]) if i]
        if x.get("set_id"):
            r["set_id"] = str(x["set_id"])
    elif raw_id:
        cid = ctx.card_id(raw_id)
        r["k"] = "card" if cid else "missing"
        r["id"] = cid or str(raw_id).strip()
    elif ae_raw:
        item = ae_canon(ae_raw, ctx.aliases)
        if not item:
            return None
        r["ae"] = item
        cid = ctx.card_for_ae(item, slot_key)
        if cid:  # a card was written for this AliExpress item since the composition: show the card
            r["k"], r["id"] = "card", cid
        else:
            r["k"], r["id"] = "ae", "ae:" + item
        ctx.want_ae(item)
    elif x.get("model") or x.get("candidate_he"):
        r["k"] = "model"
        r["title"] = str(x.get("model") or x.get("candidate_he")).strip()
    else:
        return None
    if role or x.get("role"):
        r["role"] = str(role or x.get("role"))
    score = to_num(x.get("score")) if not isinstance(x.get("score"), bool) else None
    if score is not None:
        r["score"] = score
    sn = str(x.get("score_note") or "")
    if x.get("provisional") is True or sn.lower().startswith("provisional"):
        r["provisional"] = True
    for k in ("price_ils", "landed_ils", "margin_pct", "contribution_ils"):
        v = to_num(x.get(k)) if not isinstance(x.get(k), (bool, list, dict)) else None
        if v is not None:
            r[k] = v
    if r.get("margin_pct") is None and isinstance(x.get("margin_range_pct"), list):
        ns = [to_num(n) for n in x["margin_range_pct"] if to_num(n) is not None]
        if ns:
            r["margin_range"] = [min(ns), max(ns)]
    if isnum(x.get("price_ils_from")):
        r["price_ils"], r["price_from"] = float(x["price_ils_from"]), True
    basis = x.get("price_basis") or x.get("price_src")
    if isinstance(basis, str) and basis.strip():
        r["price_basis"] = basis.strip()
    if x.get("price_proposed") is True or "proposed" in str(basis or "").lower() or "suggested" in str(basis or "").lower():
        r["proposed"] = True
    q = x.get("price_for_qty") or x.get("price_for")
    if q:
        r["price_for"] = str(q)
    for flag in ("addon_only", "borderline", "temporary", "needs_card", "estimated", "margin_estimated"):
        if x.get(flag) is True:
            r[flag] = True
    if x.get("conditional") is True or x.get("conditional_he") or x.get("conditions_he") or x.get("condition_he"):
        r["conditional"] = True
    if isinstance(x.get("flag"), str) and x["flag"].strip():
        r["flag"] = x["flag"].strip()
    opts = [str(x[k]).strip() for k in REF_OPTION_KEYS if isinstance(x.get(k), str) and x[k].strip()]
    if x.get("dims_cm"):
        opts.append(f"{x['dims_cm']} ס\"מ" if isinstance(x["dims_cm"], str) else json.dumps(x["dims_cm"], ensure_ascii=False))
    if opts:
        r["option"] = " · ".join(opts)
    notes = []
    for k in REF_NOTE_KEYS:
        notes += as_text_list(x.get(k))
    if isinstance(x.get("alt_price"), dict):
        a = x["alt_price"]
        if isnum(a.get("price_ils")) and isnum(a.get("margin_pct")):
            notes.append(f"ב-₪{a['price_ils']:g}: מרווח {a['margin_pct']:g}%")
    if isnum(x.get("margin_at_current_price")):
        notes.append(f"במחיר הנוכחי: מרווח {x['margin_at_current_price']:g}%")
    if notes:
        r["note"] = "\n".join(dict.fromkeys(notes))
    if isinstance(x.get("ship_days"), (str, int)) and str(x["ship_days"]).strip():
        r["ship_days"] = str(x["ship_days"]).strip()
    if r["k"] == "model" and isinstance(x.get("note"), str):
        r["note"] = (r.get("note", "") + "\n" + x["note"]).strip()
    return r


def norm_slot_block(s: dict, ctx: CompCtx, key: str | None) -> dict:
    """The parts a slot and a per-room sub-slot (kids: boy / girl) share."""
    o: dict = {}
    st = comp_status(s.get("status"))
    if st:
        o["status"] = st
    d = norm_ref(s.get("default"), ctx, key, "default") if s.get("default") else None
    if d:
        o["default"] = d
    vars_ = [v for v in (norm_ref(v, ctx, key) for v in (s.get("variations") or []) if v) if v]
    if vars_:
        o["variations"] = vars_
    if not d and s.get("candidate_he"):
        o["candidate_he"] = str(s["candidate_he"])
    shown = {r.get("ae") for r in ([d] if d else []) + vars_ if r} | {r.get("id") for r in ([d] if d else []) + vars_ if r}
    nc = []
    for n in s.get("needs_card") or []:
        if isinstance(n, bool):
            continue
        item = ae_canon(n.get("item_id") or n.get("ae_item_id") if isinstance(n, dict) else n, ctx.aliases)
        if item and item not in shown:
            ref = norm_ref({"ae_item_id": item}, ctx, key, "needs_card")
            if ref:
                nc.append(ref)
    if nc:
        o["needs_card"] = nc
    blocked_raw = as_text_list(s.get("blocked_by"))
    if blocked_raw:
        o["blocked"] = [{"text": t, "ids": decision_ids([t], ctx.dec_ids)} for t in blocked_raw]
    notes = as_text_list(s.get("notes_he"))
    if notes:
        o["notes"] = "\n".join(notes)
    more = []
    for k, label in SLOT_MORE_HE:
        lines = as_text_list(s.get(k))
        if lines:
            more.append({"label": label, "items": lines, "ids": decision_ids(lines, ctx.dec_ids) if k in ("lock_decision", "lock_conditions_he", "conditions_he") else []})
    if more:
        o["more"] = more
    return o


def norm_whole(w) -> dict | None:
    if not isinstance(w, dict):
        return None

    def totals(b: dict) -> dict:
        t = {}
        for out_k, keys in (("price", ("total_price_ils",)), ("contribution", ("total_contribution_ils",)),
                            ("net", ("total_net_ils",)), ("landed", ("total_landed_ils",)),
                            ("margin", ("weighted_margin_pct", "blended_margin_pct", "margin_pct")),
                            ("after_cac", ("contribution_after_one_cac_ils", "contribution_after_cac_ils"))):
            v = first_num(b, *keys)
            if v is not None:
                t[out_k] = v
        if "margin" not in t and t.get("price") and t.get("contribution") is not None:
            net = t.get("net") or t["price"] / 1.18
            t["margin"] = round(t["contribution"] / net * 100, 1) if net else None
            t["margin_computed"] = True
        rng = b.get("weighted_margin_range_pct")
        if isinstance(rng, list) and all(isnum(n) for n in rng) and rng:
            t["margin_range"] = [min(rng), max(rng)]
        return t

    o = {"main": totals(w), "subs": [], "texts": [], "lists": []}
    for k, v in w.items():
        if isinstance(v, dict) and any(x in v for x in ("total_price_ils", "items", "items_he")):
            sub = totals(v)
            n_items = len(v["items"]) if isinstance(v.get("items"), list) else None
            if sub or n_items:
                o["subs"].append({"key": k, "label": WHOLE_SUB_HE.get(k, k.replace("_", " ")), **sub, **({"items": n_items} if n_items else {})})
            if isinstance(v.get("items_he"), str):
                o["texts"].append({"label": WHOLE_SUB_HE.get(k, k), "text": v["items_he"]})
    if not o["main"] and o["subs"]:  # kids: no house total, the two rooms together are the total
        both = next((s for s in o["subs"] if s["key"] == "both_rooms"), None)
        if both:
            o["main"] = {k: both[k] for k in ("price", "contribution", "margin", "after_cac", "net") if k in both}
            o["main_from"] = both["label"]
    items = w.get("items") if isinstance(w.get("items"), list) else w.get("defaults") if isinstance(w.get("defaults"), list) else None
    if items is not None:
        o["n_items"] = len(items)
    if isnum(w.get("of_slots")):
        o["of_slots"] = w["of_slots"]
    if isnum(w.get("slots_with_default")):
        o["n_items"] = w["slots_with_default"]
    for k, label in WHOLE_TEXT_HE.items():
        if isinstance(w.get(k), str) and w[k].strip():
            o["texts"].append({"label": label, "text": w[k].strip()})
    if isnum(w.get("full_look_estimate_ils")):
        o["full_look"] = w["full_look_estimate_ils"]
    if isnum(w.get("missing_slots_at_slot_price_ils")):
        o["missing_at_slot_price"] = w["missing_slots_at_slot_price_ils"]
    for k, label in (("addon_only", "רק כתוספת לסל"), ("excluded", "לא בסכום"), ("furniture_pending_ls1", "ריהוט שמחכה לאישור ספק (LS1)")):
        lines = as_text_list(w.get(k))
        if lines:
            o["lists"].append({"label": label, "items": lines})
    return o


def comp_paragraphs(v) -> list[str]:
    """room_check_he as paragraphs: a list stays a list; a long string splits before its numbered points '(1)', '(2)'."""
    out = []
    for t in as_text_list(v):
        parts = re.split(r"\s+(?=\(\d{1,2}\)\s)", t)
        out.extend(p.strip() for p in parts if p.strip())
    return out


def load_compositions(comp_dir: Path, ctx: CompCtx) -> dict:
    out = {"dir": rel(comp_dir) if comp_dir.is_relative_to(ROOT) else str(comp_dir), "present": False, "rooms": {},
           "files": [], "warnings": []}
    if not comp_dir.exists():
        return out
    best: dict[tuple, tuple] = {}
    for f in sorted(comp_dir.glob("*.json")):
        try:
            d = read_json(f)
        except Exception as e:
            out["warnings"].append(f"{f.name}: {type(e).__name__}: {e}"[:200])
            continue
        if not isinstance(d, dict):
            out["warnings"].append(f"{f.name}: not an object")
            continue
        room = room_key(d.get("room") or "", set(ctx.room_ids))
        if not room:  # from the file name: <room>-<style>-<date>.json
            m = re.match(r"(.+?)-([a-z-]+?)-(\d{4}-\d{2}-\d{2})$", f.stem)
            room = room_key(m.group(1), set(ctx.room_ids)) if m else None
        if not room:
            out["warnings"].append(f"{f.name}: unknown room {d.get('room')!r}")
            continue
        style = style_key(d.get("style")) or style_key((re.match(r".+?-([a-z-]+?)-\d{4}", f.stem) or [None, ""])[1]) or "nordic"
        date = first_date(str(d.get("date") or "")) or first_date(f.stem) or ""
        k = (room, style)
        if k not in best or (date, f.name) > (best[k][0], best[k][1].name):
            best[k] = (date, f, d)
    for (room, style), (date, f, d) in sorted(best.items()):
        try:
            out["rooms"].setdefault(room, {})[style] = norm_composition(d, f, room, style, date, ctx)
            out["files"].append(rel(f) if f.is_relative_to(ROOT) else f.name)
        except Exception as e:  # one bad file never stops the build
            out["warnings"].append(f"{f.name}: {type(e).__name__}: {e}"[:200])
    out["present"] = bool(out["rooms"])
    return out


def norm_composition(d: dict, f: Path, room: str, style: str, date: str, ctx: CompCtx) -> dict:
    raw = d.get("slots")
    if isinstance(raw, dict):
        pairs = [(k, v) for k, v in raw.items() if isinstance(v, dict)]
    elif isinstance(raw, list):
        pairs = [(str(v.get("slot") or v.get("id") or ""), v) for v in raw if isinstance(v, dict)]
    else:
        pairs = []
    file_slots = {s["id"]: s for k, s in ctx.slot_by_key.items() if k.startswith(room + "/")}
    order = {sid: i for i, sid in enumerate(file_slots)}
    slots = []
    for sid, s in pairs:
        sid = sid.split("/")[-1].strip()
        if not sid:
            continue
        key = f"{room}/{sid}"
        o = {"id": sid, "key": key}
        meta = file_slots.get(sid)
        if meta:
            o["name_he"] = meta.get("name_he")
        else:
            o["unknown_slot"] = True
        o.update(norm_slot_block(s, ctx, key))
        if s.get("priority"):
            o["priority"] = str(s["priority"])
        miss = first_num(s, "missing", "missing_variations")
        if miss is not None:
            o["missing"] = int(miss)
        if isinstance(s.get("frames"), list):
            o["frames"] = [str(x) for x in s["frames"]]
        if isinstance(s.get("kind"), str):
            o["kind"] = s["kind"]
        if isnum(s.get("proposed_price_ils")):
            o["proposed_price_ils"] = s["proposed_price_ils"]
        if isinstance(s.get("rooms"), list):
            o["rooms"] = [str(x) for x in s["rooms"]]
        if isinstance(s.get("by_room"), dict):
            subs = []
            for rk, rv in s["by_room"].items():
                if isinstance(rv, dict):
                    subs.append({"room": rk, "label": SUBROOM_HE.get(rk, rk), **norm_slot_block(rv, ctx, key)})
            if subs:
                o["by_room"] = subs
                if "status" not in o:
                    sts = [x.get("status") for x in subs if x.get("status")]
                    o["status"] = next((x for x in ("partial", "ready-to-lock", "empty", "on-hold") if x in sts), sts[0] if sts else None)
        if o.get("status") is None:
            o["status"] = "partial" if o.get("default") else "empty"
        lock = next((m for m in o.get("more") or [] if m["label"] == "החלטת נעילה"), None)
        if lock and lock["ids"]:
            o["lock_ids"] = lock["ids"]
        slots.append(o)
    slots.sort(key=lambda o: (order.get(o["id"], 999), o["id"]))
    counts = {k: 0 for k in COMP_STATUSES}
    for o in slots:
        counts[o["status"]] = counts.get(o["status"], 0) + 1
    fc = d.get("counts") if isinstance(d.get("counts"), dict) else d.get("status_counts") if isinstance(d.get("status_counts"), dict) else None
    file_counts = {comp_status(k): v for k, v in fc.items() if isnum(v)} if fc else None
    if file_counts and all(file_counts.get(k, 0) == counts.get(k, 0) for k in set(file_counts) | set(counts)):
        file_counts = None  # the file's own summary agrees with its slots
    doc = d.get("doc") if isinstance(d.get("doc"), str) else None
    if not doc:
        guess = ROOMS_DOC_DIR / (f.stem + ".md")
        doc = rel(guess) if guess.exists() else None
    decisions = []
    for x in d.get("decisions_needed") or []:
        if isinstance(x, dict):
            text = str(x.get("he") or x.get("why_he") or x.get("text") or "").strip()
            did = str(x.get("id") or "").strip()
            decisions.append({"id": did, "known": did in ctx.dec_ids, "existing": x.get("existing"), "text": text,
                              "ids": decision_ids([text], ctx.dec_ids)})
        elif isinstance(x, str):
            decisions.append({"id": "", "known": False, "text": x, "ids": decision_ids([x], ctx.dec_ids)})
    note = d.get("status_note_he") or d.get("kind")
    return {
        "file": rel(f) if f.is_relative_to(ROOT) else f.name, "doc": doc, "room": room, "style": style, "date": date or None,
        "author": d.get("author"), "frame": d.get("frame"), "note": note if isinstance(note, str) else None,
        "counts": counts, "file_counts": file_counts,
        "whole": norm_whole(d.get("whole_look")), "check": comp_paragraphs(d.get("room_check_he")),
        "decisions": decisions, "swaps": as_text_list(d.get("swaps_he")),
        "fixed_he": d.get("fixed_furniture_he") if isinstance(d.get("fixed_furniture_he"), str) else None,
        "safety_he": d.get("safety_gate_he") if isinstance(d.get("safety_gate_he"), str) else None,
        "slots": slots,
    }


def ae_record_index(items: set[str], ctx: CompCtx, extra_dirs: list[Path]) -> None:
    """Title, link and image URL for every AliExpress item a composition or the sourcing round shows without a card:
    first the deep pass records, then the scale run, then the cached API answer in data/sources/aliexpress/<id>.json."""
    need = {i for i in items if i not in ctx.ae or not ctx.ae[i].get("img_url")}
    for d in [DEEP_DIR, SCALE_DIR] + extra_dirs:
        if not need or not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                recs, _ = read_records(f)
            except Exception:
                continue
            for r in recs:
                if not isinstance(r, dict):
                    continue
                item = ae_canon(r.get("item_id") or (AE_ITEM.search(str(r.get("url") or "")) or [None, None])[1], ctx.aliases)
                if item not in need:
                    continue
                info = ctx.ae.setdefault(item, {})
                img = r.get("image") or r.get("image_url") or r.get("main_image")
                if isinstance(img, str) and img.startswith("https://") and not info.get("img_url"):
                    info["img_url"] = img
                if r.get("title") and not info.get("title"):
                    info["title"] = str(r["title"]).strip()
                if info.get("img_url") and info.get("title"):
                    need.discard(item)
    for item in list(need):
        f = AE_SOURCES / f"{item}.json"
        if not f.exists():
            continue
        try:
            p = ((read_json(f).get("sections") or {}).get("product") or {}).get("payload") or {}
            res = p.get("result") or {}
            info = ctx.ae.setdefault(item, {})
            urls = str((res.get("ae_multimedia_info_dto") or {}).get("image_urls") or "").split(";")
            if urls and urls[0].startswith("https://") and not info.get("img_url"):
                info["img_url"] = urls[0]
            subj = (res.get("ae_item_base_info_dto") or {}).get("subject")
            if subj and not info.get("title"):
                info["title"] = str(subj).strip()
        except Exception:
            continue
    for item in items:
        info = ctx.ae.setdefault(item, {})
        info.setdefault("url", f"https://www.aliexpress.com/item/{item}.html")
        info.setdefault("title", f"AliExpress {item}")


def build_thumb_images(targets: list[tuple[str, str]], offline: bool, budget: int) -> dict:
    """Small images of things that are not cards yet (AliExpress items, sourcing results) into dist/img/a/<hash>.webp.
    targets: [(key, https url)], in priority order. Returns {key: src}; beyond the file budget the page uses the URL."""
    out, seen = {}, set()
    todo = []
    for key, url in targets:
        if key in seen or not isinstance(url, str) or not url.startswith("https://"):
            continue
        seen.add(key)
        todo.append((key, url))
    todo = todo[:max(0, budget)]

    def work(kv):
        key, url = kv
        b, err, _ = fetch_cached(url, offline)
        if b is None:
            return key, None
        name = hashlib.sha1(url.encode()).hexdigest()[:16]
        dst = DIST / "img" / "a" / f"{name}.webp"
        try:
            if not dst.exists():
                to_webp(Image.open(io.BytesIO(b)), P_SIZE, P_Q, dst)
            return key, f"img/a/{name}.webp"
        except Exception:
            return key, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for key, src in ex.map(work, todo):
            if src:
                out[key] = src
    return out


def latest_round(src_dir: Path) -> tuple[Path | None, int | None]:
    best = None
    for f in src_dir.glob("round-*.json"):
        m = re.match(r"round-(\d+)-(\d{4}-\d{2}-\d{2})$", f.stem)
        if m:
            k = (int(m.group(1)), m.group(2))
            if best is None or k > best[0]:
                best = (k, f)
    return (best[1], best[0][0]) if best else (None, None)


def norm_result(r: dict, ctx: CompCtx, key: str, source: str | None = None) -> dict:
    """One product the round found: an AliExpress record, a CJ product or a card written from it."""
    o: dict = {}
    url = r.get("url") or r.get("product_url")
    m_ae = AE_ITEM.search(str(url or ""))
    raw_item = r.get("item_id") or r.get("ae_item_id") or (m_ae.group(1) if m_ae else None)
    if not raw_item and str(source or r.get("source") or "").lower() == "aliexpress":
        raw_item = r.get("product_id")
    item = ae_canon(raw_item, ctx.aliases) if raw_item else None
    cid = ctx.card_id(r.get("card_id")) or ctx.card_id(r.get("id")) or (ctx.card_for_ae(item, key) if item else None)
    if item:
        o["item"] = item
    if cid:
        o["card"] = cid
    elif isinstance(r.get("card_id") or r.get("id"), str) and re.match(r"^[a-z0-9]+(?:-[a-z0-9.]+){2,}$", str(r.get("card_id") or r.get("id"))):
        o["card_pending"] = str(r.get("card_id") or r.get("id"))  # a card id the round wrote that this build does not see (yet)
    o["url"] = url if isinstance(url, str) and url.startswith("https://") else (f"https://www.aliexpress.com/item/{item}.html" if item else None)
    img = r.get("image") or r.get("image_url") or r.get("main_image") or ((r.get("images") or [None])[0] if isinstance(r.get("images"), list) else None)
    if isinstance(img, str) and img.startswith("https://"):
        o["img_url"] = img
    title = r.get("title") or r.get("name") or (f"AliExpress {item}" if item else None) or o.get("card_pending") or r.get("option")
    o["title"] = str(title or "").strip() or "—"
    if isinstance(r.get("option"), str) and r["option"].strip() and r["option"].strip() != o["title"]:
        o["option"] = r["option"].strip()
    for out_k, keys in (("price_usd", ("price_usd", "sku_price_usd", "cost_usd", "price")), ("ship_usd", ("ship_usd", "shipping_usd")),
                        ("landed_ils", ("landed_ils",)), ("retail_ils", ("retail_ils", "price_ils", "slot_price_ils")),
                        ("margin_ils", ("margin_ils", "contribution_ils")), ("fit", ("fit", "score", "nordic_fit", "design_score"))):
        v = first_num(r, *keys)
        if v is not None:
            o[out_k] = v
    fr = r.get("freight") if isinstance(r.get("freight"), dict) else {}
    if "ship_usd" not in o and to_num(fr.get("usd")) is not None:
        o["ship_usd"] = to_num(fr.get("usd"))
    m = frac(r.get("margin_pct") if r.get("margin_pct") is not None else r.get("margin"))
    if m is not None:
        o["margin"] = m
    o["ship_days"] = days_pair(r.get("ship_days") or fr.get("days"))
    if isinstance(r.get("passes_40"), bool):
        o["passes_40"] = r["passes_40"]
    for k in ("verdict", "status", "query", "sku"):
        if isinstance(r.get(k), str) and r[k].strip():
            o[k] = r[k].strip()
    src = source or r.get("source")
    if isinstance(src, str) and src.strip():
        o["source"] = src.strip().lower()
    reason = r.get("reason") or r.get("why_he") or r.get("why") or r.get("note_he") or r.get("note")
    lines = ([reason.strip()] if isinstance(reason, str) and reason.strip() else []) + as_text_list(r.get("flags"))
    if lines:
        o["reason"] = " · ".join(lines)[:500]
    return {k: v for k, v in o.items() if v is not None}


REPORT_KEYS = ("summary", "found", "opened", "next", "not_opened_notable", "cards")


def norm_report(v: dict, meta: dict, fname: str) -> dict:
    """A slot's report from a round file ({slots: {"room/slot": {found, summary, next, queries, opened, not_opened_notable, cards}}})."""
    o: dict = {"file": fname}
    src = v.get("source") or meta.get("source")
    if isinstance(src, str) and src.strip():
        o["source"] = src.strip().lower()
    if isinstance(v.get("found"), bool):
        o["found"] = v["found"]
    for k in ("summary", "next"):
        if isinstance(v.get(k), str) and v[k].strip():
            o[k] = v[k].strip()
    if isinstance(v.get("queries"), list):
        o["n_queries"] = len(v["queries"])
    opened = [x for x in v.get("opened") or [] if isinstance(x, dict)]
    if opened:
        counts: dict[str, int] = {}
        for x in opened:
            s = str(x.get("status") or "other")
            counts[s] = counts.get(s, 0) + 1
        o["opened"] = counts
        o["opened_rows"] = [{"status": str(x.get("status") or ""), "reason": str(x.get("reason") or x.get("why") or "")[:300]}
                            for x in opened if x.get("status") != "card"][:12]
    notable = []
    for x in v.get("not_opened_notable") or []:
        if isinstance(x, dict):
            notable.append(" · ".join(str(x[k]).strip() for k in ("name", "why") if x.get(k)))
        elif isinstance(x, str) and x.strip():
            notable.append(x.strip())
    if notable:
        o["notable"] = notable
    cards = [str(c) for c in v.get("cards") or [] if isinstance(c, str)]
    if cards:
        o["cards"] = cards
    return o


def load_round_results(res_dir: Path, ctx: CompCtx) -> dict:
    """data/leads/next-sourcing/round-N-results/*.json: what the round found, per slot. Accepted shapes: the sourcing
    round's report per source ({source, queries_run, budget, slots: {"room/slot": {found, summary, next, opened,
    not_opened_notable, cards}}, cards: [{id, slot, option, landed_ils, margin_pct, passes_40, flags...}]}, the first real
    file, cj.json), and the shapes of the other sourcing files: a list of records, {records|results|items: [...]},
    {slots: {"room/slot": [...]}} or one file per slot (room--slot.json). Every record needs a slot it can be tied to."""
    out = {"dir": rel(res_dir) if res_dir.is_relative_to(ROOT) else str(res_dir), "present": False, "files": [],
           "by_slot": {}, "reports": {}, "unmatched": [], "warnings": [], "n": 0}
    if not res_dir.exists():
        return out
    room_ids = set(ctx.room_ids)

    def key_of(*cands):
        for c in cands:
            if isinstance(c, (list, tuple)) and len(c) == 2:
                room, slot = c
                rk = room_key(str(room or ""), room_ids)
                if rk and slot and f"{rk}/{slot}" in ctx.slot_by_key:
                    return f"{rk}/{slot}"
            elif isinstance(c, str) and c:
                parts = re.split(r"/|--|__", c.strip(), maxsplit=1)
                if len(parts) == 2:
                    rk = room_key(parts[0], room_ids)
                    if rk and f"{rk}/{parts[1]}" in ctx.slot_by_key:
                        return f"{rk}/{parts[1]}"
        return None

    for f in sorted(res_dir.glob("*.json")):
        try:
            d = read_json(f)
        except Exception as e:
            out["warnings"].append(f"{f.name}: {type(e).__name__}: {e}"[:200])
            continue
        meta = d if isinstance(d, dict) else {}
        source = meta.get("source") if isinstance(meta.get("source"), str) else None
        groups, reports = [], []
        if isinstance(d, list):
            groups.append((None, d))
        elif isinstance(d, dict):
            sl = d.get("slots") if isinstance(d.get("slots"), (dict, list)) else d.get("by_slot")
            if isinstance(sl, dict):
                for k, v in sl.items():
                    if isinstance(v, list):
                        groups.append((k, v))
                    elif isinstance(v, dict):
                        recs = next((v[x] for x in RESULT_LIST_KEYS if isinstance(v.get(x), list) and all(isinstance(y, dict) for y in v[x])), None)
                        if recs is not None:
                            groups.append((k, recs))
                        if any(x in v for x in REPORT_KEYS):
                            reports.append((k, v))
            elif isinstance(sl, list):
                for v in sl:
                    if isinstance(v, dict):
                        recs = next((v[x] for x in RESULT_LIST_KEYS if isinstance(v.get(x), list)), None)
                        if recs is not None:
                            groups.append((v.get("slot") or v.get("key"), recs))
                        if any(x in v for x in REPORT_KEYS):
                            reports.append((v.get("slot") or v.get("key"), v))
            recs = next((d[k] for k in RESULT_LIST_KEYS + ("cards",) if isinstance(d.get(k), list) and all(isinstance(y, dict) for y in d[k])), None)
            if recs is not None:
                groups.append((None, recs))
        n_ok = n_all = 0
        for hint, recs in groups:
            for i, r in enumerate(recs):
                if not isinstance(r, dict):
                    continue
                n_all += 1
                slot_v = r.get("slot") or r.get("slot_key")
                key = key_of(slot_v if isinstance(slot_v, str) and "/" in slot_v else None,
                             (r.get("room") or meta.get("room"), slot_v) if isinstance(slot_v, str) and "/" not in slot_v else None,
                             hint if isinstance(hint, str) else None, (meta.get("room"), hint) if isinstance(hint, str) else None,
                             meta.get("slot") if isinstance(meta.get("slot"), str) else None,
                             (meta.get("room"), meta.get("slot")), f.stem)
                keys = [key] if key else []
                if not keys and isinstance(r.get("slots"), list):
                    keys = [k for k in (key_of(x) for x in r["slots"]) if k]
                if not keys:
                    out["unmatched"].append({"where": f"{f.name} #{i + 1}", "title": str(r.get("title") or r.get("name") or r.get("item_id") or r.get("id") or "")[:120],
                                             "slot": str(slot_v or hint or "")[:60]})
                    continue
                for k in keys:
                    out["by_slot"].setdefault(k, []).append(norm_result(r, ctx, k, source))
                n_ok += 1
        n_rep = 0
        for hint, v in reports:
            key = key_of(hint if isinstance(hint, str) else None, (meta.get("room"), hint) if isinstance(hint, str) else None)
            if not key:
                out["unmatched"].append({"where": f"{f.name} · slots", "title": "דוח עמדה", "slot": str(hint or "")[:60]})
                continue
            out["reports"].setdefault(key, []).append(norm_report(v, meta, f.name))
            n_rep += 1
        st = f.stat()
        info = {"file": f.name, "records": n_all, "ok": n_ok, "reports": n_rep,
                "date": first_date(str(meta.get("updated") or meta.get("date") or "")) or dt.date.fromtimestamp(st.st_mtime).isoformat()}
        if source:
            info["source"] = source.lower()
        for k in ("by", "run_id"):
            if isinstance(meta.get(k), str):
                info[k] = meta[k]
        if isinstance(meta.get("queries_run"), list):
            info["queries_run"] = len(meta["queries_run"])
        if isinstance(meta.get("queries_not_run"), list):
            info["queries_not_run"] = len(meta["queries_not_run"])
        bud = meta.get("budget") if isinstance(meta.get("budget"), dict) else {}
        if isnum(bud.get("cj_points_used")):
            info["points"] = bud["cj_points_used"]
        md = f.with_suffix(".md")
        if md.exists():
            info["md"] = rel(md) if md.is_relative_to(ROOT) else md.name
        out["files"].append(info)
    vrank = {"best": 0, "pick": 0, "alternative": 1, "candidate": 1, "maybe": 2, "reject": 4, "rejected": 4}
    for k, rows in out["by_slot"].items():
        rows.sort(key=lambda x: (0 if x.get("card") or x.get("card_pending") else 1, vrank.get(str(x.get("verdict", "")).lower(), 3),
                                 -(x.get("fit") or 0), -(x.get("margin") or 0), x.get("title", "")))
    out["n"] = sum(len(v) for v in out["by_slot"].values())
    out["n_slots"] = len(set(out["by_slot"]) | set(out["reports"]))
    out["present"] = bool(out["files"] or out["warnings"])  # a folder of unreadable files still shows, with its warnings
    return out


def load_searched_index(path: Path) -> dict | None:
    """data/leads/next-sourcing/searched-index.json, as counts only (the full lists hold 1,579 queries)."""
    if not path.exists():
        return None
    try:
        d = read_json(path)
    except Exception as e:
        return {"file": rel(path) if path.is_relative_to(ROOT) else path.name, "error": f"{type(e).__name__}: {e}"[:200]}
    reg = d.get("registry") if isinstance(d.get("registry"), dict) else {}
    by_slot = d.get("aliexpress_queries_by_slot") if isinstance(d.get("aliexpress_queries_by_slot"), dict) else {}
    cj = d.get("cj_queries")
    pend = d.get("pending_aliexpress_queries")
    return {
        "file": rel(path) if path.is_relative_to(ROOT) else path.name, "updated": d.get("updated"), "note": d.get("note"),
        "registry_file": reg.get("file"), "registry_items": reg.get("items") if isnum(reg.get("items")) else None,
        "registry_by": {k: v for k, v in (reg.get("by_source_status") or {}).items() if isnum(v)},
        "ae_queries": sum(len(v) for v in by_slot.values() if isinstance(v, list)), "ae_slots": len(by_slot),
        "ae_by_slot": {k: len(v) for k, v in by_slot.items() if isinstance(v, list)},
        "cj_queries": len(cj) if isinstance(cj, (list, dict)) else None,
        "pending_ae_queries": len(pend) if isinstance(pend, list) else None,
        "pending_freight_checks": d.get("pending_aliexpress_freight_checks") if isinstance(d.get("pending_aliexpress_freight_checks"), str) else None,
    }


def envelope_lines(env) -> list[str]:
    out = []
    if isinstance(env, dict):
        for k, v in env.items():
            if isinstance(v, list) and v and all(isnum(x) for x in v):
                out.append(f"{k} {min(v):g}–{max(v):g}" if len(v) > 1 and min(v) != max(v) else f"{k} {v[0]:g}")
            elif isnum(v):
                out.append(f"{k} {v:g}")
            elif isinstance(v, str) and v.strip():
                out.append(f"{k}: {v.strip()}")
            elif isinstance(v, dict):
                out.extend(f"{k}.{x}" for x in envelope_lines(v))
    elif isinstance(env, str) and env.strip():
        out.append(env.strip())
    return out


def load_next_sourcing(src_dir: Path, res_dir: Path | None, ctx: CompCtx, comps: dict) -> dict:
    out = {"dir": rel(src_dir) if src_dir.is_relative_to(ROOT) else str(src_dir), "present": False, "warnings": []}
    out["searched"] = load_searched_index(src_dir / "searched-index.json")
    f, rnd = latest_round(src_dir) if src_dir.exists() else (None, None)
    if not f:
        out["results"] = load_round_results(res_dir or src_dir / "round-results", ctx)
        return out
    try:
        d = read_json(f)
    except Exception as e:
        out["warnings"].append(f"{f.name}: {type(e).__name__}: {e}"[:200])
        return out
    if not isinstance(d, dict):
        out["warnings"].append(f"{f.name}: not an object")
        return out
    md = f.with_suffix(".md")
    out.update({"present": True, "file": rel(f) if f.is_relative_to(ROOT) else f.name,
                "md": (rel(md) if md.is_relative_to(ROOT) else md.name) if md.exists() else None,
                "round": d.get("round") if isnum(d.get("round")) else rnd, "date": d.get("date") or first_date(f.stem),
                "rules": as_text_list(d.get("rules_he")),
                "freight_checks_pending": d.get("freight_checks_pending") if isinstance(d.get("freight_checks_pending"), str) else None})
    # tiers: counts and sources from search_plan (the plan block is the fallback for the counts)
    plan = d.get("plan") if isinstance(d.get("plan"), dict) else {}
    sp = d.get("search_plan") if isinstance(d.get("search_plan"), dict) else {}
    q_tier: dict[tuple, tuple] = {}
    tiers = []
    for t in list(TIER_ORDER) + [k for k in list(sp) + list(plan) if k not in TIER_ORDER]:
        if t not in sp and t not in plan:
            continue
        if any(x["id"] == t for x in tiers):
            continue
        rows = sp.get(t) if isinstance(sp.get(t), list) else []
        by_src: dict[str, int] = {}
        for q in rows:
            if not isinstance(q, dict):
                continue
            src = str(q.get("source") or "other").lower()
            by_src[src] = by_src.get(src, 0) + 1
            for sk in q.get("slots") or []:
                q_tier[(str(sk), str(q.get("query") or ""))] = (t, src, len(q.get("slots") or []))
        n = len(rows) if rows else (plan.get(t) if isnum(plan.get(t)) else 0)
        tiers.append({"id": t, "label": TIER_HE.get(t, t), "n": n, "by_source": by_src})
    out["tiers"] = tiers
    srch = d.get("searches") if isinstance(d.get("searches"), dict) else {}
    by_source = {k: len(v) for k, v in srch.items() if isinstance(v, list)}
    if not by_source:
        for t in tiers:
            for k, v in t["by_source"].items():
                by_source[k] = by_source.get(k, 0) + v
    out["by_source"] = by_source
    out["n_queries"] = sum(by_source.values()) or sum(t["n"] for t in tiers)
    # slots
    comp_slot = {}
    for room, styles in (comps.get("rooms") or {}).items():
        c = styles.get("nordic") or next(iter(styles.values()), None)
        for s in (c or {}).get("slots") or []:
            comp_slot[s["key"]] = s
    by_slot_n = ((out["searched"] or {}).get("ae_by_slot") or {})
    slots = []
    for s in d.get("slots") or []:
        if not isinstance(s, dict):
            continue
        key = str(s.get("slot") or s.get("key") or "")
        if "/" not in key and s.get("room"):
            key = f"{s['room']}/{key}"
        room, _, sid = key.partition("/")
        rk = room_key(room, set(ctx.room_ids)) or room
        key = f"{rk}/{sid}"
        meta = ctx.slot_by_key.get(key) or {}
        pc = s.get("price_ceiling") if isinstance(s.get("price_ceiling"), dict) else {}
        ceil = {k: pc[k] for k in ("breakeven_landed_ils", "landed_for_40_ils", "slot_price_ils", "pack_median_ils", "breakeven_landed_usd",
                                   "landed_for_40_usd", "proposed_price_ils", "at_proposed", "set_of_4_price_ils", "at_set_of_4") if pc.get(k) is not None}
        unit_he = {"pair": "מחיר לזוג", "single": "מחיר ליחידה", "unit": "מחיר ליחידה", "set": "מחיר לסט"}
        notes = [unit_he.get(str(pc[k]), str(pc[k])) if k == "unit" else (f"המחיר המוצע ל{pc[k]}" if k == "proposed_for" else f"מחיר העמדה ל{pc[k]}" if k == "price_for" else str(pc[k]))
                 for k in ("unit", "price_for", "proposed_for", "price_note_he", "note", "girl_shaked") if isinstance(pc.get(k), (str, int, float)) and str(pc.get(k)).strip()]
        if notes:
            ceil["notes"] = notes
        qs = []
        for q in s.get("queries") or []:
            text = q if isinstance(q, str) else (q.get("query") if isinstance(q, dict) else None)
            if not text:
                continue
            t = q_tier.get((key, text)) or q_tier.get((str(s.get("slot")), text))
            row = {"q": text}
            if t:
                row["tier"], row["src"] = t[0], t[1]
                if t[2] > 1:
                    row["shared"] = t[2]
            qs.append(row)
        cs = comp_slot.get(key) or {}
        blocked = sorted({i for b in cs.get("blocked") or [] for i in b.get("ids") or []}, key=str)
        slots.append({
            "key": key, "room": rk, "id": sid, "name_he": meta.get("name_he"), "in_slots": bool(meta),
            "status": comp_status(s.get("status")) or s.get("status"), "priority": str(s.get("priority") or "") or None,
            "need": int(s["need_variations"]) if isnum(s.get("need_variations")) else None,
            "source": str(s.get("source_type") or "").lower() or None, "spec": s.get("spec_he") if isinstance(s.get("spec_he"), str) else None,
            "why": s.get("why_he") if isinstance(s.get("why_he"), str) else None,
            "check_first": as_text_list(s.get("check_first")), "rooms": s.get("rooms") if isinstance(s.get("rooms"), list) else None,
            "envelope": envelope_lines(s.get("envelope_cm")), "ceiling": ceil, "queries": qs,
            "searched_n": by_slot_n.get(key), "blocked": blocked,
        })
    prank = {"high": 0, "medium": 1, "low": 2}
    srank = {"empty": 0, "partial": 1, "ready-to-lock": 2, "on-hold": 3}
    room_order = {r: i for i, r in enumerate(ctx.room_ids)}
    slots.sort(key=lambda x: (prank.get(x["priority"] or "", 3), srank.get(x["status"] or "", 4), room_order.get(x["room"], 99), x["id"]))
    out["slots"] = slots
    # needs a card: the item, its slots, and whether a card exists by now
    nc = []
    for x in d.get("needs_card") or []:
        item = ae_canon(x.get("item_id") if isinstance(x, dict) else x, ctx.aliases)
        if not item:
            continue
        sl = [str(k) for k in (x.get("slots") or [])] if isinstance(x, dict) else []
        card = None
        for k in sl or [None]:
            card = ctx.card_for_ae(item, k)
            if card:
                break
        ctx.want_ae(item)
        nc.append({"item": item, "slots": sl, "registry": x.get("registry") if isinstance(x, dict) else None, "card": card})
    out["needs_card"] = nc
    out["dropped"] = [{"slot": str(x.get("slot") or ""), "query": str(x.get("query") or ""), "already_ran": str(x.get("already_ran") or "")}
                      for x in d.get("dropped_as_already_searched") or [] if isinstance(x, dict)]
    out["results"] = load_round_results(res_dir or src_dir / f"round-{out['round']}-results", ctx)
    return out


# --------------------------------------------------------------------------- official coverage, data chunks, publish

COVERAGE_JSON = ROOT / "data" / "leads" / "final-2026-10-13" / "coverage.json"


def load_coverage(path: Path = COVERAGE_JSON) -> dict:
    """The official coverage (scripts/sourcing/final_round_coverage.py -> coverage.json): per style and in total, the
    share of slots with 3 options ready to sell (pct_ready) and with Israeli shops too (pct_any). The Studio shows it on
    the overview and the boards screen (QA 2026-10-17, M7); the boards' own map counts something else."""
    if not path.exists():
        return {"present": False, "file": rel(path)}
    try:
        d = read_json(path)
    except Exception as e:
        log(f"  ! coverage: cannot read {rel(path)}: {e}")
        return {"present": False, "file": rel(path), "error": f"{type(e).__name__}: {e}"[:200]}
    keys = ("eligible", "covered_ready", "covered_any", "pct_ready", "pct_any", "pct_one_ready", "pct_one_any",
            "on_hold", "pct_ready_incl_on_hold")
    styles = []
    for sid, v in (d.get("styles") or {}).items():
        if isinstance(v, dict):
            styles.append(dict({"id": sid, "he": STYLE_FALLBACK_HE.get(sid, sid)}, **{k: v[k] for k in keys if isnum(v.get(k))}))
    order = {s: i for i, s in enumerate(STYLE_ORDER)}
    styles.sort(key=lambda s: order.get(s["id"], 99))
    tot = d.get("total") or {}
    return {"present": True, "file": rel(path), "date": d.get("date"), "fit_threshold": d.get("fit_threshold"),
            "styles": styles, "total": {k: tot[k] for k in keys + ("target_pct",) if isnum(tot.get(k))},
            "target_metric": tot.get("target_metric") if isinstance(tot.get("target_metric"), str) else None,
            "remaining": {k: len(v) for k, v in (d.get("remaining") or {}).items() if isinstance(v, list)}}


# The screens that are not the overview load their data when they open (QA 2026-10-17, M9: one 14.9 MB data.json took
# 17.9 s to the overview on a slow phone). Each chunk file holds {key: value} for whole keys (None) or {key: {sub: ...}}
# for the heavy parts of a key whose light parts stay in data.json; data.json "chunks" lists them for the page.
CHUNKS = (("compare", "comparison", ("rooms",)), ("sourcing", "next_sourcing", ("results", "dropped")),
          ("furniture", "furniture", None), ("boards", "boards", None), ("leads", "leads", None), ("log", "log", None))
CORE_TAIL = {"log": 12}  # a whole-key chunk whose last entries stay in data.json (the overview shows the latest log lines)
CORE_LIMIT_BYTES = 4 * 1024 * 1024  # the first load (data.json); a warning above it


def split_chunks(data: dict) -> dict:
    """Move the chunks out of data (in place) and return {file name: chunk}; data["chunks"] says where they went."""
    files, index = {}, {}
    for name, key, subs in CHUNKS:
        if key not in data or data[key] is None:
            continue
        v = data[key]
        if subs is None:
            part = {key: v}
            del data[key]
            if key in CORE_TAIL and isinstance(v, list):
                data[key] = v[-CORE_TAIL[key]:]
        elif isinstance(v, dict) and any(s in v for s in subs):
            part = {key: {s: v.pop(s) for s in subs if s in v}}
        else:
            continue
        fname = f"data-{name}.json"
        files[fname] = part
        index[name] = {"file": fname, "keys": {key: list(subs) if subs else None}}
    data["chunks"] = index
    return files


def read_dist_data(dist: Path) -> dict:
    """data.json with its chunks merged back (for the tests and tools that read a build)."""
    data = json.loads((dist / "data.json").read_text(encoding="utf-8"))
    for name, c in (data.get("chunks") or {}).items():
        f = dist / c["file"]
        if not f.exists():
            continue
        part = json.loads(f.read_text(encoding="utf-8"))
        for key, subs in (c.get("keys") or {}).items():
            if subs is None:
                data[key] = part.get(key)
            elif isinstance(part.get(key), dict):
                data.setdefault(key, {}).update(part[key])
    return data


# The paths of the published version (Artifact files listing). After a publish, the art director refreshes it (the
# Artifact tool: action "list", scope "files"). The build prints what the publish must remove: paths in it that this
# build no longer produces (old img/a and img/p pictures, older sheets), so the version stays under 511 files.
PUBLISHED_FILES = STUDIO / "published-files.json"
PUBLISH_MAX_SEND, VERSION_MAX_FILES = 255, 511


def publish_plan(produced: list[str], path: Path = PUBLISHED_FILES) -> dict:
    out = {"file": rel(path), "present": path.exists(), "stale": [], "new": [], "published": None}
    if not path.exists():
        return out
    try:
        d = read_json(path)
        pub = d.get("paths") if isinstance(d, dict) else d
        pub = [x for x in pub or [] if isinstance(x, str)]
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"[:200]
        return out
    prod = set(produced)
    out.update({"published": len(pub), "version": d.get("version") if isinstance(d, dict) else None,
                "stale": sorted(set(pub) - prod), "new": sorted(prod - set(pub))})
    return out


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
    comp_dir, src_dir, res_dir = COMPOSITIONS_DIR, NEXT_SOURCING_DIR, None
    if "--compositions-dir" in sys.argv:  # testing: room compositions from another folder (studio/tests/fixtures/compositions)
        comp_dir = Path(sys.argv[sys.argv.index("--compositions-dir") + 1]).resolve()
    if "--sourcing-dir" in sys.argv:  # testing: round-N-*.json and searched-index.json from another folder
        src_dir = Path(sys.argv[sys.argv.index("--sourcing-dir") + 1]).resolve()
    if "--round-results-dir" in sys.argv:  # testing: the round's results from another folder (default <sourcing-dir>/round-N-results)
        res_dir = Path(sys.argv[sys.argv.index("--round-results-dir") + 1]).resolve()
    t0 = time.time()
    log(f"Studio build · repo {ROOT}")
    plan = read_json(ROOT / "docs" / "house-plan.json")
    order, rooms = load_rooms(plan)
    slots = load_slots(order, rooms)
    products = load_products(set(order))
    # one id, one card (QA 2026-10-17, M1): a second card with the same id hides the first in the Studio, and a Studio
    # edit would land in the wrong file (studio/apply_edits.py refuses such an id). Said loudly, here and at the end.
    by_id_paths: dict[str, list[str]] = {}
    for p in products:
        by_id_paths.setdefault(p["id"], []).append(p["_path"])
    dup_ids = {k: v for k, v in sorted(by_id_paths.items()) if len(v) > 1}
    for k, v in dup_ids.items():
        log(f"  ! DUPLICATE CARD ID {k}: {', '.join(v)}")
    n_dup = mark_duplicates(products)
    attach_candidates(slots, products)
    slot_by_key = {s["key"]: s for rows in slots.values() for s in rows}
    recs = lead_records()
    for p in products:
        p["_lead_rec"] = recs.get(p["id"])
        p["_sell_qty"] = sell_qty_default(p, slot_by_key)
    n_qty = sum(1 for p in products if p["_sell_qty"]["qty"] > 1)
    n_unsure = sum(1 for p in products if not p["_sell_qty"]["sure"])
    log(f"  rooms {len(order)} · slots {sum(len(v) for v in slots.values())} · products {len(products)} ({len(by_id_paths)} ids)"
        f" · duplicate cards {n_dup} (same supplier listing) · duplicate ids {len(dup_ids)}")
    log(f"  sell quantity: {n_qty} cards sold as a set by default · {n_unsure} not sure (default 1)")

    # fresh dist (studio/dist is generated output)
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "img" / "s").mkdir(parents=True)
    (DIST / "img" / "f").mkdir(parents=True)

    pstats = build_product_images(products, offline)
    log(f"  product images: downloaded {pstats['downloaded']} · from cache {pstats['cached']} · failed {pstats['failed']} · used a later image {pstats['fallback']}")
    boards = load_boards(products, offline)
    if boards.get("present"):
        bi = boards["images"]
        n_fill = sum(1 for b in boards["boards"] for s in b["slots"] if s["status"] in ("chosen", "candidate"))
        n_all = sum(len(b["slots"]) for b in boards["boards"])
        log(f"  boards: {len(boards['boards'])} (styles {len(boards['styles'])} x rooms {len(boards['rooms'])}) · slots {n_all}, filled {n_fill}"
            f" · cards {bi['cards']}, thumbnails {bi['with_file']} ({len(bi['placeholders'])} placeholders, {len(bi['built_now'])} built now)"
            + (f" · not a card {len(bi['not_cards'])}" if bi["not_cards"] else "") + f" · redacted {boards['redacted']}")

    frames = collect_frames(plan, order, rooms)
    hits = build_frame_images(frames)
    log(f"  frame images: {len(frames)} ({hits} from cache)")

    economics = load_economics(eco_dir, products)
    if economics["files"]:
        c = economics.get("counts", {})
        log(f"  economics: {', '.join(economics['files'])} · shipping from CJ {c.get('shipping_cj', 0)}, Zendrop {c.get('shipping_zendrop', 0)},"
            f" AliExpress {c.get('shipping_aliexpress', 0)}, card SKU {c.get('shipping_card', 0)}, manual {c.get('shipping_manual', 0)}"
            f" · no route to Israel {c.get('no_route', 0)} · no option within 20 days {c.get('no_fast_shipping', 0)}"
            f" · retail prices {c.get('retail', 0)} ({c.get('initial_prices', 0)} initial, {c.get('from_card', 0)} from the card or its final-round record"
            f", shipping from that record {c.get('shipping_leads', 0)}) · sell quantities {c.get('sell_qty', 0)}")
    else:
        log(f"  economics: no files in {economics['dir']} (the page shows its defaults)")

    board = parse_board(ROOT / "status" / "board.md")
    decisions = load_decisions(order)
    blockers = load_blockers()
    office = load_office(board["log"])
    if office:
        n_ins = sum(1 for a in office["agents"] if a["instructions"])
        log(f"  office: {len(office['agents'])} offices in {len(office['wings'])} wings · {len(office['flows'])} flows · instructions {n_ins}"
            f" · board mentions {sum(a['board']['count'] for a in office['agents'])}" + (f" · redacted {office['redacted']}" if office["redacted"] else ""))
        for w in office["warnings"]:
            log(f"  ! office: {w}")
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
    # the designer's room compositions and the next sourcing round (cards may appear while this runs: read once, tolerate gaps)
    ctx = CompCtx(products, dec_ids, order, slot_by_key)
    compositions = load_compositions(comp_dir, ctx)
    next_sourcing = load_next_sourcing(src_dir, res_dir, ctx, compositions)
    ae_record_index(set(ctx.wanted), ctx, [d for d in (deep_dir,) if d != DEEP_DIR])
    res = (next_sourcing.get("results") or {})
    targets = [("ae:" + i, ctx.ae[i].get("img_url")) for i in sorted(ctx.wanted) if ctx.ae.get(i)]
    targets += [("res:" + r["img_url"], r["img_url"]) for rows in res.get("by_slot", {}).values() for r in rows if not r.get("card") and r.get("img_url")]
    # no more one-file thumbnails of AliExpress items without a card (dist/img/a, QA 2026-10-17 B1): those tiles show the
    # supplier's image URL, and the product pictures are packed into sheets
    thumbs = build_thumb_images(targets, offline, 0)
    for i, info in ctx.ae.items():
        if thumbs.get("ae:" + i):
            info["img"] = thumbs["ae:" + i]
    for rows in res.get("by_slot", {}).values():
        for r in rows:
            src = thumbs.get("res:" + r["img_url"]) if r.get("img_url") else None
            if src:
                r["img"] = src
    compositions["ae"] = {i: ctx.ae[i] for i in sorted(ctx.wanted) if i in ctx.ae}
    n_comp_slots = sum(len(c["slots"]) for st in compositions["rooms"].values() for c in st.values())
    n_ae_tiles = len(re.findall(r'"k": "ae"', json.dumps(compositions["rooms"])))
    log(f"  compositions: {len(compositions['rooms'])} rooms · {n_comp_slots} slots · AliExpress records {len(compositions['ae'])}"
        f" ({sum(1 for i in compositions['ae'] if ctx.ae_cards.get(i))} have a card by now, {n_ae_tiles} tiles still need one)"
        f" · thumbnails {len(thumbs)} of {len(targets)}"
        + (f" · warnings {len(compositions['warnings'])}" if compositions["warnings"] else "") + ("" if compositions["present"] else f" (no {compositions['dir']} yet)"))
    for w in compositions["warnings"] + next_sourcing.get("warnings", []):
        log(f"  ! {w}")
    if next_sourcing.get("present"):
        sx = next_sourcing.get("searched") or {}
        log(f"  next sourcing: round {next_sourcing.get('round')} · {len(next_sourcing['slots'])} slots · {next_sourcing['n_queries']} queries"
            f" · needs a card {len(next_sourcing['needs_card'])} · results {res.get('n', 0)} in {len(res.get('files') or [])} files"
            + ("" if res.get("present") else f" (no {res.get('dir')} yet)")
            + (f" · searched index: {sx.get('ae_queries')} AliExpress queries in {sx.get('ae_slots')} slots, registry {sx.get('registry_items')}" if sx else ""))
    else:
        log(f"  next sourcing: no round-N file in {next_sourcing['dir']}")
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

    sheets = pack_product_sheets(products)
    pstats["failed"] += sheets["decode_failed"]
    log(f"  product sheets: {sheets['sheets']} sheets ({SHEET_COLS}x{SHEET_ROWS} cells of {SHEET_CELL}px) · {sheets['cells']} pictures"
        f" · {sheets['from_cache']} from cache · {sheets['bytes'] / 1024 / 1024:.2f} MB" + (f" · {sheets['decode_failed']} did not open" if sheets["decode_failed"] else ""))
    coverage = load_coverage()
    if coverage.get("present"):
        ct = coverage.get("total") or {}
        log(f"  official coverage ({coverage['file']}, {coverage.get('date')}): 3 options ready {ct.get('pct_ready')}% · with Israeli shops {ct.get('pct_any')}%")
    else:
        log(f"  official coverage: no {coverage['file']}")

    out_products = []
    for p in products:
        q = {k: v for k, v in p.items() if not k.startswith("_")}
        im = q.get("images")
        if isinstance(im, dict) and isinstance(im.get("urls"), list):  # the page shows only how many (QA M9: data.json weight)
            q["images"] = dict({k: v for k, v in im.items() if k != "urls"}, n=len(im["urls"]))
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
            "product_sheets": sheets,
        },
        "counts": {
            "products": len(by_id_paths),
            "cards": len(products),
            "duplicate_ids": dup_ids,
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
        "office": office,
        "economics": economics,
        "market": market,
        "styles": styles,
        "suppliers": suppliers,
        "comparison": comparison,
        "furniture": furniture,
        "compositions": compositions,
        "next_sourcing": next_sourcing,
        "boards": boards,
        "reports": qa,
        "leads": leads,
        "coverage": coverage,
    }
    for fname, part in split_chunks(data).items():
        (DIST / fname).write_text(json.dumps(part, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        data["chunks"][next(c for c in data["chunks"] if data["chunks"][c]["file"] == fname)]["bytes"] = (DIST / fname).stat().st_size
    (DIST / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    if not PAGE_SRC.exists():
        log(f"  ! missing page source {rel(PAGE_SRC)}")
        return 1
    shutil.copyfile(PAGE_SRC, DIST / "index.html")

    files = [p for p in DIST.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    produced = sorted(str(p.relative_to(DIST)) for p in files)
    core = (DIST / "data.json").stat().st_size
    chunk_line = ", ".join(f"{c['file']} {c['bytes'] / 1024:.0f} KB" for c in data["chunks"].values())
    log(f"  dist: {len(files)} files · {total / 1024 / 1024:.2f} MB (limits {LIMIT_FILES} files, {LIMIT_BYTES / 1024 / 1024:.0f} MB)"
        f" · {sum(1 for x in produced if x.startswith('img/s/'))} product sheets, {sum(1 for x in produced if x.startswith('img/f/'))} frames")
    log(f"  data.json {core / 1024:.0f} KB (the first load; limit {CORE_LIMIT_BYTES / 1024 / 1024:.0f} MB)"
        f" · chunks {chunk_line} · commit {commit}{' (uncommitted changes)' if dirty else ''}")
    if core > CORE_LIMIT_BYTES:
        log("  ! data.json is over 4 MB: the overview loads slowly on a phone (move a heavy key into a chunk)")
    plan = publish_plan(produced)
    if plan["present"] and plan.get("published") is not None:
        send = sorted(set(plan["new"]) | {x for x in produced if not x.startswith("img/")})
        entries = len(send) + len(plan["stale"])
        n_batches = max(1, -(-entries // PUBLISH_MAX_SEND))
        log(f"  publish: {len(send)} files to send (new paths, the page and the data) and {len(plan['stale'])} to remove; the published version"
            f" holds {plan['published']} ({plan['file']}{', ' + plan['version'] if plan.get('version') else ''}), after the publish {len(files)}")
        if n_batches > 1:
            log(f"  publish in {n_batches} batches of at most {PUBLISH_MAX_SEND} entries: first the {len(send)} files"
                f" (the version then holds {plan['published'] + len(plan['new'])}, under {VERSION_MAX_FILES}), then the removals")
        if plan["published"] + len(plan["new"]) > VERSION_MAX_FILES:
            log(f"  ! sending the new files first would pass {VERSION_MAX_FILES} files in the version: remove the stale paths first")
        try:  # the same plan as a file for the publish (outside dist, which is published as it is); not from test builds
            if DIST.resolve() != (STUDIO / "dist").resolve():
                raise RuntimeError("a build into another folder (--dist) does not replace it")
            (CACHE / "publish-plan.json").write_text(json.dumps({"built_at": data["build"]["built_at"], "commit": commit,
                "published": plan["file"], "send": send, "remove": plan["stale"]}, ensure_ascii=False, indent=1), encoding="utf-8")
            log(f"  the plan: {rel(CACHE / 'publish-plan.json')}")
        except Exception as e:
            log(f"  (no publish plan file: {e})")
        if plan["stale"]:
            log(f"  published paths this build no longer produces ({len(plan['stale'])}): remove them in the publish (null):")
            for x in plan["stale"]:
                log(f"    {x}")
    elif plan.get("error"):
        log(f"  ! {plan['file']}: {plan['error']}")
    else:
        log(f"  publish: no {plan['file']} (the published paths), so the stale paths are not known")
    if dup_ids:
        log(f"  ! DUPLICATE CARD IDS ({len(dup_ids)}): the Studio shows one card per id, and studio/apply_edits.py refuses edits to them:")
        for k, v in dup_ids.items():
            log(f"    {k}: {', '.join(v)}")
    log(f"done in {time.time() - t0:.1f}s")
    if total > LIMIT_BYTES or len(files) > LIMIT_FILES:
        log("  ! dist is over the limit")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
