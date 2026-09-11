import {
  BASE_SCROLL_VIEWPORTS,
  journeyScrollDistance,
  journeyProgressFromScroll,
} from './scroll';
import { getProductionClip } from '../media/production';
import { INITIAL_MEDIA_REQUESTS, requestNearbyMedia } from '../media/loading';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { content as c } from '../content';
import { DRIVE_FPS, JUNCTION_MEDIA_VERSION, sampleJunction } from './junction';
import {
  CHAPTER_PROGRESS,
  sampleJourney,
  createVideoScrubber,
} from './timeline';
import { desktopPortalMedia, mobilePortalMedia } from '../media/portal';
export function useJourney() {
  const city = useRef<HTMLVideoElement>(null),
    film = useRef<HTMLVideoElement>(null),
    portalFilm = useRef<HTMLVideoElement>(null),
    main = useRef<HTMLElement>(null),
    spacer = useRef<HTMLDivElement>(null),
    heroViewport = useRef<HTMLDivElement>(null),
    heroSlot = useRef<HTMLDivElement>(null);
  const tools = useRef<HTMLVideoElement>(null),
    magazines = useRef<HTMLVideoElement>(null),
    monitor = useRef<HTMLVideoElement>(null);
  const [portalEndReady, setPortalEndReady] = useState(false);
  const [portalBypass, setPortalBypass] = useState(false);
  const [pastHero, setPastHero] = useState(false);
  const pendingViewportResize = useRef<number | null>(null);
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
    [idleReady, setIdleReady] = useState<Record<string, boolean>>({});
  const [requestedMedia, setRequestedMedia] = useState(INITIAL_MEDIA_REQUESTS);
  const profile = variant ?? 'desktop';
  const liveEnabled = variant !== null && !reduced;
  const routeFps = getProductionClip(variant, 'route')?.fps ?? 8;
  const liveMedia =
    profile === 'mobile' ? mobilePortalMedia : desktopPortalMedia;
  const portalFps = liveMedia('portal').fps;
  const scrubber = useRef<ReturnType<typeof createVideoScrubber> | null>(null),
    portalScrubber = useRef<ReturnType<typeof createVideoScrubber> | null>(
      null,
    );
  const chapter = scene.chapter,
    entered =
      scene.complete &&
      (!liveEnabled || portalEndReady || portalBypass || failed),
    portal = scene.portal > 0,
    moving = !scene.hold && scene.progress > 0;
  const asset = (name: string) =>
    variant ? `/media/images/fallback/${variant}/${name}` : undefined;
  const streetAsset = (name: string) =>
    variant
      ? `/media/images/fallback/${variant}/${name}?v=${JUNCTION_MEDIA_VERSION}`
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
    if (next < 4) {
      setPortalBypass(false);
      setPortalEndReady(false);
    }
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
    setPortalBypass(true);
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
  useLayoutEffect(() => {
    const progress = pendingViewportResize.current;
    if (variant === null || progress === null) return;
    pendingViewportResize.current = null;
    window.scrollTo({
      top:
        baseScrollHeight() *
        journeyScrollDistance(progress, entryPhase.current ?? 0),
      behavior: 'instant',
    });
  }, [view.width, view.height, variant]);
  useEffect(() => {
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)'),
      mobile = window.matchMedia('(max-width:700px)');
    const motionChange = () => setReduced(motion.matches);
    const profileChange = () => {
      setFailed(false);
      setPortalEndReady(false);
      setPortalBypass(
        window.scrollY >= (spacer.current?.offsetHeight ?? Infinity),
      );
      setVariant(mobile.matches ? 'mobile' : 'desktop');
      setReady(false);
      setPortalReady(false);
      setIdleReady({});
    };
    motionChange();
    profileChange();
    motion.addEventListener('change', motionChange);
    mobile.addEventListener('change', profileChange);
    let frame = 0;
    let previousHeight = window.innerHeight;
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
      const progress =
        window.scrollY >= (spacer.current?.offsetHeight ?? Infinity) - 0.5
          ? 1
          : journeyProgressFromScroll(distance, entryPhase.current ?? 0);
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
      setPastHero(
        window.scrollY >
          (spacer.current?.offsetHeight ?? 0) +
            (heroViewport.current?.firstElementChild?.clientHeight ??
              window.innerHeight) -
            100,
      );
      scrubber.current?.seek(next.time);
      portalScrubber.current?.seek(Math.max(0, next.time - 81));
    };
    const scroll = () => {
      if (!frame) frame = requestAnimationFrame(sync);
    };
    const resize = () => {
      if (
        previousHeight !== window.innerHeight &&
        lastProgress.current > 0 &&
        lastProgress.current < 1
      )
        pendingViewportResize.current = lastProgress.current;
      previousHeight = window.innerHeight;
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
      portalDriver = createVideoScrubber(p, portalFps, variant !== null);
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
    return () => {
      driver.dispose();
      streetDriver?.dispose();
      cityDriver.current = null;
      portalDriver.dispose();
      scrubber.current = null;
      portalScrubber.current = null;
    };
  }, [routeFps, portalFps, variant]);
  useEffect(() => {
    if (!reduced && !entered) {
      setRequestedMedia((previous) =>
        requestNearbyMedia(
          previous,
          liveEnabled && !entered
            ? Math.min(0.999, scene.progress)
            : scene.progress,
        ),
      );
    }
  }, [scene.progress, entered, reduced, liveEnabled]);
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
  const journeyUiOpacity = Math.max(0, Math.min(1, (86 - scene.time) / 2));

  useEffect(() => {
    if (!scene.complete) {
      setPortalBypass(false);
      return;
    }
    if (!liveEnabled || entered) return;
    const timer = window.setTimeout(() => setPortalBypass(true), 1500);
    return () => window.clearTimeout(timer);
  }, [liveEnabled, scene.complete, entered]);
  const poster =
    chapter === 0
      ? 'city'
      : chapter === 1
        ? 'tools'
        : chapter === 2
          ? 'magazines'
          : 'monitor';

  return {
    city,
    film,
    portalFilm,
    main,
    spacer,
    heroViewport,
    heroSlot,
    tools,
    magazines,
    monitor,
    portalBypass,
    setPortalEndReady,
    pastHero,
    scene,
    turnReady,
    setTurnReady,
    ready,
    setReady,
    portalReady,
    setPortalReady,
    failed,
    setFailed,
    paused,
    setPaused,
    reduced,
    menu,
    setMenu,
    visible,
    variant,
    view,
    idleReady,
    setIdleReady,
    requestedMedia,
    profile,
    liveEnabled,
    liveMedia,
    chapter,
    entered,
    portal,
    moving,
    asset,
    streetAsset,
    junction,
    scrollScale,
    go,
    skip,
    replay,
    togglePause,
    card,
    journeyUiOpacity,
    poster,
  };
}
export type JourneyState = ReturnType<typeof useJourney>;
