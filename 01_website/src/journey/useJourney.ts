import {
  BASE_SCROLL_VIEWPORTS,
  journeyScrollDistance,
  journeyProgressFromScroll,
} from './scroll';
import { INITIAL_MEDIA_REQUESTS, requestNearbyMedia } from '../media/loading';
import { assetUrl } from '../media/urls';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { content as c } from '../content';
import {
  DRIVE_FPS,
  JUNCTION_END,
  JUNCTION_MEDIA_VERSION,
  sampleJunction,
} from './junction';
import {
  CHAPTER_PROGRESS,
  sampleJourney,
  createVideoScrubber,
} from './timeline';
import { desktopPortalMedia, mobilePortalMedia } from '../media/portal';
import { useStartupLoading } from '../media/useStartupLoading';
import type { GateFile } from '../media/download-gates';
export function useJourney() {
  const city = useRef<HTMLVideoElement>(null),
    film = useRef<HTMLVideoElement>(null),
    filmSecond = useRef<HTMLVideoElement>(null),
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
  const startup = useStartupLoading({
    profile: variant,
    reduced,
    city,
    decoded: turnReady && ready && Boolean(idleReady.tools),
    failed,
  });
  const [videoWaiting, setVideoWaiting] = useState(false);
  const [boundaryWaiting, setBoundaryWaiting] = useState(false);
  const [bufferCity, setBufferCity] = useState(false);
  const gateBypass = useRef(false);
  const boundaryIntent = useRef(false);
  const pendingNavigation = useRef<number | null>(null);
  const [waitingFiles, setWaitingFiles] = useState<GateFile[]>([]);
  const waitingFileKey = waitingFiles.map((file) => file.src).join('|');
  useEffect(() => {
    startup.downloads.focus(
      boundaryWaiting ? waitingFiles.map((file) => file.src) : [],
    );
  }, [boundaryWaiting, waitingFileKey, startup.downloads]);
  useEffect(() => {
    if (waitingFiles.some((file) => file.src.includes('/drive/')))
      setBufferCity(true);
    const paths = {
      junction: '/junction/',
      route: '/route/',
      tools: '/tools-idle/',
      magazines: '/magazines-idle/',
      monitor: '/monitor-idle/',
      portal: '/portal/',
    };
    setRequestedMedia((previous) => {
      let next = previous;
      for (const key of Object.keys(paths) as (keyof typeof paths)[])
        if (
          !next[key] &&
          waitingFiles.some((file) => file.src.includes(paths[key]))
        )
          next = { ...next, [key]: true };
      return next;
    });
  }, [waitingFiles]);
  const downloadsRef = useRef(startup.downloads);
  downloadsRef.current = startup.downloads;
  const gateState = useRef({ plan: planNavigation, disabled: reduced });
  gateState.current = { plan: planNavigation, disabled: reduced };
  function planNavigation(requested: number, current: number) {
    if (reduced) return { progress: requested, files: [] };
    if (current >= 1 && requested < 1) {
      const video = portalFilm.current;
      if (
        !video ||
        video.readyState < 2 ||
        video.seeking ||
        video.currentTime < video.duration - 0.1
      )
        return { progress: 1, files: startup.returnFiles };
    }
    const plan = startup.navigationPlan(requested, current);
    if (
      current >= JUNCTION_END &&
      requested < JUNCTION_END &&
      plan.progress < JUNCTION_END + 1e-5
    ) {
      const video = city.current;
      if (
        !video ||
        !Array.from({ length: video.buffered.length }, (_, i) => [
          video.buffered.start(i),
          video.buffered.end(i),
        ]).some(([start, end]) => start <= 0.05 && end >= video.duration * 0.75)
      )
        return { progress: JUNCTION_END + 1e-5, files: startup.streetFiles };
    }
    return plan;
  }
  function waitForNavigation(requested: number, files: GateFile[]) {
    pendingNavigation.current = requested;
    boundaryIntent.current = true;
    setBoundaryWaiting(true);
    setWaitingFiles(files);
    void Promise.all(
      files.map((file) => downloadsRef.current.ensure(file.src, file.bytes, 0)),
    ).catch(() => {});
  }
  useEffect(() => {
    if (!boundaryWaiting) return;
    const timer = setInterval(() => {
      const requested = pendingNavigation.current;
      if (requested === null) return;
      const plan = gateState.current.plan(requested, lastProgress.current);
      if (
        Math.abs(plan.progress - lastProgress.current) >
          Math.max(1e-5, 2 / baseScrollHeight()) ||
        plan.progress === requested
      ) {
        pendingNavigation.current = null;
        boundaryIntent.current = false;
        setBoundaryWaiting(false);
      } else {
        setWaitingFiles(plan.files);
        void Promise.all(
          plan.files.map((file) =>
            startup.downloads.ensure(file.src, file.bytes, 0),
          ),
        ).catch(() => {});
      }
    }, 150);
    return () => clearInterval(timer);
  }, [boundaryWaiting, startup.downloads]);
  const waitingScene = useRef({ scene, turnReady });
  waitingScene.current = { scene, turnReady };
  useEffect(() => {
    if (!startup.blocked) return;
    const root = document.documentElement;
    const oldOverflow = root.style.overflow;
    root.style.overflow = 'hidden';
    root.dataset.videoLoading = 'true';
    const stop = (event: Event) => {
      if (
        !(
          event.target instanceof Element && event.target.closest('.menu-panel')
        )
      )
        event.preventDefault();
    };
    const key = (event: KeyboardEvent) => {
      if (
        event.target instanceof Element &&
        event.target.closest('.menu-panel')
      )
        return;
      if (
        [
          'ArrowDown',
          'ArrowUp',
          'PageDown',
          'PageUp',
          'Home',
          'End',
          ' ',
        ].includes(event.key) &&
        !(event.target instanceof HTMLButtonElement)
      )
        event.preventDefault();
    };
    const position = window.scrollY;
    const reset = () => {
      if (!gateBypass.current && window.scrollY !== position)
        window.scrollTo({ top: position, behavior: 'instant' });
    };
    window.addEventListener('wheel', stop, { passive: false });
    window.addEventListener('touchmove', stop, { passive: false });
    window.addEventListener('keydown', key);
    window.addEventListener('scroll', reset);
    return () => {
      root.style.overflow = oldOverflow;
      delete root.dataset.videoLoading;
      window.removeEventListener('wheel', stop);
      window.removeEventListener('touchmove', stop);
      window.removeEventListener('keydown', key);
      window.removeEventListener('scroll', reset);
    };
  }, [startup.blocked]);
  useEffect(() => {
    if (startup.blocked || reduced) {
      setVideoWaiting(false);
      return;
    }
    let since = 0;
    const timer = setInterval(() => {
      const current = waitingScene.current;
      const holdVideo =
        current.scene.hold === 'tools'
          ? tools.current
          : current.scene.hold === 'magazines'
            ? magazines.current
            : current.scene.hold === 'monitor'
              ? monitor.current
              : null;
      const waiting =
        current.scene.progress > 0 && current.scene.progress < JUNCTION_END
          ? !current.turnReady
          : current.scene.time >= 81
            ? Boolean(
                portalFilm.current &&
                (portalFilm.current.readyState < 2 ||
                  portalFilm.current.seeking),
              )
            : Boolean(
                current.scene.progress >= JUNCTION_END &&
                document.querySelector('video[data-media-waiting="true"]'),
              ) || Boolean(holdVideo && holdVideo.readyState < 2);
      if (!waiting) since = 0;
      else if (!since) since = Date.now();
      setVideoWaiting(waiting && Date.now() - since > 250);
    }, 150);
    return () => clearInterval(timer);
  }, [startup.blocked, reduced]);
  const liveMedia =
    profile === 'mobile' ? mobilePortalMedia : desktopPortalMedia;
  const portalFps = liveMedia('portal').fps;
  const portalScrubber = useRef<ReturnType<typeof createVideoScrubber> | null>(
    null,
  );
  const chapter = scene.chapter,
    entered =
      scene.complete &&
      (!liveEnabled || portalEndReady || portalBypass || failed),
    portal = scene.portal > 0,
    moving = !scene.hold && scene.progress > 0;
  const nextButtonPlan = planNavigation(
    CHAPTER_PROGRESS[Math.min(4, chapter + 1)],
    scene.progress,
  );
  const nextButtonKey = nextButtonPlan.files.map((file) => file.src).join('|');
  useEffect(() => {
    if (startup.blocked || entered || reduced || !scene.hold) return;
    void Promise.all(
      nextButtonPlan.files.map((file) =>
        startup.downloads.ensure(file.src, file.bytes, 2),
      ),
    ).catch(() => {});
  }, [
    startup.blocked,
    entered,
    reduced,
    scene.hold,
    nextButtonKey,
    startup.downloads,
  ]);
  const asset = (name: string) =>
    variant ? assetUrl(`/media/images/fallback/${variant}/${name}`) : undefined;
  const streetAsset = (name: string) =>
    variant
      ? assetUrl(
          `/media/images/fallback/${variant}/${name}?v=${JUNCTION_MEDIA_VERSION}`,
        )
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
    if (next === 0) {
      restartJourney();
      return;
    }
    if (startup.blocked) return;
    if (next < 4) {
      gateBypass.current = false;
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
    const requested = CHAPTER_PROGRESS[Math.max(0, Math.min(4, next))];
    const plan =
      reduced || gateBypass.current
        ? { progress: requested, files: [] }
        : planNavigation(requested, scene.progress);
    const target = plan.progress;
    if (target !== requested) waitForNavigation(requested, plan.files);
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
  function canGo(next: number) {
    if (next === 0) return true;
    const target = CHAPTER_PROGRESS[Math.max(0, Math.min(4, next))];
    return (
      reduced ||
      (startup.cityReady &&
        !startup.blocked &&
        Math.abs(planNavigation(target, scene.progress).progress - target) <
          1e-8)
    );
  }
  function preparationFor() {
    return startup.blocked ? startup.progress : startup.boundaryProgress;
  }
  function skip(id?: string) {
    gateBypass.current = true;
    startup.bypass();
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
    restartJourney();
  }
  function restartJourney() {
    // A deliberate restart is not a request to traverse the unread reverse path.
    pendingNavigation.current = null;
    boundaryIntent.current = false;
    setBoundaryWaiting(false);
    setWaitingFiles([]);
    setVideoWaiting(false);
    gateBypass.current = false;
    entryPhase.current = null;
    lastProgress.current = 0;
    pendingViewportResize.current = null;
    cityDriver.current?.release();
    setPortalBypass(false);
    setPortalEndReady(false);
    setPastHero(false);
    setMenu(false);
    setFailed(false);
    setPaused(false);
    setRequestedMedia(INITIAL_MEDIA_REQUESTS);
    startup.downloads.cancelPending();
    if (window.location.hash)
      window.history.replaceState(
        null,
        '',
        window.location.pathname + window.location.search,
      );
    window.scrollTo({ top: 0, behavior: 'instant' });
    if (city.current && city.current.readyState >= 1)
      city.current.currentTime = 0;
    setScene(sampleJourney(0));
    if (startup.error) startup.retry();
    startup.replay();
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
      setBufferCity(false);
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
      const requestedProgress =
        window.scrollY >= (spacer.current?.offsetHeight ?? Infinity) - 0.5
          ? 1
          : journeyProgressFromScroll(distance, entryPhase.current ?? 0);
      if (
        lastProgress.current >= 1 &&
        requestedProgress < 1 &&
        entryPhase.current === null
      )
        entryPhase.current = 0;
      const gate = gateState.current;
      const leaveBody = requestedProgress >= 1 && lastProgress.current >= 1;
      const plan =
        gate.disabled ||
        leaveBody ||
        (gateBypass.current && requestedProgress >= lastProgress.current)
          ? { progress: requestedProgress, files: [] }
          : gate.plan(requestedProgress, lastProgress.current);
      const progress = plan.progress;
      if (Math.abs(progress - requestedProgress) > 1e-8) {
        waitForNavigation(requestedProgress, plan.files);
        window.scrollTo({
          top:
            height * journeyScrollDistance(progress, entryPhase.current ?? 0),
          behavior: 'instant',
        });
      } else if (
        Math.abs(progress - lastProgress.current) > 2 / height ||
        (leaveBody && window.scrollY > (spacer.current?.offsetHeight ?? 0) + 2)
      ) {
        pendingNavigation.current = null;
        boundaryIntent.current = false;
        setBoundaryWaiting(false);
      }
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
    const p = portalFilm.current;
    if (!p) return;
    const streetDriver = city.current
      ? createVideoScrubber(city.current, DRIVE_FPS)
      : null;
    cityDriver.current = streetDriver;
    const portalDriver = createVideoScrubber(p, portalFps, variant !== null);
    portalScrubber.current = portalDriver;
    const time = sampleJourney(
      journeyProgressFromScroll(
        window.scrollY / baseScrollHeight(),
        entryPhase.current ?? 0,
      ),
      entryPhase.current ?? 0,
    ).time;
    portalDriver.seek(Math.max(0, time - 81));
    return () => {
      streetDriver?.dispose();
      cityDriver.current = null;
      portalDriver.dispose();
      portalScrubber.current = null;
    };
  }, [portalFps, variant]);
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
    if (startup.prefetch)
      setRequestedMedia((previous) => ({
        ...previous,
        junction: true,
        route: true,
        tools: true,
      }));
  }, [startup.prefetch]);
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
      gateBypass.current = false;
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
    bufferCity,
    boundaryProgress: Math.floor(
      startup.downloads.progress(waitingFiles.map((file) => file.src)) * 100,
    ),
    canGo,
    preparationFor,
    boundaryWaiting,
    startup,
    videoWaiting,
    city,
    film,
    filmSecond,
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
