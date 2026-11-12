import sys, numpy as np
from PIL import Image
f=sys.argv[1]; out=sys.argv[2]
im=Image.open(f).convert('RGBA')
def comp(bg):
    b=Image.new('RGBA',im.size,bg+(255,)); b.alpha_composite(im); return b.convert('RGB')
p=comp((0xF4,0xF1,0xEC)); d=comp((0x3A,0x3A,0x3A))
W,H=im.size; s=900/H
p=p.resize((round(W*s),900),Image.LANCZOS); d=d.resize((round(W*s),900),Image.LANCZOS)
c=Image.new('RGB',(p.width*2+10,900),(255,255,255)); c.paste(p,(0,0)); c.paste(d,(p.width+10,0)); c.save(out)
