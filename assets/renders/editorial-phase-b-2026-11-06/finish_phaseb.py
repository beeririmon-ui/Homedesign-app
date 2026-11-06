#!/usr/bin/env python3
"""
finish_phaseb.py: editorial phase B (briefs/render-editorial-phase-b-2026-11-06.md, ED2 / ED3), render-agent, 2026-11-06, 0 tokens.
  nordicA   the size fixes in code on the seedream finishing pass of Nordic A (QA: the travertine block wall lights 2.6-3x their 8 x 16,
            the pendant 50-65 cm for its 40): each wall light with its glow scaled about its centre (the glow as light added to the wall,
            the wall under it rebuilt from its surroundings with the wall's own grain); the pendant scaled about its cable's ceiling point
  finish    light finishing for the seven frames: a soft highlight knee per channel (0.90 -> 0.985), nothing else; raws stay in raw/
  sheet     the owner's 7-frame sheet with the locked M0 v6 small and a product list with quick fidelity notes per frame
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RAW = os.path.join(HERE, "raw")
SCONCE_SCALE = 0.36
PENDANT_SCALE = 0.70
SUN_TOP = 548                     # the top of the sun stripes on the back wall in the Nordic A seedream frame (px)


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((np.clip(x, 0, None) + 0.055) / 1.055) ** 2.4)


def l2s(x):
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def load01(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255


def fill(img, mask, grain_shift=None):
    """the masked area rebuilt as plain wall: a smooth fill (Telea at quarter size, upsampled, blurred) plus fine plaster grain of the std
    measured on the plain wall round it (synthetic, so no structure is copied in)"""
    H, W = img.shape[:2]
    small = cv2.resize((img * 255).astype(np.uint8), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    ms = cv2.dilate(cv2.resize(mask.astype(np.uint8), (W // 4, H // 4), interpolation=cv2.INTER_NEAREST), np.ones((3, 3), np.uint8))
    fs = cv2.inpaint(small, ms, 5, cv2.INPAINT_TELEA)
    low = cv2.GaussianBlur(cv2.resize(fs, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255, (0, 0), 6)
    hp = img - cv2.GaussianBlur(img, (0, 0), 2)
    ring = cv2.dilate(mask.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool) & ~mask
    g = np.abs(cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY), cv2.CV_32F, ksize=3))
    plain = ring & (g < np.percentile(g[ring], 60))
    sd = float(np.std(hp[plain].mean(1))) if plain.any() else 0.004
    rng = np.random.default_rng(11)
    nz = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.8)
    nz = nz / max(float(nz.std()), 1e-6) * sd
    a = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 2)[..., None]
    return np.clip(img * (1 - a) + np.clip(low + nz[..., None], 0, 1) * a, 0, 1)


def body_bbox(img, box):
    """the wall light's body in a rough box: the textured, brighter-than-wall block (largest component of high local contrast)"""
    x0, y0, x1, y1 = box
    sub = img[y0:y1, x0:x1]
    L = cv2.cvtColor(sub, cv2.COLOR_RGB2LAB)[..., 0]
    tex = cv2.GaussianBlur(np.abs(L - cv2.GaussianBlur(L, (0, 0), 2)), (0, 0), 4)
    m = (tex > np.percentile(tex, 70)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, _ = st[k]
    return x0 + x, y0 + y, x0 + x + w, y0 + y + h


def nordic_a():
    src = os.path.join(RAW, "nordic-A-fin-seedream.png")
    a = load01(src)
    H, W = a.shape[:2]
    out = a.copy()
    rec = dict(source="raw/nordic-A-fin-seedream.png", sconce_scale=SCONCE_SCALE, pendant_scale=PENDANT_SCALE, sconces=[])
    # 1. the two travertine block wall lights (rough boxes read on the frame), with their glow
    for rough in [(1040, 330, 1200, 600), (2020, 300, 2180, 600)]:
        bx0, by0, bx1, by1 = body_bbox(a, rough)
        cx, cy = 0.5 * (bx0 + bx1), 0.5 * (by0 + by1)
        bw, bh = bx1 - bx0, by1 - by0
        # the region the light reaches (body and glow), rebuilt as plain wall
        gx0, gy0 = int(cx - 1.1 * bw), int(cy - 0.9 * bh)
        gx1, gy1 = int(cx + 1.1 * bw), max(min(int(cy + 0.9 * bh), SUN_TOP), by1 + 8)   # not into the sun patch (kept), but the whole body
        reg = np.zeros((H, W), bool)
        reg[gy0:gy1, gx0:gx1] = True
        # not the leaves or a frame that reach into the box: strong edges outside the body, grown
        gg = np.abs(cv2.Laplacian(cv2.GaussianBlur(cv2.cvtColor(out, cv2.COLOR_RGB2GRAY), (0, 0), 1.0), cv2.CV_32F, ksize=3))
        objs = (gg > 0.035) & reg
        objs[by0 - 6:by1 + 6, bx0 - 6:bx1 + 6] = False
        objs = cv2.dilate(objs.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
        n_, lab_, st_, _ = cv2.connectedComponentsWithStats(objs.astype(np.uint8))
        keep_o = np.zeros((H, W), bool)
        for i in range(1, n_):
            if st_[i, cv2.CC_STAT_AREA] > 1500:
                keep_o |= lab_ == i
        reg &= ~keep_o
        body = np.zeros((H, W), bool)
        body[by0:by1, bx0:bx1] = True
        clean = fill(out, reg)
        # the glow: what the light adds to the wall (linear, >= 0), outside the body; the body: opaque
        glow = np.clip(s2l(out) - s2l(clean), 0, None) * (~body)[..., None] * reg[..., None]
        A = np.array([[SCONCE_SCALE, 0, cx - SCONCE_SCALE * cx], [0, SCONCE_SCALE, cy - SCONCE_SCALE * cy]], np.float32)
        glow_s = cv2.warpAffine(glow, A, (W, H), flags=cv2.INTER_AREA)
        bal = cv2.GaussianBlur(body.astype(np.float32), (0, 0), 0.7)
        body_c = cv2.warpAffine(out * bal[..., None], A, (W, H), flags=cv2.INTER_AREA)
        body_a = np.clip(cv2.warpAffine(bal, A, (W, H), flags=cv2.INTER_AREA), 0, 1)
        lit = np.clip(l2s(s2l(clean) + glow_s), 0, 1)
        out = np.where(reg[..., None], lit, out)
        out = out * (1 - body_a[..., None]) + np.clip(body_c / np.maximum(body_a[..., None], 1e-4), 0, 1) * body_a[..., None]
        rec["sconces"].append(dict(body_px=[int(bx0), int(by0), int(bx1), int(by1)], size_px_before=[int(bw), int(bh)],
                                   size_px_after=[round(bw * SCONCE_SCALE, 1), round(bh * SCONCE_SCALE, 1)], centre=[round(cx, 1), round(cy, 1)]))
    # 2. the pendant: scaled about its cable's ceiling point
    # the shade: its right half is in shade at the wall's own L, so it is drawn as read on the frame's edges (gradient maxima):
    # a flattened ellipse x 1146-1578, y 94-306 (the diffuser ring inside its bottom)
    shm = np.zeros((H, W), np.uint8)
    cv2.ellipse(shm, (1362, 200), (216, 106), 0, 0, 360, 1, -1)
    shade = cv2.dilate(shm, np.ones((7, 7), np.uint8)).astype(bool)
    ys, xs = np.nonzero(shade)
    sy0 = int(ys.min())
    cxp = 1362.0
    # the cable: a thin dark line above the shade
    L = cv2.cvtColor(out, cv2.COLOR_RGB2LAB)[..., 0]
    cable = np.zeros((H, W), bool)
    c0, c1 = int(cxp - 12), int(cxp + 12)
    band = L[0:sy0 + 4, c0:c1]
    med = np.median(band, axis=1, keepdims=True)
    cable[0:sy0 + 4, c0:c1] = (med - band) > 12
    pend = shade | cable
    pend = cv2.dilate(pend.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    ys2, xs2 = np.nonzero(pend)
    anchor = (cxp, 0.0)
    A = np.array([[PENDANT_SCALE, 0, anchor[0] * (1 - PENDANT_SCALE)], [0, PENDANT_SCALE, 0]], np.float32)
    pal = cv2.GaussianBlur(pend.astype(np.float32), (0, 0), 0.8)
    pc = cv2.warpAffine(out * pal[..., None], A, (W, H), flags=cv2.INTER_AREA)
    pa = np.clip(cv2.warpAffine(pal, A, (W, H), flags=cv2.INTER_AREA), 0, 1)
    hole = cv2.dilate(pend.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    out = fill(out, hole)
    out = out * (1 - pa[..., None]) + np.clip(pc / np.maximum(pa[..., None], 1e-4), 0, 1) * pa[..., None]
    new_bottom = int(np.nonzero(pa > 0.5)[0].max())
    # the triptych's top (the dark frame line under the pendant): the first strong dark row below the pendant in its column band
    col = L[:, int(cxp - 300):int(cxp + 300)]
    dark_rows = np.nonzero((col < 50).mean(1) > 0.3)[0]
    trip_top = int(dark_rows[dark_rows > new_bottom].min()) if (dark_rows > new_bottom).any() else None
    rec["pendant"] = dict(anchor_px=[round(cxp, 1), 0], shade_px_before=[int(xs.min()), int(sy0), int(xs.max()), int(ys.max())],
                          bottom_px_after=new_bottom, triptych_top_px=trip_top,
                          gap_to_triptych_frame=round((trip_top - new_bottom) / H, 3) if trip_top else None)
    o8 = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(o8).save(os.path.join(RAW, "nordic-A-fin-codefix.png"))
    print(json.dumps(rec, indent=0))
    return rec


def knee(x, k=0.90, top=0.985):
    return np.where(x > k, k + (top - k) * np.tanh((x - k) / (top - k)), x)


FRAMES = [("nordic-A-fin", "raw/nordic-A-fin-codefix.png", "Nordic A, finished", "gpt base + seedream pass + code (lights x0.36, pendant x0.70)"),
          ("nordic-B-fin", "raw/nordic-B-fin-seedream.png", "Nordic B, finished", "nano-banana-2 base + seedream-5-pro pass"),
          ("warm-modern-A-fin", "raw/warm-modern-A-fin-seedream.png", "Warm modern A, finished", "gpt-image-2-5 base + seedream-5-pro pass"),
          ("boho-A", "raw/boho-A-gpt-image-2-5.png", "Boho A", "gpt-image-2-5 sunburst"),
          ("mediterranean-A", "raw/mediterranean-A-gpt-image-2-5.png", "Mediterranean A", "gpt-image-2-5 sunburst"),
          ("modern-country-A", "raw/modern-country-A-gpt-image-2-5.png", "Modern country A", "gpt-image-2-5 sunburst"),
          ("japandi-A", "raw/japandi-A-nano-banana-2.png", "Japandi A", "nano-banana-2")]


def finish():
    rec = {}
    for fid, raw, title, model in FRAMES:
        p = os.path.join(HERE, raw)
        if not os.path.exists(p):
            continue
        a = load01(p)
        clip0 = float((a.max(2) >= 254.5 / 255).mean() * 100)
        o8 = (np.clip(knee(a), 0, 1) * 255 + 0.5).astype(np.uint8)
        Image.fromarray(o8).save(os.path.join(HERE, fid + ".png"))
        rec[fid] = dict(raw=raw, clipped_pct_before=round(clip0, 3), px_at_255_after=int((o8.max(2) >= 255).sum()), how="a soft knee per channel 0.90 -> 0.985 only")
        print(fid, rec[fid])
    J = json.load(open(os.path.join(HERE, "jobs.json")))
    J["finishing"] = rec
    json.dump(J, open(os.path.join(HERE, "jobs.json"), "w"), indent=1, ensure_ascii=False)


def sheet():
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    J = json.load(open(os.path.join(HERE, "jobs.json")))
    notes = J.get("product_notes_render_agent", {})
    w, h, G = 1280, 720, 30
    NT = 150
    W = 2 * w + 3 * G
    H = 80 + 4 * (h + 46 + NT) + 20
    out = Image.new("RGB", (W, H), (250, 249, 247))
    d = ImageDraw.Draw(out)
    d.text((G, 22), "Editorial phase B (ED2 / ED3, 2026-11-06): three finished frames + four styles. TEST, not for the site. Products by reference.",
           fill=(0, 0, 0), font=fb)
    tok = {j["id"]: j["tokens"] for j in J["jobs"]}
    cells = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2), (0, 3)]
    for (fid, raw, title, model), (cx, cy) in zip(FRAMES, cells):
        p = os.path.join(HERE, fid + ".png")
        x, y = G + cx * (w + G), 80 + cy * (h + 46 + NT)
        if os.path.exists(p):
            im = Image.open(p).convert("RGB").resize((w, h), Image.LANCZOS)
            out.paste(im, (x, y))
        else:
            d.rectangle((x, y, x + w, y + h), fill=(226, 223, 218), outline=(160, 156, 150), width=3)
            d.text((x + 60, y + h // 2 - 40), "Not fetched: the job is submitted and paid,", fill=(70, 70, 70), font=fb)
            d.text((x + 60, y + h // 2 + 4), "but var2 asked for sign-in before the result came back.", fill=(70, 70, 70), font=fb)
        d.text((x, y + h + 8), f"{title}  |  {model}  |  {tok.get(fid, '?')} tokens", fill=(0, 0, 0), font=f)
        yy = y + h + 40
        for ln in notes.get(fid, [])[:6]:
            d.text((x, yy), ln[:150], fill=(60, 60, 60), font=fs)
            yy += 22
    m0 = Image.open(os.path.join(REPO, "assets/renders/living-room/nordic/v9/m0-1-2-products-fix2-frame-fix-v6.png")).convert("RGB")
    m0 = m0.resize((w * 3 // 4, h * 3 // 4), Image.LANCZOS)
    x, y = G + (w + G), 80 + 3 * (h + 46 + NT)
    out.paste(m0, (x, y))
    d.text((x, y + m0.size[1] + 8), "For comparison: the old locked Nordic M0 (v6)", fill=(70, 70, 70), font=fs)
    p = os.path.join(HERE, "sheet.jpg")
    out.save(p, quality=90)
    print(p, out.size)


if __name__ == "__main__":
    w = sys.argv[1]
    if w == "nordicA":
        nordic_a()
    if w == "finish":
        finish()
    if w == "sheet":
        sheet()
