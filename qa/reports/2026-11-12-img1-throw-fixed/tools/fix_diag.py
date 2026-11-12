"""IMG1 round 4: 0-token code fixes for the throw P2 (nano test), rebuilt from the raw every time.
Inputs (ours): raw/p2-throw-nano-test-raw.png (opaque, on our palette) and raw/p2-throw-nano-test-nobg.png (remove-background).
1) re-matte of the right-edge fringe: recover thread ends clipped by remove-background and open the gaps where paper shows,
   by difference against a smooth paper/shadow model; semi-transparent pixels take the local thread colour.
2) global linear exposure gain k on the product colour.  3) interior alpha clamp.  4) re-frame to 80% of width on 1638x2048.
Usage: python3 fix_throw_nano.py <img1-dir> <out.png> [k]"""
import sys, json, numpy as np, cv2
from PIL import Image
D=sys.argv[1].rstrip('/')+'/'; OUTP=sys.argv[2]; K=float(sys.argv[3]) if len(sys.argv)>3 else 0.934
P=dict(rows=(360,1965), inner_band=12, outer_ext=40, gap_tol=3.0, min_contrast=8.0, min_diff=8.0, vsigma=6, open_inner=False)
def srgb2lin(c): c=c/255.0; return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
def lin2srgb(c): c=np.clip(c,0,1); return np.where(c<=0.0031308,12.92*c,1.055*c**(1/2.4)-0.055)*255
def Lstar(rgb):
    lin=srgb2lin(rgb.astype(np.float64)); Y=lin@np.array([0.2126729,0.7151522,0.0721750])
    f=np.where(Y>(6/29)**3,np.cbrt(Y),Y/(3*(6/29)**2)+4/29); return 116*f-16
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB')).astype(np.float64)
nb=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png').convert('RGBA'))
a0=nb[...,3].astype(np.float64)/255; H,W=a0.shape; L=Lstar(raw)
y0,y1=P['rows']
# right boundary of the remove-bg alpha per row: xout (alpha>0.04) and x5 (alpha>=0.5)
xout=np.full(H,-1); x5=np.full(H,-1)
for y in range(y0,y1):
    xs=np.where(a0[y]>0.04)[0]
    x5s=np.where(a0[y]>=0.5)[0]
    if len(xs) and len(x5s): xout[y]=xs.max(); x5[y]=x5s.max()
# paper model: lower envelope of L outside the alpha, constant inward from the boundary, smoothed across rows
Pm=np.full((H,W),np.nan)
for y in range(y0,y1):
    if xout[y]<0: continue
    xs=np.arange(xout[y]+1,min(W,xout[y]+260)); v=L[y,xs].copy(); v[a0[y,xs]>0.02]=np.nan
    env=np.array([np.nanpercentile(v[max(0,i-10):i+11],20) if np.isfinite(v[max(0,i-10):i+11]).any() else np.nan for i in range(len(v))])
    Pm[y,xs]=env; Pm[y,max(0,x5[y]-P['inner_band']-2):xout[y]+1]=env[np.isfinite(env)][0] if np.isfinite(env).any() else np.nan
rowsP=np.where(np.isfinite(Pm).any(1))[0]
Pf=np.nan_to_num(Pm,nan=0.0); wgt=np.isfinite(Pm).astype(np.float64)
Pf=cv2.GaussianBlur(Pf,(1,0),sigmaX=0.01,sigmaY=P['vsigma']); wgt=cv2.GaussianBlur(wgt,(1,0),sigmaX=0.01,sigmaY=P['vsigma'])
Ps=np.where(wgt>0.2,Pf/np.maximum(wgt,1e-6),np.nan)
F=cv2.dilate(L.astype(np.float32),np.ones((9,9),np.uint8)).astype(np.float64)       # local brightest thread
Lin=np.where(a0>=0.5,L,255.0).astype(np.float32)
G=cv2.erode(Lin,np.ones((7,7),np.uint8)).astype(np.float64)                          # local darkest gap, inside the alpha only
am=np.clip((L-Ps)/np.maximum(F-Ps,1e-6),0,1); am[(L-Ps)<P['min_diff']]=0; am[(F-Ps)<P['min_contrast']]=np.nan
alpha=a0.copy(); zone=np.zeros((H,W),bool); outer=np.zeros((H,W),bool); inner=np.zeros((H,W),bool)
for y in range(y0,y1):
    if xout[y]<0: continue
    xi=np.arange(max(0,x5[y]-P['inner_band']),x5[y]+1); xo=np.arange(x5[y]+1,min(W,xout[y]+1+P['outer_ext']))
    inner[y,xi]=True; outer[y,xo]=True
zone=inner|outer
ok=np.isfinite(am)&np.isfinite(Ps)
# the remove-bg soft ramp and beyond (outside the alpha=0.5 contour): alpha from the difference matte
sel=outer&ok; alpha[sel]=am[sel]
# inside the outer band: open only where the local gap is as dark as the paper (paper shows through)
paper_visible=inner&ok&(np.abs(G-Ps)<=P['gap_tol'])
if P['open_inner']: alpha[paper_visible]=np.minimum(alpha[paper_visible],am[paper_visible])
else: paper_visible=paper_visible&False   # conservative: gaps inside the 0.5 contour read brighter than the adjacent shadowed paper (lower layer beneath), so they stay opaque
# keep only recovered pixels connected to the product
m=(alpha>0.04).astype(np.uint8); n,lbl,st,_=cv2.connectedComponentsWithStats(m,8); keep=1+np.argmax(st[1:,4])
alpha[(lbl!=keep)&outer]=0
# colour of semi-transparent zone pixels: local thread colour (median of bright pixels nearby), not the baked-in paper
thread=(L>=F-2.0)&(a0>0.5)|(L>=F-2.0)&outer
T=np.zeros_like(raw)
for c in range(3):
    num=cv2.blur((raw[...,c]*thread).astype(np.float32),(11,11)); den=cv2.blur(thread.astype(np.float32),(11,11))
    T[...,c]=np.where(den>1e-3,num/np.maximum(den,1e-3),raw[...,c])
col=raw.copy(); fix=sel&(alpha<0.98)&(alpha>0); col[fix]=T[fix]   # only where the matte was applied

import json as _j
fa=np.array(Image.open(D+'sofa-cover-cj-cotton-muslin-fringe/p2-nano-fixed-fullres.png'))[...,3]/255.
paperthr=(thread&(fa<0.04)).astype(np.float32)   # "thread" pixels that the final matte itself calls background
allthr=thread.astype(np.float32)
fp=cv2.blur(paperthr,(11,11))/np.maximum(cv2.blur(allthr,(11,11)),1e-6)
chg=np.load('out/chg.npy')
TL=Lstar(T); RL=Lstar(raw)
r={'fix_px':int(fix.sum()),'fix_equals_changed_plus_rounding':int((fix&~chg).sum()),'changed_not_in_fix':int((chg&~fix).sum()),
   'thread_px_in_outer_zone':int((thread&outer).sum()),'of_which_final_alpha_lt_0.04':int((thread&outer&(fa<0.04)).sum()),
   'share_of_paper_in_T_at_fix_px_p50_p90_max':[round(float(np.percentile(fp[fix],q)),3) for q in (50,90,100)],
   'fix_px_where_T_darker_than_raw':int((TL[fix]<RL[fix]).sum()),
   'fix_px_where_T_darker_and_paper_share_gt_0.3':int(((TL<RL)&(fp>0.3))[fix].sum())}
print(_j.dumps(r,indent=1))
