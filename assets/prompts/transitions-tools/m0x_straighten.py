"""m0x_straighten.py: M0x-W's floor line and skirting made straight and continuous with the exact strip (0 tokens).
seedream drew the corner as a wide swoop and its skirting 22 px taller than M0-W's at the seam. A vertical displacement field,
only right of the exact strip: (1) at the seam the skirting top and the floor line meet the strip's (fading out over 260 px);
(2) the floor line becomes two straight segments, seam -> corner apex -> the jamb's foot, with a short round at the apex; the
skirting moves with it. The floor tone is cross-faded into the strip's over 120 px. python3 m0x_straighten.py IN.png MASK.png OUT.png"""
import sys, json, numpy as np, cv2
from PIL import Image
inp, maskp, out = sys.argv[1:4]
im = np.array(Image.open(inp).convert('RGB')).astype(np.float32)
exact = np.array(Image.open(maskp)) > 127
xs = int(np.nonzero(exact.any(0))[0].max())                       # the strip's right edge
L = cv2.GaussianBlur(cv2.cvtColor(im.astype(np.uint8), cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32), (0, 0), 2)
gy = np.diff(L, axis=0)
def line_at(x, y0, y1, sign=-1):
    col = sign * gy[y0:y1, x]; return y0 + int(np.argmax(col))
X = np.arange(xs + 8, 960); yf = np.array([line_at(x, 860, 1060) for x in X], np.float32)
yf = cv2.GaussianBlur(yf[None], (0, 0), 6)[0]
# the strip's own floor line and skirting top, a few columns left of the seam (median)
yf_s = float(np.median([line_at(x, 900, 1060) for x in range(xs - 30, xs - 4)]))
yt_s = float(np.median([line_at(x, 860, int(yf_s) - 8, sign=+1) for x in range(xs - 30, xs - 4)]))  # wall -> white skirting: darker->lighter? use |grad|
yt_r = float(np.median([line_at(x, 840, int(yf[0]) - 8, sign=+1) for x in range(xs + 10, xs + 40)]))
ia = int(np.argmin(yf)); xa, ya = float(X[ia]), float(yf[ia]); xj = float(X[-1]); yj = float(yf[-1])
x0 = float(X[0]); y0 = yf_s
tgt = np.where(X <= xa, y0 + (X - x0) * (ya - y0) / (xa - x0), ya + (X - xa) * (yj - ya) / (xj - xa))
r = 30.0; near = np.abs(X - xa) < r                                 # a short round at the apex
tgt[near] = np.minimum(tgt[near], ya + (np.abs(X[near] - xa) ** 2) / (2 * r) * abs((yj - ya) / (xj - xa)))
fade = np.clip((X - x0) / 260.0, 0, 1); fade = fade * fade * (3 - 2 * fade)
# the chords seam -> apex -> jamb foot lie BELOW seedream's rounded swoop: the wall and skirting are moved DOWN onto them and
# the floor below the new line is not moved at all (moving the floor bent its planks)
tgt = np.maximum(tgt, yf)
dfl = tgt - yf
dtop = (yt_s - yt_r) * (1 - fade)                                    # extra shift at the skirting top near the seam
H, W = im.shape[:2]; dy = np.zeros((H, W), np.float32)
yy = np.arange(H, dtype=np.float32)[:, None]
for j, x in enumerate(X):
    f = yf[j]; t = tgt[j]; top = f - 70.0
    w_above = np.where(yy < top, np.exp(-(top - yy) ** 2 / (2 * 60.0 ** 2)), 1.0)
    s = np.where(yy >= top, dfl[j] + dtop[j] * np.clip((f - yy) / 70.0, 0, 1), dfl[j] + dtop[j])
    dy[:, x] = (s * w_above * np.clip((t - yy + 1.0) / 2.0, 0, 1))[:, 0]          # a 2 px ramp: no stair at the new line
dy[:, :xs + 1] = 0
gx, gy2 = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
warped = cv2.remap(im, gx, gy2 - dy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
# floor tone: blend the right side's floor toward the strip's over 120 px (below the floor line only)
reg = np.zeros((H, W), np.float32)
for x in range(xs + 1, min(W, xs + 121)):
    j = x - int(X[0]); fl = int(tgt[max(0, min(j, len(tgt) - 1))]) if j >= 0 else int(y0)
    reg[fl + 4:, x] = 1 - (x - xs) / 120.0
strip_floor = np.median(im[int(y0) + 10:1075, xs - 40:xs - 5].reshape(-1, 3), 0); right_floor = np.median(warped[int(y0) + 10:1075, xs + 5:xs + 40].reshape(-1, 3), 0)
gain = strip_floor / np.maximum(right_floor, 1)
warped = warped * (1 + (gain - 1) * reg[..., None])
# wall and skirting tone: the right side eased into the strip's shade over 160 px, rows 560 .. the floor line (low frequency only)
band = slice(560, int(y0))
ls = cv2.GaussianBlur(np.median(warped[band, xs - 34:xs - 4], 1)[None], (0, 0), 8)[0]; rs = cv2.GaussianBlur(np.median(warped[band, xs + 6:xs + 36], 1)[None], (0, 0), 8)[0]
gb = ls / np.maximum(rs, 1)
for x in range(xs + 1, min(W, xs + 161)):
    a = 1 - (x - xs) / 160.0; a = a * a * (3 - 2 * a)
    j = x - int(X[0]); fl = int(tgt[max(0, min(j, len(tgt) - 1))])
    rows = np.arange(560, min(fl, int(y0)))
    warped[rows, x] *= (1 + (gb[: len(rows)] - 1) * a)
Image.fromarray(np.clip(warped + 0.5, 0, 255).astype(np.uint8)).save(out)
rep = dict(seam_x=xs, strip_floor_y=round(y0, 1), strip_skirting_top=round(yt_s, 1), right_skirting_top=round(yt_r, 1), apex=[xa, round(ya, 1)],
           jamb_foot=[xj, round(yj, 1)], max_shift_px=round(float(np.abs(dy).max()), 1), floor_gain=np.round(gain, 3).tolist())
json.dump(rep, open(out.rsplit('.', 1)[0] + '.json', 'w'), indent=1); print(rep)
