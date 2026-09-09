"""Saved-file checks for the eight v16 changes."""
import bpy,math,json,ast
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/blender/CPO_v16_refined.blend'))
main=bpy.context.scene;loop=bpy.data.scenes.get('CPO_V16_DRIVE_LOOP') or bpy.data.scenes['CPO_V15_DRIVE_LOOP']
old=main.frame_current;chain=[];o=main.camera
while o:chain.append(o);o=o.parent
qa=bpy.data.scenes.new('V16 QA');mapping={}
for o in reversed(chain):
 n=o.copy();qa.collection.objects.link(n);n.parent=mapping.get(o.parent);n.matrix_parent_inverse=o.matrix_parent_inverse.copy();n.matrix_basis=o.matrix_basis.copy();mapping[o]=n
for n in mapping.values():
 if n.animation_data:
  for fc in n.animation_data.drivers:
   ast.parse(fc.driver.expression,mode='eval')
   assert len(fc.driver.expression)<240
   for variable in fc.driver.variables:
    for target in variable.targets:
     if target.id in mapping:target.id=mapping[target.id]
bpy.context.window.scene=qa;cam=mapping[main.camera];poses=[]
for f in range(2701):
 qa.frame_set(f);poses.append((cam.matrix_world.translation.copy(),cam.matrix_world.to_quaternion().normalized()))
steps=[]
for f in range(1,2701):
 a,aq=poses[f-1];b,bq=poses[f];steps.append({'frame':f,'metres':(b-a).length,'degrees':math.degrees(2*math.acos(min(1,abs(aq.dot(bq)))))})
substeps=[];previous=None
for k in range(1200*8,1520*8+1):
 f=k/8;qa.frame_set(int(f),subframe=f-int(f));q=cam.matrix_world.to_quaternion().normalized()
 if previous:substeps.append(math.degrees(2*math.acos(min(1,abs(previous.dot(q))))))
 previous=q
bpy.context.window.scene=main;main.frame_set(old)
for n in mapping.values():bpy.data.objects.remove(n,do_unlink=True)
bpy.data.scenes.remove(qa)
def reachable(col,seen=None):
 seen=set() if seen is None else seen
 if col in seen:return set()
 seen.add(col);result=set(col.objects)
 for child in col.children:result.update(reachable(child,seen))
 for o in col.objects:
  if o.instance_collection:result.update(reachable(o.instance_collection,seen))
 return result
loop_objects=reachable(loop.collection)
contamination=[o.name for o in loop_objects if o.name.startswith(('EXT.','F01.','F02.','F03.','F04.','F05.','F06.','F07.')) or (o.type=='FONT' and 'CAR PRODUCE' in o.data.body.upper())]
assert not contamination,contamination
tile=bpy.data.collections['V15_CITY_256M_MODULE'];campaigns={int(o['campaign_id']) for o in tile.objects if not o.hide_render and 'campaign_id' in o}
missing=[im.name for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not im.packed_files]
assert not missing,missing
assert max(p['degrees'] for p in steps)<3
assert max(substeps)<.5
base=bpy.data.objects['CPO_BASE_CAMERA_v13'];fcs=[fc for layer in base.animation_data.action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves if fc.data_path=='rotation_quaternion']
fcs.sort(key=lambda fc:fc.array_index);values=[[fc.keyframe_points[i].co.y for fc in fcs] for i in range(len(fcs[0].keyframe_points))]
assert min(sum(a*b for a,b in zip(values[i-1],values[i])) for i in range(1,len(values)))>0
report={'camera_max_rotation_deg_frame':max(p['degrees'] for p in steps),'camera_max_subframe_rotation_deg':max(substeps),'camera_1323':steps[1322],'camera_1323_world_position':list(poses[1323][0]),'camera_hold_departure_displacement_m':(poses[1341][0]-poses[1296][0]).length,'loop_company_objects':contamination,'loop_reachable_objects':len(loop_objects),'campaign_ids':sorted(campaigns),'missing_images':missing,'setback_m':main.get('V16_store_setback_m'),'idle_gain':main.camera.get('V16_idle_gain'),'scope':'Camera poses and subframes, shared resource dependency graph, image packing, advertisement identity; not exhaustive scene collision proof.'}
assert campaigns==set(range(1,17)),campaigns
magazines=[bpy.data.objects['V14 Printed cover '+str(i)] for i in range(8)]
report['magazine_materials']=[o.data.materials[0].name for o in magazines]
assert len(set(report['magazine_materials']))==8
report['shared_pavement_material']=bpy.data.objects['V16 continuous frontage paving'].data.materials[0].name
assert report['shared_pavement_material']=='V15 granite pedestrian paving'
report['ambient_light_ratio']={name:bpy.data.objects[name].data.energy/bpy.data.objects[name]['V16_previous_energy'] for name in ['V14 Shop ceiling bounce','V14 Front window blue bounce','V14 Office ambient']}
assert all(abs(v-.87)<.0001 for v in report['ambient_light_ratio'].values())
report['invalid_camera_drivers']=[d.data_path for d in main.camera.animation_data.drivers if not d.is_valid]
assert not report['invalid_camera_drivers']
(ROOT/'docs/v16-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('V16_VALIDATED',json.dumps(report),flush=True)
