#!/usr/bin/env python3
"""Sync edits made in the Studio (claude.ai Artifact db) back into the repo.

The repo stays the source of truth; the Artifact db only holds corrections. The
manager exports the db to one JSON file and runs:

    python3 studio/apply_edits.py EXPORT.json            # apply and write
    python3 studio/apply_edits.py EXPORT.json --dry-run  # only print the diff

EXPORT.json (the Studio's "sync file" button produces exactly this):
    {
      "product_edits": [{"id": "<product id>", "data": {"fields": {...}, "history": [...], "synced": false}}],
      "product_new":   [{"id": "<db doc id>",  "data": {"url": ..., "room": ..., "slot": ..., "name": ...,
                                                         "cost_usd": ..., "note": ..., "links": [...]}}],
      "settings":      {"economics": {...} | null, "budget": {"rows": [...]} | null}
    }
Lists may also be given as {id: data} objects.

What it does:
  * applies each product patch to data/products/**/<id>.json. Only schema fields are
    touched: name, slot, rooms, status, supplier.product_url, supplier.sku, price.cost,
    notes. Extra links go into a [studio-links] block at the end of notes (the schema
    has no links field). A slot move to another room also moves the file (--no-move to skip).
  * writes economics fields (shipping_cost_usd, retail_ils, compare_at_ils) to
    data/economics/products.json and the settings to data/economics/settings.json.
  * creates a lead card per new product in data/products/leads/<id>.json (status
    candidate); missing required fields are listed in its notes.
  * validates every card it writes against data/product-card.schema.json (never edits it).
  * prints a diff summary and the ids that were synced, so the manager can set
    synced:true on those db documents.

Options: --dry-run, --no-move, --all (also re-apply documents already marked synced),
         --force (write a card even if it fails validation), --root DIR, --out FILE.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402  (shared helpers: links block, room folders)

STATUS = ("candidate", "selected", "rejected")
ECON_KEYS = ("shipping_cost_usd", "retail_ils", "compare_at_ils")
ROOM_FOLDER = {"living-room": None, "dining-room": "dining", "hall": "entrance", "bath": "bath",
               "corridor": "corridor", "kids": "kids", "master": "master", "work": "work"}


# --------------------------------------------------------------------------- helpers

def isnum(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def nested(fields: dict) -> dict:
    """Accept both {"supplier": {"sku": ...}} and {"supplier.sku": ...}."""
    out: dict = {}
    for k, v in (fields or {}).items():
        if "." in k:
            a, b = k.split(".", 1)
            out.setdefault(a, {})[b] = v
        elif isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def as_items(x) -> list[tuple[str, dict]]:
    if not x:
        return []
    if isinstance(x, dict):
        return [(k, v) for k, v in x.items()]
    return [(i.get("id"), i.get("data") if "data" in i else i) for i in x]


def flat(o, prefix=""):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            out.update(flat(v, f"{prefix}.{k}" if prefix else k))
        return out
    return {prefix: o}


def short(v, n=70):
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[: n - 1] + "…"


def https_ok(u) -> bool:
    return isinstance(u, str) and u.startswith("https://") and len(u) > 9


def slugify(text: str, n=5) -> str:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return "-".join(words[:n])


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- schema (simple)

PY_TYPES = {"string": str, "object": dict, "array": list, "boolean": bool}


def type_ok(v, t) -> bool:
    if t == "null":
        return v is None
    if t == "number":
        return isnum(v)
    if t == "integer":
        return isnum(v) and float(v).is_integer()
    return isinstance(v, PY_TYPES.get(t, object)) and not (t != "boolean" and isinstance(v, bool))


def validate(inst, schema: dict, path="$", errs=None) -> list[str]:
    errs = [] if errs is None else errs
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(type_ok(inst, x) for x in ts):
            errs.append(f"{path}: expected {'/'.join(ts)}, got {type(inst).__name__}")
            return errs
    if "enum" in schema and inst not in schema["enum"]:
        errs.append(f"{path}: {short(inst)} is not one of {schema['enum']}")
    if isinstance(inst, str) and "pattern" in schema and not re.search(schema["pattern"], inst):
        errs.append(f"{path}: {short(inst)} does not match {schema['pattern']}")
    if isnum(inst):
        if "minimum" in schema and inst < schema["minimum"]:
            errs.append(f"{path}: {inst} < {schema['minimum']}")
        if "maximum" in schema and inst > schema["maximum"]:
            errs.append(f"{path}: {inst} > {schema['maximum']}")
    if isinstance(inst, dict):
        for r in schema.get("required", []):
            if r not in inst:
                errs.append(f"{path}: missing required '{r}'")
        props = schema.get("properties", {})
        for k, v in inst.items():
            if k in props:
                validate(v, props[k], f"{path}.{k}", errs)
            elif isinstance(schema.get("additionalProperties"), dict):
                validate(v, schema["additionalProperties"], f"{path}.{k}", errs)
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected field '{k}'")
    if isinstance(inst, list) and isinstance(schema.get("items"), dict):
        for i, v in enumerate(inst):
            validate(v, schema["items"], f"{path}[{i}]", errs)
    return errs


# --------------------------------------------------------------------------- main work

class Run:
    def __init__(self, root: Path, args):
        self.root = root
        self.args = args
        self.products_dir = root / "data" / "products"
        self.eco_dir = root / "data" / "economics"
        self.schema = json.loads((root / "data" / "product-card.schema.json").read_text(encoding="utf-8"))
        self.index = {p.stem: p for p in self.products_dir.rglob("*.json")}
        self.room_slots = {}
        for f in (root / "data" / "slots").glob("*.json"):
            try:
                self.room_slots[f.stem] = {s["id"] for s in json.loads(f.read_text(encoding="utf-8")).get("slots", [])}
            except Exception:
                pass
        self.lines: list[str] = []
        self.problems: list[str] = []
        self.synced_edits: list[str] = []
        self.synced_new: list[str] = []
        self.econ_updates: dict[str, dict] = {}
        self.today = dt.date.today().isoformat()

    def say(self, s=""):
        self.lines.append(s)

    def current_room_slot(self, path: Path, card: dict):
        parts = path.relative_to(self.products_dir).parts
        if parts[0] == B.LEADS_DIR:
            return None, card.get("slot")
        if len(parts) == 2:
            return "living-room", card.get("slot") or parts[0]
        if parts[0] == B.POOL_DIR:
            return None, card.get("slot")
        return B.ROOM_DIRS.get(parts[0]), card.get("slot") or parts[1]

    def target_path(self, room: str, slot: str, pid: str) -> Path | None:
        if room not in ROOM_FOLDER:
            return None
        folder = ROOM_FOLDER[room]
        return (self.products_dir / slot / f"{pid}.json") if folder is None else (self.products_dir / folder / slot / f"{pid}.json")

    # ---- product patches
    def apply_edit(self, pid: str, doc: dict):
        if not pid:
            return
        if doc.get("synced") and not self.args.all:
            return
        f = nested(doc.get("fields") or {})
        path = self.index.get(pid)
        if not path:
            self.problems.append(f"{pid}: no card with this id under data/products/ (skipped)")
            return
        card = json.loads(path.read_text(encoding="utf-8"))
        before = copy.deepcopy(card)
        errs: list[str] = []

        if "name" in f:
            if isinstance(f["name"], str) and f["name"].strip():
                card["name"] = f["name"].strip()
            else:
                errs.append("name: empty")
        if "status" in f:
            if f["status"] in STATUS:
                card["status"] = f["status"]
            else:
                errs.append(f"status: {short(f['status'])} is not one of {STATUS}")
        if "rooms" in f:
            if isinstance(f["rooms"], list) and all(isinstance(x, str) for x in f["rooms"]):
                card["rooms"] = f["rooms"]
            else:
                errs.append("rooms: must be a list of strings")
        sup = f.get("supplier") or {}
        if "product_url" in sup:
            if https_ok(sup["product_url"]):
                card.setdefault("supplier", {})["product_url"] = sup["product_url"].strip()
            else:
                errs.append(f"supplier.product_url: must start with https:// ({short(sup['product_url'])})")
        if "sku" in sup:
            v = sup["sku"]
            if v is None or isinstance(v, str):
                card.setdefault("supplier", {})["sku"] = (v.strip() or None) if isinstance(v, str) else None
            else:
                errs.append("supplier.sku: must be text")
        price = f.get("price") or {}
        if "cost" in price:
            if isnum(price["cost"]) and price["cost"] >= 0:
                card.setdefault("price", {})["cost"] = price["cost"]
            else:
                errs.append(f"price.cost: must be a number >= 0 ({short(price['cost'])})")
        if "notes" in f or "links" in f:
            cur_notes, cur_links = B.split_links(card.get("notes"))
            notes = f["notes"] if "notes" in f else cur_notes
            links = f["links"] if "links" in f else cur_links
            good = []
            for l in links or []:
                if isinstance(l, dict) and https_ok(l.get("url")):
                    good.append({"label": str(l.get("label") or "").replace("|", "/").strip(), "url": l["url"].strip()})
                else:
                    errs.append(f"links: skipped {short(l)} (url must start with https://)")
            card["notes"] = B.join_links(notes if isinstance(notes, str) else None, good)

        move_to = None
        if "slot" in f or "slot_room" in f:
            cur_room, cur_slot = self.current_room_slot(path, card)
            new_room = f.get("slot_room", cur_room)
            new_slot = f.get("slot", cur_slot)
            if not new_slot or (new_room and new_slot not in self.room_slots.get(new_room, set())):
                errs.append(f"slot: '{new_room}/{new_slot}' is not a slot in data/slots/{new_room}.json")
            else:
                card["slot"] = new_slot
                if (new_room, new_slot) != (cur_room, cur_slot) and new_room:
                    tp = self.target_path(new_room, new_slot, pid)
                    if tp and tp != path:
                        move_to = tp

        econ = f.get("economics") or {}
        eu = {}
        for k in ECON_KEYS:
            if k in econ:
                v = econ[k]
                if v is None or (isnum(v) and v >= 0):
                    eu[k] = v
                else:
                    errs.append(f"economics.{k}: must be a number >= 0 or empty ({short(v)})")
        if eu:
            self.econ_updates[pid] = eu

        verrs = validate(card, self.schema)
        diff = [(k, flat(before).get(k), v) for k, v in flat(card).items() if flat(before).get(k) != v]
        diff += [(k, v, None) for k, v in flat(before).items() if k not in flat(card)]
        self.say(f"• {pid}  ({path.relative_to(self.root)})")
        for k, a, b in diff:
            self.say(f"    {k}: {short(a)} → {short(b)}")
        for k, v in eu.items():
            self.say(f"    economics.{k} → {short(v)}  (data/economics/products.json)")
        if move_to:
            self.say(f"    MOVE → {move_to.relative_to(self.root)}" + ("  (skipped: --no-move)" if self.args.no_move else ""))
        if not diff and not eu and not move_to:
            self.say("    no change (already matches the repo)")
        for e in errs:
            self.say(f"    ! {e}")
            self.problems.append(f"{pid}: {e}")
        if verrs:
            for e in verrs:
                self.say(f"    ! schema: {e}")
            self.problems += [f"{pid}: schema: {e}" for e in verrs]
            if not self.args.force:
                self.say("    card NOT written (fails the schema; --force to override)")
                return
        if not self.args.dry_run:
            if diff:
                write_json(path, card)
            if move_to and not self.args.no_move:
                if move_to.exists():
                    self.problems.append(f"{pid}: target {move_to.relative_to(self.root)} exists, not moved")
                else:
                    move_to.parent.mkdir(parents=True, exist_ok=True)
                    path.replace(move_to)
                    self.index[pid] = move_to
        if not errs:
            self.synced_edits.append(pid)

    # ---- new leads
    def apply_new(self, doc_id: str, d: dict):
        if not doc_id or (d.get("synced") and not self.args.all):
            return
        marker = f"product_new/{doc_id}"
        for p in (self.products_dir / B.LEADS_DIR).glob("*.json") if (self.products_dir / B.LEADS_DIR).exists() else []:
            if marker in (p.read_text(encoding="utf-8")):
                self.say(f"• lead {doc_id}: already in {p.relative_to(self.root)} (skipped)")
                self.synced_new.append(doc_id)
                return
        url = (d.get("url") or "").strip()
        host = urllib.parse.urlparse(url).hostname or ""
        sup_short = "cj" if "cjdropshipping" in host else (host.replace("www.", "").split(".")[0] or "web")
        sup_name = "CJ Dropshipping" if sup_short == "cj" else (host.replace("www.", "") or "לא ידוע")
        slot = (d.get("slot") or "").strip() or None
        room = (d.get("room") or "").strip() or None
        name = (d.get("name") or "").strip()
        base = slugify(name) or slugify(urllib.parse.urlparse(url).path) or doc_id.lower()
        pid = f"{slot or 'lead'}-{sup_short}-{base}"[:80].strip("-")
        while pid in self.index:
            pid += "-x"
        missing = []
        card = {"id": pid, "slot": slot or "", "name": name or f"ליד מ-{host or 'קישור'}"}
        if not slot:
            missing.append("slot")
        if not name:
            missing.append("name")
        if room:
            card["rooms"] = [room]
        card["supplier"] = {"name": sup_name, "product_url": url, "sku": None, "rating": None}
        if not https_ok(url):
            self.problems.append(f"lead {doc_id}: url must start with https:// ({short(url)})")
        price = {"currency": "USD", "suggested_retail": None}
        if isnum(d.get("cost_usd")) and d["cost_usd"] >= 0:
            price = {"cost": d["cost_usd"], **price}
        else:
            missing.append("price.cost")
        card["price"] = price
        card["images"] = {"urls": [], "quality": "low", "usage_rights": "unclear"}
        missing += ["colors", "materials", "visual_weight", "images.urls"]
        card["status"] = "candidate"
        by = d.get("by") or "?"
        intro = (f"ליד מהסטודיו ({marker}), נוסף {str(d.get('created_at') or self.today)[:10]} על ידי {by}. "
                 f"חסרים שדות חובה: {', '.join(missing)}. אין תמונות עד שה-sourcing-agent ימלא את הכרטיס.")
        note = (d.get("note") or "").strip()
        good = [l for l in d.get("links") or [] if isinstance(l, dict) and https_ok(l.get("url"))]
        card["notes"] = B.join_links(intro + (("\n" + note) if note else ""), good)
        path = self.products_dir / B.LEADS_DIR / f"{pid}.json"
        verrs = validate(card, self.schema)
        expected = [e for e in verrs if "missing required" in e and any(f"'{m.split('.')[-1]}'" in e for m in missing)]
        other = [e for e in verrs if e not in expected]
        self.say(f"• lead {doc_id} → {path.relative_to(self.root)}")
        self.say(f"    name {short(card['name'])} · slot {room}/{slot} · url {short(url, 60)}")
        if expected:
            self.say(f"    (expected for a lead) {len(expected)} schema gaps: {', '.join(missing)}")
        for e in other:
            self.say(f"    ! schema: {e}")
            self.problems.append(f"lead {doc_id}: schema: {e}")
        if not self.args.dry_run:
            write_json(path, card)
            self.index[pid] = path
        self.synced_new.append(doc_id)

    # ---- economics files
    def write_economics(self, settings: dict | None):
        if self.econ_updates:
            pp = self.eco_dir / "products.json"
            cur = json.loads(pp.read_text(encoding="utf-8")) if pp.exists() else {}
            prods = cur.get("products", {}) if isinstance(cur, dict) else {}
            for pid, eu in self.econ_updates.items():
                e = dict(prods.get(pid) or {})
                for k, v in eu.items():
                    if v is None:
                        e.pop(k, None)
                    else:
                        e[k] = v
                e["updated_at"] = self.today
                e["source"] = "studio"
                if any(k in e for k in ECON_KEYS):
                    prods[pid] = e
                else:
                    prods.pop(pid, None)
            out = {"version": 1, "note": "שדות כלכלה לכל מוצר (נכתב על ידי studio/apply_edits.py). משלוח ידני גובר על freight-cj.json.",
                   "updated": self.today, "products": dict(sorted(prods.items()))}
            self.say(f"• data/economics/products.json: {len(self.econ_updates)} products updated ({len(prods)} total)")
            if not self.args.dry_run:
                write_json(pp, out)
        if settings and (settings.get("economics") or settings.get("budget")):
            sp = self.eco_dir / "settings.json"
            cur = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
            out = {"version": 1, "updated": self.today,
                   "economics": settings.get("economics") or cur.get("economics"),
                   "budget": settings.get("budget") or cur.get("budget")}
            for k in ("economics", "budget"):
                if settings.get(k):
                    for a, b in [(x, y) for x, y in flat(settings[k]).items() if flat(cur.get(k) or {}).get(x) != y and not x.endswith(("updated_at", ".by", "by"))][:12]:
                        self.say(f"    settings.{k}.{a} → {short(b)}")
            n = len(((out.get("budget") or {}).get("rows")) or [])
            self.say(f"• data/economics/settings.json: economics {'set' if out['economics'] else '—'}, budget rows {n}")
            if not self.args.dry_run:
                write_json(sp, out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply Studio db edits to the repo")
    ap.add_argument("export", help="JSON exported from the Studio db")
    ap.add_argument("--dry-run", action="store_true", help="print the diff only")
    ap.add_argument("--no-move", action="store_true", help="do not move a card when its slot moves to another room")
    ap.add_argument("--all", action="store_true", help="also apply documents already marked synced")
    ap.add_argument("--force", action="store_true", help="write cards that fail schema validation")
    ap.add_argument("--root", default=str(B.ROOT), help="repo root (default: this repo)")
    ap.add_argument("--out", help="also write the synced ids to this JSON file")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    export = json.loads(Path(args.export).read_text(encoding="utf-8"))
    run = Run(root, args)
    run.say(f"Studio sync · {'DRY RUN · ' if args.dry_run else ''}repo {root}")
    run.say("")
    edits = as_items(export.get("product_edits"))
    news = as_items(export.get("product_new"))
    run.say(f"Product edits: {len(edits)}")
    for pid, doc in edits:
        run.apply_edit(pid, doc or {})
    run.say("")
    run.say(f"New leads: {len(news)}")
    for doc_id, d in news:
        run.apply_new(doc_id, d or {})
    run.say("")
    run.write_economics(export.get("settings"))
    result = {"product_edits": run.synced_edits, "product_new": run.synced_new, "dry_run": args.dry_run}
    run.say("")
    if run.problems:
        run.say(f"Problems ({len(run.problems)}):")
        for p in run.problems:
            run.say(f"  - {p}")
    else:
        run.say("No problems.")
    run.say("")
    run.say("Synced ids (set synced:true on these db documents" + (" after a real run" if args.dry_run else "") + "):")
    run.say(json.dumps(result, ensure_ascii=False))
    print("\n".join(run.lines))
    if args.out:
        write_json(Path(args.out), result)
    return 1 if run.problems else 0


if __name__ == "__main__":
    sys.exit(main())
