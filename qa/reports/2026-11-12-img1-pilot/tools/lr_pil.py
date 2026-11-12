import sys
from PIL import Image, ImageStat
# left/right half median luminance inside an RGBA cut's opaque area (pure PIL)
im=Image.open(sys.argv[1]).convert('RGBA'); a=im.getchannel('A').point(lambda v:255 if v>=250 else 0); L=im.convert('L')
w,h=im.size; bb=a.getbbox(); xm=(bb[0]+bb[2])//2
for name,box in [('left',(bb[0],bb[1],xm,bb[3])),('right',(xm,bb[1],bb[2],bb[3]))]:
    st=ImageStat.Stat(L.crop(box),a.crop(box)); print(name,'mean L(8bit)',round(st.mean[0],1),'median',st.median[0])
# top vs bottom
ym=(bb[1]+bb[3])//2
for name,box in [('upper',(bb[0],bb[1],bb[2],ym)),('lower',(bb[0],ym,bb[2],bb[3]))]:
    st=ImageStat.Stat(L.crop(box),a.crop(box)); print(name,'mean',round(st.mean[0],1))
