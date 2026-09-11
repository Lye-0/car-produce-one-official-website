import assert from 'node:assert/strict';
import { lstatSync, readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..', 'dist');
const base = (process.env.PAGES_BASE_PATH || '/').replace(/\/+$/, '') + '/';
let bytes = 0,
  files = 0,
  videos = 0;
function visit(directory) {
  for (const entry of readdirSync(directory)) {
    const path = resolve(directory, entry),
      stat = lstatSync(path);
    assert(!stat.isSymbolicLink(), `Unexpected symbolic link: ${path}`);
    if (stat.isDirectory()) visit(path);
    else {
      assert(
        stat.isFile() && stat.nlink === 1,
        `Unexpected file or hard link: ${path}`,
      );
      bytes += stat.size;
      files++;
      if (entry.endsWith('.mp4')) {
        assert(stat.size < 100 * 1024 * 1024, `Video exceeds 100 MiB: ${path}`);
        videos++;
      }
    }
  }
}
visit(root);
assert(bytes < 1_000_000_000, 'The published site must be smaller than 1 GB.');
assert(videos > 0, 'The publication directory must include the videos.');
const html = readFileSync(resolve(root, 'index.html'), 'utf8');
const resources = [...html.matchAll(/(?:src|href)="([^"]+)"/g)].map(
  (match) => match[1],
);
assert(resources.some((url) => url.endsWith('.js')));
assert(resources.some((url) => url.endsWith('.css')));
for (const url of resources) {
  if (/^(https?:|data:|#)/.test(url)) continue;
  assert(url.startsWith(base), `Resource is outside the Pages path: ${url}`);
  assert(
    lstatSync(resolve(root, url.slice(base.length))).isFile(),
    `Missing built resource: ${url}`,
  );
}
console.log(
  `PASS: ${files} publishable files, ${videos} videos, ${bytes} bytes, base ${base}`,
);
