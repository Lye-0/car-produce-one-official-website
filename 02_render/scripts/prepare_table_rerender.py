"""Seed only the certified, unchanged street clips into the repaired frame bank."""
import json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render_contract import load_config,fingerprint,digest,valid_png,COUNTS
cfg=load_config(ROOT);report=json.loads((ROOT/'reports/table-glass-fix.json').read_text())
assert cfg['run_name'] in (report['source_bank'],report['target_bank'],report.get('previous_target_bank'))
assert digest(ROOT/'scene/CPO_MASTER.blend')==report['new_master_sha256']
old=ROOT/'output'/report['source_bank'];new=ROOT/'output'/report['target_bank']
oldstamp=json.loads((old/'render-settings.json').read_text());stamp=fingerprint(ROOT,cfg)
assert oldstamp['master_sha256']==report['old_master_sha256']
assert {k:v for k,v in oldstamp.items() if k!='master_sha256'}=={k:v for k,v in stamp.items() if k!='master_sha256'}
new.mkdir(exist_ok=True)
manifest=new/'render-settings.json'
if manifest.exists():assert json.loads(manifest.read_text())==stamp
else:manifest.write_text(json.dumps(stamp,indent=2))
count=0
for profile in ('desktop','mobile'):
 w,h=(cfg['width'],cfg['height']) if profile=='desktop' else (cfg['height'],cfg['width'])
 for job in report['unchanged_jobs']:
  src=old/profile/job;dst=new/profile/job;dst.mkdir(parents=True,exist_ok=True)
  names=[f'{i:05d}.png' for i in range(COUNTS[job])]+(['endpoint.png'] if job=='drive' else [])
  for name in names:
   a,b=src/name,dst/name
   assert valid_png(a,w,h,cfg['color_depth']),str(a)
   if b.exists():assert digest(a)==digest(b),str(b)
   else:shutil.copy2(a,b)
   count+=1
  shutil.copy2(src/'complete.json',dst/'complete.json')
  print('REUSED',profile,job,len(names),flush=True)
# Copy encoded immutable street results too; the packager re-verifies bytes and source digests.
enc=json.loads((ROOT/'encoding.json').read_text());source_export=old/'exports'/enc['name'];target_export=new/'exports'/enc['name']
old_export=json.loads((source_export/'export-settings.json').read_text())
assert old_export['render']==oldstamp and old_export['encoding']==enc
assert old_export['encoder']=={k:digest(ROOT/'scripts'/k) for k in ('media_encoding.py','media_runtime.py','package_media.py')}
for profile in ('desktop','mobile'):
 for job in report['unchanged_jobs']:
  src=source_export/profile/job;dst=target_export/profile/job
  if not dst.exists():shutil.copytree(src,dst)
(new/'reuse-validation.json').write_text(json.dumps({'source_fingerprint':oldstamp,'target_fingerprint':stamp,'reused_images':count,'reused_jobs':report['unchanged_jobs'],'scope_evidence':report},indent=2))
cfg['run_name']=report['target_bank'];(ROOT/'settings.json').write_text(json.dumps(cfg,indent=2)+'\n')
print('READY:',new,'reused',count,'remaining',6488,flush=True)

