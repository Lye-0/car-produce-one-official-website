# CAR PRODUCE ONE 制作フォルダ


## DEPLOYMENT



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

サイトと映像の詳細は `01_website/README.md` にあります。
