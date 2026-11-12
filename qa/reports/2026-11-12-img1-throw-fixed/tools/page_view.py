# right-edge fringe at page size (asset scaled to H px tall), old vs new, paper and dark. Ours only.
import sys
from PIL import Image, ImageDraw
A=sys.argv[1].rstrip('/')+'/'; out=sys.argv[2]; Ht=int(sys.argv[3]); box=tuple(map(int,sys.argv[4].split(',')))  # box in 2048-space
tiles=[]
for f in ['p2-nano-test.png','p2-nano-fixed.png']:
    im=Image.open(A+f).convert('RGBA'); s=Ht/im.height
    for bg in [(0xF4,0xF1,0xEC),(0x3A,0x3A,0x3A)]:
        b=Image.new('RGBA',im.size,bg+(255,)); b.alpha_composite(im); b=b.convert('RGB').resize((round(im.width*s),Ht),Image.LANCZOS)
        tiles.append(((f.split('-')[-1][:-4])+(' paper' if bg[0]>200 else ' dark'),b.crop(tuple(round(v*s) for v in box))))
w,h=tiles[0][1].size; S=Image.new('RGB',(w*4+18,h+14),(255,255,255)); d=ImageDraw.Draw(S)
for i,(n,t) in enumerate(tiles): S.paste(t,(i*(w+6),14)); d.text((i*(w+6)+2,1),n,fill=(0,0,0))
S.save(out)
