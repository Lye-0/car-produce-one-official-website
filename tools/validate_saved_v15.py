"""Read-only validation of the saved v15 file, including frontage placement."""
import bpy,json,runpy,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/blender/CPO_v15_refined.blend'))
scene=bpy.context.scene;scene.frame_set(0);bpy.context.view_layer.update()
assert scene.name=='CPO_V15_MAIN',scene.name
assert scene.camera.name=='CPO_CINEMATIC_CAMERA'
assert 'CPO_V15_DRIVE_LOOP' in bpy.data.scenes
missing=[im.name for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not im.packed_files]
assert not missing,missing
tile=bpy.data.collections['V15_CITY_256M_MODULE'];assert tile.get('V15_frontage_fixed')
overlaps=[]
for o in tile.objects:
    if o.hide_render or o.type!='MESH' or 'pavement' not in o.name:continue
    p=[o.matrix_world@Vector(v) for v in o.bound_box];lo=[min(v[i] for v in p) for i in range(3)];hi=[max(v[i] for v in p) for i in range(3)]
    if hi[0]>.0 and lo[0]<10.5 and hi[1]>-1.49 and lo[1]<3.8:overlaps.append({'name':o.name,'min':lo,'max':hi})
assert not overlaps,overlaps
for i in [0,1,2]:assert bpy.data.objects['V15 traffic vehicle '+str(i)].location.y<=-5.8
bad=[o.name for o in bpy.data.objects if o.animation_data and any(not d.is_valid for d in o.animation_data.drivers)]
assert not bad,bad
camera=runpy.run_path(str(ROOT/'tools/assemble_v15.py'))['validate_camera']()
report={'file':str(ROOT/'assets/blender/CPO_v15_refined.blend'),'blender':bpy.app.version_string,'main_scene':scene.name,'loop_scene':'CPO_V15_DRIVE_LOOP','packed_image_count':len([im for im in bpy.data.images if im.source=='FILE']),'missing_images':missing,'invalid_drivers':bad,'city_pavement_overlaps_shop':overlaps,'near_traffic_y':{str(i):bpy.data.objects['V15 traffic vehicle '+str(i)].location.y for i in [0,1,2]},'camera_max_step_deg':camera['largest_rotation_steps'][0]['rotation_deg'],'scope':'Resource checks, camera samples, conservative vehicle boxes and targeted frontage checks; not an exhaustive continuous collision audit.'}
(ROOT/'docs/v15-saved-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('V15_SAVED_FILE_VALIDATED',json.dumps(report),flush=True)
