# G-IMG 6 item 3 in the top corner as implemented in v3 (ours only): the over-product gaps left half-open (alpha cap 0.9).
# (1) the gaps by QA's definition (gimg6_segments.py: band from the file's own 0.5 contour, gap = L* <= local max - 6, over product = > paper env + 5),
#     top segment y<560 and the v3 tool's whole corner zone; their alpha; their colour class (dE00 to the fabric line, paper-like %) on ALL of them,
#     i.e. would they pass item 3 if they were opaque;
# (2) visibility: composite on paper #F4F1EC and dark #3A3A3A, v3 vs the same file with those px at their pre-cap alpha (v1 fullres alpha, opaque),
#     per px in raw space and at page size (1638 file -> 1280 tall, LANCZOS), dE00;
# (3) the halo px around the restored tips (non-product 8-neighbours of product px that gained alpha vs v2) and their alpha.
# Usage: item3_corner.py <tools(v2)> <img1-dir> <out.json>
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab, de00
D=sys.argv[2].rstrip('/')+'/'; OUT=sys.argv[3]; A=D+'sofa-cover-cj-cotton-muslin-fringe/'
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB'))
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
v1=np.array(Image.open(A+'p2-nano-fixed-fullres.png').convert('RGBA')); v2=np.array(Image.open(A+'p2-nano-fixed-v2-fullres.png').convert('RGBA'))
v3=np.array(Image.open(A+'p2-nano-fixed-v3-fullres.png').convert('RGBA'))
lab=srgb_to_lab(raw).astype(np.float32); L=lab[...,0]; H,W=L.shape
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
Lp=np.where(sure>0,L,255).astype(np.float32); env=np.where(sure>0,cv2.erode(Lp,np.ones((15,15),np.uint8)),0)
wg=cv2.GaussianBlur(sure,(0,0),8); Pm=cv2.GaussianBlur(env*sure,(0,0),8)/np.maximum(wg,1e-6); valid=wg>0.01
F=cv2.dilate(L,np.ones((9,9),np.uint8))
lab3=np.stack([cv2.blur(lab[...,c],(3,3)) for c in range(3)],-1)
wg10=cv2.GaussianBlur(sure,(0,0),10); PmLab=np.stack([cv2.GaussianBlur(lab[...,c]*sure,(0,0),10)/np.maximum(wg10,1e-6) for c in range(3)],-1)
fab=cv2.erode((a0>0.99).astype(np.uint8),np.ones((51,51),np.uint8)).astype(bool)
bins=np.arange(40,100); fa=np.full(len(bins),np.nan); fb=np.full(len(bins),np.nan)
for i,l in enumerate(bins):
    s=fab&(L>=l)&(L<l+1)
    if s.sum()>200: fa[i]=np.median(lab[...,1][s]); fb[i]=np.median(lab[...,2][s])
ok=np.isfinite(fa); fa=np.interp(bins,bins[ok],fa[ok]); fb=np.interp(bins,bins[ok],fb[ok])
idx=np.clip(np.round(lab3[...,0]).astype(int)-40,0,len(bins)-1)
Fab=np.stack([lab3[...,0],fa[idx],fb[idx]],-1); dP=de00(lab3,PmLab); dF=de00(lab3,Fab); paperlike=(dP<dF)&(dP<=3)
Y=np.arange(H)[:,None]; X=np.arange(W)[None,:]
a3=v3[...,3]/255.; a1=v1[...,3]/255.; a2=v2[...,3]/255.
op=a3>=0.5; din=cv2.distanceTransform(op.astype(np.uint8),cv2.DIST_L2,3); dout=cv2.distanceTransform((~op).astype(np.uint8),cv2.DIST_L2,3)
band=((op&(din<=40))|(~op&(dout<=45)))&(X>=1450)&valid&(Y>=360)&(Y<1966)
gap=band&(L<=F-6); over=gap&(L>Pm+5)
zone=(X>=1486)&(Y<566)&(Y>=360)
def q(v,ps=(10,50,90)): v=np.asarray(v,float); return [round(float(x),3) for x in np.percentile(v,ps)] if len(v) else None
out={}
for nm,m in [('top_segment_y<560',over&(Y<560)),('v3_corner_zone_x>=1486_y<566',over&zone)]:
    out[nm]={'over_product_gaps':int(m.sum()),'alpha_p10_p50_p90':q(a3[m]),'opaque_ge_0.98':int((a3[m]>=0.98).sum()),
             'alpha_0.5_to_0.98':int(((a3[m]>=0.5)&(a3[m]<0.98)).sum()),'alpha_lt_0.5':int((a3[m]<0.5).sum()),
             'of_lt_0.5_v1_alpha_lt_0.5':int(((a3[m]<0.5)&(a1[m]<0.5)).sum()),
             'v1_alpha_p10_p50_p90':q(a1[m]),'v1_opaque_ge_0.98_pct':round(100*float((a1[m]>=0.98).mean()),1) if m.any() else None,
             'colour_all_dE00_to_fabric_p50':round(float(np.median(dF[m])),2) if m.any() else None,
             'colour_all_paperlike_pct':round(100*float(paperlike[m].mean()),1) if m.any() else None,
             'colour_all_dE00_to_paper_p50':round(float(np.median(dP[m])),2) if m.any() else None,
             'L_minus_paper_env_p10_p50':q((L-Pm)[m],(10,50))}
# where v3 alpha is below v1 alpha in the corner although the px is product (would be 'opaque' in v1): the half-open set, any band
capped=zone&(L>Pm+5)&(a3<a1-0.02)&(a1>=0.5)
out['product_px_in_zone_with_alpha_below_v1']={'px':int(capped.sum()),'alpha_drop_p50_max':[round(float(np.median((a1-a3)[capped])),3),round(float((a1-a3)[capped].max()),3)] if capped.any() else None}
# (2) visibility: v3 vs v3 with the capped px restored to their v1 alpha (only alpha changes; RGB is the file's own)
alt=v3.copy(); alt[...,3][capped]=v1[...,3][capped]
def comp(im,bg):
    a=im[...,3:4]/255.; return np.clip(im[...,:3]*a+np.array(bg,float)*(1-a),0,255)
vis={}
for bn,bg in [('paper',(0xF4,0xF1,0xEC)),('dark',(0x3A,0x3A,0x3A))]:
    c3=comp(v3,bg); ca=comp(alt,bg); d=de00(srgb_to_lab(c3[capped]),srgb_to_lab(ca[capped]))
    vis[bn+'_raw_px']={'p50':round(float(np.median(d)),2),'p95':round(float(np.percentile(d,95)),2),'max':round(float(d.max()),2)} if len(d) else None
out['visibility_capped_vs_v1_alpha']=vis
# the halo: product-neighbour px that gained alpha vs v2 in the zone but are not product (<= paper + 5)
gain=zone&(a3>a2+0.02); halo=gain&~(L>Pm+5)
out['gained_alpha_vs_v2']={'px':int(gain.sum()),'product_px':int((gain&(L>Pm+5)).sum()),'non_product_px':int(halo.sum()),
   'non_product_alpha_p50_max':[round(float(np.median(a3[halo])),3),round(float(a3[halo].max()),3)] if halo.any() else None,
   'non_product_alpha_gt_0.5':int((a3[halo]>0.5).sum())}
json.dump(out,open(OUT,'w'),indent=1); print(json.dumps(out,indent=1))
