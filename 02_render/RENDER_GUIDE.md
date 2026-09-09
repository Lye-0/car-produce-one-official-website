# 最終レンダリングの手順

## 使用するファイルと現在の設定

原本は `scene/CPO_MASTER.blend`。ルートの `OPEN_BLENDER.cmd` で開けます。レンダリング時の画質は `settings.json` から上書きするため、MASTERの画質表示と異なる場合があります。

- 横1920×1080／縦1080×1920、30fps、16bit RGB PNG。
- Cycles最大48・最小8サンプル、ノイズ閾値0.05。
- 最大反射回数6、反射・屈折コースティクス無効。
- OptiX GPU描画、OpenImageDenoise GPU・High。連続フレームのデータ再利用が有効。
- 現在の `run_name`: `final-glass-fixed-01`。

`CPO_JUNCTION_DRIVE` が走行・右折、`CPO_V18_SITE_MAIN` が到着から店内・モニターまでです。旧 `CPO_V18_CITY_LOOP` は現行サイトで使用しません。

## RENDER.cmd のメニュー

既に開いているメニューは閉じ、ルートの **RENDER.cmdを開き直してください**。以前のメニューと番号が異なります。

| 番号 | 処理 |
|---|---|
| 1 | GPU・原本・空き容量・実エンコーダーの事前確認。シーン描画なし |
| 2 | 低解像度の技術確認用PNGテスト |
| 3 | 本番画質の部分サンプル・静止画と二形式動画生成 |
| **4** | **横・縦の全シーンをPNG描画し、H.265／H.264を生成** |
| **5** | **完成済みの本番PNGから動画生成だけを実行** |
| 6 | 品質サンプルからの時間・容量見積もり |
| 7 | 全14クリップの二形式が完成・検証済みの場合にローカルサイトへ反映 |
| 8 | 出力フォルダーを開く |

最初に1で確認し、全編作成は4を選びます。4はサイトへの反映までは実行しません。まず完成した映像を確認してください。

ドアガラスを窓枠に沿う形へ修正し、厚みの重複を解消済みです。旧 `output/final-optimized-02` の181枚は保持していますが、原本が変わったため新しい連番へ流用しません。修正版は上記の出力先で最初から描画します。

## GPUでの動画生成

`encoding.json` の `backend` は **nvenc**。H.265は `hevc_nvenc` のMain10・10bit、H.264は `h264_nvenc` のHigh・8bitです。両方とも1080p・30fps、SDR BT.709で色を合わせます。

現在は品質重視のP7/HQ、H.265 CQ18／H.264 CQ17。CQはCPUエンコーダーのCRFと異なる尺度で、数値をそのまま交換しません。スクロール映像はGOP6、走行・待機ループはGOP30。Bフレームなし、fast-start MP4です。

両形式を新規生成する際は、PNG読み込みと色変換を一度だけ行って2つのGPUエンコーダーで共有します。PNGの読み込みや色変換・検証にはCPUも使用します。GPU化するのは主に動画圧縮であり、PNGを描画する時間とは別です。

長い描画の前に、横・縦それぞれでH.265／H.264を実エンコードし、10bit/8bit・色・フレーム数・GOPをデコード検証します。**GPUが使用できない場合は停止し、自動的にCPU方式へ切り替えません。** 意図してCPU方式を使う場合のみ `backend` を `software` に変更し、新しい `name` にしてください。

現在の動画出力設定名は `delivery-nvenc-01`。変更する場合は新しい名前にして、旧エンコードと混在させません。

## 出力先と枚数

PNG原本: `output/final-glass-fixed-01/{desktop,mobile}/{job}/`

動画・WebP・検証記録: `output/final-glass-fixed-01/exports/delivery-nvenc-01/`

部分サンプルは `output/quality-final-glass-fixed-01/`、1枚比較は `output/sample-final-glass-fixed-01/` に分離されます。

| job | 内容 | 各向きの動画用PNG枚数 |
|---|---|---:|
| drive | 20秒の走行ループ | 600 |
| junction | 減速・右折・直進、終端を含む | 481 |
| route | 会社への到着からモニター前まで | 2430 |
| portal | モニターへの接近、終端を含む | 271 |
| tools-idle | 工具前の6秒ループ | 180 |
| magazines-idle | 雑誌前の6秒ループ | 180 |
| monitor-idle | モニター前の6秒ループ | 180 |

横・縦とループの検証用endpointを含め、全体で8,652枚。endpoint.pngは動画に含みません。独自のフレーム対応と照明処理があるため、全素材の作成にはBlenderのCtrl+F12ではなくRENDER.cmdを使ってください。

## 中断・再開

同じ原本・設定・スクリプトで再実行すると、PNGの寸法・bit深度・CRC・終端を確認し、正常な画像を再利用します。動画も元PNGのハッシュとデコード結果を確認して再利用します。一方だけ失敗した場合は、その形式だけ再生成します。

原本や描画設定を変えたら `settings.json` の `run_name` を変更します。エンコードだけを変更する場合は `encoding.json` の `name` を変更します。原本・描画スクリプト・設定の不一致では、既存の連番への追加を停止します。

残りのPNGに必要な容量と20GiBの予備容量を確認します。実行中だけWindowsの自動スリープを抑え、終了時に元へ戻します。

## 実行環境

Blender 5.2とOptiX対応GPUを使用します。Blenderの場所は `scripts/render.ps1` で指定しています。Pythonは `CPO_PYTHON` 環境変数、既存のCodex同梱Python、PATH上のPythonの順に探します。必要なライブラリは `scripts/requirements-media.txt`。このPCでは既存のライブラリを利用し、追加インストールせず確認済みです。

個別に描画と動画生成を行う例（02_render内のPowerShell）:

```powershell
./scripts/render.ps1 -Action final -Profile desktop -Job junction
```

CPU・NVENC比較や過去の1枚比較は `output/` 内の各比較フォルダーに保持しています。静止画比較と短いエンコード検証は実施済みですが、全編の描画・動画の見た目確認は別途必要です。

## 接続シーンを作り直す場合

`scripts/build_junction.py`は本編の0フレームを基に、固定した交差点と車の経路の候補を `output/junction-work-v4/CPO_JUNCTION_CANDIDATE.blend` に作ります。候補を確認してからMASTERへ反映してください。
`scripts/render_junction.py`、`encode_junction.py`、`validate_junction_media.py`は確認用動画の作成・照合用です。動画変換に必要なPythonライブラリは `scripts/requirements-media.txt` に記載しています。
現在のRENDER.cmdは動画エンコーダーを事前確認するため、Pythonの追加ライブラリも必要です。

確認用の候補や画質を変更して作り直すときは、以前の `output/junction-work-v4` を保管してから候補を生成してください。プレビュー描画・変換は元ファイルの照合情報を確認し、異なる条件のフレームが混ざる場合は停止します。

走行区間は、到着先と同じ建材・店舗・ホテル・段状の建物を、道路へ向けた160mの街区です。
scripts/junction_frontage.pyで配置し、入口や窓の寸法を保つため建物の縦横比は変更していません。
確認動画は横640×360・縦360×640、Cycles 16 samplesです。encode_junction.pyはoutput/junction-work-v4/mediaへ仮出力します。validate_junction_media.py --stagedで確認してからサイトへ反映します。
review_junction.pyはサイトに組み込んだ動画から「3周＋右折」を作成します。

静止画の確認: render_junction.py -- review（横・縦各4枚、960×540／540×960、64 samples）。境界の確認: -- seam（境界前後の6枚ずつ）。サイト用のテスト品質動画は -- preview で描画し、今回の横・縦の描画は完了しています。
モデルの確認画像は reports/streetscape-frontage.png、streetscape-depth.png、streetscape-overview.png です。junction-streetscape-review.json に確認段階と元ファイルの照合情報を記録しています。
動画を更新する際は4本のMP4と2枚のポスター、junction-media-manifest.jsonをそろえて反映します。現行サイトはDRIVE_SECONDS=20、DRIVE_FPS・TURN_FPS=30です。差し替え時はJUNCTION_MEDIA_VERSIONも更新して操作確認を行ってください。

今回の追加修正: 新しい広告8種類、大小24面の追加広告、カフェ・ホテル・オフィス・ガレージ・閉店中の店舗・奥まったロビーの6種類の1階、街路樹8本、駐車区画の車1台、バス停と街路設備を配置しました。左車線の走行と路面表示を整え、古い地面による路面の遮蔽を除去しました。
サイト側は、冒頭へ戻った際にスクロール用のシークを解除し、動画全体のループ再生へ戻す処理を修正しました。23件のテストと横・縦画面で復帰を確認済みです。CGの更新はMASTER・確認画像・サイトのテスト品質動画に反映済みです。

短い動きの確認は `render_junction.py -- short desktop` → `encode_streetlife_review.py`。reports/streetlife-short.mp4は元240〜329フレームの3秒、streetlife-loop-boundary.mp4は570〜599→0〜29の2秒です。30fpsを保ち、補間や速度変更は行いません。この2本は部分確認用で、サイト用の全編素材ではありません。

`validate_junction_media.py --staged desktop`は横のみを検証し、候補出力先に結果を保存します。`--staged`だけで両方を検証し、元シーンと4本の動画のSHA-256を含む検証記録をreportsへ保存します。
