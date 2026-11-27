"""finish.py (FB21): a seedream return -> the waypoint still. 0 tokens.
The return is aligned to the code input (SIFT similarity, rotation dropped), its tones matched to the input on the refed
area (per-channel LUT), and then every refed pixel the approved stills give reliably is pasted back exactly (feathered 3 px).
  python3 finish.py RETURN.png INPUT.png MASKS.npy OUT.png [sources...]   (sources: indices into the masks' `who`, default 0 1)"""
import os, sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msr

def align(ret, inp, mask):
    g1 = cv2.cvtColor(ret, cv2.COLOR_RGB2GRAY); g2 = cv2.cvtColor(inp, cv2.COLOR_RGB2GRAY)
    s = cv2.SIFT_create(6000); k1, d1 = s.detectAndCompute(g1, None); k2, d2 = s.detectAndCompute(g2, (mask * 255).astype(np.uint8))
    m = cv2.BFMatcher().knnMatch(d1, d2, k=2); good = [a for a, b in m if a.distance < 0.75 * b.distance]
    p1 = np.float32([k1[a.queryIdx].pt for a in good]); p2 = np.float32([k2[a.trainIdx].pt for a in good])
    A, inl = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=2.0, maxIters=5000)
    sc = float(np.hypot(A[0, 0], A[1, 0])); A2 = np.array([[sc, 0, A[0, 2]], [0, sc, A[1, 2]]], np.float64)
    # refit the translation with rotation dropped
    q = p1[inl.ravel() > 0]; r = p2[inl.ravel() > 0]; A2[:, 2] = np.median(r - q * sc, 0)
    res = np.abs(q * sc + A2[:, 2] - r); return A2, dict(matches=len(good), inliers=int(inl.sum()), scale=round(sc, 5),
                                                         rot_deg_dropped=round(float(np.degrees(np.arctan2(A[1, 0], A[0, 0]))), 3),
                                                         resid_px_median=round(float(np.median(np.hypot(*res.T))), 2))

def main(ret_p, inp_p, masks_p, out_p, srcs=(0, 1)):
    ret = msr.rgb(ret_p); inp = msr.rgb(inp_p); M = np.load(masks_p)
    thru, val, hole, who, bm = M[0], M[1] > 0.5, M[2] > 0.5, M[3].astype(int), M[4] > 0.5
    k = 1920 / ret.shape[1]; ret = cv2.resize(ret, (1920, int(round(ret.shape[0] * k))), interpolation=cv2.INTER_AREA)
    keep = (thru > 0.99) & val & np.isin(who, srcs) & ~bm
    keep = cv2.erode(keep.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    try:
        A, rep = align(ret, inp, keep.astype(np.float32))
    except Exception as e:
        A, rep = None, dict(error=str(e))
    if A is None or not (0.97 < A[0, 0] < 1.03) or abs(rep.get('rot_deg_dropped', 99)) > 2 or rep.get('inliers', 0) < 25:
        # seedream keeps the framing: fall back to a pure translation by phase correlation on the whole frame
        g1 = cv2.cvtColor(ret, cv2.COLOR_RGB2GRAY).astype(np.float32); g2 = cv2.cvtColor(inp, cv2.COLOR_RGB2GRAY).astype(np.float32)
        (dx, dy), resp = cv2.phaseCorrelate(g1, g2, cv2.createHanningWindow(g1.shape[::-1], cv2.CV_32F))
        A = np.array([[1, 0, dx], [0, 1, dy]], np.float64); rep = dict(fallback='phase correlation', shift=[round(dx, 2), round(dy, 2)], response=round(float(resp), 3), sift=rep)
    reta = cv2.warpAffine(ret, A, (1920, 1080), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    retm = reta.astype(np.float32); L = None
    a = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 1.5)[..., None]
    out = np.clip(retm * (1 - a) + inp * a + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(out_p)
    rep.update(paste_px=int(keep.sum()))
    json.dump(rep, open(out_p.rsplit('.', 1)[0] + '-finish.json', 'w'), indent=1); print(rep)

if __name__ == '__main__':
    main(*sys.argv[1:5], srcs=tuple(int(x) for x in sys.argv[5:]) or (0, 1))
