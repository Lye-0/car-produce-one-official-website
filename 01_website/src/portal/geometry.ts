export type Point = readonly [number, number];
export type Quad = readonly [Point, Point, Point, Point];
export type Viewport = { width: number; height: number };
export type TrackingFrame = { f: number; quad: number[][]; visible: boolean };
export const rectQuad = ({ width: w, height: h }: Viewport): Quad => [
  [0, 0],
  [w, 0],
  [w, h],
  [0, h],
];
export function sampleQuad(rows: TrackingFrame[], frame: number): Quad | null {
  if (!rows.length || frame < rows[0].f) return null;
  const offset = Math.min(rows.length - 1, Math.max(0, frame - rows[0].f));
  const a = rows[Math.floor(offset)],
    b = rows[Math.min(rows.length - 1, Math.ceil(offset))];
  if (!a.visible || !b.visible) return null;
  const t = offset - Math.floor(offset);
  return a.quad.map((p, i) => [
    p[0] + (b.quad[i][0] - p[0]) * t,
    p[1] + (b.quad[i][1] - p[1]) * t,
  ]) as unknown as Quad;
}
export function coverQuad(quad: Quad, media: Viewport, view: Viewport): Quad {
  const scale = Math.max(view.width / media.width, view.height / media.height);
  const w = media.width * scale,
    h = media.height * scale;
  return quad.map(([x, y]) => [
    x * w + (view.width - w) / 2,
    y * h + (view.height - h) / 2,
  ]) as unknown as Quad;
}
export function containsPoint(quad: Quad, p: Point) {
  let positive = false,
    negative = false;
  for (let i = 0; i < 4; i++) {
    const a = quad[i],
      b = quad[(i + 1) % 4];
    const cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]);
    if (cross > 1e-5) positive = true;
    if (cross < -1e-5) negative = true;
  }
  return !(positive && negative);
}
/** Unit-square homography converted to CSS's column-major matrix3d. */
export function quadMatrix(source: Viewport, quad: Quad) {
  const uv = [
    [0, 0],
    [1, 0],
    [1, 1],
    [0, 1],
  ];
  const rows: number[][] = [];
  for (let i = 0; i < 4; i++) {
    const [u, v] = uv[i],
      [x, y] = quad[i];
    rows.push(
      [u, v, 1, 0, 0, 0, -u * x, -v * x, x],
      [0, 0, 0, u, v, 1, -u * y, -v * y, y],
    );
  }
  for (let c = 0; c < 8; c++) {
    let pivot = c;
    for (let r = c + 1; r < 8; r++)
      if (Math.abs(rows[r][c]) > Math.abs(rows[pivot][c])) pivot = r;
    if (Math.abs(rows[pivot][c]) < 1e-10) return null;
    [rows[c], rows[pivot]] = [rows[pivot], rows[c]];
    const value = rows[c][c];
    for (let j = c; j < 9; j++) rows[c][j] /= value;
    for (let r = 0; r < 8; r++)
      if (r !== c) {
        const f = rows[r][c];
        for (let j = c; j < 9; j++) rows[r][j] -= f * rows[c][j];
      }
  }
  const [a, b, c, d, e, f, g, h] = rows.map((r) => r[8]);
  return [
    a / source.width,
    d / source.width,
    0,
    g / source.width,
    b / source.height,
    e / source.height,
    0,
    h / source.height,
    0,
    0,
    1,
    0,
    c,
    f,
    0,
    1,
  ];
}
