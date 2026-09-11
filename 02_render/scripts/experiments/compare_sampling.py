"""Compare three sampling/denoising changes independently against the adopted settings."""
from pathlib import Path
import sys,json,runpy,hashlib
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import render_contract
variant,job=sys.argv[sys.argv.index('--')+1:]
assert variant in ('baseline','min-8','max-48','balanced') and job in ('drive','route')
cfg={**render_contract.load_config(ROOT),'run_name':'sampling-'+variant+'-01'}
if variant=='min-8':cfg['min_samples']=8
if variant=='max-48':cfg['samples']=48
quality='BALANCED' if variant=='balanced' else 'HIGH'
@bpy.app.handlers.persistent
def configure_after_load(_):
 for name in ('CPO_V18_SITE_MAIN','CPO_JUNCTION_DRIVE'):
  bpy.data.scenes[name].cycles.denoising_quality=quality
bpy.app.handlers.load_post.append(configure_after_load)
render_contract.load_config=lambda root:cfg
out=ROOT/'output'/('sample-'+cfg['run_name']);out.mkdir(parents=True,exist_ok=True)
provenance={'variant':variant,'config':cfg,'denoising_quality':quality,'trial_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
stamp=out/'trial-settings.json'
if stamp.exists():assert json.loads(stamp.read_text())==provenance,'Trial settings changed; use a new trial run name.'
else:stamp.write_text(json.dumps(provenance,indent=2))
sys.argv=['render.py','--','sample','desktop',job]
runpy.run_path(str(ROOT/'scripts/render.py'),run_name='__main__')
s=bpy.data.scenes['CPO_JUNCTION_DRIVE' if job=='drive' else 'CPO_V18_SITE_MAIN']
assert s.cycles.samples==cfg['samples'] and s.cycles.adaptive_min_samples==cfg['min_samples'] and s.cycles.denoising_quality==quality
print('VERIFIED_TRIAL',variant,job,json.dumps({k:getattr(s.cycles,k) for k in ('max_bounces','caustics_reflective','caustics_refractive','adaptive_threshold','samples','adaptive_min_samples','denoising_quality','denoising_use_gpu')}),flush=True)
