"""Cut a product out of a supplier image: crop box, GrabCut seeded by a rect (+ optional lab rule), output RGBA + preview on #808080."""
import sys, json, numpy as np, cv2
from PIL import Image
spec=json.loads(sys.argv[1])
src=spec['src']; out=spec['out']
im=np.array(Image.open(src).convert('RGB'))
x0,y0,x1,y1=spec['crop']; im=im[y0:y1,x0:x1].copy()
h,w=im.shape[:2]
mask=np.full((h,w),cv2.GC_BGD,np.uint8)
rx0,ry0,rx1,ry1=spec.get('rect',[0,0,w,h])
mask[ry0:ry1,rx0:rx1]=cv2.GC_PR_FGD
lab=cv2.cvtColor(im,cv2.COLOR_RGB2LAB).astype(np.float32)
L=lab[...,0]*100/255; A=lab[...,1]-128; B=lab[...,2]-128
for rule in spec.get('fg_rules',[]):
    m=eval(rule); mask[m & (mask!=cv2.GC_BGD)]=cv2.GC_FGD
for rule in spec.get('bg_rules',[]):
    m=eval(rule); mask[m]=cv2.GC_BGD
for bx in spec.get('bg_boxes',[]):
    a,b,c,d=bx; mask[b:d,a:c]=cv2.GC_BGD
for bx in spec.get('fg_boxes',[]):
    a,b,c,d=bx; mask[b:d,a:c]=cv2.GC_FGD
if spec.get('mode')=='threshold':
    fg=eval(spec['fg_expr']).astype(np.uint8)
    for bx in spec.get('bg_boxes',[]):
        a_,b_,c_,d_=bx; fg[b_:d_,a_:c_]=0
    k=np.ones((3,3),np.uint8); fg=cv2.morphologyEx(fg,cv2.MORPH_OPEN,k); fg=cv2.morphologyEx(fg,cv2.MORPH_CLOSE,k)
else:
    bgd=np.zeros((1,65),np.float64); fgd=np.zeros((1,65),np.float64)
    cv2.grabCut(cv2.cvtColor(im,cv2.COLOR_RGB2BGR),mask,None,bgd,fgd,spec.get('iters',6),cv2.GC_INIT_WITH_MASK)
    fg=((mask==cv2.GC_FGD)|(mask==cv2.GC_PR_FGD)).astype(np.uint8)
# keep largest components
n,lbl,stats,_=cv2.connectedComponentsWithStats(fg,8)
keep=spec.get('keep',1)
order=np.argsort(-stats[1:,cv2.CC_STAT_AREA])[:keep]+1
fg=np.isin(lbl,order).astype(np.uint8)
# fill holes
inv=1-fg; n2,l2,s2,_=cv2.connectedComponentsWithStats(inv,4)
for i in range(1,n2):
    x,y,ww,hh,a=s2[i]
    if x>0 and y>0 and x+ww<w and y+hh<h and a<spec.get('hole_max',5000): fg[l2==i]=1
a=cv2.GaussianBlur(fg.astype(np.float32),(0,0),spec.get('feather',0.8))
rgba=np.dstack([im,(a*255).clip(0,255).astype(np.uint8)])
ys,xs=np.where(fg>0); bb=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
rgba=rgba[bb[1]:bb[3],bb[0]:bb[2]]
Image.fromarray(rgba,'RGBA').save(out)
g=Image.new('RGB',(rgba.shape[1],rgba.shape[0]),(128,128,128)); g.paste(Image.fromarray(rgba,'RGBA'),(0,0),Image.fromarray(rgba,'RGBA'))
g.save(out.replace('.png','-prev.jpg'),quality=90)
print(json.dumps({'out':out,'bbox_in_crop':bb,'size':[rgba.shape[1],rgba.shape[0]],'fg_px':int(fg.sum())}))
