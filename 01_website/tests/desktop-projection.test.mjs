import test from 'node:test';
import assert from 'node:assert/strict';
import rows from '../src/desktop-screen-tracking.json' with { type: 'json' };
import {
  desktopProjection,
  projectPoint,
  IDENTITY_TRANSFORM,
  screenPower,
} from '../src/desktop-projection.ts';
import { containsPoint } from '../src/screen-projection.ts';
for (const view of [
  { width: 1280, height: 720 },
  { width: 1440, height: 900 },
  { width: 1680, height: 720 },
  { width: 900, height: 900 },
  { width: 760, height: 1400 },
  { width: 2560, height: 1080 },
]) {
  test(
    'PC endpoint exactly matches native page at ' +
      view.width +
      'x' +
      view.height,
    () => {
      const end = desktopProjection(rows, 2700, view);
      assert.equal(end.transform, IDENTITY_TRANSFORM);
      for (const [x, y] of [
        [0, 0],
        [view.width, 0],
        [view.width, view.height],
        [0, view.height],
        [view.width * 0.37, view.height * 0.61],
      ]) {
        assert.deepEqual(projectPoint(end.matrix, x, y), [x, y]);
        assert(containsPoint(end.quad, [x, y]));
      }
    },
  );
  test(
    'PC projection remains invertible, finite, and reversible at ' +
      view.width +
      'x' +
      view.height,
    () => {
      for (let f = 2340; f <= 2700; f += 0.5) {
        const a = desktopProjection(rows, f, view),
          b = desktopProjection(rows, f, view);
        assert.deepEqual(a, b);
        assert(a.matrix.every(Number.isFinite));
        const end = desktopProjection(rows, 2700, view);
        end.quad.forEach(([x, y], i) => {
          const mapped = projectPoint(a.matrix, x, y);
          assert(
            Math.hypot(mapped[0] - a.quad[i][0], mapped[1] - a.quad[i][1]) <
              1e-6,
          );
        });
      }
    },
  );
}
test('power-on starts dark and reaches full content before the monitor hold', () => {
  assert.equal(screenPower(2370), 0);
  assert.equal(screenPower(2424), 1);
  assert.equal(screenPower(2430), 1);
  let previous = 0;
  for (let f = 2370; f <= 2424; f++) {
    const next = screenPower(f);
    assert(next >= previous);
    previous = next;
  }
});

test('PC scrubbing selects the last frame center despite rounded MP4 duration', async () => {
  const { createVideoScrubber } = await import('../src/journey-timeline.ts');
  const video = {
    currentTime: 0,
    duration: 9.033332,
    readyState: 2,
    seeking: false,
    pause() {},
    addEventListener() {},
    removeEventListener() {},
  };
  const driver = createVideoScrubber(video, 30, true);
  driver.seek(9);
  assert(Math.abs(video.currentTime - 9.0166666667) < 1e-8);
  driver.seek(9.1);
  assert(video.currentTime < video.duration);
  driver.seek(0);
  assert.equal(video.currentTime, 0.5 / 30);
  driver.dispose();
});
