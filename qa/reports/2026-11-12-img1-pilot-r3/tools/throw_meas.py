import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab, lch, de00
D=sys.argv[2]
fin=np.array(Image.open(D+'/sofa-cover-cj-cotton-muslin-fringe/p2-nano-test.png').convert('RGBA')).astype(np.float64)
raw=np.array(Image.open(D+'/raw/p2-throw-nano-test-raw.png').convert('RGB')).astype(np.float64)
nob=np.array(Image.open(D+'/raw/p2-throw-nano-test-nobg.png').convert('RGBA')).astype(np.float64)
pal=np.array(Image.open(D+'/bases/palette-F4F1EC-1638x2048.png').convert('RGB')).astype(np.float64)
out={}
out['palette_unique']=np.unique(pal.reshape(-1,3),axis=0).tolist()[:3]
def lit(rgb,mask):
    lab=srgb_to_lab(rgb[mask]); L=lab[:,0]
    p90,p99=np.percentile(L,[90,99]); s=(L>=p90)&(L<=p99)
    p75,p98=np.percentile(L,[75,98]); s2=(L>=p75)&(L<=p98)
    return {'p90_99':lch(np.median(lab[s],0)),'p75_98':lch(np.median(lab[s2],0)),'median_all':lch(np.median(lab,0)),'L_p50':round(float(np.median(L)),2)}
a=fin[...,3]/255; m=a>=0.9
out['final_lit']=lit(fin[...,:3],m)
an=nob[...,3]/255; mn=an>=0.9
out['nobg_lit']=lit(nob[...,:3],mn)
out['raw_lit_under_nobg_mask']=lit(raw,mn)
# raw paper: pixels far from the product (alpha==0 dilated away) 
far=cv2.erode((an<0.01).astype(np.uint8),np.ones((61,61),np.uint8)).astype(bool)
pl=srgb_to_lab(raw[far]); out['raw_paper']={'px':int(far.sum()),'median_rgb':np.median(raw[far],0).tolist(),'lab_median':lch(np.median(pl,0)),'L_p5_p95':[round(float(x),2) for x in np.percentile(pl[:,0],[5,95])]}
out['palette_lab']=lch(srgb_to_lab(np.array([0xF4,0xF1,0xEC],float)))
out['card_hex_EEE8DD']=lch(srgb_to_lab(np.array([0xEE,0xE8,0xDD],float)))
out['card_hex_E2D9CB']=lch(srgb_to_lab(np.array([0xE2,0xD9,0xCB],float)))
# top-layer lit side: exclude bottom stack band and right fringe band: use central region of the product bbox
ys,xs=np.nonzero(m); y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
out['final_bbox_a09']=[int(x0),int(y0),int(x1),int(y1)]
top=np.zeros_like(m); top[y0+int(0.05*(y1-y0)):y0+int(0.80*(y1-y0)), x0+int(0.03*(x1-x0)):x0+int(0.80*(x1-x0))]=True
out['final_toplayer_lit']=lit(fin[...,:3],m&top)
# left half vs right half of top layer (light direction)
L=srgb_to_lab(fin[...,:3])[...,0]
xm=(x0+x1)//2
out['L_left_right_toplayer_median']=[round(float(np.median(L[m&top&(np.arange(fin.shape[1])[None,:]<xm)])),2),round(float(np.median(L[m&top&(np.arange(fin.shape[1])[None,:]>=xm)])),2)]
# alpha stats
O=(a>=0.5).astype(np.uint8)
n,lbl,st,_=cv2.connectedComponentsWithStats(O,8)
out['components_ge_0.5']=sorted([int(st[i,4]) for i in range(1,n)],reverse=True)[:8]
inner=cv2.erode(O,np.ones((15,15),np.uint8)).astype(bool)
out['interior_alpha']={'p0.1':float(np.percentile(fin[...,3][inner],0.1)),'p1':float(np.percentile(fin[...,3][inner],1)),'p50':float(np.median(fin[...,3][inner])),'frac_lt_255':round(float((fin[...,3][inner]<255).mean()),5)}
out['alpha_border_max']=int(max(fin[0,:,3].max(),fin[-1,:,3].max(),fin[:,0,3].max(),fin[:,-1,3].max()))
hist=np.histogram(fin[...,3],bins=[0,1,26,128,230,255,256])[0].tolist(); out['alpha_hist_0_1-25_26-127_128-229_230-254_255']=hist
print(json.dumps(out,indent=1))
