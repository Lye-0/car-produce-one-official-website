# 制作準備と検証

準備日：2026-09-08。使用：Blender 5.2.0 LTS。

## 原本の移管

Downloadsの `CAR_PRODUCE_ONE_ANIMATED_v13_PACKAGE/CAR_PRODUCE_ONE_v13` から42ファイルを `assets/source/v13` にコピー。各ファイルのSHA-256をコピー元と比較し、不一致0。元ファイルは削除していない。

GLB、timeline、カメラサンプル、元のBlender設定スクリプト、Web確認プレイヤー、プレビュー、制作・検証ソースを相対パスごと保持した。元ソースからの再生成には別途v12 GLBが必要で、同梱されていない。現v13の利用・Blender編集にv12は不要。

## 作業用Blenderファイル

`assets/blender/CPO_v13_working.blend`（約39MB、圧縮保存）。

- 独立したBlenderプロセスで、元の `OPEN_IN_BLENDER.py` を実行して読み込み。ユーザーの作業中シーンに重ねていない。
- シーン `CPO_v13_ANIMATED`、4,796オブジェクト（4,134メッシュオブジェクト）。
- カメラ `CPO_CINEMATIC_CAMERA`、30fps、0〜2700フレーム。
- `CPO_MASTER_90s` と `CPO_IDLE_CITY_LOOP` を保持。未使用アクションにもfake userを設定し、保存後に失われないようにした。
- 本編用では独立した街ループは無効。再利用時にはアクションを対象へ明示的に割り当て、主アニメーションと二重に動かさない。
- 61画像データブロック、外部ファイル画像の未パック0。GLBの画像定義数とはインポーターによる重複の統合などで一致するとは限らない。
- 元の設定スクリプトに従った確認用ワールド・補助照明・9個の章マーカー・非表示の経路ガイドを含む。
- 経路ガイドは参照用の折れ線で、主カメラを駆動する編集用スプラインリグではない。実際のカメラは焼き込まれたアニメーションを再生する。
- 最終照明や車の造形には手を加えていない。PCからHTMLへの接続は同梱Web側の機能であり、blend単体には含まれない。

## 検証

保存前と、別のBlenderプロセスで保存済みファイルを開き直した後に、主要20フレームのカメラ位置・回転を `camera_samples.npz` と比較。位置最大誤差は約0.00000131m、回転の比較値は最大約0.040度（浮動小数点精度を含む）。両方合格。

詳細：`blender-import-validation.json`、`blender-reopen-validation.json`。

開き直したファイルから、工具台（1080）、雑誌（1800）、PC（2520）をCycles CPU、640×360、8samplesで確認レンダリングし、画像を目視確認した。画像は `work/blender-review` にある。これは材質・空間・構図の読み込み確認であり、本番品質の映像ではない。

今回、モデル全体の衝突判定やスマホでの性能検証は再実施していない。同梱されている旧検証記録は、元の作成環境での結果として区別する。

## Blender MCP

初回はBlenderが起動しておらず未接続。既存のBlender 5.2と導入済み `blender_mcp` アドオンで作業ファイルを開いた後、MCP経由でファイルパス、カメラ、オブジェクト数、フレーム範囲とサーバー稼働を確認済み。

新規アドオンのインストールやユーザー設定の保存はしていない。次回もこのblendを開き、必要ならBlender MCPパネルの接続操作を行う。MCPで変更する前には現在のファイルパスを確認する。

## 補助ツール

`tools/prepare_blender.py` は原本からの再変換と保存後検証用。既存の作業blendを上書きしない。再検証例：

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --threads 8 --python-exit-code 1 --python tools/prepare_blender.py -- . --verify
```

`--render` を追加すると一時確認画像を出力する。再検証時の低解像度レンダー設定は作業blendへ保存しない。

プレビュー起動は `OPEN_PREVIEW.cmd`。Pythonの自動検出が合わない環境では `CPO_PYTHON` 環境変数にPython実行ファイルを指定できる。既存のプレビューソースは未改変。
