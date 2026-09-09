"""Encode two bounded motion checks; no retiming or frame interpolation."""
from pathlib import Path
import av,json,hashlib
from PIL import Image
R=Path(__file__).resolve().parents[1];O=R/'output/junction-work-v4'
provenance=json.loads((O/'short-provenance.json').read_text());assert provenance['source_sha256']==hashlib.sha256((R/'scene/CPO_MASTER.blend').read_bytes()).hexdigest()
clips=[]
for name,indices,source_frames in [('streetlife-short',range(90),list(range(240,330))),('streetlife-loop-boundary',range(90,150),list(range(570,600))+list(range(0,30)))]:
 target=R/'reports'/(name+'.mp4')
 with av.open(str(target),'w',options={'movflags':'+faststart'}) as out:
  stream=out.add_stream('libx264',rate=30);stream.width=640;stream.height=360;stream.pix_fmt='yuv420p';stream.options={'crf':'18','preset':'medium','g':'1'}
  for i,idx in enumerate(indices):
   frame=av.VideoFrame.from_image(Image.open(O/'short/desktop'/f'{idx:04d}.png').convert('RGB'));frame.pts=i
   for packet in stream.encode(frame):out.mux(packet)
  for packet in stream.encode():out.mux(packet)
 with av.open(str(target)) as reader:
  frames=list(reader.decode(video=0));assert len(frames)==len(indices);assert float(reader.streams.video[0].average_rate)==30
 clips.append({'file':target.name,'frames':len(indices),'source_frames':source_frames,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
report={'source_sha256':provenance['source_sha256'],'fps':30,'dimensions':[640,360],'clips':clips,'site_media_updated':False}
(R/'reports/streetlife-short-manifest.json').write_text(json.dumps(report,indent=2)+'\n');print('ENCODED',*[c['file'] for c in clips])
