import sys
from PIL import Image
# grid_pil.py out.jpg cell w1 f1 f2 ... : contact sheet, each image fitted into cell x cell (pure PIL)
out=sys.argv[1]; C=int(sys.argv[2]); fs=sys.argv[3:]
n=len(fs); cols=min(n,3); rows=(n+cols-1)//cols
sh=Image.new('RGB',(cols*(C+8)+8,rows*(C+8)+8),(200,200,200))
for i,f in enumerate(fs):
    im=Image.open(f)
    if im.mode=='RGBA':
        bg=Image.new('RGBA',im.size,(0xF4,0xF1,0xEC,255)); bg.alpha_composite(im); im=bg
    im=im.convert('RGB'); im.thumbnail((C,C),Image.LANCZOS)
    sh.paste(im,(8+(i%cols)*(C+8),8+(i//cols)*(C+8)))
sh.save(out,quality=90); print(out,sh.size)
