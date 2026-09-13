import {
  useContext,
  useEffect,
  useLayoutEffect,
  useRef,
  type RefObject,
} from 'react';
import { DownloadContext } from './DownloadContext';
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
  const retainedFrame = useRef<HTMLCanvasElement>(null);
  const downloads = useContext(DownloadContext);
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
    if (retainedFrame.current) retainedFrame.current.width = 0;
    const playback = createSegmentedPlayback([first, second], {
      beforeSwitch: (previous, next) => {
        const canvas = retainedFrame.current;
        const source = previous ?? next;
        if (!canvas || source.readyState < 2 || !source.videoWidth)
          return false;
        // Capture the outgoing decoded image BEFORE either native video layer
        // changes. Safari may present the replacement layer one paint later.
        // A staging canvas keeps an existing good snapshot intact on failure.
        const staging = document.createElement('canvas');
        staging.width = source.videoWidth;
        staging.height = source.videoHeight;
        try {
          const context = staging.getContext('2d');
          const target = canvas.getContext('2d');
          if (!context || !target) return false;
          context.drawImage(source, 0, 0);
          if (
            canvas.width !== staging.width ||
            canvas.height !== staging.height
          ) {
            canvas.width = staging.width;
            canvas.height = staging.height;
          }
          target.globalCompositeOperation = 'copy';
          target.drawImage(staging, 0, 0);
          return true;
        } catch {
          return false;
        }
      },
      chooseVariant: downloads ? (asset) => downloads.choose(asset) : undefined,
      onVariant: downloads
        ? (asset, variant) => downloads.remember(asset, variant)
        : undefined,
      onReady: (ready) => latest.current.onReady(ready),
      onError: () => latest.current.onError(),
      resolveSource: downloads
        ? (src, priority) => downloads.acquire(src, priority)
        : undefined,
    });
    controller.current = playback;
    playback.seek(latest.current.time);
    void playback.setMedia(props.enabled ? props.media : undefined);
    return () => {
      playback.dispose();
      controller.current = null;
    };
  }, [props.media, props.enabled, props.videoRef, props.secondRef, downloads]);
  useLayoutEffect(() => {
    controller.current?.seek(props.time);
  }, [props.time]);
  return (
    <>
      <canvas
        ref={retainedFrame}
        className={`${props.className.replace(/\binterior\b/g, '')} route-retained-frame`}
        aria-hidden="true"
      />
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
