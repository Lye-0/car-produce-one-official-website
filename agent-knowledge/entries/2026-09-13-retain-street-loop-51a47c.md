---
id: rm-20260913-retain-street-loop
topic: video-loading
type: failure
status: active
maturity: candidate
created: 2026-09-13
last_verified: 2026-09-13
source_commit: "6e311e859fa60d1f42905fa6b134829a08025836"
related_files:
  - 01_website/src/media/useStartupLoading.ts
  - 01_website/src/media/downloads.ts
  - 01_website/src/media/playback.ts
  - 01_website/src/journey/Journey.tsx
  - 01_website/tests/downloads.test.mjs
  - 01_website/docs/video-loading.md
tags:
  - buffering
  - autoplay
  - bandwidth
  - blob
supersedes: null
promoted_to: null
---

# 街の部分先読みの制約と75%を許容する方針

## Conclusion

街の冒頭5秒だけをネイティブpreloadし、その再生中に店内MP4をfetchする方式は低速回線で破綻する。街の残りと店内が帯域を共有し、再生中のバッファが尽きる。全量保持ではこの帯域競合を避けられるが、最初の黒背景が長くなる。ユーザーはその後、カクつきを許容して75%で街を表示し、店内を優先する方針を明示した。現実装はネイティブ再生で先頭15秒の連続バッファを確認し、先頭へ戻して表示する。この過去の障害を根拠に全量待ちへ戻さない。

## Scope

Applicable: 起動時の街の待機ループ、先読みの順序、低速回線での停止、ロード解除条件の変更。

Do not apply: Safari固有のメモリ制限や描画停止の原因を、この検証だけで断定すること。スクロール用動画すべてを先に取得する根拠にすること。

## Evidence

- 2026-09-13の作業ツリーをEdge・390×844・共有4 Mbpsで確認。旧方式は経過25〜45秒の間、街の再生時刻が4.7999秒から動かず、店内の取得率は9%から24%へ増加した。
- 全量保持後は街を約50秒で表示し、約185秒でスクロールを解放。街はBlobから繰り返し再生し、ネットワーク由来のstalled通知はなかった。利用者が報告したエラー画面自体はこの比較では再現しなかった。
- 別途、店内の通信を保留した24秒間を計測。街は一周以上再生し、722フレーム中3フレームがdrop、最大フレーム間隔100.1ms。完全なコマ落ちゼロを意味しない。
- ネイティブループ境界では短いwaiting通知（この測定では0.1〜2.5ms）が出る。waitingの件数だけで長い停止の回帰と判断せず、実フレーム間隔や停止時間も測る。
- `downloads.test.mjs` は取得途中をreadyと扱わないことと、進捗が続く58秒の転送を30秒の無通信タイムアウトと区別することを検証する。

- 現行75%方式の4 Mbps確認では、約36.84秒時点で街のbufferedが0〜15.062秒、currentTimeが0の状態で店内取得を開始した。

## Verification

4 Mbps・キャッシュ無効で、街の先頭から15秒分の連続バッファができた時点で街を先頭から表示し、店内を取得し始めることを確認する。現方式では街はネイティブHTTPソースのままであり、Blobであることや全量待ちを要件にしない。時間経過による再生停止はフレーム間隔とcurrentTimeの進み方で判定する。Safari実機は別途確認する。
