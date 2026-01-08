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
    # 1. トレンド取得（2段構え）
    # ==================================================
    # URLリスト（上から順に試す）
    rss_sources = [
        # 1. Googleトレンド（Daily）: .com (国際版の日本リージョン)
        "https://trends.google.com/trends/trendingsearches/daily/rss?geo=JP",
        # 2. Googleニュース（バックアップ）
        "https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja"
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    trend_list = []
    
    for rss_url in rss_sources:
        try:
            print(f"トレンド取得を試行中... ({rss_url[:30]}...)")
            resp = requests.get(rss_url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                items = soup.find_all('item')
                
                if items:
                    for item in items[:15]:
                        title_tag = item.find('title')
                        if title_tag:
                            trend_list.append(title_tag.get_text())
                    
                    if trend_list:
                        print("✅ 取得成功！")
                        break # 成功したらループを抜ける
            else:
                print(f"⚠️ 取得失敗 (Status: {resp.status_code})。次のソースを試します。")

        except Exception as e:
            print(f"⚠️ エラー発生: {e}。次のソースを試します。")
            continue

    # どちらもダメだった場合
    if not trend_list:
        print("❌ すべてのソースからトレンド取得に失敗しました。")
        sys.exit()

    trends_str = ", ".join(trend_list)
    print(f"★使用するトレンド候補: {trends_str}")

    # ==================================================
    # 2. AIによる「大喜利お題」生成
    # ==================================================
    print("AIが大喜利のお題を考案中...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    # プロンプトの修正点：具体的なジャンル例（RPGなど）を削除し、
    # その単語の「ジャンル」に合わせて柔軟に変換するように指示を変更
    prompt = f"""
    あなたはX（Twitter）で大人気の「大喜利Bot」です。
    以下の【トレンド単語リスト】を見て、最も大喜利のお題にしやすそうな単語を1つ選んでください。

    【トレンド単語リスト】
    {trends_str}

    【重要なお願い】
    最近「RPG」ネタばかりになっているので、今回は**RPG・ファンタジー以外のジャンル**（日常、学校、会社、恋愛、スポーツ、芸能など）を優先して作ってください。

    【ルール】
    1. **安全第一**: 事件・事故・政治・誰かが傷つく話題は絶対に避けてください。
    2. **わかりやすく**: 選んだ単語がマニアックな場合（知らない人の名前や専門用語）は、**その単語そのものを使わず**、誰でもわかる言葉に言い換えてください。
       * 悪い例：特定のゲーム名を使う
       * 良い例：「話題の新作ゲーム」「無理ゲー」など
       * 悪い例：知らない野球選手の名前
       * 良い例：「大谷翔平レベルの選手」「ベンチ入り選手」など
    3. **形式**: 「こんな〇〇は嫌だ」「〇〇が言いそうな一言」「写真で一言」など、回答者が即座に答えられる形式にしてください。

    【出力形式】
    以下の形式のみを出力してください。（余計な挨拶は不要）

    【お題】(ここにお題)
    
    #(選んだ単語や関連ワード) #大喜利 #IPPON
    
    ★いいね数が一番多い人が優勝！
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
