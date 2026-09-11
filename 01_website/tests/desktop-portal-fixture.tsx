import React, { useRef, useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { MainHero } from '../src/App';
import { DesktopPortal } from '../src/DesktopPortal';
import { MediaVideo } from '../src/MediaVideo';
import {
  desktopPortalMedia,
  mobilePortalMedia,
} from '../src/desktop-portal-media';
import { createVideoScrubber } from '../src/journey-timeline';
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
    (window as any).desktopFixture = { ready, setNative };
  }, [ready]);
  return (
    <>
      <section
        className="journey scroll-journey desktop-exact-journey"
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
        <DesktopPortal
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
        <div ref={slot} className="desktop-hero-slot">
          <div ref={viewport} className="desktop-hero-viewport">
            <MainHero desktop mobileWings={mobile} />
          </div>
        </div>
      </main>
    </>
  );
}
createRoot(document.getElementById('root')!).render(<Fixture />);
