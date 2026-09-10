import {
  BASE_SCROLL_VIEWPORTS,
  journeyScrollDistance,
  journeyProgressFromScroll,
} from './journey-scroll';
import { MediaVideo } from './MediaVideo';
import { getProductionClip, getProductionPoster } from './production-media';
import { INITIAL_MEDIA_REQUESTS, requestNearbyMedia } from './media-loading';
import { useEffect, useMemo, useRef, useState } from 'react';
import { content as c } from './content';
import { WebsiteBody } from './WebsiteBody';
import { JunctionTransition } from './JunctionTransition';
import { MonitorApproach } from './MonitorApproach';
import {
  JUNCTION_END,
  DRIVE_FPS,
  JUNCTION_MEDIA_VERSION,
  sampleJunction,
} from './junction-transition';
import {
  CHAPTER_PROGRESS,
  sampleJourney,
  createVideoScrubber,
} from './journey-timeline';
import {
  firstCoverFrame,
  sampleQuad,
  coverQuad,
  blendQuad,
  rectQuad,
  quadMatrix,
} from './screen-projection';
import type { CSSProperties } from 'react';
import { PortalNoise, usePortalHandoff } from './PortalHandoff';
import tracking from './screen-tracking.json';
function MainHero() {
  return (
    <section className="main-hero">
      <div className="hero-label eyebrow">
        CAR PRODUCE ONE — TOYONAKA, OSAKA
      </div>
      <h1>
        {c.headline[0]}
        <br />
        {c.headline[1]}
      </h1>
      <div className="hero-bottom">
        <p>
          車と過ごす日々に、
          <br />
          あなたらしい選択を。
        </p>
        <a className="text-link" href="#services">
          私たちにできること <span>↓</span>
        </a>
      </div>
      <div className="hero-rule" />
      <div className="giant-type" aria-hidden="true">
        ONE.
      </div>
    </section>
  );
}
const profiles = {
  desktop: { width: 1280, height: 720 },
  mobile: { width: 720, height: 1280 },
};
export default function Home() {
  const city = useRef<HTMLVideoElement>(null),
    film = useRef<HTMLVideoElement>(null),
    portalFilm = useRef<HTMLVideoElement>(null),
    main = useRef<HTMLElement>(null),
    spacer = useRef<HTMLDivElement>(null);
  const tools = useRef<HTMLVideoElement>(null),
    magazines = useRef<HTMLVideoElement>(null),
    monitor = useRef<HTMLVideoElement>(null);
  const [scene, setScene] = useState(() => sampleJourney(0));
  const [turnReady, setTurnReady] = useState(false);
  const cityDriver = useRef<ReturnType<typeof createVideoScrubber> | null>(
    null,
  );
  const entryPhase = useRef<number | null>(null);
  const lastProgress = useRef(0);
  const [ready, setReady] = useState(false),
    [portalReady, setPortalReady] = useState(false),
    [failed, setFailed] = useState(false),
    [paused, setPaused] = useState(false),
    [reduced, setReduced] = useState(false),
    [menu, setMenu] = useState(false),
    [visible, setVisible] = useState(true);
  const [variant, setVariant] = useState<'desktop' | 'mobile' | null>(null),
    [view, setView] = useState({ width: 1280, height: 720 }),
    [presentedFrame, setPresentedFrame] = useState(2430),
    [idleReady, setIdleReady] = useState<Record<string, boolean>>({});
  const [requestedMedia, setRequestedMedia] = useState(INITIAL_MEDIA_REQUESTS);
  const profile = variant ?? 'desktop';
  const routeFps = getProductionClip(variant, 'route')?.fps ?? 8;
  const portalFps = getProductionClip(variant, 'portal')?.fps ?? 24;
  const scrubber = useRef<ReturnType<typeof createVideoScrubber> | null>(null),
    portalScrubber = useRef<ReturnType<typeof createVideoScrubber> | null>(
      null,
    );
  const chapter = scene.chapter,
    entered = scene.complete,
    portal = scene.portal > 0,
    moving = !scene.hold && scene.progress > 0;
  const asset = (name: string) =>
    variant ? `/media/stage4/${variant}/${name}` : undefined;
  const streetAsset = (name: string) =>
    variant
      ? `/media/junction/${variant}/${name}?v=${JUNCTION_MEDIA_VERSION}`
      : undefined;
  const junction = sampleJunction(scene.junction, entryPhase.current ?? 0);
  const scrollScale = journeyScrollDistance(1, entryPhase.current ?? 0);
  function baseScrollHeight() {
    const node = spacer.current;
    return node
      ? node.offsetHeight / Number(node.dataset.scrollScale ?? 1)
      : window.innerHeight * BASE_SCROLL_VIEWPORTS;
  }
  function go(next: number) {
    if (next < 4) handoff.reset('camera');
    setMenu(false);
    if (window.location.hash)
      window.history.replaceState(
        null,
        '',
        window.location.pathname + window.location.search,
      );
    const target = CHAPTER_PROGRESS[Math.max(0, Math.min(4, next))];
    if (target > 0 && target < 1 && entryPhase.current === null) {
      entryPhase.current = city.current?.currentTime ?? 0;
    }
    window.scrollTo({
      top:
        baseScrollHeight() *
        journeyScrollDistance(target, entryPhase.current ?? 0),
      behavior: 'instant',
    });
  }
  function skip(id?: string) {
    handoff.reset('site');
    setMenu(false);
    const target = id ? document.getElementById(id) : main.current;
    if (target)
      window.scrollTo({
        top:
          target.getBoundingClientRect().top + window.scrollY - (id ? 90 : 0),
        behavior: 'instant',
      });
    if (id && window.location.hash !== '#' + id) {
      window.history.pushState(null, '', '#' + id);
    }
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        target?.focus({ preventScroll: true });
      }),
    );
  }
  useEffect(() => {
    const followHash = () => {
      const id = window.location.hash.slice(1);
      if (['services', 'about', 'access', 'contact'].includes(id)) {
        requestAnimationFrame(() => skip(id));
      }
    };
    followHash();
    window.addEventListener('hashchange', followHash);
    return () => window.removeEventListener('hashchange', followHash);
  }, []);
  useEffect(() => {
    if (!menu) return;
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenu(false);
        document.querySelector<HTMLButtonElement>('.menu-toggle')?.focus();
      }
    };
    const wide = window.matchMedia('(min-width: 701px)');
    const dismiss = () => {
      if (wide.matches) setMenu(false);
    };
    document.addEventListener('keydown', escape);
    wide.addEventListener('change', dismiss);
    return () => {
      document.removeEventListener('keydown', escape);
      wide.removeEventListener('change', dismiss);
    };
  }, [menu]);
  function replay() {
    go(0);
  }
  function togglePause() {
    setPaused((v) => !v);
  }
  useEffect(() => {
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)'),
      mobile = window.matchMedia('(max-width:700px)');
    const motionChange = () => setReduced(motion.matches);
    const profileChange = () => {
      setFailed(false);
      setVariant(mobile.matches ? 'mobile' : 'desktop');
      setReady(false);
      setPortalReady(false);
      setIdleReady({});
      setPresentedFrame(2430);
    };
    motionChange();
    profileChange();
    motion.addEventListener('change', motionChange);
    mobile.addEventListener('change', profileChange);
    let frame = 0;
    const sync = () => {
      frame = 0;
      const height = baseScrollHeight();
      const distance = window.scrollY / height;
      if (
        distance > 0 &&
        distance <
          journeyScrollDistance(1, entryPhase.current ?? 0) - 1 / height &&
        lastProgress.current === 0 &&
        entryPhase.current === null
      ) {
        entryPhase.current = city.current?.currentTime ?? 0;
      }
      const progress = journeyProgressFromScroll(
        distance,
        entryPhase.current ?? 0,
      );
      const next = sampleJourney(progress, entryPhase.current ?? 0);
      if (next.progress === 0) {
        cityDriver.current?.release();
        entryPhase.current = null;
      } else if (entryPhase.current !== null) {
        cityDriver.current?.seek(
          sampleJunction(next.junction, entryPhase.current).driveTime,
        );
      }
      lastProgress.current = next.progress;
      setScene(next);
      scrubber.current?.seek(next.time);
      portalScrubber.current?.seek(Math.max(0, next.time - 81));
    };
    const scroll = () => {
      if (!frame) frame = requestAnimationFrame(sync);
    };
    const resize = () => {
      setView({
        width: document.documentElement.clientWidth,
        height: window.innerHeight,
      });
      scroll();
    };
    window.addEventListener('scroll', scroll, { passive: true });
    window.addEventListener('resize', resize);
    resize();
    sync();
    return () => {
      motion.removeEventListener('change', motionChange);
      mobile.removeEventListener('change', profileChange);
      window.removeEventListener('scroll', scroll);
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(frame);
    };
  }, []);
  useEffect(() => {
    const v = film.current,
      p = portalFilm.current;
    if (!v || !p) return;
    const streetDriver = city.current
      ? createVideoScrubber(city.current, DRIVE_FPS)
      : null;
    cityDriver.current = streetDriver;
    const driver = createVideoScrubber(v, routeFps),
      portalDriver = createVideoScrubber(p, portalFps);
    scrubber.current = driver;
    portalScrubber.current = portalDriver;
    const time = sampleJourney(
      journeyProgressFromScroll(
        window.scrollY / baseScrollHeight(),
        entryPhase.current ?? 0,
      ),
      entryPhase.current ?? 0,
    ).time;
    driver.seek(time);
    portalDriver.seek(Math.max(0, time - 81));
    // Geometry follows the frame actually presented, including queued decoder seeks.
    let callback = 0;
    const receive: VideoFrameRequestCallback = (_, metadata) => {
      setPresentedFrame(Math.min(2700, 2430 + metadata.mediaTime * 30));
      callback = p.requestVideoFrameCallback(receive);
    };
    const fallback = () =>
      setPresentedFrame(
        Math.min(
          2700,
          2430 + (Math.floor(p.currentTime * portalFps) / portalFps) * 30,
        ),
      );
    if (typeof p.requestVideoFrameCallback === 'function')
      callback = p.requestVideoFrameCallback(receive);
    else p.addEventListener('seeked', fallback);
    return () => {
      driver.dispose();
      streetDriver?.dispose();
      cityDriver.current = null;
      portalDriver.dispose();
      scrubber.current = null;
      portalScrubber.current = null;
      if (callback) p.cancelVideoFrameCallback(callback);
      p.removeEventListener('seeked', fallback);
    };
  }, [routeFps, portalFps, variant]);
  useEffect(() => {
    if (!reduced && !entered) {
      setRequestedMedia((previous) =>
        requestNearbyMedia(previous, scene.progress),
      );
    }
  }, [scene.progress, entered, reduced]);
  useEffect(() => {
    const update = () => setVisible(document.visibilityState === 'visible');
    update();
    document.addEventListener('visibilitychange', update);
    return () => document.removeEventListener('visibilitychange', update);
  }, []);
  const card =
    scene.hold === 'tools'
      ? c.cards[0]
      : scene.hold === 'magazines'
        ? c.cards[1]
        : null;
  const coverAt = useMemo(
    () => firstCoverFrame(tracking[profile], profiles[profile], view),
    [profile, view],
  );
  const handoff = usePortalHandoff({
    requested: scene.time * 30,
    presented: portalReady ? presentedFrame : 2430,
    coverAt,
    reduced,
    profile,
    onArrive: () =>
      window.scrollTo({
        top: Math.max(
          window.scrollY,
          spacer.current?.offsetHeight ?? window.scrollY,
        ),
        behavior: 'instant',
      }),
  });

  // Blend only after the physical bezel has left the viewport. Match the baked
  // monitor typography at the start and the normal desktop hero at the end.
  const desktopFade =
    variant === 'desktop' && handoff.active
      ? (() => {
          const t = handoff.siteOpacity;
          const mix = (a: number, b: number) => a + (b - a) * t;
          const q = sampleQuad(tracking.desktop, presentedFrame);
          if (!q) return undefined;
          const source = {
            width: mix(1280, view.width),
            height: mix(720, view.height),
          };
          const matrix = quadMatrix(
            source,
            blendQuad(coverQuad(q, profiles.desktop, view), rectQuad(view), t),
          );
          return {
            width: source.width,
            height: source.height,
            transform: matrix
              ? 'matrix3d(' + matrix.join(',') + ')'
              : undefined,
            '--screen-font':
              mix(64, Math.min(90, Math.max(40, view.width * 0.058))) + 'px',
            '--screen-top': mix(120, 180) + 'px',
            '--screen-side': mix(102.4, view.width * 0.08) + 'px',
            '--screen-bottom': mix(60, 80) + 'px',
            '--screen-heading-bottom': mix(32, 48) + 'px',
            '--screen-letter-spacing': '.12em',
            '--screen-label': '9px',
            '--screen-copy': '13px',
            '--screen-footer-display': 'flex',
            '--screen-link-margin': '0px',
            '--screen-giant':
              mix(371.2, Math.min(450, Math.max(170, view.width * 0.29))) +
              'px',
          } as CSSProperties;
        })()
      : undefined;

  const poster =
    chapter === 0
      ? 'city'
      : chapter === 1
        ? 'tools'
        : chapter === 2
          ? 'magazines'
          : 'monitor';
  return (
    <>
      <a
        className="skip-link"
        href="#services"
        onClick={(e) => {
          e.preventDefault();
          skip('services');
        }}
      >
        サービスへ移動
      </a>
      <header className={'site-header ' + (entered ? 'header-body' : '')}>
        <button
          className="wordmark"
          onClick={() =>
            entered
              ? window.scrollTo({
                  top: spacer.current?.offsetHeight ?? 0,
                  behavior: reduced ? 'instant' : 'smooth',
                })
              : go(0)
          }
          aria-label="CAR PRODUCE ONE トップ"
        >
          CAR PRODUCE ONE<span>AUTOMOTIVE / SERVICE & CARE</span>
        </button>
        <nav className="desktop-nav" aria-label="メインナビゲーション">
          <a
            href="#services"
            onClick={(e) => {
              if (!entered) {
                e.preventDefault();
                skip('services');
              }
            }}
          >
            サービス
          </a>
          <a
            href="#about"
            onClick={(e) => {
              if (!entered) {
                e.preventDefault();
                skip('about');
              }
            }}
          >
            私たちについて
          </a>
          <a
            href="#access"
            onClick={(e) => {
              if (!entered) {
                e.preventDefault();
                skip('access');
              }
            }}
          >
            アクセス
          </a>
          <a
            href="#contact"
            className="contact-link"
            onClick={(e) => {
              if (!entered) {
                e.preventDefault();
                skip('contact');
              }
            }}
          >
            相談する <span>↗</span>
          </a>
        </nav>
        <button
          className="menu-toggle"
          aria-label={menu ? 'メニューを閉じる' : 'メニューを開く'}
          aria-controls="mobile-menu"
          aria-expanded={menu}
          onClick={() => setMenu(!menu)}
        >
          {menu ? '閉じる −' : 'MENU +'}
        </button>
      </header>
      {menu && (
        <nav
          id="mobile-menu"
          className="menu-panel"
          aria-label="メインナビゲーション"
        >
          {[
            ['services', 'サービス'],
            ['about', '私たちについて'],
            ['access', 'アクセス'],
            ['contact', '相談する'],
          ].map(([id, label]) => (
            <a
              key={id}
              href={'#' + id}
              onClick={(e) => {
                e.preventDefault();
                skip(id);
              }}
            >
              {label} ↗
            </a>
          ))}
        </nav>
      )}
      {
        <section
          hidden={entered}
          className={
            'journey scroll-journey ' +
            (moving ? 'moving ' : '') +
            (portal ? 'portal ' : '')
          }
          aria-label="店舗を巡る映像"
        >
          <picture className="film fallback">
            <source
              media="(max-width:700px)"
              srcSet={
                getProductionPoster('mobile', poster) ??
                (poster === 'city'
                  ? `/media/junction/mobile/drive.jpg?v=${JUNCTION_MEDIA_VERSION}`
                  : '/media/stage4/mobile/' + poster + '.jpg')
              }
            />
            <img
              src={
                getProductionPoster('desktop', poster) ??
                (poster === 'city'
                  ? `/media/junction/desktop/drive.jpg?v=${JUNCTION_MEDIA_VERSION}`
                  : '/media/stage4/desktop/' + poster + '.jpg')
              }
              alt=""
            />
          </picture>
          <MediaVideo
            aria-hidden="true"
            videoRef={city}
            style={{
              opacity:
                scene.progress < JUNCTION_END &&
                (junction.stage === 'drive' || !turnReady) &&
                !reduced
                  ? 1
                  : 0,
            }}
            className="film city"
            autoPlay={false}
            muted
            loop
            playsInline
            poster={
              getProductionPoster(profile, 'city') ?? streetAsset('drive.jpg')
            }
            src={streetAsset('drive.mp4')}
            media={getProductionClip(variant, 'drive')}
            enabled={!reduced}
            preload="auto"
            playing={
              visible && scene.progress === 0 && !paused && !reduced && !entered
            }
            onPlayBlocked={() => setPaused(true)}
            onError={() => setFailed(true)}
          />
          <JunctionTransition
            profile={variant}
            requested={requestedMedia.junction && !reduced}
            time={junction.turnTime}
            active={
              junction.stage === 'turn' &&
              scene.progress < JUNCTION_END &&
              !reduced &&
              !failed
            }
            onReady={setTurnReady}
          />
          <MediaVideo
            aria-hidden="true"
            videoRef={film}
            className={
              'film interior ' +
              (ready && scene.time < 81 && !reduced && !failed
                ? 'visible'
                : ' ')
            }
            muted
            playsInline
            preload="metadata"
            src={asset('route.mp4')}
            media={getProductionClip(variant, 'route')}
            enabled={requestedMedia.route && !reduced}
            onLoadStart={() => setReady(false)}
            onLoadedData={() => setReady(true)}
            onError={() => setFailed(true)}
          />
          <MonitorApproach
            profile={variant}
            time={scene.time}
            requested={requestedMedia.monitor && !reduced}
          />
          <MediaVideo
            aria-hidden="true"
            videoRef={portalFilm}
            className={
              'film portal-film ' +
              (scene.time >= 81 && portalReady && !reduced ? 'visible' : '')
            }
            muted
            playsInline
            preload="metadata"
            src={asset('portal.mp4')}
            media={getProductionClip(variant, 'portal')}
            enabled={requestedMedia.portal && !reduced}
            onLoadStart={() => setPortalReady(false)}
            onError={() => setPortalReady(false)}
            onLoadedData={() => setPortalReady(true)}
          />
          {(
            [
              ['tools', tools],
              ['magazines', magazines],
              ['monitor', monitor],
            ] as const
          ).map(([name, ref]) => (
            <MediaVideo
              aria-hidden="true"
              key={name}
              videoRef={ref}
              className="film ambient"
              style={{
                opacity:
                  scene.hold === name && idleReady[name] && !reduced
                    ? scene.cardOpacity
                    : 0,
              }}
              muted
              loop
              playsInline
              preload="auto"
              src={asset(name + '-idle.mp4')}
              media={getProductionClip(variant, name + '-idle')}
              enabled={requestedMedia[name] && !reduced}
              onLoadStart={() => setIdleReady((v) => ({ ...v, [name]: false }))}
              playing={
                visible &&
                !entered &&
                !paused &&
                !reduced &&
                scene.hold === name
              }
              onLoadedData={() => setIdleReady((v) => ({ ...v, [name]: true }))}
            />
          ))}
          {scene.hold && !idleReady[scene.hold] && (
            <img
              className="film hold-poster"
              src={
                getProductionPoster(profile, scene.hold) ??
                asset(scene.hold + '.jpg')
              }
              alt=""
            />
          )}

          <div className="film-shade" />
          {scene.progress < 0.03 && (
            <div className="welcome" style={{ opacity: scene.introOpacity }}>
              <p className="eyebrow">TOYONAKA, OSAKA / AUTOMOTIVE CARE</p>
              <h1>
                {c.headline[0]}
                <br />
                {c.headline[1]}
              </h1>
              <p className="welcome-caption">
                車と過ごす日々を、あなたらしく。
              </p>
              <button className="text-link" onClick={() => go(1)}>
                店舗を巡る <span>↗</span>
              </button>
            </div>
          )}
          {card && (
            <article
              style={{ opacity: scene.cardOpacity }}
              inert={scene.cardOpacity < 0.1}
              aria-hidden={scene.cardOpacity < 0.1}
              key={chapter}
              className={'reading-card card-' + chapter}
            >
              <p className="eyebrow">{card.label}</p>
              <h2>{card.title}</h2>
              <p>{card.body}</p>
              <button className="text-link" onClick={() => skip('services')}>
                サービスを見る <span>↗</span>
              </button>
            </article>
          )}
          {scene.inviteOpacity > 0 && (
            <div
              className="monitor-invite"
              inert={scene.inviteOpacity < 0.1}
              aria-hidden={scene.inviteOpacity < 0.1}
              style={{ opacity: scene.inviteOpacity }}
            >
              <p className="eyebrow">03 / CONTINUE THE STORY</p>
              <h2>この先も、あなたと。</h2>
              <button className="text-link" onClick={() => go(4)}>
                サイトへ入る ↗
              </button>
            </div>
          )}
          {portal && reduced && (
            <div
              className="reduced-handoff"
              inert
              style={{ opacity: scene.portal }}
              aria-hidden="true"
            >
              <MainHero />
            </div>
          )}
          {handoff.siteOpacity > 0 && !reduced && (
            <div
              className={desktopFade ? 'projected-screen' : 'responsive-screen'}
              style={{ ...desktopFade, opacity: handoff.siteOpacity }}
              aria-hidden="true"
              inert
            >
              <MainHero />
            </div>
          )}
          <div className="journey-bottom">
            <div className="chapter-nav" aria-label="映像の場面">
              {c.chapters.map((label, i) => (
                <button
                  key={label}
                  aria-current={chapter === i ? 'step' : undefined}
                  onClick={() => go(i)}
                >
                  <span>0{i + 1}</span>
                  <b>{label}</b>
                </button>
              ))}
            </div>
            <div className="journey-actions">
              <button
                onClick={togglePause}
                aria-label={
                  paused ? '背景の動きを再生' : '背景の動きを一時停止'
                }
              >
                {paused ? '背景を再生 ▷' : '背景を停止 Ⅱ'}
              </button>
              <button className="next" onClick={() => go(chapter + 1)}>
                {chapter === 3 ? 'サイトへ' : '次の場面へ'} <span>↓</span>
              </button>
            </div>
          </div>
          <span className="status" aria-live="polite">
            {failed
              ? '映像を読み込めませんでした。各場面とサービスは引き続きご覧いただけます。'
              : reduced
                ? '動きを抑えて表示しています。'
                : 'スクロールに合わせて進みます / 上へ戻すとカメラも戻ります'}
          </span>
        </section>
      }
      {handoff.active && variant === 'mobile' && !reduced && (
        <PortalNoise
          key={handoff.active.id}
          video={portalFilm}
          direction={handoff.active.to}
          onSwap={handoff.swap}
          onComplete={handoff.finish}
        />
      )}
      <div
        ref={spacer}
        className="journey-scroll-space"
        aria-hidden="true"
        data-scroll-scale={scrollScale}
        style={{ height: `${BASE_SCROLL_VIEWPORTS * 100 * scrollScale}svh` }}
      />
      <main ref={main} tabIndex={-1} className="main-site" inert={!entered}>
        <MainHero />
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
    </>
  );
}
