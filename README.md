# ImageMagick MCPサーバ

ImageMagick MCPサーバは、MCPプロトコル（Model Context Protocol）を使用してImageMagickの画像処理機能を提供するサーバです。現在は画像の二値化機能のみを実装しています。

## 機能

- 画像の二値化処理（閾値を指定可能）
- MCPプロトコルによるAIアシスタントとの連携
- 処理結果の画像表示

## 必要条件

- Python 3.8以上
- ImageMagick
- MCPライブラリ
- Wandライブラリ（ImageMagickのPythonバインディング）
- Clickライブラリ

## インストール

1. リポジトリをクローン:
```bash
git clone https://github.com/aimino/imagemagic-mcp.git
cd imagemagic-mcp
```

2. 依存関係のインストール:
```bash
# ImageMagickのインストール
sudo apt-get update
sudo apt-get install -y imagemagick libmagickwand-dev

# Pythonパッケージのインストール
pip install wand mcp click
```

## 使用方法

### サーバの実行

サーバは以下の方法で実行できます:

1. 直接Pythonで実行:
```bash
python imagemagick_server.py
```

2. MCPのCLIツールを使用:
```bash
mcp run imagemagick_server.py
```

このサーバは以下のツールを提供します:
- `binarize_image`: ImageMagickを使用して画像を二値化

### MCPサーバの設定

MCPサーバを使用するには、`cline_mcp_settings.json`ファイルを適切な場所に作成する必要があります:

#### Windows
```
%APPDATA%\cline\cline_mcp_settings.json
```

#### macOS/Linux
```
~/.config/cline/cline_mcp_settings.json
```

`cline_mcp_settings.json`ファイルの内容は以下のようにします:

```json
{
  "mcpServers": {
    "imagemagick-mcp": {
      "command": "python",
      "args": ["C:/path/to/imagemagic-mcp/imagemagick_server.py"],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

`C:/path/to/imagemagic-mcp`は実際のリポジトリのパスに置き換えてください。

### Claudeやその他のMCPクライアントでのテスト

サーバが実行され、設定されると、Claudeやその他のMCPクライアントがこれを使用して画像処理を行うことができます。

例えば、Claudeでは以下のように使用できます:

```
imagemagick-mcpツールを使って画像を二値化したいです。
```

Claudeは以下のようなコマンドでMCPサーバを使用して画像を二値化できます:

```json
{
  "image_path": "/path/to/image.jpg",
  "threshold": 0.5
}
```

### 仕組み

サーバはMCPプロトコルを使用してAIアシスタントからのリクエストを受け取り、ImageMagick（Wandライブラリ経由）を使用して画像処理を行います。通信はstdio（標準入出力）を通じて行われ、Claudeやその他のMCP対応アシスタントと互換性があります。

Claudeが画像を二値化するリクエストを受け取ると:
1. `cline_mcp_settings.json`の設定を使用してMCPサーバに接続
2. 画像パスと閾値パラメータを指定して`binarize_image`ツールを呼び出す
3. サーバはImageMagickを使用して画像を二値化し、結果を返す

## ライセンス

MIT
