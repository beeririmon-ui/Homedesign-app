#!/usr/bin/env python3
"""
export_seq.py: cut a transition's playback frames into the site's frame sequences and write its manifest.

Input: PNG frames uniform in path progress at the play rate (60 fps, brief §8.1), 1920x1080 for desktop and the
648x1080 phone sequence (the moving 3:5 window), as written by pan_reproject.py (pan-only transitions) or by the
assembly step that joins pans and retimed video segments.

Output (assets/frames/<from>--<to>.<style>/):
  1920/0001.avif ... + .webp     desktop, 16:9
  1080/0001.avif ... + .webp     small screens / tablets, 16:9 (1080x608)
  mobile/0001.avif ... + .webp   phone, 3:5 (648x1080)
  manifest.json                  frames, fps, play time, easing, sizes, bytes, segments, swap blends, QA state
  preview-desktop.mp4, preview-mobile.mp4   the eased playback for review (not loaded by the site)

WebP is the fallback for browsers without AVIF; on the phone it is cut at every second frame (30 fps) to stay in
the weight budget, and the player blends between frames.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pan_reproject as pr  # noqa: E402

VARIANTS = {
    # name: (source, size, avif quality, webp quality, webp step)
    "1920": ("desktop", (1920, 1080), 55, 75, 1),
    "1080": ("desktop", (1080, 608), 50, 72, 1),
    "mobile": ("mobile", (648, 1080), 40, 60, 2),
}
MOBILE_BUDGET_PER_2S = 1.5e6   # bytes, phone, AVIF (motion-agent brief)


def encode(src: str, dst_base: str, size, aq: int, wq: int, webp: bool) -> tuple[int, int]:
    im = Image.open(src).convert("RGB")
    if im.size != tuple(size):
        im = im.resize(size, Image.LANCZOS)
    im.save(dst_base + ".avif", "AVIF", quality=aq, speed=6)
    a = os.path.getsize(dst_base + ".avif")
    w = 0
    if webp:
        im.save(dst_base + ".webp", "WEBP", quality=wq, method=6)
        w = os.path.getsize(dst_base + ".webp")
    return a, w


def preview(frames_dir: str, fps: float, play_s: float, out: str) -> None:
    """The eased playback as the site will show it (frames are uniform in progress; time is eased)."""
    names = sorted(f for f in os.listdir(frames_dir) if f.endswith(".png"))
    n = len(names)
    tmp = out + ".frames"
    os.makedirs(tmp, exist_ok=True)
    m = int(round(play_s * fps))
    for j in range(m):
        p = pr.ease(j / (m - 1)) * (n - 1)
        i = int(np.floor(p))
        f = p - i
        a = np.asarray(Image.open(os.path.join(frames_dir, names[i])).convert("RGB")).astype(np.float32)
        if f > 1e-3 and i + 1 < n:
            b = np.asarray(Image.open(os.path.join(frames_dir, names[i + 1])).convert("RGB")).astype(np.float32)
            a = a * (1 - f) + b * f
        Image.fromarray(np.clip(a + 0.5, 0, 255).astype(np.uint8)).save(os.path.join(tmp, f"{j + 1:04d}.png"), compress_level=1)
    # half a second of the landing frame, so the end can be judged
    last = os.path.join(tmp, f"{m:04d}.png")
    for k in range(int(fps // 2)):
        os.link(last, os.path.join(tmp, f"{m + k + 1:04d}.png"))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "%04d.png"),
                    "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-an", out], check=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--desktop", required=True, help="dir of 1920x1080 PNGs (0001.png ...)")
    ap.add_argument("--mobile", help="dir of 648x1080 PNGs")
    ap.add_argument("--out", required=True, help="assets/frames/<from>--<to>.<style>")
    ap.add_argument("--id", required=True)
    ap.add_argument("--from", dest="frm", required=True)
    ap.add_argument("--to", required=True)
    ap.add_argument("--style", default="nordic")
    ap.add_argument("--play-s", type=float, required=True)
    ap.add_argument("--fps", type=float, default=60.0)
    ap.add_argument("--mobile-window", help="c0,c1")
    ap.add_argument("--segments", default="[]", help="JSON list: [{type, p:[a,b], source, ...}]")
    ap.add_argument("--note", default="")
    ap.add_argument("--temporary", action="store_true", help="test asset: not QA'd, not for the site")
    ap.add_argument("--no-preview", action="store_true")
    a = ap.parse_args(argv)

    os.makedirs(a.out, exist_ok=True)
    srcs = {"desktop": sorted(os.path.join(a.desktop, f) for f in os.listdir(a.desktop) if f.endswith(".png"))}
    if a.mobile:
        srcs["mobile"] = sorted(os.path.join(a.mobile, f) for f in os.listdir(a.mobile) if f.endswith(".png"))
    n = len(srcs["desktop"])
    if a.mobile and len(srcs["mobile"]) != n:
        raise SystemExit("desktop and mobile frame counts differ")
    sizes, bytes_ = {}, {}
    for name, (src, size, aq, wq, wstep) in VARIANTS.items():
        if src not in srcs:
            continue
        d = os.path.join(a.out, name)
        os.makedirs(d, exist_ok=True)
        jobs = [(p, os.path.join(d, f"{i + 1:04d}"), size, aq, wq, i % wstep == 0 or i == n - 1)
                for i, p in enumerate(srcs[src])]
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
            res = list(ex.map(lambda j: encode(*j), jobs))
        sizes[name] = dict(w=size[0], h=size[1], avif_quality=aq, webp_quality=wq,
                           webp_frames=sum(1 for j in jobs if j[5]), webp_fps=a.fps / wstep)
        bytes_[name] = dict(avif=sum(r[0] for r in res), webp=sum(r[1] for r in res))
    per2 = {k: dict(avif=round(v["avif"] / a.play_s * 2), webp=round(v["webp"] / a.play_s * 2)) for k, v in bytes_.items()}
    man = dict(
        id=a.id, **{"from": a.frm}, to=a.to, style=a.style,
        frames=n, fps=a.fps, play_s=a.play_s,
        sampling="uniform-progress: frame i sits at progress i/(frames-1) along the path, at constant speed inside each "
                 "segment and matched speed across joins; the player maps time to progress with the easing",
        easing=dict(type="bible-ease-in-out-cubic", accel=0.15, land=0.30,
                    velocity="cubic smoothstep ramps over the first 15 % and the last 30 % of play_s, constant between",
                    reverse="the same frames played from last to first with the same curve in time"),
        reverse=True,
        path="{variant}/{index:04d}.{ext}",
        variants=sizes, formats=["avif", "webp"],
        mobile=dict(window_u=[float(x) for x in a.mobile_window.split(",")] if a.mobile_window else None,
                    frac=pr.MOBILE_FRAC, rule="full-height 3:5 window, centre moves linearly in progress (eased in time)"),
        first_frame=f"{a.frm}: identical to the master at this size", last_frame=f"{a.to}: identical to the master at this size",
        segments=json.loads(a.segments),
        swap=dict(blend_in_ms=180, blend_out_ms=180,
                  rule="the player cross-fades from the composed room (current variants) to frame 1, and from the last "
                       "frame to the composed room; footage is rendered with the default products"),
        bytes=bytes_, bytes_per_2s=per2,
        mobile_budget=dict(limit_per_2s=MOBILE_BUDGET_PER_2S,
                           avif_ok=(per2.get("mobile", {}).get("avif", 0) <= MOBILE_BUDGET_PER_2S) if "mobile" in per2 else None),
        qa="pending", temporary=bool(a.temporary), note=a.note)
    with open(os.path.join(a.out, "manifest.json"), "w") as fh:
        json.dump(man, fh, indent=1, ensure_ascii=False)
    if not a.no_preview:
        preview(a.desktop, a.fps, a.play_s, os.path.join(a.out, "preview-desktop.mp4"))
        if a.mobile:
            preview(a.mobile, a.fps, a.play_s, os.path.join(a.out, "preview-mobile.mp4"))
    print(json.dumps(dict(frames=n, bytes=bytes_, bytes_per_2s=per2, mobile_budget=man["mobile_budget"]), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
