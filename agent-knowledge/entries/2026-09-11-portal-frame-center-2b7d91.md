---
id: rm-20260911-portal-frame-center
topic: monitor-portal
type: constraint
status: active
maturity: candidate
created: 2026-09-11
last_verified: 2026-09-11
source_commit: "11cc8bd3e0dbe0744842f3a229563d920b27667f"
related_files:
  - 01_website/src/journey/timeline.ts
  - 01_website/src/journey/useJourney.ts
  - 01_website/tests/monitor-projection.test.mjs
tags:
  - mp4
  - frame-center
  - endpoint
supersedes: null
promoted_to: null
---

# モニター終端はフレーム中央へシークする

## Conclusion

モニター接近動画のシークには `createVideoScrubber` の `frameCenter` を使用する。MP4の丸められたdurationからフレーム境界を指定すると、最後の表示フレームに到達する条件とずれる場合がある。中央時刻の指定により、終端フレーム番号とデコード対象をそろえる。

## Scope

Applicable:
- 現在の30fpsのportal動画、終端待機、スクラバーの時刻丸めの変更。

Do not apply:
- 全動画の再生時刻を一律に補正する変更。自動再生とシークの役割はそれぞれの制御に従う。

## Evidence

- `01_website/src/journey/timeline.ts`: `createVideoScrubber` は希望フレームを丸め、最終フレームの範囲に収めてから0.5フレーム分を加える。
- `01_website/src/journey/useJourney.ts`: portal用スクラバーで中央指定を有効にする。
- `01_website/tests/monitor-projection.test.mjs`: `PC scrubbing selects the last frame center despite rounded MP4 duration` はduration 9.033332秒でも最終フレームの中央へ入ることを検証する。

## Verification

1. 新しい動画でもfps、フレーム数、終端の定義がマニフェストと一致することを確認する。
2. `01_website` で `node --test --test-name-pattern="frame center" tests/monitor-projection.test.mjs` を実行する。
3. 接近直後に停止する操作と高速で本文まで進む操作で、終端待ちが不要に長引かないことを確認する。
