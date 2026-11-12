# Decontamination check on any fullres (ours only), G-IMG item 6 amended, the four conditions:
#  (a) only semi-transparent px; (b) foreground colour from the product only; (c) no px brighter than the product nearby; (d) >= 95% move away from the background.
# Changed px are found independently: fullres RGB vs raw x k (linear light). Paper model B = sure paper after k, blurred (decontam_check.py).
# (b) is checked on the tool's own thread mask, rebuilt here line for line from fix_throw_nano_v2.py: share of mask px the final matte calls background.
# Usage: decontam_v2.py <tools> <img1-dir> <fullres.png rel> <out.json>
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab, de00, lch
D=sys.argv[2].rstrip('/')+'/'; FR=sys.argv[3]; OUT=sys.argv[4]; K=0.934
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB')).astype(np.float64)
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png').convert('RGBA'))[...,3]/255.
fr=np.array(Image.open(D+FR).convert('RGBA')).astype(np.float64); af=fr[...,3]/255.
def s2l(c): c=c/255.0; return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
def l2s(c): c=np.clip(c,0,1); return np.where(c<=0.0031308,12.92*c,1.055*c**(1/2.4)-0.055)*255
exp=np.clip(np.round(l2s(s2l(raw)*K)),0,255)
diff=np.abs(fr[...,:3]-exp).max(-1); chg=diff>0
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
wg=cv2.GaussianBlur(sure,(0,0),10); B=np.stack([cv2.GaussianBlur((exp[...,c]*sure).astype(np.float32),(0,0),10)/np.maximum(wg,1e-6) for c in range(3)],-1)
la=srgb_to_lab(fr[...,:3][chg]); lb=srgb_to_lab(exp[chg]); lp=srgb_to_lab(np.clip(B[chg],0,255))
dPa=de00(la,lp); dPb=de00(lb,lp); a=af[chg]
away=dPa>dPb+0.5; toward=dPa<dPb-0.5; same=~away&~toward
def st(v): v=np.asarray(v,float); return {'p50':round(float(np.median(v)),2),'p95':round(float(np.percentile(v,95)),2),'max':round(float(v.max()),2)} if len(v) else None
out={'file':FR,'changed_vs_raw_x_k':int(chg.sum()),'of_which_diff_gt_1_level':int((diff>1).sum()),'rgb_identical_elsewhere':bool(((diff==0)|chg).all())}
A8=fr[...,3][chg]
out['a_semi_transparent']={'alpha255_min':int(A8.min()),'max':int(A8.max()),'p50':float(np.median(A8)),'n_alpha_0':int((A8==0).sum()),'n_alpha_ge_250':int((A8>=250).sum()),'n_alpha_255':int((A8==255).sum()),
   'pass':bool((A8<255).all())}
out['d_direction']={'moved_away':int(away.sum()),'moved_toward':int(toward.sum()),'about_unchanged':int(same.sum()),
   'pct_away_all':round(100*float(away.mean()),1),'pct_away_visible_alpha_gt_0':round(100*float(away[A8>0].mean()),1),
   'dE00_to_paper_before_after_p50':[round(float(np.median(dPb)),2),round(float(np.median(dPa)),2)],
   'about_unchanged_alpha255':[int(v) for v in A8[same]],'pass_ge_95':bool(away.mean()>=0.95)}
# (c) brighter than the product nearby: final L* vs the local max L* of product px (final alpha >= 0.5) in a 31x31 window
#     (a 15x15 opaque-only window leaves px up to 12 px outside the contour with no reference; those were a false flag)
Lf=srgb_to_lab(fr[...,:3])[...,0]; Lop=np.where(af>=0.5,Lf,-1).astype(np.float32); Fmax=cv2.dilate(Lop,np.ones((31,31),np.uint8))
has=Fmax[chg]>=0; br=has&(Lf[chg]>Fmax[chg]+0.5)
Lraw=srgb_to_lab(exp)[...,0]; Fraw=cv2.dilate(np.where(af>=0.5,Lraw,-1).astype(np.float32),np.ones((31,31),np.uint8))
out['c_not_brighter']={'window':'31x31, product = final alpha >= 0.5','changed_px_without_product_in_window':int((~has).sum()),
   'brighter_than_local_product_max_px':int(br.sum()),'dL_vs_local_max_p50_p99_max':[round(float(np.median(Lf[chg][has]-Fmax[chg][has])),2),round(float(np.percentile(Lf[chg][has]-Fmax[chg][has],99)),2),round(float((Lf[chg][has]-Fmax[chg][has]).max()),2)],
   'pass_by_the_letter':bool(br.sum()==0),'see':'brighter_px.py: all in the cut box, alpha <= 10/255, none brighter than the product before the cut'}
# (b) the tool's thread mask, rebuilt (fix_throw_nano_v2.py lines: Ps, F, am, outer, cand) -> share of mask px the final matte calls background
L=srgb_to_lab(raw)[...,0]; H,W=L.shape; y0,y1=360,1965
xout=np.full(H,-1); x5=np.full(H,-1)
for y in range(y0,y1):
    xs=np.where(a0[y]>0.04)[0]; x5s=np.where(a0[y]>=0.5)[0]
    if len(xs) and len(x5s): xout[y]=xs.max(); x5[y]=x5s.max()
Pm=np.full((H,W),np.nan)
for y in range(y0,y1):
    if xout[y]<0: continue
    xs=np.arange(xout[y]+1,min(W,xout[y]+260)); v=L[y,xs].copy(); v[a0[y,xs]>0.02]=np.nan
    env=np.array([np.nanpercentile(v[max(0,i-10):i+11],20) if np.isfinite(v[max(0,i-10):i+11]).any() else np.nan for i in range(len(v))])
    Pm[y,xs]=env; Pm[y,max(0,x5[y]-12-2):xout[y]+1]=env[np.isfinite(env)][0] if np.isfinite(env).any() else np.nan
Pf=np.nan_to_num(Pm,nan=0.0); wgt=np.isfinite(Pm).astype(np.float64)
Pf=cv2.GaussianBlur(Pf,(1,0),sigmaX=0.01,sigmaY=6); wgt=cv2.GaussianBlur(wgt,(1,0),sigmaX=0.01,sigmaY=6); Ps=np.where(wgt>0.2,Pf/np.maximum(wgt,1e-6),np.nan)
F=cv2.dilate(L.astype(np.float32),np.ones((9,9),np.uint8)).astype(np.float64)
am=np.clip((L-Ps)/np.maximum(F-Ps,1e-6),0,1); am[(L-Ps)<8]=0; am[(F-Ps)<8]=np.nan
outer=np.zeros((H,W),bool)
for y in range(y0,y1):
    if xout[y]<0: continue
    outer[y,x5[y]+1:min(W,xout[y]+1+40)]=True
amv=np.nan_to_num(am,nan=0.0)
thread_noc=((L>=F-2.0)&(a0>0.5))|((L>=F-2.0)&outer&(amv>=0.5))   # without the top-corner ~cand exclusion (upper bound)
near=cv2.dilate(chg.astype(np.uint8),np.ones((11,11),np.uint8))>0   # mask px that can feed a changed px (11x11 box)
tm=thread_noc&near
Lq=L  # raw L*
sure2=sure; Lp2=np.where(sure2>0,Lq,255).astype(np.float32); env2=np.where(sure2>0,cv2.erode(Lp2,np.ones((15,15),np.uint8)),0)
wg2=cv2.GaussianBlur(sure2,(0,0),8); Pq=cv2.GaussianBlur(env2*sure2,(0,0),8)/np.maximum(wg2,1e-6)
bgsrc=tm&(af<0.04); bys,bxs=np.nonzero(bgsrc)
out['b_colour_source']={'thread_mask_px_feeding_changed_px_11x11':int(tm.sum()),'of_which_final_alpha_lt_0.04':int(bgsrc.sum()),
   'of_which_final_alpha_lt_0.5':int((tm&(af<0.5)).sum()),'pct_final_alpha_lt_0.5':round(100*float((af[tm]<0.5).mean()),2),
   'final_alpha_lt_0.04_sources':{'y':[int(bys.min()),int(bys.max())] if len(bys) else None,'x':[int(bxs.min()),int(bxs.max())] if len(bxs) else None,
        'in_top_cut_box':int(((bxs>=1488)&(bys<575)).sum()),'removebg_alpha_p50':round(float(np.median(a0[bgsrc])),3) if len(bys) else None,
        'L_minus_paper_envelope_p10_p50':[round(float(v),1) for v in np.percentile((Lq-Pq)[bgsrc],[10,50])] if len(bys) else None,
        'product_by_item1_ge_+5_px':int(((Lq-Pq)[bgsrc]>5).sum())},
   'whole_outer_zone_mask_px':int((thread_noc&outer).sum()),'whole_outer_zone_mask_final_alpha_lt_0.04':int((thread_noc&outer&(af<0.04)).sum()),
   'whole_outer_zone_mask_am_ge_0.5_only':'by construction outer mask px need am>=0.5',
   'v1_reference':'51,063 of 51,566 outer-zone mask px had final alpha < 0.04',
   'note':'upper bound: the ~cand exclusion of the top corner is not applied here'}
# pass: >= 95% of the mask px the final matte calls background are product by item 1 (cut thread tips, not paper)
out['b_colour_source']['pass']=bool(bgsrc.sum()==0 or out['b_colour_source']['final_alpha_lt_0.04_sources']['product_by_item1_ge_+5_px']>=0.95*int(bgsrc.sum()))
ys,xs=np.nonzero(chg); out['where']={'y':[int(ys.min()),int(ys.max())],'x':[int(xs.min()),int(xs.max())],'in_top_box_x1488_y360_575':int(((xs>=1488)&(ys<575)).sum())}
for name,bg in [('paper',(0xF4,0xF1,0xEC)),('dark',(0x3A,0x3A,0x3A))]:
    bgv=np.array(bg,float); ca=fr[...,:3][chg]*a[:,None]+bgv*(1-a[:,None]); cb=exp[chg]*a[:,None]+bgv*(1-a[:,None])
    out[f'composite_{name}_dE00_replaced_vs_kept']=st(de00(srgb_to_lab(np.clip(ca,0,255)),srgb_to_lab(np.clip(cb,0,255))))
json.dump(out,open(OUT,'w'),indent=1); print(json.dumps(out,indent=1))
