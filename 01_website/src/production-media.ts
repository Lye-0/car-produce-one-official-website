import manifest from './production-media.json';
import type { MediaAsset } from './media-playback';
const profiles = manifest.profiles as Partial<
  Record<'desktop' | 'mobile', Record<string, MediaAsset>>
>;
export function getProductionClip(
  profile: 'desktop' | 'mobile' | null,
  job: string,
): MediaAsset | undefined {
  return profile ? profiles[profile]?.[job] : undefined;
}

export function getProductionPoster(
  profile: 'desktop' | 'mobile',
  scene: string,
): string | undefined {
  if (scene === 'monitor') return manifest.posters[profile]['monitor-idle'];
  return getProductionClip(
    profile,
    scene === 'city' ? 'drive' : scene + '-idle',
  )?.poster;
}
