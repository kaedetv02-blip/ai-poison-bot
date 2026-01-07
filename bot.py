import tweepy
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import random
import sys
import io
import time
import os

# 文字化け対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("詳細：プログラムを開始します...")

    # ==================================================
    # 鍵の読み込み
    # ==================================================
    try:
        X_API_KEY = os.environ["X_API_KEY"]
        X_API_SECRET = os.environ["X_API_SECRET"]
        X_ACCESS_TOKEN = os.environ["X_ACCESS_TOKEN"]
        X_ACCESS_TOKEN_SECRET = os.environ["X_ACCESS_TOKEN_SECRET"]
        OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    except KeyError:
        print("エラー：鍵が見つかりません。GitHub Secretsの設定を確認してください。")
        sys.exit()

    # ==================================================
    # 1. ネタ元のRSS（まとめサイト）リスト
    # ==================================================
    # ここに好きなまとめサイトのRSS URLを追加・変更できます
    rss_urls = [
        "http://blog.livedoor.jp/news23vip/index.rdf",       # VIPPERな俺（VIP系）
        "http://alfalfalfa.com/index.rdf",                  # アルファルファモザイク（総合）
        "http://himasoku.com/index.rdf",                    # 暇人速報（ニュース系）
        "http://blog.livedoor.jp/nicovip2ch/index.rdf",     # ニコニコVIP2ch
        "http://workingnews.blog77.fc2.com/?xml",           # 働くモノニュース（仕事・社会）
    ]
    
    # ランダムに1つのサイトを選ぶ
    target_rss = random.choice(rss_urls)
    print(f"★今回のネタ元: {target_rss}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # RSSを取得
        resp = requests.get(target_rss, headers=headers, timeout=10)
        # XMLをパース（html.parserでも簡易的に読めます）
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # 記事（item）をすべて取得
        items = soup.find_all('item')
        if not items:
            # RDF形式の場合の対応
            items = soup.find_all('entry')

        if not items:
            print("❌ エラー：記事が見つかりませんでした。")
            sys.exit()

        # ランダムに1記事選ぶ
        chosen_item = random.choice(items)
        
        # タイトルとURLを抽出
        title = chosen_item.find('title').get_text().strip()
        link = chosen_item.find('link').get_text().strip()
        
        # 次の処理のためにURLへアクセスして本文を少し取る（AIの精度向上のため）
        print(f"記事を取得中... {title}")
        print(f"URL: {link}")
        time.sleep(1)

        article_resp = requests.get(link, headers=headers, timeout=10)
        article_soup = BeautifulSoup(article_resp.content, 'html.parser')

        # 本文抽出（サイトによって構造が違うため、body全体のテキストをごっそり取ってAIに整理させる）
        # ※長すぎるとエラーになるので先頭3000文字程度にカット
        body_text = article_soup.get_text().replace("\n", " ").replace("\r", "")
        # 空白削除
        body_text = ' '.join(body_text.split())
        content_for_ai = body_text[:3000]

        print(f"★取得データ（抜粋）: {title}")

    except Exception as e:
        print(f"通信/解析エラー: {e}")
        sys.exit()

    # ==================================================
    # 2. AIによる要約生成
    # ==================================================
    print("AIが記事を要約中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    あなたは「2ch（5ch）の面白いスレを紹介するインフルエンサー」です。
    以下の【Webサイトのテキスト】から、ノイズ（広告やメニュー）を除去し、
    このスレ（記事）の内容を面白おかしく要約して紹介してください。

    【Webサイトのテキスト】:
    タイトル：{title}
    本文の一部：{content_for_ai}

    【出力ルール】
    1. 1行目：記事のタイトルをそのまま書く（【】などで強調する）。
    2. 2行目以降：スレの内容やオチ、みんなの反応などを「3つの箇条書き」で要約する。
    3. 最後に一言：あなたの感想を「〜ワロタ」「〜草」などのネットスラングを使って短く添える。
    4. 全体を通して、広告の文言や「ランキング」などの無関係な情報は完全に無視すること。
    
    出力例：
    【スレタイ】会社で「お前無能だな」って言われたから言い返した結果ｗｗｗ

    ・上司にミスを指摘されて逆ギレしたイッチ
    ・「お前こそハゲやんけ」と言い放ち会議室が凍りつく
    ・現在は無敵の人となって自宅警備員をしている模様

    さすがにこれはイッチが悪いやろｗ メンタル強すぎワロタ
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0, 
        )
        ai_output = response.choices[0].message.content
        print(f"★生成結果:\n{ai_output}")

    except Exception as e:
        print(f"エラー：AI生成に失敗しました: {e}")
        sys.exit()

    # 3. 投稿
    # リンクを付けることで、気になった人が元記事を見に行けるようにします
    tweet_content = f"{ai_output}\n\n元記事: {link}\n#2ch #面白いスレ #暇つぶし"

    try:
        client_x = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET
        )
        client_x.create_tweet(text=tweet_content)
        print("✅ 投稿成功！")

    except Exception as e:
        print(f"❌ 投稿失敗：{e}")
        if "duplicate" in str(e).lower():
            print("重複エラー：スキップします。")

if __name__ == "__main__":
    main()
