# Fidelity per plan 5.5 on the final throw P2 (ours only): lit side, top layer, dE00 vs the SKU lit side (QA r3 value), texture, sharpness, clipping.
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab, lch, de00
new=np.array(Image.open(sys.argv[2]).convert('RGBA')).astype(np.float64)
old=np.array(Image.open(sys.argv[3]).convert('RGBA')).astype(np.float64)
SKU_LCH=(90.35,3.93,72.3)
sku=np.array([SKU_LCH[0],SKU_LCH[1]*np.cos(np.radians(SKU_LCH[2])),SKU_LCH[1]*np.sin(np.radians(SKU_LCH[2]))])
def lit(im,extra=None,lo=90,hi=99):
    m=im[...,3]>=0.9*255
    if extra is not None: m&=extra
    lab=srgb_to_lab(im[...,:3][m]); L=lab[:,0]; p1,p2=np.percentile(L,[lo,hi]); v=np.median(lab[(L>=p1)&(L<=p2)],0)
    return v
def toplayer(im):
    m=im[...,3]>=0.9*255; ys,xs=np.nonzero(m); y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
    t=np.zeros(m.shape,bool); t[y0+int(0.05*(y1-y0)):y0+int(0.80*(y1-y0)), x0+int(0.03*(x1-x0)):x0+int(0.80*(x1-x0))]=True; return t
def hpstd(im):
    m=cv2.erode((im[...,3]>=0.98*255).astype(np.uint8),np.ones((15,15),np.uint8))>0
    L=srgb_to_lab(im[...,:3])[...,0]; return float(np.std((L-cv2.GaussianBlur(L,(0,0),8))[m]))
out={}
for tag,im in [('fixed',new),('nano_test_before',old)]:
    v=lit(im); t=lit(im,toplayer(im)); p=lit(im,None,75,98)
    out[tag]={'lit_p90_99_LCh':lch(v),'top_layer_lit_LCh':lch(t),'p75_98_LCh':lch(p),
              'dE00_vs_sku_lit':round(float(de00(v[None],sku[None])[0]),2),'dL_vs_sku':round(float(v[0]-SKU_LCH[0]),2),
              'top_layer_dE00_vs_sku':round(float(de00(t[None],sku[None])[0]),2),
              'hp_std_L_sigma8':round(hpstd(im),3),
              'clipped_any_channel_ge254_pct_of_opaque':round(100*float((im[...,:3][im[...,3]>=230]>=254).any(-1).mean()),3),
              'all_channels_ge254_px':int(((im[...,:3]>=254).all(-1)&(im[...,3]>=230)).sum())}
out['texture_hp_std_change_pct']=round(100*(out['fixed']['hp_std_L_sigma8']/out['nano_test_before']['hp_std_L_sigma8']-1),2)
win={'L':(89,95),'C':(3,9),'h':(70,100)}
L,C,h=out['fixed']['lit_p90_99_LCh']; out['window_pass']={'L':win['L'][0]<=L<=win['L'][1],'C':win['C'][0]<=C<=win['C'][1],'h':win['h'][0]<=h<=win['h'][1],'dL_le_6':abs(out['fixed']['dL_vs_sku'])<=6,'dE00_le_3_GIMG':out['fixed']['dE00_vs_sku_lit']<=3}
print(json.dumps(out,indent=1))
