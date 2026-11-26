import sys, json
import numpy as np, cv2
from PIL import Image
def meas(p, pend_x=(640,840)):
    a=np.asarray(Image.open(p).convert('RGB')).astype(np.float32)/255
    lab=cv2.cvtColor(a,cv2.COLOR_RGB2LAB); L=lab[...,0]
    H,W=L.shape
    out=dict(size=[W,H], L_p0_5=round(float(np.percentile(L,0.5)),1), L_p50=round(float(np.percentile(L,50)),1), L_p99_5=round(float(np.percentile(L,99.5)),1))
    # the pendant's top: the first row where the column band over the table differs from the wall around it
    band=L[:, pend_x[0]:pend_x[1]]
    side=np.concatenate([L[:, pend_x[0]-90:pend_x[0]-30], L[:, pend_x[1]+30:pend_x[1]+90]],axis=1)
    diff=np.abs(band - np.median(side,axis=1,keepdims=True))
    wide=(diff>6).sum(axis=1)                     # px of the row that are not wall
    rows=np.where(wide>40)[0]
    out['pendant_top_row_px']=int(rows.min()) if len(rows) else None
    out['pendant_clearance_share_of_height']=round(float(rows.min())/H,4) if len(rows) else None
    # wall patches (upper right wall = shade; the patch left of the first print)
    for k,(x0,y0,x1,y1) in dict(wall_upper_right=(1120,60,1300,160), wall_left_of_prints=(470,230,560,330), wall_above_sofa_left=(500,400,580,440), table_top=(640,600,760,618), sofa_seat=(600,575,680,590)).items():
        out[k+'_Lab']=[round(float(v),1) for v in np.median(lab[y0:y1,x0:x1].reshape(-1,3),axis=0)]
    return out
r={}
for p in sys.argv[1:]:
    r[p.split('/')[-1]]=meas(p)
print(json.dumps(r,indent=1))
