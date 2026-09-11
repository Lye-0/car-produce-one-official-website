---
id: rm-20260911-render-provenance-layers
topic: render-pipeline
type: constraint
status: active
maturity: candidate
created: 2026-09-11
last_verified: 2026-09-11
source_commit: "11cc8bd3e0dbe0744842f3a229563d920b27667f"
related_files:
  - 02_render/scripts/render_contract.py
  - 02_render/scripts/package_media.py
  - 02_render/scripts/test_production_media.py
  - 02_render/RENDER_GUIDE.md
tags:
  - provenance
  - resume
  - encoding
supersedes: null
promoted_to: null
---

# PNGと動画出力の一致条件を分けて判断する

## Conclusion

PNGの再利用は原本・描画設定・描画スクリプトの一致で判断し、動画の再利用はさらにエンコード設定とエンコード関連ソースの一致で判断する。`package_media.py` のサイト反映処理だけを変更した場合も、ファイル全体のハッシュが動画の一致条件に含まれるため、新しいエンコード出力名が必要になる場合がある。PNGの再描画が必要かどうかは描画側の条件で別に判定する。

## Scope

Applicable:
- 再開時の一致エラー、動画パッケージ処理の改修、出力ディレクトリの変更、既存PNGからの再生成。

Do not apply:
- 原本・カメラ・描画設定の変更後に、エンコードだけを更新すれば足りるという判断。

## Evidence

- `02_render/scripts/render_contract.py`: `fingerprint` はMASTER・RENDER_KEYS・render.py・render_contract.pyを扱う。
- `02_render/scripts/package_media.py`: `package` の `export_stamp` は描画側の指紋に加え、encoding設定とmedia_encoding.py／media_runtime.py／package_media.pyのハッシュを含む。
- `02_render/scripts/test_production_media.py`: 入力変更による再利用条件と、一方の形式だけを再生成する条件を検証する。
- `02_render/RENDER_GUIDE.md`: 「再開と出力名」が運用手順を定義する。

## Verification

1. `render-settings.json` と `export-settings.json` のどちらの一致判定で停止したか確認する。
2. 現在の `fingerprint`、encoding設定、エンコード関連ソースのハッシュを対応する記録と照合する。
3. 変更した層に合わせて `run_name` または `name` を設定し、記録の照合を保ったまま処理を再実行する。
