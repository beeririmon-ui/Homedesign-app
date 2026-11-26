"""chords.py: a room corner's floor line drawn as two straight chords (left end -> apex -> right end) instead of a rounded swoop:
the wall and skirting above it move DOWN onto the chords; the floor below is never moved (its planks stay straight)."""
import numpy as np, cv2

def straighten(img, xl, xr, ylo=820, yhi=1075, w=1.0):
    im = img.astype(np.float32)
    L = cv2.GaussianBlur(cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32), (0, 0), 2)
    gy = np.diff(L, axis=0)
    X = np.arange(xl, xr); yf = np.array([ylo + int(np.argmax(-gy[ylo:yhi, x])) for x in X], np.float32)
    yf = cv2.GaussianBlur(yf[None], (0, 0), 6)[0]
    ia = int(np.argmin(yf)); xa, ya = X[ia], yf[ia]
    if ia < 20 or ia > len(X) - 20: return img, 0.0                 # no apex inside: nothing to straighten
    tgt = np.where(X <= xa, yf[0] + (X - X[0]) * (ya - yf[0]) / (xa - X[0]), ya + (X - xa) * (yf[-1] - ya) / (X[-1] - xa))
    tgt = np.maximum(tgt, yf); d = (tgt - yf) * w
    H = im.shape[0]; yy = np.arange(H, dtype=np.float32); dy = np.zeros(im.shape[:2], np.float32)
    for j, x in enumerate(X):
        f, t = yf[j], yf[j] + d[j]; top = f - 70.0
        wa = np.where(yy < top, np.exp(-(top - yy) ** 2 / (2 * 60.0 ** 2)), 1.0)
        dy[:, x] = d[j] * wa * np.clip((t - yy + 1.0) / 2.0, 0, 1)
    fade = np.ones(len(X), np.float32); r = min(40, len(X) // 4)
    fade[:r] = np.linspace(0, 1, r); fade[-r:] = np.linspace(1, 0, r); dy[:, xl:xr] *= fade[None]
    gx, g2 = np.meshgrid(np.arange(im.shape[1], dtype=np.float32), np.arange(H, dtype=np.float32))
    out = cv2.remap(im, gx, g2 - dy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return np.clip(out + 0.5, 0, 255).astype(np.uint8), float(np.abs(dy).max())

def walnut_left_edge(img, x0=150, x1=1400):
    """the first column (from the left) where the opening's walnut leaf starts: dark across rows 450-850"""
    L = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32)
    m = np.median(L[450:850, x0:x1], 0); idx = np.nonzero(m < 0.42 * np.median(L[450:850, x0:x1]))[0]
    return int(x0 + idx[0]) if len(idx) else None
