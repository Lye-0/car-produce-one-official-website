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

`encoding.json` の `backend` は **nvenc**。H.265は `hevc_nvenc` のMain10・10bit、H.264は `h264_nvenc` のHigh・8bitです。両方とも1080p・30fps。原画のsRGB伝達特性を維持し、BT.709の色域・YUV行列とlimited rangeで保存します。色メタデータはprimaries=1 / transfer=13（IEC 61966-2-1）/ matrix=1 / range=1です。

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

## 2026-09-10: ガラス天板の黒つぶれ修正後の再描画

原因は、屈折コースティクス無効の描画設定で、透明な天板が雑誌への直射光を遮っていたこと。現在は `CPO_V18_SITE_MAIN` の `F05.Table.UpperGlass` にオブジェクト専用の材質を割り当て、シャドウレイだけを暖色の部分透過（線形RGB 0.72 / 0.676 / 0.615）へ分岐する。visible_shadow は True。ガラスのカメラ表示・反射・透過、木目や雑誌、照明、カメラ、車の修正は保持する。これは薄い透明板の影を弱める近似で、物理的な集光模様を計算するものではない。可視ガラス用の元シェーダーは保持し、共有材質や街側の複製には変更を加えない。

旧原本は `output/table-glass-fix-01/CPO_MASTER_before_table_fix.blend` に保存。修正根拠と原本SHA-256は `reports/table-glass-fix.json`。横・縦の雑誌停止場面と本編1950フレームを48 samples / OptiXで静止画確認済み。

`prepare_table_rerender.py` は専用のハッシュ検証付き移行処理。影響のない `CPO_JUNCTION_DRIVE` の drive / junction のみ、PNG整合性を検証して新しい出力先へコピーした。古い連番は保持し、室内連番は流用しない。現在の出力先は `final-table-approved-20w`。先の明るい修正版 `final-table-glass-fixed-01` は保管し、新しい連番には混ぜない。

- 再利用: drive 0–599＋endpoint、junction 0–480（元シーン600–1080）。横・縦計2,164枚。
- 再描画: route 0–2429（最終PNGは元2430）、portal 0–270（元2430–2700）、tools-idle / magazines-idle / monitor-idle 各0–179＋endpoint。横・縦計6,488枚。
- 影響は天板下だけでなく間接光・反射にも及ぶため、机が大きく映るフレームだけを差し替えず、本編シーンに属する5種類の動画を更新する。
- 既存の走行・右折の動画もコピー済み。エンコーダーはPNGハッシュと動画検証に合格した場合だけ再利用する。

**プロジェクト直下の `RERENDER_TABLE.cmd` を実行する。** 正常な走行・右折PNGをスキップして室内を再描画し、HEVC/H.264へ変換、全14クリップの検証後にローカルサイトへ反映する。途中停止時は同じファイルで再開可能。実行中のサイトは以前の動画を表示し、完成後にまとめて切り替わる。

通常メニューなら `RENDER.cmd` の4（描画＋変換）、完了後7（サイト反映）でも同じ結果。BlenderのCtrl+F12では独自の動画区分・停止ループを生成できない。

前回の実測は対象6,488枚で約6.24時間。今回の所要時間を保証する値ではなく、GPU負荷・材質処理・動画変換で増減する。走行と右折の再利用で、前回実績相当の約3時間分の描画を省ける。

### 工具台の雰囲気に合わせた最終調整

机のガラスを通る光だけを少し弱く、暖かく調整した。照明・露出・工具台の材質・サイトのグラデーションは保持。机中央の確認領域の平均画素値は前の修正版の約78%。工具台の1026フレームは元の完成画像と比較して平均RGB差0.43/255以下（8bit確認画像と16bit原画の比較を含む）で、横・縦の机と工具台を目視確認済み。

最新の確認画像は `output/table-glass-tone-02/warm-desktop-route.png`、`warm-mobile-magazines.png`、`warm-desktop-tools.png`。原本変更スクリプトは `scripts/refine_table_tone.py`（一度だけ実行するSHA-256ガード付き移行）。通常の再描画は引き続き `RERENDER_TABLE.cmd` を実行する。再描画対象6,488枚・走行/右折再利用2,164枚の区分は同じ。


### 追加の明るさ調整（tone-03）

ユーザー指定により机をもう一段暗くした。シャドウ透過値のみ0.72 / 0.676 / 0.615へ変更し、暖色の比率を保持。横・縦48 samples静止画で確認済み。上のtone-02の比較数値は旧版の検証記録であり、最新版の計測値ではない。最新画像は `output/table-glass-tone-03/tone03-desktop.png` と `tone03-mobile.png`。再描画は同じ `RERENDER_TABLE.cmd` を使用する。


### 承認済み20 W版・レンダリング準備完了

現在の原本は V14 Magazine raking key = 20 W、机のシャドウ透過RGB = 0.72 / 0.676 / 0.615。1950フレームと1230・1400・2390フレームを確認し、サイトと同じ暗いCSSグラデーションを重ねた机の見え方が承認済み。確認原本と画像は `output/approved-table-20w/` に保存。

新しい連番先は `final-table-approved-20w`。走行と右折のシーンは11,645オブジェクトの基本属性と12カメラサンプルを旧原本と比較し一致。描画済み2,164枚を再利用し、室内側6,488枚を再描画する。同じ `RERENDER_TABLE.cmd` で描画・動画変換・完成後のローカルサイト反映まで実行する。準備中には長時間レンダリングを開始しない。原本をさらに保存変更した場合は、再び出力先と再利用範囲の検証が必要。

## 静止画プレビューと動画の暗さを揃える色変換

`delivery-srgb-nvenc-02` から、16bit PNGのsRGB画素値を保持して動画化する。以前のsRGB→BT.709 OETF変換では、ブラウザーで動画が静止画より暗く見えた。sRGB伝達特性を明示したHEVC/H.264の比較動画では、同じPNG・WebPに近い明るさになることを確認した。CSSによる一律の明るさ補正は使わない。

`media_encoding.py` の書き込みフレームとストリームの両方にtransfer=13を指定する。`verify()`は全動画の色メタデータ・フレーム数・精度・キーフレーム間隔を検証する。テストは実エンコード後のsRGB値と元画像を直接比較し、逆ガンマ変換で問題を打ち消す検証をしない。

色変換だけの変更なので、原本と完成PNGは保持し、`render.ps1 -Action encode -Profile both -Job all` で全動画を新しいencoding.nameへ生成する。全クリップの検証後に `-Action install` でサイトへまとめて反映する。旧版は保存される。
