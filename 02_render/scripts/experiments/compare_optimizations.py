"""Independent single-variable optimization trials; production settings stay untouched."""
from pathlib import Path
import sys,json,runpy,hashlib
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import render_contract
variant,job=sys.argv[sys.argv.index('--')+1:]
assert variant in ('baseline','caustics-off','bounces-6','noise-005') and job in ('drive','route')
cfg=render_contract.load_config(ROOT)
cfg={**cfg,'run_name':'opt-'+variant+'-01'}
changes={}
if variant=='caustics-off':changes={'caustics_reflective':False,'caustics_refractive':False}
if variant=='bounces-6':changes={'max_bounces':6} # Other per-type limits stay identical to A.
if variant=='noise-005':cfg['noise_threshold']=0.05
@bpy.app.handlers.persistent
def configure_after_load(_):
 for name in ('CPO_V18_SITE_MAIN','CPO_JUNCTION_DRIVE'):
  for key,value in changes.items():setattr(bpy.data.scenes[name].cycles,key,value)
bpy.app.handlers.load_post.append(configure_after_load)
render_contract.load_config=lambda root:cfg
out=ROOT/'output'/('sample-'+cfg['run_name']);out.mkdir(parents=True,exist_ok=True)
provenance={'variant':variant,'config':cfg,'cycles_overrides':changes,'trial_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
stamp=out/'trial-settings.json'
if stamp.exists():assert json.loads(stamp.read_text())==provenance,'Trial settings changed; use a new trial run name.'
else:stamp.write_text(json.dumps(provenance,indent=2))
sys.argv=['render.py','--','sample','desktop',job]
runpy.run_path(str(ROOT/'scripts/render.py'),run_name='__main__')
s=bpy.data.scenes['CPO_JUNCTION_DRIVE' if job=='drive' else 'CPO_V18_SITE_MAIN']
print('VERIFIED_TRIAL',variant,job,json.dumps({k:getattr(s.cycles,k) for k in ('max_bounces','caustics_reflective','caustics_refractive','adaptive_threshold','samples','denoising_use_gpu')}),flush=True)
