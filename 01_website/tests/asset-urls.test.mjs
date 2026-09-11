import test from 'node:test';
import assert from 'node:assert/strict';
import { assetUrl, assetWithBase } from '../src/media/urls.ts';

test('asset paths follow a root domain or Pages repository prefix, preserving query strings', () => {
  assert.equal(
    assetUrl('/media/video.mp4?v=abc', '/'),
    '/media/video.mp4?v=abc',
  );
  assert.equal(
    assetUrl('/media/video.mp4?v=abc', '/car-produce-one-official-website/'),
    '/car-produce-one-official-website/media/video.mp4?v=abc',
  );
  assert.equal(
    assetUrl('/favicon.svg', '/nested/site'),
    '/nested/site/favicon.svg',
  );
  for (const path of [
    'https://example.com/x',
    '//cdn.example.com/x',
    'data:image/png,xyz',
    'blob:https://example.com/id',
    '#services',
    'relative.jpg',
    undefined,
  ])
    assert.equal(assetUrl(path, '/site/'), path);
});

test('single videos, split videos and posters are rebased without modifying canonical manifests', () => {
  const asset = {
    fps: 30,
    frames: 4,
    poster: '/media/poster.webp',
    variants: [
      { codec: 'hevc', src: '/media/hevc.mp4' },
      {
        codec: 'h264',
        segments: [
          { src: '/media/part-1.mp4', startFrame: 0, frames: 2 },
          { src: '/media/part-2.mp4', startFrame: 2, frames: 2 },
        ],
      },
    ],
  };
  const original = structuredClone(asset),
    result = assetWithBase(asset, '/site/');
  assert.deepEqual(asset, original);
  assert.equal(result.poster, '/site/media/poster.webp');
  assert.equal(result.variants[0].src, '/site/media/hevc.mp4');
  assert.equal(result.variants[1].segments[1].src, '/site/media/part-2.mp4');
  assert.equal(result.variants[1].segments[1].startFrame, 2);
});
