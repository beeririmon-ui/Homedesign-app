# Which rows drive the per-row edge-loss p99 in the top corner (ours only); same definitions as edge_loss_2d.py (product_ge_paper+5).
# Prints rows with x-extent > 6 px for each alpha file, and the lost px (x,y,L-paper) there; writes a map: raw, lost px red, 0.5 contour cyan.
# Usage: lost_rows_v3.py <tools(v2)> <img1-dir> <out.png> zoom tag=alpha.png ...
import sys, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab
D=sys.argv[2].rstrip('/')+'/'; OUT=sys.argv[3]; z=int(sys.argv[4]); srcs=[a.split('=',1) for a in sys.argv[5:]]
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB'))
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
L=srgb_to_lab(raw)[...,0].astype(np.float32); H,W=L.shape
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
Lp=np.where(sure>0,L,255).astype(np.float32); env=np.where(sure>0,cv2.erode(Lp,np.ones((15,15),np.uint8)),0)
wg=cv2.GaussianBlur(sure,(0,0),8); Pq=cv2.GaussianBlur(env*sure,(0,0),8)/np.maximum(wg,1e-6); valid=wg>0.01
X=np.arange(W)[None,:]; Y=np.arange(H)[:,None]; band_xy=(X>=1450)&(Y>=360)&(Y<1966)
tiles=[]
for tag,f in srcs:
    A=np.array(Image.open(D+f).convert('RGBA'))[...,3]/255.; op=A>=0.5
    dout=cv2.distanceTransform((~op).astype(np.uint8),cv2.DIST_L2,5)
    cand=(L>Pq+5)&valid&~op&band_xy&(dout<=45)
    n,cc=cv2.connectedComponents((cand|op).astype(np.uint8),connectivity=8); body=np.bincount(cc[op].ravel(),minlength=n).argmax(); lost=cand&(cc==body)
    print(tag,'lost px y<560:',int(lost[:560].sum()))
    for y in range(360,560):
        xs=np.nonzero(op[y]&band_xy[y])[0]
        if not len(xs): continue
        x5=xs.max(); xl=np.nonzero(lost[y,x5+1:x5+46])[0]
        if len(xl) and xl.max()+1>6:
            lx=np.nonzero(lost[y])[0]; print(f'  {tag} row {y}: x5 {x5} extent {xl.max()+1} lost x {list(lx)} L-paper {[round(float(v),1) for v in (L-Pq)[y,lx]]}')
    x0,y0,w,h=1530,480,80,90; sl=(slice(y0,y0+h),slice(x0,x0+w)); m=raw[sl].copy(); m[lost[sl]]=(255,0,0)
    e=op[sl].astype(np.uint8)-cv2.erode(op[sl].astype(np.uint8),np.ones((3,3),np.uint8)); m[e>0]=(0,200,255); tiles.append(m)
row=np.concatenate([np.concatenate([t,np.full((t.shape[0],3,3),255,np.uint8)],1) for t in tiles],1)
Image.fromarray(row).resize((row.shape[1]*z,row.shape[0]*z),Image.NEAREST).save(OUT)
