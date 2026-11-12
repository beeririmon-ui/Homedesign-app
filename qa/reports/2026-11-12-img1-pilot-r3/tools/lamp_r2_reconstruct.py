import sys, numpy as np, cv2, json
from PIL import Image
# lamp_r2_reconstruct.py raw.png final.png split_x shift_px scale : rebuild the final from the raw (cut, shift, premultiplied downscale) and compare
raw=np.array(Image.open(sys.argv[1]).convert('RGBA')).astype(float); fin=np.array(Image.open(sys.argv[2]).convert('RGBA')).astype(float)
sx,sh,s=int(sys.argv[3]),int(sys.argv[4]),float(sys.argv[5]); H,W=raw.shape[:2]
cv=np.zeros((H,W+sh,4)); cv[:,:sx]=raw[:,:sx]; cv[:,sx+sh:W+sh]=raw[:,sx:]
al=cv[...,3:4]/255; pm=np.concatenate([cv[...,:3]*al,cv[...,3:4]],-1)
big=cv2.resize(pm,(round(pm.shape[1]*s),round(pm.shape[0]*s)),interpolation=cv2.INTER_AREA)
ys,xs=np.nonzero(big[...,3]>=128); fy,fx=np.nonzero(fin[...,3]>=128); ox,oy=fx.min()-xs.min(),fy.min()-ys.min()
rec=np.zeros_like(fin); h,w=big.shape[:2]; y0,x0=max(0,oy),max(0,ox)
rec[y0:y0+h-max(0,-oy),x0:x0+w-max(0,-ox)]=big[max(0,-oy):h,max(0,-ox):w][:rec.shape[0]-y0,:rec.shape[1]-x0]
A=rec[...,3]>=128; B=fin[...,3]>=128; m=(rec[...,3]>=250)&(fin[...,3]>=250)
rgb=rec[...,:3]/np.maximum(rec[...,3:4]/255,1e-6); d=np.abs(rgb[m]-fin[...,:3][m])
print(json.dumps({'raw_col_alpha_max_at_split':float(raw[:,sx,3].max()),'offset':[int(ox),int(oy)],'alpha_iou':round(float((A&B).sum()/(A|B).sum()),4),'rgb_absdiff_mean':round(float(d.mean()),2),'rgb_absdiff_p99':round(float(np.percentile(d,99)),1)}))
