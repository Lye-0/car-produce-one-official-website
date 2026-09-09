import bpy,sys,json,time,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'output/junction-work'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['stills'];mode=args[0];profiles=args[1:] or ['desktop','mobile']
source=O/'CPO_JUNCTION_CANDIDATE.blend'
signature={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'mode':mode,'samples':8 if mode=='stills' else 6,'seed':18,'desktop':[960,540],'mobile':[540,960],'drive_fps':8,'turn_fps':12}
provenance=O/(mode+'-provenance.json')
if provenance.exists():
 assert json.loads(provenance.read_text())==signature,'Candidate or render settings changed. Archive junction-work and rebuild before rendering.'
else:
 existing=list((O/'stills' if mode=='stills' else O/'drive').glob('*/*.png'))
 assert not existing,'Existing frames have no provenance. Archive the previous output before rendering.'
 provenance.write_text(json.dumps(signature,indent=2))
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.data.scenes['CPO_JUNCTION_DRIVE'];bpy.context.window.scene=s
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
s.render.engine='CYCLES';s.cycles.device='GPU';s.cycles.samples=8 if mode=='stills' else 6;s.cycles.use_denoising=True;s.cycles.denoiser='OPTIX';s.cycles.seed=18;s.cycles.use_animated_seed=False;s.render.use_persistent_data=True;s.render.use_motion_blur=False;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
status={'mode':mode,'started':time.time(),'completed':0}
for profile,w,h in [('desktop',960,540),('mobile',540,960)]:
 if profile not in profiles:continue
 s.camera=bpy.data.objects[s['JT_camera_'+profile]];s.render.resolution_x=w;s.render.resolution_y=h
 jobs={'stills':[0,300,420,510,600,690,780]} if mode=='stills' else {'drive':[i*3.75 for i in range(80)],'turn':[300+i*2.5 for i in range(193)]}
 for job,frames in jobs.items():
  folder=O/job/profile;folder.mkdir(parents=True,exist_ok=True)
  for i,f in enumerate(frames):
   path=folder/f'{i:04d}.png';s.frame_set(int(f),subframe=f-int(f))
   if not path.exists():s.render.filepath=str(path);bpy.ops.render.render(write_still=True)
   status.update(profile=profile,job=job,frame=i,source=f,completed=status['completed']+1);(O/'progress.json').write_text(json.dumps(status));print('JUNCTION_FRAME',profile,job,i,flush=True)
  if mode!='stills' and job=='drive':
   s.frame_set(300);s.render.filepath=str(folder/'endpoint.png');bpy.ops.render.render(write_still=True)
status['complete']=True;(O/'progress.json').write_text(json.dumps(status));print('JUNCTION_RENDER_DONE',flush=True)
