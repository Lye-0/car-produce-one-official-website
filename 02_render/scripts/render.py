"""Production and bounded quality PNG renderer. Launch through RENDER.cmd."""
import bpy,sys,json,math,time,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render_contract import load_config,fingerprint,valid_png,indices,source_frame,COUNTS,HOLDS,expected_images
args=sys.argv[sys.argv.index('--')+1:];action,profile,selection=args
assert action in ('check','test','sample','quality','final')
cfg=load_config(ROOT);stamp=fingerprint(ROOT,cfg);source=ROOT/'scene/CPO_MASTER.blend'
profiles=['desktop','mobile'] if profile=='both' else [profile];assert all(p in ('desktop','mobile') for p in profiles)
jobs=list(COUNTS) if selection=='all' else [selection];assert all(j in COUNTS for j in jobs)
bpy.ops.wm.open_mainfile(filepath=str(source))
missing=[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file and not Path(bpy.path.abspath(i.filepath)).exists()]
assert not missing,missing
assert not bpy.data.libraries
main=bpy.data.scenes['CPO_V18_SITE_MAIN'];junction=bpy.data.scenes['CPO_JUNCTION_DRIVE']
for p in profiles:
 assert junction['JT_camera_'+p] in bpy.data.objects
 for suffix in ['Route','Idle_tools','Idle_magazines','Idle_monitor']:assert 'V18_'+p+'_'+suffix in bpy.data.objects
use_gpu=False;devices=[]
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type=cfg['device'];prefs.get_devices()
 for d in prefs.devices:
  d.use=d.type!='CPU'
  if d.use:devices.append(d.name)
 use_gpu=bool(devices)
except Exception as error:print('GPU detection:',error,flush=True)
assert use_gpu or not cfg['require_gpu'],'GPU unavailable. Refusing an unintended CPU render.'
free=shutil.disk_usage(ROOT).free
upper=expected_images()*cfg['width']*cfg['height']*3*(cfg['color_depth']//8)*1.02
summary={'profiles':profiles,'jobs':jobs,'settings':cfg,'gpu_devices':devices,'free_bytes':free,'full_image_count':expected_images(),'uncompressed_png_budget_bytes':int(upper),'reserve_bytes':int(cfg['reserve_gib']*1024**3)}
print(json.dumps(summary,indent=2),flush=True)
if action=='check':
 assert free>cfg['reserve_gib']*1024**3,'Insufficient reserve space.'
 print('PREFLIGHT PASSED: packed master, cameras, GPU and settings verified.',flush=True);sys.exit(0)
# Validate the selected bank before counting complete frames toward the disk budget.
out=ROOT/'output'/((action+'-' if action in ('test','sample','quality') else '')+cfg['run_name'])
out.mkdir(parents=True,exist_ok=True);manifest=out/'render-settings.json'
if manifest.exists():assert json.loads(manifest.read_text())==stamp,'Source/settings changed: choose a NEW run_name; never mix frame banks.'
else:manifest.write_text(json.dumps(stamp,indent=2))
if action=='final':
 remaining=0
 for p in profiles:
  w,h=(cfg['width'],cfg['height']) if p=='desktop' else (cfg['height'],cfg['width'])
  for job in jobs:
   names=[f'{i:05d}.png' for i in range(COUNTS[job])]
   if job in HOLDS or job=='drive':names.append('endpoint.png')
   remaining+=sum(not valid_png(out/p/job/name,w,h,cfg['color_depth']) for name in names)
 remaining_budget=remaining*cfg['width']*cfg['height']*3*(cfg['color_depth']//8)*1.02
 assert free>remaining_budget+cfg['reserve_gib']*1024**3,'Insufficient space for remaining images plus reserve.'
 print('REMAINING_IMAGES',remaining,'BUDGET_BYTES',int(remaining_budget),flush=True)
for s in [main,junction]:
 s.cycles.max_bounces=cfg['max_bounces'];s.cycles.caustics_reflective=cfg['caustics_reflective'];s.cycles.caustics_refractive=cfg['caustics_refractive']
 s.render.engine='CYCLES';s.cycles.samples=2 if action=='test' else cfg['samples'];s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=cfg['noise_threshold'];s.cycles.adaptive_min_samples=0 if action=='test' else cfg['min_samples']
 s.cycles.use_denoising=True;s.cycles.denoiser=cfg['denoiser'];s.cycles.denoising_use_gpu=cfg['denoising_use_gpu'];s.cycles.device='GPU' if use_gpu else 'CPU';s.cycles.seed=18;s.cycles.use_animated_seed=False
 s.render.use_persistent_data=True;s.render.use_motion_blur=cfg['motion_blur'];s.render.resolution_percentage=100;s.render.fps=30
 s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth=str(8 if action=='test' else cfg['color_depth']);s.render.image_settings.compression=30
light=bpy.data.objects['V18 Passing reflection'];origin=light.location.copy();completed=0;skipped=0
for p in profiles:
 w,h=(320,180) if action=='test' else (cfg['width'],cfg['height'])
 if p=='mobile':w,h=h,w
 depth=8 if action=='test' else cfg['color_depth']
 for job in (['drive','junction'] if action=='test' and selection=='all' else jobs):
  s=junction if job in ('drive','junction') else main;bpy.context.window.scene=s;s.render.resolution_x=w;s.render.resolution_y=h
  s.camera=bpy.data.objects[junction['JT_camera_'+p] if job in ('drive','junction') else 'V18_'+p+'_'+('Idle_'+job.replace('-idle','') if job in HOLDS else 'Route')]
  folder=out/p/job;folder.mkdir(parents=True,exist_ok=True)
  selected=indices(action,job);sequence=[(i,f'{i:05d}.png') for i in selected]
  if action not in ('test','sample') and (job in HOLDS or job=='drive'):sequence.append((COUNTS[job],'endpoint.png'))
  for i,name in sequence:
   path=folder/name
   if valid_png(path,w,h,depth):skipped+=1;continue
   assert shutil.disk_usage(ROOT).free>cfg['reserve_gib']*1024**3,'Disk reserve reached; resume after freeing space.'
   frame=source_frame(job,i);s.frame_set(frame);light.location=origin.copy();light.data.energy=0
   if job in HOLDS:
    phase=i/COUNTS[job];light.location.x+=4*(phase-.5);light.data.energy=0 if i in (0,COUNTS[job]) else 16*math.sin(math.pi*phase)**4
   started=time.perf_counter();s.render.filepath=str(path);bpy.ops.render.render(write_still=True)
   assert valid_png(path,w,h,depth),str(path)
   record={'profile':p,'job':job,'index':i,'source_frame':frame,'seconds':time.perf_counter()-started,'bytes':path.stat().st_size,'path':str(path.relative_to(out))}
   with (out/'timings.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
   completed+=1;(out/'progress.json').write_text(json.dumps({**record,'rendered_this_run':completed,'skipped_this_run':skipped,'action':action}));print('FRAME_COMPLETE',p,job,i,round(record['seconds'],2),flush=True)
  (folder/'complete.json').write_text(json.dumps({'indices':selected,'frames':len(selected),'fps':30,'width':w,'height':h,'depth':depth,'production':action=='final','action':action,'endpoint':job in HOLDS or job=='drive'}))
(out/'render-complete.json').write_text(json.dumps({'action':action,'profiles':profiles,'jobs':jobs,'rendered':completed,'skipped':skipped,'fingerprint':stamp},indent=2))
print('RENDER COMPLETE:',out,'rendered',completed,'skipped',skipped,flush=True)


