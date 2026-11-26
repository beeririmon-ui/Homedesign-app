import numpy as np, cv2
KU=28/36; KV=KU*16/9; c=(0.60,5.35,1.0,8.0,0.5,0.5)
def uv(P):
    Xc,Yc,H,yaw,u0,v0=c; y=np.radians(yaw); f=np.array([-np.sin(y),-np.cos(y)]); r=np.array([np.cos(y),-np.sin(y)])
    d=(P[:,:2]-[Xc,Yc])@f; x=(P[:,:2]-[Xc,Yc])@r; return u0+KU*x/d, v0+KV*(H-P[:,2])/d
def sil(cx,cy,D=0.50,H=0.35,W=960,Hh=540,m=600):
    t=np.linspace(0,2*np.pi,64,endpoint=False); pts=[]
    for z in np.linspace(0,H,8):
        rr=D/2*np.sqrt(max(0,1-((z-H/2)/(H/2+1e-9))**2))**0.6
        pts.append(np.stack([cx+rr*np.cos(t),cy+rr*np.sin(t),np.full(64,z)],1))
    P=np.vstack(pts); u,v=uv(P)
    img=np.zeros((Hh+2*m,W+2*m),np.uint8)
    hull=cv2.convexHull(np.stack([u*W+m,v*Hh+m],1).astype(np.float32)).astype(np.int32)
    cv2.fillConvexPoly(img,hull,1)
    tot=img.sum(); vis=img[m:m+Hh,m:m+W].sum()
    return vis/max(tot,1), vis/(W*Hh), (u.min(),u.max(),v.min(),v.max())
# table Olia front-right corner (0.8, 2.045)
best=[]
for cx in np.arange(1.2,2.31,0.05):
    for cy in np.arange(2.2,3.61,0.05):
        if cx+0.25>2.5-0.05: continue
        share,fr,b=sil(cx,cy)
        gap_tab=np.hypot(max(0,cx-0.8),max(0,cy-2.045))-0.25
        onrug = cx<=1.85 and cy+0.25<=3.02
        if 0.30<=share<=0.60 and b[1]>1.0 and gap_tab>=0.25:
            best.append((abs(share-0.45)+(0 if onrug else 0.2), round(cx,2),round(cy,2),round(share,3),round(100*fr,2),[round(x,3) for x in b],onrug,round(gap_tab,2)))
best.sort()
for b in best[:10]: print(b)
