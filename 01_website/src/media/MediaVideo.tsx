import {
  useEffect,
  useContext,
  useRef,
  type RefObject,
  type VideoHTMLAttributes,
} from 'react';
import { createMediaSourceController, type MediaAsset } from './playback';
import { DownloadContext } from './DownloadContext';
type Props = Omit<VideoHTMLAttributes<HTMLVideoElement>, 'ref'> & {
  videoRef: RefObject<HTMLVideoElement | null>;
  media?: MediaAsset;
  playing?: boolean;
  enabled?: boolean;
  onPlayBlocked?: () => void;
  buffered?: boolean;
  sourceVersion?: number;
};
export function MediaVideo({
  videoRef,
  media,
  enabled = true,
  playing,
  onPlayBlocked,
  buffered = true,
  sourceVersion = 0,
  src,
  onError,
  ...props
}: Props) {
  const downloads = useContext(DownloadContext);
  const bufferedVersion = buffered ? sourceVersion : 0;
  const latest = useRef({ playing, onPlayBlocked });
  latest.current = { playing, onPlayBlocked };
  const controller = useRef<ReturnType<
    typeof createMediaSourceController
  > | null>(null);
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const source = createMediaSourceController(video, {
      chooseVariant: downloads ? (asset) => downloads.choose(asset) : undefined,
      onVariant: downloads
        ? (asset, variant) => downloads.remember(asset, variant)
        : undefined,
      playing: () => latest.current.playing,
      onPlayBlocked: () => latest.current.onPlayBlocked?.(),
      resolveSource:
        downloads && buffered ? (src) => downloads.acquire(src) : undefined,
    });
    controller.current = source;
    void source.setSource(
      enabled ? src : undefined,
      enabled ? media : undefined,
    );
    return () => {
      source.dispose();
      controller.current = null;
    };
  }, [src, media, videoRef, enabled, downloads, buffered, bufferedVersion]);
  useEffect(() => {
    controller.current?.syncPlaying();
  }, [playing]);
  return (
    <video
      {...props}
      ref={videoRef}
      poster={media?.poster ?? props.poster}
      onError={(event) => {
        if (!controller.current?.handleError()) onError?.(event);
      }}
    />
  );
}
