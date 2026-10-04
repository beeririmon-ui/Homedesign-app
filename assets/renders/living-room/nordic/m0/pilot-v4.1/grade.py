import numpy as np, colorsys
from PIL import Image
P='/home/user/homedesign-app/assets/renders/living-room/nordic/m0/pilot-v4.1/'
W,H=2752,1548
def s2l(x): return np.where(x<=0.04045,x/12.92,((x+0.055)/1.055)**2.4)
def l2s(x): return np.where(x<=0.0031308,x*12.92,1.055*np.power(np.clip(x,0,None),1/2.4)-0.055)
def grade(n,stops=0.5,bp=0.13):
    a=np.asarray(Image.open(P+f'm0-pilot-{n}.png'),float)/255
    lin=s2l(a)*2**stops
    k=0.70  # soft shoulder above k (per channel would shift hue; apply on max channel)
    m=lin.max(2,keepdims=True)
    mc=np.where(m>k,k+(0.985-k)*(1-np.exp(-(m-k)/(0.985-k))),m)
    lin=lin*np.where(m>0,mc/np.maximum(m,1e-6),1)
    s=l2s(lin)
    s=bp+(1-bp)*s   # black point lift (HSL L floor ~bp*100)
    return np.clip(s,0,1)
def hslL(a): return (a.max(2)+a.min(2))/2*100
def stats(a,tag):
    out={}
    def p(u,v,w=0.01):
        hw=int(w*W/2);x=int(u*W);y=int(v*H);c=a[y-hw:y+hw+1,x-hw:x+hw+1].reshape(-1,3).mean(0)
        h,l,s=colorsys.rgb_to_hls(*c);return (round(h*360,1),round(s*100,1),round(l*100,1))
    for k,(u,v) in {'win-wall front (0.10,0.30)':(0.10,0.30),'win-wall beside (0.405,0.30)':(0.405,0.30),'back near corner (0.467,0.385)':(0.467,0.385),'back behind sofa (0.69,0.22)':(0.69,0.22),'back behind sofa (0.69,0.42)':(0.69,0.42),'back right edge (0.97,0.31)':(0.97,0.31),'ceiling (0.55,0.04)':(0.55,0.04),'sofa back':(0.70,0.60),'sofa seat face':(0.6634,0.6733),'chair seat':(0.31,0.75),'chair back':(0.25,0.68),'table top':(0.62,0.715)}.items():
        out[k]=p(u,v)
    for k,(u,v) in {'chair leg':(0.382,0.74),'chair rail':(0.27,0.815)}.items(): out[k]=p(u,v,0.004)
    # floor region median
    reg=a[int(0.87*H):int(0.99*H),int(0.42*W):int(0.98*W)].reshape(-1,3)
    hls=np.array([colorsys.rgb_to_hls(*c) for c in reg[::37]])
    out['floor median (u0.42-0.98,v0.87-0.99) HSL']=(round(np.median(hls[:,0])*360,1),round(np.median(hls[:,2])*100,1),round(np.median(hls[:,1])*100,1))
    L=hslL(a);r=L[int(0.74*H):int(0.83*H),int(0.52*W):int(0.84*W)]
    out['under-sofa min L / p1']=(round(float(r.min()),1),round(float(np.percentile(r,1)),1))
    w=L[int(0.025*H):int(0.553*H),int(0.19*W):int(0.375*W)]
    sat=a.max(2)>=254.5/255
    out['window L p50/p99/max, 255px in/out']=(round(float(np.median(w)),1),round(float(np.percentile(w,99)),1),round(float(w.max()),1),int(sat[int(0.025*H):int(0.553*H),int(0.19*W):int(0.375*W)].sum()),int(sat.sum()-sat[int(0.025*H):int(0.553*H),int(0.19*W):int(0.375*W)].sum()))
    print('==',tag)
    for k,v in out.items(): print('  ',k,v)
    return out
import json
res={}
for n in ['a','b','text']:
    res[n]=stats(np.asarray(Image.open(P+f'm0-pilot-{n}.png'),float)/255,n)
g=grade("b",0.45,0.12); res['b-graded']=stats(g,'b graded +0.5 stop, bp 0.12 k0.70')
Image.fromarray((g*255+0.5).astype(np.uint8)).save(P+'m0-pilot-b-graded.png')
json.dump(res,open(P+'measurements-summary.json','w'),indent=1)
