import manifest from './desktop-portal-media.json';
import type { MediaAsset } from './media-playback';
export function desktopPortalMedia(job: 'portal' | 'monitor-idle'): MediaAsset {
  return manifest[job] as MediaAsset;
}
