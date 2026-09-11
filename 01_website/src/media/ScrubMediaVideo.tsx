import { useEffect, useLayoutEffect, useRef, type RefObject } from 'react';
import type { MediaAsset } from './playback';
import { createSegmentedPlayback } from './segmented-playback';

type Props = {
  videoRef: RefObject<HTMLVideoElement | null>;
  secondRef: RefObject<HTMLVideoElement | null>;
  media?: MediaAsset;
  enabled: boolean;
  time: number;
  className: string;
  onReady: (ready: boolean) => void;
  onError: () => void;
};

export function ScrubMediaVideo(props: Props) {
  const latest = useRef(props);
  latest.current = props;
  const controller = useRef<ReturnType<typeof createSegmentedPlayback> | null>(
    null,
  );
  useEffect(() => {
    const first = props.videoRef.current,
      second = props.secondRef.current;
    if (!first || !second) return;
    latest.current.onReady(false);
    const playback = createSegmentedPlayback([first, second], {
      onReady: (ready) => latest.current.onReady(ready),
      onError: () => latest.current.onError(),
    });
    controller.current = playback;
    playback.seek(latest.current.time);
    void playback.setMedia(props.enabled ? props.media : undefined);
    return () => {
      playback.dispose();
      controller.current = null;
    };
  }, [props.media, props.enabled, props.videoRef, props.secondRef]);
  useLayoutEffect(() => {
    controller.current?.seek(props.time);
  }, [props.time]);
  return (
    <>
      {[props.videoRef, props.secondRef].map((ref, index) => (
        <video
          key={index}
          ref={ref}
          className={props.className}
          data-media-active="false"
          aria-hidden="true"
          muted
          playsInline
          preload="none"
          poster={props.media?.poster}
        />
      ))}
    </>
  );
}
