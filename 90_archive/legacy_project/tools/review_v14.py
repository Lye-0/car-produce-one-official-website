"""Render and validate the saved v14 in a separate Blender process."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
ROOT=Path('C:/Users/kawau/dev/car-produce-one-official-website')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/blender/CPO_v14_refined.blend'))
s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type!='CPU'
    if any(d.use for d in prefs.devices):s.cycles.device='GPU'
except Exception as e:print('CPU fallback:',e)
s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'
out=ROOT/'work/v14-review';out.mkdir(parents=True,exist_ok=True)
original=s.camera
poses=[]
for frame in [0,300,648,1026,1080,1200,1296,1701,1800,1950,2025,2200,2430,2700]:
    s.frame_set(frame);m=original.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world
    base=bpy.data.objects['CPO_BASE_CAMERA_v13'].evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world
    poses.append({'frame':frame,'eye':list(m.translation),'micro_offset_m':(m.translation-base.translation).length})
assert max(p['micro_offset_m'] for p in poses)<.005
assert (Vector(poses[4]['eye'])-Vector(poses[5]['eye'])).length>.0001
assert (Vector(poses[8]['eye'])-Vector(poses[9]['eye'])).length>.0001
missing=[im.name for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not im.packed_files]
assert not missing,missing
report={'file':str(ROOT/'assets/blender/CPO_v14_refined.blend'),'blender':bpy.app.version_string,'objects':len(s.objects),'visible_meshes':sum(o.type=='MESH' and not o.hide_render for o in s.objects),'camera':original.name,'camera_samples':poses,'images':len(bpy.data.images),'unpacked':missing,'limitations':['Vehicle surfaces are original approximations, not CAD.','Full continuous collision re-audit not performed.','Loop segmentation and final rendering not part of this revision.']}
(ROOT/'docs/v14-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
shots=[('01_night',0,None,None),('02_entry',720,None,None),('03_tools',1080,None,None),('04_magazines',1800,None,None),('05_turn',2220,None,None),('06_pc',2520,None,None),('07_prelude',1080,(4.7,-.45,1.55),(1.5,1.1,.7)),('08_vezel',1080,(5.8,-.45,1.65),(8.9,1.1,.85)),('09_store',500,(12,-13,3.2),(4.9,.5,2.0))]
if '--shots' in sys.argv:
    names=sys.argv[sys.argv.index('--shots')+1].split(',');shots=[q for q in shots if q[0] in names]
for name,frame,eye,target in shots:
    s.frame_set(frame);s.camera=original
    if eye:
        d=bpy.data.cameras.new('temporary review lens');d.lens=37;d.clip_start=.02
        c=bpy.data.objects.new('temporary review camera',d);s.collection.objects.link(c);c.location=eye;c.rotation_euler=(Vector(target)-Vector(eye)).to_track_quat('-Z','Y').to_euler();s.camera=c
    s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('REVIEW_SAVED',name,flush=True)
    if eye:bpy.data.objects.remove(c,do_unlink=True)
print('V14_REVIEW_DONE',flush=True)
