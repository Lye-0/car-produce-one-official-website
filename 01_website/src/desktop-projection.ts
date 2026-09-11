import {
  coverQuad,
  quadMatrix,
  sampleQuad,
  type Quad,
  type Viewport,
  type TrackingFrame,
} from './screen-projection.ts';
export const DESKTOP_SCREEN_START = 2340;
export const DESKTOP_SCREEN_END = 2700;
export const IDENTITY_TRANSFORM = 'matrix3d(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)';
type Matrix = number[];
function homography(q: Quad): Matrix {
  const m = quadMatrix({ width: 1, height: 1 }, q);
  if (!m) throw new Error('Degenerate screen plane');
  return [m[0], m[4], m[12], m[1], m[5], m[13], m[3], m[7], m[15]];
}
function inverse(m: Matrix): Matrix {
  const [a, b, c, d, e, f, g, h, i] = m;
  const cof = [
    e * i - f * h,
    c * h - b * i,
    b * f - c * e,
    f * g - d * i,
    a * i - c * g,
    c * d - a * f,
    d * h - e * g,
    b * g - a * h,
    a * e - b * d,
  ];
  const det = a * cof[0] + b * cof[3] + c * cof[6];
  if (Math.abs(det) < 1e-12) throw new Error('Non-invertible screen plane');
  return cof.map((v) => v / det);
}
function multiply(a: Matrix, b: Matrix): Matrix {
  return Array.from({ length: 9 }, (_, index) => {
    const row = Math.floor(index / 3),
      col = index % 3;
    return (
      a[row * 3] * b[col] +
      a[row * 3 + 1] * b[3 + col] +
      a[row * 3 + 2] * b[6 + col]
    );
  });
}
export function projectPoint(m: Matrix, x: number, y: number) {
  const w = m[6] * x + m[7] * y + m[8];
  return [(m[0] * x + m[1] * y + m[2]) / w, (m[3] * x + m[4] * y + m[5]) / w];
}
export function desktopProjection(
  rows: TrackingFrame[],
  frame: number,
  view: Viewport,
  source: Viewport = { width: 1920, height: 1080 },
) {
  const normalized = sampleQuad(rows, frame),
    terminal = sampleQuad(rows, DESKTOP_SCREEN_END);
  if (!normalized || !terminal) return null;
  const quad = coverQuad(normalized, source, view),
    end = coverQuad(terminal, source, view);
  // A single page layout is attached to the monitor plane by the inverse endpoint.
  // The endpoint is the identity for every viewport, without a second layout or blend.
  const matrix =
    frame >= DESKTOP_SCREEN_END
      ? [1, 0, 0, 0, 1, 0, 0, 0, 1]
      : multiply(homography(quad), inverse(homography(end)));
  const [a, b, c, d, e, f, g, h, i] = matrix;
  return {
    quad,
    matrix,
    transform:
      frame >= DESKTOP_SCREEN_END
        ? IDENTITY_TRANSFORM
        : 'matrix3d(' +
          [a, d, 0, g, b, e, 0, h, 0, 0, 1, 0, c, f, 0, i].join(',') +
          ')',
  };
}
export function screenPower(frame: number) {
  const t = Math.min(1, Math.max(0, (frame - 2370) / 54));
  return t * t * (3 - 2 * t);
}
