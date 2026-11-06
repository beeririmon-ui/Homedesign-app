#!/usr/bin/env python3
"""
ed4_composite.py: ED4 (four targeted fidelity passes, render-agent, 2026-11-06) put back into the frames with a mask in code, so nothing
outside the mask can change.
Each pass was a seedream-5-pro image-to-image edit of a local crop (16:9 or 3:4) of the frame, with the product's card image as the
reference (prompts in assets/prompts/editorial-phase-b-2026-11-06/ed4-*.txt). Here, per frame:
  1. the 2K result is scaled to the crop and registered to it (ECC, affine) on the area outside the edit
  2. its colour is matched to the frame (per-channel linear gain, measured on a ring round the mask)
  3. the mask: inside a hand-set region round the product, the union of its outline in the frame and in the result (a colour or
     lightness rule read on both), holes filled, grown a few px for the contact shadow, feathered 3 px
  4. composited into the frame's raw; outside the region not one pixel changes (checked); then the same soft knee as the other frames
  sheet: a before / after sheet of the four
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finish_phaseb import s2l, l2s, load01, knee  # noqa: E402

RAW = os.path.join(HERE, "raw")
REC = os.path.join(HERE, "ed4.json")

# id: (base raw, crop box in the frame, model result file in raw/, regions (x0, y0, x1, y1) in crop px where the edit may land, diff threshold)
JOBS = {
    "nordic-A": dict(base="raw/nordic-A-fin2-codefix.png", box=(1180, 650, 2220, 1235), result="raw/ed4-nordic-A-seedream.png",
                     regions=[], thr=0.035, out="nordic-A-ed4"),
    "warm-modern-A": dict(base="raw/warm-modern-A-fin2-codefix.png", box=(1000, 0, 1910, 512), result="raw/ed4-warm-modern-A-seedream.png",
                          regions=[], thr=0.035, out="warm-modern-A-ed4"),
    "mediterranean-A": dict(base="raw/mediterranean-A-gpt-image-2-5.png", box=(900, 1000, 1620, 1405),
                            result="raw/ed4-mediterranean-A-seedream.png", regions=[], thr=0.035, out="mediterranean-A-ed4"),
    "japandi-A": dict(base="raw/japandi-A-nano-banana-2.png", box=(480, 560, 960, 1200), result="raw/ed4-japandi-A-seedream.png",
                      regions=[], thr=0.035, out="japandi-A-ed4"),
}
CFG = os.path.join(HERE, "ed4_regions.json")
if os.path.exists(CFG):
    for k, v in json.load(open(CFG)).items():
        JOBS[k].update(v)


def register(res, org, keep):
    """affine ECC of res onto org on the pixels in keep; returns the warped res and the matrix"""
    g1 = cv2.GaussianBlur(cv2.cvtColor((org * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255, (0, 0), 1.5)
    g2 = cv2.GaussianBlur(cv2.cvtColor((res * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255, (0, 0), 1.5)
    M = np.eye(2, 3, dtype=np.float32)
    try:
        _, M = cv2.findTransformECC(g1, g2, M, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6),
                                    keep.astype(np.uint8), 5)
    except cv2.error:
        pass
    h, w = org.shape[:2]
    out = cv2.warpAffine(res, M, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    return out, M


def one(k):
    J = JOBS[k]
    base = load01(os.path.join(HERE, J["base"]))
    x0, y0, x1, y1 = J["box"]
    org = base[y0:y1, x0:x1]
    h, w = org.shape[:2]
    res = load01(os.path.join(HERE, J["result"]))
    res = cv2.resize(res, (w, h), interpolation=cv2.INTER_AREA)
    region = np.zeros((h, w), bool)
    for rx0, ry0, rx1, ry1 in J["regions"]:
        region[ry0:ry1, rx0:rx1] = True
    J.setdefault("rules", [])
    keep = ~cv2.dilate(region.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)
    keep[:8], keep[-8:], keep[:, :8], keep[:, -8:] = False, False, False, False
    reg, M = register(res, org, keep)
    # colour: per-channel gain in linear light on a ring round the region
    ring = cv2.dilate(region.astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool) & ~region
    lo, lr = s2l(org), s2l(reg)
    gain = np.array([np.median(lo[..., c][ring]) / max(np.median(lr[..., c][ring]), 1e-5) for c in range(3)], np.float32)
    lr = lr * gain
    # the mask: per region, the product's outline in the frame and in the result (union), by a rule read on both
    # (dark / bright: L*; green: a*; ellipse: set by hand; diff: the blurred difference), holes filled, grown by the region's px (contact shadows)
    labo = cv2.cvtColor((org * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    labr = cv2.cvtColor((np.clip(l2s(lr), 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    db = cv2.GaussianBlur(np.abs(l2s(lr) - org).max(2), (0, 0), 6)
    m = np.zeros((h, w), bool)
    for rx0, ry0, rx1, ry1, rule, thr, grow in J["rules"]:
        rg = np.zeros((h, w), bool)
        rg[ry0:ry1, rx0:rx1] = True
        if rule == "dark":
            mm = (labo[..., 0] * 100 / 255 < thr) | (labr[..., 0] * 100 / 255 < thr)
        elif rule == "bright":
            mm = (labo[..., 0] * 100 / 255 > thr) | (labr[..., 0] * 100 / 255 > thr)
        elif rule == "green":
            mm = (labo[..., 1] - 128 < thr) | (labr[..., 1] - 128 < thr)
        elif rule == "ellipse":
            mm = np.zeros((h, w), np.uint8)
            cv2.ellipse(mm, ((rx0 + rx1) // 2, (ry0 + ry1) // 2), ((rx1 - rx0) // 2, (ry1 - ry0) // 2), 0, 0, 360, 1, -1)
            mm = mm.astype(bool)
        else:
            mm = db > thr
        mm = cv2.morphologyEx((mm & rg).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mm = cv2.morphologyEx(mm, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(mm)
        big = np.zeros_like(mm)
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] > 300:
                big[lab == i] = 1
        ff = big.copy()
        cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
        filled = (big | (1 - ff)).astype(np.uint8)
        g = int(grow) * 2 + 1
        m |= cv2.dilate(filled, np.ones((g, g), np.uint8)).astype(bool) & rg
    a = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 3) * region
    a = a[..., None]
    comp = l2s(lo * (1 - a) + lr * a)
    out = base.copy()
    out[y0:y1, x0:x1] = np.clip(comp, 0, 1)
    o8 = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(o8).save(os.path.join(RAW, J["out"] + "-composite.png"))
    f8 = (np.clip(knee(out), 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(f8).save(os.path.join(HERE, J["out"] + ".png"))
    Image.fromarray((m * 255).astype(np.uint8)).save(os.path.join(RAW, J["out"] + "-mask.png"))
    b8 = (base * 255 + 0.5).astype(np.uint8)
    moved = np.abs(o8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
    allowed = np.zeros(moved.shape, bool)
    allowed[y0:y1, x0:x1] = region
    return dict(base=J["base"], crop_box=list(J["box"]), result=J["result"], regions_crop_px=J["regions"], rules=J["rules"], ecc_affine=np.round(M, 4).tolist(),
                colour_gain_linear=np.round(gain, 4).tolist(), mask_px=int(m.sum()), raw=f"raw/{J['out']}-composite.png", finished=J["out"] + ".png",
                nothing_else_moved=dict(px_changed_outside_region=int((moved & ~allowed).sum()), px_changed_inside=int((moved & allowed).sum())))


JAR_SCALE_X = 0.76      # the jar reads 132 x 201 px (h/w 1.52, its right edge mirrored about its axis); the card is 30 x 15 (h/w 2.0)


def jar():
    """Japandi A: the ED4 seedream pass left the jar's proportion as it was, so it is done in code (0 tokens): the jar (rim to foot)
    narrowed x0.76 about its vertical axis (x 666), height, base and mouth height kept. Its outline: the right edge (a strong gradient on
    every row) mirrored about the axis (the left shoulder is lit by the lantern and has no reliable edge). The strips it leaves: the
    background shifted in from 34 px beside the jar (along the bottom rails' own slope, -0.40 / -0.44), so the rails, sill edge and garden carry on."""
    base = load01(os.path.join(HERE, "raw/japandi-A-nano-banana-2.png"))
    H, W = base.shape[:2]
    L = cv2.cvtColor((base * 255).astype(np.uint8), cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32) * 100 / 255
    gx = cv2.Sobel(cv2.GaussianBlur(L, (0, 0), 1.2), cv2.CV_32F, 1, 0, ksize=3)
    AX = 666.0
    ytop, ybot = 922, 1129
    hw = np.zeros(H)
    for y in range(930, 1125):
        hw[y] = 680 + int(np.argmax(gx[y, 680:760])) - AX
    hw[930:1125] = np.convolve(np.r_[[hw[930]] * 4, hw[930:1125], [hw[1124]] * 4], np.ones(9) / 9, mode="same")[4:-4]
    hw[ytop:930] = hw[930] + 5          # the rim's lip
    hw[1125:ybot] = hw[1124]
    xx = np.arange(W)[None, :].astype(np.float32)
    yy = np.arange(H)[:, None]
    rows = (yy >= ytop) & (yy < ybot)
    old = rows & (np.abs(xx - AX) <= hw[:, None] + 4)          # with its dark antialiased edge
    new_a = np.clip(hw[:, None] * JAR_SCALE_X + 0.5 - np.abs(xx - AX), 0, 1) * rows
    # the new jar: each row of the old one sampled narrower about the axis
    jar_px = base.copy()
    for y in range(ytop, ybot):
        xs = np.arange(int(AX - hw[y] - 3), int(AX + hw[y] + 4))
        src = AX + (xs - AX) / JAR_SCALE_X
        for c in range(3):
            jar_px[y, xs, c] = np.interp(src, np.arange(W), base[y, :, c])
    # the strips: background shifted in from beside the jar: horizontally at the top rail (y < 945), below it along the bottom rails'
    # own slope, measured on their edges (left -0.40, right -0.44 px per px); 34 px, so no texture repeats next to itself
    def shifted(dx, dy):
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        return cv2.warpAffine(base, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    S_ = 34
    t = np.clip((yy - 945) / 15.0, 0, 1)[..., None].astype(np.float32)
    bgL = shifted(S_, 0) * (1 - t) + shifted(S_, -0.40 * S_) * t      # out(x, y) = base(x - 34, y [+ 13.6])
    bgR = shifted(-S_, 0) * (1 - t) + shifted(-S_, 0.44 * S_) * t     # out(x, y) = base(x + 34, y [- 15.0])
    bg = np.where((xx < AX)[..., None], bgL, bgR)
    oa = cv2.GaussianBlur(old.astype(np.float32), (0, 0), 2.0)[..., None]
    out = base * (1 - oa) + bg * oa
    na = new_a[..., None].astype(np.float32)
    out = out * (1 - na) + jar_px * na
    o8 = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(o8).save(os.path.join(RAW, "japandi-A-ed4-codefix.png"))
    Image.fromarray((np.clip(knee(out), 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(HERE, "japandi-A-ed4.png"))
    b8 = (base * 255 + 0.5).astype(np.uint8)
    moved = np.abs(o8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
    allowed = cv2.dilate(old.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    wmax = 2 * float(hw[930:1125].max())
    hgt = ybot - ytop
    return dict(base="raw/japandi-A-nano-banana-2.png", raw="raw/japandi-A-ed4-codefix.png", finished="japandi-A-ed4.png", scale_x=JAR_SCALE_X,
                axis_x=AX, size_px_before=[round(wmax, 1), hgt], size_px_after=[round(wmax * JAR_SCALE_X, 1), hgt],
                h_over_w_before=round(hgt / wmax, 2), h_over_w_after=round(hgt / (wmax * JAR_SCALE_X), 2),
                seedream_result_unused="raw/ed4-japandi-A-seedream.png (the pass left the jar's proportion as it was)",
                nothing_else_moved=dict(px_changed_outside_silhouette=int((moved & ~allowed).sum()), px_changed_inside=int((moved & allowed).sum())))


def sheet():
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    R = json.load(open(REC))
    rows = []
    for k, J in JOBS.items():
        if k not in R:
            continue
        x0, y0, x1, y1 = J["box"]
        before = Image.open(os.path.join(HERE, J["base"])).convert("RGB").crop((x0, y0, x1, y1))
        after = Image.open(os.path.join(HERE, J["out"] + ".png")).convert("RGB").crop((x0, y0, x1, y1))
        s = 560 / before.height
        before = before.resize((int(before.width * s), 560), Image.LANCZOS)
        after = after.resize((int(after.width * s), 560), Image.LANCZOS)
        rows.append((k, before, after, R[k].get("note", "")))
    W = 40 + 2 * max(r[1].width for r in rows) + 30
    H = 70 + len(rows) * (560 + 80)
    out = Image.new("RGB", (W, H), (250, 249, 247))
    d = ImageDraw.Draw(out)
    d.text((20, 18), "ED4 (2026-11-06): four targeted fidelity passes, seedream-5-pro on a local crop, masked back in code. TEST, not for the site.",
           fill=(0, 0, 0), font=fb)
    y = 70
    for k, b, a, note in rows:
        d.text((20, y), f"{k}: before (left) / after (right)   {note}", fill=(0, 0, 0), font=f)
        out.paste(b, (20, y + 30))
        out.paste(a, (40 + b.width, y + 30))
        y += 560 + 80
    p = os.path.join(HERE, "ed4-sheet.jpg")
    out.save(p, quality=90)
    print(p, out.size)


if __name__ == "__main__":
    R = json.load(open(REC)) if os.path.exists(REC) else dict(date="2026-11-06", by="render-agent", decision="ED4", budget=2600)
    for k in sys.argv[1:]:
        if k == "sheet":
            sheet()
            continue
        if k == "jar":
            R.setdefault("japandi-A", {}).update(jar())
            print(json.dumps(R["japandi-A"], indent=0))
            continue
        r = one(k)
        R.setdefault(k, {}).update(r)
        print(k, json.dumps(r["nothing_else_moved"]), r["colour_gain_linear"], r["mask_px"])
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
