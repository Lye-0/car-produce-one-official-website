"""Verify the loop, shared junction entry, and native arrival endpoint."""
from pathlib import Path
import json,sys,hashlib
import av
import numpy as np
from PIL import Image,ImageFilter
R=Path(__file__).resolve().parents[3];O=R/'output/junction-work-v4';WEB=R.parent/'01_website/public/media'
DRIVE=O/'media'
def rgb(im):return np.asarray(im.convert('RGB').filter(ImageFilter.GaussianBlur(2))).astype(float)
profiles=[a for a in sys.argv[1:] if a in ('desktop','mobile')] or ['desktop','mobile']
report={}
for profile in profiles:
 first=Image.open(O/'drive'/profile/'0000.png');loop_end=Image.open(O/'drive'/profile/'endpoint.png');turn_first=Image.open(O/'turn'/profile/'0000.png')
 loop_error=float(abs(rgb(first)-rgb(loop_end)).mean());entry_error=float(abs(np.asarray(loop_end).astype(float)-np.asarray(turn_first).astype(float)).mean())
 assert loop_error<1,(profile,'same-pose loop seam',loop_error)
 assert entry_error<.05,(profile,'shared entry',entry_error)
 streams={};decoded={}
 for name,count,fps in [('drive',600,30),('turn',481,30)]:
  with av.open(str(DRIVE/profile/(name+'.mp4'))) as reader:
   stream=reader.streams.video[0];assert float(stream.average_rate)==fps
   frames=list(reader.decode(stream));assert len(frames)==count and all(f.key_frame for f in frames)
   times=[float(f.pts*f.time_base) for f in frames]
   assert all(abs(t-i/fps)<1e-6 for i,t in enumerate(times)),(profile,name,'nonuniform timestamps')
   streams[name]={'frames':count,'fps':fps,'width':stream.width,'height':stream.height,'all_keyframes':True};decoded[name]=frames
 # Inspect the actual encoded last -> first step against its temporal neighbours.
 # A stationary endpoint comparison alone does not verify playback continuity.
 loop=decoded['drive'];a,b,c,d=[rgb(f.to_image()) for f in [loop[-2],loop[-1],loop[0],loop[1]]]
 regions={};height,width=c.shape[:2]
 for row in range(3):
  for col in range(3):
   sl=(slice(row*height//3,(row+1)*height//3),slice(col*width//3,(col+1)*width//3))
   boundary=float(abs(b[sl]-c[sl]).mean());adjacent=float((abs(a[sl]-b[sl]).mean()+abs(c[sl]-d[sl]).mean())/2)
   pose_error=float(abs(rgb(first)[sl]-rgb(loop_end)[sl]).mean())
   assert pose_error<3,(profile,row,col,'local same-pose discontinuity',pose_error)
   assert boundary<=1.8*adjacent+.2,(profile,row,col,'abnormal encoded boundary step',boundary,adjacent)
   regions[f'{row},{col}']={'boundary_step':boundary,'adjacent_step':adjacent,'same_pose_error':pose_error}
 with av.open(str(WEB/'videos'/profile/'route/h264.mp4')) as old:arrival=next(old.decode(video=0)).to_image().resize((width,height),Image.Resampling.BILINEAR)
 end_error=float(abs(rgb(decoded['turn'][-1].to_image())-rgb(arrival)).mean());assert end_error<1.5,(profile,'native handoff',end_error)
 report[profile]={'loop_endpoint_blurred_rgb_mae':loop_error,'shared_entry_raw_rgb_mae':entry_error,'native_handoff_blurred_rgb_mae':end_error,'boundary_regions':regions,'streams':streams}
report['source_sha256']=hashlib.sha256((O/'CPO_JUNCTION_CANDIDATE.blend').read_bytes()).hexdigest()
report['media_sha256']={profile+'/'+name:hashlib.sha256((DRIVE/profile/(name+'.mp4')).read_bytes()).hexdigest() for profile in profiles for name in ['drive','turn']}
report['passed']=True
target=R/'reports/history/junction-media-validation.json' if len(profiles)==2 else O/('media-validation-'+profiles[0]+'.json')
target.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
