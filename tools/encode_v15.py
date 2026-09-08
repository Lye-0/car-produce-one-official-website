"""Encode lossless review frames into browser-playable H.264 review movies."""
import sys,json,os
from pathlib import Path
sys.path.insert(0,os.environ.get('CPO_PYTHON_VENDOR',str(Path(__file__).parent/'python_vendor')))
import av
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/previews/v15';OUT.mkdir(parents=True,exist_ok=True)
def encode(files,fps,name):
    target=OUT/name
    first=Image.open(files[0]);width,height=first.size
    with av.open(str(target),'w',options={'movflags':'+faststart'}) as container:
        stream=container.add_stream('libx264',rate=fps);stream.width=width;stream.height=height;stream.pix_fmt='yuv420p';stream.options={'crf':'18','preset':'medium'}
        for i,path in enumerate(files):
            with Image.open(path) as im:frame=av.VideoFrame.from_image(im.convert('RGB'))
            frame.pts=i
            for packet in stream.encode(frame):container.mux(packet)
        for packet in stream.encode():container.mux(packet)
    with av.open(str(target)) as container:
        stream=container.streams.video[0];count=sum(1 for _ in container.decode(stream))
        assert count==len(files),(count,len(files))
    result={'name':name,'frames':len(files),'fps':fps,'duration_s':len(files)/fps,'width':width,'height':height,'bytes':target.stat().st_size}
    print(json.dumps(result),flush=True);return result
jobs={
 'camera':(ROOT/'work/v15-motion/camera',151,30,'CPO_v15_camera_2323_30fps.mp4'),
 'prelude':(ROOT/'work/v15-studio/PRELUDE_SHOWROOM_rotation',192,24,'CPO_v15_Prelude_360.mp4'),
 'vezel':(ROOT/'work/v15-studio/VEZEL_SHOWROOM_rotation',192,24,'CPO_v15_Vezel_360.mp4'),
 'loop':(ROOT/'work/v15-motion/loop',384,8,'CPO_v15_city_loop.mp4'),
 'journey':(ROOT/'work/v15-motion/journey',720,8,'CPO_v15_full_journey.mp4'),
}
selected=sys.argv[1:] or list(jobs);results=[]
for name in selected:
    if name=='connection':
        loop=sorted((ROOT/'work/v15-motion/loop').glob('*.png'));arrival=sorted((ROOT/'work/v15-motion/journey').glob('*.png'))[:101]
        assert len(loop)==384 and len(arrival)==101
        results.append(encode(loop+loop+arrival,8,'CPO_v15_two_loops_then_arrival.mp4'));continue
    folder,count,fps,filename=jobs[name];files=sorted(folder.glob('*.png'));assert len(files)==count,(name,len(files),count)
    results.append(encode(files,fps,filename))
manifest=OUT/'video_manifest.json';previous=json.loads(manifest.read_text()) if manifest.exists() else {}
for result in results:previous[result['name']]=result
manifest.write_text(json.dumps(previous,indent=2),encoding='utf-8')
