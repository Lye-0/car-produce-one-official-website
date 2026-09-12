import {
  browserCapability,
  preferredVariant,
  type MediaAsset,
  type MediaVariant,
} from './playback.ts';
/** One transfer per URL. Visible footage outranks speculative prefetches. */
type Entry = {
  src: string;
  received: number;
  total: number;
  url?: string;
  error?: Error;
  priority: number;
  touched: number;
  pins: number;
  visited?: boolean;
  chunks: ArrayBuffer[];
  paused?: boolean;
  promise: Promise<string>;
  resolve: (url: string) => void;
  reject: (error: Error) => void;
};
export class VideoDownloads {
  private choices = new Map<MediaAsset, Promise<MediaVariant>>();
  private selected = new Map<MediaAsset, MediaVariant>();
  choose(asset: MediaAsset) {
    let choice = this.choices.get(asset);
    if (!choice) {
      choice = preferredVariant(asset, browserCapability).then((variant) => {
        this.selected.set(asset, variant);
        this.notify();
        return variant;
      });
      this.choices.set(asset, choice);
    }
    return choice;
  }
  variant(asset: MediaAsset) {
    return this.selected.get(asset);
  }
  remember(asset: MediaAsset, variant: MediaVariant) {
    if (this.selected.get(asset) === variant) return;
    this.selected.set(asset, variant);
    this.choices.set(asset, Promise.resolve(variant));
    this.notify();
  }
  private entries = new Map<string, Entry>();
  private listeners = new Set<() => void>();
  private active?: AbortController;
  private activeEntry?: Entry;
  private focused = new Set<string>();
  focus(sources: readonly string[]) {
    this.focused = new Set(sources);
    const entry = this.activeEntry;
    if (
      entry &&
      sources.length &&
      !this.focused.has(entry.src) &&
      sources.some((src) => {
        const candidate = this.entries.get(src);
        return candidate && !candidate.url && !candidate.error;
      }) &&
      !(entry.total > 0 && entry.received >= entry.total)
    ) {
      entry.paused = true;
      this.active?.abort();
    }
    this.notify();
  }
  private disposed = false;
  private revision = 0;
  private timer?: ReturnType<typeof setTimeout>;
  readonly subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };
  readonly snapshot = () => this.revision;
  private notify() {
    if (this.timer || this.disposed) return;
    this.timer = setTimeout(() => {
      this.timer = undefined;
      this.revision++;
      this.listeners.forEach((fn) => fn());
    }, 100);
  }
  progress(sources: readonly string[]) {
    let received = 0,
      total = 0;
    for (const src of new Set(sources)) {
      const entry = this.entries.get(src);
      if (!entry) return 0;
      received += entry.received;
      total += entry.total;
    }
    return total ? Math.min(1, received / total) : 0;
  }
  error() {
    return [...this.entries.values()].find((e) => e.error)?.error;
  }
  isReady(src: string) {
    return Boolean(this.entries.get(src)?.url);
  }
  prefetch(src: string, total = 0) {
    const retained = [...this.entries.values()].reduce(
      (bytes, entry) => bytes + entry.total,
      0,
    );
    if (!this.entries.has(src) && retained + total > 160 * 1024 * 1024)
      return Promise.resolve();
    return this.ensure(src, total, 10).then(() => {});
  }
  retry() {
    for (const [src, entry] of this.entries)
      if (entry.error) this.entries.delete(src);
    this.notify();
  }
  cancelPending() {
    this.active?.abort();
    for (const [src, entry] of this.entries) {
      if (entry.url) continue;
      entry.reject(new Error('Navigation restarted'));
      this.entries.delete(src);
    }
    this.notify();
  }
  ensure(src: string, total = 0, priority = 0): Promise<string> {
    if (this.disposed)
      return Promise.reject(new Error('Download session closed'));
    const found = this.entries.get(src);
    if (found) {
      if (!found.total && total) found.total = total;
      found.priority = Math.min(found.priority, priority);
      found.touched = Date.now();
      return found.promise;
    }
    let resolve!: Entry['resolve'], reject!: Entry['reject'];
    const promise = new Promise<string>((yes, no) => {
      resolve = yes;
      reject = no;
    });
    this.entries.set(src, {
      src,
      total,
      received: 0,
      priority,
      touched: Date.now(),
      pins: 0,
      chunks: [],
      promise,
      resolve,
      reject,
    });
    this.notify();
    void this.pump();
    return promise;
  }
  async acquire(src: string, priority = 0) {
    if (this.disposed) throw new Error('Download session closed');
    const promise = this.ensure(src, 0, priority);
    const entry = this.entries.get(src)!;
    entry.pins++;
    entry.visited = true;
    try {
      const url = await promise;
      return {
        url,
        release: () => {
          entry.pins = Math.max(0, entry.pins - 1);
          this.trim();
        },
      };
    } catch (error) {
      entry.pins--;
      throw error;
    }
  }
  private trim() {
    // Attached videos retain their source; only unreferenced downloads are evicted.
    let bytes = [...this.entries.values()]
      .filter((e) => e.url)
      .reduce((n, e) => n + e.received, 0);
    for (const entry of [...this.entries.values()].sort(
      (a, b) => a.touched - b.touched,
    )) {
      if (bytes <= 160 * 1024 * 1024) break;
      if (!entry.url || entry.pins || entry.visited) continue;
      URL.revokeObjectURL(entry.url);
      this.entries.delete(entry.src);
      bytes -= entry.received;
    }
  }
  private async pump() {
    if (this.active || this.disposed) return;
    const entry = [...this.entries.values()]
      .filter((e) => !e.url && !e.error)
      .sort(
        (a, b) =>
          Number(this.focused.has(b.src)) - Number(this.focused.has(a.src)) ||
          a.priority - b.priority,
      )[0];
    if (!entry) return;
    const controller = new AbortController();
    this.active = controller;
    this.activeEntry = entry;
    let timeout: ReturnType<typeof setTimeout>;
    const touch = () => {
      clearTimeout(timeout);
      timeout = setTimeout(() => controller.abort(), 30000);
    };
    try {
      touch();
      const offset = entry.received;
      const response = await fetch(entry.src, {
        signal: controller.signal,
        ...(offset ? { headers: { Range: `bytes=${offset}-` } } : {}),
      });
      if (!response.ok)
        throw new Error(`Video download failed (${response.status})`);
      const length = Number(response.headers.get('content-length'));
      if (response.status === 206) {
        const range = /^bytes (\d+)-(\d+)\/(\d+)$/.exec(
          response.headers.get('content-range') ?? '',
        );
        if (
          !range ||
          Number(range[1]) !== offset ||
          (entry.total && entry.total !== Number(range[3]))
        )
          throw new Error('Invalid video resume response');
        entry.total = Number(range[3]);
      } else {
        if (offset) {
          entry.received = 0;
          entry.chunks = [];
        }
        if (!entry.total && length) entry.total = length;
      }
      const reader = response.body?.getReader();
      const chunks = entry.chunks;
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          chunks.push(value.slice().buffer);
          entry.received += value.byteLength;
          touch();
          this.notify();
        }
      } else {
        const data = await response.arrayBuffer();
        chunks.push(data);
        entry.received += data.byteLength;
      }
      if (entry.total && entry.received !== entry.total)
        throw new Error('Incomplete video download');
      if (this.disposed) throw new Error('Download session closed');
      entry.total = entry.received;
      entry.url = URL.createObjectURL(new Blob(chunks, { type: 'video/mp4' }));
      entry.chunks = [];
      entry.resolve(entry.url);
    } catch (error) {
      if (entry.paused) entry.paused = false;
      else {
        entry.error = error instanceof Error ? error : new Error(String(error));
        entry.chunks = [];
        entry.reject(entry.error);
      }
    } finally {
      clearTimeout(timeout!);
      this.active = undefined;
      this.activeEntry = undefined;
      this.notify();
      if (!this.disposed) void this.pump();
    }
  }
  dispose() {
    this.disposed = true;
    this.active?.abort();
    clearTimeout(this.timer);
    for (const entry of this.entries.values()) {
      if (entry.url) URL.revokeObjectURL(entry.url);
      else entry.reject(new Error('Download session closed'));
    }
    this.entries.clear();
    this.choices.clear();
    this.selected.clear();
    this.listeners.clear();
  }
}
