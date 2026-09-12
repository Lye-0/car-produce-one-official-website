# GitHub Pagesへの公開

`.github/workflows/pages.yml` は、`main` へのpushでテスト・ビルド・公開を順に実行します。動画44本を含む `01_website/dist` を公開します。Git LFSや外部ストレージの取得処理はありません。

## 初回の設定

GitHubリポジトリの **Settings → Pages → Build and deployment → Source** を **GitHub Actions** に設定してください。APIトークンやRepository secretsの追加は不要です。ワークフローはGitHubが発行する `GITHUB_TOKEN` を使います。

ワークフローとサイトの変更を `main` に反映してpushすると公開が始まります。作業ブランチへのpushでは公開しません。手動実行は **Actions → Deploy GitHub Pages → Run workflow** で `main` を選びます。

実行結果と公開URLはActionsの実行画面と `github-pages` environmentで確認できます。

## 実行内容

1. 通常Gitのソースと動画を取得し、Node.js 24で依存をインストール。
2. GitHub Pagesの設定から公開パスを取得。
3. `npm test` と `npm run build` を実行。動画のハッシュ・形式・分割範囲・100MiB未満の容量も照合。
4. `npm run verify:pages` で公開物の総容量1GB未満、通常ファイル、HTMLからの参照先を検証。
5. 成果物をアップロードし、ビルド成功後にPagesへ公開。

公開は同時に複数実行しません。アップロードしたActions成果物の保持期間は1日です。

## 公開パス

`configure-pages` の `base_path` 出力を環境変数 `PAGES_BASE_PATH` へ渡します。リポジトリ名付きURLでは `/car-produce-one-official-website/`、独自ドメインなどのルート公開では `/` になります。リポジトリ名や独自ドメインを変更したときも、Pages設定に合わせて再ビルドすれば追従します。

ViteはHTML内のJS・CSS・faviconを変換します。アプリから指定する画像、ポスター、単一動画、分割動画には `src/media/urls.ts` で同じ公開パスを付けます。元のマニフェストには `/media/...` の正規パスを保持します。

動画の参照オブジェクトはモジュール初期化時に一度だけ変換します。getterやReactの描画中で毎回作り直すと、プレーヤーが別の素材と判断して読み直すためです。

## ローカル確認

通常の `npm run dev` と `npm run build` はルートパスを使います。リポジトリ名付きの公開を確認する場合は `01_website` で実行します。

```powershell
$env:PAGES_BASE_PATH = '/car-produce-one-official-website'
npm run build
npm run verify:pages
npm run preview
```

`http://127.0.0.1:4173/car-produce-one-official-website/` で確認できます。確認後はプレビューを終了し、`Remove-Item Env:PAGES_BASE_PATH` でこのターミナルの設定を解除します。

公開後は、PCとスマートフォンで画像・動画の表示、分割境界の往復、モニターから本文への接続、本文リンクを確認してください。
