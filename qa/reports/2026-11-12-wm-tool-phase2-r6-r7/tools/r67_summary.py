#!/usr/bin/env python3
"""qa-agent 2026-11-12: the report's JSON (qa/reports/2026-11-12-wm-tool-phase2-r6-r7.json) from data/*.json; the verdicts are QA's."""
import json
import os

OUT = "/home/user/homedesign-app/qa/reports/2026-11-12-wm-tool-phase2-r6-r7"
D = lambda n: json.load(open(os.path.join(OUT, "data", n)))  # noqa: E731
i6, i7 = D("integrity-r6.json"), D("integrity-r7.json")


def integ(d):
    return dict(base_same_bytes_as_approved=d["base_same_bytes_as_approved"],
                recomposite_defaults={s: {p: dict(p999=v["p999_region"], max=v["max"], px_gt2=v["px_gt2"], px_gt6=v["px_gt6"]) for p, v in x.items()}
                                      for s, x in d["recomposite_defaults"].items()},
                recomposite_pass=d["recomposite_defaults_pass"], swap_toggles=len(d["swap_diff_defaults"]),
                swap_changed_outside_region_total=d["swap_diff_defaults_outside_total"],
                region_px_beyond_60px_of_alpha_box={k: v for k, v in d["region_px_beyond_60px_of_alpha_box"].items() if v},
                scenes_vs_prev=d["scenes_vs_prev"], layer_change_detail=d["layer_change_detail"],
                disjoint=d["disjoint"], variants_alone_pass=d["variants_alone_pass"],
                variants_alone_worst={k: dict(max=max(x["max"] for x in v.values() if isinstance(x, dict)),
                                              p999=max(x["p999_region"] for x in v.values() if isinstance(x, dict)),
                                              swap_outside_two_regions=max(v[f"{s} P1"]["swap_vs_default_outside_two_regions"] for s in "ABC"),
                                              vs_empty_outside=max(v[f"{s} P1"]["variant_vs_empty_outside_variant_region"] for s in "ABC"),
                                              truth_B_outside_two_regions_px=v["truth_B_differs_from_default_outside_two_regions"])
                                      for k, v in d["variants_alone"].items()},
                full_cross={k: d["full_cross"][k] for k in ("slots", "n_combos", "n_composites", "union_px", "worst", "all_pass", "independence_all_zero", "fails")},
                full_cross_1d_consistency_max=d["full_cross_1d_consistency_max"])


res = dict(
    id="qa-2026-11-12-wm-tool-phase2-r6-r7", author="qa-agent", date="2026-11-12", tokens=0,
    scope="warm-modern living-room tool, phase 2: R6 (0-token code fixes) and R7 (planter k, sold curtain lengths, table group WM-T2, pass 6', curtain 3 from 7')",
    inputs=dict(manifests=["layers/manifest-r6.json", "layers/manifest-r7.json"],
                briefs=["briefs/render-wm-tool-r6-codefix-2026-11-12.md", "briefs/render-wm-tool-r7-2026-11-12.md"],
                decisions=["docs/proposals/owner-answers-applied-2026-11-12.md", "docs/proposals/wm-phase2-r5-eye-2026-11-11.md"],
                previous_qa="qa/reports/2026-11-11-wm-tool-phase2-r5.md"),
    integrity=dict(r6=integ(i6), r7=integ(i7)),
    grade=D("grade.json"), lock={k: dict(pass_all_samples=v["pass_all_samples"], worst_p90=v["worst_p90_all"]) for k, v in D("lock.json").items()
                                 if isinstance(v, dict) and "pass_all_samples" in v},
    shadow=D("shadow.json"), curtains=D("curtains.json"), planter=D("planter.json"), table=D("table.json"), r6_checks=D("r6-checks.json"),
    halo=D("halo.json"), hem_halo=D("hem-halo.json"), combos=D("combos.json"))
res["findings"] = json.load(open(os.path.join(OUT, "data/findings.json")))
json.dump(res, open(OUT + ".json", "w"), indent=1, default=float, ensure_ascii=False)
print("written", OUT + ".json")
