# Edge (tip) loss in 2-D, per segment (ours only). Replaces the per-row tip count of fringe_matte_v2.py, which only scans
# raw rows 500-1900 (the v2 top-corner cut is at raw y 360-575) and only counts px >= 5 L* above a far-paper median.
# Thread px = product by G-IMG item 6 (1): >= 5 L* brighter than the local paper lower envelope (main definition, 'product_ge_paper+5').
#   Stricter: the same and a fibre ridge (relief >= 4 L* over the 5x5 minimum). Sensitivity (upper bound, low-contrast top corner):
#   any fibre ridge near the local max, no +5 (may include paper edges between tips). Paper control printed for each.
# Lost = thread px with alpha < 0.5, outside the alpha 0.5 contour, connected to the body through thread px.
# Depth = L2 distance to the alpha 0.5 region. Per edge position = max depth assigned to each contour px (nearest-contour label).
# Usage: edge_loss_2d.py <tools-dir> <img1-dir> <out.json> name=alpha.png [name=alpha.png ...]   (alpha files relative to img1-dir)
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab
D=sys.argv[2].rstrip('/')+'/'; OUT=sys.argv[3]; srcs=[a.split('=',1) for a in sys.argv[4:]]
CELL=25.5; HALF=CELL/2
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB'))
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
L=srgb_to_lab(raw)[...,0].astype(np.float32); H,W=L.shape
sure=(cv2.dilate((a0>=0.01).astype(np.uint8),np.ones((5,5),np.uint8))==0).astype(np.float32)
Lp=np.where(sure>0,L,255).astype(np.float32); env=np.where(sure>0,cv2.erode(Lp,np.ones((15,15),np.uint8)),0)
wg=cv2.GaussianBlur(sure,(0,0),8); Pq=cv2.GaussianBlur(env*sure,(0,0),8)/np.maximum(wg,1e-6); valid=wg>0.01
F=cv2.dilate(L,np.ones((9,9),np.uint8)); relief=L-cv2.erode(L,np.ones((5,5),np.uint8))
ridge=(L>=F-6)&(relief>=4)
X=np.arange(W)[None,:]; Y=np.arange(H)[:,None]
band_xy=(X>=1450)&(Y>=360)&(Y<1966)
SEG={'top_corner_y<560':(360,560),'mid_third1_560-973':(560,973),'mid_third2_973-1387':(973,1387),'mid_third3_1387-1800':(1387,1800),'bottom_corner_y>=1800':(1800,1966),
     'top_cut_rows_360-575':(360,575),'all_360-1966':(360,1966)}
far=(sure>0)&valid&band_xy&(cv2.distanceTransform((a0<0.01).astype(np.uint8),cv2.DIST_L2,3)>15)
out={'cell_px_raw':CELL,'half_cell_px_raw':HALF,'control_sure_paper_px':int(far.sum()),
     'control_paper_counted_as_thread_pct':round(100*float((ridge&(L>Pq+5))[far].mean()),3),
     'control_paper_counted_as_ridge_any_pct':round(100*float(ridge[far].mean()),3),
     'control_paper_counted_as_product_ge_paper+5_pct':round(100*float((L>Pq+5)[far].mean()),3)}
def stats(v):
    v=np.asarray(v,float)
    if len(v)==0: return None
    return {'n':int(len(v)),'p50':round(float(np.median(v)),2),'p95':round(float(np.percentile(v,95)),2),'p99':round(float(np.percentile(v,99)),2),'max':round(float(v.max()),2),
            'n_gt_half_cell':int((v>HALF).sum()),'pct_gt_half_cell':round(100*float((v>HALF).mean()),2),'p99_cells':round(float(np.percentile(v,99))/CELL,2),'max_cells':round(float(v.max())/CELL,2)}
for name,path in srcs:
    A=np.array(Image.open(path if path.startswith('/') else D+path).convert('RGBA'))[...,3]/255.
    op=(A>=0.5)
    dout,lab=cv2.distanceTransformWithLabels((~op).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
    res={}
    for tag,thr in [('product_ge_paper+5',(L>Pq+5)&valid),('stricter_ridge_and_ge_paper+5',ridge&(L>Pq+5)&valid),('sensitivity_any_ridge',ridge&valid)]:
        cand=thr&~op&band_xy&(dout<=45)
        # connected to the body through thread px (8-conn), seeded at the 0.5 contour
        m=(cand|op).astype(np.uint8); n,cc=cv2.connectedComponents(m,connectivity=8)
        body=np.bincount(cc[op].ravel(),minlength=n).argmax(); lost=cand&(cc==body)
        depth=dout[lost]
        # per edge position: contour px of op in the band, max depth of the lost px whose nearest op px it is
        edge=op&(cv2.erode(op.astype(np.uint8),np.ones((3,3),np.uint8))==0)&band_xy
        # map label -> op pixel coordinates
        ys,xs=np.nonzero(~op==False)
        lbl_of_op=np.zeros((H,W),np.int32); zy,zx=np.nonzero(op)
        # labels in DIST_LABEL_PIXEL are assigned to zero px of the input ((~op)==0 -> op px) in raster order starting at 1
        lbl_of_op[zy,zx]=np.arange(1,len(zy)+1)
        per=np.zeros(len(zy)+1,np.float32)
        np.maximum.at(per,lab[lost],dout[lost])
        ey,ex=np.nonzero(edge); per_edge=per[lbl_of_op[ey,ex]]
        r={}
        for sn,(y0,y1) in SEG.items():
            mpx=(np.nonzero(lost)[0]>=y0)&(np.nonzero(lost)[0]<y1)
            me=(ey>=y0)&(ey<y1)
            # per row (horizontal), like the old tool but with this thread definition: max x-extent beyond the contour
            rows=[]
            for y in range(y0,y1):
                xs_op=np.nonzero(op[y]&band_xy[y])[0]
                if not len(xs_op): continue
                x5=xs_op.max(); xl=np.nonzero(lost[y,x5+1:x5+46])[0]
                rows.append(int(xl.max())+1 if len(xl) else 0)
            r[sn]={'lost_thread_px':int(mpx.sum()),'depth_of_lost_px':stats(depth[mpx]),
                   'per_edge_position':stats(per_edge[me]),'per_row_x_extent':stats(rows)}
        res[tag]=r
    out[name]=res
json.dump(out,open(OUT,'w'),indent=1)
print({k:out[k] for k in out if k.startswith('control') or k.startswith('cell')})
for nm in [n for n,_ in srcs]:
    for tag,vv in out[nm].items():
        for sn,x in vv.items():
            e=x['per_edge_position']; r=x['per_row_x_extent']; d=x['depth_of_lost_px']
            f=lambda q: '-' if q is None else f"p99 {q['p99']:5.1f} max {q['max']:5.1f} >half {q['n_gt_half_cell']:4d}"
            print(f"{nm:8s} {tag:30s} {sn:24s} lost {x['lost_thread_px']:5d} | edge {f(e)} | row {f(r)} | depth {f(d)}")
