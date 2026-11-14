#!/usr/bin/env python3
"""
export_arrival.py: the whole arrival from the front door (storyboard S1) as the site's frame sequences, a manifest
and a master clip, from the two banks (assemble.py) and the stills. 0 var2 tokens.

  door (code) -> bank 1, D0 -> HD (the leaf still swinging over its first frames) -> the turn (code, HD + HDx)
  -> bank 2, HDx -> M0, landing -> hold

Every frame is made for its moment on the timeline of the chosen version (arrival_timeline.py): the frames are
UNIFORM IN TIME, so the player only plays them at a fixed rate. The fast version is another export from the same
banks and stills (0 tokens). The version inside U5 (a cut at HD in place of the turn) is the same files with the
turn's frames skipped: the manifest gives the range.

Output (--out, e.g. assets/frames/d0--m0.warm-modern/):
  1920/0001.avif + .webp   60 stored frames per second (desktop)
  1080/0001.avif + .webp   30 stored frames per second, 1080 x 608 (phone, whole frame, FB2); each is the mean of
                           the 60 fps frames around it (0.25, 0.5, 0.25): motion blur as long as the frame spacing,
                           so that the player's blend of two neighbours at 60 Hz reads as motion
  manifest.json            frames, rates, sizes, bytes, segments, the cut range, what to load before the press
  --mp4 PATH               the master / preview, H.264, 60 fps, no audio

  python3 export_arrival.py --bank1 DIR --bank2 DIR --d0 D0.png --canvas-d0 base --hd HD.png --hdx HDx.png --canvas-turn tall
                            --version 7.3 --out DIR [--only 1080] [--w 1920] [--mp4 out.mp4] [--temporary] [--note "..."]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arrival_timeline as tl  # noqa: E402
import camgeo as cg  # noqa: E402
import turn_door as td  # noqa: E402

PHONE_BUDGET_PER_2S = 1.5e6      # bytes, phone, AVIF (motion-agent standing brief)
FIRST_LOAD_BUDGET = 3.0e6        # bytes, phone (docs/skeleton-spec.md, "יעדי ביצועים": first load of a room)
ROOM_FIRST_LOAD = 1.13e6         # bytes, the living room's own first load on the phone as measured in MOCK2
D0_BYTES = 0.12e6                # bytes, the door image at 1080 (AVIF), an estimate until D0 exists


class Bank:
    """Frames uniform in distance (assemble.py). at(s) returns float RGB 0..1 at the output size."""

    def __init__(self, folder: str, length: float, w: int, h: int):
        self.names = sorted(f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".jpeg")) and f[:4].isdigit())
        if len(self.names) < 2:
            raise SystemExit(f"{folder}: no bank frames")
        self.folder, self.L, self.w, self.h = folder, length, w, h
        self.cache: dict = {}

    def _get(self, i: int) -> np.ndarray:
        if i not in self.cache:
            if len(self.cache) > 6:
                self.cache.pop(next(iter(self.cache)))
            im = cv2.cvtColor(cv2.imread(os.path.join(self.folder, self.names[i]), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
            if im.shape[1] != self.w or im.shape[0] != self.h:
                im = cv2.resize(im, (self.w, self.h), interpolation=cv2.INTER_AREA if im.shape[1] > self.w else cv2.INTER_CUBIC)
            self.cache[i] = im.astype(np.float32) / 255.0
        return self.cache[i]

    def at(self, s: float) -> np.ndarray:
        p = float(np.clip(s / self.L, 0, 1)) * (len(self.names) - 1)
        i = int(np.floor(p))
        f = p - i
        if f < 0.12 or i + 1 >= len(self.names):
            return self._get(i)
        if f > 0.88:
            return self._get(i + 1)
        return self._get(i) * (1 - f) + self._get(i + 1) * f


def encode(img8: np.ndarray, base: str, aq: int, wq: int) -> tuple[int, int]:
    im = Image.fromarray(img8)
    im.save(base + ".avif", "AVIF", quality=aq, speed=6)
    im.save(base + ".webp", "WEBP", quality=wq, method=4)
    return os.path.getsize(base + ".avif"), os.path.getsize(base + ".webp")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bank1", required=True)
    ap.add_argument("--bank2", required=True)
    ap.add_argument("--d0", required=True, help="the closed-door still (the leaf's texture, and frame 1)")
    ap.add_argument("--canvas-d0", default="base", choices=["base", "tall", "frame"])
    ap.add_argument("--hd", required=True)
    ap.add_argument("--hdx", required=True)
    ap.add_argument("--canvas-turn", default="tall", choices=["base", "tall", "frame"])
    ap.add_argument("--version", default="7.3", choices=sorted(tl.VERSIONS), help="the -cut versions are for a preview clip (--mp4-only): "
                    "on the site the cut is the same frames with the turn skipped")
    ap.add_argument("--desktop-fps", type=int, default=60, choices=[30, 60], help="stored frames per second of the 1920 sequence: 60, or 30 "
                    "with the same blur and neighbour blend as the phone (half the weight)")
    ap.add_argument("--mp4-only", action="store_true", help="write only the clip (--mp4), no sequences and no manifest")
    ap.add_argument("--out", required=True)
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--only", choices=["1920", "1080"], help="write one variant only")
    ap.add_argument("--mp4")
    ap.add_argument("--mp4-w", type=int, default=None)
    ap.add_argument("--style", default="warm-modern")
    ap.add_argument("--aq", type=int, default=40)
    ap.add_argument("--temporary", action="store_true", help="a test asset: not QA'd, not for the public site")
    ap.add_argument("--note", default="")
    a = ap.parse_args(argv)

    V = tl.VERSIONS[a.version]
    W, H = a.w, int(round(a.w * 9 / 16))
    fr = cg.Canvas.frame(W, H)
    b1, b2 = Bank(a.bank1, tl.L1, W, H), Bank(a.bank2, tl.L2, W, H)
    d0_full = td.load(a.d0)
    d0 = td.canvas_for(a.canvas_d0, d0_full.shape[1], d0_full.shape[0]).crop_frame(d0_full, W, H)
    hd, hdx = td.load(a.hd), td.load(a.hdx)
    T = td.Turn([td.Still(hd, cg.HD, td.canvas_for(a.canvas_turn, hd.shape[1], hd.shape[0]), "HD"),
                 td.Still(hdx, cg.HDX, td.canvas_for(a.canvas_turn, hdx.shape[1], hdx.shape[0]), "HDx")], None, 2.0, W)
    states = V.frames(60.0)
    n60 = len(states)
    worst_hole = 0.0

    def render(i: int) -> np.ndarray:
        nonlocal worst_hole
        st = states[i]
        if st["phase"] in ("door", "door+walk", "walk"):
            if st["s1"] <= 0 and st["door"] <= 0:
                return d0
            base = b1.at(st["s1"])
            if st["door"] < 90 - 1e-3:
                cam = cg.D0.moved(loc=(cg.D0.loc[0] - st["s1"], cg.D0.loc[1], cg.D0.loc[2]))
                return td.door_frame(base, d0, cam, fr, st["door"], cg.D0, fr)
            return base
        if st["phase"] == "turn":
            p0 = states[max(0, i - 1)]["turn"]
            p1 = states[min(n60 - 1, i + 1)]["turn"]
            f, hole = T.frame_blur(st["turn"], (p1 - p0) / 2)
            worst_hole = max(worst_hole, hole)
            return f
        return b2.at(st["s2"])

    variants = {"1920": dict(w=W, h=H, fps=a.desktop_fps, step=60 // a.desktop_fps), "1080": dict(w=1080, h=608, fps=30, step=2)}
    if a.only:
        variants = {a.only: variants[a.only]}
    if a.mp4_only:
        if not a.mp4:
            raise SystemExit("--mp4-only needs --mp4")
        variants = {}
    for name in variants:
        os.makedirs(os.path.join(a.out, name), exist_ok=True)
    ff = None
    if a.mp4:
        mw = a.mp4_w or W
        mh = int(round(mw * 9 / 16)) // 2 * 2
        os.makedirs(os.path.dirname(os.path.abspath(a.mp4)), exist_ok=True)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{mw}x{mh}", "-r", "60",
                               "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                               "-movflags", "+faststart", "-an", a.mp4], stdin=subprocess.PIPE)
    to8 = lambda x: np.clip(np.rint(x * 255.0), 0, 255).astype(np.uint8)
    sizes = {k: [] for k in variants}
    pool = ThreadPoolExecutor(max_workers=max(2, (os.cpu_count() or 4) - 1))
    futs = {k: [] for k in variants}
    ring: dict = {}
    n30 = (n60 + 1) // 2
    last_q = 60
    for i in range(n60):
        f = render(i)
        ring[i] = f
        ring.pop(i - 3, None)
        if ff:
            g = f if (mw, mh) == (W, H) else cv2.resize(f, (mw, mh), interpolation=cv2.INTER_AREA)
            ff.stdin.write(to8(g).tobytes())
        if "1920" in variants and a.desktop_fps == 60:
            q = last_q if i >= n60 - 10 else a.aq
            futs["1920"].append(pool.submit(encode, to8(f), os.path.join(a.out, "1920", f"{i + 1:04d}"), q, 72))
        # the 30 fps frame j sits at 60 fps frame 2j and is the mean of frames 2j-1, 2j, 2j+1
        half = [k for k in variants if variants[k]["fps"] == 30]
        if half:
            emit = []
            if i >= 1 and (i - 1) % 2 == 0:
                emit.append((i - 1) // 2)
            if i == n60 - 1 and i % 2 == 0:
                emit.append(i // 2)                               # the last centre has no successor
            for jj in emit:
                c = 2 * jj
                if jj == 0 or jj == n30 - 1 or c + 1 not in ring or c - 1 not in ring:
                    g = ring[c]                                   # the two end frames stay exact
                else:
                    g = 0.25 * ring[c - 1] + 0.5 * ring[c] + 0.25 * ring[c + 1]
                q = last_q if jj >= n30 - 5 else a.aq
                for k in half:
                    vw, vh = variants[k]["w"], variants[k]["h"]
                    gk = g if (vw, vh) == (W, H) else cv2.resize(g, (vw, vh), interpolation=cv2.INTER_AREA)
                    futs[k].append((jj, pool.submit(encode, to8(gk), os.path.join(a.out, k, f"{jj + 1:04d}"), q, 60 if k == "1080" else 72)))
    if ff:
        ff.stdin.close()
        ff.wait()
    if a.mp4_only:
        print(json.dumps(dict(version=V.name, mp4=a.mp4, frames_60fps=n60, play_s=round(V.t_end, 3), turn_worst_hole_frac=worst_hole), indent=1))
        return 0
    bytes_ = {}
    counts = {}
    for k in variants:
        if variants[k]["fps"] == 60:
            res = [x.result() for x in futs[k]]
        else:
            seen = {}
            for jj, x in futs[k]:
                seen[jj] = x.result()
            res = [seen[j] for j in sorted(seen)]
        counts[k] = len(res)
        sizes[k] = res
        bytes_[k] = dict(avif=int(sum(r[0] for r in res)), webp=int(sum(r[1] for r in res)))
    pool.shutdown()

    def seg_ranges(fps: int) -> dict:
        step = 60 // fps
        idx = list(range(0, n60, step))
        out: dict = {}
        for j, i in enumerate(idx):
            out.setdefault(states[i]["phase"], [j + 1, j + 1])[1] = j + 1
        return out

    play = V.t_end
    man = dict(
        id="T-D0", **{"from": "D0"}, to="M0", style=a.style, version=V.name, play_s=round(play, 3), hold_s=V.hold_s,
        timeline=V.summary(),
        sampling="uniform in time: frame i (1-based) of a variant is shown at (i - 1) / fps seconds; ramps, the turn's speed curve and the "
                 "landing are baked in. Reverse = the same frames from last to first.",
        path="{variant}/{index:04d}.{ext}", formats=["avif", "webp"],
        variants={k: dict(w=v["w"], h=v["h"], fps=v["fps"], frames=counts[k], avif_quality=a.aq, last_frames_quality=last_q,
                          segments=seg_ranges(v["fps"])) for k, v in variants.items()},
        bytes=bytes_,
        bytes_per_2s={k: dict(avif=round(b["avif"] / (play + V.hold_s) * 2), webp=round(b["webp"] / (play + V.hold_s) * 2)) for k, b in bytes_.items()},
        first_frame="D0: identical to the door still at this size", last_frame="M0: identical to the 16:9 frame of base.png at this size",
        cut_version=None if V.cut else dict(rule="the version inside U5: skip the frames of segment 'turn' (a cut HD -> HDx); play_s is shorter by the turn",
                                            play_s=round(play - V.turn_s, 3)),
        loading=dict(before_the_press="the door image (frame 1 is the same picture) and segments door, door+walk, walk",
                     stream="segments turn, dolly, landing, hold: requested at once, in play order; the button waits until they are in, or until "
                            "the measured rate puts their arrival before they are due with a 1.5x margin",
                     never="no frame is waited for during play: a late frame is skipped and counted"),
        turn_worst_hole_frac=worst_hole,
        swap=dict(blend_out_ms=200, rule="after the hold, a soft swap to the live layers of the empty room (the same picture)"),
        qa="pending", temporary=bool(a.temporary), note=a.note)
    if "1080" in bytes_:
        segs = man["variants"]["1080"]["segments"]
        pre_last = max(v[1] for k, v in segs.items() if k in ("door", "door+walk", "walk"))
        pre = int(sum(r[0] for r in sizes["1080"][:pre_last]))
        man["phone_budget"] = dict(per_2s_limit=PHONE_BUDGET_PER_2S, per_2s=man["bytes_per_2s"]["1080"]["avif"],
                                   per_2s_ok=man["bytes_per_2s"]["1080"]["avif"] <= PHONE_BUDGET_PER_2S,
                                   before_the_press_frames=pre_last, before_the_press_bytes=pre, streamed_bytes=bytes_["1080"]["avif"] - pre,
                                   first_load=int(D0_BYTES + pre), first_load_limit=FIRST_LOAD_BUDGET,
                                   first_load_ok=(D0_BYTES + pre) <= FIRST_LOAD_BUDGET,
                                   room_layers_stream_during_the_walk=int(ROOM_FIRST_LOAD),
                                   all_by_the_landing=int(D0_BYTES + bytes_["1080"]["avif"] + ROOM_FIRST_LOAD),
                                   rule="first load = the door image and the frames up to the turn; the rest of the frames and the living room's "
                                        "layers stream from the press, in play order (they are needed from the turn and from the landing)")
    with open(os.path.join(a.out, "manifest.json"), "w") as fh:
        json.dump(man, fh, indent=1, ensure_ascii=False)
    print(json.dumps(dict(version=V.name, frames=counts, bytes=bytes_, bytes_per_2s=man["bytes_per_2s"], phone_budget=man.get("phone_budget"),
                          turn_worst_hole_frac=worst_hole), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
