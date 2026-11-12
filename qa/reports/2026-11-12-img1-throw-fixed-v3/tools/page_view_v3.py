# Page-size and 100% views of the throw P2 (ours only), any versions, on the site paper #F4F1EC and dark #3A3A3A.
# Usage: page_view_v3.py <asset-dir> <out.png> Ht x0,y0,x1,y1 (box in final 1638x2048 space; 'full' = whole) zoom tag=file.png [tag=file.png ...]
import sys
from PIL import Image, ImageDraw
A=sys.argv[1].rstrip('/')+'/'; out=sys.argv[2]; Ht=int(sys.argv[3]); bx=sys.argv[4]; z=int(sys.argv[5]); srcs=[a.split('=',1) for a in sys.argv[6:]]
tiles=[]
for tag,f in srcs:
    im=Image.open(A+f).convert('RGBA'); s=Ht/im.height
    box=(0,0,im.width,im.height) if bx=='full' else tuple(map(int,bx.split(',')))
    for bg in [(0xF4,0xF1,0xEC),(0x3A,0x3A,0x3A)]:
        b=Image.new('RGBA',im.size,bg+(255,)); b.alpha_composite(im); b=b.convert('RGB')
        if Ht!=im.height: b=b.resize((round(im.width*s),Ht),Image.LANCZOS)
        c=b.crop(tuple(round(v*s) for v in box))
        if z>1: c=c.resize((c.width*z,c.height*z),Image.NEAREST)
        tiles.append((f"{tag} {'paper' if bg[0]>200 else 'dark'} @{Ht}"+(f' x{z}' if z>1 else ''),c))
w,h=tiles[0][1].size; n=len(tiles); S=Image.new('RGB',(w*n+6*(n-1),h+14),(255,255,255)); d=ImageDraw.Draw(S)
for i,(nm,t) in enumerate(tiles): S.paste(t,(i*(w+6),14)); d.text((i*(w+6)+2,1),nm,fill=(0,0,0))
S.save(out,quality=92) if out.endswith('.jpg') else S.save(out)
