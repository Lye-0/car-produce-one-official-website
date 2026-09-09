"""Encode the corner preview as independently seekable H.264 frames."""
from pathlib import Path
import sys,json,hashlib
import av
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'output/corner-work';WEB=ROOT.parent/'01_website/public/media/corner'
selected=sys.argv[1:] or ['desktop','mobile']
report={}
for profile in selected:
 files=sorted((WORK/'frames'/profile).glob('[0-9][0-9][0-9][0-9].png'))
 if len(files)!=97:print('PENDING',profile,len(files),flush=True);continue
 folder=WEB/profile;folder.mkdir(parents=True,exist_ok=True);destination=folder/'corner.mp4';temporary=folder/'corner.build.mp4'
 with Image.open(files[0]) as im:w,h=im.size
 # Conform the last, already-aligned preview frames to the deployed route plate.
 # This compensates for its lower resolution/sampling, without blurring the turn.
 with av.open(str(ROOT.parent/'01_website/public/media/stage4'/profile/'route.mp4')) as route:
  endpoint=next(route.decode(video=0)).to_image().convert('RGB').resize((w,h),Image.Resampling.BILINEAR)
 with av.open(str(temporary),'w',options={'movflags':'+faststart'}) as out:
  stream=out.add_stream('libx264',rate=30);stream.width=w;stream.height=h;stream.pix_fmt='yuv420p';stream.options={'crf':'18','preset':'medium','g':'1','keyint_min':'1','bf':'0','sc_threshold':'0'}
  for i,path in enumerate(files):
   with Image.open(path) as im:rgb=im.convert('RGB')
   if i>=94:rgb=Image.blend(rgb,endpoint,(i-93)/3)
   frame=av.VideoFrame.from_image(rgb)
   frame.pts=i
   for packet in stream.encode(frame):out.mux(packet)
  for packet in stream.encode():out.mux(packet)
 with av.open(str(temporary)) as check:
  frames=list(check.decode(video=0));assert len(frames)==97;assert all(f.key_frame for f in frames)
 assert temporary.stat().st_size<25*1024*1024
 temporary.replace(destination)
 report[profile]={'frames':97,'fps':30,'width':w,'height':h,'all_keyframes':True,'preview_endpoint_conform_frames':[94,95,96],'bytes':destination.stat().st_size,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}
 print('ENCODED',profile,report[profile],flush=True)
reportfile=WORK/'encoded-media.json'
previous=json.loads(reportfile.read_text()) if reportfile.exists() else {};previous.update(report);reportfile.write_text(json.dumps(previous,indent=2))
