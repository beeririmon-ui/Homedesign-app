"""qa-agent 2026-11-07: register v6 (qa/reports/ged-register-2026-11-07-r6.json), superseding v5: units_in_frame on every final_test frame
that shows more than one physical unit of a product, read against how the card sells it (a single SKU, a set SKU, or a per-unit price
with the set made of several units):
- the count in the frame: QA's eye on the full frame (and the story points);
- the sale unit: the card (data/products/**/<id>.json: name, option labels, notes) and the site's pack (site/.generated/catalog.story.full.json
  'pack.set_qty', from data/economics/products.json 'price_for_qty').
units_in_frame counts what the look puts in the cart: the purchasable unit (a set SKU, or a site pack, counts once).
Usage: python3 -I build_register_v6.py"""
import copy
import json
import os

REPO = "/home/user/homedesign-app"
V5P = "qa/reports/ged-register-2026-11-07-r5.json"
reg = copy.deepcopy(json.load(open(os.path.join(REPO, V5P))))
reg.update(version=6, supersedes=V5P, id="ged-register-2026-11-07-r6", date="2026-11-07", by="qa-agent")
reg.pop("changes_from_v4", None)


def row(frame, card_id, option="any"):
    for r in reg["frames"][frame]["rows"]:
        if r["card_id"] == card_id and (option == "any" or r.get("option") == option):
            return r
    raise KeyError((frame, card_id, option))


def units(frame, card_id, n, sale_unit, seen, option="any"):
    r = row(frame, card_id, option)
    r["units_in_frame"] = n
    r["sale_unit"] = sale_unit
    r["units_note"] = f"register v6: {seen}; sold as {sale_unit}, so the look adds {n}"


SCONCE_BOHO = "single lamps (one SKU 'Lampshade Color: A', package 15 x 15 x 15 cm, 0.6 kg: one lamp; no pair in the listing)"
for fr in ("boho-A-fin7", "boho-A-fin6"):
    units(fr, "wall-sconce-aliexpress-rattan-bamboo-wall-lamp-671943", 2, SCONCE_BOHO, "two bamboo ball sconces, either side of the triptych")
units("mediterranean-A-ed7", "cushions-cj-washed-cotton-frayed", 3, "single covers (the card: 'cover only', price per cover, no site pack)",
      "three white back cushions on the bench (left, middle, right), the story point says 'שלוש כריות גב לבנות'", option={"other": "white"})
units("mediterranean-A-ed7", "candle-holders-cj-travertine-pedestal", 1, "a set of 2 (the site's pack set_qty 2; the card: 'set of 2')", "the pedestal pair on the table")
units("nordic-A-ed4", "candle-holders-cj-travertine-pedestal", 1, "a set of 2 (the site's pack set_qty 2; the card: 'set of 2')", "the pedestal pair on the table")
units("nordic-A-ed4", "accent-sconces-cj-travertine-block-updown-8x16", 2,
      "single lamps (the card: '₪299 per unit', 'pair (2 units, ₪598)'; no site pack)", "two travertine blocks, either side of the triptych")
units("nordic-A-ed4", "framed-art-aliexpress-minimal-geometric-triptych-prints", 1, "a set of 3 (the site's pack set_qty 3)", "the three prints of the triptych")
row("nordic-A-ed4", "framed-art-aliexpress-minimal-geometric-triptych-prints")["units_note"] += (
    ". The set must be the three different prints (options 1, 2, 3), not three of print 1 (QA's site S4 finding, with frontend-dev)")
units("modern-country-A-fix4", "cushions-aliexpress-farmhouse-floral-pillow-covers-166217", 1,
      "a set of 2 covers in one SKU (the listing: 'Pillow Covers Set of 2')", "exactly the two block-print cushions")
row("modern-country-A-fix4", "cushions-aliexpress-farmhouse-floral-pillow-covers-166217")["units_note"] += (
    ". The site has no pack for it (data/economics/products.json price_for_qty 1): the product page should say 'a set of 2' (sourcing-agent / frontend-dev)")
units("modern-country-A-fix4", "curtains-aliexpress-linen-blend-s-fold-180502", 2, "single panels (the size labels '1PC W..'; the card: 'sold as a pair (qty 2)')",
      "two panels, either side of the window", option={"style": "pull-pleated-tape"})
units("nordic-B-fin", "curtains-aliexpress-linen-blend-s-fold-180502", 2, "single panels (the size labels '1PC W..'; the card: 'sold as a pair (qty 2)')",
      "two panels, either side of the window (the row's dot is closeup_only)")
po = row("mediterranean-A-ed7", "framed-art-aliexpress-mediterranean-wabi-sabi-poster-802890")
po["designs_in_frame"] = 3
po["units_note"] = ("register v6: three different prints of this card (olive tree; vases with an arch; arched stairs with a palm), each its own option "
                    "(colour 01-08, sold one print at a time, 'No Frame'). No units_in_frame on purpose: on this row (no option) it would put three of one "
                    "design in the cart. Open: the three designs' option ids (sourcing-agent, from the listing's option photos), then one row and one story "
                    "point option per design, 1 unit each")
reg["frames"]["mediterranean-A-ed7"].setdefault("open", [])
reg["frames"]["mediterranean-A-ed7"]["open"] = list(reg["frames"]["mediterranean-A-ed7"].get("open") or []) + [
    "the poster triptych: the option ids of its three designs (sourcing-agent), then a row per design (QA) and the story point per design (frontend-dev)"]
reg["schema"]["units_in_frame"] = ("optional on a row: what the look puts in the cart for this product and option when the frame shows more than one "
                                   "physical unit, counted in purchasable units: a set SKU or a site pack counts once (sale_unit says which, units_note "
                                   "what the frame shows). 1-12, read by site/tools/lib/qa-frames.ts")
reg["schema"]["designs_in_frame"] = "optional: a card shown in several different options (e.g. prints of one listing); those need one row per option, not units"
reg["units_audit_v6"] = {
    "scope": "every final_test frame of v5: nordic-A-ed4, nordic-B-fin, modern-country-A-fix4, mediterranean-A-ed7, boho-A-fin7 (and boho-A-fin6 for the same sconces)",
    "set": {"boho-A-fin7 / fin6 sconces": 2, "mediterranean-A-ed7 white cushions": 3, "nordic-A-ed4 accent sconces": 2, "modern-country-A-fix4 curtains": 2,
            "nordic-B-fin curtains": 2},
    "one_set_shown": {"mediterranean-A-ed7 candle holders": "set of 2", "nordic-A-ed4 candle holders": "set of 2", "nordic-A-ed4 triptych": "set of 3",
                      "modern-country-A-fix4 floral covers": "set of 2 in one SKU (no site pack yet)"},
    "unchanged": {"boho-A-fin7 rust cushions": 2},
    "open": ["mediterranean-A-ed7 posters: three designs (options), not units"],
    "not_checked": "frames that are not final_test (warm-modern-A-ed7, japandi-A-ed5): they get the same check when they reach final_test; already visible there: "
                   "warm-modern ed7's two accent sconces and pedestal pair, japandi's three prints of one series and its iron candle-plate set",
}
reg["changes_from_v5"] = ["units_in_frame on the final_test frames (units_audit_v6)", "mediterranean-A-ed7: the poster triptych needs a row per design (open)"]
json.dump(reg, open(os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r6.json"), "w"), ensure_ascii=False, indent=1)
S, Dt = {"not_yet", "almost", "final_test", "approved_for_site"}, {"yes", "no", "closeup_only"}
bad = []
for part in ("frames", "closeups"):
    for k, f in (reg.get(part) or {}).items():
        if f.get("state") not in S:
            bad.append(f"{part}.{k}.state")
        if not isinstance(f.get("rows"), list) or (f["state"] != "not_yet" and not f["rows"]):
            bad.append(f"{part}.{k}.rows")
        for i, r in enumerate(f.get("rows") or []):
            u = r.get("units_in_frame")
            if not isinstance(r.get("card_id"), str) or not isinstance(r.get("verdict"), str) or r.get("dot") not in Dt or (u is not None and not (isinstance(u, int) and 1 <= u <= 12)):
                bad.append(f"{part}.{k}.rows[{i}]")
print("version", reg["version"], "bad", bad)
for k, f in reg["frames"].items():
    us = [(r["card_id"][:40], r["units_in_frame"]) for r in f["rows"] if "units_in_frame" in r]
    if us:
        print(k, f["state"], us)
