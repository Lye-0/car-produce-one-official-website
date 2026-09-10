/** Physical scroll distance, measured in the original journey's scroll range. */
import {
  JUNCTION_END,
  TURN_SECONDS,
  junctionDuration,
} from './junction-transition.ts';

export const BASE_SCROLL_VIEWPORTS = 12;
export const INTERIOR_SCROLL_MULTIPLIER = 2;

export function turnScrollStart(entryPhase = 0) {
  return JUNCTION_END * (1 - TURN_SECONDS / junctionDuration(entryPhase));
}

/** Integrate a smooth 1x -> 2x scroll cost across the turn, then keep 2x. */
export function journeyScrollDistance(progress: number, entryPhase = 0) {
  const p = Math.min(1, Math.max(0, Number.isFinite(progress) ? progress : 0));
  const start = turnScrollStart(entryPhase);
  const length = JUNCTION_END - start;
  if (p <= start) return p;
  const u = Math.min(1, (p - start) / length);
  // Integral of smoothstep(u) = 3u² - 2u³; its endpoint slopes are zero.
  const turnExtra = length * (u ** 3 - u ** 4 / 2);
  return (
    p +
    (INTERIOR_SCROLL_MULTIPLIER - 1) *
      (turnExtra + Math.max(0, p - JUNCTION_END))
  );
}

/** Pure inverse: reversing the document scroll retraces exactly the same frames. */
export function journeyProgressFromScroll(distance: number, entryPhase = 0) {
  const d = Math.max(0, Number.isFinite(distance) ? distance : 0);
  if (d >= journeyScrollDistance(1, entryPhase) - 1e-12) return 1;
  const start = turnScrollStart(entryPhase);
  if (d <= start) return d;
  const end = journeyScrollDistance(JUNCTION_END, entryPhase);
  if (d >= end)
    return Math.min(1, JUNCTION_END + (d - end) / INTERIOR_SCROLL_MULTIPLIER);
  let low = start,
    high = JUNCTION_END;
  for (let i = 0; i < 40; i++) {
    const middle = (low + high) / 2;
    if (journeyScrollDistance(middle, entryPhase) < d) low = middle;
    else high = middle;
  }
  return (low + high) / 2;
}
