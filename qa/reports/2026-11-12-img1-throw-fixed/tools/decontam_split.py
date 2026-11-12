# Split the replaced pixels: moved toward the thread (decontamination) vs toward the paper (re-contamination). Ours only.
import sys, json, numpy as np, cv2
sys.path.insert(0,sys.argv[1]); from lab import srgb_to_lab, de00
from PIL import Image
D=sys.argv[2].rstrip('/')+'/'; chg=np.load(sys.argv[3])
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB')).astype(float)
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
fr=np.array(Image.open(D+'sofa-cover-cj-cotton-muslin-fringe/p2-nano-fixed-fullres.png')).astype(float)
K=0.934
def s2l(c): c=c/255.0; return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
def l2s(c): c=np.clip(c,0,1); return np.where(c<=0.0031308,12.92*c,1.055*c**(1/2.4)-0.055)*255
exp=np.round(l2s(s2l(raw)*K))
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
wg=cv2.GaussianBlur(sure,(0,0),10); B=np.stack([cv2.GaussianBlur((exp[...,c]*sure).astype(np.float32),(0,0),10)/np.maximum(wg,1e-6) for c in range(3)],-1)
la=srgb_to_lab(fr[...,:3][chg]); lb=srgb_to_lab(exp[chg]); lp=srgb_to_lab(np.clip(B[chg],0,255))
dPa=de00(la,lp); dPb=de00(lb,lp); dL=la[:,0]-lb[:,0]; a=fr[...,3][chg]/255.
toward_paper=dPa<dPb-0.5; away=dPa>dPb+0.5
out={'n':int(chg.sum()),
 'moved_away_from_paper':int(away.sum()),'moved_toward_paper':int(toward_paper.sum()),'about_unchanged':int((~away&~toward_paper).sum()),
 'toward_paper':{'dL_p50':round(float(np.median(dL[toward_paper])),2),'dL_min':round(float(dL[toward_paper].min()),2),
   'dE00_to_paper_before_after_p50':[round(float(np.median(dPb[toward_paper])),2),round(float(np.median(dPa[toward_paper])),2)],
   'alpha_p50':round(float(np.median(a[toward_paper])),2),
   'n_after_within_dE00_3_of_paper':int((dPa[toward_paper]<=3).sum())},
 'away_from_paper':{'dL_p50':round(float(np.median(dL[away])),2),'dE00_to_paper_before_after_p50':[round(float(np.median(dPb[away])),2),round(float(np.median(dPa[away])),2)]}}
# visible effect of the toward-paper pixels on dark: composite dE00 vs keeping the raw colour
bg=np.array([0x3A,0x3A,0x3A],float)
ca=fr[...,:3][chg]*a[:,None]+bg*(1-a[:,None]); cb=exp[chg]*a[:,None]+bg*(1-a[:,None])
d=de00(srgb_to_lab(ca),srgb_to_lab(cb))
out['toward_paper']['dark_composite_dE00_vs_kept_p50_max']=[round(float(np.median(d[toward_paper])),2),round(float(d[toward_paper].max()),2)]
print(json.dumps(out,indent=1))
