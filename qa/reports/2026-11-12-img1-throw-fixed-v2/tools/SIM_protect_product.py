# SIMULATION, NOT AN ASSET (ours only): v2 alpha, but px that G-IMG 6 (1) calls product (>= local paper envelope + 5 L*), connected
# to the body through product px, keep their v1 alpha inside the top-corner box (raw x>=1488, y<580). Writes an alpha-only PNG for the
# QA tools (edge_loss_2d.py, gimg6_segments.py). It changes nothing in the repo's assets.
# Usage: SIM_protect_product.py <tools> <img1-dir> <out_alpha.png>
import sys, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab
D=sys.argv[2].rstrip('/')+'/'; OUT=sys.argv[3]; A=D+'sofa-cover-cj-cotton-muslin-fringe/'
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB'))
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
v1=np.array(Image.open(A+'p2-nano-fixed-fullres.png'))[...,3].astype(np.float64); v2=np.array(Image.open(A+'p2-nano-fixed-v2-fullres.png'))[...,3].astype(np.float64)
L=srgb_to_lab(raw)[...,0].astype(np.float32); H,W=L.shape
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
Lp=np.where(sure>0,L,255).astype(np.float32); env=np.where(sure>0,cv2.erode(Lp,np.ones((15,15),np.uint8)),0)
wg=cv2.GaussianBlur(sure,(0,0),8); Pq=cv2.GaussianBlur(env*sure,(0,0),8)/np.maximum(wg,1e-6); valid=wg>0.01
prod=(L>Pq+5)&valid&(v1>=128)
box=np.zeros((H,W),bool); box[:580,1488:]=True
n,cc=cv2.connectedComponents((prod|(v2>=128)).astype(np.uint8),connectivity=8); body=np.bincount(cc[v2>=128].ravel()).argmax()
keep=prod&(cc==body)&box
keep=cv2.dilate(keep.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)&box&(v1>v2)
sim=v2.copy(); sim[keep]=v1[keep]
Image.fromarray(np.clip(np.round(sim),0,255).astype(np.uint8),'L').convert('RGBA').save(OUT) if False else None
rgba=np.zeros((H,W,4),np.uint8); rgba[...,3]=np.clip(np.round(sim),0,255).astype(np.uint8); Image.fromarray(rgba,'RGBA').save(OUT)
print('restored px',int(keep.sum()))
