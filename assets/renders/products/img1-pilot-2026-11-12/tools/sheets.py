import os
import sys; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import json, numpy as np
from PIL import Image
from colorlib import *
SP=os.environ['IMG1_WORK'].rstrip('/')+'/'
GRAY=(128,128,128); H=640; GAP=16; SW=256
def tile(path, mode, scale=None):
    im=Image.open(SP+'cut/'+path).convert('RGBA')
    if path.endswith('patch.png'):
        im.putalpha(255)
    arr=np.array(im)
    if mode=='lum':
        lab=srgb_to_lab(arr[...,:3]); lab[...,1]=0; lab[...,2]=0
        arr=np.dstack([lab_to_srgb(lab),arr[...,3]])
    im=Image.fromarray(arr,'RGBA')
    if scale is None: scale=H/im.height
    return im.resize((round(im.width*scale),round(im.height*scale)),Image.LANCZOS)
def lum_match(t, target_L):
    arr=np.array(t); lab=srgb_to_lab(arr[...,:3]); m=arr[...,3]>=230
    med=np.median(lab[...,0][m]); lab[...,0]=np.clip(lab[...,0]+(target_L-med),0,100)
    return Image.fromarray(np.dstack([lab_to_srgb(lab),arr[...,3]]),'RGBA')
def build(name, r1, details, scales=()):
    r1im=Image.open(SP+'cut/'+r1).convert('RGBA'); a1=np.array(r1im)
    lit,n=lit_side(a1,90,99); med_all=np.median(srgb_to_lab(a1[...,:3])[a1[...,3]>=230][:,0])
    tiles=[tile(r1,'colour')]
    s1=H/r1im.height
    for d,f in zip(details,scales): tiles.append(lum_match(tile(d,'lum',s1*f),med_all))
    sw=Image.new('RGBA',(SW,SW),tuple(int(v) for v in lab_to_srgb(np.array(lit)))+(255,))
    W=GAP+sum(t.width+GAP for t in tiles)+SW+GAP; Ht=H+2*GAP
    sheet=Image.new('RGB',(W,Ht),GRAY); x=GAP
    for t in tiles: sheet.paste(t,(x,GAP+(H-t.height)//2),t); x+=t.width+GAP
    sheet.paste(sw,(x,GAP+(H-SW)//2)); sheet.save(SP+f'sheets/{name}.png')
    return {'sheet':f'sheets/{name}.png','size':list(sheet.size),'r1_lit_lab':[round(float(v),2) for v in lit],'r1_lit_lch':lch(lit),'r1_lit_px':n,'swatch_rgb':[int(v) for v in lab_to_srgb(np.array(lit))],'r1_median_L':round(float(med_all),2)}
out={}
out['throw']=build('throw-white',  'throw-r1-u0.png', ['throw-r2-u2.png','throw-r3-u4.png'], scales=(5.0/11.0, 5.0/6.2))
out['vase']=build('vase-large',    'vase-r1-u4.png',  ['vase-r2-u2.png','vase-r3-u1-patch.png'], scales=((549/32)/(392/32), (549/32)/(400/26.5)))
out['lamp']=build('lamp-16',       'lamp-r1-u9.png',  ['lamp-r2-u0-end.png'], scales=((150/6.5)/(80/6.5),))
out['pecan']=build('throw-pecan',  'pecan-sku.png',   [])
json.dump(out,open(SP+'sheets/sheets.json','w'),indent=1); print(json.dumps(out,indent=1))
# our empty palette and empty transparent canvas
Image.new('RGB',(1638,2048),(0xF4,0xF1,0xEC)).save(SP+'sheets/palette-F4F1EC-1638x2048.png')
Image.new('RGBA',(1638,2048),(0,0,0,0)).save(SP+'sheets/canvas-transparent-1638x2048.png')
