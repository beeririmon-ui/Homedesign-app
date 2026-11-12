import sys, json, numpy as np, cv2
from PIL import Image
# 1D profile method: average high-passed L along rows (for x period) / columns (y period), zero-padded FFT, parabolic peak
f=sys.argv[1]; boxes=[tuple(map(int,b.split(','))) for b in sys.argv[2:]]
im=np.array(Image.open(f).convert('L')).astype(float)
def period(sig,lo=8,hi=60):
    sig=sig-sig.mean(); sig=sig*np.hanning(len(sig)); N=8192
    P=np.abs(np.fft.rfft(sig,N))**2; fr=np.fft.rfftfreq(N)
    m=(fr>1/hi)&(fr<1/lo); i=np.argmax(np.where(m,P,0))
    a,b,c=P[i-1],P[i],P[i+1]; d=0.5*(a-c)/(a-2*b+c); fpk=fr[i]+d*(fr[1]-fr[0])
    prom=b/np.median(P[m]); return round(1/fpk,2), round(float(prom),1)
out=[]
for (x0,y0,w,h) in boxes:
    p=im[y0:y0+h,x0:x0+w]; hp=p-cv2.GaussianBlur(p,(0,0),12)
    # x period: FFT of each row, average power
    def avgper(arr):
        N=8192; Ps=None
        for row in arr:
            r=(row-row.mean())*np.hanning(len(row)); P=np.abs(np.fft.rfft(r,N))**2; Ps=P if Ps is None else Ps+P
        fr=np.fft.rfftfreq(N); m=(fr>1/60)&(fr<1/8); i=np.argmax(np.where(m,Ps,0))
        a,b,c=Ps[i-1],Ps[i],Ps[i+1]; d=0.5*(a-c)/(a-2*b+c); fpk=fr[i]+d*(fr[1]-fr[0])
        return round(1/fpk,2), round(float(b/np.median(Ps[m])),1)
    tx=avgper(hp); ty=avgper(hp.T)
    out.append({'box':[x0,y0,w,h],'Tx':tx,'Ty':ty,'Ty_over_Tx':round(ty[0]/tx[0],3)})
print(json.dumps(out,indent=0))
