import numpy as np
M=np.array([[0.4124564,0.3575761,0.1804375],[0.2126729,0.7151522,0.0721750],[0.0193339,0.1191920,0.9503041]])
def srgb_to_lab(rgb):
    c=rgb.astype(np.float64)/255.0
    c=np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
    xyz=c@M.T/np.array([0.95047,1.0,1.08883])
    f=np.where(xyz>(6/29)**3,np.cbrt(xyz),xyz/(3*(6/29)**2)+4/29)
    return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],-1)
def lch(lab):
    L,a,b=lab; return [round(float(L),2),round(float(np.hypot(a,b)),2),round(float(np.degrees(np.arctan2(b,a))%360),1)]
def de00(lab1,lab2):
    L1,a1,b1=[lab1[...,i] for i in range(3)]; L2,a2,b2=[lab2[...,i] for i in range(3)]
    C1=np.hypot(a1,b1); C2=np.hypot(a2,b2); Cb=(C1+C2)/2
    G=0.5*(1-np.sqrt(Cb**7/(Cb**7+25.0**7)))
    a1p=(1+G)*a1; a2p=(1+G)*a2; C1p=np.hypot(a1p,b1); C2p=np.hypot(a2p,b2)
    h1p=np.degrees(np.arctan2(b1,a1p))%360; h2p=np.degrees(np.arctan2(b2,a2p))%360
    dLp=L2-L1; dCp=C2p-C1p; dhp=h2p-h1p
    dhp=np.where(dhp>180,dhp-360,np.where(dhp<-180,dhp+360,dhp)); dhp=np.where(C1p*C2p==0,0,dhp)
    dHp=2*np.sqrt(C1p*C2p)*np.sin(np.radians(dhp/2))
    Lbp=(L1+L2)/2; Cbp=(C1p+C2p)/2
    hs=h1p+h2p; hd=np.abs(h1p-h2p)
    hbp=np.where(C1p*C2p==0,hs,np.where(hd<=180,hs/2,np.where(hs<360,(hs+360)/2,(hs-360)/2)))
    T=1-0.17*np.cos(np.radians(hbp-30))+0.24*np.cos(np.radians(2*hbp))+0.32*np.cos(np.radians(3*hbp+6))-0.20*np.cos(np.radians(4*hbp-63))
    dth=30*np.exp(-((hbp-275)/25)**2); RC=2*np.sqrt(Cbp**7/(Cbp**7+25.0**7))
    SL=1+0.015*(Lbp-50)**2/np.sqrt(20+(Lbp-50)**2); SC=1+0.045*Cbp; SH=1+0.015*Cbp*T; RT=-np.sin(np.radians(2*dth))*RC
    return np.sqrt((dLp/SL)**2+(dCp/SC)**2+(dHp/SH)**2+RT*(dCp/SC)*(dHp/SH))
