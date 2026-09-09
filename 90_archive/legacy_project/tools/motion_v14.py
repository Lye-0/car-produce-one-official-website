"""Low-cost full-journey camera review; not production rendering."""
import bpy,math,time
from pathlib import Path
ROOT=Path('C:/Users/kawau/dev/car-produce-one-official-website')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/blender/CPO_v14_refined.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=4;s.cycles.use_denoising=True
s.render.use_persistent_data=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type!='CPU'
s.cycles.device='GPU' if any(d.use for d in prefs.devices) else 'CPU'
s.render.resolution_x=480;s.render.resolution_y=270;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'
out=ROOT/'work/v14-motion-frames';out.mkdir(parents=True,exist_ok=True)
t=time.perf_counter()
for i in range(360):
    frame=i*7.5;s.frame_set(int(frame),subframe=frame-int(frame));s.render.filepath=str(out/f'{i:04d}.png')
    bpy.ops.render.render(write_still=True)
    if i%20==0:print('MOTION_PROGRESS',i,round(time.perf_counter()-t,1),flush=True)
print('MOTION_RENDER_DONE',round(time.perf_counter()-t,1),flush=True)
