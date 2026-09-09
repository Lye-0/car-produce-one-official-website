import { useEffect, useRef, type RefObject, type VideoHTMLAttributes } from 'react';
import { createMediaSourceController, type MediaAsset } from './media-playback';
type Props = Omit<VideoHTMLAttributes<HTMLVideoElement>, 'ref'> & {
  videoRef: RefObject<HTMLVideoElement | null>;
  media?: MediaAsset;
  playing?: boolean;
  onPlayBlocked?: () => void;
};
export function MediaVideo({ videoRef, media, playing, onPlayBlocked, src, onError, ...props }: Props) {
  const latest = useRef({ playing, onPlayBlocked });
  latest.current = { playing, onPlayBlocked };
  const controller = useRef<ReturnType<typeof createMediaSourceController> | null>(null);
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const source = createMediaSourceController(video, {
      playing: () => latest.current.playing,
      onPlayBlocked: () => latest.current.onPlayBlocked?.(),
    });
    controller.current = source;
    void source.setSource(src, media);
    return () => { source.dispose(); controller.current = null; };
  }, [src, media, videoRef]);
  useEffect(() => { controller.current?.syncPlaying(); }, [playing]);
  return <video {...props} ref={videoRef} poster={media?.poster ?? props.poster}
    onError={event => { if (!controller.current?.handleError()) onError?.(event); }} />;
}
