import test from 'node:test';
import assert from 'node:assert/strict';
import { portalDirection, portalTiming } from '../src/portal-timing.ts';
import { sampleJourney } from '../src/journey-timeline.ts';
test('the monitor invitation is readable before and after the stationary hold', () => {
  for (const p of [0.865, 0.88, 0.89, 0.9, 0.925])
    assert.equal(sampleJourney(p).inviteOpacity, 1);
  for (const p of [0, 0.84, 0.95, 1])
    assert.equal(sampleJourney(p).inviteOpacity, 0);
});
test('entry waits for the displayed frame to cover the viewport; a fast end scroll can finish', () => {
  for (const cover of [2614, 2673]) {
    assert.equal(portalDirection('camera', cover + 1, cover - 1, cover), null);
    assert.equal(portalDirection('camera', cover + 1, cover, cover), 'site');
    assert.equal(portalDirection('camera', 2700, 2430, cover), 'site');
  }
});
test('a stopped scroll still finishes after 700ms and the swap is fully covered', () => {
  assert.equal(portalTiming(149).swapped, false);
  assert.equal(portalTiming(299).swapped, false);
  assert.equal(portalTiming(300).swapped, true);
  for (const t of [299, 300, 301]) {
    assert.equal(portalTiming(t).cover, 1);
    assert.equal(portalTiming(t).reveal, 0);
  }
  assert.equal(portalTiming(699).complete, false);
  assert.equal(portalTiming(700).complete, true);
  assert.equal(portalTiming(9000).reveal, 1);
});
test('reverse entry has hysteresis and cannot retrigger at the same boundary', () => {
  assert.equal(portalDirection('site', 2670, 2670, 2673), null);
  assert.equal(portalDirection('site', 2654, 2654, 2673), 'camera');
  assert.equal(portalDirection('camera', 2654, 2654, 2673), null);
});
