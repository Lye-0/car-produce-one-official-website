---
id: rm-20260911-route-segment-projection
topic: monitor-portal
type: constraint
status: active
maturity: candidate
created: 2026-09-11
last_verified: 2026-09-13
source_commit: "d08a868a51b8eceb99fcb16fd058d64f446a8ad4"
related_files:
  - 01_website/src/media/segmented-playback.ts
  - 01_website/src/portal/MonitorPortal.tsx
  - 01_website/src/media/manifests/journey.json
  - 01_website/tests/segmented-playback.test.mjs
  - 01_website/docs/route-media.md
tags:
  - video
  - segments
  - projection
  - global-frame
supersedes: null
promoted_to: null
---

# 分割routeのモニター投影は全体フレームを使う

## Conclusion

HEVC・H.264の各区間はローカル時刻0から始まるが、モニター追跡は元のroute全体のフレームを参照する。描画元は現在表示しているセグメントを選び、`startFrame` を加えたフレーム番号とデコード済み画像を組にして投影する。デコード済みの別セグメントへ戻る操作では新しい `seeked` が発生しない場合もあるため、表示先変更の `routeframe` 通知も必要になる。

## Scope

Applicable:
- routeの分割点・フレームレート・表示先の変更、モニター前へのジャンプ、再入場、投影のずれの調査。

Do not apply:
- portal動画へrouteのオフセットを加える処理。portalは別に2430開始として扱う。
- 待機ループを時間に応じて進むカメラ映像として扱う変更。

## Evidence

- `journey.json`: routeのHEVC・H.264はともに5区間。startFrameは0・1212・1512・1812・2112。2つのvideo要素を再利用するため、DOM上の1個目・2個目と区間番号は一致しない。
- `segmented-playback.ts`: 表示中の動画に `data-media-active`・`data-media-start-frame`・`data-media-frame` を設定し、表示先変更時に `routeframe` を送る。
- `MonitorPortal.tsx`: 表示中のrouteから全体フレームを計算してSnapshotを取得する。route末尾2429を元シーンの2430へ対応させる処理も残る。
- `segmented-playback.test.mjs`: 全2430フレームの時間軸変換、境界の往復、デコード済み画像の保持、HEVC失敗時の全体時刻維持を検証する。
- ブラウザーでは分割前後38フレームの画像が未分割の元動画と一致し、実ページのモニター直前でもCanvasと投影のフレーム・描画IDが一致することを確認した。

## Verification

1. `npm test` と `npm run build` を実行し、フレーム範囲・全ファイルのハッシュを照合する。
2. `tests/segmented-video-fixture.html` で1211/30秒と1212/30秒を往復し、表示元と全体フレームを確認する。
3. 実ページでモニター直前へ移り、後半動画のローカル時刻にstartFrameを加えた番号と `portal-camera-canvas` の番号が一致することを確認する。
4. 本文へ入ってから逆スクロールし、Canvasと投影要素の `data-frame`・`data-paint` が一致することを確認する。
