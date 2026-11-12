# paper vs fabric chromaticity as a function of L* in the raw (our image only)
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, sys.argv[1]); from lab import srgb_to_lab
D=sys.argv[2].rstrip('/')+'/'
raw=np.array(Image.open(D+'raw/p2-throw-nano-test-raw.png').convert('RGB'))
a0=np.array(Image.open(D+'raw/p2-throw-nano-test-nobg.png'))[...,3]/255.
lab=srgb_to_lab(raw); L=lab[...,0]
paper=a0<0.01
# fabric for sure: alpha==1 eroded 25 px (far from any edge)
fab=cv2.erode((a0>0.99).astype(np.uint8),np.ones((51,51),np.uint8)).astype(bool)
out={}
for name,m in [('paper',paper),('fabric_interior',fab)]:
    rows=[]
    for lo in range(55,96,5):
        s=m&(L>=lo)&(L<lo+5)
        if s.sum()<50: continue
        v=lab[s]; C=np.hypot(v[:,1],v[:,2]); h=np.degrees(np.arctan2(v[:,2],v[:,1]))%360
        rows.append({'L':f'{lo}-{lo+5}','n':int(s.sum()),'a':round(float(np.median(v[:,1])),2),'b':round(float(np.median(v[:,2])),2),'C':round(float(np.median(C)),2),'h':round(float(np.median(h)),1)})
    out[name]=rows
print(json.dumps(out,indent=0))
