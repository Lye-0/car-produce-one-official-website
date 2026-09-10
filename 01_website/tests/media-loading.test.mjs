import test from 'node:test';
import assert from 'node:assert/strict';
import {
  INITIAL_MEDIA_REQUESTS,
  requestNearbyMedia,
} from '../src/media-loading.ts';
import { createVideoScrubber } from '../src/journey-timeline.ts';
test('initial and skipped visits do not request the full film library', () => {
  assert.equal(
    requestNearbyMedia(INITIAL_MEDIA_REQUESTS, 0),
    INITIAL_MEDIA_REQUESTS,
  );
  assert.equal(
    requestNearbyMedia(INITIAL_MEDIA_REQUESTS, 1),
    INITIAL_MEDIA_REQUESTS,
  );
  const first = requestNearbyMedia(INITIAL_MEDIA_REQUESTS, 0.02);
  assert.equal(first.junction, true);
  assert.equal(first.route, false);
  assert.equal(first.tools, false);
  assert.equal(first.portal, false);
});
test('approaching a stop preloads it and reverse scrolling retains requested footage', () => {
  const tools = requestNearbyMedia(INITIAL_MEDIA_REQUESTS, 0.3);
  assert.equal(tools.route, true);
  assert.equal(tools.tools, true);
  assert.equal(tools.magazines, false);
  assert.equal(tools.portal, false);
  assert.equal(requestNearbyMedia(tools, 0.05), tools);
  const portal = requestNearbyMedia(tools, 0.87);
  assert.equal(portal.portal, true);
  assert.equal(portal.monitor, true);
});
test('metadata-only footage starts decoding the pending scroll target without another scroll', () => {
  const events = new Map();
  const video = {
    currentTime: 0,
    duration: 81,
    readyState: 0,
    seeking: false,
    pause() {},
    addEventListener(name, fn) {
      events.set(name, fn);
    },
    removeEventListener(name) {
      events.delete(name);
    },
  };
  const scrub = createVideoScrubber(video, 30);
  scrub.seek(34.2);
  assert.equal(video.currentTime, 0);
  video.readyState = 1;
  events.get('loadedmetadata')();
  assert.equal(video.currentTime, 34.2);
  scrub.dispose();
  assert.equal(events.size, 0);
});
