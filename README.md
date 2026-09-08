# CAR PRODUCE ONE — 制作準備

2026-09-08時点。3D制作データの移管とBlender作業ファイルの準備まで完了。公式サイト本体はまだ実装していません。

## 開くもの

- `OPEN_BLENDER.cmd`：Blender 5.2で `assets/blender/CPO_v13_working.blend` を開く。
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
  videos/             ユーザー撮影の参考サイト動画2本
docs/                 方針と検証記録
tools/                Blender変換・再検証、プレビュー起動の補助
work/                 確認レンダー・ログなどの一時データ（Git対象外）
```

`assets/source/v13` は相対パスを含めて保持しています。原本を編集する代わりに、Blenderでの制作は `assets/blender` で続けます。Downloads側の元ファイルは残しています。

Blenderのシーンは `CPO_v13_ANIMATED`、カメラは `CPO_CINEMATIC_CAMERA`、主アニメーションは `CPO_MASTER_90s`。30fps、0〜2700フレームです。停止区間や場面の区切りはタイムラインのマーカーから確認できます。

Gitのコミット・push・公開は行っていません。大型の3Dデータと参考メディアも現時点ではローカルファイルです。Git LFSや配信用素材の管理方式は未設定です。
