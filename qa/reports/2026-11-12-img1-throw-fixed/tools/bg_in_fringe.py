# Background (paper) left opaque inside the fringe band, by render-agent's own criterion turned around:
# a lower fabric layer reads BRIGHTER than the shaded paper next to it; a gap that is NOT brighter than the local paper
# (L* <= paper model + 2) and is not a thread (>= 6 L* below the local brightest) is paper seen between threads.
# Ours only. Writes an overlay of the flagged pixels.
import sys, json, numpy as np, cv2
sys.path.insert(0,sys.argv[1]); from lab import srgb_to_lab
from PIL import Image
D=sys.argv[2].rstrip('/')+'/'; OUT=sys.argv[3]
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB'))
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
af=np.array(Image.open(D+'sofa-cover-cj-cotton-muslin-fringe/p2-nano-fixed-fullres.png'))[...,3]/255.
L=srgb_to_lab(raw)[...,0].astype(np.float32); H,W=L.shape
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
# paper model: local LOWER envelope of sure paper (contact shadow), so the test is conservative
Lp=np.where(sure>0,L,255).astype(np.float32); env=cv2.erode(Lp,np.ones((15,15),np.uint8)); env=np.where(sure>0,env,0)
wg=cv2.GaussianBlur(sure,(0,0),8); Pm=cv2.GaussianBlur(env*sure,(0,0),8)/np.maximum(wg,1e-6); valid=wg>0.01
F=cv2.dilate(L,np.ones((9,9),np.uint8))
res={}
for tag,alpha in [('fixed',af),('remove_bg',a0)]:
    op=alpha>=0.5; dist=cv2.distanceTransform(op.astype(np.uint8),cv2.DIST_L2,3)
    band=op&(dist<=40)&(np.arange(W)[None,:]>=1450)&valid
    flag=band&(L<=Pm+2)&(L<=F-6)
    rows=np.arange(H)[:,None]; r={'band_px':int(band.sum()),'flagged_px':int(flag.sum())}
    for nm,(r0,r1) in {'top_y<560':(0,560),'mid_560-1800':(560,1800),'bottom_y>=1800':(1800,H)}.items():
        m=(rows>=r0)&(rows<r1); r[nm]=int((flag&m).sum())
    r['flagged_px_final_scale_approx']=int(round(flag.sum()*0.8878**2))
    res[tag]=r
    if tag=='fixed': fl=flag
# overlay crops
rgb=raw.copy(); ov=rgb.copy(); ov[fl]=(255,0,0)
for nm,box in {'bottom':(1540,1780,1700,1960),'mid':(1480,1100,1680,1300),'top':(1380,370,1620,560)}.items():
    x0,y0,x1,y1=box; c=np.concatenate([rgb[y0:y1,x0:x1],np.full((y1-y0,4,3),255,np.uint8),ov[y0:y1,x0:x1]],1)
    Image.fromarray(c).resize(((c.shape[1])*3,(y1-y0)*3),Image.NEAREST).save(OUT.replace('.json',f'-{nm}.png'))
    res['flagged_in_'+nm+'_crop']=int(fl[y0:y1,x0:x1].sum())
json.dump(res,open(OUT,'w'),indent=1); print(json.dumps(res,indent=1))
