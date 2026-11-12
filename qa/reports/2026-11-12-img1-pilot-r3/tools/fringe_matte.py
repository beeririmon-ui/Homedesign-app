import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab
D=sys.argv[2]
raw=np.array(Image.open(D+'/raw/p2-throw-nano-test-raw.png').convert('RGB')).astype(float)
nob=np.array(Image.open(D+'/raw/p2-throw-nano-test-nobg.png').convert('RGBA')).astype(float)
a=nob[...,3]/255; L=srgb_to_lab(raw)[...,0]
H,W=a.shape
# right fringe: for each row y in the fringe span, rightmost x with a>=0.5
res={}
rows=range(500,1900)
xr=np.array([ (np.nonzero(a[y]>=0.5)[0].max() if (a[y]>=0.5).any() else -1) for y in rows])
res['right_edge_x_p5_p50_p95']=[int(v) for v in np.percentile(xr,[5,50,95])]
# straightness of the alpha boundary: runs of rows where xr changes by <=1px
d=np.abs(np.diff(xr)); runs=[];r=0
for v in d:
    if v<=1: r+=1
    else:
        if r>0: runs.append(r)
        r=0
runs.append(r); runs=sorted(runs,reverse=True)
res['boundary_straight_runs_rows_top5']=runs[:5]
# raw: where do threads actually end? paper L* reference beside the fringe (shadowed paper) per row: median L* at xr+40..xr+80
# thread pixels in raw beyond the alpha boundary: bright (L*>= paper_local+4) pixels at x in (xr, xr+60]
lost=[]; lostpx=0
for i,y in enumerate(rows):
    x0=xr[i]
    if x0<0 or x0+90>=W: continue
    bgL=np.median(L[y,x0+60:x0+90])
    seg=L[y,x0+1:x0+60]
    br=np.nonzero(seg>=bgL+5)[0]
    if len(br): lost.append(int(br.max())+1); lostpx+=len(br)
    else: lost.append(0)
lost=np.array(lost)
res['raw_thread_px_beyond_alpha_edge']={'rows_with_any':int((lost>0).sum()),'rows':int(len(lost)),'max_extent_px':int(lost.max()),'p95_extent_px':float(np.percentile(lost,95)),'bright_px_total':int(lostpx)}
# matte resolution: along vertical lines inside the outer fringe (xr-25..xr-5 per row band), count luminance vs alpha crossings
def crossings(v,thr): s=(v>thr).astype(int); return int(np.abs(np.diff(s)).sum())
lc=0; ac=0; n=0; gap_opaque=0; gap_total=0
for y0 in range(520,1880,40):
    ys=np.arange(y0,y0+40)
    xm=int(np.median(xr[ys-500]))
    for x in range(xm-30,xm-5,5):
        col=L[y0:y0+40,x]; al=a[y0:y0+40,x]
        lc+=crossings(col,np.median(col)); ac+=crossings(al,0.5); n+=1
        # gaps: darker than the local median by 6 L* and alpha>=0.98
        g=col<np.median(col)-6; gap_total+=int(g.sum()); gap_opaque+=int((g&(al>=0.98)).sum())
res['outer_fringe_lines']={'n_line_segments':n,'luminance_crossings':lc,'alpha_crossings':ac,'gap_px':gap_total,'gap_px_opaque_a_ge_0.98':gap_opaque}
print(json.dumps(res,indent=1))
