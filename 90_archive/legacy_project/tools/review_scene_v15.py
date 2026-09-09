"""Saved-file rendering of selected v15 shots. Does not save the work scene."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/blender/CPO_v15_refined.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=int(sys.argv[sys.argv.index('--samples')+1]) if '--samples' in sys.argv else 48;s.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type!='CPU'
s.cycles.device='GPU';s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
if '--small' in sys.argv:s.render.resolution_percentage=60
out=ROOT/'work/v15-review';out.mkdir(parents=True,exist_ok=True)
original=s.camera
shots=[('01_night',0,None,None,0),('02_drive',180,None,None,0),('03_entry',720,None,None,0),('04_tools',1080,None,None,0),('05_magazines',1800,None,None,0),('06_turn',2323,None,None,0),('07_prelude',1080,(4.5,-.70,1.45),(1.5,1.0,.7),35),('08_vezel',1080,(5.8,-.8,1.65),(8.9,1.0,.82),35),('09_store',500,(14,-19,5.0),(4.9,.5,4.4),32),('10_city',0,(-43,-8.5,2.1),(-7,-7.5,7),30),('11_showroom',1080,(7.1,3.4,1.8),(4.6,.8,.8),20)]
if '--shots' in sys.argv:
 names=sys.argv[sys.argv.index('--shots')+1].split(',');shots=[x for x in shots if x[0] in names]
for name,frame,eye,target,lens in shots:
 s.frame_set(frame);s.camera=original
 if eye:
  d=bpy.data.cameras.new('temporary V15 review camera');d.lens=lens;d.clip_start=.03;d.clip_end=500
  c=bpy.data.objects.new('temporary V15 review camera',d);s.collection.objects.link(c);c.location=eye;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();s.camera=c
 s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True);print('V15_REVIEW_SAVED',name,flush=True)
 if eye:bpy.data.objects.remove(c,do_unlink=True)
print('V15_REVIEW_DONE',flush=True)
