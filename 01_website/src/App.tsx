import { MainHero } from './components/MainHero';
import { SiteHeader } from './components/SiteHeader';
import { WebsiteBody } from './components/WebsiteBody';
import { Journey } from './journey/Journey';
import { useJourney } from './journey/useJourney';
import { BASE_SCROLL_VIEWPORTS } from './journey/scroll';
import { DownloadContext } from './media/DownloadContext';
import { VideoLoading } from './components/VideoLoading';
import './styles/video-loading.css';
export default function App() {
  const journey = useJourney();
  const {
    spacer,
    scrollScale,
    liveEnabled,
    view,
    main,
    entered,
    heroSlot,
    heroViewport,
    profile,
    replay,
    reduced,
  } = journey;
  return (
    <DownloadContext.Provider value={journey.startup.downloads}>
      <SiteHeader state={journey} />
      <div inert={journey.startup.blocked && !journey.startup.cityReady}>
        <Journey state={journey} />
      </div>
      <VideoLoading state={journey} />
      <div
        ref={spacer}
        className="journey-scroll-space"
        aria-hidden="true"
        data-scroll-scale={scrollScale}
        style={{
          height: liveEnabled
            ? `${Math.round(view.height * BASE_SCROLL_VIEWPORTS * scrollScale)}px`
            : `${BASE_SCROLL_VIEWPORTS * 100 * scrollScale}svh`,
        }}
      />
      <main ref={main} tabIndex={-1} className="main-site" inert={!entered}>
        {liveEnabled ? (
          <div ref={heroSlot} className="portal-hero-slot">
            <div ref={heroViewport} className="portal-hero-viewport">
              <MainHero projected mobileWings={profile === 'mobile'} />
            </div>
          </div>
        ) : (
          <MainHero />
        )}
        <WebsiteBody
          replay={replay}
          top={() => {
            window.scrollTo({
              top: spacer.current?.offsetHeight ?? 0,
              behavior: reduced ? 'instant' : 'smooth',
            });
            main.current?.focus({ preventScroll: true });
          }}
        />
      </main>
    </DownloadContext.Provider>
  );
}
