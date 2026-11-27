"""M0-W fix1 stack: compose like layers/manifest-fix1.json, in the 1920x1080 frame."""
import json, numpy as np, cv2
from PIL import Image
B = '/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25/'
M = json.load(open(B + 'layers/manifest-fix1.json'))
FB = M['frame_box']

def to_frame(a, interp=cv2.INTER_AREA):
    """canvas array -> 1920x1080 frame (frame_box crop, resample), float"""
    x0, y0, x1, y1 = FB
    sx, sy = (x1 - x0) / 1920, (y1 - y0) / 1080
    A = np.array([[sx, 0, x0 + 0.5 * sx - 0.5], [0, sy, y0 + 0.5 * sy - 0.5]], np.float32)
    a = a.astype(np.float32)
    if interp == cv2.INTER_AREA:  # pre-blur for downscale then sample
        a = cv2.GaussianBlur(a, (0, 0), 0.5 * sx)
    return cv2.warpAffine(a, A, (1920, 1080), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)

def load(p):
    return np.array(Image.open(B + p)).astype(np.float32) / 255.0

def stack(frame=True):
    """returns plate, list of (slot, z, rgb, alpha, shadow), lights (sum-screen), all in frame space if frame"""
    f = to_frame if frame else (lambda a: a)
    plate = f(load('plate-PW.png'))
    layers = []
    for L in sorted(M['layers'], key=lambda L: L['z']):
        rgba = f(load('layers/../' + L['layer'] if False else L['layer']))
        sh = f(load(L['shadow'])) if L.get('shadow') else None
        layers.append((L['slot'], L['z'], rgba[..., :3], rgba[..., 3:4], sh))
    lights = [f(load(L['file'])) for L in M['light']]
    return plate, layers, lights

def compose(plate, layers, lights, skip=()):
    img = plate.copy(); every = np.zeros(plate.shape[:2] + (1,), np.float32)
    for slot, z, rgb, a, sh in layers:
        if sh is not None: img = img * sh
        if slot in skip: continue
        img = img * (1 - a) + rgb * a; every = np.maximum(every, a)  # 'every alpha' union
    for Lt in lights:
        Lt = Lt * (1 - every); img = 1 - (1 - img) * (1 - Lt)
    return img
