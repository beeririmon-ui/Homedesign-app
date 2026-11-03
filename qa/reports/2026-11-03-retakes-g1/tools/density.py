"""
G1.6 density on the bath retakes (masters B1 r3, B2 r3) and, for the record, on the two poses:
  (a) the test rule of studio rules 2.11 (V7Q5 b): a test frame passes when every slot that has an approved product is filled;
      the empty slots are listed as sourcing tasks. "Approved product" = a card the product check of 2026-11-02 lists as usable /
      usable-with-note / replace-with-card for that frame, or one of the two designer-6.5 cards the user admitted for the test
      (V7Q3); the slots without any such card are the sourcing tasks (sourcing-agent 2026-11-03: 0 cards, no API keys).
  (b) the written rule of today on the clay boxes (D1 / D1B: >= 50 % visible, >= 0.5 % of the frame, fixed-product counts, a
      set once; 14 / 11 / 5; 4 of 5 categories), as in qa/reports/2026-11-02-v7-g1 section 7.
  (c) an estimate under the adopted rule V7Q6 (studio rules 2.13, docs/proposals/density-count-rule-2026-11-03.md), from the
      same clay boxes: readability (0.5 %, or 0.15 % and the visible silhouette's larger dimension >= 6 % of the frame height,
      at >= 50 % visible); a group of 3 or 5 on one surface counts once when its uncounted members' union is >= 0.5 %; a dressed
      fixed-product piece is measured with its textile; the planned front layer counts from 25 % visible and 1 % of the frame;
      room minimum (11 + 4 = 15 unique slots over B1 + B2) and half the minimum (6) for the second frame. The clay selfcheck has
      no silhouette index for the render yet, so the silhouette height is the box height and groups are read from the slots
      file (`placement_detail`); the implementation in the clay selfcheck is a separate task (section 8 of the report).
Writes data/density.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

PC = json.load(open(os.path.join(C.REPO, "docs/render-products-check-2026-11-02.json")))
SLOTS = {r: json.load(open(os.path.join(C.REPO, f"data/slots/{f}.json"))) for r, f in (("bath", "bath"), ("work", "work"), ("kids", "kids"))}
for _r, _s in SLOTS.items():                      # work.json / kids.json keep the slots as a list of records with an id
    if isinstance(_s["slots"], list):
        _s["slots"] = {x["id"]: x for x in _s["slots"]}
FRAME_PX = 3840 * 2160
MIN = {"B1": 11, "B2": 11}
TEST_ONLY = {"floor-planter": "floor-planter-aliexpress-seagrass-straight-planter-basket-30 (designer 6.5, test only, V7Q3)",
             "toilet-brush": "toilet-brush-aliexpress-matte-black-steel-cylinder-245996 (designer 6.5, test only, V7Q3)"}
CATS4 = {"textile", "lighting", "ceramics-tableware", "storage-function", "art-decor-toys"}
CATEGORY = {}
for room, s in SLOTS.items():
    for sid, sl in s["slots"].items():
        CATEGORY[(room, sid)] = sl.get("category", "other")
PLACEMENT = {(room, sid): (sl.get("placement"), sl.get("placement_detail")) for room, s in SLOTS.items() for sid, sl in s["slots"].items()}
FIXED = {"B1": ["bath vanity 110 (fixed)"], "B2": ["bath vanity 110 (fixed)"]}


def approved_cards(frame):
    """slot -> card id with an approved product in this frame, from the product check (+ the two test-only cards)."""
    out = {}
    fr = next((x for x in PC["frames"] if x["frame"] == frame), None)
    if fr:
        for r in fr["rows"]:
            slot = r["slot"].split(" ")[0]
            rep = r.get("replacement")
            if r["verdict"] in ("usable", "usable-with-note"):
                out[slot] = r["card_id"]
            elif r["verdict"] == "replace" and isinstance(rep, dict) and rep.get("kind") == "card":
                out[slot] = rep["card_id"]
    return out


def run_master(sid):
    d = C.load(sid, raw=False)
    frame = d["frame"]
    sc = d["sc"]
    Wc, Hc = sc["resolution"]
    iv = sc.get("items_visible", {})
    room_slots = SLOTS["bath"]["slots"]
    plan = C.PLAN3["frames"][frame]
    placeholders = set(plan["placeholders"])
    approved = approved_cards(frame)
    for k, v in TEST_ONLY.items():
        if k in placeholders:
            approved[k] = v
    # (a) the test rule
    rows_a = []
    for slot, sl in room_slots.items():
        if frame not in sl.get("frames", []):
            continue
        has = slot in approved
        filled = slot in placeholders or (sl.get("kind") == "fixed-product")
        rows_a.append(dict(slot=slot, category=sl.get("category"), fixed_product=sl.get("kind") == "fixed-product", approved_card=approved.get(slot), filled=filled,
                           status=("filled" if filled else ("EMPTY with an approved card" if has else "empty: sourcing task"))))
    unfilled_with_card = [r["slot"] for r in rows_a if r["approved_card"] and not r["filled"]]
    sourcing = [r["slot"] for r in rows_a if not r["approved_card"] and not r["filled"]]
    # (b) today's rule and (c) V7Q6 on the clay boxes
    rows = []
    for nm, b in sc.get("boxes", {}).items():
        if b["kind"] not in ("proxy", "proxy-transit") or not nm.startswith("bath/"):
            continue
        slot = nm.split("/", 1)[1]
        area = b["px"] / FRAME_PX
        vis = iv.get(nm, {}).get("visible_pct")
        vis_ok = True if vis is None else vis >= 50.0
        u0, u1, v0, v1 = b["box"]
        hgt = (v1 - v0) * Hc / 2160            # the box height as a fraction of the 16:9 frame height
        wid = (u1 - u0) * Wc / 3840
        dim = max(hgt, wid)
        today = bool(vis_ok and area >= 0.005)
        read1 = bool(vis_ok and (area >= 0.005 or (area >= 0.0015 and dim >= 0.06)))
        rows.append(dict(slot=slot, category=CATEGORY.get(("bath", slot), "other"), area_pct=round(100 * area, 2), visible_pct=vis, visibility_assumed=vis is None,
                         larger_dim_pct_of_frame=round(100 * dim, 1), placement=PLACEMENT.get(("bath", slot)), counted_today=today, counted_v7q6_rule1=read1,
                         why_not_today=None if today else ("visible < 50 %" if not vis_ok else "area < 0.5 %"),
                         why_not_v7q6=None if read1 else ("visible < 50 %" if not vis_ok else ("area < 0.15 %" if area < 0.0015 else "larger dimension < 6 % of the height"))))
    # V7Q6 rule 2: groups of 3 or 5 on one surface among the uncounted members
    groups = {}
    for r in rows:
        if r["counted_v7q6_rule1"]:
            continue
        pd = (r["placement"] or (None, None))[1]
        if pd:
            groups.setdefault(pd, []).append(r)
    group_rows = []
    for surface, members in groups.items():
        # the surface group = all slots on this surface in the frame (counted or not); the rule needs a designed group of 3 or 5
        allm = [r for r in rows if (r["placement"] or (None, None))[1] == surface]
        union = sum(r["area_pct"] for r in members) / 100
        ok = len(allm) in (3, 5) and union >= 0.005
        group_rows.append(dict(surface=surface, members_uncounted=[r["slot"] for r in members], members_all=[r["slot"] for r in allm], union_area_pct=round(100 * union, 2),
                               counts_as_one=bool(ok), why_not=None if ok else (f"{len(allm)} on the surface, not 3 or 5" if len(allm) not in (3, 5) else "union < 0.5 %")))
    fixed = []
    for nm in FIXED[frame]:
        b = sc["boxes"].get(nm)
        area = b["px"] / FRAME_PX
        vis = iv.get(nm, {}).get("visible_pct")
        vis_ok = (True if vis is None else vis >= 50.0)
        fixed.append(dict(name=nm, area_pct=round(100 * area, 2), visible_pct=vis, counted_today=bool(vis_ok and area >= 0.005), counted_v7q6=bool(vis_ok and area >= 0.005),
                          note="B1: only the vanity's top corner is in frame (8.7 % visible): not counted in either rule" if frame == "B1" else None))
    n_today = sum(r["counted_today"] for r in rows) + sum(f["counted_today"] for f in fixed)
    n_v7q6 = sum(r["counted_v7q6_rule1"] for r in rows) + sum(g["counts_as_one"] for g in group_rows) + sum(f["counted_v7q6"] for f in fixed)
    cats_today = {r["category"] for r in rows if r["counted_today"]} | ({"storage-function"} if any(f["counted_today"] for f in fixed) else set())
    cats_v7q6 = {r["category"] for r in rows if r["counted_v7q6_rule1"]} | ({"storage-function"} if any(f["counted_v7q6"] for f in fixed) else set())
    v7q6_min = MIN[frame] if frame == "B1" else 6
    rec = dict(frame=sid, minimum_today=MIN[frame], minimum_v7q6=v7q6_min, v7q6_frame_kind="arrival frame (11)" if frame == "B1" else "second frame of the room: half the minimum (6); the room (B1 + B2) 15 unique",
               test_rule=dict(rule="studio rules 2.11 (V7Q5 b): every slot with an approved product filled; empty slots = sourcing tasks",
                              slots_in_frame=len(rows_a), filled=[r["slot"] for r in rows_a if r["filled"]], unfilled_with_approved_card=unfilled_with_card, sourcing_tasks=sourcing,
                              passed=bool(not unfilled_with_card), rows=rows_a),
               today_rule=dict(counted=n_today, minimum=MIN[frame], categories=sorted(cats_today), categories_of_5=len(cats_today & CATS4), passed=bool(n_today >= MIN[frame] and len(cats_today & CATS4) >= 4)),
               v7q6_estimate=dict(counted=n_v7q6, minimum=v7q6_min, categories=sorted(cats_v7q6), categories_of_5=len(cats_v7q6 & CATS4), passed_frame=bool(n_v7q6 >= v7q6_min and len(cats_v7q6 & CATS4) >= 4),
                                  groups=group_rows, counted_slots=[r["slot"] for r in rows if r["counted_v7q6_rule1"]] + [f["name"] for f in fixed if f["counted_v7q6"]],
                                  note="estimate from clay boxes (box height as the silhouette height); the selfcheck has no silhouette index yet"),
               rows=rows, fixed=fixed)
    print(f"{sid}: test rule {'pass' if rec['test_rule']['passed'] else 'FAIL'} (filled {len(rec['test_rule']['filled'])}, unfilled-with-card {unfilled_with_card}, sourcing {sourcing}) | "
          f"today {n_today}/{MIN[frame]} cats {sorted(cats_today)} | V7Q6 est {n_v7q6}/{v7q6_min} cats {sorted(cats_v7q6)} counted {rec['v7q6_estimate']['counted_slots']} groups {[(g['surface'], g['counts_as_one'], g['why_not']) for g in group_rows]}")
    return rec


def run_pose(sid):
    d = C.load(sid, raw=False)
    frame, base = d["frame"], d["base"]
    room = {"work": "work", "girl": "kids"}[d["room"]]
    pl = C.PLAN["poses"][frame]
    placeholders = set(pl["placeholders"])
    approved = approved_cards(base)
    room_slots = SLOTS[room]["slots"]
    rows = []
    for slot, sl in room_slots.items():
        if base not in sl.get("frames", []):
            continue
        if room == "kids" and sl.get("rooms") and "girl" not in sl["rooms"]:
            continue
        filled = slot in placeholders or sl.get("kind") == "fixed-product"
        rows.append(dict(slot=slot, approved_card=approved.get(slot), filled_in_pose_plan=filled, in_frame_by_eye=None))
    rec = dict(frame=sid, base=base, note="a pose shows a subset of the master's slots; G1.6 (density) is judged on the master, the pose is listed for the record",
               filled=[r["slot"] for r in rows if r["filled_in_pose_plan"]], unfilled_with_approved_card=[r["slot"] for r in rows if r["approved_card"] and not r["filled_in_pose_plan"]],
               sourcing_tasks=[r["slot"] for r in rows if not r["approved_card"] and not r["filled_in_pose_plan"]], rows=rows)
    print(f"{sid}: pose of {base}: filled {rec['filled']} | unfilled with card {rec['unfilled_with_approved_card']} | sourcing {rec['sourcing_tasks']}")
    return rec


if __name__ == "__main__":
    out = {"B1 r3": run_master("B1 r3"), "B2 r3": run_master("B2 r3"), "W0-in r2": run_pose("W0-in r2"), "K-girl-0 r2": run_pose("K-girl-0 r2")}
    b1, b2 = out["B1 r3"]["v7q6_estimate"]["counted_slots"], out["B2 r3"]["v7q6_estimate"]["counted_slots"]
    uniq = sorted(set(b1) | set(b2))
    out["bath room V7Q6"] = dict(unique_slots=uniq, count=len(uniq), minimum=15, passed=bool(len(uniq) >= 15))
    print("bath room V7Q6 unique:", len(uniq), "/ 15", uniq)
    json.dump(out, open(os.path.join(C.OUT, "data", "density.json"), "w"), indent=1, ensure_ascii=False)
