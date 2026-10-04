# styled-preview: ONE global grade on step-d.png (no local correction).
# 1) global white-balance gains (linear, per channel) so the back-wall reference patch returns to the base
#    chromaticity (cancels the accumulated pink drift of the A->D chain); luminance-neutral (Y kept)
# 2) exposure, capped at +0.5 stop, aiming back-wall L at the base value
# 3) highlight shoulder as pilot grade.py; 4) black point lift (L floor) 0.12. No saturation operator.
import numpy as np, json, sys
from PIL import Image
R='/home/user/homedesign-app/'; P=R+'assets/renders/living-room/nordic/styled-preview/'
BASE=R+'assets/renders/living-room/nordic/m0/pilot-v4.1/m0-pilot-b-graded.png'
W,H=2752,1548
def s2l(x): return np.where(x<=0.04045,x/12.92,((x+0.055)/1.055)**2.4)
def l2s(x): return np.where(x<=0.0031308,x*12.92,1.055*np.power(np.clip(x,0,None),1/2.4)-0.055)
ref=(0.62,0.80,0.12,0.24)   # back wall above the art, right of the pendant
def mean_lin(a,box):
    u0,u1,v0,v1=box; return a[int(v0*H):int(v1*H),int(u0*W):int(u1*W)].reshape(-1,3).mean(0)
b=s2l(np.asarray(Image.open(BASE).convert('RGB'),float)/255)
d=s2l(np.asarray(Image.open(P+'step-d.png').convert('RGB'),float)/255)
mb,md=mean_lin(b,ref),mean_lin(d,ref)
Y=np.array([0.2126,0.7152,0.0722])
gain=(mb/mb.dot(Y))/(md/md.dot(Y))           # chromaticity match, Y-neutral
lin=d*gain
stops=float(np.clip(np.log2(mb.dot(Y)/(md*gain).dot(Y)),0,0.5))
lin=lin*2**stops
k=0.70; m=lin.max(2,keepdims=True)
mc=np.where(m>k,k+(0.985-k)*(1-np.exp(-(m-k)/(0.985-k))),m)
lin=lin*np.where(m>0,mc/np.maximum(m,1e-6),1)
bp=0.12
s=np.clip(bp+(1-bp)*l2s(lin),0,1)
Image.fromarray((s*255+0.5).astype(np.uint8)).save(P+'styled-preview.png')
rec={'wb_gain_linear_rgb':[round(x,4) for x in gain],'exposure_stops':round(stops,3),'shoulder_k':k,'black_point':bp,'ref_patch_uv':ref}
json.dump(rec,open(P+'raw/grade-params.json','w'),indent=1); print(rec)
