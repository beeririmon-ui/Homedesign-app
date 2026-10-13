#!/usr/bin/env python3
"""Set the required `room` field on every product card from its folder (card schema 1.1, user decision Q2).

    python3 scripts/migrate_card_room.py             # write room into the cards, then validate them all
    python3 scripts/migrate_card_room.py --dry-run   # only report what it would do
    python3 scripts/migrate_card_room.py --check     # report only; exit 1 if a card that has a room folder still lacks room
    add --list to print every card that fails the schema

Folder -> room (room = the id of data/slots/<room>.json, the enum in data/product-card.schema.json):
    data/products/<slot>/<card>.json               living-room (the first room keeps its slots at the top level)
    data/products/dining/<slot>/<card>.json        dining-room
    data/products/entrance/<slot>/<card>.json      hall
    data/products/<room>/<slot>/<card>.json        <room>: bath, corridor, kids, master, work
    data/products/pool/..., data/products/leads/...  no room in the path: listed, never guessed

A card gets `room` only when (1) its folder maps to a room in the schema enum, (2) the folder's slot equals the
card's `slot`, and (3) that slot exists in data/slots/<room>.json. Anything else is listed and left alone.
The only change to a card is one added line, `"room": "<id>",` just above its top-level `"slot"`.
A card that already has a different room is listed as a conflict, not overwritten.
After writing, every card is validated against the schema with the Studio's validator
(studio/apply_edits.py) and the failures are summarised by cause.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS = ROOT / "data" / "products"
SCHEMA = ROOT / "data" / "product-card.schema.json"
SLOTS_DIR = ROOT / "data" / "slots"

# Card folders whose name is not the room id. Every other room folder is named after its room.
FOLDER_ROOM = {"dining": "dining-room", "entrance": "hall"}
NO_ROOM_FOLDERS = {"pool": "pool card (slot null): no room in the path", "leads": "Studio lead: no room in the path"}
SLOT_LINE = re.compile(r'^  "slot":', re.M)


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def load_slots(room_ids) -> dict[str, set[str]]:
    out = {}
    for rid in room_ids:
        f = SLOTS_DIR / f"{rid}.json"
        out[rid] = {s["id"] for s in json.loads(f.read_text(encoding="utf-8")).get("slots", [])} if f.exists() else set()
    return out


def placement(path: Path, card: dict, room_ids, slots) -> tuple[str | None, str | None]:
    """(room, None) when the folder places the card, or (None, why not)."""
    parts = path.relative_to(PRODUCTS).parts
    if parts[0] in NO_ROOM_FOLDERS:
        return None, NO_ROOM_FOLDERS[parts[0]]
    if len(parts) == 2:
        room, folder_slot = "living-room", parts[0]
    elif len(parts) == 3:
        room, folder_slot = FOLDER_ROOM.get(parts[0], parts[0]), parts[1]
        if room not in room_ids:
            return None, f"folder '{parts[0]}' is not a room"
    else:
        return None, f"unexpected folder depth ({len(parts) - 1})"
    if card.get("slot") != folder_slot:
        return None, f"folder slot '{folder_slot}' but card slot {json.dumps(card.get('slot'))}"
    if folder_slot not in slots.get(room, set()):
        return None, f"slot '{folder_slot}' is not in data/slots/{room}.json"
    return room, None


def add_room(text: str, room: str) -> str:
    hits = SLOT_LINE.findall(text)
    if len(hits) != 1:
        raise ValueError(f"expected one top-level \"slot\" line, found {len(hits)}")
    m = SLOT_LINE.search(text)
    return text[:m.start()] + f'  "room": {json.dumps(room)},\n' + text[m.start():]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    ap.add_argument("--check", action="store_true", help="report only; exit 1 if a placeable card lacks room")
    ap.add_argument("--list", action="store_true", help="list every card that fails the schema")
    a = ap.parse_args()
    write = not (a.dry_run or a.check)

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    room_prop = (schema.get("properties") or {}).get("room") or {}
    room_ids = [r for r in room_prop.get("enum", []) if r]
    if not room_ids:
        sys.exit("data/product-card.schema.json has no room enum yet (schema 1.1). Nothing done.")
    slots = load_slots(room_ids)

    added, already, unplaced, conflicts, errors = [], [], [], [], []
    by_room = Counter()
    for path in sorted(PRODUCTS.rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        card = json.loads(text)
        room, why = placement(path, card, room_ids, slots)
        have = card.get("room")
        if room is None:
            if have is None:
                unplaced.append((rel(path), why))
            else:
                already.append(rel(path))
            continue
        by_room[room] += 1
        if have == room:
            already.append(rel(path))
            continue
        if have is not None:
            conflicts.append((rel(path), f"card room {json.dumps(have)}, folder room '{room}'"))
            continue
        try:
            new = add_room(text, room)
        except ValueError as e:
            errors.append((rel(path), str(e)))
            continue
        if json.loads(new) != {**card, "room": room}:  # nothing but the one field may change
            errors.append((rel(path), "insertion changed more than room"))
            continue
        added.append(rel(path))
        if write:
            path.write_text(new, encoding="utf-8")

    verb = "added" if write else "would add"
    print(f"cards: {len(added) + len(already) + len(unplaced) + len(conflicts) + len(errors)}")
    print(f"  room {verb}: {len(added)}  ·  already set: {len(already)}")
    print("  placed by room: " + ", ".join(f"{r} {by_room[r]}" for r in room_ids))
    for title, rows in (("not placed (left alone)", unplaced), ("conflicts (left alone)", conflicts), ("errors", errors)):
        if rows:
            print(f"  {title}: {len(rows)}")
            for p, why in rows:
                print(f"    {p}: {why}")

    # validate every card (as written, or as it would be written)
    sys.path.insert(0, str(ROOT / "studio"))
    from apply_edits import validate  # noqa: E402  (stdlib validator for this schema)
    added_set = set(added)
    fails: dict[str, list[str]] = {}
    for path in sorted(PRODUCTS.rglob("*.json")):
        card = json.loads(path.read_text(encoding="utf-8"))
        if not write and rel(path) in added_set:
            room, _ = placement(path, card, room_ids, slots)
            card = {**card, "room": room}
        errs = validate(card, schema)
        if errs:
            fails[rel(path)] = errs
    total = len(added) + len(already) + len(unplaced) + len(conflicts) + len(errors)
    print(f"schema: {total - len(fails)} pass, {len(fails)} fail")
    def cause(e: str) -> str:
        m = re.match(r"^\$(?:\.(\S+))?: missing required '([^']+)'", e)
        if m:
            return ".".join(x for x in (m.group(1), m.group(2)) if x) + " missing"
        return e.split(":")[0].removeprefix("$.")

    causes = defaultdict(list)
    for p, errs in fails.items():
        causes[" + ".join(sorted({cause(e) for e in errs}))].append(p)
    for sig, ps in sorted(causes.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(ps):3d}  {sig}")
        if a.list:
            for p in ps:
                print(f"         {p}")
    if a.check and added:
        return 1
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
