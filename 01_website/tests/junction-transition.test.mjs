import test from 'node:test';
import assert from 'node:assert/strict';
import {
  JUNCTION_END,
  DRIVE_SECONDS,
  TURN_SECONDS,
  junctionProgress,
  sampleJunction,
} from '../src/junction-transition.ts';

test('every starting phase reaches the common street endpoint before the turn', () => {
  for (const phase of [0, 5, 10, 15, DRIVE_SECONDS - 1 / 30]) {
    const boundary =
      (DRIVE_SECONDS - phase) / (DRIVE_SECONDS - phase + TURN_SECONDS);
    const before = sampleJunction(boundary - 1e-6, phase);
    const at = sampleJunction(boundary, phase);
    assert.equal(before.stage, 'drive');
    assert.equal(before.turnTime, 0);
    assert.ok(Math.abs(at.driveTime - DRIVE_SECONDS) < 1e-8);
    assert.ok(at.turnTime < 1e-8);
    assert.equal(sampleJunction(boundary + 1e-6, phase).stage, 'turn');
  }
});
test('the first scroll continues from the visible loop position, with no reset', () => {
  for (const phase of [0, 5, 10, 15, DRIVE_SECONDS - 1 / 30]) {
    assert.equal(sampleJunction(0, phase).driveTime, phase);
    assert.ok(sampleJunction(0.0001, phase).driveTime >= phase);
  }
});
test('reverse scrolling retraces the same street and turn coordinates', () => {
  const positions = [0, 0.03, 0.18, 0.37, 0.6, 0.8, 1];
  for (const phase of [0, 3.4, 12.5, 19.8]) {
    const forward = positions.map((p) => sampleJunction(p, phase));
    for (let i = positions.length - 1; i >= 0; i--)
      assert.deepEqual(sampleJunction(positions[i], phase), forward[i]);
  }
});
test('all phases end at the same arrival pose and tolerate invalid input', () => {
  for (const phase of [0, 5, 10, 15, DRIVE_SECONDS - 1 / 30])
    assert.deepEqual(sampleJunction(1, phase), {
      driveTime: DRIVE_SECONDS,
      turnTime: 16,
      stage: 'turn',
      complete: true,
    });
  assert.equal(junctionProgress(JUNCTION_END), 1);
  assert.equal(junctionProgress(-1), 0);
  assert.equal(junctionProgress(NaN), 0);
  assert.equal(sampleJunction(NaN, NaN).driveTime, 0);
});

import { sampleJourney, HOLD_RANGES } from '../src/journey-timeline.ts';
test('arrival starts after the junction while the three reading positions remain fixed', () => {
  assert.equal(sampleJourney(JUNCTION_END).time, 0);
  assert.ok(sampleJourney(JUNCTION_END + 0.001).time > 0);
  for (const [name, [a, b]] of Object.entries(HOLD_RANGES))
    assert.equal(sampleJourney((a + b) / 2).hold, name);
});

test('scroll speed remains continuous from the turn into the arrival clip', () => {
  const epsilon = 1e-6;
  for (const phase of [0, 5, 10, 15, DRIVE_SECONDS - 1 / 30]) {
    const before =
      (TURN_SECONDS -
        sampleJunction(junctionProgress(JUNCTION_END - epsilon), phase)
          .turnTime) /
      epsilon;
    const after = sampleJourney(JUNCTION_END + epsilon, phase).time / epsilon;
    assert.ok(
      Math.abs(before - after) / before < 0.0001,
      `${phase}: ${before} vs ${after}`,
    );
  }
});
