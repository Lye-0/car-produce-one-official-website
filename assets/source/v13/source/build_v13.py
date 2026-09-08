"""Build the complete, editable animated CPO scene from v12. No image generation.
Python 3.11+, numpy, scipy, shapely, trimesh, Pillow. See README_JA.txt.
"""
from pathlib import Path
import sys,math,json,copy,hashlib
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from scipy.interpolate import PchipInterpolator, CubicHermiteSpline
import trimesh
from PIL import Image,ImageDraw
from glb_edit import GLB,T
import geometry_tools as h
from vehicles import make_car
BASE=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/mnt/data/CAR_PRODUCE_ONE_v12/CAR_PRODUCE_ONE_INTERIOR_EXTERIOR_v12.glb')
OUT=Path(__file__).resolve().parents[1]
for sub in ['animation','previews','web']: (OUT/sub).mkdir(exist_ok=True)
g=GLB(BASE); base_count=len(g.j['nodes']);h.setup(g)
# A source-frame transform evaluator with quaternion support, unlike the older static helper.
def matrix(self,i):
 n=self.j['nodes'][i]
 if 'matrix' in n:return np.array(n['matrix']).reshape(4,4,order='F')
 m=np.eye(4);m[:3,:3]=Rotation.from_quat(n.get('rotation',[0,0,0,1])).as_matrix()@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0]);return m
GLB.matrix=matrix
base_root=1
# Movable furniture identified in the accepted route study. No large furniture / walls changed.
moves={'F05.RollingStool.0':[-.605,0,0],'F05.RollingStool.1':[-.605,0,0],'05f_Rear_Side_Unit_And_Basket':[-.15,0,0],'07d_End_Utility_Cabinet':[1.254,-1.692,0]}
for name,off in moves.items():
 i=g.ids[name];m=g.matrix(i);m[:3,3]+=off;g.j['nodes'][i]['matrix']=m.flatten(order='F').tolist();g.j['nodes'][i].pop('translation',None)
# The white stool is photographed inside the desk; retain it, do not remove.
vehicles_root=h.group('90_VEHICLES',1)
pre,_,_,_=make_car('PRELUDE_SHOWROOM',vehicles_root)
vez,_,_,_=make_car('VEZEL_SHOWROOM',vehicles_root,suv=True)
g.j['nodes'][pre]['translation']=[1.5,1.31,0];g.j['nodes'][vez]['translation']=[8.9,1.22,0]
drive,wheels,door,hinge=make_car('ARRIVAL_CAR',vehicles_root,cabin=True)
# Editable pivot parenting with localised child transforms. Preserve visible rest geometry.
def pivot_rebase(group,origin):
 old=g.matrix(group)
 parent_world=g.world(g.parent[group])
 origin=(np.linalg.inv(parent_world)@np.r_[origin,1])[:3]
 for c in g.j['nodes'][group].get('children',[]):
  m=old@g.matrix(c);m[:3,3]-=origin;g.j['nodes'][c]['matrix']=m.flatten(order='F').tolist()
  for key in ['rotation','translation','scale']:g.j['nodes'][c].pop(key,None)
 g.j['nodes'][group].pop('matrix',None)
 g.j['nodes'][group]['translation']=list(origin)
pivot_rebase(door,np.array(hinge))
for wi,p in wheels:pivot_rebase(wi,np.array(p))
# City: independently editable near-future corridor; periodic set dressing is not the actual shop.
city=h.group('91_NIGHT_CITY',1)
loopcity=h.group('CITY_PERIODIC_STREET',city)
asphalt=h.material('CITY.Asphalt',(.020,.027,.036),.36,.14)
stone=h.material('CITY.Paving',(.085,.105,.122),.58,.05)
metal=h.material('CITY.GraphiteMetal',(.028,.041,.057),.32,.62)
cyan=h.material('CITY.CyanLight',(.15,.48,.62),.25,.1,(.15,.7,1))
amber=h.material('CITY.WarmLight',(.72,.39,.15),.35,.05,(1,.55,.24))
blue=h.material('CITY.BlueLight',(.095,.2,.48),.3,.1,(.12,.3,.82))
window=h.material('CITY.GlassFacade',(.025,.07,.105),.16,.58)
windowsoft=h.material('CITY.WindowWarm',(.18,.20,.21),.35,.15,(.23,.30,.34))
h.transformed_box('CITY.GroundBase',(0,12,-.38),(420,190,.30),asphalt,city,bevel=.001)
h.transformed_box('CITY.Road',(0,-8.5,-.16),(420,13,.10),asphalt,city,bevel=.001)
for yy in [-16.3,3.8]:
 # Omit the shop's existing lot from the added sidewalk.
 for xx,ll in [(-114,172),(115,162)]:h.transformed_box(f'CITY.Sidewalk{yy}_{xx}',(xx,yy,-.12),(ll,4,.20),stone,city,bevel=.002)
for xx in range(-195,191,8):
 h.transformed_box(f'CITY.LaneMark{xx}',(xx,-8.4,-.103),(3.3,.055,.003),windowsoft,loopcity,bevel=.0005)
# Many building windows combined per building, not thousands of individual scene nodes.
for bi,xx in enumerate(list(range(-184,185,16))):
 for si,yy in enumerate([-23,18]):
  rng=np.random.default_rng(220+(bi%2)*7+si);ht=float(rng.choice([13,18,22,28]));ww=float(rng.choice([9,11,12]));dd=10
  grp=h.group(f'CITY.Block{bi:02d}_{si}',loopcity)
  h.transformed_box(f'CITY.Tower{bi}_{si}',(xx,yy,ht/2-.1),(ww,dd,ht),metal,grp,bevel=.055)
  h.transformed_box(f'CITY.Crown{bi}_{si}',(xx,yy,ht+.1),(ww+.2,dd+.2,.22),metal,grp,bevel=.03)
  faces=[];emfaces=[]
  fronty=yy+(dd/2+.015 if yy<0 else -dd/2-.015)
  for floor in np.arange(1.5,ht-1,2.5):
   for sx in np.arange(-ww/2+.65,ww/2-.4,1.35):
    m=trimesh.creation.box(extents=(.81,.025,1.22));m.apply_translation((xx+sx,fronty,floor));(emfaces if rng.random()<.64 else faces).append(m)
  if faces:h.mesh(f'CITY.DarkWindows{bi}_{si}',trimesh.util.concatenate(faces),window,grp)
  if emfaces:h.mesh(f'CITY.LitWindows{bi}_{si}',trimesh.util.concatenate(emfaces),windowsoft if si else amber,grp)
  for sx in [-ww/2+.1,ww/2-.1]:h.transformed_box(f'CITY.LightEdge{bi}_{si}_{sx}',(xx+sx,fronty,ht/2),(.023,.03,ht-.2),cyan if bi%3 else blue,grp,bevel=.004)
  h.transformed_box(f'CITY.EntranceLintel{bi}_{si}',(xx,fronty,2.8),(ww*.8,.13,.028),amber,grp,bevel=.004)
# Taller skyline farther away.
for k in range(28):
 rng=np.random.default_rng(k+80);xx=float(rng.uniform(-120,130));yy=float(rng.choice([-1,1]))*float(rng.uniform(42,72));ht=float(rng.uniform(25,70));ww=float(rng.uniform(6,13))
 h.transformed_box(f'CITY.Skyline{k}',(xx,yy,ht/2),(ww,ww*.8,ht),metal,city,bevel=.08)
 h.transformed_box(f'CITY.SkylineLine{k}',(xx,yy-ww*.41,ht*.7),(.04,.04,ht*.58),blue,city,bevel=.005)
# Light portals over the distant avenue and street light posts.
for xx in [-72,-40,40,72,104]:
 for yy in [-15.5,-1.1]:
  if -5<xx<16 and yy>-8:continue
  # Shop-side lamps remain fixed; a captured idle offset must never put a lamp inside the store.
  lamp_parent=city if yy>-8 else loopcity
  h.cyl(f'CITY.LampPost{xx}_{yy}',(xx,yy,0),(xx,yy,5.2),.05,metal,lamp_parent,n=12)
  h.pipe(f'CITY.LampArm{xx}_{yy}',[(xx,yy,5.2),(xx,yy+(1.1 if yy< -8 else -1.1),5.2)],.04,metal,lamp_parent,n=10)
  h.transformed_box(f'CITY.LampGlow{xx}_{yy}',(xx,yy+(1.1 if yy< -8 else -1.1),5.16),(.26,.70,.027),cyan,lamp_parent,bevel=.01)
for xx in [-54,64]:
 for yy in [-17,1.5]:h.transformed_box(f'CITY.PortalPost{xx}_{yy}',(xx,yy,7.1),(.45,.45,14.4),metal,loopcity,bevel=.05)
 h.transformed_box(f'CITY.Portal{xx}',(xx,-7.75,14.2),(.5,19.1,.4),metal,loopcity,bevel=.05)
 h.transformed_box(f'CITY.PortalLight{xx}',(xx,-7.75,13.975),(.04,18.5,.023),blue,loopcity,bevel=.003)
# Put the drive car on the actual road plane.
rz=Rotation.from_euler('z',90,degrees=True).as_quat().tolist()
g.j['nodes'][drive]['translation']=[-48,-5.65,-.10];g.j['nodes'][drive]['rotation']=rz
# Two existing first panels: fold inwards as one coupled accordion, not disappear.
gate1=g.ids['F01.Bay_R.Leaf_01'];gate2=g.ids['F01.Bay_R.Leaf_02']
g1p=np.array([5.230,-1.488,0.0]);g2p=np.array([6.042,-1.488,0.0]);pivot_rebase(gate1,g1p);pivot_rebase(gate2,g2p)
# Camera and meaningful route references (invisible transform-only nodes).
camroot=h.group('92_CAMERA_AND_ROUTE',1)
ci=len(g.j.setdefault('cameras',[]));g.j['cameras'].append({'name':'CPO_CINEMATIC_CAMERA','type':'perspective','perspective':{'yfov':math.radians(46),'znear':.012,'zfar':450}})
cn=h.group('CPO_CINEMATIC_CAMERA',camroot);g.j['nodes'][cn]['camera']=ci
# Camera coordinate: glTF -Z forward/+Y up, expressed in the source Z-up world under root conversion.
def lookquat(eye,target):
 f=np.array(target,float)-eye;f/=np.linalg.norm(f);rr=np.cross(f,[0,0,1]);rr/=np.linalg.norm(rr);uu=np.cross(rr,f)
 return Rotation.from_matrix(np.column_stack([rr,uu,-f])).as_quat()
def smooth(u):u=np.clip(u,0,1);return u*u*(3-2*u)
def drive_x(p):u=np.clip(p/.14,0,1);return -48+52.95*(1-(1-u)**2)
# Piecewise paths use PCHIP on axes to avoid spline overshoot into furniture at corners.
# Explicit zero-speed ends provide smooth entry/exit to each hold; intermediate key points carry the route.
def path_segment(keys,ps):
 tt=np.array([k[0] for k in keys]);pp=np.array([k[1] for k in keys]);t0,t1=tt[0],tt[-1]
 # Time-warped PCHIP; only at segment ends (holds) velocity falls to zero.
 res=PchipInterpolator(tt,pp,axis=0)(np.clip(ps,t0,t1))
 return res
# XYZ source coordinates; camera maintains eye height until magazine detail and final screen approach.
walkkeys=[(.14,[5,-5.23,.99]),(.157,[5,-5.23,.99]),(.17,[5,-4.90,1.00]),(.188,[5,-4.10,1.06]),(.203,[5,-3.45,1.55]),(.22,[5.4,-2.55,1.585]),(.24,[6.1,-2.25,1.585]),(.26,[6.1,-.80,1.60]),(.295,[6.3,1.2,1.60]),(.34,[7.0,2.7,1.60]),(.38,[7.1,3.4,1.60])]
toolskeys=[(.48,[7.1,3.4,1.60]),(.504,[6.80,3.74,1.60]),(.527,[6.3,3.95,1.6]),(.552,[4.35,4.10,1.6]),(.577,[2.5,4.15,1.6]),(.591,[1.84,4.18,1.6]),(.607,[1.84,4.85,1.57]),(.63,[1.84,5.70,1.48])]
rearkeys=[(.75,[1.84,5.70,1.48]),(.777,[1.84,6.60,1.60]),(.794,[1.84,7.16,1.60]),(.810,[1.91,7.40,1.60]),(.825,[2.18,7.53,1.60]),(.840,[2.40,7.53,1.60]),(.864,[2.90,7.50,1.60]),(.88,[3.13,7.28,1.60]),(.90,[3.11,6.60,1.58])]
center=np.array([2.381034374,6.655703545,1.361953139]);normal=np.array([.965925826,-.258819045,0])
end=center+normal*.275
pckeys=[(.90,[3.11,6.6,1.58]),(.930,(center+normal*.62+np.array([0,0,.065])).tolist()),(.970,(center+normal*.36).tolist()),(1.,end.tolist())]
# Per-stage position with eased endpoints, sample at 30 fps.
def ease_path(keys,p):
 a,b=keys[0][0],keys[-1][0];u=(p-a)/(b-a)
 # Endpoint ease over 13% of stage; keep bulk travel approximately constant.
 e=.13
 if u<e:u=e*(2*(u/e)**2-(u/e)**3)
 elif u>1-e:u=1-e*(2*((1-u)/e)**2-((1-u)/e)**3)
 return path_segment(keys,a+u*(b-a))
def eye_at(p):
 if p<=.14:return np.array([drive_x(p)+.05,-5.23,.99])
 if p<.38:return ease_path(walkkeys,p)
 if p<=.48:return np.array([7.1,3.4,1.6])
 if p<.63:return ease_path(toolskeys,p)
 if p<=.75:return np.array([1.84,5.70,1.48])
 if p<.90:return ease_path(rearkeys,p)
 return ease_path(pckeys,p)
# Authored orientation anchors. Quaternion interpolation, not Euler wrapping or point-by-point look-at snap.
orientation=[(0,[1.0,.10,.035]),(.105,[1,.10,.035]),(.14,[.9,.35,.04]),(.164,[.04,1,-.015]),(.194,[.04,1,.1]),(.225,[.16,1,.04]),(.247,[.05,1,0]),(.295,[.26,1,0]),(.355,[.16,1,.075]),(.38,[.23,1.60,-.18]),(.48,[.23,1.60,-.18]),(.514,[-1,.16,-.035]),(.56,[-1,.02,0]),(.587,[-.35,.94,-.01]),(.607,[-.12,1,-.12]),(.63,[-.74,.40,-.746]),(.75,[-.74,.40,-.746]),(.777,[0,1,0]),(.808,[.40,.92,0]),(.837,[1,.1,0]),(.865,[.4,-1,0]),(.90,(center-np.array([3.11,6.6,1.58])).tolist()),(.93,(-normal-np.array([0,0,.06])).tolist()),(.97,(-normal).tolist()),(1.,(-normal).tolist())]
qtimes=np.array([a for a,b in orientation]);qquats=np.array([lookquat(np.zeros(3),b) for a,b in orientation])
qslerp=Slerp(qtimes,Rotation.from_quat(qquats))
def quat_at(p):
 k=np.clip(np.searchsorted(qtimes,p)-1,0,len(qtimes)-2);a,b=qtimes[k:k+2];qtime=a+smooth((p-a)/(b-a))*(b-a);return qslerp([qtime]).as_quat()[0]
times=np.linspace(0,90,2701);ps=times/90;eyes=np.array([eye_at(p) for p in ps]);quats=np.array([quat_at(p) for p in ps])
for k in range(1,len(quats)):
 if quats[k]@quats[k-1]<0:quats[k]*=-1
# GLB animation accessors must not declare a vertex buffer target.
def aacc(data,typ):
 i=g.addacc(data,typ,target=34962);g.j['bufferViews'][g.j['accessors'][i]['bufferView']].pop('target',None);return i
clips=[]
def clip(name):
 c={'name':name,'samplers':[],'channels':[],'extras':{'duration_seconds':90,'fps':30}};clips.append(c);return c
def track(c,node,path,ts,values,interp='LINEAR'):
 ai=aacc(np.asarray(ts)[:,None],'SCALAR');vi=aacc(values,'VEC4' if path=='rotation' else 'VEC3');si=len(c['samplers']);c['samplers'].append({'input':ai,'output':vi,'interpolation':interp});c['channels'].append({'sampler':si,'target':{'node':node,'path':path}})
main=clip('CPO_MASTER_90s');track(main,cn,'translation',times,eyes);track(main,cn,'rotation',times,quats)
g.j['nodes'][cn]['translation']=eyes[0].tolist();g.j['nodes'][cn]['rotation']=quats[0].tolist()
carpositions=np.c_[[drive_x(p) for p in ps],np.full(len(ps),-5.65),np.full(len(ps),-.10)];track(main,drive,'translation',times,carpositions)
# Passenger door safely opens before lateral exit, closes after the camera is on sidewalk.
def door_angle(p):return -math.radians(80)*smooth((p-.142)/.017)*(1-smooth((p-.213)/.026))
doorq=Rotation.from_euler('z',np.array([door_angle(p) for p in ps])[:,None]).as_quat();track(main,door,'rotation',times,doorq)
# Wheel spin follows exact translational distance, no skidding start/stop in master.
for wi,pos in wheels:
 angles=(carpositions[:,0]-carpositions[0,0])/.327
 track(main,wi,'rotation',times,Rotation.from_euler('x',angles[:,None]).as_quat())
def gate_angle(p):return math.radians(88)*smooth((p-.212)/.03)*(1-smooth((p-.313)/.037))
aa=np.array([gate_angle(p) for p in ps]);track(main,gate1,'rotation',times,Rotation.from_euler('z',aa[:,None]).as_quat());track(main,gate2,'rotation',times,Rotation.from_euler('z',-aa[:,None]).as_quat())
p2=np.tile(g1p,(len(ps),1))+np.c_[.812*np.cos(aa),.812*np.sin(aa),np.zeros(len(ps))]; pw=np.linalg.inv(g.world(g.parent[gate2]));p2=p2@pw[:3,:3].T+pw[:3,3];track(main,gate2,'translation',times,p2)
# Real-time loop scenery; current phase is retained by the web player at main start.
loop=clip('CPO_IDLE_CITY_LOOP');loopdur=32/(2*52.95/12.6);loop['extras']['duration_seconds']=loopdur
track(loop,loopcity,'translation',[0,loopdur],[[0,0,0],[-32,0,0]])
# Ambient motion for inspection; muted by reduced-motion preference in preview.
# Finish screen remains separate, usable by native web or Blender image replacement.
screen=g.ids['COUNTER.TargetPC.Screen'];mi=g.j['meshes'][g.j['nodes'][screen]['mesh']]['primitives'][0]['material']
im=Image.new('RGB',(1600,900),(11,15,19));d=ImageDraw.Draw(im)
d.line((100,120,1500,120),fill=(83,111,127),width=2)
d.text((100,180),'CAR',font=h.font(98,True),fill=(226,231,231));d.text((100,280),'PRODUCE ONE',font=h.font(115,True),fill=(226,231,231));d.text((105,477),'AUTOMOTIVE  /  SERVICE & CARE',font=h.font(28),fill=(136,158,169));d.text((105,724),'THE JOURNEY CONTINUES.',font=h.font(20),fill=(146,159,166));d.line((100,688,1500,688),fill=(61,80,90),width=2)
im.save(OUT/'web/screen.png');newmat=h.texture_material('CPO.Screen.WebHandoff',im,.75,0);g.j['materials'][newmat]['emissiveFactor']=[.25,.25,.25];g.j['materials'][newmat]['emissiveTexture']=copy.deepcopy(g.j['materials'][newmat]['pbrMetallicRoughness']['baseColorTexture']);g.j['meshes'][g.j['nodes'][screen]['mesh']]['primitives'][0]['material']=newmat
# Cinematic warm lights added separately; original lighting settings untouched.
lightsroot=h.group('93_CINEMATIC_LIGHTING',1)
def point(name,p,color,intensity,range_=7):
 li=len(g.j.setdefault('extensions',{}).setdefault('KHR_lights_punctual',{}).setdefault('lights',[]));g.j['extensions']['KHR_lights_punctual']['lights'].append({'name':name,'type':'point','color':color,'intensity':intensity,'range':range_});ni=h.group(name,lightsroot);g.j['nodes'][ni].update(translation=list(p),extensions={'KHR_lights_punctual':{'light':li}})
for k,p in enumerate([(2.4,1.7,2.76),(8.3,1.7,2.76),(6.8,4.0,2.70),(1.5,6.2,2.65),(3.1,6.8,2.69)]):point(f'CINE.WarmFill{k}',p,[1,.76,.53],90,6)
for k,p in enumerate([(5,-3.2,4.9),(-42,-4.9,6),(38,-5.7,6)]):point(f'CINE.Street{k}',p,[.4,.65,1],150,15)
g.j['animations']=clips
g.j['nodes'][1]['extras'].update(revision='v13',notes='Complete continuous animated camera journey. Photo-guided approximate cars. No passengers or people meshes.',approved_layout_unchanged=False)
# Route reference empties, no visible lines in final render.
for name,xyz in [('ANCHOR_TOOLS',[7.1,3.4,1.6]),('ANCHOR_MAGAZINES',[1.84,5.70,1.48]),('ANCHOR_PC',center),('ANCHOR_ENTRY',[6.1,-1.5,1.60])]:ni=h.group(name,camroot);g.j['nodes'][ni]['translation']=list(xyz)
g.j['asset']['extras']={'v13':'Edited from v12; manufactured models are approximations; dynamic city not survey geometry.'}
g.save(OUT/'CAR_PRODUCE_ONE_ANIMATED_v13.glb')
# Correct generator name from legacy writer without rewriting binary.
p=OUT/'CAR_PRODUCE_ONE_ANIMATED_v13.glb';raw=p.read_bytes();import struct
jl=struct.unpack_from('<I',raw,12)[0];jj=json.loads(raw[20:20+jl]);jj['asset']['generator']='CAR PRODUCE ONE v13 / animated end-to-end cinematic reconstruction';bb=raw[28+jl:];jb=json.dumps(jj,ensure_ascii=False,separators=(',',':')).encode();jb+=b' '*(-len(jb)%4);p.write_bytes(struct.pack('<III',0x46546c67,2,28+len(jb)+len(bb))+struct.pack('<II',len(jb),0x4e4f534a)+jb+struct.pack('<II',len(bb),0x004e4942)+bb)
manifest={'version':'13','base_sha256':g.sha,'source_frame':'X right; +Y shop interior; +Z up. GLB retains root Y-up conversion.','duration':90,'fps':30,'frames':2701,'camera':'CPO_CINEMATIC_CAMERA','main_clip':'CPO_MASTER_90s','idle_clip':'CPO_IDLE_CITY_LOOP','idle_period':loopdur,'fov_degrees':46,'near':.012,'vehicles':[{'name':'PRELUDE_SHOWROOM','center':[1.5,1.31,0],'dimensions':[1.88,4.52,1.355],'paint':'custom dark blue','quality':'original photo-guided approximate mesh, not Honda CAD'},{'name':'VEZEL_SHOWROOM','center':[8.9,1.22,0],'dimensions':[1.79,4.34,1.59],'paint':'black','quality':'original photo-guided approximate mesh, not Honda CAD'}],'furniture_moves':moves,'screen':{'node':'COUNTER.TargetPC.Screen','center':center.tolist(),'normal':normal.tolist(),'final_eye':end.tolist(),'handoff_start':.965},'segments':[{'id':'ARRIVAL','range':[0,.14],'title':'夜の都市から到着'},{'id':'EXIT','range':[.14,.24],'title':'降車して店舗へ'},{'id':'ENTER','range':[.24,.38],'title':'入店・工具台へ'},{'id':'TOOLS','range':[.38,.48],'title':'工具台・固定'},{'id':'CROSS','range':[.48,.63],'title':'ガラス机へ移動'},{'id':'MAGAZINES','range':[.63,.75],'title':'雑誌・固定'},{'id':'LOOP','range':[.75,.90],'title':'デスク奥を回り込む'},{'id':'PC','range':[.90,.97],'title':'PCへ接近'},{'id':'HANDOFF','range':[.97,1],'title':'静かなサイトへ'}],'route_keys':walkkeys+toolskeys+rearkeys+pckeys,'limitations':['Cars are procedural visual approximations, not exact manufacturer surfaces.','Screen/HTML handoff and idle-to-main phase retention are player logic outside glTF core.','Materials and lighting in dependency-free WebGL review renderer are simplified.','Full Blender application execution is not available in authoring container.']}
(OUT/'animation/timeline.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));np.savez_compressed(OUT/'animation/camera_samples.npz',time=times,source_position=eyes,source_quaternion=quats)
(OUT/'source/build_manifest.json').write_text(json.dumps({'base_nodes':base_count,'node_count':len(g.j['nodes']),'mesh_nodes':sum('mesh'in n for n in g.j['nodes']),'animation_tracks':len(main['channels']),'size_bytes':p.stat().st_size},indent=2))
print('BUILT',p,p.stat().st_size,flush=True)
