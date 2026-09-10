import {
  JUNCTION_END,
  junctionProgress,
  junctionDuration,
} from './junction-transition.ts';
/** Camera position is a pure function of document scroll, never elapsed time. */
export type Hold = 'tools' | 'magazines' | 'monitor';
export const CHAPTER_PROGRESS = [0, 0.4, 0.7, 0.89, 1] as const;
export const HOLD_RANGES = {
  tools: [0.35, 0.46],
  magazines: [0.65, 0.76],
  monitor: [0.88, 0.9],
} as const;
const clamp = (v: number) => Math.min(1, Math.max(0, v));
const interpolate = (p: number, a: number, b: number, x: number, y: number) =>
  x + (y - x) * clamp((p - a) / (b - a));
export function sampleJourney(value: number, entryPhase = 0) {
  const p = clamp(Number.isFinite(value) ? value : 0);
  let time = 0,
    hold: Hold | null = null;
  if (p < JUNCTION_END) time = 0;
  else if (p < 0.35) {
    // Match the outgoing turn's virtual-time slope at the shared arrival pose.
    const u = (p - JUNCTION_END) / (0.35 - JUNCTION_END);
    const linear =
      (junctionDuration(entryPhase) / JUNCTION_END) * (0.35 - JUNCTION_END);
    time = linear * u + (34.2 - linear) * u * u;
  } else if (p < 0.46) {
    time = 34.2;
    hold = 'tools';
  } else if (p < 0.65) time = interpolate(p, 0.46, 0.65, 43.2, 56.7);
  else if (p < 0.76) {
    time = 56.7;
    hold = 'magazines';
  } else if (p < 0.88) time = interpolate(p, 0.76, 0.88, 67.5, 81);
  else if (p < 0.9) {
    time = 81;
    hold = 'monitor';
  } else time = interpolate(p, 0.9, 1, 81, 90);
  let cardOpacity = 0;
  if (hold) {
    const [a, b] = HOLD_RANGES[hold];
    const edge = Math.min(0.012, (b - a) / 4);
    cardOpacity = Math.min(clamp((p - a) / edge), clamp((b - p) / edge));
  }
  return {
    progress: p,
    junction: junctionProgress(p),
    time,
    hold,
    cardOpacity,
    chapter: p < JUNCTION_END ? 0 : p < 0.46 ? 1 : p < 0.76 ? 2 : 3,
    introOpacity: 1 - clamp(p / 0.03),
    portal: clamp((p - 0.9) / 0.1),
    complete: p >= 1,
  };
}

/** Coalesce seeks while a decoder is busy. Always finish on the latest scroll. */
export interface SeekableVideo {
  currentTime: number;
  duration: number;
  readyState: number;
  seeking: boolean;
  pause(): void;
  addEventListener(type: string, fn: () => void): void;
  removeEventListener(type: string, fn: () => void): void;
}
export function createVideoScrubber(video: SeekableVideo, fps = 8) {
  let desired = 0,
    disposed = false,
    released = false;
  const flush = () => {
    if (disposed || released || video.readyState < 1 || video.seeking) return;
    const max = Number.isFinite(video.duration)
      ? Math.max(0, video.duration - 1 / fps)
      : 89.875;
    const next = Math.min(max, Math.max(0, desired));
    if (video.readyState < 2 || Math.abs(video.currentTime - next) >= 0.5 / fps)
      video.currentTime = next;
  };
  video.pause();
  video.addEventListener('seeked', flush);
  video.addEventListener('loadedmetadata', flush);
  video.addEventListener('loadeddata', flush);
  return {
    seek(time: number) {
      released = false;
      desired = time;
      video.pause();
      flush();
    },
    release() {
      released = true;
    },
    dispose() {
      disposed = true;
      video.removeEventListener('seeked', flush);
      video.removeEventListener('loadedmetadata', flush);
      video.removeEventListener('loadeddata', flush);
    },
  };
}
