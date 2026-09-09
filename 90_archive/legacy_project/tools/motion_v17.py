"""Review motion plates; production render settings in the blend stay intact."""
import bpy,sys,math,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/blender/CPO_v17_refined.blend'))
mode=sys.argv[sys.argv.index('--mode')+1] if '--mode' in sys.argv else 'seams'
main=bpy.context.scene;loop=bpy.data.scenes.get('CPO_V17_DRIVE_LOOP') or bpy.data.scenes['CPO_V15_DRIVE_LOOP']
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type!='CPU'
out=ROOT/'work/v17-motion'/mode;out.mkdir(parents=True,exist_ok=True)
if mode=='seams':jobs=[(main,0,'main_0000'),(loop,0,'loop_0000'),(loop,1440,'loop_1440')];fps=30;width=640;height=360;samples=48
elif mode=='camera':jobs=[(main,float(f),f'{f-2190:04d}') for f in range(2190,2431)];fps=30;width=768;height=432;samples=16
elif mode=='loop':jobs=[(loop,i*3.75,f'{i:04d}') for i in range(384)];fps=8;width=640;height=360;samples=8
elif mode=='journey':jobs=[(main,i*3.75,f'{i:04d}') for i in range(720)];fps=8;width=640;height=360;samples=8
else:raise ValueError(mode)
for scene in {j[0] for j in jobs}:
 scene.render.engine='CYCLES';scene.cycles.samples=samples;scene.cycles.use_denoising=True;scene.cycles.device='GPU';scene.cycles.seed=15;scene.cycles.use_animated_seed=False
 scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.use_persistent_data=mode!='seams'
 scene.render.use_motion_blur=False
start=time.perf_counter()
for i,(scene,frame,name) in enumerate(jobs):
 bpy.context.window.scene=scene;scene.frame_set(int(frame),subframe=frame-int(frame));scene.render.filepath=str(out/(name+'.png'))
 bpy.ops.render.render(write_still=True)
 if i%30==0:print('V17_MOTION_PROGRESS',mode,i,len(jobs),round(time.perf_counter()-start,1),flush=True)
(out/'manifest.json').write_text(json.dumps({'mode':mode,'fps':fps,'width':width,'height':height,'samples':samples,'frames':len(jobs),'seconds':len(jobs)/fps,'elapsed_seconds':time.perf_counter()-start,'complete':True},indent=2),encoding='utf-8')
print('V17_MOTION_DONE',mode,round(time.perf_counter()-start,1),flush=True)
