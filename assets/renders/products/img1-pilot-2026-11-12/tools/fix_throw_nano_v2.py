"""IMG1 round 4, v2 (QA throw-fixed fixes 1-3): 0-token code fixes for the throw P2 (nano test), rebuilt from the raw every time.
Inputs (ours): raw/p2-throw-nano-test-raw.png (opaque, on our palette) and raw/p2-throw-nano-test-nobg.png (remove-background).
1) re-matte of the right-edge fringe: recover thread ends clipped by remove-background and open the gaps where paper shows,
   by difference against a smooth paper/shadow model; semi-transparent pixels take the local thread colour.
2) global linear exposure gain k on the product colour.  3) interior alpha clamp.  4) re-frame to 80% of width on 1638x2048.
v2: (1) thread mask outside the remove-bg 0.5 contour only where am>=0.5, and colour replaced only where it moves away from the paper;
    (2) 2-D matte in the top corner for gaps not clearly brighter than the paper envelope (<= +5 L*);
    (3) detached specks with alpha<8 zeroed after the resize; tip pieces within 3 px of the body kept.
Usage: python3 fix_throw_nano_v2.py <img1-dir> <out.png> [k] [top_matte_inside 0|1]"""
import sys, json, numpy as np, cv2
from PIL import Image
D=sys.argv[1].rstrip('/')+'/'; OUTP=sys.argv[2]; K=float(sys.argv[3]) if len(sys.argv)>3 else 0.934
TMI=(sys.argv[4]!='0') if len(sys.argv)>4 else False
P=dict(rows=(360,1965), inner_band=12, outer_ext=40, gap_tol=3.0, min_contrast=8.0, min_diff=8.0, vsigma=6, open_inner=False,
       top_box=(1488,360,1600,562), top_band_in=40, top_band_out=45, top_bg_tol=5.0, top_paper_relief=3.0, top_fiber_relief=4.0, top_paper_above_env=10.0, top_mode='cut', top_cut_px=10, top_matte_inside=TMI, away_min_dE=0.5, keep_near_px=3, speck_alpha=8)
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
near=cv2.dilate((lbl==keep).astype(np.uint8),np.ones((2*P['keep_near_px']+1,2*P['keep_near_px']+1),np.uint8))>0
for i in range(1,n):
    if i!=keep and not (near&(lbl==i)).any(): alpha[(lbl==i)&outer]=0
# (2) top corner: 2-D matte for gaps that are not clearly brighter than the local paper envelope (QA: <= +5 L* is background)
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
Lp=np.where(sure>0,L,255).astype(np.float32); envp=np.where(sure>0,cv2.erode(Lp,np.ones((15,15),np.uint8)),0)
wgp=cv2.GaussianBlur(sure,(0,0),8); Pq=cv2.GaussianBlur(envp*sure,(0,0),8)/np.maximum(wgp,1e-6); validq=wgp>0.01
bx0,by0,bx1,by1=P['top_box']; box=np.zeros((H,W),bool); box[by0:by1,bx0:bx1]=True
op=a0>=0.5; din=cv2.distanceTransform(op.astype(np.uint8),cv2.DIST_L2,3); dout=cv2.distanceTransform((~op).astype(np.uint8),cv2.DIST_L2,3)
tband=box&((op&(din<=P['top_band_in']))|(~op&(dout<=P['top_band_out'])))&validq
Bloc=cv2.GaussianBlur(cv2.erode(L.astype(np.float32),np.ones((7,7),np.uint8)),(0,0),2).astype(np.float64)
cand=tband&(L<=F-6)&(L<=Pq+P['top_bg_tol'])
a2d=np.clip((L-Bloc)/np.maximum(F-Bloc,1e-6),0,1)
top_pre=alpha.copy(); top_before=alpha[cand].copy()
if P['top_matte_inside']: alpha[cand]=np.minimum(alpha[cand],a2d[cand])
# tight cut of the light paper haze around the thread ends: smooth (low relief), not a fibre, not clearly brighter than the paper envelope
relief=L-cv2.erode(L.astype(np.float32),np.ones((5,5),np.uint8)).astype(np.float64)
fiber=(relief>=P['top_fiber_relief'])&(L>=F-6)
near_fiber=cv2.dilate(fiber.astype(np.uint8),np.ones((3,3),np.uint8))>0
haze=tband&~near_fiber&(relief<P['top_paper_relief'])&(L<F-2)&(L<=Pq+P['top_paper_above_env'])&~cand
haze=cv2.morphologyEx(haze.astype(np.uint8),cv2.MORPH_OPEN,np.ones((2,2),np.uint8))>0
if P['top_mode']=='cut':
    # tight cut: erode the alpha inside the corner box by top_cut_px (< half a waffle cell, ~12.7 px raw), feathered into the box edges
    haze[:]=False
    r=P['top_cut_px']; er=cv2.erode((alpha>=0.5).astype(np.uint8),cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*r+1,2*r+1)))
    keep_cut=cv2.GaussianBlur(cv2.dilate(er,np.ones((3,3),np.uint8)).astype(np.float32),(0,0),1.2).astype(np.float64)
    wbox=np.zeros((H,W),np.float32); wbox[by0+8:by1-8,bx0+8:bx1]=1; wbox=cv2.GaussianBlur(wbox,(0,0),6).astype(np.float64)
    cut=np.minimum(alpha,keep_cut); alpha=alpha*(1-wbox)+cut*wbox
    haze=(wbox>0.01)&(alpha<top_pre-0.05) if False else haze
else:
    alpha[haze]=0.0
# drop opaque crumbs left in the corner band that no longer touch the body
mm=(alpha>0.04).astype(np.uint8); nn,ll,ss,_=cv2.connectedComponentsWithStats(mm,8); kk=1+np.argmax(ss[1:,4])
for i in range(1,nn):
    if i!=kk and (tband&(ll==i)).any(): alpha[ll==i]=0
cut_px=int(((top_pre>=0.5)&(alpha<0.5)&box).sum())
cand=cand|haze
top_opened=int((alpha[cand]<=0.5).sum()); top_cand=int(cand.sum())
# colour of semi-transparent zone pixels: local thread colour (median of bright pixels nearby), not the baked-in paper
amv=np.nan_to_num(am,nan=0.0)
thread=((L>=F-2.0)&(a0>0.5)&~cand)|((L>=F-2.0)&outer&(amv>=0.5))
T=np.zeros_like(raw)
for c in range(3):
    num=cv2.blur((raw[...,c]*thread).astype(np.float32),(11,11)); den=cv2.blur(thread.astype(np.float32),(11,11))
    T[...,c]=np.where(den>1e-3,num/np.maximum(den,1e-3),raw[...,c])
col=raw.copy(); fix0=(sel|cand)&(alpha<0.98)&(alpha>0)   # only where a matte was applied
# paper colour model (sure paper, blurred) and dE00 to it, before and after: replace only if the colour moves away from the paper
wq=cv2.GaussianBlur(sure,(0,0),10); Bq=np.stack([cv2.GaussianBlur((raw[...,c]*sure).astype(np.float32),(0,0),10)/np.maximum(wq,1e-6) for c in range(3)],-1)
def lab(rgb):
    lin=srgb2lin(np.clip(rgb,0,255)); M=np.array([[0.4124564,0.3575761,0.1804375],[0.2126729,0.7151522,0.0721750],[0.0193339,0.1191920,0.9503041]])
    xyz=lin@M.T/np.array([0.95047,1.0,1.08883]); f=np.where(xyz>(6/29)**3,np.cbrt(xyz),xyz/(3*(6/29)**2)+4/29)
    return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],-1)
def de00v(a,b):
    L1,a1,b1=a[:,0],a[:,1],a[:,2]; L2,a2,b2=b[:,0],b[:,1],b[:,2]; C1=np.hypot(a1,b1); C2=np.hypot(a2,b2); Cb=(C1+C2)/2
    G=0.5*(1-np.sqrt(Cb**7/(Cb**7+25**7))); a1p=(1+G)*a1; a2p=(1+G)*a2; C1p=np.hypot(a1p,b1); C2p=np.hypot(a2p,b2)
    h1=np.degrees(np.arctan2(b1,a1p))%360; h2=np.degrees(np.arctan2(b2,a2p))%360; dL=L2-L1; dC=C2p-C1p; dh=h2-h1
    dh=np.where(C1p*C2p==0,0,np.where(dh>180,dh-360,np.where(dh<-180,dh+360,dh))); dH=2*np.sqrt(C1p*C2p)*np.sin(np.radians(dh/2))
    Lb=(L1+L2)/2; Cbp=(C1p+C2p)/2; hs=h1+h2; hb=np.where(C1p*C2p==0,hs,np.where(np.abs(h1-h2)<=180,hs/2,np.where(hs<360,(hs+360)/2,(hs-360)/2)))
    T_=1-0.17*np.cos(np.radians(hb-30))+0.24*np.cos(np.radians(2*hb))+0.32*np.cos(np.radians(3*hb+6))-0.20*np.cos(np.radians(4*hb-63))
    dth=30*np.exp(-((hb-275)/25)**2); RC=2*np.sqrt(Cbp**7/(Cbp**7+25**7)); SL=1+0.015*(Lb-50)**2/np.sqrt(20+(Lb-50)**2); SC=1+0.045*Cbp; SH=1+0.015*Cbp*T_; RT=-np.sin(np.radians(2*dth))*RC
    return np.sqrt((dL/SL)**2+(dC/SC)**2+(dH/SH)**2+RT*(dC/SC)*(dH/SH))
idx=np.nonzero(fix0); lp=lab(Bq[idx]); d_raw=de00v(lab(raw[idx]),lp); d_T=de00v(lab(T[idx]),lp)
notbrighter=lab(T[idx])[:,0]<=F[idx]+0.5
ok_away=(d_T>d_raw+P['away_min_dE'])&notbrighter
fix=np.zeros((H,W),bool); fix[idx[0][ok_away],idx[1][ok_away]]=True
col[fix]=T[fix]
# 2) linear exposure gain on the product colour
col=lin2srgb(srgb2lin(col)*K)
# 3) interior alpha clamp
a8=np.clip(np.round(alpha*255),0,255).astype(np.uint8)
solid=(a8>=200).astype(np.uint8); dd=cv2.distanceTransform(solid,cv2.DIST_L2,3); div=float(np.percentile(a8[dd>6],1))
a8=np.clip(np.round(a8.astype(np.float64)*255/div),0,255).astype(np.uint8)
rgba=np.dstack([np.clip(np.round(col),0,255).astype(np.uint8),a8])
Image.fromarray(rgba,'RGBA').save(OUTP.replace('.png','-fullres.png'))
# 4) re-frame to 80% width on 1638x2048 (premultiplied, downscale only)
ys,xs=np.where(a8>8); bb=(int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1)
prod=Image.fromarray(rgba,'RGBA').crop(bb); pw,ph=prod.size; s=min(0.8*1638/pw,0.8*2048/ph); assert s<=1
f=np.array(prod).astype(np.float32)/255; pm=np.dstack([f[...,:3]*f[...,3:4],f[...,3:4]])
p=Image.fromarray((pm*255+0.5).astype(np.uint8),'RGBA').resize((round(pw*s),round(ph*s)),Image.LANCZOS)
b=np.array(p).astype(np.float32)/255; al=b[...,3:4]; rgb=np.where(al>1e-4,b[...,:3]/np.maximum(al,1e-4),0)
p2=Image.fromarray((np.dstack([rgb.clip(0,1),al])*255+0.5).astype(np.uint8),'RGBA')
can=Image.new('RGBA',(1638,2048),(0,0,0,0)); can.paste(p2,((1638-p2.width)//2,(2048-p2.height)//2))
ca=np.array(can); n2,l2,s2,_=cv2.connectedComponentsWithStats((ca[...,3]>0).astype(np.uint8),8); main=1+np.argmax(s2[1:,4]); specks=0
for i in range(1,n2):
    if i!=main and ca[...,3][l2==i].max()<P['speck_alpha']: ca[...,3][l2==i]=0; specks+=int((l2==i).sum())
Image.fromarray(ca,'RGBA').save(OUTP)
info={'params':P,'k':K,'alpha_clamp_divisor':div,'zone_px':int(zone.sum()),'outer_recovered_px':int(((alpha>0.04)&outer&(a0<=0.04)).sum()),'ramp_raised_px':int((outer&(alpha>a0+0.1)).sum()),'ramp_lowered_px':int((outer&(alpha<a0-0.1)).sum()),
      'inner_opened_px':int((paper_visible&(alpha<a0-0.02)).sum()),'inner_band_px':int(inner.sum()),'inner_paper_visible_px':int(paper_visible.sum()),
      'colour_replaced_px':int(fix.sum()),'colour_candidates_px':int(fix0.sum()),'colour_skipped_not_moving_away_px':int(fix0.sum()-fix.sum()),
      'colour_replaced_dE_to_paper_before_after_p50':[round(float(np.median(d_raw[ok_away])),2),round(float(np.median(d_T[ok_away])),2)] if ok_away.any() else None,
      'top_corner_candidates_px':top_cand,'top_corner_haze_cut_px':int(haze.sum()),'top_corner_cut_px':cut_px,'top_corner_alpha_le_0.5_px':top_opened,'top_corner_alpha_before_p50':round(float(np.median(top_before)),3) if top_cand else None,'bbox':bb,'scale':round(s,4),'placed':[(1638-p2.width)//2,(2048-p2.height)//2,p2.width,p2.height],'specks_zeroed_px':specks}
json.dump(info,open(OUTP.replace('.png','.json'),'w'),indent=1); print(json.dumps(info))
