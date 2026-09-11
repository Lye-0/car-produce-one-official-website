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

ソース・設定・掲載資料・静止画は通常のGit、サイトで使う本番動画28本はGit LFSで管理します。`.gitattributes` と `.gitignore` は現在の配信マニフェストにある動画・ポスターのみを対象にします。動画はLFSポインター、ポスター20枚は通常のGitへ保存します。

以下はGit／LFSの対象外です。

- `02_render/output/`: レンダリング元の連番画像、中間出力、エンコード出力
- `01_website/public/media/production/` 内の書き出し用JSONなど、対象一覧にないファイル
- `02_render/.python_vendor/`、`01_website/node_modules/`、`01_website/dist/`: 依存とビルド出力

別のPCではGit LFSを導入し、`git lfs install`、clone後に必要なら `git lfs pull` を実行してください。その後 `01_website` で `npm ci`、`npm run build` を実行すると動画本体も照合できます。LFSポインターだけの状態では素材検証が失敗します。

新しい配信版を追加する場合は、対応するマニフェストを更新し、動画の正確なパスを `.gitattributes` のLFS対象へ追加してください。動画と必要なポスターのパスを `.gitignore` の許可一覧にも追加し、`git add`、`git lfs status`、`npm run build` で確認します。レンダリング出力を `git add -f` で追加しないでください。

LFSは保管・履歴管理用です。公開時の動画配信にはR2を使用する予定で、R2へのアップロードとデプロイ設定は別途行います。

## 整理方針

現在使用する配信版・最終元画像・最新MASTERを保持します。旧プロジェクト、旧試作レンダリング、旧配信版は削除しました。最終元画像は再生成に時間がかかり、今後のPC版接続の検証にも使うため保持しています。


## 旧動画の整理（2026-09-11）

旧確認用動画16本、旧モニター合成動画12本、旧エンコード出力 `delivery-nvenc-01` を削除しました。現在の配信動画は28本です。使用中のポスター・画像・最終16-bit元画像・最新エンコード出力・Blender原本・提供資料は保持しています。

`npm run build` は現行28動画をSHA-256で検証し、public/mediaに未参照の動画があれば停止します。旧動画を誤って再配置して配布することを防ぎます。distも作り直して旧動画を除きました。
