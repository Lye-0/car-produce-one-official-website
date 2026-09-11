import test from 'node:test';
import assert from 'node:assert/strict';
import desktop from '../src/portal/tracking/desktop.json' with { type: 'json' };
import mobile from '../src/portal/tracking/mobile.json' with { type: 'json' };
const tracking = { desktop, mobile };
import {
  sampleQuad,
  coverQuad,
  quadMatrix,
  rectQuad,
} from '../src/portal/geometry.ts';
const apply = (m, [x, y]) => {
  const w = m[3] * x + m[7] * y + m[15];
  return [(m[0] * x + m[4] * y + m[12]) / w, (m[1] * x + m[5] * y + m[13]) / w];
};
for (const [profile, media, view] of [
  ['desktop', { width: 1280, height: 720 }, { width: 1440, height: 900 }],
  ['mobile', { width: 720, height: 1280 }, { width: 390, height: 844 }],
]) {
  test(
    profile +
      ': every tracked corner stays on its rendered screen under cover cropping',
    () => {
      for (let f = 2430; f <= 2700; f += 1.25) {
        const q = coverQuad(sampleQuad(tracking[profile], f), media, view),
          m = quadMatrix(view, q);
        assert.ok(m);
        rectQuad(view).forEach((p, i) => {
          const actual = apply(m, p);
          assert.ok(
            Math.hypot(actual[0] - q[i][0], actual[1] - q[i][1]) < 0.001,
          );
        });
      }
    },
  );
}
test('same frame and viewport reproduce the same projection when scrolling back', () => {
  const view = { width: 390, height: 844 },
    media = { width: 720, height: 1280 };
  const at = (f) =>
    quadMatrix(view, coverQuad(sampleQuad(tracking.mobile, f), media, view));
  const first = at(2580.5);
  at(2650);
  assert.deepEqual(at(2580.5), first);
  assert.equal(sampleQuad(tracking.mobile, 2339), null);
});
