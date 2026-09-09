"""Package the shared approach and physical right turn for scroll-controlled playback."""
from pathlib import Path
import sys,json,hashlib,shutil
import av
from PIL import Image
R=Path(__file__).resolve().parents[1];O=R/'output/junction-work-v4';WEB=O/'media'
provenance=json.loads((O/'preview-provenance.json').read_text());assert provenance['source_sha256']==hashlib.sha256((O/'CPO_JUNCTION_CANDIDATE.blend').read_bytes()).hexdigest(),'Render the current candidate before encoding.'
profiles=sys.argv[1:] or ['desktop','mobile'];reportfile=O/'media-manifest.json';report=json.loads(reportfile.read_text()) if reportfile.exists() else {}
for profile in profiles:
 for job,count,fps in [('drive',600,30),('turn',481,30)]:
  files=sorted((O/job/profile).glob('[0-9][0-9][0-9][0-9].png'))
  if len(files)!=count:print('PENDING',profile,job,len(files),flush=True);continue
  target=WEB/profile/(job+'.mp4');target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_suffix('.build.mp4')
  with Image.open(files[0]) as im:w,h=im.size
  endpoint=None
  if job=='turn':
   # Both cameras reach the same pose. Anchor the last preview frame to the
   # existing compressed arrival plate, avoiding a quality change on the cut.
   with av.open(str(R.parent/'01_website/public/media/stage4'/profile/'route.mp4')) as old:
    endpoint=next(old.decode(video=0)).to_image().convert('RGB').resize((w,h),Image.Resampling.BILINEAR)
  with av.open(str(temporary),'w',options={'movflags':'+faststart'}) as container:
   stream=container.add_stream('libx264',rate=fps);stream.width=w;stream.height=h;stream.pix_fmt='yuv420p';stream.options={'crf':'18','preset':'medium','g':'1','keyint_min':'1','bf':'0','sc_threshold':'0'}
   for i,path in enumerate(files):
    with Image.open(path) as im:rgb=im.convert('RGB')
    if endpoint is not None and i==count-1:rgb=endpoint
    frame=av.VideoFrame.from_image(rgb);frame.pts=i
    for packet in stream.encode(frame):container.mux(packet)
   for packet in stream.encode():container.mux(packet)
  with av.open(str(temporary)) as reader:
   video=reader.streams.video[0];assert float(video.average_rate)==fps
   decoded=list(reader.decode(video));assert len(decoded)==count and all(f.key_frame for f in decoded)
  assert temporary.stat().st_size<25*1024*1024
  temporary.replace(target)
  if job=='drive':
   with Image.open(files[0]) as im:im.convert('RGB').save(WEB/profile/'drive.jpg',quality=93)
  report[profile+'/'+job]={'frames':count,'fps':fps,'width':w,'height':h,'all_keyframes':True,'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'endpoint_anchor':job=='turn','source_sha256':provenance['source_sha256']}
  reportfile.write_text(json.dumps(report,indent=2));print('ENCODED',profile,job,report[profile+'/'+job],flush=True)
  if profile=='desktop' and job=='turn':shutil.copyfile(target,O/'right-turn-review.mp4')
