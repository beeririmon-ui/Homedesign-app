import sys
from PIL import Image
# cropzoom.py out.png target_h  file:x0,y0,x1,y1 ...  (each crop scaled to target_h, LANCZOS; RGBA composited on F4F1EC)
out=sys.argv[1]; H=int(sys.argv[2]); tiles=[]
for spec in sys.argv[3:]:
    f,b=spec.rsplit(':',1); x0,y0,x1,y1=map(int,b.split(','))
    im=Image.open(f)
    if im.mode=='RGBA':
        bg=Image.new('RGBA',im.size,(0xF4,0xF1,0xEC,255)); bg.alpha_composite(im); im=bg
    im=im.convert('RGB').crop((x0,y0,x1,y1)); s=H/im.height
    tiles.append(im.resize((round(im.width*s),H),Image.LANCZOS))
W=sum(t.width for t in tiles)+8*(len(tiles)+1)
sh=Image.new('RGB',(W,H+16),(128,128,128)); x=8
for t in tiles: sh.paste(t,(x,8)); x+=t.width+8
sh.save(out); print(out, sh.size)
