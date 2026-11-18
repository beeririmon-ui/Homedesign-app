#!/usr/bin/env python3
"""levels_hc130.py: HC130's light against route 12.4 / 12.5 (display stops vs base.png's back wall), render-agent 2026-11-18. 0 tokens."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402
from prep_ht2 import normals  # noqa: E402


def main(still, outp):
    N = "HC130"
    a8 = K.rgb8(still)
    Y = K.to_lin(a8 / 255.0) @ K.W709
    P, ok = K.world(N)
    n = normals(N)
    U, V = K.canvas(N).uv()
    Z = P[..., 2]
    mid = ok & (Z >= 0.80) & (Z <= 1.65)
    st = lambda m: round(K.stops_of(np.median(Y[m])), 3) if m.any() else None
    far = (n[..., 0] > 0.7) & (P[..., 0] < 0.83)
    back = (n[..., 1] < -0.7) & (np.abs(P[..., 1] - 9.80) < 0.02)
    corr = (P[..., 1] > 9.96) & (np.abs(n[..., 0]) > 0.7)
    R = dict(jib_door_mid=dict(stops=st(mid & far & (U >= 0.70) & (U < 0.95)), target="-0.60 +-1/6"),
             back_wall=dict(stops=st(mid & back), target="-0.60 to -0.90"),
             corridor_wall_through_portal=dict(stops=st(mid & corr), target="-0.8 +-1/6"),
             clipped_pct=round(float((a8.max(-1) >= 255).mean()) * 100, 3))
    K.dump(outp, R)
    print(R)


if __name__ == "__main__":
    main(*sys.argv[1:3])
