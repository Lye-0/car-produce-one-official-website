import manifest from './manifests/portal-desktop.json';
import mobile from './manifests/portal-mobile.json';
import type { MediaAsset } from './playback';
export function desktopPortalMedia(job: 'portal' | 'monitor-idle'): MediaAsset {
  return manifest[job] as MediaAsset;
}

export function mobilePortalMedia(job: 'portal' | 'monitor-idle'): MediaAsset {
  return mobile[job] as MediaAsset;
}
