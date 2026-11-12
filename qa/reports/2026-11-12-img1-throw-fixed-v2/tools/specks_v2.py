# Specks (ours only): (1) detached components of alpha>0 in the final 1638x2048 and the fullres; (2) what the v2 speck step zeroed:
# the canvas before that step is rebuilt from the fullres with the tool's own resize code (fix_throw_nano_v2.py step 4) and diffed.
import sys, json, numpy as np, cv2
from PIL import Image
A=sys.argv[1].rstrip('/')+'/'
fin=np.array(Image.open(A+'p2-nano-fixed-v2.png').convert('RGBA')); full=np.array(Image.open(A+'p2-nano-fixed-v2-fullres.png').convert('RGBA'))
def detached(al,thr=0):
    n,l,s,_=cv2.connectedComponentsWithStats((al>thr).astype(np.uint8),8); main=1+np.argmax(s[1:,4])
    d=[{'px':int(s[i,4]),'max_alpha':int(al[l==i].max()),'xy':[int(s[i,0]),int(s[i,1])]} for i in range(1,n) if i!=main]
    return {'components':len(d),'max_alpha':max([c['max_alpha'] for c in d],default=0),'alpha_ge_8':sum(c['max_alpha']>=8 for c in d),'px':sum(c['px'] for c in d),'list_first10':d[:10]}
out={'final_alpha_gt_0':detached(fin[...,3]),'final_alpha_ge_6':detached(fin[...,3],5),'fullres_alpha_gt_0':detached(full[...,3]),'fullres_alpha_gt_8':detached(full[...,3],8)}
# rebuild the pre-speck canvas
a8=full[...,3]; ys,xs=np.where(a8>8); bb=(int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1)
prod=Image.fromarray(full,'RGBA').crop(bb); pw,ph=prod.size; s=min(0.8*1638/pw,0.8*2048/ph)
f=np.array(prod).astype(np.float32)/255; pm=np.dstack([f[...,:3]*f[...,3:4],f[...,3:4]])
p=Image.fromarray((pm*255+0.5).astype(np.uint8),'RGBA').resize((round(pw*s),round(ph*s)),Image.LANCZOS)
b=np.array(p).astype(np.float32)/255; al=b[...,3:4]; rgb=np.where(al>1e-4,b[...,:3]/np.maximum(al,1e-4),0)
p2=Image.fromarray((np.dstack([rgb.clip(0,1),al])*255+0.5).astype(np.uint8),'RGBA')
can=Image.new('RGBA',(1638,2048),(0,0,0,0)); can.paste(p2,((1638-p2.width)//2,(2048-p2.height)//2)); pre=np.array(can)
z=(pre[...,3]>0)&(fin[...,3]==0); other=(pre!=fin).any(-1)&~z
n,l,st,_=cv2.connectedComponentsWithStats(z.astype(np.uint8),8)
main=(fin[...,3]>0).astype(np.uint8); dmain=cv2.distanceTransform(1-main,cv2.DIST_L2,3)
comps=[{'px':int(st[i,4]),'max_alpha':int(pre[...,3][l==i].max()),'dist_to_body_px':round(float(dmain[l==i].min()),1)} for i in range(1,n)]
out['zeroed_by_speck_step']={'px':int(z.sum()),'components':len(comps),'max_alpha':max(c['max_alpha'] for c in comps) if comps else 0,
   'components_alpha_ge_8':sum(c['max_alpha']>=8 for c in comps),'sum_alpha_255':int(pre[...,3][z].sum()),
   'dist_to_body_p50_max':[float(np.median([c['dist_to_body_px'] for c in comps])),max(c['dist_to_body_px'] for c in comps)] if comps else None,
   'other_px_differing_from_rebuilt_canvas':int(other.sum())}
print(json.dumps(out,indent=1))
