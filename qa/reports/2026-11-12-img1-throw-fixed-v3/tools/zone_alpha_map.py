# Where the v3 top-corner alpha differs from v1 and v2 (ours only): classes in the corner zone (x>=1486, y 360-565), raw space.
# product = >= QA paper envelope + 5 L* (G-IMG 6 (1)); non-product = the rest. Prints a breakdown by sub-area and writes a colour map:
# red = non-product px with v3 alpha > 0.5 that v2 had cut (<0.5); orange = same, v3 alpha 0.1-0.5; cyan = product px restored vs v2 (v2 <0.5, v3 >=0.5);
# yellow = over-product gaps capped (v3 alpha 0.85-0.98 where v1 >= 0.98); magenta = product px still lost vs v1 (v1 >=0.5, v3 <0.5).
# Also: the over-product-gap visibility for the capped set only. Usage: zone_alpha_map.py <tools(v2)> <img1-dir> <out.png> <out.json> zoom
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab, de00
D=sys.argv[2].rstrip('/')+'/'; OUTP=sys.argv[3]; OUTJ=sys.argv[4]; z=int(sys.argv[5]); A=D+'sofa-cover-cj-cotton-muslin-fringe/'
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB'))
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
v1=np.array(Image.open(A+'p2-nano-fixed-fullres.png').convert('RGBA')); v2=np.array(Image.open(A+'p2-nano-fixed-v2-fullres.png').convert('RGBA')); v3=np.array(Image.open(A+'p2-nano-fixed-v3-fullres.png').convert('RGBA'))
L=srgb_to_lab(raw)[...,0].astype(np.float32); H,W=L.shape
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
Lp=np.where(sure>0,L,255).astype(np.float32); env=np.where(sure>0,cv2.erode(Lp,np.ones((15,15),np.uint8)),0)
wg=cv2.GaussianBlur(sure,(0,0),8); Pm=cv2.GaussianBlur(env*sure,(0,0),8)/np.maximum(wg,1e-6)
F=cv2.dilate(L,np.ones((9,9),np.uint8))
a1,a2,a3=[v[...,3]/255. for v in (v1,v2,v3)]
Y=np.arange(H)[:,None]; X=np.arange(W)[None,:]; zone=(X>=1486)&(Y>=360)&(Y<566)
prod=L>Pm+5
red=zone&~prod&(a2<0.5)&(a3>0.5); orange=zone&~prod&(a2<0.5)&(a3>0.1)&(a3<=0.5)
cyan=zone&prod&(a2<0.5)&(a3>=0.5); yellow=zone&prod&(L<=F-6)&(a1>=0.98)&(a3>=0.85)&(a3<0.98); mag=zone&prod&(a1>=0.5)&(a3<0.5)
areas={'ramp_left_x1486-1510':(X<1510),'ramp_bottom_y542-566':(Y>=542)&(X>=1510),'full_cut_x>=1510_y<542':(X>=1510)&(Y<542)}
out={}
for nm,m in [('red_nonproduct_v2cut_v3_gt_0.5',red),('orange_nonproduct_v2cut_v3_0.1-0.5',orange),('cyan_product_restored_vs_v2',cyan),('yellow_overproduct_gaps_capped',yellow),('magenta_product_lost_vs_v1',mag)]:
    out[nm]={'px':int(m.sum()),**{k:int((m&a).sum()) for k,a in areas.items()},'L_minus_paper_p50':round(float(np.median((L-Pm)[m])),2) if m.any() else None,
             'v1_alpha_p50':round(float(np.median(a1[m])),3) if m.any() else None,'v3_alpha_p50':round(float(np.median(a3[m])),3) if m.any() else None}
# red px: were they opaque in v1 too (i.e. back to v1, the ramp), and how far are they from the v3 0.5 contour
op3=a3>=0.5; din=cv2.distanceTransform(op3.astype(np.uint8),cv2.DIST_L2,3)
out['red_detail']={'v1_alpha_ge_0.5':int((red&(a1>=0.5)).sum()),'depth_inside_v3_contour_p50_p95_max':[round(float(v),1) for v in np.percentile(din[red],[50,95,100])] if red.any() else None,
                   'is_gap_L_le_F-6':int((red&(L<=F-6)).sum())}
# visibility of the capped over-product gaps only (yellow): v3 vs the same px at the v1 alpha
def comp(im,bg,alpha=None):
    a=(im[...,3] if alpha is None else alpha)[...,None]/255.; return np.clip(im[...,:3]*a+np.array(bg,float)*(1-a),0,255)
vis={}
for bn,bg in [('paper',(0xF4,0xF1,0xEC)),('dark',(0x3A,0x3A,0x3A))]:
    alt=v3[...,3].copy(); alt[yellow]=v1[...,3][yellow]
    d=de00(srgb_to_lab(comp(v3,bg)[yellow]),srgb_to_lab(comp(v3,bg,alt)[yellow]))
    vis[bn]={'p50':round(float(np.median(d)),2),'p95':round(float(np.percentile(d,95)),2),'max':round(float(d.max()),2)} if len(d) else None
    # the same at page size: resize both composites with the shipped re-frame (x0.8878) then to 1280 tall (x0.625)
    s=0.8878*0.625; c3=Image.fromarray(comp(v3,bg).astype(np.uint8)).crop((1440,340,1700,620)); ca=Image.fromarray(comp(v3,bg,alt).astype(np.uint8)).crop((1440,340,1700,620))
    sz=(round(260*s),round(280*s)); r3=np.array(c3.resize(sz,Image.LANCZOS)).astype(float); ra=np.array(ca.resize(sz,Image.LANCZOS)).astype(float)
    dp=de00(srgb_to_lab(r3.reshape(-1,3)),srgb_to_lab(ra.reshape(-1,3)))
    vis[bn+'_page1280']={'p99':round(float(np.percentile(dp,99)),2),'max':round(float(dp.max()),2),'px_gt_2':int((dp>2).sum())}
out['yellow_capped_visibility_vs_v1_alpha']=vis
x0,y0,w,h=1480,355,130,215; sl=(slice(y0,y0+h),slice(x0,x0+w))
m=(raw[sl]*0.55+0.45*255*0).astype(np.uint8)
for msk,colr in [(red,(255,0,0)),(orange,(255,150,0)),(cyan,(0,220,255)),(yellow,(255,255,0)),(mag,(255,0,255))]: m[msk[sl]]=colr
c=v3[sl]; e=(c[...,3]>=128).astype(np.uint8); e=e-cv2.erode(e,np.ones((3,3),np.uint8)); m[e>0]=(255,255,255)
Image.fromarray(m).resize((w*z,h*z),Image.NEAREST).save(OUTP)
json.dump(out,open(OUTJ,'w'),indent=1); print(json.dumps(out,indent=1))
