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

現在の出力先は **output/final-junction-03** です。以前の出力と混ざらない名前にしています。
テストは `output/test-final-junction-03/{desktop,mobile}/drive` と `junction` に保存します。

Blender 5.2を使用します。インストール場所が違う場合は `scripts/render.ps1` のblenderPathを変更してください。OPTIX対応GPUを優先し、利用できなければCPUを使用します。

## 出力するPNG連番

| フォルダ | 内容 | 枚数 |
|---|---|---:|
| drive | 交差点へ続く20秒・160mの走行ループ | 600 |
| junction | 減速・90度右折・直進、16秒＋終端 | 481 |
| route | 会社への到着からモニター前まで | 2430 |
| portal | モニターへの接近、終端を含む | 271 |
| tools-idle | 工具の前、6秒ループ | 180 |
| magazines-idle | 雑誌の前、6秒ループ | 180 |
| monitor-idle | モニターの前、6秒ループ | 180 |

走行ループは元シーンの0〜599フレーム、右折は600〜1080フレームです。driveの`endpoint.png`は600フレームで、junctionの最初と同じ位置です。endpoint.pngは動画に含めません。
各ループの専用処理があるため、すべてのサイト素材を出す場合はBlenderのCtrl+F12ではなく、RENDER.cmdを使ってください。

## 中断・再開

Ctrl+Cで中断できます。同じMASTER・設定・スクリプトで再実行すると、完了したPNGをスキップします。
MASTERや画質設定を変更したら、run_nameを`final-junction-03`など新しい名前にしてください。異なる条件が混ざる場合は停止します。
`complete.json`はクリップの完了記録、`progress.json`は最新の進捗、`render-settings.json`は使用条件の記録です。

個別に描画する場合（02_render内のPowerShell）:

```powershell
./scripts/render.ps1 -Action final -Profile desktop -Job junction
```

## サイトへの組み込み

通常の描画メニューは高画質のPNG原本を生成します。サイトの動画は自動で置き換えません。
最新MASTERの走行は20秒・160m、右折は16秒、いずれも30fpsです。下層部の壁・柱・基礎、大小の広告、背後の建物を追加し、現在は静止画の確認段階です。動画の長い描画は停止しています。現行サイトの動画はまだ差し替えておらず、従来の10秒・8fpsの走行、12fpsの右折を使用しています。到着後のrouteは8fps、portalと待機ループは24fpsです。

最終画質の全編描画は、今回の変更では実行していません。

## 接続シーンを作り直す場合

`scripts/build_junction.py`は本編の0フレームを基に、固定した交差点と車の経路の候補を `output/junction-work-v4/CPO_JUNCTION_CANDIDATE.blend` に作ります。候補を確認してからMASTERへ反映してください。
`scripts/render_junction.py`、`encode_junction.py`、`validate_junction_media.py`は確認用動画の作成・照合用です。動画変換に必要なPythonライブラリは `scripts/requirements-media.txt` に記載しています。
通常のRENDER.cmdによるPNG描画には、これらの追加ライブラリは不要です。

確認用の候補や画質を変更して作り直すときは、以前の `output/junction-work-v4` を保管してから候補を生成してください。プレビュー描画・変換は元ファイルの照合情報を確認し、異なる条件のフレームが混ざる場合は停止します。

走行区間は、到着先と同じ建材・店舗・ホテル・段状の建物を、道路へ向けた160mの街区です。
scripts/junction_frontage.pyで配置し、入口や窓の寸法を保つため建物の縦横比は変更していません。
確認動画は横640×360・縦360×640、Cycles 16 samplesです。encode_junction.pyはoutput/junction-work-v4/mediaへ仮出力します。validate_junction_media.py --stagedで確認してからサイトへ反映します。
review_junction.pyはサイトに組み込んだ動画から「3周＋右折」を作成します。

静止画の確認: render_junction.py -- review（横・縦各4枚、960×540／540×960、64 samples）。境界の確認: -- seam（境界前後の6枚ずつ）。動画は -- preview で描画しますが、現在は再開していません。
モデルの確認画像は reports/streetscape-frontage.png、streetscape-depth.png、streetscape-overview.png です。junction-streetscape-review.json に確認段階と元ファイルの照合情報を記録しています。
動画を更新する際は4本のMP4と2枚のポスター、junction-media-manifest.jsonを揃えて反映し、サイトのDRIVE_SECONDSを20、DRIVE_FPS・TURN_FPSを30へ変更してから操作確認を行ってください。

今回の追加修正: 新しい広告8種類、大小24面の追加広告、カフェ・ホテル・オフィス・ガレージ・閉店中の店舗・奥まったロビーの6種類の1階、街路樹8本、駐車区画の車1台、バス停と街路設備を配置しました。左車線の走行と路面表示を整え、古い地面による路面の遮蔽を除去しました。
サイト側は、冒頭へ戻った際にスクロール用のシークを解除し、動画全体のループ再生へ戻す処理を修正しました。23件のテストと横・縦画面で復帰を確認済みです。CGの更新はMASTERと確認画像に反映済みで、サイトの動画差し替えは長編描画後です。

短い動きの確認は `render_junction.py -- short desktop` → `encode_streetlife_review.py`。reports/streetlife-short.mp4は元240〜329フレームの3秒、streetlife-loop-boundary.mp4は570〜599→0〜29の2秒です。30fpsを保ち、補間や速度変更は行いません。この2本は部分確認用で、サイト用の全編素材ではありません。
