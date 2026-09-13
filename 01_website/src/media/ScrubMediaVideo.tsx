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
    const staging = document.createElement('canvas');
    const capture = (source: HTMLVideoElement) => {
      const canvas = retainedFrame.current;
      if (!canvas || source.readyState < 2 || !source.videoWidth) return false;
      try {
        const context = staging.getContext('2d');
        const target = canvas.getContext('2d');
        if (!context || !target) return false;
        if (
          staging.width !== source.videoWidth ||
          staging.height !== source.videoHeight
        ) {
          staging.width = source.videoWidth;
          staging.height = source.videoHeight;
        }
        context.globalCompositeOperation = 'copy';
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
        canvas.dataset.mediaFrame = source.dataset.mediaFrame ?? '';
        return true;
      } catch {
        return false;
      }
    };
    // Keep the underlay current inside each part too. A switch-only snapshot
    // would retain the street frame throughout the first interior part.
    const retainPresented = (event: Event) => {
      const video = event.currentTarget as HTMLVideoElement;
      if (video.dataset.mediaActive === 'true' && !video.seeking)
        capture(video);
    };
    first.addEventListener('routeframe', retainPresented);
    second.addEventListener('routeframe', retainPresented);
    const playback = createSegmentedPlayback([first, second], {
      beforeSwitch: (previous, next) => capture(previous ?? next),
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
      first.removeEventListener('routeframe', retainPresented);
      second.removeEventListener('routeframe', retainPresented);
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
        />
      ))}
    </>
  );
}
