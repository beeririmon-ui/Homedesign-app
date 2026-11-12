# Paper colour inside the fringe band, by colour likelihood (our images only).
# For every opaque gap pixel in the right-edge fringe band: dE00 to the local paper model (paper Lab extrapolated inward)
# vs dE00 to the fabric shadow line at the same L* (interior fabric, >=25 px from any edge). Paper-like = closer to paper and dE00<=3.
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab, de00
D=sys.argv[2].rstrip('/')+'/'; OUT=sys.argv[3]
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB'))
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
af=np.array(Image.open(D+'sofa-cover-cj-cotton-muslin-fringe/p2-nano-fixed-fullres.png'))[...,3]/255.
lab=srgb_to_lab(raw).astype(np.float32); L=lab[...,0]; H,W=L.shape
lab3=np.stack([cv2.blur(lab[...,c],(3,3)) for c in range(3)],-1)
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
wg=cv2.GaussianBlur(sure,(0,0),10); Pm=np.stack([cv2.GaussianBlur(lab[...,c]*sure,(0,0),10)/np.maximum(wg,1e-6) for c in range(3)],-1)
valid=wg>0.01
fab=cv2.erode((a0>0.99).astype(np.uint8),np.ones((51,51),np.uint8)).astype(bool)
# fabric line: median a*, b* per 1-L* bin
bins=np.arange(40,100); fa=np.full(len(bins),np.nan); fb=np.full(len(bins),np.nan)
for i,l in enumerate(bins):
    s=fab&(L>=l)&(L<l+1)
    if s.sum()>200: fa[i]=np.median(lab[...,1][s]); fb[i]=np.median(lab[...,2][s])
ok=np.isfinite(fa); fa=np.interp(bins,bins[ok],fa[ok]); fb=np.interp(bins,bins[ok],fb[ok])
idx=np.clip(np.round(lab3[...,0]).astype(int)-40,0,len(bins)-1)
Fab=np.stack([lab3[...,0],fa[idx],fb[idx]],-1)
dP=de00(lab3,Pm); dF=de00(lab3,Fab)
F=cv2.dilate(L,np.ones((9,9),np.uint8))
res={}
maps={}
for tag,alpha in [('fixed',af),('remove_bg',a0)]:
    opaque=alpha>=0.5
    dist=cv2.distanceTransform(opaque.astype(np.uint8),cv2.DIST_L2,3)
    region=opaque&(dist<=40)&(np.arange(W)[None,:]>=1450)&valid
    gap=region&(L<=F-12)
    paper=gap&(dP<dF)&(dP<=3)
    r={'gap_px':int(gap.sum()),'paperlike_px':int(paper.sum()),'pct':round(100*paper.sum()/max(1,gap.sum()),1),
       'gap_dE_to_paper_p50':round(float(np.median(dP[gap])),2),'gap_dE_to_fabric_p50':round(float(np.median(dF[gap])),2)}
    rows=np.arange(H)[:,None]
    for nm,(r0,r1) in {'top_y<560':(0,560),'mid_560-1800':(560,1800),'bottom_y>=1800':(1800,H)}.items():
        m=(rows>=r0)&(rows<r1); g=gap&m; p=paper&m
        r[nm]={'gap':int(g.sum()),'paperlike':int(p.sum()),'pct':round(100*p.sum()/max(1,g.sum()),1)}
    for d0,d1 in [(0,5),(5,15),(15,40)]:
        m=(dist>d0)&(dist<=d1); r[f'dist_{d0}-{d1}']={'gap':int((gap&m).sum()),'paperlike':int((paper&m).sum())}
    res[tag]=r; maps[tag]=paper
# control: the same classifier on sure-fabric gaps (interior waffle cells) and sure-paper pixels
ctrl_f=fab&(L<=F-12); ctrl_p=(sure>0)&valid&(np.arange(W)[None,:]>=1450)&(cv2.distanceTransform((a0<0.01).astype(np.uint8),cv2.DIST_L2,3)<=30)
res['control_interior_fabric_gaps_classified_paper_pct']=round(100*float(((dP<dF)&(dP<=3))[ctrl_f&valid].mean()),1) if (ctrl_f&valid).any() else None
res['control_sure_paper_classified_paper_pct']=round(100*float(((dP<dF)&(dP<=3))[ctrl_p].mean()),1)
res['fabric_line_ab_at_L60_70_80']=[[round(float(fa[l-40]),2),round(float(fb[l-40]),2)] for l in (60,70,80)]
json.dump(res,open(OUT,'w'),indent=1); print(json.dumps(res,indent=1))
np.save(OUT.replace('.json','-map.npy'),maps['fixed'])
