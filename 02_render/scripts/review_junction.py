"""Make a 3-cycle + turn review from the exact deployed frames, without retiming."""
from pathlib import Path
import av,sys
R=Path(__file__).resolve().parents[1];O=R/'output/junction-work-v3';WEB=R.parent/'01_website/public/media/junction'
if '--staged' in sys.argv:WEB=O/'media'
for profile in ([p for p in sys.argv[1:] if p!='--staged'] or ['desktop','mobile']):
    assert profile in ('desktop','mobile'),profile
    for name,count in [('drive',600),('turn',481)]:
        with av.open(str(WEB/profile/(name+'.mp4'))) as source:
            track=source.streams.video[0]
            assert float(track.average_rate)==30 and track.frames==count,'Encode the new 20-second/30fps drive and 16-second/30fps turn before making a review.'
    target=O/('loop-and-turn-'+profile+'.mp4')
    with av.open(str(target),'w',options={'movflags':'+faststart'}) as output:
        stream=None;index=0
        for name in ['drive','drive','drive','turn']:
            with av.open(str(WEB/profile/(name+'.mp4'))) as source:
                for frame in source.decode(video=0):
                    if stream is None:
                        stream=output.add_stream('libx264',rate=30);stream.width=frame.width;stream.height=frame.height;stream.pix_fmt='yuv420p';stream.options={'crf':'18','preset':'medium','g':'30'}
                    frame=av.VideoFrame.from_ndarray(frame.to_ndarray(format='rgb24'),format='rgb24');frame.pts=index;index+=1
                    for packet in stream.encode(frame):output.mux(packet)
        for packet in stream.encode():output.mux(packet)
    assert index==2281,index
    print('REVIEW',profile,target,flush=True)
