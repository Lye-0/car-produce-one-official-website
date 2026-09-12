import {
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
  type RefObject,
} from 'react';
import { VideoDownloads } from './downloads';
import type { MediaAsset } from './playback';
import {
  nextDownloadGate,
  routeDownloadGates,
  type DownloadGate,
  type MediaSpan,
  constrainMediaProgress,
  beforeRouteFrame,
} from './download-gates';
import { getProductionClip } from './production';
import { desktopPortalMedia, mobilePortalMedia } from './portal';
import { JUNCTION_END } from '../journey/junction';

export function useStartupLoading(options: {
  profile: 'desktop' | 'mobile' | null;
  reduced: boolean;
  city: RefObject<HTMLVideoElement | null>;
  decoded: boolean;
  failed: boolean;
}) {
  const [attempt, setAttempt] = useState(0);
  const [entranceCycle, setEntranceCycle] = useState(0);
  const downloads = useMemo(
    () => new VideoDownloads(),
    [options.profile, attempt],
  );
  useSyncExternalStore(downloads.subscribe, downloads.snapshot);
  const [cityReady, setCityReady] = useState(false);
  const [cityFraction, setCityFraction] = useState(0);
  const [cityError, setCityError] = useState(false);
  const [sources, setSources] = useState<string[]>([]);
  const [prepared, setPrepared] = useState(false);
  const [unlocked, setUnlocked] = useState(false);
  const [bypass, setBypass] = useState(() =>
    ['#services', '#about', '#access', '#contact'].includes(
      window.location.hash,
    ),
  );
  const disabled = options.reduced || bypass;
  useEffect(() => () => downloads.dispose(), [downloads]);
  useEffect(() => {
    // Restored document positions and a profile change in the main site must
    // not force the user through the entrance gate again.
    if (window.scrollY > 0) setBypass(true);
    setCityReady(false);
    setCityFraction(0);
    setCityError(false);
    setPrepared(false);
    setUnlocked(false);
    setSources([]);
    const video = options.city.current;
    if (!video || disabled) return;
    let rewound = false,
      complete = false;
    let latestEnd = 0,
      changedAt = Date.now();
    const update = () => {
      if (complete) return;
      let end = 0;
      for (let i = 0; i < video.buffered.length; i++) {
        if (video.buffered.start(i) > end + 0.05) break;
        end = Math.max(end, video.buffered.end(i));
      }
      const duration = Number.isFinite(video.duration) ? video.duration : 20;
      if (
        end > latestEnd ||
        video.paused ||
        document.visibilityState === 'hidden'
      )
        changedAt = Date.now();
      latestEnd = Math.max(latestEnd, end);
      if (Date.now() - changedAt > 30000) setCityError(true);
      setCityFraction(Math.min(1, end / (duration * 0.75)));
      if (end + 0.01 < duration * 0.75 || video.readyState < 2) return;
      if (!rewound) {
        rewound = true;
        // Prime native preload behind the black screen, then reveal the loop
        // from its beginning with 75% already buffered.
        video.currentTime = 0;
        return;
      }
      if (!video.seeking && video.readyState >= 2) {
        complete = true;
        clearInterval(timer);
        setCityReady(true);
      }
    };
    const events = ['progress', 'loadeddata', 'canplay', 'seeked'];
    events.forEach((event) => video.addEventListener(event, update));
    const timer = setInterval(update, 200);
    update();
    return () => {
      clearInterval(timer);
      events.forEach((event) => video.removeEventListener(event, update));
    };
  }, [downloads, disabled, options.city, entranceCycle]);
  useEffect(() => {
    if (!cityReady || !options.profile || disabled) return;
    let cancelled = false;
    const profile = options.profile;
    async function prepare() {
      const jobs = ['junction', 'route', 'tools-idle'];
      const variants = await Promise.all(
        jobs.map((job) => downloads.choose(getProductionClip(profile, job)!)),
      );
      if (cancelled) return;
      const first = variants.map(
        (v) => v.segments?.[0] ?? (v as { src: string; bytes?: number }),
      );
      setSources(first.map((v) => v.src));
      await Promise.all(first.map((v) => downloads.ensure(v.src, v.bytes, 1)));
      if (!cancelled) setPrepared(true);
    }
    void prepare().catch(() => {
      /* Download state owns retry feedback. */
    });
    return () => {
      cancelled = true;
    };
  }, [cityReady, options.profile, downloads, disabled]);
  useEffect(() => {
    if (prepared && cityReady && options.decoded) setUnlocked(true);
  }, [prepared, cityReady, options.decoded]);
  const portal =
    options.profile === 'mobile' ? mobilePortalMedia : desktopPortalMedia;
  const route = options.profile
    ? getProductionClip(options.profile, 'route')
    : undefined;
  const magazine = options.profile
    ? getProductionClip(options.profile, 'magazines-idle')
    : undefined;
  const junction = options.profile
    ? getProductionClip(options.profile, 'junction')
    : undefined;
  const tools = options.profile
    ? getProductionClip(options.profile, 'tools-idle')
    : undefined;
  const assets: MediaAsset[] =
    route && magazine && junction && tools
      ? [
          route,
          magazine,
          junction,
          tools,
          portal('monitor-idle'),
          portal('portal'),
        ]
      : [];
  useEffect(() => {
    // Probe codec support during the street stage; this does not download media.
    if (options.profile && !options.reduced)
      void Promise.all(assets.map((asset) => downloads.choose(asset))).catch(
        () => {},
      );
  }, [options.reduced, downloads, options.profile]);
  const routeVariant = route && downloads.variant(route);
  const gates: DownloadGate[] = routeVariant
    ? routeDownloadGates(routeVariant, route!.fps)
    : [];
  const entryVariants = [route, junction, tools].map(
    (asset) => asset && downloads.variant(asset),
  );
  if (entryVariants.every(Boolean))
    gates.push({
      before: 0,
      files: entryVariants.map(
        (variant) =>
          variant!.segments?.[0] ??
          (variant as { src: string; bytes?: number }),
      ),
    });
  for (const [asset, before] of [
    [magazine, 0.65],
    [portal('monitor-idle'), 0.88],
    [portal('portal'), 0.9],
  ] as const) {
    const variant = asset && downloads.variant(asset);
    if (variant)
      gates.push({
        before: before - 1e-7,
        files: variant.segments ?? [variant as { src: string; bytes?: number }],
      });
  }
  gates.sort((a, b) => a.before - b.before);
  const catalogueReady =
    assets.length > 0 && assets.every((asset) => downloads.variant(asset));
  const gateKey = gates
    .flatMap((gate) => gate.files.map((file) => file.src))
    .join('|');
  useEffect(() => {
    if (!unlocked || disabled || !catalogueReady) return;
    let cancelled = false;
    async function warm() {
      for (const gate of gates)
        for (const file of gate.files) {
          if (cancelled) return;
          await downloads.prefetch(file.src, file.bytes);
        }
    }
    void warm().catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [unlocked, disabled, downloads, gateKey, catalogueReady]);
  const nextGate = nextDownloadGate(gates, (src) => downloads.isReady(src));
  const spans: MediaSpan[] = [];
  const parts = routeVariant?.segments;
  if (parts)
    parts.forEach((part, i) =>
      spans.push({
        start: i ? beforeRouteFrame(part.startFrame, 30) : 0,
        end:
          i + 1 < parts.length
            ? beforeRouteFrame(parts[i + 1].startFrame, 30)
            : 0.9 - 1e-7,
        files: [part],
      }),
    );
  for (const [asset, start, end] of [
    [junction, 0, JUNCTION_END],
    [tools, 0.35, 0.46],
    [magazine, 0.65, 0.76],
    [portal('monitor-idle'), 0.88, 0.9],
    [portal('portal'), 0.9, 1],
  ] as const) {
    const v = asset && downloads.variant(asset);
    if (v)
      spans.push({
        start: Math.max(0, start - 1e-7),
        end: end === 1 ? 1 : end - 1e-7,
        files: v.segments ?? [v as { src: string; bytes?: number }],
      });
  }
  const portalVariant = downloads.variant(portal('portal'));
  const blocked = !disabled && !unlocked;
  const stage = !cityReady ? 'city' : 'interior';
  const progress = Math.min(
    0.99,
    stage === 'city' ? cityFraction : downloads.progress(sources),
  );
  return {
    sourceVersion: entranceCycle,
    preparationSources: sources,
    downloads,
    navigationPlan: (requested: number, current: number) =>
      options.reduced
        ? { progress: requested, files: [] }
        : catalogueReady
          ? constrainMediaProgress(requested, current, spans, (src) =>
              downloads.isReady(src),
            )
          : { progress: current, files: [] },
    streetFiles: options.profile
      ? (() => {
          const asset = getProductionClip(options.profile!, 'drive')!;
          const v = downloads.variant(asset);
          return v
            ? (v.segments ?? [v as { src: string; bytes?: number }])
            : [];
        })()
      : [],
    returnFiles: portalVariant
      ? (portalVariant.segments ?? [
          portalVariant as { src: string; bytes?: number },
        ])
      : [],
    blocked,
    cityReady: disabled || cityReady,
    cityPriming: !disabled && !cityReady,
    maxProgress: options.reduced
      ? 1
      : catalogueReady
        ? (nextGate?.before ?? 1)
        : 0,
    boundaryProgress: nextGate
      ? Math.floor(
          downloads.progress(nextGate.files.map((file) => file.src)) * 100,
        )
      : 100,
    boundaryKey: nextGate?.files.map((file) => file.src).join('|') ?? '',
    requestBoundary: () => {
      if (nextGate)
        void Promise.all(
          nextGate.files.map((file) =>
            downloads.ensure(file.src, file.bytes, 0),
          ),
        ).catch(() => {});
    },
    stage,
    progress: Math.floor(progress * 1000) / 10,
    prefetch: cityReady && !disabled,
    error: Boolean(downloads.error() || cityError || options.failed),
    retry: () => setAttempt((value) => value + 1),
    bypass: () => setBypass(true),
    replay: () => {
      setBypass(false);
      setEntranceCycle((value) => value + 1);
    },
  };
}
