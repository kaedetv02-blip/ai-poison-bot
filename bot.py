name: Daily Run Bot

on:
  schedule:
    # 日本時間の 7, 10, 12, 15, 18, 21, 23時に実行
    - cron: '0 22 * * *'
    - cron: '0 1 * * *'
    - cron: '0 3 * * *'
    - cron: '0 6 * * *'
    - cron: '0 9 * * *'
    - cron: '0 12 * * *'
    - cron: '0 14 * * *'
  
  # 手動実行ボタン
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: リポジトリのコピー
        uses: actions/checkout@v3

      - name: Pythonのセットアップ
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: ライブラリのインストール
        # ここに lxml を追加しました
        run: |
          pip install tweepy requests beautifulsoup4 openai lxml

      - name: Botの実行
        env:
          X_API_KEY: ${{ secrets.X_API_KEY }}
          X_API_SECRET: ${{ secrets.X_API_SECRET }}
          X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
          X_ACCESS_TOKEN_SECRET: ${{ secrets.X_ACCESS_TOKEN_SECRET }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python bot.py
