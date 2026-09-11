---
id: rm-20260911-paused-video-presentation
topic: monitor-portal
type: constraint
status: active
maturity: candidate
created: 2026-09-11
last_verified: 2026-09-11
source_commit: "11cc8bd3e0dbe0744842f3a229563d920b27667f"
related_files:
  - 01_website/src/portal/MonitorPortal.tsx
  - 01_website/src/journey/useJourney.ts
tags:
  - video
  - seeked
  - reverse-scroll
supersedes: null
promoted_to: null
---

# 非表示中の動画シークとモニター描画

## Conclusion

モニターへの再入場では、`requestVideoFrameCallback` と `seeked`／`loadeddata` の両経路で、デコード済み画像と対応フレームを取得する必要がある。本文表示中に完了するpaused動画のシークは、提示コールバックだけでは画面への反映が欠ける場合がある。

## Scope

Applicable:
- 店舗映像と本文を往復する操作、映像の表示切り替え、モニター投影の更新処理。

Do not apply:
- 自動再生の街ループを、この理由だけで毎フレームシークへ変更する判断。

## Evidence

- `01_website/src/portal/MonitorPortal.tsx`: `capture` は画像とフレーム番号を同じSnapshotへ保存し、`paint` がCanvasとHTMLの投影を更新する。
- 同ファイルの `decoded` は `video.seeking` の終了を確認し、`seeked` と `loadeddata` から取得する。
- `01_website/src/journey/useJourney.ts`: スクロール制御は本文表示中も動画の再入場位置を扱う。本文から戻る操作ではデコード完了と提示のタイミングが分離し得る。

## Verification

1. 現在の `capture`、`decoded`、コールバック解除処理が同じ動画を扱うことを確認する。
2. サイトへ入り、本文のサービスリンクへ進んでからモニター内へ逆スクロールする。
3. カメラCanvasと投影要素の `data-frame`／`data-paint` が一致し、停止後も最後の入力位置が表示されることを確認する。
