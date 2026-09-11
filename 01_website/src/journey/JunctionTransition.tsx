import { MediaVideo } from '../media/MediaVideo';
import { getProductionClip } from '../media/production';
import { useEffect, useRef, useState } from 'react';
import { createVideoScrubber } from './timeline';
import { TURN_FPS } from './junction';
type Props = {
  profile: 'desktop' | 'mobile' | null;
  time: number;
  requested: boolean;
  active: boolean;
  onReady: (ready: boolean) => void;
};
export function JunctionTransition({
  profile,
  time,
  active,
  requested,
  onReady,
}: Props) {
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
    <MediaVideo
      videoRef={video}
      media={getProductionClip(profile, 'junction')}
      enabled={requested}
      aria-hidden="true"
      className="film junction-film"
      style={{ opacity: active && ready ? 1 : 0 }}
      muted
      playsInline
      preload="metadata"
      onLoadStart={() => {
        setReady(false);
        onReady(false);
      }}
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
