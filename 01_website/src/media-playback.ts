export type MediaVariant = {
  src: string;
  type: string;
  codec: 'hevc' | 'h264';
  width: number;
  height: number;
  bitrate: number;
  fps: number;
};
export type MediaAsset = { fps: number; frames: number; poster: string; variants: MediaVariant[] };
export type CapabilityProbe = (variant: MediaVariant) => Promise<boolean>;

export async function browserCapability(variant: MediaVariant): Promise<boolean> {
  const video = document.createElement('video');
  if (!video.canPlayType(variant.type)) return false;
  if (!navigator.mediaCapabilities?.decodingInfo) return true;
  try {
    const result = await navigator.mediaCapabilities.decodingInfo({
      type: 'file',
      video: { contentType: variant.type, width: variant.width, height: variant.height,
        bitrate: variant.bitrate, framerate: variant.fps },
    });
    return result.supported && result.smooth;
  } catch { return false; }
}

export async function preferredVariant(asset: MediaAsset, probe: CapabilityProbe): Promise<MediaVariant> {
  const fallback = asset.variants.find(v => v.codec === 'h264');
  if (!fallback) throw new Error('An H.264 fallback is required');
  const hevc = asset.variants.find(v => v.codec === 'hevc');
  if (hevc) {
    try { if (await probe(hevc)) return hevc; } catch { /* Use the mandatory fallback. */ }
  }
  return fallback;
}

// Owns source changes only. Scroll scrubbing continues to own the playhead after loading.
export function createMediaSourceController(
  video: HTMLVideoElement,
  options: { playing?: () => boolean | undefined; onPlayBlocked?: () => void } = {},
) {
  let generation = 0;
  let disposed = false;
  let selected: MediaVariant | undefined;
  let fallback: MediaVariant | undefined;
  let restore: { time: number; playing: boolean } | undefined;
  let resumePlaying: boolean | undefined;
  function syncPlaying() {
    const playing = options.playing?.() ?? resumePlaying;
    resumePlaying = undefined;
    if (playing === true) video.play().catch(error => {
      if (error?.name === 'NotAllowedError') options.onPlayBlocked?.();
    });
    else if (playing === false) video.pause();
  }
  function metadata() {
    if (!restore) return;
    video.currentTime = Math.min(restore.time, Math.max(0, video.duration - 1 / (selected?.fps ?? 30)));
    resumePlaying = restore.playing;
    restore = undefined;
  }
  function assign(variant: MediaVariant | undefined, src: string) {
    selected = variant;
    video.src = src;
    video.load();
  }
  video.addEventListener('loadedmetadata', metadata);
  video.addEventListener('loadeddata', syncPlaying);
  return {
    async setSource(src?: string, asset?: MediaAsset, probe: CapabilityProbe = browserCapability) {
      const ticket = ++generation;
      restore = undefined;
      resumePlaying = undefined;
      fallback = undefined;
      if (!src && !asset) {
        selected = undefined;
        video.removeAttribute('src');
        video.load();
        return;
      }
      if (!asset) { assign(undefined, src!); return; }
      const candidate = await preferredVariant(asset, probe);
      if (disposed || ticket !== generation) return;
      fallback = asset.variants.find(v => v.codec === 'h264');
      assign(candidate, candidate.src);
    },
    handleError() {
      if (disposed || selected?.codec !== 'hevc' || !fallback) return false;
      restore = { time: Number.isFinite(video.currentTime) ? video.currentTime : 0, playing: !video.paused };
      const next = fallback;
      fallback = undefined;
      assign(next, next.src);
      return true;
    },
    syncPlaying,
    dispose() {
      disposed = true;
      generation++;
      video.removeEventListener('loadedmetadata', metadata);
      video.removeEventListener('loadeddata', syncPlaying);
    },
  };
}
