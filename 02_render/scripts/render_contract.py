"""Render contract shared by the Blender entry point, packaging and tests."""
from pathlib import Path
import hashlib,json,struct,zlib

COUNTS={'drive':600,'junction':481,'route':2430,'portal':271,'tools-idle':180,'magazines-idle':180,'monitor-idle':180}
HOLDS={'tools-idle':1026,'magazines-idle':1701,'monitor-idle':2430}
QUALITY={'drive':[0,*range(240,252),599],'junction':[0,180,270,480],'route':[0,1026,1701,2429],'portal':[0,*range(120,180),240,270],**{k:[0,90] for k in HOLDS}}
RENDER_KEYS=('width','height','fps','samples','noise_threshold','min_samples','color_depth','color_mode','denoiser','denoising_use_gpu','max_bounces','caustics_reflective','caustics_refractive','motion_blur','device','require_gpu')

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load_config(root):
 cfg=json.loads((Path(root)/'settings.json').read_text(encoding='utf-8-sig'))
 assert cfg['fps']==30,'Camera tracking and frame mappings require 30 fps.'
 assert cfg['width']>0 and cfg['height']>0 and cfg['samples']>0
 assert 1<=cfg['max_bounces']<=1024
 assert isinstance(cfg['caustics_reflective'],bool) and isinstance(cfg['caustics_refractive'],bool)
 assert cfg['color_depth'] in (8,16) and cfg['color_mode']=='RGB'
 assert cfg['run_name'] and all(c.isalnum() or c in '-_' for c in cfg['run_name'])
 return cfg

def fingerprint(root,cfg):
 root=Path(root)
 return {'master_sha256':digest(root/'scene/CPO_MASTER.blend'),'settings':{k:cfg[k] for k in RENDER_KEYS},'renderer_sha256':digest(root/'scripts/render.py'),'contract_sha256':digest(root/'scripts/render_contract.py')}

def valid_png(path,w,h,depth):
 """Check dimensions, precision, every chunk CRC and a complete PNG terminator."""
 try:
  with Path(path).open('rb') as f:
   if f.read(8)!=b'\x89PNG\r\n\x1a\n':return False
   first=True;seen_data=False
   while True:
    header=f.read(8)
    if len(header)!=8:return False
    size,kind=struct.unpack('>I4s',header)
    if size>256*1024*1024:return False
    data=f.read(size);crc=f.read(4)
    if len(data)!=size or len(crc)!=4 or zlib.crc32(kind+data)&0xffffffff!=struct.unpack('>I',crc)[0]:return False
    if first:
     if kind!=b'IHDR' or len(data)!=13:return False
     iw,ih,bits,color,*_=struct.unpack('>IIBBBBB',data)
     if (iw,ih,bits,color)!=(w,h,depth,2):return False
     first=False
    if kind==b'IDAT':seen_data=True
    if kind==b'IEND':return size==0 and seen_data and not f.read(1)
 except (OSError,ValueError,struct.error):return False

def indices(action,job):
 if action=='sample':return [{'drive':240,'junction':180,'route':1026,'portal':120,**{k:0 for k in HOLDS}}[job]]
 if action=='quality':return QUALITY[job]
 if action=='test':return [0,240,480] if job=='junction' else [0,599] if job=='drive' else [0]
 return list(range(COUNTS[job]))

def source_frame(job,index):
 if job in HOLDS:return HOLDS[job]
 if job=='junction':return 600+index
 if job=='portal':return 2430+index
 if job=='route' and index==2429:return 2430
 return index

def expected_images():return 2*(sum(COUNTS.values())+1+len(HOLDS))


