import sys
from PIL import Image, ImageDraw
# usage: contact.py out.jpg cell_h img1 img2 ...
out=sys.argv[1]; H=int(sys.argv[2]); files=sys.argv[3:]
ims=[]
for f in files:
    im=Image.open(f).convert('RGB'); print(f, im.size)
    s=H/im.height; ims.append(im.resize((max(1,round(im.width*s)),H), Image.LANCZOS))
W=sum(i.width for i in ims)+8*(len(ims)+1)
sheet=Image.new('RGB',(W,H+16),(200,200,200)); x=8
for i in ims: sheet.paste(i,(x,8)); x+=i.width+8
sheet.save(out,quality=88)
