import sys, numpy as np, json, cv2
from PIL import Image
# vase_clamp_check.py <lab_dir> <before.png> <after.png> <divisor>: alpha-only change? RGB untouched? composite dE00 before/after
sys.path.insert(0,sys.argv[1]); from lab import srgb_to_lab, de00
b=np.array(Image.open(sys.argv[2]).convert('RGBA')).astype(int); a=np.array(Image.open(sys.argv[3]).convert('RGBA')).astype(int); div=float(sys.argv[4])
ab,aa=b[...,3],a[...,3]; out={'rgb_changed_px':int((np.abs(b[...,:3]-a[...,:3]).max(-1)>0).sum())}
out['alpha_rule_mismatch_px']=int((np.clip(np.round(ab*255/div),0,255).astype(int)!=aa).sum())
out['zero_to_nonzero']=int(((ab==0)&(aa>0)).sum()); out['nonzero_to_zero']=int(((ab>0)&(aa==0)).sum())
inner=cv2.erode((aa>=128).astype(np.uint8),np.ones((9,9),np.uint8)).astype(bool)
out['interior_after_p0.1_p1_p50']=[float(x) for x in np.percentile(aa[inner],[0.1,1,50])]
for name,bg in [('paper',(0xF4,0xF1,0xEC)),('dark',(0x3A,0x3A,0x3A))]:
    bg=np.array(bg,float); m=(ab>0)|(aa>0)
    cb=b[...,:3]*(ab[...,None]/255)+bg*(1-ab[...,None]/255); ca=a[...,:3]*(aa[...,None]/255)+bg*(1-aa[...,None]/255)
    d=de00(srgb_to_lab(cb[m]),srgb_to_lab(ca[m])); out['composite_dE00_'+name]={'max':round(float(d.max()),3),'p99':round(float(np.percentile(d,99)),3),'px_gt_1':int((d>1).sum())}
print(json.dumps(out))
