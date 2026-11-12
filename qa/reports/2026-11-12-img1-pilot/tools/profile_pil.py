import sys, json
from PIL import Image
# width profile of an RGBA cut (alpha>=128), pure PIL
f=sys.argv[1]; im=Image.open(f).convert('RGBA'); a=im.getchannel('A').point(lambda v:255 if v>=128 else 0)
bb=a.getbbox(); x0,y0,x1,y1=bb; H=y1-y0
ws=[]
for y in range(y0,y1):
    r=a.crop((0,y,a.width,y+1)).getbbox()
    ws.append((r[2]-r[0]) if r else 0)
D=max(ws); yD=ws.index(D)
top=max(ws[:max(1,int(0.04*H))])
prof=[round(ws[int(p*(H-1))]/D,3) for p in [i/10 for i in range(11)]]
print(json.dumps({'file':f.split('/')[-1],'bbox':bb,'H':H,'D':D,'H_over_D':round(H/D,3),'shoulder_frac':round(yD/H,3),'mouth_over_D':round(top/D,3),'foot_over_D':round(max(ws[-max(1,int(0.01*H)):])/D,3),'profile':prof}))
