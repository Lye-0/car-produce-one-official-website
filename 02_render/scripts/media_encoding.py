"""16-bit sRGB PNG -> sRGB transfer with BT.709 primaries/matrix, SDR limited range."""
from pathlib import Path
from fractions import Fraction
import json,hashlib,time,tempfile
from contextlib import ExitStack
from media_runtime import av,np,Image
from av.video.reformatter import Colorspace,ColorRange,Interpolation

# Keep the PNG transfer function: converting dark sRGB values to BT.709 OETF
# made browser video darker than the same image. Signal IEC 61966-2-1 (13)
# explicitly; the YUV matrix/primaries remain BT.709 and levels remain limited.
SRGB_TRC=13

def read_png16(path):
 with av.open(str(path)) as source:frame=next(source.decode(video=0))
 assert max(c.bits for c in frame.format.components)>=16,(path,frame.format.name)
 return frame.to_ndarray(format='rgb48le')

def format_frame(frame,w,h,depth,pixel_format=None):
 result=frame.reformat(width=w,height=h,format=pixel_format or ('yuv420p10le' if depth==10 else 'yuv420p'),src_colorspace=Colorspace.ITU709,dst_colorspace=Colorspace.ITU709,src_color_range=ColorRange.JPEG,dst_color_range=ColorRange.MPEG,interpolation=Interpolation.LANCZOS,dst_color_trc=SRGB_TRC,dst_color_primaries=1)
 result.color_range=1;result.colorspace=1;result.color_trc=SRGB_TRC;result.color_primaries=1
 return result

def encode_frame(rgb,w,h,depth,pixel_format=None):
 frame=av.VideoFrame.from_ndarray(rgb,format='rgb48le')
 return format_frame(frame,w,h,depth,pixel_format)

def decoded_srgb(frame):
 frame=frame.reformat(format='rgb48le',src_colorspace=Colorspace.ITU709,dst_colorspace=Colorspace.ITU709,src_color_range=ColorRange.MPEG,dst_color_range=ColorRange.JPEG)
 return frame.to_ndarray()

def codec_string(context):
 data=context.extradata
 if context.name=='h264':return 'avc1.'+data[1:4].hex().upper()
 assert data[0]==1,'Expected hvcC configuration record'
 space=['','A','B','C'][data[1]>>6];profile=data[1]&31;tier='H' if data[1]&32 else 'L'
 compat=int(f'{int.from_bytes(data[2:6],"big"):032b}'[::-1],2)
 constraints=list(data[6:12])
 while constraints and constraints[-1]==0:constraints.pop()
 return f'hvc1.{space}{profile}.{compat:X}.{tier}{data[12]}'+''.join(f'.{v:02X}' for v in constraints)

def configure_stream(output,w,h,codec,quality,gop,preset,fps,backend):
 assert codec in ('hevc','h264') and backend in ('nvenc','software')
 assert gop>=1 and fps>=1 and w>0 and h>0 and not w%2 and not h%2
 depth=10 if codec=='hevc' else 8
 encoder=(codec+'_nvenc') if backend=='nvenc' else ('libx265' if codec=='hevc' else 'libx264')
 pixel_format=('p010le' if backend=='nvenc' else 'yuv420p10le') if depth==10 else 'yuv420p'
 stream=output.add_stream(encoder,rate=fps);stream.width=w;stream.height=h;stream.pix_fmt=pixel_format
 context=stream.codec_context;context.color_range=1;context.colorspace=1;context.color_trc=SRGB_TRC;context.color_primaries=1
 if backend=='nvenc':
  # CQ and software CRF are independent quality scales. Never substitute one silently.
  context.bit_rate=0
  options={'preset':preset,'tune':'hq','rc':'vbr','cq':str(quality),'b':'0','g':str(gop),'bf':'0','no-scenecut':'1','forced-idr':'1'}
  if codec=='hevc':options['profile']='main10'
  else:options['profile']='high'
 else:
  options={'crf':str(quality),'preset':preset,'g':str(gop),'keyint_min':str(gop),'bf':'0','sc_threshold':'0'}
  if codec=='hevc':options.update(profile='main10',**{'x265-params':f'keyint={gop}:min-keyint={gop}:scenecut=0:bframes=0:open-gop=0:log-level=error:pools=8'})
 if codec=='hevc':context.codec_tag='hvc1'
 stream.options=options
 return stream,depth,pixel_format,encoder

def write_rgb_sequences(arrays,targets,w,h,qualities,gop,preset,fps,backend):
 # Each PNG and transfer conversion is shared by both encoders. Memory stays bounded to a frame.
 encoders={}
 with ExitStack() as stack:
  streams=[]
  for codec,target in targets.items():
   output=stack.enter_context(av.open(str(target),'w',options={'movflags':'+faststart'}))
   stream,depth,pixel_format,encoder=configure_stream(output,w,h,codec,qualities[codec],gop,preset,fps,backend)
   streams.append((output,stream,depth,pixel_format));encoders[codec]=encoder
  for i,rgb in enumerate(arrays):
   rgb_frame=av.VideoFrame.from_ndarray(rgb,format='rgb48le')
   for output,stream,depth,pixel_format in streams:
    frame=format_frame(rgb_frame,w,h,depth,pixel_format);frame.pts=i;frame.time_base=Fraction(1,fps)
    for packet in stream.encode(frame):output.mux(packet)
   if i>0 and i%60==0:print('ENCODING_FRAME',i,flush=True)
  for output,stream,_,_ in streams:
   for packet in stream.encode():output.mux(packet)
 return encoders

def write_rgb_sequence(arrays,target,w,h,codec,quality,gop,preset,fps,backend):
 return write_rgb_sequences(arrays,{codec:target},w,h,{codec:quality},gop,preset,fps,backend)[codec]

def encode(files,target,w,h,codec,crf,gop,preset='slow',fps=30,*,backend='software',cq=None,nvenc_preset='p7'):
 assert files,'Cannot encode an empty sequence'
 assert backend in ('nvenc','software')
 if backend=='nvenc':
  assert cq is not None,'NVENC requires an explicit CQ; software CRF is not reused'
  quality=cq;selected_preset=nvenc_preset
 else:quality=crf;selected_preset=preset
 target=Path(target);target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix('.build.mp4');started=time.perf_counter()
 encoder=write_rgb_sequence((read_png16(path) for path in files),temp,w,h,codec,quality,gop,selected_preset,fps,backend)
 stats=verify(temp,len(files),fps,w,h,codec,gop);temp.replace(target)
 stats.update(src=target.name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),encode_seconds=time.perf_counter()-started,encoder=encoder,backend=backend,quality_mode='cq' if backend=='nvenc' else 'crf',quality=quality,gop=gop,preset=selected_preset,bitrate=round(target.stat().st_size*8/(len(files)/fps)))
 return stats

def encode_pair(files,targets,w,h,gop,config,fps=30):
 assert files and set(targets)=={'hevc','h264'}
 backend=config['backend'];preset=config['nvenc_preset'] if backend=='nvenc' else config['preset']
 qualities={codec:config[codec+('_cq' if backend=='nvenc' else '_crf')] for codec in targets}
 targets={codec:Path(path) for codec,path in targets.items()}
 for path in targets.values():path.parent.mkdir(parents=True,exist_ok=True)
 temporary={codec:path.with_suffix('.build.mp4') for codec,path in targets.items()};started=time.perf_counter()
 encoders=write_rgb_sequences((read_png16(path) for path in files),temporary,w,h,qualities,gop,preset,fps,backend)
 # Verify both before replacing either final output. The manifest is written after both succeed.
 records={codec:verify(path,len(files),fps,w,h,codec,gop) for codec,path in temporary.items()}
 elapsed=time.perf_counter()-started
 for codec,path in targets.items():
  temporary[codec].replace(path)
  records[codec].update(src=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),encode_seconds=elapsed,encode_seconds_scope='hevc+h264 pair',shared_input_pass=True,encoder=encoders[codec],backend=backend,quality_mode='cq' if backend=='nvenc' else 'crf',quality=qualities[codec],gop=gop,preset=preset,bitrate=round(path.stat().st_size*8/(len(files)/fps)))
 return records

def probe_encoders(config):
 """Test the actual GPU driver, dual encoder sessions and portrait Main10 before rendering."""
 backend=config['backend'];results=[]
 with tempfile.TemporaryDirectory(prefix='cpo-encoder-check-') as temp:
  for w,h in ((config['width'],config['height']),(config['height'],config['width'])):
   rgb=np.full((h,w,3),32768,dtype=np.uint16)
   targets={codec:Path(temp)/f'{codec}-{w}x{h}.mp4' for codec in ('hevc','h264')}
   qualities={codec:config[codec+('_cq' if backend=='nvenc' else '_crf')] for codec in targets}
   encoders=write_rgb_sequences((rgb for _ in range(7)),targets,w,h,qualities,config['scroll_gop'],config['nvenc_preset'] if backend=='nvenc' else config['preset'],30,backend)
   for codec,target in targets.items():
    result=verify(target,7,30,w,h,codec,config['scroll_gop']);result['encoder']=encoders[codec];results.append(result)
 return results

def verify(path,count,fps,w,h,codec,gop):
 seen=0;last_key=0;max_gap=0
 with av.open(str(path)) as source:
  stream=source.streams.video[0];context=stream.codec_context
  assert float(stream.average_rate)==fps and context.name==('hevc' if codec=='hevc' else 'h264')
  assert (context.width,context.height)==(w,h)
  assert (context.color_primaries,context.color_trc,context.colorspace,context.color_range)==(1,SRGB_TRC,1,1)
  codecs=codec_string(context)
  for i,frame in enumerate(source.decode(video=0)):
   assert abs(float(frame.pts*frame.time_base)-i/fps)<1e-6
   if i==0:assert frame.key_frame
   if frame.key_frame:max_gap=max(max_gap,i-last_key);last_key=i
   assert i-last_key<gop
   assert max(c.bits for c in frame.format.components)==(10 if codec=='hevc' else 8)
   seen+=1
 assert seen==count,(seen,count)
 data=Path(path).read_bytes();assert data.find(b'moov')<data.find(b'mdat'),'MP4 is not fast-start'
 return {'codec':codec,'type':f'video/mp4; codecs="{codecs}"','frames':count,'fps':fps,'width':w,'height':h,'bit_depth':10 if codec=='hevc' else 8,'color':'sRGB transfer / BT.709 primaries and matrix / SDR limited range','color_transfer':SRGB_TRC,'max_keyframe_gap':max_gap,'validated':True}

def poster(path,target,width=1280):
 rgb=read_png16(path);im=Image.fromarray((rgb/257).round().astype(np.uint8),'RGB');im.thumbnail((width,width),Image.Resampling.LANCZOS);im.save(target,quality=90,method=6)
