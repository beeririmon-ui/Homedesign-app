import sys, json, itertools
from PIL import Image, ImageFilter, ImageOps, ImageChops
# C3 per the plan: edge map INSIDE the product (silhouette excluded), after aligning the product box; alignment search +-10% scale, +-6% shift, mirror. Pure PIL.
S=256; KEEP=0.15; DIL=5; ERODE=9
def load(spec):
    name,rest=spec.split('=',1); thr=None; box=None
    if '#' in rest: rest,thr=rest.split('#'); thr=int(thr)
    if '@' in rest: path,b=rest.split('@'); box=tuple(map(int,b.split(',')))
    else: path=rest
    im=Image.open(path)
    if im.mode=='RGBA':
        a=im.getchannel('A'); bb=a.point(lambda v:255 if v>=128 else 0).getbbox(); box=box or bb
        bg=Image.new('RGBA',im.size,(0xF4,0xF1,0xEC,255)); bg.alpha_composite(im); L=bg.convert('L')
        m=a.point(lambda v:255 if v>=128 else 0)
    else:
        L=im.convert('L'); box=box or (0,0)+im.size
        m=L.point(lambda v:255 if v<thr else 0) if thr else Image.new('L',im.size,255)
    L=L.crop(box).resize((S,S),Image.LANCZOS); m=m.crop(box).resize((S,S),Image.NEAREST).filter(ImageFilter.MinFilter(ERODE))
    return name,(L,m)
def edges(L,m):
    b=L.filter(ImageFilter.GaussianBlur(3))
    gx=b.filter(ImageFilter.Kernel((3,3),[-1,0,1,-2,0,2,-1,0,1],8,128)); gy=b.filter(ImageFilter.Kernel((3,3),[-1,-2,-1,0,0,0,1,2,1],8,128))
    c=Image.new('L',(S,S),128)
    mag=ImageChops.add(ImageChops.difference(gx,c),ImageChops.difference(gy,c),1)
    mag=ImageChops.multiply(mag,m)
    h=mag.histogram(); tot=m.histogram()[255]; acc=0; t=255
    for v in range(255,0,-1):
        acc+=h[v]
        if acc>=KEEP*tot: t=v; break
    return mag.point(lambda v:255 if v>t else 0).filter(ImageFilter.MaxFilter(DIL)).convert('1')
def iou(ea,ma,eb,mb):
    M=ImageChops.logical_and(ma,mb)
    A=ImageChops.logical_and(ea,M); B=ImageChops.logical_and(eb,M)
    i=ImageChops.logical_and(A,B).histogram()[-1]; u=ImageChops.logical_or(A,B).histogram()[-1]
    return i/u if u else 0
def tf(img,s,dx,dy,fill):
    a=1/s; c=S/2-a*S/2-dx*S; f=S/2-a*S/2-dy*S
    return img.transform((S,S),Image.AFFINE,(a,0,c,0,a,f),Image.BILINEAR,fillcolor=fill)
items=dict(load(s) for s in sys.argv[1:])
base={n:(edges(L,m),m.convert('1')) for n,(L,m) in items.items()}
var={}
for n,(L,m) in items.items():
    vs=[]
    for mir in (False,True):
        L2=ImageOps.mirror(L) if mir else L; m2=ImageOps.mirror(m) if mir else m
        for s in (0.9,0.95,1.0,1.05,1.1):
            for dx in (-0.06,0,0.06):
                for dy in (-0.06,0,0.06):
                    Lt=tf(L2,s,dx,dy,int(L2.getpixel((2,2)))); mt=tf(m2,s,dx,dy,0).point(lambda v:255 if v>=128 else 0)
                    vs.append(((('M' if mir else ''),s,dx,dy),edges(Lt,mt),mt.convert('1')))
    var[n]=vs
res={}
for a,b in itertools.combinations(items,2):
    ea,ma=base[a]; eb,mb=base[b]
    best=max(((iou(ea,ma,e,m),p) for p,e,m in var[b]),key=lambda x:x[0])
    res[a+'|'+b]={'aligned':round(iou(ea,ma,eb,mb),3),'search_max':round(best[0],3),'at':best[1]}
print(json.dumps(res))
