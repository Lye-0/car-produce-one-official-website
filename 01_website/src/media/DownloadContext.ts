import { createContext } from 'react';
import type { VideoDownloads } from './downloads';
export const DownloadContext = createContext<VideoDownloads | null>(null);
