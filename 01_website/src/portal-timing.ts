export const PORTAL_DURATION = 450;
export const PORTAL_SWAP = 190;
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
  const u = Math.min(1, Math.max(0, (time - 280) / 170));
  return {
    swapped: time >= PORTAL_SWAP,
    complete: time >= PORTAL_DURATION,
    distortion: Math.max(0, 1 - time / 100),
    cover: Math.min(1, time / 100),
    settle: u * u * (3 - 2 * u),
  };
}
