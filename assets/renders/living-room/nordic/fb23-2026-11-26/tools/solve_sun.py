import numpy as np
# sun at 14:00 solar time, mid-February (decl -12.6), latitude chosen so altitude ~30 (proposal 3)
def sun(lat,decl=-12.6,h=30.0):
    la,de,ha=map(np.radians,(lat,decl,h))
    alt=np.arcsin(np.sin(la)*np.sin(de)+np.cos(la)*np.cos(de)*np.cos(ha))
    az=np.arccos((np.sin(de)-np.sin(la)*np.sin(alt))/(np.cos(la)*np.cos(alt)))
    return np.degrees(alt), 360-np.degrees(az)
for lat in (32,40,41,42,55): print('lat',lat,'alt,az',[round(x,1) for x in sun(lat)])
alt,az=sun(41.0)
print('USE alt',round(alt,2),'az',round(az,2))
def sdir(R,alt,az):
    # plan coords: the north-facade outward normal (-X) faces azimuth R; compass clockwise seen from above; plan world is mirrored (X)
    th=np.radians(-(az-R))            # physical (Blender, X'=-X) math angle from +X'
    a=np.radians(alt); d=np.array([np.cos(th)*np.cos(a), np.sin(th)*np.cos(a), np.sin(a)])
    return np.array([-d[0],d[1],d[2]])   # back to plan coords (towards the sun)
def through(P,s):
    ok=np.ones(len(P),bool)
    for xp in (-2.30,-2.60):
        t=(xp-P[:,0])/s[0]; Q=P+t[:,None]*s
        ok&=(t>0)&(Q[:,1]>0.9)&(Q[:,1]<2.7)&(Q[:,2]>0.75)&(Q[:,2]<2.7)
    return ok
g=np.random.default_rng(1)
seat=np.stack([g.uniform(-0.76,1.16,4000),g.uniform(0.30,0.93,4000),np.full(4000,0.44)],1)
rug=np.stack([g.uniform(-1.45,1.85,6000),g.uniform(0.72,3.02,6000),np.full(6000,0.012)],1)
backw=np.stack([g.uniform(-2.3,2.5,6000),np.full(6000,0.001),g.uniform(0.78,2.9,6000)],1)
for R in range(200,265,5):
    s=sdir(R,alt,az)
    print(R,'sun(plan)',np.round(s,3),'seat lit %.0f%%'%(100*through(seat,s).mean()),'rug lit %.0f%%'%(100*through(rug,s).mean()),'back wall above sofa lit %.0f%%'%(100*through(backw,s).mean()))
