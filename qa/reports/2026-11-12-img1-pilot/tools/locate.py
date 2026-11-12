import sys, json
from PIL import Image
# locate a cut (RGBA, pixels copied verbatim) inside its source image by exact row-byte matching
src, cut = sys.argv[1], sys.argv[2]
S=Image.open(src).convert('RGB'); C=Image.open(cut).convert('RGBA')
w,h=C.size; W,H=S.size
a=C.getchannel('A'); rgb=C.convert('RGB')
res=None
for ry in [h//2, h//3, 2*h//3]:
    # longest run of alpha==255 in row ry
    row=[a.getpixel((x,ry)) for x in range(w)]
    best=(0,0); s=None
    for x,v in enumerate(row+[0]):
        if v==255 and s is None: s=x
        if v!=255 and s is not None:
            if x-s>best[1]-best[0]: best=(s,x)
            s=None
    x0,x1=best
    if x1-x0<20: continue
    seg=rgb.crop((x0,ry,x1,ry+1)).tobytes()
    for y in range(H):
        line=S.crop((0,y,W,y+1)).tobytes()
        i=line.find(seg)
        while i!=-1 and i%3!=0: i=line.find(seg,i+1)
        if i!=-1:
            ox=i//3-x0; oy=y-ry
            res={'offset':[ox,oy],'bbox':[ox,oy,ox+w,oy+h],'src_size':[W,H]}
            break
    if res: break
print(json.dumps(res))
