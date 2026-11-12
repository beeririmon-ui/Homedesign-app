import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab, de00
f=sys.argv[2]
im=np.array(Image.open(f).convert('RGBA')).astype(np.float64); rgb=im[...,:3]; a=im[...,3]/255.0
op=(a>=0.98).astype(np.uint8)
# nearest opaque pixel colour for each soft pixel (decontaminated edge colour)
_,lbl=cv2.distanceTransformWithLabels(1-op,cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
coords=np.argwhere(op==1); idmap=np.zeros(lbl.max()+1,np.int64); idmap[lbl[op==1]]=np.arange(len(coords))
soft=(a>0.02)&(a<0.98); ys,xs=np.nonzero(soft); near=coords[idmap[lbl[ys,xs]]]
clean=rgb[near[:,0],near[:,1]]; actual=rgb[ys,xs]; al=a[ys,xs][:,None]
out={'file':f.split('/')[-1],'soft_px':int(len(ys))}
for name,bg in [('paper_F4F1EC',(0xF4,0xF1,0xEC)),('dark_3A3A3A',(0x3A,0x3A,0x3A))]:
    bg=np.array(bg,float); ca=actual*al+bg*(1-al); cc=clean*al+bg*(1-al)
    d=de00(srgb_to_lab(cc),srgb_to_lab(ca)); dl=srgb_to_lab(ca)[:,0]-srgb_to_lab(cc)[:,0]
    out[name]={'dE00_median':round(float(np.median(d)),2),'dE00_p95':round(float(np.percentile(d,95)),2),'dE00_p99':round(float(np.percentile(d,99)),2),'frac_gt_2':round(float((d>2).mean()),4),'frac_gt_5':round(float((d>5).mean()),4),'dL_median':round(float(np.median(dl)),2)}
# alpha ramp width: distance from a=0.5 contour to a<=0.02 outside, median over boundary
O=(a>=0.5).astype(np.uint8); dist=cv2.distanceTransform(1-O,cv2.DIST_L2,5)
skirt=(a>0.02)&(O==0); out['alpha_skirt_px_max_dist']=round(float(dist[skirt].max()),2) if skirt.any() else 0; out['alpha_skirt_px_p99_dist']=round(float(np.percentile(dist[skirt],99)),2) if skirt.any() else 0
print(json.dumps(out))
