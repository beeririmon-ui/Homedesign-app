#!/usr/bin/env python3
"""guide_hw_geom.py: the M0-W projection and the frames' quads (shared by the guide, the prints and the extraction)."""
import math

import cv2
import numpy as np

FB = (77.4852652259332, 43.427947598253276, 2642.5147347740667, 1486.5720524017468)
ART_X = (-0.36, 0.20, 0.76)
ART_Z = (1.13, 1.83)
ART_HALF = 0.25
ART_Y = 0.03
MOULD = 0.016
CAM = dict(loc=(0.95, 5.55, 1.05), yaw=14.0, lens=35.0, u0=0.50, v0=0.555)


def project(Xw, Yw, Zw):
    y = math.radians(CAM["yaw"])
    fw, rt, K = (-math.sin(y), -math.cos(y)), (math.cos(y), -math.sin(y)), CAM["lens"] / 36.0
    dx, dy = Xw - CAM["loc"][0], Yw - CAM["loc"][1]
    d = fw[0] * dx + fw[1] * dy
    x = rt[0] * dx + rt[1] * dy
    u, v = CAM["u0"] + K * x / d, CAM["v0"] + K * 16 / 9 * (CAM["loc"][2] - Zw) / d
    return np.array([FB[0] + u * (FB[2] - FB[0]), FB[1] + v * (FB[3] - FB[1])]), d


def quad_mask(pts, shape=(1530, 2720)):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.int32(np.rint(np.float32(pts) * 8))], 1, lineType=cv2.LINE_AA, shift=3)
    return m.astype(np.float32)


def art_quads():
    out = []
    for cx in ART_X:
        outer = [project(cx - ART_HALF, ART_Y, ART_Z[1])[0], project(cx + ART_HALF, ART_Y, ART_Z[1])[0], project(cx + ART_HALF, ART_Y, ART_Z[0])[0],
                 project(cx - ART_HALF, ART_Y, ART_Z[0])[0]]
        inner = [project(cx - ART_HALF + MOULD, ART_Y, ART_Z[1] - MOULD)[0], project(cx + ART_HALF - MOULD, ART_Y, ART_Z[1] - MOULD)[0],
                 project(cx + ART_HALF - MOULD, ART_Y, ART_Z[0] + MOULD)[0], project(cx - ART_HALF + MOULD, ART_Y, ART_Z[0] + MOULD)[0]]
        out.append((outer, inner))
    return out
