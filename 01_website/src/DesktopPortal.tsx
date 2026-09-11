import { useEffect, useLayoutEffect, useRef, type RefObject } from 'react';
import {
  desktopProjection,
  IDENTITY_TRANSFORM,
  screenPower,
} from './desktop-projection';
import tracking from './desktop-screen-tracking.json';

type Props = {
  enabled: boolean;
  time: number;
  hold: boolean;
  complete: boolean;
  entered: boolean;
  bypass: boolean;
  route: RefObject<HTMLVideoElement | null>;
  portal: RefObject<HTMLVideoElement | null>;
  monitor: RefObject<HTMLVideoElement | null>;
  viewport: RefObject<HTMLDivElement | null>;
  slot: RefObject<HTMLDivElement | null>;
  onEndpoint: (ready: boolean) => void;
};
type Snapshot = { image: HTMLCanvasElement; frame: number };
export function DesktopPortal(props: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const latest = useRef(props);
  latest.current = props;
  const repaint = useRef<() => void>(() => {});
  useEffect(() => {
    if (!props.enabled) return;
    const output = canvas.current,
      viewport = props.viewport.current,
      slot = props.slot.current;
    const hero = viewport?.querySelector<HTMLElement>('.main-hero');
    if (!output || !viewport || !slot || !hero) return;
    const ctx = output.getContext('2d', { alpha: false });
    if (!ctx) {
      latest.current.onEndpoint(true);
      return;
    }
    const snapshots = new Map<HTMLVideoElement, Snapshot>();
    let disposed = false,
      endpoint = false,
      serial = 0,
      backgroundKey = '';
    const signal = (value: boolean) => {
      if (endpoint !== value) {
        endpoint = value;
        latest.current.onEndpoint(value);
      }
    };
    const resetProjection = () => {
      viewport.classList.remove('is-projecting');
      viewport.style.removeProperty('clip-path');
      hero.style.transform = IDENTITY_TRANSFORM;
      hero.style.opacity = '1';
      output.style.display = 'none';
    };
    const paint = () => {
      if (disposed) return;
      const p = latest.current;
      const width = viewport.getBoundingClientRect().width,
        height =
          parseFloat(getComputedStyle(output).height) || window.innerHeight;
      hero.style.width = width + 'px';
      hero.style.minHeight = height + 'px';
      const heroHeight = parseFloat(getComputedStyle(hero).height);
      slot.style.height = heroHeight + 'px';
      const bounds = desktopProjection(tracking, 2700, { width, height })!.quad;
      const left = Math.floor(Math.min(0, ...bounds.map((p) => p[0]))) - 2;
      const top = Math.floor(Math.min(0, ...bounds.map((p) => p[1]))) - 2;
      hero.style.setProperty('--desktop-bg-left', left + 'px');
      hero.style.setProperty('--desktop-bg-top', top + 'px');
      hero.style.setProperty(
        '--desktop-bg-width',
        Math.ceil(Math.max(width, ...bounds.map((p) => p[0])) - left) +
          2 +
          'px',
      );
      hero.style.setProperty(
        '--desktop-bg-height',
        Math.ceil(Math.max(heroHeight, ...bounds.map((p) => p[1])) - top) +
          2 +
          'px',
      );
      hero.style.setProperty(
        '--desktop-gradient-x',
        width * 0.95 - left + 'px',
      );
      hero.style.setProperty(
        '--desktop-gradient-y',
        heroHeight * 0.9 - top + 'px',
      );
      hero.style.setProperty(
        '--desktop-radius-x',
        width * 0.95 * Math.SQRT2 + 'px',
      );
      hero.style.setProperty(
        '--desktop-radius-y',
        heroHeight * 0.9 * Math.SQRT2 + 'px',
      );
      const background = hero.querySelector<HTMLCanvasElement>(
        '.desktop-hero-background',
      );
      const dprForBackground = window.devicePixelRatio || 1;
      const bgWidth =
        Math.ceil(Math.max(width, ...bounds.map((p) => p[0])) - left) + 2;
      const bgHeight =
        Math.ceil(Math.max(heroHeight, ...bounds.map((p) => p[1])) - top) + 2;
      const key = [width, heroHeight, bgWidth, bgHeight, dprForBackground].join(
        '/',
      );
      if (background && backgroundKey !== key) {
        background.width = Math.ceil(bgWidth * dprForBackground);
        background.height = Math.ceil(bgHeight * dprForBackground);
        const bg = background.getContext('2d', { alpha: false });
        if (bg) {
          bg.setTransform(dprForBackground, 0, 0, dprForBackground, 0, 0);
          bg.fillStyle = '#141a1b';
          bg.fillRect(0, 0, bgWidth, bgHeight);
          const cx = width * 0.95 - left,
            cy = heroHeight * 0.9 - top,
            rx = width * 0.95 * Math.SQRT2,
            ry = heroHeight * 0.9 * Math.SQRT2;
          bg.translate(cx, cy);
          bg.scale(rx, ry);
          const gradient = bg.createRadialGradient(0, 0, 0, 0, 0, 1);
          gradient.addColorStop(0, '#1e2d32');
          gradient.addColorStop(0.55, '#1e2d3200');
          gradient.addColorStop(1, '#1e2d3200');
          bg.fillStyle = gradient;
          bg.fillRect(-cx / rx, -cy / ry, bgWidth / rx, bgHeight / ry);
          backgroundKey = key;
        }
      }
      if (p.entered || p.bypass || p.time < 78) {
        resetProjection();
        if (!p.complete) signal(false);
        return;
      }
      const candidates = p.hold
        ? [p.monitor.current, p.portal.current, p.route.current]
        : p.time >= 81
          ? [p.portal.current]
          : [p.route.current];
      const shot = candidates
        .map((v) => (v ? snapshots.get(v) : undefined))
        .find(Boolean);
      if (!shot || shot.frame < 2340) {
        resetProjection();
        return;
      }
      const geometry = desktopProjection(tracking, shot.frame, {
        width,
        height,
      });
      if (!geometry) {
        resetProjection();
        return;
      }
      const dpr = window.devicePixelRatio || 1;
      const w = Math.round(width * dpr),
        h = Math.round(height * dpr);
      if (output.width !== w || output.height !== h) {
        output.width = w;
        output.height = h;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const scale = Math.max(
        width / shot.image.width,
        height / shot.image.height,
      );
      ctx.drawImage(
        shot.image,
        (width - shot.image.width * scale) / 2,
        (height - shot.image.height * scale) / 2,
        shot.image.width * scale,
        shot.image.height * scale,
      );
      viewport.classList.add('is-projecting');
      viewport.style.clipPath =
        'polygon(' +
        geometry.quad.map(([x, y]) => x + 'px ' + y + 'px').join(',') +
        ')';
      hero.style.transform = geometry.transform;
      hero.style.opacity = String(screenPower(shot.frame));
      output.style.display = 'block';
      const id = String(++serial);
      output.dataset.frame = viewport.dataset.frame = String(shot.frame);
      output.dataset.paint = viewport.dataset.paint = id;
      signal(p.complete && shot.frame >= 2700);
    };
    repaint.current = paint;
    const cleanups: (() => void)[] = [];
    for (const [ref, start, fixed] of [
      [props.route, 0, false],
      [props.portal, 2430, false],
      [props.monitor, 2430, true],
    ] as const) {
      const video = ref.current;
      if (!video) continue;
      let callback = 0;
      const capture = (mediaTime: number) => {
        if (disposed || video.readyState < 2 || !video.videoWidth) return;
        let frame = fixed ? 2430 : start + Math.round(mediaTime * 30);
        if (start === 0 && frame === 2429) frame = 2430; // source-frame contract for route's last image
        if (frame < 2340) return;
        let shot = snapshots.get(video);
        if (!shot) {
          shot = { image: document.createElement('canvas'), frame };
          snapshots.set(video, shot);
        }
        if (
          shot.image.width !== video.videoWidth ||
          shot.image.height !== video.videoHeight
        ) {
          shot.image.width = video.videoWidth;
          shot.image.height = video.videoHeight;
        }
        const buffer = shot.image.getContext('2d', { alpha: false });
        if (!buffer) return;
        // Capture an immutable image and its frame number together, then paint both
        // camera and DOM geometry synchronously. React never schedules these pixels.
        buffer.drawImage(video, 0, 0);
        shot.frame = frame;
        paint();
      };
      if (typeof video.requestVideoFrameCallback === 'function') {
        const receive: VideoFrameRequestCallback = (_, meta) => {
          capture(meta.mediaTime);
          callback = video.requestVideoFrameCallback(receive);
        };
        callback = video.requestVideoFrameCallback(receive);
        if (!video.seeking) capture(video.currentTime);
      }
      // A seek completed while the journey was hidden may not emit rVFC.
      // Read the decoded image on seeked too, preserving image/geometry pairing.
      const decoded = () => {
        if (!video.seeking)
          capture(Math.floor(video.currentTime * 30 + 1e-4) / 30);
      };
      video.addEventListener('loadeddata', decoded);
      video.addEventListener('seeked', decoded);
      decoded();
      cleanups.push(() => {
        video.removeEventListener('loadeddata', decoded);
        video.removeEventListener('seeked', decoded);
      });
      cleanups.push(() => {
        if (callback) video.cancelVideoFrameCallback(callback);
      });
    }
    window.addEventListener('resize', paint);
    const observer = new ResizeObserver(paint);
    observer.observe(hero);
    paint();
    return () => {
      disposed = true;
      cleanups.forEach((fn) => fn());
      observer.disconnect();
      window.removeEventListener('resize', paint);
      repaint.current = () => {};
      resetProjection();
      slot.style.removeProperty('height');
      for (const key of [
        'width',
        'min-height',
        'transform',
        'opacity',
        '--desktop-gradient-x',
        '--desktop-gradient-y',
        '--desktop-radius-x',
        '--desktop-radius-y',
        '--desktop-bg-left',
        '--desktop-bg-top',
        '--desktop-bg-width',
        '--desktop-bg-height',
      ])
        hero.style.removeProperty(key);
    };
  }, [
    props.enabled,
    props.route,
    props.portal,
    props.monitor,
    props.viewport,
    props.slot,
  ]);
  useLayoutEffect(() => {
    repaint.current();
  }, [
    props.time,
    props.hold,
    props.complete,
    props.entered,
    props.bypass,
    props.enabled,
  ]);
  return (
    <canvas ref={canvas} className="desktop-camera-canvas" aria-hidden="true" />
  );
}
