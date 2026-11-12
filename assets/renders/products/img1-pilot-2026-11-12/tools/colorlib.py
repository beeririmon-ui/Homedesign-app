import numpy as np, cv2
def srgb_to_lab(rgb):
    """rgb uint8 (...,3) -> float Lab (D65), exact CIE formulas."""
    c=rgb.astype(np.float64)/255.0
    c=np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
    M=np.array([[0.4124564,0.3575761,0.1804375],[0.2126729,0.7151522,0.0721750],[0.0193339,0.1191920,0.9503041]])
    xyz=c@M.T
    xyz=xyz/np.array([0.95047,1.0,1.08883])
    f=np.where(xyz>(6/29)**3,np.cbrt(xyz),xyz/(3*(6/29)**2)+4/29)
    L=116*f[...,1]-16; a=500*(f[...,0]-f[...,1]); b=200*(f[...,1]-f[...,2])
    return np.stack([L,a,b],-1)
def lab_to_srgb(lab):
    L,a,b=lab[...,0],lab[...,1],lab[...,2]
    fy=(L+16)/116; fx=fy+a/500; fz=fy-b/200
    def finv(t): return np.where(t>6/29,t**3,3*(6/29)**2*(t-4/29))
    xyz=np.stack([finv(fx)*0.95047,finv(fy),finv(fz)*1.08883],-1)
    Mi=np.linalg.inv(np.array([[0.4124564,0.3575761,0.1804375],[0.2126729,0.7151522,0.0721750],[0.0193339,0.1191920,0.9503041]]))
    c=xyz@Mi.T; c=np.clip(c,0,1)
    c=np.where(c<=0.0031308,12.92*c,1.055*c**(1/2.4)-0.055)
    return (c*255+0.5).clip(0,255).astype(np.uint8)
def lch(lab):
    L,a,b=lab; C=float(np.hypot(a,b)); h=float(np.degrees(np.arctan2(b,a))%360); return [round(float(L),2),round(C,2),round(h,1)]
def lit_side(rgba, lo=75, hi=98):
    """median Lab of product pixels (alpha>=0.9) whose L* is between the lo and hi percentile = 'the lit side'"""
    a=rgba[...,3]>=230; lab=srgb_to_lab(rgba[...,:3])[a]
    L=lab[:,0]; p1,p2=np.percentile(L,[lo,hi]); sel=lab[(L>=p1)&(L<=p2)]
    return np.median(sel,0), int(sel.shape[0])
def ciede2000(lab1, lab2):
    L1,a1,b1=lab1; L2,a2,b2=lab2
    C1=np.hypot(a1,b1); C2=np.hypot(a2,b2); Cb=(C1+C2)/2
    G=0.5*(1-np.sqrt(Cb**7/(Cb**7+25**7)))
    a1p=(1+G)*a1; a2p=(1+G)*a2; C1p=np.hypot(a1p,b1); C2p=np.hypot(a2p,b2)
    h1p=np.degrees(np.arctan2(b1,a1p))%360; h2p=np.degrees(np.arctan2(b2,a2p))%360
    dLp=L2-L1; dCp=C2p-C1p
    dhp=h2p-h1p
    if C1p*C2p==0: dhp=0
    elif dhp>180: dhp-=360
    elif dhp<-180: dhp+=360
    dHp=2*np.sqrt(C1p*C2p)*np.sin(np.radians(dhp/2))
    Lbp=(L1+L2)/2; Cbp=(C1p+C2p)/2
    if C1p*C2p==0: hbp=h1p+h2p
    elif abs(h1p-h2p)<=180: hbp=(h1p+h2p)/2
    elif h1p+h2p<360: hbp=(h1p+h2p+360)/2
    else: hbp=(h1p+h2p-360)/2
    T=1-0.17*np.cos(np.radians(hbp-30))+0.24*np.cos(np.radians(2*hbp))+0.32*np.cos(np.radians(3*hbp+6))-0.20*np.cos(np.radians(4*hbp-63))
    dth=30*np.exp(-((hbp-275)/25)**2); RC=2*np.sqrt(Cbp**7/(Cbp**7+25**7))
    SL=1+0.015*(Lbp-50)**2/np.sqrt(20+(Lbp-50)**2); SC=1+0.045*Cbp; SH=1+0.015*Cbp*T; RT=-np.sin(np.radians(2*dth))*RC
    return float(np.sqrt((dLp/SL)**2+(dCp/SC)**2+(dHp/SH)**2+RT*(dCp/SC)*(dHp/SH)))
