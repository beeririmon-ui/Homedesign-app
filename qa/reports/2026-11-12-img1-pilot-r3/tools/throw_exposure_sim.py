import sys, numpy as np, json, cv2
from PIL import Image
# throw_exposure_sim.py <lab_dir> <p2.png> <target_L>: linear-light gain k so the lit side (p90-99 L*, alpha>=0.9) hits target; texture change; SIMULATION ONLY
sys.path.insert(0,sys.argv[1]); from lab import srgb_to_lab, lch
im=np.array(Image.open(sys.argv[2]).convert('RGBA')).astype(float); tgt=float(sys.argv[3]); rgb=im[...,:3]; m=im[...,3]>=0.9*255
lin=lambda c:np.where(c/255<=0.04045,c/255/12.92,((c/255+0.055)/1.055)**2.4); enc=lambda l:255*np.where(np.clip(l,0,1)<=0.0031308,12.92*np.clip(l,0,1),1.055*np.clip(l,0,1)**(1/2.4)-0.055)
def lit(x):
    lab=srgb_to_lab(x[m]); L=lab[:,0]; p90,p99=np.percentile(L,[90,99]); return lch(np.median(lab[(L>=p90)&(L<=p99)],0))
def hp(x):
    L=srgb_to_lab(x)[...,0]; return float(np.std((L-cv2.GaussianBlur(L,(0,0),8))[cv2.erode(m.astype(np.uint8),np.ones((15,15)))>0]))
lo,hi=0.7,1.0
for _ in range(30):
    k=(lo+hi)/2
    if lit(enc(lin(rgb)*k))[0]>tgt: hi=k
    else: lo=k
x=enc(lin(rgb)*k); print(json.dumps({'k':round(k,4),'lit_before':lit(rgb),'lit_after':lit(x),'hp_std_change_pct':round(100*(hp(x)/hp(rgb)-1),1)}))
