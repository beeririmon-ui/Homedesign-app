#!/usr/bin/env python3
"""
finish_sheet.py: the editorial-frame test (briefs/render-editorial-test-2026-11-06.md, ED1), render-agent, 2026-11-06, 0 tokens.
  finish  light finishing only (the brief): a gentle white balance where the frame leans too orange, and a highlight roll-off so nothing clips
          (a soft knee per channel from 0.90, ceiling 0.985); no exposure targets, nothing that flattens the light -> <style>/<id>.jpg (q 95)
  sheet   the owner's sheet: the five frames large, labelled style / frame / model, and the current Nordic M0 small -> sheet.jpg
The raws stay in <style>/raw/.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FRAMES = [("nordic", "nordic-A-nano-banana-2", "nordic/raw/nordic-A-nano-banana-2.jpg", "Nordic, frame A (wide editorial)", "nano-banana-2, 2K", (1.0, 1.0, 1.0)),
          ("nordic", "nordic-A-gpt-image-2-5", "nordic/raw/nordic-A-gpt-image-2-5.png", "Nordic, frame A (same brief)", "gpt-image-2-5 sunburst, 2K", (0.97, 1.0, 1.04)),
          ("nordic", "nordic-B-nano-banana-2", "nordic/raw/nordic-B-nano-banana-2.png", "Nordic, frame B (window-corner vignette)", "nano-banana-2, 2K", (1.0, 1.0, 1.0)),
          ("warm-modern", "warm-modern-A-nano-banana-2", "warm-modern/raw/warm-modern-A-nano-banana-2.jpg", "Warm modern, frame A", "nano-banana-2, 2K", (1.0, 1.0, 1.0)),
          ("warm-modern", "warm-modern-A-gpt-image-2-5", "warm-modern/raw/warm-modern-A-gpt-image-2-5.png", "Warm modern, frame A (same brief)", "gpt-image-2-5 sunburst, 2K", (0.95, 1.0, 1.06))]
M0 = os.path.join(REPO, "assets/renders/living-room/nordic/v9/m0-1-2-products-fix2-frame-fix-v6.png")


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((np.clip(x, 0, None) + 0.055) / 1.055) ** 2.4)


def l2s(x):
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def knee(x, k=0.90, top=0.985):
    return np.where(x > k, k + (top - k) * np.tanh((x - k) / (top - k)), x)


def finish():
    rec = {}
    for style, fid, raw, title, model, wb in FRAMES:
        a = np.asarray(Image.open(os.path.join(HERE, raw)).convert("RGB")).astype(np.float32) / 255
        clip0 = float((a.max(2) >= 254.5 / 255).mean() * 100)
        lin = s2l(a) * np.array(wb, np.float32)
        lin = lin / max(1.0, float((np.array(wb) * np.array([0.2126, 0.7152, 0.0722])).sum()))     # keep the mean luminance
        out = knee(np.clip(l2s(lin), 0, 1.2))
        o8 = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
        p = os.path.join(HERE, style, fid + ".jpg")
        Image.fromarray(o8).save(p, quality=95)
        rec[fid] = dict(raw=raw, finished=os.path.relpath(p, REPO), size=list(a.shape[1::-1]), white_balance_linear_rgb=list(wb),
                        clipped_pct_before=round(clip0, 3), px_at_255_after=int((o8.max(2) >= 255).sum()),
                        how="white balance (linear gains, mean luminance kept) only where the frame leaned orange; a soft knee per channel from 0.90 to 0.985")
        print(fid, rec[fid]["clipped_pct_before"], rec[fid]["px_at_255_after"])
    J = json.load(open(os.path.join(HERE, "jobs.json")))
    J["finishing"] = rec
    json.dump(J, open(os.path.join(HERE, "jobs.json"), "w"), indent=1, ensure_ascii=False)


def sheet():
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    w, h = 1280, 720
    G = 30
    W = 2 * w + 3 * G
    H = 80 + 3 * (h + 60) + 20
    out = Image.new("RGB", (W, H), (250, 249, 247))
    d = ImageDraw.Draw(out)
    d.text((G, 22), "Editorial-frame test (ED1, 2026-11-06): the living room, Nordic and warm modern. TEST, not for the site. Products by reference; no clay lock.",
           fill=(0, 0, 0), font=fb)
    J = json.load(open(os.path.join(HERE, "jobs.json")))
    tok = {j["id"]: j["tokens"] for j in J["jobs"]}
    pos = [(0, 0), (1, 0), (0, 1), (0, 2), (1, 2)]
    for (style, fid, raw, title, model, wb), (cx, cy) in zip(FRAMES, pos):
        im = Image.open(os.path.join(HERE, style, fid + ".jpg")).convert("RGB").resize((w, h), Image.LANCZOS)
        x, y = G + cx * (w + G), 80 + cy * (h + 60)
        out.paste(im, (x, y))
        d.text((x, y + h + 10), f"{title}  |  {model}  |  {tok.get(fid, '?')} tokens", fill=(0, 0, 0), font=f)
    # the current Nordic M0, small, in the free cell
    m0 = Image.open(M0).convert("RGB").resize((w * 3 // 4, h * 3 // 4), Image.LANCZOS)
    x, y = G + (w + G), 80 + (h + 60)
    out.paste(m0, (x, y))
    d.text((x, y + m0.size[1] + 10), "For comparison: the current Nordic M0 (locked camera, products fix2, graded v6)", fill=(70, 70, 70), font=fs)
    p = os.path.join(HERE, "sheet.jpg")
    out.save(p, quality=90)
    print(p, out.size)


if __name__ == "__main__":
    if sys.argv[1] == "finish":
        finish()
    if sys.argv[1] == "sheet":
        sheet()
