import {
  browserCapability,
  preferredVariant,
  type CapabilityProbe,
  type MediaAsset,
  type MediaSegment,
  type MediaVariant,
} from './playback.ts';

/** Local MP4 timestamps are zero-based; the journey always uses global frames. */
export function mediaSegments(
  variant: MediaVariant,
  frames: number,
): MediaSegment[] {
  return variant.segments ?? [{ src: variant.src, startFrame: 0, frames }];
}

export function segmentTarget(
  segments: MediaSegment[],
  frames: number,
  fps: number,
  time: number,
) {
  const frame = Math.min(
    frames - 1,
    Math.max(0, Math.round((Number.isFinite(time) ? time : 0) * fps)),
  );
  const index = segments.findIndex(
    (part) => frame >= part.startFrame && frame < part.startFrame + part.frames,
  );
  if (index < 0)
    throw new Error('The segmented timeline must cover every frame.');
  const localFrame = frame - segments[index].startFrame;
  return { index, frame, localFrame, time: (localFrame + 0.5) / fps };
}

// Native video elements preserve the AVC compatibility fallback, including on
// browsers without MediaSource. A decoded frame stays visible until its
// replacement is ready; neither source reassignment nor a crossfade joins parts.
export function createSegmentedPlayback(
  videos: readonly HTMLVideoElement[],
  options: { onReady: (ready: boolean) => void; onError: () => void },
) {
  let disposed = false;
  let generation = 0;
  let asset: MediaAsset | undefined;
  let selected: MediaVariant | undefined;
  let parts: MediaSegment[] = [];
  let desired = 0;
  let announced = false;
  let failed = false;
  const decoded = videos.map(() => -1);
  const loaded = videos.map(() => false);
  const callbacks = videos.map(() => 0);
  const warmSeconds = 12;

  function announce(ready: boolean) {
    if (announced !== ready) {
      announced = ready;
      options.onReady(ready);
    }
  }

  function clear() {
    parts = [];
    videos.forEach((video, index) => {
      loaded[index] = false;
      decoded[index] = -1;
      video.dataset.mediaActive = 'false';
      video.dataset.mediaStartFrame = '0';
      delete video.dataset.mediaFrame;
      video.pause();
      video.removeAttribute('src');
      video.load();
    });
  }

  function load(index: number) {
    if (loaded[index]) return;
    const video = videos[index];
    const part = parts[index];
    loaded[index] = true;
    decoded[index] = -1;
    video.dataset.mediaStartFrame = String(part.startFrame);
    video.dataset.mediaCodec = selected!.codec;
    video.preload = 'auto';
    video.src = part.src;
    video.load();
  }

  function present(index: number, frame: number) {
    const video = videos[index];
    const changed =
      video.dataset.mediaActive !== 'true' ||
      video.dataset.mediaFrame !== String(frame);
    videos.forEach((item, i) => {
      item.dataset.mediaActive = String(i === index);
    });
    video.dataset.mediaFrame = String(frame);
    announce(true);
    // Monitor projection must also repaint when switching to an already decoded
    // video: there may be no new seeked/rVFC event in that case.
    if (changed) video.dispatchEvent(new Event('routeframe'));
  }

  function seekVideo(index: number, localFrame: number, globalFrame?: number) {
    const video = videos[index];
    if (video.readyState < 1 || video.seeking) return;
    if (decoded[index] === localFrame && video.readyState >= 2) {
      if (globalFrame !== undefined) present(index, globalFrame);
      return;
    }
    video.pause();
    video.currentTime = (localFrame + 0.5) / asset!.fps;
  }

  function flush() {
    if (disposed || failed || !asset || !selected || !parts.length) return;
    const target = segmentTarget(parts, asset.frames, asset.fps, desired);
    load(target.index);
    seekVideo(target.index, target.localFrame, target.frame);
    // Warm the next/previous boundary while approaching it. Keep visited parts
    // attached so fast reverse scrolling does not reload the source.
    for (const index of [target.index - 1, target.index + 1]) {
      const part = parts[index];
      if (!part) continue;
      if (videos[index].dataset.mediaActive === 'true') continue;
      const frame =
        index < target.index
          ? part.startFrame + part.frames - 1
          : part.startFrame;
      if (Math.abs(target.frame - frame) > warmSeconds * asset.fps) continue;
      load(index);
      seekVideo(index, index < target.index ? part.frames - 1 : 0);
    }
  }

  function configure(variant: MediaVariant) {
    clear();
    selected = variant;
    parts = mediaSegments(variant, asset!.frames);
    let end = 0;
    for (const part of parts) {
      if (
        part.startFrame !== end ||
        !Number.isInteger(part.frames) ||
        part.frames <= 0
      )
        throw new Error('Segments must be contiguous and nonempty.');
      end += part.frames;
    }
    if (parts.length > videos.length || end !== asset!.frames)
      throw new Error('Unsupported segmented media layout.');
    flush();
  }

  function fail(index: number) {
    if (disposed || failed || !loaded[index] || !selected) return;
    if (selected.codec === 'hevc') {
      const fallback = asset!.variants.find((v) => v.codec === 'h264');
      if (fallback) {
        announce(false);
        configure(fallback);
        return;
      }
    }
    failed = true;
    options.onError();
  }

  const cleanups = videos.map((video, index) => {
    const receive = (mediaTime: number) => {
      if (
        disposed ||
        !asset ||
        !loaded[index] ||
        video.seeking ||
        video.readyState < 2
      )
        return;
      const frame = Math.floor(mediaTime * asset.fps + 1e-4);
      // A queued compositor callback can describe the frame from before a seek.
      if (frame !== Math.floor(video.currentTime * asset.fps + 1e-4)) return;
      decoded[index] = frame;
      flush();
    };
    const decode = () => receive(video.currentTime);
    const metadata = () => flush();
    const error = () => fail(index);
    video.addEventListener('loadedmetadata', metadata);
    video.addEventListener('loadeddata', decode);
    video.addEventListener('seeked', decode);
    video.addEventListener('error', error);
    if (typeof video.requestVideoFrameCallback === 'function') {
      const frame: VideoFrameRequestCallback = (_, info) => {
        receive(info.mediaTime);
        if (!disposed)
          callbacks[index] = video.requestVideoFrameCallback(frame);
      };
      callbacks[index] = video.requestVideoFrameCallback(frame);
    }
    return () => {
      video.removeEventListener('loadedmetadata', metadata);
      video.removeEventListener('loadeddata', decode);
      video.removeEventListener('seeked', decode);
      video.removeEventListener('error', error);
      if (callbacks[index]) video.cancelVideoFrameCallback(callbacks[index]);
    };
  });

  return {
    async setMedia(
      next?: MediaAsset,
      probe: CapabilityProbe = browserCapability,
    ) {
      const ticket = ++generation;
      announce(false);
      clear();
      asset = next;
      selected = undefined;
      failed = false;
      if (disposed || !next) return;
      try {
        const variant = await preferredVariant(next, probe);
        if (disposed || ticket !== generation) return;
        configure(variant);
      } catch {
        if (!disposed && ticket === generation) {
          failed = true;
          options.onError();
        }
      }
    },
    seek(time: number) {
      desired = time;
      flush();
    },
    dispose() {
      disposed = true;
      generation++;
      cleanups.forEach((cleanup) => cleanup());
      clear();
    },
  };
}
