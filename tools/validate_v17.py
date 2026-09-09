import bpy,math,json,ast
from pathlib import Path
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
def sample(version):
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'assets/blender/CPO_v{version}_refined.blend'));main=bpy.context.scene;chain=[];o=main.camera
 while o:chain.append(o);o=o.parent
 qa=bpy.data.scenes.new('V17 validation');mapping={}
 for o in reversed(chain):
  n=o.copy();qa.collection.objects.link(n);n.parent=mapping.get(o.parent);n.matrix_parent_inverse=o.matrix_parent_inverse.copy();n.matrix_basis=o.matrix_basis.copy();mapping[o]=n
 for n in mapping.values():
  if n.animation_data:
   for fc in n.animation_data.drivers:
    ast.parse(fc.driver.expression,mode='eval')
    for v in fc.driver.variables:
     for t in v.targets:
      if t.id in mapping:t.id=mapping[t.id]
 bpy.context.window.scene=qa;cam=mapping[main.camera];poses=[]
 for f in range(2701):
  qa.frame_set(f);m=cam.matrix_world;q=m.to_quaternion().normalized();look=q@Vector((0,0,-1));poses.append({'route':list(mapping[bpy.data.objects['CPO_BASE_CAMERA_v13']].matrix_world.translation),'p':list(m.translation),'q':list(q),'yaw':math.atan2(look.y,look.x),'pitch':math.asin(max(-1,min(1,look.z)))})
 fine=[]
 for i in range(2300*8,2350*8+1):
  f=i/8;qa.frame_set(int(f),subframe=f-int(f));look=cam.matrix_world.to_quaternion()@Vector((0,0,-1));fine.append([math.atan2(look.y,look.x),math.asin(max(-1,min(1,look.z)))])
 bpy.context.window.scene=main
 for n in mapping.values():bpy.data.objects.remove(n,do_unlink=True)
 bpy.data.scenes.remove(qa)
 return poses,np.array(fine)
before,bfine=sample(16);after,afine=sample(17)
def stats(fine):
 yaw=np.unwrap(fine[:,0]);pitch=fine[:,1];return {'yaw_reversal_steps':int(np.sum(np.diff(yaw)>math.radians(.005))),'max_up_down_step_deg':float(np.degrees(abs(np.diff(pitch))).max()),'signed_yaw_step_range_deg':[float(v) for v in np.degrees([np.diff(yaw).min(),np.diff(yaw).max()])]}
oldstats,newstats=stats(bfine),stats(afine)
assert newstats['yaw_reversal_steps']==0,newstats
assert newstats['max_up_down_step_deg']<.03,newstats
outside=list(range(2025))+list(range(2431,2701))
dist=max(np.linalg.norm(np.array(before[i]['route'])-after[i]['route']) for i in range(2701))
qdot=min(abs(np.dot(before[i]['q'],after[i]['q'])) for i in outside)
assert dist<.0001,dist
assert qdot>.99999,qdot
g=bpy.data.objects['CPO_REAR_TURN_GAZE'];assert not g.animation_data or not g.animation_data.action
ads=[o for o in bpy.data.collections['V15_CITY_256M_MODULE'].objects if not o.hide_render and 'campaign_id' in o]
assert set(int(o['campaign_id']) for o in ads)==set(range(1,17))
report={'scope':'Signed world camera direction sampled every eighth frame between 2300 and 2350; all route positions and rotations outside 2025..2430 compared to v16.','before':oldstats,'after':newstats,'max_route_position_difference_m':float(dist),'minimum_unchanged_orientation_absolute_dot':float(qdot),'advertisements':len(ads),'unique_campaigns':16,'additive_gaze_action':False}
(ROOT/'docs/v17-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('V17_VALIDATED',json.dumps(report),flush=True)
