import manifest from './desktop-portal-media.json';
import mobile from './mobile-portal-media.json';
import type { MediaAsset } from './media-playback';
export function desktopPortalMedia(job: 'portal' | 'monitor-idle'): MediaAsset {
  return manifest[job] as MediaAsset;
}

export function mobilePortalMedia(job: 'portal' | 'monitor-idle'): MediaAsset {
  return mobile[job] as MediaAsset;
}
