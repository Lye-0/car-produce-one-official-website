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

- **01_website** — 現在のサイト。React + Vite。文章は `src/content.ts`、画面は `src/App.tsx`、見た目は `src/globals.css`。現在の確認用動画は `public/media/junction` と `public/media/stage4`。
- **02_render** — 最新MASTER、画質設定、実行スクリプト、出力先。最終レンダリングの入口はここです。
- **03_reference** — 掲載内容メモと、提供・収集した参考写真や資料。
- **90_archive** — 過去版、旧Sitesプロジェクト、旧出力、作業途中のデータ。制作の履歴として保存。

## サイト

ChatGPT Sitesへの依存を外しました。APIキーやSitesのプロジェクト情報なしで起動・ビルドできます。
`OPEN_PREVIEW.cmd` を開き、表示されたローカルURLをブラウザーで開いてください。起動中のウィンドウは開いたままにします。終了は Ctrl+C。

別のPCでは Node.js 22.13以上を用意し、`01_website` 内で `npm ci`、`npm run dev`。配布用ファイルの生成は `npm run build`、出力先は `01_website/dist` です。新しい公開先はまだ設定していません。
旧Sitesの非公開プレビューは過去のスナップショットとして残っていますが、今後の作業・更新先には使いません。

## 現在の状態

第5段階のサイト本体を実装済み。6サービスの説明、店舗紹介、アクセス、電話・LINE・QRの相談導線を整えました。横画面と390px・320pxの縦画面で操作を確認済みです。詳細は `01_website/README.md`。ビルドと21件のテストも成功しています。
MASTERの外部リンク切れなし。実行メニューによる横・縦の代表フレームの低画質テスト済み。
最終画質の全編レンダリングはまだ実行していません。サイトの動画は既存の確認用素材です。新しい街並みの動画への差し替えは、まだ行っていません。

現在の接続は、固定した交差点を車と車載カメラが右折する構成です。CPO_MASTER.blendに走行・右折シーンを含め、RENDER.cmdの最終描画へ反映しています。詳細は01_website/README.mdと02_render/RENDER_GUIDE.mdをご覧ください。

最新MASTERは20秒・160mの街並みループです。道路に向いた店舗・ホテル・中層建築に、下層部の壁・柱・基礎、大小の広告、背後の建物を追加しました。現在は静止画の確認段階で、長い動画描画は停止しています。ループと右折の経路は確認済みの版と同じです。確認画像は02_render/reports/streetscape-*.pngです。
