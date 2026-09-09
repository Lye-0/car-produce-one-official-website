import test from 'node:test';
import assert from 'node:assert/strict';
import {
  sampleJourney,
  createVideoScrubber,
  HOLD_RANGES,
} from '../src/journey-timeline.ts';
class Decoder {
  duration = 90;
  readyState = 4;
  seeking = false;
  paused = true;
  time = 0;
  writes = [];
  listeners = new Map();
  get currentTime() {
    return this.time;
  }
  set currentTime(value) {
    this.time = value;
    this.writes.push(value);
    this.seeking = true;
  }
  pause() {
    this.paused = true;
  }
  addEventListener(type, fn) {
    this.listeners.set(type, fn);
  }
  removeEventListener(type) {
    this.listeners.delete(type);
  }
  complete() {
    this.seeking = false;
    this.listeners.get('seeked')?.();
  }
}
test('partial forward scroll positions the camera between chapter stops', () => {
  const a = sampleJourney(0.1),
    b = sampleJourney(0.11),
    c = sampleJourney(0.12);
  assert.ok(a.time < b.time && b.time < c.time);
  assert.ok(c.time < 35.5);
});
test('stopping scroll cannot advance the camera or portal with elapsed time', async () => {
  for (const p of [0.2, 0.52, 0.82, 0.96]) {
    const before = sampleJourney(p),
      v = new Decoder(),
      driver = createVideoScrubber(v);
    driver.seek(before.time);
    v.complete();
    const writes = v.writes.length;
    await new Promise((r) => setTimeout(r, 30));
    assert.equal(v.currentTime, before.time);
    assert.equal(v.writes.length, writes);
    assert.equal(v.paused, true);
    assert.deepEqual(sampleJourney(p), before);
    driver.dispose();
  }
});
test('reverse scroll retraces precisely, including the portal before and after its end', () => {
  for (const p of [0.01, 0.2, 0.4, 0.55, 0.7, 0.82, 0.91, 0.96, 0.999]) {
    const outbound = sampleJourney(p);
    sampleJourney(Math.min(1, p + 0.05));
    assert.deepEqual(sampleJourney(p), outbound);
  }
  assert.equal(sampleJourney(1.2).complete, true);
  assert.equal(sampleJourney(0.99).complete, false);
  assert.ok(sampleJourney(0.97).portal > sampleJourney(0.95).portal);
});
test('reading ranges hold the camera while retaining the ambient-loop selection', () => {
  for (const [hold, [a, b]] of Object.entries(HOLD_RANGES)) {
    const start = sampleJourney(a + 0.001),
      middle = sampleJourney((a + b) / 2),
      end = sampleJourney(b - 0.001);
    assert.equal(start.hold, hold);
    assert.equal(end.hold, hold);
    assert.equal(start.time, end.time);
    assert.equal(middle.cardOpacity, 1);
    assert.ok(start.cardOpacity < 1 && end.cardOpacity < 1);
  }
});
test('busy decoding coalesces rapid forward and reverse input to the LAST scroll position', () => {
  const v = new Decoder(),
    driver = createVideoScrubber(v);
  driver.seek(45);
  driver.seek(60);
  driver.seek(12);
  assert.deepEqual(v.writes, [45]);
  v.complete();
  assert.deepEqual(v.writes, [45, 12]);
  v.complete();
  assert.equal(v.currentTime, 12);
  assert.equal(v.paused, true);
  driver.dispose();
});
test('a scroll before loading is restored as soon as media is available', () => {
  const v = new Decoder();
  v.readyState = 0;
  const driver = createVideoScrubber(v);
  driver.seek(72);
  assert.equal(v.writes.length, 0);
  v.readyState = 4;
  v.listeners.get('loadeddata')();
  assert.equal(v.currentTime, 72);
  driver.dispose();
});
test('endpoints, overscroll and decoder lifecycle are bounded', () => {
  assert.equal(sampleJourney(-1).time, 0);
  assert.equal(sampleJourney(9).time, 90);
  const v = new Decoder(),
    driver = createVideoScrubber(v);
  driver.seek(999);
  assert.equal(v.currentTime, 89.875);
  driver.dispose();
  v.complete();
  assert.equal(v.listeners.size, 0);
});

test('24fps portal seeks retain adjacent frames and its exact endpoint', () => {
  const v = new Decoder();
  v.duration = 217 / 24;
  const driver = createVideoScrubber(v, 24);
  driver.seek(1 / 24);
  assert.equal(v.currentTime, 1 / 24);
  v.complete();
  driver.seek(2 / 24);
  assert.equal(v.currentTime, 2 / 24);
  v.complete();
  driver.seek(9);
  assert.ok(Math.abs(v.currentTime - 9) < 1e-9);
  driver.dispose();
});
test('leaving the monitor hold preserves the entire approach without a time jump', () => {
  assert.equal(sampleJourney(0.899999).time, 81);
  const start = sampleJourney(0.900001).time;
  assert.ok(start >= 81 && start < 81.001);
  assert.ok(sampleJourney(0.91).time < sampleJourney(0.95).time);
  assert.equal(sampleJourney(1).time, 90);
});

