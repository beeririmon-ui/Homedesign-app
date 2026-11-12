# Condition (c) detail (ours only): changed px brighter than the local product max (final alpha >= 0.5, 31x31) - where, alpha,
# and was the raw x k colour there already brighter (i.e. the cut removed the bright neighbours) or did the replacement make it brighter.
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab
D=sys.argv[2].rstrip('/')+'/'; K=0.934
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB')).astype(np.float64)
fr=np.array(Image.open(D+'sofa-cover-cj-cotton-muslin-fringe/p2-nano-fixed-v2-fullres.png').convert('RGBA')).astype(np.float64); af=fr[...,3]/255.
def s2l(c): c=c/255.0; return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
def l2s(c): c=np.clip(c,0,1); return np.where(c<=0.0031308,12.92*c,1.055*c**(1/2.4)-0.055)*255
exp=np.clip(np.round(l2s(s2l(raw)*K)),0,255); chg=np.abs(fr[...,:3]-exp).max(-1)>0
Lf=srgb_to_lab(fr[...,:3])[...,0]; Le=srgb_to_lab(exp)[...,0]
Fmax=cv2.dilate(np.where(af>=0.5,Lf,-1).astype(np.float32),np.ones((31,31),np.uint8))
# the same reference with the v1 alpha (before the cut)
a1=np.array(Image.open(D+'sofa-cover-cj-cotton-muslin-fringe/p2-nano-fixed-fullres.png'))[...,3]/255.
F1=cv2.dilate(np.where(a1>=0.5,Le,-1).astype(np.float32),np.ones((31,31),np.uint8))
m=chg&(Fmax>=0)&(Lf>Fmax+0.5); ys,xs=np.nonzero(m)
r={'n':int(m.sum()),'y':[int(ys.min()),int(ys.max())],'x':[int(xs.min()),int(xs.max())],'in_top_cut_box':int(((xs>=1488)&(ys<575)).sum()),
   'alpha255':sorted(int(v) for v in fr[...,3][m]),'dL_final_vs_local_product_max':[round(float(v),1) for v in sorted(Lf[m]-Fmax[m])],
   'raw_x_k_was_already_brighter_than_that_max':int((Le[m]>Fmax[m]+0.5).sum()),
   'final_vs_raw_x_k_dL_p50':round(float(np.median(Lf[m]-Le[m])),2),
   'brighter_than_the_product_max_before_the_cut_(v1 alpha)':int((Lf[m]>F1[m]+0.5).sum())}
# visible contribution: alpha-weighted excess on dark and paper (8-bit, luminance of the composite vs composite with the local max colour)
print(json.dumps(r,indent=1))
