import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

from media_runtime import av, np
from media_encoding import configure_stream
from split_route_media import prepare, digest


class SplitRouteTests(unittest.TestCase):
    def source(self, directory):
        source = Path(directory)/'h264.mp4'
        with av.open(str(source), 'w', options={'movflags': '+faststart'}) as output:
            stream, _, _, _ = configure_stream(output,32,32,'h264',17,6,'fast',30,'software')
            for index in range(18):
                frame=av.VideoFrame.from_ndarray(np.full((32,32,3),index*12,dtype=np.uint8),format='rgb24')
                frame=frame.reformat(format='yuv420p')
                frame.pts=index;frame.time_base=Fraction(1,30)
                for packet in stream.encode(frame):output.mux(packet)
            for packet in stream.encode():output.mux(packet)
        variant={'src':'/media/videos/desktop/route/h264.mp4','sha256':digest(source),
                 'bytes':source.stat().st_size,'frames':18,'fps':30,'width':32,'height':32,'gop':6,'codec':'h264'}
        return source,variant

    def test_copy_preserves_every_frame_and_zero_based_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            source,variant=self.source(directory)
            result,outputs=prepare(source,variant,6)
            self.assertEqual([p['frames'] for p in result['segments']],[6,12])
            self.assertEqual([p['startFrame'] for p in result['segments']],[0,6])
            self.assertNotIn('src',result)
            self.assertEqual(result['source_file']['sha256'],variant['sha256'])
            self.assertEqual(digest(source),variant['sha256'])
            self.assertTrue(all(temporary.exists() and not final.exists() for temporary,final,_,_ in outputs))

    def test_non_keyframe_cut_is_rejected_and_partial_outputs_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            source,variant=self.source(directory)
            with self.assertRaises(AssertionError):prepare(source,variant,7)
            self.assertEqual(list(Path(directory).glob('*.splitting.mp4')),[])
            self.assertEqual(digest(source),variant['sha256'])

    def test_size_limit_failure_keeps_the_original(self):
        with tempfile.TemporaryDirectory() as directory:
            source,variant=self.source(directory)
            with patch('split_route_media.MAX_BYTES',1):
                with self.assertRaisesRegex(AssertionError,'95 MiB'):prepare(source,variant,6)
            self.assertEqual(list(Path(directory).glob('*.splitting.mp4')),[])
            self.assertEqual(digest(source),variant['sha256'])


if __name__=='__main__':unittest.main()
