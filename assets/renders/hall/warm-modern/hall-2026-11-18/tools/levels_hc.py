#!/usr/bin/env python3
"""levels_hc.py: HC's light against route 12.3 / 12.5 (display stops vs base.png's back wall), render-agent 2026-11-18. 0 tokens.
  python3 levels_hc.py <still.png> <report.json>"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402
from prep_hc import groups  # noqa: E402


def main(still, outp):
    G, P, ok = groups()
    a8 = K.rgb8(still)
    lin = K.to_lin(a8 / 255.0)
    Y = lin @ K.W709
    U, V = K.canvas("HC").uv()
    Z, Yw = P[..., 2], P[..., 1]
    mid = (Z >= 0.80) & (Z <= 1.65)
    R = {}
    def st(m):
        return round(K.stops_of(np.median(Y[m])), 3) if m.any() else None
    R["hall_around_portal"] = dict(stops=st(G["hall"] & (((U >= 0.05) & (U < 0.20)) | ((U >= 0.85) & (U < 0.95))) & (V >= 0.40) & (V < 0.60)), target="-0.60 +-1/6")
    R["hall_left_side"] = st(G["hall"] & (U >= 0.05) & (U < 0.20) & (V >= 0.40) & (V < 0.60))
    R["hall_right_side"] = st(G["hall"] & (U >= 0.85) & (U < 0.95) & (V >= 0.40) & (V < 0.60))
    r = st(G["right"] & mid & (Yw >= 11) & (Yw <= 13))
    l = st(G["left"] & mid & (Yw >= 11) & (Yw <= 13))
    R["corridor_right_wall"] = dict(stops=r, target="-0.8 +-1/6")
    R["corridor_left_wall"] = dict(stops=l, under_right=round(r - l, 3), target="0.4-0.6 under the right")
    bm = G["bedroom"] & (V >= 0.40) & (V < 0.60)
    R["bedroom_through_door"] = dict(stops=st(bm), target="0 +-1/4", clipped_px=int((a8[bm].max(-1) >= 255).sum()))
    sl = G["slot"]
    R["slot_line"] = dict(px=int(sl.sum()), channel_255_pct=round(float((a8[sl].max(-1) >= 255).mean()) * 100, 3) if sl.any() else None, frame_255_pct=round(float((a8.max(-1) >= 255).mean()) * 100, 3))
    wl = G["walnut"]
    lab = K.lab_from_lin(lin)
    R["walnut_in_shade"] = dict(L_median=round(float(np.median(lab[wl][:, 0])), 1), L_p5=round(float(np.percentile(lab[wl][:, 0], 5)), 1),
                                black_point_L_p01=round(float(np.percentile(lab[..., 0], 0.1)), 1))
    # brightest point after the slot: the bedroom against every other group's 99th percentile (outside the slot)
    br = {}
    for k in ("hall", "right", "left", "bedroom", "ceiling", "floor"):
        m = G[k] & (V >= 0.0) & (V <= 1.0) & (U >= 0) & (U <= 1)
        if m.any():
            br[k] = round(K.stops_of(np.percentile(Y[m], 95)), 3)
    R["p95_by_surface_in_frame"] = br
    R["bedroom_is_brightest_after_slot"] = bool(br["bedroom"] >= max(v for k, v in br.items() if k != "bedroom"))
    K.dump(outp, R)
    print(R)


if __name__ == "__main__":
    main(*sys.argv[1:3])
