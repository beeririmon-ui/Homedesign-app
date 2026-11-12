import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab, lch
f=sys.argv[2]
im=np.array(Image.open(f).convert('RGBA')).astype(float); a=im[...,3]/255; lab=srgb_to_lab(im[...,:3]); L=lab[...,0]
h=np.degrees(np.arctan2(lab[...,2],lab[...,1]))%360; C=np.hypot(lab[...,1],lab[...,2])
O=(a>=0.5)
n,lbl,st,_=cv2.connectedComponentsWithStats(O.astype(np.uint8),8)
units=sorted([i for i in range(1,n) if st[i,4]>5000],key=lambda i:st[i,0])
out={'file':f.split('/')[-1],'per_unit':[]}
for i in units:
    u=(lbl==i); ys=np.nonzero(u.any(1))[0]
    xr=np.array([np.nonzero(u[y])[0].max() if u[y].any() else -1 for y in range(im.shape[0])])
    stone=u&(L>=42)&(h>=66)&(h<=100)&(C>=6)
    mid=range(int(np.percentile(ys,35)),int(np.percentile(ys,65)))
    xl=int(np.median([np.nonzero(stone[y])[0].min() for y in mid if stone[y].any()]))
    xrm=int(np.median([xr[y] for y in mid])); D=xrm-xl+1; cx=(xl+xrm)//2
    col=np.nonzero(u[:,cx])[0]; top_apex,bot_apex=int(col.min()),int(col.max())
    full=[y for y in range(top_apex,bot_apex+1) if xr[y]>=xrm-1]
    tc,bc=min(full),max(full)
    # wood plate: dark reddish component, largest
    wood=(u&(L<50)&(h>=20)&(h<70)&(C>=12)).astype(np.uint8)
    wood=cv2.morphologyEx(wood,cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
    nn,l2,s2,_=cv2.connectedComponentsWithStats(wood,8); k=1+int(np.argmax(s2[1:,4]))
    pb=[int(s2[k,0]),int(s2[k,1]),int(s2[k,0]+s2[k,2]-1),int(s2[k,1]+s2[k,3]-1)]
    sil=bot_apex-top_apex+1
    labs=lab[stone]; Ls=labs[:,0]; p90,p99=np.percentile(Ls,[90,99]); s=(Ls>=p90)&(Ls<=p99)
    out['per_unit'].append({'D':D,'axis_x':cx,'top_apex':top_apex,'top_full':tc,'bottom_full':bc,'bottom_apex':bot_apex,'sil_h':sil,
      'top_bulge':tc-top_apex,'bottom_bulge':bot_apex-bc,'H_over_D_sil':round(sil/D,3),'H_over_D_centres':round((bc-tc)/D,3),
      'b_over_a_top':round(2*(tc-top_apex)/D,3),'b_over_a_bottom':round(2*(bot_apex-bc)/D,3),
      'plate_bbox':pb,'plate_h_over_sil':round((pb[3]-pb[1]+1)/sil,3),'plate_top_below_top_over_D':round((pb[1]-top_apex)/D,3),'plate_bottom_above_bottom_over_D':round((bot_apex-pb[3])/D,3),
      'stone_lit_LCh_p90_99':lch(np.median(labs[s],0))})
print(json.dumps(out))
