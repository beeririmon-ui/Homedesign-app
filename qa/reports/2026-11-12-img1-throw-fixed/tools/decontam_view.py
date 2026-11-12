# x6 view of replaced pixels on dark: as shipped vs raw colour kept (same alpha); toward-paper pixels marked. Ours only.
import sys, numpy as np, cv2
sys.path.insert(0,sys.argv[1]); from lab import srgb_to_lab, de00
from PIL import Image, ImageDraw
D=sys.argv[2].rstrip('/')+'/'; chg=np.load(sys.argv[3]); out=sys.argv[4]
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB')).astype(float)
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
fr=np.array(Image.open(D+'sofa-cover-cj-cotton-muslin-fringe/p2-nano-fixed-fullres.png')).astype(float)
K=0.934
def s2l(c): c=c/255.0; return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
def l2s(c): c=np.clip(c,0,1); return np.where(c<=0.0031308,12.92*c,1.055*c**(1/2.4)-0.055)*255
exp=np.round(l2s(s2l(raw)*K))
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
wg=cv2.GaussianBlur(sure,(0,0),10); B=np.stack([cv2.GaussianBlur((exp[...,c]*sure).astype(np.float32),(0,0),10)/np.maximum(wg,1e-6) for c in range(3)],-1)
dPa=de00(srgb_to_lab(fr[...,:3]),srgb_to_lab(np.clip(B,0,255))); dPb=de00(srgb_to_lab(exp),srgb_to_lab(np.clip(B,0,255)))
tp=chg&(dPa<dPb-0.5)
ys,xs=np.nonzero(tp); y=int(np.median(ys[(ys>1400)&(ys<1800)])); x=int(np.median(xs[(ys>1400)&(ys<1800)]))
x0,y0=x-30,y-30; box=(slice(y0,y0+60),slice(x0,x0+60)); a=fr[...,3][box][...,None]/255.; bg=np.array([0x3A,0x3A,0x3A],float)
ship=fr[...,:3][box]*a+bg*(1-a); kept=exp[box]*a+bg*(1-a); mark=ship.copy(); mark[tp[box]]=(255,0,0)
row=np.concatenate([ship,np.full((60,2,3),255),kept,np.full((60,2,3),255),mark],1).clip(0,255).astype(np.uint8)
Image.fromarray(row).resize((row.shape[1]*6,360),Image.NEAREST).save(out); print('box',x0,y0,'toward-paper px in box',int(tp[box].sum()))
