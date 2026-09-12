import test from 'node:test';
import assert from 'node:assert/strict';
import {
  beforeRouteFrame,
  routeDownloadGates,
  nextDownloadGate,
  capForwardProgress,
} from '../src/media/download-gates.ts';
import { sampleJourney } from '../src/journey/timeline.ts';

test('every route gate stops on the preceding frame, including gaps inside reading holds', () => {
  for (const frame of [1212, 1512, 1812, 2112]) {
    const gate = beforeRouteFrame(frame, 30);
    assert(Math.round(sampleJourney(gate).time * 30) < frame);
    assert(Math.round(sampleJourney(gate + 1e-5).time * 30) >= frame);
  }
  assert(Math.abs(beforeRouteFrame(1212, 30) - 0.46) < 1e-5);
  assert(Math.abs(beforeRouteFrame(1812, 30) - 0.76) < 1e-5);
});
test('the first incomplete section gates progress, even if later sections finish first', () => {
  const variant = {
    segments: [
      { src: 'a', startFrame: 0 },
      { src: 'b', startFrame: 1212 },
      { src: 'c', startFrame: 1512 },
    ],
  };
  const gates = routeDownloadGates(variant, 30);
  assert.equal(nextDownloadGate(gates, (src) => src === 'c').files[0].src, 'b');
  assert.equal(nextDownloadGate(gates, (src) => src === 'b').files[0].src, 'c');
  assert.equal(
    nextDownloadGate(gates, () => true),
    undefined,
  );
});
test('forward input is capped, reverse input is free, and completion never advances a stationary camera', () => {
  const limit = beforeRouteFrame(1212, 30);
  assert.equal(capForwardProgress(0.9, 0.4, limit), limit);
  assert.equal(capForwardProgress(0.2, limit, limit), 0.2);
  assert.equal(capForwardProgress(limit, limit, 1), limit);
  assert.equal(capForwardProgress(0.7, 0.8, limit), 0.7);
});

test('unvisited reverse footage stops at its far edge and groups overlapping dependencies', async () => {
  const { constrainMediaProgress } =
    await import('../src/media/download-gates.ts');
  const spans = [
    { start: 0, end: 0.46, files: [{ src: 'front' }] },
    { start: 0.76, end: 0.9, files: [{ src: 'route-end' }] },
    { start: 0.88, end: 0.9, files: [{ src: 'monitor' }] },
    { start: 0.9, end: 1, files: [{ src: 'portal' }] },
  ];
  assert.deepEqual(
    constrainMediaProgress(0.5, 1, spans, () => false),
    { progress: 1, files: [{ src: 'portal' }] },
  );
  const stopped = constrainMediaProgress(
    0.5,
    0.95,
    spans,
    (src) => src === 'portal',
  );
  assert(Math.abs(stopped.progress - 0.90001) < 1e-8);
  assert.deepEqual(stopped.files.map((f) => f.src).sort(), [
    'monitor',
    'route-end',
  ]);
  // Unread early footage must not trap someone who wants to return to the body.
  assert.equal(
    constrainMediaProgress(1, 0.91, spans, (src) => src === 'portal').progress,
    1,
  );
  assert.equal(
    constrainMediaProgress(0.2, 0.95, spans, () => true).progress,
    0.2,
  );
  assert.equal(
    constrainMediaProgress(0.95, 0.95, spans, () => false).progress,
    0.95,
  );
});
