import manifest from './manifests/portal-desktop.json';
import mobile from './manifests/portal-mobile.json';
import type { MediaAsset } from './playback';
import { assetWithBase } from './urls';
const desktopAssets = {
  portal: assetWithBase(manifest.portal as MediaAsset),
  'monitor-idle': assetWithBase(manifest['monitor-idle'] as MediaAsset),
};
const mobileAssets = {
  portal: assetWithBase(mobile.portal as MediaAsset),
  'monitor-idle': assetWithBase(mobile['monitor-idle'] as MediaAsset),
};
export function desktopPortalMedia(job: 'portal' | 'monitor-idle'): MediaAsset {
  return desktopAssets[job];
}

export function mobilePortalMedia(job: 'portal' | 'monitor-idle'): MediaAsset {
  return mobileAssets[job];
}
