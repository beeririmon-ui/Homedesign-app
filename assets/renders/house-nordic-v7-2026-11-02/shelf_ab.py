#!/usr/bin/env python3
"""
shelf_ab.py: the shelf A/B of M0 1.2 (decision SHF1 = (a); docs/proposals/living-room-shelf-2026-11-06.md section 2; render-agent, 2026-11-06).
One seedream-5-pro image-to-image pass (~650) on the graded Nordic M0 after the products pass (m0-1-2-products-graded-fix-v6.png): a 55 x 18
floating oiled-oak shelf (#C8A27A, 3 thick, no visible bracket) on the back wall at X -1.65..-1.10, top at 1.00, replacing the wall round, with
(left to right) the black matte stoneware jar 30, the cream fluted column vase 25 with one dry branch, the travertine organic tray 24 with the
travertine-look reed diffuser on it. Then in code (0 tokens): the pass registered to the base, only the shelf group and the wall where the round
was laid back (everything else the base), "nothing else moved", the A/B sheet (round | shelf).
  ref | fetch <url> | lay | sheet
"""
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m0_products_pass as PP  # noqa: E402

REPO, OD, OD_REL = PP.REPO, PP.OD, PP.OD_REL
DATE = "2026-11-06"
BASE = os.path.join(OD, "m0-1-2-products-graded-fix-v6.png")
REF = os.path.join(OD, "m0-shelf-ab-ref-clay.png")
PASS_ID = "m0-shelf-ab-pass"
OUT_ID = "m0-1-2-products-shelf-graded-fix-v6"
SHEET = os.path.join(REPO, "assets/renders/house-nordic-m0-shelf-ab-sheet-2026-11-06.jpg")
DL = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/dl-shelf/"
CARDS = {"vase-cj-black-matte-stoneware-jar-30": "https://cf.cjdropshipping.com/quick/product/82e47b21-45f9-4973-b808-e93df5a70283.jpg",
         "sill-vase-cj-cream-fluted-column-25": "https://cf.cjdropshipping.com/quick/product/87f621eb-d46f-45e7-95ab-aecfd2f1191d.jpg",
         "pool-cj-travertine-organic-tray-24": "https://oss-cf.cjdropshipping.com/product/2025/05/30/11/cb6b4dae-a522-438d-9dce-b6d90cb638b0.jpg",
         "reed-diffuser-cj-travertine-look-bamboo-lid-milktea": "https://cf.cjdropshipping.com/quick/product/b9b7e7e5-2dc0-4697-8090-689303451bc9.jpg"}
SHELF = dict(x=(-1.65, -1.10), y=(0.0, 0.18), z_top=1.00, t=0.03)
ZONE = (0.42, 0.53, 0.42, 0.58)          # canvas uv: the shelf group and the round's place (the round: canvas u 0.464-0.508, v 0.458-0.542)
# widened after the pass (2026-11-06): the pass drew the shelf about 2x long (canvas u 0.411-0.543) and the vase's branch up to v 0.387; the lay zone
# is the union of these canvas-uv boxes, and only where the clay index says back wall (no sconce, cushion, curtain or triptych pixels)
ZONES = [(0.40, 0.555, 0.42, 0.583), (0.465, 0.515, 0.375, 0.42)]
INDEX = os.path.join(OD, "m0-clay-r5b-index.png")


def zone_mask(H, W, wall_only=True):
    z = np.zeros((H, W), bool)
    for u0, u1, v0, v1 in ZONES:
        z[int(v0 * H):int(v1 * H), int(u0 * W):int(u1 * W)] = True
    if wall_only:
        I = cv2.resize(cv2.imread(INDEX, cv2.IMREAD_UNCHANGED), (W, H), interpolation=cv2.INTER_NEAREST)
        wall = cv2.erode((I == 5).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
        z &= wall
    return z


def proxies():
    sx0, sx1 = SHELF["x"]
    zt = SHELF["z_top"]
    F = {}
    F["shelf"] = PP.box_faces(((sx0 + sx1) / 2, 0.09), (1.0, 0.0), sx1 - sx0, 0.18, SHELF["t"], zt - SHELF["t"], 0.66)
    F["jar"] = PP.cyl_faces((-1.57, 0.09), 0.075, zt, zt + 0.30, 0.18)
    F["column"] = PP.cyl_faces((-1.40, 0.09), 0.0425, zt, zt + 0.247, 0.86)
    F["tray"] = PP.box_faces((-1.23, 0.09), (1.0, 0.0), 0.24, 0.17, 0.018, zt, 0.78)
    F["diffuser"] = PP.cyl_faces((-1.23, 0.09), 0.035, zt + 0.018, zt + 0.12, 0.74) + PP.cyl_faces((-1.23, 0.09), 0.004, zt + 0.12, zt + 0.22, 0.45)
    return F


def ref():
    base = np.asarray(Image.open(PP.REF2).convert("RGB")).astype(np.float32)
    H, W = base.shape[:2]
    dep = cv2.resize(np.load(PP.DEPTH), (W, H), interpolation=cv2.INTER_NEAREST)
    out = base.copy()
    Ldir = np.array([-0.75, 0.35, 0.55])
    Ldir /= np.linalg.norm(Ldir)
    zall = dep.astype(np.float32).copy()
    rec = {}
    for name, faces in sorted(proxies().items(), key=lambda kv: -np.mean([PP.proj(p)[2] for poly, _ in kv[1] for p in poly])):
        zbuf = np.full((H, W), np.inf, np.float32)
        layer = np.zeros((H, W, 3), np.float32)
        for poly, grey in faces:
            pr = [PP.proj(p) for p in poly]
            uv = np.array([[(u * 3840 + 116) / 4072 * W, (v * 2160 + 65) / 2290 * H] for u, v, _ in pr])
            d = float(np.mean([q[2] for q in pr]))
            n = np.cross(poly[1] - poly[0], poly[2] - poly[0])
            n = n / (np.linalg.norm(n) + 1e-9)
            if np.dot(n, np.array(PP.CAM["loc"]) - np.mean(poly, 0)) < 0:
                n = -n
            shade = 0.55 + 0.45 * max(0.0, float(np.dot(n, Ldir)))
            m = np.zeros((H, W), np.uint8)
            cv2.fillPoly(m, [np.round(uv * 4).astype(np.int32)], 1, shift=2)
            m = m.astype(bool) & (d < zbuf) & (d < zall + 0.12)
            zbuf[m] = d
            layer[m] = np.clip(grey * shade, 0, 1) * 255
        cov = np.isfinite(zbuf)
        out[cov] = layer[cov]
        zall[cov] = np.minimum(zall[cov], zbuf[cov])
        ys, xs = np.nonzero(cov)
        rec[name] = [round(xs.min() / W, 3), round(xs.max() / W, 3), round(ys.min() / H, 3), round(ys.max() / H, 3)] if cov.any() else None
    Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8)).resize((2736, 1539), Image.LANCZOS).save(REF)
    json.dump(dict(what="the shelf A/B position map: the products-pass reference 2 r2 + the shelf group proxies (SHF1 a); no wall round", date=DATE,
                   shelf=SHELF, boxes_canvas_uv=rec), open(REF.replace(".png", ".json"), "w"), indent=1)
    print(json.dumps(rec))


def load01(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0


def fetch(url):
    os.makedirs(DL, exist_ok=True)
    dl = os.path.join(DL, PASS_ID + ".png")
    if not os.path.exists(dl):
        subprocess.run(["curl", "-sS", "-L", "--max-time", "240", "-o", dl, url], check=True)
    os.makedirs(os.path.join(OD, "raw"), exist_ok=True)
    open(os.path.join(OD, "raw", PASS_ID + ".png"), "wb").write(open(dl, "rb").read())
    im0 = Image.open(dl).convert("RGB")
    norm = os.path.join(OD, PASS_ID + ".png")
    im0.resize((2736, 1539), Image.LANCZOS).save(norm)
    p, b = load01(norm), load01(BASE)
    H, W = b.shape[:2]
    # register the pass to the base (ECC affine, the shelf zone masked out)
    g = lambda x: cv2.resize(cv2.cvtColor((x * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY), (W // 2, H // 2), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    m = (~zone_mask(H // 2, W // 2, wall_only=False)).astype(np.uint8)
    A_ = np.eye(2, 3, dtype=np.float32)
    cc, A_ = cv2.findTransformECC(g(b), g(p), A_, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), m, 5)
    A_[:, 2] *= 2
    pr = np.clip(cv2.warpAffine(p, A_, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE), 0, 1)
    Image.fromarray((pr * 255 + 0.5).astype(np.uint8)).save(os.path.join(OD, PASS_ID + "-reg.png"))
    zm = zone_mask(H, W, wall_only=False)
    fr = np.zeros((H, W), bool)
    fr[int(round(65 / 2290 * H)):int(round(2225 / 2290 * H)), int(round(116 / 4072 * W)):int(round(3956 / 4072 * W))] = True
    d = np.abs(pr - b) * 255
    nem = dict(rule="mean |delta| per channel <= 2 outside the shelf zone (ZONES), on the 16:9 frame (the pass against the graded base, registered)",
               outside_mean_per_channel=[round(float(d[..., c][fr & ~zm].mean()), 2) for c in range(3)])
    nem["pass"] = bool(max(nem["outside_mean_per_channel"]) <= 2)
    rec = dict(asset_id=PASS_ID, date=DATE, tokens=650, model="seedream-5-pro i2i 2K auto", url=url, base=os.path.relpath(BASE, REPO),
               register=dict(ecc=round(float(cc), 4), shift_px=[round(float(A_[0, 2]), 2), round(float(A_[1, 2]), 2)]), nothing_else_moved_raw=nem,
               normalised=OD_REL + PASS_ID + ".png", reference=os.path.relpath(REF, REPO), cards=CARDS)
    json.dump(rec, open(os.path.join(OD, PASS_ID + ".json"), "w"), indent=1)
    print(json.dumps(rec, indent=1))


def lay():
    """the graded base everywhere; from the registered pass (one linear-light gain per channel onto the base's tone) only the shelf zone
    where the pass changed it (the shelf group, its shadows, the wall where the round was), feathered"""
    b = load01(BASE)
    pr = load01(os.path.join(OD, PASS_ID + "-reg.png"))
    H, W = b.shape[:2]
    zm = zone_mask(H, W)
    s2l = lambda x: np.where(x <= 0.04045, x / 12.92, ((np.clip(x, 0, None) + 0.055) / 1.055) ** 2.4)
    l2s = lambda x: np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)
    zr = zone_mask(H, W, wall_only=False)
    ring = cv2.dilate(zr.astype(np.uint8), np.ones((121, 121), np.uint8)).astype(bool) & ~zr
    sel = ring & (pr.min(2) > 0.25) & (pr.max(2) < 0.95)
    gains = [float(np.median(s2l(b[..., c][sel]) / np.maximum(s2l(pr[..., c][sel]), 1e-4))) for c in range(3)]
    pt = np.clip(l2s(s2l(pr) * np.array(gains)), 0, 1).astype(np.float32)
    D = cv2.GaussianBlur(np.abs(pt - b).max(2), (0, 0), 2)
    m = ((D > 0.035) & zm).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((21, 21), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros((H, W), np.uint8)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > 400:
            keep[lab == i] = 1
    # the round's place always from the pass (it was removed there), the whole group region grown 10 px
    rnd = np.zeros((H, W), np.uint8)
    rr = json.load(open(os.path.join(OD, "m0-1-2-shell-seedream-fix-base.json")))["wall_round"]["target"]
    cv2.ellipse(rnd, ((rr["centre_px"][0], rr["centre_px"][1]), (rr["axes_px"][0] + 30, rr["axes_px"][1] + 30), 0), 1, -1)
    reg = cv2.dilate(np.maximum(keep, rnd), np.ones((21, 21), np.uint8))
    reg[~zm] = 0
    a = cv2.GaussianBlur(reg.astype(np.float32), (0, 0), 8)
    a = np.maximum(a, cv2.erode(reg, np.ones((15, 15), np.uint8)).astype(np.float32)) * zm
    a = cv2.GaussianBlur(a, (0, 0), 3)
    out = np.clip(b * (1 - a[..., None]) + pt * a[..., None], 0, 1)
    p = os.path.join(OD, OUT_ID + ".png")
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(p)
    fx0, fy0 = int(round(116 / 4072 * W)), int(round(65 / 2290 * H))
    fx1, fy1 = int(round(3956 / 4072 * W)), int(round(2225 / 2290 * H))
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).crop((fx0, fy0, fx1, fy1)).save(p.replace("-graded-fix-v6", "-frame-fix-v6"))
    d = np.abs(out - b) * 255
    fr = np.zeros((H, W), bool)
    fr[fy0:fy1, fx0:fx1] = True
    ys, xs = np.nonzero(reg)
    rec = json.load(open(os.path.join(OD, PASS_ID + ".json")))
    rec["lay"] = dict(tone_gains_rgb=[round(g, 4) for g in gains], region_canvas_uv=[round(xs.min() / W, 3), round(xs.max() / W, 3), round(ys.min() / H, 3), round(ys.max() / H, 3)],
                      region_px=int(reg.sum()), nothing_else_moved_after_lay=dict(outside_zone_mean_per_channel=[round(float(d[..., c][fr & ~zm].mean()), 3) for c in range(3)],
                                                                   max_outside_zone=round(float(d[fr & ~zm].max()), 2)),
                      how="the graded base everywhere; the pass only inside the shelf zone where it changed it (|delta| > 0.035 after the tone gain, closed, > 400 px) "
                          "and over the round's place; grown 10 px, feathered 8 px",
                      output=OD_REL + OUT_ID + ".png", frame=OD_REL + OUT_ID.replace("-graded-fix-v6", "-frame-fix-v6") + ".png")
    json.dump(rec, open(os.path.join(OD, PASS_ID + ".json"), "w"), indent=1)
    print(json.dumps(rec["lay"], indent=1))


def sheet():
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    A = Image.open(BASE).convert("RGB")
    B = Image.open(os.path.join(OD, OUT_ID + ".png")).convert("RGB")
    W, H = A.size
    box = (int(round(116 / 4072 * W)), int(round(65 / 2290 * H)), int(round(3956 / 4072 * W)), int(round(2225 / 2290 * H)))
    A, B = A.crop(box).resize((1280, 720), Image.LANCZOS), B.crop(box).resize((1280, 720), Image.LANCZOS)
    zx0, zx1 = int((0.38 * W - box[0]) / (box[2] - box[0]) * 1280), int((0.58 * W - box[0]) / (box[2] - box[0]) * 1280)
    zy0, zy1 = int((0.38 * H - box[1]) / (box[3] - box[1]) * 720), int((0.62 * H - box[1]) / (box[3] - box[1]) * 720)
    Az = Image.open(BASE).convert("RGB").crop((int(0.38 * W), int(0.38 * H), int(0.58 * W), int(0.62 * H))).resize((1280, int(1280 * 0.24 * H / (0.20 * W))), Image.LANCZOS)
    Bz = Image.open(os.path.join(OD, OUT_ID + ".png")).convert("RGB").crop((int(0.38 * W), int(0.38 * H), int(0.58 * W), int(0.62 * H))).resize(Az.size, Image.LANCZOS)
    # the spec (55x18, 3 thick, objects at card size) as outlines on B's zoom, from the position map's boxes
    rb = json.load(open(REF.replace(".png", ".json")))["boxes_canvas_uv"]
    zd = ImageDraw.Draw(Bz)
    zx = lambda u: (u - 0.38) / 0.20 * Bz.size[0]
    zy = lambda v: (v - 0.38) / 0.24 * Bz.size[1]
    for k, (u0, u1, v0, v1) in rb.items():
        zd.rectangle((zx(u0), zy(v0), zx(u1), zy(v1)), outline=(220, 30, 30), width=3)
    out = Image.new("RGB", (2 * 1280 + 30, 60 + 720 + 40 + Az.size[1] + 90), (255, 255, 255))
    d = ImageDraw.Draw(out)
    d.text((10, 16), f"M0 1.2, shelf A/B (SHF1 = a, {DATE}): A = the wall round (products pass, graded v6) | B = the floating oak shelf, jar, fluted column, "
                     "travertine tray, diffuser. Not QA'd.", fill=(0, 0, 0), font=fb)
    out.paste(A, (10, 60))
    out.paste(B, (1300, 60))
    d.text((14, 784), "A: round", fill=(0, 0, 0), font=f)
    d.text((1304, 784), "B: shelf", fill=(0, 0, 0), font=f)
    out.paste(Az, (10, 820))
    out.paste(Bz, (1300, 820))
    lay = json.load(open(os.path.join(OD, PASS_ID + ".json"))).get("size_check", {})
    d.text((10, 820 + Az.size[1] + 10), "Red outlines on B's zoom: the spec from the position map (shelf 55x18, 3 thick, top at 1.00; jar 30x15, column 25, tray 24, diffuser).",
           fill=(160, 0, 0), font=f)
    d.text((10, 820 + Az.size[1] + 44), lay.get("summary_en", ""), fill=(160, 0, 0), font=f)
    out.save(SHEET, quality=88)
    print(SHEET)


if __name__ == "__main__":
    w = sys.argv[1]
    if w == "ref":
        ref()
    if w == "fetch":
        fetch(sys.argv[2])
    if w == "lay":
        lay()
    if w == "sheet":
        sheet()
