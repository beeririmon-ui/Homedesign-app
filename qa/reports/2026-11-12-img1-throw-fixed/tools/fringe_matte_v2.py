# QA r3 fringe_matte.py, extended: same raw, alpha from either remove-bg or the fixed fullres; adds the G-IMG item 6 split
# (gaps against the background vs gaps over the product). Ours only.
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab
D=sys.argv[2].rstrip('/')+'/'
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB')).astype(float)
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
af=np.array(Image.open(D+'sofa-cover-cj-cotton-muslin-fringe/p2-nano-fixed-fullres.png'))[...,3]/255.
L=srgb_to_lab(raw)[...,0].astype(np.float32); H,W=L.shape
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
Lp=np.where(sure>0,L,255).astype(np.float32); env=np.where(sure>0,cv2.erode(Lp,np.ones((15,15),np.uint8)),0)
wg=cv2.GaussianBlur(sure,(0,0),8); Pm=cv2.GaussianBlur(env*sure,(0,0),8)/np.maximum(wg,1e-6); valid=wg>0.01
F=cv2.dilate(L,np.ones((9,9),np.uint8))
out={}
for tag,a in [('remove_bg',a0),('fixed',af)]:
    rows=range(500,1900)
    xr=np.array([(np.nonzero(a[y]>=0.5)[0].max() if (a[y]>=0.5).any() else -1) for y in rows])
    lost=[]
    for i,y in enumerate(rows):
        x0=xr[i]
        if x0<0 or x0+90>=W: lost.append(0); continue
        bgL=np.median(L[y,x0+60:x0+90]); seg=L[y,x0+1:x0+60]; br=np.nonzero(seg>=bgL+5)[0]
        lost.append(int(br.max())+1 if len(br) else 0)
    lost=np.array(lost)
    d=np.abs(np.diff(xr)); runs=[];r=0
    for v in d:
        if v<=1: r+=1
        else:
            if r>0: runs.append(r)
            r=0
    runs.append(r)
    res={'tips':{'rows_with_thread_beyond_alpha05':int((lost>0).sum()),'rows_ge3px':int((lost>=3).sum()),'max_px':int(lost.max()),'p99_px':float(np.percentile(lost,99)),'max_cells':round(float(lost.max())/25.5,2)},
         'longest_straight_boundary_run_rows':int(max(runs))}
    # G-IMG 6 split, in the right-edge band (within 40 px inside the 0.5 contour, plus everything outside it up to +45 px)
    op=a>=0.5; din=cv2.distanceTransform(op.astype(np.uint8),cv2.DIST_L2,3); dout=cv2.distanceTransform((~op).astype(np.uint8),cv2.DIST_L2,3)
    band=((op&(din<=40))|(~op&(dout<=45)))&(np.arange(W)[None,:]>=1450)&valid&(np.arange(H)[:,None]>=360)&(np.arange(H)[:,None]<1966)
    gap=band&(L<=F-6)
    vs_bg=gap&(L<=Pm+2)       # not brighter than the local (contact-shadow) paper: background between threads
    over=gap&(L>Pm+5)         # clearly brighter than the paper: a lower layer of the product
    ys=np.arange(H)[:,None]
    def frac(m,cond): return round(100*float(cond[m].mean()),1) if m.any() else None
    for nm,(r0,r1) in {'all':(0,H),'top_y<560':(0,560),'mid_560-1800':(560,1800),'bottom_y>=1800':(1800,H)}.items():
        m=(ys>=r0)&(ys<r1)
        res['gimg6_'+nm]={'gaps_vs_background':int((vs_bg&m).sum()),'pct_alpha_le_0.5':frac(vs_bg&m,a<=0.5),
                          'gaps_over_product':int((over&m).sum()),'pct_over_product_opaque_ge_0.98':frac(over&m,a>=0.98)}
    out[tag]=res
print(json.dumps(out,indent=1))
