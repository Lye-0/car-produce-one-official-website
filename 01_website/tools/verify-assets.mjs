import { createHash } from 'node:crypto';
import { readFileSync, statSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
const root = resolve(import.meta.dirname, '..');
const readJson = (path) =>
  JSON.parse(readFileSync(resolve(root, path), 'utf8'));
const production = readJson('src/media/manifests/journey.json');
const live = {
  desktop: readJson('src/media/manifests/portal-desktop.json'),
  mobile: readJson('src/media/manifests/portal-mobile.json'),
};
const expectedVideos = new Set();
let videoCount = 0,
  posterCount = 0;
function local(url) {
  if (!url?.startsWith('/media/') || url.includes('..'))
    throw new Error(`Invalid asset URL: ${url}`);
  return resolve(root, 'public', '.' + url);
}
function poster(url) {
  const data = readFileSync(local(url));
  if (
    data.toString('ascii', 0, 4) !== 'RIFF' ||
    data.toString('ascii', 8, 12) !== 'WEBP'
  )
    throw new Error(`Invalid poster: ${url}`);
  posterCount++;
}
for (const profile of ['desktop', 'mobile']) {
  const [width, height] = profile === 'desktop' ? [1920, 1080] : [1080, 1920];
  const jobs = Object.entries(production.profiles[profile]);
  if (
    jobs.length !== 5 ||
    ['drive', 'junction', 'route', 'tools-idle', 'magazines-idle'].some(
      (job) => !production.profiles[profile][job],
    )
  )
    throw new Error(`Invalid production jobs: ${profile}`);
  for (const [job, asset] of [...jobs, ...Object.entries(live[profile])]) {
    if (
      asset.fps !== 30 ||
      !Number.isInteger(asset.frames) ||
      asset.frames <= 0 ||
      asset.variants?.length !== 2
    )
      throw new Error(`Invalid asset: ${profile}/${job}`);
    poster(asset.poster);
    for (const codec of ['hevc', 'h264']) {
      const v = asset.variants.find((v) => v.codec === codec);
      if (
        !v?.validated ||
        v.frames !== asset.frames ||
        v.fps !== 30 ||
        v.width !== width ||
        v.height !== height
      )
        throw new Error(`Invalid variant: ${profile}/${job}/${codec}`);
      const file = local(v.src),
        data = readFileSync(file);
      if (
        data.length !== v.bytes ||
        data.toString('ascii', 4, 8) !== 'ftyp' ||
        createHash('sha256').update(data).digest('hex') !== v.sha256
      )
        throw new Error(`Video differs from validated export: ${v.src}`);
      expectedVideos.add(file);
      videoCount++;
    }
  }
  for (const url of Object.values(production.posters[profile])) poster(url);
  const tracking = readJson(`src/portal/tracking/${profile}.json`);
  if (
    tracking.length !== 361 ||
    tracking.some(
      (row, i) =>
        row.f !== 2340 + i ||
        !row.visible ||
        row.quad.length !== 4 ||
        row.quad.some(
          (p) => p.length !== 2 || p.some((v) => !Number.isFinite(v)),
        ),
    )
  )
    throw new Error(`Invalid live screen tracking: ${profile}`);
  for (const name of [
    'city.jpg',
    'tools.jpg',
    'magazines.jpg',
    'monitor.jpg',
    'car-foreground.png',
  ])
    if (
      !statSync(resolve(root, 'public/media/images/fallback', profile, name))
        .size
    )
      throw new Error(`Empty fallback image: ${profile}/${name}`);
  if (
    !statSync(
      resolve(root, 'public/media/images/fallback', profile, 'drive.jpg'),
    ).size
  )
    throw new Error(`Empty driving poster: ${profile}`);
}
for (const name of ['tools.webp', 'car.jpg'])
  if (!statSync(resolve(root, 'public/media/images/monitor-wings', name)).size)
    throw new Error(`Empty monitor wing: ${name}`);
function checkDirectory(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const file = resolve(dir, entry.name);
    if (entry.isDirectory()) checkDirectory(file);
    else if (/\.(mp4|webm|mov)$/i.test(entry.name) && !expectedVideos.has(file))
      throw new Error(`Unreferenced delivery video: ${file}`);
  }
}
checkDirectory(resolve(root, 'public/media'));
console.log(
  `Verified ${videoCount} active videos by SHA-256, ${posterCount} production posters, fallback images, and both live screen tracks; no unreferenced delivery videos.`,
);
