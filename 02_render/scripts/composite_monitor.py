from pathlib import Path
import sys,json,hashlib,os,copy,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'02_render/scripts'))
from media_runtime import np,Image
from media_encoding import read_png16,write_rgb_sequences,verify
parser=argparse.ArgumentParser(description='Composite the monitor hero into existing 16-bit production frames. Does not activate the result.')
parser.add_argument('--version',required=True)
parser.add_argument('--hero',type=Path,default=R/'02_render/assets/monitor-hero.png')
args=parser.parse_args();version=args.version
assert version and all(c.isalnum() or c in '-_' for c in version)
W=R/'02_render/output'/('review-'+version);W.mkdir(parents=True,exist_ok=True)
old=json.loads((R/'01_website/src/production-media.json').read_text())
manifest=copy.deepcopy(old);manifest['version']=version
# Legacy baking is an explicit optional export; the live site no longer carries these videos.
template=json.loads((R/'02_render/assets/monitor-baking-template.json').read_text())
for profile,assets in manifest['profiles'].items():assets.update(copy.deepcopy(template[profile]))
base=R/'01_website/public/media/production'; output=base/version
if output.exists():raise FileExistsError('Use a new immutable version name: '+version)
tracking=json.loads((R/'01_website/src/screen-tracking.json').read_text())
approach_tracking=json.loads((R/'02_render/assets/monitor-approach-tracking.json').read_text())
hero=Image.open(args.hero).convert('RGBA');tw,th=hero.size

def composite(rgb,quad,gain=1):
 h,w=rgb.shape[:2];q=np.array(quad)*[w,h];src=np.array([[0,0],[tw,0],[tw,th],[0,th]],float)
 rows=[];values=[]
 for (x,y),(u,v) in zip(q,src):
  rows.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]);values.extend([u,v])
 coeff=np.linalg.solve(rows,values)
 warped=np.asarray(hero.transform((w,h),Image.Transform.PERSPECTIVE,coeff,Image.Resampling.BICUBIC))
 alpha=warped[:,:,3:4].astype(np.float32)/255*gain
 return np.round(rgb*(1-alpha)+warped[:,:,:3].astype(np.float32)*257*alpha).astype(np.uint16)

for profile,assets in manifest['profiles'].items():
 for job,asset in assets.items():
  dest=output/profile/job;dest.mkdir(parents=True,exist_ok=True)
  original=base/old['version']/profile/job
  asset['poster']=asset['poster'].replace(old['version'],version)
  for v in asset['variants']:v['src']=v['src'].replace(old['version'],version)
  if job not in ('portal','monitor-idle','monitor-approach'):
   for path in original.iterdir():
    if path.is_file() and not (dest/path.name).exists():os.link(path,dest/path.name)
   continue
  count=asset['frames'];w,h=(1920,1080) if profile=='desktop' else (1080,1920)
  bank=R/'02_render/output/final-table-approved-20w'/profile/('route' if job=='monitor-approach' else job)
  def arrays():
   for i in range(count):
    if job=='monitor-approach':
     f=2340+i;rgb=read_png16(bank/f'{min(2429,f):05d}.png');q=approach_tracking[profile][90 if f==2429 else i]['quad']
     t=max(0,min(1,(f-2370)/54));gain=t*t*(3-2*t)
    else:
     rgb=read_png16(bank/f'{i:05d}.png');q=tracking[profile][i if job=='portal' else 0]['quad'];gain=1
    result=composite(rgb,q,gain)
    if i in (0,120,240):
     Image.fromarray((result/257).round().astype(np.uint8)).save(W/f'baked-{profile}-{job}-{i}.png')
    if i==0:
     im=Image.fromarray((result/257).round().astype(np.uint8));im.thumbnail((1280,1280));im.save(dest/'00000.webp',quality=95)
    yield result
  targets={c:dest/f'{job}-{c}.mp4' for c in ('hevc','h264')}
  print('START',profile,job,flush=True)
  write_rgb_sequences(arrays(),targets,w,h,{'hevc':18,'h264':17},30 if job=='monitor-idle' else 6,'p7',30,'nvenc')
  variants=[]
  for codec,target in targets.items():
   info=verify(target,count,30,w,h,codec,30 if job=='monitor-idle' else 6)
   info.update(src=f'/media/production/{version}/{profile}/{job}/{target.name}',bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bitrate=round(target.stat().st_size*8/(count/30)),encoder=codec+'_nvenc',backend='nvenc',quality_mode='cq',quality=18 if codec=='hevc' else 17,gop=30 if job=='monitor-idle' else 6,preset='p7',screen_baked=True,hero_sha256=hashlib.sha256((args.hero).read_bytes()).hexdigest())
   target.with_suffix('.json').write_text(json.dumps(info,indent=2));variants.append(info)
  asset['variants']=variants;asset['screen_baked']=True
  print('VERIFIED',profile,job,flush=True)
(W/'baked-production-media.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('ALL_BAKED_AND_VERIFIED',flush=True)
