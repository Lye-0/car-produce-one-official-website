"""Compare the delivered rest layout with v12, allowing only four agreed group moves."""
from pathlib import Path
import json,sys,numpy as np
from scipy.spatial.transform import Rotation
from glb_edit import GLB
ROOT=Path(__file__).resolve().parents[1]
base=GLB(sys.argv[1] if len(sys.argv)>1 else '/mnt/data/CAR_PRODUCE_ONE_v12/CAR_PRODUCE_ONE_INTERIOR_EXTERIOR_v12.glb')
g=GLB(ROOT/'CAR_PRODUCE_ONE_ANIMATED_v13.glb')
def matrix(self,i):
 n=self.j['nodes'][i]
 if 'matrix'in n:return np.array(n['matrix']).reshape(4,4,order='F')
 m=np.eye(4);m[:3,:3]=Rotation.from_quat(n.get('rotation',[0,0,0,1])).as_matrix()@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0]);return m
GLB.matrix=matrix
manifest=json.loads((ROOT/'animation/timeline.json').read_text(encoding='utf-8'));offsets={}
for name,delta in manifest['furniture_moves'].items():
 for i in list(base.descendants(base.ids[name]))+[base.ids[name]]:offsets[base.j['nodes'][i]['name']]=np.array(delta)
bad=[];fixed=0;moved=0;matbad=[]
for i,n in enumerate(base.j['nodes']):
 if 'mesh'not in n:continue
 k=g.ids[n['name']];expected=base.world(i).copy();delta=offsets.get(n['name'])
 if delta is not None:expected[:3,3]+=delta;moved+=1
 else:fixed+=1
 if not np.allclose(expected,g.world(k),atol=1e-6):bad.append(n['name'])
 if n['name']!='COUNTER.TargetPC.Screen':
  p=base.j['meshes'][n['mesh']]['primitives'];q=g.j['meshes'][g.j['nodes'][k]['mesh']]['primitives']
  for a,b in zip(p,q):
   if base.j['materials'][a['material']]!=g.j['materials'][b['material']]:matbad.append(n['name'])
r={'unchanged_rest_positions':fixed,'authorised_moved_meshes':moved,'unexpected_transform_changes':bad,'unexpected_material_changes_except_screen':matbad,'all_original_binary_bytes_retained':bytes(g.data[:len(base.data)])==bytes(base.data),'all_passed':not bad and not matbad}
(ROOT/'source/preservation_report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
