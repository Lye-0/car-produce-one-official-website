import bpy,json
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'scene/CPO_MASTER.blend'))
main=bpy.data.scenes['CPO_V18_SITE_MAIN'];corner=bpy.data.scenes['CPO_CORNER_CONNECTOR']
assert len(main.objects)==10522
assert len(bpy.data.scenes['CPO_V18_CITY_LOOP'].objects)==328
bpy.context.window.scene=main;main.frame_set(0);bpy.context.view_layer.update()
reference={p:bpy.data.objects['V18_'+p+'_Route'].matrix_world.copy() for p in ['desktop','mobile']}
car=bpy.data.objects['ARRIVAL_CAR'];names={'BC.'+o.name for o in [car,*car.children_recursive]}
body=[o for o in corner.objects if o.name in names]
bpy.context.window.scene=corner;corner.frame_set(0);bpy.context.view_layer.update();poses={o.name:o.matrix_world.copy() for o in body}
error=0;camera_error=0
for frame in [0,24,48,72,96]:
 corner.frame_set(frame);bpy.context.view_layer.update()
 for o in body:error=max(error,max(abs(o.matrix_world[i][j]-poses[o.name][i][j]) for i in range(4) for j in range(4)))
 for p in reference:
  cam=bpy.data.objects[corner['BC_camera_'+p]];camera_error=max(camera_error,max(abs(cam.matrix_world[i][j]-reference[p][i][j]) for i in range(4) for j in range(4)))
root_error=max(abs(bpy.data.objects['BC.Environment'].matrix_world[i][j]-Matrix.Identity(4)[i][j]) for i in range(4) for j in range(4))
assert error<1e-6 and camera_error<1e-6 and root_error<1e-5
assert not bpy.data.libraries
missing=[im.name for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).exists()]
assert not missing
corner.camera=bpy.data.objects[corner['BC_camera_desktop']];corner.frame_set(0);corner.render.resolution_x=1920;corner.render.resolution_y=1080;corner.render.filepath='//../output/manual-corner/frame_'
bpy.context.window.scene=main;main.frame_set(0)
bpy.context.preferences.filepaths.save_version=0

report={'passed':True,'original_main_object_count':len(main.objects),'original_city_object_count':328,'camera_pose_max_error':camera_error,'cabin_pose_max_change':error,'cabin_objects_checked':len(body),'environment_endpoint_max_error':root_error,'missing_dependencies':missing}
(ROOT/'reports/corner-scene-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
