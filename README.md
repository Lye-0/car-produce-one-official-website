# CAR PRODUCE ONE 制作フォルダ

今後の作業場所はこのフォルダです。
`C:\Users\kawau\dev\car-produce-one-official-website`

| やりたいこと | 開くもの |
|---|---|
| サイトをローカルで確認 | `OPEN_PREVIEW.cmd` |
| 最新の3Dシーンを編集 | `OPEN_BLENDER.cmd` → `02_render/scene/CPO_MASTER.blend` |
| 最終画質でレンダリング | `RENDER.cmd`（まず 1 の確認、次に 2 のテスト） |
| レンダリングの設定・手順を見る | `02_render/RENDER_GUIDE.md` |

## フォルダの役割

- **01_website** — 現在のサイト。React + Vite。文章は `src/content.ts`、画面は `src/App.tsx`、見た目は `src/globals.css`。現在の確認用動画は `public/media/stage4`。
- **02_render** — 最新MASTER、画質設定、実行スクリプト、出力先。最終レンダリングの入口はここです。
- **03_reference** — 掲載内容メモと、提供・収集した参考写真や資料。
- **90_archive** — 過去版、旧Sitesプロジェクト、旧出力、作業途中のデータ。制作の履歴として保存。

## サイト

ChatGPT Sitesへの依存を外しました。APIキーやSitesのプロジェクト情報なしで起動・ビルドできます。
`OPEN_PREVIEW.cmd` を開き、表示されたローカルURLをブラウザーで開いてください。起動中のウィンドウは開いたままにします。終了は Ctrl+C。

別のPCでは Node.js 22.13以上を用意し、`01_website` 内で `npm ci`、`npm run dev`。配布用ファイルの生成は `npm run build`、出力先は `01_website/dist` です。新しい公開先はまだ設定していません。
旧Sitesの非公開プレビューは過去のスナップショットとして残っていますが、今後の作業・更新先には使いません。

## 現在の状態

独立サイトのビルド、15件のテスト、ブラウザーでの表示・場面切替を確認済み。依存パッケージ監査は0件。
MASTERの外部リンク切れなし。実行メニューによる横・縦各2枚の低画質テスト済み。
最終画質の全編レンダリングはまだ実行していません。サイトの動画は段階4の確認用素材です。
