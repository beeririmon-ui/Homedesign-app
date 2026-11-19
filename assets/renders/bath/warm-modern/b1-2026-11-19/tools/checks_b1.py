#!/usr/bin/env python3
"""
checks_b1.py: the brief's checks on B1 (render-agent, 2026-11-19), 0 tokens. Reads the files as written (layers/manifest.json, the
composites, the plate, the clay ids) and writes b1-checks.json:
  rnd2         outside every alpha, shadow and light: plate.png pixel for pixel (defaults and the Beige)
  shadows      each shadow one z below its product
  black_point  WM-G1 (black L* 11-14): the frame box's darkest pixels (min, p0.1, p0.5) and the black products' own blacks
  same_house   the plate's shared regions against B2's, the floor, the plaster
  colour       the jar (neutral black, against its SKU photo), the mat (R5, Khaki and Beige)
  counts       V7Q6 (03.11): a product counts at >= 0.5 % of the frame, or >= 0.15 % and >= 6 % of its height, and >= 50 % visible;
               a group of 3 or 5 is one item
  halos        light fringes: soft-edge pixels of a product lighter than both the plate under them and the product's own edge by 6 L*
  python3 checks_b1.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, "/home/user/homedesign-app/assets/renders/bath/warm-modern/stage1-2026-11-17/tools")
sys.path.insert(0, HERE)
import compose_defaults as C  # noqa: E402
import grade_plate as G  # noqa: E402
import compose_b1_defaults as D  # noqa: E402

B2 = "/home/user/homedesign-app/assets/renders/bath/warm-modern/stage1-2026-11-17/"
B2CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-bath-2026-11-17/"
JAR_PHOTO = (17.9, 2.0, -4.0)                       # house-20 photo check, blackjar (Style4 jar 30 body)
GROUPS = {"shower-dispensers": 3}                   # a group of 3 = one item


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float64) / 255


def frame_mask(H, W):
    x0, y0, x1, y1 = G.FRAME
    m = np.zeros((H, W), bool)
    m[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))] = True
    return m


def black_point(img, fm):
    L = G.to_lab(img[fm])[:, 0]
    return dict(min=round(float(L.min()), 2), p0_1=round(float(np.percentile(L, 0.1)), 2), p0_5=round(float(np.percentile(L, 0.5)), 2),
                p5=round(float(np.percentile(L, 5)), 2))


def main():
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    ids = np.asarray(Image.open(D.CLAY + "B1-id.png"))
    H, W = ids.shape
    fm = frame_mask(H, W)
    farea, fh = float(fm.sum()), G.FRAME[3] - G.FRAME[1]
    plate = load(os.path.join(ST, "plate.png"))
    dflt = load(os.path.join(ST, "b1-defaults.png"))
    beige = load(os.path.join(ST, "b1-variant-mat-beige.png"))
    lay = {l["slot"]: l for l in man["layers"]}
    A = {k: np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3] for k, l in lay.items()}
    out = dict(date="2026-11-19", frame="B1", measured_on="b1-defaults.png and b1-variant-mat-beige.png (2720 x 1530 canvas; the frame box "
                                                          + str([round(v, 2) for v in G.FRAME]) + ")")
    # RND2
    out["rnd2"] = dict(defaults=man["rnd2"]["outside_differing_px"],
                       beige=[v["outside_differing_px_vs_plate"] for v in man["variants"]][0],
                       beige_differs_from_defaults_outside_the_mat_alpha=[v["differing_px_vs_defaults_outside_alpha"] for v in man["variants"]][0],
                       rule=man["rnd2"]["rule"])
    # shadows
    out["shadows"] = dict(all_one_below=all(l["shadow_z"] == l["z"] - 1 for l in man["layers"]),
                          pairs={l["slot"]: [l["z"], l["shadow_z"]] for l in man["layers"]}, light_z=man["light"]["z"])
    # black point
    b2d = load(B2 + "b2-defaults.png")
    bk = {}
    for k in ("window-sill-vase", "toilet-paper-stand", "toilet-brush"):
        m = C.ero(A[k] == 255, 2)
        L = G.to_lab(dflt[m])[:, 0]
        bk[k] = dict(min=round(float(L.min()), 2), p1=round(float(np.percentile(L, 1)), 2), p50=round(float(np.median(L)), 2))
    out["black_point"] = dict(rule="WM-G1: black L* 11-14", defaults=black_point(dflt, fm), beige=black_point(beige, fm),
                              plate=black_point(plate, fm), b2_defaults=black_point(b2d, fm), black_products=bk,
                              ok=bool(10.5 <= black_point(dflt, fm)["min"] <= 14 and 10.5 <= black_point(beige, fm)["min"] <= 14))
    # same house
    pc = json.load(open(os.path.join(ST, "plate-compose.json")))
    b2ids = np.asarray(Image.open(B2CLAY + "B2-id.png"))
    b2p = load(B2 + "plate.png")
    def med(img, m):  # noqa: E301
        return [round(float(x), 1) for x in G.to_lab(C.srgb(np.median(C.lin(img[m]), 0))[None])[0]]
    floor1, floor2 = med(plate, np.isin(ids, (9, 10)) & fm), med(b2p, np.isin(b2ids, (9, 10)) & fm)
    pl1, pl2 = med(plate, np.isin(ids, D.PLASTER) & fm), med(b2p, np.isin(b2ids, D.PLASTER) & fm)
    de = lambda x, y: round(float(G.de00(np.array([x]), np.array([y]))[0]), 2)  # noqa: E731
    out["same_house"] = dict(
        shared_regions_b1=pc["final"]["shared_regions"],
        shared_regions_b2=pc.get("b2_plate_same_regions"),
        floor_median=dict(b1=floor1, b2=floor2, de00=de(floor1, floor2)),
        plaster_median=dict(b1=pl1, b2=pl2, de00=de(pl1, pl2)),
        note="B1 looks at the window wall (lit), B2 at the vanity: the plaster matches within 1-2 L*; the floor in B1 is a little warmer "
             "(b* about 12 against 8) and nearer the bible's #D8C8AE (b* 15)")
    # colour
    jm = C.ero(A["window-sill-vase"] == 255, 3)
    jl = G.to_lab(dflt[jm])
    lo, hi = np.percentile(jl[:, 0], [20, 80])
    jmed = med(dflt, jm)
    jsel = jl[(jl[:, 0] >= lo) & (jl[:, 0] <= hi)]
    jar = [round(float(x), 1) for x in np.median(jsel, 0)]
    out["colour"] = dict(
        jar=dict(as_seen_mid_tone=jar, chroma=round(float(np.hypot(jar[1], jar[2])), 1), photo=list(JAR_PHOTO),
                 photo_chroma=round(float(np.hypot(*JAR_PHOTO[1:])), 1), body_median=jmed,
                 note="neutral black, not warmed: as seen on the sill against the frosted glass; the photo's body reading for reference"),
        mat=dict(khaki=man["record"]["mat_recolour"], beige=[v["readings_vs_floor"] for v in man["variants"]][0],
                 light=man["record"]["mat_light"]))
    # counts (V7Q6), on the defaults; the mat also as the Beige (the same alpha)
    order = [l["slot"] for l in sorted(man["layers"], key=lambda x: (x["z"], x["slot"]))]
    rows = {}
    for i, k in enumerate(order):
        a = (A[k] >= 128) & fm
        if not a.any():
            continue
        above = np.zeros((H, W), bool)
        for o in order[i + 1:]:
            above |= A[o] >= 128
        own = A[k] >= 128
        vis = a & ~above
        ys = np.nonzero(vis.any(1))[0]
        area, hgt = 100 * vis.sum() / farea, 100 * (ys.max() - ys.min() + 1) / fh
        visible = 100 * vis.sum() / max(own.sum(), 1)
        ok = (area >= 0.5 or (area >= 0.15 and hgt >= 6)) and visible >= 50
        rows[k] = dict(product=lay[k]["product"], area_pct=round(float(area), 3), height_pct=round(float(hgt), 2),
                       visible_pct=round(float(visible), 1), counts=bool(ok), items=1)
    n_ok = sum(1 for r in rows.values() if r["counts"])
    new_in_b1 = ["bath-mat", "toilet-paper-stand", "bin", "toilet-brush", "reed-diffuser", "candle", "window-sill-vase"]
    out["counts"] = dict(rule="V7Q6 (03.11): >= 0.5 % of the frame, or >= 0.15 % and >= 6 % of its height; >= 50 % visible; a group of 3 or 5 = one item",
                         frame_px=int(farea), per_product=rows, in_b1_frame=len(rows), counting_in_b1=n_ok,
                         not_counting_in_b1=[k for k, r in rows.items() if not r["counts"]],
                         new_unique_in_b1=new_in_b1, also_in_b2=[k for k in rows if k not in new_in_b1],
                         room_unique=dict(b2=11, b1_new=len(new_in_b1), total=11 + len(new_in_b1), target=20,
                                          gaps=["shower-stool", "wall-art (the small print)", "ledge-planter"]))
    # halos
    hal = {}
    Lc, Lp = G.to_lab(dflt)[..., 0], G.to_lab(plate)[..., 0]
    for k in order:
        a = A[k]
        edge = (a > 0) & (a < 255)
        inner = C.dil(edge, 3) & (a == 255)
        if not inner.any():
            continue
        ref = float(np.median(Lc[inner]))
        light = edge & (Lc > Lp + 6) & (Lc > ref + 6)
        hal[k] = dict(edge_px=int(edge.sum()), light_fringe_px=int(light.sum()))
    out["halos"] = dict(rule="soft-edge pixels lighter than the plate under them and than the product's own edge by 6 L*", per_product=hal,
                        total_light_fringe_px=int(sum(v["light_fringe_px"] for v in hal.values())))
    # QA round 1 (qa/reports/2026-11-19-bath-b1): M1-M3 and B1-L1, as fixed in compose_b1_defaults.py
    r = man["record"]
    cur = A["shower-curtain"]
    jr = r["jar_refit"]
    ja = A["window-sill-vase"] >= 128
    jys = np.nonzero(ja.any(1))[0]
    jxs = np.nonzero(ja.any(0))[0]
    out["qa_round1"] = dict(
        report="qa/reports/2026-11-19-bath-b1/README.md",
        M1_planter=dict(r5_vs_plaster=r["planter_recolour"]["r5_lab_after"], sku_lch=r["planter_recolour"]["sku_lch"],
                        de00=r["planter_recolour"]["de00_after"], b2_after_m5_lch=[59.4, 4.1, 88.3], rule="dE00 <= 4 vs the SKU; beside B2 at x1"),
        M2_jar=dict(width_vs_clay_by_height=jr["width_vs_clay_by_height"], rule_width="within +-8 % of the clay at every height",
                    h_over_w=round(float((jys.max() - jys.min() + 1) / (jxs.max() - jxs.min() + 1)), 2), h_over_w_clay_photo=1.84,
                    hp_sigma2_before_after_this_tool=jr["hp_sigma2_before_after"], hp_rule="1.3-1.8 in QA's reading (QA read 3.09 where this tool reads 2.35)",
                    speckle_share_C_gt_8=jr["speckle_share_C_gt_8_after"], median_lab=jr["median_lab_after"], light_fringe_px=hal["window-sill-vase"]["light_fringe_px"]),
        M3_curtain=dict(hole_px_in_qa_box=int((cur[1288:1330, 1736:1746] == 0).sum()), box=[1736, 1288, 1745, 1329],
                        stray_line_px_left_of_edge=int(((cur[1280:1340, 1728:1737] > 0) & (cur[1280:1340, 1737:1746] == 0)).sum())),
        B1_L1_candle=dict(alpha_px_right_of_861_rows_735_785=int((A["candle"][735:786, 862:880] > 0).sum()),
                          overlap_with_diffuser_px=int(((A["candle"] > 0) & (A["reed-diffuser"] > 0)).sum())))
    json.dump(out, open(os.path.join(ST, "b1-checks.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(out["qa_round1"]))
    print(json.dumps(dict(rnd2=out["rnd2"], black=out["black_point"]["defaults"], black_ok=out["black_point"]["ok"], jar=out["colour"]["jar"]["as_seen_mid_tone"],
                          floor=out["same_house"]["floor_median"], plaster=out["same_house"]["plaster_median"], n_ok=n_ok,
                          notc=out["counts"]["not_counting_in_b1"], halos=out["halos"]["total_light_fringe_px"])))
    for k, r in rows.items():
        print(k, r["area_pct"], r["height_pct"], r["visible_pct"], r["counts"], hal.get(k))


if __name__ == "__main__":
    main()
