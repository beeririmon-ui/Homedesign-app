# final asset (ours): right-edge fringe at 100% and at the 1280-high page size, on paper and dark, old vs new
import sys
from PIL import Image, ImageDraw
A=sys.argv[1].rstrip('/')+'/'; out=sys.argv[2]; box=tuple(map(int,sys.argv[3].split(','))); z=float(sys.argv[4])
def comp(im,bg):
    b=Image.new('RGBA',im.size,bg+(255,)); b.alpha_composite(im); return b.convert('RGB')
tiles=[]
for f in ['p2-nano-test.png','p2-nano-fixed.png']:
    im=Image.open(A+f).convert('RGBA')
    for bg in [(0xF4,0xF1,0xEC),(0x3A,0x3A,0x3A)]:
        c=comp(im,bg).crop(box); tiles.append((f.split('-')[-1][:-4]+(' paper' if bg[0]>200 else ' dark'),c.resize((round(c.width*z),round(c.height*z)),Image.LANCZOS if z<1 else Image.NEAREST)))
w,h=tiles[0][1].size; s=Image.new('RGB',(w*4+18,h+16),(255,255,255)); d=ImageDraw.Draw(s)
for i,(n,t) in enumerate(tiles): s.paste(t,(i*(w+6),16)); d.text((i*(w+6)+2,2),n,fill=(0,0,0))
s.save(out)
