import numpy as np, json
from PIL import Image, ImageFilter
R='/home/user/homedesign-app/'
P=R+'assets/renders/living-room/nordic/m0/pilot-v4.1/'
W,H=2752,1548
clay=np.asarray(Image.open(R+'assets/blockout/living-room/m0-clay-4k.png').convert('L').resize((W,H),Image.LANCZOS),float)
def hsl(rgb):
    r,g,b=[x/255 for x in rgb]; mx,mn=max(r,g,b),min(r,g,b); l=(mx+mn)/2
    if mx==mn: return (0.0,0.0,round(l*100,1))
    d=mx-mn; s=d/(2-mx-mn) if l>0.5 else d/(mx+mn)
    if mx==r: h=((g-b)/d)%6
    elif mx==g: h=(b-r)/d+2
    else: h=(r-g)/d+4
    return (round(h*60,1),round(s*100,1),round(l*100,1))
def Lmap(a):
    return (a.max(2)+a.min(2))/2/255*100
def patch(a,u,v,w=0.01):
    hw=max(2,int(w*W/2)); x=int(u*W); y=int(v*H)
    return hsl(a[y-hw:y+hw+1,x-hw:x+hw+1].reshape(-1,3).mean(0))
def grad(g):
    gx=np.zeros_like(g); gy=np.zeros_like(g)
    gx[:,1:-1]=g[:,2:]-g[:,:-2]; gy[1:-1]=g[2:]-g[:-2]
    return np.hypot(gx,gy)
gc=grad(clay)
def shift(gi,box,s=14):
    u0,u1,v0,v1=box; x0,x1,y0,y1=int(u0*W),int(u1*W),int(v0*H),int(v1*H)
    A=gc[y0:y1,x0:x1]; A=(A-A.mean())/(A.std()+1e-9)
    best=(-9,0,0)
    for dy in range(-s,s+1):
        for dx in range(-s,s+1):
            ys,xs=y0+dy,x0+dx
            if ys<0 or xs<0 or ys+(y1-y0)>H or xs+(x1-x0)>W: continue
            B=gi[ys:ys+(y1-y0),xs:xs+(x1-x0)]; B=(B-B.mean())/(B.std()+1e-9)
            c=(A*B).mean()
            if c>best[0]: best=(c,dx,dy)
    return {'corr':round(best[0],3),'du':round(best[1]/W,4),'dv':round(best[2]/H,4)}
regions={'frame':(0.05,0.95,0.05,0.95),'corner+cornice':(0.40,0.50,0.0,0.62),'window':(0.17,0.40,0.0,0.62),
 'sofa':(0.5208,0.8396,0.5509,0.7949),'table':(0.512,0.762,0.6787,0.8699),'armchair':(0.1896,0.3867,0.6218,0.9056),
 'ceiling-band':(0.55,0.95,0.0,0.15),'floor/skirting-right':(0.84,0.99,0.60,0.95)}
pts={
 'wall: window wall front of window (0.10,0.30)':(0.10,0.30),
 'wall: window wall beside window (0.405,0.30)':(0.405,0.30),
 'wall: back wall near corner (0.467,0.385)':(0.467,0.385),
 'wall: back wall behind sofa (0.69,0.22)':(0.69,0.22),
 'wall: back wall behind sofa (0.69,0.42)':(0.69,0.42),
 'wall: back wall right edge (0.97,0.31)':(0.97,0.31),
 'ceiling (0.55,0.04)':(0.55,0.04),
 'sofa back cushion (0.70,0.60)':(0.70,0.60),
 'sofa seat face (0.663,0.673)':(0.6634,0.6733),
 'armchair seat boucle (0.31,0.75)':(0.31,0.75),
 'armchair back boucle (0.25,0.68)':(0.25,0.68),
 'table top oak (0.62,0.715)':(0.62,0.715),
 'floor (0.45,0.95)':(0.45,0.95),'floor (0.70,0.95)':(0.70,0.95),'floor (0.92,0.85)':(0.92,0.85),'floor (0.10,0.95)':(0.10,0.95),'floor (0.45,0.80)':(0.45,0.80),
}
out={}
for n in ['a','b','text']:
    im=np.asarray(Image.open(P+f'm0-pilot-{n}.png').convert('RGB'),float)
    g=np.asarray(Image.open(P+f'm0-pilot-{n}.png').convert('L'),float)
    gi=grad(g); L=Lmap(im)
    r={'shifts':{k:shift(gi,b) for k,b in regions.items()},'patches':{k:patch(im,*p) for k,p in pts.items()}}
    # armchair frame leg (small patch)
    r['patches']['armchair front leg oak (0.382,0.74) 0.4%']=patch(im,0.382,0.74,0.004)
    r['patches']['armchair rear rail oak (0.27,0.815) 0.4%']=patch(im,0.27,0.815,0.004)
    # contact shadow under sofa
    Lm=np.asarray(Image.fromarray(L.astype(np.float32)).filter(ImageFilter.MedianFilter(3)))
    x0,x1,y0,y1=int(0.52*W),int(0.84*W),int(0.76*H),int(0.83*H)
    reg=Lm[y0:y1,x0:x1]
    # 0.5%-patch mean min
    k=int(0.005*W)
    from numpy.lib.stride_tricks import sliding_window_view
    pm=sliding_window_view(reg,(k,k))[::3,::3].mean((2,3))
    iy,ix=np.unravel_index(reg.argmin(),reg.shape)
    r['contact_shadow_under_sofa']={'region_uv':[0.52,0.84,0.76,0.83],'min_px_L_median3':round(float(reg.min()),1),
       'at_uv':[round((x0+ix)/W,3),round((y0+iy)/H,3)],'p1_L':round(float(np.percentile(reg,1)),1),'min_patch0.5pct_L':round(float(pm.min()),1)}
    # whole-frame darkest
    r['frame_min_patch0.5pct_L']=round(float(sliding_window_view(Lm,(k,k))[::4,::4].mean((2,3)).min()),1)
    # window
    wx0,wx1,wy0,wy1=int(0.19*W),int(0.375*W),int(0.025*H),int(0.553*H)
    wL=L[wy0:wy1,wx0:wx1]
    sat=(im.max(2)>=254.5)
    inwin=np.zeros_like(sat); inwin[wy0:wy1,wx0:wx1]=True
    r['window']={'L_p50':round(float(np.median(wL)),1),'L_p99':round(float(np.percentile(wL,99)),1),'L_max':round(float(wL.max()),1),
      'px_255_in_window':int((sat&inwin).sum()),'px_255_outside_window':int((sat&~inwin).sum())}
    # wall column medians
    cols={}
    for u in [0.05,0.15,0.40,0.45,0.55,0.69,0.80,0.90,0.97]:
        x=int(u*W); cols[u]=round(float(np.median(L[int(0.15*H):int(0.45*H),x-6:x+7])),1)
    r['wall_column_median_L_v0.15-0.45']=cols
    # armchair top vs sill: per-column strongest edges
    prof=[]
    for u in np.arange(0.215,0.300,0.01):
        x=int(u*W); c=np.median(L[:,x-3:x+4],1)
        d=np.convolve(c,[1,1,1,0,-1,-1,-1],'same')  # positive where L drops going down? compute explicitly
        dd=c[4:]-c[:-4]  # L(y+4)-L(y)
        # sill underside: brightest->darker edge in 0.57-0.605
        ys0,ys1=int(0.55*H),int(0.605*H); sy=ys0+int(np.argmin(dd[ys0:ys1]))+2
        yc0,yc1=int(0.595*H),int(0.70*H); cy=yc0+int(np.argmax(np.abs(dd[yc0:yc1])))+2
        prof.append({'u':round(float(u),3),'sill_edge_v':round(sy/H,4),'chair_top_v':round(cy/H,4),'gap_v':round((cy-sy)/H,4)})
    r['armchair_vs_sill_columns']=prof
    out[n]=r
json.dump(out,open(P+'measurements.json','w'),indent=1)
for n,r in out.items():
    print('=====',n)
    for k,v in r['shifts'].items(): print(' shift',k,v)
    for k,v in r['patches'].items(): print(' ',k,v)
    print(' contact',r['contact_shadow_under_sofa'],'frame min',r['frame_min_patch0.5pct_L'])
    print(' window',r['window'])
    print(' cols',r['wall_column_median_L_v0.15-0.45'])
    for p in r['armchair_vs_sill_columns']: print('  ',p)
