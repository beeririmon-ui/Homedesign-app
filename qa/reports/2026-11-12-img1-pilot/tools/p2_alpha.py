import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab, de00, lch
path=sys.argv[2]
im=np.array(Image.open(path).convert('RGBA')).astype(np.float64)
H,W=im.shape[:2]; rgb=im[...,:3]; a=im[...,3]/255.0
out={'file':path,'size':[W,H]}
O=(a>=0.5).astype(np.uint8)
n,lbl,st,_=cv2.connectedComponentsWithStats(O,8)
comps=sorted([(int(st[i,4]),i) for i in range(1,n)],reverse=True)
out['components_ge_0.5']=[{'area':ar,'bbox':[int(st[i,0]),int(st[i,1]),int(st[i,0]+st[i,2]),int(st[i,1]+st[i,3])]} for ar,i in comps[:6]]
big=[i for ar,i in comps if ar>2000]
main=np.isin(lbl,big).astype(np.uint8)
# stray specks: alpha>0.02 components not connected to main objects (dilated)
anyA=(a>0.02).astype(np.uint8)
n2,l2,s2,_=cv2.connectedComponentsWithStats(anyA,8)
md=cv2.dilate(main,np.ones((9,9),np.uint8))
stray=[int(s2[i,4]) for i in range(1,n2) if not md[l2==i].any()]
out['stray_specks']={'count':len(stray),'px':int(sum(stray))}
# edge of canvas
out['alpha_on_canvas_border_max']=int(max(a[0].max(),a[-1].max(),a[:,0].max(),a[:,-1].max())*255)
# interior transparency: fill holes of main
filled=main.copy(); cnts,_=cv2.findContours(main,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE); cv2.drawContours(filled,cnts,-1,1,-1)
inner=cv2.erode(filled,np.ones((7,7),np.uint8)).astype(bool)
out['interior']={'px':int(inner.sum()),'frac_alpha_lt_0.98':round(float((a[inner]<0.98).mean()),5),'frac_alpha_lt_0.5':round(float((a[inner]<0.5).mean()),5),'min_alpha':round(float(a[inner].min()),3)}
# soft edge width: pixels with 0.02<a<0.98 per unit of contour length
soft=((a>0.02)&(a<0.98)); perim=sum(len(c) for c in cnts)
out['soft_edge']={'px':int(soft.sum()),'perimeter_px':int(perim),'mean_width_px':round(float(soft.sum()/max(perim,1)),2)}
# distance outside O
dist=cv2.distanceTransform((1-filled).astype(np.uint8),cv2.DIST_L2,5)
band=(dist>=0.5)&(dist<=4.5)
out['alpha_in_band_1_4px']={'max255':int(round(a[band].max()*255)),'p99_255':int(round(np.percentile(a[band],99)*255)),'px_gt_0.05':int((a[band]>0.05).sum())}
for name,bg in [('paper_F4F1EC',(0xF4,0xF1,0xEC)),('dark_3A3A3A',(0x3A,0x3A,0x3A))]:
    bgv=np.array(bg,float); comp=rgb*a[...,None]+bgv*(1-a[...,None])
    L1=srgb_to_lab(comp[band].clip(0,255)); L0=srgb_to_lab(np.tile(bgv,(L1.shape[0],1)))
    d=de00(L0,L1)
    # edge ring just inside the boundary (soft pixels with a in (0.05,0.95)) vs object colour 3px inside
    out['band_dE00_'+name]={'median':round(float(np.median(d)),3),'p95':round(float(np.percentile(d,95)),3),'max':round(float(d.max()),3),'frac_gt_2':round(float((d>2).mean()),5)}
# colour contamination of soft edge: straight RGB of 0.1<a<0.9 vs nearest opaque pixel (via inpaint-free approach: median of opaque px within 4px)
sel=np.argwhere((a>0.1)&(a<0.9))
op=(a>=0.99).astype(np.uint8)
dist_in, labels = cv2.distanceTransformWithLabels(1-op, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
# map label -> coordinate of the opaque pixel
ys,xs=np.nonzero(op==0) # unused
opix=np.argwhere(op.T.T==1)
lab_idx=np.zeros(labels.max()+1,dtype=np.int64)
# build mapping from label id to opaque coordinate
lbl_at_op=labels[op==1]; coords=np.argwhere(op==1)
lab_idx[lbl_at_op]=np.arange(len(coords))
if len(sel):
    near=coords[lab_idx[labels[sel[:,0],sel[:,1]]]]
    e=srgb_to_lab(rgb[sel[:,0],sel[:,1]]); o=srgb_to_lab(rgb[near[:,0],near[:,1]])
    d=de00(o,e); dL=e[:,0]-o[:,0]
    out['soft_edge_colour_vs_nearest_opaque']={'n':int(len(sel)),'dE00_median':round(float(np.median(d)),2),'dE00_p95':round(float(np.percentile(d,95)),2),'dL_median':round(float(np.median(dL)),2),'dL_p5':round(float(np.percentile(dL,5)),2),'dL_p95':round(float(np.percentile(dL,95)),2)}
print(json.dumps(out,indent=1))
