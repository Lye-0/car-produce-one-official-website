"""Small synthetic media checks; no Blender render or production files are changed."""
from pathlib import Path
import tempfile,unittest,struct,zlib,json
from unittest.mock import patch
from render_contract import valid_png,fingerprint,load_config
from media_encoding import read_png16,encode,decoded_srgb,SRGB_TRC
from media_runtime import np,av

def png16(path,rgb):
 h,w,_=rgb.shape
 def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
 raw=b''.join(b'\0'+row.astype('>u2').tobytes() for row in rgb)
 Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,16,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))

class MediaTests(unittest.TestCase):
 def test_precision_crc_and_incomplete_resume_input(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'ramp.png';rgb=np.arange(64*32*3,dtype=np.uint16).reshape(32,64,3);png16(path,rgb)
   self.assertTrue(valid_png(path,64,32,16));self.assertFalse(valid_png(path,64,32,8))
   np.testing.assert_array_equal(read_png16(path),rgb)
   data=path.read_bytes();path.write_bytes(data[:-5]);self.assertFalse(valid_png(path,64,32,16))
   corrupt=bytearray(data);corrupt[-20]^=1;path.write_bytes(corrupt);self.assertFalse(valid_png(path,64,32,16))
 def test_settings_and_source_changes_invalidate_bank(self):
  root=Path(__file__).resolve().parents[1];cfg=load_config(root);before=fingerprint(root,cfg)
  changed={**cfg,'samples':cfg['samples']+1};self.assertNotEqual(before,fingerprint(root,changed))
  self.assertEqual(before,fingerprint(root,{**cfg,'reserve_gib':99}))
 def test_transfer_and_real_dual_codec_decode(self):
  # A smooth neutral ramp is sensitive to transfer/range mistakes and 8-bit truncation.
  ramp=np.linspace(0,65535,128).round().astype(np.uint16)
  rgb=np.repeat(np.repeat(ramp[None,:,None],64,axis=0),3,axis=2)
  with tempfile.TemporaryDirectory() as temp:
   source=Path(temp)/'ramp.png';png16(source,rgb)
   for codec in ('hevc','h264'):
    target=Path(temp)/(codec+'.mp4');stats=encode([source]*7,target,128,64,codec,12,3,'fast')
    self.assertEqual(stats['frames'],7);self.assertTrue(stats['validated'])
    with av.open(str(target)) as container:
     self.assertEqual(container.streams.video[0].codec_context.color_trc,SRGB_TRC)
     decoded=decoded_srgb(next(container.decode(video=0)))
    error=decoded.astype(np.float64)-rgb
    psnr=20*np.log10(65535/np.sqrt(np.mean(error**2)))
    self.assertGreater(psnr,40,(codec,psnr))
    # Direct decoded sRGB dark values must match PNG, without an inverse gamma LUT.
    dark=(rgb>=3000)&(rgb<=14000)
    self.assertLess(abs(error[dark].mean()),600,(codec,error[dark].mean()))

 def test_gpu_failure_stops_preflight_without_silent_cpu_fallback(self):
  import package_media
  with patch.object(package_media,'probe_encoders',side_effect=RuntimeError('GPU unavailable')) as probe:
   with self.assertRaisesRegex(RuntimeError,'encoder preflight failed'):
    package_media.preflight()
   self.assertEqual(probe.call_count,1)
 def test_nvenc_requires_separate_quality_setting(self):
  with self.assertRaisesRegex(AssertionError,'explicit CQ'):
   encode(['not-read.png'],'not-written.mp4',1920,1080,'hevc',22,6,backend='nvenc')
 def test_nvenc_formats_and_loop_gop(self):
  import package_media
  from media_encoding import probe_encoders
  config=package_media.encoding_config()
  results=probe_encoders(config)
  self.assertEqual({(r['width'],r['height'],r['bit_depth']) for r in results},{(1920,1080,8),(1920,1080,10),(1080,1920,8),(1080,1920,10)})
  with tempfile.TemporaryDirectory() as temp:
   source=Path(temp)/'ramp.png'
   rgb=np.repeat(np.repeat(np.linspace(0,65535,256).round().astype(np.uint16)[None,:,None],144,axis=0),3,axis=2)
   png16(source,rgb)
   for codec in ('hevc','h264'):
    stats=encode([source]*31,Path(temp)/(codec+'.mp4'),256,144,codec,19,30,backend='nvenc',cq=config[codec+'_cq'],nvenc_preset=config['nvenc_preset'])
    self.assertEqual(stats['encoder'],codec+'_nvenc');self.assertEqual(stats['max_keyframe_gap'],30)
    self.assertEqual(stats['quality_mode'],'cq');self.assertEqual(stats['frames'],31)

 def test_pair_reads_each_png_once_and_packaging_resumes_one_failed_codec(self):
  import package_media,media_encoding
  from render_contract import QUALITY
  config=package_media.encoding_config();config={**config,'width':256,'height':144}
  cfg={**load_config(package_media.ROOT),'width':256,'height':144,'run_name':'fixture'}
  stamp={'fixture':'source-settings'}
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);scripts=root/'scripts';scripts.mkdir()
   for name in ('media_encoding.py','media_runtime.py','package_media.py'):(scripts/name).write_text('fixture')
   bank=root/'output/quality-fixture';folder=bank/'desktop/drive';folder.mkdir(parents=True)
   (bank/'render-settings.json').write_text(json.dumps(stamp))
   rgb=np.repeat(np.repeat(np.linspace(0,65535,256).round().astype(np.uint16)[None,:,None],144,axis=0),3,axis=2)
   for index in QUALITY['drive']:png16(folder/f'{index:05d}.png',rgb)
   png16(folder/'endpoint.png',rgb)
   (folder/'complete.json').write_text(json.dumps({'indices':QUALITY['drive'],'action':'quality','fps':30,'width':256,'height':144,'depth':16}))
   with patch.object(package_media,'ROOT',root),patch.object(package_media,'preflight',return_value=(cfg,config)),patch.object(package_media,'fingerprint',return_value=stamp):
    with patch.object(media_encoding,'read_png16',wraps=media_encoding.read_png16) as reader:
     out=package_media.package('quality','desktop','drive')
     self.assertEqual(reader.call_count,13) # One poster plus one read for each of 12 shared input frames.
    manifest=json.loads((out/'manifest.json').read_text());asset=manifest['profiles']['desktop']['drive']
    self.assertFalse(manifest['production']);self.assertEqual(asset['frames'],12)
    self.assertTrue(all(v['shared_input_pass'] for v in asset['variants']))
    self.assertTrue(all('\\' not in v['src'] for v in asset['variants']))
    with patch.object(package_media,'encode_pair',side_effect=AssertionError('Unexpected re-encode')),patch.object(package_media,'encode',side_effect=AssertionError('Unexpected re-encode')):
     package_media.package('quality','desktop','drive')
    damaged=out/next(v['src'] for v in asset['variants'] if v['codec']=='h264');damaged.write_bytes(b'truncated')
    with patch.object(package_media,'encode_pair',side_effect=AssertionError('Unexpected pair encode')),patch.object(package_media,'encode',wraps=media_encoding.encode) as single:
     package_media.package('quality','desktop','drive');self.assertEqual(single.call_count,1)
     self.assertEqual(single.call_args.args[4],'h264')

if __name__=='__main__':unittest.main()
