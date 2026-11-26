#!/usr/bin/env python3
"""grade.py: one display grade of a concept: a shoulder curve in linear light, y = k x / (1 + (k - 1) x) (0 and 1 stay; the mid-tones
rise by about log2(k) stops near black and less toward the highlights). python3 -P grade.py <in> <out.png> <k>"""
import sys
import numpy as np
from PIL import Image
src, dst, k = sys.argv[1], sys.argv[2], float(sys.argv[3])
a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255.0
lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
Y = lin @ np.float32([0.2126, 0.7152, 0.0722])
Y2 = k * Y / (1 + (k - 1) * Y)
lin2 = lin * (Y2 / np.maximum(Y, 1e-5))[..., None]            # on luminance: the hues stay
out = np.where(lin2 <= 0.0031308, lin2 * 12.92, 1.055 * np.clip(lin2, 0, None) ** (1 / 2.4) - 0.055)
Image.fromarray(np.rint(np.clip(out, 0, 1) * 255).astype(np.uint8)).save(dst, optimize=True)
