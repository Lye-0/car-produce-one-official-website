---
id: rm-20260913-safari-route-flash
topic: video-loading
type: case
status: active
maturity: candidate
created: 2026-09-13
last_verified: 2026-09-13
source_commit: "42dd58c2db6633405e3e6362346c05a0349c0bc4"
related_files:
  - 01_website/src/media/ScrubMediaVideo.tsx
  - 01_website/src/media/segmented-playback.ts
  - 01_website/src/styles/globals.css
  - 01_website/tests/segmented-playback.test.mjs
  - 01_website/docs/route-media.md
tags:
  - safari
  - video
  - compositing
supersedes: null
promoted_to: null
---

# 分割切り替え中に章別fallbackが露出する

## Conclusion

ユーザー提供Safari録画2本で、routeの工具・窓場面の切り替えに雑誌コーナーの代替画像が1～2コマ露出した。active切り替え直前に旧videoの画像をCanvasへ保存し、videoより下、fallbackより上に置く防御を追加。代替画像の削除だけでは空白に変わり得る。

## Scope

分割routeの正逆方向切り替え。Safari全般のバグ断定や、修正後実機検証済みという意味には用いない。

## Evidence

2026-09-13提供録画の4.226667秒（1コマ）と3.311667秒（2コマ）で同じ雑誌コーナー画像を確認。ローカルHEVCの分割境界は工具・窓の景色で連続していた。beforeSwitchによる正逆の事前保存・保存失敗時の旧レイヤー維持テストを追加し76件PASS。Edgeでは1026→1701の切り替えと1920×1080の保持Canvas生成を確認。Safari内部のイベント順序と修正後の実機結果は未確認。

## Verification

Safari実機で工具の説明終了（part1→2）と窓・カウンター付近（part2→3）を正逆方向に往復し、録画を全フレーム確認する。ロード・停止・リプレイ・画面幅変更でも保持画像が別プロファイルから残らないことを確認する。

## Follow-up: 前回の保持だけでは不十分

11:39:58の追加Safari録画で5.325秒（1コマ）に街の画像が出た。雑誌画像ではない。分割videoに共通の街posterを指定していたことと、保持Canvasが切り替え時にしか更新されず初回の街画像を保持し続けることを確認した。2026-09-13にposter指定を除去し、routeframeごとにCanvasを更新する修正を追加。元の対策だけで解決済みと扱わない。77件の自動テストが通過し、修正後Safari実機での再検証は依然必要。
