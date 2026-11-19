"""the clay's analytic projection (CB, 24 mm, u0 0.52, v0 0.46; canvas 2720 x 1530 with the 3 % overscan), for B1 (yaw -22) and B2 (-57)"""
import math
import numpy as np

FX0, FY0, FW, FH = 77.4882, 43.4301, 2565.0236, 1443.1398


def px(x, y, z, yaw_deg=-22.0):
    yaw = math.radians(yaw_deg)
    fwd = np.array([-math.sin(yaw), -math.cos(yaw)])
    right = np.array([-fwd[1], fwd[0]])
    d = np.array([x - 3.80, y - 13.20])
    dep, lat = d @ fwd, d @ right
    f = 24 / 36 * FW
    return FX0 + 0.52 * FW + f * lat / dep, FY0 + 0.46 * FH - f * (z - 1.15) / dep
