# Are the colour_replaced_px matte decontamination only? (ours only)
# 1) Independent: fullres RGB vs the declared operation alone (raw x k in linear light). Every pixel that differs is a "replaced" pixel.
# 2) Where they are: alpha, side of the remove-bg 0.5 contour, distance.
# 3) What colour they got: vs raw, vs local paper, vs the nearest opaque thread pixels; compositing-equation residual raw ~ a*F + (1-a)*B.
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab, de00, lch
D=sys.argv[2].rstrip('/')+'/'; K=0.934
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB')).astype(np.float64)
nb=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png').convert('RGBA'))
fr=np.array(Image.open(D+'sofa-cover-cj-cotton-muslin-fringe/p2-nano-fixed-fullres.png').convert('RGBA'))
a0=nb[...,3]/255.; af=fr[...,3]/255.
def s2l(c): c=c/255.0; return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
def l2s(c): c=np.clip(c,0,1); return np.where(c<=0.0031308,12.92*c,1.055*c**(1/2.4)-0.055)*255
exp=np.clip(np.round(l2s(s2l(raw)*K)),0,255).astype(np.uint8)
diff=np.abs(fr[...,:3].astype(int)-exp.astype(int)).max(-1)
chg=diff>0
out={'rgb_px_differing_from_raw_x_k':int(chg.sum()),'of_which_diff_gt_1_level':int((diff>1).sum()),
     'rgb_identical_elsewhere':bool(((diff==0)|chg).all())}
ys,xs=np.nonzero(chg)
O5=(a0>=0.5).astype(np.uint8)
d_out=cv2.distanceTransform(1-O5,cv2.DIST_L2,3)
out['alpha_of_replaced_255']={'min':int(fr[...,3][chg].min()),'max':int(fr[...,3][chg].max()),'p50':float(np.median(fr[...,3][chg])),'n_alpha_ge_250':int((fr[...,3][chg]>=250).sum()),'n_alpha_0':int((fr[...,3][chg]==0).sum())}
out['side_of_removebg_05_contour']={'outside':int((O5[chg]==0).sum()),'inside':int((O5[chg]==1).sum()),'dist_outside_px_p50_max':[float(np.median(d_out[chg])),float(d_out[chg].max())]}
out['rows_x']={'y':[int(ys.min()),int(ys.max())],'x':[int(xs.min()),int(xs.max())]}
lab_raw=srgb_to_lab(np.clip(np.round(raw),0,255)); lab_exp=srgb_to_lab(exp); lab_fr=srgb_to_lab(fr[...,:3])
# local paper model (sure paper, extrapolated) after k
expf=exp.astype(np.float64)
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
wg=cv2.GaussianBlur(sure,(0,0),10); B=np.stack([cv2.GaussianBlur((expf[...,c]*sure).astype(np.float32),(0,0),10)/np.maximum(wg,1e-6) for c in range(3)],-1)
# nearest opaque thread colour: median of pixels with af>=0.98 and L within 3 of the local max (threads) in a 15x15 window
L=lab_exp[...,0]; Fm=cv2.dilate(L.astype(np.float32),np.ones((15,15),np.uint8))
thr=(af>=0.98)&(L>=Fm-6)
Tn=np.zeros_like(expf)
for c in range(3):
    num=cv2.blur((expf[...,c]*thr).astype(np.float32),(15,15)); den=cv2.blur(thr.astype(np.float32),(15,15)); Tn[...,c]=np.where(den>1e-3,num/np.maximum(den,1e-3),np.nan)
labB=srgb_to_lab(np.clip(B,0,255)); labT=srgb_to_lab(np.clip(np.nan_to_num(Tn),0,255))
sel=chg&np.isfinite(Tn).all(-1)
def st(v): return {'p50':round(float(np.median(v)),2),'p95':round(float(np.percentile(v,95)),2),'max':round(float(v.max()),2)}
out['replaced_vs_before_L']={'before_L_p50':round(float(np.median(lab_exp[...,0][chg])),2),'after_L_p50':round(float(np.median(lab_fr[...,0][chg])),2),'dL_after_minus_before':st(lab_fr[...,0][chg]-lab_exp[...,0][chg])}
out['dE00_after_vs_local_paper']=st(de00(lab_fr[chg],labB[chg]))
out['dE00_before_vs_local_paper']=st(de00(lab_exp[chg],labB[chg]))
out['dE00_after_vs_nearby_opaque_threads']=st(de00(lab_fr[sel],labT[sel]))
out['dE00_before_vs_nearby_opaque_threads']=st(de00(lab_exp[sel],labT[sel]))
out['after_LCh_p50']=lch(np.median(lab_fr[chg],0)); out['nearby_threads_LCh_p50']=lch(np.median(labT[sel],0)); out['paper_LCh_p50']=lch(np.median(labB[chg],0))
# compositing equation: raw(after k) ~ a*F + (1-a)*B, residual in 8-bit RGB, F = after colour, vs F = before colour (no decontam)
a=af[chg][:,None]
res_after=np.abs(expf[chg]-(a*fr[...,:3][chg]+(1-a)*B[chg])).mean(-1)
res_before=np.abs(expf[chg]-(a*expf[chg]+(1-a)*B[chg])).mean(-1)
out['compositing_residual_8bit']={'with_replaced_colour':st(res_after),'if_raw_colour_kept':st(res_before)}
# what the viewer sees: composites on paper and dark, replaced vs kept
for name,bg in [('paper',(0xF4,0xF1,0xEC)),('dark',(0x3A,0x3A,0x3A))]:
    bgv=np.array(bg,float)
    ca=fr[...,:3][chg]*a+bgv*(1-a); cb=expf[chg]*a+bgv*(1-a); cr=raw[chg]*0+expf[chg]  # cr: the raw photo itself (on our palette)
    out[f'composite_{name}']={'dE00_replaced_vs_kept':st(de00(srgb_to_lab(np.clip(ca,0,255)),srgb_to_lab(np.clip(cb,0,255))))}
# the tool's own fix mask, recomputed by its code path (to tie the count to colour_replaced_px)
np.save(sys.argv[3],chg)
print(json.dumps(out,indent=1))
