"""Independent structural/preservation/path validation. Run against the written GLB."""
from pathlib import Path
import sys,json,copy,hashlib,io,math
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from shapely.geometry import MultiPoint,Point,LineString,box
from shapely.strtree import STRtree
from shapely.ops import unary_union
from PIL import Image
import trimesh
from glb_edit import GLB
OUT=Path(__file__).resolve().parents[1]
base=GLB(sys.argv[1] if len(sys.argv)>1 else '/mnt/data/CAR_PRODUCE_ONE_v12/CAR_PRODUCE_ONE_INTERIOR_EXTERIOR_v12.glb');g=GLB(OUT/'CAR_PRODUCE_ONE_ANIMATED_v13.glb')
def matrix(self,i):
 n=self.j['nodes'][i]
 if 'matrix' in n:return np.array(n['matrix']).reshape(4,4,order='F')
 m=np.eye(4);m[:3,:3]=Rotation.from_quat(n.get('rotation',[0,0,0,1])).as_matrix()@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0]);return m
GLB.matrix=matrix
j=g.j;tests=[]
def check(name,condition,detail=None):tests.append({'name':name,'passed':bool(condition),'detail':detail})
check('Has actual perspective camera',any(c['type']=='perspective' for c in j['cameras']))
check('Master and idle clips present',{a['name'] for a in j['animations']}=={'CPO_MASTER_90s','CPO_IDLE_CITY_LOOP'})
for ci,clip in enumerate(j['animations']):
 for k,ch in enumerate(clip['channels']):
  sam=clip['samplers'][ch['sampler']];tt=g.acc(sam['input']).ravel();vv=g.acc(sam['output']);node=j['nodes'][ch['target']['node']]
  check(f'Clip {ci} track {k} time/values',len(tt)==len(vv) and np.isfinite(vv).all() and np.all(np.diff(tt)>0))
  check(f'Clip {ci} track {k} TRS target','matrix' not in node)
  if ch['target']['path']=='rotation':check(f'Clip {ci} track {k} unit quaternions',np.allclose(np.linalg.norm(vv,axis=1),1,atol=2e-6))
check('Explicit valid texture samplers',all(isinstance(t.get('sampler'),int) and t['sampler']<len(j.get('samplers',[])) for t in j['textures']))
# Decode all embedded images independently.
image_ok=0
for im in j['images']:
 v=j['bufferViews'][im['bufferView']]
 try:Image.open(io.BytesIO(g.data[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']])).verify();image_ok+=1
 except Exception:pass
check('All embedded images decode',image_ok==len(j['images']),image_ok)
# Immutable geometry (animation and explicit furniture translations are allowed).
unchanged=0;changed=[]
for i,n in enumerate(base.j['nodes']):
 if 'mesh' not in n:continue
 ni=g.ids[n['name']];n2=j['nodes'][ni]
 if 'mesh' not in n2:changed.append(n['name']+' REMOVED');continue
 p=base.j['meshes'][n['mesh']]['primitives'];q=j['meshes'][n2['mesh']]['primitives']
 same=len(p)==len(q)
 if same:
  for p1,p2 in zip(p,q):
   same &= all(np.array_equal(base.acc(ai),g.acc(p2['attributes'][key])) for key,ai in p1['attributes'].items())
   same &= np.array_equal(base.acc(p1['indices']),g.acc(p2['indices']))
 if same:unchanged+=1
 else:changed.append(n['name'])
check('All original mesh vertex/normal/UV/index data preserved',not changed,{'preserved_meshes':unchanged,'changed':changed})
# Camera target sampler extracts independent of source build functions.
clip=j['animations'][0];channels={ (j['nodes'][c['target']['node']]['name'],c['target']['path']):c for c in clip['channels']}
ch=channels[('CPO_CINEMATIC_CAMERA','translation')];s=clip['samplers'][ch['sampler']];times=g.acc(s['input']).ravel();eyes=g.acc(s['output']);p=times/90
qch=channels[('CPO_CINEMATIC_CAMERA','rotation')];qq=g.acc(clip['samplers'][qch['sampler']]['output']);frw=Rotation.from_quat(qq).apply([0,0,-1])
for a,b,name in [(.38,.48,'tools'),(.63,.75,'magazines')]:
 ids=np.flatnonzero((p>=a+1e-6)&(p<=b-1e-6));check(name+' hold translation constant',np.max(np.ptp(eyes[ids],axis=0))<1e-5);check(name+' hold rotation constant',np.max(np.ptp(qq[ids],axis=0))<1e-5)
vel=np.linalg.norm(np.diff(eyes,axis=0),axis=1)*30
check('No position jump per frame',vel.max()<12,{'max_m_per_s':float(vel.max()),'at_s':float(times[np.argmax(vel)])})
check('Indoor walking max speed under 2.0 m/s',vel[(p[:-1]>.245)&(p[:-1]<.9)].max()<2,{'maximum':float(vel[(p[:-1]>.245)&(p[:-1]<.9)].max())})
# Snapshot at chosen time. Transforms applied recursively in source coordinates.
rest=copy.deepcopy(g.j['nodes']);trackdata=[]
for ch in clip['channels']:
 sa=clip['samplers'][ch['sampler']];trackdata.append((ch['target']['node'],ch['target']['path'],g.acc(sa['input']).ravel(),g.acc(sa['output'])))
def pose(t):
 for i,key,tt,vv in trackdata:
  if key=='rotation':val=Slerp(tt,Rotation.from_quat(vv))([min(float(tt[-1]),max(float(tt[0]),t))]).as_quat()[0]
  else:val=np.array([np.interp(t,tt,vv[:,k]) for k in range(vv.shape[1])])
  g.j['nodes'][i][key]=val.tolist()
# Plan obstacle polygons from actual written triangles, clipping to a human-height band.
# Openings must not be convex-hulled as a whole: walls are split into triangle projections.
animated_ids=set(c['target']['node'] for c in clip['channels'])
anim_desc=set(animated_ids)
for i in animated_ids:anim_desc.update(g.descendants(i))
pose(28.0)
polys=[];names=[]
for i,n in enumerate(g.j['nodes']):
 if 'mesh' not in n or i in anim_desc:continue
 name=n['name'];v=g.vertices(i)
 if v.size==0 or v[:,2].max()<.075 or v[:,2].min()>1.82:continue
 if v[:,0].max()<-.8 or v[:,0].min()>11.2 or v[:,1].max()<-3 or v[:,1].min()>9:continue
 # Casework/walls triangle projection union avoids overblocking windows and interior frame holes.
 faces=np.concatenate([g.acc(pr['indices']).reshape(-1,3) for pr in g.j['meshes'][n['mesh']]['primitives']])
 # all construction assets have one primitive; handle multimat below in a future extension.
 sel=v[(v[:,2]>.05)&(v[:,2]<1.83)]
 if len(sel)<3:
  # Tall vertical walls span band without any vertex inside it; retain XY footprint.
  if v[:,2].min()<.1 and v[:,2].max()>1.8:sel=v
  else:continue
 if name.startswith(('EXT.Portal','EXT.Ground','F01.Pier','F06.Wall','F03.Wall','F04.Wall','COUNTER.Top.')):
  # Project clipped triangles rather than filling door/window openings with one convex hull.
  projected=[]
  for tri in v[faces]:
   pts=list(tri)
   for cut,sign in [(.075,1),(1.82,-1)]:
    if not pts:break
    dest=[]
    for a,b in zip(pts,pts[1:]+pts[:1]):
     ina=sign*(a[2]-cut)>=0;inb=sign*(b[2]-cut)>=0
     if ina:dest.append(a)
     if ina!=inb:
      u=(cut-a[2])/(b[2]-a[2]);dest.append(a+(b-a)*u)
    pts=dest
   if len(pts)>=2:
    piece=MultiPoint(np.array(pts)[:,:2]).convex_hull
    if not piece.is_empty:projected.append(piece)
  poly=unary_union(projected)
 else:poly=MultiPoint(sel[:,:2]).convex_hull
 if poly.is_empty:continue
 polys.append(poly);names.append(name)
tree=STRtree(polys)
mins=[];viol=[]
for k in np.flatnonzero((p>=.245)&(p<=.900001)):
 xy=eyes[k,:2];pt=Point(xy);found=tree.query(pt.buffer(.9));dist=[(float(pt.distance(polys[ii])),int(ii)) for ii in found];dist.sort()
 if dist:
  d,ix=dist[0];mins.append((d,float(times[k]),names[ix]))
  if d<.274:viol.append((d,float(times[k]),names[ix],xy.tolist()))
check('Walking swept cylinder static-clearance (0.275m radius)',not viol,{'minimum':min(mins) if mins else None,'violations':viol[:12],'count':len(viol),'method':'Actual mesh vertex-height-band convex footprints, sampled camera every 1/30 sec. Conservative; does not replace continuous analytic collision proof.'})
# Door/gate/car dynamics: pose-dependent eye clearance and human proxy where upright.
dynamic_meshes=[i for i in anim_desc if 'mesh'in g.j['nodes'][i]]
dynviol=[];headmin=(999,None,None)
for k in range(0,len(times),3):
 if not(.13<=p[k]<=.36):continue
 pose(float(times[k]));eye=eyes[k];rr=.08 if p[k]<.21 else .25
 for i in dynamic_meshes:
  n=g.j['nodes'][i];v=g.vertices(i)
  if np.any(eye+rr<v.min(0)) or np.any(eye-rr>v.max(0)):continue
  # Nearest triangle distance, including door openings. Brute force candidate meshes only.
  verts=[];faces=[];off=0;tf=g.world(i)
  for pr in g.j['meshes'][n['mesh']]['primitives']:
   vs=g.acc(pr['attributes']['POSITION']);vs=vs@tf[:3,:3].T+tf[:3,3];ff=g.acc(pr['indices']).reshape(-1,3);verts.append(vs);faces.append(ff+off);off+=len(vs)
  m=trimesh.Trimesh(np.concatenate(verts),np.concatenate(faces),process=False)
  nearest,dd,idx=trimesh.proximity.closest_point_naive(m,[eye]);d=float(dd[0])
  if d<headmin[0]:headmin=(d,float(times[k]),n['name'])
  if d<rr:dynviol.append((d,float(times[k]),n['name']))
check('Moving geometry eye/sphere clearance',not dynviol,{'minimum':headmin,'violations':dynviol[:18],'count':len(dynviol),'sample_step_seconds':.1,'radius_exit':.08,'radius_upright':.25})
# Gate opening width at crossing, source X between folded set and third leaf.
pose(24.0)
fold=np.concatenate([g.vertices(i) for group in ['F01.Bay_R.Leaf_01','F01.Bay_R.Leaf_02'] for i in g.descendants(g.ids[group]) if 'mesh'in g.j['nodes'][i]])
third=np.concatenate([g.vertices(i) for i in g.descendants(g.ids['F01.Bay_R.Leaf_03']) if 'mesh'in g.j['nodes'][i]])
check('Entry opening wider than 0.9m',third[:,0].min()-fold[:,0].max()>.9,float(third[:,0].min()-fold[:,0].max()))
# Count and report full model load via independent library.
try:
 scene=trimesh.load_scene(OUT/'CAR_PRODUCE_ONE_ANIMATED_v13.glb',process=False)
 check('Independent trimesh GLB load',len(scene.graph.nodes_geometry)>3000,{'mesh_nodes':len(scene.graph.nodes_geometry),'geometries':len(scene.geometry)})
except Exception as e:check('Independent trimesh GLB load',False,str(e))
report={'file':'CAR_PRODUCE_ONE_ANIMATED_v13.glb','sha256':hashlib.sha256((OUT/'CAR_PRODUCE_ONE_ANIMATED_v13.glb').read_bytes()).hexdigest(),'base_sha256':base.sha,'tests':tests,'passed':sum(t['passed'] for t in tests),'failed':sum(not t['passed'] for t in tests),'limitations':['Blender application import/render not executed.','Proxy scan covers authored walk and eye clearance; does not certify real-world accessibility.','Vehicle surfacing is a visual approximation.']}
(OUT/'source/validation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'passed':report['passed'],'failed':[t for t in tests if not t['passed']]},indent=2),flush=True)
