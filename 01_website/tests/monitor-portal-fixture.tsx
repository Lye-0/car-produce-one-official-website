import React, { useRef, useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { MainHero } from '../src/components/MainHero';
import { MonitorPortal } from '../src/portal/MonitorPortal';
import { MediaVideo } from '../src/media/MediaVideo';
import { desktopPortalMedia, mobilePortalMedia } from '../src/media/portal';
import { createVideoScrubber } from '../src/journey/timeline';
function Fixture() {
  const mobile =
    new URLSearchParams(location.search).get('profile') === 'mobile';
  const portal = useRef<HTMLVideoElement>(null),
    route = useRef<HTMLVideoElement>(null),
    monitor = useRef<HTMLVideoElement>(null),
    viewport = useRef<HTMLDivElement>(null),
    slot = useRef<HTMLDivElement>(null);
  const [native, setNative] = useState(false),
    [ready, setReady] = useState(false);
  useEffect(() => {
    const driver = createVideoScrubber(portal.current!, 30, true);
    driver.seek(9);
    return () => driver.dispose();
  }, []);
  useEffect(() => {
    (window as any).portalFixture = { ready, setNative };
  }, [ready]);
  return (
    <>
      <section
        className="journey scroll-journey monitor-portal-journey"
        hidden={native}
      >
        <MediaVideo
          videoRef={portal}
          media={(mobile ? mobilePortalMedia : desktopPortalMedia)('portal')}
          muted
          playsInline
          preload="auto"
          className="film visible"
        />
        <MonitorPortal
          profile={mobile ? 'mobile' : 'desktop'}
          enabled
          time={90}
          hold={false}
          complete
          entered={native}
          bypass={false}
          route={route}
          portal={portal}
          monitor={monitor}
          viewport={viewport}
          slot={slot}
          onEndpoint={setReady}
        />
      </section>
      <main className="main-site" inert={!native}>
        <div ref={slot} className="portal-hero-slot">
          <div ref={viewport} className="portal-hero-viewport">
            <MainHero projected mobileWings={mobile} />
          </div>
        </div>
      </main>
    </>
  );
}
createRoot(document.getElementById('root')!).render(<Fixture />);
