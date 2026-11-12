import sys, json
from PIL import Image, ImageFilter, ImageChops
# pore count on a cylinder face crop (pure PIL): pores = connected dark blobs in high-pass L, sized 0.0004-0.02 D^2; normalised per D^2.
# args: file x0,y0,x1,y1 D_px [thr]
f=sys.argv[1]; box=tuple(map(int,sys.argv[2].split(','))); Dp=float(sys.argv[3]); thr=int(sys.argv[4]) if len(sys.argv)>4 else 14
im=Image.open(f)
if im.mode=='RGBA':
    bg=Image.new('RGBA',im.size,(128,128,128,255)); bg.alpha_composite(im); im=bg
L=im.convert('L').crop(box)
# resample so that D = 150 px for comparability
s=150.0/Dp; L=L.resize((max(1,round(L.width*s)),max(1,round(L.height*s))),Image.LANCZOS)
bl=L.filter(ImageFilter.GaussianBlur(5))
W,H=L.size; a=list(L.getdata()); b=list(bl.getdata())
mask=[1 if (b[i]-a[i])>=thr else 0 for i in range(W*H)]
seen=[0]*(W*H); sizes=[]
for i in range(W*H):
    if mask[i] and not seen[i]:
        st=[i]; seen[i]=1; n=0
        while st:
            j=st.pop(); n+=1; x,y=j%W,j//W
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                xx,yy=x+dx,y+dy
                if 0<=xx<W and 0<=yy<H:
                    k=yy*W+xx
                    if mask[k] and not seen[k]: seen[k]=1; st.append(k)
        sizes.append(n)
area_D2=(W*H)/(150.0*150.0)
pores=[n for n in sizes if 2<=n<=450]
print(json.dumps({'file':f.split('/')[-1],'crop':box,'scaled_size':[W,H],'area_D2':round(area_D2,3),'pores':len(pores),'pores_per_D2':round(len(pores)/area_D2,1),'dark_frac_pct':round(100*sum(mask)/(W*H),2)}))
