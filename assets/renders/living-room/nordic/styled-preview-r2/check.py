# styled-preview round 2: fetch raw -> 2752x1548 (Lanczos, no crop) -> checks vs base -> colour lock (brief 10.4)
# usage: python3 check.py <step> <result_url>
# Colour lock: if back wall (0.69,0.22) H outside 26-40, or armchair seat (0.31,0.75) H<25 with S>15,
# apply ONE global white-balance (linear per-channel gains, luminance Y kept) that puts the back-wall
# patch at H 33 (target band 30-36), same S and L. No local correction, no saturation operator.
import sys, json, hashlib, subprocess, colorsys, numpy as np
from PIL import Image
R='/home/user/homedesign-app/'
P=R+'assets/renders/living-room/nordic/styled-preview-r2/'
BASE=R+'assets/renders/living-room/nordic/m0/pilot-v4.1/m0-pilot-b-graded.png'
W,H=2752,1548
def s2l(x): return np.where(x<=0.04045,x/12.92,((x+0.055)/1.055)**2.4)
def l2s(x): return np.where(x<=0.0031308,x*12.92,1.055*np.power(np.clip(x,0,None),1/2.4)-0.055)
def grad(g):
    gx=np.zeros_like(g); gy=np.zeros_like(g)
    gx[:,1:-1]=g[:,2:]-g[:,:-2]; gy[1:-1]=g[2:]-g[:-2]
    return np.hypot(gx,gy)
def shift(ga,gi,box,s=14):
    u0,u1,v0,v1=box; x0,x1,y0,y1=int(u0*W),int(u1*W),int(v0*H),int(v1*H)
    A=ga[y0:y1,x0:x1]; A=(A-A.mean())/(A.std()+1e-9); best=(-9,0,0)
    for dy in range(-s,s+1):
        for dx in range(-s,s+1):
            ys,xs=y0+dy,x0+dx
            if ys<0 or xs<0 or ys+(y1-y0)>H or xs+(x1-x0)>W: continue
            B=gi[ys:ys+(y1-y0),xs:xs+(x1-x0)]; B=(B-B.mean())/(B.std()+1e-9)
            c=(A*B).mean()
            if c>best[0]: best=(c,dx,dy)
    return {'corr':round(best[0],3),'du':round(best[1]/W,4),'dv':round(best[2]/H,4)}
def hsl(c):
    r,g,b=[x/255 for x in c]; mx,mn=max(r,g,b),min(r,g,b); l=(mx+mn)/2
    if mx==mn: return (0.0,0.0,round(l*100,1))
    d=mx-mn; s=d/(2-mx-mn) if l>0.5 else d/(mx+mn)
    h=((g-b)/d)%6 if mx==r else ((b-r)/d+2 if mx==g else (r-g)/d+4)
    return (round(h*60,1),round(s*100,1),round(l*100,1))
def pmean(a,u,v,w=0.01):
    hw=max(2,int(w*W/2)); x=int(u*W); y=int(v*H); return a[y-hw:y+hw+1,x-hw:x+hw+1].reshape(-1,3).mean(0)
regions={'frame':(0.05,0.95,0.05,0.95),'corner+cornice':(0.40,0.50,0.0,0.30),'window':(0.20,0.37,0.03,0.50),
 'cornice-right':(0.55,0.95,0.0,0.12),'sofa':(0.5208,0.8396,0.5509,0.7949),'table':(0.512,0.762,0.6787,0.8699),
 'armchair':(0.1896,0.3867,0.6218,0.9056)}
pts={'back wall (0.69,0.22)':(0.69,0.22),'back wall right (0.97,0.31)':(0.97,0.31),'armchair seat (0.31,0.75)':(0.31,0.75),
 'rug (0.60,0.93)':(0.60,0.93),'sofa back cushion (0.70,0.60)':(0.70,0.60),'win-wall (0.10,0.30)':(0.10,0.30),
 'table top (0.62,0.715)':(0.62,0.715),'floor (0.92,0.85)':(0.92,0.85)}
def window_L(a):
    L=(a.max(2)+a.min(2))/2/255*100; w=L[int(0.025*H):int(0.553*H),int(0.19*W):int(0.375*W)]
    return {'p50':round(float(np.median(w)),1),'p99':round(float(np.percentile(w,99)),1),
            'rest_p99.5':round(float(np.percentile(np.concatenate([L[:,:int(0.19*W)].ravel(),L[:,int(0.375*W):].ravel()]),99.5)),1)}
def patches(a): return {k:hsl(pmean(a,*p)) for k,p in pts.items()}
def colour_lock(a):
    bw=hsl(pmean(a,0.69,0.22)); ac=hsl(pmean(a,0.31,0.75))
    need=not(26<=bw[0]<=40) or (ac[0]<25 and ac[1]>15)
    if not need: return a,None
    lin=s2l(a/255); cur=s2l(pmean(a,0.69,0.22)/255)
    r,g,b=colorsys.hls_to_rgb(33/360,bw[2]/100,max(bw[1],1)/100); tgt=s2l(np.array([r,g,b]))
    Y=np.array([0.2126,0.7152,0.0722])
    gain=(tgt/tgt.dot(Y))/(cur/cur.dot(Y))
    out=np.clip(l2s(lin*gain),0,1)*255
    return out,[round(float(x),4) for x in gain]
if __name__=='__main__':
    step,url=sys.argv[1],sys.argv[2]
    tag=sys.argv[3] if len(sys.argv)>3 else step
    raw=P+f'raw/step-{tag}.jpg'
    subprocess.run(['curl','-sS','-o',raw,url],check=True)
    im=Image.open(raw); rs=im.size
    out=im.convert('RGB') if im.size==(W,H) else im.convert('RGB').resize((W,H),Image.LANCZOS)
    a=np.asarray(out,float); b=np.asarray(Image.open(BASE).convert('RGB'),float)
    before=patches(a)
    a2,gain=colour_lock(a)
    Image.fromarray((a2+0.5).astype(np.uint8)).save(P+f'step-{tag}.png')
    ga=grad(np.asarray(Image.open(BASE).convert('L'),float)); gi=grad(a2.mean(2))
    res={'raw_size':rs,'raw_sha256':hashlib.sha256(open(raw,'rb').read()).hexdigest(),
      'colour_lock_gain_linear_rgb':gain,
      'patches':{'base':patches(b),'raw':before,'after_lock':patches(a2)},
      'window_L':{'base':window_L(b),'step':window_L(a2)},
      'shifts_vs_base':{k:shift(ga,gi,bx) for k,bx in regions.items()}}
    json.dump(res,open(P+f'raw/step-{tag}-check.json','w'),indent=1)
    print(json.dumps({k:v for k,v in res.items() if k!='shifts_vs_base'},indent=1)); print(json.dumps(res['shifts_vs_base']))
