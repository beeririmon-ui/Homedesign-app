import sys, json, math
from PIL import Image, ImageFilter, ImageMath, ImageChops, ImageOps
# C2b tracing probe, pure PIL + python sums: NCC of high-pass luminance inside the product (bbox-aligned)
sup_img, sup_bbox, sup_cut, ours, ours_bbox = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
sb=list(map(int,sup_bbox.split(','))); ob=list(map(int,ours_bbox.split(',')))
S=Image.open(sup_img).convert('L').crop(sb); W,H=S.size
Sa=Image.open(sup_cut).getchannel('A').resize((W,H))
O=Image.open(ours).convert('RGBA'); Oa=O.getchannel('A').crop(ob).resize((W,H),Image.LANCZOS)
g=Image.new('RGBA',O.size,(128,128,128,255)); g.alpha_composite(O); Og=g.convert('L').crop(ob).resize((W,H),Image.LANCZOS)
def hp(im,r):
    return ImageMath.eval("a-b",a=im.convert('F'),b=im.filter(ImageFilter.GaussianBlur(r)).convert('F'))
def mask(a1,a2):
    m=ImageChops.darker(a1.point(lambda v:255 if v>=250 else 0),a2.point(lambda v:255 if v>=250 else 0)).filter(ImageFilter.MinFilter(9))
    return [1 if v else 0 for v in m.getdata()]
def ncc(A,B,M):
    a=list(A.getdata()); b=list(B.getdata())
    idx=[i for i,m in enumerate(M) if m]
    ma=sum(a[i] for i in idx)/len(idx); mb=sum(b[i] for i in idx)/len(idx)
    sab=saa=sbb=0.0
    for i in idx:
        x=a[i]-ma; y=b[i]-mb; sab+=x*y; saa+=x*x; sbb+=y*y
    return sab/math.sqrt(saa*sbb), len(idx)
out={'size':[W,H]}
for r in (2,4):
    hs=hp(S,r); M=mask(Sa,Oa)
    z,n=ncc(hs,hp(Og,r),M)
    res={'zero':round(z,3),'n':n,'mirror':round(ncc(hs,hp(ImageOps.mirror(Og),r),mask(Sa,ImageOps.mirror(Oa)))[0],3)}
    sh=[]
    for dx,dy in [(6,0),(-6,0),(0,10),(0,-10),(12,12),(-12,-12),(0,25),(0,-25)]:
        sh.append(round(ncc(hs,hp(ImageChops.offset(Og,dx,dy),r),mask(Sa,ImageChops.offset(Oa,dx,dy)))[0],3))
    res['shifted']=sh
    out['hp_r%d'%r]=res
print(json.dumps(out))
