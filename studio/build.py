#!/usr/bin/env python3
"""Build "the Studio" (internal back-office) into studio/dist/.

Reads the repo's source-of-truth files (read-only) and writes:
  dist/data.json        everything the page shows, computed from the repo
  dist/img/p/<id>.webp  first image of each product, 360px long side, q72
  dist/img/f/<n>.webp   frames and renders, 1280px long side, q78
  dist/index.html       the page (copied from studio/src/index.html)

Product images are downloaded once and cached in studio/.cache/, so a second
build does not hit the network. Frame conversions are cached there too.

Usage: python3 studio/build.py [--offline]
  --offline  never download; products without a cached image get a placeholder.

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

LIMIT_BYTES = 12 * 1024 * 1024
LIMIT_FILES = 240
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
    """Default shipping from CJ freight data: the cheapest option that arrives within 20 days,
    otherwise the cheapest option overall. Returns (usd, option_key, option) or None."""
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
    pool = under or [(k, o) for k, o in opts if k == "cheapest"] or opts
    k, o = min(pool, key=lambda x: x[1]["usd"])
    return o["usd"], k, o


def load_economics(eco_dir: Path, products: list[dict]) -> dict:
    out = {"dir": rel(eco_dir) if eco_dir.is_relative_to(ROOT) else str(eco_dir), "settings": None, "budget": None,
           "products": {}, "freight": None, "bundles": None, "files": []}
    if not eco_dir.exists():
        return out
    sp = eco_dir / "settings.json"
    if sp.exists():
        d = read_json(sp)
        out["settings"] = d.get("economics")
        out["budget"] = d.get("budget")
        out["files"].append(sp.name)
    bp = eco_dir / "budget.json"
    if out["budget"] is None and bp.exists():
        out["budget"] = read_json(bp)
        out["files"].append(bp.name)
    manual = {}
    pp = eco_dir / "products.json"
    if pp.exists():
        d = read_json(pp)
        manual = d.get("products", d) if isinstance(d, dict) else {}
        out["files"].append(pp.name)
    freight, fdate = {}, None
    fp = eco_dir / "freight-cj.json"
    if fp.exists():
        try:
            d = read_json(fp)
            freight = d.get("products") or {}
            for k in ("updated", "generated_at", "generated", "date", "checked_at", "as_of", "created"):
                if d.get(k):
                    fdate = first_date(str(d[k]))
                    if fdate:
                        break
            fdate = fdate or git_date(fp) or dt.date.fromtimestamp(fp.stat().st_mtime).isoformat()
            out["freight"] = {"file": fp.name, "date": fdate, "products": len(freight)}
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
    n_cj = n_manual = 0

    def opt(o):
        if not isinstance(o, dict) or not isnum(o.get("usd")):
            return None
        days = o.get("days") or (f"{o.get('days_min')}-{o.get('days_max')}" if o.get("days_min") is not None else None)
        return {"usd": o["usd"], "name": o.get("name") or o.get("logistic") or o.get("method"), "days": days}

    for p in products:
        pid = p["id"]
        m = manual.get(pid) or {}
        e = {}
        if isnum(m.get("shipping_cost_usd")):
            e["manual"] = {"shipping_cost_usd": m["shipping_cost_usd"], "date": first_date(str(m.get("updated_at") or ""))}
            n_manual += 1
        fe = freight.get(pid)
        if isinstance(fe, dict):
            under = pick_freight(fe)
            cj = {"cheapest": opt(fe.get("cheapest")), "under20": opt(under[2]) if under else None,
                  "date": first_date(str(fe.get("checked_at") or fe.get("date") or "")) or fdate, "status": fe.get("status")}
            if cj["cheapest"] is None and under:  # no explicit cheapest: the cheapest of all options
                allo = [opt(o) for o in (fe.get("options") or [])] + [cj["under20"]]
                allo = [o for o in allo if o]
                cj["cheapest"] = min(allo, key=lambda o: o["usd"]) if allo else None
            if cj["cheapest"] or cj["under20"]:
                n_cj += 1
            e["cj"] = cj
        for k in ("retail_ils", "compare_at_ils"):
            if isnum(m.get(k)):
                e[k] = m[k]
        if e:
            out["products"][pid] = e
    out["counts"] = {"shipping_cj": n_cj, "shipping_manual": n_manual,
                     "retail": sum(1 for v in out["products"].values() if "retail_ils" in v)}
    return out


# --------------------------------------------------------------------------- main

def main() -> int:
    offline = "--offline" in sys.argv
    eco_dir = ROOT / "data" / "economics"
    if "--economics-dir" in sys.argv:  # for testing with sample files outside the repo data
        eco_dir = Path(sys.argv[sys.argv.index("--economics-dir") + 1]).resolve()
    t0 = time.time()
    log(f"Studio build · repo {ROOT}")
    plan = read_json(ROOT / "docs" / "house-plan.json")
    order, rooms = load_rooms(plan)
    slots = load_slots(order, rooms)
    products = load_products(set(order))
    n_dup = mark_duplicates(products)
    attach_candidates(slots, products)
    log(f"  rooms {len(order)} · slots {sum(len(v) for v in slots.values())} · products {len(products)} · duplicate cards {n_dup}")

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
        log(f"  economics: {', '.join(economics['files'])} · shipping from CJ {c.get('shipping_cj', 0)}, manual {c.get('shipping_manual', 0)} · retail prices {c.get('retail', 0)}")
    else:
        log(f"  economics: no files in {economics['dir']} (the page shows its defaults)")

    board = parse_board(ROOT / "status" / "board.md")
    decisions = load_decisions(order)
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
        })
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
        "economics": economics,
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
