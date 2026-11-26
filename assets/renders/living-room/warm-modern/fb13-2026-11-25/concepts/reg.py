import sys, json
import numpy as np, cv2
from PIL import Image
SP=sys.argv[1]
g=cv2.cvtColor(np.asarray(Image.open(SP+'/out/guide-A.png').convert('RGB')),cv2.COLOR_RGB2GRAY)
r=cv2.cvtColor(np.asarray(Image.open(SP+'/dl/A-r1.jpg').convert('RGB')),cv2.COLOR_RGB2GRAY)
g=cv2.resize(g,(1344,756),interpolation=cv2.INTER_AREA)   # 1920x1080 -> 1344 wide (16:9 = 756 high)
sift=cv2.SIFT_create(6000)
k1,d1=sift.detectAndCompute(g,None); k2,d2=sift.detectAndCompute(r,None)
m=cv2.BFMatcher().knnMatch(d1,d2,k=2)
good=[a for a,b in m if a.distance<0.8*b.distance]
p1=np.float32([k1[a.queryIdx].pt for a in good]); p2=np.float32([k2[a.trainIdx].pt for a in good])
print('kp',len(k1),len(k2),'good',len(good))
A,inl=cv2.estimateAffine2D(p1,p2,method=cv2.RANSAC,ransacReprojThreshold=6.0,maxIters=20000)
print('affine',A.round(4).tolist(),'inliers',int(inl.sum()))
Hm,inl2=cv2.findHomography(p1,p2,cv2.RANSAC,6.0,maxIters=20000)
print('homography',Hm.round(5).tolist(),'inliers',int(inl2.sum()))
pi=p1[inl2.ravel()>0]
print('inlier spread x',pi[:,0].min(),pi[:,0].max(),'y',pi[:,1].min(),pi[:,1].max())
# regional: where are inliers
for name,(x0,y0,x1,y1) in dict(art=(620,220,1030,420),sofa=(480,440,1110,660),table=(520,600,1000,756),lamp=(1040,260,1220,700),olive=(330,180,520,680),left=(0,300,330,756),pendant=(630,0,850,150)).items():
    sel=(pi[:,0]>x0)&(pi[:,0]<x1)&(pi[:,1]>y0)&(pi[:,1]<y1); print(name,int(sel.sum()))
json.dump(dict(affine=A.tolist(),homography=Hm.tolist(),guide_scaled=[1344,756]),open(SP+'/out/reg-A.json','w'))
# check overlay: warp guide to r1 frame, edges
w=cv2.warpPerspective(g,Hm,(1344,768))
ov=np.dstack([r, (0.5*r+0.5*w).astype(np.uint8), w])
Image.fromarray(ov).save(SP+'/out/reg-check.jpg',quality=85)
