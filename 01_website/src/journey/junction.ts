export const JUNCTION_MEDIA_VERSION = 'streetlife-v4';
/** Reach the shared junction entry before taking the turn. No hidden scene reset. */
export const JUNCTION_END = 0.18;
export const DRIVE_SECONDS = 20;
export const TURN_SECONDS = 16;
export const DRIVE_FPS = 30;
export const TURN_FPS = 30;
export function junctionProgress(progress: number) {
  return Math.min(
    1,
    Math.max(0, Number.isFinite(progress) ? progress / JUNCTION_END : 0),
  );
}
export function junctionDuration(entryPhase: number) {
  const phase = Number.isFinite(entryPhase)
    ? entryPhase >= 0
      ? entryPhase % DRIVE_SECONDS
      : ((entryPhase % DRIVE_SECONDS) + DRIVE_SECONDS) % DRIVE_SECONDS
    : 0;
  return DRIVE_SECONDS - phase + TURN_SECONDS;
}
export function sampleJunction(progress: number, entryPhase: number) {
  const phase = Number.isFinite(entryPhase)
    ? entryPhase >= 0
      ? entryPhase % DRIVE_SECONDS
      : ((entryPhase % DRIVE_SECONDS) + DRIVE_SECONDS) % DRIVE_SECONDS
    : 0;
  const remaining = DRIVE_SECONDS - phase;
  const p = Math.min(1, Math.max(0, Number.isFinite(progress) ? progress : 0));
  const elapsed = p * (remaining + TURN_SECONDS);
  return {
    driveTime: Math.min(DRIVE_SECONDS, phase + elapsed),
    turnTime: Math.min(TURN_SECONDS, Math.max(0, elapsed - remaining)),
    stage: elapsed < remaining ? ('drive' as const) : ('turn' as const),
    complete: p === 1,
  };
}
