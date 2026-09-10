export const PORTAL_DURATION = 700;
export const PORTAL_SWAP = 300;
export const PORTAL_RESET_MARGIN = 18;
export type PortalSide = 'camera' | 'site';
export function portalDirection(
  side: PortalSide,
  requested: number,
  presented: number,
  coverAt: number,
) {
  if (
    side === 'camera' &&
    requested >= coverAt &&
    (presented >= coverAt || requested >= 2700)
  )
    return 'site';
  if (side === 'site' && requested < coverAt - PORTAL_RESET_MARGIN)
    return 'camera';
  return null;
}
export function portalTiming(elapsed: number) {
  const time = Math.max(0, elapsed);
  return {
    swapped: time >= PORTAL_SWAP,
    complete: time >= PORTAL_DURATION,
    distortion: Math.max(0, 1 - time / 150),
    cover: Math.min(1, time / 150),
    reveal: Math.min(1, Math.max(0, (time - 450) / 250)),
  };
}
