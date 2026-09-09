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
