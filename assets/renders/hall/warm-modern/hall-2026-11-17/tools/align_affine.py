#!/usr/bin/env python3
"""align_affine.py: bring a render whose canvas came back at another size onto the still's canvas, then (if needed) one
global affine fitted against the model input's structure (ECC on gradient magnitude, coarse to fine). render-agent, 0 tokens.
  python3 align_affine.py <raw.png> <input.png> <out.png> <W> <H> [--no-ecc]"""
import json, sys
import cv2
import numpy as np
from PIL import Image
raw, inp, out, W, H = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
im = np.asarray(Image.open(raw).convert("RGB"))
rep = dict(returned_px=[im.shape[1], im.shape[0]])
if (im.shape[1], im.shape[0]) != (W, H):
    im = cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA if im.shape[1] > W else cv2.INTER_CUBIC)
rep["resampled_to"] = [W, H]
if "--no-ecc" not in sys.argv:
    g = lambda a: cv2.GaussianBlur(cv2.magnitude(cv2.Sobel(a, cv2.CV_32F, 1, 0), cv2.Sobel(a, cv2.CV_32F, 0, 1)), (0, 0), 1.5)
    A = g(cv2.cvtColor(im, cv2.COLOR_RGB2GRAY).astype(np.float32))
    B = g(cv2.cvtColor(np.asarray(Image.open(inp).convert("RGB")), cv2.COLOR_RGB2GRAY).astype(np.float32))
    M = np.eye(2, 3, dtype=np.float32)
    for s in (0.25, 0.5, 1.0):
        a_, b_ = cv2.resize(A, None, fx=s, fy=s), cv2.resize(B, None, fx=s, fy=s)
        Ms = M.copy(); Ms[:, 2] *= s
        cc, Ms = cv2.findTransformECC(b_, a_, Ms, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
        M = Ms.copy(); M[:, 2] /= s
    rep["affine_img_from_ref"] = M.round(5).tolist()
    rep["ecc"] = round(float(cc), 4)
    im = cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
Image.fromarray(im).save(out)
print(json.dumps(rep))
