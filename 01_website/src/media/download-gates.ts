import { sampleJourney } from '../journey/timeline.ts';
import type { MediaVariant } from './playback.ts';
export type GateFile = { src: string; bytes?: number };
export type DownloadGate = { before: number; files: GateFile[] };
export type MediaSpan = { start: number; end: number; files: GateFile[] };
export function constrainMediaProgress(
  requested: number,
  current: number,
  spans: MediaSpan[],
  ready: (src: string) => boolean,
) {
  const reverse = requested < current;
  let progress = requested;
  let files: GateFile[] = [];
  for (const span of spans) {
    if (span.files.every((file) => ready(file.src))) continue;
    if (
      reverse
        ? requested >= span.end || current <= span.start
        : requested <= span.start || current >= span.end
    )
      continue;
    const boundary = reverse
      ? Math.min(current, Math.min(1, span.end + 1e-5))
      : Math.max(current, span.start);
    if (reverse ? boundary > progress + 1e-8 : boundary < progress - 1e-8) {
      progress = boundary;
      files = [...span.files];
    } else if (Math.abs(boundary - progress) < 1e-8) files.push(...span.files);
  }
  return { progress, files };
}

/** Stay on a frame owned by the preceding part, including jumps over holds. */
export function beforeRouteFrame(startFrame: number, fps: number) {
  const time = (startFrame - 0.5) / fps;
  let lo = 0,
    hi = 1;
  for (let i = 0; i < 48; i++) {
    const mid = (lo + hi) / 2;
    if (sampleJourney(mid).time < time) lo = mid;
    else hi = mid;
  }
  return Math.max(0, lo - 1e-7);
}
export function routeDownloadGates(
  variant: MediaVariant,
  fps: number,
): DownloadGate[] {
  return (variant.segments ?? []).slice(1).map((part) => ({
    before: beforeRouteFrame(part.startFrame, fps),
    files: [part],
  }));
}
export function nextDownloadGate(
  gates: DownloadGate[],
  ready: (src: string) => boolean,
) {
  return [...gates]
    .sort((a, b) => a.before - b.before)
    .find((gate) => gate.files.some((file) => !ready(file.src)));
}
export function capForwardProgress(
  requested: number,
  current: number,
  limit: number,
) {
  return requested > current
    ? Math.min(requested, Math.max(current, limit))
    : requested;
}
