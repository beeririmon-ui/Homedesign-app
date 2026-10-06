# styled-preview round 2: ONE global grade on step-d.png (brief 10.5). No local correction, no saturation operator.
# 1) global white balance: linear per-channel gains, luminance (Y) kept, back-wall patch (0.69,0.22) to H 35
# 2) exposure: aim back-wall L at 88, capped at +0.2 stop (brief cap)
# 3) highlight shoulder (as round 1, k 0.70)  4) black point 0.125 (L 12-13)  5) gentle S curve (mix 0.12)
import json, colorsys, numpy as np
from PIL import Image
R='/home/user/homedesign-app/'; P=R+'assets/renders/living-room/nordic/styled-preview-r2/'
W,H=2752,1548
def s2l(x): return np.where(x<=0.04045,x/12.92,((x+0.055)/1.055)**2.4)
def l2s(x): return np.where(x<=0.0031308,x*12.92,1.055*np.power(np.clip(x,0,None),1/2.4)-0.055)
def pmean(a,u,v,w=0.01):
    hw=max(2,int(w*W/2)); x=int(u*W); y=int(v*H); return a[y-hw:y+hw+1,x-hw:x+hw+1].reshape(-1,3).mean(0)
d=np.asarray(Image.open(P+'step-d.png').convert('RGB'),float)/255
lin=s2l(d)
cur=s2l(pmean(d,0.69,0.22)); h,l,s=colorsys.rgb_to_hls(*pmean(d,0.69,0.22))
tgt=s2l(np.array(colorsys.hls_to_rgb(35/360,l,s)))
Y=np.array([0.2126,0.7152,0.0722])
gain=(tgt/tgt.dot(Y))/(cur/cur.dot(Y)); lin=lin*gain
wallL=lambda a: (lambda c:(c.max()+c.min())/2)(l2s(pmean(a,0.69,0.22)))
Lw=wallL(lin)
stops=float(np.clip(np.log2(s2l(np.array(0.88))/s2l(np.array(Lw))),0,0.2)); lin=lin*2**stops
k=0.70; m=lin.max(2,keepdims=True)
mc=np.where(m>k,k+(0.985-k)*(1-np.exp(-(m-k)/(0.985-k))),m)
lin=lin*np.where(m>0,mc/np.maximum(m,1e-6),1)
sv=np.clip(l2s(lin),0,1)
mix=0.12; sv=(1-mix)*sv+mix*(sv*sv*(3-2*sv))
bp=0.125; sv=np.clip(bp+(1-bp)*sv,0,1)
Image.fromarray((sv*255+0.5).astype(np.uint8)).save(P+'styled-preview.png')
rec={'wb_gain_linear_rgb':[round(float(x),4) for x in gain],'wb_target_backwall_H':35,'exposure_stops':round(stops,3),
     'shoulder_k':k,'s_curve_mix':mix,'black_point':bp}
json.dump(rec,open(P+'raw/grade-params.json','w'),indent=1); print(rec)
