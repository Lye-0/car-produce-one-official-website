# 最終レンダリングの手順

## 使うファイル

最新版は **scene/CPO_MASTER.blend** です。ルートの **OPEN_BLENDER.cmd** で開けます。画像を内包しており、過去フォルダの素材を探す必要はありません。

- `CPO_JUNCTION_DRIVE`: 最初の走行と交差点の右折。固定した街区の中を、車と車載カメラが走行します。
- `CPO_V18_SITE_MAIN`: 会社への到着から店内、モニターまで。
- `CPO_V18_CITY_LOOP`: 以前の都市ループの記録。現在のサイトでは使用しません。

## 実行方法

1. 必要な編集をMASTERへ保存します。
2. `settings.json` で画質を設定します。初期値は横1920×1080／縦1080×1920、30fps、Cycles 128 samples、デノイズ有効です。width・heightは横向きの寸法で、縦向きは自動で入れ替えます。fpsは30のまま使用してください。
3. ルートの **RENDER.cmd** を開きます。
4. `1` でファイルと設定を確認、`2` で横・縦各5枚の小さなテスト描画を実行します。
5. `3` が横のみ、`4` が縦のみ、`5` が両方の最終描画です。

現在の出力先は **output/final-junction-01** です。以前の出力と混ざらない名前にしています。
テストは `output/test/{desktop,mobile}/drive` と `junction` に保存します。

Blender 5.2を使用します。インストール場所が違う場合は `scripts/render.ps1` のblenderPathを変更してください。OPTIX対応GPUを優先し、利用できなければCPUを使用します。

## 出力するPNG連番

| フォルダ | 内容 | 枚数 |
|---|---|---:|
| drive | 交差点へ続く10秒の走行ループ | 300 |
| junction | 減速・90度右折・直進、16秒＋終端 | 481 |
| route | 会社への到着からモニター前まで | 2430 |
| portal | モニターへの接近、終端を含む | 271 |
| tools-idle | 工具の前、6秒ループ | 180 |
| magazines-idle | 雑誌の前、6秒ループ | 180 |
| monitor-idle | モニターの前、6秒ループ | 180 |

走行ループは元シーンの0〜299フレーム、右折は300〜780フレームです。driveの`endpoint.png`は300フレームで、junctionの最初と同じ位置です。endpoint.pngは動画に含めません。
各ループの専用処理があるため、すべてのサイト素材を出す場合はBlenderのCtrl+F12ではなく、RENDER.cmdを使ってください。

## 中断・再開

Ctrl+Cで中断できます。同じMASTER・設定・スクリプトで再実行すると、完了したPNGをスキップします。
MASTERや画質設定を変更したら、run_nameを`final-junction-02`など新しい名前にしてください。異なる条件が混ざる場合は停止します。
`complete.json`はクリップの完了記録、`progress.json`は最新の進捗、`render-settings.json`は使用条件の記録です。

個別に描画する場合（02_render内のPowerShell）:

```powershell
./scripts/render.ps1 -Action final -Profile desktop -Job junction
```

## サイトへの組み込み

通常の描画メニューは高画質のPNG原本を生成します。サイトの動画は自動で置き換えません。
全素材が揃った後、MP4へ変換し、サイト側のfps設定を揃えて接続を確認します。現在の走行ループは8fps、右折は12fps、店内までのrouteは8fps、portalと待機ループは24fpsの確認用です。最終30fpsへ差し替える際は、それぞれのスクロール制御のfpsも変更してください。

最終画質の全編描画は、今回の変更では実行していません。

## 接続シーンを作り直す場合

`scripts/build_junction.py`は本編の0フレームを基に、固定した交差点と車の経路の候補を `output/junction-work/CPO_JUNCTION_CANDIDATE.blend` に作ります。候補を確認してからMASTERへ反映してください。
`scripts/render_junction.py`、`encode_junction.py`、`validate_junction_media.py`は確認用動画の作成・照合用です。動画変換に必要なPythonライブラリは `scripts/requirements-media.txt` に記載しています。
通常のRENDER.cmdによるPNG描画には、これらの追加ライブラリは不要です。

確認用の候補や画質を変更して作り直すときは、以前の `output/junction-work` を保管してから候補を生成してください。プレビュー描画・変換は元ファイルの照合情報を確認し、異なる条件のフレームが混ざる場合は停止します。
