#!/usr/bin/env python3
"""
kids_art.py: the art of the framed prints, put into the frames by code (א.6 2ג / ב.6: "the art goes into the frames in code"),
render-agent, 2026-11-24; 0 tokens. Two steps:
  extract <kid>        : (run with python3.12 -I: it reads the supplier photo) the three panels of the set from the SKU photo (boy Type C
                         39ab48bc, girl Type A 5667565b; the same three-panel template), each inner art area found by scanning from its
                         centre to the wood frame, rectified to 300 x 400 (30 x 40), into the scratchpad (wm-kids/art/<kid>-<n>.png)
  place <kid>          : into the framed-prints layer: per frame (A, B over the desk; C on the top ledge) the blank canvas the edit drew
                         is found inside the frame (the pale area inside the layer's frame pixels, near the clay's art region), its four
                         corners fitted, and the panel warped in by a homography; lit by the canvas's own light (per channel, the lit
                         canvas over the panel's paper colour), so the paper takes the canvas's light and the ink scales with it
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SKU = {"boy": "39ab48bc_2685afe5-6908-4d88-8c17-7cbc9c0fc90f.jpg", "girl": "5667565b_48135295-96c3-49cf-9e9b-a8dc5972c7d9.jpg"}
# approximate centres of the three panels in the 1000 x 1000 SKU photo (the template is shared)
CENTRES = [(190, 455), (535, 450), (846, 450)]
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/"


def extract(kid):
    from PIL import Image
    im = Image.open(SCR + "picks/img/" + SKU[kid]).convert("RGB")
    a = np.asarray(im).astype(np.float64) / 255
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    Mx = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ Mx.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    L = 116 * f[..., 1] - 16
    A, B = 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])
    Cc = np.hypot(A, B)
    hh = np.degrees(np.arctan2(B, A)) % 360
    wood = (Cc > 20) & (hh > 45) & (hh < 85) & (L > 22) & (L < 62)
    out = []
    os.makedirs(SCR + "wm-kids/art", exist_ok=True)
    for n, (cx, cy) in enumerate(CENTRES):
        def scan(x0, y0, dx, dy):
            x, y = x0, y0
            run = 0
            while 0 < x < 999 and 0 < y < 999:
                run = run + 1 if wood[y, x] else 0
                if run >= 3:
                    return x - 2 * dx, y - 2 * dy
                x += dx
                y += dy
            return x, y
        # four edges, each from 5 scanlines
        lefts, rights, tops, bots = [], [], [], []
        for t in np.linspace(-0.35, 0.35, 7):
            yy = int(cy + t * 450)
            lefts.append(scan(cx, yy, -1, 0))
            rights.append(scan(cx, yy, 1, 0))
            xx = int(cx + t * 260)
            tops.append(scan(xx, cy, 0, -1))
            bots.append(scan(xx, cy, 0, 1))

        def fit(pts, vertical):
            p = np.array(pts, float)
            if vertical:              # x = a y + b
                A_ = np.stack([p[:, 1], np.ones(len(p))], 1)
                return np.linalg.lstsq(A_, p[:, 0], rcond=None)[0]
            A_ = np.stack([p[:, 0], np.ones(len(p))], 1)
            return np.linalg.lstsq(A_, p[:, 1], rcond=None)[0]
        lv, rv, th, bh = fit(lefts, True), fit(rights, True), fit(tops, False), fit(bots, False)

        def inter(v, h_):             # x = v0 y + v1 ; y = h0 x + h1
            y = (h_[0] * v[1] + h_[1]) / (1 - h_[0] * v[0])
            return v[0] * y + v[1], y
        q = [inter(lv, th), inter(rv, th), inter(rv, bh), inter(lv, bh)]
        if kid == "girl":             # her flowers are terracotta and mustard (they read as the frame): the template is the boy's photo's
            q = [tuple(v) for v in json.load(open(SCR + "wm-kids/art/boy-panels.json"))["panels"][n]["quad"]]
            out.append(dict(panel=n, quad=[[round(v, 1) for v in p] for p in q], note="the boy's quad (the same template)"))
        inset = 0.0 if kid == "girl" else 2.0
        cxq, cyq = np.mean([p[0] for p in q]), np.mean([p[1] for p in q])
        q = [(p[0] + inset * np.sign(cxq - p[0]), p[1] + inset * np.sign(cyq - p[1])) for p in q]
        import cv2
        Hm = cv2.getPerspectiveTransform(np.float32(q), np.float32([(0, 0), (300, 0), (300, 400), (0, 400)]))
        panel = cv2.warpPerspective(np.asarray(im), Hm, (300, 400), flags=cv2.INTER_LANCZOS4)
        Image.fromarray(panel).save(SCR + f"wm-kids/art/{kid}-{n}.png")
        if kid != "girl":
            out.append(dict(panel=n, quad=[[round(v, 1) for v in p] for p in q]))
    json.dump(dict(sku_photo=SKU[kid], panels=out), open(SCR + f"wm-kids/art/{kid}-panels.json", "w"), indent=1)
    print(json.dumps(out))


def place(kid, frames=("A", "B", "C")):
    import cv2
    from PIL import Image
    sys.path.insert(0, HERE)
    import kids_common as K
    from kids_passes import PRODUCTS
    C = K.C
    st = K.ST[kid]
    slot, pid = PRODUCTS[kid]["framed-prints"][0], PRODUCTS[kid]["framed-prints"][1]
    lp = os.path.join(st, "layers", slot, pid + ".png")
    blank = os.path.join(K.SCR, f"{kid}-framed-prints-blank.png")
    if not os.path.exists(blank):                 # the frames with their blank canvases, kept so the art can be placed again
        import shutil
        shutil.copy(lp, blank)
    rgba = np.asarray(Image.open(blank)).astype(np.float64) / 255
    a = rgba[..., 3]
    rgb = rgba[..., :3]
    ids = K.ids(f"K-{kid}")
    lab = C.to_lab(np.clip(rgb, 0, 1))
    rec = {}
    for n, (fr, cid) in enumerate((("A", 43), ("B", 43), ("C", 45))):
        if fr not in frames:
            continue
        art_clay = ids == cid
        ncomp, lb = cv2.connectedComponents(art_clay.astype(np.uint8))
        comps = sorted([(np.nonzero(lb == i)[1].mean(), i) for i in range(1, ncomp) if (lb == i).sum() > 200])
        if cid == 43:
            comp = lb == comps[0 if fr == "A" else 1][1]
        else:
            comp = lb == comps[0][1]
        # the blank canvas in the edit: the hole inside the drawn honey-wood frame (the wood ring found by its colour, near the clay's
        # art region), so the paper's own fall-off of light does not matter
        near = C.dil(comp, 30) & (a > 0.6)
        Cc = np.hypot(lab[..., 1], lab[..., 2])
        hh = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
        wood = near & (Cc > 16) & (hh > 40) & (hh < 90) & (lab[..., 0] < 80)
        wood = cv2.morphologyEx(wood.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(2)).astype(bool)
        n_, lb2, st2, _ = cv2.connectedComponentsWithStats(wood.astype(np.uint8))
        holes = []
        if n_ >= 2:
            ring = lb2 == 1 + int(np.argmax(st2[1:, cv2.CC_STAT_AREA]))
            inv = (~ring).astype(np.uint8)
            n3, lb3, st3, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
            border = set(np.unique(np.concatenate([lb3[0], lb3[-1], lb3[:, 0], lb3[:, -1]])))
            holes = [i for i in range(1, n3) if i not in border and st3[i, cv2.CC_STAT_AREA] > 0.5 * comp.sum()]
        if holes:
            canvas = lb3 == max(holes, key=lambda i: st3[i, cv2.CC_STAT_AREA])
            how = "the hole inside the drawn wood frame"
        else:                         # the frame's bottom hidden (frame C behind the ledge's lip): the pale paper near the clay's art
            nearp = C.dil(comp, 14) & (a > 0.9)
            pale = nearp & (lab[..., 0] > np.percentile(lab[..., 0][nearp], 35)) & (Cc < 18)
            pale = cv2.morphologyEx(pale.astype(np.uint8), cv2.MORPH_OPEN, C.disk(2)).astype(bool)
            n4, lb4, st4, _ = cv2.connectedComponentsWithStats(pale.astype(np.uint8))
            if n4 < 2:
                rec[fr] = "no blank canvas found"
                continue
            canvas = lb4 == 1 + int(np.argmax(st4[1:, cv2.CC_STAT_AREA]))
            how = "the pale paper near the clay's art region (the frame ring is not closed)"
        canvas = cv2.morphologyEx(canvas.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(3)).astype(bool)
        cnt, _ = cv2.findContours(canvas.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cnt = max(cnt, key=cv2.contourArea)
        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True).reshape(-1, 2).astype(np.float32)
        if len(approx) != 4:
            rect = cv2.minAreaRect(cnt)
            approx = cv2.boxPoints(rect).astype(np.float32)
        s = approx.sum(1)
        dfx = np.diff(approx, axis=1).ravel()
        q = np.float32([approx[np.argmin(s)], approx[np.argmin(dfx)], approx[np.argmax(s)], approx[np.argmax(dfx)]])   # tl, tr, br, bl
        panel = np.asarray(Image.open(SCR + f"wm-kids/art/{kid}-{n}.png").convert("RGB")).astype(np.float64) / 255
        Hm = cv2.getPerspectiveTransform(np.float32([(0, 0), (300, 0), (300, 400), (0, 400)]), q)
        warped = cv2.warpPerspective(panel.astype(np.float32), Hm, (K.W, K.H), flags=cv2.INTER_LANCZOS4).astype(np.float64)
        cover = cv2.warpPerspective(np.ones((400, 300), np.float32), Hm, (K.W, K.H), flags=cv2.INTER_LINEAR).astype(np.float64)
        inner = C.ero(canvas, 1) & (cover > 0.5)
        # light: the lit blank canvas (smoothed, so no texture of the edit's blank survives) over the panel's paper colour
        canvas_lin = C.lin(np.clip(rgb, 0, 1))
        w = C.ero(canvas, 3).astype(np.float64)
        lit = np.stack([C.blur(canvas_lin[..., c] * w, 6) / np.maximum(C.blur(w, 6), 1e-4) for c in range(3)], -1)
        plab = C.to_lab(panel)
        paper = C.lin(panel)[plab[..., 0] > np.percentile(plab[..., 0], 70)].mean(0)
        out_lin = C.lin(np.clip(warped, 0, 1)) * lit / np.maximum(paper, 1e-4)
        art = C.srgb(np.clip(out_lin, 0, 1))
        m = np.clip(cover, 0, 1) * canvas.astype(np.float64)
        m = np.where(inner, 1.0, C.blur(m, 0.7) * canvas)
        rgb = rgb * (1 - m[..., None]) + art * m[..., None]
        rec[fr] = dict(found_by=how, canvas_px=int(canvas.sum()), quad=[[round(float(v), 1) for v in p] for p in q], paper_lin=[round(float(v), 4) for v in paper])
    out = np.dstack([C.q(np.clip(rgb, 0, 1)), C.q(a)])
    out[..., :3][out[..., 3] == 0] = 0
    Image.fromarray(out, "RGBA").save(lp, optimize=True)
    man = json.load(open(os.path.join(st, "manifest.json")))
    man.setdefault("code_fixes", {})["framed-prints art"] = dict(rec, how="tools/kids_art.py place: the set's three panels from the SKU photo, "
                                                              "warped into the blank canvases the edit drew, lit by the canvas")
    json.dump(man, open(os.path.join(st, "manifest.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(rec))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "extract":
        extract(a[1])
    elif a[0] == "place":
        place(a[1], tuple(a[2].split(",")) if len(a) > 2 else ("A", "B", "C"))
