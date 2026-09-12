export type MediaSegment = {
  src: string;
  startFrame: number;
  frames: number;
  bytes?: number;
};
export type MediaVariant = (
  | { src: string; segments?: undefined }
  | { src?: undefined; segments: MediaSegment[] }
) & {
  type: string;
  codec: 'hevc' | 'h264';
  width: number;
  height: number;
  bitrate: number;
  fps: number;
  bytes?: number;
};
export type MediaAsset = {
  fps: number;
  frames: number;
  poster: string;
  variants: MediaVariant[];
};
export type CapabilityProbe = (variant: MediaVariant) => Promise<boolean>;

export async function browserCapability(
  variant: MediaVariant,
): Promise<boolean> {
  const video = document.createElement('video');
  if (!video.canPlayType(variant.type)) return false;
  if (!navigator.mediaCapabilities?.decodingInfo) return true;
  try {
    const result = await navigator.mediaCapabilities.decodingInfo({
      type: 'file',
      video: {
        contentType: variant.type,
        width: variant.width,
        height: variant.height,
        bitrate: variant.bitrate,
        framerate: variant.fps,
      },
    });
    return result.supported && result.smooth;
  } catch {
    return false;
  }
}

export async function preferredVariant(
  asset: MediaAsset,
  probe: CapabilityProbe,
  timeoutMs = 1500,
): Promise<MediaVariant> {
  const fallback = asset.variants.find((v) => v.codec === 'h264');
  if (!fallback) throw new Error('An H.264 fallback is required');
  const hevc = asset.variants.find((v) => v.codec === 'hevc');
  if (hevc) {
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      const supported = await Promise.race([
        probe(hevc),
        new Promise<boolean>((resolve) => {
          timer = setTimeout(() => resolve(false), timeoutMs);
        }),
      ]);
      if (supported) return hevc;
    } catch {
      /* Use the mandatory fallback. */
    } finally {
      if (timer !== undefined) clearTimeout(timer);
    }
  }
  return fallback;
}

function singleFile(variant: MediaVariant): string {
  if (variant.segments)
    throw new Error('Segmented assets require ScrubMediaVideo.');
  return variant.src;
}

// Owns source changes only. Scroll scrubbing continues to own the playhead after loading.
export function createMediaSourceController(
  video: HTMLVideoElement,
  options: {
    playing?: () => boolean | undefined;
    onPlayBlocked?: () => void;
    resolveSource?: (
      src: string,
    ) => Promise<{ url: string; release: () => void }>;
    onSourceError?: () => void;
    chooseVariant?: (asset: MediaAsset) => Promise<MediaVariant>;
    onVariant?: (asset: MediaAsset, variant: MediaVariant) => void;
  } = {},
) {
  let generation = 0;
  let disposed = false;
  let hasSource = false;
  let pending = false;
  let selected: MediaVariant | undefined;
  let fallback: MediaVariant | undefined;
  let restore: { time: number; playing: boolean } | undefined;
  let resumePlaying: boolean | undefined;
  let sourceTicket = 0;
  let currentAsset: MediaAsset | undefined;
  let release: (() => void) | undefined;
  function syncPlaying() {
    if (disposed || !hasSource || pending) return;
    const playing = options.playing?.() ?? resumePlaying;
    resumePlaying = undefined;
    if (playing === true)
      video.play().catch((error) => {
        if (!disposed && error?.name === 'NotAllowedError')
          options.onPlayBlocked?.();
      });
    else if (playing === false) video.pause();
  }
  function metadata() {
    if (!restore) return;
    video.currentTime = Math.min(
      restore.time,
      Math.max(0, video.duration - 1 / (selected?.fps ?? 30)),
    );
    resumePlaying = restore.playing;
    restore = undefined;
  }
  function assign(variant: MediaVariant | undefined, src: string) {
    const ticket = ++sourceTicket;
    selected = variant;
    if (variant && currentAsset) options.onVariant?.(currentAsset, variant);
    hasSource = true;
    const install = (url: string) => {
      video.src = url;
      video.load();
    };
    release?.();
    release = undefined;
    if (!options.resolveSource) {
      install(src);
      return;
    }
    pending = true;
    video.dataset.downloadSource = src;
    options
      .resolveSource(src)
      .then((lease) => {
        if (disposed || ticket !== sourceTicket) {
          lease.release();
          return;
        }
        release = lease.release;
        pending = false;
        install(lease.url);
      })
      .catch(() => {
        if (disposed || ticket !== sourceTicket) return;
        pending = false;
        options.onSourceError?.();
      });
  }
  function clearSource() {
    sourceTicket++;
    release?.();
    release = undefined;
    video.pause();
    selected = undefined;
    hasSource = false;
    video.removeAttribute('src');
    video.load();
  }
  video.addEventListener('loadedmetadata', metadata);
  video.addEventListener('loadeddata', syncPlaying);
  return {
    async setSource(
      src?: string,
      asset?: MediaAsset,
      probe: CapabilityProbe = browserCapability,
    ) {
      if (disposed) return;
      const ticket = ++generation;
      currentAsset = asset;
      pending = false;
      restore = undefined;
      resumePlaying = undefined;
      fallback = undefined;
      if (!src && !asset) {
        clearSource();
        return;
      }
      if (!asset) {
        assign(undefined, src!);
        return;
      }
      pending = true;
      clearSource();
      let candidate: MediaVariant;
      try {
        candidate = await (options.chooseVariant
          ? options.chooseVariant(asset)
          : preferredVariant(asset, probe));
      } catch (error) {
        if (disposed || ticket !== generation) return;
        pending = false;
        if (src) {
          assign(undefined, src);
          return;
        }
        throw error;
      }
      if (disposed || ticket !== generation) return;
      pending = false;
      fallback = asset.variants.find((v) => v.codec === 'h264');
      assign(candidate, singleFile(candidate));
    },
    handleError() {
      if (disposed || pending || !hasSource) return true;
      if (selected?.codec !== 'hevc' || !fallback) return false;
      restore = {
        time: Number.isFinite(video.currentTime) ? video.currentTime : 0,
        playing: !video.paused,
      };
      const next = fallback;
      fallback = undefined;
      assign(next, singleFile(next));
      return true;
    },
    syncPlaying,
    dispose() {
      disposed = true;
      sourceTicket++;
      release?.();
      release = undefined;
      generation++;
      video.removeEventListener('loadedmetadata', metadata);
      video.removeEventListener('loadeddata', syncPlaying);
    },
  };
}
