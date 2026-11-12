# Map of the product px (>= local paper envelope + 5 L*, connected to the body) that v2 makes transparent, over the raw (ours only).
# Left: raw; middle: raw with lost px in red and the v2 0.5 contour in cyan; right: v2 on dark. Usage: lost_map.py <tools> <img1-dir> <out.png> x0 y0 w h zoom
import sys, numpy as np, cv2
from PIL import Image, ImageDraw
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab
D=sys.argv[2].rstrip('/')+'/'; out=sys.argv[3]; x0,y0,w,h,z=map(int,sys.argv[4:9])
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB'))
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
v2=np.array(Image.open(D+'sofa-cover-cj-cotton-muslin-fringe/p2-nano-fixed-v2-fullres.png').convert('RGBA'))
L=srgb_to_lab(raw)[...,0].astype(np.float32)
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
Lp=np.where(sure>0,L,255).astype(np.float32); env=np.where(sure>0,cv2.erode(Lp,np.ones((15,15),np.uint8)),0)
wg=cv2.GaussianBlur(sure,(0,0),8); Pq=cv2.GaussianBlur(env*sure,(0,0),8)/np.maximum(wg,1e-6); valid=wg>0.01
op=v2[...,3]>=128; dout=cv2.distanceTransform((~op).astype(np.uint8),cv2.DIST_L2,5)
cand=(L>Pq+5)&valid&~op&(dout<=45)&(np.arange(raw.shape[1])[None,:]>=1450)
n,cc=cv2.connectedComponents((cand|op).astype(np.uint8),connectivity=8); body=np.bincount(cc[op].ravel()).argmax(); lost=cand&(cc==body)
sl=(slice(y0,y0+h),slice(x0,x0+w))
m=raw[sl].copy(); m[lost[sl]]=(255,0,0); e=op[sl].astype(np.uint8)-cv2.erode(op[sl].astype(np.uint8),np.ones((3,3),np.uint8)); m[e>0]=(0,200,255)
a=v2[sl][...,3:4]/255.; dk=(v2[sl][...,:3]*a+np.array([0x3A]*3)*(1-a)).clip(0,255).astype(np.uint8)
row=np.concatenate([raw[sl],np.full((h,3,3),255,np.uint8),m,np.full((h,3,3),255,np.uint8),dk],1)
Image.fromarray(row).resize((row.shape[1]*z,h*z),Image.NEAREST).save(out)
print('lost px in crop',int(lost[sl].sum()),'depth p50/p99/max',np.percentile(dout[lost&np.pad(np.ones((h,w),bool),((y0,raw.shape[0]-y0-h),(x0,raw.shape[1]-x0-w)))],[50,99,100]).round(1))
