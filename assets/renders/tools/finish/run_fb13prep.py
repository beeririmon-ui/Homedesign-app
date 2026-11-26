#!/usr/bin/env python3
"""
run_fb13prep.py: FB13 stage 0 over every warm-modern room with product layers (render-agent, 2026-11-25). 0 var2 tokens.
For each room of finish.ROOMS (its current default frame):
  1. the stack is composed with the manifest's formula and checked against the room's own frame (reproduce_check);
  2. the pasted test (pasted_test.run_test) on the stack as it is ("before");
  3. the shared finish (finish.finish_room): per layer sharpness, depth of field where a depth map exists, light wrap, bounce, the
     positional grain and the per-layer top-up;
  4. the finished frame, written under a NEW name next to the room's frame: <frame>-fb13prep.png (the 2720 x 1530 canvas). No room file
     is overwritten or edited;
  5. the pasted test on the finished stack ("after");
  6. what changes at x1: the 1920 frame before and after, both blurred 0.8 px (the grain is not a visible change at x1), dE76 per product
     (inside: its alpha grown 3 px; ring: 3-40 px out, where the bounce lands). A room "changes visibly at x1" when a product has >= 200 px
     inside or >= 400 px in its ring at dE >= 2.5; only then a QA sheet is written: <frame>-qa-fb13prep.jpg (the frame before / after and
     the most changed products at x1 and x2);
  7. a record per room (<frame>-fb13prep.json) and the table of every room and product, worst first, in this folder:
     pasted-test-2026-11-25.json and pasted-test-2026-11-25.tsv.

    python3.12 -I -B run_fb13prep.py [room ...]          # default: every room
"""
import json
import math
import os
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import finish as F  # noqa: E402
import pasted_test as P  # noqa: E402

DATE = "2026-11-25"
SUFFIX = "-fb13prep"


def bake(fbase, layers, bounces, grain):
    """the finished stack with the bounce tints and the grain baked by position (for the 'after' test)"""
    b = fbase.astype(np.float64)
    for t in bounces:
        b = b * t
    b = np.clip(F.rhu(b + grain[..., None]), 0, 255).astype(np.uint8)
    out = []
    for L, S in layers:
        Lf = L.astype(np.float64)
        Lf[..., :3] += grain[..., None]
        out.append((np.clip(F.rhu(Lf), 0, 255).astype(np.uint8), S))
    return b, out


def lab(img):
    return cv2.cvtColor(img.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)


def change_at_x1(st, before, after, layers):
    fb, fa = F.frame_view(before, st), F.frame_view(after, st)
    b1, a1 = cv2.GaussianBlur(fb, (0, 0), 0.8), cv2.GaussianBlur(fa, (0, 0), 0.8)
    dE = np.linalg.norm(lab(a1) - lab(b1), axis=2)
    out = {}
    for (L, _), e in zip(layers, st["entries"]):
        a = F.frame_view(L[..., 3], st) > 25
        if a.sum() < 20:
            continue
        ins = cv2.dilate(a.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
        ring = cv2.dilate(a.astype(np.uint8), np.ones((81, 81), np.uint8)).astype(bool) & ~ins
        out[e["name"]] = dict(inside_px=int((ins & (dE >= 2.5)).sum()), ring_px=int((ring & (dE >= 2.5)).sum()),
                              inside_p95=round(float(np.percentile(dE[ins], 95)), 2), ring_p95=round(float(np.percentile(dE[ring], 95)), 2) if ring.any() else 0.0)
    vis = {k: v for k, v in out.items() if v["inside_px"] >= 200 or v["ring_px"] >= 400}
    return dict(per_layer=out, visible_layers=sorted(vis, key=lambda k: -(vis[k]["inside_px"] + vis[k]["ring_px"])),
                frame_px_dE_2_5=int((dE >= 2.5).sum()), visible=bool(vis)), fb, fa


def font(sz):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", sz)
    except OSError:
        return ImageFont.load_default()


def qa_sheet(path, st, fb, fa, before, after, layers, chg, rec_room):
    W = 1920
    tiles = []
    for name in chg["visible_layers"][:4]:
        i = [e["name"] for e in st["entries"]].index(name)
        a = F.frame_view(layers[i][0][..., 3], st) > 25
        ys, xs = np.nonzero(a)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        pw, ph = int(0.35 * (x1 - x0) + 30), int(0.35 * (y1 - y0) + 30)
        x0, x1, y0, y1 = max(0, x0 - pw), min(1920, x1 + pw), max(0, y0 - ph), min(1080, y1 + ph)
        c1b, c1a = fb[y0:y1, x0:x1], fa[y0:y1, x0:x1]
        # x2: from the canvas (1.336 x the 1920 frame), scaled to 2 x
        fbx = st["frame_box"]
        k = (fbx[2] - fbx[0]) / 1920.0
        cx0, cy0 = int(fbx[0] + x0 * k), int(fbx[1] + y0 * k)
        cx1, cy1 = int(fbx[0] + x1 * k), int(fbx[1] + y1 * k)
        s2 = 2.0 / k
        c2b = cv2.resize(before[cy0:cy1, cx0:cx1], None, fx=s2, fy=s2, interpolation=cv2.INTER_LANCZOS4)
        c2a = cv2.resize(after[cy0:cy1, cx0:cx1], None, fx=s2, fy=s2, interpolation=cv2.INTER_LANCZOS4)
        tiles.append((name, c1b, c1a, c2b, c2a))
    rows_h = 540 + 60
    tile_rows = []
    for name, c1b, c1a, c2b, c2a in tiles:
        def fit(im, w, h):
            sc = min(w / im.shape[1], h / im.shape[0], 1.0)
            return cv2.resize(im, (max(1, int(im.shape[1] * sc)), max(1, int(im.shape[0] * sc))), interpolation=cv2.INTER_AREA) if sc < 1 else im
        t = [fit(c1b, 460, 420), fit(c1a, 460, 420), fit(c2b, 460, 420), fit(c2a, 460, 420)]
        tile_rows.append((name, t))
    H = rows_h + sum(max(x.shape[0] for x in t) + 40 for _, t in tile_rows) + 20
    sheet = Image.new("RGB", (W, H), (24, 24, 24))
    dr = ImageDraw.Draw(sheet)
    f1, f2 = font(22), font(16)
    g = rec_room["finish"]["grain"]
    dr.text((12, 10), f"{st['key']}  FB13 finish (0 tokens): before | after   grain {g['amplitude_8bit']} (8-bit, seed {g['seed']}), "
                      f"top-up {len(g['top_up'])} layers; score before {rec_room['score_before']:.1f} -> after {rec_room['score_after']:.1f}",
            fill=(235, 235, 235), font=f1)
    sheet.paste(Image.fromarray(cv2.resize(fb, (950, 534), interpolation=cv2.INTER_AREA)), (5, 50))
    sheet.paste(Image.fromarray(cv2.resize(fa, (950, 534), interpolation=cv2.INTER_AREA)), (965, 50))
    y = rows_h
    for name, t in tile_rows:
        c = chg["per_layer"][name]
        fx = rec_room["finish"]["layers"].get(name, {})
        dr.text((12, y), f"{name}: x1 before | x1 after | x2 before | x2 after   (dE>=2.5: inside {c['inside_px']} px, ring {c['ring_px']} px; "
                         f"{fx.get('sharpness', '')}; wrap {fx.get('light_wrap', {}).get('max_mix', 0)})", fill=(235, 235, 235), font=f2)
        x = 5
        for im in t:
            sheet.paste(Image.fromarray(im), (x, y + 24))
            x += im.shape[1] + 10
        y += max(im.shape[0] for im in t) + 40
    sheet.save(path, quality=88)


def compact(rows):
    keep = ("layer", "slot", "product", "kind", "frame_px", "score", "fails", "sharp_ratio", "interior_ratio", "grain_ratio", "light", "contact",
            "black", "lamp", "edge_rows_x1", "shadow_rows_x1", "edge_rows_low", "shadow_rows_low", "note")
    return [{k: r[k] for k in keep if k in r} for r in rows]


def run_room(key):
    t0 = time.time()
    st = F.load_room(key)
    base, layers, lights = F.read_stack(st)
    before = F.compose(base, layers, lights)
    rep = F.reproduce_check(st, before)
    tb = P.run_test(st, base, layers, lights, "before")
    dep = F.load_depth(st["cfg"])
    fl, fbase, bounces, grain, frec = F.finish_room(st, base, layers, lights, dict(dof=dep))
    after = F.compose(fbase, fl, lights, bounces, grain)
    od = os.path.join(F.R, st["cfg"]["out_dir"])
    name = st["cfg"]["out_name"] + SUFFIX
    out_png = os.path.join(od, name + ".png")
    assert not os.path.exists(out_png) or out_png.endswith(SUFFIX + ".png")
    Image.fromarray(after).save(out_png, optimize=True)
    bb, bl = bake(fbase, fl, bounces, grain)
    ta = P.run_test(st, bb, bl, lights, "after")
    chg, fb, fa = change_at_x1(st, before, after, layers)
    sb = round(sum(r.get("score", 0) for r in tb["rows"]), 2)
    sa = round(sum(r.get("score", 0) for r in ta["rows"]), 2)
    if dep is not None:
        dep = {k: v for k, v in dep.items() if k != "m"}
    rec = dict(room=key, date=DATE, stage="FB13 stage 0 (0 tokens): the shared finish and the pasted test on the current default frame",
               manifest=os.path.relpath(st["manifest"], F.REPO), frame=os.path.relpath(st["frame"], F.REPO), reproduce=rep,
               finished_frame=os.path.relpath(out_png, F.REPO), depth=dep, finish=frec, score_before=sb, score_after=sa, change_at_x1=chg,
               test_before=compact(tb["rows"]), test_after=compact(ta["rows"]), plate_black_p05_L=tb["plate_black_p05_L"],
               light_centroid=tb["light_centroid"], plate_reference=tb.get("plate_reference"))
    if chg["visible"]:
        qp = os.path.join(od, st["cfg"]["out_name"] + "-qa" + SUFFIX + ".jpg")
        qa_sheet(qp, st, fb, fa, before, after, layers, chg, rec)
        rec["qa_sheet"] = os.path.relpath(qp, F.REPO)
    rec["runtime_s"] = round(time.time() - t0, 1)
    json.dump(rec, open(os.path.join(od, name + ".json"), "w"), indent=1, ensure_ascii=False, default=float)
    print(f"{key}: {len(st['entries'])} layers, reproduce max {rep.get('max')} mean {rep.get('mean')}; score {sb} -> {sa}; "
          f"visible at x1: {chg['visible']} {chg['visible_layers'][:4]}; {rec['runtime_s']} s", flush=True)
    return rec


def main():
    keys = sys.argv[1:] or list(F.ROOMS)
    recs = {}
    allp = os.path.join(HERE, f"pasted-test-{DATE}.json")
    if os.path.exists(allp):
        recs = json.load(open(allp)).get("rooms", {})
    for k in keys:
        r = run_room(k)
        recs[k] = dict(score_before=r["score_before"], score_after=r["score_after"], reproduce=r["reproduce"], change_at_x1_visible=r["change_at_x1"]["visible"],
                       visible_layers=r["change_at_x1"]["visible_layers"], finished_frame=r["finished_frame"], qa_sheet=r.get("qa_sheet"),
                       record=os.path.relpath(os.path.join(F.R, F.ROOMS[k]["out_dir"], F.ROOMS[k]["out_name"] + SUFFIX + ".json"), F.REPO),
                       grain=r["finish"]["grain"], before=r["test_before"], after=r["test_after"])
    order = sorted(recs, key=lambda k: -recs[k]["score_before"])
    json.dump(dict(date=DATE, method=P.__doc__.strip().split("\n\n")[1], not_layered=F.NOT_LAYERED, room_order_worst_first=order, rooms=recs),
              open(allp, "w"), indent=1, ensure_ascii=False, default=float)
    lines = ["room\troom_score_before\troom_score_after\trank_in_room\tlayer\tproduct\tscore_before\tscore_after\tfails_before\tfails_after\t"
             "sharp_before\tsharp_after\tgrain_before\tgrain_after"]
    for k in order:
        after = {r["layer"]: r for r in recs[k]["after"]}
        for i, r in enumerate(recs[k]["before"]):
            a = after.get(r["layer"], {})
            lines.append("\t".join(str(x) for x in (k, recs[k]["score_before"], recs[k]["score_after"], i + 1, r["layer"], r.get("product"),
                                                     r.get("score", ""), a.get("score", ""), "; ".join(r.get("fails", [])) or r.get("note", "clean"),
                                                     "; ".join(a.get("fails", [])) or a.get("note", "clean"), r.get("sharp_ratio", ""),
                                                     a.get("sharp_ratio", ""), r.get("grain_ratio", ""), a.get("grain_ratio", ""))))
    open(os.path.join(HERE, f"pasted-test-{DATE}.tsv"), "w").write("\n".join(lines) + "\n")
    print("->", allp)


if __name__ == "__main__":
    main()
