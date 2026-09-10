import test from 'node:test';
import assert from 'node:assert/strict';
import {
  journeyScrollDistance as distance,
  journeyProgressFromScroll as progress,
  turnScrollStart,
} from '../src/journey-scroll.ts';
import { sampleJourney, CHAPTER_PROGRESS } from '../src/journey-timeline.ts';
import {
  JUNCTION_END,
  junctionProgress,
  sampleJunction,
} from '../src/junction-transition.ts';
const phases = [0, 5, 10, 15, 19.99];
const close = (a, b, tolerance = 1e-8) =>
  assert.ok(Math.abs(a - b) < tolerance, `${a} vs ${b}`);

test('straight driving keeps its original scroll speed for every captured loop phase', () => {
  for (const phase of phases) {
    const start = turnScrollStart(phase);
    for (const p of [0, start * 0.25, start * 0.75, start]) {
      close(distance(p, phase), p);
      close(progress(p, phase), p);
    }
  }
});

test('every interval after the turn needs twice the old scroll distance', () => {
  for (const phase of phases)
    for (const [a, b] of [
      [0.18, 0.35],
      [0.35, 0.46],
      [0.46, 0.65],
      [0.65, 0.76],
      [0.76, 0.88],
      [0.9, 1],
    ])
      close(distance(b, phase) - distance(a, phase), 2 * (b - a));
});

test('turn deceleration is monotone and meets unchanged driving and half-speed arrival smoothly', () => {
  const h = 1e-7;
  for (const phase of phases) {
    const start = turnScrollStart(phase),
      end = distance(JUNCTION_END, phase);
    const speed = (d) =>
      (progress(d + h, phase) - progress(d - h, phase)) / (2 * h);
    close(speed(start), 1, 1e-5);
    close(speed(end), 0.5, 1e-5);
    let previous = 1;
    for (let i = 1; i <= 40; i++) {
      const v = speed(
        distance(start + ((JUNCTION_END - start) * i) / 40, phase),
      );
      assert.ok(v <= previous + 1e-5 && v >= 0.5 - 1e-5);
      previous = v;
    }
    const before =
      (16 -
        sampleJunction(junctionProgress(progress(end - h, phase)), phase)
          .turnTime) /
      h;
    const after = sampleJourney(progress(end + h, phase), phase).time / h;
    assert.ok(Math.abs(before - after) / before < 1e-4);
  }
});

test('chapter targets, reverse scrolling, and final site handoff use the same invertible mapping', () => {
  for (const phase of phases) {
    const points = [
      ...CHAPTER_PROGRESS,
      0.025,
      0.12,
      0.18,
      0.25,
      0.6,
      0.94,
    ].sort((a, b) => a - b);
    const forward = points.map((p) =>
      sampleJourney(progress(distance(p, phase), phase), phase),
    );
    for (let i = points.length - 1; i >= 0; i--) {
      close(progress(distance(points[i], phase), phase), points[i]);
      assert.deepEqual(
        sampleJourney(progress(distance(points[i], phase), phase), phase),
        forward[i],
      );
    }
    assert.equal(
      sampleJourney(progress(distance(1, phase), phase), phase).complete,
      true,
    );
  }
  assert.equal(progress(NaN), 0);
  assert.equal(progress(-10), 0);
  assert.equal(progress(10), 1);
});
