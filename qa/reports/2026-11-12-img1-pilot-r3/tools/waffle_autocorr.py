import sys, numpy as np, cv2, json
from PIL import Image
# waffle_autocorr.py raw.png x0 y0 size: normalised autocorrelation of high-passed L at lag bands (tile-repeat check)
im=np.array(Image.open(sys.argv[1]).convert('L')).astype(float); x0,y0,s=map(int,sys.argv[2:5])
p=im[y0:y0+s,x0:x0+s]; hp=p-cv2.GaussianBlur(p,(0,0),6); hp-=hp.mean()
F=np.fft.fft2(hp,s=(2*s,2*s)); ac=np.fft.fftshift(np.real(np.fft.ifft2(np.abs(F)**2))); ac/=ac[s,s]
yy,xx=np.mgrid[-s:s,-s:s]; r=np.hypot(xx,yy)
def mx(lo,hi): k=(r>=lo)&(r<hi); i=np.argmax(np.where(k,ac,-9)); return round(float(ac.flat[i]),3)
print(json.dumps({'one_period_20_30':mx(20,30),'lag_60_150':mx(60,150),'lag_150_400':mx(150,400),'lag_400_600':mx(400,600)}))
