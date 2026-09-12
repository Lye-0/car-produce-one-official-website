import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createSegmentedPlayback,
  segmentTarget,
  mediaSegments,
} from '../src/media/segmented-playback.ts';

const parts = [
  { src: 'part-1.mp4', startFrame: 0, frames: 1212 },
  { src: 'part-2.mp4', startFrame: 1212, frames: 1218 },
];
const hevc = { codec: 'hevc', src: 'hevc.mp4', fps: 30 };
const h264 = { codec: 'h264', segments: parts, fps: 30 };
const asset = { frames: 2430, fps: 30, variants: [hevc, h264] };
class Video extends EventTarget {
  dataset = {};
  src = '';
  readyState = 0;
  seeking = false;
  paused = true;
  time = 0;
  requests = [];
  seeks = [];
  get currentTime() {
    return this.time;
  }
  set currentTime(time) {
    this.time = time;
    this.seeks.push(time);
    this.seeking = true;
  }
  pause() {
    this.paused = true;
  }
  load() {
    this.time = 0;
    this.readyState = 0;
    this.seeking = false;
    if (this.src) this.requests.push(this.src);
  }
  removeAttribute(name) {
    if (name === 'src') this.src = '';
  }
  metadata() {
    this.readyState = 1;
    this.dispatchEvent(new Event('loadedmetadata'));
  }
  complete() {
    this.readyState = 2;
    this.seeking = false;
    this.dispatchEvent(new Event('seeked'));
  }
}
function fixture() {
  const videos = [new Video(), new Video()],
    ready = [],
    errors = [];
  const controller = createSegmentedPlayback(videos, {
    onReady: (v) => ready.push(v),
    onError: () => errors.push(true),
  });
  return { videos, ready, errors, controller };
}
const finish = (video) => {
  if (video.readyState === 0) video.metadata();
  video.complete();
};

test('every global route frame maps to exactly one local frame, including both sides of the split', () => {
  for (let frame = 0; frame < 2430; frame++) {
    const target = segmentTarget(parts, 2430, 30, frame / 30);
    assert.equal(target.frame, frame);
    assert.equal(target.localFrame + parts[target.index].startFrame, frame);
    assert.equal(Math.floor(target.time * 30), target.localFrame);
  }
  assert.equal(segmentTarget(parts, 2430, 30, 40.4).index, 1);
  assert.equal(segmentTarget(parts, 2430, 30, 90).frame, 2429);
  assert.equal(segmentTarget(parts, 2430, 30, -1).frame, 0);
  assert.equal(segmentTarget(parts, 2430, 30, NaN).frame, 0);
  assert.deepEqual(mediaSegments(hevc, 2430), [
    { src: 'hevc.mp4', startFrame: 0, frames: 2430 },
  ]);
});

test('only the needed fallback part loads initially; neighboring parts warm during the tools hold', async () => {
  const {
    controller: c,
    videos: [a, b],
    ready,
  } = fixture();
  await c.setMedia(asset, async () => false);
  assert.deepEqual(a.requests, ['part-1.mp4']);
  assert.deepEqual(b.requests, []);
  finish(a);
  assert.equal(a.dataset.mediaActive, 'true');
  assert.deepEqual(ready, [true]);
  c.seek(34.2);
  assert.deepEqual(b.requests, ['part-2.mp4']);
  finish(a);
  finish(b);
  assert.equal(a.dataset.mediaActive, 'true');
  assert.equal(b.dataset.mediaActive, 'false');
  c.dispose();
});

test('the old decoded image stays active until the requested part is decoded; reverse seeks reuse sources', async () => {
  const {
    controller: c,
    videos: [a, b],
  } = fixture();
  await c.setMedia(asset, async () => false);
  finish(a);
  c.seek(40.4);
  assert.equal(a.dataset.mediaActive, 'true');
  assert.equal(b.dataset.mediaActive, 'false');
  finish(b);
  assert.equal(a.dataset.mediaActive, 'false');
  assert.equal(b.dataset.mediaActive, 'true');
  assert.equal(b.dataset.mediaFrame, '1212');
  // The outgoing part is being warmed at its final frame. Its completion must
  // not replace the currently requested part.
  a.complete();
  assert.equal(b.dataset.mediaActive, 'true');
  c.seek(1211 / 30);
  assert.equal(a.dataset.mediaActive, 'true');
  assert.equal(a.dataset.mediaFrame, '1211');
  assert.equal(a.requests.length, 1);
  assert.equal(b.requests.length, 1);
  c.dispose();
});

test('rapid alternating seeks finish at the last request even if the other decoder completes later', async () => {
  const {
    controller: c,
    videos: [a, b],
  } = fixture();
  await c.setMedia(asset, async () => false);
  finish(a);
  c.seek(55);
  b.metadata();
  c.seek(12);
  c.seek(60);
  c.seek(20);
  a.complete();
  a.complete();
  b.complete();
  assert.equal(a.dataset.mediaActive, 'true');
  assert.equal(a.dataset.mediaFrame, '600');
  assert.equal(b.dataset.mediaActive, 'false');
  assert.equal(a.currentTime, 600.5 / 30);
  c.dispose();
});

test('direct late entry does not load part one, and decoder fallback preserves the global playhead', async () => {
  const {
    controller: c,
    videos: [a, b],
    errors,
  } = fixture();
  c.seek(79);
  await c.setMedia(asset, async () => true);
  finish(a);
  assert.equal(a.dataset.mediaFrame, '2370');
  a.dispatchEvent(new Event('error'));
  assert.equal(b.src, 'part-2.mp4');
  assert.deepEqual(a.requests, ['hevc.mp4']);
  finish(b);
  assert.equal(b.dataset.mediaStartFrame, '1212');
  assert.equal(b.dataset.mediaFrame, '2370');
  assert.equal(b.currentTime, (2370 - 1212 + 0.5) / 30);
  b.dispatchEvent(new Event('error'));
  assert.equal(errors.length, 1);
  b.dispatchEvent(new Event('error'));
  assert.equal(errors.length, 1);
  c.dispose();
});

test('stale codec probes, disabled media and disposed decoders cannot restore old sources', async () => {
  const {
    controller: c,
    videos: [a, b],
    errors,
  } = fixture();
  let resolve;
  const pending = c.setMedia(
    asset,
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  await c.setMedia(undefined);
  resolve(true);
  await pending;
  assert.equal(a.src, '');
  assert.equal(b.src, '');
  await c.setMedia(asset, async () => false);
  finish(a);
  c.dispose();
  a.dispatchEvent(new Event('error'));
  a.complete();
  assert.equal(a.src, '');
  assert.equal(b.src, '');
  assert.equal(errors.length, 0);
});

test('missing timeline coverage is rejected instead of playing a wrong segment', async () => {
  const { controller: c, errors } = fixture();
  await c.setMedia(
    {
      ...asset,
      variants: [
        { ...h264, segments: [parts[0], { ...parts[1], startFrame: 1213 }] },
      ],
    },
    async () => false,
  );
  assert.equal(errors.length, 1);
  c.dispose();
});

test('five parts reuse two decoder slots while preserving global frames in both directions', async () => {
  const starts = [0, 1212, 1512, 1812, 2112],
    ends = [1212, 1512, 1812, 2112, 2430];
  const segmented = {
    frames: 2430,
    fps: 30,
    variants: [
      {
        codec: 'h264',
        segments: starts.map((startFrame, i) => ({
          src: `p${i}.mp4`,
          startFrame,
          frames: ends[i] - startFrame,
        })),
      },
    ],
  };
  const { controller: c, videos } = fixture();
  await c.setMedia(segmented, async () => false);
  for (const time of [0, 34.2, 43.2, 52, 68, 75, 80.9666667, 68, 52, 34.2, 0]) {
    c.seek(time);
    for (let tick = 0; tick < 8; tick++)
      for (const video of videos) {
        if (video.src && video.readyState === 0) video.metadata();
        if (video.seeking) video.complete();
      }
    const active = videos.filter((v) => v.dataset.mediaActive === 'true');
    assert.equal(active.length, 1);
    assert.equal(
      +active[0].dataset.mediaFrame,
      Math.min(2429, Math.round(time * 30)),
    );
  }
  assert(videos.every((video) => video.requests.length > 1));
  c.dispose();
});
