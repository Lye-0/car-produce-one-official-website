"""Verify the loop, shared junction entry, and native arrival endpoint."""
from pathlib import Path
import json
import av
import numpy as np
from PIL import Image,ImageFilter
R=Path(__file__).resolve().parents[1];O=R/'output/junction-work';WEB=R.parent/'01_website/public/media'
def rgb(im):return np.asarray(im.convert('RGB').filter(ImageFilter.GaussianBlur(2))).astype(float)
report={}
for profile in ['desktop','mobile']:
 first=Image.open(O/'drive'/profile/'0000.png');loop_end=Image.open(O/'drive'/profile/'endpoint.png');turn_first=Image.open(O/'turn'/profile/'0000.png')
 loop_error=float(abs(rgb(first)-rgb(loop_end)).mean());entry_error=float(abs(np.asarray(loop_end).astype(float)-np.asarray(turn_first).astype(float)).mean())
 assert loop_error<2,(profile,'loop seam',loop_error)
 assert entry_error<.05,(profile,'shared entry',entry_error)
 streams={};decoded={}
 for name,count,fps in [('drive',80,8),('turn',193,12)]:
  with av.open(str(WEB/'junction'/profile/(name+'.mp4'))) as reader:
   stream=reader.streams.video[0];assert float(stream.average_rate)==fps
   frames=list(reader.decode(stream));assert len(frames)==count and all(f.key_frame for f in frames)
   streams[name]={'frames':count,'fps':fps,'width':stream.width,'height':stream.height,'all_keyframes':True};decoded[name]=frames
 with av.open(str(WEB/'stage4'/profile/'route.mp4')) as old:arrival=next(old.decode(video=0)).to_image()
 end_error=float(abs(rgb(decoded['turn'][-1].to_image())-rgb(arrival)).mean());assert end_error<1.5,(profile,'native handoff',end_error)
 report[profile]={'loop_endpoint_blurred_rgb_mae':loop_error,'shared_entry_raw_rgb_mae':entry_error,'native_handoff_blurred_rgb_mae':end_error,'streams':streams}
report['passed']=True
(R/'reports/junction-media-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
