# メルカリ自動運営ツール / Mercari Auto Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

メルカリの出品・価格管理・メッセージ対応を自動化するデスクトップツールです。  
支持中日英三语言，跨平台运行 (Windows / macOS)。

## 機能

### 1. 批量上架（一括出品）
- CSV ファイルから商品を一括インポート
- タイトル・説明文の自動最適化（テンプレートエンジン）
- カテゴリ自動推薦
- 画像の自動アップロード
- 出品キューで順次自動出品

### 2. 自动调价（自動価格調整）
- 売れ残り日数に応じた自動値下げ
  - 1日: -3%
  - 3日: -5%
  - 7日: -10%
- 最低価格保護
- 価格変更履歴の記録

### 3. 自动回复（自動返信）
- キーワードマッチングによる自動コメント返信
- カスタマイズ可能な返信ルール
- 返信履歴の記録

## 環境構築

### 必要条件
- Python 3.11 以上
- Windows 10/11 または macOS

### インストール

```bash
# リポジトリをクローン/ダウンロード後
cd merukari

# 仮想環境を作成（推奨）
python -m venv venv

# 仮想環境を有効化
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 依存パッケージをインストール
pip install -r requirements.txt

# Playwright ブラウザをインストール
playwright install chromium
```

## 使い方

### 起動

```bash
python main.py
```

### 基本的な流れ

1. **ブラウザ起動**: 左メニュー下部の「启动浏览器」をクリック
2. **ログイン**: ブラウザが開いたら、手動でメルカリにログイン
3. **機能を選択**:
   - 「批量上架」: CSV をインポートして一括出品
   - 「自动调价」: 売れ残り商品の価格を自動調整
   - 「自动回复」: 購入者からのコメントに自動返信

### CSV フォーマット

`templates/sample_products.csv` を参考にしてください：

| カラム | 説明 | 例 |
|--------|------|-----|
| title | 商品タイトル | NIKE スニーカー 27cm |
| description | 説明文（空欄時は自動生成） | |
| category | カテゴリ（空欄時は自動推薦） | |
| price | 価格（円） | 3500 |
| condition | 商品の状態 | 目立った傷や汚れなし |
| images | 画像パス（セミコロン区切り） | img1.jpg;img2.jpg |
| notes | 備考（説明文に反映） | 数回着用のみ |

## 設定

`config.yaml` で各種設定を変更できます。アプリの「设置」画面からも変更可能です。

## プロジェクト構成

```
merukari/
├── main.py                  # エントリーポイント
├── config.yaml              # 設定ファイル
├── requirements.txt         # 依存パッケージ
├── src/
│   ├── automation/          # ブラウザ自動化
│   │   ├── browser_manager.py
│   │   ├── mercari_operations.py
│   │   └── scheduler.py
│   ├── core/                # ビジネスロジック
│   │   ├── listing_engine.py
│   │   ├── pricing_engine.py
│   │   ├── reply_engine.py
│   │   └── template_engine.py
│   ├── data/                # データ層
│   │   └── database.py
│   ├── gui/                 # GUI
│   │   ├── app.py
│   │   ├── dashboard.py
│   │   ├── listing_panel.py
│   │   ├── pricing_panel.py
│   │   ├── reply_panel.py
│   │   └── settings_panel.py
│   └── utils/               # ユーティリティ
│       ├── config.py
│       └── logger.py
├── data/                    # データ保存
├── logs/                    # ログ
└── templates/               # テンプレート・サンプル
```

## 注意事項

- 本ツールはメルカリの利用規約に基づいてご使用ください
- 過度な自動化はアカウント制限のリスクがあります
- 操作の間に適切な遅延を設定してください（デフォルト設定推奨）
- ログインは手動で行う必要があります（セキュリティのため）

## License

MIT License - see [LICENSE](LICENSE) for details.
