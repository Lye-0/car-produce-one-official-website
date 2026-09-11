import test from 'node:test';
import assert from 'node:assert/strict';
import { sampleJourney } from '../src/journey/timeline.ts';
test('the monitor invitation is readable before and after the stationary hold', () => {
  for (const p of [0.865, 0.88, 0.89, 0.9, 0.925])
    assert.equal(sampleJourney(p).inviteOpacity, 1);
  for (const p of [0, 0.84, 0.95, 1])
    assert.equal(sampleJourney(p).inviteOpacity, 0);
});
