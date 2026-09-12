"""Losslessly split route exports for bounded startup prefetch and Git file limits.

The encoder uses closed GOPs and no B frames. Each segment starts at an IDR,
keeps the original compressed packets, and has a zero-based local timeline.
"""
from pathlib import Path
from fractions import Fraction
from copy import deepcopy
import argparse
import hashlib
import itertools
import json

from media_runtime import av
from media_encoding import verify

SPLIT_FRAME = 1212  # 40.4 s, inside the tools hold (34.2 -> 43.2 s).
MAX_BYTES = 95 * 1024 * 1024


def digest(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def packet_records(path):
    with av.open(str(path)) as container:
        for packet in container.demux(video=0):
            if packet.size:
                yield (packet.pts * packet.time_base,
                       hashlib.sha256(bytes(packet)).digest())


def decoded_records(path):
    with av.open(str(path)) as container:
        for frame in container.decode(video=0):
            yield hashlib.sha256(frame.to_ndarray(format=frame.format.name)).digest()


def remux(source, target, start, end, fps):
    with av.open(str(source)) as container:
        stream = container.streams.video[0]
        assert len(container.streams) == 1, 'Only silent video is supported.'
        assert not stream.codec_context.has_b_frames, 'Reordered frames need a different remux contract.'
        assert stream.codec_context.name in ('h264', 'hevc')
        with av.open(str(target), 'w', options={'movflags': '+faststart'}) as output:
            result = output.add_stream_from_template(stream)
            result.time_base = stream.time_base
            origin = Fraction(start, fps) / stream.time_base
            assert origin.denominator == 1
            count = 0
            for index, packet in enumerate(p for p in container.demux(stream) if p.size):
                if index < start:
                    continue
                if index >= end:
                    break
                assert packet.pts == packet.dts
                assert packet.pts * packet.time_base == Fraction(index, fps)
                if count == 0:
                    assert packet.is_keyframe, 'Split point must be a keyframe.'
                packet.pts -= int(origin)
                packet.dts -= int(origin)
                packet.stream = result
                output.mux(packet)
                count += 1
            assert count == end - start


def prepare(source, variant, split_frame=None):
    """Prepare and verify all files before the manifest or source is changed."""
    source = Path(source)
    assert digest(source) == variant['sha256']
    assert source.stat().st_size == variant['bytes']
    cuts = [split_frame] if split_frame is not None else list(range(SPLIT_FRAME, variant['frames'] - 150, 300))
    assert all(0 < cut < variant['frames'] for cut in cuts)
    points = [0, *cuts, variant['frames']]
    ranges = list(zip(points, points[1:]))
    outputs = []
    try:
        for part, (start, end) in enumerate(ranges, 1):
            final = source.with_name(f"{variant['codec']}-part-{part}.mp4")
            temporary = final.with_suffix('.splitting.mp4')
            outputs.append((temporary, final, start, end))
            remux(source, temporary, start, end, variant['fps'])
            assert temporary.stat().st_size < MAX_BYTES, f'Segment exceeds 95 MiB: {temporary}'
            verify(temporary, end-start, variant['fps'], variant['width'],
                   variant['height'], variant['codec'], variant['gop'])

        # This compares every encoded packet and every decoded YUV frame, rather
        # than relying on similar-looking samples at the cut.
        packet_iter = itertools.chain.from_iterable(
            ((pts + Fraction(start, variant['fps']), checksum)
             for pts, checksum in packet_records(temporary))
            for temporary, _, start, _ in outputs)
        for expected, actual in itertools.zip_longest(packet_records(source), packet_iter):
            assert expected == actual, 'Compressed packet or timestamp changed.'
        frame_iter = itertools.chain.from_iterable(decoded_records(p) for p, _, _, _ in outputs)
        for expected, actual in itertools.zip_longest(decoded_records(source), frame_iter):
            assert expected == actual, 'Decoded frame differs from the source.'

        result = deepcopy(variant)
        result['source_file'] = {
            'sha256': result.pop('sha256'), 'bytes': result.pop('bytes'),
            'lossless_split': True,
        }
        base_url = result.pop('src').rsplit('/', 1)[0]
        result['segments'] = [
            {'src': f'{base_url}/{final.name}', 'startFrame': start,
             'frames': end-start, 'bytes': temporary.stat().st_size,
             'sha256': digest(temporary)}
            for temporary, final, start, end in outputs
        ]
        return result, outputs
    except BaseException:
        for temporary, _, _, _ in outputs:
            temporary.unlink(missing_ok=True)
        raise


def install(website):
    website = Path(website)
    path = website/'src/media/manifests/journey.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    prepared = []
    try:
        for profile in ('desktop', 'mobile'):
            for codec in ('hevc', 'h264'):
                variants = manifest['profiles'][profile]['route']['variants']
                index = next(i for i, v in enumerate(variants) if v['codec'] == codec)
                variant = variants[index]
                if 'segments' in variant:
                    for part in variant['segments']:
                        file = website/'public'/part['src'].lstrip('/')
                        assert file.stat().st_size == part['bytes'] and digest(file) == part['sha256']
                    print('ALREADY SPLIT', profile, codec, flush=True)
                    continue
                source = website/'public'/variant['src'].lstrip('/')
                result, outputs = prepare(source, variant)
                prepared.append((source, outputs))
                variants[index] = result
                print('LOSSLESS VERIFIED', profile, codec,
                      [(p['startFrame'], p['frames'], p['bytes']) for p in result['segments']], flush=True)
        for _, outputs in prepared:
            for temporary, final, _, _ in outputs:
                temporary.replace(final)
        if prepared:
            temporary_manifest = path.with_suffix('.splitting.json')
            temporary_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            temporary_manifest.replace(path)
            for source, _ in prepared:
                source.unlink()
    finally:
        for _, outputs in prepared:
            for temporary, _, _, _ in outputs:
                temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--website', type=Path, default=Path(__file__).resolve().parents[2]/'01_website')
    install(parser.parse_args().website)
