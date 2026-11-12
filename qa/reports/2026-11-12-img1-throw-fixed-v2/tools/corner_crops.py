# Corner crops (ours only): raw, then for each alpha source (remove-bg, v1 fullres, v2 fullres) the alpha and composites on
# the site paper #F4F1EC and dark #3A3A3A, nearest-neighbour zoom. Rows = sources; columns = alpha | paper | dark | raw-with-0.5-contour.
# Usage: corner_crops.py <img1-dir> <out.png> x0 y0 w h zoom
import sys, numpy as np, cv2
from PIL import Image, ImageDraw
D=sys.argv[1].rstrip('/')+'/'; out=sys.argv[2]; x0,y0,w,h,z=map(int,sys.argv[3:8])
A=D+'sofa-cover-cj-cotton-muslin-fringe/'
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB'))
srcs=[('remove-bg',np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png').convert('RGBA'))),
      ('v1 556112',np.array(Image.open(A+'p2-nano-fixed-fullres.png').convert('RGBA'))),
      ('v2 ee131b',np.array(Image.open(A+'p2-nano-fixed-v2-fullres.png').convert('RGBA')))]
sl=(slice(y0,y0+h),slice(x0,x0+w))
def comp(rgba,bg):
    a=rgba[...,3:4]/255.; return (rgba[...,:3]*a+np.array(bg)*(1-a)).clip(0,255).astype(np.uint8)
rows=[]
for n,im in srcs:
    c=im[sl]; a=c[...,3]
    cont=raw[sl].copy(); m=(a>=128).astype(np.uint8); e=m-cv2.erode(m,np.ones((3,3),np.uint8)); cont[e>0]=(255,0,0)
    tiles=[np.dstack([a]*3),comp(c,(0xF4,0xF1,0xEC)),comp(c,(0x3A,0x3A,0x3A)),cont]
    rows.append((n,tiles))
W=w*z; H=h*z; S=Image.new('RGB',(4*W+18,len(rows)*(H+16)),(255,255,255)); d=ImageDraw.Draw(S)
for r,(n,tiles) in enumerate(rows):
    for i,t in enumerate(tiles):
        S.paste(Image.fromarray(t).resize((W,H),Image.NEAREST),(i*(W+6),r*(H+16)+14))
    d.text((2,r*(H+16)+1),f'{n}: alpha | on paper | on dark | raw + 0.5 contour   raw x{x0} y{y0} {w}x{h} x{z}',fill=(0,0,0))
S.save(out)
