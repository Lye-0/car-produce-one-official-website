---
id: rm-20260913-cold-return-gates
topic: video-loading
type: constraint
status: active
maturity: candidate
created: 2026-09-13
last_verified: 2026-09-13
source_commit: "6e311e859fa60d1f42905fa6b134829a08025836"
related_files:
  - 01_website/src/journey/useJourney.ts
  - 01_website/src/media/downloads.ts
  - 01_website/tests/downloads.test.mjs
  - 01_website/src/media/download-gates.ts
  - 01_website/src/media/useStartupLoading.ts
  - 01_website/tests/download-gates.test.mjs
  - 01_website/docs/video-loading.md
tags:
  - reverse-scroll
  - skip
  - buffering
supersedes: null
promoted_to: null
---

# 本文スキップは映像の訪問済み状態ではない

## Conclusion

初期ロードからヘッダーで本文へ直接移動した場合、portalも店内も未取得になり得る。逆方向を無条件に許可せず、移動経路に重なる未取得の映像区間の外側で待機する。一方、未取得の前半を理由に、取得済みの後半から本文へ進む操作を止めない。ロゴや明示的な再開始は通常の逆スクロールに通さず、共通のrestartJourneyで保留入力と入口位相を解除して先頭へ戻す。

## Scope

Applicable: 本文への直接移動、ハッシュリンク、逆スクロール、区間ゲート、再入場。

Do not apply: 読み込み済みの逆移動を一律に止めること、明示的な「もう一度、店舗を巡る」を通常の逆スクロールとして扱うこと。

## Evidence

- `constrainMediaProgress` はstart/end範囲と必要ファイルを使い、要求方向の最初の未取得区間で止める。重なった待機ループと移動映像を同時に準備する。
- 本文からの最初の逆移動はportal終端のデコードまで本文側で待つ。完了しても過去の入力を再実行しない。
- 2026-09-13、EdgeのPC・モバイル幅で「街の取得を保留→アクセスへ直接移動→逆スクロール」を検証。本文側へ移動し直せること、後半の未取得区間で止まることを確認。
- 別途、街が未読込のまま全区間を逆方向に戻り、必要箇所で順に待機して街のループへ復帰することを確認。

- ロゴからの再開始はPC・モバイル幅の本文、逆移動待ち、映像途中、街の取得中で確認済み。完了済み動画を保持して未完了転送だけを取り消すテストを追加した。

- 逆移動の取得順はキュー優先度だけでは足りない。進行中の前半取得を待つと後半のゲートが0%のまま止まる。ゲートの必要ファイルをfocusし、無関係な転送を受信済みデータを保持したまま中断する。Range再開で元のバイト列が復元される単体テスト、および前半を保留したEdgeで後半の進捗が約0.5秒で1%に進むことを確認した。

## Verification

街・portal・中間区間の取得をそれぞれ保留し、本文へ直接移動してから逆スクロールする。待機中は本文と最後の表示を維持し、本文側への前進を許可する。取得を解放しただけで位置が変わらないこと、再度のスクロールで正しい区間へ入ること、街への復帰と明示的リプレイの両方を確認する。

