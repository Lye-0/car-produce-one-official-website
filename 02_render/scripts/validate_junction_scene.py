import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
R=Path(__file__).resolve().parents[1];O=R/'output/junction-work'
bpy.ops.wm.open_mainfile(filepath=str(R/'scene/CPO_MASTER.blend'))
s=bpy.data.scenes['CPO_JUNCTION_DRIVE'];bpy.context.window.scene=s;s.frame_set(0);bpy.context.view_layer.update()
rig=bpy.data.objects['JT.Vehicle path'];fixed=[o for o in bpy.data.objects if o.name.startswith('JT.') and o!=rig and o.parent!=rig and o.type!='CAMERA']
assert all(not o.animation_data for o in fixed),'Animated scenery remains'
base={o.name:o.matrix_world.copy() for o in fixed}
cam=bpy.data.objects[s['JT_camera_desktop']];relative=rig.matrix_world.inverted()@cam.matrix_world
fixed_error=0;relative_error=0
for frame in [0,150,300,420,510,600,690,780]:
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
 if ob.type!='MESH' or not any(k in ob.name.lower() for k in ['tower','podium','building']):continue
 pts=[inst.matrix_world@Vector(v) for v in ob.bound_box];lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
 if lo[2]>2 or hi[2]<2 or hi[0]<-130 or lo[0]>-20 or hi[1]<-160 or lo[1]>40:continue
 rects.append((ob.name,lo,hi))
assert rects
minimum=1e9;closest=None
for pose in poses[::3]:
 x,y,_=pose['position']
 for name,lo,hi in rects:
  distance=math.hypot(max(lo[0]-x,0,x-hi[0]),max(lo[1]-y,0,y-hi[1]))-2.8
  if distance<minimum:minimum=distance;closest={'object':name,'frame':pose['f'],'position':pose['position']}
assert minimum>3,(minimum,closest)
report={'passed':True,'fixed_scene_objects':len(fixed),'fixed_world_transform_max_delta':fixed_error,'camera_relative_to_vehicle_max_delta':relative_error,'arrival_pose_max_error':end_error,'turn_degrees':90,'max_heading_step_degrees':math.degrees(max_step),'minimum_building_clearance_conservative_m':minimum,'closest_building':closest,'loop_seconds':10,'turn_seconds':16,'curve_speed_mps':path['turnSpeed']}
(R/'reports/junction-scene-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
