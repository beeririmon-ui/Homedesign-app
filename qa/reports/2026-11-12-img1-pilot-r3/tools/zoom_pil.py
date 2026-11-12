import sys
from PIL import Image
# zoom_pil.py out.png scale file:x0,y0,x1,y1 ... (nearest-free LANCZOS upscale, tiles side by side)
out=sys.argv[1]; s=float(sys.argv[2]); tiles=[]
for spec in sys.argv[3:]:
    f,b=spec.rsplit(':',1); x0,y0,x1,y1=map(int,b.split(','))
    im=Image.open(f)
    if im.mode=='RGBA':
        bg=Image.new('RGBA',im.size,(0x3A,0x3A,0x3A,255)); bg.alpha_composite(im); im=bg
    im=im.convert('RGB').crop((x0,y0,x1,y1))
    tiles.append(im.resize((round(im.width*s),round(im.height*s)),Image.LANCZOS))
W=sum(t.width for t in tiles)+8*(len(tiles)+1); H=max(t.height for t in tiles)+16
sh=Image.new('RGB',(W,H),(128,128,128)); x=8
for t in tiles: sh.paste(t,(x,8)); x+=t.width+8
sh.save(out); print(out,sh.size)
