/** The street reset happens only while a solid building covers every window. */
export const CORNER_END = 0.065;
export const CORNER_FPS = 30;
export const CORNER_LAST_FRAME = 96;
export const CORNER_CUT_FRAME = 48;
export const CORNER_DURATION = CORNER_LAST_FRAME / CORNER_FPS;
export function cornerProgress(progress: number) {
  return Math.min(
    1,
    Math.max(0, Number.isFinite(progress) ? progress / CORNER_END : 0),
  );
}
export function cornerFrame(time: number) {
  return Math.min(
    CORNER_LAST_FRAME,
    Math.max(0, Math.floor(time * CORNER_FPS + 0.0001)),
  );
}
export function coverPolygon(
  polygon: number[][],
  source: { width: number; height: number },
  view: { width: number; height: number },
) {
  const scale = Math.max(
    view.width / source.width,
    view.height / source.height,
  );
  const w = source.width * scale,
    h = source.height * scale;
  return polygon.map(([x, y]) => [
    ((x * w - (w - view.width) / 2) / view.width) * 100,
    ((y * h - (h - view.height) / 2) / view.height) * 100,
  ]);
}
export function coversViewport(polygon: number[][]) {
  return [
    [0, 0],
    [1, 0],
    [1, 1],
    [0, 1],
  ].every(([x, y]) =>
    polygon.every((a, i) => {
      const b = polygon[(i + 1) % polygon.length];
      return (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0]) >= -1e-7;
    }),
  );
}
