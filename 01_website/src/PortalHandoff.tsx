import { lockPageScroll } from './scroll-lock';
import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type RefObject,
} from 'react';
import {
  portalDirection,
  portalTiming,
  PORTAL_RESET_MARGIN,
  type PortalSide,
} from './portal-timing';

type Input = {
  requested: number;
  presented: number;
  coverAt: number;
  reduced: boolean;
  profile: string;
  onArrive: () => void;
};
export function usePortalHandoff(input: Input) {
  const latest = useRef(input);
  latest.current = input;
  const suppressed = useRef<number | null>(null);
  const sequence = useRef(0);
  const unlock = useRef<() => void>(() => {});
  const [desktopBlend, setDesktopBlend] = useState(0);
  const [side, setSide] = useState<PortalSide>('camera');
  const [active, setActive] = useState<{ id: number; to: PortalSide } | null>(
    null,
  );
  const reset = (next: PortalSide) => {
    unlock.current();
    suppressed.current = latest.current.requested;
    setActive(null);
    setSide(next);
  };
  useEffect(() => {
    reset(input.requested >= 2700 ? 'site' : 'camera');
  }, [input.profile]);
  useEffect(() => {
    if (input.reduced) {
      setActive(null);
      setSide(input.requested >= 2700 ? 'site' : 'camera');
      return;
    }
    if (suppressed.current === input.requested) return;
    suppressed.current = null;
    if (active) return;
    const to = portalDirection(
      side,
      input.requested,
      input.presented,
      input.coverAt,
    );
    if (to) setActive({ id: ++sequence.current, to });
  }, [
    input.requested,
    input.presented,
    input.coverAt,
    input.reduced,
    input.profile,
    side,
    active,
  ]);
  const finish = () => {
    unlock.current();
    if (!active) return;
    setSide(active.to);
    setActive(null);
    // Keep rapid forward scrolling; only advance the remaining approach if still entering.
    if (
      active.to === 'site' &&
      latest.current.requested >= latest.current.coverAt - PORTAL_RESET_MARGIN
    )
      latest.current.onArrive();
  };
  useLayoutEffect(() => {
    if (!active || input.profile !== 'mobile' || input.reduced) return;
    const release = lockPageScroll();
    unlock.current = release;
    return () => {
      release();
      if (unlock.current === release) unlock.current = () => {};
    };
  }, [active, input.profile, input.reduced]);
  useLayoutEffect(() => {
    if (!active || input.profile !== 'desktop' || input.reduced) return;
    const from = side === 'site' ? 1 : 0,
      to = active.to === 'site' ? 1 : 0;
    const start = performance.now();
    let frame = 0;
    setDesktopBlend(from);
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / 320),
        eased = t * t * (3 - 2 * t);
      setDesktopBlend(from + (to - from) * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
      else finish();
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [active, input.profile, input.reduced]);
  return {
    active,
    siteOpacity:
      active && input.profile === 'desktop'
        ? desktopBlend
        : side === 'site'
          ? 1
          : 0,
    reset,
    swap: () => {
      if (active) setSide(active.to);
    },
    finish,
  };
}

export function PortalNoise({
  video,
  direction,
  onSwap,
  onComplete,
}: {
  video: RefObject<HTMLVideoElement | null>;
  direction: PortalSide;
  onSwap: () => void;
  onComplete: () => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const callbacks = useRef({ onSwap, onComplete });
  callbacks.current = { onSwap, onComplete };
  useEffect(() => {
    const node = canvas.current;
    if (!node) return;
    const ctx = node.getContext('2d', { alpha: true });
    if (!ctx) {
      callbacks.current.onSwap();
      callbacks.current.onComplete();
      return;
    }
    const width = (node.width = document.documentElement.clientWidth);
    const height = (node.height = window.innerHeight);
    const snapshot = document.createElement('canvas');
    snapshot.width = width;
    snapshot.height = height;
    const capture = snapshot.getContext('2d');
    const source = video.current;
    if (capture && source && source.readyState >= 2 && source.videoWidth) {
      const scale = Math.max(
        width / source.videoWidth,
        height / source.videoHeight,
      );
      capture.drawImage(
        source,
        (width - source.videoWidth * scale) / 2,
        (height - source.videoHeight * scale) / 2,
        source.videoWidth * scale,
        source.videoHeight * scale,
      );
    }
    const grain = document.createElement('canvas');
    grain.width = Math.ceil(width / 2);
    grain.height = Math.ceil(height / 2);
    const gc = grain.getContext('2d')!;
    const pixels = gc.createImageData(grain.width, grain.height);
    let frame = 0,
      started = performance.now(),
      swapped = false;
    const draw = (now: number) => {
      const elapsed = now - started;
      const timing = portalTiming(elapsed);
      if (timing.swapped && !swapped) {
        swapped = true;
        callbacks.current.onSwap();
      }
      if (timing.complete) {
        callbacks.current.onComplete();
        return;
      }
      ctx.clearRect(0, 0, width, height);
      if (timing.distortion > 0 && direction === 'site') {
        ctx.globalAlpha = Math.sin(Math.PI * (1 - timing.distortion));
        for (let i = 0; i < 12; i++) {
          const y = Math.random() * height,
            h = 2 + Math.random() * 30;
          const shift = (Math.random() - 0.5) * 65 * timing.distortion;
          ctx.drawImage(
            snapshot,
            0,
            y,
            width,
            Math.min(h, height - y),
            shift,
            y,
            width,
            Math.min(h, height - y),
          );
        }
      }
      ctx.globalAlpha = 1;
      ctx.save();
      const strength = 1 - timing.settle;
      ctx.globalAlpha = timing.cover * strength * strength;
      ctx.fillStyle = '#0b181c';
      ctx.fillRect(0, 0, width, height);
      for (let i = 0; i < pixels.data.length; i += 4) {
        const v = 14 + Math.floor(Math.random() * (18 + 44 * strength));
        pixels.data[i] = v * 0.55;
        pixels.data[i + 1] = v * 0.85;
        pixels.data[i + 2] = v;
        pixels.data[i + 3] = Math.random() < strength ? 255 : 0;
      }
      gc.putImageData(pixels, 0, 0);
      ctx.imageSmoothingEnabled = false;
      ctx.globalAlpha = timing.cover * strength;
      ctx.drawImage(grain, 0, 0, width, height);
      ctx.globalAlpha = timing.cover * strength * strength;
      ctx.fillStyle = '#00101488';
      for (let y = Math.floor(elapsed / 12) % 4; y < height; y += 4)
        ctx.fillRect(0, y, width, 1);
      for (let i = 0; i < 8; i++) {
        ctx.fillStyle = i % 2 ? '#7098a633' : '#00101488';
        ctx.fillRect(
          (Math.random() - 0.2) * width,
          Math.random() * height,
          width * Math.random(),
          1 + Math.random() * 8,
        );
      }
      ctx.restore();
      frame = requestAnimationFrame(draw);
    };
    draw(started);
    return () => cancelAnimationFrame(frame);
  }, [video, direction]);
  return (
    <canvas ref={canvas} className="portal-noise-live" aria-hidden="true" />
  );
}
