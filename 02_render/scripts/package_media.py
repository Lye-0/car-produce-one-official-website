"""Validated dual-codec packaging; quality exports never activate production media."""
from pathlib import Path
import argparse,json,hashlib,shutil,statistics,sys
from render_contract import load_config,fingerprint,valid_png,digest,COUNTS,HOLDS,QUALITY
from media_encoding import encode,verify,poster,probe_encoders,encode_pair
from media_runtime import av
ROOT=Path(__file__).resolve().parents[1]

def write_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)

def encoding_config():
 config=json.loads((ROOT/'encoding.json').read_text(encoding='utf-8-sig'))
 assert config['name'] and all(c.isalnum() or c in '-_' for c in config['name'])
 assert config['width']>0 and config['height']>0 and not config['width']%2 and not config['height']%2
 assert 1<=config['scroll_gop']<=6 and 1<=config['loop_gop']<=30
 assert config['backend'] in ('nvenc','software')
 assert config['nvenc_preset'] in ('p4','p5','p6','p7')
 assert config['preset'] in ('fast','medium','slow','slower')
 for key in ('hevc_crf','h264_crf','hevc_cq','h264_cq'):assert 0<=config[key]<=40
 return config

def preflight():
 cfg=load_config(ROOT);enc=encoding_config()
 try:checks=probe_encoders(enc)
 except Exception as error:
  raise RuntimeError(f"{enc['backend']} encoder preflight failed. Rendering was not started by the launcher. Check the GPU/driver; CPU encoding requires explicitly selecting backend=software in encoding.json. Original error: {error}") from error
 result={'python':sys.executable,'pyav':av.__version__,'backend':enc['backend'],'encoder_checks':checks,'render':cfg,'encoding':enc}
 print(json.dumps(result,indent=2),flush=True)
 return cfg,enc

def checked_folder(bank,profile,job,action,cfg):
 folder=bank/profile/job
 record=json.loads((folder/'complete.json').read_text())
 w,h=(cfg['width'],cfg['height']) if profile=='desktop' else (cfg['height'],cfg['width'])
 expected=list(range(COUNTS[job])) if action=='final' else QUALITY[job]
 assert record['indices']==expected and record['action']==action and record['fps']==30
 assert (record['width'],record['height'],record['depth'])==(w,h,16)
 names=[f'{i:05d}.png' for i in expected]
 if job in HOLDS or job=='drive':names.append('endpoint.png')
 for name in names:assert valid_png(folder/name,w,h,16),f'Invalid or missing PNG: {folder/name}'
 return folder

def package(action,profile,job):
 cfg,enc=preflight();stamp=fingerprint(ROOT,cfg)
 bank=ROOT/'output'/((action+'-' if action=='quality' else '')+cfg['run_name'])
 assert json.loads((bank/'render-settings.json').read_text())==stamp,'Source or render settings changed; choose the matching frame bank.'
 encoder_stamp={k:digest(ROOT/'scripts'/k) for k in ('media_encoding.py','media_runtime.py','package_media.py')}
 export_stamp={'render':stamp,'encoding':enc,'encoder':encoder_stamp,'action':action}
 out=bank/'exports'/enc['name'];out.mkdir(parents=True,exist_ok=True)
 if (out/'export-settings.json').exists():assert json.loads((out/'export-settings.json').read_text())==export_stamp,'Encoding changed: choose a new encoding.name.'
 else:write_json(out/'export-settings.json',export_stamp)
 profiles=['desktop','mobile'] if profile=='both' else [profile]
 jobs=list(COUNTS) if job=='all' else [job]
 manifest_path=out/'manifest.json'
 manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'version':cfg['run_name']+'-'+enc['name'],'production':action=='final','profiles':{}}
 for p in profiles:
  clips=manifest['profiles'].setdefault(p,{})
  w,h=(enc['width'],enc['height']) if p=='desktop' else (enc['height'],enc['width'])
  for j in jobs:
   folder=checked_folder(bank,p,j,action,cfg);delivery=out/p/j;delivery.mkdir(parents=True,exist_ok=True)
   chosen=list(range(COUNTS[j])) if action=='final' else list(range(240,252)) if j=='drive' else list(range(120,180)) if j=='portal' else []
   # Representative full-quality stills are retained even for jobs without a short motion sample.
   still_indices=QUALITY[j] if action=='quality' and not chosen else [chosen[0]]
   stills=[]
   for i in still_indices:
    target=delivery/f'{i:05d}.webp';poster(folder/f'{i:05d}.png',target);stills.append(target.relative_to(out).as_posix())
   if not chosen:
    clips[j]={'stills':stills,'fps':30,'frames':0,'variants':[]};write_json(manifest_path,manifest);continue
   files=[folder/f'{i:05d}.png' for i in chosen]
   source_digest=hashlib.sha256(''.join(digest(f) for f in files).encode()).hexdigest()
   gop=enc['loop_gop'] if j=='drive' or j in HOLDS else enc['scroll_gop']
   asset={'fps':30,'frames':len(chosen),'source_start':chosen[0],'poster':stills[0],'variants':[]}
   targets={codec:delivery/f'{j}-{codec}.mp4' for codec in ('hevc','h264')}
   records={};pending={}
   for codec,target in targets.items():
    record_path=target.with_suffix('.json');record=None
    if record_path.exists() and target.exists():
     candidate=json.loads(record_path.read_text())
     if candidate.get('source_digest')==source_digest and candidate.get('sha256')==digest(target):
      verify(target,len(files),30,w,h,codec,gop);record=candidate
    if record is None:pending[codec]=target
    else:records[codec]=record
   if len(pending)==2:records.update(encode_pair(files,pending,w,h,gop,enc))
   elif pending:
    codec,target=next(iter(pending.items()))
    records[codec]=encode(files,target,w,h,codec,enc[codec+'_crf'],gop,enc['preset'],backend=enc['backend'],cq=enc[codec+'_cq'],nvenc_preset=enc['nvenc_preset'])
   for codec,target in targets.items():
    record=records[codec]
    if codec in pending:
     record['source_digest']=source_digest;write_json(target.with_suffix('.json'),record)
    record['src']=target.relative_to(out).as_posix()
    asset['variants'].append(record)
    print('ENCODE_VERIFIED',p,j,codec,record['bytes'],flush=True)
   clips[j]=asset;write_json(manifest_path,manifest)
 print('EXPORT COMPLETE:',out,flush=True)
 return out

def install():
 cfg,enc=preflight();out=ROOT/'output'/cfg['run_name']/'exports'/enc['name']
 manifest=json.loads((out/'manifest.json').read_text())
 assert manifest['production'] is True,'Quality samples cannot be installed as production media.'
 assert json.loads((out/'export-settings.json').read_text())['render']==fingerprint(ROOT,cfg)
 for p in ('desktop','mobile'):
  assert set(manifest['profiles'][p])==set(COUNTS),'All fourteen production clips are required.'
  for job,asset in manifest['profiles'][p].items():
   assert asset['frames']==COUNTS[job] and asset['fps']==30
   assert {v['codec'] for v in asset['variants']}=={'hevc','h264'}
   assert (out/asset['poster']).is_file()
   for v in asset['variants']:
    path=out/v['src'];assert digest(path)==v['sha256']
    verify(path,COUNTS[job],30,v['width'],v['height'],v['codec'],v['gop'])
 from site_media_layout import site_asset_plan
 website=ROOT.parent/'01_website';manifests=website/'src/media/manifests'
 current=json.loads((manifests/'journey.json').read_text())
 journey,portals,copies=site_asset_plan(manifest,current['posters'])
 # Copy only runtime videos/posters, never render frames or export-side metadata.
 for source,url in copies:
  target=website/'public'/url.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True)
  temporary=target.with_suffix(target.suffix+'.installing')
  shutil.copy2(out/source,temporary);temporary.replace(target)
 for profile,clips in portals.items():write_json(manifests/f'portal-{profile}.json',clips)
 write_json(manifests/'journey.json',journey)
 print('PRODUCTION MEDIA ACTIVATED:',website/'public/media/videos')


def benchmark():
 cfg=load_config(ROOT);bank=ROOT/'output'/('quality-'+cfg['run_name']);records={}
 for line in (bank/'timings.jsonl').read_text().splitlines():
  row=json.loads(line);records[(row['profile'],row['job'],row['index'])]=row
 groups={};total_seconds=0;total_bytes=0
 for p in ('desktop','mobile'):
  for j,count in COUNTS.items():
   rows=[r for r in records.values() if r['profile']==p and r['job']==j]
   if not rows:continue
   seconds=[r['seconds'] for r in rows];sizes=[r['bytes'] for r in rows];n=count+(j in HOLDS or j=='drive')
   estimate=statistics.mean(seconds)*n;size=statistics.mean(sizes)*n
   groups[p+'/'+j]={'samples':len(rows),'seconds_min':min(seconds),'seconds_median':statistics.median(seconds),'seconds_max':max(seconds),'estimated_hours':estimate/3600,'estimated_bytes':int(size)}
   total_seconds+=estimate;total_bytes+=size
 result={'measured_groups':len(groups),'expected_groups':14,'groups':groups,'estimated_total_hours':total_seconds/3600,'estimated_png_bytes':int(total_bytes),'free_bytes':shutil.disk_usage(ROOT).free,'caveat':'Sparse samples; scene complexity, thermal load and encoding add uncertainty. Plan 0.75–1.5 times the estimated rendering duration.'}
 write_json(bank/'benchmark.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['check','quality','final','install','benchmark']);parser.add_argument('profile',nargs='?',default='both',choices=['desktop','mobile','both']);parser.add_argument('job',nargs='?',default='all',choices=['all',*COUNTS]);args=parser.parse_args()
 if args.action=='check':preflight()
 elif args.action=='install':install()
 elif args.action=='benchmark':benchmark()
 else:package(args.action,args.profile,args.job)
