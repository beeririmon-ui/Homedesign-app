#!/usr/bin/env python3
"""depth_fb17.py (motion-agent, 2026-11-26, 0 tokens): a depth map per warm-modern room frame for the code 2.5D moves.

Per frame:
  1. the clay depth pass of the same camera and canvas (metres = value / 5000);
  2. its steps snapped to the frame's colours (site/tools/transitions/room_depth.py snap_edges, imported, not edited);
  3. every default product layer (RGBA, full canvas) enforced as a hard silhouette, in z order:
     - inside the alpha: pixels the clay shows as something else (the proxy smaller than the product) take the depth of
       the nearest pixel of the product's own proxy;
     - outside the alpha: pixels of the proxy (the proxy larger than the product) take the depth of the nearest
       background pixel. So the depth step lies exactly on the product's cut-out edge.
Output: <dir>/<name>, uint16, near = bright, linear in 1/d (as assets/renders/living-room/warm-modern/depth.json), and a
JSON next to it. Writes only new files.
"""
import json
import os
import sys

import cv2
import numpy as np

REPO = "/home/user/homedesign-app"
sys.path.insert(0, os.path.join(REPO, "site/tools/transitions"))
import camgeo as cg  # noqa: E402
from room_depth import edge_sharpness, snap_edges  # noqa: E402

R = "assets/renders/"
B = "assets/blockout/house/framing/"
FRAMES = [
    # id, image, clay dir + camera, manifest (or None), frame filter, out
    ("MB0", R + "master/warm-modern/stage1-2026-11-17/mb0-defaults-fb15.png", B + "wm-master-2026-11-17/MB0",
     R + "master/warm-modern/stage1-2026-11-17/layers/manifest-fb15.json", None, "depth-fb17.png"),
    ("MB1", R + "master/warm-modern/mb1-2026-11-19/mb1-defaults-fb15.png", R + "master/warm-modern/mb1-2026-11-19/clay/MB1",
     R + "master/warm-modern/mb1-2026-11-19/layers/manifest-fb15.json", None, "depth-fb17.png"),
    ("W0", R + "work/warm-modern/stage1-2026-11-20/w0-defaults-fb15.png", B + "wm-work-2026-11-20/W0",
     R + "work/warm-modern/stage1-2026-11-20/layers/manifest-fb15.json", None, "depth-fb17.png"),
    ("B1", R + "bath/warm-modern/b1-2026-11-19/b1-defaults-fb15.png", B + "wm-bath-b1-2026-11-19/B1",
     R + "bath/warm-modern/b1-2026-11-19/layers/manifest-fb15.json", None, "depth-fb17.png"),
    ("B2", R + "bath/warm-modern/stage1-2026-11-17/b2-defaults-fb13prep.png", B + "wm-bath-2026-11-17/B2",
     R + "bath/warm-modern/stage1-2026-11-17/layers/manifest.json", None, "depth-fb17.png"),
    ("D1", R + "dining/warm-modern/stage1-2026-11-20/D1-defaults-fb15.png", B + "wm-dining-2026-11-24/D1",
     R + "dining/warm-modern/stage1-2026-11-20/manifest-fb15.json", "D1", "D1-depth-fb17.png"),
    ("D2", R + "dining/warm-modern/stage1-2026-11-20/D2-defaults-fb15.png", B + "wm-dining-2026-11-24/D2",
     R + "dining/warm-modern/stage1-2026-11-20/manifest-fb15.json", "D2", "D2-depth-fb17.png"),
    ("K-boy", R + "boy/warm-modern/stage1-2026-11-24/K-boy-defaults-fb15.png", B + "wm-kids-2026-11-24/K-boy",
     R + "boy/warm-modern/stage1-2026-11-24/manifest-fb15.json", None, "depth-fb17.png"),
    ("K-girl", R + "girl/warm-modern/stage1-2026-11-24/K-girl-defaults-g1-fb15.png", B + "wm-kids-2026-11-24/K-girl",
     R + "girl/warm-modern/stage1-2026-11-24/manifest-g1-fb15.json", None, "depth-fb17.png"),
    ("HDx2", R + "hall/warm-modern/hall-products-2026-11-19/hdx2-products-fb13prep.png", B + "wm-hall-2026-11-18/HDx",
     R + "hall/warm-modern/hall-products-2026-11-19/hdx2/manifest.json", None, "hdx2-depth-fb17.png"),
    ("HC", R + "hall/warm-modern/hall-2026-11-18/hc.png", B + "wm-hall-2026-11-18/HC", None, None, "hc-depth-fb17.png"),
    ("D0", R + "hall/warm-modern/door-2026-11-16/d0.png", B + "wm-door-2026-11-16/D0-closed", None, None, "depth-fb17.png"),
]

# the empty plates (the moves run on the empty room: the products go down before a move and come back in the reveal)
PLATES = [
    ("MB0-plate", R + "master/warm-modern/stage1-2026-11-17/plate.png", B + "wm-master-2026-11-17/MB0-plate", "depth-plate-fb17.png"),
    ("MB1-plate", R + "master/warm-modern/mb1-2026-11-19/plate.png", R + "master/warm-modern/mb1-2026-11-19/clay/MB1-plate", "depth-plate-fb17.png"),
    ("W0-plate", R + "work/warm-modern/stage1-2026-11-20/plate.png", B + "wm-work-2026-11-20/W0-plate", "depth-plate-fb17.png"),
    ("B1-plate", R + "bath/warm-modern/b1-2026-11-19/plate.png", B + "wm-bath-b1-2026-11-19/B1-plate", "depth-plate-fb17.png"),
    ("B2-plate", R + "bath/warm-modern/stage1-2026-11-17/plate.png", B + "wm-bath-2026-11-17/B2-plate", "depth-plate-fb17.png"),
    ("D1-plate", R + "dining/warm-modern/stage1-2026-11-20/plate-D1.png", B + "wm-dining-2026-11-20/D1-plate", "D1-depth-plate-fb17.png"),
    ("D2-plate", R + "dining/warm-modern/stage1-2026-11-20/plate-D2.png", B + "wm-dining-2026-11-24/D2-plate", "D2-depth-plate-fb17.png"),
    ("K-boy-plate", R + "boy/warm-modern/stage1-2026-11-24/plate.png", B + "wm-kids-2026-11-24/K-boy-plate", "depth-plate-fb17.png"),
    ("K-girl-plate", R + "girl/warm-modern/stage1-2026-11-24/plate.png", B + "wm-kids-2026-11-24/K-girl-plate", "depth-plate-fb17.png"),
]
FRAMES += [(i, img, clay, None, None, out) for i, img, clay, out in PLATES]


def nearest_fill(values, source, region):
    """values at `region` pixels <- a smooth fill from the `source` pixels only (push-pull: normalised area averages
    down a pyramid, then back up). Smooth, so a large hole on a sloping bed or floor gets a slope, not Voronoi tiles."""
    if not source.any():
        return values
    v = np.where(source, values, 0).astype(np.float32)
    w = source.astype(np.float32)
    stack = []
    while True:
        stack.append((v, w))
        if (w > 0).all() or min(v.shape) <= 2:
            break
        h2, w2 = max(1, v.shape[0] // 2), max(1, v.shape[1] // 2)
        v = cv2.resize(v, (w2, h2), interpolation=cv2.INTER_AREA)
        w = cv2.resize(w, (w2, h2), interpolation=cv2.INTER_AREA)
    vv, ww = stack[-1]
    cur = np.where(ww > 0, vv / np.maximum(ww, 1e-9), np.float32(np.median(values[source])))
    for vv, ww in reversed(stack[:-1]):
        up = cv2.resize(cur, (vv.shape[1], vv.shape[0]), interpolation=cv2.INTER_LINEAR)
        own = vv / np.maximum(ww, 1e-9)
        a = np.clip(ww * 4.0, 0, 1)  # trust a level's own average where it has enough source
        cur = a * own + (1 - a) * up
    out = values.copy()
    out[region] = cur[region]
    return out


def layer_list(manifest, frame):
    d = json.load(open(manifest))
    base = os.path.dirname(manifest)
    out = []
    for e in d.get("layers", []):
        if not e.get("default") or e.get("retired"):
            continue
        if frame and e.get("frame") not in (frame, None):
            continue
        p = os.path.join(base, e["layer"])
        if not os.path.exists(p):
            p = os.path.join(os.path.dirname(base), e["layer"])
        ids = e.get("clay_ids") or ([e["clay_id"]] if isinstance(e.get("clay_id"), int) else None)
        out.append((e.get("z", 0), e.get("slot"), p, ids))
    return sorted(out, key=lambda t: t[0])


def enforce_layers(depth, valid, idmap, layers, legend):
    H, W = depth.shape
    FAR = 1e3
    d = np.where(valid, depth, FAR).astype(np.float32)
    rep = []
    ids_all, counts_all = np.unique(idmap, return_counts=True)
    count_of = dict(zip(ids_all.tolist(), counts_all.tolist()))
    done = np.zeros((H, W), bool)  # the alphas of the layers already enforced (lower z)
    for z, slot, path, ids in layers:
        a = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if a is None or a.ndim != 3 or a.shape[2] != 4 or a.shape[:2] != (H, W):
            rep.append(dict(slot=slot, skipped="not a full-canvas RGBA layer"))
            continue
        m = a[..., 3] >= 128
        if m.sum() < 30:
            rep.append(dict(slot=slot, skipped="empty alpha"))
            continue
        ys, xs = np.nonzero(m)
        pad = 48
        y0, y1, x0, x1 = max(0, ys.min() - pad), min(H, ys.max() + pad + 1), max(0, xs.min() - pad), min(W, xs.max() + pad + 1)
        mb, ib, db = m[y0:y1, x0:x1], idmap[y0:y1, x0:x1], d[y0:y1, x0:x1]
        how = "manifest clay ids"
        if not ids:
            # the product's own proxy, by name (selfcheck.json 'ids'), plus the fillers that live only around it
            import re
            inner = cv2.erode(mb.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
            near = cv2.dilate(mb.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
            u, c = np.unique(ib[near], return_counts=True)
            pat = re.compile("^" + re.escape((slot or "").lower()) + r"(?![-\w])")
            ids = [i for i in u.tolist() if slot and pat.match(legend.get(str(i), "").lower())]
            how = "clay ids by name"
        if ids:
            # its fillers: a filler id that touches the proxy in the clay (a plant on its pot, stems in a vase)
            # (within 40 px of it, and nearer to it than to any other product's proxy)
            pm = np.isin(idmap, ids).astype(np.uint8)
            ring = cv2.dilate(pm, np.ones((81, 81), np.uint8)).astype(bool) & ~pm.astype(bool)
            for i in np.unique(idmap[ring]).tolist():
                fname = legend.get(str(i), "").lower()
                if i in ids or "filler" not in fname:
                    continue
                owner = [sl for _, sl, _, _ in layers if sl and fname.startswith(sl.lower() + " ")]
                if owner:  # the legend names its product ("desk-organizer filler (pencils)")
                    if owner[0] == slot:
                        ids.append(i)
                    continue
                fr = cv2.dilate((idmap == i).astype(np.uint8), np.ones((81, 81), np.uint8)).astype(bool)
                u2, c2 = np.unique(idmap[fr], return_counts=True)
                prod = {a: b for a, b in zip(u2.tolist(), c2.tolist()) if "(product" in legend.get(str(a), "").lower() or a in ids}
                mine = sum(prod.get(a, 0) for a in ids)
                others = max([b for a, b in prod.items() if a not in ids] or [0])
                if mine and mine > others:
                    ids.append(i)
            # the work area covers the alpha and the whole proxy
            ys2, xs2 = np.nonzero(m | np.isin(idmap, ids))
            y0, y1, x0, x1 = max(0, ys2.min() - pad), min(H, ys2.max() + pad + 1), max(0, xs2.min() - pad), min(W, xs2.max() + pad + 1)
            mb, ib, db = m[y0:y1, x0:x1], idmap[y0:y1, x0:x1], d[y0:y1, x0:x1]
        if not ids:
            # no proxy in the clay: the product stands where its foot touches (the depth just under its lowest pixels);
            # a wall-hung product gets its wall, so nothing changes for it
            cols = np.nonzero(mb.any(axis=0))[0]
            yb = mb.shape[0] - 1 - np.argmax(mb[::-1, :][:, cols], axis=0)
            ylo, yhi = int(np.nonzero(mb.any(axis=1))[0].min()), int(yb.max())
            foot = yb >= yhi - max(4, 0.12 * (yhi - ylo))  # only the foot, not the leaves or a shade that overhang
            cols, yb = cols[foot], yb[foot]
            yy = np.clip(yb + 3, 0, mb.shape[0] - 1)
            smp = db[yy, cols]
            smp = smp[(smp < FAR * 0.5) & ~mb[yy, cols]]
            inside = db[mb & (db < FAR * 0.5)]
            if len(smp) >= 5 and len(inside):
                dc, di = float(np.median(smp)), float(np.median(inside))
                if dc < di * 0.96:
                    fix = mb & ((db > dc * 1.04) | (db >= FAR * 0.5))
                    db[fix] = dc
                    d[y0:y1, x0:x1] = db
                    rep.append(dict(slot=slot, z=z, proxy="none: the contact depth under its foot", contact_m=round(dc, 3),
                                    behind_m=round(di, 3), set_px=int(fix.sum())))
                    continue
            rep.append(dict(slot=slot, z=z, proxy="none: on its wall or surface, the clay depth (snapped) stands"))
            continue
        proxy = np.isin(ib, ids) & (db < FAR * 0.5)
        if not proxy.any():
            rep.append(dict(slot=slot, z=z, proxy="ids not in view"))
            continue
        # inside: pixels the clay shows as something else take the proxy's depth (nearest proxy pixel)
        nn = nearest_fill(db, proxy, mb & ~proxy)
        diff = np.abs(nn - db) / np.maximum(nn, 1e-3)
        fix_in = mb & ~proxy & (diff > 0.04)
        db2 = np.where(fix_in, nn, db)
        # outside: the proxy's overhang takes the nearest background depth
        bg = ~proxy & ~mb & (db2 < FAR * 0.5)
        over = proxy & ~mb & ~done[y0:y1, x0:x1]
        nb = nearest_fill(db2, bg, over)
        db3 = np.where(over, nb, db2)
        d[y0:y1, x0:x1] = db3
        done[y0:y1, x0:x1] |= mb
        rep.append(dict(slot=slot, z=z, proxy_ids=[int(i) for i in ids], how=how, alpha_px=int(mb.sum()),
                        filled_inside_px=int(fix_in.sum()), overhang_cleared_px=int(over.sum())))
    v = d < FAR * 0.5
    return np.where(v, d, np.inf).astype(np.float32), v, rep


def edge_agreement(depth, valid, layers, H, W):
    """share of product-alpha boundary pixels that carry a depth step (> 3 %) within 1 px: how crisp the products are."""
    FAR = 1e3
    d = np.where(valid, depth, FAR).astype(np.float32)
    k3 = np.ones((3, 3), np.uint8)
    step = cv2.dilate(d, k3) > cv2.erode(d, k3) * 1.03
    step = cv2.dilate(step.astype(np.uint8), k3).astype(bool)
    tot = hit = 0
    for _, _, path, _ in layers:
        a = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if a is None or a.ndim != 3 or a.shape[:2] != (H, W):
            continue
        m = (a[..., 3] >= 128).astype(np.uint8)
        edge = (cv2.dilate(m, k3) - cv2.erode(m, k3)).astype(bool)
        tot += int(edge.sum())
        hit += int((edge & step).sum())
    return tot, hit


def main(only=None):
    os.chdir(REPO)
    index = []
    for fid, image, clay, manifest, ffilter, outname in FRAMES:
        if only and fid not in only:
            continue
        out = os.path.join(os.path.dirname(image), outname)
        if os.environ.get("DRY"):
            out = os.path.join(os.environ["DRY"], fid + "-" + outname)
        if os.path.exists(out) and not os.environ.get("REWRITE_FB17"):
            raise SystemExit(f"{out} exists: this script writes new files only (REWRITE_FB17=1 rewrites its own fb17 files)")
        img = cv2.cvtColor(cv2.imread(image, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        depth, valid = cg.load_depth_png(clay + "-depth.png")
        from PIL import Image
        idmap = np.array(Image.open(clay + "-id.png"))  # palette indices for a P image (the ids of selfcheck.json)
        if idmap.ndim == 3:
            idmap = idmap[..., 0].astype(np.int32) + 256 * idmap[..., 1].astype(np.int32) + 65536 * idmap[..., 2].astype(np.int32)
        idmap = idmap.astype(np.int32)
        assert img.shape[:2] == depth.shape == idmap.shape[:2], (fid, img.shape, depth.shape, idmap.shape)
        before = edge_sharpness(depth, valid)
        snapped, vs, snap_rep = snap_edges(depth, valid, img)
        layers = layer_list(manifest, ffilter) if manifest else []
        H, W = depth.shape
        agree_clay = edge_agreement(depth, valid, layers, H, W) if layers else (0, 0)
        legend = {}
        for lp in (os.path.join(os.path.dirname(clay), "selfcheck.json"), os.path.join(os.path.dirname(clay), "clay-meta.json")):
            if os.path.exists(lp):
                j = json.load(open(lp))
                legend = j.get("ids") or next((v["ids"] for v in j.values() if isinstance(v, dict) and "ids" in v), {})
                if legend:
                    break
        final, vf, lrep = enforce_layers(snapped, vs, idmap, layers, legend) if layers else (snapped, vs, [])
        after = edge_sharpness(final, vf)
        agree = edge_agreement(final, vf, layers, H, W) if layers else (0, 0)
        info = cg.save_room_depth(out, final, vf, dict(
            frame=fid, image=os.path.basename(image),
            canvas=f"{W} x {H}, the image's own canvas (pixel for pixel)",
            source=dict(clay_depth=clay + "-depth.png", clay_id=clay + "-id.png", layers=manifest,
                        rule="clay depth (every proxy), steps snapped to the image (room_depth.snap_edges), then each default "
                             "product layer's alpha enforced as the depth edge (scratchpad depth_fb17.py)"),
            covers=("the empty plate (shell and fixed furniture): the map for the moves, which run on the empty room" if fid.endswith("-plate") else "the frame as rendered with its default products (shell, fixed furniture and product layers)"),
            snap=snap_rep, layers=lrep,
            crispness=dict(before=before, after=after),
            product_edges=dict(boundary_px=agree[0], with_depth_step_px=agree[1],
                               share=round(agree[1] / max(1, agree[0]), 3),
                               share_on_the_raw_clay=round(agree_clay[1] / max(1, agree_clay[0]), 3)),
            no_surface_px=int((~vf).sum()),
            note="motion-agent, 2026-11-26 (FB17), 0 tokens. For frontend-dev's 2.5D moves (MOCK7). A variant swap "
                 "changes only its own layer: re-run on that layer if its silhouette differs much from the default."))
        back, vb = cg.load_room_depth(out)
        err = float((np.abs(back[vf] - final[vf]) / final[vf]).max())
        info["roundtrip_rel_err_max"] = err
        with open(os.path.splitext(out)[0] + ".json", "w") as fh:
            json.dump(info, fh, indent=1, ensure_ascii=False)
        row = dict(frame=fid, depth=out, image=image, size=[W, H], d_near_m=round(info["d_near_m"], 3),
                   d_far_m=round(info["d_far_m"], 3), layers=len(layers),
                   product_edge_share=info["product_edges"]["share"],
                   product_edge_share_raw_clay=info["product_edges"]["share_on_the_raw_clay"],
                   between_share=round(after["between_share"], 4), roundtrip=err, kb=os.path.getsize(out) // 1024)
        print(json.dumps(row))
        index.append(row)
    return index


if __name__ == "__main__":
    idx = main(sys.argv[1:] or None)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "depth_fb17_index.json"), "w") as fh:
        json.dump(idx, fh, indent=1)
