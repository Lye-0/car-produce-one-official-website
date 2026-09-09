import { useEffect, useRef, useState } from 'react';
import { createVideoScrubber } from './journey-timeline';
import { TURN_FPS } from './junction-transition';
type Props = {
  profile: 'desktop' | 'mobile' | null;
  time: number;
  active: boolean;
  onReady: (ready: boolean) => void;
};
export function JunctionTransition({ profile, time, active, onReady }: Props) {
  const video = useRef<HTMLVideoElement>(null);
  const driver = useRef<ReturnType<typeof createVideoScrubber> | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!video.current) return;
    const scrubber = createVideoScrubber(video.current, TURN_FPS);
    driver.current = scrubber;
    return () => {
      scrubber.dispose();
      driver.current = null;
    };
  }, []);
  useEffect(() => {
    setReady(false);
    onReady(false);
  }, [profile, onReady]);
  useEffect(() => {
    driver.current?.seek(time);
  }, [time, profile]);
  return (
    <video
      ref={video}
      aria-hidden="true"
      className="film junction-film"
      style={{ opacity: active && ready ? 1 : 0 }}
      src={profile ? `/media/junction/${profile}/turn.mp4` : undefined}
      muted
      playsInline
      preload="auto"
      onLoadedData={() => {
        setReady(true);
        onReady(true);
      }}
      onError={() => {
        setReady(false);
        onReady(false);
      }}
    />
  );
}
