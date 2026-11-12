import sys, json
from PIL import Image, ImageStat
# product bbox on a near-white background + left/right/top/bottom brightness of the product (pure PIL)
f=sys.argv[1]; thr=int(sys.argv[2])
im=Image.open(f).convert('RGB'); L=im.convert('L'); W,H=im.size
m=L.point(lambda v:255 if v<thr else 0)
bb=m.getbbox(); x0,y0,x1,y1=bb
out={'size':[W,H],'bbox':bb,'w_frac':round((x1-x0)/W,3),'h_frac':round((y1-y0)/H,3),'centre':[round((x0+x1)/2/W,3),round((y0+y1)/2/H,3)],'area_frac':round(sum(1 for v in m.getdata() if v)/(W*H),3)}
xm=(x0+x1)//2; ym=(y0+y1)//2
for name,box in [('left',(x0,y0,xm,y1)),('right',(xm,y0,x1,y1)),('upper',(x0,y0,x1,ym)),('lower',(x0,ym,x1,y1))]:
    st=ImageStat.Stat(L.crop(box),m.crop(box)); out['mean_L8_'+name]=round(st.mean[0],1)
print(json.dumps(out))
