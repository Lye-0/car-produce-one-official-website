import bpy,json,math,sys,hashlib,bmesh
from pathlib import Path
from mathutils import Matrix,Vector
R=Path(__file__).resolve().parents[3];O=R/'output/junction-work-v4'
candidate='--candidate' in sys.argv
source=O/'CPO_JUNCTION_CANDIDATE.blend' if candidate else R/'scene/CPO_MASTER.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.data.scenes['CPO_JUNCTION_DRIVE'];bpy.context.window.scene=s;s.frame_set(0);bpy.context.view_layer.update()
rig=bpy.data.objects['JT.Vehicle path'];fixed=[o for o in bpy.data.objects if o.name.startswith('JT.') and o!=rig and o.parent!=rig and o.type!='CAMERA']
assert all(not o.animation_data for o in fixed),'Animated scenery remains'
base={o.name:o.matrix_world.copy() for o in fixed}
cam=bpy.data.objects[s['JT_camera_desktop']];relative=rig.matrix_world.inverted()@cam.matrix_world
fixed_error=0;relative_error=0
for frame in [0,150,300,450,600,720,810,900,990,1080]:
 s.frame_set(frame);bpy.context.view_layer.update()
 for o in fixed:fixed_error=max(fixed_error,max(abs(o.matrix_world[i][j]-base[o.name][i][j]) for i in range(4) for j in range(4)))
 m=rig.matrix_world.inverted()@cam.matrix_world;relative_error=max(relative_error,max(abs(m[i][j]-relative[i][j]) for i in range(4) for j in range(4)))
assert fixed_error<1e-6 and relative_error<2e-5,(fixed_error,relative_error)
end_error=max(abs(rig.matrix_world[i][j]-Matrix.Identity(4)[i][j]) for i in range(4) for j in range(4));assert end_error<1e-4
path=json.loads((O/'junction-path.json').read_text());poses=path['poses'];headings=[p['heading'] for p in poses]
assert all(b<=a+1e-7 for a,b in zip(headings,headings[1:]));assert abs(headings[0]-headings[-1]-math.pi/2)<1e-6
max_step=max(abs(b-a) for a,b in zip(headings,headings[1:]));assert max_step<math.radians(1)
# Conservative clearance: subtract a 2.8 m envelope around the whole car.
s.frame_set(0);bpy.context.view_layer.update();rects=[]
for inst in bpy.context.evaluated_depsgraph_get().object_instances:
 ob=inst.object
 if ob.hide_render or ob.type!='MESH' or not any(k in ob.name.lower() for k in ['tower','podium','building','jt.frontage.','jt.ground.','jt.streetlife.']):continue
 pts=[inst.matrix_world@Vector(v) for v in ob.bound_box];lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
 if lo[2]>2 or hi[2]<2 or hi[0]<-130 or lo[0]>-20 or hi[1]<-240 or lo[1]>40:continue
 rects.append((ob.name,lo,hi))
assert rects
minimum=1e9;closest=None
for pose in poses[::3]:
 x,y,_=pose['position']
 for name,lo,hi in rects:
  distance=math.hypot(max(lo[0]-x,0,x-hi[0]),max(lo[1]-y,0,y-hi[1]))-2.8
  if distance<minimum:minimum=distance;closest={'object':name,'frame':pose['f'],'position':pose['position']}
assert minimum>3,(minimum,closest)
families=sorted({o.get('JT_frontage_family') for o in s.objects if o.get('JT_frontage_family')})
assert len(families)==6,families
report={'passed':True,'fixed_scene_objects':len(fixed),'fixed_world_transform_max_delta':fixed_error,'camera_relative_to_vehicle_max_delta':relative_error,'arrival_pose_max_error':end_error,'turn_degrees':90,'max_heading_step_degrees':math.degrees(max_step),'minimum_building_clearance_conservative_m':minimum,'closest_building':closest,'loop_seconds':20,'turn_seconds':16,'curve_speed_mps':path['turnSpeed'],'street_frontage_groups':families,'cycle_length_m':160}
report['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
ground=[o for o in s.objects if o.type=='MESH' and o.name.startswith('JT.Ground.') and 'shop glazing' not in o.name]
assert len(ground)>50,len(ground)
for ob in ground:
 bm=bmesh.new();bm.from_mesh(ob.data);closed=all(e.is_manifold for e in bm.edges);bm.free();assert closed,ob.name
foundations=[o for o in ground if 'foundation' in o.name]
assert len(foundations)>=6
for ob in foundations:
 points=[ob.matrix_world@Vector(v) for v in ob.bound_box]
 assert min(p.z for p in points)<-.14 and max(p.z for p in points)>=0,ob.name
advertisements=[o for o in s.objects if o.get('JT_advertisement')]
rear=next(c for c in s.collection.children if 'JT_backdrop_buildings' in c)
report['closed_ground_meshes']=len(ground);report['grounded_foundations']=len(foundations);report['additional_advertisements_per_district']=len(advertisements);report['background_buildings_per_district']=len(json.loads(rear['JT_backdrop_buildings']))
assert len(advertisements)>=9
accepted=O.parent/'junction-work-v2/junction-path.json'
if accepted.exists():
 old=json.loads(accepted.read_text())['poses'];assert len(old)==len(poses)
 delta=max(math.dist(a['position'],b['position']) for a,b in zip(old,poses));angle=max(abs(a['heading']-b['heading']) for a,b in zip(old,poses))
 assert math.dist(old[-1]['position'],poses[-1]['position'])<1e-6
 report['previous_motion_position_delta_m']=delta;report['previous_motion_heading_delta_radians']=angle
lane=path['laneCenterX'];assert abs(lane-(path['roadCenterX']-2.6))<1e-5
assert all(abs(p['position'][0]-lane)<1e-5 for p in poses[:601])
report['left_lane_offset_m']=2.6
district=next(c for c in s.collection.children if 'JT_street_level_uses' in c)
report['street_level_uses']=district['JT_street_level_uses'];report['street_trees']=district['JT_added_street_trees'];report['parked_cars']=district['JT_added_parked_cars'];report['new_campaigns']=district['JT_new_campaigns']
target=O/'junction-scene-validation.json' if candidate else R/'reports/history/junction-scene-validation.json'
target.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
