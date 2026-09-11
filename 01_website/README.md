# Webサイトの開発

React + Viteで構成した店舗サイトです。掲載内容の編集、ブラウザーでの確認、配信用ビルドをこのフォルダで行います。

## 起動

Node.js 24とGit LFSを使用します。リポジトリを取得したら、ルートで次を実行します。

```powershell
git lfs install --local
git lfs pull
cd 01_website
npm ci
npm run dev
```

[開発用URL](http://127.0.0.1:5173/)を開きます。起動済みのサーバーはそのまま利用でき、終了は起動したターミナルで `Ctrl+C` です。[OPEN_PREVIEW.cmd](../OPEN_PREVIEW.cmd)からも起動できます。

## 編集する場所

| 対象 | ファイル・フォルダ |
|---|---|
| 掲載文章・サービス・連絡先 | [src/content.ts](src/content.ts) |
| ページ全体の組み立て | [src/App.tsx](src/App.tsx) |
| ヘッダー・ヒーロー・本文 | [src/components](src/components) |
| 映像の表示とスクロール制御 | [src/journey](src/journey) |
| モニターからサイトへの接続 | [src/portal](src/portal) |
| 動画の読み込み・形式選択 | [src/media](src/media) |
| スタイル | [src/styles](src/styles) |
| 動画の参照先と検証情報 | [src/media/manifests](src/media/manifests) |

掲載情報の確認には[参考資料](../03_reference/README.md)を使用します。

## 映像と画面の接続

映像の進行はスクロール位置に対応します。モニター内と通常サイトは同じ `MainHero` 要素を使い、提示された動画フレームと、そのフレームに対応する画面の投影を一緒に更新します。終端では通常のページ配置へ戻ります。

スマートフォンでは中央のヒーローに左右の背景画像を添え、接近に合わせて左右が画面外へ抜けます。ヒーローや投影の変更時は、往復スクロールと表示領域の高さ変更を合わせて確認します。

## 素材の管理

| 素材 | 配置・管理 |
|---|---|
| 配信動画28本 | `public/media/videos/{desktop,mobile}/{場面}/{hevc,h264}.mp4`・Git LFS |
| ポスター・写真・QR | [public/media/images](public/media/images)・通常のGit |
| 参照先・フレーム数・SHA-256 | [src/media/manifests](src/media/manifests)・通常のGit |
| レンダリング元画像 | `02_render/output/`・ローカル保管 |
| 依存とビルド出力 | `node_modules/`・`dist/`・各PCで再生成 |

動画は7場面×2方向×2形式です。更新時は動画本体、対応するマニフェスト、ポスターを一組としてそろえます。新しい動画パスを追加するときは、[.gitattributes](../.gitattributes)と[.gitignore](../.gitignore)の対象一覧も更新します。コミット前には `git lfs status` で動画がLFS対象になっていることを確認します。

動画の生成とサイトへの反映は[制作ガイド](../02_render/RENDER_GUIDE.md)を参照してください。

## 検証とビルド

このフォルダで実行します。

```powershell
npm test
npm run build
npm run preview
```

`npm run build` は配信素材のハッシュ・形式・追跡データを照合し、型チェック後に `dist` を生成します。`public/media` にマニフェスト未登録の動画がある場合も検出します。ビルド結果は[確認用URL](http://127.0.0.1:4173/)で開けます。

ブラウザーでは、各場面への移動、通常・高速・逆方向のスクロール、途中停止、モニターへの進入と退出、メニューと本文リンクを確認します。スマートフォンはタッチ操作・縦横切り替え・ブラウザーの上下バーによる高さ変更も対象です。

接続の終端比較には、開発サーバー上の[PC用比較画面](http://127.0.0.1:5173/tests/monitor-portal-fixture.html)と[スマホ用比較画面](http://127.0.0.1:5173/tests/monitor-portal-fixture.html?profile=mobile)を使用できます。開発者コンソールで `window.portalFixture.ready` が `true` になったら、`window.portalFixture.setNative(true)` で通常配置へ切り替えて比較します。

映像接続や再生成の調査では、[プロジェクト固有の知識](../agent-knowledge/INDEX.md)から関連する項目を参照します。
