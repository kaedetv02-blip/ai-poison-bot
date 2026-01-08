import tweepy
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import sys
import io
import os
import datetime

# 文字化け対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    print("詳細：大喜利Botプログラムを開始します...")

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
        print("❌ エラー：鍵が見つかりません。GitHub Secretsの設定を確認してください。")
        sys.exit()

    # ==================================================
    # 1. Googleトレンド（日本）を取得
    # ==================================================
    # Google TrendsのRSSフィード（日本）
    rss_url = "https://trends.google.co.jp/trends/trendingsearches/daily/rss?geo=JP"
    
    try:
        print("Googleトレンドを取得中...")
        resp = requests.get(rss_url, timeout=10)
        # lxmlパーサーでXMLを解析
        soup = BeautifulSoup(resp.content, 'xml')
        
        items = soup.find_all('item')
        
        if not items:
            print("❌ エラー：トレンドが取得できませんでした。")
            sys.exit()

        # トレンド単語のリストを作成（上位15件ほど）
        trend_list = []
        for item in items[:15]:
            title = item.find('title').text
            trend_list.append(title)
        
        # リストをカンマ区切りの文字列にする（AIに渡すため）
        trends_str = ", ".join(trend_list)
        print(f"★取得したトレンド候補: {trends_str}")

    except Exception as e:
        print(f"通信/解析エラー: {e}")
        sys.exit()

    # ==================================================
    # 2. AIによる「大喜利お題」生成
    # ==================================================
    print("AIが大喜利のお題を考案中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    # 現在の日時（季節感を出すため）
    now = datetime.datetime.now()
    date_str = now.strftime("%m月%d日")

    prompt = f"""
    あなたはX（Twitter）で大人気の「大喜利Bot」です。
    以下の【トレンド単語リスト】を見て、最も盛り上がりそうな単語を1つ選び、面白い大喜利のお題を作ってください。

    【トレンド単語リスト】
    {trends_str}

    【重要ルール】
    1. **安全第一**: 事件・事故・政治・宗教・誰かが亡くなった話題・誰かを傷つける話題は**絶対に無視**してください。
    2. **一般化**: 選んだ単語が専門的すぎる場合（特定のゲーム名、IT用語、知らない芸能人など）は、**「RPG」「スマホ」「上司」「イケメン」**のような**誰でもわかる一般的な言葉**に置き換えてお題を作ってください。
       (例: 「エルデンリング」→「超難しいRPG」、「国会」→「学級会」)
    3. **回答しやすさ**: 回答者が知識ゼロでも答えられるよう、「状況」や「セリフ」を問う形式にしてください。
       (良い例: 「こんな〇〇は嫌だ」「〇〇が言いそうな一言」)
    4. **もし使える単語がなければ**: リストを無視して、「給料日」「満員電車」「コンビニ」など、万人が共感できるテーマで作成してください。

    【出力形式】
    以下の形式のみを出力してください（余計な挨拶は不要）。

    【お題】(ここにお題)
    #(ハッシュタグ) #大喜利 #IPPON
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0, # 創造性を高くする
        )
        ai_output = response.choices[0].message.content
        print(f"★生成結果:\n{ai_output}")

    except Exception as e:
        print(f"エラー：AI生成に失敗しました: {e}")
        sys.exit()

    # 3. 投稿
    # 出力そのまま投稿
    tweet_content = ai_output

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
