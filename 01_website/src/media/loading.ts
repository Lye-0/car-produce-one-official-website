export type RequestedMedia = {
  junction: boolean;
  route: boolean;
  portal: boolean;
  tools: boolean;
  magazines: boolean;
  monitor: boolean;
};
export const INITIAL_MEDIA_REQUESTS: RequestedMedia = {
  junction: false,
  route: false,
  portal: false,
  tools: false,
  magazines: false,
  monitor: false,
};
const thresholds: Record<keyof RequestedMedia, number> = {
  junction: 0,
  route: 0.1,
  tools: 0.28,
  magazines: 0.56,
  monitor: 0.8,
  portal: 0.85,
};
/** Keep requested footage for reverse scrolling; skipping the journey requests nothing new. */
export function requestNearbyMedia(
  previous: RequestedMedia,
  progress: number,
): RequestedMedia {
  if (!Number.isFinite(progress) || progress <= 0 || progress >= 1)
    return previous;
  let next = previous;
  for (const key of Object.keys(thresholds) as (keyof RequestedMedia)[]) {
    if (!previous[key] && progress > thresholds[key]) {
      if (next === previous) next = { ...previous };
      next[key] = true;
    }
  }
  return next;
}
