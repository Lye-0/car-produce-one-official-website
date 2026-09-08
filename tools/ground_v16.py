"""Connect the shop's side paving and give the urban plots a ground plane."""
import bpy,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def apply():
    m=runpy.run_path(str(ROOT/'tools/city_v15.py'));h=m['h'];h.COL=bpy.data.collections['V15_CITY_256M_MODULE']
    if bpy.data.objects.get('V16_LOT_GROUND'):return
    p=h.obj('V16_LOT_GROUND',None);stone=bpy.data.materials['V15 granite pedestrian paving']
    h.box('V16 north urban ground',(0,29,-.13),(256,53.7,.10),stone,p,0)
    h.box('V16 south urban ground',(0,-36,-.13),(256,40,.10),stone,p,0)
    for a,b in [(-2.9,-.10),(10.60,12.60)]:
        h.box('V16 shop side shared paving',((a+b)/2,8.0,-.05),(b-a,11.7,.10),stone,p,.005)
    print('V16_SIDE_GROUND_CONNECTED',flush=True)
if __name__=='__main__':apply()
