"""
Direct, named edges per retake (QA's fourth lock measure, independent of the selfcheck boxes): for each architectural or
fixed-furniture line that the eye can name, the 1-D gradient profile across the line (averaged over a named span) in the
clay and in the raw still, at 1920x1080 of the 16:9 frame; the offset by cross-correlation (+-90 px) and by the strongest
peak in the search window. Reported in px at 1920 (horizontal lines: px of 1080 height). The desk front edge of W0-in and
the vanity edges of B2 are not box edges in the selfcheck, so neither lock_v2 nor QA's box edges measured them.
Writes data/edges-direct.json and overlays/edges-<id>.jpg.
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import lock as LK  # noqa: E402

W, H = 1920, 1080
# id: list of (name, orientation 'h' (a horizontal line: offset in rows) | 'v', span (u0,u1) for h / (v0,v1) for v, search (lo,hi) of the other axis in frame fractions)
EDGES = {
    "W0-in r2": [("shelf top", "h", (0.30, 0.70), (0.05, 0.20)), ("shelf bottom (front face)", "h", (0.30, 0.70), (0.12, 0.26)),
                 ("desk top front edge", "h", (0.68, 0.80), (0.55, 0.85)), ("desk top front edge (left of chair)", "h", (0.20, 0.33), (0.55, 0.85)),
                 ("drawer bottom / apron", "h", (0.20, 0.33), (0.70, 0.95)), ("chair back top", "h", (0.40, 0.60), (0.62, 0.90)),
                 ("desk left outer edge", "v", (0.80, 0.95), (0.08, 0.26)), ("desk right outer edge", "v", (0.80, 0.95), (0.75, 0.92)),
                 ("chair back left edge", "v", (0.82, 0.98), (0.28, 0.44)), ("chair back right edge", "v", (0.82, 0.98), (0.56, 0.72))],
    "K-girl-0 r2": [("desk top", "h", (0.25, 0.45), (0.50, 0.66)), ("band top (desk wall)", "h", (0.05, 0.20), (0.28, 0.44)),
                    ("bed foot top", "h", (0.02, 0.14), (0.55, 0.72)), ("skirting top (desk wall)", "h", (0.08, 0.20), (0.70, 0.90)),
                    ("room corner", "v", (0.08, 0.30), (0.52, 0.68)), ("desk left leg", "v", (0.72, 0.90), (0.15, 0.28)),
                    ("desk right leg", "v", (0.72, 0.90), (0.40, 0.52)), ("bed foot right edge", "v", (0.68, 0.90), (0.10, 0.24))],
    "B1 r3": [("glazing top", "h", (0.24, 0.32), (0.08, 0.22)), ("glazing bottom / sill", "h", (0.24, 0.32), (0.42, 0.56)),
              ("ledge top (WC block)", "h", (0.17, 0.30), (0.48, 0.62)), ("WC block bottom", "h", (0.17, 0.30), (0.90, 1.0)),
              ("glazing left", "v", (0.20, 0.42), (0.14, 0.26)), ("glazing right", "v", (0.20, 0.42), (0.30, 0.42)),
              ("WC block left", "v", (0.62, 0.90), (0.08, 0.20)), ("WC block right", "v", (0.62, 0.90), (0.36, 0.46)),
              ("curtain track end / corner", "v", (0.05, 0.40), (0.68, 0.78)), ("vanity left edge", "v", (0.66, 0.95), (0.86, 0.96))],
    "B2 r3": [("vanity top", "h", (0.52, 0.70), (0.44, 0.60)), ("mirror top", "h", (0.60, 0.76), (0.02, 0.14)), ("mirror bottom", "h", (0.60, 0.76), (0.40, 0.52)),
              ("niche top", "h", (0.53, 0.63), (0.34, 0.46)), ("vanity left edge", "v", (0.58, 0.90), (0.42, 0.54)), ("vanity right edge", "v", (0.60, 0.90), (0.76, 0.88)),
              ("mirror left", "v", (0.12, 0.40), (0.50, 0.62)), ("mirror right", "v", (0.12, 0.40), (0.74, 0.86)),
              ("niche left", "v", (0.38, 0.48), (0.48, 0.58)), ("niche right", "v", (0.38, 0.48), (0.60, 0.70)), ("curtain outer edge", "v", (0.20, 0.70), (0.26, 0.36))],
}


def profiles(gc, gr, orient, span, search):
    if orient == "h":
        c0, c1 = int(span[0] * W), int(span[1] * W)
        r0, r1 = int(search[0] * H), int(search[1] * H)
        pc = np.abs(np.diff(gc[:, c0:c1], axis=0)).mean(1)
        prr = np.abs(np.diff(gr[:, c0:c1], axis=0)).mean(1)
        return pc, prr, r0, r1
    r0, r1 = int(span[0] * H), int(span[1] * H)
    c0, c1 = int(search[0] * W), int(search[1] * W)
    pc = np.abs(np.diff(gc[r0:r1], axis=1)).mean(0)
    prr = np.abs(np.diff(gr[r0:r1], axis=1)).mean(0)
    return pc, prr, c0, c1


def measure(gc, gr, orient, span, search):
    pc, prr, a0, a1 = profiles(gc, gr, orient, span, search)
    ic = a0 + int(np.argmax(pc[a0:a1]))
    sc = float(pc[ic])
    ir = a0 + int(np.argmax(prr[a0:a1]))
    sr = float(prr[ir])
    # the render peak nearest the clay peak within +-90 px (a second estimate when the strongest render edge is another line)
    lo, hi = max(a0, ic - 90), min(a1, ic + 90)
    near = lo + int(np.argmax(prr[lo:hi]))
    o, r = LK.xcorr_offset(pc, prr, ic / (H if orient == "h" else W), (H if orient == "h" else W), half=90)
    return dict(orientation=orient, span=list(span), search=list(search), clay_px=ic, clay_strength=round(sc, 1), render_strongest_px=ir, render_strength=round(sr, 1),
                d_strongest_px=ir - ic, render_nearest_px=near, d_nearest_px=near - ic, d_xcorr_px=o, xcorr_r=r)


def run(sid):
    d = C.load(sid)
    clay = C.at(d["clay"], W, H)
    rend = C.at(d["raw"], W, H)
    gc, gr = LK.gray(clay), LK.gray(rend)
    out = {}
    im = cv2.cvtColor((rend * 255).astype(np.uint8).copy(), cv2.COLOR_RGB2BGR)
    for name, orient, span, search in EDGES[sid]:
        m = measure(gc, gr, orient, span, search)
        out[name] = m
        if orient == "h":
            x0, x1 = int(span[0] * W), int(span[1] * W)
            cv2.line(im, (x0, m["clay_px"]), (x1, m["clay_px"]), (0, 0, 255), 2)
            cv2.line(im, (x0, m["render_strongest_px"]), (x1, m["render_strongest_px"]), (0, 200, 0), 1)
            cv2.putText(im, f"{name}: clay {m['clay_px']} render {m['render_strongest_px']} ({m['d_strongest_px']:+d}) xcorr {m['d_xcorr_px']}", (x0, m["clay_px"] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        else:
            y0, y1 = int(span[0] * H), int(span[1] * H)
            cv2.line(im, (m["clay_px"], y0), (m["clay_px"], y1), (0, 0, 255), 2)
            cv2.line(im, (m["render_strongest_px"], y0), (m["render_strongest_px"], y1), (0, 200, 0), 1)
            cv2.putText(im, f"{name}: {m['d_strongest_px']:+d} / xc {m['d_xcorr_px']}", (m["clay_px"] + 4, y0 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        print(f"{sid:12s} {name:36s} clay {m['clay_px']:5d} render strongest {m['render_strongest_px']:5d} ({m['d_strongest_px']:+4d}) nearest ({m['d_nearest_px']:+4d}) xcorr {m['d_xcorr_px']} (r {m['xcorr_r']}) "
              f"strength clay {m['clay_strength']} render {m['render_strength']}")
    cv2.putText(im, f"{sid}: named edges, red = clay line, green = strongest render edge in the search window", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(C.OUT, "overlays", f"edges-{C.fn(sid)}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return out


if __name__ == "__main__":
    res = {s: run(s) for s in (sys.argv[1:] or C.RETAKES)}
    json.dump(res, open(os.path.join(C.OUT, "data", "edges-direct.json"), "w"), indent=1)
