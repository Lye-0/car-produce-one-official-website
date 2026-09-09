import bpy,sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/corner-work'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['stills']
mode=args[0];selected=args[1:] or ['desktop','mobile']
bpy.ops.wm.open_mainfile(filepath=str(OUT/'CPO_CORNER_CANDIDATE.blend'))
scene=bpy.data.scenes['CPO_CORNER_CONNECTOR'];main=bpy.data.scenes['CPO_V18_SITE_MAIN']
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type!='CPU'
for s in [scene,main]:
 s.render.engine='CYCLES';s.cycles.samples=8 if mode=='stills' else 16;s.cycles.device='GPU';s.cycles.use_denoising=True;s.cycles.denoiser='OPTIX';s.cycles.seed=18;s.cycles.use_animated_seed=False;s.render.use_persistent_data=True;s.render.use_motion_blur=False
 s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.compression=30
status={'mode':mode,'started':time.time(),'completed':0}
for p,w,h in [('desktop',1280,720),('mobile',720,1280)]:
 if p not in selected:continue
 scene.camera=bpy.data.objects[scene['BC_camera_'+p]];scene.render.resolution_x=w;scene.render.resolution_y=h
 frames=[0,30,45,48,51,72,96] if mode=='stills' else range(97)
 for f in frames:
  bpy.context.window.scene=scene;scene.frame_set(f);path=OUT/('stills' if mode=='stills' else 'frames')/p/f'{f:04d}.png';path.parent.mkdir(parents=True,exist_ok=True)
  if not path.exists():scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
  status.update(profile=p,frame=f,completed=status['completed']+1);(OUT/'render-progress.json').write_text(json.dumps(status));print('CORNER_PROGRESS',p,f,flush=True)
 if mode=='stills':
  bpy.context.window.scene=main;main.camera=bpy.data.objects['V18_'+p+'_Route'];main.frame_set(0);main.render.resolution_x=w;main.render.resolution_y=h;main.render.filepath=str(OUT/'stills'/p/'source.png');bpy.ops.render.render(write_still=True)
status['complete']=True;(OUT/'render-progress.json').write_text(json.dumps(status));print('CORNER_RENDER_DONE',flush=True)
