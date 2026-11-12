import sys, numpy as np
from PIL import Image, ImageDraw
D=sys.argv[1].rstrip('/')+'/'; out=sys.argv[2]; y0=int(sys.argv[3]); x0=int(sys.argv[4]); h=int(sys.argv[5]); w=int(sys.argv[6]); z=int(sys.argv[7])
raw=Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB')
nb=Image.open(D+'raw/p2-throw-nano-test-nobg.png').convert('RGBA')
fx=Image.open(D+'sofa-cover-cj-cotton-muslin-fringe/p2-nano-fixed-fullres.png').convert('RGBA')
box=(x0,y0,x0+w,y0+h)
def comp(im,bg):
    b=Image.new('RGBA',im.size,bg+(255,)); b.alpha_composite(im); return b.convert('RGB')
tiles=[('raw',raw.crop(box)),
       ('nobg a',nb.crop(box).getchannel('A').convert('RGB')),
       ('fixed a',fx.crop(box).getchannel('A').convert('RGB')),
       ('nobg dark',comp(nb.crop(box),(0x3A,0x3A,0x3A))),
       ('fixed dark',comp(fx.crop(box),(0x3A,0x3A,0x3A))),
       ('fixed paper',comp(fx.crop(box),(0xF4,0xF1,0xEC)))]
W=w*z; H=h*z; c=Image.new('RGB',(W*3+12,(H+18)*2+6),(255,255,255)); dr=ImageDraw.Draw(c)
for i,(n,t) in enumerate(tiles):
    cx=(i%3)*(W+6); cy=(i//3)*(H+24)
    c.paste(t.resize((W,H),Image.NEAREST),(cx,cy+18)); dr.text((cx+3,cy+3),n+f' y{y0} x{x0}',fill=(0,0,0))
c.save(out)
