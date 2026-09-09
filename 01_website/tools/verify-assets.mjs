import { readFileSync, statSync, openSync, readSync, closeSync } from 'node:fs';
import { resolve } from 'node:path';
const root = resolve(import.meta.dirname, '..');
let checked = 0;
for (const profile of ['desktop', 'mobile']) {
  for (const name of [
    'city.mp4',
    'route.mp4',
    'portal.mp4',
    'tools-idle.mp4',
    'magazines-idle.mp4',
    'monitor-idle.mp4',
    'city.jpg',
    'tools.jpg',
    'magazines.jpg',
    'monitor.jpg',
    'car-foreground.png',
  ]) {
    const path = resolve(root, 'public/media/stage4', profile, name),
      stat = statSync(path);
    if (!stat.isFile() || stat.size === 0)
      throw new Error(`Missing media: ${profile}/${name}`);
    if (name.endsWith('.mp4')) {
      if (stat.size > 25 * 1024 * 1024)
        throw new Error(`Media exceeds project file budget: ${name}`);
      const file = openSync(path, 'r'),
        header = Buffer.alloc(16);
      try {
        readSync(file, header, 0, 16, 0);
      } finally {
        closeSync(file);
      }
      if (header.toString('ascii', 4, 8) !== 'ftyp')
        throw new Error(`Invalid MP4: ${name}`);
    }
    checked++;
  }
}
const tracking = JSON.parse(
  readFileSync(resolve(root, 'src/screen-tracking.json'), 'utf8'),
);
for (const profile of ['desktop', 'mobile']) {
  const frames = tracking[profile];
  if (frames.length !== 271 || frames[0].f !== 2430 || frames.at(-1).f !== 2700)
    throw new Error(`Invalid screen tracking: ${profile}`);
  if (
    frames.some(
      (row) =>
        !row.visible ||
        row.quad.length !== 4 ||
        row.quad.some(
          (p) => p.length !== 2 || p.some((v) => !Number.isFinite(v)),
        ),
    )
  )
    throw new Error(`Invalid monitor coordinates: ${profile}`);
}
console.log(
  `Verified ${checked} media files and both screen-tracking profiles.`,
);

const corner = JSON.parse(
  readFileSync(resolve(root, 'src/corner-tracking.json'), 'utf8'),
);
for (const profile of ['desktop', 'mobile']) {
  const video = resolve(root, 'public/media/corner', profile, 'corner.mp4');
  const stat = statSync(video);
  if (!stat.isFile() || stat.size < 1000 || stat.size > 25 * 1024 * 1024)
    throw new Error(`Invalid corner video: ${profile}`);
  const rows = corner.profiles[profile];
  if (
    rows.length !== 97 ||
    rows.some(
      (r, i) =>
        r.f !== i ||
        r.polygon.length < 4 ||
        r.polygon.some(
          (p) => p.length !== 2 || p.some((v) => !Number.isFinite(v)),
        ),
    )
  )
    throw new Error(`Invalid corner tracking: ${profile}`);
  for (const f of [46, 47, 48, 49, 50]) {
    const polygon = rows[f].polygon;
    for (const [x, y] of [
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    ]) {
      if (
        !polygon.every((a, i) => {
          const b = polygon[(i + 1) % polygon.length];
          return (
            (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0]) >= -1e-7
          );
        })
      )
        throw new Error(`Exposed street at corner cut: ${profile}, ${f}`);
    }
  }
}
console.log('Verified both corner videos and the fully occluded cut interval.');
