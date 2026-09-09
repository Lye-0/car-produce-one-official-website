"""Validate arbitrary city phases, cabin stability, and delivered video endpoints."""
from pathlib import Path
import json
import av
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'output/corner-work';WEB=ROOT.parent/'01_website/public/media'
meta=json.loads((WORK/'corner-tracking.json').read_text());report={}
for profile in ['desktop','mobile']:
 target=WEB/'corner'/profile/'corner.mp4'
 if not target.exists():raise RuntimeError('Missing '+str(target))
 with av.open(str(target)) as reader:
  stream=reader.streams.video[0];frames=[f.to_image().convert('RGBA') for f in reader.decode(stream)]
 assert len(frames)==97
 with av.open(str(WEB/'stage4'/profile/'city.mp4')) as reader:
  phases=[f.to_image().convert('RGBA') for i,f in enumerate(reader.decode(video=0)) if i in [0,96,192,288]]
 w,h=frames[0].size;phases=[im.resize((w,h),Image.Resampling.LANCZOS) for im in phases]
 foreground=Image.open(WEB/'stage4'/profile/'car-foreground.png').convert('RGBA').resize((w,h),Image.Resampling.LANCZOS)
 opaque=np.asarray(foreground)[:,:,3]==255
 assert opaque.sum()>w*h*.2
 composites={}
 for f in [0,30,46,47,48,49,50,72,96]:
  mask=Image.new('L',(w,h),255 if f>=48 else 0)
  if f<48:ImageDraw.Draw(mask).polygon([(x*w,y*h) for x,y in meta['profiles'][profile][f]['polygon']],fill=255)
  if f==0:assert mask.getbbox() is None
  composites[f]=[]
  for background in phases:
   mixed=Image.composite(frames[f],background,mask);mixed=Image.alpha_composite(mixed,foreground)
   composites[f].append(np.asarray(mixed).astype(int))
 cut_difference=max(int(abs(composites[f][i]-composites[f][0]).max()) for f in [46,47,48,49,50] for i in range(4))
 cabin_difference=max(int(abs(composites[f][0]-composites[0][0])[opaque].max()) for f in composites)
 assert cut_difference==0,(profile,'city phase leak',cut_difference)
 assert cabin_difference==0,(profile,'cabin moved',cabin_difference)
 with av.open(str(WEB/'stage4'/profile/'route.mp4')) as route:
  source=next(route.decode(video=0)).to_image().convert('RGB').resize((w,h),Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(2))
 end=frames[-1].convert('RGB').filter(ImageFilter.GaussianBlur(2))
 endpoint_mae=float(abs(np.asarray(source).astype(float)-np.asarray(end).astype(float)).mean())
 # Allow <0.6% RGB range for the additional 8-bit YUV420 encode/decode round trip.
 assert endpoint_mae<1.5,(profile,'endpoint mismatch',endpoint_mae)
 report[profile]={'decoded_frames':97,'fps':30,'size':[w,h],'city_phases':[0,.25,.5,.75],'cut_frames_checked':[46,47,48,49,50],'cut_background_max_difference':cut_difference,'opaque_cabin_max_difference':cabin_difference,'encoded_endpoint_blurred_rgb_mae':endpoint_mae}
 preview=Image.fromarray(composites[30][0].astype('uint8'));preview.save(WORK/f'{profile}-composite-preview.png')
report['passed']=True
(ROOT/'reports/corner-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
