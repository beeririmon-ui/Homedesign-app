"""Pinhole cameras in house-plan conventions (yaw_deg_left, u = u0 + (L/36) x/d, v = v0 + (L/36)(16/9)(Hc - Z)/d)."""
import numpy as np, cv2
W, H = 1920, 1080

class Cam:
    def __init__(s, loc, yaw, lens, u0, v0):
        s.C = np.array(loc, float); y = np.radians(yaw)
        s.f = np.array([-np.sin(y), -np.cos(y), 0.0]); s.r = np.array([np.cos(y), -np.sin(y), 0.0])
        s.k = lens / 36.0; s.u0, s.v0 = u0, v0
    def project(s, P):  # P (...,3) -> px (...,2), d
        Q = P - s.C; d = Q @ s.f; x = Q @ s.r; z = Q[..., 2]
        u = s.u0 + s.k * x / d; v = s.v0 + s.k * 16 / 9 * (-z) / d
        return np.stack([u * W, v * H], -1), d
    def rays(s, px):  # px (...,2) -> unit-depth ray dirs (d=1)
        u = px[..., 0] / W; v = px[..., 1] / H
        x = (u - s.u0) / s.k; z = -(v - s.v0) / (s.k * 16 / 9)
        return s.f * 1.0 + x[..., None] * s.r + z[..., None] * np.array([0, 0, 1.0])

def plane_hit(cam, px, n, c):  # plane n.P = c ; returns P, t (t = planar depth)
    D = cam.rays(px); den = D @ n; t = (c - cam.C @ n) / den
    return cam.C + t[..., None] * D, t

def plane_H(src, dst, n, c, quad=((200, 200), (1700, 200), (1700, 900), (200, 900))):
    """homography taking src-frame px -> dst-frame px for points on plane n.P=c"""
    q = np.array(quad, float); P, _ = plane_hit(src, q, np.array(n, float), c)
    p2, _ = dst.project(P)
    return cv2.getPerspectiveTransform(q.astype(np.float32), p2.astype(np.float32))

HDX2 = dict(loc=(2.462, 8.15, 1.2), yaw=25.0, lens=24.0, u0=0.47, v0=0.5)
M0W_CLAY = dict(loc=(0.95, 5.55, 1.05), yaw=14.0, lens=35.0, u0=0.5, v0=0.52)
M0W_IMG = dict(loc=(0.95, 5.55, 1.05), yaw=14.0, lens=35.0, u0=0.5, v0=0.555)
