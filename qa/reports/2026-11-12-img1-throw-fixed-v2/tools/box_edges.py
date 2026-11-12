# Artefacts at the edges of the v2 top-corner box (ours only): (1) step in the top silhouette at the box's left edge (x~1488):
# y of the alpha-0.5 top contour per column, v1 vs v2; (2) soft band (0.1 < alpha < 0.9) area and its width at the box's lower edge,
# v1 vs v2; (3) alpha of v2 vs v1 in the ghost areas. Raw coordinates.
import sys, json, numpy as np
from PIL import Image
A=sys.argv[1].rstrip('/')+'/'
v1=np.array(Image.open(A+'p2-nano-fixed-fullres.png'))[...,3]/255.; v2=np.array(Image.open(A+'p2-nano-fixed-v2-fullres.png'))[...,3]/255.
def topy(a,x): c=np.nonzero(a[340:470,x]>=0.5)[0]; return int(c.min())+340 if len(c) else None
out={'top_contour_y_per_x':{str(x):[topy(v1,x),topy(v2,x)] for x in range(1470,1512,2)}}
dy=[(topy(v2,x)-topy(v1,x)) for x in range(1440,1600) if topy(v1,x) is not None and topy(v2,x) is not None]
out['top_edge_shift_v2_minus_v1_px']={'x1440-1487':[int(min(dy[:48])),int(max(dy[:48]))],'x1488-1599':[int(min(dy[48:])),int(max(dy[48:]))]}
# largest jump of the v2 top contour between neighbouring columns near the box edge vs elsewhere
ty=[topy(v2,x) for x in range(1440,1600)]; jumps=[abs(ty[i+1]-ty[i]) for i in range(len(ty)-1) if ty[i] is not None and ty[i+1] is not None]
ty1=[topy(v1,x) for x in range(1440,1600)]; j1=[abs(ty1[i+1]-ty1[i]) for i in range(len(ty1)-1) if ty1[i] is not None and ty1[i+1] is not None]
out['top_contour_max_column_jump_px']={'v1':int(max(j1)),'v2':int(max(jumps)),'v2_at_x':1440+int(np.argmax(jumps))}
for nm,(y0,y1,x0,x1) in {'box_top_edge_y360-395_x1470-1600':(360,395,1470,1600),'box_bottom_edge_y535-580_x1540-1620':(535,580,1540,1620)}.items():
    s=(slice(y0,y1),slice(x0,x1))
    soft1=((v1[s]>0.1)&(v1[s]<0.9)); soft2=((v2[s]>0.1)&(v2[s]<0.9))
    out[nm]={'soft_px_v1':int(soft1.sum()),'soft_px_v2':int(soft2.sum()),
             'soft_width_per_row_p50_v1_v2':[float(np.median(soft1.sum(1))),float(np.median(soft2.sum(1)))],
             'px_where_v2_alpha_lower_by_gt_0.3':int((v2[s]<v1[s]-0.3).sum()),'px_where_v2_alpha_higher_by_gt_0.1':int((v2[s]>v1[s]+0.1).sum())}
print(json.dumps(out,indent=1))
