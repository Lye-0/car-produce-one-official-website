import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { sampleJourney } from '../src/journey-timeline.ts';
import {
  CORNER_END,
  CORNER_CUT_FRAME,
  CORNER_LAST_FRAME,
  cornerFrame,
  cornerProgress,
  coversViewport,
  coverPolygon,
} from '../src/corner-transition.ts';
const tracking = JSON.parse(
  readFileSync(new URL('../src/corner-tracking.json', import.meta.url), 'utf8'),
);

test('street reset has full solid cover before, during and after the cut in both orientations', () => {
  for (const profile of ['desktop', 'mobile']) {
    for (let f = CORNER_CUT_FRAME - 2; f <= CORNER_CUT_FRAME + 2; f++) {
      assert.ok(
        coversViewport(tracking.profiles[profile][f].polygon),
        `${profile}, frame ${f}`,
      );
    }
  }
});
test('cover cropping cannot expose any background at the cut on narrow or wide viewports', () => {
  for (const [profile, source, views] of [
    [
      'desktop',
      { width: 1280, height: 720 },
      [
        { width: 1440, height: 900 },
        { width: 1920, height: 1080 },
        { width: 900, height: 1000 },
      ],
    ],
    [
      'mobile',
      { width: 720, height: 1280 },
      [
        { width: 390, height: 844 },
        { width: 320, height: 740 },
        { width: 700, height: 800 },
      ],
    ],
  ])
    for (const view of views) {
      const polygon = coverPolygon(
        tracking.profiles[profile][CORNER_CUT_FRAME].polygon,
        source,
        view,
      ).map(([x, y]) => [x / 100, y / 100]);
      assert.ok(coversViewport(polygon), `${profile} ${JSON.stringify(view)}`);
    }
});
test('the corner is entirely outside the image at both endpoints', () => {
  for (const profile of ['desktop', 'mobile'])
    for (const f of [0, CORNER_LAST_FRAME]) {
      const xs = tracking.profiles[profile][f].polygon.map((p) => p[0]);
      assert.ok(Math.max(...xs) < 0 || Math.min(...xs) > 1, `${profile} ${f}`);
    }
});
test('arrival starts only after the corner, and reverse scrolling retraces the same positions', () => {
  const stops = [0, 0.006, 0.018, 0.031, 0.05, CORNER_END];
  const forward = stops.map((p) => sampleJourney(p));
  for (const state of forward) assert.equal(state.time, 0);
  for (let i = stops.length - 1; i >= 0; i--)
    assert.deepEqual(sampleJourney(stops[i]), forward[i]);
  assert.ok(sampleJourney(CORNER_END + 0.001).time > 0);
  assert.equal(cornerProgress(-1), 0);
  assert.equal(cornerProgress(2), 1);
});
test('mask uses the decoded frame, including fractional seek times and the exact endpoint', () => {
  assert.equal(cornerFrame(47.99 / 30), 47);
  assert.equal(cornerFrame(48 / 30), 48);
  assert.equal(cornerFrame(96 / 30), 96);
  assert.equal(cornerFrame(99), 96);
});
