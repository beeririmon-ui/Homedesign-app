"""m0x_finish.py: the M0x-W still from seedream's return: registered onto the seed (similarity, ECC on the seed's structure), then
the strip M0-W sees is pasted back exactly (the turned fix1-pecan pixels, feathered 24 px into seedream's) so every product M0-W
shows stays true.  python3 m0x_finish.py RETURNED.png WORKDIR OUT.png"""
import sys, json, numpy as np, cv2
from PIL import Image
ret, work, out = sys.argv[1:4]
R = np.array(Image.open(ret).convert('RGB').resize((1920, 1080), Image.LANCZOS)).astype(np.float32)
seed = np.array(Image.open(work + '/m0x-seed.png').convert('RGB')).astype(np.float32)
exact = np.array(Image.open(work + '/m0x-exact-mask.png')) > 127
rot = np.load(work + '/m0x-rot.npy').astype(np.float32)
# registration: a similarity (uniform scale + shift, rotation dropped to keep the verticals) from SIFT matches between seedream's
# left part and the exact strip; sampled from the full-size return (2720 wide), so the zoom costs no sharpness
R0 = np.array(Image.open(ret).convert('RGB')).astype(np.float32); kx = R0.shape[1] / 1920.0
sift = cv2.SIFT_create(4000); gr = lambda a: cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2GRAY)
m1 = (exact * 255).astype(np.uint8); m2 = np.zeros((1080, 1920), np.uint8); m2[:, :700] = 255
k1, d1 = sift.detectAndCompute(gr(rot), m1); k2, d2 = sift.detectAndCompute(gr(R), m2)
good = [p for p, q in cv2.BFMatcher().knnMatch(d1, d2, k=2) if p.distance < 0.75 * q.distance]
p1 = np.float32([k1[m.queryIdx].pt for m in good]); p2 = np.float32([k2[m.trainIdx].pt for m in good])
A, inl = cv2.estimateAffinePartial2D(p2, p1, ransacReprojThreshold=4)
sc = float(np.hypot(A[0, 0], A[1, 0])); M = np.float32([[sc, 0, A[0, 2]], [0, sc, A[1, 2]]])
Ms = M.copy(); Ms[:, :2] /= kx                                              # return px (full size) -> frame px
Rw = cv2.warpAffine(cv2.GaussianBlur(R0, (0, 0), 0.4), Ms, (1920, 1080), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
cc, warp = None, M
# tone: the strip's seedream version vs the exact pixels -> a gain for the whole return (small)
m = cv2.erode(exact.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
gain = np.array([np.median(rot[..., c][m] / np.maximum(Rw[..., c][m], 1)) for c in range(3)], np.float32)
Rw = Rw * gain
d = cv2.distanceTransform((~exact).astype(np.uint8), cv2.DIST_L2, 5)
w = np.clip(1 - d / 24.0, 0, 1)[..., None]; w = np.where(exact[..., None], 1.0, w)
final = rot * w + Rw * (1 - w)
Image.fromarray(np.clip(final + 0.5, 0, 255).astype(np.uint8)).save(out)
rep = dict(similarity_return1920_to_frame=np.round(warp, 4).tolist(), matches=len(good), inliers=int(inl.sum()), gain=np.round(gain, 4).tolist(),
           strip_mean_diff_before_paste=round(float(np.abs(Rw[m] - rot[m]).mean()), 2))
json.dump(rep, open(work + '/m0x-finish.json', 'w'), indent=1); print(rep)
