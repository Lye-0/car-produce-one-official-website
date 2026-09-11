import manifest from './manifests/journey.json';
import type { MediaAsset } from './playback';
import { assetUrl, assetWithBase } from './urls';
const profiles = Object.fromEntries(
  Object.entries(manifest.profiles).map(([profile, clips]) => [
    profile,
    Object.fromEntries(
      Object.entries(clips).map(([job, asset]) => [
        job,
        assetWithBase(asset as MediaAsset),
      ]),
    ),
  ]),
) as Partial<Record<'desktop' | 'mobile', Record<string, MediaAsset>>>;
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
  if (scene === 'monitor')
    return assetUrl(manifest.posters[profile]['monitor-idle']);
  return getProductionClip(
    profile,
    scene === 'city' ? 'drive' : scene + '-idle',
  )?.poster;
}
