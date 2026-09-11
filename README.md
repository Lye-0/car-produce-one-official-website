# CAR PRODUCE ONE 制作フォルダ

## 現在の構成

| フォルダ | 内容 |
|---|---|
| `01_website` | React + Viteのサイト、配信素材、検証ツール |
| `02_render` | 最新Blender MASTER、レンダリング・合成スクリプト、最終元画像 |
| `03_reference` | 掲載内容の根拠と提供された参考資料 |

- サイトの確認: `OPEN_PREVIEW.cmd`
- 3Dシーンの編集: `OPEN_BLENDER.cmd` → `02_render/scene/CPO_MASTER.blend`
- レンダリング: `RENDER.cmd`。操作は `02_render/RENDER_GUIDE.md` を参照。
- サイトの文章・連絡先: `01_website/src/content.ts`
- 映像・サイト接続: `01_website/src/App.tsx`、`DesktopPortal.tsx`、`PortalHandoff.tsx`

本番映像は横1920×1080・縦1080×1920、30fps。配信版は `01_website/src/production-media.json` で指定します。サイトと映像の詳細は `01_website/README.md` にあります。

## 起動・検証

Node.js 22.13以上を使用し、`01_website` 内で `npm ci`、`npm run dev` を実行します。`npm test` でテスト、`npm run build` で素材検証・型検査・配布用ビルドを行います。公開先はまだ設定していません。

## 大容量データとGit管理

Gitではソース・設定・最新Blender MASTER・掲載資料を管理します。以下はローカルに保持する生成物・依存で、Gitへ追加しません。

- `01_website/public/media/production/`: 現在使う本番配信動画
- `02_render/output/final-table-approved-20w/`: 再合成・再エンコード用の最終16-bit元画像
- `02_render/.python_vendor/`: このPCの動画処理ライブラリ
- `01_website/node_modules/`、`01_website/dist/`: 再生成できる依存とビルド出力

別のPCで本番動画を使う場合は、`01_website/src/production-media.json` の `version` と一致する配信フォルダと、PC用 `01_website/public/media/production/desktop-live-screen-05/` とスマホ用 `01_website/public/media/production/mobile-live-screen-06/` をコピーしてから起動・ビルドしてください。再合成には最終元画像も必要です。Python依存は `02_render/scripts/requirements-media.txt` から導入できます。

生成済み素材を `git add -f` で追加しないでください。大きな動画は通常のGit履歴へ入れるとプッシュを妨げます。

## 整理方針

現在使用する配信版・最終元画像・最新MASTERを保持します。旧プロジェクト、旧試作レンダリング、旧配信版は削除しました。最終元画像は再生成に時間がかかり、今後のPC版接続の検証にも使うため保持しています。


## 旧動画の整理（2026-09-11）

旧確認用動画16本、旧モニター合成動画12本、旧エンコード出力 `delivery-nvenc-01` を削除しました。現在の配信動画は28本です。使用中のポスター・画像・最終16-bit元画像・最新エンコード出力・Blender原本・提供資料は保持しています。

`npm run build` は現行28動画をSHA-256で検証し、public/mediaに未参照の動画があれば停止します。旧動画を誤って再配置して配布することを防ぎます。distも作り直して旧動画を除きました。
