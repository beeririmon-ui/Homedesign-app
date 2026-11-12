# G-IMG item 6 as amended by QA (throw-fixed report, section 4), per segment (each corner and each third), ours only.
# (1) measured classification of a gap px in the right-edge fringe band (gap = >= 6 L* under the local brightest):
#     over the product only if >= 5 L* brighter than the local paper lower envelope; <= +5 (incl. the +2..+5 doubt zone) = against the background.
#     The legacy split (+2 / +5, doubt zone dropped) is printed next to it for comparison with the earlier reports.
# (3) over-product gaps may stay opaque if median dE00 to the fabric line <= 3 and paper-like <= 5% per segment (classifier of fringe_paper2.py).
# (4) against-background gaps: >= 50% at alpha <= 0.5 in every segment.
# Usage: gimg6_segments.py <tools> <img1-dir> <out.json> name=alpha.png ...
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab, de00
D=sys.argv[2].rstrip('/')+'/'; OUT=sys.argv[3]; srcs=[a.split('=',1) for a in sys.argv[4:]]
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB'))
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
lab=srgb_to_lab(raw).astype(np.float32); L=lab[...,0]; H,W=L.shape
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
Lp=np.where(sure>0,L,255).astype(np.float32); env=np.where(sure>0,cv2.erode(Lp,np.ones((15,15),np.uint8)),0)
wg=cv2.GaussianBlur(sure,(0,0),8); Pm=cv2.GaussianBlur(env*sure,(0,0),8)/np.maximum(wg,1e-6); valid=wg>0.01
F=cv2.dilate(L,np.ones((9,9),np.uint8))
# colour classifier (fringe_paper2.py): dE00 to the local paper Lab vs to the interior fabric line at the same L*
lab3=np.stack([cv2.blur(lab[...,c],(3,3)) for c in range(3)],-1)
wg10=cv2.GaussianBlur(sure,(0,0),10); PmLab=np.stack([cv2.GaussianBlur(lab[...,c]*sure,(0,0),10)/np.maximum(wg10,1e-6) for c in range(3)],-1)
fab=cv2.erode((a0>0.99).astype(np.uint8),np.ones((51,51),np.uint8)).astype(bool)
bins=np.arange(40,100); fa=np.full(len(bins),np.nan); fb=np.full(len(bins),np.nan)
for i,l in enumerate(bins):
    s=fab&(L>=l)&(L<l+1)
    if s.sum()>200: fa[i]=np.median(lab[...,1][s]); fb[i]=np.median(lab[...,2][s])
ok=np.isfinite(fa); fa=np.interp(bins,bins[ok],fa[ok]); fb=np.interp(bins,bins[ok],fb[ok])
idx=np.clip(np.round(lab3[...,0]).astype(int)-40,0,len(bins)-1)
Fab=np.stack([lab3[...,0],fa[idx],fb[idx]],-1); dP=de00(lab3,PmLab); dF=de00(lab3,Fab)
paperlike=(dP<dF)&(dP<=3)
SEG={'top_corner_y<560':(360,560),'mid_third1_560-973':(560,973),'mid_third2_973-1387':(973,1387),'mid_third3_1387-1800':(1387,1800),'bottom_corner_y>=1800':(1800,1966),
     'legacy_mid_560-1800':(560,1800),'all':(360,1966)}
Y=np.arange(H)[:,None]; X=np.arange(W)[None,:]
out={'definition':'band = within 40 px inside the alpha 0.5 contour + 45 px outside it, x>=1450, raw rows 360-1965; gap = L* <= local max (9x9) - 6',
     'control_sure_paper_classified_paperlike_pct':round(100*float(paperlike[(sure>0)&valid&(X>=1450)&(cv2.distanceTransform((a0<0.01).astype(np.uint8),cv2.DIST_L2,3)<=30)].mean()),1)}
for name,path in srcs:
    a=np.array(Image.open(path if path.startswith('/') else D+path).convert('RGBA'))[...,3]/255.
    op=a>=0.5; din=cv2.distanceTransform(op.astype(np.uint8),cv2.DIST_L2,3); dout=cv2.distanceTransform((~op).astype(np.uint8),cv2.DIST_L2,3)
    band=((op&(din<=40))|(~op&(dout<=45)))&(X>=1450)&valid&(Y>=360)&(Y<1966)
    gap=band&(L<=F-6)
    bg_amended=gap&(L<=Pm+5); over=gap&(L>Pm+5)
    bg_legacy=gap&(L<=Pm+2); doubt=gap&(L>Pm+2)&(L<=Pm+5)
    opq_over=over&(a>=0.98)
    r={}
    for sn,(y0,y1) in SEG.items():
        m=(Y>=y0)&(Y<y1)
        def pct(mask,cond): return round(100*float(cond[mask].mean()),1) if mask.any() else None
        oo=opq_over&m
        r[sn]={'vs_background_amended_px':int((bg_amended&m).sum()),'vs_background_amended_pct_alpha_le_0.5':pct(bg_amended&m,a<=0.5),
               'doubt_zone_+2_+5_px':int((doubt&m).sum()),'doubt_zone_pct_alpha_le_0.5':pct(doubt&m,a<=0.5),
               'vs_background_legacy_+2_px':int((bg_legacy&m).sum()),'vs_background_legacy_pct_alpha_le_0.5':pct(bg_legacy&m,a<=0.5),
               'over_product_px':int((over&m).sum()),'over_product_pct_opaque_ge_0.98':pct(over&m,a>=0.98),
               'over_product_opaque_dE00_to_fabric_p50':round(float(np.median(dF[oo])),2) if oo.any() else None,
               'over_product_opaque_paperlike_pct':pct(oo,paperlike),
               'item4_pass_ge_50':(pct(bg_amended&m,a<=0.5) or 0)>=50 if (bg_amended&m).any() else None,
               'item3_pass':(bool(np.median(dF[oo])<=3) and pct(oo,paperlike)<=5) if oo.any() else None}
    out[name]=r
json.dump(out,open(OUT,'w'),indent=1)
print('control paperlike on sure paper %',out['control_sure_paper_classified_paperlike_pct'])
for name,_ in srcs:
    for sn,x in out[name].items():
        print(f"{name:8s} {sn:24s} bg(<=+5) {x['vs_background_amended_px']:5d} open {x['vs_background_amended_pct_alpha_le_0.5']!s:>5}% [legacy<=+2 {x['vs_background_legacy_+2_px']:5d} open {x['vs_background_legacy_pct_alpha_le_0.5']!s:>5}%; doubt {x['doubt_zone_+2_+5_px']:4d} open {x['doubt_zone_pct_alpha_le_0.5']!s:>5}%] | over {x['over_product_px']:5d} opaque {x['over_product_pct_opaque_ge_0.98']!s:>5}% dE-fab {x['over_product_opaque_dE00_to_fabric_p50']!s:>5} paperlike {x['over_product_opaque_paperlike_pct']!s:>5}% | item4 {x['item4_pass_ge_50']} item3 {x['item3_pass']}")
