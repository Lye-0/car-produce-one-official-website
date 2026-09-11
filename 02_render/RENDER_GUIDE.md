# 映像の制作とサイトへの反映

## 使用するファイル

| ファイル | 役割 |
|---|---|
| [scene/CPO_MASTER.blend](scene/CPO_MASTER.blend) | Blender原本 |
| [settings.json](settings.json) | 解像度・描画品質・PNG出力名 |
| [encoding.json](encoding.json) | 動画形式・品質・動画出力名 |
| [scripts/render.ps1](scripts/render.ps1) | 操作メニューと実行環境 |
| [scripts/render.py](scripts/render.py) | PNG描画 |
| [scripts/package_media.py](scripts/package_media.py) | 動画生成・検証・サイト反映 |
| [scripts/site_media_layout.py](scripts/site_media_layout.py) | 配信用ファイルとマニフェストの配置 |

原本は[OPEN_BLENDER.cmd](../OPEN_BLENDER.cmd)で開けます。動画用のカメラとフレーム対応はスクリプトが設定するため、生成には[RENDER.cmd](../RENDER.cmd)を使用します。

## 実行環境

Blender 5.2、OptiX対応GPU、NVENC対応ドライバー、Pythonを使用します。Blenderの実行パスは `scripts/render.ps1` で設定します。

Pythonを指定する場合は、このフォルダで次を実行します。

```powershell
$env:CPO_PYTHON = (Get-Command python).Source
& $env:CPO_PYTHON -m pip install -r ./scripts/requirements-media.txt
```

ランチャーは `CPO_PYTHON`、同梱ランタイム、PATHの順にPythonを選択します。

## 現在の出力設定

設定の参照元は `settings.json` と `encoding.json` です。

- PCは1920×1080、スマートフォンは1080×1920、30fps。
- 元画像は16-bit RGB PNG。Cycles最大48・最小8サンプル、ノイズ閾値0.05、OptiXとOpenImageDenoiseを使用。
- 配信動画はHEVC 10-bitとH.264 8-bit。NVENC P7、HEVC CQ18／H.264 CQ17。
- 色はsRGB伝達特性、BT.709色域・YUV行列、limited range。スクロール用GOPは6、ループ用GOPは30。

| 出力 | 保存先 |
|---|---|
| PNG | `output/<run_name>/{desktop,mobile}/<job>/` |
| 動画・ポスター・検証情報 | `output/<run_name>/exports/<name>/` |
| 品質サンプル | `output/quality-<run_name>/` |

現在保存されている本番PNGは `output/final-table-approved-20w/`、検証済み動画はその配下の `exports/delivery-srgb-nvenc-02/` にあります。

## 実行する処理

`RENDER.cmd` のメニューから選択します。

| 番号 | 処理 |
|---|---|
| 1 | GPU・原本・空き容量・エンコーダーを確認 |
| 2 | 小規模な描画テスト |
| 3 | 本番品質の部分サンプルと動画を生成 |
| 4 | 全編PNGと両形式の動画を生成 |
| 5 | 完成済みPNGから両形式の動画を生成 |
| 6 | 品質サンプルから時間・容量を見積もる |
| 7 | 検証済みの全場面をローカルサイトへ反映 |
| 8 | 出力フォルダを開く |

生成時は1で環境を確認し、3で品質を確認してから4へ進みます。PNGを再利用する場合は、`encoding.json` に新しい `name` を設定して5を実行します。出力を確認後、7でサイトへ反映します。

[RERENDER_TABLE.cmd](../RERENDER_TABLE.cmd)は、全編の生成とサイトへの反映を連続して実行する入口です。

## 場面とフレーム数

| job | 内容 | 各方向の動画フレーム数 |
|---|---|---:|
| drive | 街の走行ループ | 600 |
| junction | 右折と合流 | 481 |
| route | 到着から店内・モニター前まで | 2430 |
| portal | モニターへの接近 | 271 |
| tools-idle | 工具前の待機ループ | 180 |
| magazines-idle | 雑誌前の待機ループ | 180 |
| monitor-idle | モニター前の待機ループ | 180 |

ループ検証用の `endpoint.png` を含む全PNGは8,652枚です。動画の時刻・カメラ対応は [scripts/render_contract.py](scripts/render_contract.py)で定義します。カメラやモニターの形状を変更するときは、サイト側の [portal/tracking](../01_website/src/portal/tracking)も同じシーンに合わせて更新します。

## 再開と出力名

同じ入力で再開すると、寸法・精度・CRCを確認したPNGと、ハッシュ・デコード検証に通った動画を再利用します。

- 原本・描画設定・描画スクリプトを変更した場合は、新しい `run_name` を使用します。
- エンコード設定・エンコード関連スクリプトを変更した場合は、新しい `name` を使用します。

描画の一致条件は `render-settings.json`、動画生成の一致条件は `export-settings.json` に保存されます。検証が不一致を報告した場合は、変更した層の設定と出力名を確認します。必要容量は残りの画像と、設定された予備容量を基準に計算されます。

## 保管

原本・テクスチャ・設定・制作スクリプトはGitで管理します。完成したPNGとエンコード出力は `output/` に保持します。別のPCで既存PNGから動画を生成する場合は、対応するフレームバンクと検証情報をまとめてコピーします。Python依存は `scripts/requirements-media.txt` から導入できます。

## サイトへの反映と検証

メニュー7は全14クリップの両形式を検証し、動画28本とポスター14枚をサイトへコピーします。参照情報は [src/media/manifests](../01_website/src/media/manifests)へ書き込みます。

| 内容 | 反映先 |
|---|---|
| 動画 | `01_website/public/media/videos/<profile>/<job>/<codec>.mp4` |
| ポスター | `01_website/public/media/images/posters/<profile>/<job>.webp` |
| 進行映像のマニフェスト | `journey.json` |
| 接続映像のマニフェスト | `portal-desktop.json`・`portal-mobile.json` |

反映後は `01_website` で `npm test` と `npm run build` を実行し、[サイト側の確認手順](../01_website/README.md)に沿って表示と操作を確認します。動画はGit LFS、ポスターとマニフェストは通常のGitで保存します。

制作ツールのテストは、依存を導入したPythonでこのフォルダから実行できます。

```powershell
& $env:CPO_PYTHON -m unittest discover -s ./scripts -p "test_*.py"
```

入力の一致条件を調査するときは、[プロジェクト固有の知識](../agent-knowledge/INDEX.md)も参照します。
