import test from 'node:test';
import assert from 'node:assert/strict';
import { preferredVariant, createMediaSourceController } from '../src/media-playback.ts';
const hevc = { src: 'h265.mp4', codec: 'hevc', fps: 30 };
const h264 = { src: 'h264.mp4', codec: 'h264', fps: 30 };
const asset = { variants: [hevc, h264] };
class Video extends EventTarget {
  src = ''; currentTime = 0; duration = 10; paused = true; loads = 0; plays = 0;
  load() { this.loads++; this.currentTime = 0; this.paused = true; }
  removeAttribute(name) { if (name === 'src') this.src = ''; }
  play() { this.paused = false; this.plays++; return Promise.resolve(); }
  pause() { this.paused = true; }
  emit(name) { this.dispatchEvent(new Event(name)); }
}
test('HEVC requires a positive capability result; unsupported and failed probes use H.264', async () => {
  assert.equal(await preferredVariant(asset, async () => true), hevc);
  assert.equal(await preferredVariant(asset, async () => false), h264);
  assert.equal(await preferredVariant(asset, async () => { throw Error('probe failed'); }), h264);
  await assert.rejects(preferredVariant({ variants: [hevc] }, async () => true), /fallback/);
});
test('decoder failure restores time and play state once, without fighting later scrubbing', async () => {
  const video = new Video(); const controller = createMediaSourceController(video);
  await controller.setSource(undefined, asset, async () => true);
  video.currentTime = 4.5; video.paused = false;
  assert.equal(controller.handleError(), true); assert.equal(video.src, 'h264.mp4');
  video.emit('loadedmetadata'); assert.equal(video.currentTime, 4.5);
  video.emit('loadeddata'); assert.equal(video.paused, false);
  video.currentTime = 2; video.emit('seeked'); assert.equal(video.currentTime, 2);
  assert.equal(controller.handleError(), false); controller.dispose();
});
test('paused scrub footage remains paused; current user pause overrides a failed playing stream', async () => {
  for (const desired of [undefined, false]) {
    const video = new Video(); const controller = createMediaSourceController(video, { playing: () => desired });
    await controller.setSource(undefined, asset, async () => true);
    video.currentTime = 7; video.paused = desired === undefined;
    controller.handleError(); video.emit('loadedmetadata'); video.emit('loadeddata');
    assert.equal(video.currentTime, 7); assert.equal(video.paused, true); controller.dispose();
  }
});
test('stale profile probes and disposed probes cannot overwrite the current source', async () => {
  const video = new Video(); const controller = createMediaSourceController(video);
  let resolve;
  const pending = controller.setSource(undefined, asset, () => new Promise(r => { resolve = r; }));
  await controller.setSource('mobile.mp4'); resolve(true); await pending;
  assert.equal(video.src, 'mobile.mp4');
  const disposed = controller.setSource(undefined, asset, () => new Promise(r => { resolve = r; }));
  controller.dispose(); resolve(true); await disposed; assert.equal(video.src, 'mobile.mp4');
});
test('legacy sources load synchronously and delayed metadata respects the latest playing intent', async () => {
  const video = new Video(); let playing = true;
  const controller = createMediaSourceController(video, { playing: () => playing });
  const pending = controller.setSource('legacy.mp4'); assert.equal(video.src, 'legacy.mp4'); await pending;
  playing = false; video.emit('loadeddata'); assert.equal(video.paused, true);
  controller.dispose();
});
