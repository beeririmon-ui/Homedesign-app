# styled-preview: fetch raw -> 2752x1548 (Lanczos, no crop) -> geometry/colour checks vs base
import sys, json, hashlib, subprocess, numpy as np
from PIL import Image
R='/home/user/homedesign-app/'
P=R+'assets/renders/living-room/nordic/styled-preview/'
BASE=R+'assets/renders/living-room/nordic/m0/pilot-v4.1/m0-pilot-b-graded.png'
W,H=2752,1548
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
def patch(a,u,v,w=0.01):
    hw=max(2,int(w*W/2)); x=int(u*W); y=int(v*H); return hsl(a[y-hw:y+hw+1,x-hw:x+hw+1].reshape(-1,3).mean(0))
# regions chosen to avoid areas that the step legitimately edits as far as possible
regions={'frame':(0.05,0.95,0.05,0.95),'corner+cornice':(0.40,0.50,0.0,0.30),'window':(0.20,0.37,0.03,0.50),
 'cornice-right':(0.55,0.95,0.0,0.12),'sofa':(0.5208,0.8396,0.5509,0.7949),'table':(0.512,0.762,0.6787,0.8699),
 'armchair':(0.1896,0.3867,0.6218,0.9056)}
pts={'win-wall (0.10,0.30)':(0.10,0.30),'back wall (0.69,0.22)':(0.69,0.22),'back wall right (0.97,0.31)':(0.97,0.31),
 'sofa back cushion (0.70,0.60)':(0.70,0.60),'sofa seat face (0.663,0.673)':(0.6634,0.6733),'armchair seat (0.31,0.75)':(0.31,0.75),
 'armchair back (0.25,0.68)':(0.25,0.68),'table top (0.62,0.715)':(0.62,0.715),'floor (0.92,0.85)':(0.92,0.85)}
def window_L(a):
    L=(a.max(2)+a.min(2))/2/255*100; w=L[int(0.025*H):int(0.553*H),int(0.19*W):int(0.375*W)]
    return {'p50':round(float(np.median(w)),1),'p99':round(float(np.percentile(w,99)),1),'frame_p99_outside':round(float(np.percentile(np.concatenate([L[:,:int(0.19*W)].ravel(),L[:,int(0.375*W):].ravel()]),99.5)),1)}
if __name__=='__main__':
    step,url=sys.argv[1],sys.argv[2]
    raw=P+f'raw/step-{step}.jpg'
    subprocess.run(['curl','-sS','-o',raw,url],check=True)
    im=Image.open(raw); rs=im.size
    out=im.convert('RGB') if im.size==(W,H) else im.convert('RGB').resize((W,H),Image.LANCZOS)
    out.save(P+f'step-{step}.png')
    a=np.asarray(out,float); b=np.asarray(Image.open(BASE).convert('RGB'),float)
    ga=grad(np.asarray(Image.open(BASE).convert('L'),float)); gi=grad(np.asarray(out.convert('L'),float))
    res={'raw_size':rs,'raw_sha256':hashlib.sha256(open(raw,'rb').read()).hexdigest(),
      'shifts_vs_base':{k:shift(ga,gi,bx) for k,bx in regions.items()},
      'patches':{k:{'base':patch(b,*p),'step':patch(a,*p)} for k,p in pts.items()},
      'window_L':{'base':window_L(b),'step':window_L(a)}}
    json.dump(res,open(P+f'raw/step-{step}-check.json','w'),indent=1)
    print(json.dumps(res,indent=1))
