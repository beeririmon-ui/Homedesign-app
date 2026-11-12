import sys, numpy as np
from PIL import Image, ImageDraw
# usage: edgezoom.py rgba.png out.png zoom  x0,y0,x1,y1 [x0,y0,x1,y1 ...]  -> grid: rows = boxes, cols = paper / dark / alpha
src,out,z=sys.argv[1],sys.argv[2],int(sys.argv[3]); boxes=[tuple(map(int,b.split(','))) for b in sys.argv[4:]]
im=Image.open(src).convert('RGBA')
tiles=[]
for b in boxes:
    c=im.crop(b); row=[]
    for bg in [(0xF4,0xF1,0xEC),(0x3A,0x3A,0x3A)]:
        t=Image.new('RGBA',c.size,bg+(255,)); t.alpha_composite(c); row.append(t.convert('RGB'))
    row.append(c.getchannel('A').convert('RGB'))
    row=[r.resize((r.width*z,r.height*z),Image.NEAREST) for r in row]
    tiles.append(row)
cw=max(sum(r.width for r in row)+4*8 for row in tiles); ch=sum(row[0].height+8 for row in tiles)+8
sheet=Image.new('RGB',(cw,ch),(128,128,128)); y=8
for row in tiles:
    x=8
    for r in row: sheet.paste(r,(x,y)); x+=r.width+8
    y+=row[0].height+8
sheet.save(out)
print(out, sheet.size)
