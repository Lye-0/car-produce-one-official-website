import { useEffect, useRef, useState } from 'react';
import { MediaVideo } from './MediaVideo';
import { getProductionClip } from './production-media';
import { createVideoScrubber } from './journey-timeline';
export function MonitorApproach({
  profile,
  time,
  requested,
}: {
  profile: 'desktop' | 'mobile' | null;
  time: number;
  requested: boolean;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const driver = useRef<ReturnType<typeof createVideoScrubber> | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!video.current) return;
    const scrubber = createVideoScrubber(video.current, 30);
    driver.current = scrubber;
    return () => {
      scrubber.dispose();
      driver.current = null;
    };
  }, []);
  useEffect(() => {
    setReady(false);
  }, [profile]);
  useEffect(() => {
    driver.current?.seek(Math.max(0, time - 78));
  }, [time, profile]);
  return (
    <MediaVideo
      videoRef={video}
      media={getProductionClip(profile, 'monitor-approach')}
      enabled={requested}
      muted
      playsInline
      preload="auto"
      aria-hidden="true"
      className="film monitor-approach"
      style={{ opacity: requested && ready && time >= 78 && time < 81 ? 1 : 0 }}
      onLoadStart={() => setReady(false)}
      onLoadedData={() => setReady(true)}
      onError={() => setReady(false)}
    />
  );
}
