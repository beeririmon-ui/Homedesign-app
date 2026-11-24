#!/usr/bin/env python3
"""
kids_checks.py: the checks of the brief (6) and the QA sheet, per room (render-agent, 2026-11-24; 0 tokens).
  - RND2: every frame equals plate.png outside every alpha, shadow and light, pixel for pixel; the variants equal the defaults outside the
    throw's alpha (V1 and Vn);
  - shadows one z below their product; lights screen (z 90);
  - WM-G1: the frame's p0.5 of L* in 11-14;
  - the count: the manager's way (each product once; a set is one) and V7Q6 (0.5 % of the frame, or 0.15 % with the larger dimension
    6 % of the frame height, and 50 % visible: the visible share from the clay's silhouettes, occlusion and frame cut);
  - the band: its implied albedo against the plaster above (boy #A8A88E, girl #E8D5CC), and the plaster above the band (ב.1: bone, no
    pink); the sample slot's rules (ד.4 / א.4: the boy's V3 fold at least 8 L* from the band; the girl's V3 pink H 10-25, S <= 40);
  - safety in the frame (א.1): no product pixel on the sill slab's top face.
  python3 kids_checks.py <kid>
"""
import colorsys
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kids_common as K  # noqa: E402
import kids_cut as KC  # noqa: E402
import compose_plate_kids as CP  # noqa: E402

C = K.C
H, W = K.H, K.W
SIL = {"boy": {"bedding": ["bedding", "pillow-lying"], "pillowcase": ["pillow-standing"]},
       "girl": {"bedding": ["bedding"], "pillowcase": ["pillow-lying", "pillow-standing"]}}
REGIONS = {   # QA regions, canvas px (x0, y0, x1, y1), shown at x2 on the sheet
    "1 the window: blind (no cord), pendant lit, the empty sill": (40, 40, 900, 560),
    "2 the nest: pillows, cushions, the soft toy, the left cushion over the standing pillow": (380, 600, 1100, 1000),
    "3 the bed: duvet hang, the throw (sample slot), the foot board": (330, 800, 1560, 1300),
    "4 the shelf: two ledge pairs, the books, print C": (1060, 100, 1600, 640),
    "5 the prints A + B over the desk (art by code)": (1760, 60, 2520, 520),
    "6 the desk: bookends, pen cup, cars": (1820, 640, 2480, 960),
    "7 the floor: the basket": (560, 1000, 1160, 1530),
    "8 the band line and the corner": (560, 300, 1460, 760),
}


def hsl(lab):
    rgb = np.clip(C.from_lab(np.array(lab, float)[None, None])[0, 0], 0, 1)
    h, l, s = colorsys.rgb_to_hls(*rgb)
    return [round(h * 360, 1), round(s * 100, 1), round(l * 100, 1)]


def main(kid):
    st = K.ST[kid]
    man = KC.load_man(kid)
    fr = K.frame_mask()
    out = dict(kid=kid, frames={})
    o8, r = KC.compose(kid, f"K-{kid}-defaults")
    out["frames"][f"K-{kid}-defaults"] = r
    dflt = o8.astype(int)
    v1 = [l for l in man["layers"] if l["key"] == "bedspread" and l.get("default", True)][0]
    a1 = np.asarray(Image.open(os.path.join(st, v1["layer"])))[..., 3] > 0
    for vn in ("V2", "V3"):
        vs = [l for l in man["layers"] if l.get("variant") == vn and l["key"] == "bedspread"]
        if not vs:
            continue
        o, rv = KC.compose(kid, f"K-{kid}-{vn}", swap={vs[0]["slot"]: vs[0]})
        an = np.asarray(Image.open(os.path.join(st, vs[0]["layer"])))[..., 3] > 0
        diff = np.abs(o.astype(int) - dflt).max(2)
        rv["vs_defaults_outside_throw_px"] = int((diff[~(a1 | an)] > 0).sum())
        rv["vs_defaults_outside_throw_max"] = int(diff[~(a1 | an)].max()) if (~(a1 | an)).any() else 0
        out["frames"][f"K-{kid}-{vn}"] = rv
    out["shadow_z"] = dict(all_one_below=all(l["shadow_z"] == l["z"] - 1 for l in man["layers"]), layers=len(man["layers"]))
    out["light"] = [dict(file=li["file"], blend=li["blend"], z=li["z"]) for li in man["light"]]
    # the count
    sel = json.load(open(os.path.join(K.CLAY, "selfcheck.json")))["frames"][f"K-{kid}"]["silhouettes"]
    rows = {}
    for l in [l for l in man["layers"] if l.get("default", True)]:
        a = np.asarray(Image.open(os.path.join(st, l["layer"])))[..., 3] > 127
        af = a & fr
        if not af.any():
            continue
        ys, xs = np.nonzero(af)
        pct = 100 * af.sum() / fr.sum()
        hp = 100 * (ys.max() - ys.min() + 1) / K.FH
        wp = 100 * (xs.max() - xs.min() + 1) / K.FH
        mem = SIL[kid].get(l["key"], [l["key"]])
        sp = sum(sel[m]["silhouette_px"] for m in mem if m in sel)
        vp = sum(sel[m]["visible_in_frame_px"] for m in mem if m in sel)
        vis = round(100 * vp / sp, 1) if sp else None
        ok_area = pct >= 0.5 or (pct >= 0.15 and max(hp, wp) >= 6.0)
        rows[l["key"]] = dict(product=l["product"], frame_pct=round(pct, 3), larger_dim_pct_of_height=round(max(hp, wp), 2), visible_pct_clay=vis,
                              v7q6=bool(ok_area and (vis is None or vis >= 50)),
                              note=None if ok_area and (vis is None or vis >= 50) else ("visible < 50 % (clay)" if ok_area else "too small"))
    out["count"] = dict(manager=len(rows), v7q6=sum(1 for v in rows.values() if v["v7q6"]), rows=rows)
    # colours
    lab_d = C.to_lab(dflt.astype(np.float64) / 255)
    cols = {}
    for l in man["layers"]:
        rgba = np.asarray(Image.open(os.path.join(st, l["layer"])))
        m = (rgba[..., 3] > 160) & fr
        if m.sum() > 30:
            md = np.median(C.to_lab(rgba[..., :3].astype(np.float64) / 255)[m], 0)
            cols[l["product"] + ("" if l.get("default", True) else f" ({l.get('variant')})")] = dict(Lab=[round(float(v), 1) for v in md],
                                                                                                   LCh=[round(v, 1) for v in K.lch(md)])
    out["colours"] = cols
    # the band and the plaster above it
    ids = K.ids(f"K-{kid}-plate")
    plate = C.load(os.path.join(st, "plate.png"))
    br = CP.band_reading(plate, ids)
    tgt = "#A8A88E" if kid == "boy" else "#E8D5CC"
    if br:
        lab_i = np.array(br["implied_Lab"])
        br["target"] = tgt
        br["target_Lab"] = [round(float(v), 1) for v in K.lab_hex(tgt)]
        br["dE00"] = round(float(C.de00(tuple(lab_i), tuple(K.lab_hex(tgt)))), 2)
        br["implied_HSL"] = hsl(lab_i)
    out["band"] = br
    upper = C.ero(np.isin(ids, (1,)), 4) & fr
    upper[:, :900] = False
    for nm in [f"K-{kid}-defaults", f"K-{kid}-V3"]:
        p = os.path.join(st, f"{nm}.png")
        if os.path.exists(p):
            lab = C.to_lab(C.load(p))
            md = np.median(lab[upper], 0)
            out.setdefault("plaster_above_band", {})[nm] = dict(Lab=[round(float(v), 1) for v in md], HSL=hsl(md),
                                                                rule="bone, HSL H 32-40 (ב.1 / ד.1: no pink above the band)")
    # the sample slot's rules
    if kid == "boy" and "bedspread" in rows:
        v3 = [l for l in man["layers"] if l.get("variant") == "V3"][0]
        rgba = np.asarray(Image.open(os.path.join(st, v3["layer"])))
        m = (rgba[..., 3] > 200) & fr
        lab = C.to_lab(rgba[..., :3].astype(np.float64) / 255)
        ys = np.nonzero(m.any(1))[0]
        fold = m.copy()
        fold[: int(ys.min() + 0.55 * (ys.max() - ys.min()))] = False      # the front fold over the side: the lower part of the throw
        bandm = C.ero(np.isin(ids, (5,)), 3) & fr
        bL = float(np.median(C.to_lab(plate)[..., 0][bandm]))
        fL = float(np.median(lab[..., 0][fold]))
        out["V3_rule"] = dict(rule="the boy's V3 (Green): the front fold at least 8 L* from the band (א.4)", fold_L=round(fL, 1), band_L=round(bL, 1),
                              dL=round(abs(fL - bL), 1), ok=abs(fL - bL) >= 8)
    if kid == "girl":
        v3 = [l for l in man["layers"] if l.get("variant") == "V3"]
        if v3:
            rgba = np.asarray(Image.open(os.path.join(st, v3[0]["layer"])))
            m = (rgba[..., 3] > 200) & fr
            md = np.median(C.to_lab(rgba[..., :3].astype(np.float64) / 255)[m], 0)
            out["V3_rule"] = dict(rule="the girl's V3 (Pink): HSL H 10-25, S <= 40, L 62-82 (ב.4)", HSL=hsl(md), Lab=[round(float(v), 1) for v in md])
    # safety: the sill slab's top face (clay id 14, the slab's upper pixels) free of any product
    slab = np.isin(K.ids(f"K-{kid}-plate"), (14,))
    allA = np.zeros((H, W), bool)
    for l in [l for l in man["layers"] if l.get("default", True)]:
        allA |= np.asarray(Image.open(os.path.join(st, l["layer"])))[..., 3] > 30
    over = slab & allA
    out["sill_empty"] = dict(rule="nothing on the sill (א.1): product pixels over the slab in the frame", px=int(over.sum()),
                             which=sorted({l["key"] for l in man["layers"] if l.get("default", True) and
                                           (np.asarray(Image.open(os.path.join(st, l["layer"])))[..., 3][slab] > 30).any()}),
                             note="a product in front of the window below the sill line occludes the slab; none stands on it (the clay places nothing there)")
    json.dump(out, open(os.path.join(st, "checks.json"), "w"), indent=1, ensure_ascii=False)
    # the QA sheet
    im = Image.fromarray(o8)
    sheet_w = 2400
    top = im.resize((sheet_w, int(sheet_w * H / W)), Image.LANCZOS)
    d = ImageDraw.Draw(top)
    s = sheet_w / W
    for name, (x0, y0, x1, y1) in REGIONS.items():
        d.rectangle([x0 * s, y0 * s, x1 * s, y1 * s], outline=(220, 40, 40), width=3)
        d.text((x0 * s + 6, y0 * s + 4), name.split(" ")[0], fill=(220, 40, 40), font_size=28)
    tiles = []
    for name, (x0, y0, x1, y1) in REGIONS.items():
        t = im.crop((x0, y0, x1, y1))
        t = t.resize((int(t.size[0] * 2 * 1920 / 2565), int(t.size[1] * 2 * 1920 / 2565)), Image.LANCZOS)   # x2 of the 1920 frame
        t.thumbnail((1180, 760))
        tiles.append((name, t))
    rows_h = []
    y = top.size[1] + 10
    sheet = Image.new("RGB", (sheet_w, y + 4 * 800 + 400), "white")
    sheet.paste(top, (0, 0))
    dd = ImageDraw.Draw(sheet)
    for i, (name, t) in enumerate(tiles):
        cx, cy = (i % 2) * 1200, y + (i // 2) * 800
        sheet.paste(t, (cx, cy + 30))
        dd.text((cx + 4, cy + 2), name + " (x2)", fill=(0, 0, 0), font_size=24)
    vy = y + 4 * 800
    for j, nm in enumerate([f"K-{kid}-defaults", f"K-{kid}-V2", f"K-{kid}-V3"]):
        p = os.path.join(st, f"{nm}.png")
        if os.path.exists(p):
            t = Image.open(p).crop((700, 850, 1500, 1250)).resize((760, 380), Image.LANCZOS)
            sheet.paste(t, (j * 790, vy + 10))
            dd.text((j * 790 + 4, vy + 12), ("V1 " if j == 0 else f"V{j + 1} ") + nm, fill=(255, 255, 255), font_size=24)
    sheet.save(os.path.join(st, "qa-sheet.jpg"), quality=85)
    print(json.dumps({k: v for k, v in out.items() if k not in ("colours",)}, indent=1)[:4000])


if __name__ == "__main__":
    main(sys.argv[1])
