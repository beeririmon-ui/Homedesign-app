import json,glob,os,subprocess,sys
from PIL import Image
SK=sys.argv[1]
ids="curtains-aliexpress-cotton-linen-curtain-look-902882 framed-art-aliexpress-japandi-bare-branch-70x100-776445 wall-decor-aliexpress-natural-raffia-woven-bohemian-763597 accent-sconces-aliexpress-indoor-stone-wall-lamp vase-cj-textured-white-stoneware rug-cj-braided-wool-natural floor-lamp-aliexpress-wabi-sabi-japan-floor-217361 planter-cj-seagrass-belly sofa-cover-cj-cotton-muslin-fringe cushions-cj-boucle-teddy cushions-cj-knitted-chenille-bean-green cushions-cj-linen-look-charcoal basket-cj-jute-rope-cylinder magazine-holder-cj-felt-log-basket table-runner-cj-linen-look-sage-fringe bowl-cj-speckled-ivory-wide-bowl-21 candle-holders-cj-travertine-pedestal pouf-cj-cotton-knit-ball-cover pendant-cj-pleated-pumpkin-lantern-40 coffee-table-idana-javorina-olia-natural pool-cj-travertine-organic-tray-24 wall-sconce-cj-black-swing-arm-fabric".split()
out={}
for i in ids:
    c=json.load(open(glob.glob(f'data/products/**/{i}.json',recursive=True)[0]))
    urls=(c.get('images') or {}).get('urls',[])
    # prefer the in-room SKU image if the card names one
    sku_img=[s.get('image') for s in (c.get('options') or {}).get('skus',[]) if isinstance(s,dict) and s.get('in_room') and s.get('image')]
    cand=(sku_img[:1]+urls)[:3]
    out[i]=[]
    for n,u in enumerate(cand):
        p=os.path.join(SK,f'{i}__{n}.img')
        r=subprocess.run(['curl','-s','-m','25','-o',p,'-w','%{http_code}',u],capture_output=True,text=True)
        try:
            im=Image.open(p); im.load(); im.convert('RGB').save(p[:-4]+'.jpg',quality=90); os.remove(p)
            out[i].append(dict(url=u,file=os.path.basename(p[:-4]+'.jpg'),px=im.size))
        except Exception as e:
            if os.path.exists(p): os.remove(p)
json.dump(out,open(os.path.join(SK,'index.json'),'w'),indent=1)
print({k:len(v) for k,v in out.items()})
