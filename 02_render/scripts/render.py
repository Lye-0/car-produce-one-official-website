"""Portable production PNG renderer. Launch through ../../RENDER.cmd."""
import bpy, sys, json, math, hashlib, struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:]
action,profile,selection=args
cfg=json.loads((ROOT/'settings.json').read_text(encoding='utf-8-sig'))
assert cfg['fps']==30, 'Keep fps at 30: camera tracking and timeline use 30 fps.'
assert cfg['width']>0 and cfg['height']>0 and cfg['samples']>0
assert cfg['run_name'] and all(c.isalnum() or c in '-_' for c in cfg['run_name']), 'Invalid run_name'
source=ROOT/'scene/CPO_MASTER.blend'
fingerprint={'master_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'settings':cfg,'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
profiles=['desktop','mobile'] if profile=='both' else [profile]
assert all(p in ('desktop','mobile') for p in profiles)
holds={'tools-idle':1026,'magazines-idle':1701,'monitor-idle':2430}
counts={'corner':97,'route':2430,'portal':271,'city':1440,**{k:180 for k in holds}}
jobs=list(counts) if selection=='all' else [selection]
assert all(j in counts for j in jobs)
print(json.dumps({'profiles':profiles,'jobs':{j:counts[j] for j in jobs},'settings':cfg},indent=2),flush=True)
bpy.ops.wm.open_mainfile(filepath=str(source))
missing=[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file and not Path(bpy.path.abspath(i.filepath)).exists()]
assert not missing,missing
assert not bpy.data.libraries
if action=='check':
 print('PREFLIGHT PASSED: self-contained master, cameras and settings verified.',flush=True)
 assert 'CPO_CORNER_CONNECTOR' in bpy.data.scenes, 'Corner scene missing'
 for p in profiles:
  assert bpy.data.scenes['CPO_CORNER_CONNECTOR']['BC_camera_'+p] in bpy.data.objects
  for suffix in ['Route','City','Idle_tools','Idle_magazines','Idle_monitor']:assert 'V18_'+p+'_'+suffix in bpy.data.objects
 sys.exit(0)
out=ROOT/'output'/('test' if action=='test' else cfg['run_name'])
out.mkdir(parents=True,exist_ok=True)
manifest=out/'render-settings.json'
if manifest.exists() and action!='test':assert json.loads(manifest.read_text())==fingerprint,'Master/settings changed: use a NEW run_name to avoid mixing renders.'
manifest.write_text(json.dumps(fingerprint,indent=2))
main=bpy.data.scenes['CPO_V18_SITE_MAIN'];city=bpy.data.scenes['CPO_V18_CITY_LOOP'];corner=bpy.data.scenes['CPO_CORNER_CONNECTOR']
use_gpu=False
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type=cfg['device'];prefs.get_devices()
 for d in prefs.devices:d.use=d.type!='CPU'
 use_gpu=any(d.use for d in prefs.devices)
except Exception as e:print('GPU unavailable; using CPU:',str(e),flush=True)
for s in [main,city,corner]:
 s.render.engine='CYCLES';s.cycles.samples=2 if action=='test' else cfg['samples'];s.cycles.use_denoising=True;s.cycles.denoiser='OPENIMAGEDENOISE';s.cycles.device='GPU' if use_gpu else 'CPU'
 s.cycles.seed=18;s.cycles.use_animated_seed=False;s.render.use_persistent_data=True;s.render.use_motion_blur=False;s.render.resolution_percentage=100;s.render.fps=30
 s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.compression=30
light=bpy.data.objects['V18 Passing reflection'];origin=light.location.copy()
def valid(path,w,h):
 if not path.exists():return False
 with path.open('rb') as f:
  head=f.read(24)
  if len(head)!=24 or head[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',head[16:24])!=(w,h):return False
  f.seek(-12,2);return f.read()==b'\x00\x00\x00\x00IEND\xaeB`\x82'
for p in profiles:
 w,h=(320,180) if action=='test' else (cfg['width'],cfg['height'])
 if p=='mobile':w,h=h,w
 for job in ((['route'] if selection=='all' else jobs) if action=='test' else jobs):
  s=corner if job=='corner' else city if job=='city' else main;bpy.context.window.scene=s;s.render.resolution_x=w;s.render.resolution_y=h
  suffix='City' if job=='city' else 'Idle_'+job.replace('-idle','') if job in holds else 'Route'
  s.camera=bpy.data.objects[corner['BC_camera_'+p] if job=='corner' else 'V18_'+p+'_'+suffix]
  folder=out/p/job;folder.mkdir(parents=True,exist_ok=True)
  indices=([0,48,96] if job=='corner' else range(2)) if action=='test' else range(counts[job])
  sequence=[(i,f'{i:05d}.png') for i in indices]
  if action!='test' and (job in holds or job=='city'):sequence.append((counts[job],'endpoint.png'))
  for i,name in sequence:
   path=folder/name
   if action!='test' and valid(path,w,h):continue
   frame=holds[job] if job in holds else 2430+i if job=='portal' else 2430 if job=='route' and i==2429 else i
   s.frame_set(frame);light.location=origin.copy();light.data.energy=0
   if job in holds:
    phase=i/counts[job];light.location.x+=4*(phase-.5);light.data.energy=0 if i in (0,counts[job]) else 16*math.sin(math.pi*phase)**4
   s.render.filepath=str(path);bpy.ops.render.render(write_still=True)
   assert valid(path,w,h),str(path)
   (out/'progress.json').write_text(json.dumps({'profile':p,'job':job,'frame':i,'total':counts[job],'last_file':str(path)}))
  (folder/'complete.json').write_text(json.dumps({'frames':len(indices),'fps':30,'width':w,'height':h,'production':action!='test'}))
print('RENDER COMPLETE: '+str(out),flush=True)
