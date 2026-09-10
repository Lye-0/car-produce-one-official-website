import { createHash } from 'node:crypto';
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

const manifest = JSON.parse(
  readFileSync(
    resolve(root, '../02_render/reports/junction-media-manifest.json'),
    'utf8',
  ),
);
for (const profile of ['desktop', 'mobile']) {
  for (const name of ['drive', 'turn']) {
    const path = resolve(root, 'public/media/junction', profile, name + '.mp4');
    const data = readFileSync(path);
    const record = manifest[profile + '/' + name];
    if (
      !record ||
      data.length !== record.bytes ||
      data.length > 25 * 1024 * 1024 ||
      data.toString('ascii', 4, 8) !== 'ftyp'
    )
      throw new Error(`Missing or invalid junction video: ${profile}/${name}`);
    if (createHash('sha256').update(data).digest('hex') !== record.sha256)
      throw new Error(
        `Junction video does not match its validation manifest: ${profile}/${name}`,
      );
  }
  const poster = readFileSync(
    resolve(root, 'public/media/junction', profile, 'drive.jpg'),
  );
  if (poster[0] !== 255 || poster[1] !== 216)
    throw new Error(`Invalid driving poster: ${profile}`);
}
console.log('Verified all four junction videos and both driving posters.');

const production = JSON.parse(
  readFileSync(resolve(root, 'src/production-media.json'), 'utf8'),
);
if (production.production) {
  const jobs = [
    'drive',
    'junction',
    'route',
    'portal',
    'tools-idle',
    'magazines-idle',
    'monitor-idle',
  ];
  let videos = 0;
  for (const profile of ['desktop', 'mobile']) {
    for (const job of jobs) {
      const asset = production.profiles?.[profile]?.[job];
      const prefix = `/media/production/${production.version}/${profile}/${job}/`;
      if (
        !asset ||
        asset.fps !== 30 ||
        !Number.isInteger(asset.frames) ||
        asset.frames <= 0 ||
        asset.variants?.length !== 2 ||
        !asset.poster?.startsWith(prefix)
      )
        throw new Error(`Invalid production asset: ${profile}/${job}`);
      const poster = readFileSync(resolve(root, 'public', '.' + asset.poster));
      if (
        poster.toString('ascii', 0, 4) !== 'RIFF' ||
        poster.toString('ascii', 8, 12) !== 'WEBP'
      )
        throw new Error(`Invalid production poster: ${profile}/${job}`);
      for (const codec of ['hevc', 'h264']) {
        const variant = asset.variants.find((v) => v.codec === codec);
        const [width, height] =
          profile === 'desktop' ? [1920, 1080] : [1080, 1920];
        if (
          !variant ||
          !variant.validated ||
          !variant.src.startsWith(prefix) ||
          variant.src.includes('..') ||
          variant.frames !== asset.frames ||
          variant.fps !== asset.fps ||
          variant.width !== width ||
          variant.height !== height
        )
          throw new Error(
            `Invalid production variant: ${profile}/${job}/${codec}`,
          );
        const data = readFileSync(resolve(root, 'public', '.' + variant.src));
        if (
          data.length !== variant.bytes ||
          data.toString('ascii', 4, 8) !== 'ftyp' ||
          createHash('sha256').update(data).digest('hex') !== variant.sha256
        )
          throw new Error(
            `Production video differs from validated export: ${profile}/${job}/${codec}`,
          );
        videos++;
      }
    }
  }
  console.log(
    `Verified ${videos} production videos by SHA-256 and 14 production posters (${production.version}).`,
  );
}
