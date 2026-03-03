# slide-usual-ppt スキルセットアップ完了

## ✅ インストール完了

PowerPoint 自動生成スキル `slide-usual-ppt` がセットアップされました！

### インストール場所
```
~/.claude/skills/slide-usual-ppt/
├── SKILL.md                          # スキル定義
├── config.json                       # 設定（色、フォント）
├── scripts/
│   ├── slides_markdown.py            # Markdownパーサー
│   └── slide_generator_pptx.py       # PPTX生成エンジン
├── references/
│   ├── workflow.md                   # ワークフロー
│   ├── layout-selection-guide.md     # レイアウト選択ガイド
│   ├── layout-rules.md               # レイアウト詳細ルール
│   ├── character-limits.md           # 文字数制限
│   └── shape-helpers.md              # 拡張図解機能
└── assets/
    └── README.md                     # 画像・テンプレート説明
```

---

## 🚀 使い方

### 1. 入力資料を準備

`input/` フォルダに以下を配置：
```
input/
├── brief.md          # プレゼンの目的・ターゲット
└── content.md        # プレゼンの内容
```

### 2. スキルを実行

#### 方法A: Claude Code コマンド
```bash
claude-code slide-usual-ppt
```

#### 方法B: Python スクリプト直接実行
```bash
cd ~/.claude/skills/slide-usual-ppt/scripts
python slide_generator_pptx.py \
  --markdown-file /path/to/output/slides.md \
  --config ../config.json \
  --title "プレゼンタイトル" \
  --output-dir /path/to/output
```

### 3. 出力ファイルを確認

```
output/
├── slides.md                    # スライド構造（Markdown形式）
└── プレゼンタイトル.pptx        # PowerPointファイル
```

---

## 📝 マークダウン記法

スキルが自動生成する `slides.md` は以下の形式です：

### レイアウト指定
```markdown
<!-- layout: レイアウト名 -->
## スライドタイトル
### キーメッセージ
- ポイント1
- ポイント2
```

### 15 レイアウトパターン
| # | レイアウト | 用途 |
|---|-----------|------|
| 1 | title | 表紙（紺色背景） |
| 2 | section | セクション区切り |
| 3 | toc | 目次・サマリー |
| 4 | bullet_points | 箇条書き（デフォルト） |
| 5 | numbered_list | 手順・ステップ |
| 6 | two_column | 2つの対比 |
| 7 | three_column | 3つの並列 |
| 8 | four_column | 4つの並列 |
| 9 | metrics | 数値・KPI |
| 10 | quote | 引用 |
| 11 | faq | Q&A |
| 12 | comparison_table | 比較表 |
| 13 | image_with_text | 画像＋テキスト |
| 14 | chart | グラフ |
| 15 | cta | 行動喚起 |

詳細は `~/.claude/skills/slide-usual-ppt/references/layout-selection-guide.md` を参照

---

## ⚙️ カスタマイズ

### カラーパレットの変更
```json
{
  "palette": {
    "primary": "#1E3A5F",     // 紺色（表紙、タイトル背景）
    "secondary": "#4A6FA5",   // 青
    "accent": "#3AA899",      // 緑（強調色）
    "gray": "#999999",        // グレー
    "text": {
      "primary": "#333333",   // 黒（本文）
      "secondary": "#666666", // グレー（補足）
      "light": "#FFFFFF"      // 白（暗い背景上）
    },
    "background": {
      "primary": "#FFFFFF",      // 白
      "secondary": "#F5F5F5",    // 薄グレー
      "dark": "#1E3A5F"          // 紺色
    }
  }
}
```

`config.json` を編集して変更：
```bash
nano ~/.claude/skills/slide-usual-ppt/config.json
```

### フォントの変更
```json
{
  "font": {
    "family": "Arial"  // または "Times New Roman", "Segoe UI" など
  }
}
```

### テンプレートの使用
```bash
# テンプレート.pptxを配置
cp my-template.pptx ~/.claude/skills/slide-usual-ppt/assets/template.pptx

# config.jsonで指定
{
  "template": {
    "pptx_path": "assets/template.pptx"
  }
}
```

---

## 📊 実装例

### 営業提案プレゼン（10分）

```markdown
<!-- layout: title -->
## 2025年度事業計画
### 売上3倍化と顧客満足度向上を実現
---
# 背景・課題
---
<!-- layout: bullet_points -->
## 市場の変化
### デジタル化が加速する中での競争激化
- クラウド化による競争加速
- 顧客ニーズの多様化
- 既存ビジネスモデルの限界
---
<!-- layout: metrics -->
## 市場規模
### 急速に拡大している
- **2.5倍** 市場成長率
- **150億円** 潜在市場規模
---
# ソリューション
---
<!-- layout: three_column -->
## 当社の3つの強み
### 他社にない競争力を有する
#### 技術力
業界トップの
R&D投資
#### 営業力
顧客数300社
のネットワーク
#### 価格競争力
10%低価格
での提供
---
<!-- layout: numbered_list -->
## 導入ステップ
### 3ステップで実現
1. **ヒアリング**
   課題・要望を詳細に把握
2. **カスタマイズ**
   最適なソリューション構築
3. **運用開始**
   スタッフ教育と並行実施
---
<!-- layout: cta -->
## 今すぐ導入を開始
### 無料トライアルで効果を実感
[お申し込みはこちら]
```

---

## 🔍 トラブルシューティング

### PowerPoint 生成に失敗
**症状**: `ERROR: Invalid markdown format`

**原因**: slides.md の形式が不正

**解決策**:
1. `---` でスライド区切りが正しいか確認
2. `<!-- layout: xxx -->` の位置を確認
3. Markdown 構文エラーがないか確認

```bash
# マークダウンをバリデーション
python ~/.claude/skills/slide-usual-ppt/scripts/slides_markdown.py output/slides.md
```

### テキストが文字数超過
**症状**: PowerPoint でテキストが見切れている

**解決策**:
- `character-limits.md` の上限を確認
- テキストを要約（数値を活用、不要な装飾を削除）
- スライドを分割

### 画像が表示されない
**症状**: 画像が黒いボックスになっている

**解決策**:
1. 画像パスが正しいか確認
   ```markdown
   ![alt](../assets/my-image.png)  ← 相対パス
   ```
2. ファイルが存在するか確認
3. 形式が PNG/JPG/GIF か確認

### フォントが文字化け
**症状**: 日本語が□□□になっている

**解決策**:
```json
{
  "font": {
    "family": "Meiryo UI"  // 日本語対応フォント
  }
}
```

推奨フォント：
- Meiryo UI（Windows）
- Hiragino Sans（macOS）
- Noto Sans JP（Linux）

---

## 📚 関連ドキュメント

- `~/.claude/skills/slide-usual-ppt/SKILL.md` - スキル定義
- `~/.claude/skills/slide-usual-ppt/references/workflow.md` - 詳細フロー
- `~/.claude/skills/slide-usual-ppt/references/layout-selection-guide.md` - レイアウト選択ガイド
- `~/.claude/skills/slide-usual-ppt/references/layout-rules.md` - 各レイアウト詳細ルール
- `~/.claude/skills/slide-usual-ppt/references/character-limits.md` - 文字数制限表

---

## 🎯 次のステップ

1. **サンプルプレゼンを作成**
   ```bash
   # input/ フォルダに資料を配置
   mkdir -p input output
   echo "プレゼンの目的を記入" > input/brief.md
   ```

2. **スキルを実行**
   ```bash
   claude-code slide-usual-ppt
   ```

3. **PowerPoint を確認**
   ```bash
   open output/*.pptx
   ```

4. **カスタマイズ**
   - config.json で色・フォント・テンプレートを調整
   - slides.md を編集して微調整

---

## 📞 サポート

問題が発生した場合：
1. `~/.claude/skills/slide-usual-ppt/references/` のドキュメントを参照
2. スクリプトのエラーメッセージを確認
3. Markdown 形式をバリデーション

---

**スキル実装完了日**: 2026-03-02
