"""Probe: gradient peaks per column / row band in the clay and the render (M0 1.2), to identify the shell lines before measuring."""
import sys
import cv2
import numpy as np
from PIL import Image

R = "/home/user/homedesign-app/"
W, H = 1920, 1080


def crop16(a):
    h, w = a.shape[:2]
    sx, sy = w / 4072, h / 2290
    return a[int(round(65 * sy)):int(round(2225 * sy)), int(round(116 * sx)):int(round(3956 * sx))]


def g(p):
    a = np.asarray(Image.open(R + p).convert("RGB"))
    a = cv2.resize(crop16(a), (W, H), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), 1.0)


def peaks(prof, lo, hi, rel=0.3, sep=4):
    seg = prof[lo:hi]
    thr = rel * seg.max()
    out = []
    for i in range(1, len(seg) - 1):
        if seg[i] >= thr and seg[i] >= seg[i - 1] and seg[i] >= seg[i + 1]:
            if out and i + lo - out[-1][0] < sep:
                if seg[i] > out[-1][1]:
                    out[-1] = (i + lo, round(float(seg[i]), 1))
                continue
            out.append((i + lo, round(float(seg[i]), 1)))
    return out


if __name__ == "__main__":
    clay, raw, fix = sys.argv[1:4]
    G = {"clay": g(clay), "raw": g(raw), "fix": g(fix)}
    spec = sys.argv[4:]
    for s in spec:
        o, c, lo, hi = s.split(":")
        c, lo, hi = int(c), int(lo), int(hi)
        for k, gg in G.items():
            if o == "h":   # horizontal lines at column c (band 16 px): rows lo-hi
                prof = np.abs(np.diff(gg[:, c - 8:c + 8], axis=0)).mean(1)
            else:          # vertical lines at row c (band 16 px): columns lo-hi
                prof = np.abs(np.diff(gg[c - 8:c + 8, :], axis=1)).mean(0)
            print(f"{s:18s} {k:4s} {peaks(prof, lo, hi)[:9]}")
