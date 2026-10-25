#!/usr/bin/env python3
"""
Close-up product references for the Phase B drafts (render-agent, 2026-10-25).

The designer's prompt headers (assets/prompts/recipe-v5.nordic/<frame>.txt) list the references in order:
    #   N https://...  (note)                      a supplier image
    #   N NAME: local scratchpad image <path> ...  a stand-in photo already on disk (Israeli rug picks)
    #   N A and M B: as in d1.txt                  cross-reference to another frame's list
This script downloads / loads each one, trims the uniform border and crops to the product (square around the non-background mass,
8 % padding), saves <= 1024 px JPEGs under refs/<slug>.jpg and records them in refs/index.json (keyed by the source URL or path, so a
product shared by several frames is prepared once). The var2 upload (request_upload + PUT) is a separate step that writes var2_url
into the index. Every card the designer names has usage_rights "unclear": the crops are internal render references only.

  python3 refs.py <frame>=<prompt.txt> [<frame>=<prompt.txt> ...]
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SCRATCH = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
REFS = os.path.join(HERE, "refs")
INDEX = os.path.join(REFS, "index.json")
URL_RE = re.compile(r"^#\s+(\d+)\s+(https?://\S+)\s*(?:\((.*)\))?\s*$")
LOCAL_RE = re.compile(r"^#\s+(\d+)\s+([A-Za-z]+):\s+local scratchpad image\s+(\S+)")
XREF_RE = re.compile(r"^#\s+(\d+)\s+(.*?):\s+as in ([a-z0-9-]+\.txt)")


def parse(path):
    """-> list of dict(n, kind, src, note) in header order."""
    out = []
    for line in open(path, encoding="utf-8"):
        if not line.startswith("#"):
            break
        m = URL_RE.match(line.rstrip())
        if m:
            out.append(dict(n=int(m.group(1)), kind="url", src=m.group(2), note=(m.group(3) or "").strip()))
            continue
        m = LOCAL_RE.match(line.rstrip())
        if m:
            out.append(dict(n=int(m.group(1)), kind="local", src=os.path.join(SCRATCH, m.group(3)), note=m.group(2)))
            continue
        m = XREF_RE.match(line.rstrip())
        if m:
            out.append(dict(n=int(m.group(1)), kind="xref", src=m.group(3), note=m.group(2)))
    return out


def fetch(url, timeout=60):
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", str(timeout), "-o", "-", url], capture_output=True)
    if r.returncode != 0 or len(r.stdout) < 2000:
        return None
    return r.stdout


def crop_product(im, pad=0.08):
    im = im.convert("RGB")
    a = np.asarray(im).astype(float)
    bg = np.median(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]), axis=0)
    m = np.abs(a - bg).sum(2) > 40
    if m.mean() < 0.01 or m.mean() > 0.97:
        return im
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    side = min(max(x1 - x0, y1 - y0) * (1 + 2 * pad), max(im.size))
    bx0, by0 = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
    bx1, by1 = int(min(im.size[0], cx + side / 2)), int(min(im.size[1], cy + side / 2))
    return im.crop((bx0, by0, bx1, by1))


def slug(s):
    s = re.sub(r"https?://", "", s)
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")
    return s[-60:]


def prepare(frames):
    os.makedirs(REFS, exist_ok=True)
    idx = json.load(open(INDEX)) if os.path.exists(INDEX) else {"refs": {}, "frames": {}, "missing": {}}
    lists = {fid: parse(p) for fid, p in frames.items()}
    for fid, refs in lists.items():
        order = []
        for r in refs:
            if r["kind"] == "xref":
                src_frame = next((f for f, p in frames.items() if os.path.basename(p) == r["src"]), None)
                for name in re.split(r"\s+and\s+\d+\s+|\s+and\s+", r["note"]):
                    name = name.strip()
                    for r2 in (lists.get(src_frame) or []):
                        if r2["kind"] == "local" and r2["note"].lower() == name.lower():
                            order.append(r2["src"])
                continue
            key = r["src"]
            if key not in idx["refs"] and key not in idx["missing"]:
                data = None
                if r["kind"] == "url":
                    data = fetch(key)
                elif os.path.exists(key):
                    data = open(key, "rb").read()
                if not data:
                    idx["missing"][key] = f"{fid} #{r['n']}: not downloadable / not on disk"
                    print("MISSING", fid, r["n"], key)
                    continue
                try:
                    im = Image.open(io.BytesIO(data))
                    im.load()
                except Exception as e:  # noqa: BLE001
                    idx["missing"][key] = f"{fid} #{r['n']}: not an image ({e})"
                    print("MISSING", fid, r["n"], key)
                    continue
                crop = crop_product(im)
                crop.thumbnail((1024, 1024), Image.LANCZOS)
                out = os.path.join(REFS, slug(key) + ".jpg")
                crop.save(out, quality=90)
                idx["refs"][key] = dict(file=os.path.relpath(out, REPO), kind=r["kind"], note=r["note"], source_size=list(im.size),
                                        crop_size=list(crop.size), sha256=hashlib.sha256(open(out, "rb").read()).hexdigest(), var2_url=None,
                                        usage="internal render reference only (usage_rights unclear on every card)")
                print("ref", fid, r["n"], im.size, "->", crop.size, r["note"][:40])
            if key in idx["refs"]:
                order.append(key)
        idx["frames"][fid] = order
    json.dump(idx, open(INDEX, "w"), indent=1, ensure_ascii=False)
    return idx


if __name__ == "__main__":
    frames = {}
    for a in sys.argv[1:]:
        fid, p = a.split("=", 1)
        frames[fid] = p
    idx = prepare(frames)
    for fid, order in idx["frames"].items():
        print(fid, len(order), "refs")
