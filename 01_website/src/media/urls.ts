import type { MediaAsset } from './playback';

export function assetUrl(src: string, base?: string): string;
export function assetUrl(
  src: string | undefined,
  base?: string,
): string | undefined;
export function assetUrl(
  src: string | undefined,
  base = import.meta.env.BASE_URL,
): string | undefined {
  if (!src?.startsWith('/') || src.startsWith('//')) return src;
  return base.replace(/\/+$/, '') + src;
}

/** Map canonical manifest paths once at module initialization, not during render. */
export function assetWithBase(
  asset: MediaAsset,
  base = import.meta.env.BASE_URL,
): MediaAsset {
  return {
    ...asset,
    poster: assetUrl(asset.poster, base),
    variants: asset.variants.map((variant) =>
      variant.segments
        ? {
            ...variant,
            segments: variant.segments.map((segment) => ({
              ...segment,
              src: assetUrl(segment.src, base),
            })),
          }
        : { ...variant, src: assetUrl(variant.src, base) },
    ),
  };
}
