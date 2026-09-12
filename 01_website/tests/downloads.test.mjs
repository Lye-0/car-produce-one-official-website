import test from 'node:test';
import assert from 'node:assert/strict';
import { VideoDownloads } from '../src/media/downloads.ts';

test('downloads deduplicate concurrent users and count received bytes, not elapsed time', async (t) => {
  let calls = 0,
    send;
  t.mock.method(globalThis, 'fetch', async () => {
    calls++;
    return new Response(
      new ReadableStream({
        start(controller) {
          send = controller;
        },
      }),
      { headers: { 'content-length': '4' } },
    );
  });
  const cache = new VideoDownloads();
  try {
    const first = cache.ensure('/a', 4),
      second = cache.ensure('/a', 4);
    assert.equal(first, second);
    assert.equal(cache.progress(['/a']), 0);
    assert.equal(cache.isReady('/a'), false);
    send.enqueue(new Uint8Array([1, 2]));
    await new Promise((r) => setImmediate(r));
    assert.equal(cache.progress(['/a']), 0.5);
    assert.equal(cache.isReady('/a'), false);
    send.enqueue(new Uint8Array([3, 4]));
    send.close();
    assert.equal(await first, await second);
    assert.equal(calls, 1);
    assert.equal(cache.progress(['/a']), 1);
    assert.equal(cache.isReady('/a'), true);
  } finally {
    cache.dispose();
  }
});

test('visible media goes ahead of queued background downloads', async (t) => {
  const calls = [];
  let unblock;
  t.mock.method(globalThis, 'fetch', async (src) => {
    calls.push(src);
    if (src === '/first') await new Promise((r) => (unblock = r));
    return new Response(new Uint8Array([1]));
  });
  const cache = new VideoDownloads();
  try {
    const first = cache.ensure('/first'),
      background = cache.ensure('/background', 1, 10),
      visible = cache.ensure('/visible', 1, 0);
    unblock();
    await Promise.all([first, background, visible]);
    assert.deepEqual(calls, ['/first', '/visible', '/background']);
  } finally {
    cache.dispose();
  }
});

test('an incomplete response is not reported ready and can be retried', async (t) => {
  let broken = true;
  t.mock.method(
    globalThis,
    'fetch',
    async () =>
      new Response(new Uint8Array(broken ? [1] : [1, 2]), {
        headers: { 'content-length': '2' },
      }),
  );
  const cache = new VideoDownloads();
  try {
    await assert.rejects(cache.ensure('/a', 2), /Incomplete/);
    assert(cache.error());
    assert.equal(cache.progress(['/a']), 0.5);
    broken = false;
    cache.retry();
    await cache.ensure('/a', 2);
    assert.equal(cache.error(), undefined);
    assert.equal(cache.progress(['/a']), 1);
  } finally {
    cache.dispose();
  }
});

test('disposing cancels active and queued transfers without starting the queue', async (t) => {
  let calls = 0;
  t.mock.method(globalThis, 'fetch', async (_src, { signal }) => {
    calls++;
    return new Promise((_resolve, reject) =>
      signal.addEventListener('abort', () => reject(new Error('aborted'))),
    );
  });
  const cache = new VideoDownloads();
  const a = cache.ensure('/a'),
    b = cache.ensure('/b');
  const settled = Promise.allSettled([a, b]);
  cache.dispose();
  assert((await settled).every((r) => r.status === 'rejected'));
  assert.equal(calls, 1);
});

test('continuous slow transfers remain valid beyond 30 seconds; only idle transfers time out', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  let send;
  t.mock.method(
    globalThis,
    'fetch',
    async (_src, { signal }) =>
      new Response(
        new ReadableStream({
          start(controller) {
            send = controller;
            signal.addEventListener('abort', () =>
              controller.error(new Error('idle timeout')),
            );
          },
        }),
        { headers: { 'content-length': '3' } },
      ),
  );
  const cache = new VideoDownloads();
  try {
    const completed = cache.ensure('/slow', 3);
    send.enqueue(new Uint8Array([1]));
    await new Promise((r) => setImmediate(r));
    t.mock.timers.tick(29000);
    send.enqueue(new Uint8Array([2]));
    await new Promise((r) => setImmediate(r));
    t.mock.timers.tick(29000);
    send.enqueue(new Uint8Array([3]));
    send.close();
    await completed;
    assert.equal(cache.isReady('/slow'), true);
    assert.equal(cache.error(), undefined);
    const stalled = cache.ensure('/stalled', 3);
    const rejection = assert.rejects(stalled, /idle timeout/);
    await new Promise((r) => setImmediate(r));
    t.mock.timers.tick(30001);
    await rejection;
    assert.equal(cache.isReady('/stalled'), false);
  } finally {
    cache.dispose();
  }
});

test('restarting cancels obsolete transfers while retaining completed videos', async (t) => {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (src, { signal }) => {
    calls.push(src);
    if (src === '/old')
      return new Promise((_resolve, reject) =>
        signal.addEventListener('abort', () => reject(new Error('cancelled'))),
      );
    return new Response(new Uint8Array([1]));
  });
  const cache = new VideoDownloads();
  try {
    const ready = await cache.ensure('/ready', 1);
    const obsolete = cache.ensure('/old'),
      queued = cache.ensure('/queued');
    const settled = Promise.allSettled([obsolete, queued]);
    cache.cancelPending();
    assert((await settled).every((result) => result.status === 'rejected'));
    assert.equal(await cache.ensure('/ready', 1), ready);
    await cache.ensure('/new', 1);
    assert.deepEqual(calls, ['/ready', '/old', '/new']);
    assert.equal(cache.error(), undefined);
  } finally {
    cache.dispose();
  }
});

test('a blocked navigation preempts an active transfer and resumes its saved bytes', async (t) => {
  let initial;
  const calls = [];
  const originalFetch = globalThis.fetch;
  t.mock.method(globalThis, 'fetch', async (src, options) => {
    calls.push({ src, range: options.headers?.Range });
    if (src === '/background' && !options.headers?.Range)
      return new Response(
        new ReadableStream({
          start(c) {
            initial = c;
            options.signal.addEventListener('abort', () =>
              c.error(new Error('paused')),
            );
          },
        }),
        { headers: { 'content-length': '4' } },
      );
    if (src === '/background')
      return new Response(new Uint8Array([3, 4]), {
        status: 206,
        headers: { 'content-length': '2', 'content-range': 'bytes 2-3/4' },
      });
    return new Response(new Uint8Array([9]), {
      headers: { 'content-length': '1' },
    });
  });
  const cache = new VideoDownloads();
  try {
    const background = cache.ensure('/background', 4, 10);
    initial.enqueue(new Uint8Array([1, 2]));
    await new Promise((r) => setImmediate(r));
    const urgent = cache.ensure('/urgent', 1, 0);
    cache.focus(['/urgent']);
    await urgent;
    const restored = await background;
    assert.deepEqual(
      new Uint8Array(await (await originalFetch(restored)).arrayBuffer()),
      new Uint8Array([1, 2, 3, 4]),
    );
    assert.deepEqual(calls, [
      { src: '/background', range: undefined },
      { src: '/urgent', range: undefined },
      { src: '/background', range: 'bytes=2-' },
    ]);
    assert.equal(cache.error(), undefined);
  } finally {
    cache.dispose();
  }
});
