import numpy as np, itertools, json
KU=28/36; KV=KU*16/9
def uv(c,P):
    Xc,Yc,H,yaw,u0,v0=c
    y=np.radians(yaw); f=np.array([-np.sin(y),-np.cos(y)]); r=np.array([np.cos(y),-np.sin(y)])
    P=np.atleast_2d(P); d=(P[:,:2]-[Xc,Yc])@f; x=(P[:,:2]-[Xc,Yc])@r
    return u0+KU*x/d, v0+KV*(H-P[:,2])/d, d
def circle(cx,cy,r,z,n=48):
    t=np.linspace(0,2*np.pi,n,endpoint=False); return np.stack([cx+r*np.cos(t),cy+r*np.sin(t),np.full(n,z)],1)
res=[]
for Xc,Yc,yaw,v0 in itertools.product(np.arange(0.3,1.01,0.05),np.arange(4.8,5.81,0.05),[6,7,8,9,10],np.arange(0.48,0.565,0.01)):
    c=(Xc,Yc,1.0,yaw,0.5,v0)
    pend=np.vstack([circle(0.2,1.72,0.2,2.15),circle(0.2,1.72,0.2,1.90)])
    pu,pv,_=uv(c,pend)
    top=pv.min()
    tab=np.array([[x,y,0.38] for x in (-0.4,0.8) for y in (1.395,2.045)]); tu,tv,_=uv(c,tab)
    art=uv(c,[[0.2,0,1.475]])[0][0]
    wb=uv(c,[[-2.3,0.9,1.6]])[0][0]; corner=uv(c,[[-2.3,0,1.6]])[0][0]
    fl=uv(c,circle(1.52,0.2,0.18,1.3))[0].max()
    sofa=uv(c,[[-0.9,0.95,0.2],[1.3,0.95,0.2]])[0]
    ok = top>=0.03 and tv.max()<=0.97 and wb>=0.06 and fl<=0.95
    if not ok: continue
    score = abs(yaw-8)*0.5 + abs(art-0.55)*10 + abs(top-0.04)*20 + abs(wb-0.12)*5 + abs(v0-0.5)*5
    res.append((round(score,3),dict(Xc=round(Xc,2),Yc=round(Yc,2),yaw=yaw,v0=round(v0,2),pend_top=round(top,3),table_front_v=round(tv.max(),3),art_u=round(art,3),win_back_u=round(wb,3),corner_u=round(corner,3),floorlamp_u=round(fl,3),sofa_u=[round(s,3) for s in sofa])))
res.sort(key=lambda t:t[0])
for r in res[:8]: print(r)
