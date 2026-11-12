# Right-edge fringe at page size (asset scaled to Ht px tall, LANCZOS), v1 vs v2, on the site paper #F4F1EC and dark #3A3A3A. Ours only.
# Usage: page_view_v2.py <asset-dir> <out.png> Ht x0,y0,x1,y1 (box in final 1638x2048 space) [zoom for display, nearest]
import sys
from PIL import Image, ImageDraw
A=sys.argv[1].rstrip('/')+'/'; out=sys.argv[2]; Ht=int(sys.argv[3]); box=tuple(map(int,sys.argv[4].split(','))); z=int(sys.argv[5]) if len(sys.argv)>5 else 1
tiles=[]
for f,tag in [('p2-nano-fixed.png','v1 556112'),('p2-nano-fixed-v2.png','v2 ee131b')]:
    im=Image.open(A+f).convert('RGBA'); s=Ht/im.height
    for bg in [(0xF4,0xF1,0xEC),(0x3A,0x3A,0x3A)]:
        b=Image.new('RGBA',im.size,bg+(255,)); b.alpha_composite(im); b=b.convert('RGB')
        if Ht!=im.height: b=b.resize((round(im.width*s),Ht),Image.LANCZOS)
        c=b.crop(tuple(round(v*s) for v in box))
        if z>1: c=c.resize((c.width*z,c.height*z),Image.NEAREST)
        tiles.append((tag+(' paper' if bg[0]>200 else ' dark'),c))
w,h=tiles[0][1].size; S=Image.new('RGB',(w*4+18,h+14),(255,255,255)); d=ImageDraw.Draw(S)
for i,(n,t) in enumerate(tiles): S.paste(t,(i*(w+6),14)); d.text((i*(w+6)+2,1),n+f' @{Ht}' + (f' x{z}' if z>1 else ''),fill=(0,0,0))
S.save(out)
