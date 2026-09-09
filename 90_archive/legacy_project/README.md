# CAR PRODUCE ONE — 制作準備

最新はv17です。2323フレーム付近で視線が逆方向へ戻る動きを解消し、広告16種類の配色配置を組み直しました。詳細は docs/v17-refinement.md。OPEN_PREVIEW.cmd は旧v13の確認サイトです。公式サイト本体はまだ実装していません。

## 開くもの

- `OPEN_BLENDER.cmd`：Blender 5.2で `assets/blender/CPO_v17_refined.blend` を開く。
- `OPEN_PREVIEW.cmd`：引き継いだ動線確認サイトをローカルで起動する。これは公式サイト本体ではありません。
- `docs/design-brief.md`：現在の希望、参考動画、検討を残した事項。
- `docs/preparation.md`：保存・検証結果と今後の扱い。

## 配置

```text
assets/
  source/v13/          ChatGPT納品パッケージ42ファイルの原本コピー
  blender/            編集していくBlenderファイル
references/
  photos/             店舗・間取り・車・構図の参照12枚
  videos/             参考サイト動画2本とv15の都市・車両参考動画6本
docs/                 方針と検証記録
tools/                Blender変換・再検証、プレビュー起動の補助
work/                 確認レンダー・ログなどの一時データ（Git対象外）
```

`assets/source/v13` は相対パスを含めて保持しています。原本を編集する代わりに、Blenderでの制作は `assets/blender` で続けます。Downloads側の元ファイルは残しています。

Blenderのメインシーンは `CPO_V17_MAIN`、カメラは `CPO_CINEMATIC_CAMERA`。30fps、0〜2700フレームです。停止区間や場面の区切りはタイムラインのマーカーから確認できます。

変更はローカルGitで管理しています。push・公開は行っていません。大型の3Dデータと参考メディアも現時点ではローカルファイルです。Git LFSや配信用素材の管理方式は未設定です。