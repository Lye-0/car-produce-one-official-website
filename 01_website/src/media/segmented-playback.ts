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
  options: {
    onReady: (ready: boolean) => void;
    onError: () => void;
    chooseVariant?: (asset: MediaAsset) => Promise<MediaVariant>;
    onVariant?: (asset: MediaAsset, variant: MediaVariant) => void;
    resolveSource?: (
      src: string,
      priority?: number,
    ) => Promise<{ url: string; release: () => void }>;
  },
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
  const slotParts = videos.map(() => -1);
  const slotTickets = videos.map(() => 0);
  let direction = 1;
  const callbacks = videos.map(() => 0);
  const warmSeconds = 12;
  let sourceGeneration = 0;
  const releases: Array<(() => void) | undefined> = videos.map(() => undefined);

  function announce(ready: boolean) {
    if (announced !== ready) {
      announced = ready;
      options.onReady(ready);
    }
  }

  function clear() {
    sourceGeneration++;
    releases.forEach((release, i) => {
      release?.();
      releases[i] = undefined;
    });
    parts = [];
    videos.forEach((video, index) => {
      loaded[index] = false;
      slotParts[index] = -1;
      slotTickets[index]++;
      decoded[index] = -1;
      video.dataset.mediaActive = 'false';
      video.dataset.mediaStartFrame = '0';
      delete video.dataset.mediaFrame;
      delete video.dataset.mediaWaiting;
      video.pause();
      video.removeAttribute('src');
      video.load();
    });
  }

  function load(partIndex: number, priority = 0) {
    const existing = slotParts.indexOf(partIndex);
    if (existing >= 0) return existing;
    const active = videos.findIndex((v) => v.dataset.mediaActive === 'true');
    const index =
      partIndex < videos.length && slotParts[partIndex] === -1
        ? partIndex
        : slotParts.indexOf(-1) >= 0
          ? slotParts.indexOf(-1)
          : active === 0
            ? 1
            : 0;
    const video = videos[index];
    const part = parts[partIndex];
    releases[index]?.();
    releases[index] = undefined;
    slotParts[index] = partIndex;
    const slotTicket = ++slotTickets[index];
    video.pause();
    video.removeAttribute('src');
    video.load();
    video.dataset.mediaActive = 'false';
    loaded[index] = true;
    decoded[index] = -1;
    video.dataset.mediaStartFrame = String(part.startFrame);
    video.dataset.mediaCodec = selected!.codec;
    video.preload = 'auto';
    if (!options.resolveSource) {
      video.src = part.src;
      video.load();
      return index;
    }
    const ticket = sourceGeneration;
    options
      .resolveSource(part.src, priority)
      .then((lease) => {
        if (
          disposed ||
          ticket !== sourceGeneration ||
          slotTicket !== slotTickets[index]
        ) {
          lease.release();
          return;
        }
        releases[index] = lease.release;
        video.src = lease.url;
        video.load();
      })
      .catch(() => {
        /* Keep the last decoded image. The download UI owns retry. */
      });
    return index;
  }

  function present(index: number, frame: number) {
    videos.forEach((item) => {
      delete item.dataset.mediaWaiting;
    });
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
    const targetSlot = load(target.index);
    videos.forEach((video, index) => {
      video.dataset.mediaWaiting = String(
        index === targetSlot && decoded[index] !== target.localFrame,
      );
    });
    seekVideo(targetSlot, target.localFrame, target.frame);
    // Two decoders alternate across any number of parts. Never replace the
    // displayed slot to warm a neighbor, or warm both neighbors into one slot.
    if (videos[targetSlot].dataset.mediaActive !== 'true') return;
    const step = parts[target.index + direction] ? direction : -direction;
    const neighbor = target.index + step;
    const part = parts[neighbor];
    if (!part) return;
    const frame =
      step < 0 ? part.startFrame + part.frames - 1 : part.startFrame;
    if (Math.abs(target.frame - frame) > warmSeconds * asset.fps) return;
    const neighborSlot = load(neighbor, 10);
    seekVideo(neighborSlot, step < 0 ? part.frames - 1 : 0);
  }

  function configure(variant: MediaVariant) {
    clear();
    selected = variant;
    options.onVariant?.(asset!, variant);
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
    if (videos.length < Math.min(2, parts.length) || end !== asset!.frames)
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
        const variant = await (options.chooseVariant
          ? options.chooseVariant(next)
          : preferredVariant(next, probe));
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
      if (time !== desired) direction = time > desired ? 1 : -1;
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
