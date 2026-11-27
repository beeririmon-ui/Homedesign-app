#!/usr/bin/env python3
"""grade.py: ONE display grade for P-N, H-N and every edit (render-agent, 2026-11-27), toward the approved magazine frame
(nordic-A-fin2.png: shaded wall Lab (63.6, 3.8, 10.5), mean a*/b* (4.6, 12.1), black p0.5 L 11). Pointwise in Lab, so it commutes
with the layers' compositing when applied to the plate and the hero before the split.
  L*: a monotone curve through GRADE_XS -> GRADE_YS (black 4.5 -> 10.5, the shaded wall 69 -> 66.5, the sun kept);
  a*, b*: + A_SHIFT, + B_SHIFT, weighted by (1 - C*/40) clipped to 0.35..1 (neutrals take it all, the sage and the charcoal less),
  and faded out above L* 94 (the lit shades and the snow stay clean).
  python3 grade.py <in.png> <out.png>"""
import sys

import cv2
import numpy as np
from PIL import Image

GRADE_XS = [0.0, 4.5, 25.0, 50.0, 69.0, 87.0, 96.0, 100.0]
GRADE_YS = [7.0, 10.5, 27.5, 49.0, 66.5, 86.5, 95.5, 99.0]
A_SHIFT, B_SHIFT = 1.6, 4.5


def grade(rgb8):
    lab = cv2.cvtColor(rgb8.astype(np.float32) / 255, cv2.COLOR_RGB2Lab)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    C = np.sqrt(a * a + b * b)
    w = np.clip(1 - C / 40, 0.35, 1.0) * np.clip((96 - L) / 6, 0, 1)
    lab[..., 0] = np.interp(L, GRADE_XS, GRADE_YS)
    lab[..., 1] = a + A_SHIFT * w
    lab[..., 2] = b + B_SHIFT * w
    out = cv2.cvtColor(lab, cv2.COLOR_Lab2RGB)
    return np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)


if __name__ == "__main__":
    Image.fromarray(grade(np.asarray(Image.open(sys.argv[1]).convert("RGB")))).save(sys.argv[2])
