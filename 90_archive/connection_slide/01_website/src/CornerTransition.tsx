import { useEffect, useRef, useState } from 'react';
import { createVideoScrubber } from './journey-timeline';
import {
  CORNER_CUT_FRAME,
  CORNER_DURATION,
  CORNER_FPS,
  cornerFrame,
  coverPolygon,
} from './corner-transition';
import tracking from './corner-tracking.json';

type Props = {
  profile: 'desktop' | 'mobile' | null;
  progress: number;
  view: { width: number; height: number };
  disabled: boolean;
  onCovered: (covered: boolean) => void;
};
export function CornerTransition({
  profile,
  progress,
  view,
  disabled,
  onCovered,
}: Props) {
  const video = useRef<HTMLVideoElement>(null);
  const driver = useRef<ReturnType<typeof createVideoScrubber> | null>(null);
  const [ready, setReady] = useState(false);
  const [frame, setFrame] = useState(0);
  useEffect(() => {
    const element = video.current;
    if (!element) return;
    let callback = 0;
    const reportsPresentedFrames =
      typeof element.requestVideoFrameCallback === 'function';
    const receive: VideoFrameRequestCallback = (_, metadata) => {
      setFrame(cornerFrame(metadata.mediaTime));
      callback = element.requestVideoFrameCallback(receive);
    };
    const presented = () => setFrame(cornerFrame(element.currentTime));
    // Observe a completed seek BEFORE the scrubber queues the next seek.
    // With RVFC, use only the frame actually presented by the decoder.
    if (!reportsPresentedFrames) element.addEventListener('seeked', presented);
    const scrubber = createVideoScrubber(element, CORNER_FPS);
    driver.current = scrubber;
    if (reportsPresentedFrames)
      callback = element.requestVideoFrameCallback(receive);
    return () => {
      scrubber.dispose();
      driver.current = null;
      element.removeEventListener('seeked', presented);
      if (callback) element.cancelVideoFrameCallback(callback);
    };
  }, []);
  useEffect(() => {
    setReady(false);
    setFrame(0);
    onCovered(false);
  }, [profile, onCovered]);
  useEffect(() => {
    driver.current?.seek(progress * CORNER_DURATION);
  }, [progress, profile]);
  useEffect(() => {
    onCovered(ready && !disabled && frame >= CORNER_CUT_FRAME);
  }, [ready, frame, disabled, onCovered]);
  const source =
    profile === 'mobile'
      ? { width: 720, height: 1280 }
      : { width: 1280, height: 720 };
  const polygon = coverPolygon(
    tracking.profiles[profile ?? 'desktop'][frame].polygon,
    source,
    view,
  );
  const clipPath =
    frame < CORNER_CUT_FRAME
      ? 'polygon(' + polygon.map(([x, y]) => `${x}% ${y}%`).join(',') + ')'
      : 'none';
  return (
    <video
      ref={video}
      aria-hidden="true"
      className="film corner-film"
      style={{
        opacity: progress > 0 && progress < 1 && ready && !disabled ? 1 : 0,
        clipPath,
      }}
      src={profile ? `/media/corner/${profile}/corner.mp4` : undefined}
      muted
      playsInline
      preload="auto"
      onLoadedData={() => setReady(true)}
      onError={() => {
        setReady(false);
        onCovered(false);
      }}
    />
  );
}
